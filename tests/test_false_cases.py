import os

import pytest
from dbyml.base import DockerImage, Registry
from docker.errors import ImageNotFound
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError


def test_dockerfile_no_exist():
    d = DockerImage("tests/sample/no_push.yml")
    # Set not exist path.
    d.config["path"] = "miss"
    d.set_param(d.config)
    with pytest.raises(FileNotFoundError) as e:
        d.build()
    assert str(e.value) == f"{d.dockerfile} does not exist."


def test_search_not_exist_image(remove_local_image):
    d = DockerImage("tests/sample/sample.yml")
    assert d.get_image() is None


def test_remove_not_exist_image_registry():
    d = DockerImage("tests/sample/sample.yml")
    assert d.registry.get_digest() is None
    assert d.registry.remove_repo_image() is None


def test_wrong_yml():
    with pytest.raises(ScannerError) as e:
        DockerImage("tests/sample/wrong.yml")


def test_miss_key():
    with pytest.raises(SystemExit) as e:
        DockerImage("tests/sample/miss_key.yml")
    assert e.type == SystemExit
    assert e.value.code == "Field 'name' is required in config file."


def test_undefined_env(env_conf):
    d = DockerImage("tests/sample/env.yml")
    # Set an undefined env.
    d.config["label"]["env1"] = r"${ENV_UNDEF}"
    with pytest.raises(KeyError) as e:
        d.parse_config(d.config)
    assert str(e.value) == r"'ENV ${ENV_UNDEF} not defined.'"


def test_wrong_env_format(env_conf):
    d = DockerImage("tests/sample/env.yml")
    # Set a wrong-formated env.
    d.config["label"]["env1"] = r"${ENV1:-ENV2:-ENV3}"
    with pytest.raises(SyntaxError) as e:
        d.parse_config(d.config)
    assert str(e.value) == r"ENV ${ENV1:-ENV2:-ENV3} is invalid format."
