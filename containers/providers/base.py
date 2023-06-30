import typing

from ..data_types import Container


class ContainerProvider:
    def build_command(self, container: Container) -> typing.Tuple[str, ...]:
        raise NotImplementedError()
