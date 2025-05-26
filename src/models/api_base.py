from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class APIBase:
    """Base class for API components"""

    path: str
    yaml: str
    type: str

    def to_json(self) -> Dict[str, Any]:
        """Convert the component to a JSON-serializable dictionary"""
        return {"path": self.path, "yaml": self.yaml, "type": self.type}

    @staticmethod
    def get_root_path(path: str) -> str:
        """Gets the root path from a full path"""
        return "/" + path.strip("/").split("/", 1)[0]
