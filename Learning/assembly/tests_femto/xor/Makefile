RISCV_TOOLCHAIN := /opt/riscv/bin/
# "linux-gnu" or "elf"
BUILD_TYPE := elf
GAS := riscv64-unknown-$(BUILD_TYPE)-as
LD  := riscv64-unknown-$(BUILD_TYPE)-ld
DUMP := riscv64-unknown-$(BUILD_TYPE)-objdump
COPY := riscv64-unknown-$(BUILD_TYPE)-objcopy

# Emulations:
# "elf32lriscv_ilp32" or "elf32lriscv"
EMULATION := elf32lriscv

BINARY_MODULE := script
FIRMWARE := firmware
HEX_FIRMWARE := $(FIRMWARE).hex

MODULES_FILES = \
	script.s

BUILD_BIN = /media/RAMDisk

.PHONY: all
all: assemble link dump out2hex

assemble: $(MODULES_FILES)
	@echo "############### Assembling ##################"
	@$(RISCV_TOOLCHAIN)$(GAS) \
	-march=rv32im \
	-mabi=ilp32 \
	-mlittle-endian \
	-mno-relax \
	-mno-arch-attr \
	-fno-pic \
	-o $(BUILD_BIN)/$(BINARY_MODULE).o $(MODULES_FILES)

# -T linker_script.ld
# 	-nostdlib \
#	-Map $(BINARY_MODULE).map \

link: $(BUILD_BIN)/$(BINARY_MODULE).o
	@echo "############### Linking... ##################"
	@$(RISCV_TOOLCHAIN)$(LD) \
	-m $(EMULATION) \
	-o $(BUILD_BIN)/$(BINARY_MODULE) \
	-O 0 \
	-T $(BINARY_MODULE).ld \
	$(BUILD_BIN)/$(BINARY_MODULE).o

# You can also dump the .o file such that it isn't relocated 
# by the linker.
#	--visualize-jumps \
#	--disassemble-zeroes \
# 	--disassembler-options=no-aliases \
#	--section=keybuffer \
# 	-t \
#   --full-contents \

.PHONY: dump
dump: $(BUILD_BIN)/${BINARY_MODULE}
	@echo "############### Dumping... ##################"
	@$(RISCV_TOOLCHAIN)$(DUMP) \
	-d \
	-h \
	-w \
	--insn-width=4 \
	--section=.text \
	--section=.data \
	--section=.rodata \
	--section=keybuffer \
	--section=stack \
	--section=micro_code \
	$(BUILD_BIN)/$(BINARY_MODULE) \
	>$(BUILD_BIN)/$(FIRMWARE).out

.PHONY: out2hex
out2hex: $(BUILD_BIN)/$(FIRMWARE).out
	@echo "############### Generating hex firmware... ##################"
	@cd ../../out2hex; \
	go run . $(BUILD_BIN)/$(FIRMWARE).out $(BUILD_BIN)/$(FIRMWARE).hex

.PHONY: out2amar
out2amar: $(BUILD_BIN)/$(FIRMWARE).out
	@echo "############### Generating Amaranth code... ##################"
	@cd ../../out2amaranth; \
	go run . $(BUILD_BIN)/$(FIRMWARE).hex $(BUILD_BIN)/$(FIRMWARE).py

.PHONY: clean
clean:
	@rm	$(BUILD_BIN)/*.o \
		$(BUILD_BIN)/*.out \
		$(BUILD_BIN)/$(BINARY_MODULE)

.PHONY: out2verlog
out2verlog: $(BUILD_BIN)/$(BINARY_MODULE)
	@echo "############### Generating hex firmware via objcopy... ##################"
	@$(RISCV_TOOLCHAIN)$(COPY) \
	-O verilog \
	--verilog-data-width 4 \
	$(BUILD_BIN)/$(BINARY_MODULE) $(BUILD_BIN)/firmware.hex
