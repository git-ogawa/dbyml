import json
import os
import re
import sys
import textwrap
from pathlib import Path
from pprint import pprint
from typing import Optional, Union

import docker.models.images
from docker import APIClient
from docker.errors import APIError, DockerException, ImageNotFound
from ruamel.yaml import YAML

from dbyml.errors import BuildError, DockerConnectionError, PushError
from dbyml.registry import Registry


class DockerImage:
    def __init__(self, config_file: Optional[Union[str, Path]] = None) -> None:
        self.config_file = config_file
        if self.config_file is not None:
            self.load_conf(self.config_file)

    def load_dict(self, param: dict, set_param: bool = True) -> None:
        self.config = self.parse_config(param)
        if set_param is True:
            self.set_param(self.config)
            self.set_client()

    def load_conf(self, path: Union[str, Path], set_param: bool = True) -> None:
        """Loads the settings from config file.

        Args:
            path (str): Path to the config file.
            set_param (bool, optional): Set the settings to the attributes. Defaults to True.
        """
        with open(path, "r") as f:
            self.config = self.parse_config(YAML().load(f))
        if set_param is True:
            self.set_param(self.config)
            self.set_client()

    def set_client(self) -> None:
        """Set docker client."""
        if self.tls_enabled is True:
            for f in [self.ca_cert, self.client_cert, self.client_key]:
                if f is not None:
                    if not Path(f).exists():
                        raise FileNotFoundError(f"{f} not found.")

            tls_config = docker.tls.TLSConfig(ca_cert=self.ca_cert, client_cert=(self.client_cert, self.client_key))
        else:
            tls_config = None

        try:
            self.client = docker.from_env()
            self.apiclient = APIClient(base_url=self.docker_host, tls=tls_config)
        except DockerException as e:
            raise DockerConnectionError(e.args[0])

    # def check_connection(self):

    def parse_config(self, config: dict) -> dict:
        """Parse values in config file.

        Detect environment variables in the config, replace these to the os env values.

        Args:
            config (dict): the config parameters.

        Returns:
            dict: The parsed config.
        """
        config_str = json.dumps(config)
        envs = re.findall(r"\$\{.+?\}", config_str)
        for e in envs:
            config_str = config_str.replace(e, self.parse_env(e))
        return json.loads(config_str)

    def parse_env(self, env_name: str) -> str:
        e = env_name.strip("${}")
        comp = re.split(":-*", e)
        if len(comp) == 1:
            return self.get_env(comp[0])
        elif len(comp) == 2:
            return os.getenv(comp[0], comp[1])
        else:
            raise SyntaxError(f"ENV {env_name} is invalid format.")

    def get_env(self, env: str) -> str:
        """Get the environment value.

        Args:
            env (str): The ENV name.

        Raises:
            KeyError: The ENV value dose not be defined.

        Returns:
            str: The ENV value.
        """
        v = os.getenv(env)
        if v is None:
            raise KeyError(f"ENV ${{{env}}} not defined.")
        else:
            return v

    def set_param(self, config: dict) -> None:
        # Image section
        image = self.config.get("image", {})
        try:
            self.name = image["name"]
        except KeyError:
            sys.exit("Field 'name' is required in config file.")
        self.tag = image.get("tag", "latest")
        self.image_name = f"{self.name}:{self.tag}"
        build_dir = image.get("path", None)
        if build_dir is None:
            self.build_dir = Path.cwd()
        else:
            self.build_dir = Path(build_dir).resolve()
        dockerfile = image.get("dockerfile", "Dockerfile")
        self.dockerfile = self.build_dir / dockerfile
        self.build_args = image.get("build_args", {})
        self.label = image.get("label", {})
        self.docker_host = image.get("docker_host", None)

        # Build section
        build = self.config.get("build", {})
        self.target = build.get("target", "")
        self.stdout = build.get("stdout", True)
        self.no_cache = build.get("no_cache", False)
        self.remove_intermediate_container = build.get("remove_intermediate_container", True)
        self.force_rm = build.get("force_rm", True)
        self.remove_dangling = build.get("remove_dangling", False)
        self.verbose = build.get("verbose", False)

        # Registry section
        registry = self.config.get("registry", {})
        if any(registry):
            self.enabled = registry.get("enabled", True)
            self.username = registry.get("username", "")
            self.password = registry.get("password", "")
            self.auth = {"username": self.username, "password": self.password}
            self.registry = Registry(
                registry.get("protocol", "http"),
                registry.get("host", ""),
                registry.get("port", ""),
                self.name,
                self.tag,
                registry.get("namespace", ""),
                self.username,
                self.password,
            )
            self.remove_local = registry.get("remove_local", True)
        else:
            self.enabled = False

        # TLS section
        tls = self.config.get("tls", {})
        if any(tls):
            self.tls_enabled = tls.get("enabled", False)
            self.ca_cert = tls.get("ca_cert")
            self.client_cert = tls.get("client_cert")
            self.client_key = tls.get("client_key")
        else:
            self.tls_enabled = False

        # Buildx section
        bx = self.config.get("buildx", {})
        if any(bx):
            self.buildx_enabled = bx.get("enabled", False)
        else:
            self.buildx_enabled = False

    def check_dockerfile(self) -> bool:
        """Check that dockerfile to build an image exists.

        Raises:
            FileNotFoundError: Raise if the dockerfile does not exist.

        Returns:
            bool: True when the dockerfile exists.
        """
        if self.dockerfile.exists():
            return True
        else:
            raise FileNotFoundError(f"{self.dockerfile} does not exist.")

    def info(self) -> None:
        """Show build information"""
        print()
        print("-" * 30 + f"{'Build information':^30}" + "-" * 30)
        info = textwrap.dedent(
            f"""\
            {'build_dir':<30} {self.build_dir}
            {'dockerfile':<30} {self.dockerfile.name}
            {'image name':<30} {self.image_name}
            """
        )
        info += self.dict_info("build_args", self.build_args)
        info += self.dict_info("label", self.label)
        info += f"{'push to registry':<30} {self.enabled}"
        if self.enabled is True:
            info += "\n"
            info += f"{'registry':<30} {self.registry.domain}\n"
            info += f"{'pushed image':<30} {self.registry.repository}"

        print(info)
        print("-" * 90)
        print()

    def dict_info(self, title: str, _dict: dict) -> str:
        if not any(_dict):
            return f"{title:<30} {_dict}\n"

        values = ""
        for i, (key, value) in enumerate(_dict.items()):
            if i == 0:
                values += f"{title:<30} {{'{key}': '{value}'}}\n"
            else:
                values += f"{'':<30} {{'{key}': '{value}'}}\n"
        return values

    def build(self) -> None:
        """Build a docker image.

        Raises:
            BuildError: Raised when catch an error message from docker API during build.
        """
        if self.verbose is True:
            self.info()
        self.check_dockerfile()
        if self.remove_dangling is True:
            try:
                self.remove_local_image(self.image_name)
            except ImageNotFound as e:
                print(f"{e} .... skip.")

        if self.stdout is True:
            print()
            print("-" * 30 + f"{'Build start':^30}" + "-" * 30)
            for line in self.apiclient.build(
                path=str(self.build_dir),
                dockerfile=self.dockerfile.name,
                tag=self.image_name,
                buildargs=self.build_args,
                labels=self.label,
                rm=self.remove_intermediate_container,
                forcerm=self.force_rm,
                decode=True,
                target=self.target,
                nocache=self.no_cache,
            ):
                for k, v in line.items():
                    if k == "error":
                        print("\033[31mAn error has occurred. The details of the error are following.\033[0m")
                        raise BuildError(v)
                    else:
                        if v != "\n":
                            if isinstance(v, str):
                                print(v.strip("\n"))
                            else:
                                print(v)
            print()
            print("-" * 30 + f"{'Build end':^30}" + "-" * 30)
            print()
            print(f"Image '{self.image_name}' has been created successfully.")
        else:
            ret = self.client.images.build(
                path=str(self.build_dir),
                dockerfile=self.dockerfile.name,
                tag=self.image_name,
                buildargs=self.build_args,
                labels=self.label,
                rm=self.remove_intermediate_container,
                forcerm=self.force_rm,
                target=self.target,
                nocache=self.no_cache,
            )
            if ret:
                print(f"Image '{self.image_name}' has been created successfully.")

    def push(self) -> None:
        """Push a docker image to the registry."""
        self.get_image()
        self.docker_tag()
        if self.stdout is True:
            print()
            print("-" * 30 + f"{'Push start':^30}" + "-" * 30)

            counter = 0
            for line in self.apiclient.push(
                repository=self.registry.repository,
                auth_config=self.auth,
                decode=True,
                stream=True,
            ):
                if line.get("status") == "Pushing":
                    # Show message every 20 lines to reduce output.
                    if counter > 20:
                        counter = 0
                        print(line)
                    else:
                        counter += 1
                else:
                    err = line.get("errorDetail")
                    if err is not None:
                        print("\033[31mAn error has occurred. The details of the error are following.\033[0m")
                        raise PushError(err)
                    else:
                        print(line)

            print()
            print("-" * 30 + f"{'Push end':^30}" + "-" * 30)
            print()
            print(f"Image '{self.image_name}' has been created successfully.")
        else:
            ret = self.client.images.push(self.registry.repository, auth_config=self.auth)
            print()
            print("-" * 25 + f"{'Push result':^25}" + "-" * 25)
            pprint(ret)
            print("-" * 60)
            print()

        if self.remove_local is True:
            self.remove_local_image(self.registry.repository)

    def get_image(self) -> Optional[docker.models.images.Image]:
        try:
            self.image = self.client.images.get(self.image_name)
            return self.image
        except ImageNotFound:
            print(f"Image '{self.image_name}' not found.")
            return None

    def pull(self, name: str, auth: dict = {}) -> None:
        """Pull a docker image from the registry.

        Auth parameters must be set when pull a docker image from the registry that requires basic authentication.
        The format of the auth must be {"username": yourname, "password": yourpassword}.

        Args:
            name (str): The name of the docker image to pull. The name should include a tag.
            auth (dict, optional): Auth credentials to access the registry. Defaults to {}.

        Raises:
            APIError: Raises when the docker api error occurs.
        """
        try:
            ret = self.apiclient.pull(name, auth_config=self.auth)
            print()
            print("-" * 30 + f"{'pull result':^30}" + "-" * 30)
            pprint(ret)
            print("-" * 90)
            print()
        except APIError as e:
            if e.response.status == 500:
                raise APIError(e.response.message.decode())

    def docker_tag(self) -> None:
        """Add tag to the image"""
        ret = self.image.tag(self.registry.repository)
        if ret is True:
            print(f"Image '{self.registry.repository}' has been created successfully.")

    def remove_local_image(self, name: str) -> None:
        try:
            self.client.images.remove(name)
            print(f"Image '{name}' has been successfully removed from local.")
        except ImageNotFound:
            raise ImageNotFound(message=f"Image '{name}' not found.")
