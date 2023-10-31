import sys
from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Signal, \
    Module, \
    ClockSignal, \
    DomainRenamer

from lib.clockworks import Clockworks

from memory import Memory
from cpu import CPU

class SOC(Elaboratable):

    def __init__(self):

        self.leds = Signal(5)

        # Signals in this list can easily be plotted as vcd traces
        self.ports = []

    def elaborate(self, platform: Platform) -> Module:

        m = Module()
        cw = Clockworks(slow=19, sim_slow=15)

        memory = DomainRenamer("slow")(Memory())
        cpu = DomainRenamer("slow")(CPU())

        m.submodules.cw = cw
        m.submodules.cpu = cpu
        m.submodules.memory = memory

        self.cpu = cpu
        self.memory = memory

        x10 = Signal(32)

        # Connect memory to CPU
        m.d.comb += [
            memory.mem_addr.eq(cpu.mem_addr),
            memory.mem_rstrb.eq(cpu.mem_rstrb),
            cpu.mem_rdata.eq(memory.mem_rdata)
        ]

        # CPU debug output
        m.d.comb += [
            x10.eq(cpu.x10),
            self.leds.eq(x10[0:5])
        ]

        # Export signals for simulation
        def export(signal, name):
            if type(signal) is not Signal:
                newsig = Signal(signal.shape(), name = name)
                m.d.comb += newsig.eq(signal)
            else:
                newsig = signal
            self.ports.append(newsig)
            setattr(self, name, newsig)

        if platform is None:
            export(ClockSignal("slow"), "slow_clk")
            #export(pc, "pc")
            #export(instr, "instr")
            #export(isALUreg, "isALUreg")
            #export(isALUimm, "isALUimm")
            #export(isBranch, "isBranch")
            #export(isJAL, "isJAL")
            #export(isJALR, "isJALR")
            #export(isLoad, "isLoad")
            #export(isStore, "isStore")
            #export(isSystem, "isSystem")
            #export(rdId, "rdId")
            #export(rs1Id, "rs1Id")
            #export(rs2Id, "rs2Id")
            #export(Iimm, "Iimm")
            #export(Bimm, "Bimm")
            #export(Jimm, "Jimm")
            #export(funct3, "funct3")
            #export(rdId, "rdId")
            #export(rs1, "rs1")
            #export(rs2, "rs2")
            #export(writeBackData, "writeBackData")
            #export(writeBackEn, "writeBackEn")
            #export(aluOut, "aluOut")
            #export((1 << cpu.fsm.state), "state")

        return m
