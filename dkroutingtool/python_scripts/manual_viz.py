"""
Allows for manual editing of routes and subsequent mapping.
"""
import pandas as pd
from file_config import SolutionOutput, ManualEditRouteOutput, ManualEditVehicleOutput, ManualSolutionOutput, ManualGPSOutput
import visualization
import optimization
from build_time_dist_matrix import NodeLoader

def write_manual_output(node_data, routes_for_mapping, vehicles, zone_route_map):
    """
    Writes the objects from the output form optimization.py to excel/csv files to be edited.
    """
    
    #Create output for manual route editing option
    zone_dfs = {}
    #for each zone, construct lists of attributes of the nodes in order
    for zone_name, route_indices in zone_route_map.items():
        node_name = []
        route_num = []
        node_num = []
        loads = []
        demands = []
        additional_info = []
        node_i = 1
        #for each route in that zone
        for route_id in sorted(route_indices):
            route = routes_for_mapping[route_id]
            #for each node in that route
            for route_i, node in enumerate(route):
                node_name.append(node[1][0])
                route_num.append(route_id)
                loads.append(node[2])
                demands.append(node[3])
                additional_info.append(node[1][1])
                #if first or last node, number (marker number) the node "Depot"
                if route_i==0 or route_i==len(route)-1:
                    node_num.append('Depot')
                #else give itthe next marker number
                else:
                    node_num.append(node_i)
                    node_i += 1
        #make a df for the zone
        zone_df = pd.DataFrame({'route': route_num, 'node_num':node_num, 
                    'node_name': node_name, 'load': loads, 'demands': demands,
                    'additional_info': additional_info})
        
        # Start Route Nums at 1 (not zero for external display)
        zone_df['route'] = zone_df['route']
        zone_dfs[zone_name] = zone_df
    
    #write the zone dataframes to a xlsx file with different sheets 
    with pd.ExcelWriter(ManualEditRouteOutput().get_filename(), engine='openpyxl') as writer:
        for zone_key, zone_df in zone_dfs.items():
            zone_df.to_excel(writer, sheet_name=zone_key, index=False)
            
    #Create a seperate csv file for the route id -> vehicle attrributes
    veh_manual = {}
    veh_id = []
    veh_names = []
    veh_profiles = []
    for k, veh in vehicles.items():
        veh_id.append(k)
        veh_names.append(veh.name)
        veh_profiles.append(veh.osrm_profile)
    veh_manual['veh_id'] = veh_id
    veh_manual['name'] = veh_names
    veh_manual['profile'] = veh_profiles
    pd.DataFrame(veh_manual).to_csv(ManualEditVehicleOutput().get_filename(), index=False)
    
    
    gps_output_config = ManualGPSOutput()
    node_data.write_nodes_to_file(gps_output_config.get_clean_filename(), verbose=True )	
    
def create_route_metrics_dict(routes_for_mapping, vehicles, node_data):
    """
    Creates a route_dict object (as in optimization.py) from manual editing files.
    """
    
    #Initialize the route_dict
    route_metrics_dict = {}
    
    #for each route
    for route_id, route in routes_for_mapping.items():
        this_veh = vehicles[route_id]

        node_names = []
        for node in route:
            node_names.append(node[1][0])
        data = optimization.DataProblem(node_data, [this_veh], node_name_ordered = node_names)
        #Find the time matrix (as done in optimizaiton.py)
        time_matrix = optimization.CreateTimeEvaluator(data, manual_run = True)
        
        route_dist = 0
        total_time = 0
        route_load = 0
        #for each node, add the time, distance and laod
        #for i, node_name in enumerate(route[:][1][0]):
        for i in range(len(node_names)-1):
            #if i < len(route[:][1][0])-1:
            total_time += time_matrix.time_evaluator(i, i+1)
            route_dist += data.distance_matrix[i][i+1]
            route_load += data.demands[i+1]
        
        #If key not in dict, add it
        if route_id not in route_metrics_dict.keys():
            route_metrics_dict[route_id] = {}
        
        route_metrics_dict[route_id]['total_time'] = total_time
        route_metrics_dict[route_id]['total_dist'] = route_dist
        route_metrics_dict[route_id]['load'] = route_load
        
    return route_metrics_dict
    
    

