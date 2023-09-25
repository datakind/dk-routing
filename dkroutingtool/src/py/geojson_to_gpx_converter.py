"""

This file contains the function to convert GeoJSON file to GPX file

"""
import glob
from collections import defaultdict
from gpx_converter import Converter

import pandas as pd
import json

def geojson_to_gpx_converter(geojson_file_path : str, output_path : str):
    
    """
    Takes in the file path and converts the geoJSON file to GPX file
    
    Args : 
        geojson_file_path (str): The file of the geojson file stored in your system 
    
    Returns : None
    
    """
    
    # Loading the json object
    geojsons = glob.glob(f'{geojson_file_path}/*.geojson')
    for geojson in geojsons:
        with open(geojson) as f: 
            data = json.load(f)
        
        featuretype = 'node'
        if 'route_geojson' in geojson:
            featuretype = 'route'

        if featuretype == 'node':
            node_df = defaultdict(list)
                        
            for dictionary in data['features']:
                coordinates = dictionary['geometry']['coordinates']
                node_df['lon'].append(coordinates[0])
                node_df['lat'].append(coordinates[1])
                node_df['properties'].append(dictionary['properties']['zone'])
                node_df['node_name'].append(dictionary['properties']['name'])
                # print(coordinates)
            node_df = pd.DataFrame.from_dict(node_df)
            
        elif featuretype == 'route':
            new_df = defaultdict(list)

            # Creating a custom dataframe from the loaded JSON object
            for dictionary in data['features']:
                for coordinates in dictionary['geometry']['coordinates'][0]:
                    new_df['lon'].append(coordinates[0])
                    new_df['lat'].append(coordinates[1])
                    new_df['properties'].append(dictionary['properties']['id'])
                    # print(coordinates)
            new_df = pd.DataFrame.from_dict(new_df)
    
    # Creating GPX file and csv file for each property present in the JSON object
    
    for idx, dataframe in new_df.groupby('properties'):
        dataframe.to_csv(f'{output_path}/{featuretype}_{idx}-input.csv')
        Converter(input_file=f'{output_path}/{featuretype}_{idx}-input.csv').csv_to_gpx(lats_colname='lat',longs_colname='lon',output_file=f'{output_path}/{featuretype}_{idx}-output.gpx')
        with open(f'{output_path}/{featuretype}_{idx}-output.gpx', 'r') as opened:
            whole = opened.read()
            parts = whole.split('<trk>')
            additions = []
            node_filtered = node_df.groupby('properties').get_group(idx)
            for i,row in node_filtered.iterrows():
                additions.append(f'<wpt lat="{row.lat}" lon="{row.lon}"><name>{row.node_name}</name><sym>Waypoint</sym></wpt>\n')              
            whole = ''.join([parts[0]]+additions+['<trk>']+parts[1:])
        with open(f'{output_path}/{featuretype}_{idx}-output.gpx', 'w') as opened:
            opened.write(whole)