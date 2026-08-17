# Signaloid SoC application

This directory holds the firmware that runs on the Signaloid SoC inside the
compute module.

The firmware is built in the Signaloid Cloud Developer Platform. Use the targets
in the top-level [Makefile](../Makefile) to build, download, and flash it.

## Files

| File                   | Purpose                                                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| [main.c](main.c)       | Entry point. Polls the command register, dispatches to the selected command, and packs the results into the output buffer. |
| [config.mk](config.mk) | Build configuration. Selects the target device sources.                                                                    |

## Configuration

`config.mk` sets the sources for the selected `DEVICE_TYPE` and the Signaloid
Compute Module Utilities path.

Add your own compiler flags through the `BUILD_FLAGS` variable, and add your
sources and include paths on the `SOURCES` and `INC` variables respectively of
`config.mk`.
