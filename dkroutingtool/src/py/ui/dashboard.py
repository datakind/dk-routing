import requests
import datetime
import streamlit as st
import zipfile
import streamlit.components.v1 as components

st.set_page_config(page_title='Container-based Action Routing Tool (CART)', layout="wide")

host_url = 'http://localhost:5001'

def download_solution(solution_path, map_path):
    timestamp = datetime.datetime.now().strftime(format='%Y%m%d-%H-%M-%S')
    response = requests.get(f'{host_url}/download')

    with open(f'solution_files_{timestamp}.zip', 'wb') as f:
        f.write(response.content)
    
    with zipfile.ZipFile(f'solution_files_{timestamp}.zip', 'r') as zipped:
        zipped.extractall(f'solution_files_{timestamp}/')
    
    with open(f'solution_files_{timestamp}/{solution_path}', 'r') as solution_txt:
        solution = solution_txt.read().replace('\n', '  \n')
    
    with open(f'solution_files_{timestamp}/{map_path}', 'r') as map_html:
        map = map_html.read()

    return solution, map

def request_solution():
    response = requests.get(f'{host_url}/get_solution')
    solution, map = download_solution(solution_path='solution.txt', map_path='/maps/route_map.html')

    return solution, map

def adjust(adjusted_file):
    headers = {
    'accept': 'application/json'
    # 'Content-Type': 'multipart/form-data',
    }

    files = {'files': adjusted_file[0]} # We only expect one
    response = requests.post(f'{host_url}/adjust_solution', headers=headers, files=files)
    if response.ok:
        message = "Adjusted routes successfully uploaded"
    else: 
        message = 'Error, verify the adjusted routes file or raise an issue'
    
    solution, map = download_solution(solution_path='manual_edits/manual_solution.txt', map_path='maps/trip_data.html')
    return message, solution, map

def upload_data(files_from_streamlit):
    files = [('files', file) for file in files_from_streamlit]

    headers = {
        'accept': 'application/json'
        #'Content-Type': 'multipart/form-data'
    }

    # if you wanted to not select them everytime?
    #files = [
    #    ('files', open('local_data/config.json', 'rb')),
    #    ('files', open('local_data/extra_points.csv', 'rb')),
    #    ('files', open('local_data/customer_data.xlsx', 'rb'))]

    response = requests.post(f'{host_url}/provide_files', headers=headers, files=files)
    if response.ok:
        return 'All files uploaded successfully'
    else:
        return 'Error, please verify your files or raise an issue'

def main():
    st.header('Container-based Action Routing Tool (CART)')

    uploaded_files = st.file_uploader('Upload all required files (config, locations, extra points)', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        response = upload_data(uploaded_files)
        st.write(response)

    st.write('Calculating a solution will take up to twice the amount of time specified by the config file')
    
    solution_requested = st.button('Click here to calculate routes')
    
    if solution_requested:
        with st.spinner('Computing routes, please wait...'):
            solution, map = request_solution()
        components.html(map, height = 800)
        st.write(solution)
    
    st.subheader('Optional route adjustments')
    uploaded_files = st.file_uploader('If adjustments are made in the manual_edits spreadsheet, upload it here to get adjusted solutions', accept_multiple_files=True)
    if len(uploaded_files) > 0:
        with st.spinner('Adjusting routes, please wait...'):
            response, solution, map = adjust(uploaded_files)
        st.write(response)
        components.html(map, height = 800)
        st.write(solution)

if __name__ == '__main__':
    main()