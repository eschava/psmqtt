# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from enum import IntEnum
import json
import logging
import hashlib
from typing import Any, List, Dict

from .handlers_base import BaseHandler
from .handlers_all import TaskHandlers
from .topic import Topic
from .mqtt_client import MqttClient


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

    def __init__(self,
            name:str,
            params:List[str],
            mqtt_topic:str,
            formatter:str,
            ha_discovery:Dict[str,Any],
            mqtt_topic_prefix:str,
            parent_schedule_rule_idx:int,
            task_idx:int) -> None:
        self.task_name = name
        self.params = params
        self.topic_name = mqtt_topic
        self.formatter = formatter
        self.ha_discovery = ha_discovery

        self.parent_schedule_rule_idx = parent_schedule_rule_idx
        self.task_friendly_name = f"schedule{parent_schedule_rule_idx}.task{task_idx}.{name}"

        # create a Topic instance associated with this Task:
        if self.topic_name is None:
            self.topic = self._topic_from_task(mqtt_topic_prefix)
        else:
            # use the specified MQTT topic name; just make sure that the MQTT topic prefix is present
            self.topic = Topic(self.topic_name if self.topic_name.startswith(mqtt_topic_prefix)
                                else mqtt_topic_prefix + self.topic_name)
        logging.info(f"Task.run_task({self.task_friendly_name}): MQTT topic is '{self.topic.get_topic()}'")

    def _topic_from_task(self, topic_prefix: str) -> Topic:
        # create the MQTT topic by concatenating the task name and its parameters with the MQTT topic-level separator '/'
        topicName = topic_prefix + self.task_name
        nonEmptyParams = [x for x in self.params if x != '']

        escapedParams = []
        for x in nonEmptyParams:
            if isinstance(x,str):
                if BaseHandler.is_join_wildcard(x):
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
            payload = TaskHandlers.get_value(self.task_name, self.params, self.formatter)
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
        if self.ha_discovery["icon"]:
            msg["icon"] = self.ha_discovery["icon"]
        if self.ha_discovery["device_class"]:
            msg["device_class"] = self.ha_discovery["device_class"]
        if self.ha_discovery["unit_of_measurement"]:
            msg["unit_of_measurement"] = self.ha_discovery["unit_of_measurement"]
        if self.ha_discovery["payload_on"]:
            msg["payload_on"] = self.ha_discovery["payload_on"]
        if self.ha_discovery["payload_off"]:
            msg["payload_off"] = self.ha_discovery["payload_off"]
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
