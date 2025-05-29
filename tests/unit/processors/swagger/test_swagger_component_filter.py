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
