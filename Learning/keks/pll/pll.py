from amaranth import Instance

from pll_parameters import PLLParams

class ICEPLL(Elaboratable):
    """An instance of the iCE40 PLL.

    The output of the PLL is connected to the clock signal of the output
    domain, and the lock output is connected to the clock domain's reset
    via a ResetSynchronizer. The type of PLL depends on the platform,
    with iCE40HX8K using PLL40_CORE.
    
    Parameters:
    -----------
    f_in      - the input frequency on inclk
    f_out     - the requested output frequency.
    inclk     - the input clock signal
    outdomain - the clock domain of the output (defaults to "sync")
    """

    def __init__(self, f_in, f_out, inclk, outdomain = "sync"):
        self.params = PLLParams(f_in, f_out)
        self.outdomain = outdomain
        self.inclk = inclk

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = cd_sync = ClockDomain("sync")

        lock = Signal()
        
        m.submodules += Instance("SB_PLL40_CORE",
            p_FEEDBACK_PATH = self.params.feedback_path,
            p_PLLOUT_SELECT = "GENCLK",
            p_DIVR = self.params.divr,
            p_DIVF = self.params.divf,
            p_DIVQ = self.params.divq,
            p_FILTER_RANGE = self.params.filter_range,

            i_REFERENCECLK = platform.request(self.inclk).i,
            i_BYPASS = Const(0),
            i_RESETB = Const(1),

            o_PLLOUTGLOBAL = ClockSignal(self.outdomain),
            o_LOCK = lock,
        )

        m.submodules += ResetSynchronizer(~lock, domain = self.outdomain)

        return m