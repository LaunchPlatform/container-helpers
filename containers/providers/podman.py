import functools
import pathlib
import typing
import uuid

from ..data_types import BindMount
from ..data_types import Container
from ..data_types import ImageMount
from ..data_types import Mount
from ..data_types import SecurityOptions
from ..data_types import VolumeMount
from .base import ContainerProvider
from .helpers import make_env_args
from .helpers import make_mount_args


class Podman(ContainerProvider):
    def __init__(self, executable: pathlib.Path = pathlib.Path("podman")):
        self.executable = executable

    def _make_unique_mount_name(self) -> str:
        return uuid.uuid4().hex

    def make_image_mount(self, mount: ImageMount, name: typing.Optional[str] = None):
        params = {
            "type": "image",
            "source": str(mount.source),
            "target": str(mount.target),
            "rw": str(mount.read_write).lower(),
        }
        return make_mount_args(params)

    def make_bind_mount(self, mount: BindMount, name: typing.Optional[str] = None):
        params = {
            "type": "bind",
            "source": str(mount.source),
            "target": str(mount.target),
            "chown": str(mount.chown).lower(),
            "readonly": str(mount.readonly).lower(),
        }
        if mount.relabel is not None:
            params["relabel"] = mount.relabel
        if mount.bind_propagation is not None:
            params["bind-propagation"] = mount.bind_propagation
        return make_mount_args(params)

    def make_volume_mount(self, mount: VolumeMount, name: typing.Optional[str] = None):
        params = {
            "type": "volume",
            "target": str(mount.target),
            "chown": str(mount.chown).lower(),
        }
        # Any value appears with ro or readonly key makes it readonly, it's a bug
        # of podman
        # ref: https://github.com/containers/podman/issues/18995
        if mount.readonly:
            params["readonly"] = str(mount.readonly).lower()
        return make_mount_args(params)

    def make_mount(
        self, mount: Mount, name: typing.Optional[str] = None
    ) -> typing.Tuple[str, ...]:
        if isinstance(mount, ImageMount):
            return self.make_image_mount(mount, name=name)
        elif isinstance(mount, BindMount):
            return self.make_bind_mount(mount, name=name)
        elif isinstance(mount, VolumeMount):
            return self.make_volume_mount(mount, name=name)
        else:
            raise ValueError("Unknown mount type %s", mount.__class__)

    def make_security_options(
        self, security_options: SecurityOptions
    ) -> typing.Tuple[str, ...]:
        args = []
        if security_options.no_new_privileges:
            args.extend(["--security-opt", "no-new-privileges:true"])
        if security_options.seccomp is not None:
            args.extend(["--security-opt", f"seccomp={security_options.seccomp}"])
        return tuple(args)

    def build_command(
        self, container: Container, log_level: typing.Optional[str] = None
    ) -> typing.Tuple[str, ...]:
        shared_args = []
        if log_level is not None:
            shared_args.append("--log-level")
            shared_args.append(log_level)
        base_args = (
            str(self.executable),
            *shared_args,
            "run",
        )

        env_args = make_env_args(container.environ)

        interactive_args = tuple()
        if container.interactive:
            interactive_args = ("--interactive",)

        tty_args = tuple()
        if container.tty:
            tty_args = ("--tty",)

        remove_args = tuple()
        if container.remove:
            remove_args = ("--rm",)

        timeout_args = tuple()
        if container.timeout is not None:
            timeout_args = ("--timeout", str(container.timeout))

        user_args = tuple()
        if container.user is not None:
            user_group = str(container.user)
            if container.group is not None:
                user_group += f":{container.group}"
            user_args = ("--user", user_group)

        work_dir_args = tuple()
        if container.work_dir is not None:
            work_dir_args = ("--workdir", str(container.work_dir))

        network_args = tuple()
        if container.network is not None:
            network_args = ("--network", container.network)

        security_options_args = tuple()
        if container.security_options is not None:
            security_options_args = self.make_security_options(
                container.security_options
            )

        mount_args = tuple(
            functools.reduce(
                lambda lhs, rhs: lhs + rhs,
                map(
                    lambda item: self.make_mount(item[1], name=f"mount-{item[0]}"),
                    enumerate(container.mounts),
                ),
                tuple(),
            )
        )
        args = (
            *base_args,
            *interactive_args,
            *tty_args,
            *remove_args,
            *timeout_args,
            *env_args,
            *user_args,
            *work_dir_args,
            *network_args,
            *security_options_args,
            *mount_args,
            container.image,
            *container.command,
        )
        return args
