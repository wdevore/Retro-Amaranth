OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    /* The addresses specified are in byte-address form */
    BRAM(wx) :ORIGIN =0x00000000,LENGTH = 176
    ROM(r)   :ORIGIN =0x00000050,LENGTH = 64
}

SECTIONS
{
    .text : {
        *(.text)
    }> BRAM

    .rodata : {
        rom_data = .;
        *(.rodata)
    }> ROM
}