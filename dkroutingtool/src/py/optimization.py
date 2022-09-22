"""Capacitated Vehicle Routing Problem with Time Windows (CVRPTW).
"""
from __future__ import print_function

from attr import attrs, attrib
import pandas as pd
import logging
from six.moves import xrange
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import numpy as np
from functools import partial
import copy
import math
import time
from time import strftime, gmtime
import os
import traceback
logging.getLogger().setLevel(logging.INFO)

from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import fcluster
import string
import ujson

import manual_viz
import file_config
from visualization import colorList
from output.route_solution_data import IntermediateOptimizationSolution, FinalOptimizationSolution
import osrmbindings

osrm_filepath = os.environ['osm_filename']

resequencing = True
resequencing_step_size = 0.0002 # Arbitrary and small, in the scale of long/lat degrees

clustering_agglomeration = True #Uses naive thresholding agglomeration unless sprawling is enabled
agg_threshold_radius = 5 #Units in seconds of travel
agglomeration_sprawling = True #Creates clusters that sprawl as long as a node is within the threshold, and probably better to use smaller radii than naive method
reoptimize_subnodes = 'relaxed' #Enable (either 'strict' or 'relaxed') to actually re-optimize routes if agglomeration is executed, this is beneficial for dense meandering streets but takes more time (disable with the value 'disabled')
reoptimize_time_factor = 0.2 #Amount of time allowed to reoptimize the subnodes after the supernode routing as a percentage of the initial allowed time

#max_time_horizon = 28800
max_time_horizon = 24*60*60

color_naming = True
north_south_ordering = True

verbose = False

def clean_up_time(hour):
    hour = hour.strip()
    if hour.endswith('AM'):
        hour, minute = hour[:-2].split(':')
        if hour == '12':
            hour = '0'
        seconds = (int(hour)*60*60)+(int(minute)*60)
    elif hour.endswith('PM'):
        hour, minute = hour[:-2].split(':')
        if hour == '12':
            hour = '0'
        seconds = ((int(hour)+12)*60*60)+(int(minute)*60)
    else: # 24 clock
        hour, minute = hour.split(':')
        seconds = (int(hour)*60*60)+(int(minute)*60)
        
    return seconds

def get_euclidean_distance(start, end):
    return ((start[0] - end[0])**2 + (start[1]-end[1])**2)**0.5

def interpolate_segment(segments, step_size_factor):
    new_coordinates = []
    for index in range(len(segments)-1):
        start = segments[index]
        end = segments[index+1]
        
        new_coordinates.append(start)
        distance = get_euclidean_distance(start, end)
        if distance > (resequencing_step_size*step_size_factor):
            extra_points = math.ceil(distance/(resequencing_step_size*step_size_factor))+1
            xs = np.linspace(start[0], end[0], extra_points)[1:-1] #excluding the start+end points
            ys = np.linspace(start[1], end[1], extra_points)[1:-1]
            for x,y in zip(xs, ys):
                new_coordinates.append([x,y])
    new_coordinates.append(end)
    return new_coordinates

def get_routes(r, d, a, m):
    capacity_dimension = r.GetDimensionOrDie('Capacity')

    all_routes = []
    for vehicle_id in range(d.num_vehicles):
        all_routes.append([])
        index = r.Start(vehicle_id)
        while not r.IsEnd(index):    
            previous_index = index #start point
            index = a.Value(r.NextVar(index)) #end point
            if not r.IsEnd(index):
                all_routes[-1].append(m.IndexToNode(index))
    return all_routes

def get_loaded_distance(data, manager, routing, assignment): 
    total_loaded_time = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')

    for vehicle_id in range(data.num_vehicles):
        index = routing.Start(vehicle_id)
        distance = 0
        while not routing.IsEnd(index):

            previous_index = index #start point

            index = assignment.Value(routing.NextVar(index)) #end point

            load_var = capacity_dimension.CumulVar(index)

            current_distance = routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            #print('Looping', current_distance, assignment.Value(load_var), previous_index, index)
            loaded_time = current_distance*assignment.Value(load_var)
            total_loaded_time += loaded_time
            distance += current_distance
    #print('Done')
    return total_loaded_time

def get_score_with_upper_bound(data, manager, routing, assignment, soft_upper_bound_value, soft_upper_bound_penalty): 
    total_time = 0
    total_score = 0
    capacity_dimension = routing.GetDimensionOrDie('Capacity')

    for vehicle_id in range(data.num_vehicles):
        index = routing.Start(vehicle_id)
        distance = 0
        while not routing.IsEnd(index):

            previous_index = index #start point

            index = assignment.Value(routing.NextVar(index)) #end point

            load_var = capacity_dimension.CumulVar(index)

            current_distance = routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            
            current_load = assignment.Value(load_var)
            total_time += current_distance
            
            if not routing.IsEnd(index): # to reproduce the fact that we don't apply a penalty for the last node
                load_difference = current_load - soft_upper_bound_value
                if load_difference > 0:
                    total_score += load_difference*soft_upper_bound_penalty 
            
    return total_score+total_time

def get_last_time(data, manager, routing, assignment):
    total_time = 0
    time_dimension = routing.GetDimensionOrDie('Time')

    for vehicle_id in range(data.num_vehicles):
        index = routing.End(vehicle_id)
        time_var = time_dimension.CumulVar(index)
        total_time += assignment.Min(time_var)

    return total_time

class Vehicle():
    """Stores the property of a vehicle"""
    def __init__(self, time_distance=None, travel_distance=None,
                 capacity=45, name=None, osrm_profile=None,
                 start=None, end=None):
        """Initializes the vehicle properties"""
        self._capacity = capacity
        self._time_distance = time_distance
        self._travel_distance = travel_distance
        self._name = name
        self._osrm_profile = osrm_profile
        self._start = start
        self._end = end

    @property
    def capacity(self):
        """Gets vehicle capacity"""
        return self._capacity

    @property
    def time_distance_matrix(self):
        """time matrices from node to node"""
        return self._time_distance

    @property
    def travel_distance_matrix(self):
        """time matrices from node to node"""
        return self._travel_distance

    @property
    def name(self):
        """Returns name of veh, used in viz"""
        return self._name

    @property
    def osrm_profile(self):
        return self._osrm_profile

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end


class DataProblem():
    """
    define the input to the dataproblem
    """
    def __init__(self, node_data, vehicle, config=None, node_name_ordered=None, node_clusters = None):
        """
        data problem class that takes the output directly from ORSM and then build the data problem so that it could be \
        consumed by or-tool enigne
        :param node_data (NodeLoader Class): rich NodeLoader instance that has distance matrices, demand and etc
        :param vehicle (list(Vehicle)): a list of vehicle instance
        """
        
        self._vehicle = vehicle #TODO maybe replace this with a plural
        self._num_vehicles = len(self._vehicle)
        
        if config:
