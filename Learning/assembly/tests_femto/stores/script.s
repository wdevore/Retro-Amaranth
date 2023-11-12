.section .text, "ax", @progbits
.align 2

# Tested against this online assembler: https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    la t0, rom_data
    li t1, 0x20
    lw a0, 4(t0)

    sb a0, 0(t1)
    sh a0, 0(t1)
    sw a0, 0(t1)

Exit:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
.word 0xD3C2B1E0
.word 0xdeadbeaf
