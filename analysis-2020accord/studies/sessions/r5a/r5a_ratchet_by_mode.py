#!/usr/bin/env python3
"""ROUTE 5a (V73) -- DOES THE ~7.79 Hz RATCHET APPEAR IN MODE 8 AS WELL AS MODE 10?

🛑🛑 READ THIS BEFORE READING ANY NUMBER BELOW -- THE CONTRAST IS CONFOUNDED BY CONSTRUCTION.
On route 5a the damper mode is a DETERMINISTIC FUNCTION of `carControl.latActive`: mode 8 while
disengaged, mode 10 while engaged, with a 1.02 s ON-delay and a 2.08 s OFF-delay. After modelling
that asymmetric delay the two agree on 104,057 / 104,061 frames (99.9962%); the 4 residuals are
single-frame edge quantisation. ⇒ **"mode 8 vs mode 10" IS "manual vs engaged" on this route.**
Any difference measured here is the engaged/manual difference already on record (44/46 engaged,
p = 4.6e-5) and CANNOT be attributed to the damper mode, the FactorC/E records, or V72's lift.
The two factors are not separately identifiable from this drive. Reported as such, not smoothed.

WHAT THIS FILE CAN STILL ANSWER, and why it is worth running: the operator's physical question --
does the micro-ratchet occur at all in the state where creep damping is EXACTLY ZERO (mode 8 is
byte-stock: FactorC 0xD17D0 = [0,950,1356,1606,0], FactorE 0xD180C = [0,115,177,253,0], Y[0]=0)
and where V72's lift (dose 389) never applied? Presence in mode 8 constrains the mechanism whether
or not the mode is the cause.

INSTRUMENT is `studies/sessions/r59/r59_ratchet_vs_history.py`'s `scan`, ported VERBATIM in every numeric respect:
6-9 Hz analytic-envelope p99, AMP_MIN = 600 counts envelope = 1200 p-p, prominence argmax over a
FREE 5-12 Hz range, fs from `_r4f_lib.fs_lattice`, engagement `cc_lat`, hands-off
sustained |lowpass(tq,3 Hz)| <= 300, NFFT 256 non-overlapping. The ONLY addition is the per-window
mode tag. Keeping the estimator byte-identical is the point: the route-5a numbers land on the same
axis as every route in `_scratch/out/_r59_ratchet_hist.json`.

🛑 EPISODES, NOT WINDOWS. Every CI resamples EPISODES (contiguous window runs inside one segment).
A window bootstrap shrinks CIs by ~sqrt(n_per_episode) and manufactures significance.
🛑 SPLIT-HALF NULL FIRST. No mode-8/mode-10 ratio is quoted before route 5a's own within-cell
episode-level split-half null is on the page.
🛑 "EMPTY" IS NOT "NULL" -- a cell with no windows is UNPOWERED and is printed as such.

⚠ WINDOW PURITY. A 2.56 s window can straddle a mode transition. Windows are assigned to a mode
only when >=90% of their frames carry it, exactly as the `lat` convention does; straddling windows
are counted and excluded, never silently binned.
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

import _r31_common as C                                                       # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained      # noqa: E402
import _r4f_lib as R4F                                                        # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
FREE = (5.0, 12.0)
GRIND = (18.0, 22.0)
HANDS_OFF = 300.0
CREEP = 4.0
AMP_MIN = 600.0            # envelope counts; p-p = 2 * env
RNG = np.random.default_rng(20260805)

CACHE, PFX, SEGS = ROOT / "_scratch/cache/r5a", "r5as", list(range(18))


def hdr(s):
    print("\n" + "=" * 118 + f"\n{s}\n" + "=" * 118)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def scan():
    """VERBATIM `r59_ratchet_vs_history.scan`, plus the per-window mode tag."""
    recs = []
    for s in SEGS:
        p = CACHE / f"{PFX}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, CACHE, PFX)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(tq, fs, *RATCH)
        eng = band_envelope(tq, fs, *GRIND)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        m10 = np.asarray(d["mode"], float) == 10
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = peak_prom(f, P, *FREE)
            fb, pb = peak_prom(f, P, *RATCH)
            fg, pg = peak_prom(f, P, *GRIND)
            recs.append(dict(seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                             fr=fr, pr=pr, fb=fb, pb=pb, fg=fg, pg=pg,
                             env99=float(np.percentile(env[w], 99)),
                             eng99=float(np.percentile(eng[w], 99)),
                             v=float(v[w].mean()), lat=float(lat[w].mean()),
                             m10=float(m10[w].mean()),
                             eff=float(np.median(eff[w])),
                             ang=float(np.median(ang[w])),
                             absang=float(np.median(np.abs(ang[w])))))
    return recs


def episodes(rs):
    """Contiguous window runs inside one segment -- the physical event, the bootstrap unit."""
    eps, cur = [], []
    for r in sorted(rs, key=lambda r: (r["seg"], r["i0"])):
        if cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r]
    if cur:
        eps.append(cur)
    return eps


def epboot(rs, key="env99", stat=np.median, nb=4000):
    eps = episodes(rs)
    if not eps:
        return np.nan, np.nan, np.nan, 0, 0
    vals = np.array([r[key] for r in rs], float)
    pt = float(stat(vals[np.isfinite(vals)])) if np.isfinite(vals).any() else np.nan
    draws = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        v = np.concatenate([[r[key] for r in eps[j]] for j in k])
        v = v[np.isfinite(v)]
        draws[b] = stat(v) if len(v) else np.nan
    ok = np.isfinite(draws)
    lo, hi = (np.percentile(draws[ok], [2.5, 97.5]) if ok.sum() > 10 else (np.nan, np.nan))
    return pt, float(lo), float(hi), len(eps), len(rs)


def splithalf_null(rs, key="env99", nb=2000):
    """The FLOOR. Split this cell's OWN episodes at random and take the ratio of medians."""
    eps = episodes(rs)
    if len(eps) < 4:
        return np.nan, np.nan, len(eps)
    out = []
    for _ in range(nb):
        k = RNG.permutation(len(eps))
        a = np.concatenate([[r[key] for r in eps[j]] for j in k[:len(eps) // 2]])
        b = np.concatenate([[r[key] for r in eps[j]] for j in k[len(eps) // 2:]])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and np.median(b) > 0:
            out.append(np.median(a) / np.median(b))
    if len(out) < 50:
        return np.nan, np.nan, len(eps)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(eps)


def cellsel(rs, mode=None, hands=None, vhi=None, angmax=None, pure=0.9):
    out = list(rs)
    if mode == 10:
        out = [r for r in out if r["m10"] >= pure]
    elif mode == 8:
        out = [r for r in out if r["m10"] <= 1 - pure]
    if vhi is not None:
        out = [r for r in out if r["v"] < vhi]
    if hands == "off":
        out = [r for r in out if r["eff"] <= HANDS_OFF]
    elif hands == "on":
        out = [r for r in out if r["eff"] > HANDS_OFF]
    if angmax is not None:
        out = [r for r in out if r["absang"] < angmax]
    return out


def line(lbl, rs):
    """One inventory row. Prints EMPTY/UNPOWERED loudly rather than a blank."""
    if not rs:
        print(f"   {lbl:38s} {'EMPTY -- UNPOWERED, not a null':>62s}")
        return None
    e = col(rs, "env99")
    hits = int((e >= AMP_MIN).sum())
    pt, lo, hi, neps, nw = epboot(rs)
    fh = col([r for r in rs if r["env99"] >= AMP_MIN], "fr")
    fstr = f"{np.median(fh):5.2f}" if len(fh) else "  -- "
    print(f"   {lbl:38s} {nw:5d}w {nw * NFFT / 100.0:7.1f}s {neps:4d}ep | "
          f"med env {pt:7.1f} [{lo:7.1f},{hi:7.1f}] | p-p med {2 * np.median(e):7.0f} "
          f"max {2 * e.max():7.0f} | >=1200pp {hits:4d} ({100.0 * hits / nw:5.1f}%) | f0 {fstr}")
    return dict(n=nw, hits=hits, med=pt, lo=lo, hi=hi, neps=neps)


ALL = scan()
straddle = [r for r in ALL if 0.1 < r["m10"] < 0.9]
hdr("§0  WINDOW INVENTORY AND THE CONFOUND")
print(f"   total windows: {len(ALL)}  ({len(ALL) * NFFT / 100.0:.1f} s at NFFT {NFFT}, "
      f"non-overlapping)")
print(f"   straddling a mode transition (0.1 < m10 < 0.9): {len(straddle)} -- EXCLUDED from both "
      f"mode cells, not rebinned")
pure10 = [r for r in ALL if r["m10"] >= 0.9]
pure8 = [r for r in ALL if r["m10"] <= 0.1]
print(f"   pure mode 10: {len(pure10)}w   pure mode 8: {len(pure8)}w")
agree = sum(1 for r in ALL if (r["m10"] >= 0.9) == (r["lat"] >= 0.9))
print(f"   🛑 CONFOUND: window-level (mode10 >= 0.9) == (lat >= 0.9) on {agree}/{len(ALL)} = "
      f"{100.0 * agree / len(ALL):.2f}% of windows.")
print("   ⇒ the mode-8/mode-10 contrast IS the manual/engaged contrast. NOT separately identifiable.")

hdr(f"§1  THE RATCHET BY MODE -- 6-9 Hz envelope p99, AMP_MIN {AMP_MIN:.0f} (= 1200 p-p)")
print(f"   {'cell':38s} {'wins':>5s} {'sec':>8s} {'eps':>5s} | {'median envelope [95% CI]':>34s} | "
      f"{'p-p med':>11s} {'max':>11s} | {'>=1200 p-p':>17s} | f0")
res = {}
for lbl, kw in (("mode 10, ALL speeds", dict(mode=10)),
                ("mode  8, ALL speeds", dict(mode=8)),
                ("mode 10, creep <4 m/s", dict(mode=10, vhi=CREEP)),
                ("mode  8, creep <4 m/s", dict(mode=8, vhi=CREEP)),
                ("mode 10, creep hands-OFF", dict(mode=10, vhi=CREEP, hands="off")),
                ("mode  8, creep hands-OFF", dict(mode=8, vhi=CREEP, hands="off")),
                ("mode 10, creep hands-ON", dict(mode=10, vhi=CREEP, hands="on")),
                ("mode  8, creep hands-ON", dict(mode=8, vhi=CREEP, hands="on")),
                ("★ mode 10, ENG creep |ang|<10", dict(mode=10, vhi=CREEP, angmax=10.0)),
                ("★ mode  8, MAN creep |ang|<10", dict(mode=8, vhi=CREEP, angmax=10.0)),
                ("mode 10, >=4 m/s", dict(mode=10, vhi=None)),
                ("mode  8, >=4 m/s", dict(mode=8, vhi=None))):
    rs = cellsel(ALL, **kw)
    if lbl.endswith(">=4 m/s"):
        rs = [r for r in cellsel(ALL, mode=kw["mode"]) if r["v"] >= CREEP]
    res[lbl] = line(lbl, rs)

hdr("§2  THE SPLIT-HALF NULL FIRST -- the floor this route's own estimator produces")
for lbl, kw in (("mode 10, creep", dict(mode=10, vhi=CREEP)),
                ("mode  8, creep", dict(mode=8, vhi=CREEP)),
                ("mode 10, all", dict(mode=10)), ("mode  8, all", dict(mode=8))):
    lo, hi, ne = splithalf_null(cellsel(ALL, **kw))
    print(f"   {lbl:24s} split-half null ratio 95% band [{lo:.3f}, {hi:.3f}]  ({ne} episodes)")
print("   ⇒ a mode-8/mode-10 ratio inside its own band is NOT a finding.")

hdr("§3  THE CONTRAST, episode-bootstrapped -- and what it may NOT be attributed to")
for lbl, ka, kb in (("creep", dict(mode=8, vhi=CREEP), dict(mode=10, vhi=CREEP)),
                    ("all speeds", dict(mode=8), dict(mode=10))):
    A, B = cellsel(ALL, **ka), cellsel(ALL, **kb)
    if not A or not B:
        print(f"   {lbl}: EMPTY on one side -- UNPOWERED, no ratio")
        continue
    epA, epB = episodes(A), episodes(B)
    draws = np.empty(4000)
    for i in range(4000):
        a = np.concatenate([[r["env99"] for r in epA[j]]
                            for j in RNG.integers(0, len(epA), len(epA))])
        b = np.concatenate([[r["env99"] for r in epB[j]]
                            for j in RNG.integers(0, len(epB), len(epB))])
        draws[i] = np.median(a) / np.median(b) if np.median(b) > 0 else np.nan
    ok = np.isfinite(draws)
    lo, hi = np.percentile(draws[ok], [2.5, 97.5])
    pt = np.median(col(A, "env99")) / np.median(col(B, "env99"))
    print(f"   {lbl:12s} mode8 / mode10 = {pt:.3f}  [{lo:.3f}, {hi:.3f}]   "
          f"({len(epA)} vs {len(epB)} episodes)")
print("   🛑 This ratio is the MANUAL/ENGAGED ratio. It carries no information about the damper")
print("      mode, the FactorC/E records, or V72's lift, because those never vary independently.")

hdr("§4  PRESENCE IN MODE 8 -- the question that IS answerable")
m8 = cellsel(ALL, mode=8)
m8h = [r for r in m8 if r["env99"] >= AMP_MIN]
print(f"   mode 8 windows over AMP_MIN: {len(m8h)} / {len(m8)} "
      f"({100.0 * len(m8h) / max(len(m8), 1):.2f}%), {len(m8h) * NFFT / 100.0:.1f} s")
if m8h:
    fr = col(m8h, "fr")
    print(f"   their FREE 5-12 Hz prominence-argmax f0: median {np.median(fr):.2f} Hz  "
          f"IQR [{np.percentile(fr, 25):.2f}, {np.percentile(fr, 75):.2f}]  "
          f"n={len(fr)}   (the recorded ratchet is 7.79 Hz)")
    print(f"   their p-p amplitudes: median {2 * np.median(col(m8h, 'env99')):.0f}  "
          f"max {2 * col(m8h, 'env99').max():.0f} counts")
    print(f"   speeds: median {np.median(col(m8h, 'v')):.2f} m/s  "
          f"range {col(m8h, 'v').min():.2f}..{col(m8h, 'v').max():.2f}")
m10h = [r for r in cellsel(ALL, mode=10) if r["env99"] >= AMP_MIN]
print(f"   mode 10 windows over AMP_MIN: {len(m10h)} / {len(pure10)} "
      f"({100.0 * len(m10h) / max(len(pure10), 1):.2f}%), {len(m10h) * NFFT / 100.0:.1f} s")
if m10h:
    fr = col(m10h, "fr")
    print(f"   their f0: median {np.median(fr):.2f} Hz  "
          f"IQR [{np.percentile(fr, 25):.2f}, {np.percentile(fr, 75):.2f}]")
    print(f"   their p-p: median {2 * np.median(col(m10h, 'env99')):.0f}  "
          f"max {2 * col(m10h, 'env99').max():.0f} counts")
