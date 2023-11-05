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

from lib.clockworks import Clockworks

from memory import Mem
from lib.femtorv32_intermissum import CPU

class SOC(Elaboratable):

    def __init__(self):
        # Signals in this list can easily be plotted as vcd traces
        self.ports = []

    def elaborate(self, platform: Platform) -> Module:
        m = Module()
        
        # NOTE:
        # Increasing the exponent value, for example, from 2^5 to 2^6
        # increases the period but doesn't change the simulation step size.
        # The step-size can't be changed, only the duration and period.
        # If we specify 1000e-6 for the deadline, in the bench, that gives
        # 1000 step duration.
        # Example 1: 2^5 yields ~33 steps between clock edges or 18 clocks
        #     over a duration of 1000 steps.
        # Example 2: 2^6 yields ~65 steps between clock edges or 8 clocks
        #     over a duration of 1000 steps.
        # Example 3: 2^7 yields ~129 steps between clock edges or 4 clocks
        #     over a duration of 1000 steps.
        # Example 4: 2^8 yields ~257 steps between clock edges or 2 clocks
        #     over a duration of 1000 steps.
        # Example 5: 2^9 yields ~513 steps between clock edges or 1 clock
        #     over a duration of 1000 steps.
        # Example 6: 2^10 yields 0 clocks over a duration of 1000 steps.
        #     However, if you increase the deadline (i.e. duration) to 2000e-6
        #     you will now yield ~1025 steps between clock edges 
        #     or 1 clock over a duration of 2000 steps.
        #     Thus as you increase the deadline (aka simulation window),
        #     you add more clock edges to the simulation.
        # For a CPU simulation you will typically need several or more clocks
        # to execute an instruction. Thus you need a duration long enough
        # to execute all instructions.
        # For example:
        # A period of 2^5 and a duration of 100e-3 (ms) gives 1562 clocks, and
        # the simulation take 100000 steps.
        # For the Femto that means 1562/4 ~= 390 instructions. The simulation
        # takes about 3 seconds to run on an 13th gen 16 thread intel.
        cw = Clockworks(slow=19, sim_slow=5)

        if platform is not None:
            clk_frequency = int(platform.default_clk_constraint.frequency)
            print("clock frequency = {}".format(clk_frequency))
        else:
            clk_frequency = 12000000

        # Move the modules into the "slow" domain
        memory = DomainRenamer("slow")(Mem())
        cpu = DomainRenamer("slow")(CPU())

        m.submodules.cw = cw
        m.submodules.cpu = cpu
        m.submodules.memory = memory

        self.cpu = cpu
        self.memory = memory

        ram_rdata = Signal(32)
        mem_wordaddr = Signal(30)
        isIO = Signal()
        isRAM = Signal()
        mem_wstrb = Signal()
        io_rdata = Signal(32)

        # Memory map bits (one-hot encoding)
        IO_LEDS_bit = 0
        IO_UART_DAT_bit = 1
        IO_UART_CNTL_bit = 2

        m.d.comb += [
            mem_wordaddr.eq(cpu.mem_addr[2:32]),
            isIO.eq(cpu.mem_addr[22]),
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
            # export(cpu.pc, "pc")
            # export(cpu.instr, "instr")
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
