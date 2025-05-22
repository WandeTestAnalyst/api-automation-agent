import pytest
from src.models.api_path import APIPath


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/api/v1/pets", "/pets"),
        ("/api/v2/pets/123", "/pets/123"),
        ("/api/v10/pets", "/pets"),
        ("api/v1/pets", "/pets"),
        ("/api/v1beta/pets", "/v1beta/pets"),
        ("/v2/products", "/products"),
        ("/pets", "/pets"),
        ("/users/profile", "/users/profile"),
        ("/pets?limit=10", "/pets?limit=10"),
    ],
)
def test_normalize_path(path, expected):
    assert APIPath.normalize_path(path) == expected
