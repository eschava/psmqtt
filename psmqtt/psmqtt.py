#!/usr/bin/env python

import os
import sys
import time
import socket
import logging
import sched
from threading import Thread
from datetime import datetime

import paho.mqtt.client as paho  # pip install paho-mqtt
from recurrent import RecurringEvent  # pip install recurrent
from dateutil.rrule import rrulestr  # pip install python-dateutil

from handlers import handlers
from format import Formatter


class MqttUserdata(object):

    def __init__(self, request_topic, qos, run_task):
        self.request_topic = request_topic
        self.qos = qos
        self.run_task = run_task


class Topic:

    def __init__(self, topic):
        self.topic = topic
        self.wildcard_index, self.wildcard_len = self._find_wildcard(topic)

    @staticmethod
    def _find_wildcard(topic):
        start = 0
        # search for * or ** (but not *; or **;) outside of []
        while start < len(topic):
            wildcard_index = topic.find('*', start)
            if wildcard_index < 0:
                break
            bracket_index = topic.find('[', start)
            if 0 <= bracket_index < wildcard_index:
                start = topic.find(']', bracket_index)
                continue
            wildcard_len = 1
            if (wildcard_index + 1 < len(topic) and
                    topic[wildcard_index + 1] == '*'):  # ** sequence
                wildcard_len += 1
            if (wildcard_index + wildcard_len < len(topic) and
                    topic[wildcard_index + wildcard_len] == ';'):
                start = wildcard_index + wildcard_len
                continue
            return wildcard_index, wildcard_len
        return -1, -1

    def is_multitopic(self):
        return self.wildcard_index > 0

    def get_subtopic(self, param):
        if self.wildcard_index < 0:
            raise Exception("Topic " + self.topic + " have no wildcard")
        return (self.topic[:self.wildcard_index] + param +
                self.topic[self.wildcard_index + self.wildcard_len:])

    def get_topic(self):
        return self.topic

    def get_error_topic(self):
        return self.topic + "/error"


class Config(object):

    def __init__(self, filename):
        self.config = {}
        execfile(filename, self.config)

    def get(self, key, default=None):
        return self.config.get(key, default)


class TimerThread(Thread):

    def __init__(self, s):
        Thread.__init__(self)
        self.s = s

    def run(self):
        self.s.run()

