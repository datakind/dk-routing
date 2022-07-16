from turtle import fillcolor
import folium
import io
from folium.plugins import BeautifyIcon
import pandas as pd
import numpy as np
from output.route_solution_data import FinalOptimizationSolution
from output.visualization_data import FoliumMapOutput, VisualizationData
from geojson import Feature, MultiLineString, FeatureCollection
import ujson

import osrmbindings

import osrm_text_instructions
import os

colorList = sorted(["red","blue","green","orange","purple","yellow","black","pink"])

osrm_filepath = os.environ['osm_filename']
def folium_map(routes, nodes, manual_editing_mode,
               nodes_for_mapping=None, route_names=None,
               filenamePreString=None, filenamePostString=None,
               focal_points = 'first_all') -> FoliumMapOutput:
    """Plots vehicles routes on HTML map
    
    Args:
        routes: list of  routes where each route is
                a list of x,y coordinate tuples in route order
        nodes: list of list of nodes where each list of nodes is
                a list of lat/long coordinates for each stop and
                each list of lists is associated with a list from
                the routes variable
        nodes_for_mapping (default None): list of customer
                lat/long coordinates to be mapped on separate layer
        filenamePostString (str, default None): additional string
                for html map naming
        route_names (list of names of routes/segments, default None):
                
        focal_points (either "first_all" or "first_last_only",
                default "first_all"): if "first all", all first
                and last points in a route/segment are a focal point,
                if "first_last_only", only first point of first segment
                and last point of last segment are focal points
        
    Returns:
        FoliumMapOutput containing html files
    
    """
    
    bottom_left_lat = 999
    bottom_left_long = 999
    
    top_right_lat = -999
    top_right_long = -999
    
    for node in routes.values():
        ys, xs = zip(*node)
        if min(xs) < bottom_left_long:
            bottom_left_long = min(xs)
        if min(ys) < bottom_left_lat:
            bottom_left_lat = min(ys)
        if max(xs) > top_right_long:
            top_right_long = max(xs)
        if max(ys) > top_right_lat:
            top_right_lat = max(ys)
    
    # Make an empty map
    f_map = folium.Map(location=[0, 0], tiles="OpenStreetMap", zoom_start=12, max_zoom=24)
    
    f_map.fit_bounds([[bottom_left_lat, bottom_left_long], [top_right_lat, top_right_long]])

    #add nodes to node_feature
    #include route number for node
    if nodes_for_mapping != None:
        node_feature = folium.FeatureGroup(name="Customer Locations", show=False)
        for pair in nodes_for_mapping:
            folium.Marker([pair[0][0], pair[0][1]], popup="Route {}".format(pair[1])).add_to(node_feature)
        #add node_feature to map
        node_feature.add_to(f_map)
    
    # PolyLine accepts a list of (x,y) tuples, where the ith and (ith+1) coordinate
    # are connected by a line segment on the map
    
    #create a map of vehicle id -> actual vehicle
    color_map = {}
    new_route_names = []
    if route_names != None:
        j = 0
        for route_id, route_name in route_names.items():
            new_route_names.append("Trip {}, {}/{}".format(route_id, route_name, nodes[route_id][0][2][0]))
            color_map[j] = route_id.split('-')[0]
            #color_map[j] = colorList[j % len(colorList)]
            j += 1
    else:
        for i in range(len(routes)):
            color_map[i] = colorList[i % len(colorList)]
            new_route_names.append("Segment {}".format(i+1))
    cust_index = 1

    if not filenamePostString:
        nodes_keys = custom_sort(list(nodes.keys()))
        master_layer = folium.FeatureGroup(name = 'All Customer Trips')
        for idx, key in enumerate(nodes_keys):
            ic = folium.plugins.BeautifyIcon(border_color=color_map[idx], text_color='black', number=idx,
                                             icon_shape='marker')
            folium.PolyLine(routes[key], color=color_map[idx], opacity=0.6, weight=5).add_to(master_layer)
            
            # If the first and last point in each segment/route is a focal point
            if focal_points == 'first_all':
                for customer in nodes[nodes_keys[idx]][1:-1]:
                    create_fol_cust_markers(color_map[idx], cust_index, (customer[0], customer[1]),
                                            customer[2]).add_to(master_layer)
                    cust_index += 1

        master_layer.add_to(f_map)  # master overlay containing all routes


    cust_index = 1 # reset cust_index
    route_keys = custom_sort(routes.keys())
    for idx, key in enumerate(route_keys):
        ic = folium.plugins.BeautifyIcon(border_color=color_map[idx], text_color='black',number=idx, icon_shape='marker')
            
        #feature group will contain 1 route + associated customers
        if filenamePostString:  # for use in master map turned off by default
            feature_group = folium.FeatureGroup(name = new_route_names[idx], show=True)
        else:  # in individual maps turned on by default
            feature_group = folium.FeatureGroup(name = new_route_names[idx], show= False)

        folium.PolyLine(routes[key], color='black', opacity=0.7, weight=5.6).add_to(feature_group) #outline
        folium.PolyLine(routes[key], color=color_map[idx], opacity=1.0, weight=5).add_to(feature_group)
        #If the first and last point in each segment/route is a focal point
        if focal_points == 'first_all':
            nodes_keys = custom_sort(list(nodes.keys()))
            for customer in nodes[nodes_keys[idx]][1:-1]:
                create_fol_cust_markers(color_map[idx], cust_index, (customer[0],customer[1]), customer[2]).add_to(feature_group)
                cust_index += 1
            
            
            for fcp in [0,-1]:
                foc_circle, foc_marker = create_fol_foc_point_marker([nodes[nodes_keys[idx]][fcp][0],
                                                                      nodes[nodes_keys[idx]][fcp][1]])
                #foc_circle.add_to(feature_group)
                foc_marker.add_to(feature_group)
        
        #if only the first point in the first segment/route and the last point in the last segment/route is the focal point
        elif focal_points == 'first_last_only':
                    
            #if first segemnt/route
            if idx == 0:
                foc_circle, foc_marker = create_fol_foc_point_marker([nodes[idx][0][0], nodes[idx][0][1]])
                #foc_circle.add_to(feature_group)
                foc_marker.add_to(feature_group)
                            
                for customer in nodes[idx][1:]:
                    
                    create_fol_cust_markers(color_map[idx], cust_index, (customer[0],customer[1]), customer[2]).add_to(feature_group)
                    cust_index += 1
           
            #if last segment/route
            elif idx == len(routes)-1:
                if len(nodes[idx]) > 0:
                    foc_circle, foc_marker = create_fol_foc_point_marker([nodes[idx][-1][0], nodes[idx][-1][1]])
                    #foc_circle.add_to(feature_group)
                    foc_marker.add_to(feature_group)

                    for customer in nodes[idx][:-1]:
                        create_fol_cust_markers(color_map[idx], cust_index, (customer[0],customer[1]), customer[2]).add_to(feature_group)
                        cust_index += 1
                            
            else:
                for customer in nodes[idx]:
                    create_fol_cust_markers(color_map[idx], cust_index, (customer[0],customer[1]), customer[2]).add_to(feature_group)
                    cust_index += 1
                
        feature_group.add_to(f_map)

    #Allow feature_groups/layers to be toggled
    folium.LayerControl().add_to(f_map)

    # if manual_editing_mode:
    #     filename = ManualMapOutput(filenamePreString, filenamePostString).get_filename()
    # else:
    #     if filenamePostString:
    #         # If numeric label Index up by 1 for labeling (start at 1 not 0)
    #         if filenamePostString.isnumeric():
    #             filenamePostString = str(int(filenamePostString))
    #     filename = MapOutput(filenamePreString, filenamePostString).get_filename()

    # Add the output to the result.
    buff = io.BytesIO()
    f_map.save(buff, close_file=False)
    return FoliumMapOutput(prefix=filenamePreString,
                           suffix=filenamePostString,
                           map_html_output=buff.getvalue())

