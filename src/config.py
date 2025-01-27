# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import os
import logging
import logging.config
import sys
import yaml
import yamale
from yamale import YamaleError

import socket
from .handlers import get_supported_handlers

class Config:
    '''
    Config class validates and reads the psmqtt YAML configuration file and reports to the
    rest of the application the data as a dictionary.
    '''
    def __init__(self):
        self.config = None
        self.schema = None

    def load(self, filename: str, schema_filename: str):
        '''
        filename is a fully qualified path to the YAML config file.
        The YAML file is validated against the schema file provided as argument,
        and optional configuration parameters are populated with their default values.
        '''

        try:
            tuple_list = yamale.make_data(filename)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file '{filename}': {e}")
        if len(tuple_list) != 1:
            raise ValueError(f"Error parsing YAML file '{filename}': expected a single document, got {len(tuple_list)}")

        try:
            schema = yamale.make_schema(schema_filename)  # Assuming self.schema_path holds the path to the YAML schema
            yamale.validate(schema, tuple_list)
        except YamaleError as e:
            raise ValueError(f"Configuration file '{filename}' does not conform to schema: {e}")

        # extract just the validated dictionary and store it in self.config
        the_tuple = tuple_list[0]
        if len(the_tuple) != 2:
            raise ValueError(f"Error parsing YAML file '{filename}': invalid format from yamala library")
        self.config = the_tuple[0]

        # add default values for optional configuration parameters, if they're missing:
        self._fill_defaults_logging()
        self._fill_defaults_mqtt()
        self._fill_defaults_schedule()
        logging.info(f"Configuration file '{filename}' successfully loaded and validated against schema. It contains {len(self.config['schedule'])} validated schedules.")
        return

    def _fill_defaults_logging(self):
        # logging
        if "logging" not in self.config:
            self.config["logging"] = {"level": "ERROR", "report_status_period_sec": 3600}
        if "level" not in self.config["logging"]:
            self.config["logging"]["level"] = "ERROR"
        if "report_status_period_sec" not in self.config["logging"]:
            self.config["logging"]["report_status_period_sec"] = 3600

    def _fill_defaults_mqtt(self):
        # mqtt.broker object
        if 'port' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["port"] = 1883
        if 'username' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["username"] = None
        if 'password' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["password"] = None

        # other optional "mqtt" keys
        if "retain" not in self.config["mqtt"]:
            self.config["mqtt"]["retain"] = False
        if "clean_session" not in self.config["mqtt"]:
            self.config["mqtt"]["clean_session"] = False
        if "clientid" not in self.config["mqtt"]:
            self.config["mqtt"]["clientid"] = 'psmqtt-%s' % os.getpid()
        if "qos" not in self.config["mqtt"]:
            self.config["mqtt"]["qos"] = 0
        if "publish_topic_prefix" not in self.config["mqtt"]:
            hn = socket.gethostname()
            self.config["mqtt"]["publish_topic_prefix"] = f"psmqtt/{hn}/"
        else:
            # make sure the publish_topic_prefix ALWAYS ends with a slash,
            # to ensure separation from the topic that will be appended to it
            if self.config["mqtt"]["publish_topic_prefix"][-1] != '/':
                self.config["mqtt"]["publish_topic_prefix"] += '/'

        if "request_topic" not in self.config["mqtt"]:
            self.config["mqtt"]["request_topic"] = 'request'

    def _fill_defaults_schedule(self):
        # provide defaults for the "schedule" key
        if not isinstance(self.config["schedule"], list):
            raise ValueError("Invalid 'schedule' key in configuration file: must be a list")

        available_handlers_names = get_supported_handlers()

        validated_schedule = []
        for s in self.config["schedule"]:
            # "cron" & "tasks" fields presence is already ensured by the JSON schema
            validated_tasks = []
            for t in s["tasks"]:
                # more validation on "task" name
                if t["task"] not in available_handlers_names:
                    raise ValueError(f"Invalid task '{t['task']}' in configuration file. Supported tasks are: {available_handlers_names}")
                # provide defaults for "params" and "formatter" fields
                if "params" not in t:
                    t["params"] = []
                if "formatter" not in t:
                    t["formatter"] = None
                if "topic" not in t:
                    t["topic"] = None
                validated_tasks.append(t)

            validated_schedule.append({"cron": s["cron"], "tasks": validated_tasks})

        self.config["schedule"] = validated_schedule


def load_config() -> Config:
    '''
    Load logging and app config, returns the latter.
    '''

    dirname = os.path.dirname(os.path.abspath(__file__))
    dirname = os.path.abspath(os.path.join(dirname, '..'))

    logging_conf_path = os.path.join(dirname, 'logging.conf')
    psmqtt_conf_path = os.getenv(
        'PSMQTTCONFIG', os.path.join(dirname, 'psmqtt.yaml'))
    psmqtt_conf_schema_path = os.getenv(
        'PSMQTTCONFIGSCHEMA', os.path.join(dirname, 'schema/psmqtt.schema.yaml'))

    try:
        # read initial config files
        logging.debug("Loading logging config '%s'", logging_conf_path)
        logging.config.fileConfig(logging_conf_path)

        # fix for error 'No handlers could be found for logger "recurrent"'
        reccurrent_logger = logging.getLogger('recurrent')
        if len(reccurrent_logger.handlers) == 0:
            reccurrent_logger.addHandler(logging.NullHandler())

        logging.debug("Loading app config '%s' and its schema '%s'", psmqtt_conf_path, psmqtt_conf_schema_path)

        # Config.load() will raise exceptions eventually:
        cfg = Config()
        cfg.load(psmqtt_conf_path, psmqtt_conf_schema_path)

        return cfg

    except Exception as e:
        logging.error(f"Cannot load configuration from file {psmqtt_conf_path}: {e}. Aborting.")
        sys.exit(2)
