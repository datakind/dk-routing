import attr
from .output_object_base import OutputObjectBase
from .file_manager import FileManager
from .visualization_data import VisualizationData, VisualizationOutput
from .route_solution_data import FinalOptimizationSolution, SolutionOutput
from attr import attrs, attrib

@attr.s
class ManualRouteData(object):
    modified_optimization_solution = attrib(type=FinalOptimizationSolution)
    modified_visualizations = attrib(type=VisualizationData)
    metrics_dict = attrib(type=dict)

class ManualRouteDataOutput(OutputObjectBase):

    def __init__(self, data: ManualRouteData):
        self.data = data

    def persist(self, file_manager: FileManager):
        """Write all Manual Route data to disk."""
        self.persist_manual_solution(file_manager)
        # Delegate to persist visualization data.
        VisualizationOutput(self.data.modified_visualizations).persist(file_manager)

    def persist_manual_solution(self, file_manager):
        """Write modified manual solution txt file."""
        path = file_manager.make_path(file_manager.output_config.manual_edit_solution_path)
        solution_str = self.serialize_solution()
        text_file = open(path, "w")
        text_file.write(solution_str)
        text_file.close()

    def serialize_solution(self) -> str:
        """
        Prints solution (time, load, dist) to file.
        """
        routes_for_mapping = self.data.modified_optimization_solution.routes_for_mapping
        vehicles = self.data.modified_optimization_solution.vehicles
        route_metrics_dict = self.data.metrics_dict

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
        return plan_output



