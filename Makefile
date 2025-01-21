
docker:
	docker build -t psmqtt:latest .

# NOTE: during integration-tests the "testcontainers" project will be used to spin up 
#       both a Mosquitto broker and the rpi2home-assistant docker, so make sure you don't
#       have a Mosquitto broker (or other containers) already listening on the 1883 port
#       when using this target:
integration-test:
ifeq ($(REGEX),)
	pytest -vvvv --log-level=INFO -s -m integration
else
	pytest -vvvv --log-level=INFO -s -m integration -k $(REGEX)
endif
