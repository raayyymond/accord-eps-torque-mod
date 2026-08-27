#!/usr/bin/env python3
"""studies/telemetry/imu_controls_and_alias.py -- data-driven IMU controls, and the honest alias verdict.

Supersedes the hand-drawn windows in studies/grind2/imu_grind_spectra.py. Every window set here is SELECTED BY THE
CAN ANALYSIS, per band:

  * the TEST set  = the top-N 2 s windows by that band's torsion-bar envelope p99
  * the CONTROL set = speed-matched windows (same vEgo +/-1 m/s) whose envelope in that band is
    below the route median, and which do not overlap any test window

🛑 WHY THE FIRST POSITIVE CONTROL WAS WRONG. Measuring 18-22 Hz inside the grind #2 demonstration
windows is not a test of "can the IMU see grind #1" -- the CAN data already says 18-22 Hz is quiet
in those windows. The control has to be run on windows where grind #1 IS present. That is what this
does, and it is the difference between an interpretable null and an uninterpretable one.

⚠ ALIAS. IMU lattice ODR 101.030 Hz vs CAN 100.00 Hz => 1.030 Hz of separation PER ALIAS ORDER. This
script measures the achievable precision on that difference instead of assuming it, including a
Lomb-Scargle attempt over the true irregular timestamps (the ~1% dropped samples are the only thing
that could break the degeneracy at all, and 1% is almost certainly too few -- tested, not assumed).
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
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parents[2]))
from analyse_v65_routes import band_env, segs  # noqa: E402
from imu_grind_spectra import AXES, load_imu, peak, slice_imu, uniform  # noqa: E402

NSEG = {"r3a": 7, "r3b": 14}
ODR = 101.030
BANDS = [("grind #1  18-22 Hz", 18.0, 22.0),
         ("grind #2  40-49 Hz", 40.0, 49.0),
         ("ratchet    5-9 Hz", 5.0, 9.0)]


def can_windows(tag, lo, hi, win=2.0, hop=0.5):
    rows = []
    for s, d in segs(tag):
        fs = 1.0 / np.median(np.diff(d["t"]))
        e = band_env(d["tq"], fs, lo, hi)
        nw, step = int(win * fs), max(1, int(hop * fs))
        for i in range(0, len(d["t"]) - nw, step):
            sl = slice(i, i + nw)
            rows.append(dict(seg=int(s), t0=float(d["t"][i]), t1=float(d["t"][i + nw - 1]),
                             env=float(np.percentile(e[sl], 99)),
                             v=float(np.median(d["cs_v"][sl]))))
    return rows


def imu_band(tag, s, t0, t1, ax, lo, hi):
    d = load_imu(tag, s)
    t, v = slice_imu(d, ax, t0, t1)
    if len(t) < 64:
        return None
    u, o, _, _, _ = uniform(t, v, ODR)
    x = u - u.mean()
    P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / o)
    k = (f >= lo) & (f <= hi)
    ref = (f >= 2) & (f <= 49.5)
    return float(P[k].sum() / k.sum()), float(P[ref].sum() / ref.sum())


def controls(tag, topn=25):
    print(f"\n{'=' * 100}\n== {tag.upper()} -- IMU BAND POWER, TEST vs SPEED-MATCHED CONTROL\n{'=' * 100}")
    out = {}
    for label, lo, hi in BANDS:
        rows = can_windows(tag, lo, hi)
        med = float(np.median([r["env"] for r in rows]))
        top = sorted(rows, key=lambda q: -q["env"])[:topn]
        near = [(r["seg"], r["t0"]) for r in top]
        ctrl = [r for r in rows
                if r["env"] < med
                and not any(r["seg"] == s and abs(r["t0"] - t) < 2.0 for s, t in near)
                and any(abs(r["v"] - q["v"]) <= 1.0 for q in top)]
        print(f"\n   *** {label} ***   test n={len(top)} (env "
              f"{top[-1]['env']:.0f}..{top[0]['env']:.0f}), control n={len(ctrl)} (env < {med:.1f})")
        print(f"   {'axis':>5s} {'test':>11s} {'control':>11s} {'RATIO':>9s} | "
              f"{'test/broad':>10s} {'ctl/broad':>10s} {'PROMINENCE':>11s}")
        for ax in AXES:
            tv = [imu_band(tag, r["seg"], r["t0"], r["t1"], ax, lo, hi) for r in top]
            cv = [imu_band(tag, r["seg"], r["t0"], r["t1"], ax, lo, hi) for r in ctrl]
            tv = [x for x in tv if x]
            cv = [x for x in cv if x]
            if not tv or not cv:
                continue
            t_abs, t_rel = np.median([a for a, _ in tv]), np.median([a / b for a, b in tv])
            c_abs, c_rel = np.median([a for a, _ in cv]), np.median([a / b for a, b in cv])
            print(f"   {ax:>5s} {t_abs:11.4g} {c_abs:11.4g} {t_abs / c_abs:8.2f}x | "
                  f"{t_rel:10.3f} {c_rel:10.3f} {t_rel / c_rel:10.2f}x")
            out[(label, ax)] = (t_abs, c_abs, t_abs / c_abs, t_rel / c_rel)
    return out


def alias(tag, topn=12):
    """Paired peak comparison on TIGHT single-burst windows, plus a Lomb-Scargle attempt."""
    print(f"\n{'=' * 100}\n== {tag.upper()} -- ALIAS DISCRIMINATION\n{'=' * 100}")
    b = json.loads((ROOT / f"_cache_{tag}" / f"{tag}_bursts.json").read_text())["band_30_49"]
    b = [r for r in b if r["dur"] >= 0.5][:topn]
    can = {s: d for s, d in segs(tag)}
    print(f"   {'seg':>4s} {'t':>7s} {'dur':>6s} | {'CAN f_pk':>9s} {'SNR':>7s} | {'ax':>3s} "
          f"{'IMU f_pk':>9s} {'SNR':>7s} | {'shift':>8s}")
    rows = []
    for r in b:
        s, t0, t1 = r["seg"], r["t"], r["t_end"]
        d = can[s]
        m = (d["t"] >= t0) & (d["t"] <= t1)
        if m.sum() < 48:
            continue
        fc, pc, flc = peak(d["tq"][m], 100.0, 30.0, 49.5)
        best = None
        for ax in AXES:
            t, v = slice_imu(load_imu(tag, s), ax, t0, t1)
            if len(t) < 48:
                continue
            u, o, _, _, _ = uniform(t, v, ODR)
            fi, pi, fli = peak(u, o, 30.0, 49.5)
            snr = pi / fli if fli > 0 else 0
            if best is None or snr > best[2]:
                best = (ax, fi, snr)
        if best is None:
            continue
        ax, fi, snr = best
        snr_can = pc / flc
        print(f"   {s:4d} {t0:6.2f}s {r['dur']:5.2f}s | {fc:9.4f} {snr_can:7.1f} | {ax:>3s} "
              f"{fi:9.4f} {snr:7.1f} | {fi - fc:+8.4f}")
        rows.append((fc, fi, snr_can, snr, ax))
    if len(rows) >= 2:
        sh = np.array([b_ - a for a, b_, _, _, _ in rows])
        hi = np.array([b_ - a for a, b_, sc, si, _ in rows if sc > 20 and si > 20])
        print(f"\n   ALL   n={len(sh):2d}  shift med {np.median(sh):+.4f} Hz  mean {sh.mean():+.4f}  "
              f"sd {sh.std(ddof=1):.4f}  sem {sh.std(ddof=1) / np.sqrt(len(sh)):.4f}")
        if len(hi) >= 2:
            print(f"   SNR>20 both n={len(hi):2d}  shift med {np.median(hi):+.4f}  "
                  f"sd {hi.std(ddof=1):.4f}  sem {hi.std(ddof=1) / np.sqrt(len(hi)):.4f}")
        print(f"\n   Separation to resolve = {ODR - 100.0:.4f} Hz per alias order.")
        sem = sh.std(ddof=1) / np.sqrt(len(sh))
        print(f"   Measured sem on the shift = {sem:.4f} Hz  =>  "
              f"{'RESOLVABLE' if sem < 0.34 else 'NOT RESOLVABLE'} "
              f"(need sem < ~1/3 of {ODR - 100.0:.3f})")
    return rows


def lombscargle(tag):
    """Do the ~1% dropped samples break the alias? Test it; do not assume.

    A perfectly uniform sampler has exact alias ambiguity. Random decimation breaks it, because the
    aliases stop being exactly degenerate. With ~1% drops the effect is expected to be tiny -- this
    measures HOW tiny, by scoring the true peak against its own mirror images above Nyquist.
    """
    from scipy.signal import lombscargle as ls
    print(f"\n-- LOMB-SCARGLE over the IRREGULAR timestamps (can the dropped samples break it?) --")
    b = json.loads((ROOT / f"_cache_{tag}" / f"{tag}_bursts.json").read_text())["band_30_49"]
    b = [r for r in b if r["dur"] >= 1.0][:4]
    for r in b:
        s, t0, t1 = r["seg"], r["t"], r["t_end"]
        d = load_imu(tag, s)
        t, v = slice_imu(d, "ay", t0, t1)
        if len(t) < 64:
            continue
        v = v - v.mean()
        f = np.arange(20.0, 200.0, 0.02)
        P = ls(t.astype(float), v.astype(float), 2 * np.pi * f, normalize=True)
        # the candidate set: the sub-Nyquist peak and its mirrors on the IMU lattice
        k = (f >= 30) & (f <= 49.5)
        f0 = f[k][np.argmax(P[k])]
        cands = [f0, ODR - f0, ODR + f0, 2 * ODR - f0, 2 * ODR + f0]
        sc = []
        for c in cands:
            j = (f >= c - 0.4) & (f <= c + 0.4)
            sc.append(P[j].max() if j.any() else 0.0)
        best = int(np.argmax(sc))
        print(f"   seg{s} t={t0:.2f}s  sub-Nyquist peak {f0:.3f} Hz")
        print(f"      candidates: " + "  ".join(f"{c:7.2f}Hz p={p:.4f}" for c, p in zip(cands, sc)))
        print(f"      argmax = {cands[best]:.2f} Hz; top/next power ratio = "
              f"{sorted(sc)[-1] / max(sorted(sc)[-2], 1e-12):.4f}  "
              f"({'DISCRIMINATES' if sorted(sc)[-1] / max(sorted(sc)[-2], 1e-12) > 1.5 else 'does NOT discriminate'})")


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["r3a", "r3b"]):
        controls(tag)
        alias(tag)
        try:
            lombscargle(tag)
        except ImportError:
            print("   scipy unavailable; Lomb-Scargle skipped")
