import pytest
from src.processors.swagger import APIDefinitionSplitter
from src.models import APIPath, APIVerb


@pytest.mark.only
def test_splitter_basic():
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
    assert parts[0].path == "/users"
    assert parts[1].path == "/orders"


@pytest.mark.only
def test_splitter_groups_same_root():
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