#             ## WHY is this here ? We filter in the built_time_dist_matrix.py - filter_nodedata function
#             _boolean_selected = np.where((node_data.type_name[:, 0] == 'Customer') 
#                                          | (node_data.type_name[:, 1] == config['Start_Point'])
#                                          | (node_data.type_name[:, 1] == config['End_Point']))[0]

            _boolean_selected = [i for i in range(len(node_data.all_clean_nodes))]
        elif node_name_ordered:
            _boolean_selected = np.array([])
            for node_name in node_name_ordered:
                _boolean_selected = np.append(_boolean_selected, np.where(node_data.names==node_name)[0])
            _boolean_selected = _boolean_selected.astype(int)

            #_boolean_selected = np.array([])
            for node_name in node_name_ordered:
                _boolean_selected = np.append(_boolean_selected, np.where(node_data.names==node_name)[0])
            _boolean_selected = _boolean_selected.astype(int)

        if verbose:
            print("Node filtering")
            print(_boolean_selected)
        # Locations in block unit
        self._boolean_selected = _boolean_selected
        self._locations = node_data.lat_long_coords[_boolean_selected]
        self._demands = node_data.get_attr('buckets')[_boolean_selected]
        self._distance = node_data.get_time_or_dist_mat(veh=vehicle[0].osrm_profile, time_or_dist='dist')[_boolean_selected][:,_boolean_selected]
        self._time_distance = node_data.get_time_or_dist_mat(veh=vehicle[0].osrm_profile, time_or_dist='time')[_boolean_selected][:,_boolean_selected]
        self._num_locations = self._locations.shape[0]
        self._demands = [i if pd.notnull(i) else 0 for i in self._demands]
        self.nodes_to_names = dict()
        
        if node_clusters is None:
            self.node_clusters = []
        else:
            self.node_clusters = node_clusters
        
        self.unload_indices = set()
        for index, name in enumerate(node_data.get_attr('name')[_boolean_selected]):
            self.nodes_to_names[index] = name
            if 'UNLOAD' in name.upper():
                self.unload_indices.add(index)
        
        if config is not None:
            # Hacky fix - if we are running manual review we don't have a config and don't have start and end stuff
            self.names_to_nodes = {v:k for (k,v) in self.nodes_to_names.items()}
            
            self.all_start_points = [int(self.names_to_nodes[v.start]) for v in vehicle]
            self.all_end_points = [int(self.names_to_nodes[v.end]) for v in vehicle] # maybe we want those as sets
            
            for point in self.all_start_points+self.all_end_points: # Starts and ends are assumed to have zero demand
                self._demands[point] = 0
                        
            extra_starts = list(set(self.all_end_points).difference(set(self.all_start_points)))
            self.cluster = config.get('cluster')
            self.k_cluster = config.get('k_cluster')
            
        self.workaround_dummy_vehicles = 0

        # Section below allows configurable hours
        if config is None:
            self.configured_time_horizon = max_time_horizon
        elif config.get('hours_allowed') is None:
            self.configured_time_horizon = max_time_horizon
        else:
            self.configured_time_horizon = int(config.get('hours_allowed')*60*60)
        
        if config is None:
            self.start_seconds = 0
        elif 'start_time' in config: # Only matters if you have time windows
            self.start_seconds = clean_up_time(config['start_time'])
            self.configured_time_horizon = self.start_seconds + self.configured_time_horizon
        else:
            self.start_seconds = 0

        self._time_windows = [(self.start_seconds, self.configured_time_horizon) for j in range(self._num_locations)]
        
        # User-provided time windows
        if config and config.get('use_time_windows', False):
            user_time_windows = node_data.get_attr('time_windows')[_boolean_selected]

            time_windows_specified = 0
            for window in user_time_windows: # A bit of a silly loop
                if isinstance(window, str):
                    time_windows_specified += 1        

            processed_time_windows = []
            for window in user_time_windows:
                if isinstance(window, str):
                    start, end = window.split('-')
                    seconds = (clean_up_time(start), clean_up_time(end))
                    processed_time_windows.append(seconds)
                elif np.isnan(window):
                    processed_time_windows.append((self.start_seconds, self.configured_time_horizon)) # A whole day for unspecified locations

            if time_windows_specified > 0:
                self._time_windows = processed_time_windows
        
        if verbose:
            logging.info('Time windows', self._time_windows)
        
        default_load_time_mins = 2.5
        if config is not None:
            self._load_time = config['load_time']*60
        else:
            self._load_time = default_load_time_mins*60

    @property
    def vehicle(self):
        """Gets a vehicle"""
        return self._vehicle

    @property
    def num_vehicles(self):
        """Gets number of vehicles"""
        return self._num_vehicles

    @property
    def locations(self):
        """Gets locations"""
        return self._locations

    @property
    def vehicle_capacity(self):
        return [v.capacity for v in self._vehicle]

    @property
    def num_locations(self):
        """Gets number of locations"""
        return len(self._locations)

    @property
    def demands(self):
        """Gets demands at each location"""
        return self._demands

    @property
    def time_per_demand_unit(self):
        """Gets the time (in min) to load a demand"""
        return self._load_time 

    @property
    def time_windows(self):
        """Gets (start time, end time) for each locations"""
        return self._time_windows

    @property
    def time_distance(self):
        return self._time_distance

    @property
    def distance_matrix(self):
        return self._distance



class CreateTimeEvaluator(object):
    """Creates callback to get total times between locations.
    BIG NOTE HERE: Only used after the solution is found, for recording purposes
    #TODO We need to refactor this bit so we don't need to change code in two places to keep it synchronized with what the optimizer actually calculates, e.g. if we change the service time formula"""
    @staticmethod
    def service_time(data, node):
        """Gets the service time for the specified location."""
        if data.node_clusters and node not in data.all_start_points+data.all_end_points:
            cluster = data.node_clusters[node]
            return int(len(cluster)*(data.time_per_demand_unit + agg_threshold_radius))
        
        return data.time_per_demand_unit

    def travel_time(self, data,from_node, to_node):
        """Gets the travel times between two locations."""
        if from_node == to_node:
            travel_time = 0
        elif self.manual_run:
            travel_time = data.time_distance[from_node][to_node]
        else:
            travel_time = data.vehicle[self.vehicle_id].time_distance_matrix[from_node][to_node]
        return travel_time

    def __init__(self, data, vehicle_id = 0, manual_run = False):
        """Initializes the total time matrix."""
        self.vehicle_id = vehicle_id
        self._total_time = {}
        self.manual_run = manual_run
        # precompute total time to have time callback in O(1)
        for from_node in range(data.num_locations):
            self._total_time[from_node] = {}
            for to_node in range(data.num_locations):
                if from_node == to_node:
                    self._total_time[from_node][to_node] = 0
                else:
                    self._total_time[from_node][to_node] = int(
                        self.service_time(data, from_node) +
                        self.travel_time(data, from_node, to_node))

    def time_evaluator(self, from_node, to_node):
        """Returns the total time between the two nodes"""
        return self._total_time[from_node][to_node]

