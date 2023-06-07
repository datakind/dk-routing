"""

This file contains the function to convert GeoJSON file to GPX file

"""

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
    f = open(f'{geojson_file_path}/node_geojson.geojson')
    data = json.load(f)
    
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
        dataframe.to_csv(f'{output_path}/{idx}-input.csv')
        Converter(input_file=f'{output_path}/{idx}-input.csv').csv_to_gpx(lats_colname='lat',longs_colname='lon',output_file=f'{output_path}/{idx}-output.gpx')