CODENAME = bench
CODE = ${CODENAME}.py

PYTHON = python

ROOTPATH = /media/iposthuman/Nihongo/Hardware/

# The vcd data for viewing
GTKWAVE_SETTINGS = waveform

# These paths are for building in a shell. VSCode uses .env file to specify paths.
PATHS := ${ROOTPATH}amaranth-boards
PATHS := ${PATHS}:${ROOTPATH}/Retro-Amaranth/Learning/simulations/bl0x

.PHONY: all

# Runs simulation
simulate: ${BENCH}
	@echo "##### Working..."
	@PYTHONPATH=${PATHS} ${PYTHON} ${CODE} 1> simulation_output.txt

view:
	@echo "################## Viewing ##################"
	gtkwave ${CODENAME}.vcd \
	${CODENAME}.gtkw \
	--rcvar 'splash_disable on' \
	--rcvar 'fontname_signals Monospace 14' \
	--rcvar 'fontname_waves Monospace 14' \
	--rcvar 'color_back 222222' \
	--rcvar 'color_trans 999999' \
	--rcvar 'color_time 00ddff' \
	--rcvar 'enable_horiz_grid off' \
	--rcvar 'highlight_wavewindow on' \
	--rcvar 'show_base_symbols on' \
	--rcvar 'fill_waveform on' \
	--rcvar 'disable_mouseover off'
