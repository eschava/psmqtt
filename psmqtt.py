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
from dateutil.rrule import *  # pip install python-dateutil

from handlers import handlers
from format import Formatter

qos = 2
CONFIG = os.getenv('PSMQTTCONFIG', 'psmqtt.conf')


class Config(object):
    def __init__(self, filename=CONFIG):
        self.config = {}
        execfile(filename, self.config)

    def get(self, key, default=None):
        return self.config.get(key, default)


try:
    cf = Config()
except Exception, e:
    print "Cannot load configuration from file %s: %s" % (CONFIG, str(e))
    sys.exit(2)

topic_prefix = cf.get('mqtt_topic_prefix', 'psmqtt/')
request_topic = cf.get('mqtt_request_topic', 'request')
if request_topic != '':
    request_topic = topic_prefix + request_topic + '/'


def run_task(task):
    if task.startswith(topic_prefix):
        task = task[len(topic_prefix):]

    topic_base = topic_prefix + task
    try:
        payload = get_value(task)
        is_seq = isinstance(payload, list) or isinstance(payload, dict)
        multitask = '*' in task
        if is_seq and not multitask:
            raise Exception("Result of task '" + task + "' has several values but task doesn't contain '*' char")
        if isinstance(payload, list):
            for i, v in enumerate(payload):
                topic = topic_base.replace('*', str(i))
                mqttc.publish(topic, str(v), qos=qos, retain=False)
        elif isinstance(payload, dict):
            for key in payload:
                topic = topic_base.replace('*', key)
                v = payload[key]
                mqttc.publish(topic, str(v), qos=qos, retain=False)
        else:
            mqttc.publish(topic_base, str(payload), qos=qos, retain=False)
    except Exception, e:
        mqttc.publish(topic_base + "/error", str(e), qos=qos, retain=False)
        logging.exception(task + ": " + str(e))


def get_value(path):
    path, _format = Formatter.get_format(path)
    head, tail = split(path)

    if head in handlers:
        value = handlers[head].handle(tail)
        if _format is not None:
            value = Formatter.format(_format, value)
        return value
    else:
        raise Exception("Element '" + head + "' in '" + path + "' is not supported")


def on_message(mosq, userdata, msg):
    logging.debug(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    if msg.topic.startswith(request_topic):
        task = msg.topic[len(request_topic):]
        run_task(task)
    else:
        logging.warn('Unknown topic: ' + msg.topic)


def on_timer(s, rrule, tasks):
    if isinstance(tasks, list):
        for task in tasks:
            run_task(task)
    else:
        run_task(tasks)

    # add next timer task
    now = datetime.now()
    delay = (rrule.after(now) - now).total_seconds()
    s.enter(delay, 1, on_timer, [s, rrule, tasks])


def on_connect(mosq, userdata, result_code):
    if request_topic != '':
        topic = request_topic + '#'
        logging.debug("Connected to MQTT broker, subscribing to topic " + topic)
        mqttc.subscribe(topic, qos)


def on_disconnect(mosq, userdata, rc):
    logging.debug("OOOOPS! psmqtt disconnects")
    time.sleep(10)


def split(s):
    parts = s.split("/", 1)
    return parts if len(parts) == 2 else [parts[0], '']


class TimerThread(Thread):
    def __init__(self, s):
        Thread.__init__(self)
        self.s = s

    def run(self):
        self.s.run()


if __name__ == '__main__':
    clientid = cf.get('mqtt_clientid', 'psmqtt-%s' % os.getpid())
    # initialise MQTT broker connection
    mqttc = paho.Client(clientid, clean_session=False)

    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect

    mqttc.will_set('clients/psmqtt', payload="Adios!", qos=0, retain=False)

    # Delays will be: 3, 6, 12, 24, 30, 30, ...
    # mqttc.reconnect_delay_set(delay=3, delay_max=30, exponential_backoff=True)

    mqttc.username_pw_set(cf.get('mqtt_username'), cf.get('mqtt_password'))

    mqttc.connect(cf.get('mqtt_broker', 'localhost'), int(cf.get('mqtt_port', '1883')), 60)

    # parse schedule
    schedule = cf.get('schedule', {})
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
        s.enter(delay, 1, on_timer, [s, rrule, schedule[t]])

    tt = TimerThread(s)
    tt.daemon = True
    tt.start()

    while True:
        try:
            mqttc.loop_forever()
        except socket.error:
            time.sleep(5)
        except KeyboardInterrupt:
            sys.exit(0)
