import re
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth


class Registry:
    def __init__(
        self,
        protocol: str = "http",
        host: str = "",
        port: str = "",
        name: str = "",
        tag: str = "",
        namespace: Optional[str] = None,
        username: str = "",
        password: str = "",
        certs: dict = {},
    ) -> None:
        self.protocol = protocol
        self.host = host
        self.port = port
        self.domain = f"{self.host}:{self.port}"
        self.name = name
        self.tag = typecheck(tag, "latest")
        self.image_name = f"{self.name}:{tag}"
        self.namespace = namespace
        if self.namespace is not None and self.namespace != "":
            self.url = f"{self.protocol}://{self.domain}/v2/{self.namespace}/{self.name}/manifests/{self.tag}"
            self.repository = f"{self.domain}/{self.namespace}/{self.image_name}"
        else:
            self.url = (
                f"{self.protocol}://{self.domain}/v2/{self.name}/manifests/{self.tag}"
            )
            self.repository = f"{self.domain}/{self.name}:{self.tag}"

        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(self.username, self.password)

        self.headers = {
            "Accept": "application/vnd.docker.distribution.manifest.v2+json"
        }

        self.certs = {
            "ca_cert": certs.get("ca-cert"),
            "client_key": certs.get("client-key"),
            "client_cert": certs.get("client-cert"),
        }

    def get_digest(self) -> Optional[str]:
        ret = requests.get(self.url, headers=self.headers, auth=self.auth)
        if ret.status_code == 200:
            return ret.headers.get("Docker-Content-Digest")
        else:
            return None

    def remove_repo_image(self) -> None:
        self.digest = self.get_digest()
        if self.digest is not None:
            # Put the digest into url.
            url = re.sub(r"/[^/]+$", f"/{self.digest}", self.url)
            ret = requests.delete(url, headers=self.headers, auth=self.auth)
            if ret.status_code == 202:
                print(
                    f"{self.repository} has been successfully removed from repository."
                )
            else:
                print(f"{self.repository} cannot be removed. ...skip.")
        else:
            print(f"{self.image_name} not found in {self.domain}.")


def typecheck(str_: Optional[str], default: str) -> str:
    if str_ is None:
        return default
    elif str_ == "":
        return default
    else:
        return str_
