# Signaloid-C0-microSD-Demo-Calculator
This demo application for the C0-microSD supports the following operations:

- Arithmetic operations (add, sub mul, div) of two uniform distributions.
- Sampling from an example built-in distribution.

Folder `python-host-application` contains the source code that runs on the host that communicates with Signaloid C0-microSD.
Folder `C0-microSD-application` contains the source code, initialization assembly, and linker script for building an application for Signaloid C0-microSD.

## Cloning this repository
The correct way to clone this repository to get the hardware and firmware submodules is:

	git clone --recursive https://github.com/signaloid/Signaloid-C0-microSD-Demo-Calculator

To update all submodules:

	git pull --recurse-submodules
	git submodule update --remote --recursive

If you forgot to clone with `--recursive`, and end up with empty submodule directories, you can remedy this with

	git submodule update --init --recursive

## How to use:


### Flash the C0-microSD application
1. Navigate to the `signaloid-soc-application/` folder.
2. Modify the `DEVICE` flag in the `Makefile` to point to your C0-microSD device path.
3. Run `make flash`, and `make switch` (the green LED should blink).
4. Power cycle the C0-microSD (the green LED should light up).


### Run the Python based host application
To run the python based host application you first need to install the Ux plotting dependencies. To do that:
1. Navigate to `./python-host-application`
2. Create a virtual environment: `python3 -m venv .env`
3. Activate virtual environment: `source .env/bin/activate`
4. Install the `signaloid-python` package: `pip install git+https://github.com/signaloid/signaloid-python`
5. Run the application: `sudo python3 host_application.py /dev/diskX add "1.0(5)" "1.0(5)"`, where `/dev/diskX` is the C0-microSD device path.

## Host application
The host application is designed to parse input arguments following [concise form of uncertainty
notation](https://physics.nist.gov/cgi-bin/cuu/Info/Constants/definitions.html#:~:text=A%20more%20concise%20form%20of,digits%20of%20the%20quoted%20result.&text=See%20Uncertainty%20of%20Measurement%20Results): `X.Y(Z)` that describe two uniform distributions. The application supports addition, subtraction,
multiplication, and division of the input arguments. The input arguments must be quoted in a linux
shell.

```
usage: host_application.py [-h] device_path {add,sub,mul,div,sample} ...

Host application for C0-microSD calculator application

positional arguments:
  device_path           Path of C0-microSD
  {add,sub,mul,div,sample}
                        Commands
    add                 Add two uncertainty values
    sub                 Subtract two uncertainty values
    mul                 Multiply two uncertainty values
    div                 Divide two uncertainty values
    sample              Get samples from example built-in distribution

optional arguments:
  -h, --help            show this help message and exit
```

For example, you can multiply the value `2.0` with a tolerance of `+- 0.5` and the value `5.0` with a tolerance of `+- 0.3` by running:

```zsh
sudo python host_application.py /dev/disk4 mul "2.0(5)" "5.0(3)"
```
In the above example, we assume that the C0-microSD device is located at `/dev/disk4`

You can also generate 100 samples from the built-in example distribution
```zsh
sudo python host_application.py /dev/disk4 sample 100
```
