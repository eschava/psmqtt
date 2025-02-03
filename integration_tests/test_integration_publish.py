import pytest
import time
import math

from integration_tests.psmqtt_container import PSMQTTContainer
from integration_tests.mosquitto_container import MosquittoContainerEnhanced


# GLOBALs

broker = MosquittoContainerEnhanced()

# HELPERS


@pytest.fixture(scope="module", autouse=True)
def setup(request):
    """
    Fixture to setup and teardown the MQTT broker
    """
    broker.start()
    print("Broker successfully started")
    ##time.sleep(10)

    def remove_container():
        broker.stop()

    request.addfinalizer(remove_container)


# TESTS

@pytest.mark.integration
def test_basic_publish():

    with PSMQTTContainer(broker=broker, loglevel="DEBUG") as container:

        tprefix = container.get_mqtt_topic_prefix()
        topics_under_test = [
            # cpu_percent gets published every 1sec:
            {"topic_name": f"{tprefix}/cpu_percent", "expected_payload": "FLOATING_POINT_NUMBER", "frequency_sec": 1},
            {"topic_name": f"{tprefix}/virtual_memory/percent", "expected_payload": "FLOATING_POINT_NUMBER", "frequency_sec": 1},
            # disk_usage gets published every 3sec:
            {"topic_name": f"{tprefix}/disk_usage/percent/|", "expected_payload": "FLOATING_POINT_NUMBER", "frequency_sec": 3},
            # uptime gets published every 5sec:
            {"topic_name": f"{tprefix}/uptime", "expected_payload": "STRING", "frequency_sec": 5},
        ]

        time.sleep(1)  # give time to the PSMQTTContainer to fully start
        if not container.is_running():
            print("Container under test has stopped running... test failed.")
            container.print_logs()
            assert False

        broker.watch_topics([t["topic_name"] for t in topics_under_test])
        container.watch_for_internal_errors(broker)

        # the integration test config contains a configuration to print the boot_time every 5sec,
        # so wait a bit more to reduce test flakyness:
        test_duration_sec = 8

        time.sleep(test_duration_sec)
        container.print_logs()

        # check there were no internal psmqtt errors
        assert container.get_num_internal_errors(broker) == 0

        for t in topics_under_test:
            tname = t["topic_name"]
            msg_count = broker.get_messages_received_in_watched_topic(tname)
            last_payload = broker.get_last_payload_received_in_watched_topic(tname)
            print(f"** TEST RESULTS for topic [{tname}]")
            print(f"  Total messages in topic: {msg_count} msgs")
            print(f"  Last payload in topic: {last_payload}")

            # the 1+ is because psmqtt at startup will publish on each topic immediately; then will start the scheduler:
            expected_msg_count = 1 + math.floor(test_duration_sec/t['frequency_sec'])
            expected_msg_count_min = expected_msg_count - 1
            expected_msg_count_max = expected_msg_count + 2
            print(f"  Expected scheduling period sec: {t['frequency_sec']}")
            print(f"  Expected number of messages: {expected_msg_count}, accepting range {expected_msg_count_min}-{expected_msg_count_max}")

            # some tolerance to deal with jitter during the test:
            assert msg_count >= expected_msg_count_min and msg_count <= expected_msg_count_max

            # check payload
            if t["expected_payload"] == "FLOATING_POINT_NUMBER":
                assert isinstance(float(last_payload), float)
            # no validation otherwise

            print("\n")

        broker.unwatch_all()
        print("Integration test passed!")
