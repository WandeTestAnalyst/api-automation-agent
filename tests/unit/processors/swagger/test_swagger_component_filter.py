import yaml
from src.processors.swagger import APIComponentsFilter


def test_filter_on_used_schemas():

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml = components_filter.filter_components(spec)
    filtered_yaml_dict = yaml.safe_load(filtered_yaml)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]

    assert filtered_yaml_dict["components"]["schemas"]["Item"] == {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }


def test_filter_on_unused_schemas():

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml = components_filter.filter_components(spec)
    filtered_yaml_dict = yaml.safe_load(filtered_yaml)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


# def test_filter_on_multiple_used_schemas():
#     assert False, "This test is not implemented yet"


# def test_filter_on_multiple_unused_schemas():
#     assert False, "This test is not implemented yet"


# def test_filter_on_no_schemas():
#     assert False, "This test is not implemented yet"


# def test_filter_on_empty_spec():
#     assert False, "This test is not implemented yet"


# def test_filter_on_no_components():
#     assert False, "This test is not implemented yet"
