import dataclasses
import pathlib
import typing

PathType = typing.Union[str, pathlib.Path, pathlib.PurePath]


@dataclasses.dataclass
class Mount:
    target: PathType


@dataclasses.dataclass
class BindMount(Mount):
    source: PathType
    readonly: bool
    chown: bool = False
    relabel: typing.Optional[str] = None
    bind_propagation: typing.Optional[str] = None


@dataclasses.dataclass
class VolumeMount(Mount):
    readonly: bool
    chown: bool = False


@dataclasses.dataclass
class ImageMount(Mount):
    source: str
    read_write: bool = False


@dataclasses.dataclass
class SecurityOptions:
    no_new_privileges: bool = False
    seccomp: typing.Optional[PathType] = None


@dataclasses.dataclass
class Container:
    image: str
    command: typing.Tuple[str, ...]
    interactive: bool = False
    tty: bool = False
    remove: bool = False
    environ: typing.Dict[str, str] = dataclasses.field(default_factory=dict)
    work_dir: typing.Optional[PathType] = None
    mounts: typing.List[Mount] = dataclasses.field(default_factory=list)
    user: typing.Optional[str] = None
    group: typing.Optional[str] = None
    network: typing.Optional[str] = None
    timeout: typing.Optional[int] = None
    security_options: typing.Optional[SecurityOptions] = None
