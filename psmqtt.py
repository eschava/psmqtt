#!/usr/bin/env python
#
# 1. Read configuration pointed to by PSMQTTCONFIG env var, or use `psmqtt.conf`
#    by default.
# 2. Extract from config file settings, e.g. mqtt broker and schedule.
# 2. Execute schedule...
# 3. Perform tasks from the schedule, which involves reading sensors and sending
#    values to the broker
#
from datetime import datetime
from dateutil.rrule import rrulestr  # pip install python-dateutil
import os
#import sys
import sched
import socket
import logging
import sys
from threading import Thread
import time
from typing import Any, Dict, List, Union

from src.config import load_config

def run_tasks(tasks: Union[str, Dict[str, str],
        List[Union[Dict[str, str], str]]]) -> None:
    '''
    tasks come from conf file, e.g.:
        ["cpu_percent", "virtual_memory/percent"]
        or
        "disk_usage/percent/|"
        or
        {"boot_time/{{x|uptime}}": "uptime" }
    '''
    # delayed import to enable PYTHONPATH adjustment
    from src.task import run_task

    logging.debug("run_tasks(%s)", tasks)

    if isinstance(tasks, dict):
        for k in tasks:
            run_task(k, tasks[k])
    elif isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict):
                for k,t in task.items():
                    run_task(k, t)
            else:
                run_task(task, task)
    else:
        run_task(tasks, tasks)
    return

class TimerThread(Thread):

    def __init__(self, scheduler:sched.scheduler):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        return

    def run(self) -> None:
        self.scheduler.run()
        return

def on_timer(s:sched.scheduler, dt: str, tasks: Any) -> None:
    logging.debug("on_timer(%s, %s, %s)", s, dt, tasks)

    run_tasks(tasks)
    # add next timer task
    now = datetime.now()
    # need reparse rule (see #10)
    delay = (rrulestr(dt).after(now) - now).total_seconds()
    s.enter(delay, 1, on_timer, (s, dt, tasks))
    return

def run() -> None:
    '''
    Main loop
    '''
    #
    # read initial config files - this may exit(2)
    #
    cf = load_config()

    # delayed import to enable PYTHONPATH adjustment
    from recurrent import RecurringEvent  # pip install recurrent
    from src.task import MqttClient
    #
    # create MqttClient
    #
    mqttc = MqttClient(
        cf.config["mqtt"]["clientid"],
        cf.config["mqtt"]["clean_session"],
        cf.config["mqtt"]["publish_topic_prefix"],
        cf.config["mqtt"]["request_topic"],
        cf.config["mqtt"]["qos"],
        cf.config["mqtt"]["retain"])
    #
    # connect MqttClient to broker
    #
    mqttc.connect(
        cf.config["mqtt"]["broker"]["host"],
        cf.config["mqtt"]["broker"]["port"],
        cf.config["mqtt"]["broker"]["username"],
        cf.config["mqtt"]["broker"]["password"])
    #
    # parse schedule
    #
    schedule = cf.get('schedule', {})
    assert isinstance(schedule, dict)
    if not schedule:
        logging.error("No schedule to execute, exiting")
        return

    s = sched.scheduler(time.time, time.sleep)
    now = datetime.now()
    for t, tasks in schedule.items():
        logging.debug("Periodicity: '%s'", t)
        logging.debug("Tasks: '%s'", tasks)
        r = RecurringEvent()
        dt = r.parse(t)
        if not r.is_recurring:
            logging.error(t + " is not recurring time. Skipping")
            continue

        delay = (rrulestr(dt).after(now) - now).total_seconds()
        s.enter(delay, 1, on_timer, (s, dt, tasks))

    TimerThread(s).start()
    while True:
        try:
            mqttc.mqttc.loop_forever()

        except socket.error:
            logging.debug("socket.error caught, sleeping for 5 sec...")
            time.sleep(5)

        except KeyboardInterrupt:
            logging.debug("KeyboardInterrupt caught, exiting")
            break
    return


if __name__ == '__main__':
    run()
