import attr
import pathlib

ROOT_OUTPUT_FOLDER = '.'
DATA_FOLDER = 'data'
GPS_CLEAN_FOLDER = 'gps_data_clean'
TIME_DIST_FOLDER = 'time_and_dist_matrices'
MAP_FOLDER = 'maps'
MANUAL_EDITS_FOLDER = 'manual_edits'
MANUAL_MAPS_FOLDER = f"{MANUAL_EDITS_FOLDER}/maps"

@attr.s
class OutputFile(object):
    path = attr.ib(str)
    filename = attr.ib(str)

@attr.s
class OutputPathConfig(object):
    solution_path = attr.ib(
        default=OutputFile(ROOT_OUTPUT_FOLDER, 'solution.txt')
    )
    route_response_path = attr.ib(
        default=OutputFile(ROOT_OUTPUT_FOLDER, 'route_response.json')
    )
    instructions_path = attr.ib(
        default=OutputFile(ROOT_OUTPUT_FOLDER, 'instructions.txt')
    )
    pickle_node_data_path = attr.ib(
        default=OutputFile(DATA_FOLDER, 'node_data_pkl.p')
    )
    manual_edit_route_path = attr.ib(
        default=OutputFile(MANUAL_EDITS_FOLDER, 'manual_routes_edits.xlsx')
    )
    manual_edit_vehicles_path = attr.ib(
        default=OutputFile(MANUAL_EDITS_FOLDER, 'manual_vehicles.csv')
    )
    manual_edit_solution_path = attr.ib(
        default=OutputFile(MANUAL_EDITS_FOLDER, 'manual_solution.txt')
    )
    manual_edit_gps_path = attr.ib(
        default=OutputFile(MANUAL_EDITS_FOLDER, 'clean_gps_points.csv')
    )
    manual_pickle_node_data_path = attr.ib(
        default=OutputFile(MANUAL_EDITS_FOLDER, 'node_data_pkl.p')
    )