#!/usr/bin/env python3
"""v75fault_oscillation.py -- was the fault preceded by a high-frequency loop oscillation?

Quantifies HF content of the two EPS-side witnesses (0x18F STEER_TORQUE_SENSOR, 0x14A
STEER_ANGLE_RATE) in 200 ms windows across the whole route, ranks the pre-fault window, and
runs a periodogram over the last 0.5 s. Also checks the same metric on V74's route 5d.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
D = dict(np.load(ROOT / "_cache_r5e" / "r5e.npz"))
t = D["t"]
T_FAULT = 284.795
H = "=" * 100
pre = t < T_FAULT


def hf_metric(x):
    """Mean |2nd difference| -- a sampling-rate-independent proxy for energy near Nyquist."""
    x = np.asarray(x, float)
    if len(x) < 3:
        return np.nan
    return float(np.mean(np.abs(np.diff(x, 2))))


def windows(w=0.2, step=0.1, upto=None):
    hi = upto if upto is not None else t[-1]
    a = t[0]
    while a + w <= hi:
        yield a, a + w
        a += step


print(H)
print("HIGH-FREQUENCY OSCILLATION IN THE 0.5 s BEFORE THE FAULT")
print(H)
CH = {"drvTq (0x18F STEER_TORQUE_SENSOR)": D["tq"],
      "rate14 (0x14A STEER_ANGLE_RATE)": D["rate_c"],
      "rate18 (0x18F STEER_ANGLE_RATE)": D["rate_f"],
      "e4 cmd (openpilot)": D["e4tq"]}
res = {}
for name, x in CH.items():
    vals, mids = [], []
    for a, b in windows(upto=T_FAULT):
        m = (t >= a) & (t < b)
        if m.sum() < 10:
            continue
        vals.append(hf_metric(x[m]))
        mids.append((a + b) / 2)
    vals = np.array(vals); mids = np.array(mids)
    # the window ending exactly at the fault
    k = int(np.argmin(np.abs(mids - (T_FAULT - 0.1))))
    rank = int((vals > vals[k]).sum())
    res[name] = (vals, mids, k, rank)
    print(f"\n  {name}")
    print(f"    HF metric (mean |2nd diff|) in the 200 ms ending at the fault: {vals[k]:.1f}")
    print(f"    route-5e pre-fault distribution p50 {np.percentile(vals, 50):.1f}  "
          f"p95 {np.percentile(vals, 95):.1f}  p99 {np.percentile(vals, 99):.1f}  "
          f"max {vals.max():.1f}")
    print(f"    ⇒ RANK {rank + 1} of {len(vals)} windows  "
          f"(percentile {100 * (1 - rank / len(vals)):.3f})")
    top = np.argsort(vals)[::-1][:8]
    print("    top-8 windows: " + "  ".join(f"{mids[i]:.2f}s={vals[i]:.0f}" for i in top))

print("\n" + H)
print("PERIODOGRAM of the last 0.5 s (0x18F driver torque and 0x14A angle rate)")
print(H)
m = (t >= T_FAULT - 0.5) & (t < T_FAULT)
fs = 1.0 / np.median(np.diff(t[m]))
print(f"  n={int(m.sum())}  fs≈{fs:.2f} Hz (Nyquist {fs / 2:.1f} Hz)")
for name, x in (("drvTq", D["tq"]), ("rate14", D["rate_c"]), ("rate18", D["rate_f"])):
    y = x[m] - np.mean(x[m])
    y = y * np.hanning(len(y))
    P = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / fs)
    k = np.argsort(P[1:])[::-1][:5] + 1
    print(f"  {name:7s} p-p={x[m].max() - x[m].min():8.0f}  rms={np.std(x[m]):7.1f}  "
          f"top lines: " + "  ".join(f"{f[i]:.1f}Hz" for i in k))

print("\n" + H)
print("BUILD-UP -- the HF metric in successive 200 ms windows approaching the fault")
print(H)
x = D["tq"]
r = D["rate_c"]
print(f"  {'window':>18s} {'drvTq HF':>9s} {'rate14 HF':>10s} {'drvTq p-p':>10s} "
      f"{'|cmd| mean':>10s} {'lvlmax':>6s}")
for k in range(-25, 1):
    a, b = T_FAULT + k * 0.2, T_FAULT + (k + 1) * 0.2
    mm = (t >= a) & (t < min(b, T_FAULT))
    if mm.sum() < 5:
        continue
    print(f"  [{a - T_FAULT:+6.2f},{b - T_FAULT:+6.2f}] {hf_metric(x[mm]):9.1f} "
          f"{hf_metric(r[mm]):10.1f} {x[mm].max() - x[mm].min():10.0f} "
          f"{np.nanmean(np.abs(D['e4tq'][mm])):10.0f} {int(D['thermo'][mm].max()):6d}")

print("\n" + H)
print("V74 (route 5d) -- the same HF metric, for scale")
print(H)
C5D = ROOT / "_cache_r5d"
tq5d, t5d, lat5d, v5d = [], [], [], []
off = 0.0
for s in range(17):
    f = C5D / f"r5ds{s}.npz"
    if not f.exists():
        continue
    z = np.load(f)
    tq5d.append(z["tq"]); t5d.append(z["t"] + off); lat5d.append(z["cc_lat"] > 0.5)
    v5d.append(z["cs_v"])
    off += float(z["t"][-1]) + 0.01
tq5d = np.concatenate(tq5d); t5d = np.concatenate(t5d)
lat5d = np.concatenate(lat5d); v5d = np.concatenate(v5d)
vals5d = []
a = t5d[0]
while a + 0.2 <= t5d[-1]:
    m2 = (t5d >= a) & (t5d < a + 0.2)
    if m2.sum() >= 10:
        vals5d.append(hf_metric(tq5d[m2]))
    a += 0.1
vals5d = np.array(vals5d)
v5, _, k5, _ = res["drvTq (0x18F STEER_TORQUE_SENSOR)"]
print(f"  route 5d (V74, {len(vals5d)} windows): p50 {np.percentile(vals5d, 50):.1f}  "
      f"p95 {np.percentile(vals5d, 95):.1f}  p99 {np.percentile(vals5d, 99):.1f}  "
      f"max {vals5d.max():.1f}")
print(f"  route 5e (V75, {len(v5)} windows):    p50 {np.percentile(v5, 50):.1f}  "
      f"p95 {np.percentile(v5, 95):.1f}  p99 {np.percentile(v5, 99):.1f}  max {v5.max():.1f}")
print(f"  the pre-fault window = {v5[k5]:.1f} ⇒ exceeded by "
      f"{int((vals5d > v5[k5]).sum())} of {len(vals5d)} V74 windows "
      f"({100 * (vals5d > v5[k5]).mean():.3f}%)")
print("  🛑 route-level medians are NOT comparable (different routes, different exposure); this is "
      "a SCALE check only, not a build comparison.")

print("\n" + H)
print("POST-FAULT 0x14A SENTINEL -- which fields are invalidated")
print(H)
post = ~pre
for nm, key, scale in (("STEER_ANGLE (bytes 0:1)", "ang", -0.1),
                       ("STEER_ANGLE_RATE (bytes 2:3)", "rate_c", -1.0),
                       ("STEER_WHEEL_ANGLE (bytes 5:6)", "wang", -0.1)):
    u = np.unique(D[key][post])
    raw = u / scale
    print(f"  0x14A {nm:32s} post-fault: n_unique={len(u)}  "
          f"raw {'/'.join(f'0x{int(round(x)) & 0xFFFF:04X}' for x in raw[:3])}"
          f"{' ...' if len(u) > 3 else ''}")
    up = np.unique(D[key][pre])
    print(f"        {'':32s} pre-fault : n_unique={len(up)}  "
          f"range {D[key][pre].min():.1f}..{D[key][pre].max():.1f}")
print(f"  0x18F STEER_TORQUE_SENSOR post-fault: n_unique={len(np.unique(D['tq'][post]))}, "
      f"range {D['tq'][post].min():.0f}..{D['tq'][post].max():.0f} "
      f"⇒ the TORQUE sensor keeps reporting; only 0x14A's ANGLE fields are invalidated")
