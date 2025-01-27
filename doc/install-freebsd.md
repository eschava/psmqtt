# psmqtt on FreeBSD

Using psmqtt on FreeBSD derivatives

```sh
alex@nass:~/ > uname -a
FreeBSD nass.lan 13.1-RELEASE-p2 FreeBSD 13.1-RELEASE-p2 n245412-484f039b1d0 TRUENAS amd64
alex@nass:~/psmqtt/ > freebsd-version
13.1-RELEASE-p2
```

## Verifying Prerequisites

Python:
```sh
alex@nass:~/ > python3 --version
Python 3.9.14
alex@nass:~/psmqtt/ > python3 -m pip
/usr/local/bin/python3: No module named pip
```

To install `pip` this should work on FreeBSD:
```sh
alex@nass:~/psmqtt/ > sudo pkg install py39-pip
Password:
Updating local repository catalogue...
pkg: file:///usr/ports/packages/meta.txz: No such file or directory
repository local has no meta file, using default settings
pkg: file:///usr/ports/packages/packagesite.pkg: No such file or directory
pkg: file:///usr/ports/packages/packagesite.txz: No such file or directory
Unable to update repository local
Error updating repositories!
```

Instead in TrueNAS:

```
alex@nass:~/psmqtt/ > python -m ensurepip
Defaulting to user installation because normal site-packages is not writeable
Looking in links: /tmp/tmp943tnjaa
Requirement already satisfied: setuptools in /usr/local/lib/python3.9/site-packages (57.0.0)
Processing /var/tmp/tmp943tnjaa/pip-22.0.4-py3-none-any.whl
Installing collected packages: pip
  WARNING: The scripts pip3 and pip3.9 are installed in '/mnt/tank/home/alex/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed pip-22.0.4
alex@nass:~/psmqtt/ > python3 -m pip --version
pip 22.0.4 from /mnt/tank/home/alex/.local/lib/python3.9/site-packages/pip (python 3.9)
```

Note that the above installation results in python libraries being installed
into `/mnt/tank/home/alex/.local/lib/python3.9/site-packages`.  When we run
`psmqtt` as a root we will need to pass this location to `psmqtt`

Disks:
```sh
alex@nass:~/ > sudo smartctl --scan
/dev/ada0 -d atacam # /dev/ada0, ATA device
/dev/ada1 -d atacam # /dev/ada1, ATA device
/dev/ada2 -d atacam # /dev/ada2, ATA device
/dev/ses0 -d atacam # /dev/ses0, ATA device
/dev/ada3 -d atacam # /dev/ada3, ATA device
/dev/ada4 -d atacam # /dev/ada4, ATA device
/dev/ada5 -d atacam # /dev/ada5, ATA device
/dev/ses1 -d atacam # /dev/ses1, ATA device
```

## Installation

```sh
git clone https://github.com/eschava/psmqtt.git
cd psmqtt
python3 -m pip install -r requirements.txt
```

## First Run

Edit your `psmqtt.yaml` to contain the correct MQTT broker IP address and port.
Then:

```sh
sudo python3 psmqtt.py
```

## Running `psmqtt` as a Service

Once you have successfully started psmqtt from command line it's suggested that you 
check how to turn psmqtt into a [SystemD service](install-systemd-service.md).

Running psmqtt as a SystemD service allows you to automatically start it after boot,
start/stop psmqtt as any system daemon, etc.