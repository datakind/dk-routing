

def main(routes_for_mapping_viz, vehicles_viz, metrics):
    # print('routes_for_mapping')
    # print(routes_for_mapping_viz)
    # print('vehicles')
    # print([(i, veh.name) for i, veh in vehicles_viz.items()])
    # print('metrics')
    # print(metrics)

    for i, veh in vehicles_viz.items():
        (zone, veh_type, capacity) = veh.name.split(',')
        load = metrics[i]['load'].strip()
        dist = metrics[i]['dist'].strip()
        time = metrics[i]['time'].strip()

        print([zone, veh_type, load, dist, time])