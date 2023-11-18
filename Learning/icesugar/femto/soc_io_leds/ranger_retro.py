from amaranth.build import Platform

from amaranth_boards.icesugar import ICESugarPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal

from soc import SOC

# A platform contains board specific information about FPGA pin assignments,
# toolchain and specific information for uploading the bitfile.
platform = ICESugarPlatform()

# We need a top level module
m = Module()

# This is the instance of our SOC
soc = SOC()

# The SOC is turned into a submodule (fragment) of our top level module.
m.submodules.soc = soc

if platform is not None:
    red_led = platform.request( 'led_r', 0 )
    grn_led = platform.request( 'led_g', 0 )
    blu_led = platform.request( 'led_b', 0 )

    m.d.comb += [
        red_led.o.eq(soc.leds[0]),
        grn_led.o.eq(soc.leds[1]),
        blu_led.o.eq(soc.leds[2])
    ]


# To generate the bitstream, we build() the platform using our top level
# module m.
platform.build(m, build_dir="/media/RAMDisk/build", do_program=False)
