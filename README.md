# docker-build-yaml (dbyml)

![License](https://img.shields.io/github/license/git-ogawa/dbyml)
[![Version](https://img.shields.io/pypi/v/dbyml)](https://pypi.python.org/pypi/dbyml/)
[![Python versions](https://img.shields.io/pypi/pyversions/dbyml)](https://pypi.python.org/pypi/dbyml/)


docker-build-yaml (dbyml) is a CLI tool to build a docker image with arguments loaded from yaml. Instead of running the `docker build` with many options, write options in config file, build your docker image with them. It helps you to manage build process more readable and flexible.

# Install 
```
pip install dbyml
```

# Usage

## Preparation
Dbyml is useful for building your docker image. To build an image, you must make your Dockerfile and config file where the build arguments are listed. For example, we will make the example `Dockerfile` and `dbyml.yml` in the same directory.

- Dockerfile
    - Dbyml does not required any settings about Dockerfile, so you can write according to [Dockerfile reference](https://docs.docker.com/engine/reference/builder/).

```Dockerfile
FROM alpine:latest
ARG key1
RUN echo key1
# You can write any process
```

- dbyml.yml
    - This is a config file used by dbyml.
    - The image name field `name` is required. 
    - The image tag field `tag` is optional. Default value is `latest`.
```yaml
---
name: myimage
tag: v1.0
```


## Build 
Run dbyml to build the image from your Dockerfile. 

```
dbyml 
```

If Dockerfile and config file are not in the same directory, you must set path to the Dockerfile with `path` field in the config.
```yaml
---
name: myimage
tag: v1.0
path: path/to/Dockerfile
```

# Configuration
The behavior of dbyml is managed by the config file written in yaml syntax. 
## Config file
Dbyml automatically searches for config file `dbyml.yml` or `dbyml.yaml` in the execution directory. If you want to use other filename or path, you need run dbyml with `-c` option to specify path to the config.

```
dbyml -c [path_to_config_file]
```

## ENV variables
You can use environment variable expressions in config. `${VAR_NAME}` and setting default_value `${VAR_NAME:-default_value}` are supported. Error occurs when the specified env is undefined.

```yaml
---
name: ${BASEIMAGE_NAME}
tag: ${VERSION:-latest}
```

## Push to repository
Dbyml supports to push the image to [docker registry v2](https://hub.docker.com/_/registry) in local. 


To push the image to be built from your Dockerfile, The `push` fields are required in config. You must set the hostname (or ip address) and port of the registry. Setting `enabled` to true enables these settings. Setting to false disables the settings, which means dose not push the image after building.

```yaml
---
name: myimage
tag: v1.0

push:
    enabled: true
    registry:
        host: "myregistry" # Registry hostname or ip address 
        port: "5000" # Registry port
```

Running `dbyml` with the config will make the docker image `myimage:v1.0`, then push it to the registry as the image name of `myregistry:5000/myimage:v1.0`.
You can check that the image has been successfully pushed to the registry such as [registry API](https://docs.docker.com/registry/spec/api/).


If you want to add more hierarchy in repository, set `namespace` field in config. The image will be pushed as `{hostname}:{port}/{namespace}/{name}:{tag}`.

```yaml
---
name: myimage
tag: v1.0

push:
    enabled: true
    registry:
        host: "myregistry" # Registry hostname or ip address 
        port: "5000" # Registry port
    namespace: myspace
```


If you use the basic authentication to access to the registry build by [Native basic auth](20ce6d8ea24dc425342a13cc06b6afed58e71419), you need set `username` and `password` fields under push in the config. 

```yaml
---
name: myimage
tag: v1.0

push:
    enabled: true
    username: ${username}
    password: ${password}
    registry:
        host: "myregistry" # Registry hostname or ip address 
        port: "5000" # Registry port
```

## other settings
See [sample.yml](sample/sample.yml) for supported fields.
