#!/usr/bin/env python3
r"""lib/v95_rez_lib.py -- the shared instrument for the 2026-08-11/12 driving-point-impedance session.

Everything in the `v95_rez_*` / `v95_lane_*` / `v95_crossbuild_*` family imports this.  READ-ONLY on
every cache and every image.  The band estimator is the kit's FROZEN one
(`decode_v90_probe._band_transfer`: Hann, detrended, Welch-summed across windows) so numbers here are
directly comparable with `studies/impedance/v92_rez_extend.py` and `studies/v91-v94-dose/v92_boost_lane_and_rez.py`.

WHAT THIS FILE ADDS OVER THE FROZEN ESTIMATOR
  1. EPISODE bookkeeping, so every CI is bootstrapped over episodes and never over windows
     (`feedback-episodes-not-windows`).  An episode is one contiguous run inside one route.
  2. FOUR hands-off definitions, because the kit's usual one is a selection effect on the
     measurement itself -- see the block below.
  3. A cache autodiscovery + route->build map covering every full-schema cache, not just r77-r79.

===================================================================================================
🛑 THE MASK IS A THRESHOLD ON THE NUMERATOR OF Z.  READ THIS BEFORE USING D0.
===================================================================================================
`opendbc/car/honda/carstate.py:163`
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD.get(fingerprint, 1200)
`HONDA_ACCORD` (10th gen) is NOT in the override dict, so T = 1200 -- and `steeringTorque` is
`STEER_TORQUE_SENSOR`, i.e. the NUMERATOR of `Z = S_wT / S_ww`.  Measured: `press` equals
`|cs_tq| > 1200` on 99.28-99.96 % of frames on every route, and a free threshold fit returns
exactly 1200 every time.  Because `runs_of` requires EVERY frame of a window to pass, one excursion
to +-1200 in 5.12 s kills the window.  That is amplitude truncation of the measured signal, and it
is ARM-ASYMMETRIC: the dropped windows carry 3.91x the 6-9 Hz torque in the engaged arm against
1.20x in the manual arm.

    D0 STRICT   press duty == 0            <- what the kit used up to 2026-08-11
    D1 TOL5     press duty <= 5 %
    D2 TOL20    press duty <= 20 %
    D3 MEDIAN   window-median |cs_tq| < 1200, press duty unconstrained   <- BAND-ORTHOGONAL
    D4          D2 AND D3                                                <- conservative

D3 is the one to use.  A median over 512 samples has essentially no leverage from 2-38 Hz content,
so the criterion is ~orthogonal to the band being measured.  It is NOT torque-free: no
torque-independent hands-on sensor exists on this car, and that is a limit, not something to work
around.  MEASURED CONSEQUENCE: `Re(Z)` at 6 Hz and above is invariant across D0..D3 (6-9 Hz reads
-3383 / -3399 / -3395 / -3394); 4-6 Hz loses 65 % of its magnitude and 2-4 Hz REVERSES SIGN
(-1312 -> +612).  ⇒ do not quote `Re(Z)` below 6 Hz from a `steeringPressed` mask.

SIGN CONVENTION, anchored rather than assumed (`studies/impedance/v95_rez_polarity_and_mask.py`):
    Z(f) = S_{w,T} / S_{w,w},  w = 0x18F b2-3 * -0.1 (rad/s),  T = 0x18F b0-1 * -1 (counts).
    Re(Z) > 0 = DISSIPATIVE, Re(Z) < 0 = the column doing work on the driver's hands.
    Physics that fixes the direction:  Z = j*w*J + b - T_motor/Omega
      => Re(Z) is REDUCED by whatever component of MOTOR torque is in phase with rate.
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
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v90_probe as P            # noqa: E402  frozen estimator
import _r31_common as C31               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEG2RAD = np.pi / 180.0
NW, HOP = 512, 256                      # 5.12 s at 100 Hz  == P.NW_Z / P.HOP_Z
NW50, HOP50 = 256, 128                  # 5.12 s on the 50 Hz 427 grid
FS = 101.0                              # pooled grid; per-route fs spread is < 0.8 %
COH_ABS, COH_REL = 0.10, 5.0            # the kit's pre-declared trust gate
STEER_THRESHOLD = 1200.0                # opendbc default; HONDA_ACCORD has no override

BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
         ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("32-38", 32.0, 38.0)]
DEFS = ("D0 STRICT", "D1 TOL5", "D2 TOL20", "D3 MEDIAN", "D4 = D2 AND D3")

# ---- cache autodiscovery.  Main npz per cache dir, both repo locations.
CACHES = {}
for _d in sorted(ROOT.glob("_cache_r*")) + sorted((ROOT / "analysis-2020accord").glob("_cache_r*")):
    if not _d.is_dir():
        continue
    _s = _d.name.replace("_cache_", "")
    for _c in (_s, _s.rstrip("x")):
        if (_d / f"{_c}.npz").exists():
            CACHES[_s] = _d / f"{_c}.npz"
            break

# route -> build.  r5e/r61/r65 corrected 2026-08-12 from the handoff prose (they were wrong in an
# earlier draft of this file); r66..r6d are pinned by decode_v84_probe_r6d.ROUTES and the extractor
# names; r77/r78/r79/r7d are pinned by their own single-frame identity tests.
BUILD = {"r5e": "V75", "r61": "V74", "r65": "V76-V38base", "r66": "V80", "r66x": "V80",
         "r67x": "V81", "r68x": "V83a", "r6d": "V84", "r6e": "V85", "r6f": "V86", "r70": "V86B",
         "r71": "V87", "r73": "V88", "r75": "V89", "r76": "V89", "r77": "V90", "r78": "V91",
         "r79": "V92", "r7d": "V94"}
NEED = {"t", "cc_lat", "cs_press", "cs_v", "tq", "rate_f"}


def load(route):
    return np.load(CACHES[route], allow_pickle=True)


def base(z):
    """The channels every arm needs, on the 100 Hz row grid.

    🛑 `cs_v` is m/s, NOT km/h.  🛑 `cs_eng` is cruiseState and is WRONG for lateral engagement --
    use `cc_lat`.  🛑 `tq` and `rate_f` are both fields of the SAME 0x18F frame, so any staleness is
    common to numerator and denominator and cancels in Z.
    """
    t = np.asarray(z["t"], float)
    return dict(
        t=t, fs=1.0 / float(np.median(np.diff(t))),
        tq=np.asarray(z["tq"], float),
        w=np.asarray(z["rate_f"], float) * DEG2RAD,
        wdeg=np.asarray(z["rate_f"], float),
        lat=np.asarray(z["cc_lat"], float) > 0.5,
        press=np.asarray(z["cs_press"], float) > 0.5,
        v=np.abs(np.asarray(z["cs_v"], float)),
        cs_tq=np.abs(np.asarray(z["cs_tq"], float)) if "cs_tq" in z.files else None,
    )


def epwins(mask, t, arrays, nw=NW, hop=HOP, max_gap=0.05):
    """[(episode_index, (a0[sl], ...)), ...] -- episode id = contiguous-run number."""
    out = []
    for ei, (a, b) in enumerate(C31.runs_of(mask, t, nw, max_gap=max_gap)):
        for i in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + i, a + i + nw)
            out.append((ei, tuple(A[sl] for A in arrays)))
    return out


def transfer(W, fs, bands=BANDS, nw=NW, rng=None, nboot=0, xi=0, yi=1):
    """Welch transfer + shuffled-pairs control + EPISODE-bootstrap CI on Re.

    W is [(episode_key, (arrays...)), ...].  `episode_key` may be any hashable -- a (route, run)
    tuple is what the pooled scripts use, so the bootstrap never resamples within a drive.
    """
    if len(W) < 6:
        return None
    pairs = [(w[1][xi], w[1][yi]) for w in W]
    r = P._band_transfer(pairs, fs, nw, bands)
    rng = rng or np.random.default_rng(20260812)
    idx = rng.permutation(len(pairs))
    rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                           for i in range(len(pairs))], fs, nw, bands)
    out = {}
    for nm, lo, hi in bands:
        out[nm] = dict(n_win=len(pairs), re=r[nm]["re_over_sxx"], gain=r[nm]["gain"],
                       phase_deg=r[nm]["phase_deg"], coh2=r[nm]["coh2"], coh2_shuf=rs[nm]["coh2"],
                       trust=bool(r[nm]["coh2"] >= COH_ABS
                                  and r[nm]["coh2"] >= COH_REL * max(rs[nm]["coh2"], 1e-9)))
    if nboot:
        eps = sorted({w[0] for w in W}, key=str)
        byep = [[w for w in W if w[0] == e] for e in eps]
        boots = {nm: [] for nm, _, _ in bands}
        for _ in range(nboot):
            pick = rng.integers(0, len(eps), size=len(eps))
            pp = [(w[1][xi], w[1][yi]) for e in pick for w in byep[e]]
            if len(pp) < 6:
                continue
            rb = P._band_transfer(pp, fs, nw, bands)
            for nm, _, _ in bands:
                boots[nm].append(rb[nm]["re_over_sxx"])
        for nm, _, _ in bands:
            b = np.asarray(boots[nm], float)
            if len(b) >= 20:
                out[nm]["re_lo"] = float(np.percentile(b, 2.5))
                out[nm]["re_hi"] = float(np.percentile(b, 97.5))
                out[nm]["n_ep"] = len(eps)
    return out


# ======================================================================================
#  THE FOUR HANDS-OFF DEFINITIONS, on a COMMON candidate population
# ======================================================================================
def bandamp(x, nw, lo, hi, fs=FS):
    h = np.hanning(nw)
    X = np.abs(np.fft.rfft((x - x.mean()) * h)) ** 2
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    return float(np.sqrt(X[(f >= lo) & (f <= hi)].sum()))


def candidates(nw=NW, hop=HOP, routes=None):
    """Windows on runs of (arm & moving), press UNCONSTRAINED, each tagged with all criteria.

    Building both arms from the same population is the point: only the hands-off CRITERION then
    differs between D0..D4, so a D0-vs-D3 comparison prices the selection effect and nothing else.
    """
    out = defaultdict(list)
    for r in sorted(routes or CACHES):
        if r == "r66x":                          # same route as r66
            continue
        z = load(r)
        if not (NEED | {"cs_tq"}) <= set(z.files):
            continue
        B = base(z)
        if len(B["t"]) < 2000:
            continue
        mov = B["v"] > 0.5
        for arm, m in (("ENG", B["lat"] & mov), ("MAN", (~B["lat"]) & mov)):
            for ei, tup in epwins(m, B["t"], (B["w"], B["tq"], B["v"], np.abs(B["wdeg"]),
                                              B["cs_tq"], B["press"].astype(float)),
                                  nw=nw, hop=hop):
                out[arm].append(dict(
                    ep=(r, arm, ei), route=r, build=BUILD.get(r, "?"),
                    w=tup[0], tq=tup[1],
                    v=float(np.mean(np.abs(tup[2]))), rate=float(np.median(tup[3])),
                    duty=float(tup[5].mean()), med=float(np.median(tup[4])),
                    a69=bandamp(tup[1], nw, 6, 9), a2631=bandamp(tup[1], nw, 26, 31)))
    return out


def passes(w, d):
    return {"D0 STRICT": w["duty"] == 0.0,
            "D1 TOL5": w["duty"] <= 0.05,
            "D2 TOL20": w["duty"] <= 0.20,
            "D3 MEDIAN": w["med"] < STEER_THRESHOLD,
            "D4 = D2 AND D3": w["med"] < STEER_THRESHOLD and w["duty"] <= 0.20}[d]


def cell(W, vlo=5.0, vhi=22.0, rlo=0.0, rhi=13.0, d="D3 MEDIAN"):
    """The matched cell.  Defaults are the session's pre-declared one: 5-22 m/s, |rate| < 13 deg/s."""
    return [w for w in W if passes(w, d) and vlo <= w["v"] < vhi and rlo <= w["rate"] < rhi]