class ConsolePrinter():
    """Print solution to console"""
    def __init__(self, data, routing, assignment, manager):
        """Initializes the printer"""
        self._data = data
        self._routing = routing
        self._assignment = assignment
        self.manager = manager

    @property
    def data(self):
        """Gets problem data"""
        return self._data

    @property
    def routing(self):
        """Gets routing model"""
        return self._routing

    @property
    def assignment(self):
        """Gets routing model"""
        return self._assignment

    def print(self):
        """Prints assignment on console"""
        # Inspect solution.
        capacity_dimension = self.routing.GetDimensionOrDie('Capacity')
        time_dimension = self.routing.GetDimensionOrDie('Time')
        total_dist = 0
        total_time = 0
        for vehicle_id in range(self.data.num_vehicles):
            index = self.routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {0}:\n'.format(vehicle_id+1)
            route_dist = 0
            route_time = 0
            while not self.routing.IsEnd(index):
                node_index = self.manager.IndexToNode(index)
                next_node_index = self.manager.IndexToNode(
                    self.assignment.Value(self.routing.NextVar(index)))
                route_dist += self.data.vehicle[vehicle_id].travel_distance_matrix[node_index][next_node_index]
                load_var = capacity_dimension.CumulVar(index)
                time_var = time_dimension.CumulVar(index)
                route_load = self.assignment.Value(load_var)
                route_time += self.data.vehicle[vehicle_id].time_distance_matrix[node_index][next_node_index]
                time_value = self.assignment.Value(time_var)
                #transit_quantity = self.assignment.Value(transit_var)
                plan_output += ' {0} Load({2}) Time({1:3.3}) Window({3})->'.format(node_index,route_time, route_load, time_value)
                index = self.assignment.Value(self.routing.NextVar(index))

            node_index = self.manager.IndexToNode(index)
            load_var = capacity_dimension.CumulVar(index)
            route_load = self.assignment.Value(load_var)
            time_var = time_dimension.CumulVar(index)
            time_value = self.assignment.Value(time_var)
            total_dist += route_dist
            total_time += route_time
            plan_output += ' {0} Load({1})\n'.format(node_index, route_load)
            plan_output += 'Distance of the route: {0}km\n'.format(route_dist/1000)
            plan_output += 'Load of the route: {0}\n'.format(route_load)
            plan_output += 'Time of the route: {:4.4}min\n'.format(route_time)
            plan_output += 'Last window: {0} min\n'.format(time_value)
            
            if verbose:
                logging.info(f"Plan Output: {plan_output}")
        
        logging.info('Total Distance of all routes: {0}km'.format(total_dist/1000))
        logging.info('Total Time of all routes: {0}min'.format(total_time))
        return (total_dist, total_time)        

def print_metrics_to_file(route_dict, output_dir, node_data=None, vehicles=None):
    """
    Prints solution (time, load, dist) to file.
    """
    plan_output = ''
    for route_id, route in route_dict.items():
        if color_naming:
            display_name = route['display_name']
            plan_output += f'Route ID {display_name}'
        else:
            plan_output += f'Route ID {route_id}'

        if vehicles != None:
            plan_output += ', ' + vehicles[route_id].name + ':\n'
        else:
            plan_output += ':\n'
            
        for i, route_index in enumerate(route["indexed_route"]):
            if node_data == None:
                plan_output += ' {0} '.format(route_index)
            else:
                plan_output += ' {0} '.format(node_data.get_names_by_index(route_index))
            if i < len(route["indexed_route"])-1:
                plan_output += '->'
        #plan_output += ' Load({1})\n'.format(route["load"])
        plan_output += '\n'
        plan_output += 'Distance of the route: {0}km\n'.format(int(route["total_dist"])/1000)
        plan_output += 'Load of the route: {0}\n'.format(int(route["load"]))
        plan_output += 'Time of the route: {0}min\n\n'.format(int(route["total_time"]/60))

    plan_output += "Total: \n"
    #Total the dist and time
    total_dist = 0
    total_time = 0
    for i in route_dict.keys():
        total_dist += route_dict[i]["total_dist"]
        total_time += route_dict[i]["total_time"]/60
    plan_output += "Distance of all routes: {0}km\n".format(int(total_dist)/1000)
    plan_output += 'Time of all routes: {0}min\n\n'.format(int(total_time))

    text_file = open(file_config.SolutionOutput.get_filename(output_dir), "w")
    text_file.write(plan_output)
    text_file.close()
    

def create_vehicle(node_data, config):
    """
    Functions to set up the number of vehicles
    """
    num_vehicle_type = len(config['trips_vehicle_profile'])
    if verbose:
        logging.info('Number of vehicle types', num_vehicle_type)
    vehicle_profile = config['trips_vehicle_profile']

    
    _boolean_selected = np.where(np.isin(node_data.all_clean_nodes[:,1], [config['Start_Point'], config['End_Point'] ])
                   | (node_data.all_clean_nodes[:,0]=='Customer') )[0]
    

    # Determine number of vehicles or trips available 
    if config['enable_unload']: 
        
        all_start_end_options = []
        for v in config['unload_vehicles']:
            all_start_end_options.extend(v[2:])
        all_start_end_options =  list(set(all_start_end_options))
        _boolean_selected = np.where(np.isin(node_data.all_clean_nodes[:,1], all_start_end_options)
                   | (node_data.all_clean_nodes[:,0]=='Customer') )[0]
        
        # If we are using unloads then the vehicle creation is different
        vehicles_details = config['unload_vehicles']
        vehicles = []
        for vec in vehicles_details:   #, "Dibout , 3 Wheeler, Cap 81"
            _time_distance = node_data.get_time_or_dist_mat(veh = vec[0], time_or_dist='time')[_boolean_selected][:,_boolean_selected]   
            _travel_distance = node_data.get_time_or_dist_mat(veh = vec[0], time_or_dist='dist')[_boolean_selected][:,_boolean_selected]
            metadata = f"{'-'.join(config['optimized_region'])} , {vec[0]}, Cap {vec[1]}"
            vehicles.append(Vehicle(_time_distance, _travel_distance, vec[1], metadata, vec[0], vec[2], vec[3]))
                   
    else:
        total_demand = sum([i for i in node_data.get_attr('buckets')[_boolean_selected] if i > 0])
        # Works for now but if vehicles of diff capacity in same zone we need to change this to get the total capacity
        vehicle_number = int((total_demand / config['trips_vehicle_profile'][0][1]) * 2) # 2 provides good surplus for balancing
        # Provide at least 4 vehicles for flexibility with balancing - if dealing with a low demand zone
        vehicle_number = max([4, vehicle_number])

        vehicles = []
        for vec in range(num_vehicle_type): # TODO - if there are multiple vehicle types then we create a lot of extra vehicles
            _time_distance = node_data.get_time_or_dist_mat(veh = vehicle_profile[vec][0], time_or_dist='time')[_boolean_selected][:,_boolean_selected]   
            _travel_distance = node_data.get_time_or_dist_mat(veh = vehicle_profile[vec][0], time_or_dist='dist')[_boolean_selected][:,_boolean_selected]
            # Create some summary info for display purposes on maps
            metadata = f"{'-'.join(config['optimized_region'])} , {vehicle_profile[vec][0]}, Cap {vehicle_profile[vec][1]}"
            vehicles = vehicles + [
                        Vehicle(_time_distance,_travel_distance,vehicle_profile[vec][1], 
                                metadata, vehicle_profile[vec][0], config['Start_Point'][0], config['End_Point'][0]) 
                            for j in range(vehicle_number)
                        ]
    return vehicles


