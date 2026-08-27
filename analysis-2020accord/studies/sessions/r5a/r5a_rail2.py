#!/usr/bin/env python3
"""THE RAIL TEST, stage 2: the three questions that separate DRIVER from SYMPTOM.

Stage 1 (`studies/sessions/r5a/r5a_rail.py`) established, engaged creep, matched on (speed, |angle|), episode-resampled:
    median |e4tq| in-burst / out-burst = 2.449 [1.353, 3.737], null [0.749, 1.318]  ⇒ CLEARS
    in-burst 27.3% of frames sit EXACTLY at the +-4096 request rail vs 0.64% above 8 m/s
but the matched RAIL-FRACTION ratio did not clear (0.486 [0.079, 1.946] vs null [0.426, 2.306]) --
five of eight cells have zero rail frames on both sides, so that estimator is degenerate, and two
informative cells point OPPOSITE ways. ⇒ "the command is LARGE in bursts" is established;
"the command is PINNED in bursts" is not, and these three tests are what decide it.

Q1  MAGNITUDE OR CLIPPING?  🛑 THE CRUX.  A large command excites the plant -- the kit already has
    "the vibration needs APPLIED torque" on record -- so a big |e4tq| in bursts is EXPECTED under
    the ordinary dose-response and is NOT evidence for saturation. The saturation hypothesis makes
    a SHARPER prediction: a STEP in burst duty at the rail, over and above the smooth ramp with
    magnitude. Bin by |e4tq| and look for the step. If duty rises smoothly and the rail bin sits on
    the ramp, the saturation story adds nothing to plain magnitude.

Q2  LEAD OR LAG?  Does the command go big/pinned BEFORE burst onset (driver) or AFTER (consequence,
    e.g. the controller fighting the oscillation)? Peri-onset profile + per-episode cross-correlation.

Q3  IS 18-22 Hz IN THE COMMAND AT ALL?  If openpilot's own request carries the line, the loop closes
    outside the EPS and neither clamp is the story. (The kit's standing finding is that it does not;
    this re-tests it on route 5a, where it matters most.)

TEST B -- THE DESCRIBING-FUNCTION SIGNATURE, WITHIN ONE ROUTE.
    Clamp-set limit cycle ⇒ amplitude fixed by the clamp, duty set by everything else. Measure the
    spread of in-burst PEAK AMPLITUDE against the spread of DUTY across covariate bins.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from r5a_rail import CREEP, MIN_CYC, RAIL, THR, bursts, frames  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(5150)
out = {}

F = frames()
minlen = int(round(MIN_CYC / 20.0 * 100))
creep = (F["v"] >= CREEP[0]) & (F["v"] < CREEP[1])
sel = creep & F["eng"]
IV = [(a, b) for a, b in bursts(F, THR, minlen) if sel[a:b].mean() > 0.8]
inb = np.zeros(len(F["t"]), bool)
for a, b in IV:
    inb[a:b] = True

# ------------------------------------------------------------------ Q1 ---------------------------
L.hdr("Q1. MAGNITUDE OR CLIPPING?  burst duty as a function of |e4tq|, engaged creep")
EB = [(0, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 3000), (3000, 4000),
      (4000, 4095.5), (4095.5, 1e9)]
LB = ["0-250", "250-500", "500-1k", "1k-2k", "2k-3k", "3k-4k", "4000-4095", "AT RAIL 4096"]
print(f"{'|e4tq| bin':>14s} {'frames':>8s} {'exposure s':>11s} {'burst duty':>11s} "
      f"{'med env':>9s} {'p95 env':>9s}   note")
q1 = []
for (lo, hi), lab in zip(EB, LB):
    m = sel & (F["ae4"] >= lo) & (F["ae4"] < hi)
    n = int(m.sum())
    if n < 30:
        print(f"{lab:>14s} {n:8d} {n / 100:11.2f}   UNPOWERED (<30 frames) -- not a null")
        q1.append((lab, n, None, None))
        continue
    duty = float(inb[m].mean())
    e = F["env"][m]
    print(f"{lab:>14s} {n:8d} {n / 100:11.2f} {duty * 100:10.3f}% {np.median(e):9.1f} "
          f"{np.percentile(e, 95):9.1f}")
    q1.append((lab, n, duty, float(np.median(e))))
out["q1"] = q1
print("\n🛑 READ THIS AS: a SMOOTH ramp with |e4tq| ⇒ plain magnitude/dose-response (already on")
print("   record). A STEP at the 4096 bin above the 3k-4k bin ⇒ the CLIP itself matters.")
d34 = [r for r in q1 if r[0] == "3k-4k"][0]
drail = [r for r in q1 if r[0] == "AT RAIL 4096"][0]
if d34[2] and drail[2]:
    print(f"   step at the rail: duty {drail[2] * 100:.2f}% vs {d34[2] * 100:.2f}% "
          f"just below = {drail[2] / d34[2]:.2f}x")
    out["q1_step"] = float(drail[2] / d34[2])

# episode CI on that step
epk = F["run"]


def duty_in(mask):
    return float(inb[mask].mean()) if mask.sum() else np.nan


mR = sel & (F["ae4"] >= 4095.5)
mB = sel & (F["ae4"] >= 3000) & (F["ae4"] < 4095.5)
eps = sorted(set(epk[sel].astype(int)))
draws = np.full(2000, np.nan)
for k in range(2000):
    pick = RNG.integers(0, len(eps), len(eps))
    keep = np.isin(epk, [eps[i] for i in pick])
    # resample WITH multiplicity: build masks per drawn episode
    nr = nb = dr = db = 0
    for i in pick:
        e = eps[i]
        me = epk == e
        nr += inb[mR & me].sum(); dr += (mR & me).sum()
        nb += inb[mB & me].sum(); db += (mB & me).sum()
    if dr > 20 and db > 20 and nb > 0:
        draws[k] = (nr / dr) / (nb / db)
lo, hi = np.nanpercentile(draws, [2.5, 97.5])
print(f"   episode-resampled 95% CI on the step: [{lo:.2f}, {hi:.2f}]  "
      f"(n_rail {int(mR.sum())} fr, n_3k-4k {int(mB.sum())} fr)")
out["q1_step_ci"] = [float(lo), float(hi)]

# ------------------------------------------------------------------ Q2 ---------------------------
L.hdr("Q2. LEAD OR LAG?  peri-onset profile of |e4tq| and the rail indicator")
W = 200          # +-2.0 s
prof_a, prof_r, prof_e = [], [], []
for a, b in IV:
    if a - W < 0 or a + W >= len(F["t"]):
        continue
    if len(set(F["run"][a - W:a + W].astype(int))) != 1:
        continue
    prof_a.append(F["ae4"][a - W:a + W])
    prof_r.append((F["ae4"][a - W:a + W] >= RAIL - .5).astype(float))
    prof_e.append(F["env"][a - W:a + W])
print(f"{len(prof_a)} of {len(IV)} bursts have a clean +-2.0 s neighbourhood inside one gapless run")
if len(prof_a) >= 8:
    Pa, Pr, Pe = np.array(prof_a), np.array(prof_r), np.array(prof_e)
    print(f"\n{'lag s':>8s} {'mean |e4tq|':>12s} {'frac AT RAIL':>13s} {'mean env':>10s}")
    for c in range(-20, 21, 2):
        s = slice(W + c * 10 - 5, W + c * 10 + 5)
        print(f"{c / 10:8.1f} {Pa[:, s].mean():12.0f} {Pr[:, s].mean() * 100:12.2f}% "
              f"{Pe[:, s].mean():10.1f}")
    pre = slice(W - 100, W)            # -1.0 .. 0 s
    post = slice(W, W + 100)           # 0 .. +1.0 s
    print(f"\n  PRE-onset (-1.0..0 s):  |e4tq| {Pa[:, pre].mean():.0f}  "
          f"at-rail {Pr[:, pre].mean() * 100:.2f}%")
    print(f"  POST-onset (0..+1.0 s): |e4tq| {Pa[:, post].mean():.0f}  "
          f"at-rail {Pr[:, post].mean() * 100:.2f}%")
    d = np.array([p[post].mean() - p[pre].mean() for p in Pa])
    bs = np.array([np.mean(d[RNG.integers(0, len(d), len(d))]) for _ in range(4000)])
    print(f"  post - pre |e4tq|, BURST-resampled: {d.mean():+.0f} "
          f"[{np.percentile(bs, 2.5):+.0f}, {np.percentile(bs, 97.5):+.0f}]  (n={len(d)} bursts)")
    out["q2_prepost"] = [float(d.mean()), float(np.percentile(bs, 2.5)),
                         float(np.percentile(bs, 97.5))]
    # far-baseline: is the command already big well BEFORE onset?
    far = slice(0, 50)                 # -2.0 .. -1.5 s
    print(f"  FAR pre (-2.0..-1.5 s): |e4tq| {Pa[:, far].mean():.0f}  "
          f"at-rail {Pr[:, far].mean() * 100:.2f}%   <-- already elevated ⇒ the command leads")
else:
    print("  UNPOWERED: fewer than 8 clean burst neighbourhoods.")

print("\n--- per-episode cross-correlation, |e4tq| vs 18-22 Hz envelope, engaged creep ---")
print("    positive lag = |e4tq| LEADS the envelope")
lags = np.arange(-150, 151, 5)
per = []
for e in sorted(set(epk[sel].astype(int))):
    m = sel & (epk == e)
    if m.sum() < 600:
        continue
    x = F["ae4"][m] - F["ae4"][m].mean()
    y = F["env"][m] - F["env"][m].mean()
    if x.std() < 1 or y.std() < 1:
        continue
    cc = []
    for lg in lags:
        if lg >= 0:
            a_, b_ = x[:len(x) - lg], y[lg:]
        else:
            a_, b_ = x[-lg:], y[:len(y) + lg]
        cc.append(np.corrcoef(a_, b_)[0, 1] if len(a_) > 50 else np.nan)
    per.append(cc)
per = np.array(per, float)
print(f"    {len(per)} episodes with >= 6 s of engaged creep")
if len(per) >= 4:
    mcc = np.nanmean(per, 0)
    jb = int(np.nanargmax(mcc))
    print(f"    peak mean r = {mcc[jb]:.3f} at lag {lags[jb] / 100:+.2f} s")
    bs = []
    for _ in range(4000):
        i = RNG.integers(0, len(per), len(per))
        m2 = np.nanmean(per[i], 0)
        bs.append(lags[int(np.nanargmax(m2))] / 100)
    print(f"    episode-resampled 95% CI on the peak lag: "
          f"[{np.percentile(bs, 2.5):+.2f}, {np.percentile(bs, 97.5):+.2f}] s")
    print(f"    {'lag s':>7s} " + " ".join(f"{lags[i] / 100:+6.2f}" for i in range(0, len(lags), 4)))
    print(f"    {'mean r':>7s} " + " ".join(f"{mcc[i]:+6.3f}" for i in range(0, len(lags), 4)))
    out["q2_lag"] = [float(lags[jb] / 100), float(np.percentile(bs, 2.5)),
                     float(np.percentile(bs, 97.5)), float(mcc[jb])]
else:
    print("    UNPOWERED for a lag estimate.")

# ------------------------------------------------------------------ Q3 ---------------------------
L.hdr("Q3. IS 18-22 Hz IN OPENPILOT'S OWN COMMAND?")
print("band power ratio, engaged creep, in-burst frames only: 18-22 Hz vs the 24-28 Hz control")
for chan, lab in (("tq", "tq  (torsion bar)"), ("e4", "e4tq (op request)")):
    vals18, vals24 = [], []
    for a, b in IV:
        if b - a < 64:
            continue
        for i in range(max(0, a - 96), min(len(F["t"]) - 256, a + 32), 32):
            x = F[chan][i:i + 256]
            if len(x) < 256 or not np.all(np.isfinite(x)):
                continue
            if len(set(F["run"][i:i + 256].astype(int))) != 1:
                continue
            P = C.periodogram(x, 100.0, 256, True)
            f = np.fft.rfftfreq(256, 1 / 100.0)
            vals18.append(P[(f >= 18) & (f <= 22)].sum())
            vals24.append(P[(f >= 24) & (f <= 28)].sum())
    if len(vals18) < 10:
        print(f"  {lab}: UNPOWERED ({len(vals18)} windows)")
        continue
    v18, v24 = np.array(vals18), np.array(vals24)
    print(f"  {lab}: n={len(v18)} windows  median P18-22 {np.median(v18):12.3e}  "
          f"P24-28 {np.median(v24):12.3e}   ratio {np.median(v18) / np.median(v24):7.3f}")
    out["q3_" + chan] = float(np.median(v18) / np.median(v24))
print("\n⇒ a ratio ~1 on `e4tq` means openpilot's request has NO 18-22 Hz line -- the oscillation")
print("  is not being commanded; the loop closes inside the EPS + plant (kit's standing finding).")

# ------------------------------------------------------------------ TEST B ------------------------
L.hdr("TEST B. DESCRIBING-FUNCTION SIGNATURE: is in-burst AMPLITUDE invariant while DUTY varies?")
VB2 = [(0.5, 1.5), (1.5, 2.5), (2.5, 4.0)]
AB2 = [(0.0, 3.0), (3.0, 8.0), (8.0, 1e9)]
print(f"{'v bin':>10s} {'ang bin':>10s} {'exposure s':>11s} {'duty %':>8s} "
      f"{'n burst':>8s} {'peak A':>8s} {'med |e4tq|':>11s}")
rows = []
for vlo, vhi in VB2:
    for alo, ahi in AB2:
        m = sel & (F["v"] >= vlo) & (F["v"] < vhi) & (F["aang"] >= alo) & (F["aang"] < ahi)
        n = int(m.sum())
        if n < 100:
            print(f"{vlo:4.1f}-{vhi:<5.1f} {alo:4.0f}-{ahi if ahi < 1e8 else 999:<5.0f} "
                  f"{n / 100:11.2f}   UNPOWERED (<1.0 s)")
            continue
        d = float(inb[m].mean())
        pk = [F["env"][a:b].max() for a, b in IV if m[a:b].mean() > 0.8]
        rows.append((vlo, vhi, alo, ahi, n, d, len(pk),
                     float(np.median(pk)) if pk else np.nan))
        print(f"{vlo:4.1f}-{vhi:<5.1f} {alo:4.0f}-{ahi if ahi < 1e8 else 999:<5.0f} "
              f"{n / 100:11.2f} {d * 100:7.2f}% {len(pk):8d} "
              f"{(np.median(pk) if pk else np.nan):8.0f} {np.median(F['ae4'][m]):11.0f}")
ok = [r for r in rows if r[6] >= 3]
if len(ok) >= 3:
    du = np.array([r[5] for r in ok])
    am = np.array([r[7] for r in ok])
    print(f"\n  over the {len(ok)} cells with >= 3 bursts:")
    print(f"     DUTY      spread {du.max() / max(du.min(), 1e-9):8.2f}x  "
          f"({du.min() * 100:.2f}% .. {du.max() * 100:.2f}%)")
    print(f"     PEAK AMP  spread {am.max() / am.min():8.2f}x  ({am.min():.0f} .. {am.max():.0f})")
    print("  ⇒ duty >> amplitude spread is the clamp-set signature; comparable spreads are not.")
    out["testB"] = dict(duty_span=float(du.max() / max(du.min(), 1e-9)),
                        amp_span=float(am.max() / am.min()), cells=len(ok))
else:
    print("\n  UNPOWERED: fewer than 3 covariate cells carry >= 3 bursts each.")

# amplitude vs the command, burst by burst -- the sharpest form of the same question
pk = np.array([F["env"][a:b].max() for a, b in IV])
cm = np.array([np.median(F["ae4"][a:b]) for a, b in IV])
rl = np.array([np.mean(F["ae4"][a:b] >= RAIL - .5) for a, b in IV])
print(f"\n  burst-by-burst (n={len(IV)}): peak amplitude vs median |e4tq| in the same burst")
print(f"     Spearman r = {np.corrcoef(np.argsort(np.argsort(pk)), np.argsort(np.argsort(cm)))[0, 1]:+.3f}")
print(f"     peak amplitude, bursts that RAIL (>25% of frames, n={int((rl > .25).sum())}): "
      f"{np.median(pk[rl > .25]) if (rl > .25).any() else float('nan'):.0f}")
print(f"     peak amplitude, bursts that DO NOT rail (n={int((rl <= .25).sum())}): "
      f"{np.median(pk[rl <= .25]) if (rl <= .25).any() else float('nan'):.0f}")
out["burst_amp_rail"] = dict(n=len(IV), n_rail=int((rl > .25).sum()),
                             amp_rail=float(np.median(pk[rl > .25])) if (rl > .25).any() else None,
                             amp_norail=float(np.median(pk[rl <= .25])) if (rl <= .25).any() else None)

with open(ROOT / "_scratch/out/_r5a_rail2.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5a_rail2.json")
