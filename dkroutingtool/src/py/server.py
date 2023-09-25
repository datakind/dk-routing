import main_application
import fastapi
import uvicorn
from fastapi import File, UploadFile
from typing import List
import glob
from fastapi.responses import FileResponse
import shutil


app = fastapi.FastAPI()

def find_most_recent_output():
    most_recent = sorted(glob.glob('/WORKING_DATA_DIR/output_data/*'))[-1]
    return most_recent

@app.post('/provide_files')
def provide_files(files: List[UploadFile] = File(...)):
    for file in files:
        contents = file.file.read()
        print(contents)
        with open(f'/data/{file.filename}', 'wb') as f:
            f.write(contents)
        file.file.close()
    return {'message': 'Uploaded'}


@app.get('/get_solution')
def get_solution():
    main_application.args.cloud = False
    main_application.args.manual_mapping_mode = False
    main_application.args.manual_input_path = None

    main_application.main()
    return {'message': 'Done'}


@app.post('/adjust_solution')
def get_solution(files: List[UploadFile] = File(...)):
    most_recent = find_most_recent_output()
    print(most_recent)

    for file in files:
        contents = file.file.read()
        print(contents)
        with open(f'{most_recent}/manual_edits/{file.filename}', 'wb') as f:
            f.write(contents)
        file.file.close()

    main_application.args.cloud = False
    main_application.args.manual_mapping_mode = True
    main_application.args.manual_input_path = f'{most_recent}/manual_edits'
    main_application.main()
    return {'message': 'Manual solution updated, please download again'}


@app.get('/download')
def download():
    most_recent = find_most_recent_output()
    print(most_recent)
    name= 'server_output'
    shutil.make_archive(name, 'zip', most_recent)
    name = name + '.zip'
    return FileResponse(path=name, filename=name, media_type='application/zip')


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)