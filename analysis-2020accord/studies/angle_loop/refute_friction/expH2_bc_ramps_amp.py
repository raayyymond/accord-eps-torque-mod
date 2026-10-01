"""EXP H2: slow ramps + small-amplitude tracking on the bias-corrected world 'bc' (see expH_biascorrected.py)."""
import numpy as np
from dataclasses import replace
import fric_lib as F
VP = F.VP
_fam = VP.family
def fam2():
    f = _fam()
    nom, blo = f["nominal"], f["b_lo"]
    fx = np.where(VP.V_CENTRES >= 10.0, 2.0, np.where(VP.V_CENTRES >= 5.0, 1.3, 1.0))
    f["bc"] = replace(blo, name="bc", Fc=nom.Fc * fx, Fs=nom.Fs * fx)
    return f
VP.family = fam2
T0, TR, TH = 1.0, 8.0, 4.0
DUR = T0 + TR + TH + TR + TH
def mkref(r):
    A = r * TR
    return lambda t: float(np.interp(t, [0, T0, T0 + TR, T0 + TR + TH, T0 + 2 * TR + TH, DUR], [0, 0, A, A, 0, 0]))
cols = [dict(member="bc", v=v, rate=r, ref=mkref(r)) for v in (8.0, 10.0, 12.5, 15.0, 19.0, 26.0) for r in (0.25, 0.5, 1.0, 2.0)]
rec = F.run(cols, DUR)
ev, jmax, dw, stick = F.dj_on(rec, T0, DUR)
print("SLOW RAMPS, world bc:  v  rate | dj events  max snap")
for j, c in enumerate(cols):
    print("   %5.1f %4.2f | %3d  %5.2f" % (c["v"], c["rate"], ev[j], jmax[j]))
cols = [dict(member="bc", v=v, amp=a, f=f, ref=lambda t, a=a, f=f: a * np.sin(2 * np.pi * f * t))
        for v in (8.0, 12.5, 19.0, 26.0) for a in (0.3, 0.5, 1.0, 2.0) for f in (0.2, 0.5)]
rec = F.run(cols, 15.0)
wire = rec["wire"].astype(float) / 10.0
nf = wire.shape[0]
idx = (np.arange(nf) * 10 + F.HT.SLOT4_PHASE).clip(0, rec["th"].shape[0] - 1)
fr_t = idx * 1e-3
print("SMALL AMPLITUDE, world bc:  v  amp  f | tracking gain (harness definition)")
for j, c in enumerate(cols):
    fw = fr_t >= 1.0 / c["f"]
    X = rec["sp"][idx, j][fw].astype(float); Y = wire[fw, j]; xm = X - X.mean()
    g = (xm * (Y - Y.mean())).sum() / (xm ** 2).sum()
    print("   %5.1f %4.1f %4.1f | %6.3f%s" % (c["v"], c["amp"], c["f"], g, "  <-- outside" if not 0.95 <= g <= 1.05 else ""))
