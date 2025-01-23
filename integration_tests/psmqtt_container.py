# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import os
import shutil
import tempfile
from testcontainers.core.container import DockerContainer
from testcontainers.mqtt import MosquittoContainer

class PSMQTTContainer(DockerContainer):
    """
    Specialization of DockerContainer to test PSMQTT docker image
    """

    CONFIG_FILE = "integration-tests-psmqtt.yaml"

    def __init__(self, broker: MosquittoContainer) -> None:
        super().__init__(image="psmqtt:latest")

        # IMPORTANT: to link with the MQTT broker we want to use the IP address internal to the docker network,
        #            and the standard MQTT port. The localhost:exposed_port address is not reachable from a
        #            docker container that has been started inside a docker network!
        broker_container = broker.get_wrapped_container()
        broker_ip = broker.get_docker_client().bridge_ip(broker_container.id)
        broker_port = MosquittoContainer.MQTT_PORT
        print(f"Linking the {self.image} container with the MQTT broker at host:ip {broker_ip}:{broker_port}")
        config_file = self._prepare_config_file(broker_ip, broker_port)

        # bind-mount the generated, transient, config file to the standard location of config file within PSMQTT container
        self.with_volume_mapping(config_file, "/opt/psmqtt/conf/psmqtt.yaml", mode="ro")

    def _prepare_config_file(self, broker_ip: str, broker_port: int):
        TEST_DIR = os.path.dirname(os.path.abspath(__file__))
        original_cfgfile = os.path.join(TEST_DIR, self.CONFIG_FILE)

        temp_cfgfile = os.path.join(tempfile.mkdtemp(), self.CONFIG_FILE)
        shutil.copy(original_cfgfile, temp_cfgfile)

        with open(temp_cfgfile, 'r+') as f:  # Open for reading and writing
            content = f.read()
            original = content
            content = content.replace("__MQTT_BROKER_IP_PLACEHOLDER__", broker_ip)
            content = content.replace("__MQTT_BROKER_PORT_PLACEHOLDER__", f"{broker_port}")

            if original != content:
                f.seek(0)  # Rewind to the beginning
                f.write(content)
                f.truncate()  # Remove any remaining old content
            else:
                raise ValueError("Failed to replace placeholders in the configuration file")

        print(f"Prepared configuration file '{temp_cfgfile}' for use in integration tests")
        return temp_cfgfile

    def is_running(self):
        self.get_wrapped_container().reload()  # force refresh of container status
        # status = self.get_wrapped_container().attrs["State"]['Status']
        status = self.get_wrapped_container().status  # same as above
        return status == "running"

    def get_short_id(self):
        # the docker container ID is a long string, the "short ID" is just the first 12 characters
        return self.get_wrapped_container().id[:12]

    def print_logs(self) -> str:
        print("** psmqtt LOGS [STDOUT]:")
        print(self.get_logs()[0].decode())
        print("** psmqtt LOGS [STDERR]:")
        print(self.get_logs()[1].decode())
