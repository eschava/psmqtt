# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest
import time
from collections import namedtuple

from .handlers_base import BaseHandler, Payload
from .handlers_derived import RateHandler

fake_task_id = "0.0"


class MonotonicTestHandler(BaseHandler):

    def __init__(self, name, type_to_return):
        super().__init__(name)
        self.value1 = 0
        self.value2 = 10
        self.type_to_return = type_to_return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        self.value1 += 1
        self.value2 += 1
        if self.type_to_return == "dict":
            return {'value1': self.value1, 'value2': self.value2}
        elif self.type_to_return == "namedtuple":
            t = namedtuple('TestTuple', ['value1', 'value2'])
            return t(self.value1, self.value2)
        elif self.type_to_return == "int":
            return self.value1
        else:
            raise Exception("Invalid type")

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_RateHandler_with_dicts(self) -> None:

        handler = RateHandler("test", MonotonicTestHandler("test", "dict"))
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

    def test_RateHandler_with_namedtuples(self) -> None:

        handler = RateHandler("test", MonotonicTestHandler("test", "namedtuple"))
        tuple_rate = handler.handle(['all','params','ignored'], fake_task_id)
        assert isinstance(tuple_rate, tuple)

        # even if the monotonic handler returns a tuple, the rate handler returns a tuple filled with ZEROS
        self.assertEqual(tuple_rate[0], 0)
        self.assertEqual(tuple_rate[1], 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        tuple_rate2 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(tuple_rate2[0], 0)
        self.assertEqual(tuple_rate2[1], 0)

        # now sleep enough time to get a rate > 0
        time.sleep(RateHandler.MINIMAL_DELTA_TIME_SECONDS + 0.1)
        tuple_rate3 = handler.handle(['all','params','ignored'], fake_task_id)

        # afterwards we should get a rate > 0 for each value
        # the exact rate value will be 1/elapsed_time_sec.. so to avoid making this unit test flaky,
        # we just check that the rate is greater than zero
        print(tuple_rate3)
        self.assertGreater(tuple_rate3[0], 0)
        self.assertGreater(tuple_rate3[1], 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        tuple_rate4 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(tuple_rate4[0], 0)
        self.assertEqual(tuple_rate4[1], 0)

    def test_RateHandler_with_int(self) -> None:

        handler = RateHandler("test", MonotonicTestHandler("test", "int"))
        int_rate = handler.handle(['all','params','ignored'], fake_task_id)
        assert isinstance(int_rate, int)

        # even if the monotonic handler returns a tuple, the rate handler returns a tuple filled with ZEROS
        self.assertEqual(int_rate, 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        int_rate2 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(int_rate2, 0)

        # now sleep enough time to get a rate > 0
        time.sleep(RateHandler.MINIMAL_DELTA_TIME_SECONDS + 0.1)
        int_rate3 = handler.handle(['all','params','ignored'], fake_task_id)

        # afterwards we should get a rate > 0 for each value
        # the exact rate value will be 1/elapsed_time_sec.. so to avoid making this unit test flaky,
        # we just check that the rate is greater than zero
        print(int_rate3)
        self.assertGreater(int_rate3, 0)

        # if we invoke the RateHandler too quickly, we will get zeroes as rate:
        int_rate4 = handler.handle(['all','params','ignored'], fake_task_id)
        self.assertEqual(int_rate4, 0)
