import os
import attr
import pathlib
from pathlib import Path

ROOT_OUTPUT_FOLDER = '.'
DATA_FOLDER = 'data'
GPS_CLEAN_FOLDER = 'gps_data_clean'
TIME_DIST_FOLDER = 'time_and_dist_matrices'
MAP_FOLDER = 'maps'
MANUAL_EDITS_FOLDER = 'manual_edits'
MANUAL_MAPS_FOLDER = f"{MANUAL_EDITS_FOLDER}/maps"

# Filenames
MANUAL_ROUTES_EDITS = 'manual_routes_edits.xlsx'
MANUAL_VEHICLES = 'manual_vehicles.csv'
CLEAN_GPS_POINTS = 'clean_gps_points.csv'

@attr.s
class OutputPathConfig(object):
    solution_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'solution.txt')
    )
    route_response_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'route_response.json')
    )
    route_geojson_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'route_geojson.geojson')
    )
    node_geojson_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'node_geojson.geojson')
    )
    # Put in manual dir instead.
    route_geojson_manual_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'route_geojson_manual.geojson')
    )
    # Put in manual dir instead.
    node_geojson_manual_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'node_geojson_manual.geojson')
    )
    instructions_path = attr.ib(
        default=Path(ROOT_OUTPUT_FOLDER, 'instructions.txt')
    )
    pickle_node_data_path = attr.ib(
        default=Path(DATA_FOLDER, 'node_data_pkl.p')
    )
    manual_edit_route_xlsx_path = attr.ib(
        default=Path(MANUAL_EDITS_FOLDER, MANUAL_ROUTES_EDITS)
    )
    manual_edit_vehicles_path = attr.ib(
        default=Path(MANUAL_EDITS_FOLDER, MANUAL_VEHICLES)
    )
    manual_edit_solution_path = attr.ib(
        default=Path(MANUAL_EDITS_FOLDER, 'manual_solution.txt')
    )
    manual_edit_gps_path = attr.ib(
        default=Path(MANUAL_EDITS_FOLDER, CLEAN_GPS_POINTS)
    )
    manual_pickle_node_data_path = attr.ib(
        default=Path(MANUAL_EDITS_FOLDER, 'node_data_pkl.p')
    )
    map_folder = attr.ib(
        default=Path(MAP_FOLDER)
    )
    cleaned_dropped_flagged_gps_path = attr.ib(
        default=Path(GPS_CLEAN_FOLDER, 'dropped_flagged_gps_points.csv')
    )
    cleaned_gps_points_path = attr.ib(
        default=Path(GPS_CLEAN_FOLDER, 'clean_gps_points.csv')
    )
    time_and_dist_matrices_folder = attr.ib(
        default=Path(TIME_DIST_FOLDER)
    )

class FileManager(object):

    def __init__(self,
                 root_output_path: str,
                 output_config: OutputPathConfig):
        self.root_output_path = pathlib.Path(root_output_path)
        self.output_config = output_config

    def make_path(self, path):
        full_path = self.root_output_path / path
        parent = full_path.parents[0]
        FileManager.make_dir_if_not_exist(parent)
        return full_path

    @staticmethod
    def make_dir_if_not_exist(output_dir):
        dir_exist = os.path.exists(output_dir)
        if not dir_exist:
           os.makedirs(output_dir)

