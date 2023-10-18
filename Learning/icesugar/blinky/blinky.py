from amaranth import *

class TestLEDModule( Elaboratable ):
  def __init__( self ):
    self.count = Signal( 32, reset = 0 )

  def elaborate( self, platform ):
    m = Module()

    m.d.sync += self.count.eq( self.count + 1 )
    if platform is not None:
      grn_led = platform.request( 'led_g', 0 )
      blu_led = platform.request( 'led_b', 0 )
      m.d.comb += [
        grn_led.o.eq( self.count[ 20 ] ),
        blu_led.o.eq( ~grn_led.o )
      ]

    return m

# --- BUILD ---

# @audit NOTE:
# I appended a module to PYTHONPATH as:
# # PYTHONPATH=:/media/iposthuman/Nihongo/Hardware/amaranth-boards

from amaranth_boards.icesugar import *

if __name__ == "__main__":
  dut = TestLEDModule()
  ICESugarPlatform().build( dut, build_dir="/media/RAMDisk/build" )
