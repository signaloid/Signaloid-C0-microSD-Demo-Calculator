# Signaloid SoC application
This directory holds the application that runs in the Signaloid C0-microSD.

## Build the application using the Signaloid API
You can build the application via the Signaloid API using the `core_downloader` module which you can find in the [C0-microSD-utilities](https://github.com/signaloid/C0-microSD-utilities) repository (which is also a submodule of this repository).

1. Create a new API key in the Signlaloid Cloud Development Platform (see [here](https://docs.signaloid.io/docs/api/quickstart/#authenticating)).
2. Make sure you have the `requests` python package installed. You can create a virtual environment and install the package with the following commands:
   ```bash
   python -m venv .env
   source .env/bin/activate
   pip install requests
   ```
3. Go to the top-level directory of the `C0-microSD-utilities` repository and run the following:
   ```bash
   python -m src.python.signaloid_api.core_downloader --api-key <YOUR_API_KEY> --repo-url https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator
   ```

If the application builds succesfully you will get a `buildArtifacts.tar.gz` archive, which includes a binary (`main.bin`) that you can flash to the C0-microSD. We have already included the [binary](main.bin) to this repository. You can find more details on how the `core_downloader` module works [here](https://github.com/signaloid/C0-microSD-utilities/blob/main/src/python/signaloid_api/README.md).

## How to flash
1. Modify the `DEVICE` flag in the `Makefile` to point to your C0-microSD device path.
2. Run `make flash` and `make switch` (the green LED should blink).
3. Power cycle the C0-microSD (the green LED should light up).
