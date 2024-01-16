
from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal

class Adq():
    def __init__(self):
        self.oe = Signal(8)
        self.o = Signal(8)
        self.i = Signal(8)

class Dqsdm():
    def __init__(self):
        self.oe = Signal(2)
        self.i = Signal(2)

class OSPI_SIM(Elaboratable):

    def __init__(self):
        self.clk = Signal()
        self.cs = Signal()
        self.adq = Adq()
        self.dqsdm = Dqsdm()

    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        print(self.cs)
        
        return m