# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from enum import IntEnum
import json
import logging
from typing import Any, List

from .handlers import get_value
from .topic import Topic
from .mqtt_client import MqttClient


class Task:
    '''
    Defines a psmqtt task, whose main properties are:
     * "task name"
     * "params"
     * "topic" and
     * "formatter"
    fields.
    '''

    # Counter of all errors that occurred during (any) task execution
    num_errors = 0

    def __init__(self,
            name:str,
            params:List[str],
            mqtt_topic:str,
            formatter:str,
            parent_schedule_rule_idx:int) -> None:
        self.task_name = name
        self.params = params
        self.topic_name = mqtt_topic
        self.formatter = formatter
        self.parent_schedule_rule_idx = parent_schedule_rule_idx

    def run_task(self, mqttc: MqttClient, taskFriendlyId: str) -> None:
        '''
        Runs a task
        '''
        assert mqttc is not None

        global num_errors

        def payload_as_string(v:Any) -> str:
            if isinstance(v, dict):
                return json.dumps(v)
            elif isinstance(v, IntEnum):
                return str(v.value)
            elif not isinstance(v, list):
                return str(v)
            elif len(v) == 1:  # single-element array should be presented as single value
                return payload_as_string(v[0])
            #else:
            return json.dumps(v)

        if self.topic_name is None:
            topic = Topic.from_task(mqttc.topic_prefix, self)
        else:
            # use the specified MQTT topic name; just make sure that the MQTT topic prefix is present
            topic = Topic(self.topic_name if self.topic_name.startswith(mqttc.topic_prefix)
                                else mqttc.topic_prefix + self.topic_name)
        logging.debug(f"run_task({taskFriendlyId}): mqtt topic is '{topic.get_topic()}'")

        try:
            payload = get_value(self.task_name, self.params, self.formatter)
            is_seq = isinstance(payload, list) or isinstance(payload, dict)
            if is_seq and not topic.is_multitopic():
                raise Exception(f"Result of task '{taskFriendlyId}' has several values but topic doesn't contain '*' char")

            if isinstance(payload, list):
                for i, v in enumerate(payload):
                    subtopic = topic.get_subtopic(str(i))
                    mqttc.publish(subtopic, payload_as_string(v))

            elif isinstance(payload, dict):
                for key in payload:
                    subtopic = topic.get_subtopic(str(key))
                    v = payload[key]
                    mqttc.publish(subtopic, payload_as_string(v))
            else:
                mqttc.publish(topic.get_topic(), payload_as_string(payload))

        except Exception as ex:
            mqttc.publish(topic.get_error_topic(), str(ex))
            logging.exception(f"run_task caught: {self} : {ex}")
            num_errors += 1
        return
