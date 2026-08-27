#!/usr/bin/env python3
r"""PRE-FLIGHT: would Lever B's r24 lane sit SATURATED at 8x?  (the V80 relay hazard)

THE ARITHMETIC, from the golden model, NOT from the brief:
  model/eps_chain_lanes.py:123  "FUN_0007f3f8 calls FUN_0007e74a ... 2*(current-delayed)/wrapped_sample_delta,
                           with delay cal tp+0x7c42=4"
  model/eps_chain_control.py:880 "gp-0x4f62 is a 4-SAMPLE FINITE DIFFERENCE at 1 kHz (2*(x[n]-x[n-4])/4 ...)"
  => d = 2*(x[n] - x[n-4]) / 4 = (x[n] - x[n-4]) / 2
  🛑 THE DIVISOR IS THE SAMPLE DELTA (4), NOT dt IN SECONDS.  `d` is in TORQUE COUNTS, not counts/s.
     The brief's "/ dt" reading would inflate every value by 1000x and invert the answer.
  => the lane saturates at |d| >= 8192*1024/5244 = 1599  <=>  |x[n]-x[n-4]| >= 3198 counts in 4 ms.

🛑 THE KIT HAS ALREADY MEASURED THIS ONCE, at 4x.  model/eps_chain_control.py:905, the V67 design note:
     "5120*5244 = 26.8M = 1.25% of INT32_MAX; lane saturates at |dtorque| >= 1599 vs a MEASURED
      123-839."
   So at 4x the peak sat at 839/1599 = 52 % of the saturation threshold.

🛑 WHY A DIRECT BUS RECONSTRUCTION CANNOT GIVE AN ABSOLUTE DUTY.
   The firmware differences its own ADC stream at 1 kHz over 4 ms.  The bus (0x18F) arrives at
   ~100 Hz -- ONE SAMPLE PER 10 ms, LONGER THAN THE WHOLE DIFFERENCE WINDOW.  Everything above 50 Hz
   is invisible, and a differentiator's gain RISES with frequency (the golden model measures 1.93x
   at 41.6 Hz vs 20.9 Hz), so the missing band is exactly the band that drives |d| toward its clamp.
   ⇒ ANY bus-derived |d| is a STRICT LOWER BOUND, and the shortfall is large and unknown.
   ⇒ This file reports (a) the LOWER BOUND, (b) the V101/V100 RATIO -- which is trustworthy because
      the same operator, the same channel and the same bandwidth deficit apply to both arms -- and
      (c) a THRESHOLD SWEEP so the builder can read a duty at any threshold once the scale is pinned.

The surrogate applies the firmware's OWN transfer function H(f) = 0.5*(1 - exp(-j*2*pi*f*0.004))
in the frequency domain to the band the bus can actually see.  That is the exact operator, evaluated
over a truncated band -- not a different operator.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DELAY_S = 0.004                 # 4 samples at 1 kHz
IN_CLAMP = 5120                 # aggregator input clamp on gp-0x4f62
DEADZONE = 3                    # cal 0xC61F6
LANE_CLAMP = 8192               # +-0x2000
ARM = 5244                      # cal 0xC6446 with Lever B armed
SAT = LANE_CLAMP * 1024.0 / ARM  # 1599.7
LIGHT = 400.0
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def dtorque(x, fs=L.FS):
    """The firmware's own operator d = (x[n]-x[n-4])/2 at 1 kHz, applied over the visible band."""
    n = len(x)
    r = np.arange(n, dtype=float)
    c = np.polyfit(r, x, 1)
    y = x - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    H = 0.5 * (1.0 - np.exp(-2j * np.pi * f * DELAY_S))
    return np.fft.irfft(X * H, n=n)


BL = {}
for route in ("85", "95"):
    out = []
    for b in L.all_blocks(route):
        d = dtorque(b["tq"])
        d = np.clip(d, -IN_CLAMP, IN_CLAMP)
        d = np.where(np.abs(d) < DEADZONE, 0.0, d)
        b["dtq"] = np.abs(d)
        b["r24"] = np.clip((np.abs(d) * ARM) / 1024.0, 0, LANE_CLAMP)
        out.append(b)
    BL[route] = out
    print("   r%s %s: %d blocks" % (route, L.ROUTES[route]["build"], len(out)))

