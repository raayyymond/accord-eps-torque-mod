#!/usr/bin/env python3
"""V62 route-37: locate and characterise the HIGH-FREQUENCY bursts (>26 Hz) on the torsion bar.

The zoom pass found a ~42 Hz, near-full-scale burst at seg1 t=10.2-10.8 s (wall 10:12:15), which
is one of the two instances the operator remembered. This script:

  1. Sweeps the WHOLE route (segs 1-14) for 26-45 Hz burst energy and ranks every occurrence.
  2. Prints the full periodogram of the top bursts so the harmonic structure is visible rather
     than summarised.
  3. Tests the 42 Hz line against its 21 Hz subharmonic (is it a harmonic of the known mode, or an
     independent line?).
  4. States the alias caveat: fs is 100.3-101.4 Hz, so 41.9 Hz is indistinguishable from any
     true frequency at |100.5*k +/- 41.9|. The CAN stream cannot resolve above ~50 Hz.
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
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402

C.CACHE = C.ROOT / "_scratch/cache/r37"
PFX = "r37s"
SEGS = list(range(1, 15))
NFFT = 256
B_HI = (26.0, 45.0)
B_MODE = (18.0, 26.0)

_C = {}


def seg(s):
    if s not in _C:
        _C[s] = C.load(s, C.CACHE, PFX)
    return _C[s]


def wall(d, t):
    return time.strftime("%H:%M:%S", time.localtime(float(d["wall_t0"][0]) + t))


def sweep():
    """Every NFFT/4-hopped window in the route, ranked by 26-45 Hz envelope p99."""
    rows = []
    for s in SEGS:
        d = seg(s)
        fs = C.fs_of(d)
        x = d["tq"]
        ehi = C.band_envelope(x, fs, *B_HI)
        emo = C.band_envelope(x, fs, *B_MODE)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        for i in range(0, len(x) - NFFT + 1, NFFT // 4):
            P = C.periodogram(x[i:i + NFFT], fs, NFFT)
            if P is None:
                continue
            sl = slice(i, i + NFFT)
            fh, ph = C.peak_prom(f, P, *B_HI)
            fm, pm = C.peak_prom(f, P, *B_MODE)
            rows.append(dict(
                seg=s, t0=float(d["t"][i]), fs=fs,
                ehi=float(np.percentile(ehi[sl], 99)), emo=float(np.percentile(emo[sl], 99)),
                fh=fh, ph=ph, fm=fm, pm=pm,
                Qh=C.q_of(f, P, fh) if np.isfinite(fh) else np.nan,
                v=float(np.mean(d["cs_v"][sl])), ang=float(np.mean(np.abs(d["ang"][sl]))),
                eff=float(np.mean(np.abs(C.sustained(d["tq"][sl], fs)))),
                e4=float(np.mean(np.abs(d["e4tq"][sl]))),
                e4sat=float(np.mean(np.abs(d["e4tq"][sl]) >= 4090)),
                lat=float(np.mean(d["cc_lat"][sl] > 0.5)),
                press=float(np.mean(d["cs_press"][sl] > 0.5)),
                therm=float(np.mean(d["therm"][sl])),
                tqmax=float(np.max(np.abs(x[sl]))),
                jump=float(np.max(np.abs(np.diff(x[sl])))),
            ))
    return rows


def main():
    rows = sweep()
    print(f"windows (NFFT=256, hop=64, segs 1-14): {len(rows)}")
    ehi = np.array([r["ehi"] for r in rows])
    print(f"26-45 Hz envelope p99 over all windows: median {np.median(ehi):.1f}  "
          f"p90 {np.percentile(ehi,90):.1f}  p99 {np.percentile(ehi,99):.1f}  "
          f"p99.9 {np.percentile(ehi,99.9):.1f}  max {ehi.max():.1f}")
    thr = np.percentile(ehi, 99.5)
    print(f"\nWindows above the 99.5th percentile of 26-45 Hz envelope ({thr:.1f} counts), "
          f"merged into bursts:")
    hot = [r for r in rows if r["ehi"] >= thr]
    hot.sort(key=lambda r: (r["seg"], r["t0"]))
    # merge into contiguous bursts
    bursts, cur = [], None
    for r in hot:
        if cur and r["seg"] == cur[-1]["seg"] and r["t0"] - cur[-1]["t0"] < 3.0:
            cur.append(r)
        else:
            if cur:
                bursts.append(cur)
            cur = [r]
    if cur:
        bursts.append(cur)
    print("  seg  wall_start..end     dur   nwin  ehi_max  emo_max  f_hi    Q     f_mode  "
          "v      |ang|   eff    e4    e4sat lat  prs therm  tqmax  maxjump")
    for bb in bursts:
        d = seg(bb[0]["seg"])
        pk = max(bb, key=lambda r: r["ehi"])
        print(f"  {bb[0]['seg']:3d}  {wall(d, bb[0]['t0'])}..{wall(d, bb[-1]['t0'])}  "
              f"{bb[-1]['t0']-bb[0]['t0']+2.56:5.2f} {len(bb):4d}  "
              f"{max(r['ehi'] for r in bb):8.1f} {max(r['emo'] for r in bb):8.1f} "
              f"{pk['fh']:6.2f} {pk['Qh']:5.1f} {pk['fm']:7.2f} "
              f"{pk['v']:6.2f} {pk['ang']:7.1f} {pk['eff']:6.0f} {pk['e4']:5.0f} "
              f"{pk['e4sat']:5.2f} {pk['lat']:4.2f} {pk['press']:4.2f} {pk['therm']:5.2f} "
              f"{pk['tqmax']:6.0f} {pk['jump']:7.0f}   t={bb[0]['t0']:.2f}..{bb[-1]['t0']:.2f}")

    # ---- full spectrum of the single worst window -------------------------------------------
    worst = max(rows, key=lambda r: r["ehi"])
    d = seg(worst["seg"])
    fs = worst["fs"]
    i = int(np.argmin(np.abs(d["t"] - worst["t0"])))
    print(f"\nFULL PERIODOGRAM, worst window: seg{worst['seg']} t={worst['t0']:.2f} "
          f"({wall(d, worst['t0'])})  fs={fs:.3f}  Nyquist={fs/2:.2f}")
    P = C.periodogram(d["tq"][i:i + NFFT], fs, NFFT)
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    Pn = P / P.max()
    for j in range(1, len(f)):
        if f[j] > 50:
            break
        bar = "#" * int(round(60 * Pn[j] ** 0.35))
        print(f"   {f[j]:6.2f} Hz  {10*np.log10(Pn[j]+1e-30):7.2f} dB  {bar}")

    # ---- harmonic test on every hot window ---------------------------------------------------
    print("\nHARMONIC TEST on hot windows: is the >26 Hz line 2x the 18-26 Hz line?")
    print("   seg   t0    wall      f_hi    f_mode   2*f_mode  |diff|   P_hi/P_mode  Q_hi")
    for r in sorted(hot, key=lambda r: -r["ehi"])[:25]:
        d = seg(r["seg"])
        fs = r["fs"]
        i = int(np.argmin(np.abs(d["t"] - r["t0"])))
        P = C.periodogram(d["tq"][i:i + NFFT], fs, NFFT)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        jh = int(np.argmin(np.abs(f - r["fh"]))) if np.isfinite(r["fh"]) else 0
        jm = int(np.argmin(np.abs(f - r["fm"]))) if np.isfinite(r["fm"]) else 0
        dif = abs(r["fh"] - 2 * r["fm"]) if np.isfinite(r["fh"]) and np.isfinite(r["fm"]) else np.nan
        print(f"   {r['seg']:3d} {r['t0']:6.2f} {wall(d, r['t0'])} {r['fh']:7.2f} "
              f"{r['fm']:8.2f} {2*r['fm']:9.2f} {dif:7.2f} "
              f"{P[jh]/max(P[jm],1e-30):12.3f} {r['Qh']:5.1f}")

    print("\n🛑 ALIAS CAVEAT: the CAN stream is ~100.5 Hz, Nyquist ~50.2 Hz. A measured 41.9 Hz is "
          "indistinguishable\n   from a true 58.6 Hz (= fs - 41.9), 142.4 Hz, ... The ECU samples "
          "the bar at ~1 kHz internally and\n   reports at 100 Hz, so this data cannot settle the "
          "true frequency above ~50 Hz. What it DOES settle is\n   that the reported sensor value "
          "swings near full scale sample-to-sample, which is a real instability.")


if __name__ == "__main__":
    main()
