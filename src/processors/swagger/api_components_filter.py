from typing import Dict, List

import yaml

from ...utils.logger import Logger


class APIComponentsFilter:
    """Reduces API definition components to only those that are necessary."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def filter_schemas(self, api_definition: Dict) -> str:
        """Filters out unreferenced schemas from the API definition components."""
        used_refs = self.collect_refs(api_definition.get("paths", {}))
        filtered_schemas = self.collect_used_schemas(
            api_definition.get("components", {}).get("schemas", {}), used_refs
        )

        filtered_spec = {
            "openapi": api_definition["openapi"],
            "info": api_definition["info"],
            "paths": api_definition["paths"],
            "components": {
                "schemas": filtered_schemas
                # TODO: other components
            },
        }

        return yaml.dump(filtered_spec, sort_keys=False)

        # filtered_definition = api_definition.copy()
        # return yaml.dump(filtered_definition)
