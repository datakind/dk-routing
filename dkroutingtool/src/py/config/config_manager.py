import attr
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
