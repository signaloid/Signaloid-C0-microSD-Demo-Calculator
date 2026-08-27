#   Copyright (c) 2026, Signaloid.
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the "Software"),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.


"""
This is a set of frequently used helper functions, meant to simplify the
application logic.

Feel free to use, copy, modify or override any of them to better suit
your application's needs.
"""


import argparse
import math
import struct
import sys
import time
import types
from enum import IntEnum
from typing import Union

import matplotlib.pyplot as plt
from signaloid.distributional.dirac_delta import DiracDelta
from signaloid.distributional.distributional import DistributionalValue
from signaloid.distributional_information_plotting.plot_histogram_dirac_deltas import (
    PlotData,
)
from signaloid.distributional_information_plotting.plot_wrapper import plot
from signaloid_utilities.c0microsd.interface import (
    C0microSDSignaloidSoCInterface,
)
from signaloid_utilities.c0sd.interface import (
    C0microSDPlusInterface,
    C0SDBaseInterface,
    C0SDInterface,
)


# Definitions -----------------------------------------------------------------
SignaloidComputeModuleInterface = Union[
    C0microSDSignaloidSoCInterface,
    C0microSDPlusInterface,
    C0SDInterface,
]

INTERFACE_BY_VARIANT: dict[str, type[SignaloidComputeModuleInterface]] = {
    "C0-microSD": C0microSDSignaloidSoCInterface,
    "C0-microSD+": C0microSDPlusInterface,
    "C0-SD": C0SDInterface,
}


class C0Status(IntEnum):
    WaitingForCommand = 0
    Calculating = 1
    Done = 2
    InvalidCommand = 3


# Data packing/unpacking ------------------------------------------------------
def pack_floats(
    floats: list[float],
    size: int,
    double_precision: bool = False,
    padding: bool = False,
) -> bytes:
    """
    Pack a list of floats to a zero-padded bytes buffer of length size

    :param floats: List of floats to be packed
    :param size: Size of target buffer
    :param double_precision: If the floats are in double precision
        representation
    :param padding: Pad resulting buffer with zeros, filling it up to size.

    :return: The padded bytes buffer
    """

    format_str = f"<{len(floats)}{'d' if double_precision else 'f'}"
    buffer = struct.pack(format_str, *floats)

    if len(buffer) > size:
        raise ValueError(
            f"Buffer length exceeds {size} bytes after packing floats."
        )

    # Pad the buffer with zeros
    if padding and len(buffer) < size:
        buffer += bytes(size - len(buffer))

    return buffer


def unpack_floats(
    byte_buffer: bytes,
    count: int,
    double_precision: bool = False,
) -> list[int]:
    """
    This function unpacks 'count' number of single or double precision
    floating-point numbers from the given byte buffer. It checks if the
    buffer has enough data to unpack.

    :param byte_buffer: A bytes object containing the binary data.
    :param count: The number of floats to unpack.
    :param double_precision: If the floats are in double precision
        representation

    :return A list of unpacked floating-point values.
    """

    # 4 bytes for each single-precision float
    # 8 bytes for each double-precision float
    float_size = 8 if double_precision else 4

    # Check if the buffer has enough bytes to unpack the requested
    # number of floats
    expected_size = float_size * count
    if len(byte_buffer) < expected_size:
        raise ValueError(
            f"Buffer too small: expected at least {expected_size} bytes, "
            f"got {len(byte_buffer)} bytes."
        )

    # Unpack the 'count' number of floats
    format_string = f"<{count}{'d' if double_precision else 'f'}"
    floats = struct.unpack(format_string, byte_buffer[:expected_size])

    return list(floats)


def pack_unsigned_integers(
    uint: list[int],
    size: int,
    padding: bool = False,
) -> bytes:
    """
    Pack a list of unsigned integers to a zero-padded bytes
    buffer of length size

    :param uint: List of unsigned integers to be packed
    :param size: Size of target buffer
    :param padding: Pad resulting buffer with zeros, filling it up to size.

    :return: The padded bytes buffer
    """

    buffer = struct.pack(f"<{len(uint)}I", *uint)

    if len(buffer) > size:
        raise ValueError(
            f"Buffer length exceeds {size} bytes after packing unsigned \
                integers."
        )

    # Pad the buffer with zeros
    if padding and len(buffer) < size:
        buffer += bytes(size - len(buffer))

    return buffer


