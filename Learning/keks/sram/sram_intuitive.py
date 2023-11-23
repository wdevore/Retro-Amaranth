from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
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
        readBuf = Signal(16)
        stateBuf = Signal(8, reset=0b11111111)

        m.d.sync += count.eq( count + 1 )

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
                pmod_a.o.eq(stateBuf),
            ]
        
            sram_0 = platform.request('sram', 0)

            # Setup address. 18bits = 0b00_0000_0000_0000_0000
            # 0x00000

            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm
                with m.State("INIT"):
                    m.d.sync += [
                        sram_0.cs.o.eq(1), # DeSelect chip
                        sram_0.we.o.eq(1), # Disable write
                        sram_0.oe.o.eq(1), # Disable output
                        sram_0.dm.o[0].eq(1), # Disable lower byte
                        sram_0.dm.o[1].eq(1), # Disable upper byte
                        stateBuf.eq(0b00000001),
                    ]
                    m.next = "WRITE_A1"

                # ------------------------------------------------
                # Write cycle (CS controlled)
                # ------------------------------------------------
                with m.State("WRITE_A1"):
                    m.d.sync += [
                        # Setup address and data
                        sram_0.a.o.eq(0x00000),
                        sram_0.d.o.eq(0xdead),
                    ]
                    m.next = "WRITE_A2"
                with m.State("WRITE_A2"):
                    m.d.sync += [
                        # Enable CS
                        sram_0.cs.o.eq(0),
                        # Enable lower/upper byte mask
                        sram_0.dm.o[0].eq(0),
                        sram_0.dm.o[1].eq(0),
                        # Start driving the bus
                        sram_0.d.oe.eq(1)
                    ]
                    m.next = "WRITE_A2a"
                with m.State("WRITE_A2a"):
                    m.d.sync += [
                        # Enable write
                        sram_0.we.o.eq(0),
                    ]
                    m.next = "WRITE_A3"
                with m.State("WRITE_A3"):
                    # Delay
                    m.next = "WRITE_A4"
                with m.State("WRITE_A4"):
                    m.d.sync += [
                        # Stop driving the bus
                        sram_0.d.oe.eq(1),
                        # Disable CS (Data latched on rising edge)
                        sram_0.cs.o.eq(1),
                        # Disable lower/upper byte mask
                        sram_0.dm.o[0].eq(1),
                        sram_0.dm.o[1].eq(1),
                        # Disable write
                        sram_0.we.o.eq(1),
                    ]
                    m.next = "READ_A1"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # ------------------------------------------------
                with m.State("READ_A1"):
                    m.d.sync += [
                        # Enable CS
                        sram_0.cs.o.eq(0),
                        # Setup address
                        sram_0.a.o.eq(0x00000),
                        # Enable lower/upper byte mask
                        sram_0.dm.o[0].eq(0),
                        sram_0.dm.o[1].eq(0),
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
                        sram_0.dm.o.eq(0b11),
                        # Data valid read
                        readBuf.eq(sram_0.d.i[0:16]),
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
                        pmod_b.o.eq(readBuf[0:8]),
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
