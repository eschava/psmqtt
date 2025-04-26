# Installing `psmqtt` from pypi

**PSMQTT** is published on [pypi.org](https://pypi.org/project/psmqtt/) as a Python wheel.
This makes it trivial to install it on both

* Windows
* MacOS
* Unix

if you have `pip`, the Python package manager, installed.

If you don't have experience with `pip`, please check out the [official PIP tutorial](https://packaging.python.org/en/latest/tutorials/installing-packages/).

Once you have verified that `pip` works fine on your system you can run:

```sh
pip install psmqtt
```

The command above will download the latest release of **PSMQTT** from [pypi.org](https://pypi.org/project/psmqtt/).
Verify your installation with the commands:

```sh
psmqtt -h
psmqtt --version
```

Then create the config file `psmqtt.yaml` in one of the paths mentioned by the `psmqtt -h` output.
Follow the [usage guide](usage.md) for configuration examples and as configuration reference guide.
