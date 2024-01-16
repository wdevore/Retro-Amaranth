from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform
from hram import HRAM
from lib.debouncer import Debouncer

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Instance, \
    ResetInserter, \
    ClockSignal, \
    ClockDomain, \
    Array, \
    Signal, \
    Cat, \
    Const

from amaranth.build import \
    Resource,\
    PinsN

from amaranth.lib.cdc import \
    ResetSynchronizer

# In this test we:
# Write to memory 0 the value 0x12345678
# Write to memory 1 the value 1122334455
# Read from memory 0 and verify
# Read from memory 1 and verify

# The next test will test modifying a single byte

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        count = Signal(32, reset = 0)
        powerUpDelay = Signal(20, reset = 0)

        # Write each data halfword for each SRAM address
        data = [0x12345678, 0x11223344, 0xffff0000, 0x0000ffff]

        # The "-" is required otherwise you get rather strange issues.
        clk_pin = platform.request(platform.default_clk, dir='-')

        lock = Signal()

        domainName = "sync"

        outClk = ClockSignal(domainName)    # Access the clock signal from "sync"
        clkDom = ClockDomain(domainName)#, reset_less=True)
        m.domains.sync = clkDom

        pll = Instance("SB_PLL40_CORE",
            p_FEEDBACK_PATH = "SIMPLE",
            p_PLLOUT_SELECT = "GENCLK",
            p_DIVR = Const(0b0000, 4),
            p_DIVF = Const(0b0000111, 7),
            # p_DIVQ = Const(0b101, 3),       # 25MHz
            p_DIVQ = Const(0b100, 3),     # 50MHz
            p_FILTER_RANGE = Const(0b101, 3),

            i_REFERENCECLK = clk_pin,
            i_BYPASS = Const(0),
            i_RESETB = Const(1),

            o_PLLOUTGLOBAL = outClk,
            o_LOCK = lock,
        )

        rstSync = ResetSynchronizer(~lock, domain = domainName)

        m.submodules += [pll, rstSync]

        # -----------------------------------------------------
        # ---- BRAM
        # -----------------------------------------------------
        memAddr = Signal(3, reset = 0)
        mem = Array([Signal(32, reset=x, name="mem{}".format(i))
                    for i,x in enumerate(data)])

        # -----------------------------------------------------
        # ---- OSPI
        # -----------------------------------------------------
        # 256Mb = 32MB => 25 address bits -> 0x0000000 -> 0x1FFFFFF
        ospiAddr = Signal(25, reset = 0)
        word = Signal(32)
        RAM_MAX_ADDR = 0x1FFFFFF

        ospi_reset     = Signal(reset=0)
        ospi_address   = Signal(32)
        ospi_wr_data   = Signal(32)
        ospi_rd_data   = Signal(32)
        ospi_ready     = Signal()
        ospi_valid     = Signal()
        ospi_wr_strb   = Signal(4)
        ospi_initng    = Signal()
        ospi_debug     = Signal(4)

        m.submodules.hram = hram = HRAM(ospi_reset, ospi_address,
                                        ospi_wr_data, ospi_rd_data,
                                        ospi_ready, ospi_valid,
                                        ospi_wr_strb,
                                        ospi_initng,
                                        ospi_debug)
        # m.submodules.hramInserter = hramInserter = ResetInserter(ospi_reset)(hram)

        if platform is not None:
            # Connect PLL's output to the "sync" domain
            m.d.comb += clkDom.clk.eq(outClk)

            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="i", conn=("pmod", 1))),
            ])

            wht_led = platform.request('led_w', 0)
            pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            # PMOD-B has status
            pmod_b = platform.request('pmod_b', 1)

            m.submodules.debouncer = debouncer = Debouncer()

            BUTTON0 = 4
            BUTTON3 = 3

            rd_data = Signal(32)
            # Low bits are higher up
            debug = Signal(8)

            m.d.sync += count.eq(count + 1)

            m.d.comb += [
                wht_led.o.eq(count[23]),
                # Connect pmod button input to debouncer
                debouncer.btn_in.eq(pmod_b.i[BUTTON3]),
                pmod_a.o.eq(debug),
            ]
        
            with m.FSM(reset="POWERUP") as fsm:
                self.fsm = fsm

                with m.State("POWERUP"):
                    m.d.sync += powerUpDelay.eq(powerUpDelay + 1)
                    with m.If(powerUpDelay[19]):
                        m.d.sync += powerUpDelay.eq(0)
                        m.next = "POWERUP1"
                    with m.Else():
                        m.next = "POWERUP"

                with m.State("POWERUP1"):
                    m.d.sync += debug.eq(Cat(Const(0b0001, 4), ospi_debug))
                    with m.If(debouncer.btn_down_out):
                        m.next = "RESET"
                    with m.Else():
                        m.next = "POWERUP1"

                with m.State("RESET"):
                    # Trigger hram reset
                    m.d.sync += ospi_reset.eq(SIG_ASSERT)
                    m.next = "RESET_END"

                with m.State("RESET_END"):
                    # Wait for hram to powerup and self reset.
                    with m.If(~ospi_initng):
                        # Now apply formal reset
                        m.d.sync += ospi_reset.eq(SIG_DEASSERT)
                        m.next = "RESET_END"
                    with m.Else():
                        m.next = "WAITING"

                with m.State("WAITING"):
                    m.d.sync += debug.eq(Cat(Const(0b1001, 4), ospi_debug))
                    with m.If(debouncer.btn_down_out):
                        m.next = "WRITE_LOC0"
                    with m.Else():
                        m.next = "WAITING"

                # ------------------------------------------------
                # Write #1
                # ------------------------------------------------
                with m.State("WRITE_LOC0"):
                    m.d.sync += [
                        ospi_address.eq(0),
                        ospi_wr_data.eq(mem[0]),
                        ospi_wr_strb.eq(0b1111),    # Write Word (32bits)
                    ]
                    # with m.If(debouncer.btn_down_out):
                    #     m.next = "WRITE_VALID0"
                    # with m.Else():
                    #     m.next = "WRITE_LOC0"
                    m.next = "WRITE_VALID0"

                with m.State("WRITE_VALID0"):
                    m.d.sync += [
                        # Indicate addr/data is valid
                        # We deassert this when "ready" flag Sets.
                        ospi_valid.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_WAIT0"

                with m.State("WRITE_WAIT0"):
                    # m.d.sync += debug.eq(Cat(Const(0b0001, 4), ospi_debug))
                    m.d.sync += ospi_valid.eq(SIG_DEASSERT)
                    # The ospi module signals completion by the rise of the
                    # "ready" signal.
                    with m.If(ospi_ready):
                        m.next = "KEY_WAIT0"
                    with m.Else():
                        m.next = "WRITE_WAIT0"

                with m.State("KEY_WAIT0"):
                    m.d.sync += debug.eq(Cat(Const(0b0010, 4), ospi_debug))
                    # m.d.sync += pmod_a.o.eq(0b00000010)
                    with m.If(debouncer.btn_down_out):
                        m.next = "WRITE_LOC1"
                    with m.Else():
                        m.next = "KEY_WAIT0"

                # ------------------------------------------------
                # Write #2
                # ------------------------------------------------
                with m.State("WRITE_LOC1"):
                    m.d.sync += [
                        ospi_address.eq(1),
                        ospi_wr_data.eq(mem[1]),
                        ospi_wr_strb.eq(0b1111),    # Write Word (32bits)
                    ]
                    m.next = "WRITE_VALID1"

                with m.State("WRITE_VALID1"):
                    m.d.sync += [
                        # Indicate addr/data is valid
                        # We deassert this when "ready" flag Sets.
                        ospi_valid.eq(SIG_ASSERT),
                    ]
                    m.next = "WRITE_WAIT1"

                with m.State("WRITE_WAIT1"):
                    m.d.sync += ospi_valid.eq(SIG_DEASSERT)
                    # m.d.sync += pmod_a.o.eq(0b00000011)
                    # Wait for the module to signal that the transfer
                    # is complete.
                    with m.If(ospi_ready):
                        m.next = "KEY_WAIT1"
                    with m.Else():
                        m.next = "WRITE_WAIT1"

                with m.State("KEY_WAIT1"):
                    m.d.sync += debug.eq(Cat(Const(0b0011, 4), ospi_debug))
                    # m.d.sync += pmod_a.o.eq(0b00000100)
                    with m.If(debouncer.btn_down_out):
                        m.next = "READ_LOC0"
                    with m.Else():
                        m.next = "KEY_WAIT1"

                # ------------------------------------------------
                # Read 0 location
                # ------------------------------------------------
                with m.State("READ_LOC0"):
                    m.d.sync += [
                        ospi_address.eq(0),
                        ospi_wr_strb.eq(0b0000),
                    ]
                    m.next = "READ_VALID0"

                with m.State("READ_VALID0"):
                    m.d.sync += [
                        # Indicate addr/data is valid
                        # We deassert this when "ready" flag Sets.
                        ospi_valid.eq(SIG_ASSERT),
                    ]
                    m.next = "READ_WAIT1"

                with m.State("READ_WAIT1"):
                    m.d.sync += debug.eq(Cat(Const(0b0100, 4), ospi_debug))
                    # Wait for the module to signal that the transfer
                    # is complete.
                    with m.If(ospi_ready):
                        m.next = "KEY_WAIT2"
                        m.d.sync += rd_data.eq(ospi_rd_data)
                    with m.Else():
                        m.next = "READ_WAIT1"

                with m.State("KEY_WAIT2"):
                    m.d.sync += debug.eq(rd_data[0:8])
                    # m.d.sync += pmod_a.o.eq(rd_data[0:8])
                    with m.If(debouncer.btn_down_out):
                        m.next = "KEY_WAIT3"
                    with m.Else():
                        m.next = "KEY_WAIT2"

                with m.State("KEY_WAIT3"):
                    m.d.sync += debug.eq(rd_data[8:17])
                    # m.d.sync += pmod_a.o.eq(rd_data[8:17])
                    with m.If(debouncer.btn_down_out):
                        m.next = "KEY_WAIT4"
                    with m.Else():
                        m.next = "KEY_WAIT3"

                with m.State("KEY_WAIT4"):
                    m.d.sync += debug.eq(rd_data[16:25])
                    # m.d.sync += pmod_a.o.eq(rd_data[16:25])
                    with m.If(debouncer.btn_down_out):
                        m.next = "KEY_WAIT5"
                    with m.Else():
                        m.next = "KEY_WAIT4"

                with m.State("KEY_WAIT5"):
                    m.d.sync += debug.eq(rd_data[24:32])
                    # m.d.sync += pmod_a.o.eq(rd_data[24:32])

                    with m.If(debouncer.btn_down_out):
                        m.next = "VALIDATE_LOC0"
                    with m.Else():
                        m.next = "KEY_WAIT5"

                # ------------------------------------------------
                # Validate data read. It should match loc 0
                # ------------------------------------------------
                with m.State("VALIDATE_LOC0"):
                    with m.If(rd_data == mem[0]):
                        m.d.sync += debug.eq(Cat(Const(0b1000, 4), ospi_debug))
                        # m.d.sync += pmod_a.o.eq(0b00001000)
                    with m.Else():
                        m.d.sync += debug.eq(Cat(Const(0b1001, 4), ospi_debug))
                        # m.d.sync += pmod_a.o.eq(0b10001001)
                    m.next = "VALIDATE_LOC0"


                # ------------------------------------------------
                # Read 1 location
                # ------------------------------------------------

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