def get_optimal_route(data, vehicles, dist_or_time='time', warmed_up = None, max_solver_time_min=2, soft_upper_bound_value=0, soft_upper_bound_penalty=0, span_cost_coefficient=0, fast_run=False):
    manager = pywrapcp.RoutingIndexManager(int(data.num_locations),
                                        int(data.num_vehicles), 
                                       [int(data.names_to_nodes[i.start]) for i in vehicles],
                                       [int(data.names_to_nodes[i.end]) for i in vehicles])

    routing = pywrapcp.RoutingModel(manager)

    # Define Specific Vehicle Costs - Allows for vehicles with different costs 
    # keep transit callback alive
    transit_callback = []
    transit_callback_index_arr = []
    for vehicle_id in range(0, data.num_vehicles):
            
        if dist_or_time == 'time':
            distance_matrix = vehicles[vehicle_id].time_distance_matrix
        elif dist_or_time == 'dist':
            distance_matrix = vehicles[vehicle_id].travel_distance_matrix

        def distance_callback_vehicle(from_index, to_index, data=distance_matrix, service_time = int(data.time_per_demand_unit), clusters=data.node_clusters, points = data.all_start_points+data.all_end_points, unload_indices = data.unload_indices):
            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            
            total_service_time = service_time
            if clusters and from_node not in points:
                cluster = clusters[from_node]
                total_service_time = int(len(cluster)*(service_time + agg_threshold_radius))
            
            travel_time = 0
            if from_node == to_node:
                travel_time = 0
            elif from_node in unload_indices and to_node in unload_indices:
                travel_time = 10000000 #big number
            elif from_node in points and to_node in unload_indices:
                travel_time = 10000000 #another big number because that vehicle just started
            elif from_node in unload_indices and to_node in points:
                travel_time = 10000000 #another big number because that vehicle is ending its run
            else:
                travel_time = data[from_node][to_node]
            
            return int(travel_time)+total_service_time

        transit_callback.append(distance_callback_vehicle)
        transit_callback_index_arr.append(routing.RegisterTransitCallback(transit_callback[-1]))
        routing.SetArcCostEvaluatorOfVehicle(transit_callback_index_arr[-1], vehicle_id) #TODO change it to probably the time evaluator

   
    def create_demand_evaluator(data):
        """Creates callback to get demands at each location."""
        _demands = data.demands

        def demand_evaluator(manager, node):
            """Returns the demand of the current node"""
            return _demands[manager.IndexToNode(node)]

        return demand_evaluator

    def add_capacity_constraints(routing, data, demand_evaluator_index):
        """Adds capacity constraint"""
        capacity = 'Capacity'
        
        slack_capacity = 0
        if min(data._demands) < 0:
            slack_capacity = int(-min(data._demands))

        routing.AddDimensionWithVehicleCapacity(
            demand_evaluator_index,
            slack_capacity,
            [f.capacity for f in data.vehicle],
            True,  # start cumul to zero
            capacity)

        capacity_dimension = routing.GetDimensionOrDie(capacity)
        #capacity_dimension.SetGlobalSpanCostCoefficient(100)
        for location_idx, time_window in enumerate(data.time_windows):
            if location_idx in data.all_start_points or location_idx in data.all_end_points:
                continue
            index = manager.NodeToIndex(location_idx)
            capacity_dimension.SetCumulVarSoftUpperBound(index, soft_upper_bound_value, soft_upper_bound_penalty)
        
        # Add Capacity constraint
    demand_evaluator_index = routing.RegisterUnaryTransitCallback(
        partial(create_demand_evaluator(data), manager))
    add_capacity_constraints(routing, data, demand_evaluator_index)

    def add_time_window_constraints(routing, manager, data, time_evaluator_index):
        """Add Global Span constraint"""
        time = 'Time'
        horizon = data.configured_time_horizon
        routing.AddDimensionWithVehicleTransits(
            time_evaluator_index,
            horizon,  # allow waiting time
            horizon,  # maximum time per vehicle
            False,  # don't force start cumul to zero since we are giving TW to start nodes
            time)
        time_dimension = routing.GetDimensionOrDie(time)
        # Add time window constraints for each location except depot
        # and 'copy' the slack var in the solution object (aka Assignment) to print it
        for location_idx, time_window in enumerate(data.time_windows):
            # The last two locations should be the start point and the end point so they are free of time windows
            # But this is a possible source of error 
            if location_idx in data.all_start_points or location_idx in data.all_end_points:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
            #time_dimension.SetCumulVarSoftLowerBound(index, 0, 0)
            #time_dimension.SetCumulVarSoftUpperBound(index, horizon, 1000000)
            routing.AddToAssignment(time_dimension.SlackVar(index))
        # Add time window constraints for each vehicle start node
        # and 'copy' the slack var in the solution object (aka Assignment) to print it
        for vehicle_id in xrange(data.num_vehicles):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(data.time_windows[0][0],data.time_windows[0][1])
            
            #time_dimension.SetCumulVarSoftUpperBound(index, horizon, 1000000)
            routing.AddToAssignment(time_dimension.SlackVar(index))
            # Warning: Slack var is not defined for vehicle's end node
            # routing.AddToAssignment(time_dimension.SlackVar(self.routing.End(vehicle_id)))
        time_dimension.SetGlobalSpanCostCoefficient(span_cost_coefficient) 

    # Add Time Window constraint
    add_time_window_constraints(routing, manager, data, transit_callback_index_arr)
    
    adjust_capacity_dimension = routing.GetDimensionOrDie('Capacity')
    for location_idx, demand in enumerate(data.demands):
        if demand < 0:
            # Makes unload nodes optional, with 0 penalty if not visited
            routing.AddDisjunction([manager.NodeToIndex(location_idx)], 0)
        if demand > 0:
            # No slack for customer nodes, might not even be necessary but safer?
            adjust_capacity_dimension.SlackVar(manager.NodeToIndex(location_idx)).SetValue(0)
    
    def find_clusters(linkage_matrix, demands, cap=81, k=None):        
        # Don't cluster is demand is lower than capacity
        if sum(demands) <= cap:
            return None, None
        
        if k:
            clusters= fcluster(linkage_matrix, k, criterion='maxclust')
            cdf = pd.DataFrame({'c':clusters,'d': demands})
            grp_c = cdf.groupby('c').sum().sort_values('d',ascending=False).reset_index()

            return clusters, grp_c[grp_c.d > .60 * cap].c.values

        # Search for clusters 
        else:
            for kv in range(2,25):
                clusters= fcluster(linkage_matrix, kv, criterion='maxclust')
                cdf = pd.DataFrame({'c':clusters,'d': demands})
                grp_c = cdf.groupby('c').sum().sort_values('d',ascending=False).reset_index()

                top_c_load = grp_c.iloc[0].d
                max_vol = top_c_load
                if max_vol <= cap:
                    return  clusters, grp_c[grp_c.d > .60 * cap].c.values

    if data.cluster:
        linkage_matrix = linkage(distance_matrix, "centroid")
        
        cap = vehicles[0].capacity

        if data.k_cluster:
            clusters, keep_clusters = find_clusters(linkage_matrix, data.demands, k=data.k_cluster, cap=cap)
        else:
            clusters, keep_clusters = find_clusters(linkage_matrix, data.demands, cap=cap)
        
        # Find_clusters can return None, None
        if keep_clusters is not None:
            veh_counter = 0
            for cluster in keep_clusters:
                total_cluster_demand = np.array(data.demands)[[np.where(clusters==cluster)[0]]].sum()
                vehicles_needed = int( np.ceil( total_cluster_demand / cap) )
                veh_list = list(range(veh_counter, veh_counter+vehicles_needed))
                for n in np.where(clusters==cluster)[0]:
                    if (data.demands[n] > 0): 
                        if verbose:
                            logging.info('Output of deprecated clustering method')
                            logging.info('-->', n,'veh=', veh_list)
                        routing.SetAllowedVehiclesForIndex(veh_list, manager.NodeToIndex(n)) 
                    # ref https://github.com/google/or-tools/issues/1258

                veh_counter += vehicles_needed


    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.time_limit.seconds = 60 * max_solver_time_min
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC) # the only one working with slack
    
    
    if not fast_run:
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    
    solver = routing.solver()  

    time_dimension = routing.GetDimensionOrDie('Time')
    capacity_dimension = routing.GetDimensionOrDie('Capacity')
        
    # Solve the problem.
    if warmed_up is not None:
        try:
            if reoptimize_subnodes == 'strict': 
                for vehicle_index, route in enumerate(warmed_up):
                    for node_index in route:
                        routing.SetAllowedVehiclesForIndex([vehicle_index], manager.NodeToIndex(node_index))
                search_parameters.time_limit.seconds = int(60 * max_solver_time_min * reoptimize_time_factor)
                assignment = routing.SolveWithParameters(search_parameters)
            elif reoptimize_subnodes == 'relaxed':
                clustered_assignment = routing.ReadAssignmentFromRoutes(warmed_up, ignore_inactive_indices=True)
                assignment = routing.SolveFromAssignmentWithParameters(clustered_assignment, search_parameters)
            else:
                routing.CloseModel()
                assignment = routing.ReadAssignmentFromRoutes(warmed_up, ignore_inactive_indices=True)
        except:
            traceback.print_exc()
            assignment = None
    else:
        assignment = routing.SolveWithParameters(search_parameters)
        assert assignment is not None, "No solution found, maybe increase allowed time or vehicles"
        
    #printer = ConsolePrinter(data, routing, assignment, manager)
    #printer.print()
    return assignment, manager, routing

