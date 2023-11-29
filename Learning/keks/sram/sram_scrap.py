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
        sram_0_wrlb = Signal()
        sram_0_wrub = Signal()
        sram_1_wrlb = Signal()
        sram_1_wrub = Signal()

        # This increments when count[27] is set
        memAddr = Signal(5, reset = 0)

        # Address = 18bits = 0b00_0000_0000_0000_0000
        #           0x00000 -> 0x3FFFF


        data = [0x5678, 0xdead, 0xbeaf, 0x0101, 0x1010, 0x0a0a, 0xa0a0]
        
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

            m.d.comb += [
                sram_wr.eq(sram_0_wrlb | sram_0_wrub | sram_1_wrlb | sram_1_wrub),
                
                sram_0_we.eq((sram_0_wrlb | sram_0_wrub)),
                sram_0.d.oe.eq(sram_wr),
                #                    LB            UB
                # sram_0.dm.o.eq(Cat(sram_0_wrlb, sram_0_wrub)),
            ]

            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm

                m.d.sync += [
                    # Default strobes
                    sram_0_wrub.eq(SIG_DEASSERT),
                    sram_0_wrlb.eq(SIG_DEASSERT),
                ]

                with m.State("INIT"):
                    m.d.sync += [
                        # For this test CS is always asserted.
                        sram_0.cs.o.eq(SIG_ASSERT),

                        # Stop driving the bus
                        # sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle
                # ------------------------------------------------
                with m.State("WRITE"):
                    m.d.sync += [
                        # Setup write strobes
                        # 0010 = only 0x56 is written
                        mem_wstrb.eq(0b0010),
                    ]
                    m.next = "WRITE_S1"
                with m.State("WRITE_S1"):
                    m.d.sync += [
                        # Setup data masks
                        sram_0_wrub.eq(mem_wstrb[1]),
                        sram_0_wrlb.eq(mem_wstrb[0]),
                        sram_0.dm.o.eq(Cat(mem_wstrb[0], mem_wstrb[1])),
                        
                        # Setup address and data
                        sram_0.a.o.eq(memAddr),
                        sram_0.d.o.eq(mem[memAddr]),

                        sram_0.we.o.eq(sram_wr),

                        # Start driving the bus
                        # sram_0.d.oe.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_END"
                with m.State("WRITE_END"):
                    m.d.sync += [
                        mem_wstrb.eq(0b0000),
                        sram_0.dm.o.eq(Cat(mem_wstrb[0], mem_wstrb[1])),
                        # Stop driving the bus
                        # sram_0.d.oe.eq(SIG_DEASSERT),
                    ]
                    m.next = "READ"

                # ------------------------------------------------
                # Read cycle
                # ------------------------------------------------
                with m.State("READ"):
                    m.d.sync += [
                        mem_wstrb.eq(0b0000),
                        # Setup address
                        sram_0.a.o.eq(memAddr),
                    ]
                    m.next = "READ_S1"
                with m.State("READ_S1"):
                    m.d.sync += [
                        sram_0.dm.o.eq(0b10), # Read only LB
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
                        stateBuf.eq(0b10000001),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:17]), # Vertical pmod
                        pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "READ_S2"


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
