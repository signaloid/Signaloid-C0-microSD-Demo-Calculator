# Siganaloid SoC application
This directory holds the application that runs in the Signaloid C0-microSD.

## How to flash
1. Modify the `DEVICE` flag in the `Makefile` to point to your C0-microSD device path.
2. Run `make flash` and `make switch` (the green LED should blink).
3. Power cycle the C0-microSD (the green LED should light up).