def create_route_dict(assignment, manager, routing, data, nodedata, vehicles, route_dict_prev=None, vehicles_prev = None):
    """Creates dictionary of routes and total distances
    
    Dictionary keys are vehicle ids:
        Each vehicle id item contains another dictionary with :
            -"route" and "total_dist" as keys
            -"route" contains a list of ((x,y), route_load) tuples
                where x,y are gps coordinates
            -"total_dist" contains total distance of route in km
    """
    route_dict = {}
    total_dist = 0
    filtered_veh = {}
    filtered_route_dict = {}
    
    time_dimension = routing.GetDimensionOrDie('Time')
    
    for vehicle_id in range(data.num_vehicles):
        time_matrix = CreateTimeEvaluator(data, vehicle_id=vehicle_id)
        index = routing.Start(vehicle_id)
        route_dict[vehicle_id] = {"route": [], "total_dist": 0, "indexed_route": [], 'loads': [], 'demands': [], 'time': [], 'current_distance': [], 'travel_time': [], 'next_names':[], "current_names": []}
        route_dist = 0 
        route_load = 0
        route_time = 0
        
        while not routing.IsEnd(index):
            next_index = assignment.Value(routing.NextVar(index))
            node_index = manager.IndexToNode(index)
            next_node_index = manager.IndexToNode(next_index)
            route_dist += data.vehicle[vehicle_id].travel_distance_matrix[node_index][next_node_index]
            route_dict[vehicle_id]['current_names'].append(data.nodes_to_names[node_index])
            route_dict[vehicle_id]['next_names'].append(data.nodes_to_names[next_node_index])
            route_dict[vehicle_id]['travel_time'].append(data.vehicle[vehicle_id].time_distance_matrix[node_index][next_node_index])
            route_dict[vehicle_id]['current_distance'].append(data.vehicle[vehicle_id].travel_distance_matrix[node_index][next_node_index])
            #route_time += time_matrix(index, next_index)
            route_time += time_matrix.time_evaluator(node_index, next_node_index)
            #route_load += data.demands[node_index] #+ assignment.Value(routing.GetDimensionOrDie("Capacity").CumulVar(index))
            if data.demands[node_index] >= 0:
                route_load += data.demands[node_index]
            
            time_var = time_dimension.CumulVar(index)
            time_value = assignment.Value(time_var)
            route_dict[vehicle_id]['time'].append(time_value)
                
            route_dict[vehicle_id]["route"].append((data.locations[node_index], route_load))
            route_dict[vehicle_id]["indexed_route"].append(nodedata.df_gps_verbose.index[node_index])
            current_load = assignment.Value(routing.GetDimensionOrDie("Capacity").CumulVar(node_index))
            route_dict[vehicle_id]['loads'].append(current_load)
            route_dict[vehicle_id]['demands'].append(data.demands[node_index])
            previous_node_index = node_index
            index = assignment.Value(routing.NextVar(index))

        node_index = manager.IndexToNode(index)
        total_dist += route_dist

        route_dict[vehicle_id]["route"].append((data.locations[node_index], route_load))
        
        previous_load_increment = data.demands[previous_node_index] # needs this trick to show what the load was just before finishing the route
        if previous_load_increment > 0:
            current_load += previous_load_increment
        route_dict[vehicle_id]['demands'].append(data.demands[node_index])
        route_dict[vehicle_id]['loads'].append(current_load)
        route_dict[vehicle_id]["indexed_route"].append(nodedata.df_gps_verbose.index[node_index])
        route_dict[vehicle_id]["total_dist"] = route_dist
        route_dict[vehicle_id]["load"] = route_load
        route_dict[vehicle_id]["total_time"] = route_time

        #Copy over only used routes
        if len(route_dict[vehicle_id]["indexed_route"]) > 2:
            filtered_veh[vehicle_id] = vehicles[vehicle_id]
            filtered_route_dict[vehicle_id] = route_dict[vehicle_id]

    #Used if multiple runs are being pieced together
    if route_dict_prev != None:
        min_key = max(route_dict_prev.keys()) + 1
    #Rekey (some code later assumes indexes as keys, this is an easier fix)
    else:
        min_key = 0
        route_dict_prev = {}
        vehicles_prev = {}
    for veh_id, route in filtered_route_dict.items():
        route_dict_prev[min_key] = route
        vehicles_prev[min_key] = filtered_veh[veh_id]
        min_key += 1

    return (route_dict_prev, vehicles_prev)

def find_near_point(segment, route_df, forbidden, step_size_factor):
    to_return = []
    threshold = resequencing_step_size*step_size_factor

    nodes = route_df[['long_snapped', 'lat_snapped']].values
    distances = ((nodes-segment)**2).sum(axis=1)**0.5

    below_threshold = (distances < threshold).sum()
    if below_threshold > 0:
        closest_points = distances.argsort()
        for i in range(below_threshold):
            closest_point = closest_points[i]
            
            if closest_point not in forbidden:
                row = route_df.iloc[closest_point]
                to_return.append(row.values)
                forbidden.add(closest_point)
    return to_return

