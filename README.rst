=======
Summary
=======

**PSMQTT** is a cross-platform utility for reporting system and processes utilization (CPU, memory, disks, network) using MQTT protocol.

Is written in Python and based on briliant `psutil <https://github.com/giampaolo/psutil>`_ library.

=======
Installation
=======
Just install required Python libraries using `pip <https://pip.pypa.io/en/stable/installing/>`_::

   pip install recurrent paho-mqtt python-dateutil psutil jinja2
   (Jinja2 is needed for formatting output and could be skipped if formatting is not used)
   
After you can run main file using::

  python psmqtt.py

  
=======
General information about tasks and MQTT topics
=======

Every utilization parameter has its own special name. It always starts with task name that could be followed with unique parameter name or/and device number/name.

E.g. task to get percent of CPU used by user apps use name **cpu_times_percent/user**. All possible parameter names are described below.

Results for parameter PARAMETER_NAME are pushed to the MQTT topic **psmqtt/PARAMETER_NAME** (prefix "psmqtt/" is configurable)


Very often it could be useful to provide several parameters from the same task using one request. In such case next formats are used:

- psmqtt/TASK_NAME/* - to get all possible parameters (MQTT topic per parameter)

- or psmqtt/TASK_NAME/*; - to get all possible parameters in one topic (combined)

Examples::

   Task psmqtt/cpu_times_percent/* provides
   psmqtt/cpu_times_percent/user 12.0
   psmqtt/cpu_times_percent/nice  1.0
   psmqtt/cpu_times_percent/system 5.0
   etc

   Task psmqtt/cpu_times_percent/*; provides
   psmqtt/cpu_times_percent/*; user=12.0;nice=1.0;system=5.0;etc


=======
Formatting output
=======

Output of task could be formatted using `Jinja2 <http://jinja.pocoo.org/>`_ templates. Append template to the task after one more "/" separator.

E.g.
    psmqtt/cpu_times_percent/user/{{x}}%
To append % symbol after CPU usage.

For task providing many parameters (having *) all parameters are available by name if they are named or by index as x[1] if they are numbered.

NOTE: After formatting tasks providing many parametes are combined to single one.

Unnamed parameters are avaiable as x.

All additional filters are defined at the filters.py file. You also can add custom filters there.

Next filters are implemented now::

    KB,MB,GB - to format value in bytes as KBytes, MBytes or GBytes.
    uptime - to format boot_time as uptime string representation.

Examples::

    virtual_memory/*/{{(100*free/total)|int}}% - free virtual memory in %
    boot_time/{{x|uptime}} - uptime
    cpu_times_percent/user/*/{{x[0]+x[1]}} - user CPU times for first and second processor total
    virtual_memory/free/{{x|MB}} - Free RAM in MB

=======
Configuration
=======
There are two ways how to force sending some system state parameter over MQTT topic

1. Schedule
2. MQTT request

=======
Schedule
=======
**schedule** parameter in **psmqtt.conf** is a Python map having human-readable period as a key and task name (or list of task names) as a value.
You can check examples of recurring period definitions `here <https://github.com/kvh/recurrent>`_.

=======
MQTT request
=======
It's better to describe how to use it using example.
To get information for task "cpu_percent" with MQTT prefix "psmqtt/" you need to send any string on topic::

  psmqtt/request/cpu_percent
  
and result will be pushed on the topic::

  psmqtt/cpu_percent


=======
Tasks
=======
CPU
::

   cpu_times/* - CPU times information. Topic per parameter
   cpu_times/*;  - CPU times information in one topic (combined)
   cpu_times/{user/nice/system/idle/iowait/irq/softirq/steal/guest} - CPU times separate parameters
   cpu_percent - CPU total usage in percent
   cpu_percent/* - CPU usage in percent. Topic per CPU number
   cpu_percent/*; - CPU usage in percent per CPU in one topic (combined)
   cpu_percent/{0/1/2/etc} - CPU usage for single CPU
   cpu_times_percent/* - CPU times in percent. Topic per parameter
   cpu_times_percent/*;  - CPU times in percent in one topic (combined)   
   cpu_times_percent/{user/nice/system/idle/iowait/irq/softirq/steal/guest} - CPU times in percent separate parameters
   cpu_times_percent/{user/nice/system/idle/iowait/irq/softirq/steal/guest}/* - CPU times in percent separate parameters. Topic per CPU number
   cpu_times_percent/{user/nice/system/idle/iowait/irq/softirq/steal/guest}/*; - CPU times in percent separate parameters per CPU number in one topic (combined)
   cpu_times_percent/{user/nice/system/idle/iowait/irq/softirq/steal/guest}/{0/1/2/etc} - CPU times in percent separate parameters for single CPU
   cpu_times_percent/*/{0/1/2/etc} - CPU times in percent for single CPU. Topic per parameter
   cpu_times_percent/*;/{0/1/2/etc} - CPU times in percent for single CPU in one topic (combined)
   cpu_stats/* - CPU statistics. Topic per parameter
   cpu_stats/*;  - CPU statistics in one topic (combined)
   cpu_stats/{ctx_switches/interrupts/soft_interrupts/syscalls} - CPU statistics separate parameters
   
Memory
::

   virtual_memory/* - Virtual memory. Topic per parameter
   virtual_memory/*;  - Virtual memory in one topic (combined)
   virtual_memory/{total/available/percent/used/free/active/inactive/buffers/cached} - Virtual memory separate parameters
   swap_memory/* - Swap memory. Topic per parameter
   swap_memory/*;  - Swap memory in one topic (combined)
   swap_memory/{total/used/free/percent/sin/sout} - Swap memory separate parameters
   
Disks
::

   disk_partitions/{device/mountpoint/fstype/opts}/* - Disk partitions separate parameters. Topic per disk number
   disk_partitions/{device/mountpoint/fstype/opts}/*; - Disk partitions separate parameters per disk number in one topic (combined)
   disk_partitions/{device/mountpoint/fstype/opts}/{0/1/2/etc} - Disk partitions separate parameter for single disk number
   disk_partitions/*/{0/1/2/etc} - Disk partitions parameters for single disk number. Topic per parameter
   disk_partitions/*;/{0/1/2/etc} - Disk partitions parameters for single disk number in one topic (combined)
   disk_usage/{total/used/free/percent}/{drive} - Disk usage single parameter (slashes in drive should be replaced with vertical slash)
   disk_usage/*/{drive} - Disk usage separate parameters. Topic per parameter
   disk_usage/*;/{drive} - Disk usage separate parameters in one topic (combined)
   disk_io_counters - to be continued...
   
Processes
::
   To be continued...

   
=======
Useful topics
=======
**psmqtt/boot_time/{{x|uptime}}** - Up time

**psmqtt/cpu_percent** - CPU usage in percent

**psmqtt/virtual_memory/percent** - RAM usage in percent

**psmqtt/virtual_memory/free/{{x|MB}}** - Free RAM in MB

**psmqtt/disk_usage/percent/|** - root drive (slash replaced with vertical slash) usage in percent (Linux)

**psmqtt/disk_usage/free/|/{{x|GB}}** - space left in GB for root drive (Linux)

**psmqtt/disk_usage/percent/C:** - C:/ drive usage in percent (Windows)

**psmqtt/processes/top_cpu/name** - name of top process consuming CPU

**psmqtt/processes/top_memory/exe** - executable file of top process consuming memory

