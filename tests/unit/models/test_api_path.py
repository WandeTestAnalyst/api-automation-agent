import pytest
from src.models.api_path import APIPath


def test_api_path_instantiation():
    """Test that APIPath instances are created with the correct type value."""
    path = "/test/path"
    yaml_content = "test: content"
    api_path = APIPath(path=path, yaml=yaml_content)

    assert api_path.type == "path"
    assert api_path.path == path
    assert api_path.yaml == yaml_content


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/api/pets", "/pets"),
        ("/api/pets/123", "/pets/123"),
        ("/api/users/profile", "/users/profile"),
        ("/api/v1/pets", "/v1/pets"),
        ("/api/v2/pets/123", "/v2/pets/123"),
        ("/api/v10/pets", "/v10/pets"),
        ("api/v1/pets", "/v1/pets"),
        ("/api/v1beta/pets", "/v1beta/pets"),
        ("/v2/products", "/v2/products"),
        ("/pets", "/pets"),
        ("/users/profile", "/users/profile"),
        ("/pets?limit=10", "/pets?limit=10"),
        ("/api/v1/", "/v1"),
        ("/api/v1", "/v1"),
        ("/", "/"),
        ("", ""),
        ("//api//v1//pets", "/v1/pets"),
        ("/api/v1/pets/", "/v1/pets"),
    ],
)
def test_normalize_path(path, expected):
    assert APIPath.normalize_path(path) == expected


def test_api_path_to_json():
    """Test that APIPath instances are correctly converted to JSON."""
    path = "/test/path"
    yaml_content = "test: content"
    api_path = APIPath(path=path, yaml=yaml_content)

    json_data = api_path.to_json()
    assert json_data == {
        "path": path,
        "yaml": yaml_content,
        "type": "path",
    }
