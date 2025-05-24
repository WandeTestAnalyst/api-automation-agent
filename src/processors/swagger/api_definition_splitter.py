import copy
import time
from typing import Dict, List

import yaml

from ...models import APIPath, APIVerb, APIDef
from ...utils.logger import Logger


class APIDefinitionSplitter:
    """Splits API definitions into smaller components."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def split(self, api_definition: Dict) -> List[APIDef]:
        """Splits the API definition into smaller, manageable parts."""
        start_time = time.time()
        self.logger.info("Splitting API definition into components...")
        api_definition_list = []

        for path, path_data in api_definition.get("paths", {}).items():
            normalized_path = APIPath.normalize_path(path)

            path_copy = copy.deepcopy(api_definition)
            path_copy["paths"] = {path: path_data}
            api_definition_list.append(
                APIPath(path=normalized_path, yaml=yaml.dump(path_copy, sort_keys=False))
            )

            for verb, verb_data in path_data.items():
                verb_copy = copy.deepcopy(path_copy)
                verb_copy["paths"][path] = {verb: verb_data}
                api_definition_list.append(
                    APIVerb(
                        verb=verb.upper(),
                        path=normalized_path,
                        root_path=APIVerb.get_root_path(normalized_path),
                        yaml=yaml.dump(verb_copy, sort_keys=False),
                    )
                )

        self.logger.info("Successfully split API definition.")
        self.logger.info(f"Time taken to split API definition: {time.time() - start_time:.2f} seconds")
        return api_definition_list
