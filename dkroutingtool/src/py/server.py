import main_application
import fastapi
import uvicorn
from fastapi import File, UploadFile
from typing import List
import glob
from fastapi.responses import FileResponse
import shutil


app = fastapi.FastAPI()


@app.post('/provide_files')
def provide_files(files: List[UploadFile] = File(...)):
    for file in files:
        contents = file.file.read()
        print(contents)
        with open(f'/data/{file.filename}', 'wb') as f:
            f.write(contents)
        file.file.close()
    return {'message': 'uploaded'}


@app.get('/get_solution')
async def get_solution():
    main_application.args.cloud = False
    main_application.main()
    return {'message': 'done'}


@app.get('/download')
def download():
    most_recent = sorted(glob.glob('/WORKING_DATA_DIR/output_data/*'))[-1]
    print(most_recent)
    name= 'server_output'
    shutil.make_archive(name, 'zip', most_recent)
    name = name + '.zip'
    return FileResponse(path=name, filename=name, media_type='application/zip')


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)