def create_fol_cust_markers(border_color, marker_text, loc, pop_up):
    ic = folium.plugins.BeautifyIcon(border_color=border_color, number=marker_text, icon_shape='marker')
    
    pop_up_html = ""
    pop_up_html += f'Trip index: {marker_text} <br>'
    for i, pop_up_entry in enumerate(pop_up):
        if isinstance(pop_up_entry, str):
            pop_up_html += pop_up_entry
            if i < len(pop_up) - 1:
                pop_up_html += '<br>'
        else:
            if not np.isnan(pop_up_entry):
                pop_up_html += str(pop_up_entry)
                if i < len(pop_up) - 1:
                    pop_up_html += '<br>'

    fol_html_popup = folium.Html(pop_up_html, script=True)
    
    return folium.Marker(location=[loc[0],loc[1]], icon=ic, popup=folium.Popup(fol_html_popup, max_width=1000))

def create_fol_foc_point_marker(loc):
    foc_circle = folium.Circle([loc[0], loc[1]], color='crimson', fill=True, radius=150)
    
    foc_marker = folium.Marker([loc[0], loc[1]],
                popup='Focal Point',
                icon=folium.Icon(icon='flag')
                )

    return foc_circle, foc_marker

def createVisObject(coordArray):

    with open('data_vis.js', 'w') as f:
        f.write("""var data = var dataset = {“type”: “FeatureCollection”, “features”:
        “id”: 0,
        “geometry”:
        """)
        for data in coordArray:
            LineStringCoords = data['routes'][0]['geometry']['coordinates']
            Node1Coords = data['waypoints'][0]['location']
            Node2Coords = data['waypoints'][1]['location']
            f.write(
                """
                {{“type”: “LineString”,
                 “coordinates”: {0} }},
                 “properties”: {{}} }},""".format(LineStringCoords)
                )
            f.write(
                """
                {{“type”: “Feature”, “id”: 1,
                “geometry”: {{“type”: “Point”, “coordinates”: {0} }},
                “properties”: {{}}}},              
                """.format(Node1Coords)
            )
            f.write(
                """
                {{“type”: “Feature”, “id”: 1,
                “geometry”: {{“type”: “Point”, “coordinates”: {0} }},
                “properties”: {{}}}},              
                """.format(Node2Coords)
            )
   
