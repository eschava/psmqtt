FROM public.ecr.aws/docker/library/python:3.10-alpine AS builder

RUN apk add build-base linux-headers

WORKDIR /build
COPY ./requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --target=/build/deps -r requirements.txt
RUN rm -r requirements.txt 

# Cleanup files we dont want to bring over
WORKDIR /build/deps
RUN find . -type f -name "*.pyc" -delete
RUN rm -rf __pycache__ pip pip* psutil/tests

FROM public.ecr.aws/docker/library/python:3.10-alpine
RUN apk add bash

WORKDIR /opt/psmqtt
COPY --from=builder /build .
COPY *.py ./
COPY psmqtt.service .
COPY logging.conf .

# add user psmqtt to image
RUN addgroup -S psmqtt && adduser -S psmqtt -G psmqtt
RUN chown -R psmqtt:psmqtt /opt/psmqtt

# process run as psmqtt user
USER psmqtt

# set conf path
ENV PSMQTTCONFIG="/opt/psmqtt/conf/psmqtt.conf"

# add deps to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/opt/psmqtt/deps"

# run process
CMD python psmqtt.py