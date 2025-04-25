#   Copyright (c) 2024, Signaloid.
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

import argparse
import sys
import struct
import signal
import time
import matplotlib.pyplot as plt
from c0microsd.interface import C0microSDSignaloidSoCInterface
from signaloid.distributional import DistributionalValue
from signaloid.distributional_information_plotting.plot_wrapper import plot
from typing import Optional, Union
import numpy as np

kSignaloidC0StatusWaitingForCommand = 0
kSignaloidC0StatusCalculating = 1
kSignaloidC0StatusDone = 2
kSignaloidC0StatusInvalidCommand = 3

kCalculateNoCommand = 0
kCalculateAddition = 1
kCalculateSubtraction = 2
kCalculateMultiplication = 3
kCalculateDivision = 4
kCalculateSample = 5

calculation_commands = {
    "add": kCalculateAddition,
    "sub": kCalculateSubtraction,
    "mul": kCalculateMultiplication,
    "div": kCalculateDivision,
    "sample": kCalculateSample,
}


def sigint_handler(signal, frame):
    plt.close()
    sys.exit(0)


# Function to pack floats into a byte buffer
def pack_floats(floats: list, size: int) -> bytes:
    """
    Pack a list of floats to a zero-padded bytes buffer of length size

    :param floats: List of floats to be packed
    :param size: Size of target buffer

    :return: The padded bytes buffer
    """
    buffer = struct.pack(f"{len(floats)}f", *floats)

    # Pad the buffer with zeros
    if len(buffer) < size:
        buffer += bytes(size - len(buffer))
    elif len(buffer) > size:
        raise ValueError(
            f"Buffer length exceeds {size} bytes after packing floats."
        )
    return buffer


def unpack_floats(byte_buffer: bytes, count: int) -> list[float]:
    """
    This function unpacks 'count' number of single-precision floating-point
    numbers from the given byte buffer. It checks if the buffer has enough
    data to unpack.

    Parameters:
        byte_buffer: A bytes object containing the binary data.
        count: The number of single-precision floats to unpack.

    Returns:
        A list of unpacked float values.
    """

    # Each float (single-precision float) is 4 bytes
    float_size = 4

    # Check if the buffer has enough bytes to unpack the requested
    # number of floats
    expected_size = float_size * count
    if len(byte_buffer) < expected_size:
        raise ValueError(
            f"Buffer too small: expected at least {expected_size} bytes, \
                got {len(byte_buffer)} bytes.")

    # Unpack the 'count' number of floats ('f' format for float in struct)
    format_string = f'{count}f'
    floats = struct.unpack(format_string, byte_buffer[:expected_size])

    return list(floats)


# Function to pack unsigned into a byte buffer
def pack_unsigned_integers(uint: list, size: int) -> bytes:
    """
    Pack a list of unsigned integers to a zero-padded bytes
    buffer of length size

    :param uint: List of unsigned integers to be packed
    :param size: Size of target buffer

    :return: The padded bytes buffer
    """
    buffer = struct.pack(f"<{len(uint)}I", *uint)

    # Pad the buffer with zeros
    if len(buffer) < size:
        buffer += bytes(size - len(buffer))
    elif len(buffer) > size:
        raise ValueError(
            f"Buffer length exceeds {size} bytes after packing floats."
        )
    return buffer


def parse_tolerance_value(value_with_uncertainty):
    # Split the value and the uncertainty part
    if '(' not in value_with_uncertainty or ')' not in value_with_uncertainty:
        raise ValueError(
            "Invalid format. Please provide value in the format 'X.Y(Z)'")

    # Extract the main value and the uncertainty
    value_str, uncertainty_str = value_with_uncertainty.split('(')
    uncertainty_str = uncertainty_str.strip(')')

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
    min_value = value - (uncertainty * (10 ** order))
    max_value = value + (uncertainty * (10 ** order))

    return min_value, max_value


