import asyncio.subprocess
import contextlib
import copy
import pathlib
import shutil
import tempfile
import typing

from ..data_types import BindMount
from ..data_types import Container
from ..data_types import Mount
from ..data_types import PathType
from .base import ContainersService
from .base import DEFAULT_LIMIT


def to_wsl_path(path: pathlib.Path):
    if not isinstance(path, pathlib.WindowsPath):
        raise ValueError(f"Expected windows path but got {path.__class__} instead")
    new_path = pathlib.Path(path)
    if new_path.drive == "":
        return new_path.as_posix()
    _, *parts = new_path.parts
    return str(
        pathlib.PurePosixPath("/mnt", new_path.drive.rstrip(":").lower(), *parts)
    )


def is_unc_path(path: PathType) -> bool:
    path = pathlib.Path(path)
    return path.drive.startswith("\\")


class WindowsContainersService(ContainersService):
    @contextlib.asynccontextmanager
    async def _make_temp_copy(
        self, src: typing.Optional[pathlib.Path], suffix: typing.Optional[str] = None
    ) -> typing.AsyncContextManager[pathlib.Path]:
        # Only copy if the drive is provided and a UNC path
        if src is not None and is_unc_path(src):
            with (
                open(src, "rb") as src_file,
                tempfile.NamedTemporaryFile(suffix=suffix) as temp_file,
            ):
                self.logger.debug(
                    "Make a temp copy of seccomp profile from %s to native windows filesystem at %s",
                    src,
                    temp_file.name,
                )
                shutil.copyfileobj(src_file, temp_file)
                temp_file.flush()
                yield pathlib.Path(temp_file.name)
        else:
            yield src

    @contextlib.asynccontextmanager
    async def _copy_readonly_unc_mounts(
        self,
        mounts: typing.List[Mount],
    ) -> typing.AsyncContextManager[typing.List[Mount]]:
        with tempfile.TemporaryDirectory() as temp_folder:
            temp_folder_path = pathlib.Path(temp_folder)
            new_mounts = []
            for i, mount in enumerate(mounts):
                if (
                    not isinstance(mount, BindMount)
                    or not is_unc_path(mount.source)
                    or not mount.readonly
                ):
                    new_mounts.append(mount)
                    continue
                new_source = temp_folder_path / f"mount-{i}"
                self.logger.info(
                    "Copy readonly UNC mount from %s to %s", mount.source, new_source
                )
                shutil.copytree(mount.source, new_source)
                mount.source = new_source
                new_mounts.append(mount)
            yield new_mounts

    @contextlib.asynccontextmanager
    async def run(
        self,
        container: Container,
        stdin: typing.Optional[int] = None,
        stdout: typing.Optional[int] = None,
        stderr: typing.Optional[int] = None,
        runtime_env: typing.Optional[dict] = None,
        limit: int = DEFAULT_LIMIT,
        log_level: typing.Optional[str] = None,
    ) -> typing.AsyncContextManager[asyncio.subprocess.Process]:
        container = copy.deepcopy(container)

        seccomp_profile = None
        if (
            container.security_options is not None
            and container.security_options.seccomp is not None
        ):
            seccomp_profile = container.security_options.seccomp
        # Under windows, if the project is living in WSL, the seccomp profile file path
        # might look like this:
        # \\wsl$\Ubuntu-18.04\home\user\workspace\my-project\seccomp-profiles\git.json
        # And it's not going to work with podman, so we need to make a temp copy into
        # native windows file system
        async with (
            self._make_temp_copy(
                seccomp_profile, suffix=".json"
            ) as temp_seccomp_profile,
            self._copy_readonly_unc_mounts(container.mounts) as new_mounts,
        ):
            if temp_seccomp_profile is not None:
                # Not only we need to copy to native window filesystem, we also
                # need to convert it into WSL path for podman in the podman WSL machine
                # to read
                # ref: https://github.com/containers/podman/issues/14494
                container.security_options.seccomp = to_wsl_path(temp_seccomp_profile)
            container.mounts = new_mounts
            async with super().run(
                container=container,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                runtime_env=runtime_env,
                limit=limit,
                log_level=log_level,
            ) as proc:
                yield proc
