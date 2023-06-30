# container-helpers
Helpers for running docker or podman containers easily in Python

## Install

```bash
pip install container-helpers
```

## Usage

Basic data types are provided in the `containers` package.
You can use them to construct a container and build the command line for running that container easily.
For example

```python
from containers import Container
from containers import Podman

container = Container(
    image="my-image",
    command=("git", "status"),
    environ=dict(ENV_VAR0="VAL0", ENV_VAR1="VAL1"),
)
podman = Podman()
command = podman.build_command(container)
print(command)
```

Then you get the command for running the container like this as a tuple:

```bash
podman run --env ENV_VAR0=VAL0 --env ENV_VAR1=VAL1 my-image git status
```

With the command, you can then use [subprocess](https://docs.python.org/3/library/subprocess.html) or other module to run it.
A more complex container can be easily constructed with different data types, like one with image mounts or bind mounts.

```python
from containers import Container
from containers import ImageMount
from containers import BindMount

Container(
    image="my-image",
    command=("git", "log", "-l3"),
    mounts=[
        ImageMount(
            target="/data",
            source="git-repo-data:write",
            read_write=True,
        ),
        BindMount(
            target="/artifacts",
            source="/var/tmp/artifacts",
            readonly=False,
            relabel="private",
            bind_propagation="rslave"
        ),
    ],
)
# ...
```

For more options, please see the `data_types.py` module.
At this moment, we only support the options needed for [LaunchPlatform](https://launchplatform.com) projects.
And the only container cli we support for now is [podman](https://podman.io).
While the most of the command generated from this package should also work for [docker](https://docker.com), but we never really tested it.
Please feel free to submit PRs for extending the package.

### Run the container with ContainersService

From time to time, we found ourselves in needs of a service for starting the container with some setting up and tearing down work.
If you happen to have similar needs, `ContainersService` comes pretty handy.
You can run your container like this:

```python
import asyncio
import asyncio.subprocess

from containers import Container
from containers import ImageMount
from containers import BindMount
from containers import ContainersService

service = ContainersService()

async def run():
    container = Container(
        image="alpine",
        command=("/path/to/my/exe", "arg0", "arg1"),
        mounts=[
            ImageMount(
                target="/data",
                source="my-data",
                read_write=True,
            ),
            BindMount(
                target="/artifacts",
                source="/var/tmp/artifacts",
                readonly=False,
                relabel="private",
                bind_propagation="rslave"
            ),
        ],
    )
    async with service.run(container, stdout=asyncio.subprocess.PIPE) as proc:
        stdout = await proc.stdout.read()
        code = await proc.wait()
        if code != 0:
            raise RuntimeError("Failed")
        # ... 

```

With the context manager, we can easily manipulate the container and make some preparation before running it and tear down after the container is done.
For example, under Windows, if you are running the container with a seccomp profile with a WSL UNC path, podman won't be able to access the seccomp profile file.

```python
import asyncio
import copy
import typing
import pathlib
import contextlib
import tempfile
import shutil

from containers import Container
from containers import ContainersService
from containers.data_types import PathType


def _to_wsl_path(path: pathlib.Path):
    if not isinstance(path, pathlib.WindowsPath):
        raise ValueError(f"Expected windows path but got {path.__class__} instead")
    new_path = pathlib.Path(path)
    if new_path.drive == "":
        return new_path.as_posix()
    _, *parts = new_path.parts
    return str(
        pathlib.PurePosixPath("/mnt", new_path.drive.rstrip(":").lower(), *parts)
    )


def _is_unc_path(path: PathType) -> bool:
    path = pathlib.Path(path)
    return path.drive.startswith("\\")



class WindowsContainersService(ContainersService):
    @contextlib.asynccontextmanager
    async def _make_temp_copy(
        self, src: typing.Optional[pathlib.Path], suffix: typing.Optional[str] = None
    ) -> typing.AsyncContextManager[pathlib.Path]:
        # Only copy if the drive is provided and a UNC path
        if src is not None and _is_unc_path(src):
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
    async def run(
        self,
        container: Container,
        stdin: typing.Optional[int] = None,
        stdout: typing.Optional[int] = None,
        stderr: typing.Optional[int] = None,
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
        async with self._make_temp_copy(seccomp_profile, suffix=".json") as temp_seccomp_profile:
            if temp_seccomp_profile is not None:
                # Not only we need to copy to native window filesystem, we also
                # need to convert it into WSL path for podman in the podman WSL machine
                # to read
                # ref: https://github.com/containers/podman/issues/14494
                container.security_options.seccomp = _to_wsl_path(temp_seccomp_profile)
            async with super().run(container, stdin, stdout, stderr, log_level) as proc:
                yield proc

```

This is just an example shows that it's very powerful to use a context manager for running your container in Python.
This allows us to work around many issues while dealing with different quirk of the container in different platform.
We actually provide the `WindowsContainerService` in the package for working around problems we saw:

 - Automatically make a temp copy of seccomp profile with a WSL UNC path and use the temp copy instead
 - Automatically make a temp copy of a readonly UNC mount path and use the temp copy instead

You can import and use it directly, or use `make_containers_service` to create the container service based on your current operating system.
