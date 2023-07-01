import sys
import typing

from ..providers.base import ContainerProvider
from .base import ContainersService
from .windows import WindowsContainersService


def make_containers_service(
    provider: typing.Optional[ContainerProvider] = None,
) -> ContainersService:
    if sys.platform == "win32":
        return WindowsContainersService(provider)
    return ContainersService(provider)
