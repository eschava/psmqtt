import os
import logging
import logging.config
import sys
from typing import Any, Dict


class Config:
    '''
    Application configuration serialized from a python file.
    '''
    def __init__(self, filename:str):
        '''
        filename is a fully qualified path to config file,
        which is just a python file.
        globals from that file are stored in self.config
        '''
        self.config: Dict[str, Any] = {}
        exec(compile(open(filename, "rb").read(), filename, 'exec'), self.config)
        return

    def get(self, key:str, default:Any = None) -> Any:
        '''
        Get config parameter
        '''
        return self.config.get(key, default)


def load_config() -> Config:
    '''
    Load logging and app config, returns the latter.
    '''

    dirname = os.path.dirname(os.path.abspath(__file__))
    dirname = os.path.abspath(os.path.join(dirname, '..'))

    logging_conf_path = os.path.join(dirname, 'logging.conf')
    psmqtt_conf_path = os.getenv(
        'PSMQTTCONFIG', os.path.join(dirname, 'psmqtt.conf'))

    try:
        # read initial config files
        logging.debug("Loading logging config '%s'", logging_conf_path)
        logging.config.fileConfig(logging_conf_path)

        # fix for error 'No handlers could be found for logger "recurrent"'
        reccurrent_logger = logging.getLogger('recurrent')
        if len(reccurrent_logger.handlers) == 0:
            reccurrent_logger.addHandler(logging.NullHandler())

        logging.debug("Loading app config '%s'", psmqtt_conf_path)
        return Config(psmqtt_conf_path)

    except Exception as e:
        print(f"Cannot load configuration from file {psmqtt_conf_path}: {e}")
        sys.exit(2)
