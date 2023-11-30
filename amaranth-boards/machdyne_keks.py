import os
import subprocess

from amaranth.build import *
from amaranth.vendor.lattice_ice40 import *
from .resources import *


__all__ = ["KeksPlatform"]


class KeksPlatform(LatticeICE40Platform):
    device      = "iCE40HX8K"
    package     = "CT256"  # I added a def for CT256
    default_clk = "clk100"

    resources   = [
        Resource("clk100", 0, Pins("F7", dir="i"), Clock(100e6), Attrs(GLOBAL=True, IO_STANDARD="LVCMOS33")),

        # Single white LED
        *LEDResources(pins="A5", invert=True, attrs=Attrs(IO_STANDARD="LVCMOS33")),

        # Semantic aliases
        Resource("led_w", 0, PinsN("A5", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),

        # A single cherry keyboard button.
        *ButtonResources(pins="A6", attrs=Attrs(IO_TYPE="LVCMOS33"), invert=True),

        # PMOD resources for an 8bit LED connected to pmod B
        # Typically for PMODs you would dynamically add them via
        # platform.add_resources([...])
        # Resource("pmod_b", 0, PinsN("R16", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 1, PinsN("T15", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 2, PinsN("P13", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 3, PinsN("T11", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 4, PinsN("M12", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 5, PinsN("T16", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 6, PinsN("R10", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),
        # Resource("pmod_b", 7, PinsN("P10", dir="o"), Attrs(IO_STANDARD="LVCMOS33")),

        # SRAM: two chips each with an upper and lower banks.
        # Totaling: 2^18 * 2 = 256KB + 256KB = 512KB
        # Both combine to create a 32bit word.
        # *ub* is the inverse of *lb* to produce the virtual address bit A18.
        # If *lb* is low then lower bank is selected. If it is high then ub is low
        # and the upper bank is selected.
        # ---------------------- Bank 0 ----------------------------
        SRAMResource(0,     # Default name = "sram"
            cs_n="G3",        # All control signals are Active Low
            oe_n="F3",
            we_n="G2",
            dm_n="F4 E4",     # bank select (lower and upper)
            #  A0 ---------------------------------------------------- A17
            a="C5 C6 C7 B6 B5 B4 B3 A1 C10 C11 A10 B11 B9 A9 B10 C9 A7 A2",
            #  D0 ----------------------------------------- D5
            d="J5 H5 H6 G5 G4 F1 E2 F2 F5 D1 E3 D2 C1 B1 C2 B2",
            attrs=Attrs(IO_STANDARD="LVCMOS33"),
        ),

        # ---------------------- Bank 1 ----------------------------
        SRAMResource(1,
            cs_n="P2",
            oe_n="P1",
            we_n="M6",
            dm_n="N2 N3",
            a="C5 C6 C7 B6 B5 B4 B3 A1 C10 C11 A10 B11 B9 A9 B10 C9 A7 A2",
            d="R1 M3 M4 N4 K4 K5 L5 M5 M1 L1 M2 K1 K3 J2 J1 H1",
            attrs=Attrs(IO_STANDARD="LVCMOS33"),
        ),

        # *SPIFlashResources(0,
        #     cs_n="AA2", clk="AE3", cipo="AE2", copi="AD2", wp_n="AF2", hold_n="AE1",
        #     attrs=Attrs(IO_TYPE="LVCMOS33")
        # ),
    ]

    # The "-" dashes represent unconnected pins. In this case they are
    # power pins based on the PMOD standard.
    connectors = [
        Connector("pmod", 0, "B12 B14 B15 C14 - - A11 B13 A15 A16 - -"),    # PMOD A
        #                     D0  D1  D2  D3      D4  D6  D7  D8
        # Postion number      1   2   3   4       7   8   9   10
        Connector("pmod", 1, "R16 T15 P13 T11 - - M12 T16 R10 P10 - -"),    # PMOD B
    ]

    def toolchain_program(self, products, name):
        import os, subprocess
        tool = os.environ.get("LDPROG", "ldprog")
        with products.extract("{}.bit".format(name)) as bitstream_filename:
            subprocess.check_call([tool, '-ks', bitstream_filename])


if __name__ == "__main__":
    from .test.blinky import Blinky

    platform = KeksPlatform()

    platform.build(Blinky(), do_program=True)
