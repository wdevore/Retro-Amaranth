class PLLParams():
    """Object to hold PLL configuration parameters. """
    
    def __init__(self, f_in, req_f_out, simple_feedback = True):
        """ Construct the PLL parameters from an input frequency and a
        requested output frequency"""
        if not 10e6 <= f_in <= 133e6:
            raise Exception("PLL f_in (%.3f MHz) out of range" % (f_in / 1e6))

        if not 16e6 <= req_f_out <= 275e6:
            raise Exception("PLL f_out (%.3f MHz) out of range" % (req_f_out / 1e6))

        # The documentation in the iCE40 PLL Usage Guide incorrectly lists the
        # maximum value of DIVF as 63, when it is only limited to 63 when using
        # feedback modes other that SIMPLE.
        if simple_feedback:
            divf_max = 128
        else:
            divf_max = 64

        variants = []
        for divr in range(0, 16):
            f_pfd = f_in / (divr + 1)
            if not 10e6 <= f_pfd <= 133e6:
                continue

            for divf in range(0, divf_max):
                if simple_feedback:
                    f_vco = f_pfd * (divf + 1)
                    if not 533e6 <= f_vco <= 1066e6:
                        continue

                    for divq in range(1, 7):
                        f_out = f_vco * (2 ** -divq)
                        variants.append((divr, divf, divq, f_pfd, f_out))

                else:
                    for divq in range(1, 7):
                        f_vco = f_pfd * (divf + 1) * (2 ** divq)
                        if not 533e6 <= f_vco <= 1066e6:
                            continue

                        f_out = f_vco * (2 ** -divq)
                        variants.append((divr, divf, divq, f_pfd, f_out))

        if not variants:
            raise Exception("PLL f_in (%.3f MHz)/f_out (%.3f MHz) out of range" %
                    (f_in / 1e6, req_f_out / 1e6))

        def f_out_diff(variant):
            *_, f_out = variant
            return abs(f_out - req_f_out)
        self.divr, self.divf, self.divq, f_pfd, self.f_out = min(variants, key=f_out_diff)

        if f_pfd < 17:
            self.filter_range = 1
        elif f_pfd < 26:
            self.filter_range = 2
        elif f_pfd < 44:
            self.filter_range = 3
        elif f_pfd < 66:
            self.filter_range = 4
        elif f_pfd < 101:
            self.filter_range = 5
        else:
            self.filter_range = 6

        if simple_feedback:
            self.feedback_path = "SIMPLE"
        else:
            self.feedback_path = "NON_SIMPLE"

        self.ppm = abs(req_f_out - f_out) / req_f_out * 1e6
