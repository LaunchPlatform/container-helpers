import asyncio.subprocess
import pathlib
import tarfile

import pytest

from .conftest import ImageMount
from containers import BindMount
from containers import Container
from containers import ContainersService


async def poll_success_file(target_file: pathlib.Path):
    while not target_file.exists():
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_load_image(containers: ContainersService):
    await containers.load_image("alpine")


@pytest.mark.asyncio
async def test_run(containers: ContainersService):
    container = Container(command=("echo", "hello"), image="alpine")
    async with containers.run(container, stdout=asyncio.subprocess.PIPE) as proc:
        stdout = await proc.stdout.read()
        assert stdout == "hello\n".encode("utf8")
        assert await proc.wait() == 0


@pytest.mark.asyncio
async def test_run_with_image_mount(containers: ContainersService):
    data_image = "alpine:3.18.2"
    await containers.load_image(data_image)
    image_mount = ImageMount(source=data_image, target="/data")
    container = Container(
        command=("ls", "/data"), image="alpine:3.18.2", mounts=[image_mount]
    )
    async with containers.run(container, stdout=asyncio.subprocess.PIPE) as proc:
        stdout = await proc.stdout.read()
        folders = frozenset(
            filter(lambda item: bool(item.strip()), stdout.decode("utf8").split("\n"))
        )
        assert folders == frozenset(
            {
                "bin",
                "dev",
                "etc",
                "home",
                "lib",
                "media",
                "mnt",
                "opt",
                "proc",
                "root",
                "run",
                "sbin",
                "srv",
                "sys",
                "tmp",
                "usr",
                "var",
            }
        )
        assert await proc.wait() == 0


@pytest.mark.asyncio
async def test_run_with_bind_mount(
    tmp_path: pathlib.Path, containers: ContainersService
):
    data_image = "alpine:3.18.2"
    await containers.load_image(data_image)

    mount_dir = tmp_path / "data"
    mount_dir.mkdir()
    file0 = mount_dir / "my-file0.txt"
    file0.write_text("hello")
    file1 = mount_dir / "nested" / "my-file1.txt"
    file1.parent.mkdir(parents=True, exist_ok=True)
    file1.write_text("there")

    bind_mount = BindMount(source=mount_dir, target="/data", readonly=False)
    container = Container(
        command=("/bin/sh", "-c", "touch /data/new && ls /data"),
        image="alpine:3.18.2",
        mounts=[bind_mount],
    )
    async with containers.run(container, stdout=asyncio.subprocess.PIPE) as proc:
        stdout = await proc.stdout.read()
        folders = frozenset(
            filter(lambda item: bool(item.strip()), stdout.decode("utf8").split("\n"))
        )
        assert folders == frozenset(
            {
                "my-file0.txt",
                "nested",
                "new",
            }
        )
        assert await proc.wait() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "disable_ovl_white_out",
    [
        False,
        True,
    ],
)
async def test_run_with_runtime_env(
    tmp_path: pathlib.Path, containers: ContainersService, disable_ovl_white_out: bool
):
    data_image = "alpine:3.18.2"
    await containers.load_image(data_image)
    archive_target = tmp_path / "archive.tar.gz"
    archive_success = tmp_path / "archive.success"
    image_mount = ImageMount(
        source=data_image,
        target="/data",
        archive_to=archive_target,
        archive_method="tar.gz",
        archive_success=archive_success,
        read_write=True,
    )
    container = Container(
        command=("rm", "/data/bin/sh"),
        image="alpine:3.18.2",
        mounts=[image_mount],
    )
    if disable_ovl_white_out:
        runtime_env = dict(FUSE_OVERLAYFS_DISABLE_OVL_WHITEOUT="y")
    else:
        runtime_env = None
    async with containers.run(
        container, runtime_env=runtime_env, log_level="debug"
    ) as proc:
        assert (await proc.wait()) == 0

    await asyncio.wait_for(poll_success_file(archive_success), 5)
    with tarfile.open(archive_target) as tar:
        if not disable_ovl_white_out:
            device = tar.getmember("./bin/sh")
            assert device.type == tarfile.CHRTYPE
            assert device.devmajor == 0
            assert device.devminor == 0
        else:
            whiteout = tar.getmember("./bin/.wh.sh")
            assert whiteout.type == tarfile.REGTYPE
