from amaranth.build import Platform

from amaranth_boards.machdyne_keks import KeksPlatform
from hram import HRAM

from amaranth.hdl import \
    Elaboratable, \
    Module, \
    ResetInserter, \
    Array, \
    Signal, \
    Const

from amaranth.build import \
    Resource,\
    PinsN

# In this test we:
# Read/Write from Double-Data-Rate Octal SPI PSRAM
# 256Mb = 32MB => 25 address bits -> 0x0000000 -> 0x1FFFFFF
# 

class Top(Elaboratable):

    def elaborate(self, platform: Platform) -> Module:
        # We need a top level module
        m = Module()

        SIG_ASSERT = Const(1, 1)
        SIG_DEASSERT = Const(0, 1)

        count = Signal(32, reset = 0)

        # Write each data halfword for each SRAM address
        data = [0x0505, 0xa0a0, 0x0000, 0xffff]

        # -----------------------------------------------------
        # ---- BRAM
        # -----------------------------------------------------
        memAddr = Signal(3, reset = 0)
        mem = Array([Signal(16, reset=x, name="mem{}".format(i))
                    for i,x in enumerate(data)])

        # -----------------------------------------------------
        # ---- OSPI
        # -----------------------------------------------------
        # 256Mb = 32MB => 25 address bits -> 0x0000000 -> 0x1FFFFFF
        ospiAddr = Signal(25, reset = 0)
        word = Signal(32)
        RAM_MAX_ADDR = 0x1FFFFFF

        # The "-" is required otherwise you get rather strange issues.
        # sys_clock = platform.request(platform.default_clk, dir='-')

        ospi_reset     = Signal(reset=1)
        ospi_address   = Signal(32)
        ospi_wr_data   = Signal(32)
        ospi_rd_data   = Signal(32)
        ospi_ready     = Signal()
        ospi_valid     = Signal()
        ospi_wr_strb   = Signal(4)

        m.submodules.hram = hram = HRAM(ospi_reset, ospi_address, ospi_wr_data, ospi_rd_data, ospi_ready, ospi_valid, ospi_wr_strb)
        # m.submodules.hramInserter = hramInserter = ResetInserter(ospi_reset)(hram)

        if platform is not None:
            platform.add_resources([
                Resource("pmod_a", 0, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 0))),
                Resource("pmod_b", 1, PinsN("1 2 3 4 7 8 9 10", dir="o", conn=("pmod", 1))),
            ])

            wht_led = platform.request('led_w', 0)
            pmod_a = platform.request('pmod_a', 0)    # Vertical pmod
            # PMOD-B has status
            pmod_b = platform.request('pmod_b', 1)

            m.d.sync += count.eq(count + 1)

            m.d.comb += [
                wht_led.o.eq(count[23]),
            ]
        
            with m.FSM(reset="INIT") as fsm:
                self.fsm = fsm

                with m.State("INIT"):
                    m.d.sync += [
                        # hram.reset.eq(SIG_ASSERT),
                        ospi_reset.eq(SIG_ASSERT),
                    ]
                    m.next = "RESET"

                with m.State("RESET"):
                    m.d.sync += [
                        # hram.reset.eq(SIG_DEASSERT),
                        ospi_reset.eq(SIG_DEASSERT),
                    ]
                    # m.next = "WRITE"

                # ------------------------------------------------
                # Write cycle #3 (WE controlled)
                # ------------------------------------------------
                # with m.State("WRITE"):
                #     m.d.sync += [
                #         # Write to addr:0 using data from BRAM addr:0
                #         sram.a.o.eq(ospiAddr),
                #         sram.d.o.eq(mem[memAddr]),

                #         sram.oe.o.eq(SIG_ASSERT),

                #         # Enable driving the bus
                #         sram.d.oe.eq(SIG_ASSERT),
                #     ]
                #     m.next = "WRITE_S1"
                # with m.State("WRITE_S1"):
                #     m.d.sync += [
                #         sram.dm.o.eq(0b11),   # Both

                #         sram.we.o.eq(SIG_ASSERT),
                #     ]
                #     m.next = "WRITE_S2a"
                # with m.State("WRITE_S2a"):
                #     m.next = "WRITE_END"
                # with m.State("WRITE_END"):
                #     m.d.sync += [
                #         sram.we.o.eq(SIG_DEASSERT),
                #         sram.oe.o.eq(SIG_DEASSERT),
                #         # Stop driving the bus
                #         sram.d.oe.eq(SIG_DEASSERT),
                #     ]
                    # m.next = "READ"

                # ------------------------------------------------
                # Read cycle (OE controlled)
                # ------------------------------------------------
                # with m.State("READ"):
                #     m.d.sync += [
                #         sram.dm.o.eq(0b11),

                #         # Read what was just written.
                #         sram.a.o.eq(ospiAddr),
                        
                #         sram.oe.o.eq(SIG_ASSERT),
                #     ]
                #     m.next = "READ_S2a"
                # with m.State("READ_S2a"):
                #     m.next = "READ_S2"
                # with m.State("READ_S2"):
                #     m.d.sync += [
                #         # Data valid read
                #         word.eq(sram.d.i[0:16]),
                #     ]
                #     m.next = "READ_S3"
                # with m.State("READ_S3"):
                #     m.d.sync += [
                #         sram.oe.o.eq(SIG_DEASSERT),

                #         # Write buf to LEDs
                #         # pmod_a.o.eq(halfWord[8:16]), # Vertical pmod
                #         # pmod_b.o.eq(halfWord[0:8]),
                #     ]
                #     m.next = "COMPARE"

                # ------------------------------------------------
                # Compare byte read to byte that was written
                # ------------------------------------------------
                # with m.State("COMPARE"):
                #     # Did what we read match what was written?
                #     with m.If(word == mem[memAddr]):
                #         # Move to the next data and potentially sram address.
                #         with m.If(memAddr > 2):
                #             m.d.sync += [memAddr.eq(0),]                            
                #             # Have we exercised the whole bank?
                #             with m.If(ospiAddr == RAM_MAX_ADDR):
                #                 m.next = "PASS"
                #             with m.Else():
                #                 m.d.sync += [
                #                     # pmod_a.o.eq(sramAddr[0:8]),
                #                     ospiAddr.eq(ospiAddr + 1),
                #                 ]
                #                 m.next = "WAIT"
                #         with m.Else():
                #             m.d.sync += [
                #                 # Move to next data
                #                 memAddr.eq(memAddr + 1)
                #             ]
                #             m.next = "WAIT"
                #     with m.Else():
                #         m.next = "FAIL"

                # with m.State("WAIT"):
                #     m.d.sync += pmod_a.o.eq(ospiAddr[8:18])
                #     # m.d.sync += [pmod_a.o.eq(sramAddr[0:8]),]

                #     with m.If(count[13]):  # 26 = ~1/2 seconds
                #         m.d.sync += count.eq(0)
                #         m.next = "WRITE"
                #     with m.Else():
                #         m.next = "WAIT"

                # with m.State("PASS"):
                #     m.d.sync += [
                #         pmod_b.o.eq(0b11100000),
                #     ]
                #     m.next = "PASS"

                # with m.State("FAIL"):
                #     m.d.sync += [
                #         pmod_a.o.eq(ospiAddr[0:8]),
                #         pmod_b.o.eq(0b10100000),
                #     ]
                #     m.next = "FAIL"
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
