import json
import base64
import requests
import datetime
import streamlit as st
import zipfile
import streamlit.components.v1 as components
from folium.plugins import Draw
from streamlit_folium import st_folium
import folium
import os
from streamlit.runtime import get_instance
from streamlit.runtime.scriptrunner import get_script_run_ctx

import numpy as np
import pandas as pd
import yaml

st.set_page_config(page_title='Container-based Action Routing Tool (CART)', layout="wide")

runtime = get_instance()
session_id = ''

host_url = 'http://{}:5001'.format(os.environ['SERVER_HOST'])

recalculate_map = True

def download_solution(solution_path, map_path):
    timestamp = datetime.datetime.now().strftime(format='%Y%m%d-%H-%M-%S')
    response = requests.get(f'{host_url}/download/?session_id={session_id}')

    solution_zip = response.content

    with open(f'solution_files_{timestamp}.zip', 'wb') as f:
        f.write(solution_zip)
    
    with zipfile.ZipFile(f'solution_files_{timestamp}.zip', 'r') as zipped:
        zipped.extractall(f'solution_files_{timestamp}/')
    
    with open(f'solution_files_{timestamp}/{solution_path}', 'r') as solution_txt:
        solution = solution_txt.read().replace('\n', '  \n')
    
    with open(f'solution_files_{timestamp}/{map_path}', 'r') as map_html:
        solutionmap = map_html.read()

    return solution, solutionmap, solution_zip

def request_solution():
    response = requests.get(f'{host_url}/get_solution/?session_id={session_id}')
    solution, solutionmap, solution_zip = download_solution(solution_path='solution.txt', map_path='/maps/route_map.html')

    return solution, solutionmap, solution_zip

def request_map(bounding_box):
    response = requests.get(f'{host_url}/request_map/?minlat={bounding_box[0]}&minlon={bounding_box[1]}&maxlat={bounding_box[2]}&maxlon={bounding_box[3]}')
    
    return True

def update_vehicle_or_map():
    response = requests.post(f'{host_url}/update_vehicle_or_map/?session_id={session_id}')

def bound_check(new, old):
    return old[0] <= new[0] and old[1] <= new[1] and old[2] >= new[2] and old[3] >= new[3] 

def adjust(adjusted_file):
    headers = {
    'accept': 'application/json'
    # 'Content-Type': 'multipart/form-data',
    }

    files = {'files': adjusted_file[0]} # We only expect one
    response = requests.post(f'{host_url}/adjust_solution/?session_id={session_id}', headers=headers, files=files)
    if response.ok:
        message = "Adjusted routes successfully uploaded"
    else: 
        message = 'Error, verify the adjusted routes file or raise an issue'
    
    solution, solutionmap, solution_zip = download_solution(solution_path='manual_edits/manual_solution.txt', map_path='maps/trip_data.html')
    return message, solution, solutionmap, solution_zip

def upload_data(files_from_streamlit):
    global session_id
    session_id = get_script_run_ctx().session_id # Only identifies a session if configuration files are uploaded

    files = [('files', file) for file in files_from_streamlit]

    headers = {
        'accept': 'application/json'
        #'Content-Type': 'multipart/form-data'
    }

    # if you wanted to not select them everytime?
    #files = [
    #    ('files', open('local_data/config.json', 'rb')),
    #    ('files', open('local_data/extra_points.csv', 'rb')),
    #    ('files', open('local_data/customer_data.xlsx', 'rb'))]

    response = requests.post(f'{host_url}/provide_files/?session_id={session_id}', headers=headers, files=files)
    if response.ok:
        return 'All files uploaded successfully'
    else:
        return 'Error, please verify your files or raise an issue'

