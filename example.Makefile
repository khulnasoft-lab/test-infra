############################################################
# Example Makefile for showing usage of the KhulnaSoft Local
# CI/Test Harness.
############################################################


# Make environment configuration
#############################################

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help # Running make without args will run the help target
.NOTPARALLEL: # Run make serially

# Dockerhub image repo
DEV_IMAGE_REPO = [your image repo]-dev

# Shared CI scripts
TEST_HARNESS_REPO = https://github.com/khulnasoft-lab/test-infra.git
CI_CMD = khulnasoft-ci/ci_harness

# Python environment
VENV = .venv
ACTIVATE_VENV := . $(VENV)/bin/activate
PYTHON := $(VENV)/bin/python3

# Testing configs
CI_COMPOSE_FILE = scripts/ci/docker-compose-ci.yaml
CLUSTER_CONFIG = tests/e2e/kind-config.yaml
CLUSTER_NAME = e2e-testing
K8S_VERSION = 1.15.7
TEST_IMAGE_NAME = $(GIT_REPO):dev


#### CircleCI environment variables
# exported variables are made available to any process called by this Makefile
############################################################

# declared in .circleci/config.yaml
export LATEST_RELEASE_MAJOR_VERSION ?=
export PROD_IMAGE_REPO ?=

# declared in CircleCI contexts
export DOCKER_USER ?=
export DOCKER_PASS ?=

# declared in CircleCI project environment variables settings
export REDHAT_PASS ?=
export REDHAT_REGISTRY ?=

# automatically set to 'true' by CircleCI runners
export CI ?= false

# Use $CIRCLE_BRANCH if it's set, otherwise use current HEAD branch
GIT_BRANCH := $(shell echo $${CIRCLE_BRANCH:=$$(git rev-parse --abbrev-ref HEAD)})

# Use $CIRCLE_PROJECT_REPONAME if it's set, otherwise the git project top level dir name
GIT_REPO := $(shell echo $${CIRCLE_PROJECT_REPONAME:=$$(basename `git rev-parse --show-toplevel`)})

# Use $CIRCLE_SHA if it's set, otherwise use SHA from HEAD
COMMIT_SHA := $(shell echo $${CIRCLE_SHA:=$$(git rev-parse HEAD)})

# Use $CIRCLE_TAG if it's set, otherwise set to null
GIT_TAG := $(shell echo $${CIRCLE_TAG:=null})


#### Make targets
############################################################

.PHONY: ci build deps install install-dev
.PHONY: lint clean clean-all test
.PHONY: test-unit test-integration test-functional test-cli
.PHONY: setup-and-test-e2e setup-e2e-tests test-e2e
.PHONY: push-dev push-rc push-prod push-rebuild push-redhat
.PHONY: compose-up compose-down cluster-up cluster-down
.PHONYT: setup-test-infra venv printvars help

ci: lint build test push-dev ## Run full CI pipeline, locally

build: Dockerfile venv setup-test-infra ## Build dev image
	@$(CI_CMD) build "$(COMMIT_SHA)" "$(GIT_REPO)" "$(TEST_IMAGE_NAME)"

deps: ## Sync dependent git submodules
	git submodule sync
	git submodule update --init

install: deps venv setup.py requirements.txt ## Install to virtual environment
	$(ACTIVATE_VENV) && pip install deps/khulnasoft-engine
	$(ACTIVATE_VENV) && pip install .

install-dev: deps venv setup.py requirements.txt ## Install to virtual environment in editable mode
	$(ACTIVATE_VENV) && pip install deps/khulnasoft-engine
	$(ACTIVATE_VENV) && pip install --editable .

lint: venv setup-test-infra ## Lint code (pylint)
	@$(ACTIVATE_VENV) && $(CI_CMD) lint

clean: ## Clean everything (with prompts)
	@$(CI_CMD) clean "$(VENV)" "$(TEST_IMAGE_NAME)"

clean-all: export NOPROMPT = true
clean-all: ## Clean everything (without prompts)
	@$(CI_CMD) clean "$(VENV)" "$(TEST_IMAGE_NAME)" $(NOPROMPT)


# Testing targets
######################

test: test-unit test-integration setup-and-test-functional setup-and-test-e2e ## Run unit, integration, functional, and end-to-end tests

test-unit: export TOX_ENV = py36 ## Run unit tests (tox)
test-unit: venv setup-test-infra
	@$(ACTIVATE_VENV) && $(CI_CMD) test-unit

test-integration: venv setup-test-infra ## Run integration tests (tox)
	@$(ACTIVATE_VENV) && $(CI_CMD) test-integration

test-functional: venv setup-test-infra ## Run functional tests, assuming compose is running
	@$(ACTIVATE_VENV) && $(CI_CMD) test-functional

