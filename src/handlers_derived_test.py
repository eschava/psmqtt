# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest
import time

from .handlers_base import BaseHandler, Payload
from .handlers_derived import RateHandler

fake_task_id = "0.0"


class MonotonicTestHandler(BaseHandler):

    def __init__(self, name):
        super().__init__(name)
        self.value1 = 0
        self.value2 = 10

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        self.value1 += 1
        self.value2 += 1
        return {'value1': self.value1, 'value2': self.value2}

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_RateHandler_with_dicts(self) -> None:

        handler = RateHandler("test", MonotonicTestHandler("test"))
        dict_rate = handler.handle(['all','params','ignored'], fake_task_id)
        assert isinstance(dict_rate, dict)

        # even if the monotonic handler returns a dict, the rate handler returns a dict filled with ZEROS
        self.assertEqual(dict_rate["value1"], 0)
        self.assertEqual(dict_rate["value2"], 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        dict_rate2 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(dict_rate2["value1"], 0)
        self.assertEqual(dict_rate2["value2"], 0)

        # now sleep enough time to get a rate > 0
        time.sleep(RateHandler.MINIMAL_DELTA_TIME_SECONDS + 0.1)
        dict_rate3 = handler.handle(['all','params','ignored'], fake_task_id)

        # afterwards we should get a rate > 0 for each value
        # the exact rate value will be 1/elapsed_time_sec.. so to avoid making this unit test flaky,
        # we just check that the rate is greater than zero
        self.assertGreater(dict_rate3["value1"], 0)
        self.assertGreater(dict_rate3["value2"], 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        dict_rate4 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(dict_rate4["value1"], 0)
        self.assertEqual(dict_rate4["value2"], 0)
