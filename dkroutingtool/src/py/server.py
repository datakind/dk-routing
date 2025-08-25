import traceback
import json
import io
from contextlib import redirect_stderr
import main_application
import fastapi
import uvicorn
from fastapi import File, UploadFile
from typing import List
import glob
from fastapi.responses import FileResponse
import shutil
import requests
import os
import subprocess
import pandas as pd

app = fastapi.FastAPI()

stateful_info = dict()

def find_most_recent_output(session_id):
    most_recent = sorted(glob.glob(f'/WORKING_DATA_DIR/data{session_id}/output_data/*'))[-1]
    return most_recent

@app.post('/provide_files')
def provide_files(files: List[UploadFile] = File(...), session_id: str=''):
    for file in files:
        contents = file.file.read()
        #print(contents)
        provided = f'/data{session_id}/{file.filename}'
        os.makedirs(os.path.dirname(provided), exist_ok=True)
        with open(provided, 'wb') as f:
            f.write(contents)
        file.file.close()
    return {'message': 'Uploaded'}

@app.post('/update_vehicle_or_map')
def update_vehicle_or_map(session_id: str=''):
    # For when user uploads vehicles files + a corresponding build_parameters.yml or a *.pbf map.
    build_profiles = False

    # Look for and move uploaded build_parameters.yml
    build_params_file = glob.glob(f'/data{session_id}/build_parameters.yml')
    if build_params_file:
        os.replace(build_params_file[0], '/build_parameters.yml')
        build_profiles = True
    # Look for and move any vehicle files
    vehicle_files = glob.glob(f'/data{session_id}/*.lua')
    if vehicle_files:
        for curr_file in vehicle_files:
            os.replace(curr_file, os.path.join('/osrm-backend/profiles', os.path.basename(curr_file)))
            veh_directory = '/'+os.path.basename(curr_file)[:-4] # removing the extension
            if not os.path.exists(veh_directory):
                os.makedirs(veh_directory)
        build_profiles = True
    # Look for osm.pbf file. Just pulls the first in sorted order if multiple are present.
    map_files = sorted(glob.glob(f'/data{session_id}/*.pbf'))
    if map_files:
        os.environ['osm_filename'] = 'upload_map'
        os.replace(map_files[0], '/upload_map.osm.pbf')
        build_profiles = True
    if build_profiles:
        temporary_build_profiles(osmpbf=True)

@app.get('/get_solution')
def get_solution(session_id: str=''):
    main_application.args.cloud = False
    main_application.args.manual_mapping_mode = False
    main_application.args.manual_input_path = None
    #temp_output = io.StringIO()
    try:
        main_application.main(user_directory=f'data{session_id}')
        stateful_info[f'{session_id}_last_output'] = 'Success'
    except Exception:
        error = traceback.format_exc()
        print(error)
        stateful_info[f'{session_id}_last_output'] = error

    return {'message': f"{stateful_info[f'{session_id}_last_output']}"}

@app.get('/get_map_info')
def get_map_info():
    return {'message': stateful_info.get('bounding_box')}

@app.post('/adjust_solution')
def get_solution_from_file(files: List[UploadFile] = File(...), session_id: str=''):
    most_recent = find_most_recent_output(session_id)
    print(most_recent)

    for file in files: # Only one expected
        contents = file.file.read()
        #print(contents)
        with open(f'{most_recent}/manual_edits/{file.filename}', 'wb') as f:
            f.write(contents)
        file.file.close()

    main_application.args.cloud = False
    main_application.args.manual_mapping_mode = True
    main_application.args.manual_input_path = f'{most_recent}/manual_edits'
    main_application.main(user_directory=f'data{session_id}')
    return {'message': 'Manual solution updated, please download again'}

@app.get('/adjust_solution_from_gui')
def get_solution_from_gui(session_id: str=''):
    most_recent = find_most_recent_output(session_id)
    print(most_recent)
    main_application.args.cloud = False
    main_application.args.manual_mapping_mode = True
    main_application.args.manual_input_path = f'{most_recent}/manual_edits'
    main_application.main(user_directory=f'data{session_id}')
    return {'message': 'Manual solution updated, please download again'}

