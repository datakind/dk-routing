cmake_minimum_required(VERSION 3.15)

project(osrmbindings C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE MATCHES Debug)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(PkgConfig REQUIRED)
pkg_check_modules(OSRM REQUIRED libosrm)

find_package(Boost REQUIRED COMPONENTS
    thread
    system
    filesystem
    iostreams
    program_options
    regex
    date_time)

find_package(fmt REQUIRED 
    PATHS /opt/fmt/lib/cmake/fmt 
    NO_DEFAULT_PATH 
    NO_SYSTEM_ENVIRONMENT_PATH
    NO_CMAKE_SYSTEM_PATH)

add_subdirectory(pybind11)

pybind11_add_module(osrmbindings example.cpp)

target_link_libraries(osrmbindings PRIVATE
    pybind11::headers
    -Wl,--whole-archive
    ${OSRM_STATIC_LIBRARIES}
    /opt/fmt/lib/libfmt.a
    -Wl,--no-whole-archive
    ${OSRM_LIBRARIES}
    Boost::thread
    Boost::system
    Boost::filesystem
    Boost::iostreams
    Boost::program_options
    Boost::regex
    Boost::date_time)
    
target_include_directories(osrmbindings PRIVATE
    ${OSRM_INCLUDE_DIRS}
    /usr/local/include
    /opt/fmt/include
    /opt/bindings/include
    include)

target_link_directories(osrmbindings PRIVATE ${OSRM_LIBRARY_DIRS})

target_compile_options(osrmbindings PRIVATE ${OSRM_CFLAGS_OTHER})