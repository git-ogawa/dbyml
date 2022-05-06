from pathlib import Path

import docker
import pytest
import requests
from docker.errors import ImageNotFound
from requests.exceptions import ConnectionError
from ruamel.yaml import YAML

settings_yml = "tests/settings.yml"
test_image = "dbyml-sample:latest"


def is_responsive(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def test_settings() -> dict:
    with open(settings_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture(scope="session")
def registry(docker_ip, docker_services, test_settings) -> str:
    """Ensure that HTTP service is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for(
        "pytest-registry", test_settings["registry"]["internal_port"]
    )
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


@pytest.fixture(scope="session")
def auth_registry(docker_ip, docker_services, test_settings) -> str:
    """Ensure that HTTP service is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for(
        "pytest-auth-registry", test_settings["auth_registry"]["internal_port"]
    )
    url = f"http://{docker_ip}:{port}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


@pytest.fixture
def remove_local_image() -> None:
    """Remove the docker image in local before each test."""
    try:
        client = docker.from_env()
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        print(f"{test_image} does not exist in local.")


@pytest.fixture
def remove_registry_image() -> None:
    """Remove the docker image in the registry before each test."""
    try:
        client = docker.from_env()
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        print(f"{test_image} does not exist in local.")


@pytest.fixture()
def clean_config():
    """Remove default config file."""
    cwd = Path.cwd()
    config = cwd / "dbyml.yml"

    # Before test
    if config.exists():
        config.unlink()

    yield None

    # After test
    if config.exists():
        config.unlink()
