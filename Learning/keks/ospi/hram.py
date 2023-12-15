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
                    clk, reset,
                    addr, wdata, rdata, ready, valid, wstrb
                    # adq, dqs, ck, ce, state
                ):
        
        # --- Ports ---
        self.sys_clock = clk
        self.reset     = reset
        self.address   = addr
        self.wr_data   = wdata
        self.rd_data   = rdata
        self.ready     = ready  # Handshake signal
        self.valid     = valid  # Handshake signal
        self.wr_strb   = wstrb
        # ---- Device signals ----
        # adq   : (I/O) Address and lower data (16 bits) - X8 mode
        # dqs   : (I/O) Read strobe or Write mask (2 bits)
        # ck    : (O)   SPI generated clock
        # cd    : (O)   Chip enable (active low)
        # ---- State ----
        # state : (O)   Module state
        # self.addr_data = adq
        # self.data      = dqs
        # self.chip_en   = ce
        # self.state     = state

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

        dqs_c = Signal(3)
        write = Signal()

        spi_clk   = Signal(reset=0)

        if platform is not None:
            ospi = platform.request('ospi_psram')

            m.d.comb += [
                write.eq(self.wr_strb.any()),
                ospi.clk.eq(self.spi_clk),
            ]

            with m.FSM(reset="RESET") as fsm:
                self.fsm = fsm

                with m.If(~self.reset):
                    m.d.sync += [
                        # Deassert (Amaranth positive-logic)
                        ospi.cs_n.eq(SIG_DEASSERT),
                        spi_clk.eq(0),         # Start clock low

                        # -------------------------------
                        # 1 = output buffer driver enabled
                        # 0 = buffer output high-Z
                        # -------------------------------
                        # addr/data OE PIN enabled (driving)
                        ospi.adq.oe.o.eq(0xFFFF),
                        # strobe/mask OE PIN disabled (not driving)
                        ospi.dqsdm.oe.eq(0b00),

                        # Data out zeroes
                        ospi.d.o.eq(0x0000),

                        xfer_edges.eq(0),       # No edges to count
                        self.ready.eq(0),       # Read data isn't valid
                    ]
                    m.next = "RESET"

                with m.Elif(self.valid & ~self.ready & fsm.ongoing("IDLE")):
                    m.d.sync += xfer_edges.eq(0) # No edges to count
                    m.next = "INIT"

                with m.Elif(~self.valid & self.ready):
                    m.d.sync += self.ready.eq(0) # Read data isn't valid

                with m.Elif(xfer_edges):
                    with m.If(fsm.ongoing("END")):
                        # Set dqs to 00 only on certain transfer edges.
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
                            ospi.adq[0:8].eq(buffer[24:32]),
                            buffer.eq(Cat(0x00, buffer)),
                        ]

                    with m.If(xfer_ctr == 1):
                        spi_clk.eq(~spi_clk),

                        m.d.sync += [
                            xfer_edges.eq(xfer_edges - 1),
                            xfer_ctr.eq(0),
                        ]
                    
                    with m.Else():
                        m.d.sync += xfer_ctr.eq(xfer_ctr + 1)
                
                with m.Else():                   
                    with m.State("IDLE"):
                        m.d.sync += self.chip_en.eq(1)

                    with m.State("RESET"):
                        m.d.sync += [
                            spi_clk.eq(0), # Setup for rising edge
                            buffer.eq(0xFFFFFFFF),
                            xfer_edges.eq(8),   # Preset to 8 edges
                            xfer_ctr.eq(0),     # Clear transfer counter
                            self.chip_en.eq(1), # Assert CE
                        ]
                        m.next = "IDLE"

                    with m.State("INIT"):
                        m.d.sync += [
                            spi_clk.eq(0), # Setup for rising edge
                            # addr/data OE PIN enabled (driving)
                            ospi.adq.oe.o.eq(0xFFFF),
                            # strobe/mask OE PIN disabled (not driving)
                            ospi.dqsdm.oe.eq(0b00),
                        ]
                        m.next = "START"

                    with m.State("START"):
                        m.d.sync += self.chip_en.eq(1) # Assert CE
                        m.next = "CMD"

                    with m.State("CMD"):
                        m.d.sync += buffer.eq(Mux(write, 0x800000000, 0x000000000))
                        # with m.If(write):
                        #     m.d.sync += buffer.eq(0x800000000)
                        # with m.Else():
                        #     m.d.sync += buffer.eq(0x000000000)

                        m.d.sync += [
                            xfer_edges.eq(2),   # Set to 2 edges
                            xfer_ctr.eq(0),     # Clear transfer counter
                        ]
                        m.next = "ADDR"

                    with m.State("ADDR"):
                        m.d.sync += [
                            buffer.eq(Cat(self.address[0:26],0b000000)),
                            xfer_edges.eq(4),   # Preset to 4 edges
                            xfer_ctr.eq(0),     # Clear transfer counter
                        ]

                        with m.If(write):
                            m.next = "WAIT"
                        with m.Else():
                            m.d.sync += wait_ctr.eq(0)
                            m.next = "WAIT_DQS_LOW"

                        m.d.sync += [
                            dqs_c.eq(0),      # Clear strobe/mask counter
                            xfer_rdy.eq(0),   # Preset to transfer not ready
                        ]

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
                                # addr/data OE PIN enabled (driving)
                                ospi.ad.oe.o.eq(0xFFFF),
                                # strobe/mask OE PIN enabled (driving)
                                ospi.dqsdm.oe.eq(0b11),
                                xfer_edges.eq(8),   # Preset to 8 edges
                            ]
                            m.next = "XFER"
                        with m.Else():
                            m.d.sync += [
                                # addr/data OE PIN enabled (driving)
                                ospi.ad.oe.o.eq(0x0000),
                                xfer_edges.eq(0),   # No edges
                            ]
                            with m.If(ospi.dqsdm.i[0] | xfer_rdy):
                                m.d.sync += xfer_rdy.eq(1)  # Transfer is ready
                                with m.If(xfer_ctr == 0):
                                    m.d.sync += buffer.eq(Cat(ospi.ad[0:8], buffer))
                                    with m.If(dqs_c == 3):
                                        m.next = "END"
                                    m.d.sync += dqs_c.eq(dqs_c + 1)

                            with m.If(xfer_ctr == 1):
                                m.d.sync += [
                                    spi_clk.eq(~spi_clk),
                                    xfer_ctr.eq(0),
                                ]
                            with m.Else():
                                m.d.sync += xfer_ctr.eq(xfer_ctr + 1)

                    with m.State("XFER"):
                        with m.If(write):
                            m.d.sync += buffer.eq(self.wr_data)
                        m.d.sync += xfer_edges.eq(4)
                        m.next = "END"

                    with m.State("END"):
                        m.d.sync += [
                            self.rd_data.eq(buffer),
                            self.ready.eq(1),
                        ]
                        m.next = "IDLE"

        return m