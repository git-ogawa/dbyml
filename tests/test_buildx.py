from pathlib import Path

import pytest
import requests
from dbyml.buildx import Buildx
from requests.auth import HTTPBasicAuth
from ruamel.yaml import YAML

config = Path("tests/config")
buildx_conf = config / "multi-platform.yml"


class TestRegistry:
    # def test_registry_ready(self, registry):
    #     response = requests.get(f"{registry}/v2/_catalog")
    #     assert response.status_code == 200
    #     assert response.content.decode() == '{"repositories":[]}\n'

    # def test_auth_registry_ready(self, auth_registry):
    #     response = requests.get(f"{auth_registry}/v2/_catalog", auth=self.auth)
    #     assert response.status_code == 200
    #     assert response.content.decode() == '{"repositories":[]}\n'

    def test_run(self):
        with open(buildx_conf, "r") as f:
            config = YAML().load(f)
        bx = Buildx.load_conf(config)
        bx.run()

    def test_create_instance(self):
        instance_name = "pytest-test-instance"
        node_name = f"buildx_buildkit_{instance_name}0"
        with open(buildx_conf, "r") as f:
            config = YAML().load(f)
        bx = Buildx.load_conf(config)
        bx.create(
            name=instance_name,
            driver=bx.driver,
            config=bx.config_file,
            driver_opt=bx.driver_opt,
            buildkitd_flags=bx.buildkitd_flags,
            debug=bx.debug,
        )

        hosts = {"test1": "192.168.200.100", "test2": "192.168.200.200"}

        bx.add_host_node(node_name, hosts)

        bx.remove(
            name="pytest-test-instance",
        )
