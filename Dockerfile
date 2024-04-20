FROM public.ecr.aws/docker/library/python:3.11-alpine AS builder

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

FROM public.ecr.aws/docker/library/python:3.11-alpine
RUN apk add bash smartmontools

WORKDIR /opt/psmqtt
COPY --from=builder /build .

RUN mkdir ./src
COPY *.py ./
COPY src/*.py ./src
COPY psmqtt.service .
COPY logging.conf .

RUN mkdir ./conf
COPY psmqtt.conf ./conf

# add user psmqtt to image
#RUN addgroup -S psmqtt && adduser -S psmqtt -G psmqtt
#RUN chown -R psmqtt:psmqtt /opt/psmqtt

# process run as psmqtt user
#USER psmqtt

# set conf path
ENV PSMQTTCONFIG="/opt/psmqtt/conf/psmqtt.conf"

# add deps to PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/opt/psmqtt/deps"

# run process
CMD python psmqtt.py
