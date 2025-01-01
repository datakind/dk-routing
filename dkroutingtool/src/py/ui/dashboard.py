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

st.set_page_config(page_title='Container-based Action Routing Tool (CART)', layout="wide")

runtime = get_instance()
session_id = ''

host_url = 'http://{}:5001'.format(os.environ['SERVER_HOST'])

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
        map = map_html.read()

    return solution, map, solution_zip

def request_solution():
    response = requests.get(f'{host_url}/get_solution/?session_id={session_id}')
    solution, map, solution_zip = download_solution(solution_path='solution.txt', map_path='/maps/route_map.html')

    return solution, map, solution_zip

def request_map(bounding_box):
    response = requests.get(f'{host_url}/request_map/?minlat={bounding_box[0]}&minlon={bounding_box[1]}&maxlat={bounding_box[2]}&maxlon={bounding_box[3]}')
    
    return True

def update_vehicle_or_map():
    response = requests.post(f'{host_url}/update_vehicle_or_map/?session_id={session_id}')

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
    
    solution, map, solution_zip = download_solution(solution_path='manual_edits/manual_solution.txt', map_path='maps/trip_data.html')
    return message, solution, map, solution_zip

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
    # Initialize session state, else get error 
    # from "if st.session_state.solution" clause
    # before solution requested
    if 'solution' not in st.session_state:
        st.session_state.solution = None
    if 'map' not in st.session_state:
        st.session_state.map = None
    if 'solution_zip' not in st.session_state:
        st.session_state.solution_zip = None
    if 'b64' not in st.session_state:
        st.session_state.b64 = None

    st.header('Container-based Action Routing Tool (CART)')

    vehicles_text = st.empty()
    vehicles_text.text('Available vehicle profiles: '+ requests.get(f'{host_url}/available_vehicles').json()['message'])
    
    st.write('If required, draw a rectangle over the area you want to use for routing. Download it again only if you updated the OpenStreetMap data. Please select an area as small as possible.')
    m = folium.Map(location=[-11.9858, -77.019], zoom_start=5)
    Draw(export=False).add_to(m)
    map_output = st_folium(m, width=700, height=500)
    if map_output['last_active_drawing'] is not None:
        coords = map_output['last_active_drawing']['geometry']['coordinates']
        lats = [coords[0][i][0] for i in range(5)] # 5 because we expect a rectangle including its center point
        lons = [coords[0][i][1] for i in range(5)]
        bounding_box = [min(lats), min(lons), max(lats), max(lons)]
        area = abs(bounding_box[2] - bounding_box[0]) * abs(bounding_box[3] - bounding_box[1]) 
        st.write(f"Bounding box: {bounding_box}, area: {round(area,5)} square units")
        if area > 0.04:
            st.write(f'Please choose a smaller area. We allow areas below 0.04')
        else:
            map_requested = st.button('Click here to download the area. You do not need to download it again if you try out multiple solutions below')
            if map_requested:
                with st.spinner('Downloading the road network. This may take a few minutes, please wait...'):
                    request_map(bounding_box)
                st.write('Road network ready for routing')

    uploaded_files = st.file_uploader('Upload all required files (config, locations, extra points)', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        response = upload_data(uploaded_files)
        st.write(response)
        vehicle_or_map_update_requested = st.button('If you uploaded modified *.lua, build_parameters.yml, or *.osm.pbf files, click here to update the network')
        if vehicle_or_map_update_requested:
            with st.spinner('Rebuilding based on updated vehicles/maps. This may take a few minutes, please wait...'):
                update_vehicle_or_map()
            vehicles_text.text('Available vehicle profiles: '+ requests.get(f'{host_url}/available_vehicles').json()['message'])

    st.write('Calculating a solution will take up to twice the amount of time specified by the config file')
    
    solution_requested = st.button('Click here to calculate routes')
    
    # On button press, save solution to session state to ensure persistence of added elements to dashboard
    if solution_requested:
        with st.spinner('Computing routes, please wait...'):
            st.session_state.solution, st.session_state.map, st.session_state.solution_zip = request_solution()
        st.session_state.b64 = base64.b64encode(st.session_state.solution_zip).decode()

    # If solution found and saved, display download link and map
    if st.session_state.solution:
        st.markdown(f'<a href="data:application/octet-stream;base64,{st.session_state.b64}" download="solution.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(st.session_state.map, height=800)
        st.write(st.session_state.solution)
    
    st.subheader('Optional route adjustments')
    uploaded_files = st.file_uploader('If adjustments are made in the manual_edits spreadsheet, upload it here to get adjusted solutions', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        with st.spinner('Adjusting routes, please wait...'):
            response, solution, map, solution_zip = adjust(uploaded_files)
        st.write(response)
        b64 = base64.b64encode(solution_zip).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="solution.zip">Download solution files</a>', unsafe_allow_html=True)
        components.html(map, height = 800)
        st.write(solution)

if __name__ == '__main__':
    main()