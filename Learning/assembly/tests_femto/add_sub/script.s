.section .text, "ax", @progbits
.align 2

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# Main
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.global _start
_start:
    li a0, 1
    li a1, 2
    add a2, a0, a1  # 1 + 2 = 3
    sub a2, a1, a0  # 2 - 1 = 1
    sub a2, a0, a1  # 1 - 2 = -1 = 0xFFFFFFFF

Exit:
    ebreak

# __++__++__++__++__++__++__++__++__++__++__++__++__++
# ROM-ish
# __++__++__++__++__++__++__++__++__++__++__++__++__++
.section .rodata
.balign 4
