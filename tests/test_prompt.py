import logging
from pathlib import Path

import pytest
from dbyml import config
from dbyml.prompt import Prompt

expected_data = {
    "name": "test_name",
    "tag": "test_tag",
    "path": "test_path",
    "build_args": {"test_build_key": "test_build_value"},
    "label": {"test_label_key": "test_label_value"},
    "username": "test_username",
    "password": "test_password",
    "host": "test_host",
    "port": 9999,
    "set_registry": True,
}

expected_str = [
    expected_data["name"],
    expected_data["tag"],
    expected_data["path"],
    expected_data["username"],
    expected_data["password"],
    expected_data["host"],
    expected_data["port"],
]
expected_properties = ["build_args", "label", "registry"]
expected_dict = [
    expected_data["build_args"],
    expected_data["label"],
]


def test_interactive_prompt(mocker, clean_config):
    Prompt.get_str_data = mocker.MagicMock(side_effect=expected_str)
    Prompt.get_dict_data = mocker.MagicMock(side_effect=expected_dict)
    Prompt.get_properties = mocker.MagicMock(return_value=expected_properties)
    p = Prompt()
    assert p.interactive_prompt() == expected_data


def test_generate_config(mocker, capfd, clean_config):
    Prompt.interactive_prompt = mocker.MagicMock(return_value=expected_data)
    config.create(quiet=False)
    out, err = capfd.readouterr()
    assert (
        out
        == "Create dbyml.yml. Check the contents and edit according to your docker image.\n"
    )

    assert err == ""