print("""
   Operator: d = (x[n]-x[n-4])/2 at 1 kHz, delay cal tp+0x7c42 = 4.
   Input clamp +-%d, deadzone %d (cal 0xC61F6), lane clamp +-%d, arm 0xC6446 = %d.
   SATURATION THRESHOLD |d| >= %.1f counts.""" % (IN_CLAMP, DEADZONE, LANE_CLAMP, ARM, SAT))


def frames(route, vlo=0, vhi=1e9, light=None, rlo=None, rhi=None):
    D, U, V, R, T = [], [], [], [], []
    for i, b in enumerate(BL[route]):
        eng = b["cc_lat"] > 0.5
        v = b["v_rear"] * 3.6
        m = eng & (v >= vlo) & (v < vhi)
        if light is True:
            m &= np.abs(b["cs_tq"]) < LIGHT
        if light is False:
            m &= np.abs(b["cs_tq"]) >= LIGHT
        if rlo is not None:
            ar = np.abs(b["rate_c"])
            m &= (ar >= rlo) & (ar < rhi)
        if m.sum() < 5:
            continue
        D.append(b["dtq"][m])
        U.append(i * 1e6 + np.floor(b["t"][m] / 15.0))
        V.append(v[m])
    if not D:
        return np.array([]), np.array([])
    return np.concatenate(D), np.concatenate(U)


def bootq(a, ua, b, ub, q, nboot=3000, seed=5):
    rng = np.random.default_rng(seed)
    if len(a) < 30 or len(b) < 30:
        return None
    Ua, Ub = np.unique(ua), np.unique(ub)
    ia = {u: np.nonzero(ua == u)[0] for u in Ua}
    ib = {u: np.nonzero(ub == u)[0] for u in Ub}
    pt = np.percentile(b, q) / max(np.percentile(a, q), 1e-9)
    out = []
    for _ in range(nboot):
        sa = np.concatenate([ia[Ua[j]] for j in rng.integers(0, len(Ua), len(Ua))])
        sb = np.concatenate([ib[Ub[j]] for j in rng.integers(0, len(Ub), len(Ub))])
        out.append(np.percentile(b[sb], q) / max(np.percentile(a[sa], q), 1e-9))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=float(pt), lo=float(lo), hi=float(hi))


def bootduty(x, u, thr, nboot=3000, seed=9):
    rng = np.random.default_rng(seed)
    U = np.unique(u)
    idx = {k: np.nonzero(u == k)[0] for k in U}
    pt = float((x >= thr).mean())
    out = [float((x[np.concatenate([idx[U[j]] for j in rng.integers(0, len(U), len(U))])] >= thr).mean())
           for _ in range(nboot)]
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(d=pt, lo=float(lo), hi=float(hi), blocks=len(U))


# =====================================================================================================
hdr("1 -- THE |d| DISTRIBUTION, engaged, both routes  (LOWER BOUND: the bus cannot see >50 Hz)")
print("   %-24s %8s %8s %8s %8s %8s %8s   %8s" %
      ("selection", "p50", "p75", "p90", "p95", "p99", "max", "max/5120"))
for lab, kw in (("all engaged", {}),
                ("engaged 5-20 km/h", dict(vlo=5, vhi=20)),
                ("engaged 20-35", dict(vlo=20, vhi=35)),
                ("engaged 35-65", dict(vlo=35, vhi=65)),
                ("engaged HANDS-LIGHT", dict(light=True)),
                ("engaged hands-on", dict(light=False))):
    for route in ("85", "95"):
        x, _u = frames(route, **kw)
        if len(x) < 30:
            continue
        print("   %-16s r%s %-4s %8.1f %8.1f %8.1f %8.1f %8.1f %8.1f   %7.3f"
              % (lab, route, L.ROUTES[route]["build"][1:],
                 *np.percentile(x, [50, 75, 90, 95, 99, 100]), x.max() / IN_CLAMP))

