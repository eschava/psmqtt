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

    # Counter of messages that were published successfully
    num_published_successful = 0

    # Counter of total messages reaching the MqttClient.publish()
    num_published_total = 0

    # Constant value indicating the absence of a connection to the broker from get_connection_id()
    CONN_ID_INVALID = 0

    # Constant values indicating the last-will MQTT topic & payload
    PSMQTT_STATUS_TOPIC = "psmqtt_status"

    NEW_CONN_PAYLOAD = "online"
    LAST_WILL_PAYLOAD = "offline"

    def __init__(self,
            client_id:str,
            clean_session:bool,
            topic_prefix:str,
            request_topic:str,
            qos:int,
            retain:bool,
            reconnect_period_sec:float,
            ha_status_topic:str) -> None:

        self.topic_prefix = topic_prefix
        assert len(self.topic_prefix) > 0 and self.topic_prefix[-1] == "/"

        self.client_id = client_id
        self.request_topic = request_topic
        self.qos = qos
        self.retain = retain
        self.reconnect_period_sec = reconnect_period_sec
        self.ha_status_topic = ha_status_topic

        # internal flags:
        self._connection_id = MqttClient.CONN_ID_INVALID
        self._ha_discovery_messages_requested = False

        # use MQTT v3.1.1 for now
        self._mqttc = paho.Client(paho.CallbackAPIVersion.VERSION2,
            client_id, clean_session=clean_session, userdata=self,
            protocol=paho.MQTTv311)
        # protocol=paho.MQTTv5
        # see http://www.steves-internet-guide.com/python-mqtt-client-changes/

        # set the call-backs
        self._mqttc.on_message = self.on_message
        self._mqttc.on_connect = self.on_connect
        self._mqttc.on_disconnect = self.on_disconnect
        self._mqttc.on_publish = self.on_publish
        self._mqttc.on_log = self.on_log

        # for sudden disconnection, send a last-will message
        self._mqttc.will_set(self.get_psmqtt_status_topic(), payload=MqttClient.LAST_WILL_PAYLOAD, qos=0, retain=True)
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

        self._mqttc.username_pw_set(username, password)

        if mqtt_port == 8883:
            assert paho.ssl
            self._mqttc.tls_set(ca_certs=None, certfile=None, keyfile=None,
                cert_reqs=paho.ssl.CERT_REQUIRED, tls_version=paho.ssl.PROTOCOL_TLS,
                ciphers=None)
        logging.info(f"Connecting to MQTT broker '{mqtt_broker}:{mqtt_port}' with client_id={self.client_id}")
        rc = self._mqttc.connect(mqtt_broker, mqtt_port)
        logging.info(f"Connecting to MQTT broker '{mqtt_broker}:{mqtt_port}'... return code was {rc}")

        if rc == paho.MQTT_ERR_SUCCESS:
            return True
        return False

    # FIXME: change this signature to allow batch-sending multiple messages
    def publish(self, topic:str, payload:str) -> None:
        '''
        Publish a message to the MQTT broker
        '''
        logging.debug("MqttClient.publish('%s', '%s')", topic, payload)
        MqttClient.num_published_total += 1
        self._mqttc.publish(topic, payload, qos=self.qos, retain=self.retain)
        return

    def loop_start(self) -> None:
        '''
        See https://www.eclipse.org/paho/clients/python/docs/#network-loop
         '''
        rc = self._mqttc.loop_start()
        logging.info(f"started MQTT client loop for connection_id={self._connection_id}; return code was {rc}")

    def loop_stop(self) -> None:
        '''
        See https://www.eclipse.org/paho/clients/python/docs/#network-loop
         '''
        rc = self._mqttc.loop_stop()
        logging.info(f"stopped MQTT client loop for connection_id={self._connection_id}; return code was {rc}")

    def is_connected(self) -> bool:
        '''
        Returns true if currently connected to the MQTT broker
        '''
        return self._mqttc.is_connected()

    def get_connection_id(self) -> int:
        '''
        Returns the ID of the current connection to the MQTT broker;
        this ID allows to distinguish between different connections so that
        the caller can detect whether the connection has been lost and re-established
        '''
        if self._mqttc.is_connected():
            return self._connection_id
        return MqttClient.CONN_ID_INVALID

    def get_and_reset_ha_discovery_messages_requested_flag(self) -> bool:
        '''
        Returns the value of the internal flag _ha_discovery_messages_requested and resets it
        '''
        ret = self._ha_discovery_messages_requested
        self._ha_discovery_messages_requested = False
        return ret

    def get_psmqtt_status_topic(self) -> str:
        '''
        Returns the topic used to publish metrics related to PSMQTT itself
        '''
        return self.topic_prefix + MqttClient.PSMQTT_STATUS_TOPIC

    # ---------------------------------------------------------------------------- #
    #                                   Callbacks                                  #
    # These will execute in the Paho secondary thread startd via loop_start()      #
    # ---------------------------------------------------------------------------- #

    def on_connect(self, mqttc: paho.Client, userdata: Any, flags: paho.ConnectFlags,
            reason_code: paho.ReasonCode, properties: paho.Properties = None) -> None:
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
        # create an ID for this new connection to the MQTT broker:
        self._connection_id += 1

        if reason_code != 0:
            logging.warning(f"Connected to MQTT broker with reason_code={reason_code}, connection_id={self._connection_id}")
        else:
            logging.info(f"Successfully connected to MQTT broker with connection_id={self._connection_id}")

        # update our status:
        self._mqttc.publish(self.get_psmqtt_status_topic(), MqttClient.NEW_CONN_PAYLOAD, qos=self.qos, retain=True)

        if self.request_topic != '':
            topic = self.request_topic
            if topic[-1] != '/':
                topic += "/"
            topic += "#"   # match all remaining levels in the topic hierarchy
            logging.info(f"Subscribing to REQUEST topic '{topic}'")
            mqttc.subscribe(topic, self.qos)
        # else: request topic is disabled

        if self.ha_status_topic != '':
            logging.info(f"Subscribing to HomeAssistant status topic '{self.ha_status_topic}'")
            mqttc.subscribe(self.ha_status_topic, self.qos)
        # else: Home Assistant MQTT discovery messages are disabled

        return

    def on_disconnect(self, mqttc: paho.Client, userdata: Any, disconnect_flags: paho.DisconnectFlags,
                      reason_code: paho.ReasonCode, properties: paho.Properties) -> None:
        '''
        MQTT callback in case of unexpected disconnection from the broker
        '''
        if reason_code != 0:
            MqttClient.num_disconnects += 1
            logging.warning(f"OOOOPS! Unexpected disconnection from the MQTT broker with reason=[{reason_code}] for connection_id={self._connection_id}. Reconnecting in {self.reconnect_period_sec}sec.")
            time.sleep(self.reconnect_period_sec)
        #else: reason_code==0 indicates an intentional disconnect
        return

    def on_message(self, mqttc: paho.Client, userdata: Any, msg: paho.MQTTMessage) -> None:
        '''
        MQTT callback in case a message is received on the REQUEST topic
        '''
        logging.info(f"MqttClient.on_message(): topic: {msg.topic}; payload: {msg.payload}")

        if msg.topic.startswith(self.request_topic):
            #task = msg.topic[len(self.request_topic):]
            # FIXME: deserialize from the payload the YAML that defines the TASK
            #        and run it -- see https://github.com/eschava/psmqtt/issues/70
            logging.error("Feature not yet implemented. Please raise a github issue if you need it.")
        elif msg.topic == self.ha_status_topic:
            mqtt_payload = msg.payload.decode("UTF-8")
            if mqtt_payload == "online":
                logging.info("HomeAssistant status changed to 'online'. Need to publish MQTT discovery messages.")
                self._ha_discovery_messages_requested = True
            elif mqtt_payload == "offline":
                # this is typically not a good news, unless it's a planned maintainance
                logging.info("!!! HomeAssistant status changed to 'offline' !!!")
        else:
            logging.warning(f"Unknown topic: {msg.topic}")
        return

    def on_publish(self, mqttc: paho.Client, userdata: Any, mid: int,
                   reason_code: paho.ReasonCode, properties: paho.Properties) -> None:
        '''
        MQTT callback in case of successful/failed publish()
        '''
        MqttClient.num_published_successful += 1
        return

    def on_log(self, mqttc: paho.Client, userdata: Any, level: int, buf: str) -> None:
        '''
        MQTT callback when paho needs to log something
        This seems unused right now and might need to be turned out via some flag
        '''
        logging.log(level, "Paho MQTT msg: " + buf)
        return
