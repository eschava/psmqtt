# Using `psmqtt` on Debian

This documentation describes how to install psmqtt on Debian systems or
Debian derivatives, e.g., Proxmox.

## Prerequisites

Check `python`:
```
python3 --version
Python 3.9.2
```
Check `pip`:
```
python3 -m pip
/usr/bin/python3: No module named pip
```

To install `pip`:
```
apt install python3-pip
```
Then:
```
# python3 -m pip --version
pip 20.3.4 from /usr/lib/python3/dist-packages/pip (python 3.9)
```

Checking for `smartctl`:
```sh
smartctl --scan
/dev/sda -d scsi # /dev/sda, SCSI device
/dev/sdb -d scsi # /dev/sdb, SCSI device
/dev/nvme0 -d nvme # /dev/nvme0, NVMe device
```

## Installation without using a venv

```
git clone https://github.com/eschava/psmqtt.git
python3 -m pip install -r requirements.txt
```

If you get an `error: externally-managed-environment` you'll have to decide if you want to keep using venvs, which is recommended by Python and Debian. If you don't want venvs you can skip the next paragraph and just run

```
rm /usr/lib/python3.11/EXTERNALLY-MANAGED
```

## Installation inside a venv

Since Debian 12 (Bookworm) Python defaults to using venvs for modules installed with pip. 
They also strongly recommend keeping it as an "externally-managed-environment".

As above, first clone the repository by running
```
git clone https://github.com/eschava/psmqtt.git
```
If you haven't already done so, you should create a directory for your venvs. Debian uses `~/.venvs` so I'll use that here.
The following command creates a new folder and venv named psmqtt.
```
python3 -m venv ~/.venvs/psmqtt
```
Then install the required modules, replacing `~/.venvs` and `/path/to/psmqtt/` with your proper paths.
```
~/.venvs/psmqtt/bin/python3 -m pip install -r /path/to/psmqtt/requirements.txt
```
For the rest of the tutorial you'll need to replace every occurence of `python3` (comands and configs) with `~/.venvs/psmqtt/bin/python3`.

## Running psmqtt

Just run `psmqtt.py` and start tweaking the configuration file:

```sh
sudo python3 psmqtt.py
```

Then use [MQTT explorer](http://mqtt-explorer.com/) to verify the sanity and the formatting of the
published data.

## Running `psmqtt` as a Service

Check the [SystemD service installation](install-systemd-service.md) page.
