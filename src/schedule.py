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
    " "tasks" which is a list of Task classes
    '''

    def __init__(self,
            cron:str,
            tasks_dict:Dict[str,Any],
            mqtt_topic_prefix:str,
            schedule_rule_idx:int) -> None:
        self.cron_expr = cron
        self.schedule_rule_idx = schedule_rule_idx

        logging.debug(f"SCHEDULE#{schedule_rule_idx}: Periodicity: {cron}")
        logging.debug(f"SCHEDULE#{schedule_rule_idx}: {len(tasks_dict)} tasks: {tasks_dict}")

        # parse the cron expression
        r = RecurringEvent()
        self.parsed_rrule = r.parse(cron)
        if not r.is_recurring:
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

    def get_next_occurrence(self) -> float:
        # compute how many secs in the future this needs to run
        # NOTE: we need reparse rule each time (see #10)
        now = datetime.datetime.now()
        return (rrulestr(self.parsed_rrule).after(now) - now).total_seconds()

    def get_tasks(self) -> List[Task]:
        return self.task_list
