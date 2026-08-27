#!/usr/bin/env python3
"""studies/sessions/v74_v75/v74fault_crux.py -- the four decision-bearing numbers on route 61, plus the bump ranking.

1 `bit7` (gp-0x6bd0 != 0) at the fault frame and around it -- the crux for V77's mechanism
2 vehicle speed at the fault, from vEgo AND independently from wheel speeds -- the 35 km/h knee
3 `state` (gp-0x67fa & 0xF) at the fault and every transition +-10 s
4 does `state` reach 8, and does it ever leave
5 `bit7` duty in manual vs speed, 5 km/h buckets -- the stock mode-24 FactorC knee, on-car
6 the IMU vertical trace around the fault, and where the fault bump ranks among the route's bumps
"""
import os
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
CACHE = Path(os.environ.get("R61_CACHE", ROOT / "_scratch/cache/r61"))
D = dict(np.load(CACHE / "r61.npz"))
t, b7, st = D["t"], D["b7"], D["state"].astype(int)
lat, sca, v = D["cc_lat"], D["sca"], D["cs_v"]
MS2KPH = 3.6
STATE_VALUE_SET = {1, 3, 4, 5, 6, 7, 8, 9, 10, 11}

K = int(np.flatnonzero(D["status"].astype(int) == 4)[0])       # the fault frame
TF = float(t[K])
print("=" * 100)
print(f"FAULT FRAME: index {K}, t = {TF:.6f} s, seg {int(D['seg'][K])}")

# ---- 1. THE CRUX: bit7 -----------------------------------------------------------------------
print("\n" + "=" * 100)
print("1. bit7 = (gp-0x6bd0 != 0)  -- THE DAMPER-NONZERO BIT")
print(f"   ★ AT THE FAULT FRAME: bit7 = {int(b7[K])}   (state {st[K]}, "
      f"status {int(D['status'][K])}, latActive {lat[K]:.0f}, "
      f"STEER_CONTROL_ACTIVE {sca[K]:.0f}, steeringPressed {D['cs_press'][K]:.0f})")
for lab, w in (("5 s", 5.0), ("2 s", 2.0), ("1 s", 1.0), ("0.5 s", 0.5)):
    m = (t >= TF - w) & (t < TF)
    mm = m & (lat <= 0.5)
    me = m & (lat > 0.5)
    print(f"   {lab:6s} before: bit7 duty {100 * b7[m].mean():7.3f}% (n={int(m.sum()):4d})   "
          f"| manual-only {100 * b7[mm].mean() if mm.sum() else float('nan'):7.3f}% "
          f"(n={int(mm.sum()):4d})  | engaged-only "
          f"{100 * b7[me].mean() if me.sum() else float('nan'):7.3f}% (n={int(me.sum()):4d})")
m = (t >= TF) & (t <= TF + 5)
print(f"   5 s AFTER : bit7 duty {100 * b7[m].mean():7.3f}% (n={int(m.sum())})")
print(f"   whole post-fault tail: {100 * b7[t >= TF].mean():7.3f}% (n={int((t >= TF).sum())})")
k0 = int(np.searchsorted(t, TF - 1.0))
run = b7[k0:K + 1]
z = np.flatnonzero(run == 0)
last0 = k0 + int(z[-1]) if len(z) else None
print(f"   last frame with bit7==0 before the fault: " +
      (f"t={t[last0]:.4f} ({TF - t[last0]:.4f} s earlier), i.e. bit7 was CONTINUOUSLY 1 for the "
       f"{K - last0} frames / {TF - t[last0]:.3f} s up to and including the fault"
       if last0 is not None else "none in the last 1 s -- bit7 was 1 throughout"))

