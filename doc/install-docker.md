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

Please note that to ensure correct behavior of the internal `psutil` and `pySMART` libraries used
by **PSMQTT** you might need to use additional flags. 
In the next sections a few use cases are analyzed.

## Measuring disk usage from Docker

In case you want to use the [disk_usage task](./usage.md#category-disks) to report the disk usage
at some path, you will need to bind-mount that particular path using `--volume` option.
E.g. if you want to measure the disk usage of the root folder `/` you can use:


```sh
docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.yaml \
    --hostname $(hostname) \
    --volume /:/host/root:ro \
    --name psmqtt \
    ghcr.io/eschava/psmqtt:latest
```

and in your `psmqtt.yaml` use e.g.:

```yaml
  ...
  - cron: "every 60 minutes"
    tasks:
      - task: disk_usage
        params: [ percent, "/host/root" ]
  ...
```

## Accessing SMART counters from Docker

In case you want to publish to the MQTT broker the SMART data for some hard drive using the 
[smart task](./usage.md#category-disks),
you will need to launch the docker container with the `--cap-add SYS_RAWIO` flag and also
provide all hard drive devices using `--device` flags.
Finally, instead of selecting the `latest` tag, the `latest-root` tag must be selected:

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

## Accessing Network Interfaces from Docker

In case you want to monitor network-related I/O counters using the 
[net_io_counters task](./usage.md#category-network),
you probably want to measure the network I/O that is happening on the physical network interfaces,
rather than the `eth0` interface that is created by Docker inside the PSMQTT docker container.
To achieve that, you will need to remove the Docker network isolation using the `--network=host` flag:

```sh
docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.yaml \
    --hostname $(hostname) \
    --network=host \
    --name psmqtt \
    ghcr.io/eschava/psmqtt:latest
```

Also note that Docker (and also other software programs) will create a lot of `veth` devices 
and the network traffic on these interfaces is typically not what you want to monitor. So it's strongly
suggested that you add a network interface card selector for the `net_io_counters` task declared in your
`psmqtt.yaml`.

## Verify psmqtt behavior

First of all, verify the logs of the psmqtt docker:

```sh
docker logs -f psmqtt
```

Finally use [MQTT explorer](http://mqtt-explorer.com/) to verify the sanity and the formatting of the
published data.

## Docker Compose

Docker compose can also be used as alternative way to start **PSMQTT**.
Here is an example of the `docker-compose.yml` file that can be used to monitor CPU/memory/disk_usage/HDD SMART counters:

```yaml
services:
  psmqtt:
    image: ghcr.io/eschava/psmqtt:latest-root
    restart: unless-stopped
    stop_grace_period: 10s
    # setting the network_mode to "host" will allow PSMQTT to monitor traffic
    # on the physical network interfaces (eth0, enp0s0f0 and similar...)
    network_mode: "host"
    cap_add:
      # SYS_RAWIO allows to monitor SMART counters
      - SYS_RAWIO
    devices:
      # PSMQTT needs access to all devices whose SMART counters will be monitored
      - "/dev/sda:/dev/sda"
      - "/dev/sdb:/dev/sdb"
    volumes:
      # map a local "./configs" folder containing the "psmqtt.yaml" file
      # to the container internal "/opt/psmqtt/conf" folder
      - "./configs:/opt/psmqtt/conf:ro"
      # a volume mapping is necessary for each "disk_usage" task:
      - "/:/host/root:ro"
      - "/usr/share/hassio/media/frigate:/host/frigate:ro"
```

You can save the YAML example above as `docker-compose.yml` on your machine and then use

```sh
docker compose up -d
docker logs -f psmqtt-psmqtt-1
```

to start **PSMQTT** and check its logs.

