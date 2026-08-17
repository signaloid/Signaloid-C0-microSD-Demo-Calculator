# Root directory variables
MAKEFILE_PATH       := $(abspath $(firstword $(MAKEFILE_LIST)))
MAKEFILE_DIR        := $(abspath $(dir $(MAKEFILE_PATH)))
ROOT_DIR            := $(abspath $(MAKEFILE_DIR))

# This is the path where your compute module is located (e.g. /dev/disk4).
# Can be overridden with `make DEVICE=<your-device> target...`.
DEVICE            ?= /dev/disk4

# This is the compute module hardware variant you are using.
# The supported options are:
#     - `SIGNALOID_C0_MICROSD`
#     - `SIGNALOID_C0_MICROSD_PLUS`
#     - `SIGNALOID_C0_SD`.
#
# Can be overridden with `make DEVICE_TYPE=<your-device-type> target...`.
DEVICE_TYPE         ?= SIGNALOID_C0_MICROSD_PLUS

PYTHON              := python3
VENV_DIR = $(ROOT_DIR)/.venv

SIGNALOID_CLI       := signaloid-cli


# Set variables based on DEVICE_TYPE
ifeq ($(DEVICE_TYPE),SIGNALOID_C0_MICROSD)
        # Signaloid C0-microSD core IDs
        CORE_ID_C0_microSD_N            := cor_271d544c73a8544d9026252652342972
        CORE_ID_C0_microSD_N_plus       := cor_c1cde893b0d75bb6a8941e9caf90f2a6
        CORE_ID_C0_microSD_XS           := cor_808bbbb9932c5d29a58370a1ec9a859f
        CORE_ID_C0_microSD_XS_plus      := cor_3d8dfc5d4f305e16b867716fe6aba1e9

        # Set the core ID to use for the build
        CORE_ID                         :=$(CORE_ID_C0_microSD_N)

        FLASH_TARGET                    := flash-C0-microSD
        DEVICE_VARIANT                  := C0-microSD
else ifeq ($(DEVICE_TYPE),SIGNALOID_C0_MICROSD_PLUS)
        # Signaloid C0-microSD+ core IDs
        CORE_ID_C0_microSD_plus_N       := cor_1faf6bb2d7d5522ea7fa8d0abb5f8287
        CORE_ID_C0_microSD_plus_N_plus  := cor_47178d2437f95276961d2b1311f6efb7
        CORE_ID_C0_microSD_plus_XS      := cor_fec16af93c525850a49abe6ddbe9a434
        CORE_ID_C0_microSD_plus_XS_plus := cor_28cfadb7a9535ddf9dffbdeaa41b0f20
        CORE_ID_C0_microSD_plus_S       := cor_b4bca7fa91c95e17bba1c210d2485eb1
        CORE_ID_C0_microSD_plus_S_plus  := cor_b3d7e24ecca45da7b3752304e1230f02

        # Set the core ID to use for the build
        CORE_ID                         := $(CORE_ID_C0_microSD_plus_N)

        FLASH_TARGET                    := flash-C0-microSD-Plus
        DEVICE_VARIANT                  := C0-microSD+
else ifeq ($(DEVICE_TYPE),SIGNALOID_C0_SD)
        # Signaloid C0-SD core IDs
        CORE_ID_C0_SD_N                 := cor_619f4edfb5105bb39dd50c115c2796d2
        CORE_ID_C0_SD_N_plus            := cor_bc2312a696d356d3bab92ff5fbfe7520
        CORE_ID_C0_SD_XS                := cor_aeafaef723f156f898e5826c9c4631bf
        CORE_ID_C0_SD_XS_plus           := cor_ee31a158687a5c3c85f13f9000937ad2
        CORE_ID_C0_SD_S                 := cor_d446925a40fc53ec90b805c7cea736f9
        CORE_ID_C0_SD_S_plus            := cor_a378e7ea331e53ed83f760bbe2c6a04c

        # Set the core ID to use for the build
        CORE_ID                         := $(CORE_ID_C0_SD_N)

        FLASH_TARGET                    := flash-C0-SD
        DEVICE_VARIANT                  := C0-SD
else
        $(error "Invalid DEVICE_TYPE specified. Please set DEVICE_TYPE to one of: SIGNALOID_C0_MICROSD, SIGNALOID_C0_MICROSD_PLUS, SIGNALOID_C0_SD")
endif


