from dependency_injector import containers, providers

from src.processors.postman_processor import PostmanProcessor
from src.processors.swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    FileLoader,
)
from src.processors.swagger_processor import SwaggerProcessor
from src.services.file_service import FileService


class ProcessorsAdapter(containers.DeclarativeContainer):
    """Adapter for processor components."""

    file_service = providers.Factory(FileService)

    file_loader = providers.Factory(FileLoader)
    splitter = providers.Factory(APIDefinitionSplitter)
    merger = providers.Factory(APIDefinitionMerger)

    swagger_processor = providers.Factory(
        SwaggerProcessor, file_loader=file_loader, splitter=splitter, merger=merger
    )
    postman_processor = providers.Factory(PostmanProcessor, file_service=file_service)
