import pytest
from src.configuration.config import Config, Envs


@pytest.fixture
def temp_config(tmp_path):
    return Config(destination_folder=str(tmp_path), env=Envs.DEV)
