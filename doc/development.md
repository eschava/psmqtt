# Development Topics

## Python linting

For psmqtt development please install `mypy` and `flake8`:

* install these using using `pip`
* `../.vscode/settings.json` takes advantage of these
* `.flake8` and `mypy.ini` control their behavior

It's suggested to use 

```sh
make test-wheel
```

to test how the project will work in a real installation (via Pypi in this case).


## Python Testing

Just do:

```sh
make unit-tests
```

or 

```sh
make integration-tests
```


## Dependencies

See the [requirements.txt](requirements.txt) file

## Creating a new release

New docker releases will be automatically published by the GitHub CI whenever a new tag is released on the project.
Sometimes however it may be useful to publish a docker release manually.
To push manually a new multi-arch docker version, use::

```sh
docker buildx build --platform linux/amd64,linux/arm/v6,linux/arm/v7,linux/arm64/v8, --tag ghcr.io/eschava/psmqtt:<new-tag> --build-arg USERNAME=root --push .
```

(remember to update the tag version)

## TODO

* support MQTTv5?
* restore the ability to request psmqtt tasks from MQTT
* implement batch transmission to MQTT to optimize network and CPU usage
