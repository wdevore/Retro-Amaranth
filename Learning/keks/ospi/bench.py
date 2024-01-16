from amaranth.sim import *

from bench_ospi import Top

ospi = Top()

sim = Simulator(ospi)

prev_clk = 0

def proc():
    while True:
        global prev_clk

        clk = yield ospi.slow_clk
        
        # if prev_clk == 0 and prev_clk != clk:
        #     print("pc={}".format((yield ospi.pc)))
        #     print("instr={:#032b}".format((yield ospi.instr)))
        #     print("LEDS = {:05b}".format((yield ospi.leds)))
        #     if (yield ospi.isALUreg):
        #         print("ALUreg rd={} rs1={} rs2={} funct3={}".format(
        #             (yield ospi.rdId), (yield ospi.rs1Id), (yield ospi.rs2Id),
        #             (yield ospi.funct3)))
        #     if (yield ospi.isALUimm):
        #         print("ALUimm rd={} rs1={} imm={} funct3={}".format(
        #             (yield ospi.rdId), (yield ospi.rs1Id), (yield ospi.Iimm),
        #             (yield ospi.funct3)))
        #     if (yield ospi.isLoad):
        #         print("LOAD")
        #     if (yield ospi.isStore):
        #         print("STORE")
        #     if (yield ospi.isSystem):
        #         print("SYSTEM")
        #         break
        yield
        
        prev_clk = clk

sim.add_clock(1e-6)
sim.add_sync_process(proc)

with sim.write_vcd('bench.vcd', traces=ospi.ports):
    # Let's run for a quite long time
    # sim.run_until(2, )
    # NOTE: The Clk tick printed is delayed 1500ns from when Gtkwave shows
    # the signal edge.
    sim.run_until(10e-3) # Deadline (aka duration) is given in seconds.
