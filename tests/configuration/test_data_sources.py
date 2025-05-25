import pytest
from dependency_injector import containers, providers

from src.configuration.data_sources import DataSource, get_processor_for_data_source
from src.container import Container
from src.configuration.config import Config, Envs
from src.processors.swagger_processor import SwaggerProcessor
from src.processors.postman_processor import PostmanProcessor


def _create_container() -> Container:
    config_adapter = containers.DynamicContainer()
    config_adapter.config = providers.Object(Config(env=Envs.DEV))
    container = Container(config_adapter=config_adapter)
    return container


def test_get_processor_for_swagger():
    container = _create_container()
    processor = get_processor_for_data_source(DataSource.SWAGGER, container)
    assert isinstance(processor, SwaggerProcessor)


def test_get_processor_for_postman():
    container = _create_container()
    processor = get_processor_for_data_source(DataSource.POSTMAN, container)
    assert isinstance(processor, PostmanProcessor)


def test_get_processor_for_unsupported_value():
    container = _create_container()
    with pytest.raises(ValueError):
        get_processor_for_data_source(DataSource.NONE, container)
