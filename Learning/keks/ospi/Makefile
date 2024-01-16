CODENAME = bench_ospi
CODE = ${CODENAME}.py

PYTHON = python
BENCHNAME = bench.py

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

# Runs simulation
simulate: ${BENCHNAME}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${BENCHNAME}

view:
	@echo "################## Viewing ##################"
	gtkwave bench.vcd \
	bench.gtkw \
	--rcvar 'splash_disable on' \
	--rcvar 'fontname_signals Monospace 10' \
	--rcvar 'fontname_waves Monospace 10' \
	--rcvar 'color_back 222222' \
	--rcvar 'color_trans 999999' \
	--rcvar 'color_time 00ddff' \
	--rcvar 'enable_horiz_grid off' \
	--rcvar 'highlight_wavewindow on' \
	--rcvar 'show_base_symbols on' \
	--rcvar 'fill_waveform on' \
	--rcvar 'disable_mouseover off'
