#!/usr/bin/env python3
r"""
DOES THE LKAS GAIN ACTUALLY REACH THE MOTOR -- AND IS THE RATCHET COMMAND-GATED?

Prompted by the operator, 2026-08-27: "I'm looking for a more structural limitation on the
steering angular velocity, one that does not scale with the 6x LKAS gain... it feels like the
max angular velocity has not scaled 6x."  He was right.

THE LADDER (read from the images; each route's build read from its cache `probe_build`):
    0xC6CD0 = 891 stock (1x) | 3564 (4x, V77-V100) | 5346 (6x, V102+) | 7128 (8x, V101)
Well-powered arm is 4x (8 routes) vs 6x (6 routes).  Stock and 8x are one route each.

TEST 1 -- GAIN DELIVERY.  Angular acceleration in the commanded direction is proportional to NET
TORQUE at the instant, before friction/damping set a steady state.  If the gain reaches the motor
it MUST scale.  Route-level p90, bootstrapped over routes (feedback-episodes-not-windows).

  🛑 THE HANDS-OFF MASK IS NOT OPTIONAL.  Without it this test returns "the gain scales NOWHERE"
     (0.948 [0.748,1.182]) -- because at low speed the wheel is moved mostly by the DRIVER and his
     torque swamps the LKAS contribution.  With D3 applied the low-command bins go to ~1.50 and
     only low-speed/high-command stays at ~1.0.  The uncorrected version supports a much stronger
     and WRONG claim.  D3 = rolling-median |cs_tq| over 0.5 s < 1200 (band-orthogonal; see
     rlog-tools/lib/v95_rez_lib.py for why the instantaneous `steeringPressed` flag is not usable).

TEST 2 -- IS THE RATCHET COMMAND-GATED?  Band power in the steering rate, NORMALISED by 1-3 Hz
power in the same window, so it is a SHAPE and not an amplitude.  Four control bands run alongside
6-9 Hz: a confound (harder steering, sharper corners) lifts every band; a real gate does not.

RESULT 2026-08-27
  T1: overall 1.429 [1.134,1.737] (ideal 1.500) -- the gain DOES reach the motor.
      <15 mph, cmd>=2048: 1.030 [0.694,1.499].   15-45 mph: 1.814 [1.276,2.521].
      ratio-of-ratios 0.557 [0.359,0.909], P(<1)=0.992.
  T2: at 1k-3k command the 6-9 Hz band rises 3.0x then 4.7x while 3-5 Hz and 10-13 Hz FALL to
      0.6-0.7x and 14-18 Hz is flat.  The ratchet is SWITCHED ON by command magnitude.

Usage:  python rlog-tools/studies/authority/gain_delivery_and_command_gate.py
"""
# --- PATH BOOTSTRAP ------------------------------------------------------------------
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _r = _os.path.dirname(_r)
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
for _root in _roots:
    for _p in [_root] + [_os.path.join(_root, d) for d in _os.listdir(_root)
                         if _os.path.isdir(_os.path.join(_root, d))]:
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
# -------------------------------------------------------------------------------------
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

REPO = _repo or _os.path.abspath(_os.path.join(_r, ".."))
CACHE = _os.path.join(REPO, "analysis-2020accord", "_scratch", "cache")
RNG = np.random.default_rng(20260827)
LADDER = {"4x": ["r77", "r78", "r79", "r7e", "r7f", "r81", "r82", "r85"],
          "6x": ["r96", "r9e", "ra4", "ra5", "ra6", "r1e"]}
IDEAL = 6.0 / 4.0
NEED = ["e4tq", "cc_lat", "cs_v", "t", "ang", "cs_tq"]


def _rollmed(x, w):
    n = len(x)
    out = np.full(n, np.nan)
    if n < w:
        return out
    m = np.median(sliding_window_view(np.abs(x), w), axis=1)
    out[w // 2:w // 2 + len(m)] = m
    return out


def prep(route):
    p = _os.path.join(CACHE, route, f"{route}.npz")
    if not _os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in NEED):
        return None
    a = {k: np.asarray(z[k]).astype(float) for k in NEED}
    n = min(len(v) for v in a.values())
    a = {k: v[:n] for k, v in a.items()}
    dt = float(np.median(np.diff(a["t"])))
    rate_raw = np.full(n, np.nan)
    rate_raw[1:] = np.diff(a["ang"]) / dt
    rate_raw = np.nan_to_num(rate_raw)
    # 🛑 The 9-point smooth is REQUIRED for the acceleration test (double differentiation of a
    # quantised angle) but must NOT be used for the 6-9 Hz spectral test -- it is a low-pass
    # sitting on the band being measured.  Keep both.
    rate = np.convolve(rate_raw, np.ones(9) / 9, mode="same")
    acc = np.full(n, np.nan)
    acc[1:] = np.diff(rate) / dt
    acc = np.convolve(np.nan_to_num(acc), np.ones(9) / 9, mode="same")
    w = max(3, int(round(0.5 / dt)) | 1)
    lag = int(round(0.5 / dt))
    prate = np.full(n, np.nan)                       # |rate| over the PRECEDING 0.5 s
    sm = np.convolve(np.nan_to_num(np.abs(rate)), np.ones(lag) / lag, mode="full")[:n]
    prate[lag:] = sm[:n - lag]
    return dict(cmd=np.abs(a["e4tq"]), dacc=-acc * np.sign(a["e4tq"]), rate=rate_raw,
                mph=a["cs_v"] * 2.23694, prate=prate, dt=dt, fs=1 / dt,
                eng=np.isfinite(a["e4tq"]) & (a["cc_lat"] > 0.5) & (_rollmed(a["cs_tq"], w) < 1200.0),
                lat=a["cc_lat"], v=a["cs_v"], e4=a["e4tq"])


