import glob 
import datetime
import shutil



def upload_results(cloud_client, scenario='input', manual=False):
    client = cloud_client
    file_manager = cloud_client.file_manager
    config_manager = cloud_client.config_manager

    output_time = datetime.datetime.utcnow().isoformat().split(".")[0]

    if manual:
        shutil.copy(
            "/manual_edits/manual_solution.txt", "/manual_edits/maps/manual_solution.txt") 

        shutil.make_archive(f"{output_time}-{scenario}-manual", "zip", "/manual_edits/maps/")    

        to_upload = f"{output_time}-{scenario}-manual.zip"
        client.upload_data(to_upload, "output")

    else:
        shutil.make_archive(f"{output_time}-{scenario}", "zip", file_manager.root_output_path)
        to_upload = f"{output_time}-{scenario}.zip"
        client.upload_data(to_upload, "output")

        manual_filenames = []
        manual_filenames.extend(glob.glob("/manual_edits/*.csv"))
        manual_filenames.extend(glob.glob("/manual_edits/*.xlsx"))

        for manual_filename in manual_filenames:
            client.upload_data(manual_filename, f"{scenario}-manual-input", filename=manual_filename.split('/')[-1])

