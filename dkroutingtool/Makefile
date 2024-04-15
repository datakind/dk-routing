build:
	sh s_build_docker_dev.sh

interact:
	docker run --name server --rm -p 5001:5001 -it ghcr.io/datakind/dk-routing:main bash

run_and_serve:
	docker run --name server -p 5001:5001 -d --rm ghcr.io/datakind/dk-routing:main /opt/conda/bin/python src/py/server.py

serve:
	/opt/conda/bin/python /src/py/server.py &

test: 
	/opt/conda/bin/python /src/tests/end_to_end/test_runner.py

dockergui:
	cd src/py/ui && docker build -t dashboard -f dashboard.dockerfile . 
	docker run -e SERVER_HOST='localhost' --name dashboard --network host -d --rm dashboard:latest

gui:
	export SERVER_HOST='localhost' && cd src/py/ui && streamlit run dashboard.py

#go to http://localhost:8501/ in your browser and it should work
demo:
	cd src/py/ui && docker build -t dashboard -f dashboard.dockerfile .
	docker run \
		--add-host=host.docker.internal:host-gateway \
		--name server \
		-p 5001:5001 \
		-d \
		--rm \
		ghcr.io/datakind/dk-routing:main \
		/opt/conda/bin/python src/py/server.py
	docker run \
		-e SERVER_HOST='host.docker.internal' \
		--add-host=host.docker.internal:host-gateway \
		--name dashboard \
		-p 8501:8501 \
		-d \
		--rm \
		dashboard:latest
