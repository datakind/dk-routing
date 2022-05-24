#!/bin/bash
export PYTHONPATH=py-lib:src/py

test_identical () {
  DIFF=`diff -q $1 $2`
  RED='\033[0;31m'
  NC='\033[0m' # No Color
  GREEN='\033[0;32m'
  if [ ! -f $1 ]
  then
      echo -e "${RED}test failed: $1 does not exist${NC}"
      return 1
  fi
  if [ ! -f $2 ]
  then
      echo -e "${RED}test failed: $1 does not exist${NC}"
      return 1
  fi

  if [ "$DIFF" ]; then
    echo -e "${RED}test failed: $1 differs${NC}"
  else
    echo -e "${GREEN}test succeeded: $1 matches${NC}"
  fi

}

# Test 1
/opt/conda/bin/python src/py/main_application.py --local
test_identical 'solution.txt' 'src/tests/end_to_end/expected_results/test1/solution.txt'
test_identical 'route_geojson.geojson' 'src/tests/end_to_end/expected_results/test1/route_geojson.geojson'
test_identical 'node_geojson.geojson' 'src/tests/end_to_end/expected_results/test1/node_geojson.geojson'
test_identical 'manual_edits/clean_gps_points.csv' 'src/tests/end_to_end/expected_results/test1/manual_edits/clean_gps_points.csv'
test_identical 'manual_edits/manual_vehicles.csv' 'src/tests/end_to_end/expected_results/test1/manual_edits/manual_vehicles.csv'
# We don't test instructions.txt or manual_routes_edits.xlsx because they appear to be nondeterministic
# test_identical 'instructions.txt' 'src/tests/integration/expected_results/test1/instructions.txt'
# test_identical 'manual_edits/manual_routes_edits.xlsx' 'src/tests/end_to_end/expected_results/test1/manual_edits/manual_routes_edits.xlsx'