CODE = bench.py

PYTHON = python

ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards
PATHS := ${PATHS}:${ROOTPATH}/Retro-Amaranth/Learning/simulations/bl0x

.PHONY: all

# Runs simulation
simulate: ${BENCH}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE}
