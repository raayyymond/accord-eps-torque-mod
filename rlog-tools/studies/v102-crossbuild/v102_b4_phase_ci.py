#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_b4_phase_ci.py -- the CI and the proper nulls for `arg(csd(b4, rate_c))` at 22-26 Hz.

`studies/v102-crossbuild/v102_b4_phase_feasibility.py` established the two things that had to be true first:
  CONTROL A  hard limiting + unfiltered 10:1 decimation recover a KNOWN phase to
             bias -0.0 deg, scatter 0.2 deg.  Bussgang holds; the 3rd-harmonic-alias worry (H3)
             does not bite in practice.
  CONTROL B  the real `b4` carries 22-26 Hz structure at 1.382x a shuffled-bit white null.

It then printed a bare `+164.4 deg` with **no CI and an incomplete null** (it reported the
time-reversed null's ANGLE but not its COHERENCE, which is the part that matters -- any complex
sum has some angle).  A phase whose SIGN is meant to decide a build cannot ship like that: +-90 deg
of uncertainty flips pump to damp.  This file supplies what was missing.

  * BLOCK BOOTSTRAP over the 8 gap-free blocks -> a CI on the phase (circular, via unwrapping the
    bootstrap distribution about the point estimate).
  * THREE nulls, each reporting COHERENCE as well as angle:
        time-reversed reference · circularly-rotated reference · phase-randomised reference
    A real result must sit ABOVE all three in coherence.
  * The coherence NOISE FLOOR for the actual number of INDEPENDENT segments (50 % overlap => the
    effective count is ~n/2, not n).
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
sys.path.insert(0, str(HERE))
import v102_xb_lib as L                       # noqa: E402
import v102_b4_phase_feasibility as FZ        # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF, WIN, FG, BAND = FZ.NF, FZ.WIN, FZ.FG, FZ.BAND
taper = FZ.taper


def collect(vlo=30.0, vhi=85.0, hands_light=True, ref="rate_c", bit="v102_b4"):
    A, B, ep = [], [], []
    for e, b in enumerate(L.all_blocks("96")):
        if bit not in b or ref not in b:
            continue
        vv = b["v_rear"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= vlo) & (vv < vhi)
        if hands_light:
            m = m & (np.abs(b["cs_tq"]) < 400)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                x = (b[bit][i:i + NF] > 0.5).astype(float) * 2 - 1
                A.append(np.fft.rfft(taper(x)))
                B.append(np.fft.rfft(taper(b[ref][i:i + NF])))
                ep.append(e)
            i += NF // 2
    return np.array(A), np.array(B), np.array(ep)


def stat(A, B):
    S, Pa, Pb = (A * np.conj(B)).sum(0), (np.abs(A) ** 2).sum(0), (np.abs(B) ** 2).sum(0)
    coh = float(np.mean((np.abs(S) ** 2) / np.maximum(Pa * Pb, 1e-30)))
    return float(np.degrees(np.angle(S[BAND].sum()))), coh


if __name__ == "__main__":
    for name, kw in (("hands-LIGHT 30-85 km/h", dict()),
                     ("ALL hands 30-85 km/h", dict(hands_light=False)),
                     ("hands-LIGHT 30-85, ref=cs_ang", dict(ref="cs_ang"))):
        A, B, ep = collect(**kw)
        if len(A) < 12:
            print("\n%-32s only %d windows -- NOT QUOTED" % (name, len(A)))
            continue
        ang, coh = stat(A, B)
        keys = np.unique(ep)
        rng = np.random.default_rng(23)
        bs = []
        for _ in range(3000):
            sel = np.concatenate([np.nonzero(ep == keys[j])[0]
                                  for j in rng.integers(0, len(keys), len(keys))])
            bs.append(stat(A[sel], B[sel])[0])
        d = (np.array(bs) - ang + 180) % 360 - 180          # unwrap about the point estimate
        lo, hi = np.percentile(d, [2.5, 97.5])
        eff = len(A) / 2.0                                   # 50 % overlap
        floor = 1.0 / eff
        print("\n%-32s  %d win / %d blocks" % (name, len(A), len(keys)))
        print("   arg = %+7.1f deg   95%% CI [%+7.1f, %+7.1f]   width %.0f deg"
              % (ang, ang + lo, ang + hi, hi - lo))
        print("   coh2 = %.4f   noise floor (1/n_eff, n_eff=%.0f) = %.4f   ratio %.1fx"
              % (coh, eff, floor, coh / floor))
        # ---- three nulls, each with its coherence
        for nm, Bn in (("time-reversed", np.array([np.fft.rfft(taper(np.real(np.fft.irfft(b))[::-1]))
                                                   for b in B])),
                       ("rotated +37 win", np.roll(B, 37, axis=0)),
                       ("phase-randomised", B * np.exp(1j * rng.uniform(
                           0, 2 * np.pi, B.shape)))):
            a2, c2 = stat(A, Bn)
            print("      null %-18s arg %+7.1f   coh2 %.4f   %s"
                  % (nm, a2, c2, "OK (below signal)" if c2 < coh * 0.6 else
                     "🛑 NULL NOT BELOW SIGNAL -- result unsafe"))
    print("""
🛑 WHAT THIS DOES AND DOES NOT LICENSE.
   Licensed: the phase and its CI, as a measurement of `sgn(gp-0x6ada)` against wheel rate.
   NOT licensed by me: the pump-or-damp verdict.  The operator-confirmed sign convention (LKAS
   demand and driver torque sit in OPPOSITE frames) must be applied ONCE, deliberately, by whoever
   converts this into a direction -- applying it twice or never is the recorded failure mode.""")
