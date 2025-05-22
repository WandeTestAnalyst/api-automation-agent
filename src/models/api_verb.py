from dataclasses import dataclass
from typing import Dict, Any
from .api_base import APIBase


@dataclass
class APIVerb(APIBase):
    """Represents an API verb (HTTP method) with its metadata"""

    verb: str
    root_path: str

    def __post_init__(self):
        self.type = "verb"

    def to_json(self) -> Dict[str, Any]:
        """Convert the verb to a JSON-serializable dictionary"""
        return {
            "verb": self.verb,
            "path": self.path,
            "root_path": self.root_path,
            "yaml": self.yaml,
            "type": self.type,
        }
