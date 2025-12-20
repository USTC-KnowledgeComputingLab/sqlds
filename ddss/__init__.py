from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ddss")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "unknown"
