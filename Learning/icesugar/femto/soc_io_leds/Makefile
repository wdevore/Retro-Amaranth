
TOP = ranger_retro
CODE = ${TOP}.py

PYTHON = python

BINPATH = /media/RAMDisk/build
ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards
PATHS := ${PATHS}:${ROOTPATH}/Retro-Amaranth/Learning

.PHONY: all

# Runs simulation
simulate: ${BENCH}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE} 1> ${BINPATH}/output.txt

# I can't figure out the udev rules correctly for icesprog to work as user
# @icesprog ${BINPATH}/top.bin
upload:
	@echo "##### Uploading..."
	@cp ${BINPATH}/top.bin /media/iposthuman/iCELink
	