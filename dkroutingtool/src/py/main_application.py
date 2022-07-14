"""Main entry point into the DK Routing tool.

Prefer using run_application.sh to launch.

Parameters:
  --input: Specify scenario directory name, default is 'input'.
  --local: If set, will use local data
  --manual: If set, will run manual mapping mode

Require environmental variables are only if we wish to operate from as
cloud directory, in which case we need access credentials. See run_application.sh.

"""
import argparse
import time

import upload_results
import manual_viz
from cloud_context import initialize_cloud_client
from run_routing import run_routing_from_config
from config.config_manager import ConfigManager, ConfigFileLocations, GPSInputPaths, ManualEditsInputPaths
from output.file_manager import FileManager, OutputPathConfig
from output import data_persisting

parser = argparse.ArgumentParser(description='DK Routing Tool - route optimization CLI')
parser.add_argument('--input', dest='scenario', default='input')
parser.add_argument('--local', dest='cloud', action='store_false')
parser.add_argument('--manual', dest='manual_mapping_mode', action='store_true')
args = parser.parse_args()

def main():
    print(f' *   Model Run Initiated {time.strftime("%H:%M:%S")} (UTC)')

    # Setup file manager.
    output_config = OutputPathConfig()
    # Output to this directory.
    # TODO: instead output to unique run output directory
    file_manager = FileManager('.', output_config)

    # Load configuration
    config_manager = ConfigManager.load(
        ConfigFileLocations(
            routing_config_file='data/config.json',
            build_parameters_file='build_parameters.yml',
            gps_input_files=GPSInputPaths(
                gps_file='data/customer_data.xlsx',
                custom_header_file='data/custom_header.yaml',
                gps_extra_input_file='data/extra_points.csv'
            ),
            manual_edits_input_files=ManualEditsInputPaths(
                manual_route_edits=file_manager.output_config.manual_edit_route_xlsx_path,
                manual_vehicles=file_manager.output_config.manual_edit_vehicles_path,
                clean_gps_points=file_manager.output_config.manual_edit_gps_path
            )
        )
    )

    # Initialize the cloud client if we are outputting to cloud directory.
    should_output_to_cloud = args.cloud
    cloud_client = None
    if should_output_to_cloud:
        cloud_client = initialize_cloud_client(args.scenario, args.manual_mapping_mode, file_manager)

    # Run either config-based routing or manual mapping.
    if not args.manual_mapping_mode:
        print(' *   Running Config-based routing.')
        solution, vis_data = run_routing_from_config(config_manager=config_manager)
        data_persisting.persist(solution, file_manager)
        data_persisting.persist(vis_data, file_manager)
    else:
        print(' *   Running Manual Update Script')
        manual_vis_data = manual_viz.run_manual_route_update(config_manager=config_manager)
        data_persisting.persist(manual_vis_data, file_manager)

    # Write results to cloud.
    if should_output_to_cloud:
        print(' *   Uploading Results to Cloud')
        upload_results.upload_results(
            cloud_client,
            scenario=args.scenario,
            manual=args.manual_mapping_mode)

    # schedule.main(routes_for_mapping_viz, vehicles_viz, metrics)
    print(f' *   Model Run Complete at {time.strftime("%H:%M:%S")} (UTC)')


if __name__ == '__main__':
    main()
