"""Main entry point into the DK Routing tool.

Prefer using run_application.sh to launch.

Parameters:
  --input: Specify scenario directory name, default is 'input'.
  --local: If set, will use local data
  --manual: If set, will run manual mapping mode

Require environmental variables are only if we wish to operate from as
cloud directory, in which case we need access credentials. See run_application.sh.


"""
import sys
import json
import argparse
import time

import build_time_dist_matrix
import optimization
import visualization
import schedule
import upload_results
import manual_viz
import cloud_context
import os
from routing_configuration import RoutingConfig

parser = argparse.ArgumentParser(description='DK Routing Tool - route optimization CLI')
parser.add_argument('--input', dest='scenario', default='input')
parser.add_argument('--local', dest='cloud', action='store_false')
parser.add_argument('--manual', dest='manual_mapping_mode', action='store_true')
args = parser.parse_args()

def initialize_cloud_client(scenario, manual_mapping_mode):
    # First retreive the cloud context environment variable
    try:
      context = os.environ["CLOUDCONTEXT"]
    except KeyError as e:
      raise Exception('!! No Cloud Context Supplied.. are you trying to run local? (--local) !!', e)

    print(f' *   Using Cloud Contex:  {context}')
    if context.upper() == 'AWS':
      cloud_client = cloud_context.AWSS3Context(scenario)
    elif context.upper() == 'GDRIVE':
      cloud_client = cloud_context.GoogleDriveContext(scenario)
    else:
      raise Exception(f"Context Not Implemented: {context}")
    cloud_client.get_input_data(manual=manual_mapping_mode)
    return cloud_client

def run_routing_from_config(config_file='data/config.json'):
    """Run routing from configuration.

    Args:
      config_file: Path to config files
    Returns:
      Writes outputs to disk.
    """
    routing_config = RoutingConfig.from_file(config_file)
    errors = routing_config.validate()
    if errors:
      raise ValueError("Error loading config json:" + '\n'.join(errors))

    print(' *   Building Time/Distance Matrices')
    #check if node_loader_options are specified
    config = routing_config.raw_json()
    if 'node_loader_options' in config.keys():
      node_data = build_time_dist_matrix.process_nodes(config['node_loader_options'], config['zone_configs'])
    else:
      node_data = build_time_dist_matrix.process_nodes()
      error = routing_config.validate_against_node_data(node_data)
      if errors:
          raise ValueError("Node validation against config failed:" + '\n'.join(errors))

    print(f' *   Starting Model Run at {time.strftime("%H:%M:%S")} (UTC)')
    #Check if solver options are specified
    routes_for_mapping_viz, vehicles_viz, zone_route_map = optimization.main(node_data, config)
    visualization.main(routes_for_mapping_viz, vehicles_viz, zone_route_map)

def main():
  print(f' *   Model Run Initiated {time.strftime("%H:%M:%S")} (UTC)')

  # Initialize the cloud client if we are outputting to cloud directoyr.
  should_output_to_cloud = args.cloud
  cloud_client = None
  if should_output_to_cloud:
      cloud_client = initialize_cloud_client(args.scenario, args.manual_mapping_mode)

  # Run either config-based routing or manual mapping.
  if not args.manual_mapping_mode:
    print(' *   Running Config-based routing.')
    run_routing_from_config()
  else:
    print(' *   Running Manual Update Script')
    manual_viz.main()

  # Write results to cloud.
  if should_output_to_cloud:
    print(' *   Uploading Results to Cloud')
    upload_results.main(cloud_client, scenario=args.scenario, manual=args.manual_mapping_mode)

  #schedule.main(routes_for_mapping_viz, vehicles_viz, metrics)
  print(f' *   Model Run Complete at {time.strftime("%H:%M:%S")} (UTC)')

if __name__ == '__main__':
  main()
