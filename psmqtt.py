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
from dateutil.rrule import rrulestr
import argparse
import os
import sched
import socket
import logging
import sys
from threading import Thread
import time
from typing import List
from recurrent import RecurringEvent

from src.config import Config
from src.mqtt_client import MqttClient
from src.task import Task

class SchedulerThread(Thread):

    def __init__(self, scheduler:sched.scheduler):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        self.keep_running = True
        return

    def start(self) -> None:
        logging.info("Starting the psmqtt scheduler")
        super().start()

    def run(self) -> None:
        while self.keep_running:
            delay_sec = self.scheduler.run(blocking=False)

            time_waited = 0
            while delay_sec > 0 and time_waited < delay_sec:
                time.sleep(0.5)
                time_waited += 0.5
                if not self.keep_running:
                    break
        return

    def stop(self) -> None:
        self.keep_running = False
        logging.info("Stopping the psmqtt scheduler")
        super().join()
        logging.info("Stopped the psmqtt scheduler")

class PsmqttApp:

    def __init__(self) -> None:
        # the app is composed by 4 major components:
        self.config = None  # instance of Config
        self.mqtt_client = None  # instance of MqttClient
        self.scheduler = None  # instance of sched.scheduler
        self.scheduler_thread = None  # instance of SchedulerThread

        self.last_logged_status = (None, None, None)

    @staticmethod
    def on_task_timer(app: 'PsmqttApp', parsed_rrule: str, tasks: List[Task]) -> None:
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

        logging.debug("PsmqttApp.on_task_timer(%s, %d tasks)", parsed_rrule, len(tasks))

        # support for the "exit_after" feature
        exit_after = app.config.config["options"]["exit_after_num_tasks"]
        reschedule = True

        for task in tasks:
            # main entrypoint for TASK execution:
            task.run_task(app.mqtt_client)

            if exit_after > 0 and Task.num_total_tasks() >= exit_after:
                reschedule = False
                break

        # need reparse rule (see #10)
        now = datetime.now()
        delay = (rrulestr(parsed_rrule).after(now) - now).total_seconds()

        # add next timer task
        if reschedule:
            app.scheduler.enter(delay, 1, PsmqttApp.on_task_timer, (app, parsed_rrule, tasks))
        return

    @staticmethod
    def log_status() -> None:
        logging.info(f"psmqtt status: {Task.num_success} successful tasks; {Task.num_errors} failed tasks; {MqttClient.num_disconnects} MQTT disconnections; {MqttClient.num_published_successful}/{MqttClient.num_published_total} successful/total MQTT messages published")

    @staticmethod
    def on_log_timer(app: 'PsmqttApp') -> None:
        '''
        Periodically prints the status of psmqtt
        '''

        new_status = (Task.num_errors, Task.num_success, MqttClient.num_disconnects)
        if new_status != app.last_logged_status:
            # publish status on MQTT
            status_topic = app.status_topic
            app.mqtt_client.publish(status_topic + "/num_tasks_errors", Task.num_errors)
            app.mqtt_client.publish(status_topic + "/num_tasks_success", Task.num_success)
            app.mqtt_client.publish(status_topic + "/num_mqtt_disconnects", MqttClient.num_disconnects)

            # publish status on log
            PsmqttApp.log_status()

            app.last_logged_status = new_status

        # add next timer task
        log_period_sec = int(app.config.config["logging"]["report_status_period_sec"])
        app.scheduler.enter(log_period_sec, 1, PsmqttApp.on_log_timer, tuple([app]))
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

    def setup(self) -> int:
        '''
        Application setup
        '''

        # CLI interface
        parser = argparse.ArgumentParser(
            prog=os.path.basename(__file__),
            description='Publish psutil/pySMART counters to an MQTT broker according to scheduling rules',
            epilog='See documentation at https://github.com/eschava/psmqtt for configuration examples. All the configuration options are read from the psmqtt.yaml file or the path pointed by the \'PSMQTTCONFIG\' environment variable.')
        parser.add_argument(
            "-V",
            "--version",
            help="Print version and exit",
            action="store_true",
            default=False,
        )

        if "COLUMNS" not in os.environ:
            os.environ["COLUMNS"] = "120"  # avoid too many line wraps
        args = parser.parse_args()
        if args.version:
            print(f"Version: {self.read_version_file()}")
            return 0

        # fix for error 'No handlers could be found for logger "recurrent"'
        recurrent_logger = logging.getLogger('recurrent')
        if len(recurrent_logger.handlers) == 0:
            recurrent_logger.addHandler(logging.NullHandler())

        # start with DEBUG logging level till we load the config file:
        logging.basicConfig(level=logging.DEBUG)

        # read config file:
        self.config = Config()
        try:
            self.config.load()
        except Exception as e:
            logging.error(f"Cannot load configuration: {e}. Aborting.")
            sys.exit(2)

        self.config.apply_logging_config()

        #
        # create MqttClient
        #
        self.mqtt_client = MqttClient(
            self.config.config["mqtt"]["clientid"],
            self.config.config["mqtt"]["clean_session"],
            self.config.config["mqtt"]["publish_topic_prefix"],
            self.config.config["mqtt"]["request_topic"],
            self.config.config["mqtt"]["qos"],
            self.config.config["mqtt"]["retain"],
            self.config.config["mqtt"]["reconnect_period_sec"])

        #
        # parse schedule
        #
        schedule = self.config.config["schedule"]
        assert isinstance(schedule, list)
        if not schedule:
            logging.error("No schedule to execute, exiting")
            return 3

        self.scheduler = sched.scheduler(time.time, time.sleep)
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

            # instantiate each task associated with this schedule
            task_list = []
            j = 0
            for t in sch["tasks"]:
                task_list.append(Task(t["task"], t["params"], t["topic"], t["formatter"], i, j))
                j += 1

            # include this in our scheduler:
            self.scheduler.enter(delay_sec, 1, PsmqttApp.on_task_timer, (self, parsed_rrule, task_list))
            i += 1

        # add periodic log
        try:
            log_period_sec = int(self.config.config["logging"]["report_status_period_sec"])
        except ValueError:
            logging.error("Invalid expression for logging.report_status_every. Please fix the syntax in the configuration file. Aborting.")
            return 5

        if log_period_sec > 0:
            self.status_topic = app.mqtt_client.topic_prefix + "psmqtt_status"
            logging.info(f"PSMQTT status will be published on topic {self.status_topic} every {log_period_sec}sec")

            self.scheduler.enter(log_period_sec, 1, PsmqttApp.on_log_timer, tuple([self]))
        #else: logging of the status has been disabled

        # store the scheduler into its own thread:
        self.scheduler_thread = SchedulerThread(self.scheduler)

        # success
        return 0

    def run(self) -> int:
        # start a secondary thread running the scheduler
        self.scheduler_thread.start()

        # estabilish a connection to the MQTT broker
        try:
            self.mqtt_client.connect(
                self.config.config["mqtt"]["broker"]["host"],
                self.config.config["mqtt"]["broker"]["port"],
                self.config.config["mqtt"]["broker"]["username"],
                self.config.config["mqtt"]["broker"]["password"])
        except ConnectionRefusedError as e:
            logging.error(f"Cannot connect to MQTT broker: {e}. Retrying shortly.")
            # IMPORTANT: there's no need to abort here -- paho MQTT client loop_start() will keep trying to reconnect
            # so, if and when the MQTT broker will be available, the connection will be established

        # block the main thread on the MQTT client loop
        keep_running = True
        exit_after = self.config.config["options"]["exit_after_num_tasks"]
        while keep_running:
            try:
                self.mqtt_client.loop_start()
                while True:
                    if exit_after > 0 and Task.num_total_tasks() >= exit_after:
                        logging.warning("exiting after executing %d tasks as requested in the configuration file", Task.num_total_tasks())
                        keep_running = False
                        break

                    # FIXME: add check here for "HA started" flag -- if true send all discovery messages

                    time.sleep(0.5)

            except socket.error:
                logging.error("socket.error caught, sleeping for 5 sec...")
                time.sleep(self.config.config["mqtt"]["reconnect_period_sec"])

            except KeyboardInterrupt:
                logging.warning("KeyboardInterrupt caught, exiting")
                break

        # gracefully stop the event loop of MQTT client
        self.mqtt_client.loop_stop()

        # stop the scheduler thread as well
        self.scheduler_thread.stop()

        # log status one last time
        PsmqttApp.log_status()

        return 0


if __name__ == '__main__':
    app = PsmqttApp()
    ret = app.setup()
    if ret != 0:
        sys.exit(ret)
    sys.exit(app.run())
