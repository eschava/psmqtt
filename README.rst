=======
Summary
=======

**PSMQTT** is a cross-platform utility for reporting system and processes
metrics (CPU, memory, disks, network, S.M.A.R.T. disk data) to an MQTT broker.

**PSMQTT**  is written in Python and is based on:

* `paho-mqtt <https://github.com/eclipse/paho.mqtt.python>` to communicate with the MQTT broker;
* `psutil <https://github.com/giampaolo/psutil>` to collect metrics;
* `pySMART <https://github.com/truenas/py-SMART>` to collect SMART data;
* `recurrent <https://github.com/kvh/recurrent>` to describe reporting schedule.
* `jinja2 <https://github.com/alex-foundation/jinja2>` to format the data.

========================
Installation from source
========================

Clone this repository and then install the required Python libraries using `pip <https://pip.pypa.io/en/stable/installing/>`_::

   pip install -r requirements.txt

(Note that you should consider installing the required libraries in a Python venv to maintain them isolated from the rest of your Python installation.
See `this page for more info <doc/debian.md>`_.)

Finally you can run **PSMQTT** using::

   python psmqtt.py

You may want to install **PSMQTT** as a service/system-daemon, see `this page for more info <doc/service.md>`_.


=====================
Installing on FreeBSD
=====================

See `FreeBSD doc <doc/freebsd.md>`_

=====================
Installing on Windows
=====================

See `Windows doc <doc/windows.md>`_


==================
Deploy with Docker
==================

**PSMQTT** is also packaged as a multi-arch Docker image. If your system does not have Python3 installed or 
you don't want to install **PSMQTT** Python dependencies in your environment, you can launch
a Docker container::

   docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      ghcr.io/eschava/psmqtt:latest

This works for most use cases, except in case you want to publish to the MQTT broker the SMART data
for some hard drive.
If that's the case, you will need to launch the docker container with the ``--cap-add SYS_RAWIO`` flag,
passing all hard drive devices using the ``--device`` flag and using the ``latest-root`` tag::

   docker run -d -v <your config file>:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      --cap-add SYS_RAWIO \
      --device=/dev/<your-hard-drive> \
      ghcr.io/eschava/psmqtt:latest-root

For example if your ``/home/user/psmqtt.conf`` file contains references to ``/dev/sda`` and ``/dev/sdb`` you may want
to launch **PSMQTT** as::

   docker run -d -v /home/user/psmqtt.conf:/opt/psmqtt/conf/psmqtt.conf \
      --hostname $(hostname) \
      --cap-add SYS_RAWIO \
      --device=/dev/sda \
      --device=/dev/sdb \
      ghcr.io/eschava/psmqtt:latest-root

Note the use of the ``latest-root`` tag instead of the ``latest`` tag: it's a docker image where
the psmqtt Python utility runs as root. This is necessary in order to access the SMART data of the hard drives.


=======================
Configuration and usage
=======================

Please check the `Usage page <doc/usage.md>`_


=======
Support
=======

Please use the `GitHub issue tracker <https://github.com/eschava/psmqtt/issues>`_
to report bugs or request features.
