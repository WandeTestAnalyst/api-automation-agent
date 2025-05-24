import copy
import time
from typing import List

import yaml

from ...models import APIPath, APIVerb, APIDef
from ...utils.logger import Logger


class APIDefinitionMerger:
    """Merges API definition components based on base resources."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def merge(self, api_definition_list: List[APIDef]) -> List[APIDef]:
        """Merges API definitions by their base resources."""
        start_time = time.time()
        merged_definitions = {}

        for item in api_definition_list:
            if isinstance(item, APIPath):
                base_path = APIPath.get_root_path(item.path)
                if base_path not in merged_definitions:
                    item.path = base_path
                    merged_definitions[base_path] = copy.deepcopy(item)
                else:
                    item_yaml = yaml.safe_load(item.yaml)
                    merged_yaml = yaml.safe_load(merged_definitions[base_path].yaml)
                    for path, path_data in item_yaml["paths"].items():
                        if path not in merged_yaml["paths"]:
                            merged_yaml["paths"].update({path: path_data})
                    merged_definitions[base_path].yaml = yaml.dump(merged_yaml, sort_keys=False)
            elif isinstance(item, APIVerb):
                merged_definitions[f"{item.path}-{item.verb}"] = copy.deepcopy(item)

        self.logger.info(f"Merged {len(merged_definitions)} API definitions")
        self.logger.info(f"Time taken to merge API definitions: {time.time() - start_time:.2f} seconds")
        return list(merged_definitions.values())
