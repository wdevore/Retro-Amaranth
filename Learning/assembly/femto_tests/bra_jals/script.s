.section .text, "ax", @progbits
.align 2

# Tested against this online assembler: https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    li a0, 3
Loop:
    addi a0, a0, -1
    beq a0, x0, Done
    j Loop

Done:
    li a0, 3
    li a1, 2
    bne a0, a1, BRNE

    li a0, 5
BRNE:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
