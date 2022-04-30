import subprocess
from pathlib import Path

import docker.models.images
import requests
from dbyml import dbyml
from requests.auth import HTTPBasicAuth

p = Path("tests/sample")
auth_conf_yml = p / "auth.yml"


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

    def test_push_registry(self, obj_full, registry):
        """Build image in local, push to registry."""
        obj_full.build()
        obj_full.push()

        assert obj_full.registry.get_digest()

        obj_full.registry.remove_repo_image()

    def test_push_auth_registry(self, test_settings):
        dby = dbyml.DockerImage(auth_conf_yml)
        dby.build()
        dby.push()

        assert dby.registry.get_digest()
        dby.remove_local_image(dby.registry.repository)
        dby.pull(dby.registry.repository, auth=dby.registry.auth)

    def test_env_value(self, obj_env):
        obj_env.build()
        assert obj_env.label == {
            "env1": "env1",
            "env_default": "default_value",
            "multi_env": "env1/test/env2.env3",
        }
