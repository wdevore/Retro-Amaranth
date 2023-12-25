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
        CMD_SYNC_READ = Const(0x00000000, 32)
        CMD_SYNC_WRITE = Const(0x80000000, 32)

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


            with m.FSM(reset="RESET") as fsm:
                self.fsm = fsm

                with m.State("POWERUP"):
                    # Device requires anything from 500us to 1ms to
                    # enter normal operation.
                    # TODO Calculate delay based on system clock
                    m.next = "RESET"

                with m.State("RESET"):
                    # Global reset is 4 clock cycles (8 edges) with CS active 
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for rising edge
                        # 0xFF is read only on the first clock.
                        buffer.eq(0xFFFFFFFF),  # Preset to F's = Cmd reset
                        xfer_ctr.eq(0),         # Clear clock transfer counter
                        ospi.cs.eq(SIG_ASSERT), # Enable chip
                        # -------------------------------
                        # 1 = output buffer driver enabled
                        # 0 = buffer output high-Z
                        # -------------------------------
                        # Begin driving PIN
                        ospi.adq.oe.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (not driving)
                        ospi.dqsdm.oe.eq(0b00),
                    ]
                    m.next = "RESET_COMPLETE"

                with m.State("RESET_COMPLETE"):
                    # Generate 4 clocks complete reset
                    with m.If(xfer_ctr == 4):
                        m.next = "IDLE"
                    with m.Else():
                        m.d.sync += [
                            spi_clk.eq(~spi_clk),   # Toggle clock
                            xfer_ctr.eq(xfer_ctr + 1),
                        ]

                with m.State("IDLE"):
                    m.d.sync += [
                        # Stop driving PIN
                        ospi.adq.oe.eq(0xFFFF),
                        ospi.cs.eq(1),   # Put in Stanby mode
                    ]

                    # Wait for the "valid" signal to start a transfer.
                    # The "ready" flag is cleared by the host via the
                    # "valid" flag deasserting.
                    with m.If(self.valid & ~self.ready):
                        m.d.sync += xfer_edges.eq(0) # No edges to count
                        m.next = "INIT"     # Initiate transfer
                    with m.Elif(~self.valid & self.ready):
                        # The host has deasserted the "valid" flag, now
                        # clear "ready" signal and remain in IDLE
                        m.d.sync += self.ready.eq(SIG_DEASSERT)

                with m.State("INIT"):
                    # Initialize for a transfer.
                    m.d.sync += [
                        spi_clk.eq(0), # Setup for a starting rising edge
                        # addr/data OE PIN switch to (driving)
                        ospi.adq.oe.eq(0xFFFF),
                        # strobe/mask OE PIN switch to (not driving)
                        # We don't want to drive dqs/dm while sending
                        # instruction + address
                        ospi.dqsdm.oe.eq(0b00),
                    ]
                    m.next = "START"

                with m.State("START"):
                    m.d.sync += ospi.cs.eq(0) # Take out of Standby mode
                    m.next = "CMD"

                with m.State("CMD"):
                    m.d.sync += [
                        # Set command instruction.
                        buffer.eq(Mux(write, CMD_SYNC_WRITE, CMD_SYNC_READ)),
                        xfer_edges.eq(2),   # 2 edges are needed (pos + neg)
                        xfer_ctr.eq(0),     # Clear transfer counter
                    ]
                    m.next = "ADDR"

                with m.State("ADDR"):
                    m.d.sync += [
                        # Setup buffer with 25 bit address and pad upper bits
                        buffer.eq(Cat(self.address[0:26],0b000000)),
                        xfer_edges.eq(4),   # 4 edges are needed
                        xfer_ctr.eq(0),     # Clear transfer counter
                        dqs_ctr.eq(0),      # Clear strobe/mask counter
                        xfer_rdy.eq(0),     # Preset to transfer not ready
                    ]

                    # Read Or Write?
                    with m.If(write):
                        # Write transfer.
                        m.next = "WAIT"
                    with m.Else():
                        #  Read transfer.
                        m.d.sync += wait_ctr.eq(0)
                        m.next = "WAIT_DQS_LOW"

                with m.State("WAIT_DQS_LOW"):
                    # Because this is a Read DQS will go low after
                    # 2 to 5 clocks
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
                            ospi.adq.oe.eq(0xFFFF),
                            # strobe/mask OE PIN switch to (driving)
                            ospi.dqsdm.oe.eq(0b11),
                            xfer_edges.eq(8),   # 8 edges are needed
                        ]
                        m.next = "XFER"
                    with m.Else():
                        # Read transfer
                        m.d.sync += [
                            # addr/data OE PIN switch to (not-driving)
                            # We don't want to drive bus while device is driving.
                            ospi.adq.oe.eq(0x0000),
                            xfer_edges.eq(0),   # No edges needed
                        ]
                        # xfer_rdy isn't Set during the first clock
                        # When dqs transition from low to high then the first
                        # data byte is ready from the device.
                        with m.If(ospi.dqsdm.i[0] | xfer_rdy):
                            # Set flag so we continue to take this path.
                            m.d.sync += xfer_rdy.eq(1)  # Transfer is now ready
                            with m.If(xfer_ctr == 0):
                                # Pack data byte by byte. D0 1st followed by D1...
                                m.d.sync += buffer.eq(Cat(ospi.adq[0:8], buffer))
                                with m.If(dqs_ctr == 3):
                                    m.next = "END"
                                m.d.sync += dqs_ctr.eq(dqs_ctr + 1)

                        # Checking for 1 causes a phase shift for DQS by half a clock
                        # DQS is 90 degrees out of phase with the SPI clock.
                        with m.If(xfer_ctr == 1):
                            # Begin toggling SPI clock
                            m.d.sync += [
                                spi_clk.eq(~spi_clk),   # Toggle clock
                                xfer_ctr.eq(0),         # Clear tranfer counter
                            ]
                        with m.Else():
                            m.d.sync += xfer_ctr.eq(xfer_ctr + 1)

