# Using the GUI

You can install python (3.7+) locally then pip install streamlit to run the GUI with
`streamlit run dashboard.py`

You will also need to configure the address of the CART server in dashboard.py.

You can also build the dockerfile and execute it:
`docker run --network host dashboard:latest`

One benefit of running the dashboard locally is that the application will download all useful files directly to the current working directory such as gpx tracks, spreadsheets, etc. 