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

parser = argparse.ArgumentParser(description='DK Routing Tool - route optimization CLI')

parser.add_argument('--input', dest='scenario', default='input')
parser.add_argument('--local', dest='cloud', action='store_false')
parser.add_argument('--manual', dest='manual_mapping_mode', action='store_true')

args = parser.parse_args()

def verify_all_zones_have_customers(config, node_data):
    for zc in config['zone_configs']:
        for z in zc['optimized_region']:
            record_count = node_data.filter_nodedata({'zone':z}).all_clean_nodes.shape[0]
            if record_count == 0:
                raise Exception(f"Data Error: No Customers in Zone {z}, perhaps this is an error. Stopping Run! ")
    return True


class ValidateConfig:
    def __init__(self, config):
        self.config = config
        self.check_all_proper_start_end_setup()

    def _check_proper_start_end_setup(self, zone_config):
        enable_unload = zone_config.get('enable_unload', None)
        if enable_unload:
            assert len(zone_config['unload_vehicles']) > 0, '!! Unload is enabled - but no vehicles are provided. !!'
        elif enable_unload is False:
            assert (len(zone_config.get('Start_Point', [])) > 0) & \
                  (len(zone_config.get('End_Point', [])) > 0), \
            f'!! Missing Start or End Point !! - \n{zone_config}'

    def check_all_proper_start_end_setup(self):
        for zone_config in self.config['zone_configs']:
            self._check_proper_start_end_setup(zone_config)
        print('Config looks valid')
		

def main():
	print(f' *   Model Run Initiated {time.strftime("%H:%M:%S")} (UTC)')
	if args.cloud:
		# First retreive the cloud context environment variable
		try:
			context = os.environ["CLOUDCONTEXT"]
		except KeyError as e:
			raise Exception('!! No Cloud Context Supplied.. are you trying to run local? (--local) !!', e)

		print(f' *   Using Cloud Contex:  {context}')
		if context.upper() == 'AWS':
			cloud_client = cloud_context.AWSS3Context(args.scenario)
		elif context.upper() == 'GDRIVE':
			cloud_client = cloud_context.GoogleDriveContext(args.scenario)
		else:
			raise Exception(f"Context Not Implemented: {context}")
		cloud_client.get_input_data(manual=args.manual_mapping_mode)

	#If mapping from manual edits, go straight to that
	if args.manual_mapping_mode:
		print(' *   Running Manual Update Script')
		manual_viz.main()
	#Else run full program
	else:

		with open('data/config.json', 'r') as opened:
			config = json.load(opened)

		config_validator = ValidateConfig(config) # This can stop the process if the config is wrong

		print(' *   Building Time/Distance Matrices')
		#check if node_loader_options are specified
		if 'node_loader_options' in config.keys():
			node_data = build_time_dist_matrix.process_nodes(config['node_loader_options'], config['zone_configs'])
		else:
			node_data = build_time_dist_matrix.process_nodes()

		verify_all_zones_have_customers(config, node_data) # Will immediately stop the software

		print(f' *   Starting Model Run at {time.strftime("%H:%M:%S")} (UTC)')
		#Check if solver options are specified
		routes_for_mapping_viz, vehicles_viz, zone_route_map = optimization.main(node_data, config)

		visualization.main(routes_for_mapping_viz, vehicles_viz, zone_route_map)
	
	if args.cloud:
		print(' *   Uploading Results to Cloud')
		upload_results.main(cloud_client, scenario=args.scenario, manual=args.manual_mapping_mode)

	#schedule.main(routes_for_mapping_viz, vehicles_viz, metrics)
	print(f' *   Model Run Complete at {time.strftime("%H:%M:%S")} (UTC)')
if __name__ == '__main__':
	main()