def parse_tolerance_value(
    value_with_uncertainty: str,
) -> tuple[float, float]:
    """
    Parse a uniform distribution, represented in the concise form of
    uncertainty notation, i.e., `X.Y(Z)`.
    Read more on:
    https://physics.nist.gov/cgi-bin/cuu/Info/Constants/definitions.html

    :param value_with_uncertainty: The `X.Y(Z)` formatted string value to parse
    :type value_with_uncertainty: str
    :raises ValueError: When the value does not conform to the formatting
    :return: A tuple with the minimum and maximum value of the uniform
        distribution
    :rtype: tuple[float, float]
    """

    # Split the value and the uncertainty part
    if "(" not in value_with_uncertainty or ")" not in value_with_uncertainty:
        raise ValueError(
            f"[Error] Cannot parse {value_with_uncertainty} as a uniform \
                distribution, represented in the concise form of uncertainty \
                notation. Please provide a value in the format 'X.Y(Z)'"
        )

    # Extract the main value and the uncertainty
    value_str, uncertainty_str = value_with_uncertainty.split("(")
    uncertainty_str = uncertainty_str.strip(")")

    # Find smallest order
    if "." in value_str:
        # Split at the decimal point
        _, decimal_part = value_str.split(".")
        order = -(len(decimal_part))
    else:
        order = 0

    # Convert to appropriate types
    value = float(value_str)
    uncertainty = int(uncertainty_str)

    # Calculate minimum and maximum values
    min_value = value - (uncertainty * (10**order))
    max_value = value + (uncertainty * (10**order))

    return min_value, max_value


# Compute module helpers ------------------------------------------------------
def init_compute_module(
    device_path: str,
    variant: str,
    timeout: float = 2.0,
    reset_on_launch: bool = True,
) -> SignaloidComputeModuleInterface:
    """
    Initializes the connected Signaloid compute module.

    Fetches the correct compute module interface class.
    Initializes the compute module object.

    Resets the compute module core if the `reset_on_launch` is set (only for
    the supported compute module variants).

    Waits for the compute module to get to the `WaitingForCommand` state,
    until the given timeout.
    """

    try:
        interface = INTERFACE_BY_VARIANT.get(variant)
        if interface is None:
            raise ValueError(
                f"Hardware variant: `{variant}` not supported."
            )

        compute_module = interface(device_path)
        if isinstance(compute_module, C0SDBaseInterface):
            if reset_on_launch:
                compute_module.reset_core(0.5)
            else:
                compute_module.apply_configure_action("core-start")

        start_time = time.time()
        status = None
        while status != C0Status.WaitingForCommand:
            if time.time() - start_time > timeout:
                raise RuntimeError("Error: Cannot start the device.")

            time.sleep(0.01)
            if isinstance(compute_module, C0microSDSignaloidSoCInterface):
                status = compute_module.get_signaloid_soc_status()
            else:
                status = compute_module.get_status()

    except Exception as e:
        sys.exit(
            f"\n[Error] An error occurred while initializing device: \n"
            f"{e}\n"
            f"Aborting.",
        )

    return compute_module


def deinit_compute_module(
    compute_module: SignaloidComputeModuleInterface,
) -> None:
    """
    Stops the compute module core.
    Only for the supported compute module variants.
    """

    if isinstance(compute_module, C0microSDPlusInterface):
        compute_module.apply_configure_action("core-stop")
        compute_module.apply_configure_action("sw-led-off")
        compute_module.apply_configure_action("red-led-off")
        compute_module.apply_configure_action("green-led-off")
        compute_module.apply_configure_action("blue-led-off")
    elif isinstance(compute_module, C0SDInterface):
        compute_module.apply_configure_action("core-stop")
        compute_module.apply_configure_action("sw-led-off")
        compute_module.apply_configure_action("green-led-off")


def send_command(
    compute_module: SignaloidComputeModuleInterface,
    command_value: int,
    verbose: bool = False,
) -> None:
    """
    Sends the command to the compute module and waits for the calculation
    to finish.
    """

    if isinstance(compute_module, C0microSDSignaloidSoCInterface):
        compute_module.calculate_command(
            command_value,
            poll_sleep_time=0.001,
            skip_MISO_read=True,
            verbose=verbose,
        )
    else:
        compute_module.calculate_command(
            command_value,
            poll_sleep_time=0.001,
            skip_MMIO_buffer_read=True,
            verbose=verbose,
        )


