.section .text, "ax", @progbits
.align 2

# Tested against this online assembler: https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    li a0, 0x05
    slti a1, a0, 4
    slti a1, a0, 6
    addi x10, x0, -5
    li a0, -5
    slti a1, a0, -4
    sltiu a1, a0, -6
    sltiu a1, a0, 6

Exit:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
