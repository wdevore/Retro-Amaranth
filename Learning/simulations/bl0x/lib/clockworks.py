from amaranth import \
    Elaboratable, \
    Signal, \
    Module

from amaranth.build import Platform

from amaranth.hdl.cd import ClockDomain
from amaranth.hdl.ast import ClockSignal

# This module handles clock division and provides a new 'slow' clock domain
class Clockworks(Elaboratable):
    """Handles clock division

    When no division is provided, just use the clock signal of
    the default ``"sync"`` domain.

    Creates a new ``"slow"`` clock domain.

    Parameters
    ----------
    slow : is the divisor for synthesis. A number that is a power of 2, for example, 2^slow.
    sim_slow : is the divisor for simulation.
    """
    def __init__(self, slow=0, sim_slow=None):
        # Since the module provides a new clock domain, which is accessible
        # via the top level module, we don't need to explicitly provide the
        # slow clock signal as an output.

        self.slow = slow
        if sim_slow is None:
            self.sim_slow = slow    # Default to slow value
        else:
            self.sim_slow = sim_slow

    def elaborate(self, platform: Platform) -> Module:

        clk = Signal()      # The new clock
        m = Module()

        if self.slow != 0:
            # When the design is simulated, platform is None
            if platform is None:
                # Have the simulation run at a different speed than the
                # actual hardware (usually faster).
                slow_bit = self.sim_slow
            else:
                slow_bit = self.slow

            # Start the slow clock past the trigger bit.
            slow_clk = Signal(slow_bit + 1)

            m.d.sync += slow_clk.eq(slow_clk + 1)
            m.d.comb += clk.eq(slow_clk[slow_bit])
        else:
            # When no division is requested, just use the clock signal of
            # the default 'sync' domain.
            m.d.comb += clk.eq(ClockSignal("sync"))

        # Create the new clock domain
        m.domains += ClockDomain("slow")

        # Assign the slow clock to the clock signal of the new domain
        m.d.comb += ClockSignal("slow").eq(clk)

        return m
