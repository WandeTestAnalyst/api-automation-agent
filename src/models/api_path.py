from dataclasses import dataclass

from .api_base import APIBase


@dataclass
class APIPath(APIBase):
    """Represents an API path with its metadata"""

    def __post_init__(self):
        self.type = "path"

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalizes the path by removing api and version prefixes."""
        parts = [p for p in path.split("/") if p]

        if not parts:
            return path

        start_index = 0

        if start_index < len(parts):
            if parts[start_index] == "api":
                start_index += 1

        if start_index < len(parts):
            if (
                parts[start_index].startswith("v")
                and len(parts[start_index]) > 1
                and parts[start_index][1:].isdigit()
            ):
                start_index += 1

        if start_index < len(parts):
            return "/" + "/".join(parts[start_index:])
        return path
