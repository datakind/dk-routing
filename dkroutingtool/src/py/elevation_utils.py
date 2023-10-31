import glob
import os
import numpy as np
import rasterio
import ujson
import pandas as pd
import requests
import datetime

import osrmbindings

osrm_filepath = os.environ['osm_filename']

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    
    All args must be of equal length. 
    Thanks StackOverflow for that piece
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    
    c = 2 * np.arcsin(np.sqrt(a))
    m = 6378137 * c
    return m

def download_elevation_data(bounding_box):
    """Needs south, north, west and east gps coordinates
    Need to add our own api key"""
    south_latmin = bounding_box[0]
    north_latmax = bounding_box[1]
    west_lonmin = bounding_box[2]
    east_lonmax = bounding_box[3]

    if len(glob.glob('/elevation.geotiff')) > 0:
        print('Reusing local elevation geotiff')
        return False

    print('Downloading digital elevation model of the area')
        
    path = f'https://portal.opentopography.org/API/globaldem?demtype=COP30&south={south_latmin}&north={north_latmax}&west={west_lonmin}&east={east_lonmax}&outputFormat=GTiff&API_Key=demoapikeyot2022'
    result = requests.get(path)

    with open('/elevation.geotiff','wb') as opened:
        opened.write(result.content)    
    print('Saved digital elevation model geotiff')

    return True

def compute_elevation_costs(vehicle, longitudes, latitudes):
    """Keeps the same order as the duration and distance matrices from the NodeData/Loader classes
    """
    print(f'Starting elevation calculations: {datetime.datetime.now()}')
    osrmbindings.initialize(f'/{vehicle}/{osrm_filepath}')

    elevation_cost = np.zeros((len(longitudes),len(longitudes)))

    with rasterio.open('/elevation.geotiff') as raster:
        altitude = raster.read()[0] #only one channel to extract, result is a xy array
        for source in range(len(longitudes)): # we could probably cut it in half once we analyze how assymetric routes impact the matrix
            for destination in range(len(longitudes)):
                if source == destination:
                    elevation_cost[source, destination] = 0
                    continue
                
                lons = [longitudes[source], longitudes[destination]]
                lats = [latitudes[source], latitudes[destination]]
                
                if np.unique(lons).shape[0] == 1 and np.unique(lats).shape[0] == 1:
                    elevation_cost[source, destination] = 0
                    continue

                response = osrmbindings.route(lons, lats) # need to write that loop in C++, or use py-osrm with nanobind
                parsed = ujson.loads(response)
                coords = np.array(parsed['routes'][0]['geometry']['coordinates'])
                ys = coords[:,1]
                xs = coords[:,0]
                
                ys0 = ys[0:-1]
                ys1 = ys[1:]
                xs0 = xs[0:-1]
                xs1 = xs[1:]
                rows, cols = rasterio.transform.rowcol(raster.transform, xs, ys)

                elevation_along_route = altitude[rows,cols]

                distances = haversine_np(xs0, ys0, xs1, ys1)
                #travelled = np.cumsum(distances)
                gradients = np.abs(np.diff(elevation_along_route))
                
                change = gradients/distances
                change[change == np.inf] = 0 #in case we divided by zero

                cost = np.max(change)
                elevation_cost[source, destination] = cost

    print(f'Elevation calculations done: {datetime.datetime.now()}')
    with open('gimme.cost','wb') as opened: # for debugging purposes
        np.save(opened, elevation_cost)
    return elevation_cost

