import json
import base64
import requests
import datetime
import streamlit as st
import zipfile
import streamlit.components.v1 as components
from folium.plugins import Draw
from streamlit_folium import st_folium
from folium.plugins import BeautifyIcon
from io import StringIO

import folium
import os
from streamlit.runtime import get_instance
from streamlit.runtime.scriptrunner import get_script_run_ctx

import numpy as np
import pandas as pd
import yaml

#TODO Need to make sure you can retrieve original solution state even if manual adjustments were requested? 

# color list is the same as the backend
colorlist = ['green', 'blue',  'orange', 'purple', 'pink',  'black', 'beige', 'white', 'darkred', 'lightblue', 'red', 'darkblue', 'darkpurple', 'lightgreen', 'lightred', 'lightgray', 'cadetblue', 'darkgreen', 'gray']

st.set_page_config(page_title='Container-based Action Routing Tool (CART)', layout="wide")

runtime = get_instance()
session_id = ''

host_url = 'http://{}:5001'.format(os.environ['SERVER_HOST'])

def request_data_for_adjustments():
    response = requests.get(f'{host_url}/get_adjustments/?session_id={session_id}')
    message = json.loads(response.json()['message'])
    customers = pd.read_json(StringIO(message['customers']), orient='split')
    points = pd.read_json(StringIO(message['adjustments']), orient='split')
    sheet_name = message['sheet_name']
    if len(message['error']) > 1:
        st.write(message['error'])

    points['node_num'] = points['node_num'].astype(str)
    headers = yaml.safe_load(message['headers'])

    new_headers = dict()
    for key, value in headers.items():
        new_headers[value] = key
    customers.columns = [new_headers.get(c,c) for c in customers.columns]
    customers['name'] = customers['name'].astype('str')
    if 'columns_to_display' not in customers.columns:
        customers['columns_to_display'] = ''
    customers = customers[['lat_orig','long_orig', 'columns_to_display', 'name', 'zone']]
    return customers, headers, sheet_name, points

def read_data():
    #customers, headers, sheet_name, points = request_data_for_adjustments()
    #return customers, headers, sheet_name, points
    if True:
        if 'reread_data' in st.session_state and st.session_state['reread_data']:
            customers, headers, sheet_name, points = request_data_for_adjustments()
            st.session_state['read_customers'] = customers
            st.session_state['read_points'] = points
            st.session_state['read_headers'] = headers
            st.session_state['sheet_name'] = sheet_name
            st.session_state['reread_data'] = False

        elif 'read_customers' in st.session_state:
            customers = st.session_state['read_customers']
            headers = st.session_state['read_headers']
            sheet_name = st.session_state['sheet_name']
            points = st.session_state['read_points']
        
        else:
            customers, headers, sheet_name, points = request_data_for_adjustments()
            st.session_state['read_customers'] = customers
            st.session_state['read_points'] = points
            st.session_state['read_headers'] = headers
            st.session_state['sheet_name'] = sheet_name
            st.session_state['reread_data'] = False

        return points, customers, headers, sheet_name    