def run_and_get_results(
    compute_module: SignaloidComputeModuleInterface,
    command_value: int,
    input_buffer: bytes,
    stop_on_exit: bool = True,
    verbose: bool = False,
) -> bytes:
    """
    Sends the inputs, issues the command, then gets the results.
    """

    result_buffer = bytes()
    try:
        # Send the inputs
        compute_module.write_input_buffer(input_buffer)

        # Run the calculation
        send_command(
            compute_module=compute_module,
            command_value=command_value,
            verbose=verbose,
        )

        # Get the results
        result_buffer = compute_module.read_output_buffer()

    except Exception as e:
        sys.exit(
            f"\n[Error] An error occurred while calculating: \n"
            f"{e}\n"
            f"Aborting.",
        )

    finally:
        if stop_on_exit:
            deinit_compute_module(
                compute_module=compute_module,
            )

    return result_buffer


def create_input_buffer(
    values: list[str | int | float ],
    buffer_size: int,
    double_precision: bool = False,
) -> bytes:
    """
    Given a list of strings, it creates a byte buffer for the calculation's
    input data.

    Each string can be:
        - A float, e.g. "123.45"
        - A uniform distribution represented in the concise form of uncertainty
            notation `X.Y(Z)`, e.g. "3.3(2)"
            Read more:
                https://physics.nist.gov/cgi-bin/cuu/Info/Constants/definitions.html
        - A Ux-String, e.g. "0.785398Ux0400000000000000003FE921FB54442D18000000013FE921FB54442D188000000000000000"
            Read more:
                https://docs.signaloid.io/docs/uxhw-api/ux-data-format/

    Generated byte buffer format:
        - Number of values (uint32_t)                                 (4 bytes)
        - Number-of-values pairs of:
            - Size of value in bytes (uint32_t)                       (4 bytes)
            - Value (float or Ux-Binary)                  (size-of-value bytes)
    """

    input_buffer = bytes()
    input_buffer += struct.pack("<I", len(values))

    for arg in values:
        try:
            if isinstance(arg, int):
                value = arg
                value_bytes = struct.pack("<I", value)
                value_bytes_len = struct.pack("<I", len(value_bytes))
                input_buffer += value_bytes_len + value_bytes
            elif isinstance(arg, float):
                value = arg
                value_bytes = struct.pack("<f", value)
                value_bytes_len = struct.pack("<I", len(value_bytes))
                input_buffer += value_bytes_len + value_bytes
            elif isinstance(arg, str):
                if "Ux" in arg:
                    dist = DistributionalValue.parse(arg)
                    if dist is None:
                        raise ValueError(f"[Error] Cannot parse Ux-String: {arg}")

                    dist_bytes = bytes(dist)
                    dist_bytes_len = struct.pack("<I", len(dist_bytes))
                    input_buffer += dist_bytes_len + dist_bytes
                elif "(" in arg and ")" in arg:
                    min_value, max_value = parse_tolerance_value(arg)
                    dist = DistributionalValue(
                        particle_value=(max_value + min_value) / 2,
                        dirac_deltas=[
                            DiracDelta(position=min_value, mass=0.5),
                            DiracDelta(position=max_value, mass=0.5),
                        ],
                        double_precision=double_precision,
                    )

                    dist_bytes = bytes(dist)
                    dist_bytes_len = struct.pack("<I", len(dist_bytes))
                    input_buffer += dist_bytes_len + dist_bytes
                else:
                    value = float(arg)
                    value_bytes = struct.pack("<f", value)
                    value_bytes_len = struct.pack("<I", len(value_bytes))
                    input_buffer += value_bytes_len + value_bytes
        except ValueError as e:
            sys.exit(
                f"[Error] Invalid input value: {arg}.\n"
                f"{e}\n"
                f"Please provide either a float, a value with "
                f"uncertainty in the format 'X.Y(Z)', or a Ux-String."
            )

    if len(input_buffer) > buffer_size:
        sys.exit(
            f"[Error] Input buffer length exceeds {buffer_size} bytes after \
                packing inputs."
        )

    return input_buffer


