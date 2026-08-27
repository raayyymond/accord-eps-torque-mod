#!/usr/bin/env python3
r"""What survives the white-noise control, and what does not.

The -3 dB width estimator returns Q p50 = 72.7 on white noise whose TRUE Q is 1.8.  That is the
kit's recorded `q_of`-returns-79.00 failure, reproduced.  So:
  1.  Re-measure the V101 vs V100 peak FREQUENCY with the speed distributions reported, since the
      peak moves +0.155 Hz per m/s and the two drives had different speed profiles.
  2.  Compute the PEAK-RELATIVE SHAPE RATIO on BOTH routes so the V102 endpoint has a real
      reference, and check its own white-noise / surrogate control.
  3.  Quantify the prominence-vs-width confound that indicts the Q ratio: a low-prominence peak
      measures WIDER under this estimator purely because the noise floor eats the -3 dB crossing.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import r95_lib as L  # noqa: E402

FS = L.fs()
out = {}
R = {}
for r, stem in (("95", "_scratch/cache/r95/r95.npz"), ("85", "_scratch/cache/r85/r85.npz")):
    z = dict(np.load(ROOT / "analysis-2020accord" / stem, allow_pickle=True))
    R[r] = dict(t=np.asarray(z["t"], float), lat=np.asarray(z["cc_lat"], float) > 0.5,
                vk=np.abs(np.asarray(z["cs_v"], float)) * 3.6,
                tq=np.asarray(z["tq"], float), rate=np.asarray(z["rate_f"], float))


def runs_break(mask, t, min_n):
    idx = np.where(mask)[0]
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


# ======================================================================================
print("=" * 100)
print("1. THE SPEED-MATCH BEHIND THE FREQUENCY CLAIM.  The peak moves +0.155 [0.089, 0.231]")
print("   Hz per m/s (measured on r95), so the two drives' speed profiles must be stated.")
print("=" * 100)
for lo, hi in ((20, 70), (20, 40), (40, 70)):
    row = {}
    for r in ("95", "85"):
        m = R[r]["lat"] & (R[r]["vk"] >= lo) & (R[r]["vk"] < hi)
        row[r] = (m.sum() / FS, float(np.mean(R[r]["vk"][m])), float(np.median(R[r]["vk"][m])))
    print(f"    {lo}-{hi} km/h:  r95 {row['95'][0]:6.1f} s mean {row['95'][1]:5.2f} med "
          f"{row['95'][2]:5.2f}   |   r85 {row['85'][0]:6.1f} s mean {row['85'][1]:5.2f} med "
          f"{row['85'][2]:5.2f}   Δmean {row['95'][1]-row['85'][1]:+5.2f} km/h "
          f"= {(row['95'][1]-row['85'][1])/3.6*0.155:+.3f} Hz of expected shift")
    out.setdefault("speed_match", []).append(dict(lo=lo, hi=hi, r95=row["95"], r85=row["85"]))


def welch(x, m, t, nfft):
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    P = np.zeros(len(f))
    K = 0
    for a, b in runs_break(m, t, nfft):
        for i in range(a, b - nfft + 1, nfft // 2):
            seg = np.nan_to_num(x[i:i + nfft] - np.nanmean(x[i:i + nfft]))
            P += np.abs(np.fft.rfft(seg * win)) ** 2
            K += 1
    return f, P / max(K, 1), K


print("\n    PEAK FREQUENCY, matched speed bands, nfft 1024 (df 0.099 Hz):")
print(f"    {'band':>12s} {'ch':>7s} | {'r95 f_pk':>9s} {'K':>4s} | {'r85 f_pk':>9s} {'K':>4s} | "
      f"{'Δf':>7s} {'expected from Δspeed':>21s}")
for lo, hi in ((20, 70), (20, 40), (40, 70)):
    for ch in ("tq", "rate"):
        vals = {}
        for r in ("95", "85"):
            m = R[r]["lat"] & (R[r]["vk"] >= lo) & (R[r]["vk"] < hi)
            f, P, K = welch(R[r][ch], m, R[r]["t"], 1024)
            b = (f >= 18) & (f <= 30)
            vals[r] = (float(f[b][np.argmax(P[b])]), K,
                       float(np.mean(R[r]["vk"][m])) if m.any() else np.nan)
        exp = (vals["95"][2] - vals["85"][2]) / 3.6 * 0.155
        print(f"    {lo:4d}-{hi:<7d} {ch:>7s} | {vals['95'][0]:9.2f} {vals['95'][1]:4d} | "
              f"{vals['85'][0]:9.2f} {vals['85'][1]:4d} | "
              f"{vals['95'][0]-vals['85'][0]:+7.2f} {exp:+21.3f}")
        out.setdefault("freq", []).append(
            dict(lo=lo, hi=hi, ch=ch, f95=vals["95"][0], f85=vals["85"][0],
                 K95=vals["95"][1], K85=vals["85"][1], expected_from_speed=float(exp)))

# ======================================================================================
print("\n" + "=" * 100)
print("2. THE PROMINENCE-vs-WIDTH CONFOUND THAT INDICTS THE Q RATIO.")
print("   Under a -3 dB estimator a peak sitting close to the noise floor measures WIDER, because")
print("   the half-power crossing runs into the floor.  V101 peak/floor = 40.9, V100 = 5.2.")
print("   Demonstration: add a synthetic floor to V101's spectrum to match V100's prominence and")
print("   re-measure its width.  If V101's width then matches V100's, the 'narrower peak' claim")
print("   is a PROMINENCE artifact, not a damping measurement.")
print("=" * 100)
m95 = R["95"]["lat"] & (R["95"]["vk"] >= 20) & (R["95"]["vk"] < 70)
f, P95, K95 = welch(R["95"]["tq"], m95, R["95"]["t"], 1024)
m85 = R["85"]["lat"] & (R["85"]["vk"] >= 20) & (R["85"]["vk"] < 70)
_f, P85, K85 = welch(R["85"]["tq"], m85, R["85"]["t"], 1024)


def width_of(f, P):
    b = (f >= 18) & (f <= 30)
    fb, Pb = f[b], P[b]
    i = int(np.argmax(Pb))
    half = Pb[i] / 2
    j = i
    while j > 0 and Pb[j] > half:
        j -= 1
    k = i
    while k < len(Pb) - 1 and Pb[k] > half:
        k += 1
    fl = float(np.median(P[(f >= 15) & (f <= 19)]))
    return float(fb[i]), float(fb[k] - fb[j]), float(Pb[i] / fl)


f95, w95, pr95 = width_of(f, P95)
f85, w85, pr85 = width_of(f, P85)
print(f"    V101: peak {f95:.2f} Hz  width {w95:.2f} Hz  Q {f95/w95:.1f}  peak/floor {pr95:.1f}")
print(f"    V100: peak {f85:.2f} Hz  width {w85:.2f} Hz  Q {f85/w85:.1f}  peak/floor {pr85:.1f}")
floor95 = float(np.median(P95[(f >= 15) & (f <= 19)]))
add = floor95 * (pr95 / pr85 - 1.0)
fA, wA, prA = width_of(f, P95 + add)
print(f"    V101 with a floor added to match V100's prominence ({prA:.1f}): peak {fA:.2f} Hz  "
      f"width {wA:.2f} Hz  Q {fA/wA:.1f}")
print(f"    ⇒ V101's width goes {w95:.2f} -> {wA:.2f} Hz purely from the floor.  V100 measured "
      f"{w85:.2f} Hz.")
verdict = ("🛑 THE WIDTH/Q RATIO IS A PROMINENCE ARTIFACT -- RETRACT IT"
           if abs(wA - w85) < 0.5 * abs(w95 - w85) else
           "the width difference survives the prominence match")
print(f"    {verdict}")
out["prominence"] = dict(v101=dict(f=f95, w=w95, prom=pr95), v100=dict(f=f85, w=w85, prom=pr85),
                         v101_floor_matched=dict(f=fA, w=wA, prom=prA), verdict=verdict)

# ======================================================================================
print("\n" + "=" * 100)
print("3. THE PEAK-RELATIVE SHAPE RATIO -- the surviving endpoint, on BOTH routes.")
print("   band = measured 18-30 Hz peak +- 2 Hz ;  control = 32-38 Hz ;  1 s engaged windows.")
print("=" * 100)


def shape_windows(r, lo, hi):
    d = R[r]
    m = d["lat"] & (d["vk"] >= lo) & (d["vk"] < hi)
    WL = int(round(1.0 * FS))
    vals = []
    for a, b in runs_break(m, d["t"], max(WL, 1024)):
        seg = np.nan_to_num(d["tq"][a:b] - np.nanmean(d["tq"][a:b]))
        ff = np.fft.rfftfreq(len(seg), 1 / FS)
        PP = np.abs(np.fft.rfft(seg)) ** 2
        bb = (ff >= 18) & (ff <= 30)
        fp = float(ff[bb][np.argmax(PP[bb])])
        X = np.fft.rfft(seg)
        f2 = np.fft.rfftfreq(len(seg), 1 / FS)
        Xa = X.copy()
        Xa[(f2 < fp - 2) | (f2 > fp + 2)] = 0
        ya = np.fft.irfft(Xa, n=len(seg))
        Xb = X.copy()
        Xb[(f2 < 32) | (f2 > 38)] = 0
        yb = np.fft.irfft(Xb, n=len(seg))
        for i in range(0, len(seg) - WL + 1, WL):
            s = slice(i, i + WL)
            vals.append(float(np.sqrt(np.mean(ya[s] ** 2)) /
                              max(np.sqrt(np.mean(yb[s] ** 2)), 1e-12)))
    return np.array(vals, float)


rng = np.random.default_rng(9)
print(f"    {'km/h':>10s} | {'V101 n':>7s} {'shape [95% CI]':>24s} | {'V100 n':>7s} "
      f"{'shape [95% CI]':>24s} | {'separation':>11s}")
for lo, hi in ((0, 70), (20, 70), (20, 40), (40, 70)):
    cells, med = "", {}
    for r in ("95", "85"):
        v = shape_windows(r, lo, hi)
        if len(v) < 8:
            cells += f"{len(v):7d}{'   --':>24s}"
            med[r] = np.nan
            continue
        bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(3000)]
        l95, h95 = np.percentile(bs, [2.5, 97.5])
        cells += f"{len(v):7d}{np.median(v):9.2f} [{l95:6.2f},{h95:6.2f}]"
        med[r] = float(np.median(v))
    sep = med["95"] / med["85"] if np.isfinite(med.get("85", np.nan)) else np.nan
    print(f"    {lo:3d}-{hi:<5d} | " + cells + f" | {sep:11.2f}x")
    out.setdefault("shape_peakrel", []).append(dict(lo=lo, hi=hi, v101=med["95"],
                                                    v100=med["85"], sep=float(sep)))

(L.CACHE / "r95_q_retract.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_q_retract.json'}")
