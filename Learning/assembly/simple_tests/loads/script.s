.section .text, "ax", @progbits
.align 2

# Tested against this online assembler: https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    la t0, rom_data
    lb a0, 0(t0)
    mv a0, x0
    lbu a0, 0(t0)
    mv a0, x0
    lbu a0, 1(t0)

    lh a0, 0(t0)
    lhu a0, 2(t0)

    lw a0, 4(t0)

Exit:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
.word 0xD3C2B1E0
.word 0xdeadbeaf
