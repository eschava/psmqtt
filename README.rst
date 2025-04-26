=======
Summary
=======

**PSMQTT** is a cross-platform utility for reporting system and processes
metrics (CPU, memory, disks, network, S.M.A.R.T. disk data, etc) to an MQTT broker.

It integrates seamlessly with `HomeAssistant <https://www.home-assistant.io/>`_
thanks to the support for `MQTT discovery messages <https://www.home-assistant.io/integrations/mqtt/#discovery-messages>`_.

**PSMQTT**  is written in Python and is based on:

* `paho-mqtt <https://github.com/eclipse/paho.mqtt.python>`_ to communicate with the MQTT broker;
* `psutil <https://github.com/giampaolo/psutil>`_ to collect metrics;
* `pySMART <https://github.com/truenas/py-SMART>`_ to collect SMART data from HDDs/SSDs;
* `recurrent <https://github.com/kvh/recurrent>`_ to describe scheduling expressions;
* `jinja2 <https://github.com/alex-foundation/jinja2>`_ to format the data.

============
Installation
============

The suggested installation method is to use the provided `Docker image <doc/install-docker.md>`_.
However alternative installation methods are available for Linux, FreeBSD and Windows:

* Installing from **pypi**: see `Install from pypi doc <doc/install-pypi.md>`_
* Installing from **sources**: see `Install from source doc <doc/install-source.md>`_
* Installing on **FreeBSD**: see `FreeBSD doc <doc/install-freebsd.md>`_
* Installing on **Windows**: see `Windows doc <doc/install-windows.md>`_

=======================
Configuration and usage
=======================

**PSMQTT** is strongly configuration-file-driven.
Please check the `Usage page <doc/usage.md>`_ which contains all documentation on the configuration options for psmqtt.

============
Known issues
============

See `Known issues <doc/known-problems.md>`_.

=======
Support
=======

Please use the `GitHub issue tracker <https://github.com/eschava/psmqtt/issues>`_
to report bugs or request features.
