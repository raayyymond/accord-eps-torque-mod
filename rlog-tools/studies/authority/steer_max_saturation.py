#!/usr/bin/env python3
r"""
IS THE LOW-SPEED STEERING-RATE LIMIT THE FIRMWARE, OR openpilot's STEER_MAX?

Answers the operator's goal #5 -- "at low speed the maximum steering angular velocity is
still limited" -- re-reported on V107 and again on V108.

Three tests, all pre-registered, all free from caches already on disk:

  T1  AUTHORITY RAMP.  gp-0x69b0's climb needs STEER_STATUS <= 2 (3/4/7 force the down-ramp).
      If STEER_STATUS flickers at low speed, the ramp is knocked down at 328/tick and recovers
      at 33/tick -- a 10:1 asymmetry that would hold average authority well below 1.0.
      NULL LICENSED: "STEER_STATUS stays 0 => the ramp holds at full scale => not the limit."
      + CONTROL: does sstat EVER move anywhere in the route?  A field that is always 0 is a
        dead decode, not a null.

  T2  COMMAND SATURATION.  Duty of |e4tq| >= 4096 while engaged, by speed.
      + CONTROL: is 4096 a real clamp?  A clamp shows a DELTA at the edge on a decaying tail.

  T3  IS THE CAR OR THE COMMAND THE LIMIT?  Achieved rate vs |command|.
      Still climbing at the rail  => openpilot ran out of command (lever = STEER_MAX).
      Flattened before the rail   => the car ran out of authority (lever = firmware).
      + CONTROL: what rate does the DRIVER achieve at the same speed?  That is the upper
        envelope of what the rack can do, and it is what excludes a plant limit.

Sign convention: +LKAS demands NEGATIVE steering angle (accord-steering-sign-convention-confirmed),
so rate-in-the-commanded-direction is -rate*sign(cmd).

Result 2026-08-27: T1 NULL (control passed), T2 railed 20-42 % at low speed, T3 still climbing
and the driver slews 3-4x faster => the limit is openpilot's STEER_MAX = 4096, and NO firmware
calibration can raise it.

Usage:  python rlog-tools/studies/authority/steer_max_saturation.py [route ...]
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

REPO = _repo or _os.path.abspath(_os.path.join(_r, ".."))
CACHE = _os.path.join(REPO, "analysis-2020accord", "_scratch", "cache")
STEER_MAX = 4096.0
BANDS = [(0, 6, "<6 mph"), (6, 10, "6-10"), (10, 15, "10-15"), (15, 20, "15-20"),
         (20, 30, "20-30"), (30, 45, "30-45"), (45, 999, "45+")]


def load(route):
    p = _os.path.join(CACHE, route, f"{route}.npz")
    if not _os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    need = ["e4tq", "cc_lat", "cs_v", "t", "ang", "sstat"]
    if any(k not in z.files for k in need):
        return None
    a = {k: np.asarray(z[k]).astype(float) for k in need}
    n = min(len(v) for v in a.values())
    a = {k: v[:n] for k, v in a.items()}
    a["mph"] = a["cs_v"] * 2.23694
    a["dt"] = float(np.median(np.diff(a["t"]))) if n > 1 else 0.01
    rate = np.full(n, np.nan)
    rate[1:] = np.diff(a["ang"]) / a["dt"]
    a["rate"] = np.convolve(np.nan_to_num(rate), np.ones(5) / 5, mode="same")
    a["rate_raw"] = rate
    a["eng"] = np.isfinite(a["e4tq"]) & np.isfinite(a["mph"]) & (a["cc_lat"] > 0.5)
    return a


def t1_ramp(route, a):
    """STEER_STATUS never leaves {0,1,2} => the authority ramp is never knocked down."""
    ss, eng, dt = a["sstat"], a["eng"], a["dt"]
    vals, cnt = np.unique(ss[np.isfinite(ss)], return_counts=True)
    print(f"  T1 sstat over the WHOLE route: { {int(k): int(c) for k, c in zip(vals, cnt)} }")
    if len(vals) == 1:
        print("     CONTROL FAILS on this route alone -- sstat never moves. Pool with others.")
    else:
        for v in vals:
            if v == 0:
                continue
            m = (ss == v) & np.isfinite(a["mph"])
            print(f"     status {int(v)}: {int(m.sum())} frames, speed p50 "
                  f"{np.nanpercentile(a['mph'][m], 50):.1f} mph, engaged-duty "
                  f"{np.nanmean(a['cc_lat'][m] > 0.5):.3f}")
    bad = ss[eng] > 2
    tr = int(np.sum(np.diff(bad.astype(int)) != 0))
    print(f"     ENGAGED: duty(sstat>2) = {bad.mean():.6f} over {eng.sum() * dt:.0f} s, "
          f"{tr} transitions")


def t2_saturation(route, a):
    e, eng, dt = np.abs(a["e4tq"]), a["eng"], a["dt"]
    over = int(np.sum(e > STEER_MAX))
    print(f"  T2 max|e4tq| = {np.nanmax(e[eng]):.1f}   frames > {STEER_MAX:.0f}: {over}")
    m = eng & (e > 3500)
    if m.sum() > 50:
        edges = [3500, 3700, 3900, 4000, 4050, 4080, 4090, 4095, 4095.5, 4096.5]
        h, _ = np.histogram(e[m], bins=edges)
        print("     clamp control (a DELTA at the edge on a decaying tail):",
              " ".join(f"{int(x)}" for x in h))
    print("     %-10s %8s %10s" % ("band", "sec", "duty@rail"))
    for lo, hi, lab in BANDS:
        mm = eng & (a["mph"] >= lo) & (a["mph"] < hi)
        if mm.sum() < 50:
            continue
        print("     %-10s %8.1f %10.4f" % (lab, mm.sum() * dt, np.mean(e[mm] >= STEER_MAX)))


def t3_rate_vs_command(route, a, vmax=15.0):
    e, dt = a["e4tq"], a["dt"]
    dirr = -a["rate"] * np.sign(e)          # rate in the COMMANDED direction
    base = np.isfinite(e) & np.isfinite(a["mph"]) & np.isfinite(a["rate_raw"]) & (a["mph"] < vmax)
    eng, man = base & (a["cc_lat"] > 0.5), base & (a["cc_lat"] < 0.5)
    if eng.sum() < 300:
        print("  T3 thin engaged exposure -- skipped")
        return
    print(f"  T3 <{vmax:.0f} mph   engaged {eng.sum()*dt:.0f} s / manual {man.sum()*dt:.0f} s")
    print("     %-14s %7s %8s %8s %8s" % ("|cmd| bin", "sec", "p50", "p90", "max"))
    bins = [(0, 256), (256, 512), (512, 1024), (1024, 2048), (2048, 3072),
            (3072, 3686), (3686, 4095), (4095, 1e9)]
    for lo, hi in bins:
        m = eng & (np.abs(e) >= lo) & (np.abs(e) < hi)
        lab = "== RAIL" if lo == 4095 else f"{lo}-{hi}"
        if m.sum() < 30:
            print("     %-14s %7.1f    (thin)" % (lab, m.sum() * dt))
            continue
        r = dirr[m]
        print("     %-14s %7.1f %8.1f %8.1f %8.1f" % (
            lab, m.sum() * dt, np.nanpercentile(r, 50), np.nanpercentile(r, 90), np.nanmax(r)))
    if man.sum() > 300:
        r = np.abs(a["rate"][man])
        r = r[np.isfinite(r)]
        print("     %-14s %7.1f %8.1f %8.1f %8.1f   <== DRIVER |rate|, same speed" % (
            "MANUAL ctrl", man.sum() * dt, np.nanpercentile(r, 50),
            np.nanpercentile(r, 90), np.nanmax(r)))


def main(routes):
    for route in routes:
        a = load(route)
        if a is None:
            print(f"\n===== {route}: absent or missing fields =====")
            continue
        print(f"\n===== {route}   engaged {a['eng'].sum()*a['dt']:.0f} s   "
              f"dt {a['dt']*1000:.1f} ms =====")
        t1_ramp(route, a)
        t2_saturation(route, a)
        t3_rate_vs_command(route, a)


if __name__ == "__main__":
    main(_sys.argv[1:] or ["r77", "ra6", "r1e", "r1b"])
