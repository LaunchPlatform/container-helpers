
FROM python:3.11.4-alpine3.18
RUN apk update && apk add --no-cache \
        fuse \
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

RUN mkdir /project
WORKDIR /project

COPY . /project/
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

RUN adduser -D containers
USER containers

ENTRYPOINT ["/init"]
