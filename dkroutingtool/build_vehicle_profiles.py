import subprocess
import glob
import os

#import ruamel.yaml # Sorry, not installed at this point in the docker image
#yaml = ruamel.yaml.YAML(typ='safe')
#with open('build_parameters.yaml', 'r') as opened:
#    desired_vehicles = yaml.load(opened)['Build']['vehicle-types']

with open('build_parameters.yml', 'r') as opened:
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

print(desired_vehicles)

print('Extracting-contracting networks per vehicle')

vehicles = glob.glob('osrm-backend/profiles/*.lua')

osm_filename = os.environ['osm_filename']

print(os.environ['osm_filename'], vehicles)

for vehicle_file in vehicles:
    vehicle_name = vehicle_file.split('/')[-1].split(".lua")[0]
    if vehicle_name not in desired_vehicles:
        continue
    print('Building', vehicle_file)
    subprocess.run(['osrm-extract', '-p', vehicle_file, f'{osm_filename}.osm.pbf'])
    subprocess.run(['mkdir', vehicle_name])
    subprocess.run(f'mv {osm_filename}.osrm* {vehicle_name}/', shell=True)
    subprocess.run(['osrm-contract', f'{osm_filename}.osrm'], cwd=vehicle_name)