# Repo URL and branch to build
REPO_URL            := $(shell git remote get-url origin | sed s,git@github.com:,https://github.com/,)
REPO_BRANCH         := $(shell git branch --show-current)

# Signaloid-Compute-Module-Utilities submodule directory
UTILITIES_DIR       := $(ROOT_DIR)/submodules/Signaloid-Compute-Module-Utilities

# Build directory
BUILD_DIR           := signaloid-soc-application

REPO_ID_FILE        := $(ROOT_DIR)/.repo_id
REPO_ID=$(shell cat $(REPO_ID_FILE))

BUILD_ID_FILE       := $(ROOT_DIR)/.build_id
BUILD_ID=$(shell cat $(BUILD_ID_FILE))

BINARY_FILENAME      = $(BUILD_ID).main.bin
BINARY_FILE          = $(ROOT_DIR)/$(BUILD_DIR)/$(BINARY_FILENAME)

# Enable Global "Exit on Error" for shell commands
.SHELLFLAGS         := -ec

all: download

print-%  : ; @echo $* = $($*)

# Search for the repo in Signaloid Cloud Developer Platform.
# If it doesn't exist, connect it.
connect $(REPO_ID_FILE):
	@RESPONSE=$$($(SIGNALOID_CLI) repos lookup \
		--url $(REPO_URL) \
		--branch $(REPO_BRANCH)); \
	REPO_ID=$$(echo $$RESPONSE | jq -r '.RepositoryID'); \
	if [ "$$REPO_ID" = "null" ]; then \
		RESPONSE=$$($(SIGNALOID_CLI) repos connect \
			--url $(REPO_URL) \
			--branch $(REPO_BRANCH) \
			--dir $(BUILD_DIR) \
			--core-id $(CORE_ID)); \
		REPO_ID=$$(echo $$RESPONSE | jq -r '.RepositoryID'); \
	fi; \
	echo $$REPO_ID > $(REPO_ID_FILE)

# Update an already connected repo:
#  - Update branch and fetch latest commit
#  - Update build directory
#  - Update selected Core ID
update: $(REPO_ID_FILE)
	@RESPONSE=$$($(SIGNALOID_CLI) repos update \
		--repo-id $(REPO_ID) \
		--branch $(REPO_BRANCH) \
		--dir $(BUILD_DIR) \
		--core-id $(CORE_ID))

# Create a build for the repo
build $(BUILD_ID_FILE): $(REPO_ID_FILE)
	@RESPONSE=$$($(SIGNALOID_CLI) builds create:repo --repo-id $(REPO_ID)); \
	BUILD_ID=$$(echo $$RESPONSE | jq -r '.BuildID'); \
	echo $$BUILD_ID > $(BUILD_ID_FILE); \
	$(SIGNALOID_CLI) builds watch --build-id $$BUILD_ID; \
	$(SIGNALOID_CLI) builds output --build-id $$BUILD_ID;

# Download the build binary
download $(BINARY_FILE): $(BUILD_ID_FILE)
	@$(SIGNALOID_CLI) builds binary \
		--build-id $(BUILD_ID) \
		--out $(BUILD_DIR) \
		--filename $(BINARY_FILENAME)

# Delete the build id and its binary
clean:
	@$(RM) $(BINARY_FILE)
	@$(RM) $(BUILD_ID_FILE)

# Delete the build id, its binary, and the connected repo id
clean-all: clean
	@$(RM) $(REPO_ID_FILE)

# Flashing targets
flash: $(FLASH_TARGET)

flash-C0-microSD: $(BINARY_FILE)
	@echo "\n- Flashing: Signaloid C0-microSD [$(DEVICE)]"
	@file_size=$$(ls -l $(BINARY_FILE) | awk '{print $$5}'); \
	if [ "$${file_size}" -gt 131072 ]; then \
		echo "Error: Binary file is too large ($$file_size bytes)."; \
		exit 1; \
	fi
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_microSD_toolkit.py -t $(DEVICE) -b $(BINARY_FILE) -U -p 128K

flash-C0-microSD-Plus: $(BINARY_FILE) stop
	@echo "\n- Flashing: Signaloid C0-microSD+ [$(DEVICE)]"
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_SD_toolkit.py --variant=$(DEVICE_VARIANT) $(DEVICE) flash-application $(BINARY_FILE)

flash-C0-SD: $(BINARY_FILE) stop
	@echo "\n- Flashing: Signaloid C0-SD [$(DEVICE)]"
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_SD_toolkit.py --variant=$(DEVICE_VARIANT) $(DEVICE) flash-application $(BINARY_FILE)

# Switch mode (Bootloader - Signaloid SoC) of the C0-microSD
switch:
	@echo "\n- Switching: Signaloid C0-microSD [$(DEVICE)]"
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_microSD_toolkit.py -t $(DEVICE) -s

# Start the Signaloid SoC core
start:
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_SD_toolkit.py --variant=$(DEVICE_VARIANT) $(DEVICE) config core-start

# Stop the Signaloid SoC core
stop:
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_SD_toolkit.py --variant=$(DEVICE_VARIANT) $(DEVICE) config core-stop

# Reset the Signaloid SoC core
reset: stop start

# Print the compute module debug logs continuously
log:
	@sudo $(PYTHON) $(UTILITIES_DIR)/C0_debug_logger.py --variant=$(DEVICE_VARIANT) $(DEVICE)

# Create the virtual environment needed for running the host application
venv $(VENV_DIR):
	@echo "\n- Creating virtual environment in $(VENV_DIR)"
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(VENV_DIR)/bin/pip install --upgrade pip
	@$(VENV_DIR)/bin/pip install -r $(ROOT_DIR)/python-host-application/requirements.txt

# Base command to run the host application
RUN_CMD=sudo $(VENV_DIR)/bin/python3 -u $(ROOT_DIR)/python-host-application/host_application.py --device-path $(DEVICE) --variant $(DEVICE_VARIANT)

# Run all application commands. Useful for testing.
run-all: $(VENV_DIR)
	@echo "\n- Running the host application"
	$(RUN_CMD) add "2.0(5)" "5.0(3)"
	$(RUN_CMD) sub "2.0(5)" "5.0(3)"
	$(RUN_CMD) mul "2.0(5)" "5.0(3)"
	$(RUN_CMD) div "2.0(5)" "5.0(3)"
	$(RUN_CMD) sample --count 100

# Benchmark all application commands. Useful for testing.
bench-all: $(VENV_DIR)
	@echo "\n- Benchmarking"
	$(RUN_CMD) --benchmark --iterations 2000 add "2.0(5)" "5.0(3)"
	$(RUN_CMD) --benchmark --iterations 2000 sub "2.0(5)" "5.0(3)"
	$(RUN_CMD) --benchmark --iterations 2000 mul "2.0(5)" "5.0(3)"
	$(RUN_CMD) --benchmark --iterations 2000 div "2.0(5)" "5.0(3)"
	$(RUN_CMD) --benchmark --iterations 2000 sample --count 100