# ---- 2. SPEED AT THE FAULT -------------------------------------------------------------------
print("\n" + "=" * 100)
print("2. VEHICLE SPEED AT THE FAULT  -- the stock mode-24 FactorC knee is X[0]=2240 cnt = 35 km/h")
print(f"   carState.vEgo        {v[K]:8.4f} m/s = {v[K] * MS2KPH:8.4f} km/h")
wt, wk = D["ws_t"], D["ws_kph"]
j = int(np.searchsorted(wt, TF)) - 1
fl, fr, rl, rr = wk[j]
print(f"   0x1D0 wheel speeds @ t={wt[j]:.4f}:  FL {fl:.2f}  FR {fr:.2f}  RL {rl:.2f}  RR {rr:.2f} "
      f"km/h  -> mean {np.mean(wk[j]):.4f} km/h = {np.mean(wk[j]) / MS2KPH:.4f} m/s")
print(f"   front-axle mean {(fl + fr) / 2:.4f} km/h · rear-axle mean {(rl + rr) / 2:.4f} km/h")
below = np.mean(wk[j]) < 35.0 and v[K] * MS2KPH < 35.0
print(f"   ⇒ BELOW the 35 km/h knee? {below}    (margin {35.0 - np.mean(wk[j]):+.3f} km/h on wheels, "
      f"{35.0 - v[K] * MS2KPH:+.3f} km/h on vEgo)")
if below and b7[K] == 1:
    print("   🛑🛑 SPEED < 35 km/h AND bit7 == 1 SIMULTANEOUSLY. Under the stock mode-24 FactorC\n"
          "        model (Y[0]=0 below X[0]=2240 counts) gp-0x6bd0 should be STRUCTURALLY ZERO\n"
          "        here. It is NOT. Either the mode is not 24, or gp-0x6bd0 is not the\n"
          "        FactorC-gated damper output. THIS IS A MAJOR FINDING.")
elif below and b7[K] == 0:
    print("   ✅ Speed < 35 km/h and bit7 == 0 -- consistent with the stock table; the damper was\n"
          "      ZERO, so 0xC63A0's weight multiplied zero and V77's mechanism is FALSIFIED here.")

# ---- 3/4. STATE ------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("3/4. STATE (gp-0x67fa & 0xF)")
print(f"   ★ AT THE FAULT FRAME: state = {st[K]}")
ch = np.flatnonzero(np.diff(st) != 0)
print(f"   TOTAL state transitions over the whole {t[-1]:.1f} s route: {len(ch)}")
for c in ch:
    print(f"      t={t[c + 1]:.6f}  {st[c]} -> {st[c + 1]}   (seg {int(D['seg'][c + 1])}, "
          f"{t[c + 1] - TF:+.6f} s relative to the fault)")
near = ch[(t[ch + 1] >= TF - 10) & (t[ch + 1] <= TF + 10)]
print(f"   transitions within +-10 s of the fault: {len(near)}"
      + ("" if len(near) else "  (none besides the ones listed above)"))
reaches8 = bool((st == 8).any())
print(f"   does state reach 8?  {reaches8}")
if reaches8:
    f8 = int(np.flatnonzero(st == 8)[0])
    after = st[f8:]
    print(f"      FIRST state==8 at index {f8}, t={t[f8]:.6f} s (fault frame index {K}; "
          f"{'SAME FRAME' if f8 == K else f'offset {f8 - K} frames'})")
    print(f"      does it ever LEAVE 8?  {bool((after != 8).any())}   "
          f"({int((after == 8).sum())}/{len(after)} frames from there to route end at "
          f"t={t[-1]:.2f} s = {t[-1] - t[f8]:.2f} s latched)")
print("   unreachable-state census (build-identity test, stronger than the payload alphabet):")
n0 = int((st == 0).sum())
nbad = int(np.isin(st, [2, 12, 13, 14, 15]).sum())
print(f"      state == 0                 : {n0}   "
      f"{'<- THE CAVE DID NOT FIRE' if n0 == len(st) else '(0 is structurally unreachable)'}")
print(f"      state in {{2,12,13,14,15}}   : {nbad}")
print(f"      ⇒ {'PASS -- every observed state is inside STATE_VALUE_SET' if n0 + nbad == 0 else 'FAIL'}"
      f"; observed states {sorted(set(st.tolist()))}, all in {sorted(STATE_VALUE_SET)}")

