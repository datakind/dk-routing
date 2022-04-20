import glob 
import datetime
import shutil



def main(cloud_client, filenames=None, manual_filenames=None, scenario='input',
         manual=False):
    client = cloud_client

    output_time = datetime.datetime.utcnow().isoformat().split(".")[0]

    if manual:
        shutil.copy(
            "/manual_edits/manual_solution.txt", "/manual_edits/maps/manual_solution.txt") 

        shutil.make_archive(f"{output_time}-{scenario}-manual", "zip", "/manual_edits/maps/")    

        to_upload = f"{output_time}-{scenario}-manual.zip"
        client.upload_data(to_upload, "output")

    else:
        if filenames is None:
            shutil.copy("solution.txt", "/maps/solution.txt")
            shutil.copy("instructions.txt", "/maps/instructions.txt")
            shutil.copy("data/config.json", "/maps/config.json")
            shutil.copy("data/gps_data_clean/dropped_flagged_gps_points.csv", "/maps/dropped_flagged_gps_points.csv")
            shutil.copy("/manual_edits/manual_routes_edits.xlsx", "/maps/manual_routes_edits.xlsx")

        shutil.make_archive(f"{output_time}-{scenario}", "zip", "/maps/")    
        
        to_upload = f"{output_time}-{scenario}.zip"
        client.upload_data(to_upload, "output")

        if manual_filenames is None:
            manual_filenames = []
            manual_filenames.extend(glob.glob("/manual_edits/*.csv"))
            manual_filenames.extend(glob.glob("/manual_edits/*.xlsx"))

        for manual_filename in manual_filenames:
            client.upload_data(manual_filename, f"{scenario}-manual-input", filename=manual_filename.split('/')[-1])

