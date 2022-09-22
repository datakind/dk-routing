import shutil

import attr
import os
import logging
from enum import Enum
from .routing_configuration import RoutingConfig
from .build_parameters import BuildParametersConfig
from .gps_input_data import GPSInputData, GPSInputPaths
from .manual_edits_input_data import ManualEditsInputPaths, ManualEditsInputData

class ConfigType(Enum):
    """Describes the set of config and input objects we will load.
    """
    BUILD_PARAMETERS = 1
    ROUTING_CONFIG = 2
    GPS_INPUT_DATA = 3
    MANUAL_EDITS_INPUT_DATA = 4

@attr.s
class ConfigFileLocations(object):
    """Describes the locations of config and input data on disk.
    """
    routing_config_file = attr.ib(type=str)
    build_parameters_file = attr.ib(type=str)
    gps_input_files = attr.ib(type=GPSInputPaths)
    manual_edits_input_files = attr.ib(type=ManualEditsInputPaths, default=None)

class ConfigManager(object):
    def __init__(self, loaded_configs, config_file_locations):
        self.configs = loaded_configs
        self.config_file_locations = config_file_locations

    @staticmethod
    def load_from_cloud(cloud_context, local_dir, manual_mode):
        # Make local directory.
        os.makedirs(local_dir, exist_ok=True)
        # Copy file on disk from custom_header.yaml from data to local_dir.
        file_name = "custom_header.yaml"
        to_path = local_dir + "/" + file_name
        shutil.copy("data/" + file_name, to_path)

        cloud_context.download_input_data(local_dir)
        if manual_mode:
            logging.info(f"Downloading manual edits from cloud to {local_dir}")
            cloud_context.download_manual_edits_data(local_dir)
            path = f"{local_dir}/manual_edits"
            manual_edits_input = ManualEditsInputPaths(
                manual_route_edits=f"{path}/manual_routes_edits.xlsx",
                manual_vehicles=f"{path}/manual_vehicles.csv",
                clean_gps_points=f"{path}/clean_gps_points.csv",
            )
        else:
            manual_edits_input = None

        return ConfigManager.load(ConfigFileLocations(
                routing_config_file=f"{local_dir}/config.json",
                build_parameters_file='build_parameters.yml',
                gps_input_files=GPSInputPaths(
                    gps_file=f"{local_dir}/customer_data.xlsx",
                    custom_header_file=f"{local_dir}/custom_header.yaml",
                    gps_extra_input_file=f"{local_dir}/extra_points.csv"
                ),
                manual_edits_input_files=manual_edits_input
            )
        )

    @staticmethod
    def load_from_local(local_dir, manual_mode, manual_input_path):
        if manual_mode:
            if not manual_input_path:
                raise Exception("Manual mode requires a path to manual edits input files specified in --manual_input_path.")

            logging.info(f"Manual mode: readings manual data from output {manual_input_path} ")
            manual_edit_input_paths = ManualEditsInputPaths(
                manual_route_edits=f"{manual_input_path}/manual_routes_edits.xlsx",
                manual_vehicles=f"{manual_input_path}/manual_vehicles.csv",
                clean_gps_points=f"{manual_input_path}/clean_gps_points.csv",
            )
        else:
            manual_edit_input_paths = None
        return ConfigManager.load(
            ConfigFileLocations(
                routing_config_file=f"{local_dir}/config.json",
                build_parameters_file='build_parameters.yml',
                gps_input_files=GPSInputPaths(
                    gps_file=f"{local_dir}/customer_data.xlsx",
                    custom_header_file=f"{local_dir}/custom_header.yaml",
                    gps_extra_input_file=f"{local_dir}/extra_points.csv"
                ),
                manual_edits_input_files=manual_edit_input_paths
            )
        )

    def __repr__(self):
        return self.config_file_locations.__repr__()

    @staticmethod
    def load(config_files: ConfigFileLocations):
        config_files = config_files
        configs = {}
        configs[ConfigType.ROUTING_CONFIG] = ConfigManager.load_routing_config(config_files)
        configs[ConfigType.BUILD_PARAMETERS] = ConfigManager.load_build_parameters(config_files)
        configs[ConfigType.GPS_INPUT_DATA] = ConfigManager.load_gps_input_data(config_files)
        if config_files.manual_edits_input_files is not None:
            configs[ConfigType.MANUAL_EDITS_INPUT_DATA] = ConfigManager.load_manual_edits_input_data(config_files)
        return ConfigManager(configs, config_files)

    @staticmethod
    def load_routing_config(config_files: ConfigFileLocations):
        routing_config = RoutingConfig.from_file(config_files.routing_config_file)
        errors = routing_config.validate()
        if errors:
            raise ValueError("Error loading config json:" + '\n'.join(errors))
        return routing_config

    @staticmethod
    def load_build_parameters(config_files: ConfigFileLocations):
       return BuildParametersConfig.load(config_files.build_parameters_file)

    @staticmethod
    def load_gps_input_data(config_files: ConfigFileLocations):
        return GPSInputData.load(config_files.gps_input_files)

    @staticmethod
    def load_manual_edits_input_data(config_files: ConfigFileLocations):
        files = config_files.manual_edits_input_files
        if files:
            return ManualEditsInputData.load(files)
        else:
            return None

    def get_routing_config(self) -> RoutingConfig:
        return self.configs[ConfigType.ROUTING_CONFIG]

    def get_build_parameters(self) -> BuildParametersConfig:
        return self.configs[ConfigType.BUILD_PARAMETERS]

    def get_gps_inputs_data(self) -> GPSInputData:
        return self.configs[ConfigType.GPS_INPUT_DATA]

    def get_manual_edits_input_data(self) -> ManualEditsInputData:
        return self.configs[ConfigType.MANUAL_EDITS_INPUT_DATA]
