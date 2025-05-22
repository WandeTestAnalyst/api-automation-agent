import yaml

from src.processors.swagger import APIDefinitionSplitter, APIDefinitionMerger
from src.models import APIPath, APIVerb


def test_split_and_merge_basic():
    spec = {
        "paths": {
            "/api/v1/users": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "post": {"responses": {"201": {"description": "created"}}},
            },
            "/api/v1/orders": {
                "get": {"responses": {"200": {"description": "ok"}}},
            },
        }
    }

    splitter = APIDefinitionSplitter()
    parts = splitter.split(spec)

    assert len(parts) == 5
    assert sum(isinstance(p, APIPath) for p in parts) == 2
    assert sum(isinstance(p, APIVerb) for p in parts) == 3

    merger = APIDefinitionMerger()
    merged = merger.merge(parts)

    assert len(merged) == 5
    assert sum(isinstance(p, APIPath) for p in merged) == 2
    assert sum(isinstance(p, APIVerb) for p in merged) == 3

    paths = {p.path for p in merged if isinstance(p, APIPath)}
    assert paths == {"/users", "/orders"}

def test_merge_groups_same_root():
    spec = {
        "paths": {
            "/api/v1/users": {
                "get": {"responses": {"200": {"description": "ok"}}},
            },
            "/api/v1/users/{id}": {
                "delete": {"responses": {"204": {"description": "deleted"}}},
            },
        }
    }

    splitter = APIDefinitionSplitter()
    parts = splitter.split(spec)

    assert len(parts) == 4
    assert sum(isinstance(p, APIPath) for p in parts) == 2
    assert sum(isinstance(p, APIVerb) for p in parts) == 2

    merger = APIDefinitionMerger()
    merged = merger.merge(parts)

    # Both paths share the same root, so only one APIPath should remain
    path_objs = [p for p in merged if isinstance(p, APIPath)]
    assert len(path_objs) == 1
    assert path_objs[0].path == "/users"

    merged_yaml = yaml.safe_load(path_objs[0].yaml)
    assert set(merged_yaml["paths"].keys()) == {"/api/v1/users", "/api/v1/users/{id}"}

    # Verb objects remain separate
    assert sum(isinstance(p, APIVerb) for p in merged) == 2
