import ruamel.yaml

class BuildParametersConfig(object):
    def __init__(self, build_config_yaml):
        self.build_config_yaml = build_config_yaml

    @staticmethod
    def load(file_path):
        yaml = ruamel.yaml.YAML(typ='safe')
        with open(file_path, 'r') as opened:
            return BuildParametersConfig(yaml.load(opened))

    def get_vehicle_profiles(self):
        return self.build_config_yaml['Build']['vehicle-types']