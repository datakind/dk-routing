#!/usr/bin/env bash
docker run -it  \
    -e CLOUDCONTEXT=$(yq e '.Run.storage-context' build_parameters.yml) \
    -e AWSACCESSKEYID=$(yq e '.Run.aws.accesskeyid' build_parameters.yml) \
    -e AWSSECRETACCESSKEY=$(yq e '.Run.aws.secretkey' build_parameters.yml) \
    -e AWSBUCKETNAME=$(yq e '.Run.aws.s3bucketname' build_parameters.yml) \
    -e GDRIVEROOTFOLDERID=$(yq e '.Run.gdrive.root_folder_id' build_parameters.yml) \
    -e GDRIVECUSTOMERFILEID=$(yq e '.Run.gdrive.customer_data_id' build_parameters.yml) \
    -e GDRIVEEXTRAFILEID=$(yq e '.Run.gdrive.facility_data_id' build_parameters.yml) \
    -p 8080:8080 \
    -p 5001:5001 \
    dkroutingtool:dev bash
