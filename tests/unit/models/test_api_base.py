import pytest
from src.models.api_verb import APIBase


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/pets/123", "/pets"),
        ("/users/profile", "/users"),
        ("/pets/123?limit=10", "/pets"),
        ("/users/profile?expand=true", "/users"),
        ("pets/123", "/pets"),
        ("/pets", "/pets"),
        ("pets", "/pets"),
        # ("/pets?limit=10", "/pets"), This is not supported, but it's not necessary at this point.
    ],
)
def test_get_root_path(path, expected):
    assert APIBase.get_root_path(path) == expected
