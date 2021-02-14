#include "osrm/match_parameters.hpp"
#include "osrm/nearest_parameters.hpp"
#include "osrm/route_parameters.hpp"
#include "osrm/table_parameters.hpp"
#include "osrm/trip_parameters.hpp"

#include "osrm/coordinate.hpp"
#include "osrm/engine_config.hpp"
#include "osrm/json_container.hpp"

#include "util/json_renderer.hpp"

#include "osrm/osrm.hpp"
#include "osrm/status.hpp"

#include <exception>
#include <iostream>
#include <string>
#include <utility>

#include <cstdlib>

#include <pybind11/pybind11.h>

osrm::OSRM* osrm_machine;

void initialize(std::string filepath){
    osrm::EngineConfig config;    
    // Configure based on a .osrm base path, and no datasets in shared mem from osrm-datastore
    config.storage_config = {filepath};
    config.use_shared_memory = false;

    // We support two routing speed up techniques:
    // - Contraction Hierarchies (CH): requires extract+contract pre-processing
    // - Multi-Level Dijkstra (MLD): requires extract+partition+customize pre-processing
    //
    //config.algorithm = EngineConfig::Algorithm::MLD;
    config.algorithm = osrm::EngineConfig::Algorithm::CH;

    osrm_machine = new osrm::OSRM(config);
}

std::string route(pybind11::list longitudes, pybind11::list latitudes)
{
    osrm::RouteParameters params;

    for (int index = 0; index < longitudes.size(); index++) {
        float longitude = longitudes[index].cast<float>();
        float latitude = latitudes[index].cast<float>();
        params.coordinates.push_back({osrm::util::FloatLongitude{longitude}, osrm::util::FloatLatitude{latitude}});
    }
    
    params.steps = true;

    params.overview = osrm::RouteParameters::OverviewType::Full;

    params.geometries = osrm::RouteParameters::GeometriesType::GeoJSON;

    osrm::json::Object result;

    const auto status = osrm_machine->Route(params, result);

    if (status == osrm::Status::Ok)
    {
        std::ostringstream buf;
        osrm::util::json::render(buf, result);
        auto stringified_json = buf.str();
     
        return stringified_json;
    }
    else if (status == osrm::Status::Error)
    {
        const auto code = result.values["code"].get<osrm::json::String>().value;
        const auto message = result.values["message"].get<osrm::json::String>().value;

        std::cout << "Code: " << code << "\n";
        std::cout << "Message: " << code << "\n";
        return message;
    }
}

std::string nearest(float longitude, float latitude)
{
    osrm::NearestParameters params;

    params.coordinates.push_back({osrm::util::FloatLongitude{longitude}, osrm::util::FloatLatitude{latitude}});

    osrm::json::Object result;

    const auto status = osrm_machine->Nearest(params, result);

    if (status == osrm::Status::Ok)
    {
    
        std::ostringstream buf;
        osrm::util::json::render(buf, result);
        auto stringified_json = buf.str();

        return stringified_json;
    } else if (status == osrm::Status::Error) 
    {
        const auto message = result.values["message"].get<osrm::json::String>().value;
        return message;
    }
}

std::string table(pybind11::list longitudes, pybind11::list latitudes)
{
    osrm::TableParameters params;

    for (int index = 0; index < longitudes.size(); index++) {
        float longitude = longitudes[index].cast<float>();
        float latitude = latitudes[index].cast<float>();
        params.coordinates.push_back({osrm::util::FloatLongitude{longitude}, osrm::util::FloatLatitude{latitude}});
    }
    osrm::json::Object result;

    const auto status = osrm_machine->Table(params, result);

    if (status == osrm::Status::Ok)
    {
        std::ostringstream buf;
        osrm::util::json::render(buf, result);
        auto stringified_json = buf.str();
     
        return stringified_json;
    }
    else if (status == osrm::Status::Error)
    {
        const auto code = result.values["code"].get<osrm::json::String>().value;
        const auto message = result.values["message"].get<osrm::json::String>().value;

        std::cout << "Code: " << code << "\n";
        std::cout << "Message: " << code << "\n";
        
        return message;
    }
}


namespace py = pybind11;

PYBIND11_MODULE(osrmbindings, m) {
    m.doc() = "OSRM Bindings";

    m.def("route", &route, "Route binding");
    m.def("table", &table, "Table binding");
    m.def("nearest", &nearest, "Nearest binding");
    m.def("initialize", &initialize, "Initialize engine, necessary before the other functions are usable");
}