def parse_arguments():
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description='Host application for C0-microSD \
            calculator application'
    )

    parser.add_argument(
        'device_path',
        type=str,
        help='Path of C0-microSD',
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Subparser for "add" command (requires two uncertainty values)
    parser_add = subparsers.add_parser(
        'add',
        help='Add two uncertainty values'
    )
    parser_add.add_argument('argument_a', type=str, help='First argument')
    parser_add.add_argument('argument_b', type=str, help='Second argument')

    # Subparser for "sub" command (requires two uncertainty values)
    parser_sub = subparsers.add_parser(
        'sub',
        help='Subtract two uncertainty values'
    )
    parser_sub.add_argument('argument_a', type=str, help='First argument')
    parser_sub.add_argument('argument_b', type=str, help='Second argument')

    # Subparser for "mul" command (requires two uncertainty values)
    parser_mul = subparsers.add_parser(
        'mul',
        help='Multiply two uncertainty values'
    )
    parser_mul.add_argument('argument_a', type=str, help='First argument')
    parser_mul.add_argument('argument_b', type=str, help='Second argument')

    # Subparser for "div" command (requires two uncertainty values)
    parser_div = subparsers.add_parser(
        'div',
        help='Divide two uncertainty values'
    )
    parser_div.add_argument('argument_a', type=str, help='First argument')
    parser_div.add_argument('argument_b', type=str, help='Second argument')

    # Subparser for "get" command (requires one positive integer argument)
    parser_sample = subparsers.add_parser(
        'sample',
        help='Get samples from example built-in distribution'
    )

    parser_sample.add_argument(
        'count',
        type=int,
        help='Sample count, maximum of 512 samples')

    parser.add_argument(
        "--benchmark",
        default=False,
        action="store_true",
        help="Enable benchmarking over 20 iterations"
    )

    # Parse the arguments
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_arguments()

    print("Available commands:")
    print("\tadd \tAdd two uncertainty values")
    print("\tsub \tSubtract two uncertainty values")
    print("\tmul \tMultiply two uncertainty values")
    print("\tdiv \tDivide two uncertainty values")
    print("\tsample \tGet samples from example "
          "built-in distribution\n")

    # Handle the commands and their arguments
    if args.command == 'add':
        print(f"Adding: {args.argument_a} and {args.argument_b}")
    elif args.command == 'sub':
        print(f"Subtracting: {args.argument_a} from {args.argument_b}")
    elif args.command == 'mul':
        print(f"Multiplying: {args.argument_a} by {args.argument_b}")
    elif args.command == 'div':
        print(f"Dividing: {args.argument_a} by {args.argument_b}")
    elif args.command == 'sample':
        if args.count <= 0 or args.count > 512:
            print("Error: The count argument must be a in the range [1, 512]")
        else:
            print("Sampling from example built-in distribution")
    else:
        print(
            "Invalid command. Please use 'add', 'sub', "
            "'mul', 'div', or 'sample'.")

    C0_microSD = C0microSDSignaloidSoCInterface(args.device_path)

    # Register the signal handler for SIGINT
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        C0_microSD.get_status()
        print(C0_microSD)

        if C0_microSD.configuration != "soc":
            raise RuntimeError(
                "Error: The C0-microSD is not in SoC mode. "
                "Switch to SoC mode and try again."
            )

        if args.command == "sample":
            C0_microSD.write_signaloid_soc_MOSI_buffer(
                pack_unsigned_integers(
                    [args.count],
                    C0_microSD.MOSI_BUFFER_SIZE_BYTES,
                )
            )

            print("Calculating command:")
            if args.benchmark:
                numIterations = 20
            else:
                numIterations = 1
            timings = []

            for i in range(numIterations):
                if args.benchmark:
                    print(f"Iteration: {i}")

                startTime = time.perf_counter()

                # Calculate result
                result_buffer = C0_microSD.calculate_command(
                    calculation_commands[args.command])

                endTime = time.perf_counter()
                iterationTime = endTime - startTime
                timings.append(iterationTime)

            if args.benchmark:
                meanTime = sum(timings) / numIterations
                print(f"Mean execution time over {numIterations} ",
                      f"iterations: {meanTime:.6f} seconds")

            # Unpack samples
            samples = unpack_floats(result_buffer, args.count)
            print("Samples:")
            for i in range(len(samples)):
                print(f"{i:>3}: {samples[i]}")

        else:
            # Parse inputs
            arg_a_min, arg_a_max = parse_tolerance_value(args.argument_a)
            arg_b_min, arg_b_max = parse_tolerance_value(args.argument_b)

            print("Sending parameters to C0-microSD...")
            C0_microSD.write_signaloid_soc_MOSI_buffer(
                pack_floats(
                    [arg_a_min, arg_a_max, arg_b_min, arg_b_max],
                    C0_microSD.MOSI_BUFFER_SIZE_BYTES,
                )
            )

            print("Calculating command:")
            if args.benchmark:
                numIterations = 20
            else:
                numIterations = 1
            timings = []

            for i in range(numIterations):
                if args.benchmark:
                    print(f"Iteration: {i}")

                startTime = time.perf_counter()

                # Calculate result
                result_buffer = C0_microSD.calculate_command(
                    calculation_commands[args.command])

                endTime = time.perf_counter()
                iterationTime = endTime - startTime
                timings.append(iterationTime)

            if args.benchmark:
                meanTime = sum(timings) / numIterations
                print(f"Mean execution time over {numIterations} ",
                      f"iterations: {meanTime:.6f} seconds")

            # Interpret and remove the first 4 bytes as an unsigned integer
            returned_bytes = struct.unpack("I", result_buffer[:4])[0]

            # Keep only needed bytes in buffer
            result_buffer = result_buffer[4:]
            result_buffer = result_buffer[:returned_bytes]

            distribution = DistributionalValue.parse(
                result_buffer, double_precision=False)

            override_params = {
                "figure.facecolor": "FFFFFF",
                "axes.facecolor": "FFFFFF"
            }

            print("Plotting distribution. Press Ctrl+C to exit.")
            plot(
                distribution,
                plotting_resolution=32,
                matplotlib_rc_params_override=override_params,
                x_label="Distribution Support",
                verbose=False,
            )
    except Exception as e:
        print(
            f"An error occurred while calculating: \n{e} \nAborting.",
            file=sys.stderr
        )
