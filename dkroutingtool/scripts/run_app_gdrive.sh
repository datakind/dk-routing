export CLOUDCONTEXT=gdrive
export GDRIVECUSTOMERFILEID=
export GDRIVEEXTRAFILEID=
export GDRIVEROOTFOLDERID=
export GDRIVECREDSFILE=src/creds/gdrive_creds.json

# Local mode
#/opt/conda/bin/python src/py/main_application.py --input test_scenario --local

# Local Manual Mode
#/opt/conda/bin/python src/py/main_application.py --input test_scenario --manual_input_path WORKING_DATA_DIR/output_data/test_scenario_2022_09_16_19_38/manual_edits --local

# Cloud mode
/opt/conda/bin/python src/py/main_application.py --input test_scenario

# Cloud manual mode
#/opt/conda/bin/python src/py/main_application.py --input test_scenario --manual

