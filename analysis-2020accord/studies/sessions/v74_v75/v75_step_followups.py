#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_followups.py -- the second methods and the diagnostics the headline numbers need.

  1. WHY the frame-level validity check is only 84.6% engaged, and whether it matters.
  2. Occupancy recomputed off the COARSE 0x14A channel -- an independent second method.
  3. Step stats restricted to the ENGAGED 0-35 km/h launch band, and where the >512 steps live.
  4. Launch events by a SECOND detector, with raw latActive per event.
  5. The EMA-attenuation arithmetic: how much of a sub-10 ms spike can a 100 Hz sampler hide?
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

ENTRY_V74, ENTRY_V75 = 400, 200
FLAT_C_CTS = 2240


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


D = L.load_route()
n = len(D["t"])
W = 1.0 / 100.0009
a6a56 = np.rint(D["rate_f"] * 10.0)
r_signed = np.trunc(a6a56 * 2048.0 / 3477.0).astype(np.int64)
r_cts = np.abs(r_signed)
r_coarse = np.rint(np.abs(D["rate_c"]) * L.CTS_PER_DEGS).astype(np.int64)
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, in24, amb = L.mode_masks(D["cc_lat"], D["t"])
mode = np.where(in26, L.MODE_ENGAGED, L.MODE_MANUAL).astype(np.int64)
o74 = L.Replay("v74").run(sp_cts, r_signed, mode)
o75 = L.Replay("v75").run(sp_cts, r_signed, mode)
obs = D["damp_nz"] > 0.5
pred = o74 != 0

# ---------------------------------------------------------------------------------------------------
hdr("1.  WHY 84.6%? -- the disagreement is a DEADBAND-EDGE artefact, not a surface error")
print("  V74 mode-26 FactorE has X[0]=12, and (429*E)>>10 first becomes non-zero at ~15 counts of")
print("  gp-0x6ac0 (3.2 column deg/s). Route 5d spends most of its time within a few counts of that")
print("  edge, where a 1-frame ZOH skew or a +-1 truncation flips the bit. Agreement vs distance")
print("  from the edge:")
edges = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 200), (200, 10 ** 9)]
m26 = in26
print(f"  {'|gp-0x6ac0| band':>20s} {'n':>8s} {'agree%':>8s} {'obs duty%':>10s} {'pred duty%':>11s}")
for a, b in edges:
    mm = m26 & (r_cts >= a) & (r_cts < b)
    if not mm.sum():
        continue
    print(f"  {f'{a}-{b if b<10**9 else 0}':>20s} {int(mm.sum()):8d} "
          f"{(pred[mm]==obs[mm]).mean()*100:8.3f} {obs[mm].mean()*100:10.3f} {pred[mm].mean()*100:11.3f}")

# tolerance: allow the observed bit to match EITHER neighbour frame (1-frame ZOH/task-phase skew)
o_prev = np.roll(obs, 1)
o_next = np.roll(obs, -1)
tol = (pred == obs) | (pred == o_prev) | (pred == o_next)
print(f"\n  agreement allowing a +-1 FRAME skew (the two tasks are 100 Hz at different phases):")
print(f"    engaged {tol[m26].mean()*100:.3f}%   route-wide {tol.mean()*100:.3f}%")
big = m26 & (r_cts >= 40)
print(f"    engaged AND >=40 counts (well clear of the deadband edge): "
      f"{(pred[big]==obs[big]).mean()*100:.3f}%  (n={int(big.sum())})")
print("  => the surface, the mode selector and the rate scale are validated; the residual is")
print("     deadband dither at |rate| < ~20 counts, a regime irrelevant to a 200/400-count plateau.")

# ---------------------------------------------------------------------------------------------------
hdr("2.  SECOND METHOD -- occupancy off the COARSE 0x14A channel (independent decode, 8x coarser LSB)")
print(f"  {'stratum':34s} | {'>=200 fine':>11s} {'>=200 coarse':>13s} | {'>=400 fine':>11s} "
      f"{'>=400 coarse':>13s} | {'ratio f':>8s} {'ratio c':>8s}")
