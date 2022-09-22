import pandas as pd
from .output_object_base import OutputObjectBase
from .file_manager import FileManager
from attr import attrs, attrib

@attrs
class IntermediateOptimizationSolution(object):
    node_data = attrib()
    route_dict = attrib(type=dict)
    vehicles = attrib(type=dict)
    zone_route_map = attrib(type=dict)

@attrs
class FinalOptimizationSolution(object):
    intermediate_optimization_solution = attrib(type=IntermediateOptimizationSolution)
    routes_for_mapping = attrib(type=dict)
    vehicles = attrib(type=dict)
    zone_route_map = attrib(type=dict)

class SolutionOutput(OutputObjectBase):

    def __init__(self, solution_output: FinalOptimizationSolution):
        self.solution_data = solution_output

    def persist(self, file_manager: FileManager):
        self.save_vehicle_attributes(file_manager)
        self.save_solution_file(file_manager)
        self.save_manual_edits_xlsx(file_manager)

    def save_solution_file(self, file_manager: FileManager):
        """
        Prints solution (time, load, dist) to file.
        """
        solution_txt = self.serialize_solution()

        # Write output.
        path = file_manager.make_path(file_manager.output_config.solution_path)
        text_file = open(path, "w")
        text_file.write(solution_txt)
        text_file.close()

    def serialize_solution(self) -> str:
        """Renders solution as a string.
        """
        solution = self.solution_data.intermediate_optimization_solution
        route_dict = solution.route_dict
        vehicles = solution.vehicles
        node_data = solution.node_data

        plan_output = ''
        for route_id, route in route_dict.items():
            if 'display_name' in route:
                plan_output += 'Route ID {0}'.format(route['display_name'])
            else:
                plan_output += 'Route ID {0}'.format(route_id+1)
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
        return plan_output

    def save_manual_edits_xlsx(self, file_manager: FileManager):
        """
        Writes the objects from the output form optimization.py to excel/csv files to be edited.
        """
        zone_route_map = self.solution_data.zone_route_map
        routes_for_mapping = self.solution_data.routes_for_mapping

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

    def save_vehicle_attributes(self, file_manager):
        vehicles = self.solution_data.vehicles
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

        output_path = file_manager.make_path(
            file_manager.output_config.manual_edit_vehicles_path
        )
        pd.DataFrame(veh_manual).to_csv(output_path, index=False)

    def save_manual_gps_output(self, file_manager: FileManager):
        output_path = file_manager.make_path(
            file_manager.output_config.manual_edit_gps_path
        )
        node_data = self.solution_data.intermediate_optimization_solution.node_data
        node_data.write_nodes_to_file(output_path, verbose=True)
