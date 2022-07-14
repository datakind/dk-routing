"""
Allows for manual editing of routes and subsequent mapping.
"""
import visualization
import optimization
from build_time_dist_matrix import NodeLoader
from config.config_manager import ConfigManager
from output.file_manager import FileManager
from output.route_solution_data import FinalOptimizationSolution, IntermediateOptimizationSolution
from output.manual_route_data import ManualRouteData

def create_route_metrics_dict(solution: FinalOptimizationSolution) -> dict:
    """
    Creates a route_dict object (as in optimization.py) from manual editing files.
    """
    routes_for_mapping = solution.routes_for_mapping
    vehicles = solution.vehicles
    node_data = solution.intermediate_optimization_solution.node_data

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

def run_manual_route_update(config_manager: ConfigManager) -> ManualRouteData:
    """
    Reads manual editing excel/csv files and recreates appropriate inputs to visualization.main()
    """
    # Ensure input data exists.
    config_manager.get_manual_edits_input_data().require()

    from optimization import Vehicle
    #Read the manual editing routes file
    manual_routes = config_manager.get_manual_edits_input_data().manual_routes
    
    #Reconstruct the nodedata class from file provided
    node_data = NodeLoader.from_clean_gps_node_data(
        config_manager, config_manager.get_manual_edits_input_data().clean_gps_node_data
    )
    #for each sheet (zone) in routes file
    routes_for_mapping = {}
    zone_route_map = {}
    df_gps_route_dict = {}
    for sheet in manual_routes.sheet_names:
        #Add the zone to the zone-to-route tracking map
        zone_route_map[sheet] = []
        #iterate through the df to create routes_for_mapping
        manual_dataframe = manual_routes.parse(sheet)
        manual_dataframe = manual_dataframe[manual_dataframe['route'] != 'Summary']
        for index, row in manual_dataframe.iterrows():
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
    manual_vehicles_df = config_manager.get_manual_edits_input_data().manual_vehicles
    #Remake the vehicles list
    vehicles = {}
    for row in manual_vehicles_df.itertuples():
        vehicles[str(row.veh_id)] = Vehicle(name=row.name, osrm_profile=row.profile)
    
    # We aren't going to re-run optimization, but instead construct
    # the solutions object from the loaded data.
    solution = FinalOptimizationSolution(
        intermediate_optimization_solution=IntermediateOptimizationSolution(
          node_data=node_data,
          route_dict=None,
          vehicles=vehicles,
          zone_route_map=zone_route_map
        ),
        routes_for_mapping=routes_for_mapping,
        vehicles=vehicles,
        zone_route_map=zone_route_map
    )

    # Re-run the visualizations
    vis_data = visualization.create_visualizations(solution, manual_editing_mode=True)

    return ManualRouteData(
        metrics_dict=create_route_metrics_dict(solution),
        modified_optimization_solution=solution,
        modified_visualizations=vis_data
    )


    
    
