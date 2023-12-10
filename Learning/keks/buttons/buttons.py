from amaranth.build import Platform
from amaranth import Instance

from amaranth_boards.machdyne_keks import KeksPlatform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal, \
    Const

from amaranth.build import \
    Resource,\
    PinsN, \
    Pins

from debouncer import Debouncer

# In this test we:
# Use a debouncer for switches and buttons.

class Top(Elaboratable):
    def elaborate(self, platform: Platform) -> Module:
        m = Module()

        count = Signal(32, reset = 0)
        buttonCount = Signal(4, reset = 0)

        if platform is not None:
            # This pin arrangement is for the iCESugar LED pmods.
            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, Pins("1 2 3 4 7 8 9 10", dir="i", conn=("pmod", 1))),
            ])

            m.submodules.debouncer = debouncer = Debouncer()

            BUTTON0 = 4
            BUTTON1 = 5
            BUTTON2 = 2
            BUTTON3 = 3
            SWITCH1 = 0
            SWITCH2 = 1
            SWITCH3 = 6
            SWITCH4 = 7

            # A Sipeed PMOD with 4 buttons and 4 switches
            # is connected to PMOD_B.
            # Switch orientation: "Down" = positioned towards text
            # 7    6   1     0
            # S3  S2   S1   S0
            # --- Buttons ---
            # 3    2   5     4      <-- button index
            # B3  B2   B1   B0
            #  "PMOD-BTN 4X4"       <-- text at edge of pmod

            wht_led = platform.request('led_w', 0)
            pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            pmod_b = platform.request('pmod_b', 1)

            m.d.sync += count.eq(count + 1)

            # Connect pmod button input to debouncer
            m.d.comb += debouncer.btn_in.eq(pmod_b.i[BUTTON0])

            with m.If(debouncer.btn_down_out):
                m.d.sync += buttonCount.eq(buttonCount + 1)
                
            m.d.comb += [
                wht_led.o.eq(count[24]),
                pmod_a.o.eq(buttonCount),
            ]

            with m.If(count[25]):  # 26 = ~1/2 seconds # type: ignore
                m.d.sync += count.eq(0)

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
