#!/usr/bin/env python3
"""Verify the signal decode and resolve the engagement-proxy question BEFORE any spectral work."""
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

OUT = Path(r"C:\Users\dudei\AppData\Local\Temp\claude"
           r"\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod"
           r"\a179e27a-7fe7-49ee-b2a8-e84c074404f9\scratchpad")
tag = sys.argv[1] if len(sys.argv) > 1 else "r29s0"
d = dict(np.load(OUT / (tag + ".npz")))

n = len(d["t"])
print(f"{tag}:  n={n}  span={d['t'][-1]:.2f}s")

print("\n=== 1. DECODE SANITY ===")
u = lambda k: {int(a): int(b) for a, b in zip(*np.unique(d[k], return_counts=True))}
print(f"  0x18F STEER_STATUS (byte4>>4 & 0xF) hist : {u('sstat')}")
print(f"  0x18F byte4 bits 2:0 hist                : {u('slow3')}")
print(f"  0x18F STEER_CONTROL_ACTIVE (bit3)        : {int(d['sca'].sum())}/{n} "
      f"({100*d['sca'].mean():.2f}%)")

print(f"\n  carState.steeringAngleDeg: min {d['cs_ang'].min():.2f} max {d['cs_ang'].max():.2f} "
      f"std {d['cs_ang'].std():.4f}   <-- std 0 => field not populated by this fork")
print(f"  carState.steeringTorque  : min {d['cs_tq'].min():.2f} max {d['cs_tq'].max():.2f} "
      f"std {d['cs_tq'].std():.4f}")
print(f"  carState.vEgo            : min {d['cs_v'].min():.3f} max {d['cs_v'].max():.3f} "
      f"std {d['cs_v'].std():.4f}")

print(f"\n  0x14A STEER_ANGLE      : min {d['ang'].min():8.1f} max {d['ang'].max():8.1f} "
      f"std {d['ang'].std():7.2f} deg")
print(f"  0x14A STEER_WHEEL_ANGLE: min {d['wang'].min():8.1f} max {d['wang'].max():8.1f} "
      f"std {d['wang'].std():7.2f} deg")
tw = d["wang"] - d["ang"]
print(f"  twist = WHEEL-ANGLE    : min {tw.min():8.2f} max {tw.max():8.2f} std {tw.std():7.3f} deg"
      f"   corr(twist, torque) = {np.corrcoef(tw, d['tq'])[0,1]:+.4f}")

# rate cross-checks on a UNIFORM grid (duplicate CAN timestamps break np.gradient)
FS = n / (d["t"][-1] - d["t"][0])
tu = np.arange(n) / FS
dang = np.gradient(d["ang"], tu)
print(f"\n  effective fs = {FS:.4f} Hz  (uniform grid used for all derivatives/spectra)")
print(f"  corr(0x18F fine rate, 0x14A coarse rate) = {np.corrcoef(d['rate_f'], d['rate_c'])[0,1]:+.6f}"
      f"   slope(coarse~fine) = {np.polyfit(d['rate_f'], d['rate_c'],1)[0]:.4f}")
print(f"  corr(0x18F fine rate, d(ANGLE)/dt)       = {np.corrcoef(d['rate_f'], dang)[0,1]:+.6f}"
      f"   slope(fine~dAng) = {np.polyfit(dang, d['rate_f'],1)[0]:.4f}")
print(f"  corr(0x14A coarse rate, d(ANGLE)/dt)     = {np.corrcoef(d['rate_c'], dang)[0,1]:+.6f}"
      f"   slope(coarse~dAng) = {np.polyfit(dang, d['rate_c'],1)[0]:.4f}")
print(f"  rms: fine {d['rate_f'].std():.2f}  coarse {d['rate_c'].std():.2f}  dAng/dt {dang.std():.2f} deg/s")
print(f"  fine rate |max| {np.abs(d['rate_f']).max():.1f} deg/s -- saturation of the i16*0.1 field "
      f"would be 3276.7; rail hits: {int((np.abs(d['rate_f'])>3270).sum())}")
q = np.unique(np.round(np.abs(np.diff(np.unique(d['rate_f']))), 6))
print(f"  fine-rate quantum (smallest nonzero step): {q[q>0][0] if (q>0).any() else 0:.4f} deg/s")
q = np.unique(np.round(np.abs(np.diff(np.unique(d['rate_c']))), 6))
print(f"  coarse-rate quantum                      : {q[q>0][0] if (q>0).any() else 0:.4f} deg/s")

