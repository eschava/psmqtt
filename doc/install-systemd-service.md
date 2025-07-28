# Setting up `psmqtt` as a SystemD Service

It is possible to install `psmqtt` using one of the documented methods (see [main readme](../README.rst) and then run `psmqtt` as a service upon system boot, using SytemD.

This step-by-step guide should work on most SystemD-enabled Linux distributions including:
* Ubuntu and its flavors
* Fedora and RedHat
* many others

Let's start.

1. Ensure that the config file (it could be located either at `/etc/psmqtt/psmqtt.yaml` or `$HOME/.config/psmqtt.yaml`) is:

* pointing to your MQTT broker (IP address and port)
* containing the scheduling rules and tasks that make sense for your setup


2. Copy the SystemD service unit definition in your SystemD path:
   
```sh
wget https://raw.githubusercontent.com/eschava/psmqtt/refs/heads/master/psmqtt.service
sudo mv psmqtt.service /etc/systemd/system
```

3. Edit the file `/etc/systemd/system/psmqtt.service` and make sure that the `ExecStart=` line contains the right installation path of psmqtt, i.e. the output of

```sh
which psmqtt
```

4. If you are interested in monitoring SMART counters, you will need to edit the `/etc/systemd/system/psmqtt.service` file
and set `User=root` instead of `User=nobody`.

5. Finally enable the SystemD unit on your system to be started at boot and right now:

```sh
sudo systemctl enable psmqtt.service
sudo systemctl start psmqtt.service
```

6. Check the service status with `sudo systemctl status psmqtt`.
Look into syslog for potential errors:

```sh
sudo tail /var/log/syslog
```

if your Linux/Unix distribution is using `syslog` or 

```sh
journalctl --pager-end --unit psmqtt
```

if you Linux/Unix distribution is using `journald`.
Please note that if the log contains errors of type `ModuleNotFoundError`, that's a sign that the installation of psmqtt was not successful.
Please make sure you correctly [installed psmqtt from sources](install-source.md) first.
