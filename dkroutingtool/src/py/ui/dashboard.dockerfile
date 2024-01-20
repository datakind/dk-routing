FROM continuumio/miniconda3:4.12.0

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /src/app

COPY dashboard.py /src/app

CMD streamlit run /src/app/dashboard.py --browser.gatherUsageStats=False --theme.base="dark"