FROM osrm-base

ARG osm_download_url

ARG osm_filename_arg

ENV osm_filename $osm_filename_arg

RUN wget $osm_download_url

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py37_4.8.3-Linux-x86_64.sh

RUN bash Miniconda3-py37_4.8.3-Linux-x86_64.sh -b -p /opt/conda

ENV PATH="${PATH}:/opt/conda/bin"

RUN mkdir osrm-backend/defaultprofiles

RUN mv osrm-backend/profiles/*.lua osrm-backend/defaultprofiles/

COPY /veh_profiles/* osrm-backend/profiles/

COPY build_parameters.yml .

COPY build_vehicle_profiles.py .

RUN /opt/conda/bin/python build_vehicle_profiles.py

COPY requirements.txt .

RUN /opt/conda/bin/python -m pip install -r requirements.txt

RUN conda install cffi==1.12.2

RUN apt-get -y install vim

RUN git clone -b v2.3 https://github.com/pybind/pybind11.git

RUN cp -r osrm-backend/include osrm-backend/example


RUN mkdir data

RUN mkdir data/gps_data_clean

RUN mkdir data/time_and_dist_matrices


COPY /c_binding_resources/CMakeLists.txt .

COPY /c_binding_resources/python_bindings.cpp example.cpp

RUN cd osrm-backend/example && mv ../../CMakeLists.txt . && mv ../../example.cpp .

RUN cp -r pybind11 osrm-backend/example/

RUN cd osrm-backend/example && mkdir build && cd build && cmake .. && make

RUN mkdir -p py-lib

RUN mv osrm-backend/example/build/osrmbindings.cpython-37m-x86_64-linux-gnu.so py-lib

RUN apt-get update

RUN apt-get -y install curl gnupg2

RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -

RUN apt-get -y install nodejs

RUN npm install osrm-text-instructions

COPY /local_data/custom_header.yaml data/.

RUN mkdir maps

RUN mkdir manual_edits

RUN mkdir manual_edits/maps

COPY src src

ENV PYTHONPATH "${PYTHONPATH}:./py-lib:/src/python"

ENTRYPOINT ["/opt/conda/bin/python", "src/py/main_application.py"]
