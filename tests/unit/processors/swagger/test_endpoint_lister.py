from src.processors.swagger.endpoint_lister import EndpointLister
from src.models.api_path import APIPath
from src.models.api_verb import APIVerb


def test_list_endpoints_outputs_paths(capsys):
    paths = [
        APIPath(path="/users", yaml=""),
        APIPath(path="/items", yaml=""),
        APIPath(path="/accounts", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    assert "Endpoints that can be used with the --endpoints flag:" in output
    for p in ["/accounts", "/items", "/users"]:
        assert f"- {p}" in output


def test_list_endpoints_empty_list(capsys):
    paths = []
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    assert "Endpoints that can be used with the --endpoints flag:" in output
    assert output.count("- ") == 0


def test_list_endpoints_duplicate_paths(capsys):
    paths = [
        APIPath(path="/users", yaml=""),
        APIPath(path="/users", yaml=""),  # Duplicate path
        APIPath(path="/items", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    assert output.count("- /users") == 1
    assert output.count("- /items") == 1


def test_list_endpoints_mixed_types(capsys):
    paths = [
        APIPath(path="/users", yaml=""),
        APIVerb(path="/users/{id}", verb="GET", yaml="", root_path="/users"),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    assert output.count("- ") == 1
    assert "- /users" in output
    assert "- /users/{id}" not in output


def test_list_endpoints_special_characters(capsys):
    paths = [
        APIPath(path="/users/{id}", yaml=""),
        APIPath(path="/items/{item_id}/status", yaml=""),
        APIPath(path="/search?q={query}", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out
    for p in ["/users/{id}", "/items/{item_id}/status", "/search?q={query}"]:
        assert f"- {p}" in output


def test_list_endpoints_sorting(capsys):
    paths = [
        APIPath(path="/zebra", yaml=""),
        APIPath(path="/apple", yaml=""),
        APIPath(path="/banana", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out

    path_lines = [line for line in output.split("\n") if line.startswith("-")]

    assert path_lines[0] == "- /apple"
    assert path_lines[1] == "- /banana"
    assert path_lines[2] == "- /zebra"


def test_list_endpoints_newline_formatting(capsys):
    paths = [
        APIPath(path="/users", yaml=""),
        APIPath(path="/items", yaml=""),
    ]
    EndpointLister.list_endpoints(paths)
    captured = capsys.readouterr()
    output = captured.out

    # Verify proper newline formatting
    print(output)
    assert output.startswith("\n")  # Should start with a newline
    assert output.count("\n") == 4  # Header + 2 paths + final newline
