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

    def elaborate(self, platform):
        # We need a top level module
        m = Module()

        count = Signal( 32, reset = 0 )

        m.d.sync += count.eq( count + 1 )

        if platform is not None:
            # NOTE PinsN is used instead of Pins because the LED strip
            # is negative logic and I wanted positive logic (i.e. 1 = on)
            # Individual Pins
            # platform.add_resources([
            #     Resource("pmod_b", 0, PinsN("1", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 1, PinsN("2", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 2, PinsN("3", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 3, PinsN("4", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 4, PinsN("5", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 5, PinsN("6", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 6, PinsN("7", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            #     Resource("pmod_b", 7, PinsN("8", dir="o", conn=("pmod", 1)), Attrs(IO_STANDARD="LVCMOS33")),
            # ])

            # or Grouped Pins. This is good for strips or arrays of LEDs
            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 1))),
            ])

            wht_led = platform.request( 'led_w', 0 )
            pmod_a = platform.request( 'pmod_a', 0 )
            pmod_b = platform.request( 'pmod_b', 1 )

            m.d.comb += [
                wht_led.o.eq( count[ 25 ] ),
                # pmod_b_1.o.eq( count[ 24 ] ),
                
                # pmod_b_1.o.eq(0b11111111),

                pmod_a.o.eq(Cat(
                    count[24],
                    count[25],
                    count[26],
                    count[27],
                    count[28],
                    count[29],
                    count[30],
                    count[31])),

                pmod_b.o.eq(Cat(
                    count[24],
                    count[25],
                    count[26],
                    count[27],
                    count[28],
                    count[29],
                    count[30],
                    count[31])),
            ]
        
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
