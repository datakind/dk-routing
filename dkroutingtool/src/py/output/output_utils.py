import pandas as pd

def write_to_spreadsheet(zone_route_map, routes_for_mapping, file_manager):
    #Create output for manual route editing option
    zone_dfs = {}
    #for each zone, construct lists of attributes of the nodes in order
    #print(routes_for_mapping)
    node_i = 1 # do not reset node numbers to have them match the trip index on the global map

    for zone_name, route_indices in zone_route_map.items():
        node_name = []
        route_num = []
        node_num = []
        loads = []
        demands = []
        additional_info = []
        

        #for each route in that zone
        for formula_index, route_id in enumerate(sorted(route_indices)):
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

            #formulas
            node_name.insert(formula_index,f'=COUNTIF(A:A,"{route_id}")-2')
            route_num.insert(formula_index,'Summary')
            node_num.insert(formula_index,f'Route {route_id}')
            loads.insert(formula_index,'')
            demands.insert(formula_index, f'=SUMIFS(E:E,A:A,"{route_id}",E:E, ">0")')
            additional_info.insert(formula_index,'')

        #make a df for the zone
        zone_df = pd.DataFrame({'route': route_num, 'node_num':node_num,
                                'node_name': node_name, 'load': loads, 'demands': demands,
                                'additional_info': additional_info})

        # Start Route Nums at 1 (not zero for external display)
        zone_df['route'] = zone_df['route']
        zone_dfs[zone_name] = zone_df

    #write the zone dataframes to a xlsx file with different sheets
    output_path = file_manager.make_path(
        file_manager.output_config.manual_edit_route_xlsx_path
    )
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for zone_key, zone_df in zone_dfs.items():
            zone_df.to_excel(writer, sheet_name=zone_key, index=False)

    with pd.ExcelWriter(str(output_path).replace('manual_routes','legacy_manual_routes'), engine='openpyxl') as writer: # for a specific flow, would like to deprecate or find a better solution
        colorList = sorted(["red","blue","green","orange","purple","yellow","black","pink"]) # again, not great ad-hoc thing here
        for zone_key, zone_df in zone_dfs.items():
            new_zone_df = zone_df.copy()
            for c in colorList:
                new_zone_df['route'] = new_zone_df['route'].str.replace(c+'-', '')
            new_zone_df.to_excel(writer, sheet_name=zone_key, index=False)
