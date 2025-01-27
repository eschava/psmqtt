# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from enum import IntEnum
import json
import logging
from typing import Any, Dict

from .handlers import get_value
from .topic import Topic
from .mqtt_client import MqttClient

# FIXME: introduce a Task class and move run_task() to it
# FIXME: introduce a Task class and move num_errors into it
num_errors = 0


def run_task(mqttc: MqttClient, taskFriendlyId: str, task: Dict[str,str]) -> None:
    '''
    Runs a task, defined as a dictionary having "task", "params", "topic" and "formatter" fields.
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

    if task["topic"] is None:
        topic = Topic.from_task(mqttc.topic_prefix, task)
    else:
        # use the specified MQTT topic name; just make sure that the MQTT topic prefix is present
        topic = Topic(task["topic"] if task["topic"].startswith(mqttc.topic_prefix)
                            else mqttc.topic_prefix + task["topic"])
    logging.debug(f"run_task({taskFriendlyId}): mqtt topic is '{topic.get_topic()}'")

    try:
        payload = get_value(task["task"], task["params"], task["formatter"])
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
        logging.exception(f"run_task caught: {task} : {ex}")
        num_errors += 1
    return
