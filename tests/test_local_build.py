from pathlib import Path

import docker.models.images
from dbyml import base

config = Path("tests/config")
full_conf = config / "dbyml.yml"


def test_local_build():
    """Build image in local, not push to registry."""
    image = base.DockerImage(full_conf)
    image.build()
    build_image = image.get_image()
    assert isinstance(build_image, docker.models.images.Image)
    assert check_labels(build_image, image.label)


def test_load_default_conf(clean_config):
    assert base.get_config_file() is None


def check_labels(image: docker.models.images.Image, labels: dict) -> bool:
    return image.attrs.get("Config").get("Labels") == labels
