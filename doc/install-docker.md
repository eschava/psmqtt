# Deploying PSMQTT with Docker

**PSMQTT** is also packaged as a multi-arch Docker image. If your system does not have Python3 installed or 
you don't want to install **PSMQTT** Python dependencies in your environment, you can launch
a Docker container::

   docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      ghcr.io/eschava/psmqtt:latest

This works for most use cases, except in case you want to publish to the MQTT broker the SMART data
for some hard drive.
If that's the case, you will need to launch the docker container with the `--cap-add SYS_RAWIO` flag,
passing all hard drive devices using the `--device` flag and using the `latest-root` tag::

   docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      --cap-add SYS_RAWIO \
      --device=/dev/<your-hard-drive> \
      ghcr.io/eschava/psmqtt:latest-root

For example if your `/home/user/psmqtt.conf` file contains references to `/dev/sda` and `/dev/sdb` you may want
to launch **PSMQTT** as::

   docker run -d -v /home/user/psmqtt.conf:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      --cap-add SYS_RAWIO \
      --device=/dev/sda \
      --device=/dev/sdb \
      ghcr.io/eschava/psmqtt:latest-root

Note the use of the `latest-root` tag instead of the `latest` tag: it's a docker image where
the psmqtt Python utility runs as root. This is necessary in order to access the SMART data of the hard drives.
