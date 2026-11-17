"""Onset / offset statistics of buzz episodes (BZ>4 for >=0.5 s, gaps <0.2 s merged). usage: <cache dir>
Onset growth = samples from the first |hr|>3 deg/s (looking back from the episode start) to the first sample with |hr| >= 0.8 x episode p90|hr|.
Pre-onset trigger = |lp rate| max and |delta tq| in the 0.5 s before; offset = what changed across the end."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs

C = sys.argv[1]
ons, offs = [], []
for seg, p in segs(C):
    d = load(p)
    on = d["bz"] > 4
    idx = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    M = []
    for s, e in zip(idx[0::2], idx[1::2]):
        if M and s - M[-1][1] < 20:
            M[-1][1] = e
        else:
            M.append([s, e])
    for s, e in M:
        if e - s < 50 or s < 80 or e > len(d["t"]) - 60 or d["v"][s:e].mean() < 2:
            continue
        hr = d["hr"]
        amp = np.percentile(np.abs(hr[s:e]), 90)
        # back off to the true start (envelope window is centred, 16 samples wide)
        k0 = s - 16
        while k0 > s - 60 and np.abs(hr[k0 - 3:k0]).max() > 3:
            k0 -= 1
        k1 = k0 + int(np.argmax(np.abs(hr[k0:e]) >= 0.8 * amp))
        pre = slice(k0 - 50, k0)
        ons.append((seg, d["t"][k0], d["req"][s:e].mean(), k1 - k0, amp, np.abs(d["rlp"][pre]).max(), np.abs(d["rlp"][k0 - 5:k0 + 5]).max(),
                    d["tlp"][k0] - d["tlp"][k0 - 50], np.abs(d["tlp"][pre]).mean(), np.abs(d["ang"][k0])))
        a, b = slice(e - 50, e - 16), slice(e + 16, e + 50)
        offs.append((d["req"][s:e].mean(), np.abs(d["tlp"][a]).mean(), np.abs(d["tlp"][b]).mean(), d["v"][a].mean(), d["v"][b].mean(),
                     np.abs(d["ang"][a]).mean(), np.abs(d["ang"][b]).mean(), d["req"][a].mean(), d["req"][b].mean(),
                     np.abs(d["rlp"][a]).mean(), np.abs(d["rlp"][b]).mean(), d["pressed"][b].mean()))
O = np.array(ons, float)
F = np.array(offs, float)
print("== %s  episodes %d (engaged %d, manual %d)" % (C, len(O), (O[:, 2] > 0.5).sum(), (O[:, 2] <= 0.5).sum()))
print("ONSET growth to 80%% amplitude (samples): p10/p50/p90 %s ; amplitude p90|hr| p10/p50/p90 %s deg/s" % (
    np.percentile(O[:, 3], [10, 50, 90]), np.round(np.percentile(O[:, 4], [10, 50, 90]), 1)))
print("ONSET pre-trigger: max |lp rate| in 0.5 s before p10/p50/p90 %s deg/s; |lp rate| at onset p50 %.1f ; dtq over 0.5 s p10/p50/p90 %s ; |tq| before p50 %.0f ; |ang| at onset p50 %.1f" % (
    np.round(np.percentile(O[:, 5], [10, 50, 90]), 1), np.median(O[:, 6]), np.round(np.percentile(O[:, 7], [10, 50, 90])), np.median(O[:, 8]), np.median(O[:, 9])))
for lab, m in (("engaged", O[:, 2] > 0.5), ("manual", O[:, 2] <= 0.5)):
    print("   %-8s n=%3d growth p50 %4.0f samples, pre max|rate| p50 %.1f, onset |rate| p50 %.1f, |tq| before p50 %.0f" % (
        lab, m.sum(), np.median(O[m, 3]), np.median(O[m, 5]), np.median(O[m, 6]), np.median(O[m, 8])))
print("OFFSET (last 0.34 s in vs first 0.34 s out), medians:")
for lab, m in (("engaged", F[:, 0] > 0.5), ("manual", F[:, 0] <= 0.5)):
    f = F[m]
    print("   %-8s n=%3d |tq| %4.0f -> %4.0f (rose >1.5x in %2.0f%%) | v %.1f->%.1f | |ang| %.1f->%.1f | req %.2f->%.2f | |rate| %.1f->%.1f | pressed after %.0f%%" % (
        lab, m.sum(), np.median(f[:, 1]), np.median(f[:, 2]), 100 * np.mean(f[:, 2] > 1.5 * f[:, 1]), np.median(f[:, 3]), np.median(f[:, 4]),
        np.median(f[:, 5]), np.median(f[:, 6]), np.mean(f[:, 7]), np.mean(f[:, 8]), np.median(f[:, 9]), np.median(f[:, 10]), 100 * np.mean(f[:, 11] > 0.5)))
    print("            ending modes: tq rose >1.5x %d, req dropped %d, |rate| rose >2x %d, v<3 after %d, none of these %d" % (
        (f[:, 2] > 1.5 * f[:, 1]).sum(), ((f[:, 7] > 0.5) & (f[:, 8] < 0.5)).sum(), (f[:, 10] > 2 * f[:, 9] + 2).sum(), (f[:, 4] < 3).sum(),
        (~((f[:, 2] > 1.5 * f[:, 1]) | ((f[:, 7] > 0.5) & (f[:, 8] < 0.5)) | (f[:, 10] > 2 * f[:, 9] + 2) | (f[:, 4] < 3))).sum()))
