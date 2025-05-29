from typing import Dict

import yaml

from ...utils.logger import Logger


class APIComponentsFilter:
    """Reduces API definition components to only those that are necessary."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def filter_components(self, api_definition: Dict) -> str:
        filtered_definition = api_definition.copy()
        return yaml.dump(filtered_definition)
