#!/usr/bin/env python3
"""V62 route-37: characterise the NEW grinding (manual turning + LKAS engaged, ~10-20 mph).

Built on `_r31_common` primitives (periodogram / peak_prom / q_of / runs_of / band_envelope /
sustained). The one convention deliberately NOT inherited is `BAND = (18,26)`:

  🛑 The peak is located FREELY over 5-48 Hz, on the PROMINENCE spectrum. V61 taught that a strict band pins the argmax to the
     band edge and reports sd=0 on what is actually broadband floor. Strict bands PRESENCE-TEST a
     known f0; they cannot LOCATE one. Fixed bands are still evaluated in parallel, but only as
     named presence tests, never as the locator.

Nyquist is ~50.2-50.7 Hz (fs 100.3-101.4 Hz per segment), so nothing above ~45 Hz is trustworthy
and anything reported near 40-50 Hz carries an alias caveat.

Subcommands:  zoom | sweep | corr | coh | order | all
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
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402

C.CACHE = C.ROOT / "_scratch/cache/r37"
PFX = "r37s"
SEGS = list(range(1, 15))           # seg 0 is a stale 07:05 boot -- EXCLUDED

NFFT = 256
# 🛑 The locator band is 5-48 Hz, NOT the 10-45 Hz first tried. With a 10 Hz lower edge, 17.7% of
# engaged windows put their argmax within 0.5 Hz of that edge, and the "new-symptom" cell reported a
# spurious 12.68 Hz cluster that DISSOLVES (median 7.47, sd 10.9) once the edge moves to 5 Hz. Same
# failure mode as V61's 18 Hz edge; the fix is a band wide enough that the argmax is interior.
FREE = (5.0, 48.0)                  # the free locator band
B_MODE = (18.0, 26.0)               # legacy 21 Hz grinding band (presence test only)
B_RATCHET = (6.0, 9.0)              # the ratchet band
B_HI = (26.0, 45.0)                 # "did V62's doubled lead create a HIGHER mode?"
B_LOW = (10.0, 18.0)                # between ratchet-2nd-harmonic and the old mode

_CACHE = {}


def prom_spectrum(f, P, halfwin=6.0, exclude=1.5):
    """P divided by its own LOCAL median floor -- the prominence at every bin, not just the argmax.

    🛑 This is the locator, and it exists because a raw-power argmax cannot work on this channel.
    `tq` carries the driver's own steering input at 1-3 Hz at amplitudes 10-100x any mode, so
    argmax(P) lands on the driver (or, with a band floor above him, on the band edge -- 17.7% of
    windows pinned at a 10 Hz edge and still 18.9% at a 5 Hz edge). Dividing by the local floor
    removes the 1/f tilt, so a genuine narrow line wins on SHAPE rather than on absolute power.
    """
    R = np.full(len(P), np.nan)
    for j in range(1, len(P) - 1):
        near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
        if near.sum() < 5:
            continue
        fl = float(np.median(P[near]))
        if fl > 0:
            R[j] = P[j] / fl
    return R


def locate(f, P, lo, hi, halfwin=6.0, exclude=1.5):
    """(f0, prominence) of the most PROMINENT line in [lo,hi] -- argmax of the prominence
    spectrum, sub-bin refined in log power. Returns (nan, nan) if no interior candidate."""
    R = prom_spectrum(f, P, halfwin, exclude)
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, R, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), float(R[j])
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(f[j] + np.clip(delta, -0.5, 0.5) * (f[1] - f[0])), float(R[j])


def seg(s):
    if s not in _CACHE:
        _CACHE[s] = C.load(s, C.CACHE, PFX)
    return _CACHE[s]


def wall(d, t):
    return time.strftime("%H:%M:%S", time.localtime(float(d["wall_t0"][0]) + t))


def specrec(d, a, b, nfft=NFFT, hop=None, chan="tq"):
    """Per-window records over [a,b) of ONE contiguous run. No splicing: caller guarantees it.

    Frequency is located FREELY in FREE; the fixed bands are reported alongside as presence tests.
    """
    fs = C.fs_of(d)
    hop = hop or nfft
    x = np.asarray(d[chan][a:b], float)
    if len(x) < nfft:
        return []
    f = np.fft.rfftfreq(nfft, 1 / fs)
    envs = {k: C.band_envelope(x, fs, *bd) for k, bd in
            (("mode", B_MODE), ("rat", B_RATCHET), ("hi", B_HI), ("low", B_LOW), ("free", FREE))}
    out = []
    for i in range(0, len(x) - nfft + 1, hop):
        P = C.periodogram(x[i:i + nfft], fs, nfft)
        if P is None:
            continue
        sl = slice(a + i, a + i + nfft)
        r = dict(seg=None, t0=float(d["t"][a + i]), i0=a + i)
        r["f0"], r["prom"] = locate(f, P, *FREE)
        r["Q"] = C.q_of(f, P, r["f0"]) if np.isfinite(r["f0"]) else np.nan
        for nm, bd in (("m", B_MODE), ("r", B_RATCHET), ("h", B_HI), ("l", B_LOW)):
            r[f"f0{nm}"], r[f"pr{nm}"] = locate(f, P, *bd)
        for k, e in envs.items():
            r["env_" + k] = float(np.percentile(e[i:i + nfft], 99))
        r["v"] = float(np.mean(d["cs_v"][sl]))
        r["vsd"] = float(np.std(d["cs_v"][sl]))
        r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
        r["eff"] = float(np.mean(np.abs(C.sustained(d["tq"][sl], fs))))
        r["e4"] = float(np.mean(np.abs(d["e4tq"][sl])))
        r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
        r["press"] = float(np.mean(d["cs_press"][sl] > 0.5))
        r["sstat4"] = int((d["sstat"][sl] == 4).sum())
        r["tqp99"] = float(np.percentile(np.abs(d["tq"][sl]), 99))
        out.append(r)
    return out


def records(s, mask=None, hop=NFFT):
    """All windows of segment `s` inside contiguous runs of `mask` (default: everything)."""
    d = seg(s)
    m = np.ones(len(d["t"]), bool) if mask is None else np.asarray(mask, bool)
    out = []
    for a, b in C.runs_of(m, d["t"], NFFT):
        for r in specrec(d, a, b, hop=hop):
            r["seg"] = s
            out.append(r)
    return out


def col(recs, k):
    return np.array([r[k] for r in recs], float)


def med(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    return np.median(v) if len(v) else np.nan


def sd(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    return v.std(ddof=1) if len(v) > 1 else np.nan


# ==============================================================================================
# 1. ZOOM: the two operator-remembered instances
# ==============================================================================================
def cmd_zoom():
    for s, tc, label in ((1, 10.0, "operator 10:12:15"), (12, 19.0, "operator 10:23:24")):
        d = seg(s)
        fs = C.fs_of(d)
        lo, hi = tc - 10.0, tc + 10.0
        m = (d["t"] >= lo) & (d["t"] <= hi)
        a, b = int(np.flatnonzero(m)[0]), int(np.flatnonzero(m)[-1]) + 1
        print(f"\n{'='*118}\nSEG {s}  {label}  t {lo:.1f}..{hi:.1f} s "
              f"({wall(d, lo)}..{wall(d, hi)})  fs={fs:.2f}  Nyq={fs/2:.1f}  n={b-a}")
        print(f"{'='*118}")
        print("  t0    wall      | FREE 5-48Hz (prom-spectrum) | 18-26        | 6-9          "
              "| 26-45        | envp99 free/mode/rat/hi | vEgo  |ang|  eff   e4    lat  prs")
        for r in specrec(d, a, b, hop=64):
            print(f"{r['t0']:6.2f} {wall(d, r['t0'])} | "
                  f"{r['f0']:6.2f} Hz p={r['prom']:6.2f} Q={r['Q']:5.1f} | "
                  f"{r['f0m']:5.2f} p={r['prm']:5.2f} | "
                  f"{r['f0r']:5.2f} p={r['prr']:5.2f} | "
                  f"{r['f0h']:5.2f} p={r['prh']:5.2f} | "
                  f"{r['env_free']:6.1f} {r['env_mode']:5.1f} {r['env_rat']:5.1f} "
                  f"{r['env_hi']:5.1f} | "
                  f"{r['v']:5.2f} {r['ang']:6.1f} {r['eff']:6.0f} {r['e4']:5.0f} "
                  f"{r['lat']:4.2f} {r['press']:4.2f}")
        # summary of the zoom
        rs = specrec(d, a, b, hop=64)
        print(f"  -- free f0: median {med(col(rs,'f0')):.2f} Hz  sd {sd(col(rs,'f0')):.2f}  "
              f"n={len(rs)}   prom median {med(col(rs,'prom')):.2f} p90 "
              f"{np.percentile(col(rs,'prom'),90):.2f}")
        # where does the free argmax LAND, as a histogram over 5 Hz bins
        h, e = np.histogram(col(rs, "f0"), bins=np.arange(10, 47.5, 2.5))
        print("  -- free-argmax histogram (2.5 Hz bins): " +
              " ".join(f"{e[i]:.0f}-{e[i+1]:.0f}:{h[i]}" for i in range(len(h)) if h[i]))


# ==============================================================================================
# 2. SWEEP: all segments, binned by (speed x effort x latActive)
# ==============================================================================================
CELLS = [
    ("ENG 3.5-10 m/s  eff>=800   << NEW-SYMPTOM REGIME", 1, (3.5, 10.0), (800, 1e9)),
    ("ENG 3.5-10 m/s  eff<300    (same speed, light)  ", 1, (3.5, 10.0), (0, 300)),
    ("ENG 3.5-10 m/s  eff 300-800                     ", 1, (3.5, 10.0), (300, 800)),
    ("ENG 1-4 m/s     any eff    (OLD creep regime)   ", 1, (1.0, 4.0), (0, 1e9)),
    ("ENG 1-4 m/s     eff>=800                        ", 1, (1.0, 4.0), (800, 1e9)),
    ("ENG >14 m/s     any eff                         ", 1, (14.0, 99.0), (0, 1e9)),
    ("ENG >14 m/s     eff>=800                        ", 1, (14.0, 99.0), (800, 1e9)),
    ("ENG 10-14 m/s   any eff                         ", 1, (10.0, 14.0), (0, 1e9)),
    ("MAN 3.5-10 m/s  eff>=800   (matched, disengaged)", 0, (3.5, 10.0), (800, 1e9)),
    ("MAN 3.5-10 m/s  any eff                         ", 0, (3.5, 10.0), (0, 1e9)),
    ("MAN 1-4 m/s     any eff                         ", 0, (1.0, 4.0), (0, 1e9)),
    ("MAN >14 m/s     any eff                         ", 0, (14.0, 99.0), (0, 1e9)),
]


def build_all(hop=NFFT):
    """Window records over every segment, split by engagement, with the mask applied BEFORE
    windowing so a window never straddles an engagement transition (convention 5)."""
    eng, man = [], []
    for s in SEGS:
        d = seg(s)
        le = d["cc_lat"] > 0.5
        eng += records(s, le, hop=hop)
        man += records(s, ~le, hop=hop)
    for r in eng:
        r["eng"] = 1
    for r in man:
        r["eng"] = 0
    return eng + man


def cmd_sweep(hop=NFFT):
    allr = build_all(hop)
    print(f"total windows (NFFT={NFFT}, hop={hop}, segs 1-14, engagement-split): {len(allr)}")
    print(f"\n{'cell':52s} {'n':>4s} | {'f0 med':>7s} {'f0 sd':>6s} | {'prom med':>8s} "
          f"{'p90':>7s} | {'env99 free':>10s} {'mode':>7s} {'rat':>7s} {'hi':>7s} | "
          f"{'18-26 prom':>10s} {'26-45 prom':>10s} {'6-9 prom':>8s} | {'v':>5s} {'ang':>6s} "
          f"{'eff':>6s}")
    for name, e, (vlo, vhi), (elo, ehi) in CELLS:
        rs = [r for r in allr if r["eng"] == e and vlo <= r["v"] < vhi and elo <= r["eff"] < ehi]
        if not rs:
            print(f"{name:52s} {0:4d} | (empty)")
            continue
        p = col(rs, "prom")
        print(f"{name:52s} {len(rs):4d} | {med(col(rs,'f0')):7.2f} {sd(col(rs,'f0')):6.2f} | "
              f"{med(p):8.2f} {np.percentile(p[np.isfinite(p)],90):7.2f} | "
              f"{med(col(rs,'env_free')):10.1f} {med(col(rs,'env_mode')):7.1f} "
              f"{med(col(rs,'env_rat')):7.1f} {med(col(rs,'env_hi')):7.1f} | "
              f"{med(col(rs,'prm')):10.2f} {med(col(rs,'prh')):10.2f} "
              f"{med(col(rs,'prr')):8.2f} | {med(col(rs,'v')):5.2f} {med(col(rs,'ang')):6.1f} "
              f"{med(col(rs,'eff')):6.0f}")

    # --- the new-symptom cell, resolved by segment and by free-argmax histogram --------------
    key = [r for r in allr if r["eng"] == 1 and 3.5 <= r["v"] < 10.0 and r["eff"] >= 800]
    print(f"\nNEW-SYMPTOM CELL (engaged, 3.5-10 m/s, eff>=800): n={len(key)}")
    h, e = np.histogram(col(key, "f0"), bins=np.arange(FREE[0], FREE[1] + 2.5, 2.5))
    print("  free-argmax histogram (2.5 Hz bins): " +
          "  ".join(f"{e[i]:.1f}-{e[i+1]:.1f}:{h[i]}" for i in range(len(h)) if h[i]))
    edge = float(np.mean(col(key, "f0") < FREE[0] + 0.5))
    print(f"  band-edge pinning check: {100*edge:.1f}% of argmaxes within 0.5 Hz of the "
          f"{FREE[0]:.0f} Hz edge (>10% means the band is still too narrow)")
    print("  per-segment:")
    print("   seg   n   f0 med   f0 sd   prom med  prom p90  env99 free  mode   rat    hi    "
          "v med  ang med  eff med")
    for s in SEGS:
        rs = [r for r in key if r["seg"] == s]
        if not rs:
            continue
        p = col(rs, "prom")
        print(f"   {s:3d} {len(rs):4d} {med(col(rs,'f0')):8.2f} {sd(col(rs,'f0')):7.2f} "
              f"{med(p):10.2f} {np.percentile(p[np.isfinite(p)],90):9.2f} "
              f"{med(col(rs,'env_free')):11.1f} {med(col(rs,'env_mode')):6.1f} "
              f"{med(col(rs,'env_rat')):6.1f} {med(col(rs,'env_hi')):6.1f} "
              f"{med(col(rs,'v')):6.2f} {med(col(rs,'ang')):8.1f} {med(col(rs,'eff')):8.0f}")

    # --- top-prominence windows anywhere in the route ----------------------------------------
    fin = [r for r in allr if np.isfinite(r["prom"])]
    fin.sort(key=lambda r: -r["prom"])
    print("\nTOP-30 windows by FREE prominence over the whole route:")
    print("   seg  t0    wall      f0     prom    Q    18-26  26-45  6-9   env99   v     |ang|"
          "   eff    e4   lat")
    for r in fin[:30]:
        d = seg(r["seg"])
        print(f"   {r['seg']:3d} {r['t0']:6.2f} {wall(d, r['t0'])} {r['f0']:6.2f} "
              f"{r['prom']:7.2f} {r['Q']:5.1f} {r['prm']:6.2f} {r['prh']:6.2f} {r['prr']:5.2f} "
              f"{r['env_free']:7.1f} {r['v']:5.2f} {r['ang']:6.1f} {r['eff']:6.0f} "
              f"{r['e4']:5.0f} {r['lat']:4.2f}")
    return allr


# ==============================================================================================
# 3. CORRELATIONS
# ==============================================================================================
def cmd_corr(allr=None):
    allr = allr or build_all()
    for lbl, subset in (("ENGAGED, all speeds", [r for r in allr if r["eng"] == 1]),
                        ("ENGAGED, 3.5-10 m/s",
                         [r for r in allr if r["eng"] == 1 and 3.5 <= r["v"] < 10.0]),
                        ("MANUAL, all speeds", [r for r in allr if r["eng"] == 0])):
        print(f"\n{lbl}: n={len(subset)}")
        print(f"  {'response':12s} " + "".join(f"{k:>18s}" for k in
                                               ("vEgo", "|ang|", "eff", "e4tq")))
        for resp in ("prom", "env_free", "env_mode", "env_hi", "env_rat", "f0"):
            y = col(subset, resp)
            row = f"  {resp:12s} "
            for k in ("v", "ang", "eff", "e4"):
                x = col(subset, k)
                m = np.isfinite(x) & np.isfinite(y)
                if m.sum() < 8:
                    row += f"{'n/a':>18s}"
                    continue
                rho, p = spearmanr(x[m], y[m])
                star = "*" if p < 0.001 else (" " if p < 0.05 else "~")
                row += f"{rho:+8.3f}{star}n={m.sum():<7d}"
            print(row)
    print("\n  * p<0.001   (blank) p<0.05   ~ not significant at 0.05")


# ==============================================================================================
# 4. COHERENCE with the NATIVE 0xE4 command grid
# ==============================================================================================
def cmd_coh():
    """Coherence(openpilot command, torsion bar) on the native 0xE4 arrival grid.

    e4hist columns: (t, torque, req, byte2). 0xE4 is sendcan src 1 (src==129), ~50 Hz, so its own
    Nyquist is ~25 Hz -- state that before reading anything at 21 Hz as "in the command".
    """
    print("Native 0xE4 grid coherence with the torsion-bar channel.")
    for s in (1, 2, 3, 12, 4, 5):
        d = seg(s)
        e4 = d["e4hist"]
        if not len(e4):
            print(f"  seg{s}: no 0xE4 frames")
            continue
        te, xe = e4[:, 0], e4[:, 1]
        fse = 1.0 / np.median(np.diff(te))
        # resample the BAR onto the e4 arrival grid (the bar is the faster channel at ~100 Hz)
        xb = np.interp(te, d["t"], d["tq"])
        le = np.interp(te, d["t"], d["cc_lat"]) > 0.5
        vv = np.interp(te, d["t"], d["cs_v"])
        m = le & (vv >= 3.5) & (vv < 10.0)
        nf = 128
        Sxx = Syy = np.zeros(nf // 2 + 1)
        Sxy = np.zeros(nf // 2 + 1, complex)
        K = 0
        for a, b in C.runs_of(m, te, nf, max_gap=0.10):
            for i in range(0, (b - a) - nf + 1, nf // 2):
                u = xe[a + i:a + i + nf] - xe[a + i:a + i + nf].mean()
                v = xb[a + i:a + i + nf] - xb[a + i:a + i + nf].mean()
                w = np.hanning(nf)
                U, V = np.fft.rfft(u * w), np.fft.rfft(v * w)
                Sxx = Sxx + np.abs(U) ** 2
                Syy = Syy + np.abs(V) ** 2
                Sxy = Sxy + U * np.conj(V)
                K += 1
        if K < 3:
            print(f"  seg{s}: K={K} -- too few windows")
            continue
        f = np.fft.rfftfreq(nf, 1 / fse)
        coh = np.abs(Sxy) ** 2 / (Sxx * Syy + 1e-300)
        null95 = 1 - 0.05 ** (1 / (K - 1))       # 95% null for magnitude-squared coherence
        print(f"  seg{s}: fs_e4={fse:.2f} Hz (Nyq {fse/2:.1f})  K={K}  null95={null95:.3f}  "
              f"(engaged, 3.5-10 m/s)")
        for lo, hi in ((5, 10), (10, 15), (15, 18), (18, 22), (22, 25)):
            mm = (f >= lo) & (f < hi)
            if mm.any():
                j = int(np.argmax(np.where(mm, coh, -1)))
                print(f"      {lo:2d}-{hi:2d} Hz: max coh {coh[j]:.3f} @ {f[j]:5.2f} Hz  "
                      f"{'ABOVE' if coh[j] > null95 else 'below'} null")


# ==============================================================================================
# 5. ORDER TRACKING -- is the line the road (speed-proportional) or the firmware (fixed)?
# ==============================================================================================
def cmd_order(allr=None):
    """Wheel order 1 is f = v / circumference; the kit's measured circumference is 2.073-2.090 m,
    so order 1 ~= 0.482*v .. 0.483*v. A line at a fixed ORDER is the road; a line at a fixed
    HERTZ is the firmware."""
    allr = allr or build_all()
    CIRC = 2.080
    key = [r for r in allr if r["eng"] == 1 and 3.5 <= r["v"] < 10.0 and r["eff"] >= 800]
    print(f"Order-tracking the NEW-SYMPTOM cell (n={len(key)}), circumference {CIRC} m.")
    ordv = np.array([r["f0"] * CIRC / max(r["v"], 1e-6) for r in key])
    print(f"  free f0 : median {med(col(key,'f0')):.2f} Hz  sd {sd(col(key,'f0')):.2f}  "
          f"IQR {np.percentile(col(key,'f0'),25):.2f}-{np.percentile(col(key,'f0'),75):.2f}")
    print(f"  order   : median {med(ordv):.2f}      sd {sd(ordv):.2f}  "
          f"IQR {np.percentile(ordv,25):.2f}-{np.percentile(ordv,75):.2f}")
    print("  => the SMALLER relative scatter identifies the domain the line is fixed in.")
    cv_f = sd(col(key, "f0")) / med(col(key, "f0"))
    cv_o = sd(ordv) / med(ordv)
    print(f"  CV(hertz)={cv_f:.3f}   CV(order)={cv_o:.3f}  -> "
          f"{'FIXED IN HERTZ (firmware/structure)' if cv_f < cv_o else 'FIXED IN ORDER (road/tyre)'}")

    # speed-resolved f0
    print("\n  f0 vs speed, engaged, eff>=800, all speeds:")
    ks = [r for r in allr if r["eng"] == 1 and r["eff"] >= 800]
    print("    v bin      n   f0 med   f0 sd   prom med   env99  |  order-1 f (0.481*v)")
    for lo, hi in ((0, 2), (2, 3.5), (3.5, 5), (5, 7), (7, 10), (10, 14), (14, 20), (20, 30)):
        rs = [r for r in ks if lo <= r["v"] < hi]
        if not rs:
            continue
        print(f"    {lo:4.1f}-{hi:4.1f} {len(rs):4d} {med(col(rs,'f0')):8.2f} "
              f"{sd(col(rs,'f0')):7.2f} {med(col(rs,'prom')):10.2f} "
              f"{med(col(rs,'env_free')):7.1f}  |  {0.481*med(col(rs,'v')):6.2f}")

    # ratchet-harmonic guard: if the free argmax lands in 12-18 Hz, is the 6-9 Hz fundamental
    # actually present and stronger?
    harm = [r for r in key if 12.0 <= r["f0"] < 18.0]
    print(f"\n  RATCHET-2ND-HARMONIC GUARD: windows with free f0 in 12-18 Hz: n={len(harm)}"
          f" of {len(key)}")
    if harm:
        strong = sum(1 for r in harm if np.isfinite(r["prr"]) and r["prr"] >= r["prom"])
        print(f"    of those, the 6-9 Hz fundamental is at least as prominent in {strong}/"
              f"{len(harm)} -- a 'harmonic' stronger than its fundamental is not a harmonic.")
        print(f"    median f0 in-band {med(col(harm,'f0')):.2f} Hz; median 6-9 f0 "
              f"{med(col(harm,'f0r')):.2f} Hz (2x = {2*med(col(harm,'f0r')):.2f} Hz)")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    hop = int(sys.argv[2]) if len(sys.argv) > 2 else NFFT
    if cmd in ("zoom", "all"):
        cmd_zoom()
    allr = None
    if cmd in ("sweep", "all"):
        print("\n" + "=" * 118 + f"\nSYSTEMATIC SWEEP (hop={hop})\n" + "=" * 118)
        allr = cmd_sweep(hop)
    if cmd in ("corr", "all"):
        print("\n" + "=" * 118 + "\nRANK CORRELATIONS (Spearman)\n" + "=" * 118)
        cmd_corr(allr)
    if cmd in ("coh", "all"):
        print("\n" + "=" * 118 + "\nCOHERENCE, NATIVE 0xE4 GRID\n" + "=" * 118)
        cmd_coh()
    if cmd in ("order", "all"):
        print("\n" + "=" * 118 + "\nORDER TRACKING\n" + "=" * 118)
        cmd_order(allr)


if __name__ == "__main__":
    main()
