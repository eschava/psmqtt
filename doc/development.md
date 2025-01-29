# Development Topics

## Python linting

For psmqtt development please install `mypy` and `flake8`:

* install these using using `pip`
* `../.vscode/settings.json` takes advantage of these
* `.flake8` and `mypy.ini` control their behavior

## Python Testing

Just do:

```
make unit-tests
```

## Dependencies

* [psutil](https://psutil.readthedocs.io/en/latest/) to retrieve sensor values
* [recurrent](https://github.com/kvh/recurrent) to schedule the actions

## Creating a new release

New docker releases will be automatically published by the GitHub CI whenever a new tag is released on the project.
Sometimes however it may be useful to publish a docker release manually.
To push manually a new multi-arch docker version, use::

```
docker buildx build --platform linux/amd64,linux/arm/v6,linux/arm/v7,linux/arm64/v8, --tag ghcr.io/eschava/psmqtt:1.0.2 --build-arg USERNAME=root --push .
```

(remember to update the tag version)


## TODO

* support MQTTv5?
* add HomeAssistant discovery message support
* restore the ability to request psmqtt tasks from MQTT
* implement batch transmission to MQTT to optimize network and CPU usage
* publish on pypi the project
* improve SMART handler so we can publish current Power_On_Hours attribute .raw_int c and last self-test ".hours" property
