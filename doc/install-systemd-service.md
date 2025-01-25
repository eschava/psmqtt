# Setting up `psmqtt` as a Service

It is possible to:

* install the required Python packages into the system-wide site packages and
* run `psmqtt.py` as a service upon system boot.

## Current Ubuntu flavors

Make a copy of `psmqtt` directory e.g., to `/opt/psmqtt`, for use by a service:

```sh
sudo cp -r ../psmqtt /opt
```

Modify the included `psmqtt.service`:

* specify `WorkingDirectory=/opt/psmqtt`
* adjust `ExecStart=/usr/bin/python3 /opt/psmqtt/psmqtt.py`

Ensure that `psmqtt.yaml` in `WorkingDirectory`:

* points to your MQTT broker
* schedules and tasks make sense

Then:

```sh
sudo cp psmqtt.service /etc/systemd/system
sudo systemctl enable psmqtt.service
sudo systemctl start psmqtt.service
```

Check the service status with `sudo systemctl status psmqtt`.

Look into syslog for potential errors:

```sh
sudo tail /var/log/syslog
```

In my case I noticed: `ModuleNotFoundError: No module named 'recurrent'`.

To resolve the problem I did `sudo pip3 install -r requirements.txt` to install
the packages into the site-packages.

And then:

```sh
sudo systemctl restart psmqtt
```
