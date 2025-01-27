# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .topic import Topic

def get_subtopic(topic:str, param:str) -> str:
    t = Topic(topic)
    return t.get_subtopic(param) if t.is_multitopic() else topic

@pytest.mark.unit
class TopicTest(unittest.TestCase):

    def test_get_subtopic(self) -> None:
        self.assertEqual("/haha", get_subtopic('/haha', 'a'))
        self.assertEqual("/a", get_subtopic('/*', 'a'))
        self.assertEqual("/a", get_subtopic('/**', 'a'))
        self.assertEqual("/a/*", get_subtopic('/*/*', 'a'))
        self.assertEqual("/a/**", get_subtopic('/*/**', 'a'))
        self.assertEqual("/a/**", get_subtopic('/**/**', 'a'))

        # wildcard inside brackets
        self.assertEqual("/name[ppp*]/a", get_subtopic('/name[ppp*]/**', 'a'))
        self.assertEqual("/name[ppp*]/*;", get_subtopic('/name[ppp*]/*;', 'a'))
        self.assertEqual("/name[ppp*]/haha", get_subtopic('/name[ppp*]/haha', 'a'))
        self.assertEqual("/a/name[ppp*]/**", get_subtopic('/*/name[ppp*]/**', 'a'))
        self.assertEqual("/a/name[ppp*]/**", get_subtopic('/**/name[ppp*]/**', 'a'))
        self.assertEqual("/*;/name[ppp*]/a", get_subtopic('/*;/name[ppp*]/**', 'a'))
        self.assertEqual("/**;/name[ppp*]/a", get_subtopic('/**;/name[ppp*]/**', 'a'))
        self.assertEqual("/**;/name[ppp*]/*;", get_subtopic('/**;/name[ppp*]/*;', 'a'))

        # wildcard with ;
        self.assertEqual("/*;", get_subtopic('/*;', 'a'))
        self.assertEqual("/**;", get_subtopic('/**;', 'a'))
        self.assertEqual("/*;/a", get_subtopic('/*;/*', 'a'))
        self.assertEqual("/*;/a", get_subtopic('/*;/**', 'a'))
        self.assertEqual("/*;/*;", get_subtopic('/*;/*;', 'a'))
        self.assertEqual("/*;/**;", get_subtopic('/*;/**;', 'a'))

    def test_from_task(self):

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
            topic = Topic.from_task(t["prefix"], t["input_task"])
            self.assertEqual(topic.get_topic(), t["expected_topic_name"])
