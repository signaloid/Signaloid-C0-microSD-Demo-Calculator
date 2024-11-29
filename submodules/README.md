# Repository Submodules

To update all submodules:

	git pull --recurse-submodules
	git submodule update --remote --recursive

If you forgot to clone with `--recursive`, and end up with empty submodule directories, you can remedy this with

	git submodule update --init --recursive
