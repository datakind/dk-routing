from typing import Any, Dict, Type
import json
from .output_object_base import OutputObjectBase
from .manual_route_data import ManualRouteDataOutput, ManualRouteData
from .route_solution_data import SolutionOutput, FinalOptimizationSolution
from .visualization_data import VisualizationData, VisualizationOutput
from .cleaned_node_data import CleanedNodeDataOutput, CleanedNodeData
OUTPUT_OBJECT_MAP: Dict[Any, Type[OutputObjectBase]] = {
    FinalOptimizationSolution: SolutionOutput,
    ManualRouteData: ManualRouteDataOutput,
    VisualizationData: VisualizationOutput,
    CleanedNodeData: CleanedNodeDataOutput,
}

def persist(output_object, file_manager):
    """ Persist output object.
    """
    output_type = OUTPUT_OBJECT_MAP.get(type(output_object))
    if not output_type:
        raise ValueError("Cannot find output object for " + type(output_object))
    output_object = output_type(output_object)
    output_object.persist(file_manager=file_manager)

def persist_config(config_manager, file_manager):
    # Save config to output file
    # TODO: Do this in a cleaner way extracting from config manager
    routing_config = config_manager.get_routing_config()
    raw_json = routing_config.get_raw_json()
    # write json to file
    config_json_path = file_manager.make_path("config.json")
    # Dump dict as json to file
    with open(config_json_path, 'w') as f:
        json.dump(raw_json, f, indent=2)


