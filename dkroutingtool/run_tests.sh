#!/bin/bash

export DK_ROUTING_SOURCE=src/

pushd $DK_ROUTING_SOURCE/src/tests/ &> /dev//null
PYTHONPATH=$PYTHONPATH:$DK_ROUTING_SOURCE/py/:DK_ROUTING_SOURCE/tests/ pytest $@
tests_exit_code=$?
popd &> /dev//null
exit $tests_exit_code

