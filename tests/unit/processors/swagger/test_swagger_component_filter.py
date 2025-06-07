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
    filtered_yaml_dict = components_filter.filter_schemas(spec)

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
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_used_schemas():
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
            },
            "/items2/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item2"}}
                            },
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "Item2" in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_unused_schemas():
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
                "UnusedSchema2": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema2" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_used_and_unused_schemas():
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
            },
            "/items2/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item2"}}
                            },
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
                "UnusedSchema2": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "Item2" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema2" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_duplicated_schema_refs():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "summary": "Get all items",
                    "responses": {
                        "200": {
                            "description": "A list of items",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Item"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "servers": [{"url": "https://api.example.com"}],
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
            },
        },
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert len(filtered_yaml_dict["components"]["schemas"]) == 1
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_schemas_on_multiple_components():
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
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            },
            "parameters": {
                "IdParam": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            },
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            },
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    expected_filtered_spec = {
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
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
            },
            "parameters": {
                "IdParam": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            },
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            },
        },
    }
    assert filtered_yaml_dict == expected_filtered_spec


def test_filter_on_no_schemas():
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
        "servers": [{"url": "https://api.example.com"}],
        "components": {},
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert filtered_yaml_dict == spec


def test_filter_on_no_components():
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
        "servers": [{"url": "https://api.example.com"}],
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert filtered_yaml_dict == spec


def test_filter_on_nested_refs():
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
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "nestedItem": {"$ref": "#/components/schemas/NestedItem"},
                    },
                },
                "NestedItem": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "nestedItem2": {"$ref": "#/components/schemas/NestedItem2"},
                    },
                },
                "NestedItem2": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert len(filtered_yaml_dict["components"]["schemas"]) == 3
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "NestedItem" in filtered_yaml_dict["components"]["schemas"]
    assert "NestedItem2" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_unused_schemas_with_nested_refs():
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
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "nestedItem": {"$ref": "#/components/schemas/NestedItem"},
                    },
                },
                "NestedItem": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "nestedItem2": {"$ref": "#/components/schemas/NestedItem2"},
                    },
                },
                "NestedItem2": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "unusedSchema2": {"$ref": "#/components/schemas/UnusedSchema2"},
                    },
                },
                "UnusedSchema2": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert len(filtered_yaml_dict["components"]["schemas"]) == 3
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "NestedItem" in filtered_yaml_dict["components"]["schemas"]
    assert "NestedItem2" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema2" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_with_no_paths():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {"schemas": {"Item": {"type": "object", "properties": {"id": {"type": "integer"}}}}},
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert filtered["components"]["schemas"] == {}


def test_filter_with_empty_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}},
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert filtered["components"]["schemas"] == {}


def test_filter_with_only_non_schema_components():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "parameters": {
                "IdParam": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            }
        },
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert "parameters" in filtered["components"]


def test_filter_with_invalid_ref_format():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Invalid ref",
                            "content": {"application/json": {"schema": {"$ref": "InvalidRefFormat"}}},
                        }
                    }
                }
            }
        },
        "components": {"schemas": {"Item": {"type": "object"}}},
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert filtered["components"]["schemas"] == {}


def test_filter_with_deeply_nested_refs():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Nested ref",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}},
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "A": {"type": "object", "properties": {"b": {"$ref": "#/components/schemas/B"}}},
                "B": {"type": "object", "properties": {"c": {"$ref": "#/components/schemas/C"}}},
                "C": {"type": "object"},
                "Unused": {"type": "object"},
            }
        },
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert set(filtered["components"]["schemas"].keys()) == {"A", "B", "C"}


def test_filter_with_circular_refs():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Circular ref",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}},
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "A": {"type": "object", "properties": {"b": {"$ref": "#/components/schemas/B"}}},
                "B": {"type": "object", "properties": {"a": {"$ref": "#/components/schemas/A"}}},
            }
        },
    }
    components_filter = APIComponentsFilter()
    filtered = components_filter.filter_schemas(spec)
    assert set(filtered["components"]["schemas"].keys()) == {"A", "B"}
