# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .task import Task

@pytest.mark.unit
class TestTask(unittest.TestCase):

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
            task = Task(t["input_task"]["task"], t["input_task"]["params"], "", "", 0, 0)
            topic = task._topic_from_task(t["prefix"])
            self.assertEqual(topic.get_topic(), t["expected_topic_name"])
