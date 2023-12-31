from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    Array

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
        self.mem = Array([Signal(32, reset=x, name="mem{}".format(i))
                          for i,x in enumerate(self.instructions)])

        self.mem_addr = Signal(32)
        self.mem_rdata = Signal(32)
        self.mem_rstrb = Signal()
        self.mem_wdata = Signal(32)
        self.mem_wmask = Signal(4)

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        word_addr = self.mem_addr[2:32]

        with m.If(self.mem_rstrb):
            m.d.sync += self.mem_rdata.eq(self.mem[word_addr])
        with m.If(self.mem_wmask[0]):
            m.d.sync += self.mem[word_addr][0:8].eq(self.mem_wdata[0:8])
        with m.If(self.mem_wmask[1]):
            m.d.sync += self.mem[word_addr][8:16].eq(self.mem_wdata[8:16])
        with m.If(self.mem_wmask[2]):
            m.d.sync += self.mem[word_addr][16:24].eq(self.mem_wdata[16:24])
        with m.If(self.mem_wmask[3]):
            m.d.sync += self.mem[word_addr][24:32].eq(self.mem_wdata[24:32])

        return m
