import subprocess

import docker.models.images
from dbyml import dbyml


def test_local_build(obj_no_push):
    """Build image in local, not push to registry."""
    obj_no_push.build()
    image = obj_no_push.get_image()
    assert isinstance(image, docker.models.images.Image)
    assert check_labels(image, obj_no_push.label)


def test_push(obj_full, remove_repo_image):
    """Build image in local, push to registry."""
    obj_full.build()

    # Check that the image to be pushed doesn't exist in registry
    assert not obj_full.registry.get_digest()

    obj_full.push()
    assert obj_full.registry.get_digest()


def test_push_auth_registry(obj_auth):
    obj_auth.build()
    obj_auth.push()

    # Check if the pushed image can be pulled from the registry.
    obj_auth.remove_local_image(obj_auth.registry.repository)
    obj_auth.pull(obj_auth.registry.repository, auth=obj_auth.registry.auth)


def test_env_value(obj_env):
    obj_env.build()
    assert obj_env.label == {
        "env1": "env1",
        "env_default": "default_value",
        "multi_env": "env1/test/env2.env3",
    }


def check_labels(image: docker.models.images.Image, labels: dict) -> bool:
    return image.attrs.get("Config").get("Labels") == labels
