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
import sched
import socket
import logging
import sys
from threading import Thread
import time
from typing import Any, List

from src.config import load_config

class TimerThread(Thread):

    def __init__(self, scheduler:sched.scheduler):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        return

    def run(self) -> None:
        self.scheduler.run()
        return

def on_timer(s: sched.scheduler, parsed_rrule: str, scheduleIdx: int, tasks: List[Any]) -> None:
    '''
    Takes a list of tasks to be run immediately.
    The list must contain dictionary items, each having "task", "params", "topic" and "formatter" fields.
    E.g.:
        [
          { "task: "cpu_percent",
            "params": [],
            "topic": None,
            "formatter": None },
          { "task": "virtual_memory",
            "params": [ "percent" ],
            "topic": "foobar",
            "formatter": None }
        ]
    '''

    logging.debug("on_timer(%s, %s, %d, %s)", s, parsed_rrule, scheduleIdx, tasks)

    # delayed import to enable PYTHONPATH adjustment
    from src.task import run_task

    assert isinstance(tasks, list)
    taskIdx = 0
    for task in tasks:
        assert isinstance(task, dict)
        run_task(f"schedule{scheduleIdx}.task{taskIdx}.{task['task']}", task)
        taskIdx += 1

    # need reparse rule (see #10)
    now = datetime.now()
    delay = (rrulestr(parsed_rrule).after(now) - now).total_seconds()

    # add next timer task
    s.enter(delay, 1, on_timer, (s, parsed_rrule, scheduleIdx, tasks))
    return

def run() -> int:
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
    try:
        mqttc.connect(
            cf.config["mqtt"]["broker"]["host"],
            cf.config["mqtt"]["broker"]["port"],
            cf.config["mqtt"]["broker"]["username"],
            cf.config["mqtt"]["broker"]["password"])
    except ConnectionRefusedError as e:
        logging.error(f"Cannot connect to MQTT broker: {e}. Aborting.")
        # FIXME: we're currently bailing out here -- instead we should keep retrying the connection!
        return 2

    #
    # parse schedule
    #
    schedule = cf.config["schedule"]
    assert isinstance(schedule, list)
    if not schedule:
        logging.error("No schedule to execute, exiting")
        return 3

    s = sched.scheduler(time.time, time.sleep)
    now = datetime.now()
    i = 0
    for sch in schedule:
        logging.debug(f"SCHEDULE#{i}: Periodicity: {sch['cron']}")
        logging.debug(f"SCHEDULE#{i}: {len(sch['tasks'])} tasks: {sch['tasks']}")

        # parse the cron expression
        r = RecurringEvent()
        parsed_rrule = r.parse(sch["cron"])
        if not r.is_recurring:
            logging.error(f"Invalid cron expression '{sch["cron"]}'. Please fix the syntax in the configuration file. Aborting.")
            return 4

        # compute how many secs in the future this needs to run
        assert isinstance(parsed_rrule, str)
        delay_sec = (rrulestr(parsed_rrule).after(now) - now).total_seconds()

        # include this in our scheduler:
        s.enter(delay_sec, 1, on_timer, (s, parsed_rrule, i, sch["tasks"]))
        i += 1

    # start a secondary thread running the scheduler
    TimerThread(s).start()

    # block the main thread on the MQTT client loop
    while True:
        try:
            mqttc.loop_forever()

        except socket.error:
            logging.debug("socket.error caught, sleeping for 5 sec...")
            time.sleep(5)

        except KeyboardInterrupt:
            logging.debug("KeyboardInterrupt caught, exiting")
            break
    return 0


if __name__ == '__main__':
    sys.exit(run())
