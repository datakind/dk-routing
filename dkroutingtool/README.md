
# DK Routing Tool General instructions

The only vehicle profiles available are the ones defined in the directory `veh_profiles`, so make sure to have at least one profile there before building the solution. Feel free to add your own profiles as needed.

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

