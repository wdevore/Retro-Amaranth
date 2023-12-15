from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Array, \
    Signal, \
    Const

from amaranth.build import \
    Resource,\
    PinsN

# In this test we:
# Cycle over both 256KB banks writing 0x0505 and 0xa0a0
# 256K half-words = 0x00000 -> 1FFFF
# 
# For each memory location write/read 4 half-words checking that
# each was written correctly.
# If a failure occurs then stop and show 2 else show a 1 when complete.

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        count = Signal(32, reset = 0)

        # Write each data halfword for each SRAM address
        data = [0x0505, 0xa0a0, 0x0000, 0xffff]

        # -----------------------------------------------------
        # ---- BRAM
        # -----------------------------------------------------
        memAddr = Signal(3, reset = 0)
        mem = Array([Signal(16, reset=x, name="mem{}".format(i))
                    for i,x in enumerate(data)])

        # -----------------------------------------------------
        # ---- SRAM
        # -----------------------------------------------------
        # 1 Bank = 18bits : 0x00000 -> 0x3FFFF
        sramAddr = Signal(18, reset = 0)
        halfWord = Signal(16)
        SRAM_MAX_ADDR = 0x3FFF
        # Please uncomment a particular bank you want to test
        RAM_BANK = 0
        # RAM_BANK = 1

        if platform is not None:
            # This pin arrangement is for the iCESugar LED pmods.
            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 1))),
            ])

            wht_led = platform.request('led_w', 0)
            pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            # PMOD-B has status
            pmod_b = platform.request('pmod_b', 1)

            m.d.sync += count.eq(count + 1)

            m.d.comb += [
                wht_led.o.eq(count[23]),
            ]
        
            sram = platform.request('sram', RAM_BANK)

            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm

                with m.State("INIT"):
                    m.d.sync += [
                        # For this test CS is always asserted.
                        sram.cs.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle #3 (WE controlled)
                # ------------------------------------------------
                with m.State("WRITE"):
                    m.d.sync += [
                        # Write to addr:0 using data from BRAM addr:0
                        sram.a.o.eq(sramAddr),
                        sram.d.o.eq(mem[memAddr]),

                        sram.oe.o.eq(SIG_ASSERT),

                        # Enable driving the bus
                        sram.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_S1"
                with m.State("WRITE_S1"):
                    m.d.sync += [
                        sram.dm.o.eq(0b11),   # Both

                        sram.we.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_HOLD"
                with m.State("WRITE_HOLD"):
                    m.next = "WRITE_END"
                with m.State("WRITE_END"):
                    m.d.sync += [
                        sram.we.o.eq(SIG_DEASSERT),
                        sram.oe.o.eq(SIG_DEASSERT),
                        # Stop driving the bus
                        sram.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "READ"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # ------------------------------------------------
                with m.State("READ"):
                    m.d.sync += [
                        sram.dm.o.eq(0b11),

                        # Read what was just written.
                        sram.a.o.eq(sramAddr),
                        
                        sram.oe.o.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_HOLD"
                with m.State("READ_HOLD"):
                    m.next = "READ_LOAD"
                with m.State("READ_LOAD"):
                    m.d.sync += [
                        # Data valid read
                        halfWord.eq(sram.d.i[0:16]),
                    ]
                    m.next = "READ_END"
                with m.State("READ_END"):
                    m.d.sync += [
                        sram.oe.o.eq(SIG_DEASSERT),

                        # Write buf to LEDs
                        # pmod_a.o.eq(halfWord[8:16]), # Vertical pmod
                        # pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "COMPARE"

                # ------------------------------------------------
                # Compare byte read to byte that was written
                # ------------------------------------------------
                with m.State("COMPARE"):
                    # Did what we read match what was written?
                    with m.If(halfWord == mem[memAddr]):
                        # Move to the next data and potentially sram address.
                        with m.If(memAddr > 2):
                            m.d.sync += [memAddr.eq(0),]                            
                            # Have we exercised the whole bank?
                            with m.If(sramAddr == SRAM_MAX_ADDR):
                                m.next = "PASS"
                            with m.Else():
                                m.d.sync += [
                                    # pmod_a.o.eq(sramAddr[0:8]),
                                    sramAddr.eq(sramAddr + 1),
                                ]
                                m.next = "WAIT"
                        with m.Else():
                            m.d.sync += [
                                # Move to next data
                                memAddr.eq(memAddr + 1)
                            ]
                            m.next = "WAIT"
                    with m.Else():
                        m.next = "FAIL"

                with m.State("WAIT"):
                    m.d.sync += pmod_a.o.eq(sramAddr[8:18])
                    # m.d.sync += [pmod_a.o.eq(sramAddr[0:8]),]

                    with m.If(count[13]):  # 26 = ~1/2 seconds
                        m.d.sync += count.eq(0)
                        m.next = "WRITE"
                    with m.Else():
                        m.next = "WAIT"

                with m.State("PASS"):
                    m.d.sync += [
                        pmod_b.o.eq(0b11100000),
                    ]
                    m.next = "PASS"

                with m.State("FAIL"):
                    m.d.sync += [
                        pmod_a.o.eq(sramAddr[0:8]),
                        pmod_b.o.eq(0b10100000),
                    ]
                    m.next = "FAIL"
        return m

# To generate the bitstream, we build() the platform using our top level
# module m.

def builder():
    top = Top()

    # A platform contains board specific information about FPGA pin assignments,
    # toolchain and specific information for uploading the bitfile.
    platform = KeksPlatform()
    
    platform.build(top, build_dir="/media/RAMDisk/build")


if __name__ == "__main__":
    builder()
