# psmqtt Makefile

#
# Python development targets:
#

format:
	black .

lint: lint-python lint-yaml lint-yaml-with-schema

lint-python:
	ruff check src/
	flake8 -v

build-wheel:
	python3 -m build --wheel --outdir dist/

test-wheel:
	rm -rf dist/ && \
 		pip3 uninstall -y psmqtt && \
		$(MAKE) build-wheel && \
		pip3 install dist/psmqtt-*-py3-none-any.whl

inspect-wheel:
	# see https://github.com/wheelodex/wheel-inspect
	wheel2json dist/psmqtt-*-py3-none-any.whl

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



#
# Config file helper targets
#

YAML_FILES:=\
	psmqtt.yaml \
	integration_tests/integration-tests-psmqtt1.yaml \
	integration_tests/integration-tests-psmqtt2-with-ha-discovery.yaml

lint-yaml:
	@for yfile in $(YAML_FILES); do \
		yq . -e $${yfile} >/dev/null && echo "Valid syntax for YAML file: $${yfile}" || ( echo "Invalid YAML file $${yfile}. Fix syntax." ; exit 2 ) \
	done

lint-yaml-with-schema:
	# use "pip install yamale" if you don't have the "yamale" CLI utility
	yamale -s src/psmqtt/schema/psmqtt.schema.yaml psmqtt.yaml 
	@# integration test file contains some placeholders that won't pass the validation:
	@#yamale -s schema/psmqtt.schema.yaml integration_tests/integration-tests-psmqtt.yaml

docker:
	docker build -t psmqtt:latest --build-arg USERNAME=root .


#
# Docker helper targets
#

# note that by using --network=host on the Mosquitto container, its default configuration
# will work out of the box (by default Mosquitto listens only local connections);
# and by using --network=host on the PSMQTT container, also the psmqtt default config
# pointing to "localhost" as MQTT broker will work fine:

ifeq ($(CFGFILE),)
CFGFILE:=$(shell pwd)/psmqtt.yaml
endif

docker-run:
	docker run -v $(CFGFILE):/opt/psmqtt/conf/psmqtt.yaml \
		--hostname $(shell hostname) \
		--network=host \
		psmqtt:latest $(ARGS)

docker-run-mosquitto:
	docker container stop mosquitto || true
	docker container rm mosquitto || true
	docker run -d --name=mosquitto --network=host eclipse-mosquitto:latest 


# to cross-build docker images for other platforms (e.g. ARM), the buildx image builder backend is required:

docker-armv6:
	docker buildx build --platform linux/arm/v6 --tag psmqtt:latest --build-arg USERNAME=root .

docker-armv7:
	docker buildx build --platform linux/arm/v7 --tag psmqtt:latest --build-arg USERNAME=root .

docker-arm64:
	docker buildx build --platform linux/arm64/v8 --tag psmqtt:latest --build-arg USERNAME=root .
