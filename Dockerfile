#
# Builder docker
#

FROM public.ecr.aws/docker/library/python:3.13-alpine AS builder

RUN apk add build-base linux-headers 

WORKDIR /build
COPY ./requirements.txt .
COPY ./pyproject.toml .
COPY ./src .
COPY ./README.rst .
RUN python -m pip install --upgrade pip
#RUN pip install --target=/build/deps -r requirements.txt
RUN pip install build
RUN python -m build
#RUN rm -r requirements.txt


#
# Production docker
#

FROM public.ecr.aws/docker/library/python:3.13-alpine

# when USERNAME=root is provided, the application runs as root within the container, this is useful in case 'pySMART' or any SMART attribute
# has been configured (smartctl requires root permissions)
ARG USERNAME=psmqtt

LABEL org.opencontainers.image.source=https://github.com/f18m/psmqtt

RUN apk add bash smartmontools

WORKDIR /opt/psmqtt
COPY --from=builder /build .

RUN mkdir ./src
COPY *.py ./
COPY src/psmqtt/*.py ./src

RUN mkdir ./conf ./schema

# do not copy the default configuration file: it's better to error out loudly
# if the user fails to bind-mount his own config file.
# the reason is that at least the MQTT broker IP address is something the user
# will need to configure
#COPY psmqtt.yaml ./conf

COPY schema/* ./schema/

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
ENV PYTHONPATH="/opt/psmqtt/deps"

# run process
CMD ["python", "psmqtt.py"]
