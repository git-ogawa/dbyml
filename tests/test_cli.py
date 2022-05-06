import shutil
import sys
from pathlib import Path

import pytest
from dbyml.base import main
from dbyml.image import DockerImage

config = Path("tests/config")
full_conf = config / "dbyml.yml"
old_conf = config / "dbyml.yml.old"


class TestCLI:
    def test_help(self):
        args = "dbyml -h"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            main()
        assert e.type == SystemExit

    def test_generate_config_quiet(self, clean_config):
        args = "dbyml --init -q"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            main()
        assert e.type == SystemExit

    def test_convert_config(self, clean_config):
        args = f"dbyml --convert {old_conf}"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            main()
        assert e.type == SystemExit

        # Check that run with the config without errors.
        sys.argv = "dbyml".split()
        main()

    def test_convert_config_same_filename(self, clean_config, capfd):
        tmp = Path("dbyml.yml")
        shutil.copy(old_conf, tmp)
        args = f"dbyml --convert {tmp}"
        sys.argv = args.split()
        with pytest.raises(SystemExit) as e:
            main()
        assert e.type == SystemExit
        out, err = capfd.readouterr()
        assert out == (
            f"Filename conflict with output. The old file is saved as {old_conf.name}.\n"
            f"Input {old_conf.name} successfully converted. Output is {full_conf.name}.\n"
        )
        assert err == ""
        Path("dbyml.yml.old").unlink()

    def test_run_with_config(self, clean_config):
        args = f"dbyml -c {full_conf}"
        sys.argv = args.split()
        main()
