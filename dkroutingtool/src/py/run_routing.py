"""
Main entry point to run routing
"""
from typing import Tuple
import time
import logging
import build_time_dist_matrix
import optimization
import visualization
import cloud_context
import os
from config.config_manager import ConfigManager
from output.route_solution_data import FinalOptimizationSolution
from output.visualization_data import VisualizationData

def initialize_cloud_client(scenario, manual_mapping_mode):
    # First retreive the cloud context environment variable
    try:
        context = os.environ["CLOUDCONTEXT"]
    except KeyError as e:
        raise Exception('!! No Cloud Context Supplied.. are you trying to run local? (--local) !!', e)

    logging.info(f'Using Cloud Contex:  {context}')
    if context.upper() == 'AWS':
        cloud_client = cloud_context.AWSS3Context(scenario)
    elif context.upper() == 'GDRIVE':
        cloud_client = cloud_context.GoogleDriveContext(scenario)
    else:
        raise Exception(f"Context Not Implemented: {context}")
    cloud_client.get_input_data(manual=manual_mapping_mode)
    return cloud_client


def run_routing_from_config(config_manager: ConfigManager) -> Tuple[FinalOptimizationSolution, VisualizationData]:
    """Runs
    """
    routing_config = config_manager.get_routing_config()
    logging.info('Building Time/Distance Matrices')
    # check if node_loader_options are specified
    config = routing_config.get_raw_json()
    if 'node_loader_options' in config.keys():
        node_data = build_time_dist_matrix.process_nodes(
            config_manager,
            config['node_loader_options'],
            config['zone_configs'])
    else:
        node_data = build_time_dist_matrix.process_nodes(config_manager)

    errors = routing_config.validate_against_node_data(node_data)
    if errors:
        raise ValueError("Node validation against config failed:" + '\n'.join(errors))

    logging.info(f'Starting Model Run at {time.strftime("%H:%M:%S")} (UTC)')

    # Check if solver options are specified
    solution = optimization.run_optimization(node_data, config)
    visualization_data = visualization.create_visualizations(solution)
    return solution, visualization_data

