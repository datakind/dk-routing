"""Main entry point into the DK Routing tool.

Prefer using run_application.sh to launch.

Parameters:
  --input: Specify scenario directory name, default is 'input'.
  --local: If set, will use local data
  --manual: If set, will run manual mapping mode

Require environmental variables are only if we wish to operate from as
cloud directory, in which case we need access credentials. See run_application.sh.

"""
import logging
import argparse
import time

import upload_results
import manual_viz
from cloud_context import initialize_cloud_client
from run_routing import run_routing_from_config
from config.config_manager import ConfigManager, ConfigFileLocations, GPSInputPaths, ManualEditsInputPaths
from output.file_manager import FileManager, OutputPathConfig
from output.cleaned_node_data import CleanedNodeData
from output import data_persisting
from geojson_to_gpx_converter import geojson_to_gpx_converter


logging.getLogger().setLevel(logging.INFO)
parser = argparse.ArgumentParser(description='DK Routing Tool - route optimization CLI')
parser.add_argument('--input', dest='scenario', default='input')
parser.add_argument('--local', dest='cloud', action='store_false')
parser.add_argument('--manual', dest='manual_mapping_mode', action='store_true')
parser.add_argument('--manual_input_path', dest='manual_input_path', default=None)
args = parser.parse_args()

OUTPUT_DATA_DIR = 'WORKING_DATA_DIR/output_data/'
INPUT_DATA_DIR = 'WORKING_DATA_DIR/input_data/'
LOCAL_TEST_INPUT_DATA_DIR = 'data/'

def main():
    timestamp = time.strftime("%Y_%m_%d_%H_%M")
    logging.info(f"Model Run Initiated {timestamp} (UTC)")

    # If a path is specified set the manual mode to true.
    if args.manual_input_path:
        args.manual_mapping_mode = True

    # Setup file manager.
    output_config = OutputPathConfig()
    # Output to this directory.
    output_path = OUTPUT_DATA_DIR + args.scenario + "_" + timestamp
    file_manager = FileManager(output_path, output_config)

    # Initialize the cloud client if we are outputting to cloud directory.
    should_use_cloud_data = args.cloud
    cloud_client = None
    if should_use_cloud_data:
        local_input_dir = INPUT_DATA_DIR + args.scenario + "_" + timestamp
        logging.info(f"Downloading cloud input data and storing locally at {local_input_dir}")
        cloud_client = initialize_cloud_client(args.scenario, file_manager)
        config_manager = ConfigManager.load_from_cloud(
            cloud_client, local_input_dir, args.manual_mapping_mode
        )
    else:
        local_input_dir = LOCAL_TEST_INPUT_DATA_DIR
        logging.info(f"Loading input from local {local_input_dir}")
        config_manager = ConfigManager.load_from_local(
            local_input_dir, args.manual_mapping_mode, args.manual_input_path)

    logging.info(f"Config setup: {config_manager}")

    # Run either config-based routing or manual mapping.
    if not args.manual_mapping_mode:
        logging.info('Running Config-based routing.')
        solution, vis_data = run_routing_from_config(config_manager=config_manager)
        data_persisting.persist(solution, file_manager)
        node_data = solution.intermediate_optimization_solution.node_data
        data_persisting.persist(CleanedNodeData(node_data), file_manager)
        data_persisting.persist(vis_data, file_manager)
        geojson_to_gpx_converter(output_path, output_path)
    else:
        logging.info('Running Manual Update Script')
        manual_vis_data = manual_viz.run_manual_route_update(config_manager=config_manager)
        data_persisting.persist(manual_vis_data, file_manager)
        geojson_to_gpx_converter(output_path, output_path)
    data_persisting.persist_config(config_manager, file_manager)
    logging.info(f"Writing output to {output_path}")
    # Write results to cloud.
    if should_use_cloud_data:
        logging.info('Uploading Results to Cloud')
        upload_results.upload_results(
            cloud_client,
            scenario=args.scenario,
            manual=args.manual_mapping_mode)

    # schedule.main(routes_for_mapping_viz, vehicles_viz, metrics)
    logging.info(f'Model Run Complete at {time.strftime("%H:%M:%S")} (UTC)')


if __name__ == '__main__':
    main()
