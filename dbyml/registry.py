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
        namespace: str = "",
        username: str = "",
        password: str = "",
    ) -> None:
        self.protocol = protocol
        self.host = host
        self.port = port
        self.domain = f"{self.host}:{self.port}"
        self.name = name
        self.tag = tag
        self.image_name = f"{self.name}:{self.tag}"

        self.namespace = namespace
        if self.namespace != "":
            self.url = f"{self.protocol}://{self.domain}/v2/{self.namespace}/{self.name}/manifests/{self.tag}"
            self.repository = f"{self.domain}/{self.namespace}/{self.image_name}"
        else:
            self.url = (
                f"{self.protocol}://{self.domain}/v2/{self.name}/manifests/{self.tag}"
            )
            self.repository = f"{self.domain}/{self.name}"

        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(self.username, self.password)

        self.headers = {
            "Accept": "application/vnd.docker.distribution.manifest.v2+json"
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
