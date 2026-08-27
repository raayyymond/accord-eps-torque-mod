#!/usr/bin/env python3
"""IMU DOSE-RESPONSE over Kd = 0 / 1x / 2x -- a sensor that shares no signal path with the lever.

Every other result in this workstream comes off the EPS's own CAN channels, so it could in
principle be an artifact of EPS signal processing or of the torsion-bar decode. The comma device's
LSM6DS3TR-C is a different sensor, a different bus and a different ECU. If the 40-49 Hz burst is
real whole-car vibration created by V62's doubled derivative lane, it is visible here too, and it
must show the same dose ordering.

  POSITIVE CONTROL, MANDATORY. If the ~20.9 Hz grind #1 mode is NOT visible on the IMU, an IMU null
  in the high band means nothing -- it would only mean the IMU cannot see steering modes at all.
  The control must pass before the test result is read.

🛑 The accelerometer samples at 98.4-100.2 Hz, i.e. essentially the CAN rate. Its Nyquist is ~49.6
Hz, so the orchestrator's requested 25-70 Hz band is NOT AVAILABLE -- anything above ~49 Hz folds.
Bands are therefore matched to the CAN analysis (18-22, 24-28, 30-40, 40-49) and the IMU inherits
the identical alias ambiguity. The IMU establishes REALITY and DOSE, not FREQUENCY.

Usage:  python studies/grind2/analyze_grind2_imu_dose.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
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
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load, sustained  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_imu_dose.json"
RNG = np.random.default_rng(20260801)
IBANDS = {"18-22": (18.0, 22.0), "24-28": (24.0, 28.0), "30-40": (30.0, 40.0),
          "40-49": (40.0, 49.0), "30-49": (30.0, 49.0), "1-4": (1.0, 4.0)}
V_MAX, EFF_MIN, ANG_MIN = 4.0, 1200.0, 100.0


def env_of(t, x, lo, hi):
    fs = 1.0 / np.median(np.diff(t))
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return fs, np.abs(np.fft.irfft(H, n=len(x)))


def attach(build, recs):
    """Add imu_<band> (p99 of the |a| band envelope over the window's own time span)."""
    B = G.BUILDS[build]
    byseg = {}
    for r in recs:
        byseg.setdefault(r["seg"], []).append(r)
    rate = []
    for s, rs in byseg.items():
        p = B["cache"] / f"{B['pfx']}{s}_imu.npz"
        if not p.exists():
            continue
        z = np.load(p)
        at = z["at"]
        if len(at) < 500:
            continue
        envs = {}
        for k, (lo, hi) in IBANDS.items():
            fsa, ex = env_of(at, z["ax"], lo, hi)
            _, ey = env_of(at, z["ay"], lo, hi)
            _, ez = env_of(at, z["az"], lo, hi)
            envs[k] = np.sqrt(ex ** 2 + ey ** 2 + ez ** 2)
            rate.append(fsa)
        for r in rs:
            m = (at >= r["t0"]) & (at < r["t0"] + 2.56)
            if m.sum() < 50:
                continue
            for k in IBANDS:
                r["imu_" + k] = float(np.percentile(envs[k][m], 99))
    return float(np.median(rate)) if rate else np.nan


def boot(rs, key, rng, fn, nboot=2000):
    blk = {}
    for r in rs:
        if key in r:
            blk.setdefault(r["blk"], []).append(r[key])
    per = [np.array(v, float) for v in blk.values()]
    if not per:
        return np.nan, np.nan, np.nan, 0
    allv = np.concatenate(per)
    dr = np.empty(nboot)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        dr[b] = fn(np.concatenate([per[j] for j in i]))
    return float(fn(allv)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5)), len(allv)


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)

    G.hdr("IMU COVERAGE AND NATIVE RATE")
    rates = {}
    for b in G.ORDER:
        rates[b] = attach(b, store[b])
        n = sum(1 for r in store[b] if "imu_30-49" in r)
        print(f"  {b:10s} kd={G.BUILDS[b]['kd']:.0f}  accel median rate {rates[b]:8.4f} Hz "
              f"(Nyquist {rates[b] / 2:.2f})   windows with IMU: {n}/{len(store[b])}")
    print("\n  🛑 Nyquist ~49.7 Hz on the IMU as well ⇒ 25-70 Hz is not available and the IMU does\n"
          "  NOT break the alias. It is an independence and dose instrument only.")

    have = [b for b in G.ORDER if any("imu_30-49" in r for r in store[b])]
    k0 = [r for b in G.DOSE[0.0] if b in have for r in store[b] if "imu_30-49" in r]
    k1 = [r for b in G.DOSE[1.0] if b in have for r in store[b] if "imu_30-49" in r]
    k2 = [r for b in G.DOSE[2.0] if b in have for r in store[b] if "imu_30-49" in r]
    out = {"rates": rates}

    # ============================================================ POSITIVE CONTROL ==============
    G.hdr("★ POSITIVE CONTROL (MANDATORY): is grind #1 visible on the IMU at all?\n"
          "Engaged creep, hands-off (eng=1, v<4, sustained effort<=200) -- grind #1's own arm --\n"
          "IMU 18-22 Hz vs the 24-28 Hz band beside it, per dose. Grind #1 is known to fall with Kd,\n"
          "so the IMU must reproduce that ordering or it cannot see steering modes.")
    def g1arm(rs):
        return [r for r in rs if r["eng"] == 1 and r["v"] < 4 and r["eff"] <= 200]
    print(f"  {'dose':6s} {'n':>4s} | {'IMU 18-22 median':>28s} | {'IMU 24-28 median':>28s} | "
          f"{'ratio 18-22/24-28':>18s}")
    pc = {}
    for k, rs in ((0.0, g1arm(k0)), (1.0, g1arm(k1)), (2.0, g1arm(k2))):
        if len(rs) < 5:
            print(f"  Kd={k:.0f}  {len(rs):4d} | (too few)")
            continue
        a = boot(rs, "imu_18-22", RNG, np.median)
        c = boot(rs, "imu_24-28", RNG, np.median)
        pc[k] = dict(b1822=a, b2428=c)
        print(f"  Kd={k:.0f}  {len(rs):4d} | {a[0]:10.5f} [{a[1]:8.5f},{a[2]:8.5f}] | "
              f"{c[0]:10.5f} [{c[1]:8.5f},{c[2]:8.5f}] | {a[0] / c[0]:18.3f}")
    out["positive_control"] = pc
    print("\n  CAN 18-22 Hz in the SAME windows, for reference:")
    for k, rs in ((0.0, g1arm(k0)), (1.0, g1arm(k1)), (2.0, g1arm(k2))):
        if len(rs) < 5:
            continue
        a = boot(rs, "e_18-22", RNG, np.median)
        print(f"    Kd={k:.0f}  CAN 18-22 median {a[0]:8.1f} [{a[1]:7.1f},{a[2]:7.1f}] counts, "
              f"n={a[3]}")

    # ============================================================ THE TEST ======================
    G.hdr("THE TEST: IMU band level by dose, in the GRIND-#2 CORNER\n"
          f"(v < {V_MAX:g} m/s, sustained driver torque >= {EFF_MIN:g}, |angle| >= {ANG_MIN:g} deg)")
    def corner(rs):
        return [r for r in rs if r["v"] < V_MAX and r["eff"] >= EFF_MIN and r["ang"] >= ANG_MIN]
    res = {}
    for bnd in ("1-4", "18-22", "24-28", "30-40", "40-49", "30-49"):
        key = "imu_" + bnd
        print(f"\n  band {bnd} Hz")
        print(f"    {'dose':6s} {'n':>4s} {'nblk':>5s} | {'median m/s^2':>26s} | "
              f"{'p95':>26s} | {'max':>8s}")
        for k, rs0 in ((0.0, k0), (1.0, k1), (2.0, k2)):
            rs = corner(rs0)
            if len(rs) < 5:
                print(f"    Kd={k:.0f}  {len(rs):4d} | (too few)")
                continue
            m = boot(rs, key, RNG, np.median)
            p = boot(rs, key, RNG, lambda v: np.percentile(v, 95))
            mx = max(r[key] for r in rs if key in r)
            res[f"{bnd}|Kd{k:g}"] = dict(med=m[:3], p95=p[:3], mx=mx, n=m[3])
            print(f"    Kd={k:.0f}  {m[3]:4d} {len({r['blk'] for r in rs}):5d} | "
                  f"{m[0]:8.5f} [{m[1]:8.5f},{m[2]:8.5f}] | {p[0]:8.5f} [{p[1]:8.5f},{p[2]:8.5f}] "
                  f"| {mx:8.4f}")
    out["corner"] = res

    # ============================================================ TAIL CENSUS ===================
    G.hdr("IMU TAIL CENSUS.  Per band, the threshold is that band's own maximum over every Kd<=1\n"
          "IMU window -- the same self-scaling rule used on the CAN side.")
    print(f"  {'band':8s} {'Kd<=1 max':>10s} {'Kd=2 max':>10s} {'max ratio':>10s} | "
          f"{'Kd=2 windows over':>18s} {'blocks':>8s}")
    k1all = k0 + k1
    tail = {}
    for bnd in ("1-4", "18-22", "24-28", "30-40", "40-49", "30-49"):
        key = "imu_" + bnd
        v1 = np.array([r[key] for r in k1all if key in r])
        v2 = np.array([r[key] for r in k2 if key in r])
        if not len(v1) or not len(v2):
            continue
        m1 = float(v1.max())
        blk = {}
        for r in k2:
            if key in r:
                blk[r["blk"]] = blk.get(r["blk"], False) or (r[key] > m1)
        tail[bnd] = dict(max1=m1, max2=float(v2.max()), ratio=float(v2.max() / m1),
                         nwin=int((v2 > m1).sum()), nblk=int(sum(blk.values())), tblk=len(blk))
        print(f"  {bnd:8s} {m1:10.4f} {v2.max():10.4f} {v2.max() / m1:9.2f}x | "
              f"{int((v2 > m1).sum()):8d}/{len(v2):<8d} {sum(blk.values()):3d}/{len(blk):<4d}")
    out["tail"] = tail

    # ============================================================ COINCIDENCE ===================
    G.hdr("COINCIDENCE: do the CAN burst windows and the IMU burst windows agree, window by window?")
    allw = [r for b in have for r in store[b] if "imu_30-49" in r]
    can = np.array([r["e_30-49"] for r in allw])
    imu = np.array([r["imu_30-49"] for r in allw])
    from scipy.stats import spearmanr
    rho, pv = spearmanr(can, imu)
    hi = can > 400
    print(f"  n={len(allw)} windows across {len(have)} routes.  Spearman rho={rho:+.3f} p={pv:.2e}")
    print(f"  IMU 30-49 |a| in CAN-burst windows (n={int(hi.sum())}): "
          f"median {np.median(imu[hi]):.4f}  max {imu[hi].max():.4f} m/s^2")
    print(f"  IMU 30-49 |a| in CAN-quiet windows (n={int((~hi).sum())}): "
          f"median {np.median(imu[~hi]):.4f}  p99 {np.percentile(imu[~hi], 99):.4f}  "
          f"max {imu[~hi].max():.4f}")
    print(f"  ⇒ separation at the median: {np.median(imu[hi]) / np.median(imu[~hi]):.1f}x")
    out["coincidence"] = dict(rho=float(rho), p=float(pv),
                              burst_med=float(np.median(imu[hi])),
                              quiet_med=float(np.median(imu[~hi])))

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
