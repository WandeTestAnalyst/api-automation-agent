import copy
from typing import Dict, Any

from ...utils.logger import Logger


class APIComponentsFilter:
    """Reduces API definition components to only those that are necessary."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def filter_schemas(self, api_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Filters out unreferenced schemas from the API definition components."""
        filtered_spec = copy.deepcopy(api_definition)

        if "components" not in filtered_spec:
            self.logger.info("No components found in the API definition.")
            return filtered_spec
        components = filtered_spec.get("components", {})

        refs_on_paths = self.collect_refs(filtered_spec.get("paths", {}))
        if "schemas" not in components:
            self.logger.info("No schemas found in the components.")
            return filtered_spec

        self.logger.info("Filtering schemas from components...")

        filtered_schemas = self.collect_used_schemas(components.get("schemas", {}), refs_on_paths)

        for component_name, component_data in components.items():
            if component_name != "schemas":
                filtered_spec["components"][component_name] = component_data

        filtered_spec["components"]["schemas"] = filtered_schemas
        self.logger.info("Successfully filtered schemas.")
        return filtered_spec

    def collect_refs(self, api_def: Any, refs: set = None) -> set:
        """Recursively collects all $ref from the API definition."""
        if refs is None:
            refs = set()

        if isinstance(api_def, dict):
            for key, value in api_def.items():
                if key == "$ref" and isinstance(value, str):
                    refs.add(value)
                else:
                    self.collect_refs(value, refs)
        elif isinstance(api_def, list):
            for item in api_def:
                self.collect_refs(item, refs)

        return refs

    def collect_used_schemas(self, schemas: Dict[str, Any], refs_on_paths: set) -> Dict[str, Any]:
        """Returns only the referenced schemas."""
        used_schemas = {}
        refs_to_check = list(refs_on_paths)

        while refs_to_check:
            ref = refs_to_check.pop()
            if not ref.startswith("#/components/schemas/"):
                continue

            schema_name = ref.split("/")[-1]
            if schema_name in used_schemas:
                continue

            schema = schemas.get(schema_name)
            if not schema:
                continue

            used_schemas[schema_name] = schema

            nested_refs = self.collect_refs(schema)
            refs_to_check.extend(nested_refs)

        return used_schemas
