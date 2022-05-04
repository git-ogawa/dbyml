import sys
from pathlib import Path

import pytest
import requests
from dbyml import base
from requests.auth import HTTPBasicAuth

config = Path("tests/config")
auth_conf = config / "auth.yml"
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
        image = base.DockerImage(full_conf)
        image.build()
        image.push()
        assert image.registry.get_digest()
        image.registry.remove_repo_image()

    def test_push_auth_registry(self):
        image = base.DockerImage(auth_conf)
        image.build()
        image.push()
        assert image.registry.get_digest()
        image.remove_local_image(image.registry.repository)
        image.pull(image.registry.repository, auth=image.auth)

    def test_env_value(self):
        image = base.DockerImage(env_conf)
        image.build()
        assert image.label == {
            "env1": "env1",
            "env_default": "default_value",
            "multi_env": "env1/test/env2.env3",
        }


class TestCLI:
    def test_help(self):
        args = "dbyml -h"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            base.main()
        assert e.type == SystemExit

    def test_generate_config_quiet(self, clean_config):
        args = "dbyml --init -q"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            base.main()
        assert e.type == SystemExit

    def test_run_with_config(self, clean_config):
        args = f"dbyml -c {full_conf}"
        sys.argv = args.split()
        base.main()
