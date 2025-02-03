import pytest
import time
import json

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
def test_ha_discovery():

    with PSMQTTContainer(config_file="integration-tests-psmqtt2-with-ha-discovery.yaml", broker=broker, loglevel="DEBUG") as container:

        tprefix = container.get_short_id()
        topics_under_test = [
            # first task
            {
                "topic_name": f"homeassistant/sensor/{tprefix}/{tprefix}-cpu_times-71ebde4492f9/config",
                "expected_payload": "VALID_JSON"
            },
            {
                "topic_name": f"psmqtt/{tprefix}/cpu_times/iowait",
                "expected_payload": "FLOATING_POINT_NUMBER"
            },

            # second task
            {
                "topic_name": f"homeassistant/sensor/{tprefix}/{tprefix}-virtual_memory-fd86717aca41/config",
                "expected_payload": "VALID_JSON"
            },
            {
                "topic_name": f"psmqtt/{tprefix}/virtual_memory/percent",
                "expected_payload": "FLOATING_POINT_NUMBER"
            },

            # third task
            {
                "topic_name": f"homeassistant/sensor/{tprefix}/{tprefix}-disk_usage-4ee49bfef1f0/config",
                "expected_payload": "VALID_JSON"
            },
            {
                "topic_name": f"psmqtt/{tprefix}/disk_usage/percent/|",
                "expected_payload": "FLOATING_POINT_NUMBER"
            },
        ]

        time.sleep(1)  # give time to the PSMQTTContainer to fully start
        if not container.is_running():
            print("Container under test has stopped running... test failed.")
            container.print_logs()
            assert False

        broker.watch_topics([t["topic_name"] for t in topics_under_test])
        container.watch_for_internal_errors(broker)
        time.sleep(3)
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

            # assert we received something
            assert msg_count > 0

            # check payload
            if t["expected_payload"] == "FLOATING_POINT_NUMBER":
                assert isinstance(float(last_payload), float)
            elif t["expected_payload"] == "VALID_JSON":
                # check JSON
                assert isinstance(last_payload, str)
                try:
                    json.loads(last_payload)
                except ValueError:
                    assert False
            else:
                assert False

            print("\n")

        broker.unwatch_all()
        print("Integration test passed!")
