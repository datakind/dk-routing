import attr
import ujson
import pathlib
from typing import List, Dict
import geojson as geojson_library
from .output_object_base import OutputObjectBase
from .file_manager import FileManager
from attr import attrs, attrib


@attr.s
class CleanedNodeData(object):
    node_data = attrib()


class CleanedNodeDataOutput(OutputObjectBase):

    def __init__(self, data: CleanedNodeData):
        self.data = data

    def persist(self, file_manager: FileManager):
        node_data = self.data.node_data
        # Write cleaned nodes to output. Note we write this to two places for legacy purposes
        paths = [
            file_manager.output_config.cleaned_gps_points_path,
            file_manager.output_config.manual_edit_gps_path
        ]
        for path in paths:
            node_data.write_nodes_to_file(
                file_manager.make_path(path),
                f_path_bad=file_manager.make_path(file_manager.output_config.cleaned_dropped_flagged_gps_path),
                verbose=True
            )

        # Write time/dist matrices to file
        # mat_file_config = TimeDistMatOutput(self.post_filename_str)
        for veh in node_data.veh_time_osrmmatrix_dict.keys():
            f_path_mat = self.make_mat_filename(veh, 'time')
            f_path_gps = self.make_snapped_gps_filename(veh)
            full_mat_path = file_manager.make_path(
                file_manager.output_config.time_and_dist_matrices_folder /
                f_path_mat)
            full_gps_path = file_manager.make_path(
                file_manager.output_config.time_and_dist_matrices_folder /
                f_path_gps)
            node_data.veh_time_osrmmatrix_dict[veh].write_to_file(
                full_mat_path, full_gps_path)
        for veh in node_data.veh_dist_osrmmatrix_dict.keys():
            f_path_mat = self.make_mat_filename(veh, 'dist')
            f_path_gps = self.make_snapped_gps_filename(veh)
            full_mat_path = file_manager.make_path(
                file_manager.output_config.time_and_dist_matrices_folder /
                f_path_mat
            )
            full_gps_path = file_manager.make_path(
                file_manager.output_config.time_and_dist_matrices_folder /
                f_path_gps
            )
            node_data.veh_dist_osrmmatrix_dict[veh].write_to_file(
                full_mat_path, full_gps_path
            )

    def make_mat_filename(self, veh, time_or_dist):
        filename_string = time_or_dist + '_matrix_' + veh
        # if self.post_name_str != None:
        #   filename_string = filename_string + '_' + self.post_name_str + '.csv'
        # else:
        filename_string += '.csv'
        return filename_string

    def make_snapped_gps_filename(self, veh):
        filename_string = 'snapped_gps_' + veh
        #if self.post_name_str != None:
        #    filename_string = filename_string + '_' + self.post_name_str + '.csv'
        #else:
        filename_string += '.csv'
        return filename_string
