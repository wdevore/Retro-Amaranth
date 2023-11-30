from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Array, \
    Signal, \
    Cat, \
    Repl, \
    Const

from amaranth.build import \
    Resource,\
    PinsN, \
    Attrs

# In this test we:
# 1) attempt to use the Verilog combinatorial approach

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        count = Signal(32, reset = 0)
        halfWord = Signal(16)

        sram0_wrlb = Signal()
        sram0_wrub = Signal()
        
        sram0_CE = Signal()
        sram0_WE = Signal()
        sram0_OE = Signal()
        sram0_LB = Signal()
        sram0_UB = Signal()

        mem_wstrb = Signal(2)

        # mem_wstrb = 0b0001    # sram 0 LB selected
        # mem_wstrb = 0b0011    # sram 0 LB and UB selected
        # etc.
        # mem_wstrb = Signal(4, reset=0b0000)   # Active high signals

        # This increments when count[27] is set
        memAddr = Signal(5, reset = 0)

        # Address = 18bits = 0b00_0000_0000_0000_0000
        #           0x00000 -> 0x3FFFF

        data = [0x1234, 0x9a5b, 0x4321, 0xbeaf, 0xdead, 0x0101, 0x1010, 0x0a0a, 0xa0a0]

        mem = Array([Signal(16, reset=x, name="mem{}".format(i))
                    for i,x in enumerate(data)])

        if platform is not None:
            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 1))),
            ])

            wht_led = platform.request('led_w', 0)
            pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            pmod_b = platform.request('pmod_b', 1)

            m.d.sync += count.eq(count + 1)

            sram_0 = platform.request('sram', 0)

            m.d.comb += [
                wht_led.o.eq(count[23]),

                # WE needs to hold for two cycles which means
                # wrlb and wrub should hold two cycles.
                sram0_WE.eq(sram0_wrlb | sram0_wrub),
                sram0_OE.eq(sram0_WE),

                sram0_LB.eq(sram0_wrlb),
                sram0_UB.eq(sram0_wrub),

                sram_0.we.o.eq(sram0_WE),
                sram_0.oe.o.eq(sram0_OE),
            ]
        
            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm

                # m.d.sync += [
                #     sram0_wrlb.eq(SIG_DEASSERT),
                #     sram0_wrub.eq(SIG_DEASSERT),
                # ]

                with m.State("INIT"):
                    m.d.sync += [
                        # For this test CS is always asserted.
                        sram_0.cs.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle #3 (WE controlled)
                # Writes 0x1234
                # ------------------------------------------------
                with m.State("WRITE"):
                    m.d.sync += [
                        # Write to addr:0 using data from BRAM addr:0
                        sram_0.a.o.eq(memAddr),
                        sram_0.d.o.eq(mem[memAddr]),

                        # sram_0.oe.o.eq(sram0_OE),
                        # Strobes initiate write sequence.
                        sram0_wrlb.eq(1),
                        sram0_wrub.eq(1),
                        sram_0.dm.o.eq(Cat(sram0_UB,sram0_LB)),   # Ub, Lb

                        # Enable driving the bus
                        sram_0.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_S1"
                with m.State("WRITE_S1"):
                    m.next = "WRITE_S2"
                with m.State("WRITE_S2"):
                    m.next = "WRITE_END"
                with m.State("WRITE_END"):
                    m.d.sync += [
                        # sram_0.we.o.eq(sram0_WE),
                        # sram_0.oe.o.eq(sram0_OE),
                        sram0_wrlb.eq(0),
                        sram0_wrub.eq(0),

                        # Stop driving the bus
                        sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "WRITE_2"
                    # m.next = "READ"

                # ------------------------------------------------
                # Write cycle #3 (WE controlled)
                # Writes 0xbeaf
                # ------------------------------------------------
                with m.State("WRITE_2"):
                    m.d.sync += [
                        # Write to addr:1 using data from BRAM addr:1
                        sram_0.a.o.eq(memAddr+1),
                        sram_0.d.o.eq(mem[memAddr+1]),

                        # sram_0.oe.o.eq(SIG_ASSERT),
                        sram0_wrlb.eq(1),
                        sram0_wrub.eq(1),
                        sram_0.dm.o.eq(Cat(sram0_UB,sram0_LB)),   # Ub, Lb

                        # Enable driving the bus
                        sram_0.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_2_S1"
                with m.State("WRITE_2_S1"):
                    m.next = "WRITE_2_S2"
                with m.State("WRITE_2_S2"):
                    m.next = "WRITE_2_END"
                with m.State("WRITE_2_END"):
                    m.d.sync += [
                        # sram_0.we.o.eq(SIG_DEASSERT),
                        # sram_0.oe.o.eq(SIG_DEASSERT),
                        sram0_wrlb.eq(0),
                        sram0_wrub.eq(0),
                        # Stop driving the bus
                        sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "READ"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # Read address 0 = 0x1234
                # ------------------------------------------------
                with m.State("READ"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b11),

                        # Setup address
                        sram_0.a.o.eq(memAddr),
                        
                        # sram_0.oe.o.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_S2a"
                with m.State("READ_S2a"):
                    m.next = "READ_S2"
                with m.State("READ_S2"):
                    m.d.sync += [
                        # Data valid read
                        halfWord.eq(sram_0.d.i[0:16]),
                    ]
                    m.next = "READ_S3"
                with m.State("READ_S3"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b11),

                        # sram_0.oe.o.eq(SIG_DEASSERT),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:16]), # Vertical pmod
                        pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "WAIT_1"
                with m.State("WAIT_1"):
                    with m.If(count[29]):  # ~4 seconds
                        m.next = "READ_2"
                    with m.Else():
                        m.next = "WAIT_1"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # Should read 0xbeaf = 1011_1110_1010_1111
                # NOTE You need to have two 8bit pmod LED plugged into
                # pmod A and B.
                # ------------------------------------------------
                with m.State("READ_2"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b11),

                        # Setup address
                        sram_0.a.o.eq(memAddr+1),
                        
                        # sram_0.oe.o.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_2_S2a"
                with m.State("READ_2_S2a"):
                    m.next = "READ_2_S2"
                with m.State("READ_2_S2"):
                    m.d.sync += [
                        # Data valid read
                        halfWord.eq(sram_0.d.i[0:16]),
                    ]
                    m.next = "READ_2_S3"
                with m.State("READ_2_S3"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b11),

                        # sram_0.oe.o.eq(SIG_DEASSERT),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:16]), # Vertical pmod
                        pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "HOLD"
                with m.State("HOLD"):
                    m.next = "HOLD"                        

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
