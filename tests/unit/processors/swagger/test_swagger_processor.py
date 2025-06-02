import yaml
from src.processors.swagger import APIDefinitionSplitter, APIDefinitionMerger, APIComponentsFilter
from src.processors.swagger_processor import SwaggerProcessor
from src.services.file_service import FileService
from src.configuration.config import Config
from src.models import APIPath, APIVerb


def test_swagger_processor_rebuilds_full_path_definition():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/api/v1/items": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
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
                "Item": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                }
            }
        },
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)
    merger = APIDefinitionMerger()
    merged = merger.merge(parts)
    components_filter = APIComponentsFilter()

    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=splitter,
        merger=merger,
        components_filter=components_filter,
        file_service=FileService(),
        config=Config(),
    )
    processor.base_definition = base_yaml

    api_path = next(p for p in merged if isinstance(p, APIPath))
    full_yaml = processor.get_api_path_content(api_path)
    reconstructed = yaml.safe_load(full_yaml)

    assert "/api/v1/items" not in base_yaml
    assert "/api/v1/items" in reconstructed["paths"]

    assert "https://api.example.com" not in api_path.yaml
    assert reconstructed["openapi"] == "3.0.0"
    assert reconstructed["servers"] == [{"url": "https://api.example.com"}]
    assert reconstructed["components"]["schemas"]["Item"] == {
        "type": "object",
        "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
    }


def test_swagger_processor_rebuilds_full_verb_definition():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {"/api/v1/items": {"get": {"responses": {"200": {"description": "ok"}}}}},
        "servers": [{"url": "https://api.example.com"}],
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)
    merger = APIDefinitionMerger()
    merged = merger.merge(parts)
    components_filter = APIComponentsFilter()

    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=splitter,
        merger=merger,
        components_filter=components_filter,
        file_service=FileService(),
        config=Config(),
    )
    processor.base_definition = base_yaml

    api_verb = next(p for p in merged if isinstance(p, APIVerb))
    full_yaml = processor.get_api_verb_content(api_verb)
    reconstructed = yaml.safe_load(full_yaml)

    assert "/api/v1/items" not in base_yaml
    assert "/api/v1/items" in reconstructed["paths"]
    assert "get" in reconstructed["paths"]["/api/v1/items"]

    assert "https://api.example.com" not in api_verb.yaml
    assert reconstructed["openapi"] == "3.0.0"
    assert reconstructed["servers"] == [{"url": "https://api.example.com"}]
