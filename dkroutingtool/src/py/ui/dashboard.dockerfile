FROM continuumio/miniconda3:4.12.0

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /opt/src/app

COPY dashboard.py /opt/src/app

EXPOSE 8501

CMD streamlit run /opt/src/app/dashboard.py --browser.gatherUsageStats=False --theme.base="dark" --server.address=0.0.0.0 --server.runOnSave=True --server.headless=True --server.fileWatcherType="poll"