TOOLKIT			= python3 ../submodules/C0-microSD-utilities/C0_microSD_toolkit.py
DEVICE			= /dev/disk4
PROGRAM			= main

flash: $(PROGRAM).bin
	sudo $(TOOLKIT) -t $(DEVICE) -b $(PROGRAM).bin -u -p 128K

switch:
	sudo $(TOOLKIT) -t $(DEVICE) -s
