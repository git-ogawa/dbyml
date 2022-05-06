import os
from pathlib import Path

import pytest
from dbyml.errors import BuildError
from dbyml.image import DockerImage
from dbyml.registry import Registry
from docker.errors import ImageNotFound
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

config = Path("tests/config")
full_conf = config / "dbyml.yml"
env_conf = config / "env.yml"
wrong_conf = config / "wrong.yml"


def test_dockerfile_no_exist():
    image = DockerImage(full_conf)

    # Set not exist path.
    image.config["image"]["path"] = "miss"

    image.set_param(image.config)
    with pytest.raises(FileNotFoundError) as e:
        image.build()
    assert str(e.value) == f"{image.dockerfile} does not exist."


def test_search_not_exist_image(remove_local_image):
    image = DockerImage(full_conf)
    assert image.get_image() is None


def test_remove_not_exist_image_registry():
    image = DockerImage(full_conf)
    # Remove the image from the registry if exists.
    image.registry.remove_repo_image()

    assert image.registry.get_digest() is None
    assert image.registry.remove_repo_image() is None


def test_wrong_yml():
    with pytest.raises(ScannerError) as e:
        DockerImage(wrong_conf)


def test_miss_key():
    # Remove required field.
    with open(full_conf, "r") as f:
        params = YAML().load(f)
        params["image"].pop("name")
    with pytest.raises(SystemExit) as e:
        DockerImage().load_dict(params)
    assert e.type == SystemExit
    assert e.value.code == "Field 'name' is required in config file."


def test_undefined_env():
    image = DockerImage(env_conf)
    # Set an undefined env.
    image.config["image"]["label"]["env1"] = r"${ENV_UNDEF}"
    with pytest.raises(KeyError) as e:
        image.parse_config(image.config)
    assert str(e.value) == r"'ENV ${ENV_UNDEF} not defined.'"


def test_wrong_env_format():
    image = DockerImage(env_conf)
    # Set a wrong-formated env.
    image.config["image"]["label"]["env1"] = r"${ENV1:-ENV2:-ENV3}"
    with pytest.raises(SyntaxError) as e:
        image.parse_config(image.config)
    assert str(e.value) == r"ENV ${ENV1:-ENV2:-ENV3} is invalid format."


def test_build_errors():
    image = DockerImage(full_conf)
    image.dockerfile = full_conf.parent / Path("dockerfiles/error_Dockerfile")
    # image.parse_config(image.config)
    with pytest.raises(BuildError) as e:
        image.build()
