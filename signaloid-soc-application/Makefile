# Root directory variables
MAKEFILE_PATH 		:= $(abspath $(firstword $(MAKEFILE_LIST)))
MAKEFILE_DIR 		:= $(abspath $(dir $(MAKEFILE_PATH)))
ROOT_DIR 		:= $(abspath $(MAKEFILE_DIR)/..)

# Name of the program
PROGRAM			= main

# Flash variables
TOOLKIT			= python3 $(ROOT_DIR)/submodules/C0-microSD-utilities/C0_microSD_toolkit.py
DEVICE			= /dev/disk4


# Build binaries using the Signaloid Cloud Engine API
# More information here:
# https://github.com/signaloid/C0-microSD-utilities/tree/main/src/python/signaloid_api

# The Signaloid Cloud Engine API key to use when building.
# Generate yours at https://signaloid.io/settings/api
API_KEY			= <your-signaloid-cloud-engine-api-key>

# The repository url to use when building with the Signaloid Cloud Engine API.
# It currently uses the remote origin url configured in this local git repo.
# If this is not a git repo, then please update this to a valid repository url.
REPO_URL		= $(shell git config --get remote.origin.url | sed 's;git@github.com:;https:\/\/github.com/;g' | sed 's;\.git;;g')

# Available core configurations [C0-microSD-XS, C0-microSD-XS+, C0-microSD-N, C0-microSD-N+]
CORE_CONFIGURATION	= C0-microSD-N

# Signaloid API Core Downloader toolkit
SIGNALOID_API_DIR	= $(ROOT_DIR)/submodules/C0-microSD-utilities/src/python/signaloid_api
SIGNALOID_API_TOOLKIT	= python3 $(SIGNALOID_API_DIR)/core_downloader.py
VENV			= $(SIGNALOID_API_DIR)/.venv

# Directory containing the build files
BUILD_DIRECTORY		= signaloid-soc-application

# Build artifacts directory and naming
BUILD_OUTPUT_DIR	= $(MAKEFILE_DIR)/dist
TIMESTAMP		= $(shell date +'%Y%m%d_%H%M%S')
BUILD_NAME		= buildArtifacts_$(TIMESTAMP).tar.gz
BUILD_OUTPUT		= $(BUILD_OUTPUT_DIR)/$(BUILD_NAME)

flash: $(PROGRAM).bin
	sudo $(TOOLKIT) -t $(DEVICE) -b $(PROGRAM).bin -u -p 128K

switch:
	sudo $(TOOLKIT) -t $(DEVICE) -s

$(VENV):
	@python3 -m venv $(VENV)
	@. $(VENV)/bin/activate && \
	pip3 install -r $(SIGNALOID_API_DIR)/requirements.txt

build: $(VENV)
	@mkdir -p $(BUILD_OUTPUT_DIR)
	@. $(VENV)/bin/activate && \
	$(SIGNALOID_API_TOOLKIT) \
		--api-key=$(API_KEY) \
		--repo-url=$(REPO_URL) \
		--output=$(BUILD_OUTPUT) \
		--build-directory=$(BUILD_DIRECTORY)
	@tar -xf $(BUILD_OUTPUT) -C $(BUILD_OUTPUT_DIR)
	@mv $(BUILD_OUTPUT_DIR)/$(BUILD_DIRECTORY)/$(PROGRAM).bin .

clean:
	@rm -rf $(BUILD_OUTPUT_DIR) main.bin
