CODENAME = sram
CODE = ${CODENAME}.py

PYTHON = python

BINPATH = /media/RAMDisk/build
ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards

.PHONY: all

# Runs simulation
build: ${BENCH}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE} 1> ${BINPATH}/output.txt

upload:
	@echo "##### Uploading..."
	@ldprog -ks ${BINPATH}/top.bin
	