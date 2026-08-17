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


import argparse
import time
from enum import IntEnum

from app_helpers import (
    compute_module_args,
    init_compute_module,
    pack_floats,
    pack_unsigned_integers,
    parse_output_buffer,
    parse_tolerance_value,
    print_output_values,
    run_and_get_results,
    unpack_floats,
)
from tqdm import tqdm


# Command IDs supported by the SoC application.
# Keep these in sync with the SignaloidSoCCommand enum in
# signaloid-soc-application/main.c.
class Commands(IntEnum):
    CalculateNoCommand = 0
    add = 1
    sub = 2
    mul = 3
    div = 4
    sample = 5


def parse_arguments(
    explicit_args: list[str] | None = None,
):
    parser = argparse.ArgumentParser(
        description="Host application for the Signaloid C0 compute modules \
            calculator demo"
    )

    compute_module_args(parser=parser)

    subparsers = parser.add_subparsers(
        dest="command",
        help="Commands",
    )

    # Subparser for "add" command (requires two uncertainty values)
    parser_add = subparsers.add_parser(
        Commands.add.name,
        help="Add two uniform distributions X, Y",
    )
    parser_add.add_argument("argument_a", type=str, help="First argument")
    parser_add.add_argument("argument_b", type=str, help="Second argument")

    # Subparser for "sub" command (requires two uncertainty values)
    parser_sub = subparsers.add_parser(
        Commands.sub.name, help="Subtract two uniform distributions X, Y"
    )
    parser_sub.add_argument("argument_a", type=str, help="First argument")
    parser_sub.add_argument("argument_b", type=str, help="Second argument")

    # Subparser for "mul" command (requires two uniform distributions X, Y)
    parser_mul = subparsers.add_parser(
        Commands.mul.name, help="Multiply two uniform distributions X, Y"
    )
    parser_mul.add_argument("argument_a", type=str, help="First argument")
    parser_mul.add_argument("argument_b", type=str, help="Second argument")

    # Subparser for "div" command (requires two uniform distributions X, Y)
    parser_div = subparsers.add_parser(
        Commands.div.name, help="Divide two uniform distributions X, Y"
    )
    parser_div.add_argument("argument_a", type=str, help="First argument")
    parser_div.add_argument("argument_b", type=str, help="Second argument")

    # Subparser for "get" command (requires one positive integer argument)
    parser_sample = subparsers.add_parser(
        Commands.sample.name,
        help="Get samples from example built-in distribution",
    )
    parser_sample.add_argument(
        "--count",
        type=int,
        default=1,
        help="Sample count, maximum of 512 samples. Default: 1"
    )

    parser.add_argument(
        "--benchmark",
        default=False,
        action="store_true",
        help="Enable benchmarking",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=20,
        help="Benchmarking iterations. Default: 20",
    )

    args = parser.parse_args(explicit_args)
    return args


def main(explicit_args: list[str] | None = None):
    args = parse_arguments(explicit_args)

    compute_module = init_compute_module(
        device_path=args.device_path,
        variant=args.variant,
        reset_on_launch=args.reset_on_launch,
    )

    command_value = Commands[args.command]

    input_buffer = bytes()
    if (
        command_value == Commands.add
        or command_value == Commands.sub
        or command_value == Commands.mul
        or command_value == Commands.div
    ):
        arg_a_min, arg_a_max = parse_tolerance_value(args.argument_a)
        arg_b_min, arg_b_max = parse_tolerance_value(args.argument_b)

        input_buffer = pack_floats(
            floats=[arg_a_min, arg_a_max, arg_b_min, arg_b_max],
            size=compute_module.INPUT_BUFFER_SIZE_BYTES,
        )
    elif command_value == Commands.sample:
        input_buffer = pack_unsigned_integers(
            uint=[args.count],
            size=compute_module.INPUT_BUFFER_SIZE_BYTES,
        )

    if args.benchmark:
        iterations = args.iterations
    else:
        iterations = 1

    timings: list[float] = []
    for _ in tqdm(range(iterations), disable=not args.benchmark):
        startTime = time.perf_counter()

        # Run the calculation and get the results
        result_buffer = run_and_get_results(
            compute_module=compute_module,
            command_value=command_value,
            input_buffer=input_buffer,
            stop_on_exit=args.stop_on_exit,
        )

        endTime = time.perf_counter()
        iterationTime = endTime - startTime
        timings.append(iterationTime)

    if args.benchmark:
        meanTime = sum(timings) / iterations
        print(f"Mean execution time over {iterations} ",
                f"iterations: {meanTime:.6f} seconds")

    if (
        command_value == Commands.add
        or command_value == Commands.sub
        or command_value == Commands.mul
        or command_value == Commands.div
    ):
        dists = parse_output_buffer(
            buffer=result_buffer,
            expected_output_count=1,
        )
        print_output_values(dists)
    elif command_value == Commands.sample:
        samples = unpack_floats(
            byte_buffer=result_buffer,
            count=args.count,
        )
        for i, sample in enumerate(samples):
            print(f"{i:>3}: {sample}")


if __name__ == "__main__":
    main()
