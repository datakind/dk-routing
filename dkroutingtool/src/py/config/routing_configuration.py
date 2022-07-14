"""Class to manage routing config.json files.

Config.json files shoudl contain
  - zone_configs: Configuration for each zone we are routing within.
  - node_loader_options: Options
  - global_solver_optiosn: Options for solver.

example file is in local_data/config.json
"""
import sys
import json
from typing import List


class RoutingConfig:
    def __init__(self, config_json):
        """Initialize a routing config from json.

        Args:
          config_json: Json loaded dictionary.
        """
        self.config = config_json

    @staticmethod
    def from_file(file_path) -> 'RoutingConfig':
        """Loads a RoutingConfig from a json file.

        Args:
          file_path: filename path to json file.
        Returns: RoutingConfig.
        """
        config_contents = None
        with open(file_path, 'r') as opened:
            config_contents = json.load(opened)
        return RoutingConfig(config_contents)

    def get_raw_json(self):
        """TODO: consider creating a wrapper around this.
        """
        return self.config

    def _check_proper_start_end_setup(self, zone_config):
        """Ensures that each zone Start and End points are valid

        Args:
          zone_config: a single zone_config json object from the config.
        Returns:
          List of errors or empty list if none.
        """
        enable_unload = zone_config.get('enable_unload', None)
        errors = []
        if enable_unload:
            unload_vehicles = zone_config['unload_vehicles']
            if len(unload_vehicles) < 1:
                errors.append('!! Unload is enabled - but no vehicles are provided. !!')
        else:
            start = zone_config.get('Start_Point', [])
            if not start:
                errors.append(f'!! Missing Start Point !! - \n{zone_config}')
            end = zone_config.get('End_Point', [])
            if not end:
                errors.append(f'!! Missing End Point !! - \n{zone_config}')

        return errors

    def _verify_all_zones_have_customers(self, node_data: 'NodeData'):
        """Verify all zones in node data have customers that need these.

        Args:
          node_data: NodeData object.
        Returns:
          List of errors or empty list if none.
        """
        errors = []
        config = self.config
        for zc in config['zone_configs']:
            for z in zc['optimized_region']:
                record_count = node_data.filter_nodedata({'zone': z}).all_clean_nodes.shape[0]
                if record_count == 0:
                    zc['optimized_region'].remove(z)
                    print(f"Data check: No customers in zone {z}, perhaps this is an error. The zone will not be computed")
                    
        # Eliminating empty zone configs, as a zone config can cover many zones but they may all get removed previously 
        for zc in config['zone_configs']:
          if len(zc['optimized_region']) == 0:
            config['zone_configs'].remove(zc)

        return errors

    def validate_against_node_data(self, node_data: 'NodeData') -> List[str]:
        """Validate against node data.

        Args:
          node_data: NodeData object.
        Returns:
          List of errors or empty list if none.
        """
        errors = self._verify_all_zones_have_customers(node_data)
        return errors

    def validate(self) -> List[str]:
        """Validate json configuration is correct.

        Returns:
          List of errors or empty list if none.
        """
        errors = []
        # TODO: add more checks.
        for zone_config in self.config['zone_configs']:
            errors.extend(self._check_proper_start_end_setup(zone_config))
        return errors