D = {r: prep(r) for rs in LADDER.values() for r in rs}


def ratio(sel, cmin=2048, n=40000):
    """Route-level p90 acceleration, 6x arm over 4x arm, with a route bootstrap."""
    arms = {}
    for g, rs in LADDER.items():
        v = []
        for r in rs:
            d = D.get(r)
            if d is None:
                continue
            m = sel(d) & d["eng"] & (d["cmd"] >= cmin) & np.isfinite(d["dacc"])
            if m.sum() < 200:
                continue
            v.append(np.percentile(d["dacc"][m], 90))
        arms[g] = np.array(v)
    A, B = arms.get("4x", []), arms.get("6x", [])
    if len(A) < 3 or len(B) < 3:
        return None
    draws = np.array([np.mean(RNG.choice(B, len(B))) / np.mean(RNG.choice(A, len(A)))
                      for _ in range(n)])
    return B.mean() / A.mean(), np.percentile(draws, 2.5), np.percentile(draws, 97.5), \
        len(A), len(B), draws


def test1():
    print("=" * 92)
    print(f"TEST 1 -- DOES THE GAIN REACH THE MOTOR?   ideal = {IDEAL:.3f}")
    print("=" * 92)
    res = {}
    for lo, hi, cmin, lab in [(0, 99, 3000, "ALL speeds, cmd>=3000"),
                              (0, 15, 2048, "<15 mph,    cmd>=2048"),
                              (15, 45, 2048, "15-45 mph,  cmd>=2048"),
                              (0, 10, 2048, "<10 mph,    cmd>=2048"),
                              (20, 45, 2048, "20-45 mph,  cmd>=2048")]:
        r = ratio(lambda d, lo=lo, hi=hi: (d["mph"] >= lo) & (d["mph"] < hi), cmin)
        if not r:
            print(f"  {lab:24s}  (thin)")
            continue
        res[lab] = r
        flag = "  <-- 1.500 EXCLUDED" if (r[1] > IDEAL or r[2] < IDEAL) else ""
        print(f"  {lab:24s} {r[0]:6.3f} [{r[1]:5.3f}, {r[2]:5.3f}]   {r[3]}/{r[4]}{flag}")
    a, b = "<10 mph,    cmd>=2048", "20-45 mph,  cmd>=2048"
    if a in res and b in res:
        d = res[a][5] / res[b][5]
        print(f"\n  RATIO-OF-RATIOS  (low speed)/(higher speed) = {res[a][0]/res[b][0]:.3f} "
              f"[{np.percentile(d,2.5):.3f}, {np.percentile(d,97.5):.3f}]  P(<1)={np.mean(d<1):.3f}")


def test2(vmax=20.0):
    print("\n" + "=" * 92)
    print("TEST 2 -- IS THE RATCHET COMMAND-GATED?  (band SHAPE, normalised by 1-3 Hz)")
    print("=" * 92)
    bands = [(3, 5, "3-5 ctl"), (6, 9, "6-9 RATCHET"), (10, 13, "10-13 ctl"),
             (14, 18, "14-18 ctl"), (20, 26, "20-26 grind")]
    cells = {}
    for r, d in D.items():
        if d is None:
            continue
        n = len(d["rate"])
        W = int(round(2.56 / d["dt"]))
        ok = d["eng"] & np.isfinite(d["v"])
        for s in range(0, n - W, W // 2):
            sl = slice(s, s + W)
            if not ok[sl].all():
                continue
            v = np.nanmean(d["v"][sl]) * 2.23694
            c = np.nanmean(d["cmd"][sl])
            if not np.isfinite(v) or not np.isfinite(c) or v >= vmax:
                continue
            x = d["rate"][sl] - np.mean(d["rate"][sl])
            X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
            f = np.fft.rfftfreq(len(x), d["dt"])
            low = float(np.sum(X[(f >= 1) & (f < 3)]))
            if low <= 0:
                continue
            cb = "<1k" if c < 1024 else ("1k-2k" if c < 2048 else ("2k-3k" if c < 3072 else "3k+"))
            e = cells.setdefault(cb, {})
            for lo, hi, lab in bands:
                e.setdefault(lab, []).append(float(np.sum(X[(f >= lo) & (f < hi)])) / low)
    print(f"  <{vmax:.0f} mph, engaged, hands-off.  median band/low ratio:")
    print("  %-8s %6s  " % ("|cmd|", "n") + " ".join("%12s" % l for _, _, l in bands))
    base = {}
    for cb in ["<1k", "1k-2k", "2k-3k", "3k+"]:
        e = cells.get(cb)
        if not e:
            continue
        med = {l: float(np.median(e[l])) for _, _, l in bands}
        if cb == "<1k":
            base = med
        print("  %-8s %6d  " % (cb, len(e["6-9 RATCHET"]))
              + " ".join("%12.3f" % med[l] for _, _, l in bands))
    if base:
        print("\n  FOLD-RISE vs the <1k baseline -- THE CONTROL THAT MATTERS:")
        print("  %-8s  " % "|cmd|" + " ".join("%12s" % l for _, _, l in bands))
        for cb in ["1k-2k", "2k-3k", "3k+"]:
            e = cells.get(cb)
            if not e:
                continue
            print("  %-8s  " % cb
                  + " ".join("%11.1fx" % (np.median(e[l]) / base[l]) for _, _, l in bands))


if __name__ == "__main__":
    test1()
    test2()