@app.post('/save_adjustments')
def save_adjustments(files: List[UploadFile] = File(...), session_id: str='', sheet_name: str='Sheet1'):
    most_recent = find_most_recent_output(session_id)
    for file in files: # Only one expected
        contents = file.file.read()
        file.file.close()
        adjustments = pd.read_json(contents, orient='split')
        adjustments.to_excel(f'{most_recent}/manual_edits/manual_routes_edits.xlsx', index=False, sheet_name=sheet_name)

    return {'message': 'Adjustments saved'}

@app.get('/get_adjustments')
def get_adjustments(session_id: str=''):
    most_recent = find_most_recent_output(session_id)
    dataset = dict()
    adjustments = pd.read_excel(f'{most_recent}/manual_edits/manual_routes_edits.xlsx', sheet_name=None)
    error = ''
    if len(adjustments.keys()) > 1:
        error = 'This does not support multiple configurations yet, please make sure you only have one item in "zone_configs" in config.json.'
    sheet_name = list(adjustments.keys())[0]
    adjustments = adjustments[sheet_name]
    
    dataset['adjustments'] = adjustments.to_json(orient='split', index=False)
    dataset['customers'] = pd.read_excel(f'data{session_id}/customer_data.xlsx').to_json(orient='split', index=False)
    with open(f'data{session_id}/custom_header.yaml', 'r') as path:
        dataset['headers'] = path.read()
    dataset['error'] = error
    dataset['sheet_name'] = sheet_name

    return {'message': json.dumps(dataset)}

@app.get('/download')
def download(session_id: str=''):
    most_recent = find_most_recent_output(session_id)
    print(most_recent)
    name= 'server_output'
    shutil.make_archive(name, 'zip', most_recent)
    name = name + '.zip'
    return FileResponse(path=name, filename=name, media_type='application/zip')


@app.get('/request_map/')
def request_map(minlat, minlon, maxlat, maxlon):  
    request_template = f'''
    [out:xml]
    [bbox:{minlon},{minlat}, {maxlon}, {maxlat}];
    nw[~"^(access|barrier|oneway|bollard|bridge|highway|route|maxspeed|junction|area)$"~"."];
    out body;
    >;
    out body qt;
    '''
    url = 'https://overpass-api.de/api/interpreter'
    print(request_template)
    r = requests.post(url, data=request_template)
    with open('ui_map.osm', 'w', encoding='utf-8') as opened:
        opened.write(r.text)
    os.environ['osm_filename'] = 'ui_map'
    temporary_build_profiles()
    stateful_info['bounding_box'] = [minlat, minlon, maxlat, maxlon]
    return {'message': 'Done'}


@app.get('/available_vehicles')
def request_vehicles():
    return {'message': f'{get_vehicles()}'}


def get_vehicles():
    with open('/build_parameters.yml', 'r') as opened:
        all_lines = opened.readlines()
        desired_vehicles = []
        found_types = False
        for line in all_lines:
            if found_types:
                if line.strip().startswith('-'):
                    desired_vehicles.append(line.replace('-','').strip())
                else:
                    break
            if 'vehicle-types' in line:
                found_types = True
    return desired_vehicles


def temporary_build_profiles(osmpbf=False):
    desired_vehicles = get_vehicles()

    print('Extracting-contracting networks per vehicle')

    vehicles = glob.glob('/osrm-backend/profiles/*.lua')

    osm_filename = os.environ['osm_filename']

    print(os.environ['osm_filename'], vehicles)

    for vehicle_file in vehicles:
        vehicle_name = vehicle_file.split('/')[-1].split(".lua")[0]
        if vehicle_name not in desired_vehicles:
            continue
        print('Building', vehicle_file)
        if not osmpbf:
            subprocess.run(['osrm-extract', '-p', vehicle_file, f'/{osm_filename}.osm'])
        else:
            subprocess.run(['osrm-extract', '-p', vehicle_file, f'/{osm_filename}.osm.pbf'])
        subprocess.run(f'mv {osm_filename}.osrm* {vehicle_name}/', shell=True)
        subprocess.run(['osrm-contract', f'{osm_filename}.osrm'], cwd=vehicle_name)
    

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
