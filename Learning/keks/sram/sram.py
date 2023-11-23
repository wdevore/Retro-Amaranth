from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Array, \
    Signal, \
    Cat, \
    Repl

from amaranth.build import \
    Resource,\
    PinsN, \
    Attrs

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        count = Signal(32, reset = 0)
        halfWord = Signal(16)
        stateBuf = Signal(8, reset=0b11111111)

        # This increments when count[27] is set
        memAddr = Signal(5, reset = 0)

        m.d.sync += count.eq(count + 1)

        data = [0x1122, 0xdead, 0xbeaf, 0x0101, 0x1010, 0x0a0a, 0xa0a0]
        
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

            m.d.comb += [
                wht_led.o.eq(count[ 23 ]),
                # pmod_a.o.eq(stateBuf),
            ]
        
            sram_0 = platform.request('sram', 0)

            # Setup address. 18bits = 0b00_0000_0000_0000_0000
            # 0x00000 -> 0x3FFFF

            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm
                with m.State("INIT"):
                    m.d.sync += [
                        sram_0.cs.o.eq(1), # DeSelect chip
                        sram_0.we.o.eq(1), # Disable write
                        sram_0.oe.o.eq(1), # Disable output
                        # Disable write mask
                        sram_0.dm.o.eq(0b00),
                        # Stop driving the bus (i.e. careen off the cliff ;-)
                        sram_0.d.oe.eq(1),
                    ]
                    m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle (CS controlled)
                # ------------------------------------------------
                with m.State("WRITE"):
                    m.d.sync += [
                        # Setup address and data
                        sram_0.a.o.eq(memAddr),
                        sram_0.d.o.eq(mem[memAddr]),
                    ]
                    m.next = "WRITE_BEGIN"
                with m.State("WRITE_BEGIN"):
                    m.d.sync += [
                        # Enable CS
                        sram_0.cs.o.eq(0),
                        # Enable lower and upper byte write mask
                        sram_0.dm.o.eq(0b11),
                        # Start driving the bus
                        sram_0.d.oe.eq(1)
                    ]
                    m.next = "WRITE_WE"
                with m.State("WRITE_WE"):
                    m.d.sync += [
                        # Enable write
                        sram_0.we.o.eq(0),
                    ]
                    m.next = "WRITE_END"
                with m.State("WRITE_END"):
                    m.d.sync += [
                        # Stop driving the bus
                        sram_0.d.oe.eq(1),
                        # Disable CS (Data latched on rising edge)
                        sram_0.cs.o.eq(1),
                        # Disable lower and upper byte write mask
                        sram_0.dm.o.eq(0b00),
                        # Disable write
                        sram_0.we.o.eq(1),
                    ]
                    m.next = "READ"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # ------------------------------------------------
                with m.State("READ"):
                    m.d.sync += [
                        # Enable CS
                        sram_0.cs.o.eq(0),
                        # Setup address
                        sram_0.a.o.eq(0x00000),
                        # Enable lower/upper byte mask
                        sram_0.dm.o.eq(0b11),
                    ]
                    m.next = "READ_A2"
                with m.State("READ_A2"):
                    m.d.sync += [
                        # Lower OE to start read cycle
                        sram_0.oe.o.eq(0),
                    ]
                    m.next = "READ_A3a"
                with m.State("READ_A3a"):
                    # m.d.sync += [
                    # ]
                    m.next = "READ_A3"
                with m.State("READ_A3"):
                    m.d.sync += [
                        # Disable CS
                        sram_0.cs.o.eq(1),
                        # Disable lower/upper byte mask
                        # sram_0.dm.o[0].eq(1),
                        # sram_0.dm.o[1].eq(1),
                        sram_0.dm.o.eq(0b00),
                        # Data valid read
                        halfWord.eq(sram_0.d.i[0:16]),
                    ]
                    m.next = "READ_A4"
                with m.State("READ_A4"):
                    m.d.sync += [
                        # Raise OE to complete read cycle
                        sram_0.oe.o.eq(1),
                    ]
                    m.next = "READ_A5"
                with m.State("READ_A5"):
                    m.d.sync += [
                        stateBuf.eq(0b10000001),
                        # Write buf to LEDs
                        pmod_a.o.eq(halfWord[8:17]),
                        pmod_b.o.eq(halfWord[0:8]),
                    ]
                    m.next = "READ_A5"


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