def resequence(node_data, data, routing, routes_all, original_routes, vehicle_profiles, unload_routes = None):
    ordered_nodes = dict()
    per_route_nodes = dict()
    
    if unload_routes is not None:
        original_routes = unload_routes['fake_routes']
        vehicle_indices = unload_routes['routes_to_vehicles']
        profiles = [vehicle_profiles[index] for index in vehicle_indices]
    else:
        profiles = vehicle_profiles
    
    for route_key, old_route in enumerate(original_routes):
        if len(old_route) == 0:
            continue
        per_route_nodes[route_key] = []
        for node in old_route:
            name = data.nodes_to_names[node]
            per_route_nodes[route_key].append(node_data.df_gps_verbose[node_data.df_gps_verbose['name'] == name].values[0])

        route_df = pd.DataFrame(per_route_nodes[route_key])
        route_df.columns = node_data.df_gps_verbose.columns
        
        step_size_factor = 1.0
        if f'long_snapped_{profiles[route_key]}' in route_df.columns:
            route_df['long_snapped'] = route_df[f'long_snapped_{profiles[route_key]}']
            route_df['lat_snapped'] = route_df[f'lat_snapped_{profiles[route_key]}']
            step_size_factor = 0.5
        else:
            logging.warning('Failed to find snapped coordinates while reordering trip sequence.')
            
        segments = routes_all[route_key]['geometry']['coordinates']    
        segments = interpolate_segment(segments, step_size_factor)
        
        segment_to_node = dict()
        forbidden = set()
        reordered_nodes = []
        for segment in segments:
            rows = find_near_point(segment, route_df, forbidden, step_size_factor)
            for row in rows:
                reordered_nodes.append(row)

        new_route_df = pd.DataFrame(reordered_nodes)
        new_route_df.columns = route_df.columns
        ordered_nodes[route_key] = new_route_df        
    
    
    new_routes_for_assignment = [[] for vehicle in range(len(original_routes))]
    for key in ordered_nodes:
        new_route = ordered_nodes[key]
        route_names = new_route['name'].values

        full_names = node_data.df_gps_verbose.iloc[data._boolean_selected]['name'].values
        node_indices = []
        for route_name in route_names:
            node_indices.append(np.where(full_names == route_name)[0][0])
        new_routes_for_assignment[key] = node_indices
    
    for index in range(len(new_routes_for_assignment)):
        if len(new_routes_for_assignment[index]) == len(original_routes[index]): # Check to see if nodes are missed
            continue
        else:
            new_routes_for_assignment[index] = original_routes[index]
    
    if unload_routes is not None:
        reconstructed_routes = []
        keys = unload_routes['routes_to_vehicles']
        starts = unload_routes['starts']
        for key in set(keys):
            reconstructed_routes.append([])
            
        for key, subroute in zip(keys, new_routes_for_assignment):
            reconstructed_routes[key].append(subroute)
            
        for key in set(keys):
            start_points = starts[key][1:] #skip the true start point
            total_subroute = reconstructed_routes[key][0] # grabs the first one since there needs to be one
            for start_point, subroute in zip(start_points, reconstructed_routes[key][1:]):
                total_subroute += [start_point]+subroute
            reconstructed_routes[key] = total_subroute
        new_routes_for_assignment = reconstructed_routes
        
    return routing.ReadAssignmentFromRoutes(new_routes_for_assignment, ignore_inactive_indices=True)

def produce_temporary_routes(routes, vehicle_profiles, data, unload_routes = None):    
    routes_all = []
    
    routes_all = dict()
    
    if unload_routes is not None:
        routes = unload_routes['fake_routes']
        vehicle_indices = unload_routes['routes_to_vehicles']
        profiles = [vehicle_profiles[index] for index in vehicle_indices]
        start_points = []
        for values in unload_routes['starts'].values():
            start_points.extend(values)
        
        end_points = []
        for values in unload_routes['ends'].values():
            end_points.extend(values)
        
    else:
        profiles = vehicle_profiles
        start_points = data.all_start_points
        end_points = data.all_end_points
    
    for index, route in enumerate(routes):
        vehicle_profile = profiles[index]
        start_point = start_points[index]
        end_point = end_points[index]
        
        if len(route) > 0:
            osrmbindings.initialize(f"/{vehicle_profile}/{osrm_filepath}")
            
            route = [start_point]+route+[end_point]
            
            latitudes = []
            longitudes = []
            for route_node in route:
                latitudes.append(data._locations[route_node][0])
                longitudes.append(data._locations[route_node][1])
            
            response = osrmbindings.route(longitudes, latitudes)

            parsed = ujson.loads(response)
            routes_all[index] = parsed['routes'][0]
        else:
            routes_all[index] = []
    
    return routes_all

def produce_agglomerations_naive(node_data_filtered, starts_ends, current_profile, capacity = 81):
    '''Takes a node data object and returns another one with super nodes, not recommended.
    Generally inferior to the sprawling method.
    Works with unload nodes.
    Does not work with (yet) individually specified time windows.'''
    #profiles = node_data_filtered.veh_time_osrmmatrix_dict.keys() #TODO require a refactor to have two vehicle types in the same zone, then we can loop over the profiles
    profile = current_profile
    
    profile_matrix = node_data_filtered.get_time_or_dist_mat(profile)
    buckets = node_data_filtered.get_attr('buckets')
    names = node_data_filtered.get_attr('name')

    supernodes = []
    chosen = set()
    new_buckets = []
    starts_ends_indices = []

    for index, node in enumerate(names):
        if node in starts_ends:
            starts_ends_indices.append(index)
            chosen.add(index)
            continue
        if 'UNLOAD' in node.upper():
            supernodes.append([index])
            new_buckets.append(buckets[index])
            chosen.add(index)
            continue

    for index, node in enumerate(names):            
        current_seed = profile_matrix[index]
        members = np.where(current_seed < agg_threshold_radius)[0]
        members = set(members)
        remaining = list(members.difference(chosen))

        demand_sum = buckets[remaining].sum()

        if len(remaining) == 0:
            continue
        for member in remaining:
            chosen.add(member)
        supernodes.append(remaining)
        new_buckets.append(demand_sum)

    fictional_points = [supernode[0] for supernode in supernodes]
    fictional_points += starts_ends_indices
    
    new_distances = profile_matrix[fictional_points,:][:,fictional_points]
    new_buckets += [np.nan for _ in starts_ends_indices]

    node_data_filtered.veh_time_osrmmatrix_dict[profile].time_dist_mat = new_distances
    node_data_filtered.df_gps_verbose = node_data_filtered.df_gps_verbose.iloc[fictional_points]
    node_data_filtered.df_gps_verbose['buckets'] = new_buckets

    return node_data_filtered, supernodes, fictional_points

def produce_agglomerations_sprawling(node_data_filtered, starts_ends, current_profile, capacity = 81):
    '''Takes a node data object and returns another one with super nodes.
    Recommended for most use cases.
    Works with unload nodes.
    Works with individually specified time windows.'''
    #profiles = node_data_filtered.veh_time_osrmmatrix_dict.keys() #TODO require a refactor to have two vehicle types in the same zone, then we can loop over the profiles
    profile = current_profile
    
    profile_matrix = node_data_filtered.get_time_or_dist_mat(profile)
    buckets = node_data_filtered.get_attr('buckets')
    names = node_data_filtered.get_attr('name')
    time_windows = node_data_filtered.get_attr('time_windows')

    supernodes = []
    chosen = set()
    new_buckets = []
    new_time_windows = []
    starts_ends_indices = []
    
    #Safety loop for special nodes
    for index, node in enumerate(names):
        if node in starts_ends:
            starts_ends_indices.append(index)
            chosen.add(index)
            continue
        if 'UNLOAD' in node.upper():
            supernodes.append([index])
            new_buckets.append(buckets[index])
            new_time_windows.append(time_windows[index])
            chosen.add(index)
            continue
    
    for index, node in enumerate(names):        
        if index in chosen:
            continue
        
        current_seed = profile_matrix[index]
        to_check = np.where(current_seed < agg_threshold_radius)[0]
        to_check = list(to_check)
        members = set([index])
        chosen.add(index)
        current_time_window = time_windows[index]

        while len(to_check) > 0:
            checking = to_check.pop(0)
            
            if isinstance(current_time_window, str):
                if not isinstance(time_windows[checking], str):
                    continue

            if isinstance(time_windows[checking], str): #disregard further comment if loop above manages that situation # extra note: if current_time_window is string and checking is nan, checking will become time-windowed
                if isinstance(current_time_window, str):
                    if time_windows[checking] != current_time_window:
                        continue
                else:
                    continue
            

            current_sum = buckets[list(members)+[checking]].sum()
            if current_sum > capacity:
                logging.info('Breaking large clusters, consider decreasing agg_threshold_radius')
                break
            
            if checking in chosen:
                continue
            
            members.add(checking)
            chosen.add(checking)
            
            maybe_check = set(np.where(profile_matrix[checking] < agg_threshold_radius)[0])
            new_checks = maybe_check.difference(chosen)
            to_check.extend(list(new_checks))            
            
        members = list(members)
        
        demand_sum = buckets[members].sum()

        if len(members) == 0:
            continue
        
        supernodes.append(members)
        new_buckets.append(demand_sum)
        new_time_windows.append(current_time_window)

    fictional_points = [supernode[0] for supernode in supernodes]
    fictional_points += starts_ends_indices
    
    if verbose:
        logging.info("Sprawling node agglomeration results", len(supernodes), len(names), sum([len(supernode) for supernode in supernodes]), [len(supernode) for supernode in supernodes])
    
    new_distances = profile_matrix[fictional_points,:][:,fictional_points]
    new_buckets += [np.nan for _ in starts_ends_indices]
    new_time_windows += [np.nan for _ in starts_ends_indices]

    node_data_filtered.veh_time_osrmmatrix_dict[profile].time_dist_mat = new_distances
    node_data_filtered.df_gps_verbose = node_data_filtered.df_gps_verbose.iloc[fictional_points]
    node_data_filtered.df_gps_verbose['buckets'] = new_buckets
    node_data_filtered.df_gps_verbose['time_windows'] = new_time_windows

    return node_data_filtered, supernodes, fictional_points