def allow_change():
    selected_prefix = "Selected, "

    def add_markers():
        for route_key, frame in st.session_state['points'].groupby('route'):
            route_counter = 0
            for i,p in frame.iterrows(): # crucial information here is that i is the index label
                if not pd.isna(p['lat_orig']):
                    if "Relanse" in p['columns_to_display']:
                        icon = folium.plugins.BeautifyIcon(border_color=route_key.split('-')[0], 
                            text_color='black', 
                            background_color='#BFFFDA',
                            number=route_counter,
                            icon_shape='circle')

                    if "Koupe" in p['columns_to_display']:
                        icon = folium.plugins.BeautifyIcon(border_color=route_key.split('-')[0], 
                            text_color='black', 
                            background_color='#FFBFFA',
                            number=route_counter,
                            icon_shape='circle')
                    else:
                        icon = folium.plugins.BeautifyIcon(border_color=route_key.split('-')[0], 
                            text_color='black', 
                            number=route_counter,
                            icon_shape='marker')
                    marker = folium.Marker([p['lat_orig'], p['long_orig']], 
                                        tooltip=f"Name:{p['name']}, Route: {route_key}, Info: {p['columns_to_display']} {p['additional_info']}, Index: {i}",
                                        icon=icon)
                    fg.add_child(marker)
                    route_counter += 1
                else:
                    continue
                
        for selected_index, selected in enumerate(st.session_state['selected']):
            index = int(selected.split('Index:')[-1].strip())
            selected = st.session_state['points'].loc[index]
            
            icon = folium.plugins.BeautifyIcon(border_color='black', 
                                        text_color='white',
                                        background_color='black', 
                                        number=selected_index,
                                        icon_shape='marker')
            
            marker = folium.Marker([selected['lat_orig'], selected['long_orig']], 
                                tooltip=f"{selected_prefix}Name:{selected['name']}, Route: {selected['route']}, Index: {index}",
                                icon=icon)
            fg.add_child(marker)

    def update_map():
        just_clicked = map_output['last_object_clicked_tooltip']
        if just_clicked is not None and st.session_state['last_selected'] != just_clicked:
            if not just_clicked.startswith('Selected'):
                st.session_state['selected'].append(just_clicked)
                st.session_state['last_selected'] = just_clicked
                st.rerun()
            else:
                original_clicked = just_clicked[len(selected_prefix):]
                if original_clicked in st.session_state['selected']:
                    st.session_state['selected'].remove(original_clicked)
                    st.rerun()
    
    def clear_selection():
        st.session_state['selected'] = []
        st.session_state['last_selected'] = None
        st.session_state['reset_number'] += 1
        st.rerun()
    
    def save_adjustments():
        to_save = st.session_state['points'][st.session_state['adjustment_columns_to_export']].to_json(orient='split', index=False)
        headers = {'accept': 'application/json'}
        files = {'files': to_save} # We only expect one
        
        response = requests.post(f'{host_url}/save_adjustments/?session_id={session_id}&sheet_name={st.session_state["sheet_name"]}', headers=headers, files=files)
        if not response.ok:
            st.write(f'Error saving the adjustments: {response}')
    
    def update_data(route_change):
        # Just changing their route id
        records_to_move = []
        for point in st.session_state['selected']:
            index = int(point.split('Index:')[-1].strip())
            records_to_move.append(index)
            st.session_state['points'].loc[index, 'route'] = route_change
        
        original = st.session_state['points'].copy()
        
        # Reordering
        if len(st.session_state['selected']) == 1:
            single_index = records_to_move[0]
            record_to_move = original.loc[single_index:single_index+0]


            first_positions = original[original['node_num'] == 'Depot']
            first_position = first_positions[first_positions['route'] == route_change].iloc[0:1].index[0]
            original = original.drop(index=single_index)
            firsthalf = original.loc[0:first_position]
            secondhalf = original.loc[first_position+1:]

            newpoints = pd.concat([firsthalf, record_to_move, secondhalf]).reset_index(drop=True)
            st.session_state['points'] = newpoints.copy()            

        else:
            consecutive_records = original.loc[records_to_move]
            first_position = records_to_move[0]
            
            original = original.drop(index=records_to_move)
            
            firsthalf = original.loc[0:first_position-1]
            secondhalf = original.loc[first_position+1:]

            newpoints = pd.concat([firsthalf, consecutive_records, secondhalf]).reset_index(drop=True)
            st.session_state['points'] = newpoints.copy()            
        
        save_adjustments()
        clear_selection()

    original_points, customers, headers, sheet_name = read_data()
    st.session_state['sheet_name'] = sheet_name
    st.session_state['adjustment_columns_to_export'] = original_points.columns
    points = pd.merge(original_points, customers, left_on='node_name', right_on='name', how='left')
    lat = points['lat_orig'].mean()
    lon = points['long_orig'].mean()
    partitions = set(points['route'])

    center = [lat, lon]
    zoom = 14

    if 'points' not in st.session_state:
        st.session_state['points'] = points.copy()
    if 'reset_number' not in st.session_state:
        st.session_state['reset_number'] = 0
    if "center" not in st.session_state:
        st.session_state["center"] = [lat, lon]
    if "zoom" not in st.session_state:
        st.session_state["zoom"] = 15
    if 'last_selected' not in st.session_state:
        st.session_state['last_selected'] = None
    if 'selected' not in st.session_state:
        st.session_state['selected'] = []

    key = f"key_{st.session_state['reset_number']}"

    m = folium.Map(location=center, zoom_start=zoom)

    fg = folium.FeatureGroup(name="Markers")

    add_markers()

    map_columns, info_columns = st.columns([3,1])
    with map_columns:
        map_output = st_folium(
            m,
            center=st.session_state["center"],
            zoom=st.session_state["zoom"],
            key=key,
            feature_group_to_add=fg,
            height=800,
            width=1200,
        )

        update_map()
    
    with info_columns:
        route_change = st.selectbox(label="Choose a route to assign the selected points", options=partitions)
        assigning = st.button('Click to assign according to your selection')
        if assigning:
            update_data(route_change)
            #st.session_state['reread_data'] = True
        
        st.write(st.session_state['points'].groupby('route')['demands'].sum())


        clearing = st.button('Clear current selection')
        if clearing:
            clear_selection()

        submitting = False
        #submitting = st.button('Click here to submit your adjustments and calculate a final solution')
        exporting = st.button('Save current work')
        if exporting:
            st.write(st.session_state['points'])
            st.session_state['points'][original_points.columns].to_excel(f'manual_routes_edits.xlsx', index=False, sheet_name=sheet_name)
            with open(f'manual_routes_edits.xlsx', 'rb') as opened:
                st.download_button('Download manual_routes_edits.xlsx', data=opened, file_name='manual_routes_edits.xlsx')

    if submitting:
        with st.spinner('Computing routes, please wait...'):
            response, st.session_state.solution, st.session_state.map, st.session_state.solution_zip = adjust_from_gui()
        st.session_state.b64 = base64.b64encode(st.session_state.solution_zip).decode()
        st.session_state['display_adjusted'] = True
    
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
    message = response.json()['message']
    if message != "Success":
        st.error(message.replace('\n', '  \n'))
        st.error("""Any outputs below are not valid, please inspect the error above.  \n
                 Guidelines: 
                 1) Typically an IndexError indicates that a location mentioned in config.json doesn't exist properly in the data, it might be a typo.
                 2) If it indicates that no solution was found, config.json may be changed to include more time or vehicles
                 3) If it's a KeyError followed by a vehicle name, make sure config.json has vehicles matching the list of available vehicles at the top of the page.""")

    #with st.expander('See optimization logs'):

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

