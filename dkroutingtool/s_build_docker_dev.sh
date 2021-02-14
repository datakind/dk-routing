#!/usr/bin/env bash

FILEPATH=$(yq e '.Build.osm-data.geofabrik-url' build_parameters.yml)
FILENAME=$(basename $FILEPATH)
SHORTFILENAME=${FILENAME%%.*}
docker build --build-arg osm_download_url=$FILEPATH --build-arg osm_filename_arg=$SHORTFILENAME -f Dockerfile.dev -t dkroutingtool:dev .