# Result parsing --------------------------------------------------------------
def parse_output_buffer(
    buffer: bytes,
    expected_output_count: int | None = None,
    double_precision: bool = False,
) -> list[float | DistributionalValue]:
    """
    Parses the given byte buffer to a list of floats and Distributional values.

    Byte buffer format:
        - Number of values (uint32_t)                                 (4 bytes)
        - Number-of-values pairs of:
            - Size of value in bytes (uint32_t)                       (4 bytes)
            - Value (float or Ux-Binary)                  (size-of-value bytes)
    """

    returned_values_count = struct.unpack("<I", buffer[:4])[0]
    buffer = buffer[4:]
    if returned_values_count <= 0 or (
        expected_output_count is not None
        and returned_values_count != expected_output_count
    ):
        raise RuntimeError(f"Output buffer cannot be parsed. Return values count: {returned_values_count}, expected: {expected_output_count}")

    returned_values: list[float | DistributionalValue] = []
    for _ in range(returned_values_count):
        returned_bytes = struct.unpack("<I", buffer[:4])[0]
        buffer = buffer[4:]

        temp_buffer = buffer[:returned_bytes]
        buffer = buffer[returned_bytes:]

        value: float | DistributionalValue | None = None
        if returned_bytes == 4:
            value = struct.unpack("<f", temp_buffer)[0]
        else:
            value = DistributionalValue.parse(
                dist=temp_buffer,
                double_precision=double_precision,
            )

        if value is None:
            value = math.nan

        returned_values.append(value)

    return returned_values


def print_output_values(
    values: list[float | DistributionalValue],
    value_labels: list[str] | None = None,
    skip_printing: bool = False,
    skip_plotting: bool = False,
):
    """
    Given a list of floats and Distributional values, it prints the floats
    and Ux-Strings, and then plots the Distributional values.

    Use the `value_labels` parameter to print names for each value.

    Printing can be skipped using the `skip_printing` parameter.
    Plotting can be skipped using the `skip_plotting` parameter.
    """

    values_index_max_digits = len(str(len(values)))
    if value_labels is None:
        value_labels = []
        for i in range(len(values)):
            text = f"Output {i + 1:>{values_index_max_digits}}"
            value_labels.append(text)

    if len(values) != len(value_labels):
        raise RuntimeError("Values and labels count must match.")

    value_labels_max_digits: int = -1
    for label in value_labels:
        value_labels_max_digits = max(value_labels_max_digits, len(label))

    if not skip_printing:
        print("- Output values:")

    for i, val in enumerate(values):
        if not skip_printing:
            if isinstance(val, DistributionalValue):
                val_str = val.particle_value
            else:
                val_str = str(val)

            print(
                f"[{value_labels[i]:>{value_labels_max_digits}}]: {val_str}"
            )

        if isinstance(val, DistributionalValue):
            if skip_plotting:
                continue

            plot(
                plot_data=PlotData(dist=val),
                matplotlib_rc_params_override={
                    "figure.facecolor": "FFFFFF",
                    "axes.facecolor": "FFFFFF",
                },
                x_label=(
                    f"Distribution Support\n"
                    f"{value_labels[i]}"
                ),
                verbose=False,
            )


# Argument parsing ------------------------------------------------------------
def compute_module_args(
    parser: argparse.ArgumentParser,
) -> None:
    """
    Default command line arguments for the compute modules. Useful for most
    applications.
    """

    parser.add_argument(
        "-d",
        "--device-path",
        type=str,
        help="Path of the C0 compute module device (e.g., /dev/disk4)",
        required=True,
    )

    parser.add_argument(
        "-v",
        "--variant",
        type=str,
        choices=INTERFACE_BY_VARIANT.keys(),
        default="C0-microSD+",
        help="Hardware variant (default: C0-microSD+)",
        required=False,
    )

    parser.add_argument(
        "-r",
        "--reset-on-launch",
        action="store_true",
        help="Reset the core on launch. Ignored on the C0-microSD.",
        default=False,
    )

    parser.add_argument(
        "-s",
        "--stop-on-exit",
        action="store_true",
        help="Stop the core on exit. Ignored on the C0-microSD.",
        default=False,
    )


def parse_arguments(
    explicit_args: list[str] | None = None, app_description: str = ""
):
    """
    Default command line argument parser. Only adds the compute module
    arguments. Useful for applications with no need for additional arguments.

    Feel free to copy and override this function for your application needs.
    """

    parser = argparse.ArgumentParser(description=app_description)

    compute_module_args(parser=parser)

    args = parser.parse_args(explicit_args)
    return args


# Misc ------------------------------------------------------------------------
def sigint_handler(
    signal: int,
    frame: types.FrameType | None,
):
    """
    Default SIGNINT handler for when exiting the application using Ctrl+C.

    Closes all open matplotlib plots.
    """

    plt.close()
    sys.exit(0)
