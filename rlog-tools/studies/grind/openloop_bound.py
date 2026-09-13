# -*- coding: utf-8 -*-
"""openloop_bound.py -- THE BOUND, stated the cleanest way: IF the 18-22 Hz content that IS present
with the LKAS rate loop open were a resonance, how damped would it have to be to look like this?
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY.

openloop_ring.py C5 injects a synthetic mode ON TOP of the real lateral-OFF data, which doubles the
in-band power and so overstates detectability slightly.  This is the replacement version and it is the
one to quote:

    take the REAL lateral-OFF segments, NOTCH ONLY 18-22 Hz out of them, then put back a synthetic
    mode of KNOWN zeta at the SAME 18-22 band amplitude the real data actually has.

    ⚠ The notch is 18-22 and NOT the whole 16-26 fit window, deliberately.  A first cut notched the
    whole window, which left the fit with no continuum at all and made every injected mode trivially
    detectable (the empty surrogate scored a `bump` of 4e8).  Notching only the replaced band keeps
    the 16-18 and 22-26 background intact, so detection is judged against a realistic floor.

Now the surrogate has exactly the measured amount of in-band energy, arranged as a resonance instead
of as broadband.  Sweep zeta; the smallest zeta that E3b can no longer tell from the real (unmodified)
data is the LOWER BOUND on the open-loop damping, at the amplitude the wire actually carries.

Run: python openloop_bound.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openloop_lib as L                       # noqa: E402
import openloop_zeta as Z                      # noqa: E402
import openloop_ring as R                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
NPER = 1024
BUMP_MIN = 1.8
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def notch(x, lo=18.0, hi=22.0, fs=FS):
    """EXACT band removal in the frequency domain.

    A 4th-order Butterworth band-stop was used first and left transition skirts just outside 18-22 Hz
    that the line fit could grip: the empty surrogate scored prom 1.84, right at the detection
    threshold, with nothing injected.  An FFT mask removes exactly the named bins and nothing else.
    """
    x = np.asarray(x, float)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X[(f >= lo) & (f <= hi)] = 0.0
    return np.fft.irfft(X, n=len(x))


def main():
    tags = L.routes()
    pr("=" * 126)
    pr("THE OPEN-LOOP BOUND -- REPLACEMENT INJECTION (the version to quote)")
    pr("=" * 126)
    for chan, unit in (("bar", "raw driver torque"), ("rate", "deg/s wheel rate")):
        off = R.pool_segs(tags, chan=chan, want_eng=False, vlo=0, vhi=4, minlen=NPER)
        eng = R.pool_segs(tags, chan=chan, want_eng=True, vlo=0, vhi=4, minlen=NPER)
        Aoff = float(np.median([np.sqrt(2) * np.std(L.bp(x, 18, 22)) for x in off]))
        Aeng = float(np.median([np.sqrt(2) * np.std(L.bp(x, 18, 22)) for x in eng]))
        base = Z.zeta_line(off, 16.0, 26.0, NPER, nboot=200, seed=11)
        pr()
        pr("channel %s (%s) -- lateral-OFF 0-4 m/s: %d segments, %.0f s"
           % (chan, unit, len(off), sum(len(x) for x in off) / FS))
        pr("  measured 18-22 Hz amplitude : OFF %.4f, ENGAGED %.4f, ratio %.4f"
           % (Aoff, Aeng, Aoff / Aeng))
        pr("  REAL data, unmodified       : bump %.2f  prom %.2f  f0 %.2f  ->  %s"
           % (base["bump"], base["prom_data"], base["f0"],
              "LINE" if (base["bump"] >= BUMP_MIN and base["prom_data"] >= BUMP_MIN
                         and not base["edge"]) else "NO LINE"))
        # the notched surrogate is the floor the injection sits on
        offn = [notch(x) for x in off]
        rn = Z.zeta_line(offn, 16.0, 26.0, NPER)
        pr("  18-22 NOTCHED surrogate     : bump %.2f  prom %.2f   (the floor the mode is put back on)"
           % (rn["bump"], rn["prom_data"]))
        pr()
        pr("  %-9s | %-44s | %-44s" % ("", "mode carries ALL the measured OFF energy",
                                       "mode carries HALF of it"))
        pr("  %-9s | %-44s | %-44s" % ("true zeta", "z_hat   bump   prom   detected?",
                                       "z_hat   bump   prom   detected?"))
        for zt in (0.010, 0.020, 0.030, 0.050, 0.080, 0.100, 0.150, 0.200, 0.300, 0.500):
            cells = []
            for frac in (1.0, 0.5):
                # keep TOTAL 18-22 energy at the measured value: modal fraction `frac` in amplitude,
                # the rest put back as the original broadband content scaled by sqrt(1-frac^2)
                al = float(np.sqrt(max(1.0 - frac ** 2, 0.0)))
                bandpart = [np.asarray(x, float) - y for x, y in zip(off, offn)]
                sfloor = [y + al * bp_ for y, bp_ in zip(offn, bandpart)]
                s2 = Z.inject(sfloor, zt, 20.0, Aoff * frac, seed=int(zt * 1e4) + 7)
                r = Z.zeta_line(s2, 16.0, 26.0, NPER)
                det = (r["bump"] >= BUMP_MIN) and (r["prom_data"] >= BUMP_MIN) and (not r["edge"])
                cells.append("%6.4f %6.2f %6.2f   %s" % (r["z"], min(r["bump"], 999.0),
                                                         min(r["prom_data"], 999.0),
                                                         "DETECTED" if det else "invisible"))
            pr("  %-9.3f | %-44s | %-44s" % (zt, cells[0], cells[1]))
    pr()
    pr("READ: the smallest zeta whose row says `invisible` in the FIRST column is the lower bound --")
    pr("below it, a resonance carrying the measured open-loop energy would have shown up and did not.")
    pr("The second column is the same bound if only half the measured in-band energy is modal.")
    with open(os.path.join(L.SCR, "openloop_bound.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote _scratch/openloop_bound.txt")


if __name__ == "__main__":
    main()
