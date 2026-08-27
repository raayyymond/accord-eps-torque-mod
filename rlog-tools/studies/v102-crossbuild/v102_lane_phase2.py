#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_lane_phase2.py -- arg(csd(gp-0x6b26 / gp-0x6bbe, STEER_TORQUE_SENSOR)) at 20-23 Hz.

This is the lane `pole-hunt` actually asked for.  It is NOT on the wire on V102 (route 96 packs
`gp-0x6b4c`), but it IS on routes 7d (V84), 77 (V90), 78 (V91) -- `gp-0x6b26` -- and 79 --
`gp-0x6bbe`.  All are 4x builds.

🛑 THIS SCRIPT WRITES NOTHING.  The per-segment caches for those routes have no `x6b26` column and
another agent is reading them, so the signed lane is rebuilt IN MEMORY from the whole-route npz
(`ab_mt` + `ab_t1ab` + `probe`) every run.  Sign bit is b7 = 0x80 on all four routes, verified:
`decode/extract_r77.py:75` B7_SIGN_6B26 = 0x80 · `decode/extract_r78_r79.py:97,99` b7_sign_6b26 / b7_sign_6bbe.
The wire SCALE (2/5, 8/5, 16/5) is irrelevant to a phase and is deliberately not applied.

INSTRUMENT HAZARDS -- unchanged from `studies/v102-crossbuild/v102_lane_phase.py`, and they dominate:
  * 427 samples at ~49.8 Hz => Nyquist 24.9 Hz.  20-23 Hz is 2.2 samples/cycle.
  * Differential ZOH: the lane is held from 49.8 Hz, `tq` from 100.74 Hz, onto the same row grid
    => a pure instrument delay (T_lane - T_tq)/2 = 5.077 ms = +39.3 deg at 21.5 Hz, corrected.
  * Aliasing: content at 26.8-29.8 Hz folds into 20-23 Hz.  Speed capped at 65 km/h.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF, FS, GAP = 256, 100.0, 0.050
WIN = np.hanning(NF)
F = np.fft.rfftfreq(NF, 1.0 / FS)
BAND = (F >= 20.0) & (F <= 23.0)
CORR = 360.0 * float(np.mean(F[BAND])) * ((1.0 / 49.8 - 1.0 / 100.74) / 2.0)

ROUTES = {"7d": ("V84  4x", "gp-0x6b26 INERTIA"), "77": ("V90  4x", "gp-0x6b26 INERTIA"),
          "78": ("V91  4x", "gp-0x6b26 INERTIA"), "79": ("V91  4x", "gp-0x6bbe VISCOUS/boost")}


def build(route):
    """Whole-route npz -> uniform 100 Hz blocks carrying `lane`, `tq`, `cc_lat`, `v_rear`."""
    z = dict(np.load(ROOT / "analysis-2020accord" / ("_cache_r%s/r%s.npz" % (route, route)),
                     allow_pickle=True))
    t = np.asarray(z["t"], float)
    p = np.asarray(z["probe"], int) & 0xFF
    sgn = np.where((p & 0x80) != 0, -1.0, 1.0)
    abt, mt = np.asarray(z["ab_t1ab"], float), np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    lane = sgn * mt[j].astype(float)          # SIGNED lane; scale irrelevant to a phase
    v = np.asarray(z["v_rear"], float) if "v_rear" in z else \
        0.5 * (np.asarray(z["ws_rl"], float) + np.asarray(z["ws_rr"], float))
    cols = {"lane": lane, "tq": np.asarray(z["tq"], float),
            "cc_lat": np.asarray(z["cc_lat"], float), "v": v,
            "cs_tq": np.asarray(z["cs_tq"], float)}
    n = min(len(t), *[len(x) for x in cols.values()])
    t = t[:n]
    cols = {k: x[:n] for k, x in cols.items()}
    brk = np.nonzero(np.diff(t) > GAP)[0]
    edges = [0] + [int(b) + 1 for b in brk] + [len(t)]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a < 4 or t[b - 1] - t[a] < 3.0:
            continue
        tt = np.arange(t[a], t[b - 1], 1.0 / FS)
        out.append({k: np.interp(tt, t[a:b], x[a:b]) for k, x in cols.items()})
    return out


def taper(x):
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    return (x - (c[0] * r + c[1])) * WIN


def phase(route, vhi=65.0):
    S, Pl, Pr, ep = [], [], [], []
    for e, b in enumerate(build(route)):
        vv = b["v"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= 5.0) & (vv < vhi)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                A = np.fft.rfft(taper(b["lane"][i:i + NF]))
                B = np.fft.rfft(taper(b["tq"][i:i + NF]))
                S.append(A * np.conj(B))
                Pl.append(np.abs(A) ** 2)
                Pr.append(np.abs(B) ** 2)
                ep.append(e)
            i += NF // 2
    if len(S) < 6:
        return None
    S, Pl, Pr, ep = np.array(S), np.array(Pl), np.array(Pr), np.array(ep)

    def est(sel):
        s, pl, pr = S[sel].sum(0), Pl[sel].sum(0), Pr[sel].sum(0)
        coh = float(np.mean((np.abs(s) ** 2) / np.maximum(pl * pr, 1e-30)))
        return np.degrees(np.angle(s[BAND].sum())), coh
    ang, coh = est(np.arange(len(S)))
    rng = np.random.default_rng(7)
    keys = np.unique(ep)
    bs = [est(np.concatenate([np.nonzero(ep == keys[j])[0]
                              for j in rng.integers(0, len(keys), len(keys))]))[0]
          for _ in range(1500)]
    bs = np.degrees(np.unwrap(np.radians(np.array(bs))))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(ang=float(ang), lo=float(lo), hi=float(hi), coh=coh,
                nwin=len(S), nep=len(keys))


if __name__ == "__main__":
    print("=" * 100)
    print("arg(csd(LANE, tq)) band-averaged 20-23 Hz, engaged, 5-65 km/h, episode bootstrap.")
    print("band centre %.2f Hz   differential-ZOH correction %+.1f deg (ADDED to raw)"
          % (float(np.mean(F[BAND])), CORR))
    print("=" * 100)
    for rt, (lab, cell) in ROUTES.items():
        try:
            r = phase(rt)
        except Exception as exc:
            print("  r%-3s %-9s FAILED: %s" % (rt, lab, exc))
            continue
        if r is None:
            print("  r%-3s %-9s too thin  (%s)" % (rt, lab, cell))
            continue
        floor = 1.0 / r["nwin"]
        print("  r%-3s %-9s  raw %+7.1f  CORRECTED %+7.1f  [%+7.1f, %+7.1f]  coh2 %.3f "
              "(noise floor %.3f)  %3d win / %d epi   %s"
              % (rt, lab, r["ang"], r["ang"] + CORR, r["lo"] + CORR, r["hi"] + CORR,
                 r["coh"], floor, r["nwin"], r["nep"], cell))
