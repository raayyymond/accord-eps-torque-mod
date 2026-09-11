# -*- coding: utf-8 -*-
"""fvlc_v289_band_robustness.py -- does the V289 detection band change any conclusion?
Subagent cyclekind, 2026-09-10.  ANALYSIS ONLY.

Three bands are in circulation for V289's relocated line: 13-18 (STATE), 14-18 (orchestrator's
correction: at 13-18 the demand-gated peak on r62 lands on the low-demand 13.18 Hz road line), and
15-18.5 (what the main FVLC study used).  This re-runs the three statistics that carry the verdict
under each band, on r62/r63, so the choice is verified rather than asserted.
Run: python fvlc_v289_band_robustness.py    (writes _scratch/fvlc_v289_band_robustness.txt)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F            # noqa: E402
import fvlc_analysis as A       # noqa: E402
import creep20_loop_id as C20   # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def run_band(tags, lo, hi):
    res = dict(f0=[], pk=[], pf=[], nb=[], idx=[], nep=0)
    acc = {"mode": [np.zeros(98), np.zeros(98), 0.0], "sham": [np.zeros(98), np.zeros(98), 0.0]}
    lags = np.arange(2, 100)
    for t in tags:
        g = A.R(t)
        eps, hot, _, _ = A.episodes_band(g, lo, hi)
        f0 = float(np.median([e[2] for e in eps])) if eps else np.nan
        res["nep"] += len(eps)
        d = {}
        for nm, c in (("mode", f0), ("sham", A.SHAM_C)):
            d[nm] = np.abs(signal.hilbert(C20.bandpass(g["bar"], c - 1.5, c + 1.5, 100.0)))
            zz = signal.hilbert(C20.bandpass(g["bar"], c - 3.0, c + 3.0, 100.0))
            d["z_" + nm] = zz * np.exp(-2j * np.pi * c * np.arange(len(zz)) / 100.0)
        dn = np.abs(signal.hilbert(C20.bandpass(g["bar"], A.NEIGH_C - 1.5, A.NEIGH_C + 1.5, 100.0)))
        for a, b, fe in eps:
            if b - a < 40:
                continue
            res["f0"].append(fe)
            res["idx"].append(float(np.median(g["idx"][a:b])))
            e = d["mode"][a:b]
            res["pk"].append(e.max())
            med = np.median(e)
            res["pf"].append(np.mean(np.abs(20 * np.log10(np.maximum(e, 1e-9) / med)) <= 2.0))
            res["nb"].append(np.median(dn[a:b]))
            if b - a >= 140:
                for nm in ("mode", "sham"):
                    z = d["z_" + nm][a:b]
                    acc[nm][2] += float(np.mean(np.abs(z) ** 2)) * (len(z) - 1)
                    for i, L in enumerate(lags):
                        acc[nm][0][i] += np.real(np.vdot(z[:-L], z[L:]))
                        acc[nm][1][i] += np.imag(np.vdot(z[:-L], z[L:]))
    for nm in ("mode", "sham"):
        rho = np.hypot(acc[nm][0], acc[nm][1]) / max(acc[nm][2], 1e-9)
        rho = np.clip(rho / max(rho[0], 1e-9), 1e-6, 1.0)
        sl = stats.linregress(lags / 100.0, np.log(rho)).slope
        res["tau_" + nm] = (-1.0 / sl) if sl < 0 else np.inf
    return res


def main():
    tags = [t for t in ("r62_v289", "r63_v289") if os.path.exists(os.path.join(F.SCR, "fvlc_%s.pkl" % t))]
    pr("V289 DETECTION-BAND ROBUSTNESS -- r62 + r63.   cyclekind, 2026-09-10")
    pr("Three bands in circulation.  If the verdict-carrying statistics agree across them, the choice is")
    pr("immaterial and the study stands as written.")
    pr("")
    pr("%-12s %5s | %-9s %-9s | %-9s %-9s %-9s | %-8s %-8s %-8s" %
       ("band", "nep", "med f0", "med idx", "tau_c mode", "tau_c sham", "ratio",
        "plateau", "CVlg pk", "CVlg nbr"))
    for lo, hi in ((13.0, 18.0), (14.0, 18.0), (15.0, 18.5)):
        r = run_band(tags, lo, hi)
        if not r["f0"]:
            pr("%-12s (no episodes)" % ("%g-%g" % (lo, hi)))
            continue
        pk = np.array(r["pk"]); nb = np.array(r["nb"])
        pr("%-12s %5d | %-9.3f %-9.1f | %-9.3f %-9.3f %-9.2f | %-8.3f %-8.3f %-8.3f" %
           ("%g-%g" % (lo, hi), r["nep"], np.median(r["f0"]), np.median(r["idx"]),
            r["tau_mode"], r["tau_sham"], r["tau_mode"] / max(r["tau_sham"], 1e-9),
            np.median(r["pf"]), np.std(np.log(pk)), np.std(np.log(np.maximum(nb, 1e-9)))))
    pr("")
    pr("READ: tau_c (phase coherence time) is the study's decisive statistic.  If it stays at a few tenths")
    pr("of a second and a few cycles under every band, the (A)/(B)-vs-(C) verdict does not depend on the")
    pr("band choice.  med f0 shows whether the band is catching the relocated grinding mode (16.2-16.9 Hz)")
    pr("or the low-demand road line (12.4-13.8 Hz) -- the latter also shows up as a LOW median demand idx.")
    with open(os.path.join(F.SCR, "fvlc_v289_band_robustness.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/fvlc_v289_band_robustness.txt")


if __name__ == "__main__":
    main()
