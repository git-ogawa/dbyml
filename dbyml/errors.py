class BuildError(Exception):
    """An Error raised on build."""

    pass


class PushError(Exception):
    """An Error raised when push to a registry"""

    pass


class DockerConnectionError(Exception):
    """An Error raised on connecting to a Docker daemon"""

    pass