setup-and-test-functional: venv setup-test-infra ## Stand up/start docker-compose, run functional tests, tear down/stop docker-compose
	@$(MAKE) compose-up
	@$(MAKE) test-functional
	@$(MAKE) compose-down

test-cli: setup-test-infra venv ## Run cli-driven end to end tests (assuming cluster is running and set up has been run)
	@$(ACTIVATE_VENV) && $(PYTHON) -m pip install faker && $(PYTHON) khulnasoft-ci/cli_driver.py

setup-e2e-tests: setup-test-infra venv ## Start kind cluster and set up end to end tests
	@$(MAKE) cluster-up
	@$(ACTIVATE_VENV) && $(CI_CMD) setup-e2e-tests "$(CLUSTER_NAME)" "$(COMMIT_SHA)" "$(DEV_IMAGE_REPO)" "$(GIT_BRANCH)" "$(GIT_REPO)" "$(GIT_TAG)" "$(TEST_IMAGE_NAME)"

test-e2e: setup-test-infra venv ## Run end to end tests (assuming cluster is running and set up has been run)
	@$(ACTIVATE_VENV) && $(CI_CMD) test-e2e

setup-and-test-e2e: setup-test-infra venv ## Set up and run end to end tests
	@$(MAKE) setup-e2e-tests
	@$(MAKE) test-e2e
	@$(MAKE) cluster-down


# Release targets
######################

push-dev: setup-test-infra ## Push dev KhulnaSoft Enterprise Docker image to Docker Hub
	@$(CI_CMD) push-dev-image "$(COMMIT_SHA)" "$(DEV_IMAGE_REPO)" "$(GIT_BRANCH)" "$(TEST_IMAGE_NAME)"

push-rc: setup-test-infra ## (Not available outside of CI) Push RC KhulnaSoft Enterprise Docker image to Docker Hub
	@$(CI_CMD) push-rc-image "$(COMMIT_SHA)" "$(DEV_IMAGE_REPO)" "$(GIT_TAG)"

push-prod: setup-test-infra ## (Not available outside of CI) Push release KhulnaSoft Enterprise Docker image to Docker Hub
	@$(CI_CMD) push-prod-image-release "$(DEV_IMAGE_REPO)" "$(GIT_BRANCH)" "$(GIT_TAG)"

push-redhat: setup-test-infra ## (Not available outside of CI) Push prod KhulnaSoft Enterprise docker image to RedHat Connect
	@$(CI_CMD) push-redhat-image "$(GIT_TAG)"

push-rebuild: setup-test-infra ## (Not available outside of CI) Rebuild and push prod KhulnaSoft Enterprise docker image to Docker Hub
	@$(CI_CMD) push-prod-image-rebuild "$(COMMIT_SHA)" "$(DEV_IMAGE_REPO)" "$(GIT_TAG)"


# Helper targets
####################

compose-up: venv setup-test-infra ## Stand up/start docker-compose with dev image
	@$(ACTIVATE_VENV) && $(CI_CMD) compose-up "$(TEST_IMAGE_NAME)" "${CI_COMPOSE_FILE}"

compose-down: venv setup-test-infra ## Tear down/stop docker compose
	@$(ACTIVATE_VENV) && $(CI_CMD) compose-down "$(TEST_IMAGE_NAME)" "${CI_COMPOSE_FILE}"

cluster-up: setup-test-infra venv ## Set up and run kind cluster
	@$(CI_CMD) install-cluster-deps "$(VENV)"
	@$(ACTIVATE_VENV) && $(CI_CMD) cluster-up "$(CLUSTER_NAME)" "$(CLUSTER_CONFIG)" "$(K8S_VERSION)"

cluster-down: setup-test-infra venv ## Tear down/stop kind cluster
	@$(ACTIVATE_VENV) && $(CI_CMD) cluster-down "$(CLUSTER_NAME)"

setup-test-infra: /tmp/test-infra ## Fetch khulnasoft-lab/test-infra repo for CI scripts
	cd /tmp/test-infra && git pull
	@$(MAKE) khulnasoft-ci
khulnasoft-ci: /tmp/test-infra/khulnasoft-ci
	rm -rf ./khulnasoft-ci; cp -R /tmp/test-infra/khulnasoft-ci .
/tmp/test-infra/khulnasoft-ci: /tmp/test-infra
/tmp/test-infra:
	git clone $(TEST_HARNESS_REPO) /tmp/test-infra

venv: $(VENV)/bin/activate ## Set up a virtual environment
$(VENV)/bin/activate:
	python3 -m venv $(VENV)

printvars: ## Print make variables
	@$(foreach V,$(sort $(.VARIABLES)),$(if $(filter-out environment% default automatic,$(origin $V)),$(warning $V=$($V) ($(value $V)))))

help:
	@printf "\n%s\n\n" "usage: make <target>"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;36m%-30s\033[0m %s\n", $$1, $$2}'
