import sys
from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    ClockSignal, \
    DomainRenamer, \
    Repl, \
    Mux, \
    Cat, C

from memory import Mem
from lib.femtorv32 import Intermission

class SOC(Elaboratable):

    def __init__(self):
        self.leds = Signal(3)

    def elaborate(self, platform: Platform) -> Module:
        m = Module()
        
        clk_frequency = int(platform.default_clk_constraint.frequency)

        # Move the modules into the "slow" domain
        memory = Mem()
        cpu = Intermission()

        m.submodules.cpu = cpu
        m.submodules.memory = memory

        # Export to public
        self.cpu = cpu
        self.memory = memory

        # IO is mapped to bit 22 of address
        # LED "device" is bit 0 (one-hot encoding)
        # 0000_0000_0010_0000_0000_0000_0000_0000 = 0x00200000 = LED selected
        isIO = Signal()
        # Ram is everything NOT mapped to any upper bit.
        isRAM = Signal()

        mem_wstrb = Signal()
        io_rdata = Signal(32)

        # Memory map bits (one-hot encoding)
        # Because the IO devices are word aligned, bit0 is actually
        # bit2 in full address.
        IO_LEDS_bit = 0     # To set bit use a value of 4

        ram_rdata = Signal(32)
        mem_wordaddr = Signal(30)

        m.d.comb += [
            mem_wordaddr.eq(cpu.mem_addr[2:32]),
            isIO.eq(cpu.mem_addr[21]),
            isRAM.eq(~isIO),
            mem_wstrb.eq(cpu.mem_wmask.any())
        ]

        # Connect memory to CPU
        m.d.comb += [
            memory.mem_addr.eq(cpu.mem_addr),
            memory.mem_rstrb.eq(isRAM & cpu.mem_rstrb),
            memory.mem_wdata.eq(cpu.mem_wdata),
            memory.mem_wmask.eq(Repl(isRAM, 4) & cpu.mem_wmask),
            ram_rdata.eq(memory.mem_rdata),
            cpu.mem_rdata.eq(Mux(isRAM, ram_rdata, io_rdata))
        ]

        # RGB LEDs
        with m.If(isIO & mem_wstrb & mem_wordaddr[IO_LEDS_bit]):
            m.d.sync += self.leds.eq(cpu.mem_wdata)

        # Export signals for simulation
        def export(signal, name):
            if type(signal) is not Signal:
                newsig = Signal(signal.shape(), name = name)
                m.d.comb += newsig.eq(signal)
            else:
                newsig = signal
            self.ports.append(newsig)
            setattr(self, name, newsig)

        return m
