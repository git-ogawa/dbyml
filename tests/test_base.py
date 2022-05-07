import sys
from pathlib import Path

import pytest
import requests
from dbyml.image import DockerImage
from requests.auth import HTTPBasicAuth

config = Path("tests/config")
full_conf = config / "dbyml.yml"
env_conf = config / "env.yml"


class TestRegistry:
    auth = HTTPBasicAuth("docker", "docker")

    def test_registry_ready(self, registry):
        response = requests.get(f"{registry}/v2/_catalog")
        assert response.status_code == 200
        assert response.content.decode() == '{"repositories":[]}\n'

    def test_auth_registry_ready(self, auth_registry):
        response = requests.get(f"{auth_registry}/v2/_catalog", auth=self.auth)
        assert response.status_code == 200
        assert response.content.decode() == '{"repositories":[]}\n'

    def test_push_registry(self, registry):
        """Build image in local, push to registry."""
        image = DockerImage(full_conf)
        image.build()
        image.push()
        assert image.registry.get_digest()
        image.registry.remove_repo_image()

    def test_push_auth_registry(self):
        image = DockerImage(full_conf)
        image.build()
        image.push()
        assert image.registry.get_digest()
        image.pull(image.registry.repository, auth=image.auth)

    def test_env_value(self):
        image = DockerImage(env_conf)
        image.build()
        assert image.label == {
            "env1": "env1",
            "env_default": "default_value",
            "multi_env": "env1/test/env2.env3",
        }