# ---- 5. THE 35 km/h KNEE ---------------------------------------------------------------------
print("\n" + "=" * 100)
print("5. bit7 DUTY vs SPEED, 5 km/h BUCKETS -- an on-car read of the stock mode-24 FactorC knee")
pre = t < TF
kph = v * MS2KPH
edges = np.arange(0, 90, 5.0)
for disc, dlabel in ((lat <= 0.5, "MANUAL (latActive==0)"),
                     (sca <= 0.5, "MANUAL (0x18F STEER_CONTROL_ACTIVE==0)")):
    print(f"\n   {dlabel}   [pre-fault frames only]")
    print("     km/h band     n      bit7 duty")
    for lo in edges:
        m = pre & disc & (kph >= lo) & (kph < lo + 5)
        if not m.sum():
            continue
        mark = "  <-- 35 km/h knee" if lo == 35 else ""
        print(f"     {lo:5.0f}-{lo + 5:5.0f}  {int(m.sum()):7d}   {100 * b7[m].mean():7.3f}%{mark}")
    lo_m = pre & disc & (kph < 35) & (kph > 1)
    hi_m = pre & disc & (kph >= 35)
    print(f"     >1 & <35 km/h {int(lo_m.sum()):7d}   "
          f"{100 * b7[lo_m].mean() if lo_m.sum() else float('nan'):7.3f}%   <- stock table says 0%")
    print(f"     >=35 km/h     {int(hi_m.sum()):7d}   "
          f"{100 * b7[hi_m].mean() if hi_m.sum() else float('nan'):7.3f}%")
print("\n   ENGAGED (latActive==1), same buckets, for contrast:")
for lo in edges:
    m = pre & (lat > 0.5) & (kph >= lo) & (kph < lo + 5)
    if m.sum():
        print(f"     {lo:5.0f}-{lo + 5:5.0f}  {int(m.sum()):7d}   {100 * b7[m].mean():7.3f}%")

# ---- 6. THE IMU / THE BUMP -------------------------------------------------------------------
print("\n" + "=" * 100)
print("6. IMU -- THE EXCITATION CHANNEL")
at = D["at"]
if not len(at):
    print("   NO IMU DATA IN THIS ROUTE.")
    sys.exit(0)
vaxis = str(D["imu_vert_axis"][0])
av = D[vaxis]
print(f"   accel {len(at)} samples, {at[0]:.2f}..{at[-1]:.2f} s, median dt "
      f"{1e3 * np.median(np.diff(at)):.4f} ms -> {1 / np.median(np.diff(at)):.4f} Hz; "
      f"gyro {len(D['gt'])} samples")
print(f"   gravity means: ax {D['ax'].mean():+.4f}  ay {D['ay'].mean():+.4f}  "
      f"az {D['az'].mean():+.4f} m/s^2  ⇒ VERTICAL = {vaxis} "
      f"({abs(av.mean()) / 9.807:.4f} g)  [kit mapping ax=vert, ay=lat, az=long]")
base = float(np.median(av))
print(f"   1 g baseline (route median of {vaxis}) = {base:+.4f} m/s^2; sd {av.std():.4f}")

