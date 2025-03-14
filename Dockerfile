# ref: https://github.com/containers/podman/blob/main/contrib/podmanimage/stable/Containerfile
FROM python:3.11.11-alpine3.21
RUN apk update && apk add --no-cache \
        uv \
        fuse3 \
        fuse-overlayfs \
        podman \
        s6-overlay \
        s6-overlay-syslogd

ARG _REPO_URL="https://raw.githubusercontent.com/containers/podman/v4.5.1/contrib/podmanimage/stable"
ADD $_REPO_URL/containers.conf /etc/containers/containers.conf
ADD $_REPO_URL/podman-containers.conf /home/podman/.config/containers/containers.conf

# Copy & modify the defaults to provide reference if runtime changes needed.
# Changes here are required for running with fuse-overlay storage inside container.
RUN sed -e 's|^#mount_program|mount_program|g' \
           -e '/additionalimage.*/a "/var/lib/shared",' \
           -e 's|^mountopt[[:space:]]*=.*$|mountopt = "nodev,fsync=0"|g' \
           /usr/share/containers/storage.conf \
           > /etc/containers/storage.conf

ADD https://github.com/LaunchPlatform/oci-hooks-archive-overlay/releases/download/2.0.4/archive_overlay /usr/bin/archive_overlay
ADD https://github.com/LaunchPlatform/oci-hooks-mount-chown/releases/download/1.0.7/mount_chown /usr/bin/mount_chown
RUN chmod +x /usr/bin/mount_chown && \
    chmod +x /usr/bin/archive_overlay
RUN mkdir -p /usr/share/containers/oci/hooks.d/
COPY ./docker/containers/*.json /usr/share/containers/oci/hooks.d/

RUN mkdir /project
WORKDIR /project

COPY . /project/
RUN uv sync

# Note VOLUME options must always happen after the chown call above
# RUN commands can not modify existing volumes
VOLUME /var/lib/containers

RUN mkdir -p /var/lib/shared/overlay-images \
             /var/lib/shared/overlay-layers \
             /var/lib/shared/vfs-images \
             /var/lib/shared/vfs-layers && \
    touch /var/lib/shared/overlay-images/images.lock && \
    touch /var/lib/shared/overlay-layers/layers.lock && \
    touch /var/lib/shared/vfs-images/images.lock && \
    touch /var/lib/shared/vfs-layers/layers.lock

ENTRYPOINT ["/init"]
