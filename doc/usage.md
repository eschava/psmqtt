# PSMQTT Usage

## PSMQTT Architecture

The PSMQTT architecture can be described as:

```mermaid
flowchart TD
%% Nodes
    OS([Linux/Windows/Mac OS HW interfaces]) 
    SMART([Hard drive SMART data])
    CLK((Clock))
    MQTT([MQTT Broker])
    psmqttTASK(PSMQTT task handler)
    psmqttSCHED(PSMQTT scheduler)
    psmqttFMT(PSMQTT formatter)

%% Edge connections between nodes
    OS -->|pySMART| psmqttTASK
    SMART -->|psutil| psmqttTASK
    CLK --> psmqttSCHED

    psmqttSCHED-->psmqttTASK
    psmqttTASK-->psmqttFMT

    psmqttFMT-->MQTT

%% Individual node styling. 
    style OS color:#FFFFFF, fill:#AA00FF, stroke:#AA00FF
    style SMART color:#FFFFFF, stroke:#00C853, fill:#00C853
    style CLK color:#FFFFFF, stroke:#2962FF, fill:#2962FF
    style MQTT color:#FFFFFF, stroke:#2962FF, fill:#2962FF
```

The PSMQTT configuration file defines:
* periodicity of each PSMQTT action;
* which "sensor" has to be queried; PSMQTT uses [psutil](https://github.com/giampaolo/psutil) 
and [pySMART](https://github.com/truenas/py-SMART) libraries to sense data from the 
HW of the device where PSMQTT runs (CPU, memory, temperature and fan sensors, SMART harddrive data,
proces information, etc);
* how each sensor data is formatted into text;
* to which MQTT broker all the outputs will be published.

The following section provides more details about the config file syntax.

## Configuration file

The PSMQTT configuration file is a [YAML file](https://en.wikipedia.org/wiki/YAML).

The PSMQTT configuration file should be located in the same 
directory containing `psmqtt.py`; alternatevely you can specify the location of the
config file using the **PSMQTTCONFIG** environment variable 
(e.g. setting **PSMQTTCONFIG=~/my-config-psmqtt.yaml**).

Please check the comments in the [default psmqtt.yaml](../psmqtt.yaml) as
documentation for most of the entries.
Typically you will need to edit are those associated
with the MQTT broker:

```
mqtt:
  broker:
    host: <put here the IP address of your MQTT broker>
    port: <port where your MQTT broker listens, typically 1883>
```

The rest of this document will focus on the format of each "scheduling expression",
whose general format is:

```
schedule:
  - cron: <human-friendly CRON expression>
    tasks:
      - task: <task name>
        params: [ <param1>, <param2>, <param3>, ... ]
        formatter: <formatting rule>
        topic: <MQTT topic>
```

Each of the following section describes in details the parameters:

1. `<human-friendly CRON expression>`: [CRON expression](#cron-expression)
2. `<task name>` and `<param1>`, `<param2>`, `<param3>`, ...: [Tasks](#tasks)
3. `<formatting rule>`: [Formatting](#formatting)
4. `<MQTT topic>`: [MQTT Topic](#mqtt-topic)


### CRON expression

The `<human-friendly CRON expression>` is a string encoding a recurrent rule, 
like e.g. "every 5 minutes" or "every monday" or "every hour except 9pm, 10pm and 11pm".

You can check examples of recurring period definitions
[here](https://github.com/kvh/recurrent).

Note that cron expressions should be unique; if there are several schedules with the same period only
last one will be used.

### Tasks

PSMQTT supports a large number of "tasks".
A "task" is the combination of
* `<task-name>`: the specification of which sensor should be read; this is just a string;
* parameter list `<param1>`,  `<param2>`, ...,  `<paramN>`: these are either strings or integers 
  represented as a YAML list (the preferred syntax is to use a comma-separated list enclosed by 
  square brackets); such parameters act as additional selectors/filters for the sensor;

The meaning for `<param1>`, `<param2>` is task-dependent.
Also the number of required paraterms is task-dependent.

The result of each task are pushed to an MQTT topic.
As an example:

```
schedule:
  - cron: every 10sec
    tasks:
      - task: cpu_times_percent
        params: [ system ]
```

configures PSMQTT to publish on the MQTT topic **psmqtt/COMPUTER_NAME/cpu_times_percent/system**
the value of the `system` field returned by the psutil [cpu_times_percent](https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent) function.

Most tasks support wildcard `*` parameters which will cause the task to produce **multiple outputs**; 
in such case the MQTT topic associated with the task should actually be 
an MQTT topic _prefix_ so that each task output will be published on a different topic.
As an example:

```
schedule:
  - cron: every 10sec
    tasks:
      - task: cpu_times_percent
        params: [ "*" ]
        topic: "cpu/*"
```

configures PSMQTT to publish on 10 MQTT topics:

* **psmqtt/COMPUTER_NAME/cpu/user** the value of the `user` field returned by the psutil [cpu_times_percent](https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent) function.
* **psmqtt/COMPUTER_NAME/cpu/nice** the value of the `nice` field returned by the psutil [cpu_times_percent](https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent) function.
* **psmqtt/COMPUTER_NAME/cpu/system** the value of the `system` field returned by the psutil [cpu_times_percent](https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent) function.

... etc etc ...


Most tasks support also the wildcard `*;` parameter to get all possible fields of the psutil or pySMART output in one single topic, 
encoding them as a **JSON string**; in other words a single MQTT message will be published
on a single MQTT topic with a message payload containing a JSON string.
As an example:

```
schedule:
  - cron: every 10sec
    tasks:
      - task: cpu_times_percent
        params: [ "*;" ]
        topic: "cpu"
```

configures PSMQTT to publish on the MQTT topic **psmqtt/COMPUTER_NAME/cpu**
the JSON encoding of what is returned by the psutil [cpu_times_percent](https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent) function, e.g. `{"user": 12.0, "nice": 1.0, "system": 5.0, ...}`.

In case of task execution error, the error message is sent to a topic named
**psmqtt/COMPUTER_NAME/error/TASK**. Please check [some MQTT documentation](https://www.hivemq.com/blog/mqtt-essentials-part-5-mqtt-topics-best-practices/) to understand the role of the `/` MQTT
topic level separator.

Here follows the reference documentation for all required tasks and their parameters:

* **Category: CPU**
  * Task name: `cpu_percent`
    * Short description: CPU total usage in percentage
    * Number of required parameters: 1
    * `<param1>`: The wildcard `*` or `*;` to select all the CPUs or the CPU index `0`, `1`, `2`, etc to select a single CPU
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent )
  * Task name: `cpu_times`
    * Short description: CPU times information
    * Number of required parameters: 1
    * `<param1>`: The wildcard `*`  or `*;` to select all fields or one of `user` / `nice` / `system` / etc.
      Full list of available fields in the external docs.
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.cpu_times )
  * Task name: `cpu_times_percent`
    * Short description: CPU times in percentage
    * Number of required parameters: 1 or 2
    * `<param1>`: The wildcard `*` or `*;` to select all fields or one of `user` / `nice` / `system` / etc.
      Full list of available fields in the external docs.
    * `<param2>`: The wildcard `*` or `*;` to select all CPUs or the CPU index `0`, `1`, `2`, etc to select a single CPU.
      Note that you cannot use a wildcard as `<param2>` together with a wildcard on `<param1>`.
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent )
  * Task name: `cpu_stats`
    * Short description: CPU statistics
    * Number of required parameters: 1
    * `<param1>`: The wildcard `*`  or `*;` to select all fields or one of `ctx_switches` / `interrupts` / `soft_interrupts` / `syscalls`.
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.cpu_stats )


* **Category: Memory**
  * Task name: `virtual_memory`
    * Short description: Virtual memory information
    * Number of required parameters: 1
    * `<param1>`: The wildcard `*`  or `*;` to select all fields or one of  `total` / `available` / `percent` / etc.
      Full list of available fields in the external docs.
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.virtual_memory )
  * Task name: `swap_memory`
    * Short description: Swap memory information
    * Number of required parameters: 1
    * `<param1>`: The wildcard `*`  or `*;` to select all fields or one of  `total` / `used` / `free` / etc.
      Full list of available fields in the external docs.
    * Link to external docs: [ psutil ]( https://psutil.readthedocs.io/en/latest/#psutil.swap_memory )


Disks :

    disk_partitions/{device/mountpoint/fstype/opts}/* - Disk partitions separate parameters. Topic per disk number
    disk_partitions/{device/mountpoint/fstype/opts}/*; - Disk partitions separate parameters per disk number in one topic (JSON string)
    disk_partitions/{device/mountpoint/fstype/opts}/{0/1/2/etc} - Disk partitions separate parameter for single disk number
    disk_partitions/*/{0/1/2/etc} - Disk partitions parameters for single disk number. Topic per parameter
    disk_partitions/*;/{0/1/2/etc} - Disk partitions parameters for single disk number in one topic (JSON string)
    disk_usage/{total/used/free/percent}/{drive} - Disk usage single parameter (slashes in drive should be replaced with vertical slash)
    disk_usage/*/{drive} - Disk usage separate parameters. Topic per parameter
    disk_usage/*;/{drive} - Disk usage separate parameters in one topic (JSON string)
    disk_io_counters/* - Disk I/O counters. Topic per parameter
    disk_io_counters/*;  - Disk I/O counters in one topic (JSON string)
    disk_io_counters/{read_count/write_count/read_bytes/write_bytes/read_time/write_time/read_merged_count/write_merged_count/busy_time} - Disk I/O counters separate parameters
    disk_io_counters/{read_count/write_count/read_bytes/write_bytes/read_time/write_time/read_merged_count/write_merged_count/busy_time}/* - Disk I/O counters separate parameters. Topic per disk number
    disk_io_counters/{read_count/write_count/read_bytes/write_bytes/read_time/write_time/read_merged_count/write_merged_count/busy_time}/*; - Disk I/O counters separate parameters per disk number in one topic (JSON string)
    disk_io_counters/{read_count/write_count/read_bytes/write_bytes/read_time/write_time/read_merged_count/write_merged_count/busy_time}/{0/1/2/etc} - Disk IO counters separate parameters for single disk
    disk_io_counters/*/{0/1/2/etc} - Disk I/O counters for single disk. Topic per parameter
    disk_io_counters/*;/{0/1/2/etc} - Disk I/O counters for single disk in one topic (JSON string)

Network :

    net_io_counters/* - Network I/O counters. Topic per parameter
    net_io_counters/*;  - Network I/O counters in one topic (JSON string)
    net_io_counters/{bytes_sent/bytes_recv/packets_sent/packets_recv/errin/errout/dropin/dropout} - Network I/O counters separate parameters
    net_io_counters/{bytes_sent/bytes_recv/packets_sent/packets_recv/errin/errout/dropin/dropout}/* - Network I/O counters separate parameters. Topic per device name
    net_io_counters/{bytes_sent/bytes_recv/packets_sent/packets_recv/errin/errout/dropin/dropout}/*; - Network I/O counters separate parameters per device in one topic (JSON string)
    net_io_counters/{bytes_sent/bytes_recv/packets_sent/packets_recv/errin/errout/dropin/dropout}/{eth0/wlan0/etc} - Network I/O counters separate parameters for single device
    net_io_counters/*/{eth0/wlan0/etc} - Network I/O counters for single device. Topic per parameter
    net_io_counters/*;/{eth0/wlan0/etc} - Network I/O counters for single device in one topic (JSON string)

Temperature :

    sensors_temperatures/* - Sensors current temperatures. Topic per sensor
    sensors_temperatures/*;  - Sensors current temperatures in one topic (JSON string)
    sensors_temperatures/{SENSOR_NAME} - Single sensor current temperature (could be array value if sensor has several devices)
    sensors_temperatures/{SENSOR_NAME}/* - Single sensor temperatures. Topic per temperature
    sensors_temperatures/{SENSOR_NAME}/*; - Single sensor temperatures in one topic (JSON string)
    sensors_temperatures/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL} - Single sensor device by number/label current temperature
    sensors_temperatures/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/* - Single sensor device by number/label temperature. Topic per parameter
    sensors_temperatures/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/*; - Single sensor device by number/label temperature in one topic (JSON string)
    sensors_temperatures/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/{label/current/high/critical} - Single sensor device by number/label temperature separate parameters

Fan speed :

    sensors_fans/* - Fans current speeds. Topic per fan
    sensors_fans/*;  - Fans current speeds in one topic (JSON string)
    sensors_fans/{SENSOR_NAME} - Single fan current speed (could be array value if fan has several devices)
    sensors_fans/{SENSOR_NAME}/* - Single fan speeds. Topic per speed
    sensors_fans/{SENSOR_NAME}/*; - Single fan speeds in one topic (JSON string)
    sensors_fans/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL} - Single fan device by number/label current speed
    sensors_fans/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/* - Single fan device by number/label speed. Topic per parameter
    sensors_fans/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/*; - Single fan device by number/label speed in one topic (JSON string)
    sensors_fans/{SENSOR_NAME}/{DEVICE_NUMBER/DEVICE_LABEL}/{label/current/high/critical} - Single fan device by number/label speed separate parameters

Battery :

    sensors_battery/* - Battery state. Topic per parameter
    sensors_battery/*;  - Battery state parameters in one topic (JSON string)
    sensors_battery/{percent/secsleft/power_plugged} - Battery state separate parameters
         where secsleft could be
             -1 if time is unknown
             -2 for unlimited time (power is plugged)
             or time in seconds

Other system info :

    users/{name/terminal/host/started}/* - Active users separate parameters. Topic per user
    users/{name/terminal/host/started}/*; - Active users separate parameters per user in one topic (JSON string)
    users/{name/terminal/host/started}/{0/1/2/etc} - Active users separate parameter for single user
    users/*/{0/1/2/etc} - Active users parameters for single user. Topic per parameter
    users/*;/{0/1/2/etc} - Active users parameters for single user in one topic (JSON string)
    boot_time - System boot time as a Unix timestamp
    boot_time/{{x|uptime}} - String representation of up time

Processes :

    pids/* - all system processes IDs. Topic per process
    pids/*; - all system processes IDs in one topic (JSON string)
    pids/{0/1/2/etc} - single process ID
    pids/count - total number of processes
    processes/{PROCESS_ID}/{PARAMETER_NAME} - single process parameter(s)
        where PROCESS_ID could be one of
            - numeric ID of the process
            - top_cpu - top CPU consuming process
            - top_cpu[N] - CPU consuming process number N
            - top_memory - top memory consuming process
            - top_memory[N] - memory consuming process number N
            - pid[PATH] - process with ID specified in the file having PATH path (.pid file). Slashes in path should be replaced with vertical slash
            - name[PATTERN] - process with name matching PATTERN pattern (use * to match zero or more characters, ? for single character)
            - * - to get value of some property for all processes. Topic per process ID
            - *; - to get value of some property for all processes in one topic (JSON string)
        and PARAMETER_NAME could be one of
            - pid - process ID
            - ppid - parent process ID
            - name - process name
            - exe - process executable file
            - cwd - process working directory
            - cmdline/* - command line. Topic per line
            - cmdline/*; - command line in one topic (JSON string)
            - cmdline/count - number of command line lines
            - cmdline/{0/1/etc} - command line single line
            - status - process status (running/sleeping/idle/dead/etc)
            - username - user started process
            - create_time - time when process was started (Unix timestamp)
            - terminal - terminal of the process
            - uids/* - process user IDs. Topic per parameter
            - uids/*; - process user IDs in one topic (JSON string)
            - uids/{real/effective/saved} - process user IDs single parameter
            - gids/* - process group IDs. Topic per parameter
            - gids/*; - process group IDs in one topic (JSON string)
            - gids/{real/effective/saved} - process group IDs single parameter
            - cpu_times/* - process CPU times. Topic per parameter
            - cpu_times/*; - process CPU times in one topic (JSON string)
            - cpu_times/{user/system/children_user/children_system} - process CPU times single parameter
            - cpu_percent - CPU percent used by process
            - memory_percent - memory percent used by process
            - memory_info/* - memory used by process. Topic per parameter
            - memory_info/*; - memory used by process in one topic (JSON string)
            - memory_info/{rss/vms/shared/text/lib/data/dirty/uss/pss/swap} - memory used by process single parameter
            - io_counters/* - process I/O counters. Topic per parameter
            - io_counters/*; - process I/O counters in one topic (JSON string)
            - io_counters/{read_count/write_count/read_bytes/write_bytes} - process I/O single counter
            - num_threads - number of threads
            - num_fds - number of file descriptors
            - num_ctx_switches/* - number of context switches. Topic per parameter
            - num_ctx_switches/*; - number of context switches in one topic (JSON string)
            - num_ctx_switches/{voluntary/involuntary} - context switches single counter
            - nice - nice value
            - * - all process properties. Topic per property
            - *; - all process properties in one topic (JSON string)
            - ** - all process properties and sub-properties. Topic per property
            - **; -  all process properties and sub-properties in one topic (JSON string)

#### Useful Tasks

These are 'tasks' I found most relevant and useful for tracking my
server(s) health and performance:

Task|Description
----|------------
`boot_time`|Up time
`cpu_percent`|CPU total usage in percent
`sensors_temperatures/coretemp/0/`|CPU package temperature
`virtual_memory/percent`|Virtual memory used
`virtual_memory/free/{{x\|GB}}`|Virtual memory free, GB
`swap_memory/percent`|Swap memory used
`disk_usage/percent/\|`|Root drive (forward slash replaced with pipe) usage in percent (Linux)
`disk_usage/free/\|/{{x\|GB}}`|space left in GB for root drive (Linux)
`smart/nvme0/`|All SMART attributes for the device \'nvme0\' (requires root priviliges)
`smart/nvme0/temperature`|Just the device \'nvme0\' temperature (requires root priviliges)
`processes/top_cpu/name`|Name of top process consuming CPU
`processes/top_memory/exe`|Executable file of top process consuming memory
`sensors_fans/dell_smm/0`|Fan seed
`sensors_battery/percent`|Battery charge

### Formatting

The output of each task can be formatted using
[Jinja2](http://jinja.pocoo.org/) templates.

E.g.:   

```
schedule:
  - cron: every 10sec
    tasks:
      - task: cpu_times_percent
        params: [ "user" ]
        formatter: "{{x}}%"
```

configures PSMQTT to append the `%` symbol after CPU usage.

For task providing many outputs (using wildcard `*`) all outputs are
available by name if they are named.
Unnamed outputs are available as `x`.
When the task produces multiple unnamed outputs they are available as `x[1]`, `x[2]`, etc if they are
numbered. 

psmqtt provides some Jinja2 filters:

* `KB`,`MB`,`GB` to format value in bytes as KBytes, MBytes or GBytes.
* `uptime` to format `boot_time` as a human friendly uptime string representation.

Examples:

```
  - task: virtual_memory
    params: [ "*" ]
    # emit free virtual memory in %
    formatter: "{{(100*free/total)|int}}%"

  - task: virtual_memory
    params: [ "free" ]
    # emit free virtual memory in MB instead of bytes
    formatter: "{{x|MB}}"

  - task: cpu_times_percent
    params: [ "user", "*" ]
    # emit total CPU time spend in user mode for the first and second logical cores only
    formatter: "{{x[0]+x[1]}}"

  - task: boot_time
    formatter: "{{x|uptime}}"

```


### MQTT Topic

The `<MQTT topic>` specification in each task definition is optional.
If it is not specified, psmqtt will generate automatically an output MQTT topic 
in the form **psmqtt/COMPUTER_NAME/<task-name>**.

To customize the prefix **psmqtt/COMPUTER_NAME** you can use the `mqtt.publish_topic_prefix`
key in the configuraton file. E.g.:

```
mqtt:
  publish_topic_prefix: my-prefix
```

configures psmqtt to emit all outputs at **my-prefix/<task-name>**.

It's important to note that when the task emits more than one output due to the use of the
wildcard `*` character then the MQTT topic must be specified and must include the 
wildcard `*` character itself.
An example the task

```
schedule:
  - cron: every 10sec
    tasks:
      - task: cpu_times_percent
        params: [ "*" ]
        topic: "cpu/*"
```

is producing 10 percentage outputs on a Linux system; one for each of `user`, `nice`, `system`,
`idle`, `iowait`, `irq`, `softirq`, `steal`, `guest` and `guest_nice` fields emitted by psutil.
These 10 outputs must be published on 10 different MQTT topics.
The use of `cpu/*` configures psmqtt to produce as output topics:
* **psmqtt/COMPUTER_NAME/cpu/user**
* **psmqtt/COMPUTER_NAME/cpu/nice**
* **psmqtt/COMPUTER_NAME/cpu/system**
* **psmqtt/COMPUTER_NAME/cpu/idle**
* **psmqtt/COMPUTER_NAME/cpu/iowait**
* **psmqtt/COMPUTER_NAME/cpu/irq**
* **psmqtt/COMPUTER_NAME/cpu/softirq**
* **psmqtt/COMPUTER_NAME/cpu/steal**
* **psmqtt/COMPUTER_NAME/cpu/guest**
* **psmqtt/COMPUTER_NAME/cpu/guest_nice**

If the wildcard `*` character is used in the task parameters but the MQTT topic is not specified
or does not contain the wildcard `*` character itself, then an error will be produced in psmqtt logs.


## Sending MQTT requests

The [psmqtt.yaml](../psmqtt.yaml) file supports a configuration named "request_topic":

```
mqtt:
  request_topic: request
```

This configuration allows you to specify an MQTT topic that will be **subscribed** 
by psmqtt and used as **input** trigger for emitting measurements.
This is an alternative way to use psmqtt compared to the use of cron expressions.

E.g. to get information for the task `cpu_percent` with MQTT prefix `psmqtt/COMPUTER_NAME` you
need to send any string on the topic **psmqtt/COMPUTER_NAME/request/cpu_percent**.
The result will be pushed on the topic **psmqtt/COMPUTER_NAME/cpu_percent**.
