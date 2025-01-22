import os
import logging
import logging.config
import sys
from typing import Any, Dict
import yaml
import json
import jsonschema
from pathlib import Path
import socket


class Config:
    '''
    Config class validates and reads the psmqtt YAML configuration file and reports to the
    rest of the application the data as a dictionary.
    '''
    def __init__(self, filename: str, schema_filename: str):
        '''
        filename is a fully qualified path to the YAML config file.
        The YAML file is validated 
        '''

        with open(schema_filename) as f:
            self.schema = json.load(f)

        with open(filename, 'r') as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing YAML file '{filename}': {e}")
        
        try:
            jsonschema.validate(instance=self.config, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Configuration file '{filename}' does not conform to schema: {e}")

        print(f"Configuration file '{filename}' successfully loaded.")

        # add default values if they're missing:

        # mqtt.broker object
        if 'port' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["port"] = 1883
        if 'username' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["username"] = None
        if 'password' not in self.config["mqtt"]["broker"]:
            self.config['mqtt']["broker"]["password"] = None

        # other "mqtt" keys
        if "clientid" not in self.config["mqtt"]:
            self.config["mqtt"]["clientid"] = 'psmqtt-%s' % os.getpid()
        if "qos" not in self.config["mqtt"]:
            self.config["mqtt"]["qos"] = 0
        if "publish_topic_prefix" not in self.config["mqtt"]:
            hn = socket.gethostname()
            self.config["mqtt"]["publish_topic_prefix"] = f"psmqtt/{hn}/"
        if "request_topic" not in self.config["mqtt"]:
            self.config["mqtt"]["request_topic"] = 'request'

        return

    # def get(self, key:str, default:Any = None) -> Any:
    #     '''
    #     Get config parameter
    #     '''
    #     return self.config.get(key, default)


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
        'PSMQTTCONFIGSCHEMA', os.path.join(dirname, 'schema/psmqtt.conf.schema.json'))

    try:
        # read initial config files
        logging.debug("Loading logging config '%s'", logging_conf_path)
        logging.config.fileConfig(logging_conf_path)

        # fix for error 'No handlers could be found for logger "recurrent"'
        reccurrent_logger = logging.getLogger('recurrent')
        if len(reccurrent_logger.handlers) == 0:
            reccurrent_logger.addHandler(logging.NullHandler())

        logging.debug("Loading app config '%s' and its schema '%s'", psmqtt_conf_path, psmqtt_conf_schema_path)
        return Config(psmqtt_conf_path, psmqtt_conf_schema_path)

    except Exception as e:
        print(f"Cannot load configuration from file {psmqtt_conf_path}: {e}")
        sys.exit(2)
