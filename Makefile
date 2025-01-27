# Basic development targets

format:
	black .

lint:
	ruff check src/
	flake8 -v

docker:
	docker build -t psmqtt:latest .



# note that by using --network=host on the Mosquitto container, its default configuration
# will work out of the box (by default Mosquitto listens only local connections);
# and by using --network=host on the PSMQTT container, also the psmqtt default config
# pointing to "localhost" as MQTT broker will work fine:

docker-run:
	docker run -v $(shell pwd)/psmqtt.yaml:/opt/psmqtt/conf/psmqtt.yaml \
		--hostname $(shell hostname) \
		--network=host \
		psmqtt:latest $(ARGS)

docker-run-mosquitto:
	docker run -d --name=mosquitto --network=host eclipse-mosquitto:latest 


# to cross-build docker images for other platforms (e.g. ARM), the buildx image builder backend is required:

docker-armv6:
	docker buildx build --platform linux/arm/v6 --tag psmqtt:latest --build-arg USERNAME=root .

docker-armv7:
	docker buildx build --platform linux/arm/v7 --tag psmqtt:latest --build-arg USERNAME=root .

docker-arm64:
	docker buildx build --platform linux/arm64/v8 --tag psmqtt:latest --build-arg USERNAME=root .

test: unit-test integration-test

unit-test:
ifeq ($(REGEX),)
	pytest -vvv --log-level=INFO -m unit
else
	pytest -vvvv --log-level=INFO -s -m unit -k $(REGEX)
endif

# During integration-tests the "testcontainers" project will be used to spin up 
# both a Mosquitto broker and the PSMQTT docker, so make sure you don't
# have a Mosquitto broker (or other containers) already listening on the 1883 port
# when using this target:
integration-test:
ifeq ($(REGEX),)
	pytest -vvvv --log-level=INFO -s -m integration
else
	pytest -vvvv --log-level=INFO -s -m integration -k $(REGEX)
endif
