# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import pytest
import time

from integration_tests.psmqtt_container import PSMQTTContainer
from integration_tests.mosquitto_container import MosquittoContainerEnhanced


@pytest.mark.integration
def test_mqtt_reconnection():

    broker = MosquittoContainerEnhanced()
    broker.start()
    with PSMQTTContainer(config_file="integration-tests-psmqtt1.yaml", broker=broker, loglevel="WARN") as container:
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

            for idx in range(1, 3):
                time.sleep(1.5)
                if not container.is_running():
                    print(
                        "Container under test has stopped running probably after retrying the connection to the broker... test failed."
                    )
                    container.print_logs()
                    assert False

            # FIXME: check psmqtt has restarted publishing data into the broker
            print("Looks like PSMQTT container is still up and running... proceeding")

        print("Test passed. Container logs should indicate several attempts to reconnect:")
        container.print_logs()

    broker.stop()
