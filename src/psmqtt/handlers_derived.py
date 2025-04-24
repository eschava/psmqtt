# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import time

from typing import (
    Any,
)
from .handlers_base import BaseHandler, Payload

class RateHandler(BaseHandler):
    '''
    RateHandler computes the rate of change of another handler.
    This is often useful when psutil provides monotonically increasing counters
    (e.g. disk I/O counters or network I/O counters) as their rate (or variation over time, or first derivative)
    is typically what makes sense to inspect.
    '''

    MINIMAL_DELTA_TIME_SECONDS = 0.1

    def __init__(self, name: str, monotonic_counter_handler: BaseHandler) -> None:
        super().__init__(name)
        self.monotonic_counter_handler = monotonic_counter_handler
        self.last_values = {}
        self.last_timestamp = {}
        return

    @staticmethod
    def compute_rate_from_dicts(new_values: dict, last_values: dict, delta_time_seconds: float) -> dict:
        # compute the rate of change of the counters
        result = {}
        for k in new_values.keys():
            if k in last_values:
                # IMPORTANT: no checks are done on the result being negative... ideally this should never happen
                #            unless psutil has some internal counter reset and its monotonically increasing counters
                #            happen to decrease. This is not expected to happen in normal operation.
                result[k] = int((new_values[k] - last_values[k]) / delta_time_seconds)
            else:
                result[k] = new_values[k]

        return result

    @staticmethod
    def compute_rate_from_tuples(new_values: tuple, last_values: tuple, delta_time_seconds: float) -> dict:
        # compute the rate of change of the counters
        result_list = []
        min_len = min(len(new_values), len(last_values))
        for idx in range(0,min_len):
            # IMPORTANT: no checks are done on the result being negative... ideally this should never happen
            #            unless psutil has some internal counter reset and its monotonically increasing counters
            #            happen to decrease. This is not expected to happen in normal operation.
            result_list.append(int((new_values[idx] - last_values[idx]) / delta_time_seconds))
        return tuple(result_list)

    @staticmethod
    def produce_zeroes_with_same_type_of(type_to_return: Any) -> Any:
        if isinstance(type_to_return, dict):
            return {k: 0 for k in type_to_return.keys()}
        elif isinstance(type_to_return, tuple):
            return (0,) * len(type_to_return)
        elif isinstance(type_to_return, int):
            return 0
        else:
            raise Exception(f"Unexpected type: {type(type_to_return)}")

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        if caller_task_id not in self.last_values:
            # this is the first sample being retrieved... just save the current values
            # and we'll be able to compute the rate/delta of the next call
            new_values = self.monotonic_counter_handler.handle(params, caller_task_id)
            new_timestamp = time.time()

            # we return zero(s) on this first sample to avoid pushing a HUGE absolute value
            # which might decrease nearly to zero on the next sample
            #logging.debug(f"{self.name}: producing first sample as zeroes for caller task {caller_task_id}: {result}")
            result = RateHandler.produce_zeroes_with_same_type_of(new_values)

            # fall to the end of the function where we update internal state
        else:
            # retrieve previous values / timestamp -- we know they are in the internal state
            old_values = self.last_values[caller_task_id]
            old_timestamp = self.last_timestamp[caller_task_id]

            # get the new sensor readings:
            new_values = self.monotonic_counter_handler.handle(params, caller_task_id)
            new_timestamp = time.time()

            delta_time_seconds = new_timestamp - old_timestamp
            if delta_time_seconds <= RateHandler.MINIMAL_DELTA_TIME_SECONDS:
                # delta is too small... return the last value and skip any internal update
                return RateHandler.produce_zeroes_with_same_type_of(new_values)

            #logging.debug(f"{self.name}: computing rate with delta_time_seconds={delta_time_seconds} for caller task {caller_task_id}")

            if isinstance(new_values, dict):
                assert isinstance(old_values, dict)
                result = RateHandler.compute_rate_from_dicts(new_values, old_values, delta_time_seconds)
            elif isinstance(new_values, tuple):
                assert isinstance(old_values, tuple)
                result = RateHandler.compute_rate_from_tuples(new_values, old_values, delta_time_seconds)
            elif isinstance(new_values, int):
                assert isinstance(old_values, int)
                # IMPORTANT: no checks are done on the result being negative... ideally this should never happen
                #            unless psutil has some internal counter reset and its monotonically increasing counters
                #            happen to decrease. This is not expected to happen in normal operation.
                result = int((new_values - old_values) / delta_time_seconds)
            else:
                raise Exception(f"{self.name}: Unexpected result type: {type(new_values)}")

        # update internal state (by caller task)
        self.last_values[caller_task_id] = new_values
        self.last_timestamp[caller_task_id] = new_timestamp
        return result

    def get_value(self) -> Payload:
        raise Exception("This method should not be called")
