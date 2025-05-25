import yaml
from src.processors.swagger import APIDefinitionSplitter, APIDefinitionMerger
from src.processors.swagger_processor import SwaggerProcessor
from src.services.file_service import FileService
from src.configuration.config import Config
from src.models import APIPath, APIVerb


def test_swagger_processor_rebuilds_full_definition():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/api/v1/items": {
                "get": {"responses": {"200": {"description": "ok"}}}
            }
        },
    }

    splitter = APIDefinitionSplitter()
    base_yaml, parts = splitter.split(spec)
    merger = APIDefinitionMerger()
    merged = merger.merge(parts)

    processor = SwaggerProcessor(
        file_loader=FileService(),
        splitter=splitter,
        merger=merger,
        file_service=FileService(),
        config=Config(),
    )
    processor.base_yaml = base_yaml

    api_path = next(p for p in merged if isinstance(p, APIPath))
    full_yaml = processor.get_api_path_content(api_path)
    reconstructed = yaml.safe_load(full_yaml)

    assert reconstructed["openapi"] == "3.0.0"
    assert "/api/v1/items" in reconstructed["paths"]