# tilt-removed residual: subtract a 1 s rolling median, then peak-pick with a 1 s exclusion
dt = float(np.median(np.diff(at)))
w = max(3, int(round(1.0 / dt)) | 1)
pad = np.pad(av, (w // 2, w // 2), mode="edge")
roll = np.array([np.median(pad[i:i + w]) for i in range(len(av))])
res = av - roll
ares = np.abs(res)

print(f"\n   ±3 s AROUND THE FAULT (t {TF - 3:.2f}..{TF + 3:.2f}) -- vertical {vaxis}:")
m = (at >= TF - 3) & (at <= TF + 3)
i_pk = int(np.flatnonzero(m)[np.argmax(ares[m])])
print(f"      peak |{vaxis}| raw           {np.abs(av[m]).max():8.4f} m/s^2")
print(f"      peak |deviation from 1 g|  {np.abs(av[m] - base).max():8.4f} m/s^2 "
      f"({np.abs(av[m] - base).max() / 9.807:.4f} g)")
print(f"      peak |tilt-removed resid|  {ares[i_pk]:8.4f} m/s^2 at t={at[i_pk]:.4f} "
      f"({at[i_pk] - TF:+.4f} s relative to the fault frame)")
mb = (at >= TF - 3) & (at < TF)
ma = (at >= TF) & (at <= TF + 3)
print(f"      BEFORE the fault (-3..0 s): peak resid {ares[mb].max():.4f} at "
      f"t={at[np.flatnonzero(mb)[np.argmax(ares[mb])]] - TF:+.4f} s")
print(f"      AFTER  the fault (0..+3 s): peak resid {ares[ma].max():.4f} at "
      f"t={at[np.flatnonzero(ma)[np.argmax(ares[ma])]] - TF:+.4f} s")
print(f"\n   the 1.0 s before the fault, decimated 5x ({vaxis}, resid):")
mm = (at >= TF - 1.0) & (at <= TF + 0.3)
for i in np.flatnonzero(mm)[::5]:
    print(f"      t={at[i]:9.4f} ({at[i] - TF:+7.4f})  {vaxis}={av[i]:+8.4f}  resid={res[i]:+8.4f}")

# route-wide peak picking
order = np.argsort(-ares)
excl = 1.0
peaks = []
taken = np.zeros(len(at), bool)
for i in order:
    if ares[i] < 0.5:
        break
    if taken[i]:
        continue
    peaks.append(i)
    lo = np.searchsorted(at, at[i] - excl)
    hi = np.searchsorted(at, at[i] + excl)
    taken[lo:hi] = True
print(f"\n   ROUTE-WIDE BUMP RANKING -- {len(peaks)} isolated excursions with |resid| >= 0.5 m/s^2 "
      f"(1 s exclusion):")
print("     rank      t        resid    |dev 1g|   vEgo km/h   d(fault)")
for r, i in enumerate(peaks[:10], 1):
    kk = int(np.clip(np.searchsorted(t, at[i]), 0, len(t) - 1))
    print(f"     {r:4d}  {at[i]:9.4f}  {ares[i]:8.4f}  {abs(av[i] - base):8.4f}  "
          f"{v[kk] * MS2KPH:9.2f}   {at[i] - TF:+9.3f} s")
# where does the fault's own excursion rank?
near_pk = [r for r, i in enumerate(peaks, 1) if abs(at[i] - TF) <= 1.0]
if near_pk:
    r = near_pk[0]
    i = peaks[r - 1]
    print(f"\n   ★ the excursion at the fault ranks #{r} of {len(peaks)} "
          f"(resid {ares[i]:.4f} m/s^2, {100 * (1 - (r - 1) / len(peaks)):.1f}th percentile), "
          f"t={at[i]:.4f} ({at[i] - TF:+.4f} s)")
    print(f"     the LARGEST excursion in the route is {ares[peaks[0]]:.4f} m/s^2 at "
          f"t={at[peaks[0]]:.4f} -- {ares[peaks[0]] / ares[i]:.2f}x the fault's")
else:
    print(f"\n   ★ NO isolated excursion >= 0.5 m/s^2 within 1 s of the fault. Peak resid in the "
          f"±1 s window is {ares[(at >= TF - 1) & (at <= TF + 1)].max():.4f} m/s^2, which ranks "
          f"below {len(peaks)} other excursions in the drive.")
    print(f"     the LARGEST excursion in the route is {ares[peaks[0]]:.4f} m/s^2 at "
          f"t={at[peaks[0]]:.4f} ({at[peaks[0]] - TF:+.1f} s from the fault)")
w1 = (at >= TF - 1) & (at <= TF + 1)
pct = 100.0 * (ares[at < TF] < ares[w1].max()).mean()
print(f"     the ±1 s window's peak resid {ares[w1].max():.4f} m/s^2 sits at the "
      f"{pct:.3f}th percentile of all pre-fault samples")
print(f"\n   npz: {CACHE / 'r61.npz'}")
