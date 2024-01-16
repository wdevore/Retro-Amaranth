from amaranth.build import Platform

from hram import HRAM
from lib.clockworks import Clockworks

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    ClockSignal, \
    Array, \
    Signal, \
    Cat, \
    Const

class Top(Elaboratable):

    def __init__(self):
        # Signals in this list can easily be plotted as vcd traces
        self.ports = []

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        cw = Clockworks(slow=19, sim_slow=5)

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        m.submodules.cw = cw

        count = Signal(32, reset = 0)
        powerUpDelay = Signal(20, reset = 0)

        # Write each data halfword for each SRAM address
        data = [0x12345678, 0x11223344, 0xffff0000, 0x0000ffff]

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

        rd_data = Signal(32)
        # Low bits are higher up
        debug = Signal(8)

        m.d.sync += count.eq(count + 1)

        with m.FSM(reset="POWERUP") as fsm:
            self.fsm = fsm

            with m.State("POWERUP"):
                m.d.sync += powerUpDelay.eq(powerUpDelay + 1)
                with m.If(powerUpDelay[5]):
                    m.d.sync += powerUpDelay.eq(0)
                    m.next = "RESET"
                with m.Else():
                    m.next = "POWERUP"

            with m.State("RESET"):
                # Trigger hram reset
                m.d.sync += ospi_reset.eq(SIG_ASSERT)
                m.next = "RESET_END"

            with m.State("RESET_END"):
                m.d.sync += ospi_reset.eq(SIG_DEASSERT)
                # Wait for hram to powerup and self reset.
                with m.If(ospi_initng):
                    # Now apply formal reset
                    m.next = "RESET_END"
                with m.Else():
                    m.next = "WRITE_LOC0"

            # ------------------------------------------------
            # Write #1
            # ------------------------------------------------
            with m.State("WRITE_LOC0"):
                m.d.sync += [
                    ospi_address.eq(0x12345678),
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
                    m.next = "WRITE_LOC1"
                with m.Else():
                    m.next = "WRITE_WAIT0"

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
                    m.next = "READ_LOC0"
                with m.Else():
                    m.next = "WRITE_WAIT1"

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
                m.next = "KEY_WAIT3"

            with m.State("KEY_WAIT3"):
                m.d.sync += debug.eq(rd_data[8:17])
                m.next = "KEY_WAIT4"

            with m.State("KEY_WAIT4"):
                m.d.sync += debug.eq(rd_data[16:25])
                m.next = "KEY_WAIT5"

            with m.State("KEY_WAIT5"):
                m.d.sync += debug.eq(rd_data[24:32])
                # m.d.sync += pmod_a.o.eq(rd_data[24:32])
                m.next = "VALIDATE_LOC0"

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
        
        if platform is None:
            # Export signals for simulation
            def export(signal, name):
                if type(signal) is not Signal:
                    newsig = Signal(signal.shape(), name = name)
                    m.d.comb += newsig.eq(signal)
                else:
                    newsig = signal
                self.ports.append(newsig)
                setattr(self, name, newsig)
                
            export(ClockSignal("slow"), "slow_clk")


        return m

