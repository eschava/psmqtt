# Deploying PSMQTT with Docker

**PSMQTT** is also packaged as a multi-arch Docker image. If your system does not have Python3 installed or 
you don't want to install **PSMQTT** Python dependencies in your environment, you can launch
a Docker container:

```sh
docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.yaml \
    --hostname $(hostname) \
    --name psmqtt \
    ghcr.io/eschava/psmqtt:latest
```

## Accessing SMART counters from Docker

The `docker run` command of the previous section works for most use cases, except in case you want to 
publish to the MQTT broker the SMART data for some hard drive.
If that's the case, you will need to launch the docker container with the `--cap-add SYS_RAWIO` flag,
passing all hard drive devices using the `--device` flag and using the `latest-root` tag:

```sh
docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.yaml \
    --hostname $(hostname) \
    --cap-add SYS_RAWIO \
    --device=/dev/<your-hard-drive> \
    --name psmqtt \
    ghcr.io/eschava/psmqtt:latest-root
```

For example if your `/home/user/psmqtt.yaml` file contains references to `/dev/sda` and `/dev/sdb` you may want
to launch **PSMQTT** as:

```sh
docker run -d -v /home/user/psmqtt.yaml:/opt/psmqtt/conf/psmqtt.yaml \
    --hostname $(hostname) \
    --cap-add SYS_RAWIO \
    --device=/dev/sda \
    --device=/dev/sdb \
    --name psmqtt \
    ghcr.io/eschava/psmqtt:latest-root
```

Note the use of the `latest-root` tag instead of the `latest` tag: it's a docker image where
the psmqtt Python utility runs as root. This is necessary in order to access the SMART data of the hard drives.

## Verify psmqtt behavior

First of all, verify the logs of the psmqtt docker:

```sh
docker logs -f psmqtt
```

Finally use [MQTT explorer](http://mqtt-explorer.com/) to verify the sanity and the formatting of the
published data.
