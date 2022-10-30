#!/usr/bin/env python
#
# Publish the requested data to the MQTT broker and exit.
# All parameters are specified on the command line.
#
import json
import argparse
import logging
import os
import socket
from typing import Any, Dict, List, Union

from task import MqttClient, run_task

def run_tasks(tasks: List[str]) -> None:
    def parse_task(t:str) -> Union[str, Dict[str, Any]]:
        logging.debug("Parsing: %s", t)
        if t.startswith('{'):
            res = json.loads(t)
            assert isinstance(res, dict)
            return res

        return t

    for t in tasks:
        task = parse_task(t)
        if isinstance(task, dict):
            for k,t in task.items():
                run_task(k, t)
        else:
            run_task(task, task)
    return

def run() -> None:

    def validate_args(args:argparse.Namespace) -> argparse.Namespace:
        #
        # establish logging level
        #
        if args.verbose > 2:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)
        logging.debug('validate_args(%s)', args)

        broker_port = args.broker
        parts = broker_port.split(':')
        if len(parts) == 1:
            args.port = 1883
        elif len(parts) == 2:
            args.broker = parts[0]
            args.port = int(parts[1])
        else:
            raise Exception('Bad broker-port spec')

        logging.debug('validate_args() => %s', args)
        return args

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description='Report data to the MQTT broker and exit',
        epilog='See documentation for task definition syntax and examples')

    parser.add_argument('-v', '--verbose', action='count', default=0,
        help='verbosity level, defaults to 0.  Increase it like this: "-vv"')
    parser.add_argument('--qos', type=int, default=0,
        help='QOS, defaults to 0')
    parser.add_argument('--retain', action='store_true',
        help='Retain flag, defaults to False')
    parser.add_argument('--username', default='',
        help='Broker host and optional port, e.g. "mqtt:1883"')
    parser.add_argument('--password', default='',  # BAD IDEA
        help='MQTT password, defaults to ""')
    parser.add_argument('broker',
        help='Broker host and optional port, e.g. "mqtt:1883"')
    parser.add_argument('task', nargs='+',
        help='Task, e.g. "cpu_percent", "virtual_memory/percent"')
        # {"boot_time/{{x|uptime}}": "uptime"}

    args = validate_args(parser.parse_args())

    topic_prefix = f'psmqtt/{socket.gethostname()}/'
    request_topic = ''  # 'request'
    if request_topic != '':
        request_topic = topic_prefix + request_topic + '/'

    mqttc = MqttClient(f'psmqtt-once-{os.getpid()}', False, topic_prefix,
        request_topic, args.qos, args.retain)
    #
    # connect MqttClient to the specified broker
    #
    mqttc.connect(args.broker, args.port, args.username, args.password)

    run_tasks(args.task)

    # wait for ACK from the broker...
    while not mqttc.connected:
        mqttc.mqttc.loop()

    return


if __name__ == '__main__':
    try:
        run()
    except socket.error as err:
        logging.error("socket.error caught: %s", err)

    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt caught, exiting")

    except Exception as ex:
        logging.error("Caught: %s", ex)