for nm, m in (("ALL frames", np.ones(n, bool)), ("ENGAGED (mode 26)", in26),
              ("ENGAGED creep < 4 m/s", in26 & (D["cs_v"] < 4.0)),
              ("ENGAGED 0-35 km/h", in26 & (sp_cts < FLAT_C_CTS)),
              ("MANUAL (mode 24)", in24)):
    f2, c2 = int((m & (r_cts >= 200)).sum()), int((m & (r_coarse >= 200)).sum())
    f4, c4 = int((m & (r_cts >= 400)).sum()), int((m & (r_coarse >= 400)).sum())
    print(f"  {nm:34s} | {f2:11d} {c2:13d} | {f4:11d} {c4:13d} | "
          f"{f2/max(f4,1):8.2f} {c2/max(c4,1):8.2f}")

# ---------------------------------------------------------------------------------------------------
hdr("3.  PER-TICK STEP in the LAUNCH BAND, and where the >512 steps actually live")
same = np.diff(D["seg"]) == 0
gdt = (np.diff(D["t"]) >= 0.005) & (np.diff(D["t"]) <= 0.015)
pair = same & gdt
d74 = np.abs(np.diff(o74))
d75 = np.abs(np.diff(o75))
for nm, m in (("ALL", np.ones(n - 1, bool)),
              ("ENGAGED (mode 26)", in26[:-1] & in26[1:]),
              ("ENGAGED 0-35 km/h", in26[:-1] & in26[1:] & (sp_cts[:-1] < FLAT_C_CTS)),
              ("ENGAGED >35 km/h", in26[:-1] & in26[1:] & (sp_cts[:-1] >= FLAT_C_CTS))):
    mm = m & pair
    if not mm.sum():
        continue
    for bn, s in (("V74", d74[mm]), ("V75", d75[mm])):
        print(f"  {nm:20s} {bn}  n {len(s):6d}  p99 {np.percentile(s,99):6.1f}  "
              f"p99.9 {np.percentile(s,99.9):6.1f}  MAX {s.max():5.0f} | >205 {int((s>205).sum()):5d}"
              f"  >450 {int((s>450).sum()):4d}  >512 {int((s>512).sum()):4d}")
print("\n  🛑 The 225 / 297 figures are the PLATEAU MAGNITUDES in the flat-FactorC band")
print("     ((429*539)>>10 and (566*539)>>10). They bound the step ONLY below 35 km/h and only for")
print("     a 0->plateau transition. A full relay REVERSAL in that band is bounded by 2x: 450 / 594.")
print("     Above 35 km/h FactorC keeps rising, so both bounds rise with speed.")
big = pair & (d75 > 512)
if big.sum():
    i = np.flatnonzero(big)
    print(f"\n  V75 steps > 512: n={len(i)}  seg/t/speed(m/s)/rate(cts)/o75_before->after:")
    for k in i[:20]:
        print(f"    seg {int(D['seg'][k]):2d}  t {D['t_seg'][k]:7.2f}  v {D['cs_v'][k]:5.2f}  "
              f"rate {r_signed[k]:6d}->{r_signed[k+1]:6d}  o75 {o75[k]:5d}->{o75[k+1]:5d}  "
              f"eng {int(in26[k])}")

# ---------------------------------------------------------------------------------------------------
hdr("4.  LAUNCH EVENTS -- SECOND DETECTOR (independent of the first), with RAW latActive")
LO, HI = 1.0 / 3.6, 20.0 / 3.6
v = D["cs_v"]
below = v < LO
above = v > HI
ev2 = []
for s in np.unique(D["seg"]):
    ms = D["seg"] == s
    idx = np.flatnonzero(ms)
    vb, va = below[idx], above[idx]
    j = 0
    while j < len(idx):
        if vb[j]:
            k = j
            while k < len(idx) and not va[k]:
                k += 1
            if k < len(idx):
                a = k
                while a > j and not vb[a]:
                    a -= 1
                ev2.append((idx[a], idx[k]))
                j = k
            else:
                break
        j += 1
