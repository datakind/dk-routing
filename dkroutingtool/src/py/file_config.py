#python 3.7
"""
Stores all file config information and some configuration info about input files (which prevents hard coding in code).
"""

import pathlib
import os
import ruamel.yaml

# TODO: move the default output dir, but also update upload_results.py
DEFAULT_OUTPUT_DIR = './'

data_folder = pathlib.Path(".").absolute().parent / 'data'
data_clean_folder = data_folder / 'gps_data_clean'
time_dist_folder = data_folder / 'time_and_dist_matrices'
map_folder = pathlib.Path(".").absolute().parent / 'maps'
manual_edits_folder = pathlib.Path(".").absolute().parent / 'manual_edits'
manual_maps_folder = manual_edits_folder / 'maps'


def make_output_dir(output_dir=DEFAULT_OUTPUT_DIR):
    dir_exist = os.path.exists(output_dir)
    if not dir_exist:
        os.makedirs(output_dir)

### Files to read ###
#Customer GPS Input object can easily be customized here (i.e. files swicthed)

class GPSInput():
    
    def __init__(self, filename, label_map):
        self.filename = filename
        self.label_map = label_map
        
    
    def get_filename(self):
        return self.filename
        
    def get_label_map(self):
        return self.label_map
      
class CustomerGPSInput(GPSInput):
    
    # read in file which contains lat long of each customer locations
    f_gps = data_folder / 'customer_data.xlsx'
    custom_header = f'{data_folder}/custom_header.yaml'

    yaml = ruamel.yaml.YAML(typ='safe')
    
    with open(custom_header, 'r') as opened:
        cust_label_map = yaml.load(opened)
        cust_label_map = {value: key for key, value in cust_label_map.items()} # Simply reverse the mapping

    def __init__(self):
        super().__init__(self.f_gps, self.cust_label_map)

class ExtraGPSInput(GPSInput):
    f_gps_extra = data_folder / 'extra_points.csv'
    
    extra_label_map = {'GPS (Latitude)':'lat_orig',\
    'GPS (Longitude)':'long_orig',\
    'name': 'name',\
    'type': 'type'
    }
    
    def __init__(self):
        super().__init__(self.f_gps_extra, self.extra_label_map)


### Files to write ###
class GPSOutput():
    
    #file names to write to
    f_gps_clean = data_clean_folder / 'clean_gps_points.csv'
    f_gps_flagged = data_clean_folder / 'dropped_flagged_gps_points.csv'
    
    def get_clean_filename(self):
        return self.f_gps_clean
        
    def get_flagged_filename(self):
        return self.f_gps_flagged
        
class TimeDistMatOutput():
    time_dist_folder = time_dist_folder
    
    def __init__(self, post_name_str=None):
        """
        Initializes the TimeDistMatOutput class.
        
        Args:
            post_name_str (str, default None): string for end of time/dist filename
        """
        self.post_name_str = post_name_str
    
    def get_folder(self):
        return time_dist_folder
        
    def make_mat_filename(self, veh, time_or_dist):
        filename_string = time_or_dist + '_matrix_' + veh
        if self.post_name_str != None:
            filename_string = filename_string + '_' + self.post_name_str + '.csv'
        else:
            filename_string += '.csv'
        filepath = self.time_dist_folder / filename_string
        return filepath
        
    def make_snapped_gps_filename(self, veh):
        filename_string = 'snapped_gps_' + veh
        if self.post_name_str != None:
            filename_string = filename_string + '_' + self.post_name_str + '.csv'
        else:
            filename_string += '.csv'
        filepath = self.time_dist_folder / filename_string
        return filepath

class SolutionOutput():

    def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
        return os.path.join(output_dir, 'solution.txt')

class RouteResponseOutput():

    def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
        return os.path.join(output_dir, 'route_response.json')


class InstructionsOutput():

    def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
        return os.path.join(output_dir, 'instructions.txt')

class MapOutput():
    
    base_filename = 'route_map'
    
    def get_filename(self):
        filename = self.base_filename
        if self.filenamePreString != None:
            filename = self.filenamePreString + filename
        if self.filenamePostString != None:
            filename += self.filenamePostString
        filename += '.html'
        filename = str(map_folder / filename)
        return filename
        
    def __init__(self, filenamePreString=None, filenamePostString=None):
        self.filenamePreString = filenamePreString
        self.filenamePostString = filenamePostString
        
        
class ManualMapOutput():

    base_filename = 'trip_map'

    def get_filename(self):
        filename = self.base_filename
        if self.filenamePreString != None:
            filename = self.filenamePreString + filename
        if self.filenamePostString != None:
            filename += self.filenamePostString
        filename += '.html'
        filename = str(manual_maps_folder / filename)
        return filename

    def __init__(self, filenamePreString=None, filenamePostString=None):
        self.filenamePreString = filenamePreString
        self.filenamePostString = filenamePostString

class ManualEditRouteOutput():
    
    route_output = 'manual_routes_edits.xlsx'
    
    def get_filename(self):
        filename = str(manual_edits_folder / self.route_output)
        return filename
        
class ManualEditVehicleOutput():

    veh_output = 'manual_vehicles.csv'

    def get_filename(self):
        filename = str(manual_edits_folder / self.veh_output)
        return filename
        
class ManualSolutionOutput():
    
    soln_output = 'manual_solution.txt'
    
    def get_filename(self):
        filename = str(manual_edits_folder / self.soln_output)
        return filename
        
class ManualGPSOutput():

    #file names to write to
    f_gps_clean = manual_edits_folder / 'clean_gps_points.csv'

    def get_clean_filename(self):
        return self.f_gps_clean
    
        
class PickleNodeDataOutput():

    #file names to write to
    pickle_file = data_folder / 'node_data_pkl.p'

    def get_filename(self):
        return self.pickle_file
        
class ManualPickleNodeDataOutput():

    #file names to write to
    pickle_file = manual_edits_folder / 'node_data_pkl.p'

    def get_filename(self):
        return self.pickle_file

