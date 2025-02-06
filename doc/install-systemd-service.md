# Setting up `psmqtt` as a SystemD Service

It is possible to:

* install the required Python packages into the system-wide site packages and
* run `psmqtt.py` as a service upon system boot.

This step-by-step guide should work on most SystemD-enabled Linux distributions including:
* Ubuntu and its flavors
* Fedora and RedHat
* many others

Let's start.
Make a copy of your cloned `psmqtt` directory to `/opt/psmqtt`:

```sh
sudo cp -r ../psmqtt /opt
```

Ensure that your `/opt/psmqtt/psmqtt.yaml`:

* points to your MQTT broker (IP address and port)
* has the scheduling rules and tasks that make sense for your setup

Then:

```sh
sudo cp psmqtt.service /etc/systemd/system
```

If you are interested in monitoring SMART counters, you will need to edit the `/etc/systemd/system/psmqtt.service` file
and set `User=root` instead of `User=nobody`.
Then:

```sh
sudo systemctl enable psmqtt.service
sudo systemctl start psmqtt.service
```

Check the service status with `sudo systemctl status psmqtt`.
Look into syslog for potential errors:

```sh
sudo tail /var/log/syslog
```

If you get errors of type `ModuleNotFoundError`,
make sure you correctly [installed psmqtt from sources](install-source.md) first.
