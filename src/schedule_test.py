# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .schedule import Schedule

@pytest.mark.unit
class TestTask(unittest.TestCase):

    def test_schedule_ctor(self):
        s = Schedule("every minute",
                     [{
                         "task": "my_task",
                         "params": [],
                         "topic": "foobar",
                         "formatter": "a-fake-one",
                         "ha_discovery": None
                        }],
                     "some-mqtt-prefix",
                     42)
        self.assertEqual(1, len(s.get_tasks()))

    def test_schedule_max_interval(self):

        testcases = [
            {
                "cron": "every 42 seconds",
                "expected_max_interval": 42,
            }
        ]

        for t in testcases:
            s = Schedule(t["cron"],
                     [],
                     "some-mqtt-prefix",
                     42)
            self.assertEqual(t["expected_max_interval"], s.get_max_interval_sec())
