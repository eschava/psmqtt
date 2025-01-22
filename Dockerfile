#
# Builder docker
#

FROM public.ecr.aws/docker/library/python:3.13-alpine AS builder

RUN apk add build-base linux-headers

WORKDIR /build
COPY ./requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --target=/build/deps -r requirements.txt
RUN rm -r requirements.txt

# Cleanup files we dont want to bring over
WORKDIR /build/deps
RUN rm -rf \
    __pycache__ \
    src/__pycache__ \
    pip \
    pip* \
    src/*_test.py \
    psutil/tests


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
COPY src/*.py ./src
COPY psmqtt.service .
COPY logging.conf .

RUN mkdir ./conf ./schema
COPY psmqtt.yaml ./conf
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
ENV PSMQTTCONFIGSCHEMA="/opt/psmqtt/schema/psmqtt.conf.schema.json"

# add deps to PYTHONPATH
ENV PYTHONPATH="/opt/psmqtt/deps"

# run process
CMD ["python", "psmqtt.py"]
