# Installing `psmqtt` from source

This documentation describes how to install psmqtt using [pip](https://pip.pypa.io/en/stable/installing/) and virtual environments.

## Prerequisites

Check `python`:
```
python3 --version
Python 3.9.2
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
pip 20.3.4 from /usr/lib/python3/dist-packages/pip (python 3.9)
```

Check you have `smartctl` installed:
```sh
smartctl --scan
/dev/sda -d scsi # /dev/sda, SCSI device
/dev/sdb -d scsi # /dev/sdb, SCSI device
/dev/nvme0 -d nvme # /dev/nvme0, NVMe device
```
If not, please install [smartmontools](https://www.smartmontools.org/wiki/Download).

## Installation inside a venv (preferred way)

Since Debian 12 (Bookworm) Python defaults to using venvs for modules installed with pip. 
They also strongly recommend keeping it as an "externally-managed-environment".

As above, first clone the repository by running
```
git clone https://github.com/eschava/psmqtt.git
cd psmqtt
```
If you haven't already done so, you should create a directory for your venvs. Debian uses `~/.venvs` so I'll use that here.
The following command creates a new folder and venv named psmqtt.
```
python3 -m venv ~/.venvs/psmqtt
```
Then activate the venv:
```
source ~/.venvs/psmqtt/bin/activate
```

You should now see "(psmqtt)" reported in your prompt to indicate that you're now running commands within the venv.
Then install the required psmqtt dependencies:

```
pip3 install -r requirements.txt
```

You are now ready to run psmqtt.

## Installation without using a venv

If for some reason you don't want to install psmqtt dependencies inside a venv, just run:

```
git clone https://github.com/eschava/psmqtt.git
python3 -m pip install -r requirements.txt
```

If you get an `error: externally-managed-environment` you'll have to decide if you want to keep using venvs, which is recommended by Python and Debian. If you still don't want venvs you can force pip to install the dependencies
using

```
rm /usr/lib/python3.11/EXTERNALLY-MANAGED
```

Then repeat the `python3 -m pip install -r requirements.txt` command.
You are now ready to run psmqtt.


## Running psmqtt

Just run `psmqtt.py`:

```sh
sudo python3 psmqtt.py
```

You will likely encounter an error with psmqtt complaining about the MQTT broker being not reachable.
Please edit the MQTT broker IP address in the `psmqtt.yaml` file in such case.

Finally use [MQTT explorer](http://mqtt-explorer.com/) to verify the sanity and the formatting of the
published data.

## Installing `psmqtt` as a Service

Once you have successfully started psmqtt from command line it's suggested that you 
check how to turn psmqtt into a [SystemD service](install-systemd-service.md).

Running psmqtt as a SystemD service allows you to automatically start it after boot,
start/stop psmqtt as any system daemon, etc.

