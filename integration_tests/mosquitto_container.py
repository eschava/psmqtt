import os
import time
from testcontainers.mqtt import MosquittoContainer
from testcontainers.core.waiting_utils import wait_container_is_ready
from typing_extensions import Self

from paho.mqtt import client as mqtt_client
import paho.mqtt.enums
from queue import Queue
from typing import Optional

# ---------------------------------------------------------------------------- #
#                          MosquittoContainerEnhanced                          #
# ---------------------------------------------------------------------------- #

class MosquittoContainerEnhanced(MosquittoContainer):
    """
    Specialization of MosquittoContainer adding the ability to watch topics
    """

    def __init__(
        self,
        image: str = "eclipse-mosquitto:latest",
        **kwargs,
    ) -> None:
        super().__init__(image, **kwargs)

        # helper used to turn asynchronous methods into synchronous:
        self.msg_queue = Queue()

        # dictionary of watched topics and their message counts:
        self.watched_topics = {}

    def start(self) -> Self:
        # do container start
        super().start()
        # now add callback
        self.get_client().on_message = MosquittoContainerEnhanced.on_message
        return self

    def stop(self, force=True, delete_volume=True) -> None:
        self.watched_topics = {}  # clean all watched topics as well
        super().stop(force, delete_volume)

    class WatchedTopicInfo:
        def __init__(self):
            self.count = 0
            self.timestamp_start_watch = time.time()
            self.last_payload = ""

        def on_message(self, msg: mqtt_client.MQTTMessage):
            self.count += 1
            # for simplicity: assume strings are used in integration tests and are UTF8-encoded:
            self.last_payload = msg.payload.decode("UTF-8")

        def get_message_count(self) -> int:
            return self.count

        def get_last_payload(self) -> str:
            return self.last_payload

        def get_rate(self) -> float:
            duration = time.time() - self.timestamp_start_watch
            if duration > 0:
                return float(self.count) / float(duration)
            return 0.0

    def on_message(
        client: mqtt_client.Client, mosquitto_container: "MosquittoContainerEnhanced", msg: mqtt_client.MQTTMessage
    ):
        # very verbose but useful for debug:
        # print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if msg.topic == "$SYS/broker/messages/received":
            mosquitto_container.msg_queue.put(msg)
        else:
            # this should be a topic added through the watch_topics() API...
            # just check it has not been removed (e.g. by unwatch_all):
            if msg.topic in mosquitto_container.watched_topics:
                mosquitto_container.watched_topics[msg.topic].on_message(msg)
            else:
                print(f"Received msg on topic [{msg.topic}] that is not being watched")

    def get_messages_received(self) -> int:
        """
        Returns the total number of messages received by the broker so far.
        """

        try:
            client = self.get_client()
        except OSError as err:
            raise RuntimeError(f"Could not connect to Mosquitto broker: {err}")

        client.subscribe("$SYS/broker/messages/received")

        # wait till we get the first message from the topic;
        # this wait will be up to 'sys_interval' second long (see mosquitto.conf)
        try:
            message = self.msg_queue.get(block=True, timeout=5)
            return int(message.payload.decode())
        except Queue.Empty:
            return 0

    def watch_topics(self, topics: list):
        try:
            client = self.get_client()
        except OSError as err:
            raise RuntimeError(f"Could not connect to Mosquitto broker: {err}")

        filtered_topics = []
        for t in topics:
            if t in self.watched_topics:
                continue  # nothing to do... the topic had already been subscribed
            self.watched_topics[t] = MosquittoContainerEnhanced.WatchedTopicInfo()
            # the topic list is actually a list of tuples (topic_name,qos)
            filtered_topics.append((t, 0))

        # after subscribe() the on_message() callback will be invoked
        err, _ = client.subscribe(filtered_topics)
        if err != paho.mqtt.enums.MQTTErrorCode.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Failed to subscribe to topics: {filtered_topics}")

    def unwatch_all(self):
        try:
            client = self.get_client()
        except OSError as err:
            raise RuntimeError(f"Could not connect to Mosquitto broker: {err}")

        # unsubscribe from all topics
        client.unsubscribe(list(self.watched_topics.keys()))
        self.watched_topics = {}

    def get_messages_received_in_watched_topic(self, topic: str) -> int:
        if topic not in self.watched_topics:
            raise RuntimeError(f"Topic {topic} is not watched! Fix the test")
        return self.watched_topics[topic].get_message_count()

    def get_last_payload_received_in_watched_topic(self, topic: str) -> str:
        if topic not in self.watched_topics:
            raise RuntimeError(f"Topic {topic} is not watched! Fix the test")
        return self.watched_topics[topic].get_last_payload()

    def get_message_rate_in_watched_topic(self, topic: str) -> float:
        if topic not in self.watched_topics:
            raise RuntimeError(f"Topic {topic} is not watched! Fix the test")
        return self.watched_topics[topic].get_rate()

    def publish_message(self, topic: str, payload: str):
        ret = self.client.publish(topic, payload)
        ret.wait_for_publish(timeout=2)
        if not ret.is_published():
            raise RuntimeError(f"Could not publish a message on topic {topic} to Mosquitto broker: {ret}")

    def print_logs(self) -> str:
        print("** BROKER LOGS [STDOUT]:")
        print(self.get_logs()[0].decode())
        print("** BROKER LOGS [STDERR]:")
        print(self.get_logs()[1].decode())
