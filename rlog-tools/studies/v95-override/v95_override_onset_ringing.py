#!/usr/bin/env python3
r"""studies/v95-override/v95_override_onset_ringing.py -- the follow-up the crossing-rate test does NOT settle.

🛑 WHY THIS FILE EXISTS.  `studies/v95-override/v95_override_authority_chatter.py` refutes the authority curve as a 6-9 Hz
OSCILLATOR: the knot is crossed at 0.47-1.69 Hz and the reconstructed authority signal keeps 88-95 %
of its energy below 3 Hz, at every unit scale from 0.6x to 2.0x.  **But a crossing rate is an
EXCITATION rate, not a ringing frequency.**  The kit has measured the 6-9 Hz mode as a lightly damped
resonance (zeta 0.017-0.036, Q 14-29, `accord-ratchet-is-a-lightly-damped-resonance`).  A STEP in
LKAS authority excites every frequency, so a ~1 Hz collapse/recovery cycle could ring a 6-9 Hz mode
once per collapse and produce exactly the felt symptom.  The oscillator hypothesis and the exciter
hypothesis are DIFFERENT, and only the first is refuted.

THE TEST: onset-aligned averaging.  Align on authority-collapse edges, average the 6-9 Hz band
envelope of column torque around the edge, and compare against edges shuffled to random times inside
the same episodes.  If 6-9 Hz energy rises after a collapse edge and not after a shuffled one, the
curve is a 6-9 Hz EXCITER even though it is not a 6-9 Hz oscillator.

ALSO HERE: the second candidate the tracer raised -- `gp-0x6ac2`, a back-drive relay feeding the
DAMPER's output ceiling (`0xC77A0`, X=[300,800] Y=[512,1024]).  `accord-damper-cannot-reach-micro-
regime` measured the damper product at ZERO on 100 % of the micro regime, and a ceiling on an
identically-zero output does nothing.  §3 confirms or refutes that from the caches, in the OVERRIDE
regime specifically -- because the prior measurement was hands-off and the damper's rate dead zone
(12.7 deg/s) may well be open during an override.

Usage:  python studies/v95-override/v95_override_onset_ringing.py
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v95_override_authority_chatter import CX, authority, episodes  # noqa: E402
from v95_override_exposure import channels  # noqa: E402
from v95_rez_lib import BUILD, CACHES, hdr  # noqa: E402

RNG = np.random.default_rng(950824)
PRE, POST = 40, 80              # samples: 0.4 s before, 0.8 s after an edge, at 100 Hz
ROUTES = ["r77", "r73", "r79", "r6e", "r76", "r6f", "r71", "r67x", "r68x", "r75"]


def envelope(x, fs, lo, hi):
    """Analytic-magnitude envelope of the band, via an FFT band-pass (whole-signal, no windows)."""
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, len(x))
    # magnitude envelope from the Hilbert pair, built on the same rfft grid
    Z = np.fft.rfft(y)
    Z[1:] *= 2.0
    return np.abs(np.fft.irfft(Z, len(x)) + 1j * 0 + 0)  # |analytic| via one-sided reconstruction


def hilb_env(x, fs, lo, hi):
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1.0 / fs)
    X[(np.abs(f) < lo) | (np.abs(f) > hi)] = 0
    X[f < 0] = 0
    X[f > 0] *= 2.0
    return np.abs(np.fft.ifft(X))


def edges_of(A, s, x, thr=127.0):
    """Downward crossings of the authority signal through mid-scale = a collapse onset."""
    a = A[s:x]
    d = np.flatnonzero((a[:-1] >= thr) & (a[1:] < thr))
    return [s + int(i) for i in d if PRE <= i < (x - s) - POST]


def part1():
    hdr("1.  ONSET-ALIGNED 6-9 Hz ENERGY AROUND AN AUTHORITY-COLLAPSE EDGE")
    print("  Is the curve a 6-9 Hz EXCITER even though it is not a 6-9 Hz oscillator?")
    print(f"  {'route':6s} {'arm':8s} {'edges':>6s} | {'pre 6-9':>9s} {'post 6-9':>9s} "
          f"{'post/pre':>9s} | {'SHUFFLED post/pre':>18s} {'verdict':>10s}")
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        fs, mov = B["fs"], B["v"] > 0.5
        _, A = authority(np.abs(B["ctq"]), fs)
        env = hilb_env(B["tq"], fs, 6.0, 9.0)
        for tag, m in (("OVR", B["lat"] & B["press"] & mov),
                       ("MAN/ON", (~B["lat"]) & B["press"] & mov)):
            eps = episodes(m, B["t"], fs, min_dur=1.5)
            ed, sh = [], []
            for s, x in eps:
                e = edges_of(A, s, x)
                ed += e
                if e:
                    sh += list(RNG.integers(s + PRE, x - POST, size=len(e)))
            if len(ed) < 12:
                continue

            def ratio(idx):
                pre = np.array([env[i - PRE:i].mean() for i in idx])
                post = np.array([env[i:i + POST].mean() for i in idx])
                return pre.mean(), post.mean(), post.mean() / max(pre.mean(), 1e-12)
            p0, p1, rr = ratio(ed)
            _, _, rs = ratio(sh)
            v = "EXCITER" if (rr > 1.15 and rr > 1.2 * rs) else "no effect"
            print(f"  {r:6s} {tag:8s} {len(ed):6d} | {p0:9.1f} {p1:9.1f} {rr:9.3f} | "
                  f"{rs:18.3f} {v:>10s}")
    print("  ⇒ post/pre >> 1 AND >> the shuffled ratio would make the collapse edge a 6-9 Hz")
    print("    exciter.  A ratio near the shuffled one means the edge carries no 6-9 Hz kick.")


def part2():
    hdr("2.  WHAT DOES 6-9 Hz COLUMN ENERGY ACTUALLY DO IN OVERRIDE vs THE OTHER ARMS?")
    print("  Amplitude, not impedance -- this is the quantity that corresponds to a felt symptom.")
    print(f"  {'route':6s} {'build':12s} | " +
          "  ".join(f"{k:>10s}" for k in ("ENG/OFF", "OVR", "MAN/ON", "MAN/OFF")) +
          " | OVR/MAN-ON  OVR/ENG-OFF")
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        fs, mov = B["fs"], B["v"] > 0.5
        env = hilb_env(B["tq"], fs, 6.0, 9.0)
        arms = {"ENG/OFF": B["lat"] & (~B["press"]) & mov, "OVR": B["lat"] & B["press"] & mov,
                "MAN/ON": (~B["lat"]) & B["press"] & mov,
                "MAN/OFF": (~B["lat"]) & (~B["press"]) & mov}
        med = {k: (float(np.median(env[m])) if m.sum() > 300 else np.nan)
               for k, m in arms.items()}
        print(f"  {r:6s} {BUILD.get(r,'?'):12s} | " +
              "  ".join(f"{med[k]:10.1f}" for k in ("ENG/OFF", "OVR", "MAN/ON", "MAN/OFF")) +
              f" | {med['OVR']/med['MAN/ON']:10.2f} {med['OVR']/med['ENG/OFF']:11.2f}")
    print("  🛑 OVR/MAN-ON is the ENGAGEMENT contrast IN THE SYMPTOM REGIME -- both arms hands-on,")
    print("     so the grip confound is matched out.  That is the number the operator's report")
    print("     should be judged against, not the hands-off impedance ratio.")


def part3():
    hdr("3.  IS THE BASE-ASSIST DAMPER STILL ZERO IN THE OVERRIDE REGIME?")
    print("  `accord-damper-cannot-reach-micro-regime` measured the product zero on 100 % of the")
    print("  micro regime -- but HANDS-OFF.  Override may open the 12.7 deg/s rate dead zone.")
    print("  FactorC dead zone ~35 km/h (9.7 m/s); FactorE dead zone 60 counts = 12.7 deg/s.")
    print(f"  {'route':6s} {'arm':8s} {'n':>7s} | {'v>9.7 m/s':>10s} {'|rate|>12.7':>12s} "
          f"{'BOTH open':>10s}")
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        mov = B["v"] > 0.5
        for tag, m in (("OVR", B["lat"] & B["press"] & mov),
                       ("ENG/OFF", B["lat"] & (~B["press"]) & mov)):
            if m.sum() < 300:
                continue
            fc = B["v"][m] > 9.7
            fe = np.abs(B["wdeg"][m]) > 12.7
            print(f"  {r:6s} {tag:8s} {int(m.sum()):7d} | {fc.mean():10.3f} {fe.mean():12.3f} "
                  f"{(fc & fe).mean():10.3f}")
    print("  ⇒ 'BOTH open' is the fraction of the arm where the damper product can be non-zero.")
    print("    If it stays near zero in OVERRIDE too, the gp-0x6ac2 ceiling candidate dies without")
    print("    a flight -- a ceiling on an identically-zero output does nothing.")


if __name__ == "__main__":
    part1()
    part2()
    part3()
