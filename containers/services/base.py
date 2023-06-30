import asyncio.subprocess
import contextlib
import logging
import shlex
import typing

from containers import Container
from containers import Podman


class ContainersService:
    def __init__(self):
        self.podman = Podman()
        self.logger = logging.getLogger(__name__)

    async def load_image(self, image: str, always_pull: bool = False):
        if not always_pull:
            command = (
                str(self.podman.executable),
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
            str(self.podman.executable),
            "pull",
            image,
        )
        self.logger.debug("Pulling image %s with command %s", image, " ".join(command))
        proc = await asyncio.create_subprocess_exec(
            *command,
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
        log_level: typing.Optional[str] = "debug",
    ) -> typing.AsyncContextManager[asyncio.subprocess.Process]:
        command = self.podman.build_command(container, log_level=log_level)
        self.logger.info("Run container with command: %s", " ".join(map(shlex.quote, command)))
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        yield proc
