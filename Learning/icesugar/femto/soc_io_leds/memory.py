from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    Array, \
    Memory

class Mem(Elaboratable):

    def __init__(self):
        # Read hex file. Parse each line for instruction and locate
        # hex instruction and convert to 32bit hex value and
        # append to Array.

        self.instructions = []
        
        # Read firmware.hex from build on RAMDisk
        # Format of input is: @00000004 0042A383
        paddr = 0

        with open('/media/RAMDisk/firmware.hex', 'r') as f:
            for line in f:
                fields = line.split()
                nddr = fields[0].split("@")[1]
                naddr = int(nddr, 16)
            
                if naddr > (paddr + 1):
                    # Pad gap with Zeroes
                    while paddr < (naddr-1) :
                        self.instructions.append(0x00000000)
                        paddr += 1
                paddr = naddr

                instr = int(fields[1], 16)
                self.instructions.append(instr)

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
