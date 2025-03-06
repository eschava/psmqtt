# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import time

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
        return RateHandler.compute_rate_from_dicts(new_values._asdict(), last_values._asdict(), delta_time_seconds)

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        if caller_task_id not in self.last_values:
            # this is the first sample being retrieved... just save the current values
            # and we'll be able to compute the rate/delta of the next call
            new_values = self.monotonic_counter_handler.handle(params, caller_task_id)
            new_timestamp = time.time()

            # we return zero(s) on this first sample to avoid pushing a HUGE absolute value
            # which might decrease nearly to zero on the next sample
            if isinstance(new_values, dict):
                result = {k: 0 for k in new_values.keys()}
            elif isinstance(new_values, tuple):
                result = (0,) * len(new_values)
            elif isinstance(new_values, int):
                result = 0
            else:
                raise Exception(f"{self.name}: Unexpected result type: {type(new_values)}")

            #logging.debug(f"{self.name}: producing first sample as zeroes for caller task {caller_task_id}: {result}")

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
                return old_values

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
