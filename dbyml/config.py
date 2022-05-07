import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from ruamel.yaml import YAML

from dbyml.prompt import Prompt


def get_file() -> Optional[Path]:
    """Find default config in current directory.

    Returns:
        Optional[Path]: Return Path object if find the config, None otherwise.
    """
    cwd = Path.cwd()
    configs = [cwd / "dbyml.yml", cwd / "dbyml.yaml"]
    for c in configs:
        if c.exists():
            return c
    return None


def replace_dict_value(d: dict, key: str, value: str) -> dict:
    """Replace value of the key in given dict.

    When the given dict contains the key, replace its value the specified one.
    The value will not be replaced when the key dose not exist in the dict.
    If the dict is nested, Search the key recursively.

    Args:
        d (dict): Dict containing the key to be searched.
        key (str): Key name.
        value (str): Value name.

    Returns:
        dict: The dict in which the value of the key is replaced with the specified one.
    """
    for k, v in d.items():
        if k == key:
            d[key] = value
            return d
        if isinstance(v, OrderedDict) or isinstance(v, dict):
            replace_dict_value(v, key, value)
    return d


def create(quiet: bool = False) -> None:
    src = Path(__file__).resolve().parent / "data" / "full.yml"
    cwd = Path.cwd()
    config = cwd / "dbyml.yml"

    with open(config, "w") as fout:
        with open(src, "r") as fin:
            y = YAML()
            if quiet is True:
                y.dump(y.load(fin), fout)
            else:
                param = Prompt().interactive_prompt()
                data = y.load(fin)
                if param["set_registry"] is False:
                    data.pop("push")
                for k, v in param.items():
                    if data.get(k) is not None:
                        data[k] = v
                    else:
                        data = replace_dict_value(data, k, v)
                y.dump(data, fout)
                replace_quotes(config)

    print(
        f"Create {config.name}. Check the contents and edit according to your docker image."
    )


def replace_quotes(path: Path) -> None:
    """Replace nested quotes into single ones.

    Args:
        path (Path): A file path in which replace quotes.
    """
    # Fix quotes
    with open(path, "r") as fin:
        data = re.sub(r"(\'\"|\"\')", "'", fin.read())

    with open(path, "w") as fout:
        fout.write(data)


def convert(path: Path) -> None:
    """Convert the content in config.

    Convert names, types and attributes of the fields from the old style (before v1.2.0) in config.

    Args:
        path (Path): Path to the config to be converted.
    """
    if isinstance(path, str):
        path = Path(path)

    ref = Path(__file__).resolve().parent / "data" / "full.yml"
    cwd = Path.cwd()
    output = cwd / "dbyml.yml"

    # If input config name is the same as output, save as old
    if path.name == output.name:
        path = path.rename(path.with_suffix(".yml.old"))
        print(f"Filename conflict with output. The old file is saved as {path.name}.")

    with open(output, "w") as fout:
        with open(ref, "r") as fref:
            with open(path, "r") as fin:
                y = YAML()
                data = y.load(fref)
                src = y.load(fin)
                for top, sub in data.items():
                    for field in sub.keys():
                        data[top][field] = search_key(field, src, data[top][field])
                y.dump(data, fout)
    print(f"Input {path.name} successfully converted. Output is {output.name}.")


def search_key(key: str, target: dict, default: Any = None) -> Any:
    """Get a value coressponding to the specified key in the dict.

    Args:
        key (str): A key corresponding to get value.
        target (dict): A dict to search
        default (Any): A returned value when cannot find the value.

    Returns:
        Any: A value coressponding to the specified key. If cannot find the key, return the value of the default.
    """
    value = default
    if key in target.keys():
        return target[key]
    else:
        for v in target.values():
            if (isinstance(v, OrderedDict) or isinstance(v, dict)) and value == default:
                value = search_key(key, v, default)
                if value != default:
                    return value
        return default
