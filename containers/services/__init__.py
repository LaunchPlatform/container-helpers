import sys

from .base import ContainersService
from .windows import WindowsContainersService


def make_containers_service() -> ContainersService:
    if sys.platform == "win32":
        return WindowsContainersService()
    return ContainersService()
