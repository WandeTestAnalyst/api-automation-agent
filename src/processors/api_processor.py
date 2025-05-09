from abc import ABC, abstractmethod
import json
import yaml
import logging
from src.configuration.data_sources import DataSource


class APIProcessor(ABC):
    @staticmethod
    def set_data_source(api_file_path: str, logger: logging.Logger = None) -> DataSource:
        """
        Determines the type of data source by reading and parsing the file.

        Args:
            api_file_path: Path to the API definition file
            logger: Logger instance for error reporting

        Returns:
            DataSource: The detected data source type (SWAGGER or POSTMAN)
        """
        if api_file_path.startswith("http"):
            return DataSource.SWAGGER
        if api_file_path.endswith((".yml", ".yaml")):
            return DataSource.SWAGGER

        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(api_file_path, "r", encoding=encoding) as f:
                    if api_file_path.endswith(".json"):
                        data = json.load(f)
                    else:
                        data = yaml.safe_load(f)

                if isinstance(data, dict):
                    if "info" in data and "_postman_id" in data["info"]:
                        return DataSource.POSTMAN
                    elif "openapi" in data or "swagger" in data:
                        return DataSource.SWAGGER

            except Exception as e:
                if logger:
                    logger.error(f"Error reading file {api_file_path} with encoding {encoding}: {e}")

    @abstractmethod
    def process_api_definition(self, api_file_path):
        pass

    @abstractmethod
    def get_api_verbs(self, api_definition, endpoints=None):
        pass

    @abstractmethod
    def get_api_paths(self, api_definition, endpoints=None):
        pass

    @abstractmethod
    def get_relevant_models(self, all_models, api_verb):
        pass

    @abstractmethod
    def get_other_models(self, all_models, api_verb):
        pass

    @abstractmethod
    def get_api_path_content(self, api_path_definition):
        pass

    @abstractmethod
    def get_api_verb_content(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_verb_rootpath(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_verb_path(self, api_verb_definition):
        pass

    @abstractmethod
    def get_api_path_name(self, api_path):
        pass

    @abstractmethod
    def get_api_verb_name(self, api_verb):
        pass

    @abstractmethod
    def extract_env_vars(self, api_defintions):
        pass
