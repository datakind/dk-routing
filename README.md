# Container-based Action Routing Tool (CART)

[![Build and test](https://github.com/datakind/dk-routing/actions/workflows/docker-actions.yml/badge.svg)](https://github.com/datakind/dk-routing/actions/workflows/docker-actions.yml)


A tool that enables the planning of container pickup and dropoff at many locations with customizables vehicles (speed, allowed roadways, capacity, etc.)

User instructions are at https://github.com/datakind/dk-routing/blob/main/dkroutingtool/README.md

Configuration manual is at https://docs.google.com/document/d/1iOlXQk6_ElM_LdawJPREHNjVkv_2Qajam3is2hm5zyM

Developed by volunteers and DataKind, formerly known as DataKind Routing Tool. The initial goal was to provide routing assistance for container-based sanitation organizations and we're open sourcing the tool to make sure it can reach many more use cases and organizations.

# Why would it be useful for me?

Here are some features supported by the current release.

* Routes through hundreds or thousands of locations in minutes
* Minimizes either time or distance across trips (with steep elevation changes as an experimental optimization)
* Specific time windows per area or per location are respected
* Configuration of multiple different vehicles with different speeds, allowable roads and capacities via OSRM profiles
* Detailed maps of the trips in html files
* Possibility of editing the routes via spreadsheets to reorder locations or put a location onto a different trip
* Exports GPX tracks to be used in turn-by-turn navigation tools (e.g. OSM Automated Navigation Directions at https://osmand.net/) 

# What does it look like?

An example of a map with all planned trips:
![image](https://github.com/datakind/dk-routing/assets/1616150/361cceb3-ea1d-498d-9ba0-d5c46ff8570b)

The spreadsheet allowing reordering of the locations:
![image](https://github.com/datakind/dk-routing/assets/1616150/ddb0c63b-7454-46b1-93b7-73a74fc32ec5)

And a sample solution that provides relevant metrics:
> ...  
> Route ID red-7, West , 3wheeler, Cap 50:  
> waste_basket -> 3365391469 -> 2068942499 -> 7778351995 -> 4056395683 -> 995175662 -> 7778324711 -> 7829947085 -> 4472447170 -> 2622751934 -> 1794111136 -> 7820195264 -> 7798179688 -> 267901435 -> 321647302 -> West-UNLOAD  
> Distance of the route: 4.926km  
> Load of the route: 45  
> Time of the route: 47min  
>
> Total:  
> Distance of all routes: 38.422km  
> Time of all routes: 311min  

# Contact

Maintained by Zebreu (Sebastien Ouellet), feel free to open issues for any question or clarification.
