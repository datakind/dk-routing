from typing import Any, Dict, Type
from .output_object_base import OutputObjectBase
from .manual_route_data import ManualRouteDataOutput, ManualRouteData
from .route_solution_data import SolutionOutput, FinalOptimizationSolution
from .visualization_data import VisualizationData, VisualizationOutput

OUTPUT_OBJECT_MAP: Dict[Any, Type[OutputObjectBase]] = {
    FinalOptimizationSolution: SolutionOutput,
    ManualRouteData: ManualRouteDataOutput,
    VisualizationData: VisualizationOutput
}

def persist(output_object, file_manager):
    """ Persist output object.
    """
    output_type = OUTPUT_OBJECT_MAP.get(type(output_object))
    if not output_type:
        raise ValueError("Cannot find output object for " + type(output_object))
    output_object = output_type(output_object)
    output_object.persist(file_manager=file_manager)
