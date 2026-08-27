#!/usr/bin/env python3
"""CROSS-BUILD RINGDOWN Q from the latActive falling edge -- the only exogenous input in these logs.

TWO QUESTIONS
  Q1  Is my reported Q amplitude-dependence (7.1 -> 74.5) real, or a NOISE-FLOOR artefact?
      v81loop measures the post-decay envelope at mean 16.3 / p95 34.4 / max 40.1 ct against my
      stated floor of 8.2, and points out my +0.5->+0.6 interval (40 -> 36 ct) sits inside it.
      Tested here by measuring the floor properly and subtracting it IN POWER
      (env_true = sqrt(max(env^2 - F^2, 0))), which is the right correction for an incoherent
      additive floor, then re-deriving the local taus.
  Q2  Does ringdown Q track the damper dose ladder (k = 1.39 / 1.58 / 4.16)?
      🛑 A PREDICTION FIRST, so this is a real test and not a fishing trip: at the falling edge the
      mode switches 26 -> 24, and V75/V81's CY0 lever dosed only the ENGAGED column -- mode 24 is
      byte-stock on every build in this ladder. So the ringdown measures the DISENGAGED plant and
      **Q should show NO dose ladder.** If it does show one, our model of which column is live is
      wrong, which would be worth more than a confirmation.

METHOD
  * native 0x18F per segment (own timestamps, no zero-order hold onto the 0x14A grid)
  * narrowband 24.6-30.6 Hz around f0 -- deliberately EXCLUDES the 3f0 fold at ~17.1 Hz
  * analytic envelope via scipy.signal.hilbert
  * Q measured at MATCHED AMPLITUDE (the decay through a stated envelope band), not over a fixed
    time window, so the amplitude-dependence question cannot contaminate the cross-build contrast
  * floor from a quiet DISENGAGED stretch with no ring, on the same segment

Usage:  python studies/damping-q/r67_ringdown_q.py
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
from scipy.signal import hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
BUILDS = {
    "V76/r65": ("75604b0a432fdc89_00000065--ae43aa0f27", ROOT / "_scratch/cache/r65", "r65s",
                list(range(11))),
    "V81/r67": ("75604b0a432fdc89_00000067--9b3ebbe218", ROOT / "_scratch/cache/r67x", "r67xs",
                list(range(14))),
    "V80/r66": ("75604b0a432fdc89_00000066--276b942769", ROOT / "_scratch/cache/r66x", "r66xs",
                list(range(15))),
}
K = {"V76/r65": 1.3866, "V81/r67": 1.5798, "V80/r66": 4.1597}
F0 = 27.64
BW = 3.0
RNG = np.random.default_rng(2764)
OUT = {}


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def i16(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def native(route, seg):
    """0x18F torque and carControl.latActive on their OWN timestamps."""
    from rlog_parse import read_messages
    p = RLOGDIR / f"{route}--{seg}--rlog.zst"
    if not p.exists():
        return None
    t, q, lt, lv = [], [], [], []
    for e in read_messages(p):
        try:
            w = e.which()
        except Exception:
            continue
        tm = e.logMonoTime * 1e-9
        if w == "can":
            for m in e.can:
                if int(m.src) == 1 and int(m.address) == 0x18F:
                    d = bytes(m.dat)
                    if len(d) >= 2:
                        t.append(tm); q.append(i16(d, 0) * -1.0)
        elif w == "carControl":
            lt.append(tm); lv.append(float(bool(e.carControl.latActive)))
    if len(t) < 1000 or not lt:
        return None
    t = np.array(t); q = np.array(q)
    t0 = t[0]; t -= t0
    lat = np.interp(t, np.array(lt) - t0, np.array(lv)) > 0.5
    return t, q, lat


def envelope(t, q, fs, f0=F0, bw=BW):
    X = np.fft.rfft(q - q.mean())
    f = np.fft.rfftfreq(len(q), 1 / fs)
    X[(f < f0 - bw) | (f > f0 + bw)] = 0
    return np.abs(hilbert(np.fft.irfft(X, n=len(q))))


def edges(t, lat, fs, guard=3.0):
    """Clean latActive falling edges: engaged for `guard` s before, disengaged `guard` s after."""
    out = []
    g = int(guard * fs)
    for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
        if i - g < 0 or i + g >= len(t):
            continue
        if lat[i - g:i].mean() > 0.95 and lat[i:i + g].mean() < 0.05:
            out.append(i)
    return out


def floor_of(env, t, lat, te, fs):
    """The noise floor: quiet DISENGAGED stretches on this segment, away from the decay."""
    m = (~lat) & (t > te + 1.5)
    if m.sum() < int(1.0 * fs):
        m = (~lat) & (t > te + 1.0)
    v = env[m]
    if len(v) < 20:
        return np.nan, np.nan, np.nan, 0
    return (float(np.mean(v)), float(np.percentile(v, 95)), float(v.max()), int(len(v)))


def q_matched(t, env, te, fs, hi, lo, F):
    """Q from the decay through a MATCHED envelope band [lo, hi], floor-subtracted in power."""
    m = (t >= te) & (t <= te + 3.0)
    tt, ee = t[m] - te, env[m]
    corr = np.sqrt(np.maximum(ee ** 2 - F ** 2, 0.0))
    k = (corr <= hi) & (corr >= lo)
    if k.sum() < 8:
        return np.nan, np.nan, int(k.sum())
    sl = np.polyfit(tt[k], np.log(corr[k]), 1)[0]
    if sl >= 0:
        return np.nan, np.nan, int(k.sum())
    tau = -1.0 / sl
    return tau, tau * 2 * np.pi * F0 / 2, int(k.sum())


def main():
    hdr("Q1  IS THE AMPLITUDE-DEPENDENCE REAL, OR THE NOISE FLOOR?  route 67 seg 8, the highway edge")
    r = native(BUILDS["V81/r67"][0], 8)
    t, q, lat = r
    fs = (len(t) - 1) / (t[-1] - t[0])
    env = envelope(t, q, fs)
    te = float(t[edges(t, lat, fs)[0]])
    print(f"  fs {fs:.4f}   falling edge t = {te:.3f} s")
    print("\n  FLOOR, measured several ways (v81loop reports mean 16.3 / p95 34.4 / max 40.1):")
    for lab, m in (("t_e+1.2 .. t_e+2.4 (their window)", (t > te + 1.2) & (t < te + 2.4)),
                   ("t_e+2 .. t_e+5 (my original)", (t > te + 2) & (t < te + 5)),
                   ("all DISENGAGED frames on seg8", ~lat),
                   ("disengaged & t > t_e+1.5", (~lat) & (t > te + 1.5))):
        v = env[m]
        if len(v) < 20:
            print(f"    {lab:36s} n={len(v):5d}  -- too few")
            continue
        print(f"    {lab:36s} n={len(v):5d}  mean {np.mean(v):6.2f}  p50 {np.median(v):6.2f}  "
              f"p95 {np.percentile(v, 95):6.2f}  max {v.max():6.2f}")
    Fm, F95, Fmx, nF = floor_of(env, t, lat, te, fs)
    print(f"\n  ⇒ adopting F = {Fm:.2f} ct (mean over {nF} disengaged frames past t_e+1.5)")

    print("\n  LOCAL DECAY RATES, raw vs FLOOR-SUBTRACTED IN POWER "
          "(env_true = sqrt(env^2 - F^2)):")
    print(f"    {'interval':>16s} {'env raw':>16s} {'env corr':>16s} {'tau raw':>9s} "
          f"{'Q raw':>7s} | {'tau corr':>9s} {'Q corr':>7s}")
    bins = [(dt, float(np.median(env[(t >= te + dt) & (t < te + dt + 0.1)])))
            for dt in np.arange(0.0, 0.85, 0.1)]
    rows = []
    for (d1, v1), (d2, v2) in zip(bins[:-1], bins[1:]):
        c1 = np.sqrt(max(v1 ** 2 - Fm ** 2, 1e-9))
        c2 = np.sqrt(max(v2 ** 2 - Fm ** 2, 1e-9))
        tr = 0.1 / np.log(v1 / v2) if v1 > v2 else np.nan
        tc = 0.1 / np.log(c1 / c2) if c1 > c2 else np.nan
        rows.append((d1, d2, v1, v2, c1, c2, tr, tc))
        print(f"    {f'{d1:+.1f}->{d2:+.1f} s':>16s} {v1:7.1f} ->{v2:7.1f} {c1:7.1f} ->{c2:7.1f} "
              f"{tr:9.3f} {tr * 2 * np.pi * F0 / 2 if np.isfinite(tr) else np.nan:7.1f} | "
              f"{tc:9.3f} {tc * 2 * np.pi * F0 / 2 if np.isfinite(tc) else np.nan:7.1f}")
    valid = [r_ for r_ in rows if np.isfinite(r_[7]) and r_[4] > 3 * Fm]
    print(f"\n    intervals with corrected amplitude > 3F ({3 * Fm:.1f} ct): {len(valid)} of "
          f"{len(rows)}")
    if valid:
        qs = [r_[7] * 2 * np.pi * F0 / 2 for r_ in valid]
        print(f"    their Q over those: {[round(x, 1) for x in qs]}   "
              f"spread {max(qs) / min(qs):.2f}x")
    OUT["q1"] = dict(floor=Fm, rows=[[float(x) if x is not None else None for x in r_]
                                     for r_ in rows])

    hdr("Q2  CROSS-BUILD RINGDOWN Q, measured at MATCHED AMPLITUDE.\n"
        "    🛑 PREDICTION STATED BEFORE THE NUMBERS: the falling edge switches mode 26 -> 24, and\n"
        "    mode 24 is BYTE-STOCK on all three builds (CY0 dosed the engaged column only), so\n"
        "    this measures the DISENGAGED plant and Q should show NO dose ladder.")
    BANDS = [(300.0, 120.0, "300 -> 120 ct"), (150.0, 60.0, "150 -> 60 ct")]
    OUT["q2"] = {}
    for b, (route, cache, pfx, segs) in BUILDS.items():
        print(f"\n  ---- {b}   k = {K[b]} ----")
        found = 0
        for s in segs:
            r = native(route, s)
            if r is None:
                continue
            t, q, lat = r
            fs = (len(t) - 1) / (t[-1] - t[0])
            env = envelope(t, q, fs)
            for i in edges(t, lat, fs):
                te = float(t[i])
                pre = float(np.percentile(env[(t > te - 2) & (t < te)], 90))
                if pre < 150:
                    continue                      # nothing to ring down
                F = floor_of(env, t, lat, te, fs)[0]
                if not np.isfinite(F):
                    continue
                res = []
                for hi, lo, lab in BANDS:
                    if pre < hi:
                        res.append((lab, np.nan, np.nan, 0))
                        continue
                    tau, Q, n = q_matched(t, env, te, fs, hi, max(lo, 3 * F), F)
                    res.append((lab, tau, Q, n))
                found += 1
                print(f"    seg{s:<3d} t={te:7.2f}  pre-p90 {pre:7.1f} ct  floor {F:5.1f}  | "
                      + " | ".join(f"{lab}: tau {tau:.3f} Q {Q:5.1f} (n={n})"
                                   if np.isfinite(Q) else f"{lab}: --"
                                   for lab, tau, Q, n in res))
                OUT["q2"].setdefault(b, []).append(
                    dict(seg=s, t=te, pre=pre, floor=F,
                         bands={lab: [tau, Q, n] for lab, tau, Q, n in res}))
        if not found:
            print("    no edge with a large enough pre-edge amplitude to ring down")

    print("\n  SUMMARY -- median Q per build at each matched amplitude band:")
    print(f"    {'build':10s} {'k':>7s} " + " ".join(f"{lab:>22s}" for _, _, lab in BANDS))
    for b in BUILDS:
        row = []
        for _, _, lab in BANDS:
            v = [e["bands"][lab][1] for e in OUT["q2"].get(b, [])
                 if np.isfinite(e["bands"][lab][1] or np.nan)]
            row.append(f"{np.median(v):6.1f}  (n={len(v)})" if v else "     --      ")
        print(f"    {b:10s} {K[b]:7.4f} " + " ".join(f"{c:>22s}" for c in row))
    print("\n    ⇒ compare against the PREDICTION above: no ladder expected. A ladder here would")
    print("      mean the dosed column is still live after disengage, which would be news.")

    (ROOT / "_scratch/cache/r67x" / "r67_ringdown_q.json").write_text(
        json.dumps(OUT, indent=1, default=lambda o: None if o is None else float(o)))
    print(f"\nwrote {ROOT / '_scratch/cache/r67x' / 'r67_ringdown_q.json'}")


if __name__ == "__main__":
    main()
