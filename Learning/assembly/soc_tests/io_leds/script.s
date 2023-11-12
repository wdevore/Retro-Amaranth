.section .text, "ax", @progbits
.align 2

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    la t0, rom_data
    li t1, 0x24         # A place in Ram just after ebreak
    lw a0, 0(t0)        # Load "deadbeaf"
    lw t2, 4(t0)        # Load addr of IO map


    # Store to ram first
    sw a0, 0(t1)

    # Select to blue LED (rgb)
    addi a1, x0, 2
    sb a1, 4(t2)        # Devices are one-hot word aligned. So LEDs are 4

    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
.word 0xdeadbeaf
.word 0x00200000        # LED IO address (bit0 = 0)
