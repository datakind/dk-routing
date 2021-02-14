# DK Routing Tool General instructions

The only vehicle profiles available are the ones defined in the directory `veh_profiles`, so make sure to have at least one profile there before building the solution. Feel free to add your own profiles as needed.

## Dev 

### Build
The whole image downloads OSRM 5.21, modifies default table parameters (because it ran into an issue otherwise), 
compiles it, gets osm data, extracts and contracts it, then gets Python dependencies and compiles the bindings. This operation will take time the first time, while later builds will be much faster (as we assume new builds might only change python scripts rather than routing dependencies).

Within this folder (dkroutingtool) run: 

`sh s_build_docker_dev.sh`


### Running Model
You can run the image interactively with the following:
 
`sh local_start.sh`

Once inside the container,  you have access to the application. The tool requires 3 data files, these files must be stored in the `local_data` directory prior to building the docker image. They must also have the same name as the files found in the github repo.

You can use a Jupyter Notebook once inside the container by typing
`sh manual.sh`

You can also interact with the software in other ways (as follows).

You can execute the routing by typing:

`/opt/conda/bin/python main_application.py --local`

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

## Other Options

### Running the Manual Update (Dev)
Download `manual_routes_edit.xlsx` file from the docker container, edit as needed and copy back into the docker container.
Then get into the docker container and run: 

`opt/conda/bin/python main_application.py --local --manual`

<br>
<br>

------------------------------------------------------------------------------