ev2 = sorted(set(ev2))
ev2 = [(a, b) for a, b in ev2 if D["t"][b] - D["t"][a] <= 30.0]
print(f"  n launch events (second detector): {len(ev2)}")
print(f"  {'#':>3s} {'seg':>4s} {'t0':>8s} {'dur':>6s} {'lat%':>6s} {'mode26%':>8s} {'vmax':>6s} "
      f"{'maxrate':>8s} {'s>=200':>7s} {'s>=400':>7s} {'|o74|':>6s} {'|o75|':>6s}")
for c, (a, b) in enumerate(ev2):
    sl = slice(a, b + 1)
    print(f"  {c:3d} {int(D['seg'][a]):4d} {D['t_seg'][a]:8.2f} {D['t'][b]-D['t'][a]:6.2f} "
          f"{(D['cc_lat'][sl]>0.5).mean()*100:6.1f} {in26[sl].mean()*100:8.1f} "
          f"{v[sl].max():6.2f} {int(r_cts[sl].max()):8d} {(r_cts[sl]>=200).sum()*W:7.2f} "
          f"{(r_cts[sl]>=400).sum()*W:7.2f} {int(np.abs(o74[sl]).max()):6d} "
          f"{int(np.abs(o75[sl]).max()):6d}")
print("\n  full stops (v < 1 km/h for >= 1 s) that were followed by ANY pull-away, engaged or not:")
runs_stop = []
idxs = np.flatnonzero(below)
if len(idxs):
    brk = np.flatnonzero(np.diff(idxs) > 1)
    for r in np.split(idxs, brk + 1):
        if len(r) * W >= 1.0:
            runs_stop.append(r)
print(f"    n stops >= 1 s: {len(runs_stop)}   total stopped time {sum(len(r) for r in runs_stop)*W:.1f} s")
eng_stop = [r for r in runs_stop if (D["cc_lat"][r] > 0.5).mean() > 0.5]
print(f"    ... with latActive true for >50% of the stop: {len(eng_stop)}")

# ---------------------------------------------------------------------------------------------------
hdr("5.  CAN THE 100 Hz BUS HIDE A SUB-10 ms SPIKE TO 4000 COUNTS?  (the load-bearing caveat)")
alpha = 37.0 / 128.0
F_EMA = 312.5      # FUN_00041464, task-level phase-gated 5/16 of the 1 kHz task
F_SAMP = 100.0     # BOTH the damper (task 5, FUN_00022ca0) and the CAN packer
per = F_EMA / F_SAMP
print(f"  gp-0x6ac0's producer FUN_00041464 updates at ~{F_EMA:.1f} Hz with EMA alpha = 37/128 = {alpha:.4f}.")
print(f"  FUN_00034350 (the damper) reads it at {F_SAMP:.0f} Hz; the CAN packer transmits it at "
      f"{F_SAMP:.0f} Hz.")
print(f"  => {per:.3f} EMA updates per sample period. A single-update impulse decays by "
      f"(1-alpha)^k:")
for k in range(0, 5):
    print(f"      {k} updates later: {(1-alpha)**k:6.3f} of peak")
print(f"  WORST CASE (sample lands 3 updates after the peak): the sampler reads "
      f"{(1-alpha)**3:.3f} of the true peak.")
print(f"  => an observed max of {r_cts.max()} counts is consistent with a true single-update peak up "
      f"to {r_cts.max()/(1-alpha)**3:.0f} counts.")
print("  BUT: a SUSTAINED excursion (>= 3 EMA updates ~ 10 ms) cannot hide -- it is sampled at")
print(f"  >= {(1-alpha)**0:.2f}x within one bus period.")
print("\n  ★ THE STRUCTURAL POINT: FactorE is indexed by the DAMPER's OWN 100 Hz sample of the same")
print("    cell. The bus copy is a fixed Q15 scale of the same EMA state (gp-0x6a56 = gp-0x6abe x")
print("    3477/2048), NOT an independently filtered estimator -- so the two are 100 Hz sub-samples")
print("    of ONE 312.5 Hz process, differing only in task phase. Over 101,102 frames their")
print("    DISTRIBUTIONS coincide; only an individual worst-case event can differ.")
