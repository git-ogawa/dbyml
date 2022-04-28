from pathlib import Path

import docker
import pytest
from dbyml import dbyml
from docker.errors import ImageNotFound
from ruamel.yaml import YAML

p = Path("tests/sample")
full_conf_yml = p / "sample.yml"
minimum_conf_yml = p / "minimum.yml"
no_push_conf_yml = p / "no_push.yml"
env_conf_yml = p / "env.yml"
auth_conf_yml = p / "auth.yml"

test_image = "dbyml-sample:latest"


@pytest.fixture
def full_conf() -> dict:
    with open(full_conf_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture
def minimum_conf() -> dict:
    with open(minimum_conf_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture
def no_push_conf() -> dict:
    with open(no_push_conf_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture
def env_conf() -> dict:
    with open(env_conf_yml, "r") as f:
        return YAML().load(f)


@pytest.fixture
def docker_client():
    return docker.from_env()


@pytest.fixture
def obj_full():
    yield dbyml.DockerImage(full_conf_yml)

    client = docker.from_env()
    try:
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        raise ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_env():
    yield dbyml.DockerImage(env_conf_yml)

    client = docker.from_env()
    try:
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        raise ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_min():
    yield dbyml.DockerImage(minimum_conf_yml)

    client = docker.from_env()
    try:
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        raise ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_no_push():
    yield dbyml.DockerImage(no_push_conf_yml)

    client = docker.from_env()
    try:
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        raise ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def obj_auth():
    yield dbyml.DockerImage(auth_conf_yml)

    client = docker.from_env()
    try:
        client.images.remove(test_image)
        print(f"{test_image} has been successfully removed from local.")
    except ImageNotFound:
        raise ImageNotFound(message=f"Image {test_image} is not found.")


@pytest.fixture
def remove_repo_image():
    print("Remove image from repo before test.")
    obj = dbyml.DockerImage(full_conf_yml)
    obj.registry.remove_repo_image()
    yield obj

    print("Remove image from repo after test.")
    obj.registry.remove_repo_image()
