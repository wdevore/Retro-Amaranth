CODENAME = ospi
CODE = ${CODENAME}.py

PYTHON = python

BINPATH = /media/RAMDisk/build
ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards:${ROOTPATH}/Retro-Amaranth/Learning

.PHONY: all

# Runs simulation
build: ${BENCH}
	@echo "##### Working on '${CODENAME}' ..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE} 1> ${BINPATH}/output.txt

upload:
	@echo "##### Uploading..."
	@ldprog -ks ${BINPATH}/top.bin
	