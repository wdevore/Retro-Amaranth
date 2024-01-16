# 
#  HRAM
#  Copyright (c) 2021 Lone Dynamics Corporation. All rights reserved.
# 
#  Verilog module for APSxxxXXN DDR Octal SPI PSRAM.
# 
#  TODO: support X16 mode
#
# Ported to Amaranth by iPostHuman

# OSPI is a type of HyperRam

from tokenize import String
from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal, \
    Cat, \
    Const, \
    Mux

from ospi_sim import OSPI_SIM

class HRAM(Elaboratable):
    """An interface for a Double-Data-Rate Octal SPI PSRAM.

    OSPI ram {256Mb = 32MB => 25 address bits -> 0x0000000 -> 0x1FFFFFF}
    
    Attributes:
    -----------
        ```txt
        clk   : (I)   System clock
        reset : (I)   Reset (active low)
        addr  : (I)   Address 32bits (only 25 bits needed)
        wdata : (I)   Data to write (32 bits)
        rdata : (O)   Data read (32 bits)
        ready : (O)   The signal is an active (high) strobe and
                      indicates that read data is correct.
                      The host needs to deassert *valid* to reset
                      the *ready* signal.
        valid : (I)   The signal is an active (high) strobe and
                      indicates the address/data is correct
                      and memory should begin a read/write.
        wstrb : (I)   Write strobe/mask (4 bits)
        initng: (O)   Active (high).
                      Device is resetting and configuring.
        ```
    """

    def __init__(self,
                    reset: Signal,
                    addr: Signal, wdata: Signal, rdata: Signal,
                    ready: Signal, valid: Signal, wstrb: Signal,
                    initng: Signal,
                    debug: Signal,
                ):
        
        # --- Ports ---
        self.reset     = reset
        self.address   = addr
        self.wr_data   = wdata
        self.rd_data   = rdata
        self.ready     = ready  # Handshake signal to --> host
        self.valid     = valid  # Handshake signal from <-- host
        self.wr_strb   = wstrb
        self.initng    = initng

        # --- DEBUGGING ---
        self.ports = []
        self.debug = debug

    def elaborate(self,  platform: Platform) -> Module:
        m = Module()

        # Amaranth positive logic (1 = assert)
        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)
        CMD_SYNC_READ = Const(0x00000000, 32)
        CMD_SYNC_WRITE = Const(0x80000000, 32)

        # Buffer to capture 
        buffer = Signal(32)
        target_hit = Signal(4, reset=0)

        reset_ctr = Signal(4, reset=0)
        # Latency counter
        lc_ctr = Signal(3, reset=0)
        # alternate
        data_out = Signal()

        # Active high when any write mask bit is set.
        write = Signal()

        spi_clk   = Signal(reset=0)

        if platform is not None:
            ospi = platform.request('ospi_psram')
        else:
            ospi = OSPI_SIM()

        m.submodules += ospi

        m.d.comb += [
            write.eq(self.wr_strb.any()),
            ospi.clk.eq(spi_clk),
        ]

        m.d.sync += self.debug.eq(target_hit)

        with m.FSM(reset="POWERUP") as fsm:
            self.fsm = fsm

            with m.State("POWERUP"):
                m.d.sync += self.initng.eq(SIG_ASSERT)
                # m.d.sync += self.db_fsm_state.eq(0b0101)
                
                # m.d.sync += target_hit.eq(target_hit + 1)
                # m.d.sync += self.debug.eq(0b0001)

                # Device requires anything from 500us to 1ms to
                # enter normal operation.
                # TODO Calculate delay based on system clock
                with m.If(self.reset):
                    m.next = "RESET"
                with m.Else():
                    m.next = "POWERUP"

            with m.State("RESET"):
                # m.d.sync += target_hit.eq(target_hit + 1)
                # m.d.sync += self.debug.eq(0b0010)
                # Global reset is 4 clock cycles (8 edges) with CS active 
                m.d.sync += [
                    spi_clk.eq(0), # Setup for rising edge
                    # 0xFF is read only on the first clock.
                    buffer.eq(0xFFFFFFFF),   # Preset to F's = Cmd reset
                    reset_ctr.eq(0),         # Clear clock transfer counter
                    ospi.cs.eq(SIG_ASSERT),
                    # -------------------------------
                    # 1 = output buffer driver enabled
                    # 0 = buffer output high-Z
                    # -------------------------------
                    # Begin driving PIN
                    ospi.adq.oe.eq(0xFF),
                    # strobe/mask OE PIN switch to (not driving)
                    # 1 = driven, 0 = not-driven (high-Z)
                    ospi.dqsdm.oe.eq(0b00),
                    # Default to non-active
                    self.ready.eq(SIG_DEASSERT),
                ]
                m.next = "RESET_COMPLETE"

            with m.State("RESET_COMPLETE"):
                # m.d.sync += target_hit.eq(0b1010)
                # m.d.sync += self.debug.eq(0b0011)
                # Generate 4 clocks (8 edges) to complete reset
                with m.If(reset_ctr == 8):
                    # m.d.sync += target_hit.eq(target_hit + 1)
                    m.d.sync += [
                        self.initng.eq(SIG_DEASSERT),
                        reset_ctr.eq(0),
                        ospi.cs.eq(SIG_DEASSERT),
                    ]
                    m.next = "IDLE"
                with m.Else():
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),   # Toggle clock
                        reset_ctr.eq(reset_ctr + 1),
                    ]
                    m.next = "RESET_COMPLETE"

            with m.State("IDLE"):
                m.d.sync += target_hit.eq(0b1100)
                # m.d.sync += target_hit.eq(target_hit | 0b1000)
                m.d.sync += [
                    # 1 = driven, 0 = not-driven (high-Z)
                    # Stop driving PIN
                    ospi.adq.oe.eq(0x00),
                    ospi.cs.eq(SIG_DEASSERT),
                ]

                # Wait for the "valid" signal to start a transfer.
                # The "ready" flag is cleared by the host via the
                # "valid" flag deasserting.
                with m.If(self.valid & ~self.ready):
                    with m.If(write):
                        m.d.sync += [
                            # Copy data to buffer for transmission
                            buffer.eq(self.wr_data),
                        ]
                    m.next = "INIT"     # Initiate transfer
                with m.Elif(~self.valid & self.ready):
                    # The host has deasserted the "valid" flag, now
                    # clear "ready" signal and remain in IDLE
                    # waiting for a new "valid" signal.
                    m.d.sync += self.ready.eq(SIG_DEASSERT)
                    m.next = "IDLE"
                with m.Else():
                    m.next = "IDLE"

            # Initialize for a transfer.
            with m.State("INIT"):
                # m.d.sync += target_hit.eq(0b0000)
                m.d.sync += [
                    spi_clk.eq(0), # Setup for a starting rising edge
                ]
                m.next = "START"

            with m.State("START"):
                m.d.sync += [
                    spi_clk.eq(0), # Setup for a starting rising edge
                    # addr/data OE PIN switch to (driving)
                    # 1 = driven, 0 = not-driven (high-Z)
                    ospi.adq.oe.eq(0xFF),

                    ospi.cs.eq(SIG_ASSERT), # Start transfer (aka exit standby)
                ]
                m.next = "CMD"

            # ------------------------------------------
            # Set command instruction for Read OR Write
            # ------------------------------------------
            with m.State("CMD"):
                m.d.sync += buffer.eq(Mux(write, CMD_SYNC_WRITE, CMD_SYNC_READ))
                m.next = "CMD_INSTR"

            with m.State("CMD_INSTR"):
                m.d.sync += [
                    # Place instruction byte on bus.
                    ospi.adq.o[0:8].eq(buffer[24:32]),
                    buffer.eq(Cat(0x00, buffer)),
                ]
                m.next = "CMD_EDGE_R"

            with m.State("CMD_EDGE_R"):
                m.d.sync += spi_clk.eq(~spi_clk)   # Rise
                m.next = "CMD_EDGE_R2"

            with m.State("CMD_EDGE_R2"):
                m.next = "CMD_EDGE_F"

            with m.State("CMD_EDGE_F"):
                m.d.sync += spi_clk.eq(~spi_clk)   # Fall
                m.d.sync += buffer.eq(self.address)
                m.next = "ADDR_BUFFER"

            # ------------------------------------------
            # Address
            # ------------------------------------------
            # TODO This can be combined with the next state
            with m.State("ADDR_BUFFER"):
                m.d.sync += buffer.eq(self.address)
                m.d.sync += [
                    # 31     24  23    16  15      8  7      0  :Verilog right to left
                    # 000000000__00000000__000000000__00000000
                    # 0:8        8:17      16:25      24:32     :Amaranth left to right
                    # Last                            First
                    ospi.adq.o[0:8].eq(buffer[24:32]),     # MSB's first
                ]
                m.next = "ADDR_ADQ"

            with m.State("ADDR_ADQ"):
                m.d.sync += spi_clk.eq(~spi_clk)    # A3 Rising
                m.next = "ADDR_ADQ_ST"

            with m.State("ADDR_ADQ_ST"):
                m.next = "ADDR_EDGE_E1"

            with m.State("ADDR_EDGE_E1"):
                m.d.sync += spi_clk.eq(~spi_clk)    # A3 Rising
                m.next = "ADDR_EDGE_E2"

            with m.State("ADDR_EDGE_E2"):
                m.d.sync += ospi.adq.o[0:8].eq(buffer[16:25]),  # Next byte
                m.next = "ADDR_EDGE_E3"

            with m.State("ADDR_EDGE_E3"):
                m.d.sync += spi_clk.eq(~spi_clk)    # A2 Falling
                m.next = "ADDR_EDGE_E4"

            with m.State("ADDR_EDGE_E4"):
                m.d.sync += ospi.adq.o[0:8].eq(buffer[8:17]),  # Next byte
                m.next = "ADDR_EDGE_E5"

            with m.State("ADDR_EDGE_E5"):
                m.d.sync += spi_clk.eq(~spi_clk)    # A1 Rising
                m.next = "ADDR_EDGE_E6"

            with m.State("ADDR_EDGE_E6"):
                m.d.sync += ospi.adq.o[0:8].eq(buffer[0:8]),  # Last byte
                m.next = "ADDR_EDGE_END"

            with m.State("ADDR_EDGE_END"):
                m.d.sync += spi_clk.eq(~spi_clk)    # A0 Falling
                # =============================
                # Read Or Write?
                # =============================
                with m.If(write):
                    m.d.sync += [
                        lc_ctr.eq(0),
                        # addr/data OE PIN switch to (driving)
                        # 1 = driven, 0 = not-driven (high-Z)
                        ospi.adq.oe.eq(0xFF),

                        # strobe/mask OE PIN switch to (driving)
                        ospi.dqsdm.oe.eq(0b11),
                        data_out.eq(0),    # Start with clock (Rising)
                    ]
                    m.next = "WRITE_LATENCY"
                with m.Else(): # Read
                    # strobe/mask OE PIN switch to (not driving)
                    # 1 = driven, 0 = not-driven (high-Z)
                    m.d.sync += ospi.dqsdm.oe.eq(0b00)
                    m.next = "READ_DQ_WAIT"

            # ------------------------------------------
            # Read data
            # ------------------------------------------
            with m.State("READ_DQ_WAIT"):
                # Clock must continue while waiting.
                m.d.sync += spi_clk.eq(~spi_clk)
                # Wait for DQ to transition to High
                with m.If(ospi.dqsdm.i[0]):     # DQ0 - Rising
                    m.d.sync += buffer.eq(Cat(ospi.adq.i[0:8], buffer)), # D0 byte
                    m.next = "READ_XFER"
                with m.Else():
                    m.next = "READ_DQ_WAIT"

            with m.State("READ_XFER"):
                m.d.sync += [
                    spi_clk.eq(~spi_clk),
                    buffer.eq(Cat(ospi.adq.i[0:8], buffer)), # D1 byte - Falling
                ]
                m.next = "READ_XFER_B2"

            with m.State("READ_XFER_B2"):
                m.d.sync += [
                    spi_clk.eq(~spi_clk),
                    buffer.eq(Cat(ospi.adq.i[0:8], buffer)), # D2 byte - Rising
                ]
                m.next = "READ_XFER_B3"

            with m.State("READ_XFER_B3"):
                m.d.sync += [
                    spi_clk.eq(~spi_clk),
                    # D3 byte - Falling
                    self.rd_data.eq(Cat(ospi.adq.i[0:8], buffer)),
                ]
                m.next = "END"

            # ------------------------------------------
            # Write data
            # ------------------------------------------
            # Address has been sent. Now wait 8 edges sending zeroes.
            # 4 latency edges + 4 Zero bytes = 8 edges.
            # This places the rising edge at D4 where we actually
            # write data.
            with m.State("WRITE_LATENCY"):
                with m.If(lc_ctr == 7):
                    m.d.sync += [
                        # Setup data for 1st byte (D0 = D4)
                        ospi.adq.o[0:8].eq(buffer[24:32]),
                        # Shift data for next edge
                        buffer.eq(Cat(0x00, buffer)),
                        lc_ctr.eq(0),
                    ]
                    m.next = "WRITE_XFER"
                with m.Else():
                    with m.If(data_out):
                        m.d.sync += [
                            # Place data on outputs
                            ospi.adq.o[0:8].eq(0x00),
                            # ospi.d.o[0:8].eq(buffer[24:32]),
                            data_out.eq(0),    # Switch to clock
                        ]
                    with m.Else():
                        m.d.sync += [
                            spi_clk.eq(~spi_clk),   # rfrfrfrf
                            lc_ctr.eq(lc_ctr + 1),  # 01234567
                            buffer.eq(Cat(0x00, buffer)),
                            data_out.eq(1),    # Switch to data
                        ]
                        m.next = "WRITE_LATENCY"

            # Now write 4 data bytes
            with m.State("WRITE_XFER"):
                with m.If(lc_ctr == 4):
                    m.d.sync += lc_ctr.eq(0)
                    m.next = "END"
                with m.Else():
                    with m.If(data_out):
                        m.d.sync += [
                            # Place data on outputs
                            ospi.adq.o[0:8].eq(buffer[24:32]), # D0,D1,D2,D3
                            # ospi.d.o[0:8].eq(buffer[24:32]),
                            data_out.eq(0),    # Switch to clock
                        ]
                    with m.Else():
                        m.d.sync += [
                            spi_clk.eq(~spi_clk),
                            lc_ctr.eq(lc_ctr + 1),   # 0-1,1-2,2-3,3-4
                            buffer.eq(Cat(0x00, buffer)),
                            data_out.eq(1),    # Switch to data
                        ]
                        m.next = "WRITE_XFER"

            # ------------------------------------------
            # End transfer
            # ------------------------------------------
            with m.State("END"):
                # m.d.sync += target_hit.eq(target_hit + 1)
                m.d.sync += [
                    self.ready.eq(SIG_ASSERT),  # Signal transfer complete
                    # 1 = driven, 0 = not-driven (high-Z)
                    # Stop driving PIN
                    ospi.adq.oe.eq(0x00),
                ]
                m.next = "IDLE"

        # self.ports.append(ospi)

        return m

