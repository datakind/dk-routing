"""Simple Flask API stub.

 /route
 Currently runs the route optimization and returns the solution text

"""

import time
from flask import Flask
from run_routing import run_routing_from_config
from config.config_manager import ConfigManager, GPSInputPaths, ConfigFileLocations
from output.route_solution_data import SolutionOutput


app = Flask(__name__)
PORT = 5001

@app.route('/route', methods=['POST'])
def route():
    root_dir = './'
    config_manager = ConfigManager.load(
        ConfigFileLocations(
            routing_config_file=f"{root_dir}/data/config.json",
            build_parameters_file=f"{root_dir}build_parameters.yml",
            gps_input_files=GPSInputPaths(
                gps_file=f"{root_dir}data/customer_data.xlsx",
                custom_header_file=f"{root_dir}data/custom_header.yaml",
                gps_extra_input_file=f"{root_dir}data/extra_points.csv"
            ),
            manual_edits_input_files=None
        )
    )
    solution_data, vis_data = run_routing_from_config(config_manager)
    # TODO: come up with better way to serialize this data.
    solution_output = SolutionOutput(solution_data)
    solution_txt = solution_output.serialize_solution()

    # Return the solution text.
    return {"solution": solution_txt}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT)