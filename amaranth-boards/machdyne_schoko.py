import os
import subprocess

from amaranth.build import *
from amaranth.vendor.lattice_ecp5 import *
from .resources import *


__all__ = ["SchokoPlatform"]


class SchokoPlatform(LatticeECP5Platform):
    device      = "LFE5U-45F"
    package     = "BG256"
    speed       = "6"
    default_clk = "clk48"

    resources   = [
        Resource("clk48", 0, Pins("A7", dir="i"), Clock(48e6), Attrs(IO_TYPE="LVCMOS33")),

        # Single component with 3 LEDs
        *LEDResources(pins="B1 C1 D1", invert=True, attrs=Attrs(IO_STANDARD="LVCMOS33")),

        # Semantic aliases
        Resource("led_r", 0, PinsN("B1", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        Resource("led_g", 0, PinsN("C1", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        Resource("led_b", 0, PinsN("D1", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),

        # UARTResource(0,
        #     rx="R26", tx="R24",
        #     attrs=Attrs(IO_TYPE="LVCMOS33", PULLMODE="UP")
        # ),

        # *SPIFlashResources(0,
        #     cs_n="AA2", clk="AE3", cipo="AE2", copi="AD2", wp_n="AF2", hold_n="AE1",
        #     attrs=Attrs(IO_TYPE="LVCMOS33")
        # ),
    ]

    connectors = [
        Connector("pmod", 0, "A2  A3  A4  A5  - - B3 B4  B5 A6 - -"),    # PMOD A
        Connector("pmod", 1, "A12 A11 B11 B10 - - A9 A10 B8 B9 - -"),    # PMOD B
    ]

    def toolchain_program(self, products, name):
        import os, subprocess
        tool = os.environ.get("OPENFPGALOADER", "openFPGALoader")
        with products.extract("{}.bit".format(name)) as bitstream_filename:
            subprocess.check_call([tool, '-c', 'ft2232', '-m', bitstream_filename])


if __name__ == "__main__":
    from .test.blinky import Blinky

    platform = SchokoPlatform()

    platform.build(Blinky(), do_program=True)
