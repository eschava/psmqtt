# Development Topics

## Python linting

I use `mypy` and `flake8`:

* install these using using `pip`
* `../.vscode/settings.json` takes advantage of these
* `.flake8` and `mypy.ini` control their behavior

## Python Testing

Just do:

```
python3 -m unittest -v src/*_test.py
```

## Dependencies

* [psutil](https://psutil.readthedocs.io/en/latest/) to retrieve sensor values
and
* [recurrent](https://github.com/kvh/recurrent) to schedule the actions

## TODO

* add python typing - DONE
* get rid of import * - DONE
* document use of testing - DONE
* document docker build and run - DONE
* document use as a service - DONE
* reorg files into src directory - DONE
* support MQTTv5?
* use `smartctl` to determine the disk HD temps