produce_agglomerations = produce_agglomerations_naive
if agglomeration_sprawling:
    produce_agglomerations = produce_agglomerations_sprawling

def get_full_routes(current_routes, supernodes, fictional_points):
    new_routes = []
    for current_route in current_routes:
        new_route = []
        for node_index in current_route:
            supernode = supernodes[node_index]
            new_route.extend(supernode)
        new_routes.append(new_route)
    return new_routes        

def deconstruct_routes(current_routes, node_data_filtered, data):
    names = node_data_filtered.get_attr('name')
    all_subroutes = dict()
    starts_per_vehicle = dict()
    for vehicle_index, current_route in enumerate(current_routes):
        subroutes = []
        all_subroutes[vehicle_index] = subroutes
        starts_per_vehicle[vehicle_index] = []
        subroutes.append([])
        for node in current_route:
            if 'UNLOAD' in names[node].upper():
                subroutes.append([])
                starts_per_vehicle[vehicle_index].append(node)
            else:
                subroutes[-1].append(node)

    for vehicle in starts_per_vehicle:
        starts_per_vehicle[vehicle].insert(0, data.all_start_points[vehicle])
        starts_per_vehicle[vehicle].append(data.all_end_points[vehicle])

    fake_routes = []
    routes_to_vehicles = []
    for vehicle in all_subroutes:
        subroutes = all_subroutes[vehicle]
        for subroute in subroutes:
            routes_to_vehicles.append(vehicle)
            fake_routes.append(subroute)

    starts = dict()
    ends = dict()
    for vehicle in starts_per_vehicle:
        starts[vehicle] = []
        ends[vehicle] = []
        points = starts_per_vehicle[vehicle]
        for index in range(len(points)-1):
            start = points[index]
            end = points[index+1]
            starts[vehicle].append(start)
            ends[vehicle].append(end)

    unload_routes = {'fake_routes': fake_routes, 'routes_to_vehicles': routes_to_vehicles, 'starts': starts, 'ends': ends}
    return unload_routes

def solve(node_data, config: str) -> IntermediateOptimizationSolution:
    """Solve the route for each zone.

    Args:
        config: json route config.
    """
    zone_configs = config.get('zone_configs')
    global_solver_options = config.get('global_solver_options')
    prev_route_dict = None
    prev_vehicles = None
    prev_keys = set([])
    zone_route_map = {}
    #for each zone configuration
    for this_config in zone_configs:
        solver_options = {**this_config.get('solver_options', {}), **global_solver_options}
        if this_config.get('enable_unload'):
            all_start_end_options = []
            for v in this_config['unload_vehicles']:
                all_start_end_options.extend(v[2:])
            all_start_end_options =  set(all_start_end_options)
            all_start_end_options_dict = {f'unload_{idx}': v for idx, v in enumerate(set(all_start_end_options))}
            all_start_end_options_dict['zone'] = this_config['optimized_region']
            node_data_filtered = node_data.filter_nodedata(all_start_end_options_dict, filter_name_str='multiple_sample')
            starts_ends = all_start_end_options

        else:
            #filter for desired zone and depot node
            node_data_filtered = node_data.filter_nodedata(
                {'zone': this_config['optimized_region'],
                 'start': this_config['Start_Point']
                    ,'end': this_config['End_Point']
                 }, filter_name_str='multiple_sample')

            starts_ends = [this_config['Start_Point'][0], this_config['End_Point'][0]]

        supernodes = []
        if clustering_agglomeration:
            original_node_data_filtered = copy.deepcopy(node_data_filtered)
            first_vehicle_profile = this_config['trips_vehicle_profile'][0][0]
            cluster_capacity = this_config['trips_vehicle_profile'][0][1]
            if this_config['enable_unload']:
                first_vehicle_profile = this_config['unload_vehicles'][0][0]
                cluster_capacity = this_config['unload_vehicles'][0][1]

            node_data_filtered, supernodes, fictional_points = produce_agglomerations(node_data_filtered, starts_ends, current_profile=first_vehicle_profile, capacity=cluster_capacity)

        #create vehicles and data problem
        vehicles = create_vehicle(node_data_filtered,this_config)
        data = DataProblem(node_data_filtered,vehicles,this_config, node_clusters = supernodes)

        if (sum(data.demands) > sum([v.capacity for v in vehicles])) and not this_config['enable_unload']:
            logging.warning('number of vehicles specified is not enough', sum(data.demands), sum([v.capacity for v in vehicles]))
            continue

        #run optimal route script
        assignment, manager, routing =  get_optimal_route(data,vehicles, **solver_options)

        #printer = ConsolePrinter(data, routing, assignment, manager)
        #printer.print()
        #return routing, assignment, manager, data

        if clustering_agglomeration:
            current_routes = get_routes(routing, data, assignment, manager)
            full_routes = get_full_routes(current_routes, supernodes, fictional_points)

            node_data_filtered = original_node_data_filtered
            vehicles = create_vehicle(node_data_filtered,this_config)
            data = DataProblem(node_data_filtered, vehicles, this_config)
            assignment, manager, routing =  get_optimal_route(data, vehicles, warmed_up = full_routes, **solver_options)
            if assignment is None:
                logging.warning("Clustered version did not work, running without it")
                assignment, manager, routing =  get_optimal_route(data, vehicles, **solver_options)

        if resequencing:
            resequence_time = time.clock()
            current_routes = get_routes(routing, data, assignment, manager)
            if this_config['enable_unload']:
                unload_routes = deconstruct_routes(current_routes, node_data_filtered, data)
                routes_all = produce_temporary_routes(current_routes, [vehicle._osrm_profile for vehicle in vehicles], data, unload_routes = unload_routes)
                new_assignment = resequence(node_data_filtered, data, routing, routes_all, current_routes, [vehicle._osrm_profile for vehicle in vehicles], unload_routes = unload_routes)

            else:
                routes_all = produce_temporary_routes(current_routes, [vehicle._osrm_profile for vehicle in vehicles], data)
                new_assignment = resequence(node_data_filtered, data, routing, routes_all, current_routes, [vehicle._osrm_profile for vehicle in vehicles])
            if new_assignment is not None:
                assignment = new_assignment
            logging.info(f'Took {time.clock() - resequence_time} seconds to resequence')

        printer = ConsolePrinter(data, routing, assignment, manager)
        printer.print()

        #Reorganize output into a route_dict, also filter out unused routes and combine w/ prev. configs
        route_dict, vehicles = create_route_dict(assignment, manager, routing, data, node_data_filtered, vehicles, prev_route_dict, prev_vehicles)
        prev_route_dict = route_dict
        prev_vehicles = vehicles

        #put together a dict of zone(s) name -> routes for per-zone maps
        curr_keys = set(route_dict.keys())
        this_zone_keys = curr_keys - prev_keys
        prev_keys = curr_keys
        zone_name = ''
        for region in this_config['optimized_region']:
            zone_name += region
        zone_name = zone_name.replace(" ", "")
        zone_route_map[zone_name] = sorted(this_zone_keys)

    return IntermediateOptimizationSolution(
        node_data=node_data,
        route_dict=route_dict,
        vehicles=vehicles,
        zone_route_map=zone_route_map
    )

