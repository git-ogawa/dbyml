from pathlib import Path

import docker
import pytest
import requests
from dbyml import dbyml
from docker.errors import ImageNotFound
from requests.exceptions import ConnectionError
from ruamel.yaml import YAML

p = Path("tests/sample")
settings_yml = "tests/settings.yml"
full_conf_yml = p / "sample.yml"
minimum_conf_yml = p / "minimum.yml"
no_push_conf_yml = p / "no_push.yml"
env_conf_yml = p / "env.yml"

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
def env_conf() -> dict:
    with open(env_conf_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture
def obj_full():
    yield dbyml.DockerImage(full_conf_yml)

    client = docker.from_env()
    client.images.remove(test_image)
    print(f"{test_image} has been successfully removed from local.")
    ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_minimum():
    yield dbyml.DockerImage(minimum_conf_yml)

    client = docker.from_env()
    client.images.remove(test_image)
    print(f"{test_image} has been successfully removed from local.")
    ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_env():
    yield dbyml.DockerImage(env_conf_yml)

    client = docker.from_env()
    client.images.remove(test_image)
    print(f"{test_image} has been successfully removed from local.")


@pytest.fixture
def obj_no_push():
    yield dbyml.DockerImage(no_push_conf_yml)

    client = docker.from_env()
    client.images.remove(test_image)
    print(f"{test_image} has been successfully removed from local.")


@pytest.fixture
def remove_local_image() -> None:
    try:
        client = docker.from_env()
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        print(f"{test_image} does not exist in local.")
