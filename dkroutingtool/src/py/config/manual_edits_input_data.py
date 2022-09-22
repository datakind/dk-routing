import attr
import pandas as pd
import ruamel.yaml
import numpy as np
import pathlib
from .gps_input_data import GPSInputData

@attr.s
class ManualEditsInputPaths(object):
    manual_route_edits = attr.ib(type=str)
    manual_vehicles = attr.ib(type=str)
    clean_gps_points = attr.ib(type=str)

class ManualEditsInputData(object):

    def __init__(self, manual_routes, manual_vehicles, clean_gps_node_data):
        self.manual_routes = manual_routes
        self.clean_gps_node_data = clean_gps_node_data
        self.manual_vehicles = manual_vehicles

    @staticmethod
    def load(paths: ManualEditsInputPaths):
        manual_edits_data = pd.ExcelFile(paths.manual_route_edits)
        clean_gps_data = GPSInputData.read_node_file(paths.clean_gps_points)
        manual_vehicles = pd.read_csv(paths.manual_vehicles)
        return ManualEditsInputData(
            manual_routes=manual_edits_data,
            clean_gps_node_data=clean_gps_data,
            manual_vehicles=manual_vehicles
        )

    def require(self):
        if self.manual_routes is None:
            raise ValueError("No manual routes available.")
        if self.clean_gps_node_data is None:
            raise ValueError("No clean gps node data available.")
        if self.manual_vehicles is None:
            raise ValueError("No manual vehicles data available.")
