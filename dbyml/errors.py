class BuildError(Exception):
    """An Error raised on build."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
