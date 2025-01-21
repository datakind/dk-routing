
# CART General Instructions

You'll need to install docker (e.g. Rancher Desktop). You can download a prebuilt docker image by executing `docker pull ghcr.io/datakind/dk-routing:main`. You will also need yq if you plan on building the tool's main image yourself.

The only vehicle profiles available are the ones defined in the directory `veh_profiles`, so make sure to have at least one profile there before building the solution. Feel free to add your own profiles as needed.

Refer to the Makefile for common use cases, e.g.
`make demo`
then go to http://localhost:8501/ to use the web-based interface. Instead of make, you can also execute 
`docker compose up`

## User Manual
This is the draft for a user manual, it has information about configuration options and a few things that are more related to setting up your workflow with the tool.
https://docs.google.com/document/d/1iOlXQk6_ElM_LdawJPREHNjVkv_2Qajam3is2hm5zyM

### Server API example
docker run --network host dkroutingtool:latest /opt/conda/bin/python src/py/server.py
or if you want to map ports instead: 
docker run -p 5001:5001 dkroutingtool:latest /opt/conda/bin/python src/py/server.py

curl -X "POST" "localhost:5001/provide_files" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "files=@local_data/config.json" -F "files=@local_data/customer_data.xlsx"

curl http://localhost:5001/get_solution

curl -o download.zip http://localhost:5001/download

curl -X "POST" "localhost:5001/adjust_solution" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "files=@download/manual_edits/manual_routes_edits.xlsx"

### GUI

Refer to the src/py/ui directory to try out the web-based interface.

## Dev

### Build
The whole image downloads OSRM 5.21, modifies default table parameters (because it ran into an issue otherwise),
compiles it, gets osm data, extracts and contracts it, then gets Python dependencies and compiles the bindings. This operation will take time the first time, while later builds will be much faster (as we assume new builds might only change python scripts rather than routing dependencies).

Within this folder (dkroutingtool) run:

`sh s_build_docker_dev.sh`


### Running Application
You can run the image interactively with the following:

`sh local_start.sh`

Once inside the container,  you have access to the application. The tool requires 3 data files, these files must be stored in the `local_data` directory prior to building the docker image. They must also have the same name as the files found in the github repo.

You can use a Jupyter Notebook once inside the container by typing
`sh manual.sh`

You can also interact with the software in other ways (as follows).

You can execute the routing by typing:

`PYTHONPATH=./py-lib:src/py /opt/conda/bin/python src/py/main_application.py --local`

From there, you can look at the files written by the application. If you want to copy them from the docker container to your local filesystem, you can do something like this in a second terminal:

To get the container name run the following in your local terminal (not in docker):
`docker ps`

You'll see a list of containers running, they'll have funny names automatically generated (dkroutingtool above is the image name, the container name is different).

 Then you can do this (still in the local terminal, the one not inside docker):

`docker cp <container_name>:/path/to/file /where/you/want/your/file`

------------------------------------------------------------------------------------------

<br>

## Updating The Tool

### Update OSM Data
If you have previously built the docker image want to use the newest OSM data(docker will use previously cached osm
data otherwise), you can force an osm update by running the following script (be warned that the script automatically cleans dangling docker images, comment out the prune line in the following script if you want to avoid this behavior):

`sh s_update_osm_data.sh`
<br>

-----------------------------------------------------------
### File input and output structure

Running in cloud mode:
When running using the cloud provider the tool will download all input data from the cloud
into the local data directory in WORKING_DATA_DIR/input_data/<scenario>-datetime/ folder and
then read from that directory. All outputs are put into WORKING_DATA_DIR/output_data/<scenario>-datetime/.
This is then zipped and uploaded to the output/ directory in the root cloud folder.

Running in local mode:
When running locally the tool will read from the data/ directory and write to the same
WORKING_DATA_DIR/output_data/<scenario>-datetime/ directory. for the output.

------------------------------------------------------------------------------
### Running the model with google drive output (for DEVELOPERS)
You can run the model with google drive by putting your credentials in src/creds/gdrive_creds.json

Then create a version of scripts/run_app.sh with the folder ids filled in (you can access these) by right
clicking your files in google drive -> copy link -> and extracting the id in the URI.

Then you can run it in the docker environment as follows:

export CLOUDCONTEXT=gdrive
export GDRIVECUSTOMERFILEID=...
export GDRIVEEXTRAFILEID=...
export GDRIVEROOTFOLDERID=...
export GDRIVECREDSFILE=src/creds/gdrive_creds.json

# Local mode
/opt/conda/bin/python src/py/main_application.py --input test_scenario --local

# Local Manual Mode
/opt/conda/bin/python src/py/main_application.py --input test_scenario --manual_input_path WORKING_DATA_DIR/output_data/test_scenario_2022_09_16_19_38/manual_edits --local

# Cloud mode
/opt/conda/bin/python src/py/main_application.py --input test_scenario

# Cloud manual mode
/opt/conda/bin/python src/py/main_application.py --input test_scenario --manual

# Troubleshooting Steps for New Users (06/01/2025)
If you try to start the docker container after pulling it, you may get a message in your terminal that looks like this:

`2025-01-01 14:49:56 INFO:root:Running Config-based routing.
2025-01-01 14:49:56 INFO:root:Building Time/Distance Matrices
2025-01-01 14:49:56 INFO:root:Num buckets Assumed: 2
2025-01-01 14:49:56 INFO:root:Starting Model Run at 13:49:56 (UTC)
2025-01-01 14:49:59 INFO:root:Took 1.8156040000000004 seconds to resequence
2025-01-01 14:49:59 INFO:root:Total Distance of all routes: 14.276600000000002km
2025-01-01 14:49:59 INFO:root:Total Time of all routes: 1599.1000000000004min
2025-01-01 14:50:03 INFO:root:Took 3.667045 seconds to resequence
2025-01-01 14:50:03 INFO:root:Total Distance of all routes: 21.9679km
2025-01-01 14:50:03 INFO:root:Total Time of all routes: 2528.1min
2025-01-01 14:50:03 INFO:root:Optmization Complete: Took 00min 06sec to optimize [['East'], ['West']]
2025-01-01 14:50:08 INFO:root:Writing output to WORKING_DATA_DIR/data/output_data/input_2025_01_01_13_49
2025-01-01 14:50:08 INFO:root:Model Run Complete at 13:50:08 (UTC)
2025-01-01 14:50:08 False
2025-01-01 14:50:08 False`

This appears to be the default behavior when you attempt to start the docker container. Therefore, in order to get the application up and running locally, you will need to take the following steps:

- Clone the repository or download it as a zip file: You may encounter an error in your terminal when you run `git clone https://github.com/datakind/dk-routing`. Most likely, the error occurs because the buffer size of your installed Git is too small to be able to successfully clone the repository, which is quite large. Therefore, the solution is to manually increase the buffer size of Git by running something like `git config --global http.postBuffer 104857600` in your terminal. This increases your Git buffer size to 100MB. With that done, try cloning the repository again, and you should succeed this time. 
- Having successfully cloned the repository, the next step is to change into the `dkroutingtool` directory, which is a subdirectory in `dk-routing`. In your terminal, run `cd dkroutingtool`. If you downloaded the repository as a zip file, unzip it and change into the `dkroutingtool` subdirectory.
- Now that you are inside the `dkroutingtool` subdirectory, run `docker compose up`. Make sure you have started docker desktop prior to running the docker compose command. Otherwise, you will get an error in your terminal.
- With that command successfully executed, as a last step, navigate to `localhost:8501` in your browser and you should see the CART streamlit application running and ready to be explored.