def adjust_from_gui():
    response = requests.get(f'{host_url}/adjust_solution_from_gui/?session_id={session_id}')
    if response.ok:
        message = "Adjusted routes successfully uploaded"
    else: 
        message = 'Error, verify the adjusted routes file or raise an issue'
    
    solution, solutionmap, solution_zip = download_solution(solution_path='manual_edits/manual_solution.txt', map_path='maps/trip_data.html')
    return message, solution, solutionmap, solution_zip

def upload_data(files_from_streamlit):
    #global session_id
    #session_id = get_script_run_ctx().session_id # Only identifies a session if configuration files are uploaded

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

    if 'solution' not in st.session_state:
        st.session_state.solution = None
    if 'map' not in st.session_state:
        st.session_state.map = None
    if 'solution_zip' not in st.session_state:
        st.session_state.solution_zip = None
    if 'b64' not in st.session_state:
        st.session_state.b64 = None
    if 'file_already_uploaded' not in st.session_state:
        st.session_state['file_already_uploaded'] = False
    
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

    global session_id
    session_id = st.text_input('Session name', f'{get_script_run_ctx().session_id}')

    uploaded_files = st.file_uploader('Upload all required files (config.json, customer_data.xlsx, extra_points.csv, custom_header.yaml). You can refer to the [files here as an example](https://github.com/datakind/dk-routing/tree/main/dkroutingtool/local_data)', accept_multiple_files=True)
    mandatory_files = ['config.json', 'custom_header.yaml', 'customer_data.xlsx', 'extra_points.csv']

    for uploaded in uploaded_files:
        uploaded.name = uploaded.name.lower()

    present = []
    for uploaded in uploaded_files:
        present.append(uploaded.name)
    missing_files = set(mandatory_files).difference(set(present))
    
    if len(missing_files) > 0:
        st.error(f'Missing files: {list(missing_files)}')

    lat_lon_columns = []

    extra_configuration = False

    solution_requested = False
    if len(uploaded_files) > 0 and len(missing_files) == 0 and not st.session_state['file_already_uploaded']:
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

        mandatory_columns = ['lat_orig', 'long_orig', 'name', 'zone', 'buckets']
        optional_columns = ['closed', 'additional_info', 'time_windows']
        for column in mandatory_columns:
            to_check = headers.get(column)
            if to_check in customers.columns:
                unknown_values = customers[to_check].isna().sum()
                if unknown_values > 0:
                    added = ''
                    if column == 'buckets':
                        added = ' If the number of containers is unknown for a particular customer, please enter 0 as the value and the software will assume a default value.'
                    st.error(f'{to_check} has {unknown_values} invalid value(s) (blank, missing, etc.), please verify customer_data.xlsx before proceeding.{added}')
                    if unknown_values < 6:
                        st.write(customers[customers[to_check].isna()])
            else:
                st.error(f'{to_check} is missing in customer_data.xlsx and it is a mandatory column, please add it before proceeding or specify the right column in custom_header.yaml.')
        for column in optional_columns:
            to_check = headers.get(column)
            if to_check in customers.columns:
                unknown_values = customers[to_check].isna().sum()
                if unknown_values > 0:
                    st.write(f":grey_question: {to_check} has {unknown_values} invalid value(s) (blank, missing, etc.), please make this is fine for your use case")
            else:
                st.write(f":grey_question: {to_check} is not found in customer_data.xlsx, please make sure it is not needed for your use case")
        
        # automatic area selection
        if recalculate_map:
            lat_lon_columns.append(headers['lat_orig'])
            lat_lon_columns.append(headers['long_orig'])
            extra_coordinates = extra[['GPS (Latitude)','GPS (Longitude)']]

            all_coords = np.concatenate([customers[lat_lon_columns].values, extra_coordinates.values])
            area_buffer = 0.06 # adding a buffer for the road network, 0.1 is about 11 km long at the equator
            minima = np.nanmin(all_coords, axis=0)-area_buffer
            maxima = np.nanmax(all_coords, axis=0)+area_buffer
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
        
        if False:
            st.write('This is the presolved set of routes to which points are assigned.')
            allow_change_presolve()
    
        st.write('Calculating a solution will take up to the amount of time specified by the config file per region')
        solution_requested = st.button('Click here to calculate routes')

    else:
        old_solution_requested = st.button('If your session was interrupted, click here to retrieve a previous solution for the session name provided above')
        if old_solution_requested:
            st.session_state.solution, st.session_state.map, st.session_state.solution_zip = download_solution(solution_path='solution.txt', map_path='/maps/route_map.html')
            st.session_state.b64 = base64.b64encode(st.session_state.solution_zip).decode()
            
            #st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="solution.zip">Download solution files</a>', unsafe_allow_html=True)
            #components.html(solutionmap, height = 800)
            #st.write(solution)

    # On button press, save solution to session state to ensure persistence of added elements to dashboard
    if solution_requested:
        st.session_state['file_already_uploaded'] = True
        with st.spinner('Computing routes, please wait...'):
            st.session_state.solution, st.session_state.map, st.session_state.solution_zip = request_solution()
        st.session_state.b64 = base64.b64encode(st.session_state.solution_zip).decode()

    # If solution found and saved, display download link and map
    if st.session_state.solution:
        st.markdown(f'<a href="data:application/octet-stream;base64,{st.session_state.b64}" download="{session_id}.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(st.session_state.map, height=800)
        st.write(st.session_state.solution)
    
    st.subheader('Optional route adjustments')
    if st.session_state.solution:
        allow_change()
    
    if "display_adjusted" in st.session_state:
        show_manual_adjustments()

    uploaded_files = st.file_uploader('If adjustments are made in the manual_edits spreadsheet, upload it here to get adjusted solutions', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        with st.spinner('Adjusting routes, please wait...'):
            response, solution, solutionmap, solution_zip = adjust(uploaded_files)
        b64 = base64.b64encode(solution_zip).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{session_id}.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(solutionmap, height = 800)
        st.write(solution)

    old_solution_requested_adjusted = st.button('If your session was interrupted and you were waiting for an adjusted solution, click here to retrieve a previous solution for the session name provided above')
    if old_solution_requested_adjusted:
        solution, solutionmap, solution_zip = download_solution(solution_path='manual_edits/manual_solution.txt', map_path='maps/trip_data.html')
        b64 = base64.b64encode(solution_zip).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{session_id}.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(solutionmap, height = 800)
        st.write(solution)

def show_manual_adjustments():
    st.markdown(f'<a href="data:application/octet-stream;base64,{st.session_state.b64}" download="{session_id}.zip">Download solution files</a>', unsafe_allow_html=True)
    components.html(st.session_state.map, height=800)
    st.write(st.session_state.solution)
    
def allow_change_presolve():
    """Ignore for now, the case for adjustments post-solve is more important"""
    selected_prefix = "Selected, "

    def add_markers():
        for i,p in st.session_state['points'].iterrows():
            
            icon = folium.plugins.BeautifyIcon(border_color=colorlist[p['partition']], 
                                        text_color='black', 
                                        number=i,
                                        icon_shape='marker')
            marker = folium.Marker([p['x'], p['y']], 
                                tooltip=f"Name:{p['name']}, Route: {p['partition']}, Index: {i}",
                                icon=icon)
            fg.add_child(marker)

        for selected in st.session_state['selected']:
            index = int(selected.split('Index:')[-1].strip())
            selected = st.session_state['points'].iloc[index]
            marker = folium.Marker([selected['x'], selected['y']], 
                                tooltip=f"{selected_prefix}Name:{selected['name']}, Route: {selected['partition']}, Index: {index}",
                                icon=folium.Icon(color='gray', icon='star'))
            fg.add_child(marker)

    def update_map():
        just_clicked = map_output['last_object_clicked_tooltip']
        if just_clicked is not None and st.session_state['last_selected'] != just_clicked:
            if not just_clicked.startswith('Selected'):
                st.session_state['selected'].add(just_clicked)
                st.session_state['last_selected'] = just_clicked
                st.rerun()
            else:
                original_clicked = just_clicked[len(selected_prefix):]
                if original_clicked in st.session_state['selected']:
                    st.session_state['selected'].remove(original_clicked)
                    st.rerun()

    def update_data():
        for point in st.session_state['selected']:
            index = int(point.split('Index:')[-1].strip())
            st.session_state['points'].loc[index, 'partition'] = route_change
        st.session_state['selected'] = set()
        st.session_state['last_selected'] = None
        st.session_state['reset_number'] += 1
        st.rerun()

    points = pd.DataFrame()
    points['x'] = [-11.98, -11.985, -11.982, -11.989]
    points['y'] = [-77.018, -77.017, -77.017, -77.015]
    points['partition'] = [1, 1, 2, 0]
    points['name'] = ['a', 'b', 'c', 'd']

    partitions = set(points['partition'])

    center = [-11.9858, -77.019]
    zoom = 15

    if 'points' not in st.session_state:
        st.session_state['points'] = points.copy()
    if 'reset_number' not in st.session_state:
        st.session_state['reset_number'] = 0
    if "center" not in st.session_state:
        st.session_state["center"] = [-11.9858, -77.019]
    if "zoom" not in st.session_state:
        st.session_state["zoom"] = 15
    if 'last_selected' not in st.session_state:
        st.session_state['last_selected'] = None
    if 'selected' not in st.session_state:
        st.session_state['selected'] = set()

    key = f"key_{st.session_state['reset_number']}"

    m = folium.Map(location=center, zoom_start=zoom)

    fg = folium.FeatureGroup(name="Markers")

    add_markers()

    map_output = st_folium(
        m,
        center=st.session_state["center"],
        zoom=st.session_state["zoom"],
        key=key,
        feature_group_to_add=fg,
        height=500,
        width=700,
    )

    update_map()

    route_change = st.selectbox(label="Choose a route to assign the selected points", options=partitions)
    assigning = st.button('Click to assign according to your selection')
    if assigning:
        update_data()


if __name__ == '__main__':
    main()