def print_metrics_to_file_manual(routes_for_mapping, vehicles, node_data):
    """
    Prints solution (time, load, dist) to file.
    """

    #find the metrics
    route_metrics_dict = create_route_metrics_dict(routes_for_mapping, vehicles, node_data)

    plan_output = ''
    for route_id, route in routes_for_mapping.items():
        plan_output += 'Route ID {0}'.format(route_id)
        if vehicles != None:
            plan_output += ', ' + vehicles[route_id].name + ':\n'
        else:
            plan_output += ':\n'

        for i, rfm_entry in enumerate(route):
            plan_output += ' {0} '.format(rfm_entry[1][0])
            if i < len(route)-1:
                plan_output += '->'
        plan_output += '\n'
        plan_output += 'Distance of the route: {0}km\n'.format(int(route_metrics_dict[route_id]["total_dist"])/1000)
        plan_output += 'Load of the route: {0}\n'.format(int(route_metrics_dict[route_id]["load"]))
        plan_output += 'Time of the route: {0}min\n\n'.format(int(route_metrics_dict[route_id]["total_time"]/60))

    plan_output += "Total: \n"
    #Total the dist and time
    total_dist = 0
    total_time = 0
    for i in route_metrics_dict.keys():
        total_dist += route_metrics_dict[i]["total_dist"]
        total_time += route_metrics_dict[i]["total_time"]/60
    plan_output += "Distance of all routes: {0}km\n".format(int(total_dist)/1000)
    plan_output += 'Time of all routes: {0}min\n\n'.format(int(total_time))

    text_file = open(ManualSolutionOutput().get_filename(), "w")
    text_file.write(plan_output)
    text_file.close()


def main():
    """
    Reads manual editing excel/csv files and recreates appropriate inputs to visualization.main()
    """
    from optimization import Vehicle
    #Read the manual editing routes file
    manual_routes = pd.ExcelFile(ManualEditRouteOutput().get_filename())
    
    #Reconstruct the nodedata class from file provided
    node_data = NodeLoader(load_clean_filepath=ManualGPSOutput().get_clean_filename()).get_nodedata()
    #for each sheet (zone) in routes file
    routes_for_mapping = {}
    zone_route_map = {}
    df_gps_route_dict = {}
    for sheet in manual_routes.sheet_names:
        #Add the zone to the zone-to-route tracking map
        zone_route_map[sheet] = []
        #iterate through the df to create routes_for_mapping
        for index, row in manual_routes.parse(sheet).iterrows():
            row_key = str(row['route'])
            #if route doesn't exist in routes_for_mapping, add it
            if row_key not in routes_for_mapping.keys():
                routes_for_mapping[row_key] = []
                zone_route_map[sheet].append(row_key)
                
            #Reconstruct the array as it was before manual editing
            #pick the lat/long and additional info from the node data file
            this_entry_nodedata = node_data.filter_nodedata({'name': row['node_name']})
            rfm_entry = [(this_entry_nodedata.lat_long_coords[0][0], this_entry_nodedata.lat_long_coords[0][1])]
            rfm_entry.append((row['node_name'], this_entry_nodedata.get_attr('additional_info')[0]))
            
            #Add the node to the appropriate route
            routes_for_mapping[row_key].append(rfm_entry)
            
    #read in the vehicles
    manual_vehicles_df = pd.read_csv(ManualEditVehicleOutput().get_filename())
    #Remake the vehicles list
    vehicles = {}
    for row in manual_vehicles_df.itertuples():
        vehicles[str(row.veh_id)] = Vehicle(name=row.name, osrm_profile=row.profile)
    
    #Create the maps for the manual solution
    visualization.main(routes_for_mapping, vehicles, zone_route_map, manual_editing_mode=True)
    
    #Print the new solution to file with estimated distances/times, etc
    print_metrics_to_file_manual(routes_for_mapping, vehicles, node_data)
    
    
