OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    /* The addresses specified are in byte-address form */
    BRAM(wx) :ORIGIN =0x00000000,LENGTH = 256
    ROM(r)   :ORIGIN =0x00000100,LENGTH = 256
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