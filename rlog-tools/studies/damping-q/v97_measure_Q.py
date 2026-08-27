#!/usr/bin/env python3
r"""THE DECIDING MEASUREMENT FOR V97 -- is `0xC63AC` a lead lever or an INVERTING one?

fw-loop's derivation, from the decompile of FUN_00038148 / FUN_0003a382:

    d(error)     = d(T) * [ 1 + Q(f) ]              T = gp-0x4f60, the torsion-bar torque
    d(gp-0x6b70) = -Q(f) * d(T)
    =>  Q(f) = - d(gp-0x6b70)/d(T)          <-- the COMPOSITE.  No decomposition needed.

Raising the Path-2 IIR pole `0xC63AC` rotates Q.  What that does to the loop's `B = 1 + Q` is

    sign( d(arg B)/d(arg Q) ) = sign( |Q| + cos(arg Q) )
        > 0  ->  the intended lead ARRIVES        (0xC63AC is a lead lever)
        < 0  ->  the intended lead ARRIVES INVERTED as LAG   (disqualified -- the V94 failure mode)

Both channels are already on the wire on routes 7e/7f (V96):
    T          = STEER_TORQUE_SENSOR, CAN 0x18F bytes 0:1, 100 Hz
    gp-0x6b70  = CAN 427 magnitude (|x|*5>>6, LSB 12.8) * sign from 0x14A byte4 b7, 50 Hz

🛑 THE VERDICT IS A FUNCTION OF BOTH FACTORS.  Separate CIs on |Q| and arg Q mislead; the CI is
taken on the composite `|Q| + cos(arg Q)` itself, bootstrapped over EPISODES (return events), never
over windows.

🛑 PAIRING.  The 427 magnitude (50 Hz) and its sign bit (0x14A, 100 Hz) are joined with the kit's
documented safe pairing `(raw14_t, raw14_b4)`; a 10 ms join error is 28 deg at 7.79 Hz, i.e. the
whole error bar, so the join residual is reported.
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
from scipy.signal import butter, sosfiltfilt, get_window

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
from v96_elicitation_finder import load, mmss  # noqa: E402
from v96_probe_vs_ratchet import signed_lane   # noqa: E402

F0 = 7.79
FS50 = 50.0


def hands_off_returns(D, dt, a_min=25.0, win=1.2, tq_max=700.0):
    """Return events: |angle| local peak >= a_min, decaying, driver released (|tq| < tq_max)."""
    t, ang, tq, lat = D["t"], D["ang"], D["tq"], D["lat"]
    n = int(win / dt)
    out, i = [], int(0.5 / dt)
    while i < len(t) - n - 2:
        if abs(ang[i]) >= a_min and abs(ang[i]) == np.max(np.abs(ang[max(0, i - 25):i + 26])):
            s = slice(i, i + n)
            if abs(ang[i + n]) < abs(ang[i]) - 5 and np.median(np.abs(tq[s])) < tq_max and lat[i]:
                out.append((float(t[i]), float(t[i + n])))
                i += int(1.0 / dt)
        i += 1
    return out


def xspec(x, y, fs, f0, bw=1.5):
    """Cross-spectrum of (x, y) in a narrow band about f0. Returns (Sxy, Sxx, Syy)."""
    n = len(x)
    if n < 32:
        return None
    w = get_window("hann", n)
    X = np.fft.rfft((x - x.mean()) * w)
    Y = np.fft.rfft((y - y.mean()) * w)
    f = np.fft.rfftfreq(n, 1 / fs)
    m = (f >= f0 - bw) & (f <= f0 + bw)
    if not m.any():
        return None
    return (np.sum(Y[m] * np.conj(X[m])), np.sum(np.abs(X[m]) ** 2), np.sum(np.abs(Y[m]) ** 2))


def run(route, rng):
    z = np.load(ROOT / "analysis-2020accord" / f"_cache_r{route}" / f"r{route}.npz",
                allow_pickle=True)
    D = load(route)
    dt = float(np.median(np.diff(D["t"])))
    lt, ly, rep = signed_lane(z)                  # signed gp-0x6b70 on the 50 Hz 427 grid
    T50 = np.interp(lt, D["t"], D["tq"])          # torque sensor onto the same grid
    ev = hands_off_returns(D, dt)
    per = []
    for t0, t1 in ev:
        m = (lt >= t0) & (lt <= t1)
        if m.sum() < 40:
            continue
        r = xspec(T50[m], ly[m], FS50, F0)
        if r is None:
            continue
        Sxy, Sxx, Syy = r
        per.append(dict(t0=t0, n=int(m.sum()), Sxy=Sxy, Sxx=float(Sxx.real),
                        Syy=float(Syy.real),
                        coh=float(np.abs(Sxy) ** 2 / max(Sxx.real * Syy.real, 1e-30))))
    return per, rep, ev


def combine(per):
    """Pool the cross-spectra, then form Q = -H and the verdict statistic."""
    Sxy = np.sum([p["Sxy"] for p in per])
    Sxx = np.sum([p["Sxx"] for p in per])
    Syy = np.sum([p["Syy"] for p in per])
    H = Sxy / Sxx                                  # d(gp-0x6b70)/d(T)
    Q = -H
    absQ = float(np.abs(Q))
    argQ = float(np.degrees(np.angle(Q)))
    coh = float(np.abs(Sxy) ** 2 / max(Sxx * Syy, 1e-30))
    return absQ, argQ, absQ + np.cos(np.radians(argQ)), coh


if __name__ == "__main__":
    rng = np.random.default_rng(17)
    out = {}
    for route in ("7e", "7f"):
        per, rep, ev = run(route, rng)
        if len(per) < 3:
            print(f"route {route}: only {len(per)} usable return episodes -- skipping")
            continue
        absQ, argQ, verdict, coh = combine(per)
        # episode bootstrap on the VERDICT statistic, not on the factors
        bs = []
        for _ in range(8000):
            pick = [per[k] for k in rng.integers(0, len(per), len(per))]
            bs.append(combine(pick)[2])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        # shuffled-pairs control: pair each episode's Y with another episode's X
        sh = []
        for _ in range(2000):
            idx = rng.permutation(len(per))
            fake = [dict(Sxy=per[i]["Sxy"] * np.exp(1j * rng.uniform(0, 2 * np.pi)),
                         Sxx=per[i]["Sxx"], Syy=per[i]["Syy"]) for i in idx]
            sh.append(combine(fake)[2])
        print(f"\n=== route {route} ===")
        print(f"  join residual: p50 {1000*rep['resid_p50']:.2f} ms  p99 "
              f"{1000*rep['resid_p99']:.2f} ms   ({1000*rep['resid_p99']*F0*0.36:.0f} deg at "
              f"{F0} Hz at p99)")
        print(f"  {len(per)} hands-off engaged return episodes, "
              f"{sum(p['n'] for p in per)} samples on the 50 Hz grid")
        print(f"  coherence(T -> gp-0x6b70) at {F0} Hz = {coh:.3f}")
        print(f"  |Q| = {absQ:.3f}    arg Q = {argQ:+.1f} deg    cos(arg Q) = "
              f"{np.cos(np.radians(argQ)):+.3f}")
        print(f"  VERDICT STATISTIC  |Q| + cos(arg Q) = {verdict:+.3f}  "
              f"[{lo:+.3f}, {hi:+.3f}]   (episode bootstrap, n={len(per)})")
        print(f"  shuffled-phase control: median {np.median(sh):+.3f} "
              f"[{np.percentile(sh,2.5):+.3f}, {np.percentile(sh,97.5):+.3f}]")
        verd = ("INVERTS -- 0xC63AC DISQUALIFIED" if hi < 0 else
                "ADDS LEAD -- 0xC63AC survives" if lo > 0 else
                "NOT RESOLVED -- CI spans zero")
        print(f"  => {verd}")
        out[route] = dict(n_ep=len(per), absQ=absQ, argQ=argQ, verdict=verdict,
                          ci=[float(lo), float(hi)], coh=coh,
                          shuffled_med=float(np.median(sh)), verdict_text=verd)
    (ROOT / "analysis-2020accord" / "sessions/v97" / "measure_Q.json").write_text(
        json.dumps(out, indent=1, default=float))
    print("\nwrote analysis-2020accord/sessions/v97/measure_Q.json")
