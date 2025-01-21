import pytest
import time

# from testcontainers.core.utils import raise_for_deprecated_parameter

from integration_tests.psmqtt_container import PSMQTTContainer
from testcontainers.mqtt import MosquittoContainer


@pytest.mark.integration
def test_mqtt_reconnection():

    broker = MosquittoContainer()
    broker.start()
    with PSMQTTContainer(broker) as container:
        time.sleep(1)  # give time to the PSMQTTContainer to fully start
        if not container.is_running():
            print("Container under test has stopped running while broker was still running?? test failed.")
            container.print_logs()
            assert False

        for attempt in range(1, 3):
            # BAM! stop the broker to simulate either a maintainance window or a power fault in the system where MQTT broker runs
            print(f"Attempt #{attempt}: Simulating BROKER failure stopping the broker container...")
            broker.stop()
            time.sleep(0.5)
            if not container.is_running():
                print("Container under test has stopped running immediately after stopping the broker... test failed.")
                container.print_logs()
                assert False

            # NOTE: MQTT_DEFAULT_RECONNECTION_PERIOD_SEC is equal 1sec
            for idx in range(1, 3):
                time.sleep(1.5)
                if not container.is_running():
                    print(
                        "Container under test has stopped running probably after retrying the connection to the broker... test failed."
                    )
                    container.print_logs()
                    assert False

            # ok seems the container is still up -- that's good -- now let's see if it can reconnect
            print(f"Attempt #{attempt}: About to restart the broker...")
            try:
                broker.start()
            except Exception as e:
                print(e)
                assert False

            #topics_under_test = ["rpi2home-assistant/opto_input_1"]
            #broker.watch_topics(topics_under_test)

            for idx in range(1, 3):
                time.sleep(1.5)
                if not container.is_running():
                    print(
                        "Container under test has stopped running probably after retrying the connection to the broker... test failed."
                    )
                    container.print_logs()
                    assert False

            # now verify that there is also traffic on the topics:
            # time.sleep(4)
            #msg_rate = broker.get_message_rate_in_watched_topic(topics_under_test[0])
            #assert msg_rate > 0
            print("Looks like PSMQTT container is still up and running... proceeding")

        print("Test passed. Container logs should indicate several attempts to reconnect:")
        container.print_logs()

    broker.stop()