def add_display_name(route_dict):
    '''Adds a field to be used in the manual edits documents, solution.txt, and maps produced in
    order to be more flexible in how we display routes as opposed to using their IDs.'''
    new_route_dict = copy.deepcopy(route_dict)

    for key in new_route_dict:
        new_route_dict[key]['display_name'] = f'{colorList[key % len(colorList)]}-{key+1}'
    
    return new_route_dict

def reorder_route_dict(route_dict):
    '''Tries to keep a reliable ordering, from North to South given the average gps 
    locations of the nodes on the route.
    Not used yet'''
    print(route_dict)
    return route_dict


def finalize_route_solution(solution: IntermediateOptimizationSolution, config) -> FinalOptimizationSolution:
    node_data = solution.node_data

    if north_south_ordering:
        averages = {}
        
        for key in solution.route_dict:
            route_coords = solution.route_dict[key]['route']
            average_point = np.zeros(shape=(2,))
            for point, _ in route_coords:
                average_point += point
            average_point /= len(route_coords)
            averages[key] = average_point[0]
        averages = pd.Series(averages).sort_values(ascending=False)

        reordered_routes = {}
        reordered_vehicles = {}
        reordered_map = {}
        for new_index, old_index in enumerate(averages.index):
            reordered_routes[new_index] = solution.route_dict[old_index]
            reordered_vehicles[new_index] = solution.vehicles[old_index]
            reordered_map[old_index] = new_index

        for key in solution.zone_route_map:
            solution.zone_route_map[key] = [reordered_map[index] for index in solution.zone_route_map[key]]

        solution_route_dict = reordered_routes
        solution_vehicles = reordered_vehicles
    else:
        solution_route_dict = solution.route_dict
        solution_vehicles = solution.vehicles

    solution_route_dict = add_display_name(solution_route_dict)
    solution.route_dict = solution_route_dict
    
    routes_for_mapping = {}
    route_dict = solution_route_dict
    vehicles = solution_vehicles
    for vehicle_id in route_dict:
        current_route = []
        for i, item in enumerate(route_dict[vehicle_id]["route"]):
            cust_popup = [node_data.get_names_by_index(route_dict[vehicle_id]["indexed_route"][i]),
            node_data.get_attr_by_index('additional_info',route_dict[vehicle_id]["indexed_route"][i])]
            current_route.append((item[0], cust_popup, route_dict[vehicle_id]['loads'][i], route_dict[vehicle_id]['demands'][i]))
        
        routes_for_mapping[vehicle_id] = current_route
    
    display_dict = {str(key+1) : route_dict[key]['display_name'] for key in route_dict}

    # Index up everything for visualizaiton purposes 
    def index_up_dict(my_dict):
        return {str(k+1): my_dict[k] for k in my_dict}

    routes_for_mapping = index_up_dict(routes_for_mapping)
    vehicles = index_up_dict(vehicles)
    for k in solution.zone_route_map:
        solution.zone_route_map[str(k)] = [str(i+1) for i in solution.zone_route_map[k]]
        
    if config is not None:
        ### First - check if we have any unload routes - as we want to segment them so they are easy to inspect
        def segment_unload_route(route):
            all_routes = []
            sub_route = []
            for elem in route:
                if 'unload' in elem[1][0].lower():
                    sub_route.append(elem)
                    all_routes.append(sub_route)
                    sub_route = [elem]
                else:
                    sub_route.append(elem)
            all_routes.append(sub_route)
            return all_routes

        for zone in config['zone_configs']:
            ref_zone_route_map = copy.deepcopy(solution.zone_route_map)
            zone_routes = []


            if zone['enable_unload']:
                zone_to_segment = ''.join([''.join(i.split(' ')) for i in zone['optimized_region']])
                routes_to_segment = ref_zone_route_map[zone_to_segment] 
                for zone_route in routes_to_segment:
                    letter_options = list(string.ascii_uppercase)+list(string.ascii_lowercase)
                    original_vehicle = vehicles[zone_route]
                    tmp_routes = segment_unload_route(routes_for_mapping[zone_route])
                    for idx, route in enumerate(tmp_routes):
                        new_label = f'{zone_route}-{letter_options[idx]}'
                        routes_for_mapping[new_label] = route     
                        vehicles[new_label] = original_vehicle
                        zone_routes.append(new_label)
                    del routes_for_mapping[zone_route]
                    del vehicles[zone_route]
                    solution.zone_route_map[zone_to_segment] = zone_routes

    if color_naming:
        new_routes_for_mapping = {}
        new_vehicles = {}
        for key in routes_for_mapping:
            if '-' in key:
                number_key = key.split('-')[0]
                second_part = key.split('-')[1]
            else:
                number_key = key
                second_part = ''
            
            new_key = display_dict[number_key]
            if second_part != '':
                new_key = f'{new_key}-{second_part}'

            new_routes_for_mapping[new_key] = routes_for_mapping[key]
            new_vehicles[new_key] = vehicles[key]
        
        routes_for_mapping = new_routes_for_mapping
        vehicles = new_vehicles

        for key in solution.zone_route_map:
            new_routes = []
            for route in solution.zone_route_map[key]:
                if '-' in route:
                    number_key = route.split('-')[0]
                    second_part = route.split('-')[1]
                else:
                    number_key = route
                    second_part = ''
                
                new_key = display_dict[number_key]
                if second_part != '':
                    new_key = f'{new_key}-{second_part}'
                
                new_routes.append(new_key)
            solution.zone_route_map[key] = new_routes
                

    #Create output for manual route editing option
    #manual_viz.write_manual_output(node_data, routes_for_mapping, vehicles, solution.zone_route_map)
    return FinalOptimizationSolution(
        intermediate_optimization_solution=solution,
        routes_for_mapping=routes_for_mapping,
        vehicles=vehicles,
        zone_route_map=solution.zone_route_map
    )

def run_optimization(node_data, config):
    """Main entrypoint for optimization"""
    starting_time = time.time()

    # Solve the routing problem.
    solution = solve(node_data, config)

    # Finalize the optimization solution.
    final_optimization = finalize_route_solution(
        solution=solution,
        config=config
    )

    # Logging
    all_zones = [i['optimized_region'] for i in config['zone_configs']]
    run_duration = strftime("%Mmin %Ssec", gmtime(time.time()-starting_time))
    logging.info(f'Optmization Complete: Took {run_duration} to optimize {all_zones}')


    return final_optimization