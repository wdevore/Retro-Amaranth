# from amaranth.sim import Simulator
from amaranth import *
from amaranth.sim import *

from soc import SOC

soc = SOC()

sim = Simulator(soc)

prev_clk = 0
clk_count = 0

def process():
    cpu = soc.cpu
    mem = soc.memory

    while True:
        global prev_clk
        global clk_count

        clk = yield soc.slow_clk
        clk_count += 1
        # print("{:8d} -------------------------".format(clk_count))

        if prev_clk == 0 and prev_clk != clk:
            # print("{:8d} #####################################".format(clk_count))
            state = (yield cpu.fsm.state)

            if state == 2:
                instr = (yield cpu.instr)
                print("-- NEW CYCLE -----------------------")
                print("  F: state={}".format(state))
                # print("  F: LEDS = {:05b}".format((yield soc.leds)))
                # print("  F: pc={}".format((yield cpu.pc)))
                print("  F: instr={:#032b}".format(instr))
                # if (yield cpu.isALUreg):
                #     print("")
                #     # print("     ALUreg rd={} rs1={} rs2={} funct3={}".format(
                #     #     (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.rs2Id),
                #     #     (yield cpu.funct3)))
                # if (yield cpu.isALUimm):
                #     print("")
                #     # print("     ALUimm rd={} rs1={} imm={} funct3={}".format(
                #     #     (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                #     #     (yield cpu.funct3)))
                # if (yield cpu.isBranch):
                #     print("")
                #     # print("    BRANCH rs1={} rs2={}".format(
                #     #     (yield cpu.rs1Id), (yield cpu.rs2Id)))
                # if (yield cpu.isLoad):
                #     print("    LOAD")
                # if (yield cpu.isStore):
                #     print("    STORE")
                # if (yield cpu.isSystem):
                #     print("    SYSTEM")
                #     break
            # if state == 4:
                # print("  R: LEDS = {:05b}".format((yield soc.leds)))
                # print("  R: rs1={}".format((yield cpu.rs1)))
                # print("  R: rs2={}".format((yield cpu.rs2)))
            # if state == 1:
                # print("  E: LEDS = {:05b}".format((yield soc.leds)))
                # print("  E: Writeback x{} = {:032b}".format((yield cpu.rdId),
                #                              (yield cpu.writeBackData)))
            if state == 8:
                print("  NEW")
        yield
        prev_clk = clk

sim.add_clock(1e-6)
sim.add_sync_process(process)

# with sim.write_vcd('bench.vcd', 'bench.gtkw'):
with sim.write_vcd('bench.vcd', 'bench.gtkw', traces=soc.ports):
    # Let's run for a quite long time
    # @NOTE: The Clk tick printed is delayed 1500ns from when Gtkwave shows
    # the signal edge.
    sim.run_until(10e-3) # Deadline (aka duration) is given in seconds.
