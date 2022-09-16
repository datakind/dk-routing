import glob 
import datetime
import shutil

def upload_results(cloud_client, scenario='input', manual=False):
    client = cloud_client
    file_manager = cloud_client.file_manager

    output_time = datetime.datetime.utcnow().isoformat().split(".")[0]

    # Create archive with output.
    if manual:
        shutil.make_archive(f"{output_time}-{scenario}-manual", "zip", file_manager.root_output_path)
        # Upload to zip file with manual extension.
        to_upload = f"{output_time}-{scenario}-manual.zip"
        client.upload_data(to_upload, "output")
    else:
        shutil.make_archive(f"{output_time}-{scenario}", "zip", file_manager.root_output_path)
        # Upload to zip file.
        to_upload = f"{output_time}-{scenario}.zip"
        client.upload_data(to_upload, "output")

        # Additionally, upload manual edit files to separate folder for easy editing.
        manual_filenames = []
        manual_edits_path = file_manager.make_path(
            file_manager.output_config.manual_edit_route_xlsx_path
        )
        manual_vehicle_path = file_manager.make_path(
            file_manager.output_config.manual_edit_vehicles_path
        )
        manual_edit_gps_path = file_manager.make_path(
            file_manager.output_config.manual_edit_gps_path
        )
        manual_filenames.append(manual_edits_path)
        manual_filenames.append(manual_vehicle_path)
        manual_filenames.append(manual_edit_gps_path)

        for manual_filename in manual_filenames:
            # strip directories from file
            name_only = manual_filename.name
            client.upload_data(str(manual_filename), f"{scenario}-manual-input", filename=name_only)

