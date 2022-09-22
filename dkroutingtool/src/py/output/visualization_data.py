import attr
import ujson
import pathlib
from typing import List, Dict
import geojson as geojson_library
from .output_object_base import OutputObjectBase
from .file_manager import FileManager
from attr import attrs, attrib

@attr.s
class FoliumMapOutput(object):
    map_html_output = attrib(type=bytes)
    prefix = attrib(type=str)
    suffix = attrib(type=str)

@attr.s
class VisualizationData(object):
    route_responses = attrib(type=Dict[int, str])
    instructions = attrib(type=Dict[int, str])
    folium_map_data = attrib(type=List[FoliumMapOutput])
    route_geojson = attrib()
    node_geojson = attrib()
    manual_editing_mode = attrib()

class VisualizationOutput(OutputObjectBase):

    def __init__(self, data: VisualizationData):
        self.data = data

    def persist(self, file_manager: FileManager):
        self.persist_instructions(file_manager)
        self.persist_map_html(file_manager)
        self.persist_node_geojson(file_manager)
        self.persist_route_geojson(file_manager)
        self.persist_route_response(file_manager)

    def persist_map_html(self, file_manager: FileManager):
        if self.data.manual_editing_mode:
            base_filename = 'trip_data'
        else:
            base_filename = 'route_map'
        for map in self.data.folium_map_data:
            filename = base_filename
            if map.prefix != None:
                filename = map.prefix + filename
            if map.suffix != None:
                filename += map.suffix
            filename += '.html'
            # write to filepath
            this_path = pathlib.Path(file_manager.output_config.map_folder, filename)
            full_path = file_manager.make_path(this_path)
            with open(full_path, 'wb') as f:
                f.write(map.map_html_output)

    def persist_route_geojson(self, file_manager: FileManager):
        if self.data.manual_editing_mode:
            path = file_manager.make_path(file_manager.output_config.route_geojson_manual_path)
        else:
            path = file_manager.make_path(file_manager.output_config.route_geojson_path)

        with open(path, 'w') as output_file:
            geojson_library.dump(self.data.route_geojson, output_file)

    def persist_node_geojson(self, file_manager: FileManager):
        if self.data.manual_editing_mode:
            path = file_manager.make_path(file_manager.output_config.node_geojson_manual_path)
        else:
            path = file_manager.make_path(file_manager.output_config.node_geojson_path)

        with open(path, 'w') as output_file:
            geojson_library.dump(self.data.node_geojson, output_file)

    def persist_route_response(self, file_manager: FileManager):
        for route_id, response in self.data.route_responses.items():
            path = file_manager.make_path(file_manager.output_config.route_response_path)
            with open(path,  "a") as json_file_output:
                ujson.dump(response, json_file_output)

    def persist_instructions(self, file_manager: FileManager):
        for route_id, instructions in self.data.instructions.items():
            path = file_manager.make_path(file_manager.output_config.instructions_path)
            with open(path,  "a") as opened:
                opened.write(f"Trip: {route_id}\n")
                for instruction in instructions:
                    opened.write(instruction)
                    opened.write("\n")
                opened.write("\n")