#!/usr/bin/env python
#
# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.
#
# This is the entrypoint of the project:
# 1. Reads configuration pointed to by PSMQTTCONFIG env var, or use `psmqtt.conf`
#    by default.
# 2. Extracts from config file settings, e.g. mqtt broker and schedule.
# 2. Executes schedule...
# 3. Performs tasks from the schedule, which involves reading sensors and sending
#    values to the broker
#

from datetime import datetime
from dateutil.rrule import rrulestr  # pip install python-dateutil
import argparse
import os
import sched
import socket
import logging
import sys
from threading import Thread
import time
from typing import Any, List

from src.config import Config
from src.config import load_config
from src.mqtt_client import MqttClient

# global counter of tasks executed so far
num_executed_tasks = 0

class TimerThread(Thread):

    def __init__(self, scheduler:sched.scheduler):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        return

    def run(self) -> None:
        self.scheduler.run()
        return

def on_timer(s: sched.scheduler, parsed_rrule: str, scheduleIdx: int, tasks: List[Any], cfg: Config, mqttc: MqttClient) -> None:
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
    global num_executed_tasks

    logging.debug("on_timer(%s, %s, %d, %s)", s, parsed_rrule, scheduleIdx, tasks)

    # delayed import to enable PYTHONPATH adjustment
    from src.task import run_task

    # support for the "exit_after" feature
    exit_after = cfg.config["options"]["exit_after_num_tasks"]
    reschedule = True

    assert isinstance(tasks, list)
    taskIdx = 0
    for task in tasks:
        assert isinstance(task, dict)
        task_friendly_name = f"schedule{scheduleIdx}.task{taskIdx}.{task['task']}"

        # main entrypoint for TASK execution:
        run_task(mqttc, task_friendly_name, task)

        taskIdx += 1
        num_executed_tasks += 1
        if exit_after > 0 and num_executed_tasks >= exit_after:
            reschedule = False
            break

    # need reparse rule (see #10)
    now = datetime.now()
    delay = (rrulestr(parsed_rrule).after(now) - now).total_seconds()

    # add next timer task
    if reschedule:
        s.enter(delay, 1, on_timer, (s, parsed_rrule, scheduleIdx, tasks, cfg, mqttc))
    return

def on_log_timer(s: sched.scheduler, log_period_sec: int, mqttc: MqttClient) -> None:
    '''
    Periodically prints the status of psmqtt
    '''
    from src.task import num_errors

    # publish also on MQTT
    status_topic = mqttc.topic_prefix + "psmqtt_status"
    mqttc.mqttc.publish(status_topic + "/num_errors", num_errors)
    logging.info(f"psmqtt status: {num_errors} errors while capturing sensor data; published status into on topic {status_topic}")

    # add next timer task
    s.enter(log_period_sec, 1, on_log_timer, (s, log_period_sec, mqttc))
    return

def read_version_file(filename='VERSION') -> str:
    """
    Reads the content of a version file.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    version_file_path = os.path.join(current_dir, filename)
    try:
        # Open the version file and read its content
        with open(version_file_path, 'r') as f:
            version_content = f.read()
            return version_content

    except FileNotFoundError:
        logging.error(f"Version file '{filename}' not found in the current directory.")
        return "N/A"

def run() -> int:
    '''
    Main loop
    '''

    # CLI interface

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description='Publish psutil/pySMART counters to an MQTT broker according to scheduling rules',
        epilog='See documentation at https://github.com/eschava/psmqtt for configuration examples')
    parser.add_argument(
        "-V",
        "--version",
        help="Print version and exit",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    if args.version:
        print(f"Version: {read_version_file()}")
        sys.exit(0)

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
        s.enter(delay_sec, 1, on_timer, (s, parsed_rrule, i, sch["tasks"], cf, mqttc))
        i += 1

    # add periodic log
    try:
        log_period_sec = int(cf.config["logging"]["report_status_period_sec"])
    except ValueError:
        logging.error("Invalid expression for logging.report_status_every. Please fix the syntax in the configuration file. Aborting.")
        return 5

    if log_period_sec > 0:
        s.enter(log_period_sec, 1, on_log_timer, (s, log_period_sec, mqttc))
    #else: logging of the status has been disabled

    # start a secondary thread running the scheduler
    TimerThread(s).start()

    # block the main thread on the MQTT client loop
    exit_after = cf.config["options"]["exit_after_num_tasks"]

    global num_executed_tasks
    keep_running = True
    while keep_running:
        try:
            mqttc.mqttc.loop_start()
            while True:
                if exit_after > 0 and num_executed_tasks >= exit_after:
                    logging.warning("exiting after executing %d tasks as requested in the configuration file", num_executed_tasks)
                    keep_running = False
                    break
                time.sleep(0.5)

        except socket.error:
            logging.error("socket.error caught, sleeping for 5 sec...")
            time.sleep(5)

        except KeyboardInterrupt:
            logging.warning("KeyboardInterrupt caught, exiting")
            break

    # gracefully stop the event loop of MQTT client
    mqttc.mqttc.loop_stop()

    return 0


if __name__ == '__main__':
    sys.exit(run())
