#!/usr/bin/env python3
"""RING-DOWN, gear check, and consolidation of the V86 ~8 Hz damping re-score.

RING-DOWN is the cleanest physical measurement of damping there is: open the loop (latActive
falls) with the line running and watch the envelope decay -- a direct zeta, independent of every
spectral estimator and of the window length.  The question this section answers is whether the
three flown routes can supply it.

Consolidates qd_score / qd_power / qd_phase / qd_lines into _cache_r6f/q_damping_score.json.

Usage:  python qd_final.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                       # noqa: E402
import qd_win as W                                                       # noqa: E402

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + "\n" + s + "\n" + "=" * 112, flush=True)


# ============================================================================================
hdr("R0  GEAR CHECK -- reverse is 100% manual on both V86 routes, so it cannot touch this")
gear = {}
for b, r in W.ROUTES.items():
    d = W.load(r)
    fs = d["fs"]
    g = np.asarray(d["cs_gear"], float).astype(int)
    lat = np.asarray(d["cc_lat"], float) > 0.5
    rows = {}
    for gi in sorted(set(g.tolist())):
        m = g == gi
        rows[GEAR[gi] if gi < len(GEAR) else str(gi)] = dict(
            s=float(m.sum() / fs), eng_s=float((m & lat).sum() / fs))
    gear[b] = rows
    print(f"  {b:5s}  " + "   ".join(
        f"{k}: {v['s']:5.1f} s ({v['eng_s']:4.1f} s engaged)" for k, v in rows.items()))
OUT["gear"] = gear

# ============================================================================================
hdr("R1  RING-DOWN AVAILABILITY -- latActive falling edges with the line running")
EDGE_PRE, EDGE_POST = 3.0, 4.0
edges = {}
for b, r in W.ROUTES.items():
    d = W.load(r)
    fs = d["fs"]
    t = d["t"]
    x = np.asarray(d[W.SIG], float)
    v = np.asarray(d["cs_v"], float)
    lat = np.asarray(d["cc_lat"], float) > 0.5
    fe = np.flatnonzero(lat[:-1] & ~lat[1:])
    npre, npost = int(EDGE_PRE * fs), int(EDGE_POST * fs)
    keep = []
    for i in fe:
        if i - npre < 0 or i + npost >= len(t):
            continue
        if not lat[i - npre:i + 1].all() or lat[i + 1:i + 1 + npost].any():
            continue
        keep.append(int(i))
    print(f"  {b:5s}  raw falling edges {len(fe):3d}   usable (>= {EDGE_PRE:.0f} s engaged before, "
          f">= {EDGE_POST:.0f} s manual after): {len(keep)}")
    rows = []
    for i in keep:
        # the line's own frequency from the 8 s before the edge
        pre = x[max(i - int(8 * fs), 0):i]
        f0 = Q.linewidth(pre, fs)["f0"] if len(pre) > 64 else 7.79
        f0 = f0 if np.isfinite(f0) else 7.79
        bp = butter(2, [max(f0 - 1.5, 0.5), f0 + 1.5], btype="band", fs=fs)
        seg = x[i - npre:i + npost]
        env = np.abs(hilbert(filtfilt(*bp, seg)))
        pre_env = float(np.percentile(env[:npre], 75))
        post = env[npre:]
        # decay: fit log-envelope over the first 2 s after the edge, floor-subtracted in POWER
        floor = float(np.percentile(env[npre + int(2.5 * fs):], 25)) if len(post) > int(3 * fs) \
            else float(np.percentile(post, 10))
        tt = np.arange(len(post)) / fs
        m = tt <= 2.0
        y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
        if np.count_nonzero(y > 1.5 * 1e-4) < 20 or pre_env <= 1.2 * floor:
            rows.append(dict(t=float(t[i]), v=float(v[i]), f0=float(f0), pre_env=pre_env,
                             floor=floor, usable=False))
            continue
        c = np.polyfit(tt[m], np.log(y), 1)
        lam = -float(c[0])                     # envelope decay rate, 1/s
        zeta = lam / (2 * np.pi * f0)
        rows.append(dict(t=float(t[i]), v=float(v[i]), f0=float(f0), pre_env=pre_env,
                         floor=floor, lam=lam, zeta=float(zeta),
                         q_ring=float(1 / (2 * zeta)) if zeta > 0 else np.inf, usable=True))
        print(f"       edge t={t[i]:7.1f} s  v={v[i]:.2f} m/s  f0={f0:5.2f} Hz  "
              f"pre-env {pre_env:7.1f} ct (floor {floor:6.1f})  lambda={lam:6.3f} /s  "
              f"zeta={zeta:.4f}  Q_ring={1/(2*zeta) if zeta > 0 else np.inf:7.1f}")
    edges[b] = rows
OUT["ringdown"] = edges
nu = {b: sum(1 for r in v if r.get("usable")) for b, v in edges.items()}
print(f"\n  usable ring-downs:  " + "   ".join(f"{b} {nu[b]}" for b in W.ROUTES))
print("  => V86 flew ONE unbroken 139.6 s engagement and never disengaged inside a segment with"
      "\n     the line running.  The single-variable pair V86/V86B therefore has NO ring-down arm:"
      "\n     the cleanest damping measurement available is structurally absent from the V86 route.")

# ============================================================================================
hdr("R2  WHAT PROTOCOL WOULD SETTLE IT")
F0 = 7.79
print("  (a) LINEWIDTH.  To leave the resolution floor the window must satisfy")
print("        T >= 2 x 1.4416 x Q / f0        [FWHM twice the Hann main lobe]")
for q in (100, 200, 400, 600, 1000):
    print(f"        Q = {q:5d}  ->  T >= {2*1.4416*q/F0:7.1f} s of UNBROKEN engaged driving "
          f"per window")
print("      V86B's longest engagement was 36.4 s.  It could not resolve Q above ~100 even with"
      "\n      infinite repeats -- more windows do not buy resolution, only precision.")
print("\n  (b) HOW MANY.  The measured DiD CI at T=10.1 s (blk 13/6/11) is [0.548,1.966], i.e."
      "\n      SE(log) = 0.326.  Precision scales as 1/sqrt(n_blk):")
for tgt in (0.30, 0.20, 0.15, 0.10):
    fac = (0.326 / (tgt / 1.96)) ** 2
    print(f"        to reach a +-{tgt*100:2.0f}% DiD CI: {fac:5.1f}x the blocks  =>  "
          f"V86B needs {6*fac:5.0f} blk = {6*fac*10.13/60:5.1f} min engaged, speed-matched")
print("\n  (c) THE CHEAP ONE -- RING-DOWN.  A direct zeta needs only ~3 s of engagement with the")
print("      line running and ~4 s of manual after it.  30 deliberate engage/hold/disengage")
print("      cycles per arm is ~10 min of driving and yields 30 independent zeta estimates, versus")
print(f"      the {sum(nu.values())} usable edges the three flown routes contain between them.")
print("      This is the protocol change that converts the question from unanswerable to routine.")
OUT["protocol"] = dict(
    linewidth_T_for_Q={q: 2 * 1.4416 * q / F0 for q in (100, 200, 400, 600, 1000)},
    blocks_needed={f"{int(t*100)}pct": (0.326 / (t / 1.96)) ** 2 for t in (0.30, 0.20, 0.15, 0.10)},
    usable_ringdowns=nu)

# ============================================================================================
hdr("R3  CONSOLIDATION")
for name in ("q_damping_score", "qd_power", "qd_phase", "qd_lines"):
    p = ROOT / "_cache_r6f" / f"{name}.json"
    if p.exists():
        OUT[name] = json.load(open(p))
        print(f"  merged {p.name}")
json.dump(OUT, open(ROOT / "_cache_r6f" / "q_damping_score.json", "w"), indent=1, default=float)
print("\nwrote _cache_r6f/q_damping_score.json  (consolidated)")
