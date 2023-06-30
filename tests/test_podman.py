import typing

import pytest

from containers import BindMount
from containers import Container
from containers import ImageMount
from containers import Podman


def parse_mount_options(options: str) -> typing.Dict[str, str]:
    return dict(map(lambda item: tuple(item.split("=")), options.split(",")))


@pytest.fixture
def podman() -> Podman:
    return Podman()


@pytest.mark.parametrize(
    "mount, expected_args",
    [
        (
            ImageMount(
                source="image-repo/my-image:write", target="/data", read_write=True
            ),
            (
                "--mount",
                "type=image,source=image-repo/my-image:write,target=/data,rw=true",
            ),
        ),
    ],
)
def test_image_mount_args(
    podman: Podman,
    mount: ImageMount,
    expected_args: typing.Tuple[str, ...],
):
    assert podman.make_mount(mount) == expected_args


@pytest.mark.parametrize(
    "mount, expected_args",
    [
        (
            BindMount(
                source="/var/tmp/artifacts",
                target="/artifacts",
                readonly=False,
                relabel="private",
                bind_propagation="rslave",
                chown=True,
            ),
            (
                "--mount",
                ",".join(
                    [
                        "type=bind",
                        "source=/var/tmp/artifacts",
                        "target=/artifacts",
                        "chown=true",
                        "readonly=false",
                        "relabel=private",
                        "bind-propagation=rslave",
                    ]
                ),
            ),
        ),
    ],
)
def test_bind_mount_args(
    podman: Podman,
    mount: BindMount,
    expected_args: typing.Tuple[str, ...],
):
    assert podman.make_mount(mount) == expected_args


@pytest.mark.parametrize(
    "container, expected_args",
    [
        (
            Container(
                image="my-image",
                command=("git", "status"),
            ),
            ("podman", "run", "my-image", "git", "status"),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                network="none",
            ),
            ("podman", "run", "--network", "none", "my-image", "git", "status"),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                interactive=True,
            ),
            ("podman", "run", "--interactive", "my-image", "git", "status"),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                remove=True,
            ),
            ("podman", "run", "--rm", "my-image", "git", "status"),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                environ=dict(ENV_VAR0="VAL0", ENV_VAR1="VAL1"),
            ),
            (
                "podman",
                "run",
                "--env",
                "ENV_VAR0=VAL0",
                "--env",
                "ENV_VAR1=VAL1",
                "my-image",
                "git",
                "status",
            ),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                user="2000",
                group="3000",
            ),
            ("podman", "run", "--user", "2000:3000", "my-image", "git", "status"),
        ),
        (
            Container(
                image="my-image",
                command=("git", "status"),
                work_dir="/my-dir",
            ),
            ("podman", "run", "--workdir", "/my-dir", "my-image", "git", "status"),
        ),
        (
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
            ),
            (
                "podman",
                "run",
                "--mount",
                "type=image,source=git-repo-data:write,target=/data,rw=true",
                "--mount",
                "type=bind,source=/var/tmp/artifacts,target=/artifacts,chown=true,readonly=false,relabel=private,bind-propagation=rslave",
                "my-image",
                "git",
                "log",
                "-l3",
            ),
        ),
    ],
)
def test_build_command(
    podman: Podman,
    container: Container,
    expected_args: typing.Tuple[str, ...],
):
    assert podman.build_command(container) == expected_args
