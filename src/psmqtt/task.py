# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from enum import IntEnum
import json
import logging
import hashlib
import psutil
from typing import Any, List, Dict

from .handlers_base import TaskParam
from .topic import Topic
from .mqtt_client import MqttClient
from .formatter import Formatter

from .handlers_base import Payload, TupleCommandHandler, ValueCommandHandler, IndexCommandHandler, IndexOrTotalCommandHandler, IndexTupleCommandHandler, IndexOrTotalTupleCommandHandler
from .handlers_psutil_processes import ProcessesCommandHandler
from .handlers_psutil import DiskIOCountersCommandHandler, DiskIOCountersRateHandler, DiskUsageCommandHandler, NetIOCountersCommandHandler, NetIOCountersRateHandler, SensorsFansCommandHandler, SensorsTemperaturesCommandHandler, GetLoadAvgCommandHandler
from .handlers_pysmart import SmartCommandHandler

class Task:
    '''
    Defines a psmqtt task, whose main properties are:
     * "task name"
     * "params"
     * "topic" and
     * "formatter"
     * "ha_discovery"
    fields.
    '''

    # Counts how many tasks triggered an errors during their execution
    num_errors = 0

    # Counts successfully-completed tasks
    num_success = 0

    # Global dictionary of supported task handlers
    handlers = {

        # CPU

        'cpu_times': TupleCommandHandler('cpu_times'),

        'cpu_percent': type(
            "CpuPercentCommandHandler",
            (IndexOrTotalCommandHandler, object),
            {
                "get_value": lambda self, total:
                    psutil.cpu_percent(percpu=not total)
            })('cpu_percent'),

        'cpu_times_percent': type(
            "CpuTimesPercentCommandHandler",
            (IndexOrTotalTupleCommandHandler, object),
            {
                "get_value": lambda self, total:
                    psutil.cpu_times_percent(percpu=not total)
            })('cpu_times_percent'),

        'cpu_stats': TupleCommandHandler('cpu_stats'),

        'getloadavg': GetLoadAvgCommandHandler(),

        # MEMORY

        'virtual_memory': TupleCommandHandler('virtual_memory'),
        'swap_memory': TupleCommandHandler('swap_memory'),

        # DISK

        'disk_partitions': IndexTupleCommandHandler('disk_partitions'),
        'disk_usage': DiskUsageCommandHandler(),
        'disk_io_counters': DiskIOCountersCommandHandler(),
        'disk_io_counters_rate': DiskIOCountersRateHandler(),
        'smart': SmartCommandHandler(),

        # NETWORK

        'net_io_counters': NetIOCountersCommandHandler(),
        'net_io_counters_rate': NetIOCountersRateHandler(),

        # PROCESSES

        'processes': ProcessesCommandHandler(),

        # OTHERS

        'users': IndexTupleCommandHandler('users'),
        'boot_time': ValueCommandHandler('boot_time'),
        'pids': IndexCommandHandler('pids'),

        # SENSORS

        'sensors_temperatures': SensorsTemperaturesCommandHandler(),
        'sensors_fans': SensorsFansCommandHandler(),
        'sensors_battery': TupleCommandHandler('sensors_battery'),
    }

    def __init__(self,
            name:str,
            params:List[str],
            mqtt_topic:str,
            formatter_str:str,
            ha_discovery:Dict[str,Any],
            mqtt_topic_prefix:str,
            parent_schedule_rule_idx:int,
            task_idx:int) -> None:
        self.task_name = name
        self.params = params
        self.topic_name = mqtt_topic
        self.formatter = Formatter(formatter_str) if formatter_str is not None and formatter_str != '' else None
        self.ha_discovery = ha_discovery

        self.parent_schedule_rule_idx = parent_schedule_rule_idx
        self.task_friendly_name = f"schedule{parent_schedule_rule_idx}.task{task_idx}.{name}"
        self.task_id = f"{parent_schedule_rule_idx}.{task_idx}"

        # create a Topic instance associated with this Task:
        if self.topic_name is None or self.topic_name == '':
            self.topic = self._topic_from_task(mqtt_topic_prefix)
        else:
            # use the specified MQTT topic name; just make sure that the MQTT topic prefix is present
            self.topic = Topic(self.topic_name if self.topic_name.startswith(mqtt_topic_prefix)
                                else mqtt_topic_prefix + self.topic_name)

        logging.info(f"Task.run_task({self.task_friendly_name}): MQTT topic is '{self.topic.get_topic()}'")
        assert self.topic.get_topic() != ''

    def _topic_from_task(self, topic_prefix: str) -> Topic:
        # create the MQTT topic by concatenating the task name and its parameters with the MQTT topic-level separator '/'
        topicName = topic_prefix + self.task_name
        nonEmptyParams = [x for x in self.params if x != '']

        escapedParams = []
        for x in nonEmptyParams:
            if isinstance(x,str):
                if TaskParam.is_join_wildcard(x):
                    # skip any join wildcard (+) parameter from the MQTT topic; do insert however the regular wildcard (*)
                    # so that the Topic class knows that it's actually a multi-topic
                    continue
                else:
                    escapedParams.append(x.replace('/', '|'))
            elif isinstance(x,int):
                escapedParams.append(str(x))
        if len(escapedParams) > 0:
            topicName += '/' + '/'.join(escapedParams)

        # ensure no empty topic-level separators are present:
        return Topic(topicName.replace("//", "/"))

    @staticmethod
    def _payload_as_string(v:Any) -> str:
        if isinstance(v, dict):
            return json.dumps(v)
        elif isinstance(v, IntEnum):
            return str(v.value)
        elif not isinstance(v, list):
            return str(v)
        elif len(v) == 1:  # single-element array should be presented as single value
            return Task._payload_as_string(v[0])
        #else:
        return json.dumps(v)

    @staticmethod
    def get_supported_handlers() -> List[str]:
        '''
        Returns list of supported handlers
        '''
        return list(Task.handlers.keys())

    def run_task(self, mqttc: MqttClient) -> None:
        '''
        Runs this task and publishes results on the provided MQTT client
        '''
        assert mqttc is not None

        if not mqttc.is_connected():
            logging.warning(f"Aborting task {self.task_friendly_name}: no MQTT connection available at this time")
            Task.num_errors += 1
            return

        try:
            payload = self.get_payload()
            is_seq = isinstance(payload, list) or isinstance(payload, dict)
            if is_seq and not self.topic.is_multitopic():
                raise Exception(f"Result of task '{self.task_friendly_name}' has several values but topic doesn't contain the wildcard '*' character. Please include the wildcard in the topic specification.")
            if not is_seq and self.topic.is_multitopic():
                raise Exception(f"Result of task '{self.task_friendly_name}' has a single value but the topic contains the wildcard '*' character. Please remove the wildcard from the topic specification.")

            if isinstance(payload, list):
                for i, v in enumerate(payload):
                    subtopic = self.topic.get_subtopic(str(i))
                    mqttc.publish(subtopic, Task._payload_as_string(v))

            elif isinstance(payload, dict):
                for key in payload:
                    subtopic = self.topic.get_subtopic(str(key))
                    v = payload[key]
                    mqttc.publish(subtopic, Task._payload_as_string(v))
            else:
                mqttc.publish(self.topic.get_topic(), Task._payload_as_string(payload))

        except Exception as ex:
            mqttc.publish(self.topic.get_error_topic(), str(ex))
            logging.exception(f"Task.run_task({self.task_friendly_name}) failed: {ex}")
            Task.num_errors += 1

        Task.num_success += 1
        return

    def get_payload(self) -> Payload:
        '''
        Invokes the handler associated with this task (the task name defines the handler to be invoked);
        the handler will retrieves the sensor value(s), filter them and returns it/them.

        Then this function formats the output(s) invoking the Task formatter.
        '''
        if self.task_name not in Task.handlers:
            raise Exception(f"Task '{self.task_name}' is not supported")

        # invoke the handler to read the sensor values
        handler = Task.handlers[self.task_name]
        value = handler.handle(self.params, self.task_id)

        # if we get here, the sensor reading was successful
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            is_seq = isinstance(value, list) or isinstance(value, dict)
            if is_seq:
                logging.debug(f"Task.get_payload({self.task_friendly_name}) produced multi-valued output:\n{value}")
            else:
                logging.debug(f"Task.get_payload({self.task_friendly_name}) produced single-valued output: {value}")

        if self.formatter is not None:
            value = self.formatter.format(value)
            logging.debug(f"Task.get_payload({self.task_friendly_name}) after formatting with {self.formatter.get_template()} => {value}")

        # the value must be one of the types declared inside "Payload"
        assert isinstance(value, str) or isinstance(value, int) or isinstance(value, float) or isinstance(value, list) or isinstance(value, dict) or isinstance(value, tuple)

        return value

    @staticmethod
    def num_total_tasks_executed() -> int:
        '''
        Returns the total number of tasks executed so far, both those successful and those failed.
        '''
        return Task.num_success + Task.num_errors

    def get_ha_unique_id(self, device_name:str) -> str:
        '''
        Returns a reasonable-unique ID to be used inside HA discovery messages
        '''

        nonEmptyParams = [str(x) for x in self.params if x != '']
        concatenated = "".join(nonEmptyParams)
        hash_object = hashlib.sha256(concatenated.encode())
        hash_hex = hash_object.hexdigest()
        return f"{device_name}-{self.task_name}-{hash_hex[:12]}"

    def get_ha_discovery_payload(self, device_name:str, psmqtt_ver:str, device_dict:Dict[str,str], default_expire_after:int) -> str:
        '''
        Returns an HomeAssistant MQTT discovery message associated with this task.
        This method is only available for single-valued tasks, having their "ha_discovery" metadata
        populated in the configuration file.
        See https://www.home-assistant.io/integrations/mqtt/#discovery-messages
        '''
        if self.ha_discovery is None:
            return None
        if self.topic.is_multitopic():
            raise Exception(f"Task '{self.task_friendly_name}' has HA discovery configured but the topic contains the wildcard '*' character, so this is a multi-result task. HA discovery options are not supported on multi-result tasks.")

        # required parameters
        if self.ha_discovery["name"] is None or self.ha_discovery["name"] == '':
            raise Exception(f"Task '{self.task_friendly_name}' has invalid HA discovery 'name' property.")

        msg = {
            "device": device_dict,
            "origin": {
                "name":"psmqtt",
                "sw": psmqtt_ver,
                "url": "https://github.com/eschava/psmqtt"
            },
            "unique_id": self.get_ha_unique_id(device_name),
            "state_topic": self.topic.get_topic(),
            "name": self.ha_discovery["name"],
        }

        # optional parameters
        # FIXME: should we add also "availability_topic", "payload_available", "payload_not_available" ?
        optional_parameters = ["icon", "device_class", "state_class", "unit_of_measurement", "payload_on", "payload_off"]
        for o in optional_parameters:
            if o in self.ha_discovery and self.ha_discovery[o]:
                msg[o] = self.ha_discovery[o]

        # expire_after is populated with user preference or a meaningful default value:
        if self.ha_discovery["expire_after"]:
            msg["expire_after"] = self.ha_discovery["expire_after"]
        elif default_expire_after:
            msg["expire_after"] = default_expire_after

        return json.dumps(msg)

    def get_ha_discovery_topic(self, ha_topic:str, device_name:str) -> str:
        '''
        Returns the TOPIC associated with the PAYLOAD returned by get_ha_discovery_payload()
        '''
        # the topic shall be in format
        #   <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
        # see https://www.home-assistant.io/integrations/mqtt/#discovery-topic
        unique_id = self.get_ha_unique_id(device_name)
        return f"{ha_topic}/{self.ha_discovery['platform']}/{device_name}/{unique_id}/config"
