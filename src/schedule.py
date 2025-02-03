# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from recurrent import RecurringEvent
from dateutil.rrule import rrulestr
import logging
import datetime
from typing import Any, Dict, List

from .task import Task


class Schedule:
    '''
    Defines a psmqtt SCHEDULING RULE, whose main properties are:
    * "cron" which defines how frequently this rule will run
    " "ts a list of Task classes
    '''

    def __init__(self,
            cron:str,
            tasks_dict:List[Dict[str,Any]],
            mqtt_topic_prefix:str,
            schedule_rule_idx:int) -> None:
        self.cron_expr = cron
        self.schedule_rule_idx = schedule_rule_idx

        # parse the cron expression
        self.recurrent_event = RecurringEvent()
        self.parsed_rrule = self.recurrent_event.parse(cron)
        if not self.recurrent_event.is_recurring:
            raise ValueError(f"Invalid cron expression '{cron}'. Please fix the syntax in the configuration file.")

        assert isinstance(self.parsed_rrule, str)

        # instantiate each task associated with this schedule
        self.task_list = []
        j = 0
        for t in tasks_dict:
            self.task_list.append(
                Task(t["task"],
                     t["params"],
                     t["topic"],
                     t["formatter"],
                    t["ha_discovery"],
                    mqtt_topic_prefix,
                     self.schedule_rule_idx, j))
            j += 1

        # summary of the whole instance:
        logging.info(f"SCHEDULE#{schedule_rule_idx}: Periodicity: {cron}; Max interval: {self.get_max_interval_sec()}sec; Contains {len(tasks_dict)} tasks: {tasks_dict}")

    def get_next_occurrence(self) -> float:
        '''
        Compute how many secs in the future this schedule needs to run and returns it
        '''
        # NOTE: we need reparse rule each time (see #10)
        now = datetime.datetime.now()
        return (rrulestr(self.parsed_rrule).after(now) - now).total_seconds()

    def get_max_interval_sec(self) -> int:
        '''
        This function attempts to find the max possible interval between 2 occurrences of the
        "cron expression" provided to the ctor.
        Returns -1 if fails to find the max possible interval.
        '''
        if self.recurrent_event.interval is None or self.recurrent_event.freq is None:
            return -1
        frequency_multiplier_sec = {
            'secondly':  1,
            'minutely': 60,
            'hourly': 60 * 60,
            'daily': 24 * 60 * 60,
            'weekly': 7 * 24 * 60 * 60,
            'monthly': 31 * 7 * 24 * 60 * 60,  # take the worst case
            'yearly': 365 * 31 * 7 * 24 * 60 * 60,  # take the worst case
        }
        if self.recurrent_event.freq not in frequency_multiplier_sec:
            return -1
        return int(self.recurrent_event.interval) * frequency_multiplier_sec[self.recurrent_event.freq]

    def get_tasks(self) -> List[Task]:
        return self.task_list
