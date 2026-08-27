#!/usr/bin/env python3
r"""V87 / route 71, part 2 -- close the fork properly, and find where the engaged HF shelf is made.

WHY THIS FILE EXISTS
    `probe/v87_probe_6b98.py` returned a NULL for the ~7.7 Hz line in `|gp-0x6b98|` while the SAME
    estimator found it at prominence 35.4 in the column torque.  That null is **not yet usable**,
    for one reason its own Stage 2 reported: rectification was transparent in **0 of 42** windows.
    Over a 10.28 s creep window the driver passes through centre, `gp-0x6b98` changes sign, and a
    7.79 Hz oscillation is folded to 15.58 Hz -- so "no line at 7.7 Hz in the probe" is exactly what
    a REAL line would also produce.  The null has to be re-run where `abs()` cannot fold anything.

    Stage 7 does that: it finds the longest stretches in which the command holds one sign with
    margin, scores them on the SHORTEST window that still resolves 7.79 Hz, and reports the
    transparent-only answer beside the all-windows answer.

    Stage 8 asks whether the 15-22 Hz shelf the probe shows is real or is 28 Hz folded down past
    the probe's 24.9 Hz Nyquist -- answerable because `tq` and `rate_c` run at 100 Hz.

    Stage 9 asks where the shelf comes from.  A differentiator has |H| proportional to f; a flat
    gain does not.  `e4tq` (openpilot's command on the wire) is the input, `|gp-0x6b98|` the output.

CONTROLS
    Every prominence in this file is read against the SAME white-noise floor and the SAME
    phase-randomised surrogate used in part 1, recomputed at each window length -- because the
    floor moves with `nw` and quoting part 1's floor at a different `nw` would be an error.
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
from scipy.signal import butter, filtfilt, csd, welch, coherence

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402
import _r31_common as C31        # noqa: E402
from v87_probe_6b98 import (CACHE, LSB, RATCHET, SAT_WIRE, band_stats, grid,  # noqa: E402
                            phase_randomise, block_boot, spec)

RNG = np.random.default_rng(87_44711)
OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def spec_nw(x, fs, nw):
    P = C31.periodogram(x, fs, nfft=nw, detrend=True)
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    R = G.prom_spectrum(f, P, halfwin=3.0, exclude=0.6)
    return f, P, R


def noise_floor(fs, nw, band=RATCHET, n=600):
    pr = [band_stats(*spec_nw(RNG.standard_normal(nw), fs, nw), *band) for _ in range(n)]
    v = np.array([p["prom"] for p in pr])
    return {p: float(np.percentile(v, p)) for p in (50, 95, 99)}


# =================================================================================================
# STAGE 7 -- the fork, re-run where `abs()` CANNOT fold
# =================================================================================================
def stage7(g):
    hdr("STAGE 7 -- THE FORK, RE-RUN ON RECTIFICATION-TRANSPARENT WINDOWS ONLY")
    fs = g["fs"]
    print("    A window is TRANSPARENT if the command never approaches zero inside it.  The screen")
    print("    is on the low-passed magnitude (the DC the ripple rides on), not the raw minimum:")
    print("        DC = 0-3 Hz lowpass of |cmd| ;  ripple = 6-9 Hz bandpass of |cmd|")
    print("        transparent  <=>  min(DC) > 3 x rms(ripple)  across the whole window")
    print("    ⇒ under that condition |cmd| = DC + ripple with no sign change, and the 7.79 Hz")
    print("      component survives to the spectrum unfolded.")

    b_dc = butter(2, 3.0, btype="low", fs=fs)
    b_rp = butter(2, list(RATCHET), btype="band", fs=fs)
    dc_all = filtfilt(*b_dc, g["cts"])
    rp_all = filtfilt(*b_rp, g["cts"])

    for nw in (512, 256, 128):
        sec = nw / fs
        cyc = 7.79 * sec
        fl = noise_floor(fs, nw)
        sub(f"nw={nw} ({sec:.2f} s, {fs/nw:.3f} Hz bins, {cyc:.1f} cycles of 7.79 Hz) "
            f"white-noise p95 = {fl[95]:.2f}")
        rows = {}
        for engaged in (True, False):
            mask = g["lat"] if engaged else ~g["lat"]
            recs = []
            for a, b in C31.runs_of(mask, g["t"], nw, max_gap=0.10):
                for j0 in range(0, (b - a) - nw + 1, nw // 2):
                    sl = slice(a + j0, a + j0 + nw)
                    if not np.all(np.isfinite(g["cts"][sl])):
                        continue
                    rip = float(np.std(rp_all[sl]))
                    recs.append(dict(sl=sl, blk=f"{a}:{j0 // nw}",
                                     clip=float(np.mean(g["wire"][sl] >= SAT_WIRE)),
                                     dcmin=float(dc_all[sl].min()), rip=rip,
                                     transparent=bool(dc_all[sl].min() > 3.0 * rip and rip > 0)))
            clean = [r for r in recs if r["clip"] == 0.0]
            trans = [r for r in clean if r["transparent"]]
            tag = "engaged" if engaged else "manual"
            print(f"      {tag:8s}: {len(recs):3d} windows, {len(clean):3d} unclipped, "
                  f"{len(trans):3d} ALSO transparent")
            for setname, S in (("unclipped", clean), ("transparent", trans)):
                if len(S) < 4:
                    print(f"        {setname:12s}: n={len(S)} -- too few to score")
                    continue
                out = {}
                for sig, lab in (("cts", "cmd |6b98|"), ("tq", "column tq"),
                                 ("e4tq", "op cmd")):
                    pr = [band_stats(*spec_nw(g[sig][r["sl"]], fs, nw), *RATCHET)["prom"]
                          for r in S]
                    bb = block_boot(pr, [r["blk"] for r in S], nboot=3000)
                    out[sig] = bb
                    print(f"        {setname:12s} {lab:11s} prom {bb['v']:6.2f} "
                          f"[{bb['lo']:5.2f},{bb['hi']:6.2f}]  n={bb['n']:3d}  "
                          f"above p95 in {100*np.mean(np.array(pr) > fl[95]):5.1f}%")
                sur = [band_stats(*spec_nw(phase_randomise(g["cts"][r["sl"]]), fs, nw),
                                  *RATCHET)["prom"] for r in S]
                sb = block_boot(sur, [r["blk"] for r in S], nboot=3000)
                print(f"        {setname:12s} {'SURROGATE':11s} prom {sb['v']:6.2f} "
                      f"[{sb['lo']:5.2f},{sb['hi']:6.2f}]   <- the probe's own null")
                out["surrogate"] = sb
                rows[f"{tag}/{setname}"] = out
        OUT[f"stage7_nw{nw}"] = dict(floor=fl, rows=rows)


# =================================================================================================
# STAGE 8 -- is the probe's 15-22 Hz shelf real, or 28 Hz folded past its 24.9 Hz Nyquist?
# =================================================================================================
def stage8(g):
    hdr("STAGE 8 -- ALIASING: the probe folds at 24.9 Hz; `tq`/`rate_c` do not (100 Hz)")
    z = np.load(CACHE / "r71.npz", allow_pickle=True)
    rt = np.asarray(z["t"], float)
    lat100 = np.asarray(z["cc_lat"], float) > 0.5
    fs100 = 1.0 / np.median(np.diff(rt))
    print(f"    row grid {fs100:.2f} Hz (Nyquist {fs100/2:.1f} Hz) vs probe {g['fs']:.2f} Hz "
          f"(Nyquist {g['fs']/2:.1f} Hz)")
    print("    If the probe's 15-22 Hz shelf is an alias of X Hz with X > 24.9, then on the 100 Hz")
    print("    channels the energy shows at X, and the fold maps X -> |X - 49.81| for X in "
          "(24.9, 49.8).")
    for sig in ("tq", "rate_c"):
        x = np.asarray(z[sig], float)
        for tag, m in (("engaged", lat100), ("manual", ~lat100)):
            f, P = welch(x[m] - np.mean(x[m]), fs100, nperseg=1024)
            print(f"      {sig:7s} {tag:8s} band rms:", end="")
            for lo, hi in ((6, 9), (15, 22), (24, 32), (32, 40), (40, 49)):
                bm = (f >= lo) & (f < hi)
                print(f"  {lo}-{hi}Hz {np.sqrt(np.trapezoid(P[bm], f[bm])):8.3f}", end="")
            print()
    print("\n    ⇒ read the 24-32 Hz column: if it is comparable to or larger than 15-22 Hz on the")
    print("      100 Hz channels, the probe's 15-22 Hz shelf CANNOT be separated from its alias.")
    OUT["stage8"] = "see printed table"


# =================================================================================================
# STAGE 9 -- where is the engaged HF shelf MADE?  differentiator or flat gain?
# =================================================================================================
def stage9(g):
    hdr("STAGE 9 -- THE ENGAGED HF SHELF: openpilot's command -> the delivered command")
    print("    Engagement multiplies the delivered command's band rms by (part 1, Stage 1):")
    print("        0.5-3 Hz 1.05x | 3-6 Hz 1.52x | 6-9 Hz 3.12x | 9-15 Hz 3.21x | 15-22 Hz 5.98x")
    print("    A DIFFERENTIATOR has |H| proportional to f.  A flat gain does not.  Here the")
    print("    input is `e4tq` (openpilot's LKAS command on the wire) and the output is the")
    print("    delivered `|gp-0x6b98|`, both on the probe's own 50 Hz grid.")
    fs = g["fs"]
    lat = g["lat"]
    x = g["e4tq"][lat]
    y = g["cts"][lat]
    x = x - x.mean()
    y = y - y.mean()
    f, pxx = welch(x, fs, nperseg=512)
    _, pyy = welch(y, fs, nperseg=512)
    _, pxy = csd(x, y, fs, nperseg=512)
    _, coh = coherence(x, y, fs, nperseg=512)
    H = np.abs(pxy) / np.where(pxx > 0, pxx, np.nan)
    print(f"\n    {'band':>10} {'|op cmd|':>10} {'|delivered|':>12} {'|H|=out/in':>11} "
          f"{'coh^2':>7} {'H/H(1-3Hz)':>11} {'f/f(2Hz)':>9}")
    ref = None
    for lo, hi in ((1, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 20), (20, 24)):
        m = (f >= lo) & (f < hi)
        hh = float(np.nanmean(H[m]))
        if ref is None:
            ref = hh
        fc = 0.5 * (lo + hi)
        print(f"    {lo:4d}-{hi:<5d} {np.sqrt(np.trapezoid(pxx[m], f[m])):10.3f} "
              f"{np.sqrt(np.trapezoid(pyy[m], f[m])):12.3f} {hh:11.4f} "
              f"{float(np.nanmean(coh[m])):7.3f} {hh/ref:11.2f} {fc/2.0:9.2f}")
    print("\n    ⇒ if the `H/H(1-3Hz)` column tracks the `f/f(2Hz)` column, the lane between")
    print("      openpilot's command and the motor is DIFFERENTIATING -- which is exactly what the")
    print("      r24/r26 derivative lane does, and it sits at its schedule MAXIMUM (3.000x) at creep.")

    sub("the same transfer, MANUAL -- there is no LKAS command, so this is the null shape")
    xm = g["e4tq"][~lat]
    ym = g["cts"][~lat]
    if len(xm) > 2048:
        f2, px2 = welch(xm - xm.mean(), fs, nperseg=512)
        _, py2 = welch(ym - ym.mean(), fs, nperseg=512)
        _, pc2 = csd(xm - xm.mean(), ym - ym.mean(), fs, nperseg=512)
        _, ch2 = coherence(xm - xm.mean(), ym - ym.mean(), fs, nperseg=512)
        H2 = np.abs(pc2) / np.where(px2 > 0, px2, np.nan)
        for lo, hi in ((1, 3), (3, 6), (6, 9), (9, 12), (15, 20)):
            m = (f2 >= lo) & (f2 < hi)
            print(f"      {lo:4d}-{hi:<5d}  |H| {float(np.nanmean(H2[m])):9.4f}   "
                  f"coh^2 {float(np.nanmean(ch2[m])):6.3f}")
    OUT["stage9"] = dict(f=f.tolist()[:130], H=H.tolist()[:130], coh=coh.tolist()[:130])


# =================================================================================================
# STAGE 10 -- the delivered command vs the column: episode-conditional, on the ratchet's own moments
# =================================================================================================
def stage10(g):
    hdr("STAGE 10 -- EPISODE-CONDITIONAL: on the windows where the COLUMN line is strongest,")
    print("             is there a line in the delivered command?")
    fs = g["fs"]
    nw = 256
    fl = noise_floor(fs, nw)
    recs = []
    for a, b in C31.runs_of(g["lat"], g["t"], nw, max_gap=0.10):
        for j0 in range(0, (b - a) - nw + 1, nw // 2):
            sl = slice(a + j0, a + j0 + nw)
            if not np.all(np.isfinite(g["cts"][sl])):
                continue
            tqp = band_stats(*spec_nw(g["tq"][sl], fs, nw), *RATCHET)
            cmp_ = band_stats(*spec_nw(g["cts"][sl], fs, nw), *RATCHET)
            recs.append(dict(sl=sl, blk=f"{a}:{j0//nw}", tq_prom=tqp["prom"], tq_f=tqp["f"],
                             cmd_prom=cmp_["prom"], cmd_f=cmp_["f"],
                             clip=float(np.mean(g["wire"][sl] >= SAT_WIRE))))
    clean = [r for r in recs if r["clip"] == 0.0]
    clean.sort(key=lambda r: -r["tq_prom"])
    k = max(4, len(clean) // 4)
    top, bot = clean[:k], clean[-k:]
    print(f"    {len(clean)} unclipped engaged windows at nw={nw} ({nw/fs:.2f} s); "
          f"white-noise p95 {fl[95]:.2f}")
    for tag, S in (("TOP quartile by column-torque line", top),
                   ("BOTTOM quartile by column-torque line", bot)):
        tqb = block_boot([r["tq_prom"] for r in S], [r["blk"] for r in S], nboot=3000)
        cmb = block_boot([r["cmd_prom"] for r in S], [r["blk"] for r in S], nboot=3000)
        fmatch = np.mean([abs(r["cmd_f"] - r["tq_f"]) < 0.4 for r in S])
        print(f"      {tag:40s} n={len(S):3d}")
        print(f"        column tq prom {tqb['v']:7.2f} [{tqb['lo']:6.2f},{tqb['hi']:7.2f}]")
        print(f"        delivered cmd  {cmb['v']:7.2f} [{cmb['lo']:6.2f},{cmb['hi']:7.2f}]   "
              f"argmax within 0.4 Hz of the column's: {100*fmatch:.0f}%")
    r_all = np.corrcoef([r["tq_prom"] for r in clean], [r["cmd_prom"] for r in clean])[0, 1]
    print(f"\n    per-window corr(column line prominence, command line prominence) = {r_all:+.3f}")
    print("    ⇒ a resonance DRIVEN by a broadband command predicts NO correlation and no argmax")
    print("      agreement.  A closed-loop pole predicts both.")
    OUT["stage10"] = dict(n=len(clean), corr=float(r_all))


if __name__ == "__main__":
    g = grid()
    only = sys.argv[1:] or None
    for name, fn in (("7", stage7), ("8", stage8), ("9", stage9), ("10", stage10)):
        if not only or name in only:
            fn(g)
    (CACHE / "v87_probe_fork.json").write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {CACHE / 'v87_probe_fork.json'}")
