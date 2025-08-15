import asyncio.subprocess
import contextlib
import logging
import shlex
import typing

from containers import Container
from containers import ContainerProvider
from containers import Podman

# ref: https://github.com/python/cpython/blob/4e08a9f97a172aa47fbed661c3cb8a9d36d43931/Lib/asyncio/streams.py#L23
# the default used in CPython's stream implementation
DEFAULT_LIMIT = 2**16  # 64 KiB


class ContainersService:
    def __init__(
        self,
        provider: typing.Optional[ContainerProvider] = None,
    ):
        self.provider = provider or Podman()
        self.logger = logging.getLogger(__name__)

    async def load_image(
        self,
        image: str,
        always_pull: bool = False,
        credentials: typing.Optional[typing.Tuple[str, str]] = None,
    ):
        # TODO: abstract this to provider instead
        if not always_pull:
            command = (
                str(self.provider.executable),
                "image",
                "inspect",
                image,
            )
            self.logger.debug("Running image inspect command %s", " ".join(command))
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            code = await proc.wait()
            if code == 0:
                return
            self.logger.debug("Image %s not found, pulling now ...", image)
        command = (
            str(self.provider.executable),
            "pull",
            image,
        )
        log_command = (
            *command,
            *(("--creds", "<REDACTED>") if credentials is not None else tuple()),
        )
        self.logger.debug(
            "Pulling image %s with command %s", image, " ".join(log_command)
        )
        full_command = (
            *command,
            *(
                ("--creds", ":".join(credentials))
                if credentials is not None
                else tuple()
            ),
        )
        proc = await asyncio.create_subprocess_exec(
            *full_command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        stderr: asyncio.StreamReader = proc.stderr
        stderr_content = await stderr.read()
        code = await proc.wait()
        if code != 0:
            self.logger.error(
                "Failed to load image %s with code=%s, stderr=%s",
                image,
                code,
                stderr_content,
            )
            raise RuntimeError(f"Failed to load image {image} with code {code}")
        self.logger.info("Image %s loaded", image)

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
        command = self.provider.build_command(container, log_level=log_level)
        self.logger.info(
            "Run container with command: %s, runtime_env=%s",
            " ".join(map(shlex.quote, command)),
            runtime_env,
        )
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=runtime_env,
            limit=limit,
        )
        yield proc