print("\n=== 2. ENGAGEMENT: FOUR PROXIES, SIDE BY SIDE ===")
eng = d["cs_eng"] > 0.5
lat = d["cc_lat"] > 0.5
sca = d["sca"] > 0.5
req = d["e4req"] > 0.5
for nm, x in (("carState.cruiseState.enabled", eng), ("carControl.latActive", lat),
              ("0x18F STEER_CONTROL_ACTIVE", sca), ("0xE4 STEER_TORQUE_REQUEST", req)):
    tr = int((np.diff(x.astype(int)) != 0).sum())
    print(f"  {nm:32s} {int(x.sum()):6d}/{n}  ({100*x.mean():6.2f}%)  transitions={tr}")

proxies = [("cruise", eng), ("latAct", lat), ("SCA", sca), ("E4req", req)]
print("\n  agreement matrix (% of frames where row == col):")
print("           " + "".join(f"{a:>9s}" for a, _ in proxies))
for na, xa in proxies:
    print(f"  {na:8s} " + "".join(f"{100*(xa==xb).mean():8.2f}%" for _, xb in proxies))

print("\n  cross-tab latActive x STEER_CONTROL_ACTIVE:")
for la in (0, 1):
    for s in (0, 1):
        print(f"    latActive={la} SCA={s}: {int(((lat==la)&(sca==s)).sum()):6d}")

print("\n=== 3. THE 0xE4 LKAS COMMAND (src 129 = TX on the steering bus) ===")
e4 = d["e4hist"]
tq, rq = e4[:, 1], e4[:, 2]
print(f"  frames {len(e4)}   STEER_TORQUE range {tq.min():.0f}..{tq.max():.0f}  rms {tq.std():.1f}")
print(f"  STEER_TORQUE_REQUEST=1 in {int(rq.sum())}/{len(e4)} ({100*rq.mean():.2f}%)")
print(f"  |torque|>0 & request=0 : {int(((rq==0)&(np.abs(tq)>0)).sum())}  (want ~0)")
print(f"  |torque|>0 & request=1 : {int(((rq==1)&(np.abs(tq)>0)).sum())}")
print(f"  byte2 hist: {dict(Counter(int(v) for v in e4[:,3]).most_common(8))}")
lv = np.abs(tq[rq == 1])
if len(lv):
    print(f"  |STEER_TORQUE| when requesting: mean {lv.mean():.1f} p50 {np.percentile(lv,50):.0f} "
          f"p95 {np.percentile(lv,95):.0f} max {lv.max():.0f}")
print(f"\n  on the 0x14A grid: mean |0xE4 torque| SCA=1 {np.abs(d['e4tq'][sca]).mean():.1f}   "
      f"SCA=0 {np.abs(d['e4tq'][~sca]).mean():.1f}")

print("\n=== 4. OPERATING POINT ===")
print(f"  vEgo   min {d['cs_v'].min():.3f} max {d['cs_v'].max():.3f} mean {d['cs_v'].mean():.3f} m/s")
print(f"  driver torque min {d['tq'].min():.0f} max {d['tq'].max():.0f} rms {d['tq'].std():.1f}  "
      f"|tq|>200 in {int((np.abs(d['tq'])>200).sum())} ({100*(np.abs(d['tq'])>200).mean():.1f}%)")
print(f"  {'vEgo bin':>16s} {'n':>6s} {'%':>6s} {'SCA%':>7s} {'|ang| mean':>11s} {'|tq| mean':>10s}")
for lo, hi in ((0, 0.05), (0.05, 0.5), (0.5, 1.5), (1.5, 3), (3, 6), (6, 100)):
    s = (d["cs_v"] >= lo) & (d["cs_v"] < hi)
    if not s.sum():
        continue
    print(f"  {f'{lo}-{hi}':>16s} {int(s.sum()):6d} {100*s.mean():5.1f}% {100*d['sca'][s].mean():6.1f}% "
          f"{np.abs(d['ang'][s]).mean():11.1f} {np.abs(d['tq'][s]).mean():10.1f}")
print(f"\n  {'|angle| bin':>16s} {'n':>6s} {'SCA%':>7s} {'v mean':>8s} {'|tq| mean':>10s}")
for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20), (20, 1e9)):
    s = (np.abs(d["ang"]) >= lo) & (np.abs(d["ang"]) < hi)
    if not s.sum():
        continue
    print(f"  {f'{lo}-{hi}':>16s} {int(s.sum()):6d} {100*d['sca'][s].mean():6.1f}% "
          f"{d['cs_v'][s].mean():8.2f} {np.abs(d['tq'][s]).mean():10.1f}")
