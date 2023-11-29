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
# 1) write a lower byte and read
# 2) write an upper byte
# 3) read upper/lower and it should equal #1 and #2 combined

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        ZERO_BYTES = Const(0b00, 2)
        UPPER_BYTE = Const(0b01, 2)
        LOWER_BYTE = Const(0b10, 2)
        BOTH_BYTES = Const(0b11, 2)

        count = Signal(32, reset = 0)
        halfWord = Signal(16)
        stateBuf = Signal(8, reset=0b11111111)

        sram_0_we = Signal()
        sram_0_oe = Signal()
        
        sram_wr = Signal()

        # mem_wstrb = 0b0001    # sram 0 LB selected
        # mem_wstrb = 0b0011    # sram 0 LB and UB selected
        # etc.
        mem_wstrb = Signal(4, reset=0b0000)   # Active high signals

        # This increments when count[27] is set
        memAddr = Signal(5, reset = 0)

        # Address = 18bits = 0b00_0000_0000_0000_0000
        #           0x00000 -> 0x3FFFF

        data = [0x5678, 0xdead, 0xbeaf, 0x0101, 0x1010, 0x0a0a, 0xa0a0]
        # wr_data = Signal(16)

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

            m.d.comb += [
                wht_led.o.eq(count[23]),
            ]
        
            sram_0 = platform.request('sram', 0)

            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm

                with m.State("INIT"):
                    m.d.sync += [
                        # For this test CS is always asserted.
                        sram_0.cs.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle (WE controlled)
                # Writes 0x78
                # ------------------------------------------------
                with m.State("WRITE"):
                    m.d.sync += [
                        # Write to addr:0 using data from BRAM addr:0
                        sram_0.a.o.eq(memAddr),
                        sram_0.d.o.eq(mem[memAddr]),

                        # Setup data mask
                        # 10 = Vert(pmod A) = UB 
                        # 01 = (pmod B) = LB = 78
                        sram_0.dm.o.eq(0b01),
                        
                        sram_0.oe.o.eq(SIG_DEASSERT),

                        # Enable driving the bus
                        sram_0.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_S1"
                with m.State("WRITE_S1"):
                    m.d.sync += [
                        sram_0.we.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_END"
                with m.State("WRITE_END"):
                    m.d.sync += [
                        sram_0.we.o.eq(SIG_DEASSERT),
                        sram_0.oe.o.eq(SIG_DEASSERT),
                        # Stop driving the bus
                        sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "READ"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # ------------------------------------------------
                with m.State("READ"):
                    m.d.sync += [
                        # If either are 0 then Read latches both bytes
                        # which doesn't seem correct according to the
                        # specs. The specs timinig diagram indicates
                        # that is correct, but the truth table indicates
                        # it is not.
                        sram_0.dm.o.eq(0b11),

                        # Setup address
                        sram_0.a.o.eq(memAddr),
                        
                        sram_0.oe.o.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_S2"
                with m.State("READ_S2"):
                    m.d.sync += [
                        # Data valid read
                        halfWord.eq(sram_0.d.i[0:16]),
                    ]
                    m.next = "READ_S3"
                with m.State("READ_S3"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b00),

                        sram_0.oe.o.eq(SIG_DEASSERT),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:17]), # Vertical pmod
                        pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "WAIT_1"
                with m.State("WAIT_1"):
                    with m.If(count[29]):  # ~4 seconds
                        memAddr.eq(memAddr + 1)
                        m.next = "WRITE_UPPER"
                    with m.Else():
                        m.next = "WAIT_1"

                # ------------------------------------------------
                # Writes 0xad from second halfword
                # ------------------------------------------------
                with m.State("WRITE_UPPER"):
                    m.d.sync += [
                        # Write to addr:0 using data from BRAM addr:1
                        sram_0.a.o.eq(memAddr),
                        sram_0.d.o.eq(mem[memAddr+1]),

                        # Setup data mask
                        # 10 = Vert(pmod A) = UB  0xde
                        # 01 = (pmod B) = LB
                        sram_0.dm.o.eq(0b10),
                        
                        sram_0.oe.o.eq(SIG_DEASSERT),

                        # Enable driving the bus
                        sram_0.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_UPPER_S1"
                with m.State("WRITE_UPPER_S1"):
                    m.d.sync += [
                        sram_0.we.o.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_UPPER_END"
                with m.State("WRITE_UPPER_END"):
                    m.d.sync += [
                        sram_0.we.o.eq(SIG_DEASSERT),
                        sram_0.oe.o.eq(SIG_DEASSERT),
                        # Stop driving the bus
                        sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "READ_BOTH"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # Should read 0xde78
                # ------------------------------------------------
                with m.State("READ_BOTH"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b11),

                        # Setup address
                        sram_0.a.o.eq(memAddr),
                        
                        sram_0.oe.o.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_BOTH_S2"
                with m.State("READ_BOTH_S2"):
                    m.d.sync += [
                        # Data valid read
                        halfWord.eq(sram_0.d.i[0:16]),
                    ]
                    m.next = "READ_BOTH_S3"
                with m.State("READ_BOTH_S3"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b00),

                        sram_0.oe.o.eq(SIG_DEASSERT),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:17]), # Vertical pmod
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
