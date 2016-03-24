=======
Summary
=======

**PSMQTT** is an utility for reporting system and processes utilization (CPU, memory, disks, network) using MQTT protocol.

Is written in Python and based on briliant `psutil <https://github.com/giampaolo/psutil>`_ library.

=======
Installation
=======
Just install required Python libraries using `pip <https://pip.pypa.io/en/stable/installing/>`_::

   pip install recurrent paho-mqtt python-dateutil psutil
   
After you can run main file using::

  python psmqtt.py

=======
Configuration
=======
There are two ways how to force sending some system state parameter over MQTT topic

1. Schedule
2. MQTT request

=======
Schedule
=======
**schedule** parameter in **psmqtt.conf** is a Python map having human-readable period as key and task name (or list of task names) as value.
Check examples of recurring period definitions you can `here <https://github.com/kvh/recurrent>`_.

=======
MQTT request
=======
I'll describe how to use it using example.
To get information for task "cpu_percent" with MQTT prefix "psmqtt/" you need to send any string on topic::

  psmqtt/request/cpu_percent
  
and result will be pushed on topic::

  psmqtt/cpu_percent
