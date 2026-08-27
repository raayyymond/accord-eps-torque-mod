#!/usr/bin/env python3
r"""Part 2 -- harden the 6-35 Hz Re(Z) extension and the D rotation.

  H1  500-draw phase-randomised surrogate DISTRIBUTION for Re(Z) and for d (not one draw)
  H2  WHEEL-ORDER veto, per band, on the D rotation -- 26-31 Hz sits on order 5 at the modal speed
  H3  SPEED-MATCHED pooling across the three drives
  H4  the exact delay / low-pass thresholds that flip each verdict (root-found, not swept)
  H5  the phase-vs-frequency slope over 16-35 Hz -- the delay-like diagnostic, stated as a LIMIT
  H6  Kd dose response: d for Kd = 2048 (stock) vs 1024 (V110), and the delta per band
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rez_3drive_and_D_rotation import (  # noqa: E402
    ALL, BANDS, FINE, NB, NW, HOP, RNG, H_D, band_stats, boot, build, ci, load, runs_of, accum)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CIRC_LO, CIRC_HI, ORDERS, GUARD = 2.073, 2.088, (1, 2, 3, 4, 5, 6), 0.8
ROUTES = ["77", "78", "79"]
hdr = lambda s: print("\n" + "=" * 100 + f"\n{s}\n" + "=" * 100, flush=True)


def order_conflict(v, lo, hi):
    return any(lo - GUARD <= k * v / c <= hi + GUARD
               for k in ORDERS for c in (CIRC_LO, CIRC_HI))


arms = {r: build(r, "engaged") for r in ROUTES}
Ap = np.concatenate([arms[r]["A"] for r in ROUTES])
vp = np.concatenate([arms[r]["v"] for r in ROUTES])
off, epp, rid = 0, [], []
for r in ROUTES:
    epp.append(arms[r]["ep"] + off)
    rid.append(np.full(len(arms[r]["A"]), int(r)))
    off += arms[r]["n_ep"]
epp = np.concatenate(epp)
rid = np.concatenate(rid)
sp = band_stats(Ap)
KEY = ["6-9", "16-18", "18-22", "22-26", "26-31", "31-35"]
KI = [b[0] for b in BANDS]

# =============================================================================== H1
hdr("H1  500-DRAW PHASE-RANDOMISED SURROGATE DISTRIBUTION (route 77 engaged)\n"
    "    |Y(f)| preserved, phase iid uniform.  This is the null for BOTH Re(Z) and d.")
d = load("77")
mask = d["lat"] & (~d["press"]) & (d["v"] > 0.5)
wx, wy = [], []
for a, b in runs_of(mask, d["t"], NW):
    for i in range(0, (b - a) - NW + 1, HOP):
        sl = slice(a + i, a + i + NW)
        wx.append(d["rate_f"][sl])
        wy.append(d["tq"][sl])
w = np.hanning(NW)
YM = [np.abs(np.fft.rfft((y - y.mean()) * w)) for y in wy]
nulls = []
for _ in range(500):
    A = []
    for i in range(len(wx)):
        ph = RNG.uniform(-np.pi, np.pi, len(YM[i]))
        ph[0] = 0.0
        ys = np.fft.irfft(YM[i] * np.exp(1j * ph), NW)
        A.append(accum(wx[i], ys / w.clip(1e-9), d["fs"])[0])
    nulls.append(band_stats(np.array(A)))
NR = np.array([n["rez"] for n in nulls])
ND = np.array([n["dnorm"] for n in nulls])
NC = np.array([n["coh"] for n in nulls])
s77 = band_stats(arms["77"]["A"])
print(f"  {'band':7s} {'REAL Re(Z)':>11s} {'null p50':>9s} {'null 95%':>19s} {'|z-score|':>10s} "
      f"| {'REAL d':>8s} {'null d 95%':>19s} {'REAL coh²':>10s} {'null coh² p95':>14s}")
for i, nm in enumerate(KI):
    zs = abs(s77["rez"][i] - NR[:, i].mean()) / NR[:, i].std()
    zd = abs(s77["dnorm"][i] - ND[:, i].mean()) / ND[:, i].std()
    print(f"  {nm:7s} {s77['rez'][i]:11.0f} {np.median(NR[:, i]):9.0f} "
          f"[{np.percentile(NR[:, i], 2.5):8.0f},{np.percentile(NR[:, i], 97.5):8.0f}] "
          f"{zs:10.1f} | {s77['dnorm'][i]:8.4f} "
          f"[{np.percentile(ND[:, i], 2.5):8.4f},{np.percentile(ND[:, i], 97.5):8.4f}] "
          f"{s77['coh'][i]:10.3f} {np.percentile(NC[:, i], 95):14.4f}   d z={zd:.1f}")

# =============================================================================== H2
hdr("H2  WHEEL-ORDER VETO on the D rotation.  Orders 1-6, circumference 2.073-2.088 m, "
    "guard 0.8 Hz.\n    26-31 Hz is hit by ORDER 5 at ~11.8 m/s -- the modal speed of every drive.")
print(f"  {'band':7s} {'arm':9s} " + " ".join(f"{'r'+r:>9s}" for r in ROUTES) +
      f" {'POOLED':>9s} {'n pooled':>9s}")
for nm, lo, hi in BANDS:
    if nm not in KEY:
        continue
    i = KI.index(nm)
    for vet in (False, True):
        vals, tot = [], []
        for r in ROUTES:
            b = arms[r]
            sel = np.flatnonzero(~np.array([order_conflict(x, lo, hi) for x in b["v"]])) if vet \
                else np.arange(len(b["A"]))
            vals.append(band_stats(b["A"], sel)["dnorm"][i] if len(sel) >= 6 else np.nan)
        selp = np.flatnonzero(~np.array([order_conflict(x, lo, hi) for x in vp])) if vet \
            else np.arange(len(Ap))
        pooled = band_stats(Ap, selp)["dnorm"][i]
        print(f"  {nm:7s} {'VETOED' if vet else 'all':9s} " +
              " ".join(f"{v:9.4f}" for v in vals) + f" {pooled:9.4f} {len(selp):9d}")

# =============================================================================== H3
hdr("H3  SPEED-MATCHED POOLING.  Windows binned by their own mean |speed| in 2 m/s bins;\n"
    "    each drive contributes the SAME number of windows per bin (min across drives).")
bins = np.arange(0, 34, 2.0)
bi = np.digitize(vp, bins)
keep = []
for bb in np.unique(bi):
    per = [np.flatnonzero((bi == bb) & (rid == int(r))) for r in ROUTES]
    n = min(len(p) for p in per)
    if n == 0:
        continue
    for p in per:
        keep.append(RNG.choice(p, n, replace=False))
keep = np.concatenate(keep) if keep else np.array([], int)
print(f"  matched pool: {len(keep)} windows "
      f"({', '.join(f'r{r}={int((rid[keep]==int(r)).sum())}' for r in ROUTES)}), "
      f"v med {np.median(vp[keep]):.2f} m/s")
sm = band_stats(Ap, keep)
bm = boot(Ap[keep], epp[keep], nboot=2000)
lo_, hi_ = ci(bm["dnorm"])
print(f"\n  {'band':7s} {'d unmatched':>12s} {'d MATCHED':>11s} {'[95% CI]':>20s} "
      f"{'Re(Z) matched':>14s} {'phase':>8s} {'coh²':>7s}")
for i, nm in enumerate(KI):
    print(f"  {nm:7s} {sp['dnorm'][i]:12.4f} {sm['dnorm'][i]:11.4f} "
          f"[{lo_[i]:9.4f},{hi_[i]:9.4f}] {sm['rez'][i]:14.0f} {sm['phase'][i]:7.1f}° "
          f"{sm['coh'][i]:7.3f}")

# =============================================================================== H4
hdr("H4  THE EXACT FLIP THRESHOLDS.  d changes sign only when the MEASURED phase is rotated\n"
    "    past the quadrature boundary.  Root-found on the pooled phase, per band.")
fcent = {nm: 0.5 * (lo + hi) for nm, lo, hi in BANDS}
fcent["6-9"] = 7.79


def dval(nm, rot, phase_src=None):
    i = KI.index(nm)
    f = fcent[nm]
    h = complex(np.atleast_1d(H_D(f))[0])
    ph = np.radians((sp["phase"][i] if phase_src is None else phase_src) + rot)
    return -abs(h) * np.cos(ph + np.angle(h))


print(f"  {'band':7s} {'f_c':>6s} {'pooled phase':>13s} {'argH_D':>8s} {'sum':>8s} {'d':>9s} "
      f"{'rot to flip':>12s} {'=> tau ms':>10s} {'=> LP fc Hz':>12s}")
for nm in KEY:
    i = KI.index(nm)
    f = fcent[nm]
    h = complex(np.atleast_1d(H_D(f))[0])
    ssum = sp["phase"][i] + np.degrees(np.angle(h))
    d0 = -abs(h) * np.cos(np.radians(ssum))
    # nearest rotation that puts the sum on the +-90 boundary
    cands = []
    for target in (-90.0, 90.0, 270.0, -270.0):
        cands.append(((target - ssum + 180) % 360) - 180)
    rot = min(cands, key=abs)
    tau = rot / 360.0 / f * 1000.0
    fclp = f / np.tan(np.radians(rot)) if 0 < rot < 90 else np.nan
    print(f"  {nm:7s} {f:6.2f} {sp['phase'][i]:12.1f}° {np.degrees(np.angle(h)):7.1f}° "
          f"{ssum:7.1f}° {d0:9.4f} {rot:+11.1f}° {tau:10.2f} "
          f"{(f'{fclp:.1f}' if np.isfinite(fclp) else 'n/a'):>12s}")
print("\n  tau > 0 == the TORQUE field lags the RATE field inside the same 0x18F frame.")
print("  LP fc  == a single-pole low-pass on the torque channel alone with that corner.")

# =============================================================================== H5
hdr("H5  THE DELAY-LIKE DIAGNOSTIC, stated as a LIMIT, not a correction.")
fs_ = np.array([fcent[nm] for nm in ("16-18", "18-22", "22-26", "26-31", "31-35")])
ph_ = np.array([sp["phase"][KI.index(nm)]
                for nm in ("16-18", "18-22", "22-26", "26-31", "31-35")])
sl, ic_ = np.polyfit(fs_, ph_, 1)
print(f"  Pooled arg Z falls linearly over 16-35 Hz:  {sl:.2f} deg/Hz  "
      f"(intercept {ic_:.1f} deg, resid rms {np.std(ph_ - (sl*fs_+ic_)):.1f} deg)")
print(f"  A PURE DELAY of tau produces -0.360*tau[ms] deg/Hz  ⇒  this slope alone would be "
      f"tau = {-sl/0.360:.1f} ms")
print("  🛑 That is NOT a measurement of instrument delay -- a closed loop and a structural mode")
print("     both produce falling phase too.  It is an UPPER BOUND on how much delay could be")
print("     hiding there, and it is the single largest threat to the 18-22 verdict.")
for nm in ("2-4", "4-6", "6-9", "9-12", "12-16"):
    i = KI.index(nm)
    print(f"     cross-check {nm:6s} f={fcent[nm]:5.2f}  measured {sp['phase'][i]:7.1f}°  "
          f"vs the 16-35 Hz line's extrapolation {sl*fcent[nm]+ic_:7.1f}°")

# =============================================================================== H6
hdr("H6  THE ACTUAL DOSE.  Kd 2048 -> 1024 halves |H_D| at every frequency.\n"
    "    delta_d = d(1024) - d(2048) = -d(2048)/2.  Sign of delta says HELP or HURT.")
bp = boot(Ap, epp, nboot=3000)
dlo, dhi = ci(bp["dnorm"])
print(f"  {'band':7s} {'d stock':>9s} {'d V110':>9s} {'delta':>9s} {'[95% CI on delta]':>22s} "
      f"{'effect of halving Kd':>24s}")
for i, nm in enumerate(KI):
    d0 = sp["dnorm"][i]
    dd = -d0 / 2.0
    l, h = -dhi[i] / 2.0, -dlo[i] / 2.0
    verd = "HELPS (removes pump)" if dd < 0 else "HURTS (removes damping)"
    print(f"  {nm:7s} {d0:9.4f} {d0/2:9.4f} {dd:+9.4f} [{l:+10.4f},{h:+10.4f}] {verd:>24s}")
print("\n  Ratio of cost to benefit, pooled, normalised (the Q-relevant form):")
b69 = sp["dnorm"][KI.index("6-9")] / 2
for nm in ("16-18", "18-22", "22-26", "26-31", "31-35"):
    c = abs(sp["dnorm"][KI.index(nm)] / 2)
    print(f"    {nm:7s} cost {c:.4f}  vs  6-9 benefit {b69:.4f}   =  {c/b69:5.2f}x")
print("\n  ⚠ The SAME trade in ABSOLUTE ct·s/rad (rate_f scale) reverses the ordering:")
for nm in ("6-9", "16-18", "18-22", "22-26", "26-31", "31-35"):
    i = KI.index(nm)
    print(f"    {nm:7s} -Re(Z_D)/2 = {-sp['reZD'][i]/2:+8.1f}   against |Z| {sp['absz'][i]:7.0f} "
          f"and Re(Z) {sp['rez'][i]:8.0f}")
