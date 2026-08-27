#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_timeline.py -- locate and characterise the V75 hard fault on route 5e.

Reads `_scratch/cache/r5e/r5e.npz` (written by `studies/sessions/v74_v75/v75fault_extract.py`). Everything here is Python + numpy;
no Ghidra, no firmware bytes.

Anchors, independently:
  A. raw CAN 0x18F (399) STEER_STATUS  -- the kit's canonical cut anchor
  B. 0x18F STEER_CONTROL_ACTIVE (byte4 bit3)
  C. openpilot onroadEvents (steerTempUnavailable / steerUnavailable / ...)
  D. carControl.latActive going false and STAYING false
  E. the last sample at which assist ever returns
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
C = ROOT / "_scratch/cache/r5e"
D = dict(np.load(C / "r5e.npz", allow_pickle=False))
EV = json.loads((C / "r5e_events.json").read_text())
CEN = json.loads((C / "r5e_census.json").read_text())

t = D["t"]
n = len(t)


def runs(mask, tt):
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    s = np.r_[idx[0], idx[brk + 1]]
    e = np.r_[idx[brk], idx[-1]]
    return [(float(tt[a]), float(tt[b]), int(a), int(b)) for a, b in zip(s, e)]


print("=" * 100)
print("ROUTE 5E OVERVIEW -- V75 flight")
print("=" * 100)
print(f"samples {n}   t 0..{t[-1]:.2f} s   segments {int(D['seg'].max()) + 1}")
sb = D["seg_bounds"]
print("segment starts (route-relative s): " +
      " ".join(f"s{int(a)}={b:.1f}" for a, b in sb))
print(f"vEgo {D['cs_v'].min():.2f}..{D['cs_v'].max():.2f} m/s   "
      f"engaged(latActive) {100 * (D['cc_lat'] > 0.5).mean():.1f}%")

# ---------------------------------------------------------------- A. STEER_STATUS
st = D["sstat"]
vals, cnt = np.unique(st, return_counts=True)
print("\nSTEER_STATUS (0x18F byte4 7:4) census: " +
      "  ".join(f"{int(v)}:{int(c)}" for v, c in zip(vals, cnt)))
for v in vals:
    r = runs(st == v, t)
    tot = sum(b - a for a, b, _, _ in r)
    print(f"   ST=={int(v)}: {len(r)} runs, {tot:.2f} s, first {r[0][0]:.2f}s "
          f"last {r[-1][1]:.2f}s, longest {max(b - a for a, b, _, _ in r):.2f}s")

# ---------------------------------------------------------------- B. STEER_CONTROL_ACTIVE
sca = D["sca"]
rs = runs(sca == 1, t)
print(f"\nSTEER_CONTROL_ACTIVE: {int((sca == 1).sum())} samples, {len(rs)} runs, "
      f"last set at t={rs[-1][1]:.3f}s" if rs else "\nSTEER_CONTROL_ACTIVE never set")

# ---------------------------------------------------------------- D. latActive
lat = D["cc_lat"] > 0.5
rl = runs(lat, t)
print(f"\nlatActive: {len(rl)} runs, total {sum(b - a for a, b, _, _ in rl):.1f} s")
for a, b, _, _ in rl:
    print(f"   {a:8.2f} .. {b:8.2f}  ({b - a:6.2f} s)")

# ---------------------------------------------------------------- C. onroadEvents
print("\nonroadEvents -- first/last occurrence and count")
names = {}
for e in EV:
    names.setdefault(e["name"], []).append(e["t"])
for k in sorted(names, key=lambda k: names[k][0]):
    v = names[k]
    print(f"   {k:34s} n={len(v):5d}  first {v[0]:8.2f}  last {v[-1]:8.2f}")

STEER_EV = [k for k in names if "steer" in k.lower() or "Steer" in k]
print("\n  steering-related events, every occurrence run:")
for k in STEER_EV:
    v = np.array(names[k])
    grp = [[v[0], v[0]]]
    for x in v[1:]:
        if x - grp[-1][1] <= 0.5:
            grp[-1][1] = x
        else:
            grp.append([x, x])
    print(f"   {k}: {len(grp)} bursts -> " +
          "  ".join(f"[{a:.2f},{b:.2f}]" for a, b in grp[:20]))

# ---------------------------------------------------------------- the fault instant
print("\n" + "=" * 100)
print("THE FAULT INSTANT")
print("=" * 100)
# last time assist was live on the bus
last_sca = rs[-1][1] if rs else np.nan
last_lat = rl[-1][1] if rl else np.nan
# STEER_STATUS: find the first index after which it never returns to the 'ok' value
ok_val = int(vals[np.argmax(cnt)])
bad = st != ok_val
last_ok = float(t[np.flatnonzero(~bad)[-1]]) if (~bad).any() else np.nan
# first index of the terminal bad run
if bad.any():
    rb = runs(bad, t)
    term = rb[-1]
    print(f"terminal STEER_STATUS != {ok_val} run: {term[0]:.3f} .. {term[1]:.3f} s "
          f"({term[1] - term[0]:.2f} s, to end of route)  value(s) "
          f"{sorted(set(int(x) for x in st[term[2]:term[3] + 1]))}")
print(f"last STEER_CONTROL_ACTIVE=1 : t={last_sca:.3f} s")
print(f"last latActive=True         : t={last_lat:.3f} s")
print(f"last STEER_STATUS=={ok_val}     : t={last_ok:.3f} s")

# ---------------------------------------------------------------- E. does the bus stay alive
print("\n" + "=" * 100)
print("POST-FAULT LIVENESS -- does the EPS keep transmitting, does the probe keep updating")
print("=" * 100)
keys = [str(k) for k in D["live_keys"]]
mat = D["live_mat"]
sec0 = float(D["live_sec0"][0])
for i, k in enumerate(keys):
    row = mat[i]
    nz = np.flatnonzero(row)
    if not len(nz):
        continue
    print(f"   {k:9s} n={row.sum():7d}  alive {sec0 + nz[0]:7.1f}..{sec0 + nz[-1]:7.1f} s  "
          f"gaps>2s: {int((np.diff(nz) > 2).sum())}")
