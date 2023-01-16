# docker-build-yaml (dbyml)

![License](https://img.shields.io/github/license/git-ogawa/dbyml)
[![Version](https://img.shields.io/pypi/v/dbyml)](https://pypi.python.org/pypi/dbyml/)
[![Python versions](https://img.shields.io/pypi/pyversions/dbyml)](https://pypi.python.org/pypi/dbyml/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Downloads](https://static.pepy.tech/badge/dbyml)](https://pepy.tech/project/dbyml)

Docker-build-yaml (dbyml) is a CLI tool to build a docker image with build options loaded from yaml. Instead of running the `docker build` with many options, write options in config file, build your docker image with them. It helps you to manage build process more readable and flexible.

# Table of contents
- [Install](#install)
- [Usage](#usage)
  - [Prerequisite](#prerequisite)
  - [Create Dockerfile and Configuration file](#create-dockerfile-and-configuration-file)
  - [Build an image](#build-an-image)
  - [Run using docker](#run-using-docker)
  - [Build-args and Labels](#build-args-and-labels)
  - [(Experimental) Multi-platform build](#experimental-multi-platform-build)
  - [Example](#example)
    - [Settings for registry](#settings-for-registry)
    - [Insecure registry](#insecure-registry)
    - [Self-signed certificates](#self-signed-certificates)
    - [Resolve registry IP](#resolve-registry-ip)
- [Configuration](#configuration)
  - [Config file](#config-file)
    - [Update from v1.2.0](#update-from-v120)
  - [Docker host](#docker-host)
  - [ENV variables](#env-variables)
  - [Multi-stage build](#multi-stage-build)
  - [Push to repository](#push-to-repository)
  - [Using TLS](#using-tls)
  - [Multi-platform build](#multi-platform-build)
  - [Other settings](#other-settings)


# Install
```
$ pip install dbyml
```

# Usage

## Prerequisite
To use dbyml, Docker Engine must be installed on host for build and run docker commands without root privileges (as non-root user) on client. Refer to [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) or [Docker rootless mode](https://docs.docker.com/engine/security/rootless/) for non-root user setting.

## Create Dockerfile and Configuration file
To build your image from Dockerfile, you must make Dockerfile and config file where the build options to be passed to docker command are listed . For example, we will make the following `Dockerfile` and `dbyml.yml` in the same directory.

- Dockerfile
    - Dbyml does not required any settings about Dockerfile, so you can write according to [Dockerfile reference](https://docs.docker.com/engine/reference/builder/).

```Dockerfile
FROM alpine:latest
ARG key1
RUN echo "$key1" > arg.txt && \
    cat arg.txt && \
    rm arg.txt

# You can write any process
```

- dbyml.yml
    - This is a config file used by dbyml.
    - The image name field `name` is required.
    - The image tag field `tag` is optional. Default value is `latest`.
    - To set `ARG key1` in the Dockerfile, Set `build_args` field and key name and its value in config.
```yaml
---
image:
    name: myimage
    tag: v1.0
    build_args:
        key1: "This is set by dbyml."
```


## Build an image
Run dbyml to build the image from your Dockerfile.

```
$ dbyml
```

The image `myimage:v1.0` will be created after successfully build.

If Dockerfile and config file are not in the same directory, you must set path to the Dockerfile with `path` field in the config.
```yaml
---
image:
    name: myimage
    tag: v1.0
    path: path/to/Dockerfile
```

Dbyml has other options for build. See each subsection for more details.

- [Set build-args and labels in image](#build-args-and-labels)
- [Push the image to a private registry](#push-to-repository)
- [Multi-platform build](#experimental-multi-platform-build)


## Run using docker
To run dbyml in docker container, mount the followings paths on host to the container on build.

- `/var/run/docker.sock` required to use the docker engine on host in a container.
- `${PWD}` A directory containing a Dockerfile and dbyml.yml must be mounted in container. See the example below.


Generate a configuration file `dbyml.yml`.
```
$ docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ${PWD}:/work \
  docogawa/dbyml:latest --init -q

# Change owner if needed.
$ sudo chown ${USER}:${USER} dbyml.yml
```

Build a image from Dockerfile and dbyml.yml in the current directory.
```
# Check that Dockerfile and dbyml.yml exist.
$ ls -1 .
Dockerfile
dbyml.yml

# Build a image.
$ docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ${PWD}:/work \
  docogawa/dbyml:latest
```



## Build-args and Labels
If you want to set build-args and labels on building, Set `build-args` and `label` fields as list of key-value pairs in config.

```yaml
---
image:
    name: myimage
    tag: v1.0
    build-args:
        myarg1: aaa
        myarg2: bbb
    label:
        mylabel: ccc
        author: me
        "my.domain.com": corporations
```

The above configuration is corresponding to the following `docker build` command.
```
docker build -t myimage:v1.0 . \
    --build-arg myarg1=aaa --build-arg myarg2=bbb \
    --label mylabel=ccc --label author=me --label my.domain.com=corporations
```


## (Experimental) Multi-platform build
Dbyml can build multi-platform image with docker buildx. At first, you need to install buildx in order to enable this feature (See [docker docs buildx](https://docs.docker.com/buildx/working-with-buildx/) for installation). After installing, make sure that can run buildx commands such as `docker buildx version` with no error.

The multi-platform build on dbyml are executed with docker buildx by the follow steps.

1. Create an instance and node for multi-platform building with `docker buildx create`.
1. Build an image on the node with `docker buildx build`.
1. Push the image to a private registry written in config file.
1. Pull the image from the registry (optional).
1. Remove the instance (optional).

To build your image with multi-platform by dbyml, The `buildx` and the `registry` fields are required in config. See example below.

## Example
If you want to make an image that works for `linux/amd64`, `linux/arm64` and `linux/arm/v7`, Set list of these values in `buildx.platform` in config. The example config is the following. You will make the image with the tag `myregistry:5000/dbyml-sample:latest`, push it to the private registry `myregistry:5000`.

```yaml
image:
  name: dbyml-sample
  path: .
  dockerfile: Dockerfile

registry:
  enabled: true
  host: "myregistry.com"
  port: "5000"

buildx:
  enabled: true
  instance: multi-builder
  use_existing_instance: false
  platform:
    - linux/amd64
    - linux/arm64
    - linux/arm/v7
  type: registry
  pull_output: true
  remove_instance: false
```

If save the configuration above as `dbyml.yml`, you can run simply dbyml command to build the image.
```shell
# In the same directory as dbyml.yml
$ dbyml

# In the different directory
$ dbyml -c path/to/dbyml.yml
```

After successfully building the image, The image `myregistry:5000/dbyml-sample:latest` will be pushed to the registry and pull automatically from the registry on your host when set `pull_output` true. So check that the image manifest includes platforms `amd64`, `arm64` and `arm/v7`.

```yaml
$ docker manifest inspect myregistry:5000/dbyml-sample:latest
{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
   "manifests": [
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 739,
         "digest": "sha256:1bc3ae24a9c6322a628254ad06accf994334f9e9609764d45dc904ae4d8f1a2a",
         "platform": {
            "architecture": "amd64",
            "os": "linux"
         }
      },
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 739,
         "digest": "sha256:4afc068927d499f90f6a8721d0f819daa1654dff3250383fd7300d03855b1e85",
         "platform": {
            "architecture": "arm64",
            "os": "linux"
         }
      },
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 739,
         "digest": "sha256:eca5fe836c0014d253004cc538e3bf3df77a3a897cf62fb15f407cced704336f",
         "platform": {
            "architecture": "arm",
            "os": "linux",
            "variant": "v7"
         }
      }
   ]
}
```


The instance used for build `multi-builder` and its node `multi-builder0` remain after successfully build since set `remove_instance: false` in config. The build caches will be used on the build of the image including the same layers. If automatically remove these instance after build, set `remove_instance: true`.
```
$ docker buildx ls
NAME/NODE        DRIVER/ENDPOINT             STATUS  PLATFORMS
multi-builder *  docker-container
  multi-builder0 unix:///var/run/docker.sock running linux/amd64, linux/amd64/v2, linux/amd64/v3, linux/amd64/v4, linux/386
```

### Settings for registry
The addition fields may be required in config file according to the registry settings.

### Insecure registry
If the registry are insecure such as HTTP registry, set `config.http: true` under `buildx` field in config file as below.
```yaml
registry:
  enabled: true
  host: "my-insecure-registry.com"
  port: "5000"

buildx:
  enabled: true
  instance: multi-builder
  use_existing_instance: false
  platform:
    - linux/amd64
    - linux/arm64
    - linux/arm/v7
  type: registry
  pull_output: true
  remove_instance: false
  config:
    http: true
```

### Self-signed certificates
If the registry uses self-signed certificates, set path to the CA certificate in `ca_cert` under `registry` field in config file as below.
```yaml
registry:
  enabled: true
  host: "self-signed_registry.com"
  port: "5000"
  ca_cert: certs/ca_cert.pem

buildx:
  enabled: true
  instance: multi-builder
  use_existing_instance: false
  platform:
    - linux/amd64
    - linux/arm64
    - linux/arm/v7
  type: registry
  pull_output: true
  remove_instance: false
```

### Resolve registry IP
Build and push are executed on buildx node (docker container), so the node may fail to resolve IP address of the registry. There are two ways to resolve it.

1. Set `driver_opt.network: host` under `buildx` field in config file as below. With this config, hosts in `/etc/hosts` on host will be added into /etc/hosts in the node.
1. Set List of hostname and ip address in `add_host` under`buildx` field in config file. The list will be addedd into `/etc/hosts` in the node.

```yaml
registry:
  enabled: true
  host: "myregistry.com1"
  port: "5000"

buildx:
  enabled: true
  instance: multi-builder
  use_existing_instance: false
  platform:
    - linux/amd64
    - linux/arm64
    - linux/arm/v7
  type: registry
  pull_output: true
  remove_instance: false
  driver_opt:
    network: host
  add_host:
    myregistry.com1: 192.168.3.100
```



# Configuration
The behavior of dbyml is managed by the config file written in yaml syntax.


## Config file
Dbyml automatically searches for config file `dbyml.yml` or `dbyml.yaml` in the execution directory. If you want to use other filename or path, you need run dbyml with `-c` option to specify path to the config.

```
$ dbyml -c [path_to_config_file]
```


To gerenate a sample config to build your docker image in local, run `dbyml --init`. The config `dbyml.yml` will be generated in the current directory by interactively specifying the values of the fields. You can edit the contents of the config later.
```
$ dbyml --init
```

Run `dbyml` with `--init -q` options to generate the config non-interactively.
```
$ dbyml --init -q
```

### Update from v1.2.0
The contents and syntax in config file has changed since v1.3.0. To Run `--convert` option in order to convert old config to the new one. The converted config `dbyml.yml` will be generated, so edit it according to your configuration.

```
$ dbyml --convert [path/to/old/config]
```


## Docker host
Docker_host under image field specify a docker daemon to connect from client. The default value is `unix:/var/run/docker.sock`, which means connect to docker daemon on local. Set hostname (or ip address) including protocol and port if you want to build your image on remote docker host.

```yaml
# Example
image:
    # Connect to docker daemon on local.
    docker_host: "unix:/var/run/docker.sock"

    # Connect to 10.10.10.20:2375 with tcp.
    # docker_host: "tcp://10.10.10.20:2375"
```



## ENV variables
You can use environment variable expressions in config. `${VAR_NAME}` and setting default_value `${VAR_NAME:-default_value}` are supported. Error occurs when the specified env is undefined.

```yaml
image:
    name: ${BASEIMAGE_NAME}
    tag: ${VERSION:-latest}
```

## Multi-stage build
`Target` field specify the name of the phase to build in multi-stage builds. See [Use multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/) for more details on multi-stage builds.

```yaml
image:
    name: myimage
    tag: v1.0
    target: init-stage
```


## Push to repository
Dbyml supports to push the image to [docker registry v2](https://hub.docker.com/_/registry) in local.


To push the image to be built from your Dockerfile, The `registry` fields are required in config. You must set the hostname (or ip address) and port of the registry. Setting `enabled` to true enables these settings. Setting to false disables the settings, which means dose not push the image after building.

```yaml
image:
    name: myimage
    tag: v1.0

registry:
    enabled: true
    host: "myregistry" # Registry hostname or ip address
    port: "5000" # Registry port
```

Running `dbyml` with the config will make the docker image `myimage:v1.0`, then push it to the registry as the image name of `myregistry:5000/myimage:v1.0`.
You can check that the image has been successfully pushed to the registry such as [registry API](https://docs.docker.com/registry/spec/api/).


If you want to add more hierarchy in repository, set `namespace` field in config. The image will be pushed as `{hostname}:{port}/{namespace}/{name}:{tag}`.

```yaml
image:
    name: myimage
    tag: v1.0

registry:
    enabled: true
    host: "myregistry" # Registry hostname or ip address
    port: "5000" # Registry port
    namespace: myspace
```


If you use the basic authentication to access to the registry build by [Native basic auth](https://docs.docker.com/registry/deploying/#native-basic-auth), you need set `username` and `password` fields under push in the config.

```yaml
image:
    name: myimage
    tag: v1.0

registry:
    enabled: true
    username: ${username}
    password: ${password}
    host: "myregistry" # Registry hostname or ip address
    port: "5000" # Registry port
```


## Using TLS
To build your image on docker host using TLS (HTTPS), Set the paths to the CA certificate, client certificate and key in each field and enabled to true under `tls` field. See [Docker documentation](https://docs.docker.com/engine/security/protect-access/#use-tls-https-to-protect-the-docker-daemon-socket) about connection to TLS docker daemon.

```yaml
tls:
  enabled: true
  ca_cert: ca.pem
  client_cert: cert.pem
  client_key: key.pem
```

## Multi-platform build
Dbyml uses [docker buildx](https://github.com/docker/buildx) for multi-platform build. The settings about are managed by `buildx` section in config file. The supported fields are below. See [sample.yml](sample/sample.yml#L121) to check how to write these values.

| key | type | required | description |
| - | - | - | - |
| enabled | bool | required | Whether to enable buildx |
| type | str | required | Output type of build image. Only `registry` is supported now. |
| platform | list | required | List of platforms |
| instance | str | optional | An instance name used on build |
| use_existing_instance | bool | optional | Whether to use the instance with the same name as specified in `instance` field if exists. When false, the instance will be recreated. |
| pull_output | bool | optional | Whether to pull the image from the registry after build. |
| remove_instance | bool | optional | Whether to remove an instance after build. |


## Other settings
See [sample.yml](sample/sample.yml) for supported fields.
