from pathlib import Path

import docker.models.images
from dbyml import base


def test_min_setting(obj_minimum):
    assert obj_minimum.build_dir == Path.cwd()

    obj_minimum.build_dir = obj_minimum.build_dir / "tests/sample/buildtest"
    obj_minimum.dockerfile = obj_minimum.build_dir / "Dockerfile"
    obj_minimum.verbose = True
    obj_minimum.build()


def test_local_build(obj_no_push):
    """Build image in local, not push to registry."""
    obj_no_push.build()
    image = obj_no_push.get_image()
    assert isinstance(image, docker.models.images.Image)
    assert check_labels(image, obj_no_push.label)


def test_load_default_conf(clean_config):
    assert base.get_config_file() is None


def check_labels(image: docker.models.images.Image, labels: dict) -> bool:
    return image.attrs.get("Config").get("Labels") == labels
