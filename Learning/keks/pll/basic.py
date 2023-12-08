from amaranth.build import Platform
from amaranth import Instance

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal, \
    ClockSignal, \
    ClockDomain, \
    Const

from amaranth.lib.cdc import \
    ResetSynchronizer

from amaranth.build import \
    Resource,\
    PinsN, \
    Attrs

# In this test we:
# Use a PLL to generate a frequency of 25MHz from 100MHz
# Based on: https://github.com/crzwdjk/uniterm/blob/main/gateware/icepll.py
# See icepll.v for verilog example.

class Top(Elaboratable):
    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        lock = Signal()

        domainName = "sync"

        outClk = ClockSignal(domainName)
        clkDom = ClockDomain(domainName)#, reset_less=True)
        m.domains.sync = clkDom

        # clk_frequency = int(platform.default_clk_constraint.frequency)
        clk_pin = platform.request(platform.default_clk, dir='-')

        # Values generated by icestorm icepll tool.
        # Given input frequency:       100.000 MHz
        # Requested output frequency:   25.000 MHz
        # Achieved output frequency:    25.000 MHz
        pll = Instance("SB_PLL40_CORE",
            p_FEEDBACK_PATH = "SIMPLE",
            p_PLLOUT_SELECT = "GENCLK",
            p_DIVR = Const(0, 4),
            p_DIVF = Const(111, 7),
            p_DIVQ = Const(101, 3),
            p_FILTER_RANGE = Const(101, 3),

            i_REFERENCECLK = clk_pin,
            i_BYPASS = Const(0),
            i_RESETB = Const(1),

            o_PLLOUTGLOBAL = outClk,
            o_LOCK = lock,
        )

        rstSync = ResetSynchronizer(~lock, domain = domainName)

        m.submodules += [pll, rstSync]

        count = Signal(32, reset = 0)

        if platform is not None:
            # platform.add_resources([
            #     Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
            #     Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 1))),
            # ])

            # Connect PLL's output to the "sync" domain
            m.d.comb += [
                clkDom.clk.eq(outClk),
            ]

            wht_led = platform.request('led_w', 0)
            # pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            # PMOD-B has status
            # pmod_b = platform.request('pmod_b', 1)

            with m.If(count[13]):  # 26 = ~1/2 seconds
                m.d.sync += count.eq(0)

            m.d.sync += [
                count.eq(count + 1),
            ]

            m.d.comb += [
                wht_led.o.eq(count[3]),
                # pmod_b.o.eq(0b10100000),
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
