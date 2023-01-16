"""
A module to build multi-platform image using docker buildx.
"""
import re
import shlex
import subprocess
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Optional, Tuple, Type, TypeVar, Union

import docker
from docker.errors import APIError
from jinja2 import Environment, FileSystemLoader

from dbyml.registry import Registry

B = TypeVar("B", bound="Buildx")


class Buildx:
    def __init__(
        self,
        add_host: Optional[dict] = None,
        build_args: Optional[dict] = None,
        config: Optional[dict] = None,
        config_file: Optional[str] = None,
        debug: bool = False,
        dockerfile: Optional[str] = None,
        driver: str = "docker-container",
        driver_opt: Optional[dict] = None,
        instance: Optional[str] = None,
        label: Optional[dict] = None,
        name: Optional[str] = None,
        path: str = ".",
        platform: Optional[list] = None,
        pull_output: bool = True,
        remove_instance: bool = False,
        registry: Optional[Registry] = None,
        type_: str = "registry",
        use_existing_instance: bool = True,
    ) -> None:
        """Class for docker buildx commands.

        Args:
            add_host (dict, optional): List of hostname and ip address. Defaults to None.
            build_args (Optional[dict], optional): Buildx_args corresponding to docker options. Defaults to None.
            config (dict, optional): Configuration written in config file. Defaults to None.
            config_file (str, optional): Configuration filename. Defaults to None.
            debug (bool, optional): Whether to enable debug mode. Defaults to False.
            dockerfile (Optional[str], optional): Dockerfile name. Defaults to None.
            driver (str, optional): The driver specified when an instance is created. Defaults to "docker-container".
            driver_opt (dict, optional): The driver options passed to an instance. Defaults to None.
            instance (Optional[str], optional): An instance name. Defaults to None.
            label (Optional[dict], optional): Labels corresponding to docker options. Defaults to None.
            name (str, optional): Image name. Defaults to None.
            path (str, optional): Path to the directory where Dockerfile exists. Defaults to ".".
            platform (list, optional): Platforms . Defaults to None.
            pull_output (bool, optional): Whether to pull an image to be built from a registry after build.
                Defaults to True.
            remove_instance (bool, optional): Whether to remove an instance after build. Defaults to False.
            registry (Registry, optional): A registry to which a built image will be pushed. Defaults to None.
            type_ (str, optional): The output type of buildx. Defaults to "registry".
            use_existing_instance (bool, optional): Whether to use an instance if already exists. Defaults to True.
        """
        self.add_host = add_host
        self.basename = name
        self.build_args = build_args
        self.config = config
        self.config_file = config_file
        self.debug = debug
        self.dockerfile = dockerfile
        self.driver = driver
        self.driver_opt = driver_opt
        self.instance = instance
        self.label = label
        self.path = path
        self.platform = platform
        self.pull_output = pull_output
        self.registry = registry
        self.remove_instance = remove_instance
        self.type = type_
        self.use_existing_instance = use_existing_instance

        self.base_cmd = "docker buildx"
        if self.registry is not None:
            self.image_name = self.registry.repository

        self.buildkitd_flags: Optional[dict]
        if self.driver_opt is not None and self.driver_opt.get("network") == "host":
            self.buildkitd_flags = {"--allow-insecure-entitlement": "network.host"}
        else:
            self.buildkitd_flags = None

        if self.instance is not None:
            self.node = f"buildx_buildkit_{self.instance}0"

    @classmethod
    def load_conf(cls: Type[B], config: dict) -> B:
        """Load properties from dict to make an instance."""
        buildx = cls()

        buildx.config = config

        img: dict = config.get("image", {})
        image = img["name"]
        tag = img.get("tag", "latest")
        buildx.basename = f"{image}:{tag}"

        buildx.path = img.get("path", ".")
        buildx.dockerfile = img.get("dockerfile", "Dockerfile")
        buildx.build_args = img.get("build_args")
        buildx.label = img.get("label")

        bx = config.get("buildx", {})
        buildx.instance = bx.get("instance")
        buildx.platform = bx.get("platform")

        buildx.driver = bx.get("driver", "docker-container")
        buildx.remove_instance = bx.get("remove_instance", False)
        buildx.config_file = "buildkitd.toml"
        buildx.use_existing_instance = bx.get("use_existing_instance", True)
        buildx.pull_output = bx.get("pull_output", True)
        buildx.add_host = bx.get("add_host")
        buildx.type = bx.get("type", "registry")
        buildx.debug = bx.get("debug", False)
        buildx.driver_opt = bx.get("driver_opt", {})

        reg = config.get("registry", {})
        buildx.registry = Registry(
            host=reg["host"],
            port=reg.get("port"),
            name=image,
            tag=tag,
            namespace=reg.get("namespace"),
            username=reg.get("username"),
            password=reg.get("password"),
            certs={
                "ca_cert": reg.get("ca_cert"),
                "client_cert": reg.get("client_cert"),
                "client_key": reg.get("client_key"),
            },
        )

        buildx.image_name = buildx.registry.repository

        if buildx.instance is not None:
            buildx.node = f"buildx_buildkit_{buildx.instance}0"

        if buildx.driver_opt is not None and buildx.driver_opt.get("network") == "host":
            buildx.buildkitd_flags = {"--allow-insecure-entitlement": "network.host"}
        else:
            buildx.buildkitd_flags = None

        return buildx

    def _run(
        self,
        cmd: str,
        sep: str = "\n",
        raw: bool = False,
        stdout: Any = subprocess.PIPE,
        stderr: Any = subprocess.PIPE,
        debug: bool = False,
        timeout: Optional[int] = None,
    ) -> Union[str, list]:
        """Run a command.

        Run a command by subprocess.run. The command output will be a string,
        so return a list of each line splitted by separator (break line by default).

        Args:
            cmd (str): Command to run.
            sep (str, optional): Separator to split the command output. Defaults to "\n".
            raw (bool, optional): Set true to return command output without formatted. Defaults to False.
            stdout (Any, optional): Stdout handler. Defaults to subprocess.PIPE.
            stderr (Any, optional): Stderr handler. Defaults to subprocess.PIPE.
            debug (bool, optional): Whether to show a command to be run. Defaults to False.

        Returns:
            Union[str, list]: The command output.
        """
        if debug is True:
            print(f"DEBUG: Run command: {cmd}")
        try:
            out = subprocess.run(
                shlex.split(cmd),
                stdout=stdout,
                stderr=stderr,
                check=True,
                text=True,
                timeout=timeout,
            )
        except CalledProcessError:
            raise

        ret: Union[str, list]

        if out.stdout is not None:
            if raw is True:
                ret = out.stdout
            else:
                ret = out.stdout.strip(sep).split(sep)
        else:
            ret = out

        return ret

    def _version(self) -> Optional[Union[str, list]]:
        """Get buildx version.

        Returns:
            Optional[Union[str, list]]: Return buildx version when successfully get the version, None otherwise.
        """
        cmd = f"{self.base_cmd} version"
        try:
            return self._run(cmd, timeout=10)
        except CalledProcessError:
            return None

    def is_executable(self) -> Tuple[bool, str]:
        """Check that docker buildx command is executable.

        Check that buildx is executable by return of docker buildx version.
        If buildx is not installed or not exist in executable path, return the NG message and its reason.

        Returns:
            Tuple[bool, str]: A pair of the result and its reason.
                Return true and OK when the command is executable, false and its reason otherwise.
        """
        if self._version() is not None:
            return True, "OK"

        return (
            False,
            (
                "Docker buildx is not installed or not found in PATH.\n"
                "Make sure that run buildx commands such as 'docker buildx version' with no error.\n"
                "See 'https://docs.docker.com/buildx/working-with-buildx/' for installation."
            ),
        )

    def run(self) -> None:
        """Run build pipeline.

        The build pipeline are executed by the following steps.

        - Check that buildx instance exist used on build. If not exist, create the new one.
        - Build an image on a node under the instance. The image will be pushed to a registry after successfully built.
        - Pull the image from the registry (optional)
        - Remove the instance (optional)

        Raises:
            APIError: Raise when an error occurs while pulling.
        """
        # Check buildx command is executable.
        ok: bool
        ret: Optional[str]

        ok, msg = self.is_executable()
        if ok is not True:
            sys.exit(msg)

        # Instance setup for build.
        if self.instance is None:
            self.instance = self.create(
                driver=self.driver,
                config=self.config_file,
                driver_opt=self.driver_opt,
                buildkitd_flags=self.buildkitd_flags,
                debug=self.debug,
            )
            if self.instance is not None:
                print(f"Build instance '{''.join(self.instance)}' successfully created.")
            else:
                print("fail")
        else:
            if self.instance_exists(self.instance) is True:
                if self.use_existing_instance is True:
                    print(f"Instance {self.instance} already exists. Use this instance.")
                else:
                    print(f"Instance {self.instance} already exists, so will be recreated")
                    self.remove(self.instance)
                    ret = self.create(
                        self.instance,
                        driver=self.driver,
                        config=self.config_file,
                        driver_opt=self.driver_opt,
                        buildkitd_flags=self.buildkitd_flags,
                        debug=self.debug,
                    )
                    if ret is True:
                        print(f"Build instance '{''.join(self.instance)}' successfully created.")
            else:
                ret = self.create(
                    self.instance,
                    driver=self.driver,
                    config=self.config_file,
                    driver_opt=self.driver_opt,
                    buildkitd_flags=self.buildkitd_flags,
                    debug=self.debug,
                )
                if ret is True:
                    print(f"Build instance '{''.join(self.instance)}' successfully created.")

        if self.add_host is not None:
            self.add_host_node(self.node, self.add_host)

        # Build and Push image
        print()
        print("-" * 30 + f"{'Build start':^30}" + "-" * 30)
        ok = self.build(
            self.image_name,
            platform=self.platform,
            label=self.label,
            path=self.path,
            type_=self.type,
            dockerfile=self.dockerfile,
            debug=self.debug,
        )
        print()
        print("-" * 30 + f"{'Build end':^30}" + "-" * 30)

        if ok is True:
            print(f"Image '{self.image_name}' has been created successfully.")
        else:
            print(f"Image '{self.image_name}' failed to be created.")
            if self.remove_instance is True and self.instance is not None:
                if self.remove(self.instance) is True:
                    print(f"Build instance '{self.instance}' successfully removed.")
            sys.exit(1)

        # Pull the image from the registry.
        if self.pull_output is True:
            cl = docker.from_env()
            try:
                cl.images.pull(self.image_name)
                if self.registry is not None:
                    print(f"Image '{self.image_name}' pulled from {self.registry.domain}.")
            except APIError as e:
                if e.response.status == 500:
                    raise APIError(e.response.message.decode())

        Buildkitd().delete()

        # Remove the instance.
        if self.remove_instance is True and self.instance is not None:
            if self.remove(self.instance) is True:
                print(f"Build instance '{self.instance}' successfully removed.")

    def instance_exists(self, name: str) -> bool:
        """Check an instance exists.

        Check that an instance with the specified name already exists by docker build inspace command.

        Args:
            name (str): An instance name.

        Returns:
            bool: Whether the instance exists or not.
        """
        ret = self.inspect(name)
        if ret is not None:
            if re.search(name, ret.get("Name", "")):
                return True
        return False

    def inspect(self, name: str) -> dict:
        """Run docker buildx inspect, return the formatted result.

        Args:
            name (str): An instance name to inspect

        Returns:
            dict: The command result.
        """
        cmd = f"{self.base_cmd} inspect {name}"
        try:
            ret = self._run(cmd)
            if isinstance(ret, list):
                return list2dict(ret)
            else:
                return {}
        except CalledProcessError:
            return {}

    def create(
        self,
        name: Optional[str] = None,
        use: bool = True,
        driver: Optional[str] = None,
        config: Optional[str] = None,
        driver_opt: Optional[dict] = None,
        buildkitd_flags: Optional[dict] = None,
        debug: bool = False,
    ) -> Optional[str]:
        """Create an instance by buildx command.

        Args:
            name (str, optional): An instance name. Defaults to None.
            platform (list, optional): _description_. Defaults to None.
            use (bool, optional): Whether to use a created instance. Defaults to True.
            driver (str, optional): A driver name. Defaults to None.
            config (str, optional): A config filename passed to buildx option. Defaults to None.
            driver_opt (dict, optional): Driver options passed to buildx option. Defaults to None.
            buildkitd_flags (dict, optional): Buildkitd flags passed to buildx option. Defaults to None.
            debug (bool, optional): Whether to show a command to be run. Defaults to False.

        Returns:
            str: An instance name when the instance successfully created, None otherwise.
        """
        options = []

        if name is not None:
            options.append("--name")
            options.append(name)

        if use is True:
            options.append("--use")

        if driver is not None:
            options.append("--driver")
            options.append(driver)

        if config is not None:
            if self.config is not None:
                bk = Buildkitd.load_config(self.config)
                bk.dump()
                options.append("--config")
                options.append(config)

        if driver_opt is not None:
            for k, v in driver_opt.items():
                options.append("--driver-opt")
                options.append(f"{k}={v}")

        if buildkitd_flags is not None:
            for k, v in buildkitd_flags.items():
                options.append("--buildkitd-flags")
                options.append(f"'{k} {v}'")

        cmd = f"{self.base_cmd} create {' '.join(options)} --bootstrap"

        try:
            ret = self._run(cmd, debug=debug)
            return "".join(ret)
        except CalledProcessError as e:
            print(e.stderr)
            return None

    def add_host_node(self, name: str, hosts: dict) -> None:
        """Add hosts into node container.

        Add hosts and ip addresses in /etc/hosts in a node.

        Args:
            name (str): A node name
            hosts (dict): Host and ip address pairs. Keys are hostname and values are ip addresses.
        """
        cl = docker.from_env()
        container = cl.containers.get(name)
        container.start()

        for host, ip in hosts.items():
            container.exec_run(f"sh -c 'echo {ip} {host} >> /etc/hosts'")

    def build(
        self,
        tag: str,
        build_args: Optional[dict] = None,
        label: Optional[dict] = None,
        target: Optional[str] = None,
        dockerfile: Optional[str] = None,
        path: str = ".",
        platform: Optional[list] = None,
        type_: Optional[str] = None,
        debug: bool = False,
    ) -> bool:
        """Build a image, push it to the registry.

        Build a image by docker buildx build command. A tag attached to the image
        must contains the registry to which push the image (for example myregistry.com:5000/myimage:latest).

        Args:
            tag (str): A image name. The name must contains registry to .
            build_args (dict, optional): Build args corresponding to docker build options. Defaults to None.
            label (dict, optional): Labels corresponding to docker build options. Defaults to None.
            target (str, optional): Target stage on multi-stage build corresponding to docker build options.
                Defaults to None.
            dockerfile (str, optional): Dockerfile name. Defaults to None.
            path (str, optional): Path to a directory where Dockerfile exists. Defaults to ".".
            platform (list, optional): Platforms for build. Defaults to None.
            type_ (str, optional): Type for output destination. Defaults to None.
            debug (bool, optional): Whether to show commands to be run. Defaults to None.

        Returns:
            bool: True if successfully build the image and push it to the registry, False otherwise.
        """
        options = []
        options.append("-t")
        options.append(tag)

        if build_args is not None:
            for k, v in build_args.items():
                options.append("--build-args")
                options.append(f"{k}='{v}'")

        if label is not None:
            for k, v in label.items():
                options.append("--label")
                options.append(f"{k}='{v}'")

        if target is not None:
            options.append("--target")
            options.append(target)

        if platform is not None:
            options.append("--platform")
            options.append(",".join(platform))

        if type_ is not None:
            options.append("--output")
            options.append(f"type={type_}")

        if dockerfile is not None:
            if path is not None:
                options.append("--file")
                options.append(str(Path(path) / dockerfile))
                options.append(path)
            else:
                options.append("--file")
                options.append(str(dockerfile))
                options.append(path)
        else:
            if path is not None:
                options.append("--file")
                options.append(str(Path(path) / "Dockerfile"))
                options.append(path)
            else:
                options.append(".")

        cmd = f"{self.base_cmd} build {' '.join(options)}"
        try:
            self._run(cmd, stdout=None, stderr=None, debug=debug)
            return True
        except CalledProcessError as e:
            if e.stderr is not None:
                print(e.stderr)
                return False
            return False

    def remove(self, name: str) -> bool:
        """Remove an instance.

        Args:
            name (str): An instance name.

        Returns:
            bool: Whether an instance was removed.
        """
        cmd = f"{self.base_cmd} rm -f {name}"
        try:
            self._run(cmd)
            return True
        except CalledProcessError as e:
            print(e.stderr)
            return False