def score(W, bands=BANDS, nw=NW, rng=None, nboot=0):
    """transfer() over a candidates()-shaped list."""
    return transfer([(w["ep"], (w["w"], w["tq"])) for w in W], FS, bands, nw, rng, nboot)


# ======================================================================================
#  printing
# ======================================================================================
def hdr(s):
    print("\n" + "=" * 104)
    print(" " + s)
    print("=" * 104)


def row(lbl, W, keys=("2-4", "4-6", "6-9", "9-12", "12-16", "18-22", "26-31", "32-38"),
        rng=None, nboot=0, minw=8):
    """One line: Re(Z) and coh2 per band, with the cell's own speed / rate / press-duty census."""
    if len(W) < minw:
        return f"    {lbl:32s} {len(W):4d} -- NOT SCOREABLE"
    r = score(W, rng=rng, nboot=nboot)
    s = " ".join(f"{r[k]['re']:+7.0f}{'' if r[k]['trust'] else '?'}({r[k]['coh2']:.2f})"
                 for k in keys)
    return (f"    {lbl:32s} {len(W):4d}/{len({w['ep'] for w in W}):3d}ep "
            f"v{np.median([w['v'] for w in W]):5.1f} r{np.median([w['rate'] for w in W]):5.2f} "
            f"d{np.median([w['duty'] for w in W]):5.3f} | {s}")