def custom_sort(to_sort):
        to_sort = list(to_sort)
        if isinstance(to_sort[0], int):
            return sorted(to_sort)
        else:
            return sorted(to_sort)
            #return sorted(to_sort, key=lambda x: (int(x.split('-')[0]), x.split('-')[1]) if '-' in x else (int(x), 0))

def get_route_geojson(mapping_routes):
    full_collection = []
    for key in mapping_routes:
        route = mapping_routes[key]
        route = list(map(lambda x: (x[1],x[0]), route))
        route = MultiLineString([route])
        route_feature = Feature(geometry=route, properties={'id':key})
        full_collection.append(route_feature)

    return FeatureCollection(full_collection)

def df_to_geojson(df, properties, lat='latitude', lon='longitude'):
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in df.iterrows():
        feature = {'type':'Feature',
                    'properties':{},
                    'geometry':{'type':'Point',
                                'coordinates':[]}}
        feature['geometry']['coordinates'] = [row[lon],row[lat]]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson

def get_nodes_geojson(nodes):
    routes=[]
    for k in nodes:
        add_key = [list(i)+[k] for i in nodes[k]]
        routes.extend(add_key)

    out_nodes = pd.DataFrame([[i[0], i[1], i[2][0], i[-1]] for i in routes], columns=['lat', 'lng', 'name', 'zone'])
    out_nodes.loc[:, 'sequence'] = out_nodes.groupby('zone').cumcount()+1
    out_nodes_geojson = df_to_geojson(out_nodes, out_nodes.columns, lat='lat', lon='lng')  
    return out_nodes_geojson

