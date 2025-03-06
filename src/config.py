# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import os
import logging
import logging.config
import yaml
import yamale
from yamale import YamaleError

import socket
from .task import Task
from .ha_units import HomeAssistantMeasurementUnits

class Config:
    '''
    Config class validates and reads the psmqtt YAML configuration file and reports to the
    rest of the application the data as a dictionary.
    '''
    HA_SUPPORTED_PLATFORMS = ["sensor", "binary_sensor"]
    HA_SUPPORTED_DEVICE_CLASSES = {
        # see https://www.home-assistant.io/integrations/binary_sensor/#device-class
        "binary_sensor": [
            "battery", "battery_charging", "carbon_monoxide", "cold", "connectivity",
            "door", "garage_door", "gas", "heat", "light", "lock", "moisture", "motion",
            "moving", "occupancy", "opening", "plug", "power", "presence", "problem",
            "running", "safety", "smoke", "sound", "tamper", "update", "vibration", "window"],
        # see https://www.home-assistant.io/integrations/sensor/#device-class
        "sensor": ['date', 'enum', 'timestamp', 'apparent_power', 'aqi', 'area',
                    'atmospheric_pressure', 'battery', 'blood_glucose_concentration',
                    'carbon_monoxide', 'carbon_dioxide', 'conductivity', 'current',
                    'data_rate', 'data_size', 'distance', 'duration', 'energy', 'energy_storage',
                    'frequency', 'gas', 'humidity', 'illuminance', 'irradiance', 'moisture',
                    'monetary', 'nitrogen_dioxide', 'nitrogen_monoxide', 'nitrous_oxide',
                    'ozone', 'ph', 'pm1', 'pm10', 'pm25', 'power_factor', 'power', 'precipitation',
                    'precipitation_intensity', 'pressure', 'reactive_power', 'signal_strength',
                    'sound_pressure', 'speed', 'sulphur_dioxide', 'temperature', 'volatile_organic_compounds',
                    'volatile_organic_compounds_parts', 'voltage', 'volume', 'volume_storage',
                    'volume_flow_rate', 'water', 'weight', 'wind_speed']
    }

    # see https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
    HA_SUPPORTED_STATE_CLASSES = ["measurement", "total", "total_increasing"]

    # see https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
    HA_UNSUPPORTED_DEVICE_CLASSES_FOR_MEASUREMENTS = ["date", "enum", "energy", "gas", "monetary", "timestamp", "volume", "water"]

    def __init__(self):
        self.config = None
        self.schema = None

    def load(self, filename: str = None, schema_filename: str = None):
        '''
        filename is a fully qualified path to the YAML config file.
        The YAML file is validated against the schema file provided as argument,
        and optional configuration parameters are populated with their default values.
        '''

        dirname = os.path.dirname(os.path.abspath(__file__))
        dirname = os.path.abspath(os.path.join(dirname, '..'))

        if filename is None:
            filename = os.getenv(
                'PSMQTTCONFIG', os.path.join(dirname, 'psmqtt.yaml'))
        if schema_filename is None:
            schema_filename = os.getenv(
                'PSMQTTCONFIGSCHEMA', os.path.join(dirname, 'schema/psmqtt.schema.yaml'))

        logging.info("Loading app config '%s' and its schema '%s'", filename, schema_filename)

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
        self._fill_defaults_options()
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

    def _fill_defaults_options(self):
        # logging
        if "options" not in self.config:
            self.config["options"] = {"exit_after_num_tasks": 0}
        if "exit_after_num_tasks" not in self.config["options"]:
            self.config["options"]["exit_after_num_tasks"] = 0

    def _fill_defaults_mqtt(self):
        m = self.config["mqtt"]

        # mqtt.broker object
        if 'port' not in m["broker"]:
            m["broker"]["port"] = 1883
        if 'username' not in m["broker"]:
            m["broker"]["username"] = None
        if 'password' not in m["broker"]:
            m["broker"]["password"] = None

        # other optional "mqtt" keys
        if "retain" not in m:
            m["retain"] = False
        if "clean_session" not in m:
            m["clean_session"] = False
        if "clientid" not in m:
            m["clientid"] = 'psmqtt-%s' % os.getpid()
        if "qos" not in m:
            m["qos"] = 0
        if "reconnect_period_sec" not in m:
            m["reconnect_period_sec"] = 5
        if "publish_topic_prefix" not in m:
            hn = socket.gethostname()
            m["publish_topic_prefix"] = f"psmqtt/{hn}/"
        else:
            # make sure the publish_topic_prefix ALWAYS ends with a slash,
            # to ensure separation from the topic that will be appended to it
            if m["publish_topic_prefix"][-1] != '/':
                m["publish_topic_prefix"] += '/'

        if "request_topic" not in m:
            m["request_topic"] = 'request'

        # mqtt.ha_discovery object
        if 'ha_discovery' not in m:
            m["ha_discovery"] = {"enabled": False, "topic": "homeassistant"}
        if 'enabled' not in m["ha_discovery"]:
            m["ha_discovery"]["enabled"] = False
        if 'topic' not in m["ha_discovery"]:
            m["ha_discovery"]["topic"] = "homeassistant"
        if 'device_name' not in m["ha_discovery"]:
            m["ha_discovery"]["device_name"] = socket.gethostname()

        # enhance the original config with the one containing all settings:
        self.config["mqtt"] = m

    def _fill_defaults_schedule(self):
        # provide defaults for the "schedule" key
        if not isinstance(self.config["schedule"], list):
            raise ValueError("Invalid 'schedule' key in configuration file: must be a list")

        available_handlers_names = Task.get_supported_handlers()

        validated_schedule = []
        for s in self.config["schedule"]:
            # "cron" & "tasks" fields presence is already ensured by the JSON schema
            validated_tasks = []
            for t in s["tasks"]:
                # validate "task" name
                if t["task"] not in available_handlers_names:
                    raise ValueError(f"Invalid task '{t['task']}' in configuration file. Supported tasks are: {available_handlers_names}")

                # provide defaults for the task:
                t = self._fill_defaults_task(t)

                # consider this as valid:
                validated_tasks.append(t)

            validated_schedule.append({"cron": s["cron"], "tasks": validated_tasks})

        # get rid of original schedule and replace with validated scheduling rules:
        self.config["schedule"] = validated_schedule

    def _fill_defaults_task(self, t: dict[str,str]) -> dict[str,str]:
        if "params" not in t:
            t["params"] = []
        if "formatter" not in t:
            t["formatter"] = None
        if "topic" not in t:
            t["topic"] = None

        if "ha_discovery" not in t:
            # HA discovery disabled for this task:
            t["ha_discovery"] = None
        else:
            h = t["ha_discovery"]

            # name is required and shall be non-empty
            if "name" not in h:
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.name' attribute in configuration file: missing")
            if h["name"] == '':
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.name' attribute in configuration file: empty")

            # optional parameters with defaults:

            if "platform" not in h:
                # most of psutil/pySMART tasks are sensors, so "sensor" is a good deafult:
                h["platform"] = "sensor"
            elif h["platform"] not in Config.HA_SUPPORTED_PLATFORMS:
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.platform' attribute in configuration file: {h['platform']}. Expected one of {Config.HA_SUPPORTED_PLATFORMS}")
            if "device_class" not in h:
                h["device_class"] = None
            elif h["device_class"] not in Config.HA_SUPPORTED_DEVICE_CLASSES[h["platform"]]:
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.device_class' attribute in configuration file: {h['device_class']}. Expected one of {Config.HA_SUPPORTED_DEVICE_CLASSES}")

            if "unit_of_measurement" in h and h["unit_of_measurement"] not in HomeAssistantMeasurementUnits.get_all_constants():
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.unit_of_measurement' attribute in configuration file: {h['unit_of_measurement']}. Expected one of {HomeAssistantMeasurementUnits.get_all_constants()}")

            if "state_class" not in h:
                # "measurement" is a good default since most of psutil/pySMART tasks represent measurements
                # of bytes, percentages, temperatures, etc.
                # We just make sure to never add "state_class" to some types of "device_class"es that will
                # trigger errors on the HomeAssistant side...
                if h["device_class"] not in Config.HA_UNSUPPORTED_DEVICE_CLASSES_FOR_MEASUREMENTS:
                    h["state_class"] = "measurement"
            elif "state_class" in h and h["state_class"] not in Config.HA_SUPPORTED_STATE_CLASSES:
                raise ValueError(f"{t['task']}: Invalid 'ha_discovery.state_class' attribute in configuration file: {h['state_class']}. Expected one of {Config.HA_SUPPORTED_STATE_CLASSES}")

            # optional parameters without defaults:

            optional_params = ["unit_of_measurement", "icon", "expire_after", "payload_on", "payload_off", "value_template"]
            for o in optional_params:
                if o not in h:
                    # create the key but set its value to None
                    h[o] = None

            t["ha_discovery"] = h

        return t

    def apply_logging_config(self):
        # Apply logging config
        logl = self.config["logging"]["level"]
        logging.info(f"Setting log level to {logl}")
        if logl == "DEBUG":
            logging.basicConfig(level=logging.DEBUG, force=True)
        elif logl == "INFO":
            logging.basicConfig(level=logging.INFO, force=True)
        elif logl == "WARN" or logl == "WARNING":
            logging.basicConfig(level=logging.WARNING, force=True)
        elif logl == "ERR" or logl == "ERROR":
            logging.basicConfig(level=logging.ERROR, force=True)
        else:
            logging.error(f"Invalid logging level '{logl}' in config file. Defaulting to ERROR level.")
            logging.basicConfig(level=logging.ERROR, force=True)
