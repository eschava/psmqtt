# Using `psmqtt` on Debian derivative, e.g., Proxmox

I want for my proxmox server to publish its metrics to MQTT broker for use by
Home Assistant.

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

## Installation

```
git clone https://github.com/asokolsky/psmqtt.git
git checkout typing
python3 -m pip install -r requirements.txt
```

## First Run

I repeatedly run `psmqtt-publish.py` adding more and more tasks untill I arrive
at something like:

```sh
python3 psmqtt-publish.py -vvv mqtt \
    cpu_percent \
    virtual_memory/percent \
    sensors_temperatures/coretemp/0/ \
    smart/nvme0/temperature \
    smart/sda/temperature \
    smart/sdb/temperature
```
I then used [mqtt explorer](http://mqtt-explorer.com/) to verify sanity of the
published data.

## Running `psmqtt` as a Service

* Modified `psmqtt.service` to have privilidges to run run `smartctl`:
```
WorkingDirectory=/root/psmqtt
User=root
ExecStart=/usr/bin/python3 /root/psmqtt/psmqtt.py
```
* Modified `psmqtt.conf` - customized tasks

Then followed steps in [service.md]:
```sh
root@suprox:~/psmqtt# cp psmqtt.service /etc/systemd/system
root@suprox:~/psmqtt# systemctl enable psmqtt.service
Created symlink /etc/systemd/system/multi-user.target.wants/psmqtt.service → /etc/systemd/system/psmqtt.service.
root@suprox:~/psmqtt# systemctl start psmqtt.service
```

To check the status:
```
root@suprox:~/psmqtt# systemctl status psmqtt.service
● psmqtt.service - Resource daemon to MQTT
     Loaded: loaded (/etc/systemd/system/psmqtt.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2022-11-05 14:39:53 PDT; 5s ago
   Main PID: 603302 (python3)
      Tasks: 2 (limit: 38329)
     Memory: 14.5M
        CPU: 108ms
     CGroup: /system.slice/psmqtt.service
             └─603302 /usr/bin/python3 /root/psmqtt/psmqtt.py

Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,728] DEBUG Loading app config '/root/psmqtt/psmqtt.conf'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,729] DEBUG Connecting to 'mqtt:1883'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,730] DEBUG Periodicity: 'every 1 minute'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,730] DEBUG Tasks: '['cpu_percent', 'virtual_memory/percent', 'sensors_temperatures/coretemp/0/', 'smart/nvme0/temperature', 'smart/sd>
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,731] DEBUG Periodicity: 'every 60 minutes'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,731] DEBUG Tasks: 'disk_usage/percent/|'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,732] DEBUG Periodicity: 'every 3 hours'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,732] DEBUG Tasks: '{'boot_time/{{x|uptime}}': 'uptime'}'
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,733] DEBUG on_connect()
Nov 05 14:39:53 suprox python3[603302]: [2022-11-05 14:39:53,733] DEBUG Connected to MQTT broker, subscribing to topic psmqtt/suprox/request/#
```
