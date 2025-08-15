import asyncio.subprocess
import copy
import dataclasses
import sys
import typing

import pytest

from containers import Container
from containers import ContainersService
from containers import ImageMount as _ImageMount
from containers import Mount
from containers import Podman as _Podman
from containers import WindowsContainersService as _WindowsContainersService
from containers.data_types import PathType
from containers.services.base import DEFAULT_LIMIT
from containers.services.windows import to_wsl_path

ARCHIVE_HOOK_PREFIX = "com.launchplatform.oci-hooks.archive-overlay."
CHOWN_HOOK_PREFIX = "com.launchplatform.oci-hooks.mount-chown."


@dataclasses.dataclass
class ImageMount(_ImageMount):
    archive_to: typing.Optional[PathType] = None
    archive_success: typing.Optional[PathType] = None
    archive_method: typing.Optional[str] = None
    archive_tar_content_owner: typing.Optional[str] = None
    chown: typing.Optional[str] = None
    chown_policy: typing.Optional[str] = None
    mode: typing.Optional[int] = None


def make_annotation_args(annotations: typing.Dict[str, str]) -> typing.Tuple[str, ...]:
    args = []
    for env_arg in map(lambda item: "=".join(item), annotations.items()):
        args.append("--annotation")
        args.append(env_arg)
    return tuple(args)


class Podman(_Podman):
    def make_overlay_archive_annotations(
        self, image_mount: ImageMount, name: typing.Optional[str] = None
    ) -> typing.Tuple[str, ...]:
        if image_mount.archive_to is None:
            return tuple()
        if name is None:
            name = self._make_unique_mount_name()
        args = {
            f"{ARCHIVE_HOOK_PREFIX}{name}.mount-point": str(image_mount.target),
            f"{ARCHIVE_HOOK_PREFIX}{name}.archive-to": str(image_mount.archive_to),
        }
        if image_mount.archive_success is not None:
            args[f"{ARCHIVE_HOOK_PREFIX}{name}.success"] = str(
                image_mount.archive_success
            )
        if image_mount.archive_method is not None:
            args[f"{ARCHIVE_HOOK_PREFIX}{name}.method"] = str(
                image_mount.archive_method
            )
        if image_mount.archive_tar_content_owner is not None:
            args[f"{ARCHIVE_HOOK_PREFIX}{name}.tar-content-owner"] = str(
                image_mount.archive_tar_content_owner
            )
        return make_annotation_args(args)

    def make_mount_chown_annotations(
        self, image_mount: ImageMount, name: typing.Optional[str] = None
    ) -> typing.Tuple[str, ...]:
        if image_mount.chown is None and image_mount.mode is None:
            return tuple()
        if name is None:
            name = self._make_unique_mount_name()
        annotations = {
            f"{CHOWN_HOOK_PREFIX}{name}.path": str(image_mount.target),
        }
        if image_mount.chown is not None:
            annotations[f"{CHOWN_HOOK_PREFIX}{name}.owner"] = image_mount.chown
        if image_mount.chown_policy is not None:
            annotations[f"{CHOWN_HOOK_PREFIX}{name}.policy"] = image_mount.chown_policy
        if image_mount.mode is not None:
            annotations[f"{CHOWN_HOOK_PREFIX}{name}.mode"] = f"{image_mount.mode:o}"
        return make_annotation_args(annotations)

    def make_image_mount(self, mount: ImageMount, name: typing.Optional[str] = None):
        args = super().make_image_mount(mount, name)
        if isinstance(mount, ImageMount):
            return (
                *args,
                *self.make_overlay_archive_annotations(image_mount=mount, name=name),
                *self.make_mount_chown_annotations(image_mount=mount, name=name),
            )
        return args


class WindowsContainersService(_WindowsContainersService):
    def _filter_mount(self, mount: Mount) -> Mount:
        if not isinstance(mount, ImageMount):
            return mount
        if mount.archive_to is None:
            return mount
        mount = copy.deepcopy(mount)
        mount.archive_to = to_wsl_path(mount.archive_to)
        if mount.archive_success is not None:
            mount.archive_success = to_wsl_path(mount.archive_success)
        return mount

    def run(
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
        container.mounts = list(map(self._filter_mount, container.mounts))
        return super().run(
            container=container,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            limit=limit,
            log_level=log_level,
        )


@pytest.fixture
def podman() -> Podman:
    return Podman()


@pytest.fixture
def containers(podman: Podman) -> ContainersService:
    if sys.platform == "win32":
        return WindowsContainersService(podman)
    return ContainersService(podman)