def create_visualizations(solution: FinalOptimizationSolution,
                          manual_editing_mode=False) -> VisualizationData:
    """ Create visualizations from route solution.
    This includes:
        1. HTML maps
        2. Turn-by-turn directions
        3. route geojson files

    Args:
      solution: Solution from optimization.py
    Returns:
      All visualization data as a VisualizationData object.
    """
    # Get data out of solution.
    routes_for_mapping = solution.routes_for_mapping
    vehicles = solution.vehicles
    zone_route_map = solution.zone_route_map

    # Create and save folium map as an HTML file
    osrm_routes_dict = {}
    #save route legs as well for individual maps
    routes_all = []
    routes_all_dict = {}

    total_distance = 0
    total_duration = 0

    unique_node = set()

    nodes_for_mapping = []
    route_names = {}

    nodes = {}
    for i in routes_for_mapping.keys():
        nodes[i] = []

    sorted_keys = custom_sort(routes_for_mapping.keys())
    # Responses by route id.
    responses_by_route_id = {}
    # Instructions by route id.
    instructions_by_route_id = {}

    for route_id in sorted_keys:
        route = routes_for_mapping[route_id]
        longitudes = []
        latitudes = []

        route_names[route_id] = vehicles[route_id].name

        #Select the profile for OSRM to construct routes for
        osrmbindings.initialize(f"/{vehicles[route_id].osrm_profile}/{osrm_filepath}")

        for index, location in enumerate(route): 
            longitudes.append(location[0][1])
            latitudes.append(location[0][0])
            unique_node.add(tuple(location[0]))
            nodes_for_mapping.append([tuple(location[0]), route_id])
            nodes[route_id].append(tuple((location[0][0], location[0][1], location[1])))

        response = osrmbindings.route(longitudes, latitudes)
    
        parsed = ujson.loads(response)

        responses_by_route_id[route_id] = response
        instructions_by_route_id[route_id] = osrm_text_instructions.get_instructions(parsed)

        try:
            geojson = parsed["routes"][0]["geometry"] # Ignores alternatives if some are even passed
            flip_it = geojson["coordinates"]
            flipped = list(map(lambda x: (x[1],x[0]), flip_it))

            osrm_routes_dict[route_id] = flipped
            routes_all.append(parsed['routes'][0])
            routes_all_dict[route_id] = parsed['routes'][0]

            duration = parsed["routes"][0]["duration"]/60

            distance = parsed["routes"][0]["distance"]/1000

            #print(f"Route {route_id}, duration: {round(duration,2)} minutes, distance: {round(distance,3)} kilometers")

            total_duration += duration
            total_distance += distance

        except:
            print("Exception In Creating Visualizaton")
            continue # hacky for now but let's just avoid showstoppers

    ## Map all the routes on one map ##
    maps = []
    maps.append(
        folium_map(osrm_routes_dict, nodes, manual_editing_mode, nodes_for_mapping, route_names)
    )

    ## Zone Maps ## 
    # If specified, create a map for each zone
    if zone_route_map != None:
        for zone_name, routes in zone_route_map.items():
            this_zone_nodes = {}
            this_zone_osrm_routes = {}
            this_zone_route_names = {}           
            for route in routes:
                this_zone_nodes[route] = nodes[route]
                this_zone_osrm_routes[route]=osrm_routes_dict[route]
                this_zone_route_names[route] = route_names[route]
                
            maps.append(
                folium_map(this_zone_osrm_routes, this_zone_nodes, manual_editing_mode, nodes_for_mapping=None, route_names=this_zone_route_names, filenamePostString = zone_name)
            )
    
    ## Individual Route Maps ##
    #Construct the individual route maps for each round-trip route
    for k in routes_all_dict:
        route = routes_all_dict[k]
        #Contruct a list of route "legs" (route between two nodes)
        route_legs = route['legs']
        segment_routes = [] #list of list of coordinates for each segment
        segment_nodes = []  #list of list of customer lat/long pairs associated with each segment
        this_segment = []   #list of coordinates for current segment
        this_segment_nodes = [nodes[k][0]]  #list of nodes for current segment
        
        
        for leg_i, route_leg in enumerate(route_legs):
            leg_coords = []
            
            #put together the list of coordinates for the current route leg
            for step_i, route_leg_step in enumerate(route_leg['steps']):
                for coord_i, coord in enumerate(route_leg_step['geometry']['coordinates']):
                    coord = tuple([coord[1], coord[0]])
                    #unless its the first point, skip is as it was the last point in the previous step
                    if leg_i == 0 and step_i == 0:
                        leg_coords.append(coord)
                    else:
                        if coord_i != 0:
                            leg_coords.append(coord)
                          
            #check if there is an intersection for the new route leg
            if any(elem in leg_coords for elem in this_segment):
                segment_routes.append(this_segment)
                segment_nodes.append(this_segment_nodes)
                this_segment = [this_segment[len(this_segment)-1]]
                this_segment.extend(leg_coords)
                this_segment_nodes = []
                this_segment_nodes.append(nodes[k][leg_i+1])
            #if no intersection, add to current segment and move on
            else:
                this_segment.extend(leg_coords)
                this_segment_nodes.append(nodes[k][leg_i+1])
        #add last route segment
        segment_routes.append(this_segment)
        segment_nodes.append(this_segment_nodes)
        
        segment_routes_dict = {}
        for idx, seg in enumerate(segment_routes):
            segment_routes_dict[idx+1] = seg

        #construct a map for each route
        maps.append(
            folium_map(segment_routes_dict, segment_nodes, manual_editing_mode, filenamePostString=str(k), focal_points = 'first_last_only')
        )

    route_geojson_data = get_route_geojson(osrm_routes_dict)
    node_geojson_data = get_route_geojson(osrm_routes_dict)
    return VisualizationData(
        route_responses=responses_by_route_id,
        instructions=instructions_by_route_id,
        folium_map_data=maps,
        manual_editing_mode=manual_editing_mode,
        node_geojson=node_geojson_data,
        route_geojson=route_geojson_data,
    )
    # Create and save a js file containing geojson
    # with route geometry
    #create_geojson(assignment, routing, data)