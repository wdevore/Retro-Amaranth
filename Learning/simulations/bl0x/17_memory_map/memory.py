from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    Array, \
    Memory

from tools.riscv_assembler import RiscvAssembler

class Mem(Elaboratable):

    def __init__(self):
        a = RiscvAssembler()

        a.read("""begin:
        LI sp, 0x1800
        LI gp, 0x400000

        l0:
        LI s0, 16
        LI a0, 0

        l1:
        SW a0, gp, 4
        CALL wait
        ADDI a0, a0, 1
        BNE a0, s0, l1

        LI s0, 26
        LI a0, "a"
        LI s1, 0

        l2:
        CALL putc
        ADDI a0, a0, 1
        ADDI s1, s1, 1
        BNE s1, s0, l2

        LI a0, 13
        CALL putc
        LI a0, 10
        CALL putc

        J l0

        EBREAK

        wait:
        LI t0, 1
        SLLI t0, t0, 18

        wait_loop:
        ADDI t0, t0, -1
        BNEZ t0, wait_loop
        RET

        putc:
        SW a0, gp, 8
        LI t0, 0x200
        putc_loop:
        LW t1, gp, 0x10
        AND t1, t1, t0
        BNEZ t1, putc_loop
        RET
        """)

        a.assemble()
        self.instructions = a.mem

        # Add 0 memory up to offset 1024 / word 256
        while len(self.instructions) < (1024 * 6 / 4):
            self.instructions.append(0)

        print("memory = {}".format(self.instructions))

        # Instruction memory initialised with above instructions
        self.mem = Memory(width=32, depth=len(self.instructions),
                          init=self.instructions, name="mem")

        self.mem_addr = Signal(32)
        self.mem_rdata = Signal(32)
        self.mem_rstrb = Signal()
        self.mem_wdata = Signal(32)
        self.mem_wmask = Signal(4)

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        # Using the memory module from amaranth library,
        # we can use write_port and read_port to easily instantiate
        # platform specific primitives to access memory efficiently.
        w_port = m.submodules.w_port = self.mem.write_port(
            domain="sync", granularity=8
        )
        r_port = m.submodules.r_port = self.mem.read_port(
            domain="sync", transparent=False
        )

        word_addr = self.mem_addr[2:32]

        # Hook up read port
        m.d.comb += [
            r_port.addr.eq(word_addr),
            r_port.en.eq(self.mem_rstrb),
            self.mem_rdata.eq(r_port.data)
        ]

        # Hook up write port
        m.d.comb += [
            w_port.addr.eq(word_addr),
            w_port.en.eq(self.mem_wmask),
            w_port.data.eq(self.mem_wdata)
        ]

        return m
