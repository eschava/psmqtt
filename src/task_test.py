# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .task import Task

@pytest.mark.unit
class TestTask(unittest.TestCase):

    def test_get_payload(self) -> None:

        testcases = [
            {
                "input_task": {"task": "cpu_percent", "params": [], "formatter": ""},
                "expected_float_payload": True,
            },
            {
                "input_task": {"task": "virtual_memory", "params": ["percent"], "formatter": ""},
                "expected_float_payload": True,
            },
        ]

        for t in testcases:
            task = Task(
                t["input_task"]["task"],
                t["input_task"]["params"],
                "",  # mqtt_topic
                t["input_task"]["formatter"],  # formatter
                {},  # ha_discovery
                "",  # mqtt_topic_prefix
                0, 0)

            payload = task.get_payload()

            if t["expected_float_payload"]:
                self.assertIsInstance(payload, float)

        return

    def test_topic_from_task(self):

        testcases = [
            {
                "prefix": "prefix/",
                "input_task": {"task": "my_task", "params": []},
                "expected_topic_name": "prefix/my_task"
            },
            {
                "prefix": "prefix/",
                "input_task": {"task": "another_task", "params": ["param1", "param2"]},
                "expected_topic_name": "prefix/another_task/param1/param2"
            },
            # with empty params:
            {
                "prefix": "prefix/",
                "input_task": {"task": "yet_another_task", "params": ["", "param1", "", "param2", ""]},
                "expected_topic_name": "prefix/yet_another_task/param1/param2"
            },
            # with slashes in params:
            {
                "prefix": "prefix/",
                "input_task": {"task": "slashed_task", "params": ["param1", "/", "param/2", ""]},
                "expected_topic_name": "prefix/slashed_task/param1/|/param|2"
            },
            # with integer params:
            {
                "prefix": "prefix/",
                "input_task": {"task": "integer_task", "params": ["param1", 123, "param2"]},
                "expected_topic_name": "prefix/integer_task/param1/123/param2"
            },
            # empty prefix:
            {
                "prefix": "",
                "input_task": {"task": "no_prefix_task", "params": ["param1", "/", "param/2", ""]},
                "expected_topic_name": "no_prefix_task/param1/|/param|2"
            },

        ]

        for t in testcases:
            task = Task(
                t["input_task"]["task"],
                t["input_task"]["params"],
                "",  # mqtt_topic
                "",  # formatter
                {},  # ha_discovery
                "",  # mqtt_topic_prefix
                0, 0)
            topic = task._topic_from_task(t["prefix"])
            self.assertEqual(topic.get_topic(), t["expected_topic_name"])

    def test_get_ha_unique_id_non_empty_params(self):
        test_task = Task(
            'test_task',
            ['param1', '', 'param3'],
            "",  # mqtt_topic
            "",  # formatter
            {},  # ha_discovery
            "",  # mqtt_topic_prefix
            0, 0)

        self.assertEqual("test_device-test_task-5c78554a57cf", test_task.get_ha_unique_id('test_device'))

        # check that changing the task name changes the unique_id non-hashed portion:
        test_task.task_name = "another_task"
        self.assertEqual("test_device-another_task-5c78554a57cf", test_task.get_ha_unique_id('test_device'))

        # check that removal of an empty parameter does not impact the unique_id
        # (IS THIS A GOOD THING? MAYBE NOT!)
        test_task.params = ["param1", "param3"]
        self.assertEqual("test_device-another_task-5c78554a57cf", test_task.get_ha_unique_id('test_device'))

        # check that different parameters produce a different unique_id:
        test_task.params = ["param1-modified", "", "param3"]
        self.assertEqual("test_device-another_task-5b5b5ff7cff8", test_task.get_ha_unique_id('test_device'))