BK = TypeVar("BK", bound="Buildkitd")


class Buildkitd:
    def __init__(
        self,
        config: dict = {},
        debug: bool = True,
        http: bool = False,
        registry: Optional[str] = None,
        ca_cert: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
    ) -> None:
        self.debug = debug
        self.http = http
        self.registry = registry
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.config = config
        self.config_file = "buildkitd.toml"

    @classmethod
    def load_config(cls: Type[BK], conf: dict) -> BK:
        """Load properties from config mapping to make an instance."""
        bk = cls()

        reg = conf["registry"]
        host = reg["host"]
        port = reg["port"]
        bk.registry = f"{host}:{port}"
        bk.ca_cert = reg.get("ca_cert")
        bk.client_cert = reg.get("client_cert")
        bk.client_key = reg.get("client_key")

        buildx = conf["buildx"]
        bk.debug = buildx.get("debug", True)
        bk.config = buildx.get("config", {})
        bk.http = bk.config.get("http", False)
        bk.config_file = "buildkitd.toml"

        return bk

    def dump(self) -> None:
        """Make a configuration file used in a buildx node."""
        data = {
            "registry": self.registry,
            "http": self.http,
            "ca_cert": self.ca_cert,
            "client_cert": self.client_cert,
            "client_key": self.client_key,
        }
        templates = Path(__file__).resolve().parent / "data" / "templates"
        toml = templates / "buildkitd.toml.j2"
        output = Path.cwd() / self.config_file
        env = Environment(loader=FileSystemLoader(str(templates), encoding="utf8"))
        tmpl = env.get_template(toml.name)
        render = tmpl.render(data)

        with open(output, "w") as f:
            f.write(render)

    def delete(self) -> None:
        file_ = Path.cwd() / self.config_file
        if file_.exists():
            file_.unlink()


def list2dict(_list: list) -> dict:
    """Convert a list in which each element is dict-like str into a dict.

    Args:
        _list (list): A list to be converted.

    Returns:
        dict: A converted dict.
    """
    return dict(map(str_split, _list))


def str_split(s: str, sep: str = ":") -> Tuple[str, str]:
    """Split a string contains a separator into dict-like key and value.

    A input string must only single separator. Return empty strings
    when containing equal or more than two separators.

    Args:
        s (str): A string to split into dict-like key.
        sep (str, optional): A separator. Defaults to ":".

    Returns:
        Tuple[str, str]: A splitted strings.
    """

    c = s.split(sep)
    if len(c) == 2:
        return c[0].strip(), c[1].strip()
    else:
        return "", ""
