from amaranth.build import Platform

from amaranth_boards.icesugar import ICESugarPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal

# A platform contains board specific information about FPGA pin assignments,
# toolchain and specific information for uploading the bitfile.
platform = ICESugarPlatform()

# We need a top level module
m = Module()

count = Signal( 32, reset = 0 )

m.d.sync += count.eq( count + 1 )

if platform is not None:
    grn_led = platform.request( 'led_r', 0 )
    blu_led = platform.request( 'led_b', 0 )
    m.d.comb += [
        grn_led.o.eq( count[ 20 ] ),
        blu_led.o.eq( ~grn_led.o )
    ]


# To generate the bitstream, we build() the platform using our top level
# module m.

platform.build(m, build_dir="/media/RAMDisk/build")
