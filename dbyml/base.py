#!/usr/bin/env python3
"""
Dbyml is a CLI tool to build your docker image with the arguments loaded from configs in yaml.

Passing the config file where the arguments are listed to build the image from your dockerfile,
push it to the docker registry.


To make sample config file, run the following command.

>>> dbyml --init

"""
import argparse
import sys

from dbyml import config
from dbyml.image import DockerImage


def main() -> None:
    usage = "%(prog)s -c [config_file] [options]"
    parser = argparse.ArgumentParser(
        usage=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument("-c", "--conf", type=str, help="Config file.")
    parser.add_argument(
        "--convert", type=str, help="Convert config file into the new one."
    )

    parser.add_argument("--init", help="Generate config file.", action="store_true")
    parser.add_argument(
        "-q",
        "--quiet",
        help="If set with --init flag, generate a config non-interactively.",
        action="store_true",
    )

    args = parser.parse_args()

    if args.init:
        config.create(args.quiet)
        sys.exit()

    if args.convert:
        config.convert(args.convert)
        sys.exit()

    if args.conf:
        conf = args.conf
    else:
        conf = config.get_file()
        if config is None:
            parser.print_help()
            sys.exit()

    img = DockerImage(conf)
    img.build()
    if img.enabled is True:
        img.push()


if __name__ == "__main__":
    main()
