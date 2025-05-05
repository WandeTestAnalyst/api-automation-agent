import json
import yaml
from typing import Dict, List, Optional, Union

from src.ai_tools.models.file_spec import FileSpec
from src.processors.api_processor import APIProcessor

from .swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    FileLoader,
    APIDefinitionLoader,
)
from ..utils.logger import Logger
import re


class SwaggerProcessor(APIProcessor):
    """Processes API definitions by orchestrating file loading, splitting, and merging."""

    def __init__(
        self,
        file_loader: FileLoader,
        splitter: APIDefinitionSplitter,
        merger: APIDefinitionMerger,
        apiDefinitionLoader: APIDefinitionLoader = None,
    ):
        """
        Initialize the SwaggerProcessor.

        Args:
            file_loader (FileLoader): Service to load API definition files.
            splitter (APIDefinitionSplitter): Service to split API definitions.
            merger (APIDefinitionMerger): Service to merge API definitions.
            apiDefinitionLoader (APIDefinitionLoader): Service to load API definition from URL or file.
        """
        self.file_loader = file_loader
        self.splitter = splitter
        self.merger = merger
        self.apiDefinitionLoader = apiDefinitionLoader or APIDefinitionLoader()
        self.logger = Logger.get_logger(__name__)

    def process_api_definition(
        self, api_definition: str
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Processes an API definition by loading, splitting, and merging its components.

        Args:
            api_definition (str): URL or path to the API definition.

        Returns:
            List of merged API definitions.
        """
        try:
            self.logger.info("Starting API processing")

            raw_definition = self.apiDefinitionLoader.load(api_definition)
            split_definitions = self.splitter.split(raw_definition)
            merged_definitions = self.merger.merge(split_definitions)

            for definition in merged_definitions:
                self.logger.debug(f"\nType: {definition['type']}")
                self.logger.debug(f"Path: {definition['path']}")
                self.logger.debug(f"Verb: {definition['verb']}")

            self.logger.info("Successfully processed API definition.")
            return merged_definitions
        except Exception as e:
            self.logger.error(f"Error processing API definition: {e}")
            raise

    def _should_process_endpoint(self, path: str, endpoints: List[str]) -> bool:
        """Check if an endpoint should be processed based on configuration"""
        if endpoints is None:
            return True

        return any(path.startswith(endpoint) for endpoint in endpoints)

    def extract_env_vars(
        self, api_definitions: List[Dict[str, Union[str, Dict]]]
    ) -> Dict[str, str]:
        self.logger.info("\nGenerating .env file...")

        api_definition_str = api_definitions["yaml"]
        try:
            api_spec = json.loads(api_definition_str)
        except json.JSONDecodeError:
            api_spec = yaml.safe_load(api_definition_str)

        base_url = self._extract_base_url(api_spec)

        if not base_url:
            self.logger.warning("⚠️ Could not extract base URL from API definition")
            base_url = input("Please enter the base URL for the API: ")

        env_file_path = ".env"
        env_content = f"BASEURL={base_url}\n"

        file_spec = FileSpec(path=env_file_path, fileContent=env_content)
        self.file_service.create_files(self.config.destination_folder, [file_spec])

        self.logger.info(f"Generated .env file with BASEURL={base_url}")

    def get_api_paths(
        self, api_definition: Union[str, Dict], endpoints=Optional[List[str]]
    ) -> List[Dict[str, Union[str, Dict]]]:
        result = []

        for definition in api_definition:
            if not self._should_process_endpoint(definition["path"], endpoints):
                continue
            if definition["type"] == "path":
                result.append(definition)

        return result

    def get_api_path_name(self, api_path: Dict[str, Union[str, Dict]]) -> str:
        return api_path["path"]

    def get_api_verbs(
        self, api_definition: Dict[str, str]
    ) -> List[Dict[str, Union[str, Dict]]]:
        result = []

        for definition in api_definition:
            if definition["type"] == "verb":
                result.append(definition)

        return result

    def get_api_verb_path(
        self, api_verb_definition: Dict[str, Union[str, Dict]]
    ) -> str:
        return api_verb_definition["path"]

    def get_api_verb_rootpath(
        self, api_verb_definition: Dict[str, Union[str, Dict]]
    ) -> str:
        return self._get_root_path(api_verb_definition["path"])

    def get_api_verb_name(self, api_verb: Dict[str, Union[str, Dict]]) -> str:
        return api_verb["verb"]

    def _get_root_path(self, path: str) -> str:
        match = re.match(r"(/[^/?]+)", path)
        if match:
            return match.group(1)
        return path

    def get_relevant_models(
        self, all_models: List[Dict[str, Union[str, Dict]]], api_verb: Union[str, Dict]
    ) -> List[Dict[str, Union[str, Dict]]]:
        result = []

        for model in all_models:
            if api_verb["path"] == model["path"] or str(api_verb["path"]).startswith(
                model["path"] + "/"
            ):
                result.append(model["models"])

        return result

    def get_other_models(
        self,
        all_models: List[Dict[str, Union[str, Dict]]],
        api_verb: Dict[str, Union[str, Dict]],
    ) -> List[Dict[str, str]]:
        result = []

        for model in all_models:
            if not (
                api_verb["path"] == model["path"]
                or str(api_verb["path"]).startswith(model["path"] + "/")
            ):
                result.append(
                    {
                        "path": model["path"],
                        "files": model["files"],
                    }
                )

        return result

    def get_api_verb_content(self, api_verb: Dict[str, Union[str, Dict]]) -> str:
        return api_verb["yaml"]

    def get_api_path_content(self, api_path: Dict[str, Union[str, Dict]]) -> str:
        return api_path["yaml"]
