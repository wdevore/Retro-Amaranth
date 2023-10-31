from amaranth import *
from amaranth.sim import *

from soc import SOC

soc = SOC()

sim = Simulator(soc)

prev_clk = 0

def proc():
    cpu = soc.cpu
    mem = soc.memory
    while True:
        global prev_clk
        clk = yield soc.slow_clk
        if prev_clk == 0 and prev_clk != clk:
            state = (yield soc.cpu.fsm.state)
            print("##### State: {} #####".format(state))
            if state == 2: # FETCH_REGS
                print("-- NEW CYCLE ---------------------------------------------------------------------")
                print("  FR: LEDS = {:05b}".format((yield soc.leds)))
                print("  FR: pc={}".format((yield cpu.pc)))
                print("  FR: instr={:#032b} 0x{:08X}".format((yield cpu.instr),(yield cpu.instr)))
                if (yield cpu.isALUreg):
                    print("     ALUreg rd={} rs1={} rs2={} funct3={}".format(
                        (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.rs2Id),
                        (yield cpu.funct3)))
                if (yield cpu.isALUimm):
                    print("     ALUimm rd={} rs1={} imm={} funct3={}".format(
                        (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                        (yield cpu.funct3)))
                if (yield cpu.isBranch):
                    print("    BRANCH rs1={} rs2={}".format(
                        (yield cpu.rs1Id), (yield cpu.rs2Id)))
                if (yield cpu.isLoad):
                    print("    LOAD rd={} rs1={} imm={} funct3={} addr=0x{:08X} rdata=0x{:08X}".format(
                        (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                        (yield cpu.funct3),
                        (yield cpu.mem_addr),
                        (yield cpu.mem_rdata)))                        
                if (yield cpu.isStore):
                    print("    STORE")
                if (yield cpu.isSystem):
                    print("    SYSTEM")
                    break
            if state == 4:  # LOAD
                print("  LD: LEDS = {:05b}".format((yield soc.leds)))
                print("  LD: rs1={}".format((yield cpu.rs1)))
                print("  LD: rs2={}".format((yield cpu.rs2)))
                print("         rd={} rs1={} imm={} funct3={} addr=0x{:08X} rdata=0x{:08X}".format(
                    (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                    (yield cpu.funct3),
                    (yield cpu.mem_addr),
                    (yield cpu.mem_rdata)))                        
            if state == 1:  # WAIT_INSTR
                print("  WI: LEDS = {:05b}".format((yield soc.leds)))
                print("  WI: Writeback x{} = 0b{:032b}".format((yield cpu.rdId),
                                             (yield cpu.writeBackData)))
            if state == 3:  # EXECUTE
                print("  X:")
                print("         rd={} rs1={} imm={} funct3={} addr=0x{:08X} rdata=0x{:08X}".format(
                    (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                    (yield cpu.funct3),
                    (yield cpu.mem_addr),
                    (yield cpu.mem_rdata)))                        
            if state == 5:  # WAIT_DATA
                print("  WD:")
                print("         rd={} rs1={} imm={} funct3={} addr=0x{:08X} rdata=0x{:08X}".format(
                    (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                    (yield cpu.funct3),
                    (yield cpu.mem_addr),
                    (yield cpu.mem_rdata)))                        
                print("         isLoad={} isStore={} isALUimm={} isALUreg={} writeBackEn={} isBranch={}".format(
                    (yield cpu.isLoad),
                    (yield cpu.isStore),
                    (yield cpu.isALUimm),
                    (yield cpu.isALUreg),
                    (yield cpu.writeBackEn),
                    (yield cpu.isBranch)))
                print("         ongoingE={} ongoingWD={}".format(
                    (yield cpu.ongoingE),
                    (yield cpu.ongoingWD)))
            if state == 0:  # FETCH_INSTR
                print("  FI:")
                print("         rd={} rs1={} imm={} funct3={} addr=0x{:08X} rdata=0x{:08X}".format(
                    (yield cpu.rdId), (yield cpu.rs1Id), (yield cpu.Iimm),
                    (yield cpu.funct3),
                    (yield cpu.mem_addr),
                    (yield cpu.mem_rdata)))                        
                print("         mBytAcc={} mHWAcc={} ldHW=0x{:04X} ldByt=0x{:02X} ldSign={} ldDat=0x{:08X}".format(
                    (yield cpu.memByteAccess),
                    (yield cpu.memHalfwordAccess),
                    (yield cpu.loadHalfword),
                    (yield cpu.loadByte),
                    (yield cpu.loadSign),
                    (yield cpu.loadData)))                        
                print("         isLoad={} isStore={} isALUimm={} isALUreg={} writeBackEn={} isBranch={}".format(
                    (yield cpu.isLoad),
                    (yield cpu.isStore),
                    (yield cpu.isALUimm),
                    (yield cpu.isALUreg),
                    (yield cpu.writeBackEn),
                    (yield cpu.isBranch)))
                print("         ongoingE={} ongoingWD={}".format(
                    (yield cpu.ongoingE),
                    (yield cpu.ongoingWD)))
            if state == 8:
                print("  NEW")
        yield
        prev_clk = clk

sim.add_clock(1e-6)
sim.add_sync_process(proc)

with sim.write_vcd('bench.vcd', 'bench.gtkw', traces=soc.ports):
    # Let's run for a quite long time
    sim.run_until(2, )
