# Installing `psmqtt` from source

This documentation describes how to install psmqtt using [pip](https://pip.pypa.io/en/stable/installing/) and virtual environments.

## Prerequisites

Check `python`:
```
python3 --version
Python 3.12.9
```
Check `pip`:
```
python3 -m pip
```

If you get an error like `/usr/bin/python3: No module named pip`, then install `pip`:
```
apt install python3-pip
```
Then:
```
# python3 -m pip --version
pip 23.2.1 from /usr/lib/python3/dist-packages/pip (python 3.12)
```

Check you have `smartctl` installed:
```sh
smartctl --scan
/dev/sda -d scsi # /dev/sda, SCSI device
/dev/sdb -d scsi # /dev/sdb, SCSI device
/dev/nvme0 -d nvme # /dev/nvme0, NVMe device
```
If not, please install [smartmontools](https://www.smartmontools.org/wiki/Download).

## Installation inside a virtual environment (preferred way)

Since Debian 12 (Bookworm) Python defaults to using [virtual environments](https://docs.python.org/3/library/venv.html) for modules installed with pip. 
They also strongly recommend keeping it as an "externally-managed-environment".

To proceed, first clone the repository by running
```
git clone https://github.com/eschava/psmqtt.git
cd psmqtt
```
If you haven't already done so, you should create a directory for your virtual environments. Debian uses `~/.venvs` so this is what is used here.
The following command creates a new folder and venv named psmqtt.
```
python3 -m venv ~/.venvs/psmqtt
```
Then activate the venv:
```
source ~/.venvs/psmqtt/bin/activate
```

You should now see "(psmqtt)" reported in your prompt to indicate that you're now running commands within the venv.
Then install psmqtt and all its required dependencies

```
pip3 install .
```

If pip is able to download and install all dependencies and build locally `psmqtt`, then you should see at the end a message like: 

```
Successfully installed certifi-2025.7.14 chardet-5.2.0 charset_normalizer-3.4.2 docker-7.1.0 humanfriendly-10.0 idna-3.10 jinja2-3.1.6 paho-mqtt-2.1.0 parsedatetime-2.6 platformdirs-4.3.7 psmqtt-2.5.1 psutil-7.0.0 pysmart-1.4.1 python-dateutil-2.9.0.post0 python-dotenv-1.1.1 pyyaml-6.0.2 recurrent-0.4.1 requests-2.32.4 testcontainers-4.9.2 types-paho-mqtt-1.6.0.20240321 typing-extensions-4.14.1 urllib3-2.5.0 wrapt-1.17.2 yamale-6.0.0
```

Note that `psmqtt` appears in the list of "successfully installed" packages.
You are now ready to run psmqtt.

## Installation without using a virtual environment

If for some reason you don't want to install psmqtt dependencies inside a virtual environment ("venv" in short), just run:

```
git clone https://github.com/eschava/psmqtt.git
cd psmqtt
pip3 install .
```

If you get an `error: externally-managed-environment` you'll have to decide if you want to use virtual environments, which is recommended by Python and Debian.
If yes, please read the previous section.
If you still don't want venvs you can force pip to install the dependencies using

```
rm /usr/lib/python3.<your Python version>/EXTERNALLY-MANAGED
```

Then repeat the `pip3 install .` command.
You are now ready to run psmqtt.


## Running psmqtt

If psmqtt was installed correctly, it should be in your PATH and you should be able to run `psmqtt`:

```sh
psmqtt
```

You will likely encounter an error with `psmqtt` complaining about the lack of configuration file.
If that's the case, install system-wide the default configuration file:

```sh
cd <path where you have cloned psmqtt>
mkdir /etc/psmqtt
cp psmqtt.yaml /etc/psmqtt/
```

Then edit the MQTT broker IP address in the `psmqtt.yaml` file:

```sh
nano /etc/psmqtt/psmqtt.yaml
```

You may also want to explore the `schedule` section to check the default scheduling rules and tasks,
which are meant to showcase the features of psmqtt and probably do not cover your specific needs.

Finally use [MQTT explorer](http://mqtt-explorer.com/) utility to verify the sanity and the formatting of the
published data.

## Installing `psmqtt` as a Service

Once you have successfully started psmqtt from command line it's suggested that you 
check how to turn psmqtt into a [SystemD service](install-systemd-service.md).

Running psmqtt as a SystemD service allows you to automatically start it after boot,
start/stop psmqtt as any system daemon, etc.

