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
                      indicates the address is correct
                      and memory should begin a read/write.
        wstrb : (I)   Write strobe/mask (4 bits)
        ```
    """

    def __init__(self,
                    reset: Signal,
                    addr: Signal, wdata: Signal, rdata: Signal,
                    ready: Signal, valid: Signal, wstrb: Signal
                ):
        
        # --- Ports ---
        self.reset     = reset
        self.address   = addr
        self.wr_data   = wdata
        self.rd_data   = rdata
        self.ready     = ready  # Handshake signal to host
        self.valid     = valid  # Handshake signal from host
        self.wr_strb   = wstrb

    def elaborate(self,  platform: Platform) -> Module:
        m = Module()

        # Amaranth positive logic (1 = assert)
        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        # Buffer to capture 
        buffer = Signal(32)

        xfer_edges = Signal(6)
        xfer_ctr = Signal(2)
        xfer_rdy = Signal()
        wait_ctr = Signal(2)

        dqs_ctr = Signal(3)
        # Active high when any write mask bit is set.
        write = Signal()

        spi_clk   = Signal(reset=0)

        if platform is not None:
            ospi = platform.request('ospi_psram')

            m.d.comb += [
                write.eq(self.wr_strb.any()),
                ospi.clk.eq(spi_clk),
            ]

            with m.If(~self.reset):
                m.d.sync += [
                    ospi.cs.eq(1),      # Put in standby mode
                    spi_clk.eq(0),      # Start clock low

                    # -------------------------------
                    # 1 = output buffer driver enabled
                    # 0 = buffer output high-Z
                    # -------------------------------
                    # addr/data OE PIN enabled (driving)
                    ospi.adq.oe.eq(0xFFFF),
                    # strobe/mask OE PIN disabled (not driving)
                    ospi.dqsdm.oe.eq(0b00),

                    # Data out zeroes
                    ospi.d.o.eq(0x0000),

                    xfer_edges.eq(0),       # No edges to count until xfer starts
                    self.ready.eq(0),       # Read data isn't valid
                ]
                m.next = "RESET"

            with m.Elif(self.valid & ~self.ready & fsm.ongoing("IDLE")):
                m.d.sync += xfer_edges.eq(0) # No edges to count
                m.next = "INIT"

            with m.Elif(~self.valid & self.ready):
                m.d.sync += self.ready.eq(0) # Data isn't valid yet

            with m.Elif(xfer_edges):
                with m.If(fsm.ongoing("END")):
                    # Set dqs to 00 only at certain transfer edges.
                    with m.If(self.wr_strb[3] & xfer_edges == 4):
                        m.d.sync += ospi.dqsdm.o.eq(0b00)
                    with m.Elif(self.wr_strb[2] & xfer_edges == 3):
                        m.d.sync += ospi.dqsdm.o.eq(0b00)
                    with m.Elif(self.wr_strb[1] & xfer_edges == 2):
                        m.d.sync += ospi.dqsdm.o.eq(0b00)
                    with m.Elif(self.wr_strb[0] & xfer_edges == 1):
                        m.d.sync += ospi.dqsdm.o.eq(0b00)
                    with m.Else():
                        m.d.sync += ospi.dqsdm.o.eq(0b11)

                with m.If(xfer_ctr == 0):
                    m.d.sync += [
                        # Assign buffer to data output
                        ospi.adq.o[0:8].eq(buffer[24:32]),
                        buffer.eq(Cat(0x00, buffer)),
                    ]

                with m.If(xfer_ctr == 1):
                    # Toggle clock
                    spi_clk.eq(~spi_clk),

                    m.d.sync += [
                        # Decrement transfer edge count
                        xfer_edges.eq(xfer_edges - 1),
                        # Reset transfer count
                        xfer_ctr.eq(0),
                    ]
                
                with m.Else():
                    # Count transfers
                    m.d.sync += xfer_ctr.eq(xfer_ctr + 1)

            with m.FSM(reset="RESET") as fsm:
                self.fsm = fsm
                
                with m.State("IDLE"):
                    m.d.sync += ospi.cs.eq(1)   # Put in Stanby mode

                with m.State("RESET"):
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for rising edge
                        buffer.eq(0xFFFFFFFF),  # Preset to Fs
                        xfer_edges.eq(8),       # Preset to 8 transfer edges
                        xfer_ctr.eq(0),         # Clear transfer counter
                        ospi.ce.eq(0),          # Place in standby mode
                    ]
                    m.next = "IDLE"

                with m.State("INIT"):
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for rising edge
                        # addr/data OE PIN switch to (driving)
                        ospi.adq.oe.o.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (not driving)
                        ospi.dqsdm.oe.eq(0b00),
                    ]
                    m.next = "START"

                with m.State("START"):
                    m.d.sync += ospi.cs.eq(0) # Take out of Standby mode
                    m.next = "CMD"

                with m.State("CMD"):
                    # with m.If(write):
                    #     m.d.sync += buffer.eq(0x800000000)
                    # with m.Else():
                    #     m.d.sync += buffer.eq(0x000000000)

                    m.d.sync += [
                        buffer.eq(Mux(write, 0x800000000, 0x000000000)),
                        xfer_edges.eq(2),   # 2 edges are needed
                        xfer_ctr.eq(0),     # Clear transfer counter
                    ]
                    m.next = "ADDR"

                with m.State("ADDR"):
                    m.d.sync += [
                        buffer.eq(Cat(self.address[0:26],0b000000)),
                        xfer_edges.eq(4),   # 4 edges are needed
                        xfer_ctr.eq(0),     # Clear transfer counter
                        dqs_ctr.eq(0),      # Clear strobe/mask counter
                        xfer_rdy.eq(0),     # Preset to transfer not ready
                    ]

                    with m.If(write):
                        m.next = "WAIT"
                    with m.Else():
                        m.d.sync += wait_ctr.eq(0)
                        m.next = "WAIT_DQS_LOW"

                with m.State("WAIT_DQS_LOW"):
                    m.d.sync += [
                        spi_clk.eq(~spi_clk),
                        wait_ctr.eq(wait_ctr + 1),
                    ]
                    with m.If(wait_ctr == 2):
                        m.next = "WAIT"

                with m.State("WAIT"):
                    with m.If(write):
                        m.d.sync += [
                            # addr/data OE PIN switch to (driving)
                            ospi.ad.oe.o.eq(0xFFFF),
                            # strobe/mask OE PIN switch to (driving)
                            ospi.dqsdm.oe.eq(0b11),
                            xfer_edges.eq(8),   # 8 edges are needed
                        ]
                        m.next = "XFER"
                    with m.Else():
                        m.d.sync += [
                            # addr/data OE PIN switch to (not-driving)
                            ospi.ad.oe.o.eq(0x0000),
                            xfer_edges.eq(0),   # No edges needed
                        ]
                        with m.If(ospi.dqsdm.i[0] | xfer_rdy):
                            m.d.sync += xfer_rdy.eq(1)  # Transfer is ready
                            with m.If(xfer_ctr == 0):
                                m.d.sync += buffer.eq(Cat(ospi.ad[0:8], buffer))
                                with m.If(dqs_ctr == 3):
                                    m.next = "END"
                                m.d.sync += dqs_ctr.eq(dqs_ctr + 1)

                        with m.If(xfer_ctr == 1):
                            m.d.sync += [
                                spi_clk.eq(~spi_clk),   # Toggle clock
                                xfer_ctr.eq(0),         # Clear tranfer counter
                            ]
                        with m.Else():
                            m.d.sync += xfer_ctr.eq(xfer_ctr + 1)

                with m.State("XFER"):
                    with m.If(write):
                        # Transfer to buffer
                        m.d.sync += buffer.eq(self.wr_data)
                    m.d.sync += xfer_edges.eq(4) # 4 Edges are needed
                    m.next = "END"

                with m.State("END"):
                    m.d.sync += [
                        # Transfer to module port
                        self.rd_data.eq(buffer),
                        self.ready.eq(SIG_ASSERT), # Signal data is ready
                    ]
                    m.next = "IDLE"

        return m