def full(lbl, W, keys=("2-4", "4-6", "6-9", "9-12", "12-16", "18-22", "26-31", "32-38"),
         rng=None, nboot=600):
    """Multi-line: per-band Re, CI, |Z|, phase, coh2, shuffled, plus route composition."""
    if len(W) < 8:
        print(f"  {lbl:34s} {len(W):4d} windows -- NOT SCOREABLE")
        return None
    r = score(W, rng=rng, nboot=nboot)
    comp = defaultdict(int)
    for w in W:
        comp[w["route"]] += 1
    print(f"\n  {lbl}: {len(W)} win / {len({w['ep'] for w in W})} ep / {len(comp)} routes  "
          f"v50 {np.median([w['v'] for w in W]):.1f} m/s  |rate|50 "
          f"{np.median([w['rate'] for w in W]):.2f} deg/s  press-duty p50/p90 "
          f"{np.percentile([w['duty'] for w in W], 50):.3f}/"
          f"{np.percentile([w['duty'] for w in W], 90):.3f}")
    print("    routes: " + ", ".join(f"{k}:{v}" for k, v in
                                     sorted(comp.items(), key=lambda x: -x[1])[:6]))
    for k in keys:
        d = r[k]
        ci = f"[{d.get('re_lo', float('nan')):+7.0f},{d.get('re_hi', float('nan')):+7.0f}]"
        print(f"      {k:6s} Re {d['re']:+7.0f} {ci:>19s}  |Z| {d['gain']:7.0f}  "
              f"{d['phase_deg']:+6.0f}\u00b0  coh2 {d['coh2']:.3f} shuf {d['coh2_shuf']:.3f}"
              f"{'' if d['trust'] else '   FAILS TRUST GATE'}")
    return r
