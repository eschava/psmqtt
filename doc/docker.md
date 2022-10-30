# Using Docker to Run `psmqtt`

Verify your docker installation by:

```sh
sudo docker run hello-world
```

## Build `psmqtt` image

```
psmqtt/ > sudo docker build -t "psmqtt:latest" .
```
Verify that the image is built:
```
 > sudo docker image ls
REPOSITORY                             TAG           IMAGE ID       CREATED              SIZE
psmqtt                                 latest        de06300844f9   About a minute ago   63.1MB
public.ecr.aws/docker/library/python   3.11-alpine   5f9e8f452a5c   5 days ago           51.1MB
```

## Execute the `psmqtt` Image in a Container

[Run the image](https://docs.docker.com/engine/reference/commandline/run/) we
created in the above step passing to it your configuration file
(`/opt/psmqtt/psmqtt.conf`)

```
docker run --rm -v /opt/psmqtt/psmqtt.conf:/opt/psmqtt/conf/psmqtt.conf:ro psmqtt
```
