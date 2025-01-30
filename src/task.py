# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from enum import IntEnum
import json
import logging
from typing import Any, List

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
            parent_schedule_rule_idx:int,
            task_idx:int) -> None:
        self.task_name = name
        self.params = params
        self.topic_name = mqtt_topic
        self.formatter = formatter
        self.parent_schedule_rule_idx = parent_schedule_rule_idx
        self.task_friendly_name = f"schedule{parent_schedule_rule_idx}.task{task_idx}.{name}"

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

        if self.topic_name is None:
            topic = self._topic_from_task(mqttc.topic_prefix)
        else:
            # use the specified MQTT topic name; just make sure that the MQTT topic prefix is present
            topic = Topic(self.topic_name if self.topic_name.startswith(mqttc.topic_prefix)
                                else mqttc.topic_prefix + self.topic_name)
        logging.debug(f"Task.run_task({self.task_friendly_name}): mqtt topic is '{topic.get_topic()}'")

        try:
            payload = TaskHandlers.get_value(self.task_name, self.params, self.formatter)
            is_seq = isinstance(payload, list) or isinstance(payload, dict)
            if is_seq and not topic.is_multitopic():
                raise Exception(f"Result of task '{self.task_friendly_name}' has several values but topic doesn't contain the wildcard '*' character. Please include the wildcard in the topic specification.")
            if not is_seq and topic.is_multitopic():
                raise Exception(f"Result of task '{self.task_friendly_name}' has a single value but the topic contains the wildcard '*' character. Please remove the wildcard from the topic specification.")

            if isinstance(payload, list):
                for i, v in enumerate(payload):
                    subtopic = topic.get_subtopic(str(i))
                    mqttc.publish(subtopic, Task._payload_as_string(v))

            elif isinstance(payload, dict):
                for key in payload:
                    subtopic = topic.get_subtopic(str(key))
                    v = payload[key]
                    mqttc.publish(subtopic, Task._payload_as_string(v))
            else:
                mqttc.publish(topic.get_topic(), Task._payload_as_string(payload))

        except Exception as ex:
            mqttc.publish(topic.get_error_topic(), str(ex))
            logging.exception(f"Task.run_task({self.task_friendly_name}) failed: {ex}")
            Task.num_errors += 1

        Task.num_success += 1
        return

    @staticmethod
    def num_total_tasks() -> int:
        return Task.num_success + Task.num_errors