# TODO ------ currently working here ----------
                with m.State("XFER"):
                    # We check "write" again in case it changed between clocks.
                    with m.If(write):
                        # Transfer to buffer for writing.
                        m.d.sync += buffer.eq(self.wr_data)
                    m.d.sync += xfer_edges.eq(4) # 4 Edges are needed = 4 bytes
                    m.next = "END"

                with m.State("END"):
                    with m.If(xfer_edges):
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

                    m.d.sync += [
                        # Transfer newly read data to module port
                        self.rd_data.eq(buffer),
                        self.ready.eq(SIG_ASSERT), # Signal data is ready
                    ]
                    m.next = "IDLE"

        return m
    
            # with m.If(~self.reset):
            #     # Global reset is 4 clock cycles with CS active 
            #     m.d.sync += [
            #         ospi.cs.eq(0),      # Enable chip
            #         spi_clk.eq(0),      # Start clock low

            #         # -------------------------------
            #         # 1 = output buffer driver enabled
            #         # 0 = buffer output high-Z
            #         # -------------------------------
            #         # addr/data OE PIN enabled (driving)
            #         ospi.adq.oe.eq(0xFFFF),
            #         # strobe/mask OE PIN disabled (not driving)
            #         ospi.dqsdm.oe.eq(0b00),

            #         # Data out zeroes
            #         ospi.d.o.eq(0x0000),

            #         xfer_edges.eq(0),       # No edges to count until xfer starts
            #         self.ready.eq(0),       # Device/Data isn't ready
            #     ]
            #     m.next = "RESET"

            # with m.Elif(self.valid & ~self.ready & fsm.ongoing("IDLE")):
            #     m.d.sync += xfer_edges.eq(0) # No edges to count
            #     m.next = "INIT"

            # with m.Elif(~self.valid & self.ready):
            #     m.d.sync += self.ready.eq(0) # Data isn't valid yet

            # with m.Elif(xfer_edges):
            #     with m.If(fsm.ongoing("END")):
            #         # Set dqs to 00 only at certain transfer edges.
            #         with m.If(self.wr_strb[3] & xfer_edges == 4):
            #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            #         with m.Elif(self.wr_strb[2] & xfer_edges == 3):
            #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            #         with m.Elif(self.wr_strb[1] & xfer_edges == 2):
            #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            #         with m.Elif(self.wr_strb[0] & xfer_edges == 1):
            #             m.d.sync += ospi.dqsdm.o.eq(0b00)
            #         with m.Else():
            #             m.d.sync += ospi.dqsdm.o.eq(0b11)

            #     with m.If(xfer_ctr == 0):
            #         m.d.sync += [
            #             # Assign buffer to data output
            #             ospi.adq.o[0:8].eq(buffer[24:32]),
            #             buffer.eq(Cat(0x00, buffer)),
            #         ]

            #     with m.If(xfer_ctr == 1):
            #         # Toggle clock
            #         spi_clk.eq(~spi_clk),

            #         m.d.sync += [
            #             # Decrement transfer edge count
            #             xfer_edges.eq(xfer_edges - 1),
            #             # Reset transfer count
            #             xfer_ctr.eq(0),
            #         ]
                
            #     with m.Else():
            #         # Count transfers
            #         m.d.sync += xfer_ctr.eq(xfer_ctr + 1)
