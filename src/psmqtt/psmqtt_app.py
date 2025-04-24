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

import argparse
import os
import sched
import socket
import logging
import sys
import platform
import time

from .config import Config
from .mqtt_client import MqttClient
from .task import Task
from .schedule import Schedule
from .utils import get_mac_address

class PsmqttApp:

    def __init__(self) -> None:
        # the app is composed by 4 major components:
        self.config = None  # instance of Config
        self.mqtt_client = None  # instance of MqttClient
        self.scheduler = None  # instance of sched.scheduler

        self.last_logged_status = (None, None, None)
        self.schedule_list = []  # list of Schedule instances

    @staticmethod
    def on_schedule_timer(app: 'PsmqttApp', schedule: Schedule) -> None:
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

        task_list = schedule.get_tasks()
        logging.debug("PsmqttApp.on_schedule_timer(%s, %d tasks)", schedule.parsed_rrule, len(task_list))

        # support for the "exit_after" feature
        exit_after = app.config.config["options"]["exit_after_num_tasks"]
        reschedule = True

        for task in task_list:
            # main entrypoint for TASK execution:
            task.run_task(app.mqtt_client)

            if exit_after > 0 and Task.num_total_tasks_executed() >= exit_after:
                reschedule = False
                break

        # add next timer task
        if reschedule:
            app.scheduler.enter(schedule.get_next_occurrence(), 1, PsmqttApp.on_schedule_timer, (app, schedule))
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
            status_topic = app.mqtt_client.get_psmqtt_status_topic()
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

    @staticmethod
    def read_version_file(filename='VERSION') -> str:
        '''
        Reads the content of a version file.
        '''

        from _psmqtt_version import version as __version__
        return __version__

        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # version_file_path = os.path.join(current_dir, filename)
        # try:
        #     # Open the version file and read its content
        #     with open(version_file_path, 'r') as f:
        #         version_content = f.read()
        #         return version_content

        # except FileNotFoundError:
        #     logging.error(f"Version file '{filename}' not found in the current directory.")
        #     return "N/A"

    def publish_ha_discovery_messages(self) -> int:
        '''
        Publish MQTT discovery messages for HomeAssistant, from all tasks that have been decorated
        with the "ha_discovery" metadata.
        Returns the number of MQTT discovery messages published.
        '''

        ha_discovery_topic = self.config.config["mqtt"]["ha_discovery"]["topic"]
        ha_device_name = self.config.config["mqtt"]["ha_discovery"]["device_name"]
        psmqtt_ver = PsmqttApp.read_version_file()

        device_dict = {
            "ids": ha_device_name,
            "name": ha_device_name,
            "manufacturer": "eschava/psmqtt",
            "sw_version": platform.system(),  # the OS name like 'Linux', 'Darwin', 'Java', 'Windows'
            "hw_version": platform.machine(),  # this is actually something like "x86_64"
            "model": platform.platform(terse=True),  # on Linux this is a condensed summary of "uname -a"
            "configuration_url": "https://github.com/eschava/psmqtt",
            "connections": [["mac", get_mac_address()]],
        }
        num_msgs = 0
        for sch in self.schedule_list:

            expire_time_sec = sch.get_max_interval_sec()
            if expire_time_sec == -1:
                # failed to compute... proceed without "expire_after"
                expire_time_sec = None
            else:
                # expire the sensor in HomeAssistant after a duration equal to 1.5 the usual interval;
                # also apply a lower bound of 10sec; this is a reasonable way to avoid that a single MQTT
                # message not delivered turns the entity into "not available" inside HomeAssistant;
                # on the other hand, if psmqtt goes down or the MQTT broker goes down, the entity at some
                # point will be unavailable so the user will know that something is wrong.
                expire_time_sec = max(10,expire_time_sec * 1.5)

            for t in sch.get_tasks():
                assert isinstance(t, Task)
                payload = t.get_ha_discovery_payload(ha_device_name, psmqtt_ver, device_dict, expire_time_sec)
                if payload is not None:
                    topic = t.get_ha_discovery_topic(ha_discovery_topic, ha_device_name)
                    logging.info(f"Publishing an MQTT discovery messages on topic '{topic}'")
                    self.mqtt_client.publish(topic, payload)
                    num_msgs += 1
        logging.info(f"Published a total of {num_msgs} MQTT discovery messages under the topic prefix '{ha_discovery_topic}' for the device '{ha_device_name}'. The HomeAssistant MQTT integration should now be showing {num_msgs} sensors for the device '{ha_device_name}'.")
        return num_msgs

    def run_all_tasks(self) -> int:
        '''
        Run all tasks immediately, disregarding the schedule.
        Returns the number of tasks that were run.
        '''
        num_tasks = 0
        for sch in self.schedule_list:
            for task in sch.get_tasks():
                task.run_task(self.mqtt_client)
                num_tasks += 1

        logging.info(f"Executed {num_tasks} tasks.")
        return num_tasks

    def setup(self) -> int:
        '''
        Application setup
        '''

        # CLI interface
        parser = argparse.ArgumentParser(
            prog="psmqtt",
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
            print(f"Version: {PsmqttApp.read_version_file()}")
            return -1

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
        ha_status_topic = ""
        if self.config.config["mqtt"]["ha_discovery"]["enabled"]:
            ha_status_topic = self.config.config["mqtt"]["ha_discovery"]["topic"] + "/status"
        self.mqtt_client = MqttClient(
            self.config.config["mqtt"]["clientid"],
            self.config.config["mqtt"]["clean_session"],
            self.config.config["mqtt"]["publish_topic_prefix"],
            self.config.config["mqtt"]["request_topic"],
            self.config.config["mqtt"]["qos"],
            self.config.config["mqtt"]["retain"],
            self.config.config["mqtt"]["reconnect_period_sec"],
            ha_status_topic)

        #
        # parse schedule
        #
        schedule = self.config.config["schedule"]
        assert isinstance(schedule, list)
        if not schedule:
            logging.error("No schedule to execute, exiting")
            return 3

        self.scheduler = sched.scheduler(time.time, time.sleep)
        i = 0
        for sch in schedule:
            try:
                new_schedule = Schedule(sch['cron'],
                                        sch['tasks'],
                                        self.config.config["mqtt"]["publish_topic_prefix"],
                                        i)
            except ValueError as e:
                logging.error(f"Cannot parse schedule #{i}: {e}. Aborting.")
                return 4

            # upon startup psmqtt will immediately run all scheduling rules, just
            # scattered 100ms one from each other:
            first_time_delay_sec = i + 0.1

            # include this in our scheduler:
            self.scheduler.enter(first_time_delay_sec, 1, PsmqttApp.on_schedule_timer, (self, new_schedule))
            i += 1

            # store the Schedule also locally:
            self.schedule_list.append(new_schedule)

        # add periodic log
        try:
            log_period_sec = int(self.config.config["logging"]["report_status_period_sec"])
        except ValueError:
            logging.error("Invalid expression for logging.report_status_every. Please fix the syntax in the configuration file. Aborting.")
            return 5

        if log_period_sec > 0:
            logging.info(f"PSMQTT status will be published on topic {self.mqtt_client.get_psmqtt_status_topic()} every {log_period_sec}sec")
            self.scheduler.enter(log_period_sec, 1, PsmqttApp.on_log_timer, tuple([self]))
        #else: logging of the status has been disabled

        # success
        return 0

    def _core_loop(self) -> None:
        '''
        Runs the logic of PSMQTT application.
        Every "sleep quantum" the app wakes up and checks whether
        * it's time to run a scheduled task
        * MQTT dicovery messages were requested
        * etc

        This function exits only in case: an exception is thrown or the total number
        of tasks executed reaches the limit set in the configuration file.
        '''
        sleep_quantum_sec = 0.5
        exit_after = self.config.config["options"]["exit_after_num_tasks"]

        while self.keep_running:
            # execute all tasks waiting in the queue
            delay_for_next_task_sec = self.scheduler.run(blocking=False)

            # execute a sliced wait, so we reuse this thread to check for other occurrences
            # (instead of resorting to a multithread Python app)
            time_waited_sec = 0
            while delay_for_next_task_sec > 0 and time_waited_sec < delay_for_next_task_sec:
                time.sleep(sleep_quantum_sec)
                time_waited_sec += sleep_quantum_sec

                if exit_after > 0 and Task.num_total_tasks_executed() >= exit_after:
                    logging.warning("exiting after executing %d tasks as requested in the configuration file", Task.num_total_tasks_executed())
                    self.keep_running = False
                    break
                if self.config.config["mqtt"]["ha_discovery"]["enabled"]:
                    curr_conn_id = self.mqtt_client.get_connection_id()
                    if curr_conn_id != self.last_ha_discovery_messages_connection_id:
                        # looks like a new MQTT connection to the broker has (recently) been estabilished;
                        # send out MQTT discovery messages
                        logging.warning(f"New connection to the MQTT broker detected (id={curr_conn_id}), sending out MQTT discovery messages...")
                        self.publish_ha_discovery_messages()
                        self.last_ha_discovery_messages_connection_id = curr_conn_id

                    if self.mqtt_client.get_and_reset_ha_discovery_messages_requested_flag():
                        # MQTT discovery messages have been requested...
                        logging.warning("Detected notification that Home Assistant just (re)started; phase 1: publishing MQTT discovery messages...")
                        self.publish_ha_discovery_messages()

                        # see https://github.com/eschava/psmqtt/issues/79
                        logging.warning("Detected notification that Home Assistant just (re)started; phase 2: publishing all sensor values (regardless of their schedule)...")
                        self.run_all_tasks()

    def run(self) -> int:
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

        self.last_ha_discovery_messages_connection_id = MqttClient.CONN_ID_INVALID

        # block the main thread on the MQTT client loop
        self.keep_running = True
        while self.keep_running:
            try:
                # restart the MQTT client secondary thread in case it was never started or failed for some reason
                self.mqtt_client.loop_start()

                # run till an exception is thrown:
                self._core_loop()

            # try to recover from exceptions:
            except socket.error:
                logging.error("socket.error caught, sleeping for 5 sec...")
                time.sleep(self.config.config["mqtt"]["reconnect_period_sec"])
            except KeyboardInterrupt:
                logging.warning("KeyboardInterrupt caught, exiting")
                break

        # gracefully stop the event loop of MQTT client
        self.mqtt_client.loop_stop()

        # log status one last time
        PsmqttApp.log_status()

        logging.warning("Exiting gracefully")

        return 0

def main() -> None:
    app = PsmqttApp()
    ret = app.setup()
    if ret > 0:
        sys.exit(ret)
    if ret == -1: # version has been requested (and already printed)
        sys.exit(0)
    sys.exit(app.run())


if __name__ == '__main__':
    main()
