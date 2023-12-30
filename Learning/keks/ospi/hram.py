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

from amaranth.build import Platform

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    Signal, \
    Cat, \
    Const, \
    Mux


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
        ready : (O)   The signal is active (high) and
                      indicates that read data is correct.
                      The host needs to deassert *valid* to reset
                      the *ready* signal.
        valid : (I)   The signal is active (high) and
                      indicates the address/data is correct
                      and memory should begin a read/write.
        wstrb : (I)   Write strobe/mask (4 bits)
        ```
    """

    def __init__(self,
                    reset: Signal,
                    addr: Signal, wdata: Signal, rdata: Signal,
                    ready: Signal, valid: Signal, wstrb: Signal,
                    debug: Signal
                ):
        
        # --- Ports ---
        self.reset     = reset
        self.address   = addr
        self.wr_data   = wdata
        self.rd_data   = rdata
        self.ready     = ready  # Handshake signal to --> host
        self.valid     = valid  # Handshake signal from <-- host
        self.wr_strb   = wstrb
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

        reset_ctr = Signal(3, reset=0)

        # Active high when any write mask bit is set.
        write = Signal()

        spi_clk   = Signal(reset=0)

        if platform is not None:
            ospi = platform.request('ospi_psram')

            m.d.comb += [
                write.eq(self.wr_strb.any()),
                ospi.clk.eq(spi_clk),
            ]

            with m.FSM(reset="POWERUP") as fsm:
                self.fsm = fsm

                with m.State("POWERUP"):
                    m.d.sync += self.debug.eq(0b0001)
                    # Device requires anything from 500us to 1ms to
                    # enter normal operation.
                    # TODO Calculate delay based on system clock
                    with m.If(self.reset):
                        m.next = "RESET"
                    with m.Else():
                        m.next = "POWERUP"

                with m.State("RESET"):
                    m.d.sync += self.debug.eq(0b0010)
                    # Global reset is 4 clock cycles (8 edges) with CS active 
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for rising edge
                        # 0xFF is read only on the first clock.
                        buffer.eq(0xFFFFFFFF),  # Preset to F's = Cmd reset
                        reset_ctr.eq(0),         # Clear clock transfer counter
                        ospi.cs.eq(SIG_ASSERT), # Enable chip
                        # -------------------------------
                        # 1 = output buffer driver enabled
                        # 0 = buffer output high-Z
                        # -------------------------------
                        # Begin driving PIN
                        ospi.adq.oe.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (not driving)
                        ospi.dqsdm.oe.eq(0b00),
                        # Default to non-active
                        self.ready.eq(SIG_DEASSERT),
                    ]
                    m.next = "RESET_COMPLETE"

                with m.State("RESET_COMPLETE"):
                    m.d.sync += self.debug.eq(0b0011)
                    # Generate 4 clocks tp complete reset
                    with m.If(reset_ctr == 4):
                        m.next = "IDLE"
                    with m.Else():
                        m.d.sync += [
                            spi_clk.eq(~spi_clk),   # Toggle clock
                            reset_ctr.eq(reset_ctr + 1),
                        ]
                        m.next = "RESET_COMPLETE"

                with m.State("IDLE"):
                    m.d.sync += self.debug.eq(0b0100)
                    m.d.sync += [
                        # Stop driving PIN
                        ospi.adq.oe.eq(0xFFFF),
                        ospi.cs.eq(SIG_ASSERT),   # Put in Stanby mode
                    ]

                    # Wait for the "valid" signal to start a transfer.
                    # The "ready" flag is cleared by the host via the
                    # "valid" flag deasserting.
                    with m.If(self.valid & ~self.ready):
                        m.next = "INIT"     # Initiate transfer
                    with m.Elif(~self.valid & self.ready):
                        # The host has deasserted the "valid" flag, now
                        # clear "ready" signal and remain in IDLE
                        # waiting for the "valid" signal.
                        m.d.sync += self.ready.eq(SIG_DEASSERT)
                        m.next = "IDLE"

                # Initialize for a transfer.
                with m.State("INIT"):
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for a starting rising edge
                        # addr/data OE PIN switch to (driving)
                        ospi.adq.oe.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (not driving)
                        # We don't want to drive dqs/dm while sending
                        # instruction + address because we need to
                        # read the DQ bus for a Rising signal that indicates
                        # data is ready.
                        ospi.dqsdm.oe.eq(0b00),
                    ]
                    m.next = "START"

                with m.State("START"):
                    m.d.sync += ospi.cs.eq(0) # Start transfer (aka exit standby)
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
                    m.next = "CMD_EDGE_F"

                with m.State("CMD_EDGE_F"):
                    m.d.sync += spi_clk.eq(~spi_clk)   # Fall
                    m.next = "ADDR_BUFFER"

                # ------------------------------------------
                # Address
                # ------------------------------------------
                with m.State("ADDR_BUFFER"):
                    m.d.sync += [
                        buffer.eq(self.address),
                    ]
                    m.next = "ADDR_ADQ"

                with m.State("ADDR_ADQ"):
                    m.d.sync += [
                        # 31     24  23    16  15      8  7      0  :Verilog right to left
                        # 000000000__00000000__000000000__00000000
                        # 0:8        8:17      16:25      24:32     :Amaranth left to right
                        # Last                            First
                        ospi.adq.o[0:8].eq(buffer[24:32]),     # MSB's first
                    ]
                    m.next = "ADDR_EDGE_E1"

                with m.State("ADDR_EDGE_E1"):
                    m.d.sync += spi_clk.eq(~spi_clk)    # Rising
                    m.next = "ADDR_EDGE_E2"

                with m.State("ADDR_EDGE_E2"):
                    m.d.sync += ospi.adq.o[0:8].eq(buffer[16:25]),  # Next byte
                    m.next = "ADDR_EDGE_E3"

                with m.State("ADDR_EDGE_E3"):
                    m.d.sync += spi_clk.eq(~spi_clk)    # Falling
                    m.next = "ADDR_EDGE_E4"

                with m.State("ADDR_EDGE_E4"):
                    m.d.sync += ospi.adq.o[0:8].eq(buffer[8:17]),  # Next byte
                    m.next = "ADDR_EDGE_E5"

                with m.State("ADDR_EDGE_E5"):
                    m.d.sync += spi_clk.eq(~spi_clk)    # Rising
                    m.next = "ADDR_EDGE_E6"

                with m.State("ADDR_EDGE_E6"):
                    m.d.sync += ospi.adq.o[0:8].eq(buffer[0:8]),  # Last byte
                    m.next = "ADDR_EDGE_E7"

                with m.State("ADDR_EDGE_E7"):
                    m.d.sync += spi_clk.eq(~spi_clk)    # Falling
                    # =============================
                    # Read Or Write?
                    # =============================
                    with m.If(write):
                        m.next = "WRITE_XFER"
                    with m.Else():
                        m.next = "READ_DQ_WAIT"

                # ------------------------------------------
                # Read data
                # ------------------------------------------
                with m.State("READ_DQ_WAIT"):
                    m.d.sync += spi_clk.eq(~spi_clk)
                    # Wait for DQ to transition to High
                    with m.If(ospi.dqsdm.i[0]):     # DQ0 - Rising
                        buffer.eq(Cat(ospi.adq.i[0:8], buffer)), # D0 byte
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
                with m.State("WRITE_XFER"):
                    m.d.sync += [
                        # addr/data OE PIN switch to (driving)
                        ospi.adq.oe.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (driving)
                        # Byte is present at DQx = 1 values
                        # TODO I may use 11 instead of specific masks.
                        # ospi.dqsdm.oe.eq(0b11),
                        # Copy data for transmission
                        buffer.eq(self.wr_data),
                    ]
                    m.next = "WRITE_XFER_B1"

                with m.State("WRITE_XFER_B1"):  # D0
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),
                        # 1 = Do not write, 0 = Write
                        ospi.dqsdm.o.eq(Mux(self.wr_strb[0], 0b01, 0b11)),
                        ospi.adq.o[0:8].eq(buffer[24:32]),  # - Rising
                        buffer.eq(Cat(0x00, buffer)),
                    ]
                    m.next = "WRITE_XFER_B2"

                with m.State("WRITE_XFER_B2"):  # D1
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),
                        ospi.dqsdm.o.eq(Mux(self.wr_strb[1], 0b10, 0b11)),
                        ospi.adq.o[0:8].eq(buffer[24:32]),  # - Falling
                        buffer.eq(Cat(0x00, buffer)),
                    ]
                    m.next = "WRITE_XFER_B3"

                with m.State("WRITE_XFER_B3"):  # D2
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),
                        ospi.dqsdm.o.eq(Mux(self.wr_strb[2], 0b01, 0b11)),
                        ospi.adq.o[0:8].eq(buffer[24:32]),  # - Rising
                        buffer.eq(Cat(0x00, buffer)),
                    ]
                    m.next = "WRITE_XFER_B4"

                with m.State("WRITE_XFER_B4"):  # D3
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),
                        ospi.dqsdm.o.eq(0b11),
                        ospi.adq.o[0:8].eq(buffer[24:32]),  # - Falling
                    ]
                    m.next = "END"

                # ------------------------------------------
                # End transfer
                # ------------------------------------------
                with m.State("END"):
                    m.d.sync += [
                        self.ready.eq(SIG_ASSERT),  # Signal transfer complete
                        ospi.cs.eq(SIG_DEASSERT),   # End operation
                    ]
                    m.next = "IDLE"

        return m
