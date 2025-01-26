# Basic development targets

format:
	black .

lint:
	ruff check src/
	flake8 -v

docker:
	docker build -t psmqtt:latest .

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
