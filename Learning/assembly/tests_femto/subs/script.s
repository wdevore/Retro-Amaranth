.section .text, "ax", @progbits
.align 2

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    li a0, 3
Loop:
    jal DecA0               # Call subroutine
    beq a0, x0, Done
    j Loop

DecA0:                      # Subroutine
    addi a0, a0, -1
    ret

Done:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
