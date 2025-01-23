from enum import IntEnum
import json
import logging
import paho.mqtt.client as paho  # pip install paho-mqtt
import time
from typing import Any, Dict, Optional


from .handlers import get_value
from .topic import Topic

theClient: Optional["MqttClient"] = None

class MqttClient:
    '''
    Wrapper around paho.Client
    FIXME: move this class to its own file
    '''

    def __init__(self,
            client_id:str,
            clean_session:bool,
            topic_prefix:str,
            request_topic:str,
            qos:int,
            retain:bool) -> None:

        global theClient
        assert theClient is None
        theClient = self

        self.connected = False
        self.topic_prefix = topic_prefix
        self.request_topic = request_topic
        self.qos = qos
        self.retain = retain
        # initialise MQTT broker connection
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
        logging.debug("Connecting to '%s:%d'", mqtt_broker, mqtt_port)
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
            topic = self.request_topic + '#'
            logging.debug(
                f"Connected to MQTT broker, subscribing to topic '{topic}'")
            mqttc.subscribe(topic, self.qos)
        self.connected = True
        return

    def on_disconnect(self, mqttc: paho.Client, userdata: Any, rc: Any) -> None:
        '''
        mqtt callback
        '''
        logging.debug("OOOOPS! psmqtt disconnects")
        time.sleep(10)  # FIXME: make this configurable
        return

    def on_message(self, mqttc: paho.Client, userdata: Any, msg: paho.MQTTMessage) -> None:
        '''
        mqtt callback
        '''
        logging.debug("on_message()")
        logging.debug(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

        if msg.topic.startswith(self.request_topic):
            task = msg.topic[len(self.request_topic):]
            run_task(task, task)
        else:
            logging.warn('Unknown topic: ' + msg.topic)
        return

    def loop_forever(self) -> None:
        '''
        This function calls the network loop functions for you in an infinite blocking loop.
        It handles reconnecting.
         '''
        logging.info('starting MQTT client loop')
        self.mqttc.loop_forever()

def run_task(taskFriendlyId: str, task: Dict[str,str]) -> None:
    '''
    Runs a task, defined as a dictionary having "task", "params", "topic" and "formatter" fields.
    '''
    mqttc = theClient
    assert mqttc is not None

    def payload_as_string(v:Any) -> str:
        if isinstance(v, dict):
            return json.dumps(v)
        elif isinstance(v, IntEnum):
            return str(v.value)
        elif not isinstance(v, list):
            return str(v)
        elif len(v) == 1:  # single-element array should be presented as single value
            return payload_as_string(v[0])
        #else:
        return json.dumps(v)

    def mqttc_publish(topic:str, payload:str) -> None:
        assert mqttc is not None
        assert mqttc.mqttc is not None
        logging.info("mqttc.publish('%s', '%s')", topic, payload)
        mqttc.mqttc.publish(topic, payload, qos=mqttc.qos, retain=mqttc.retain)
        return

    if task["topic"] is None:
        topic = Topic(mqttc.topic_prefix + "/" + task["task"])
    else:
        topic = Topic(task["topic"] if task["topic"].startswith(mqttc.topic_prefix)
                            else mqttc.topic_prefix + task["topic"])
    logging.debug(f"run_task({taskFriendlyId}): mqtt topic is '{topic.get_topic()}'")

    try:
        payload = get_value(task["task"], task["params"], task["formatter"])
        is_seq = isinstance(payload, list) or isinstance(payload, dict)
        if is_seq and not topic.is_multitopic():
            raise Exception(f"Result of task '{taskFriendlyId}' has several values but topic doesn't contain '*' char")

        if isinstance(payload, list):
            for i, v in enumerate(payload):
                subtopic = topic.get_subtopic(str(i))
                mqttc_publish(subtopic, payload_as_string(v))

        elif isinstance(payload, dict):
            for key in payload:
                subtopic = topic.get_subtopic(str(key))
                v = payload[key]
                mqttc_publish(subtopic, payload_as_string(v))
        else:
            mqttc_publish(topic.get_topic(), payload_as_string(payload))

    except Exception as ex:
        mqttc_publish(topic.get_error_topic(), str(ex))
        logging.exception(f"run_task caught: {task} : {ex}")
    return
