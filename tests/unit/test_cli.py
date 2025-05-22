import sys
from src.configuration.cli import CLIArgumentParser


def test_parse_arguments_defaults(monkeypatch):
    test_args = ["main.py", "spec.yaml"]
    monkeypatch.setattr(sys, "argv", test_args)
    args = CLIArgumentParser.parse_arguments()
    assert args.api_definition == "spec.yaml"
    assert args.generate == "models_and_tests"
