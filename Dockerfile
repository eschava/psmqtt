#
# Builder docker
#

FROM public.ecr.aws/docker/library/python:3.14-alpine AS builder

# NOTE1: build-base and linux-headers are required to build psutil dependency
# NOTE2: git is required to get the "hatch-vcs" plugin to work and produce the _psmqtt_version.py file
RUN apk add build-base linux-headers git

WORKDIR /build
COPY requirements.txt pyproject.toml README.rst ./
COPY ./src ./src/
COPY ./.git ./.git/

RUN python -m pip install --upgrade pip
RUN pip install --target=/build/deps -r requirements.txt
RUN pip install build
RUN python -m build --wheel --outdir /build/wheel


#
# Production docker
#

FROM public.ecr.aws/docker/library/python:3.14-alpine

# when USERNAME=root is provided, the application runs as root within the container, this is useful in case 'pySMART' or any SMART attribute
# has been configured (smartctl requires root permissions)
ARG USERNAME=psmqtt

LABEL org.opencontainers.image.source=https://github.com/f18m/psmqtt

# install pySMART (and bash to ease debug -- TODO get rid of bash)
RUN apk add bash smartmontools

WORKDIR /opt/psmqtt

# copy the dependencies from the builder stage
COPY --from=builder /build/deps ./deps/

# copy all source code
COPY src/psmqtt/*.py ./src/

# copy the version file produced by hatch-vcs plugin from the builder stage:
COPY --from=builder /build/src/_psmqtt_version.py ./src/

RUN mkdir ./conf ./schema
COPY src/psmqtt/schema/* ./schema/

# do not copy the default configuration file: it's better to error out loudly
# if the user fails to bind-mount his own config file, rather than using a default config file.
# the reason is that at least the MQTT broker IP address is something the user
# will need to configure
#COPY psmqtt.yaml ./conf

# add user psmqtt to image
RUN if [[ "$USERNAME" != "root" ]]; then \
    addgroup -S psmqtt && \
    adduser -S ${USERNAME} -G psmqtt && \
    chown -R ${USERNAME}:psmqtt /opt/psmqtt ; \
    fi

# process run as psmqtt user
USER ${USERNAME}

# set conf path
ENV PSMQTTCONFIG="/opt/psmqtt/conf/psmqtt.yaml"
ENV PSMQTTCONFIGSCHEMA="/opt/psmqtt/schema/psmqtt.schema.yaml"

# add deps to PYTHONPATH
ENV PYTHONPATH="/opt/psmqtt/src:/opt/psmqtt/deps"

# run process
# it's important to use python -m to run the module, otherwise the relative imports
# will not work. Remember that the docker image does not contain the actual psmqtt
# wheel installed (this is to make it possible to remove "pip" from the base image in future)
CMD ["python", "-m", "src.main"]
