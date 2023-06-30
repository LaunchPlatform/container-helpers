import dataclasses
import pathlib
import typing

PathType = typing.Union[str, pathlib.Path, pathlib.PurePath]


def make_mount(params: typing.Dict[str, str]) -> str:
    return ",".join(map(lambda item: "=".join(item), params.items()))


def make_mount_args(params: typing.Dict[str, str]) -> typing.Tuple[str, str]:
    return ("--mount", make_mount(params))


def make_annotation_args(annotations: typing.Dict[str, str]) -> typing.Tuple[str, ...]:
    return tuple(
        map(lambda item: "--annotation=" + "=".join(item), annotations.items())
    )


@dataclasses.dataclass
class Mount:
    target: PathType


@dataclasses.dataclass
class BindMount(Mount):
    source: PathType
    readonly: bool
    chown: bool = True
    relabel: typing.Optional[str] = None
    bind_propagation: typing.Optional[str] = None


@dataclasses.dataclass
class VolumeMount(Mount):
    readonly: bool
    chown: bool = True


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
    security_options: typing.Optional[SecurityOptions] = None