# =====================================================================================================
hdr("2 -- 🛑 THE HEADLINE: saturation duty d(|d| >= %.0f) with block-bootstrap CI" % SAT)
for lab, kw in (("all engaged", {}), ("HANDS-LIGHT", dict(light=True)), ("hands-on", dict(light=False)),
                ("5-20 km/h", dict(vlo=5, vhi=20)), ("20-35 km/h", dict(vlo=20, vhi=35)),
                ("35-65 km/h", dict(vlo=35, vhi=65))):
    row = []
    for route in ("85", "95"):
        x, u = frames(route, **kw)
        if len(x) < 30:
            row.append("%-30s" % "  (thin)")
            continue
        r = bootduty(x, u, SAT)
        row.append("r%s %s: %.5f [%.5f,%.5f] n=%d" % (route, L.ROUTES[route]["build"][1:],
                                                      r["d"], r["lo"], r["hi"], len(x)))
    print("   %-14s  %s" % (lab, "   ".join(row)))

# =====================================================================================================
hdr("3 -- THE THRESHOLD SWEEP.  Duty vs threshold, so any scale correction can be applied later.")
print("   threshold is |d|; the arm that puts SATURATION there is 8192*1024/threshold")
print("   %8s %10s %14s %14s %10s" % ("|d| thr", "implied arm", "V100 r85 duty", "V101 r95 duty", "ratio"))
x85, u85 = frames("85")
x95, u95 = frames("95")
for thr in (25, 50, 100, 200, 400, 800, 1600):
    d85 = float((x85 >= thr).mean())
    d95 = float((x95 >= thr).mean())
    print("   %8d %10.0f %14.5f %14.5f %10s"
          % (thr, LANE_CLAMP * 1024.0 / thr, d85, d95,
             "%.2f" % (d95 / d85) if d85 > 0 else "-"))

# =====================================================================================================
hdr("4 -- r, THE RATIO OF |d| BETWEEN 8x AND 4x -- the scale-free number the arm should be sized on")
print("   Matched (speed x wheel-rate) cells, 15 s blocks.  If the 8x multiplies |d| by r, the arm")
print("   that preserves V88-V100's saturation duty is 5244 / r.")
pack = []
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a, ua = frames("85", vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b, ub = frames("95", vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        if len(a) > 200 and len(b) > 200:
            pack.append(((vlo, vhi), (rlo, rhi), a, ua, b, ub))
print("\n   cells used: %d" % len(pack))
print("   %-11s %-11s %8s %8s   %s" % ("speed", "rate", "nA", "nB", "r at p50 / p90 / p99 / p99.9"))
logs = {q: [] for q in (50, 90, 99, 99.9)}
for (vlo, vhi), (rlo, rhi), a, ua, b, ub in pack:
    cells = []
    for q in (50, 90, 99, 99.9):
        rr = np.percentile(b, q) / max(np.percentile(a, q), 1e-9)
        logs[q].append((np.log(rr), min(len(a), len(b))))
        cells.append("%5.2f" % rr)
    print("   %-11s %-11s %8d %8d   %s" % ("%d-%d km/h" % (vlo, vhi), "%d-%d d/s" % (rlo, rhi),
                                           len(a), len(b), " / ".join(cells)))
print()
for q in (50, 90, 99, 99.9):
    w = np.array([x[1] for x in logs[q]], float)
    v = np.array([x[0] for x in logs[q]], float)
    r = float(np.exp(np.sum(v * w) / w.sum()))
    print("   pooled r at p%-5s = %5.2f   =>  arm that preserves the 4x duty = 5244 / r = %6.0f"
          % (q, r, ARM / r))
allq = bootq(x85, u85, x95, u95, 99, seed=21)
allq9 = bootq(x85, u85, x95, u95, 99.9, seed=23)
print("\n   unstratified (exposure-confounded, for reference): r p99 = %.2f [%.2f, %.2f], "
      "p99.9 = %.2f [%.2f, %.2f]"
      % (allq["r"], allq["lo"], allq["hi"], allq9["r"], allq9["lo"], allq9["hi"]))

print("\n[done]")
