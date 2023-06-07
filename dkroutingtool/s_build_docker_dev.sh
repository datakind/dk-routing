#!/usr/bin/env bash

FILEPATH=$(yq '.Build."osm-data"."geofabrik-url"' build_parameters.yml)
FILENAME=$(basename $FILEPATH)
SHORTFILENAME=${FILENAME%%.*}

docker build --platform=linux/amd64 --memory=8g --build-arg osm_download_url=$FILEPATH --build-arg osm_filename_arg=$SHORTFILENAME -f Dockerfile.dev -t dkroutingtool:dev .

