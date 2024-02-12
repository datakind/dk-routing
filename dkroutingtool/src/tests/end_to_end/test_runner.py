import zipfile
import requests
import time
import subprocess

host_url = 'http://localhost:5001'

def download_solution(solution_path):
    response = requests.get(f'{host_url}/download')
    solution_zip = response.content

    with open(f'solution_files.zip', 'wb') as f:
        f.write(solution_zip)
    
    with zipfile.ZipFile(f'solution_files.zip', 'r') as zipped:
        zipped.extractall(f'solution_files/')
    
    with open(f'solution_files/{solution_path}', 'r') as solution_txt:
        solution = solution_txt.read().replace('\n', '  \n')
    
    return solution

def request_solution():
    response = requests.get(f'{host_url}/get_solution')
    solution = download_solution(solution_path='solution.txt')
    return solution

def does_it_work_at_all():
    start = time.time()
    solution = request_solution()
    assert len(solution) > 1, "The solution file is empty"
    print('Success:', time.time()-start, 'seconds')

subprocess.Popen("/opt/conda/bin/python /src/py/server.py &", shell=True)
time.sleep(10)
does_it_work_at_all()

