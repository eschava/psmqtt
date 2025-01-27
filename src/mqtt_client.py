# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
import paho.mqtt.client as paho  # pip install paho-mqtt
import time
from typing import Any, Optional


class MqttClient:
    '''
    Wrapper around paho.Client
    '''

    # Counter of MQTT broker disconnections
    num_disconnects = 0

    def __init__(self,
            client_id:str,
            clean_session:bool,
            topic_prefix:str,
            request_topic:str,
            qos:int,
            retain:bool,
            reconnect_period_sec:float) -> None:

        self.connected = False
        self.topic_prefix = topic_prefix
        self.request_topic = request_topic
        self.qos = qos
        self.retain = retain
        self.reconnect_period_sec = reconnect_period_sec

        # use MQTT v3.1.1 for now
        self.mqttc = paho.Client(paho.CallbackAPIVersion.VERSION1,
            client_id, clean_session=clean_session, userdata=self,
            protocol=paho.MQTTv311)
        # protocol=paho.MQTTv5
        # see http://www.steves-internet-guide.com/python-mqtt-client-changes/

        # set the call-backs
        self.mqttc.on_message = self.on_message
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_disconnect = self.on_disconnect

        self.mqttc.will_set('clients/psmqtt', payload="Adios!", qos=0, retain=False)
        return

    def connect(self,
            mqtt_broker:str,
            mqtt_port:int,
            username:str,
            password:Optional[str]) -> bool:
        '''
        Connect to the MQTT broker
        '''
        # Delays will be: 3, 6, 12, 24, 30, 30, ...
        # mqttc.reconnect_delay_set(delay=3, delay_max=30, exponential_backoff=True)

        self.mqttc.username_pw_set(username, password)

        if mqtt_port == 8883:
            assert paho.ssl
            self.mqttc.tls_set(ca_certs=None, certfile=None, keyfile=None,
                cert_reqs=paho.ssl.CERT_REQUIRED, tls_version=paho.ssl.PROTOCOL_TLS,
                ciphers=None)
        logging.debug("Connecting to MQTT broker '%s:%d'", mqtt_broker, mqtt_port)
        self.mqttc.connect(mqtt_broker, mqtt_port)
        return True

    def on_connect(self, mqttc: paho.Client, userdata: Any, flags: Any,
            result_code: Any, properties: Any = None) -> None:
        '''
        mqtt callback
        client:     the client instance for this callback
        userdata:   the private user data as set in Client() or userdata_set()
        flags:      response flags sent by the broker
        rc:         the connection result
        reasonCode: the MQTT v5.0 reason code: an instance of the ReasonCode class.
                    ReasonCode may be compared to integer.
        properties: the MQTT v5.0 properties returned from the broker.  An instance
                    of the Properties class.
                    For MQTT v3.1 and v3.1.1 properties is not provided but for
                    compatibility with MQTT v5.0, we recommend adding
                    properties=None.
        '''
        logging.debug("on_connect()")
        if self.request_topic != '':
            topic = self.request_topic
            if topic[-1] != '/':
                topic += "/"
            topic += "#"   # match all remaining levels in the topic hierarchy
            logging.debug(
                f"Connected to MQTT broker, subscribing to topic '{topic}'")
            mqttc.subscribe(topic, self.qos)
        # else: request topic is disabled

        self.connected = True
        return

    def on_disconnect(self, mqttc: paho.Client, userdata: Any, rc: Any) -> None:
        '''
        MQTT callback in case of unexpected disconnection from the broker
        '''
        if rc != 0:
            MqttClient.num_disconnects += 1
            logging.debug("OOOOPS! Unexpected disconnection from the MQTT broker. Reconnecting in {self.reconnect_period_sec}sec.")
            time.sleep(self.reconnect_period_sec)
        #else: rc==0 indicates an intentional disconnect
        return

    def on_message(self, mqttc: paho.Client, userdata: Any, msg: paho.MQTTMessage) -> None:
        '''
        MQTT callback in case a message is received on the REQUEST topic
        '''
        logging.debug("MqttClient.on_message()")
        logging.debug(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

        if msg.topic.startswith(self.request_topic):
            #task = msg.topic[len(self.request_topic):]
            # FIXME: deserialize from the payload the YAML that defines the TASK
            #        and run it
            logging.error("Feature not yet implemented. Please raise a github issue if you need it.")
        else:
            logging.warning('Unknown topic: ' + msg.topic)
        return

    def publish(self, topic:str, payload:str) -> None:
        logging.info("MqttClient.publish('%s', '%s')", topic, payload)
        self.mqttc.publish(topic, payload, qos=self.qos, retain=self.retain)
        return

    def loop_start(self) -> None:
        '''
        See https://www.eclipse.org/paho/clients/python/docs/#network-loop
         '''
        logging.info('starting MQTT client loop')
        self.mqttc.loop_start()

    def loop_stop(self) -> None:
        '''
        See https://www.eclipse.org/paho/clients/python/docs/#network-loop
         '''
        logging.info('stopping MQTT client loop')
        self.mqttc.loop_stop()
