"""Tests RoutingConfig validtator

TODO: add tests for more syntax erorrs
TODO: add tests for validate_against_node_data
"""
from routing_configuration import RoutingConfig

TEST_CONFIG1 = {
    "zone_configs": [
        {
            "optimized_region": ["West"],
            "Start_Point": ["waste_basket"],
            "End_Point": ["West-UNLOAD"],
            "load_time": 2.5,
            "trips_vehicle_profile": [["3wheeler", 50]],
            "enable_unload": False,
            "unload_vehicles": [],
            "hours_allowed": 5
        }
    ]
}

TEST_CONFIG2 = {
    "zone_configs": [
        {
            "optimized_region": ["East"],
            "Start_Point": ["waste_basket"],
            "End_Point": ["waste_basket"],
            "load_time": 8.2,
            "trips_vehicle_profile": [["3wheeler", 50]],
            "hours_allowed": 2,
            "start_time": "8:45AM",
            "enable_unload": True,
            "unload_vehicles": [
                ["3wheeler", 50, "waste_basket", "waste_basket"],
                ["3wheeler", 50, "waste_basket", "waste_basket"],
                ["3wheeler", 50, "waste_basket", "waste_basket"]
            ],
            "custom_unload_points": ["East-UNLOAD"]
        }
    ]
}

TEST_BAD_CONFIG1 = {
    "zone_configs": [
        {
            "optimized_region": ["West"],
            "Start_Point": ["waste_basket"],
            "load_time": 2.5,
            "trips_vehicle_profile": [["3wheeler", 50]],
            "enable_unload": False,
            "unload_vehicles": [],
            "hours_allowed": 5
        }
    ]
}

TEST_BAD_CONFIG2 = {
    "zone_configs": [
        {
            "optimized_region": ["East"],
            "Start_Point": ["waste_basket"],
            "End_Point": ["waste_basket"],
            "load_time": 8.2,
            "trips_vehicle_profile": [["3wheeler", 50]],
            "hours_allowed": 2,
            "start_time": "8:45AM",
            "enable_unload": True,
            "unload_vehicles": [],
            "custom_unload_points": ["East-UNLOAD"]
        }
    ]
}

def test_local_data_routing_config():
    config = RoutingConfig.from_file('../../local_data/config.json')
    errors = config.validate()
    assert errors == []

def test_simple_config_no_unload():
    config = RoutingConfig(TEST_CONFIG1)
    errors = config.validate()
    assert errors == []

def test_simple_config_with_unload():
    config = RoutingConfig(TEST_CONFIG2)
    errors = config.validate()
    assert errors == []

def test_bad_config_no_end_point():
    config = RoutingConfig(TEST_BAD_CONFIG1)
    errors = config.validate()
    assert len(errors) > 0

def test_bad_config_no_vehicles():
    config = RoutingConfig(TEST_BAD_CONFIG2)
    errors = config.validate()
    assert len(errors) > 0