# noinspection PyUnusedLocal
def on_message(mosq, userdata, msg):
    logging.debug(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    if msg.topic.startswith(userdata.request_topic):
        task = msg.topic[len(userdata.request_topic):]
        userdata.run_task(task, task)
    else:
        logging.warn('Unknown topic: ' + msg.topic)

# noinspection PyUnusedLocal
def on_connect(mosq, userdata, result_code):
    if userdata.request_topic != '':
        topic = userdata.request_topic + '#'
        logging.debug(
            "Connected to MQTT broker, subscribing to topic " + topic)
        mosq.subscribe(topic, userdata.qos)

# noinspection PyUnusedLocal
def on_disconnect(mosq, userdata, rc):
    logging.debug("OOOOPS! psmqtt disconnects")
    time.sleep(10)


class PsmqttApp(object):

    qos = 2
    module_path = os.path.dirname(__file__)
    default_config = os.path.join(module_path, 'psmqtt.conf')
    CONFIG = os.getenv('PSMQTTCONFIG', default_config)
    mqttc = None

    try:
        cf = Config(CONFIG)
    except Exception as e:
        print("Cannot load configuration from file %s: %s" % (CONFIG, str(e)))
        sys.exit(2)

    topic_prefix = cf.get('mqtt_topic_prefix', 'psmqtt/' +
                          socket.gethostname() + '/')
    request_topic = cf.get('mqtt_request_topic', 'request')
    if request_topic != '':
        request_topic = topic_prefix + request_topic + '/'

    # fix for error 'No handlers could be found for logger "recurrent"'
    reccurrent_logger = logging.getLogger('recurrent')
    if len(reccurrent_logger.handlers) == 0:
        reccurrent_logger.addHandler(logging.NullHandler())

    def run_task(self, task, topic):
        if task.startswith(self.topic_prefix):
            task = task[len(self.topic_prefix):]

        topic = Topic(topic if topic.startswith(self.topic_prefix)
                      else self.topic_prefix + topic)
        try:
            payload = self.get_value(task)
            is_seq = isinstance(payload, list) or isinstance(payload, dict)
            if is_seq and not topic.is_multitopic():
                raise Exception(
                    "Result of task '" + task +
                    "' has several values but topic doesn't contain '*' char")
            if isinstance(payload, list):
                for i, v in enumerate(payload):
                    topic = topic.get_subtopic(str(i))
                    self.mqttc.publish(
                        topic, str(v), qos=self.qos, retain=False)
            elif isinstance(payload, dict):
                for key in payload:
                    topic = topic.get_subtopic(str(key))
                    v = payload[key]
                    self.mqttc.publish(
                        topic, str(v), qos=self.qos, retain=False)
            else:
                self.mqttc.publish(topic.get_topic(), str(payload),
                                   qos=self.qos, retain=False)
        except Exception as ex:
            self.mqttc.publish(topic.get_error_topic(), str(ex), qos=self.qos,
                               retain=False)
            logging.exception(task + ": " + str(ex))

    def get_value(self, path):
        path, _format = Formatter.get_format(path)
        head, tail = self.split(path)

        if head in handlers:
            value = handlers[head].handle(tail)
            if _format is not None:
                value = Formatter.format(_format, value)
            return value
        else:
            raise Exception(
                "Element '" + head + "' in '" + path + "' is not supported")

    def on_timer(self, s, rrule, tasks):
        if isinstance(tasks, dict):
            for k in tasks:
                self.run_task(k, tasks[k])
        elif isinstance(tasks, list):
            for task in tasks:
                if isinstance(task, dict):
                    for k in task:
                        self.run_task(k, task[k])
                else:
                    self.run_task(task, task)
        else:
            self.run_task(tasks, tasks)

        # add next timer task
        now = datetime.now()
        delay = (rrule.after(now) - now).total_seconds()
        s.enter(delay, 1, self.on_timer, [s, rrule, tasks])

    def split(self, s):
        parts = s.split("/", 1)
        return parts if len(parts) == 2 else [parts[0], '']

    def run(self):
        print('psmqtt using config: %s' % self.CONFIG)
        print('you can set the configuration '
              'with environment variable "PSMQTTCONFIG"')

        clientid = self.cf.get('mqtt_clientid', 'psmqtt-%s' % os.getpid())

        # additonal userdata for mqtt callbacks
        mqttc_userdata = MqttUserdata(
            self.request_topic, self.qos, self.run_task)

        # initialise MQTT broker connection
        mqttc = paho.Client(
            clientid, clean_session=False, userdata=mqttc_userdata)
        self.mqttc = mqttc

        mqttc.on_message = on_message
        mqttc.on_connect = on_connect
        mqttc.on_disconnect = on_disconnect

        mqttc.will_set('clients/psmqtt', payload="Adios!", qos=0, retain=False)

        # Delays will be: 3, 6, 12, 24, 30, 30, ...
        # mqttc.reconnect_delay_set(
        #   delay=3, delay_max=30, exponential_backoff=True)

        mqttc.username_pw_set(self.cf.get('mqtt_username'),
                              self.cf.get('mqtt_password'))

        mqttc.connect(self.cf.get('mqtt_broker', 'localhost'),
                      int(self.cf.get('mqtt_port', '1883')), 60)

        # parse schedule
        schedule = self.cf.get('schedule', {})
        s = sched.scheduler(time.time, time.sleep)
        now = datetime.now()
        for t in schedule:
            r = RecurringEvent()
            dt = r.parse(t)
            if not r.is_recurring:
                logging.error(t + " is not recurring time. Skipping")
                continue
            rrule = rrulestr(dt)
            delay = (rrule.after(now) - now).total_seconds()
            s.enter(delay, 1, self.on_timer, [s, rrule, schedule[t]])

        tt = TimerThread(s)
        tt.daemon = True
        tt.start()
        while True:
            try:
                mqttc.loop_forever()
            except socket.error:
                print('socket error retrying.')
                time.sleep(5)
            except KeyboardInterrupt:
                sys.exit(0)

if __name__ == '__main__':
    app = PsmqttApp()
    app.run()
