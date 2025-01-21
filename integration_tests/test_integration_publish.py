import pytest
import time

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

    def remove_container():
        broker.stop()

    request.addfinalizer(remove_container)


# TESTS

@pytest.mark.integration
def test_basic_publish():

    with PSMQTTContainer(broker=broker) as container:

        dockerid = container.get_short_id()
        topics_under_test = [
            {"topic_name": f"psmqtt/{dockerid}/cpu_percent", "expected_payload": "FLOATING_POINT_NUMBER", "min_msg_count": 5},
            {"topic_name": f"psmqtt/{dockerid}/virtual_memory/percent", "expected_payload": "FLOATING_POINT_NUMBER", "min_msg_count": 5},
            # disk_usage gets published every 3sec:
            {"topic_name": f"psmqtt/{dockerid}/disk_usage/percent/|", "expected_payload": "FLOATING_POINT_NUMBER", "min_msg_count": 2},
            # uptime gets published every 5sec:
            {"topic_name": f"psmqtt/{dockerid}/uptime", "expected_payload": "STRING", "min_msg_count": 1},
        ]

        time.sleep(1)  # give time to the PSMQTTContainer to fully start
        if not container.is_running():
            print("Container under test has stopped running... test failed.")
            container.print_logs()
            assert False

        broker.watch_topics([t["topic_name"] for t in topics_under_test])

        # the integration test config contains a configuration to print the boot_time every 5sec,
        # so wait a bit more to reduce test flakyness:
        time.sleep(6)
        container.print_logs()

        for t in topics_under_test:
            tname = t["topic_name"]
            msg_count = broker.get_messages_received_in_watched_topic(tname)
            last_payload = broker.get_last_payload_received_in_watched_topic(tname)
            print(f"** TEST RESULTS for topic [{tname}]")
            print(f"  Total messages in topic: {msg_count} msgs")
            print(f"  Last payload in topic: {last_payload}")

            # some tolerance to deal with jitter during the test:
            assert msg_count >= t["min_msg_count"] and msg_count <= t["min_msg_count"]+2

            # check payload
            if t["expected_payload"] == "FLOATING_POINT_NUMBER":
                assert isinstance(float(last_payload), float)
            # no validation otherwise

            print("\n")

        broker.unwatch_all()
        print("Integration test passed!")
