#!/usr/bin/env python3
"""IS THE FIXED ~42 Hz HIGHWAY LINE AN ENGINE ORDER SEEN THROUGH THE ALIAS?

`studies/highway/highway_order_test.py` established, with a razor-sharp positive control (the 8-30 Hz line reads
wheel order 1.00-1.02 in every speed bin), that the 30-49.5 Hz line on all four comma-IMU axes
sits at 42-43 Hz and does NOT move while road speed runs 22 -> 35 m/s. Wheel order 3 would climb
33.3 -> 47.9 Hz across that span, so ORDER 3 IS REFUTED and the operator's "the pitch stays about
the same" is confirmed as a measurement.

That leaves TWO ways to be fixed in hertz, and they have opposite consequences:

  (A) a genuine structural/control MODE          -> a firmware target is conceivable
  (B) an ENGINE order, held still by the CVT     -> not a firmware target at all

The 2020 Accord's CVT holds engine speed roughly constant at cruise, so (B) produces a line that
is fixed in hertz while road speed varies -- the same signature. Measured highway rpm on route 47
is 1330-1810 (p50 1504-1796 per segment), so:

    engine order 2 (4-cylinder firing) = rpm/30 = 44.3 .. 60.3 Hz   -- ABOVE both Nyquists
    aliased onto the IMU lattice   |101.03 - rpm/30| = 40.7 .. 56.7 Hz
    aliased onto the CAN grid      |100.00 - rpm/30| = 39.7 .. 55.7 Hz

🛑 THE ALIAS IS ALSO THE TEST'S TEETH, TWICE OVER:
  1. An ALIASED line moves OPPOSITE to its source: rpm UP => apparent frequency DOWN. No mode and
     no wheel order does that. A negative f0-vs-rpm slope of -1/30 Hz per rpm is a signature that
     is very hard to counterfeit.
  2. The IMU lattice (101.03 Hz) and the CAN grid (100.000 Hz) fold about DIFFERENT points, so one
     physical line above Nyquist must appear ~1.03 Hz apart on the two channels while a true
     sub-50 Hz line must appear at the SAME frequency on both.

Usage:  python studies/highway/highway_rpm_test.py
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r47_imu_lib as I         # noqa: E402
import highway_event_hunt as H   # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_scratch/out/_hwy_rpm_test.json"
NFFT = 256
CIRC = H.CIRC
CACHE = {"47": "_scratch/cache/r47", "3b": "_scratch/cache/r3b", "2b": "_scratch/cache/r2b", "37": "_scratch/cache/r37"}
PFX = {"47": "r47s", "3b": "r3bs", "2b": "r2bs", "37": "r37s"}


def load_rpm(rt, seg):
    p = ROOT / CACHE.get(rt, "") / f"{PFX.get(rt, '')}{seg}_rpm.npz"
    return dict(np.load(p)) if p.exists() else None


def main():
    store = {}
    rows = []

    # ------------------------------------------------------------------ build the window table --
    for rt, cd, pfx, segs, bld, kd in H.ROUTES:
        if rt not in CACHE:
            continue
        for s in segs:
            dr = load_rpm(rt, s)
            dc = H.load_seg(cd, pfx, s)
            if dr is None or dc is None:
                continue
            fs = 1.0 / float(np.median(np.diff(dc["t"])))
            rpm_on_can = np.interp(dc["t"], dr["t"], dr["rpm"])
            # ---- CAN torsion bar --------------------------------------------------------------
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            v = np.abs(dc["cs_v"])
            lat = dc["cc_lat"] > 0.5
            for i in range(0, len(dc["t"]) - NFFT + 1, NFFT // 2):
                sl = slice(i, i + NFFT)
                vv = float(np.mean(v[sl]))
                if vv < 22.0 or np.mean(lat[sl]) < 0.9:
                    continue
                P = G.periodogram(dc["tq"][sl], fs, NFFT, True)
                if P is None:
                    continue
                R = G.prom_spectrum(f, P)
                f0, pr = G.locate(f, P, 30.0, 49.5, R=R)
                rows.append(dict(chan="bar", route=rt, kd=kd, seg=int(s), i=i, fs=fs, v=vv,
                                 rpm=float(np.median(rpm_on_can[sl])), f0=f0, prom=pr,
                                 t=float(dc["t"][i])))
            # ---- IMU ---------------------------------------------------------------------------
            pim = ROOT / cd / f"{pfx}{s}_imu.npz"
            if not pim.exists():
                continue
            di = dict(np.load(pim))
            for ax in ("ay", "gz", "az"):
                g = ax[0]
                u, odr, _, tu = I.uniform(di["at"] if g == "a" else di["gt"], di[ax])
                vv_i = I.lerp(tu, dc["t"], v)
                lat_i = I.hold(tu, dc["t"], lat.astype(float))
                rpm_i = I.lerp(tu, dr["t"], dr["rpm"])
                fi = np.fft.rfftfreq(NFFT, 1 / odr)
                for i in range(0, len(u) - NFFT + 1, NFFT // 2):
                    sl = slice(i, i + NFFT)
                    sp = float(np.mean(vv_i[sl]))
                    if sp < 22.0 or np.mean(lat_i[sl]) < 0.9:
                        continue
                    P = I.periodogram(u[sl], odr, NFFT, True)
                    if P is None:
                        continue
                    Rp = I.prom_spectrum(fi, P)
                    f0, pr = I.locate(fi, P, 30.0, 49.5, R=Rp)
                    rows.append(dict(chan=ax, route=rt, kd=kd, seg=int(s), i=i, fs=odr, v=sp,
                                     rpm=float(np.median(rpm_i[sl])), f0=f0, prom=pr,
                                     t=float(tu[i])))
    print(f"[{len(rows)} windows with both engine rpm and a 30-49.5 Hz line, v >= 22 m/s]")
    if not rows:
        print("no rows -- run extract/extract_rpm_cache.py first")
        return

    # ------------------------------------------------------------------ 1. the candidates -------
    G.hdr("1.  WHAT EACH HYPOTHESIS PREDICTS, on this population")
    r = [x for x in rows if np.isfinite(x["f0"])]
    rpm = np.array([x["rpm"] for x in r])
    print(f"    engine rpm at v>=22 m/s: p05 {np.percentile(rpm, 5):.0f}  p50 "
          f"{np.median(rpm):.0f}  p95 {np.percentile(rpm, 95):.0f}   "
          f"(CVT: rpm and road speed are only loosely coupled)")
    vv = np.array([x["v"] for x in r])
    print(f"    road speed:              p05 {np.percentile(vv, 5):.1f}  p50 "
          f"{np.median(vv):.1f}  p95 {np.percentile(vv, 95):.1f} m/s")
    print(f"    corr(rpm, v) = {np.corrcoef(rpm, vv)[0, 1]:+.3f}  -- if this were near 1 the two\n"
          f"      hypotheses could not be separated on this data; it is not.")
    store["corr_rpm_v"] = float(np.corrcoef(rpm, vv)[0, 1])

    # ------------------------------------------------------------------ 2. model comparison -----
    G.hdr("2.  MODEL COMPARISON, per channel. Residual sd of the observed 30-49.5 Hz line\n"
          "    against each zero-free-parameter prediction. Lowest wins.")
    print(f"    {'chan':>5}{'n':>6}{'f0 p50':>9}" + "".join(
        f"{k:>14}" for k in ("const", "wheel ord3", "eng2 alias", "eng2 direct", "eng1")))
    for ch in ("bar", "ay", "gz", "az"):
        s = [x for x in r if x["chan"] == ch]
        if len(s) < 40:
            continue
        f0 = np.array([x["f0"] for x in s])
        rp = np.array([x["rpm"] for x in s])
        vs = np.array([x["v"] for x in s])
        fsm = float(np.median([x["fs"] for x in s]))
        pred = {
            "const": np.full(len(s), np.median(f0)),
            "wheel ord3": 3 * vs / CIRC,
            "eng2 alias": np.abs(fsm - rp / 30.0),
            "eng2 direct": rp / 30.0,
            "eng1": rp / 60.0,
        }
        sds = {k: float(np.std(f0 - p)) for k, p in pred.items()}
        best = min(sds, key=sds.get)
        print(f"    {ch:>5}{len(s):>6}{np.median(f0):>9.2f}"
              + "".join(f"{sds[k]:>14.2f}" for k in pred)
              + f"   best: {best}")
        store.setdefault("resid_sd", {})[ch] = sds
    print("\n    (units are Hz; the 0.39 Hz bin size is the floor a perfect model could reach)")

    # ------------------------------------------------------------------ 3. the alias signature --
    G.hdr("3.  THE ALIAS SIGNATURE: does f0 move DOWN when rpm moves UP?\n"
          "    An aliased engine order 2 must have slope -1/30 = -0.0333 Hz per rpm.\n"
          "    A mode gives 0. A wheel order gives 0 too (rpm and speed are decoupled here).")
    for ch in ("bar", "ay", "gz", "az"):
        s = [x for x in r if x["chan"] == ch]
        if len(s) < 40:
            continue
        f0 = np.array([x["f0"] for x in s])
        rp = np.array([x["rpm"] for x in s])
        sl, lo, hi, ic, n = H.theil_sen(rp, f0, RNG, 600)
        print(f"    {ch:>5}  n={n:5d}  slope {sl:+.5f} Hz/rpm  [{lo:+.5f}, {hi:+.5f}]  "
              f"intercept {ic:7.2f}")
        print(f"    {'':5}    alias prediction -0.03333: "
              f"{'INSIDE' if lo <= -1 / 30 <= hi else 'EXCLUDED'};   "
              f"mode/order prediction 0.0: {'INSIDE' if lo <= 0 <= hi else 'EXCLUDED'}")
        store.setdefault("slope_vs_rpm", {})[ch] = dict(slope=sl, lo=lo, hi=hi, n=n)

    # ------------------------------------------------------------------ 4. rpm-binned table -----
    G.hdr("4.  BINNED f0 vs ENGINE RPM (the assumption-free version of §3)")
    RB = [(1300, 1450), (1450, 1550), (1550, 1650), (1650, 1750), (1750, 1850), (1850, 2400)]
    for ch in ("ay", "gz", "az", "bar"):
        s = [x for x in r if x["chan"] == ch]
        if len(s) < 40:
            continue
        fsm = float(np.median([x["fs"] for x in s]))
        print(f"\n    --- {ch} ---   {'rpm bin':>12}{'n':>6}{'f0 p50':>9}{'eng2 alias':>12}"
              f"{'eng2 true':>11}{'  v p50':>9}{'wheel3':>9}")
        for a, b in RB:
            k = [x for x in s if a <= x["rpm"] < b]
            if len(k) < 10:
                continue
            f0 = np.median([x["f0"] for x in k])
            rp = np.median([x["rpm"] for x in k])
            vm = np.median([x["v"] for x in k])
            print(f"    {'':>9}{f'{a}-{b}':>12}{len(k):>6}{f0:>9.2f}"
                  f"{abs(fsm - rp / 30):>12.2f}{rp / 30:>11.2f}{vm:>9.1f}{3 * vm / CIRC:>9.2f}")

    # ------------------------------------------------------------------ 5. two-lattice test -----
    G.hdr("5.  THE TWO-LATTICE TEST. One physical line ABOVE Nyquist must appear ~1.03 Hz\n"
          "    apart on the CAN grid (100.000 Hz) and the IMU lattice (101.03 Hz); a true\n"
          "    sub-50 Hz line must appear at the SAME frequency on both.")
    pair = {}
    for x in r:
        pair.setdefault((x["route"], x["seg"], round(x["t"], 0)), {})[x["chan"]] = x["f0"]
    dif = [(p["ay"] - p["bar"]) for p in pair.values() if "ay" in p and "bar" in p]
    if len(dif) > 20:
        d = np.array(dif)
        m, lo, hi = np.median(d), np.percentile(d, 25), np.percentile(d, 75)
        print(f"    n={len(d)} co-timed window pairs.  f0(IMU ay) - f0(bar) = "
              f"{m:+.2f} Hz  [IQR {lo:+.2f}, {hi:+.2f}]")
        print(f"      a shared SUB-Nyquist line predicts  0.00 Hz")
        print(f"      a shared line aliased once predicts +1.03 Hz "
              f"(the two lattices fold about different points)")
        print("    🛑 This test is weak here: the two channels do not have to be dominated by the\n"
              "       SAME line, and the bar's 30-49.5 argmax is demonstrably a wheel order below\n"
              "       30 m/s. Read it as corroboration only, never as the primary evidence.")
        store["two_lattice_diff"] = dict(n=len(d), median=float(m), q25=float(lo), q75=float(hi))

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
