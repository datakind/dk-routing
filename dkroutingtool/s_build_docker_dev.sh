#!/usr/bin/env bash

# FILEPATH=$(yq '.Build."osm-data"."geofabrik-url"' build_parameters.yml)
# FILENAME=$(basename $FILEPATH)
# SHORTFILENAME=${FILENAME%%.*}

docker build --platform=linux/amd64 --memory=8g --build-arg osm_download_url=https://download.geofabrik.de/europe/monaco-latest.osm.pbf --build-arg osm_filename_arg=monaco-latest -f Dockerfile.dev -t dkroutingtool:dev .