def main():
    st.header('Container-based Action Routing Tool (CART)')

    vehicles_text = st.empty()
    vehicles_text.text('Available vehicle profiles: '+ requests.get(f'{host_url}/available_vehicles').json()['message'])
    recalculate_map = st.toggle(label='Calculate area to download from OpenStreetMaps automatically based on the locations to visit', value=True)
    if not recalculate_map:
        st.write('If required, draw a rectangle over the area you want to use for routing. Download it again only if you updated the OpenStreetMap data. Please select an area as small as possible.')
        m = folium.Map(location=[-11.9858, -77.019], zoom_start=5)
        Draw(export=False).add_to(m)
        map_output = st_folium(m, width=700, height=500)
        if map_output['last_active_drawing'] is not None:
            coords = map_output['last_active_drawing']['geometry']['coordinates']
            lats = [coords[0][i][0] for i in range(5)] # 5 because we expect a rectangle including its center point
            lons = [coords[0][i][1] for i in range(5)]
            bounding_box = [min(lats), min(lons), max(lats), max(lons)] # did I invert lats and lons here?
            area = abs(bounding_box[2] - bounding_box[0]) * abs(bounding_box[3] - bounding_box[1]) 
            st.write(f"Bounding box: {bounding_box}, area: {round(area,5)} Cartesian square units")
            if area > 0.05:
                st.write(f'Please choose a smaller area. We typically allow areas below 0.05')
            else:
                map_requested = st.button('Click here to download the area. You do not need to download it again if you try out multiple solutions below')
                if map_requested:
                    with st.spinner('Downloading the road network. This may take a few minutes, please wait...'):
                        request_map(bounding_box)
                    st.write('Road network ready for routing')

    uploaded_files = st.file_uploader('Upload all required files (config.json, customer_data.xlsx, extra_points.csv, custom_header.yaml)', accept_multiple_files=True)
    
    lat_lon_columns = []

    extra_configuration = False

    solution_requested = False

    if len(uploaded_files) > 0:
        
        # validation steps
        for uploaded in uploaded_files:
            if uploaded.name == 'config.json':
                try:
                    loaded = json.load(uploaded)
                    uploaded.seek(0)
                except json.JSONDecodeError:
                    st.error('The file config.json is not valid JSON. Please validate the syntax in a text editor')
            if uploaded.name.endswith('lua') or uploaded.name.endswith('osm.pbf') or uploaded.name.endswith('build_parameters.yml'):
                extra_configuration = True
            
            if uploaded.name == 'customer_data.xlsx':
                    customers = pd.read_excel(uploaded)
                    uploaded.seek(0)
            if uploaded.name == 'custom_header.yaml':
                    headers = yaml.load(uploaded, Loader=yaml.CLoader)
                    uploaded.seek(0)

            if uploaded.name == 'extra_points.csv':
                extra = pd.read_csv(uploaded)
                uploaded.seek(0)

        mandatory_columns = ['lat_orig', 'long_orig', 'name', 'zone']
        for column in mandatory_columns:
            to_check = headers.get(column)
            unknown_values = customers[to_check].isna().sum()
            if unknown_values > 0:
                st.error(f'{to_check} has {unknown_values} invalid value(s) (blank, missing, etc.), please verify customer_data.xlsx')

        if recalculate_map:
            lat_lon_columns.append(headers['lat_orig'])
            lat_lon_columns.append(headers['long_orig'])
            extra_coordinates = extra[['GPS (Latitude)','GPS (Longitude)']]

            all_coords = np.concatenate([customers[lat_lon_columns].values, extra_coordinates.values])
            area_buffer = 0.07 # adding a buffer for the road network, 0.1 is about 11 km long at the equator
            minima = all_coords.min(axis=0)-area_buffer
            maxima = all_coords.max(axis=0)+area_buffer
            bounding_box = [minima[1], minima[0], maxima[1], maxima[0]] 
            area = abs(bounding_box[2] - bounding_box[0]) * abs(bounding_box[3] - bounding_box[1]) 
            
        response = upload_data(uploaded_files)
        st.write(response)
        if extra_configuration:
            vehicle_or_map_update_requested = st.button('If you uploaded modified *.lua, build_parameters.yml, or *.osm.pbf files, click here to update the network')
            if vehicle_or_map_update_requested:
                with st.spinner('Rebuilding based on updated vehicles/maps. This may take a few minutes, please wait...'):
                    update_vehicle_or_map()
                vehicles_text.text('Available vehicle profiles: '+ requests.get(f'{host_url}/available_vehicles').json()['message'])

        if recalculate_map:
            response = requests.get(f'{host_url}/get_map_info/')
            old_bounding_box = [0,0,0,0]
            if response.json()["message"] is not None:                
                old_bounding_box = tuple(map(np.float64, response.json()['message']))

            if bound_check(tuple(bounding_box), old_bounding_box):
                st.write(':heavy_check_mark: The currently available map covers the desired area, no need to redownload it unless you edited OSM since the last download')
            else:
                st.error(f"It would be recommended to download the area as you have locations in your input data outside the currently downloaded area. The size is {round(area,2)} in Cartesian square units, be mindful that values above 0.2 may lead to the download taking many minutes")
            
            map_requested_auto = st.button(f'Click here to download the area. You do not need to download it again if you try out multiple scenarios with the same customer_data.xlsx file')
            
            if map_requested_auto:
                with st.spinner('Downloading the road network. Please wait...'):
                    request_map(bounding_box)
                #st.write(':heavy_check_mark: Road network ready for routing')
                st.rerun() 
        st.write('Calculating a solution will take up to twice the amount of time specified by the config file')
        solution_requested = st.button('Click here to calculate routes')
    
    if solution_requested:
        with st.spinner('Computing routes, please wait...'):
            solution, solutionmap, solution_zip = request_solution()
        #this button reloads the page, let's avoid it
        #st.download_button('Download solution files', solution_zip, file_name='solution.zip', 
        #                   mime='application/octet-stream', help='Downloads all the files generated by the tool')
        b64 = base64.b64encode(solution_zip).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="solution.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(solutionmap, height = 800)
        st.write(solution)
    
    st.subheader('Optional route adjustments')
    uploaded_files = st.file_uploader('If adjustments are made in the manual_edits spreadsheet, upload it here to get adjusted solutions', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        with st.spinner('Adjusting routes, please wait...'):
            response, solution, solutionmap, solution_zip = adjust(uploaded_files)
        st.write(response)
        b64 = base64.b64encode(solution_zip).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="solution.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(solutionmap, height = 800)
        st.write(solution)

if __name__ == '__main__':
    main()