build:
	sh s_build_docker_dev.sh

interact:
	docker run --name server --rm --network host -it dkroutingtool:dev bash

run_and_serve:
	docker run --name server --network host -d --rm dkroutingtool:dev /opt/conda/bin/python src/py/server.py

serve:
	/opt/conda/bin/python /src/py/server.py &

test: 
	/opt/conda/bin/python /src/tests/end_to_end/test_runner.py

dockergui:
	cd src/py/ui && docker build -t dashboard -f dashboard.dockerfile . 
	docker run --name dashboard --network host -d --rm dashboard:latest

gui:
	cd src/py/ui && streamlit run dashboard.py

#go to http://localhost:8501/ in your browser and it should work
demo: run_and_serve dockergui