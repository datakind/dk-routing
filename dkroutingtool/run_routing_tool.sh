docker run --name routing_tool dkroutingtool:dev && 
docker cp routing_tool:/maps /home/zebreu/routing_output/ &&
docker cp routing_tool:/route_geojson.geojson /home/zebreu/routing_output/ &&
docker cp routing_tool:/node_geojson.geojson /home/zebreu/routing_output/ &&
docker cp routing_tool:/solution.txt /home/zebreu/routing_output &&
docker container prune --force