# DEPRECATED FILE: use file_manager instead

import pathlib
import os
import ruamel.yaml

# # TODO: move the default output dir, but also update upload_results.py
# DEFAULT_OUTPUT_DIR = './'
#
# data_folder = pathlib.Path(".").absolute().parent / 'data'
# data_clean_folder = data_folder / 'gps_data_clean'
# time_dist_folder = data_folder / 'time_and_dist_matrices'
# map_folder = pathlib.Path(".").absolute().parent / 'maps'
# manual_edits_folder = pathlib.Path(".").absolute().parent / 'manual_edits'
# manual_maps_folder = manual_edits_folder / 'maps'
#
#
# def make_output_dir(output_dir=DEFAULT_OUTPUT_DIR):
#     dir_exist = os.path.exists(output_dir)
#     if not dir_exist:
#         os.makedirs(output_dir)
#
# ### Files to read ###
# #Customer GPS Input object can easily be customized here (i.e. files swicthed)
#
#
#
# ### Files to write ###
# class GPSOutput():
#
#     #file names to write to
#     f_gps_clean = data_clean_folder / 'clean_gps_points.csv'
#     f_gps_flagged = data_clean_folder / 'dropped_flagged_gps_points.csv'
#
#     def get_clean_filename(self):
#         return self.f_gps_clean
#
#     def get_flagged_filename(self):
#         return self.f_gps_flagged
#
# class TimeDistMatOutput():
#     time_dist_folder = time_dist_folder
#
#     def __init__(self, post_name_str=None):
#         """
#         Initializes the TimeDistMatOutput class.
#
#         Args:
#             post_name_str (str, default None): string for end of time/dist filename
#         """
#         self.post_name_str = post_name_str
#
#     def get_folder(self):
#         return time_dist_folder
#
#     def make_mat_filename(self, veh, time_or_dist):
#         filename_string = time_or_dist + '_matrix_' + veh
#         if self.post_name_str != None:
#             filename_string = filename_string + '_' + self.post_name_str + '.csv'
#         else:
#             filename_string += '.csv'
#         filepath = self.time_dist_folder / filename_string
#         return filepath
#
#     def make_snapped_gps_filename(self, veh):
#         filename_string = 'snapped_gps_' + veh
#         if self.post_name_str != None:
#             filename_string = filename_string + '_' + self.post_name_str + '.csv'
#         else:
#             filename_string += '.csv'
#         filepath = self.time_dist_folder / filename_string
#         return filepath
#
# class SolutionOutput():
# #done
#     def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
#         return os.path.join(output_dir, 'solution.txt')
#
# class RouteResponseOutput():
# #done
#     def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
#         return os.path.join(output_dir, 'route_response.json')
#
#
# class InstructionsOutput():
# #done
#     def get_filename(self, output_dir=DEFAULT_OUTPUT_DIR):
#         return os.path.join(output_dir, 'instructions.txt')
#
# class MapOutput():
#
#     base_filename = 'route_map'
#
#     def get_filename(self):
#         filename = self.base_filename
#         if self.filenamePreString != None:
#             filename = self.filenamePreString + filename
#         if self.filenamePostString != None:
#             filename += self.filenamePostString
#         filename += '.html'
#         filename = str(map_folder / filename)
#         return filename
#
#     def __init__(self, filenamePreString=None, filenamePostString=None):
#         self.filenamePreString = filenamePreString
#         self.filenamePostString = filenamePostString
#
#
# class ManualMapOutput():
#
#     base_filename = 'trip_map'
#
#     def get_filename(self):
#         filename = self.base_filename
#         if self.filenamePreString != None:
#             filename = self.filenamePreString + filename
#         if self.filenamePostString != None:
#             filename += self.filenamePostString
#         filename += '.html'
#         filename = str(manual_maps_folder / filename)
#         return filename
#
#     def __init__(self, filenamePreString=None, filenamePostString=None):
#         self.filenamePreString = filenamePreString
#         self.filenamePostString = filenamePostString
#
# class ManualEditRouteOutput():
#     #done
#     route_output = 'manual_routes_edits.xlsx'
#
#     def get_filename(self):
#         filename = str(manual_edits_folder / self.route_output)
#         return filename
#
# class ManualEditVehicleOutput():
# #done
#     veh_output = 'manual_vehicles.csv'
#
#     def get_filename(self):
#         filename = str(manual_edits_folder / self.veh_output)
#         return filename
#
# class ManualSolutionOutput():
#     #done
#     soln_output = 'manual_solution.txt'
#
#     def get_filename(self):
#         filename = str(manual_edits_folder / self.soln_output)
#         return filename
#
# class ManualGPSOutput():
# #done
#     #file names to write to
#     f_gps_clean = manual_edits_folder / 'clean_gps_points.csv'
#
#     def get_clean_filename(self):
#         return self.f_gps_clean
#
#
# class PickleNodeDataOutput():
#     #file names to write to
#     pickle_file = data_folder / 'node_data_pkl.p'
#
#     def get_filename(self):
#         return self.pickle_file
