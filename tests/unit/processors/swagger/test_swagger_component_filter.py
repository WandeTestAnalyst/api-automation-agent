import yaml
from src.processors.swagger import APIComponentFilter


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

    filter = APIComponentFilter()
    filtered_yaml = filter.filter(spec)

    assert "components" in filtered_yaml
    assert "schemas" in filtered_yaml["components"]

    filtered_yaml_dict = yaml.safe_load(filtered_yaml)
    assert filtered_yaml_dict["components"]["schemas"]["Item"] == {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }
