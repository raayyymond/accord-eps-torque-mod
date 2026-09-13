# -*- coding: utf-8 -*-
"""Part 4: does a LONGER WINDOW identify 10-14 Hz, and does B(f) move there when it does?"""
import numpy as np
from b_iv_kappa import pr, J, ang
import b_iv_kappa as M
import bof_v282 as BF
from _biv_part2 import SK, SN

FR = [8.0, 9.94, 10.0, 11.0, 12.0, 12.85, 13.0, 13.7, 14.0, 16.0, 20.3]


def longwin(G):
    pr("\n" + "=" * 150)
    pr("7. THE 10-14 Hz GAP IS PARTLY A WINDOW-LENGTH ARTEFACT -- B(f) RE-MEASURED AT nperseg 512")
    pr("   bof used nperseg 128 (1.28 s, 0.78 Hz resolution).  Section 4.1 showed coh(rate,bar) at 12 Hz")
    pr("   rising 0.45 -> 0.60 -> 0.66 as the window goes 128 -> 256 -> 512.  If B varies fast across the")
    pr("   band, the short window smears it and the coherence loss is RESOLUTION, not noise.")
    pr("   Reported with the effective number of averages, so a small-sample coherence bias is visible:")
    pr("   E[coh_hat] ~ coh + (1-coh)/Neff, Neff ~ 0.5 * nwin * (independent cells in the +-0.40 Hz band).")
    pr("=" * 150)
    R = {}
    for key in ("creep_1_3med", "creep_1_6med", "loaded_any"):
        pr("")
        pr("  %s   [%s]" % (SN[key], key))
        pr("  %6s | %-28s | %-28s | %-28s"
           % ("f(Hz)", "nperseg 128 (bof)", "nperseg 256", "nperseg 512"))
        pr("  %6s | %8s %8s %6s | %8s %8s %6s | %8s %8s %6s"
           % ("", "|B|Hv", "ang", "coh", "|B|Hv", "ang", "coh", "|B|Hv", "ang", "coh"))
        pr("  " + "-" * 106)
        PP = {}
        for nps, nfft in ((128, 512), (256, 1024), (512, 2048)):
            PP[nps] = BF.pool_stratum(G, BF.V282_ROUTES, SK[key], ("bar", "wire", "cmd"), nps, nfft)
        for f0 in FR:
            cells, row = [], {"f": f0}
            for nps in (128, 256, 512):
                P, secs = PP[nps]
                if P.n < 6:
                    cells.append("%8s %8s %6s" % ("-", "-", "-")); continue
                h1, c, nb = P.bavg("wire", "bar", f0)
                hv = abs(h1) / np.sqrt(max(c, 1e-9))
                cells.append("%8.2f %8s %6.2f" % (hv, ("%+.0f" % ang(h1)) if c >= 0.40 else "n/a", c))
                row["n%d" % nps] = dict(magHv=float(hv), magH1=float(abs(h1)), ang=ang(h1),
                                        coh=float(c), nbins=int(nb), nwin=int(P.n), secs=float(secs))
            pr("  %6.2f | %s | %s | %s" % (f0, cells[0], cells[1], cells[2]))
            R["%s|%g" % (key, f0)] = row
        for nps in (128, 256, 512):
            P, secs = PP[nps]
            pr("        nperseg %3d : %6.1f s, %5d windows" % (nps, secs, P.n))
    J["longwin"] = R

    pr("")
    pr("  7.1 REPLICATION -- the same nperseg 512 read, per route (r39 and r6c are 1580 s apart)")
    pr("  %-15s %-5s | %s" % ("stratum", "route", "  ".join("%14.2f Hz" % f for f in [10, 12, 13, 14])))
    for key in ("creep_1_3med", "creep_1_6med"):
        for t in BF.V282_ROUTES:
            P, secs = BF.pool_stratum(G, (t,), SK[key], ("bar", "wire"), 512, 2048)
            if P.n < 4:
                continue
            cs = []
            for f0 in (10.0, 12.0, 13.0, 14.0):
                h1, c, _ = P.bavg("wire", "bar", f0)
                cs.append("%6.2f @%+4.0f c%.2f" % (abs(h1) / np.sqrt(max(c, 1e-9)), ang(h1), c))
            pr("  %-15s %-5s | %s   (%d win)" % (key, t, "  ".join(cs), P.n))
