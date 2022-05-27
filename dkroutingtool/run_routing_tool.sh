output_destination="$HOME/routing_output/"

docker run --name routing_tool dkroutingtool:dev &&
docker cp routing_tool:/maps $output_destination &&
docker cp routing_tool:/route_geojson.geojson $output_destination &&
docker cp routing_tool:/node_geojson.geojson $output_destination &&
docker cp routing_tool:/manual_edits $output_destination &&
docker cp routing_tool:/solution.txt $output_destination

docker container prune --force
