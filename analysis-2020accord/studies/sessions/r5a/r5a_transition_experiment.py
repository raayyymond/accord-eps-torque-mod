#!/usr/bin/env python3
"""ROUTE 5a (V73) -- THE MODE-SWITCH TRANSITION WINDOW: command held FIXED, damping VARIED.

WHY THIS FILE EXISTS, AND WHAT IT FIXES ABOUT THE OBVIOUS COMPARISON
--------------------------------------------------------------------
On route 5a the damper mode is a deterministic function of `latActive`: mode 8 disengaged, mode 10
engaged, with a **1.02 s ON-delay** and a **2.08 s OFF-delay** (n=9 each, sd 4.9 ms / 0.8 ms;
residual after modelling 4 / 104,061 frames). At creep, mode 10 carries V72's lift (FactorC Y[0]=430,
FactorE Y[0]=927 => dose 389) and mode 8 is byte-stock (Y[0]=0 => dose 0).

🛑 THE WHOLE-DRIVE "mode 8 vs mode 10" CONTRAST IS **NOT** A NATURAL EXPERIMENT. Mode and engagement
are collinear at 99.9962%, so that contrast varies the LKAS command and the damping dose TOGETHER
and cannot attribute anything to either. §1 reports it only because it is the exposure-matched
version of a number already on record, and it is labelled as the manual/engaged contrast it is.

★★ THE TRANSITION WINDOWS ARE THE ACTUAL EXPERIMENT, and they are the only place in this corpus
where the two factors come apart:

    RISE arm   (1.02 s, n=9 onsets)     command ON,  damping OFF (mode 8)  ->  command ON,  damping ON
    FALL arm   (2.08 s, n=9 offsets)    command OFF, damping ON  (mode 10) ->  command OFF, damping OFF

⇒ **the FALL arm is the cleaner of the two**: the LKAS command is off on BOTH sides, so only the
damping changes. The RISE arm has the authority ramp running through it -- the command is not merely
present but GROWING -- so it is confounded by construction and its command is measured and reported
alongside every amplitude, never assumed matched.

🛑 POWER, STATED UP FRONT RATHER THAN DISCOVERED AT THE END.
  · Each RISE pre-window is **102 frames = 1.02 s**. NFFT 256 (2.56 s) is the kit's standard and
    **does not fit**. No Welch/periodogram estimate is possible on this arm at the standard
    resolution, so every amplitude here is the ANALYTIC BAND ENVELOPE, computed on the whole segment
    and sliced -- the same `band_envelope` the ratchet inventory uses for its p99.
  · n = 9 pairs. A paired sign test bottoms out at **2 * 0.5^9 = 0.0039**, so the design CAN reach
    significance, but ONLY if all 9 pairs move the same way. Anything less is not powered, and
    "not powered" is reported as the result rather than dressed up as a trend.
  · EPISODES ARE ONSETS. The bootstrap unit is the transition, n=9, not the frame and not the
    window. A frame bootstrap here would shrink the CI by ~sqrt(102) and manufacture significance.

⚠ FILTER SMEARING AT THE STEP. A 6-9 Hz band-pass has ~1/(3 Hz) = 0.33 s of time smearing and an
18-22 Hz one ~0.25 s, so the envelope within ~0.3 s of the mode switch mixes both sides. Every
statistic is therefore computed BOTH on the full window and on a version trimmed by 30 frames
(0.30 s) at the boundary. If the two disagree the result is smearing, not physics, and it is
reported as such.

Engagement is `cc_lat` (carControl.latActive). fs from `_r4f_lib.fs_lattice`, never 1/median(dt).
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
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C                                              # noqa: E402
from _r31_common import band_envelope, sustained                     # noqa: E402
import _r4f_lib as R4F                                              # noqa: E402
from scipy.stats import wilcoxon, binomtest                          # noqa: E402

CACHE, PFX, SEGS = ROOT / "_scratch/cache/r5a", "r5as", list(range(18))
GRIND = (18.0, 22.0)
RATCH = (6.0, 9.0)
RISE_N, FALL_N = 102, 208        # frames @100 Hz -- the MEASURED lags, 1.02 s / 2.08 s
TRIM = 30                        # 0.30 s, >= the 6-9 Hz band-pass smearing time
RNG = np.random.default_rng(20260805)


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112)


def p99(x):
    return float(np.percentile(x, 99)) if len(x) else np.nan


PAIRS = {"rise": [], "fall": []}
for s in SEGS:
    d = C.load(s, CACHE, PFX)
    fs = R4F.fs_lattice(d)
    tq = np.asarray(d["tq"], float)
    eg = band_envelope(tq, fs, *GRIND)
    er = band_envelope(tq, fs, *RATCH)
    eff = np.abs(sustained(tq, fs))
    lat = np.asarray(d["cc_lat"], float) > 0.5
    mode = np.asarray(d["mode"], float)
    v = np.abs(np.asarray(d["cs_v"], float))
    ang = np.asarray(d["ang"], float)
    req = np.abs(np.asarray(d["cc_req"], float))
    e4 = np.abs(np.asarray(d["e4tq"], float))
    n = len(tq)
    for i in np.nonzero(np.diff(lat.astype(int)) != 0)[0]:
        up = bool(lat[i + 1])
        L = RISE_N if up else FALL_N
        a0, a1, b0, b1 = i + 1, i + 1 + L, i + 1 + L, i + 1 + 2 * L
        if b1 > n:
            continue
        # the pre window must be PURE in the OLD mode and the post window PURE in the NEW one,
        # or the pair is not the contrast it claims to be.
        pre_m, post_m = mode[a0:a1], mode[b0:b1]
        want_pre, want_post = (8.0, 10.0) if up else (10.0, 8.0)
        if not ((pre_m == want_pre).all() and (post_m == want_post).all()):
            continue
        rec = dict(seg=s, i=int(i), up=up)
        for tag, sl in (("pre", slice(a0, a1)), ("post", slice(b0, b1))):
            t0, t1 = sl.start, sl.stop
            tr = slice(t0 + (TRIM if tag == "post" else 0), t1 - (TRIM if tag == "pre" else 0))
            rec[tag] = dict(g=p99(eg[sl]), r=p99(er[sl]),
                            g_t=p99(eg[tr]), r_t=p99(er[tr]),
                            v=float(v[sl].mean()), ang=float(np.abs(ang[sl]).mean()),
                            eff=float(np.median(eff[sl])),
                            req=float(np.nanmean(req[sl])), e4=float(np.nanmean(e4[sl])))
        PAIRS["rise" if up else "fall"].append(rec)

hdr("§0  THE PAIRS, AND WHETHER THE COMMAND IS ACTUALLY HELD FIXED")
for arm in ("rise", "fall"):
    P = PAIRS[arm]
    L = RISE_N if arm == "rise" else FALL_N
    print(f"\n  {arm.upper()} arm: n = {len(P)} transitions, {L} frames ({L / 100:.2f} s) per window, "
          f"{2 * len(P) * L / 100:.1f} s total")
    if not P:
        print("     🛑 EMPTY -- UNPOWERED, not a null")
        continue
    for k, lbl in (("req", "openpilot cmd |actuators.torque|"), ("e4", "0xE4 |cmd| (sendcan src1)"),
                   ("eff", "driver effort |lowpass(tq,3Hz)|"), ("v", "speed m/s"),
                   ("ang", "|angle| deg")):
        a = np.array([p["pre"][k] for p in P]); b = np.array([p["post"][k] for p in P])
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 3:
            print(f"     {lbl:34s} : insufficient finite values")
            continue
        try:
            pw = wilcoxon(a[ok], b[ok]).pvalue
        except Exception:
            pw = np.nan
        print(f"     {lbl:34s} : pre {np.median(a[ok]):9.2f}  post {np.median(b[ok]):9.2f}  "
              f"ratio {np.median(b[ok]) / max(np.median(a[ok]), 1e-9):6.3f}  Wilcoxon p={pw:.3f}")
print("\n  ⇒ READ THIS BEFORE §1: the FALL arm is the experiment (command off both sides). On the")
print("    RISE arm the command is RAMPING, so any pre/post amplitude change is confounded with it.")

hdr("§1  THE CONTRAST -- 18-22 Hz (grind #1) and 6-9 Hz (ratchet), paired by transition")
for arm in ("rise", "fall"):
    P = PAIRS[arm]
    if not P:
        continue
    what = ("command ON:  damping OFF -> ON" if arm == "rise"
            else "command OFF: damping ON -> OFF")
    print(f"\n  {arm.upper()} arm ({what}), n = {len(P)}")
    for key, tkey, lbl in (("g", "g_t", "18-22 Hz"), ("r", "r_t", " 6-9 Hz")):
        for kk, sub in ((key, "full   "), (tkey, f"trim{TRIM}")):
            a = np.array([p["pre"][kk] for p in P]); b = np.array([p["post"][kk] for p in P])
            ok = np.isfinite(a) & np.isfinite(b)
            a, b = a[ok], b[ok]
            if len(a) < 3:
                print(f"     {lbl} {sub}: too few finite pairs -- UNPOWERED")
                continue
            # ratio point estimate + bootstrap over ONSETS (the episode here IS the transition)
            draws = np.empty(4000)
            for j in range(4000):
                k = RNG.integers(0, len(a), len(a))
                draws[j] = np.median(b[k]) / max(np.median(a[k]), 1e-9)
            lo, hi = np.percentile(draws, [2.5, 97.5])
            nup = int((b > a).sum())
            sg = binomtest(nup, len(a), 0.5).pvalue
            try:
                pw = wilcoxon(a, b).pvalue
            except Exception:
                pw = np.nan
            print(f"     {lbl} {sub}: pre {np.median(a):8.1f}  post {np.median(b):8.1f}  "
                  f"post/pre {np.median(b) / max(np.median(a), 1e-9):6.3f} "
                  f"[{lo:.3f}, {hi:.3f}] | {nup}/{len(a)} up  sign p={sg:.4f}  Wilcoxon p={pw:.4f}")

hdr("§2  POWER -- what this design could have detected, computed BEFORE reading the p-values")
for arm in ("rise", "fall"):
    P = PAIRS[arm]
    if not P:
        continue
    n = len(P)
    print(f"  {arm.upper()} arm, n = {n} transitions:")
    print(f"     paired sign test floor  = 2 * 0.5^{n} = {2 * 0.5 ** n:.4f}  "
          f"⇒ significance requires ALL {n} pairs to move the same way")
    for key, lbl in (("g", "18-22 Hz"), ("r", " 6-9 Hz")):
        a = np.array([p["pre"][key] for p in P]); b = np.array([p["post"][key] for p in P])
        lr = np.log(np.maximum(b, 1e-9) / np.maximum(a, 1e-9))
        lr = lr[np.isfinite(lr)]
        if len(lr) < 3:
            continue
        sd = lr.std(ddof=1)
        # MDE at 80% power, paired t, two-sided 0.05
        mde = float(np.exp(2.9 * sd / np.sqrt(len(lr))))
        print(f"     {lbl}: sd(log ratio) = {sd:.3f} over {len(lr)} pairs "
              f"⇒ MDE at 80% power ≈ **{mde:.2f}x** (or 1/{mde:.2f})")
print("\n  ⇒ Any true effect SMALLER than the MDE cannot be seen here regardless of the p-value.")
