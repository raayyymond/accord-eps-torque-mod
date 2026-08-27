#!/usr/bin/env python3
"""D5 ss6-9 -- the reconciliation tests.

ss3 located a 7.2-8.0 Hz line and a 18-22 Hz line, and ss4 showed they do NOT track (so 7.79 Hz is
not a subharmonic of 20.9 Hz). ss5 found the 12-28 Hz carrier's ENVELOPE is modulated at 7.71 Hz
above a phase-randomised surrogate. This file asks the four questions that turns that into a verdict:

  ss6  STRICT-BAND prominence per speed bin, with the WHEEL ORDER annotated.
       🛑 ss3's free 5-12 Hz locate reads 9.61 Hz at 15-25 m/s and 12.01 Hz at 25+ -- those are
       0.489*v, i.e. TYRE ORDER 1, not the ratchet. Any "the ratchet is speed-independent" claim
       has to be made in the strict band with the order excluded.
  ss7  SIDEBANDS. True AM of a 20.9 Hz carrier at 7.79 Hz puts lines at 13.1 and 28.7 Hz. Look.
  ss8  COHERENCE. If the 7.8 Hz thing you FEEL is the envelope of the 21 Hz thing you HEAR, then the
       6-9 Hz band-passed signal and the 12-28 Hz envelope must be COHERENT. Null = circular shift,
       which preserves both power spectra exactly and destroys only the timing relation.
  ss9  CHANNEL. Which recorded channel is the driver torsion-bar sensor, and are both lines in it?
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r59_lib as L  # noqa: E402

OUT = ROOT / "_scratch/out/_d5_coupling.json"
RNG = np.random.default_rng(590805)
BUILDS = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37", "V65/r3a",
          "V65/r3b", "V67/r47", "V68/r4e", "V71B/r54", "V71C/r58", "V72/r59"]
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 1e9)]
VN = ["0-2", "2-4", "4-8", "8-15", "15-25", "25+"]
CARRIER = (12.0, 28.0)
CIRC = L.CIRC


def segs_of(build):
    B = G.BUILDS[build]
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if p.exists() and s not in L.PARKED.get(build, []):
            yield s, C.load(s, B["cache"], B["pfx"])


def vbin(v):
    for i, (lo, hi) in enumerate(VB):
        if lo <= v < hi:
            return i
    return len(VB) - 1


def hilbert(xr):
    n = len(xr)
    X = np.fft.fft(xr)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[0] = 1
        h[1:(n + 1) // 2] = 2
    return np.fft.ifft(X * h)


def bandpass(x, fs, lo, hi):
    x = np.asarray(x, float)
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    y = x - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = X[m]
    return np.fft.irfft(H, n=len(y))


# ------------------------------------------------------------------ ss6 strict bands -------------
def strict_bands(nfft=1024, chan="tq"):
    """Averaged engaged periodogram per speed bin; prominence measured in the STRICT bands."""
    acc = {i: None for i in range(len(VB))}
    K = {i: 0 for i in range(len(VB))}
    vsum = {i: [] for i in range(len(VB))}
    fref = None
    for b in BUILDS:
        for s, d in segs_of(b):
            if chan not in d:
                continue
            fs = G.fs_of(d)
            f = np.fft.rfftfreq(nfft, 1 / fs)
            fref = f if fref is None else fref
            x = np.asarray(d[chan], float)
            v = np.abs(np.asarray(d["cs_v"], float))
            m = np.asarray(d["cc_lat"], float) > 0.5
            for a, e in C.runs_of(m, d["t"], nfft):
                for i in range(a, e - nfft + 1, nfft // 2):
                    P = C.periodogram(x[i:i + nfft], fs, nfft, True)
                    if P is None:
                        continue
                    vm = float(np.mean(v[i:i + nfft]))
                    j = vbin(vm)
                    acc[j] = P.copy() if acc[j] is None else acc[j] + P
                    K[j] += 1
                    vsum[j].append(vm)
    return fref, acc, K, vsum


def main():
    L.install_fs()
    res = {}

    # ---------------------------------------------------------------- ss6 ----------------------
    f, acc, K, vsum = strict_bands()
    L.hdr("ss6  STRICT-BAND prominence, engaged, `tq`, NFFT 1024 -- with the TYRE ORDER annotated")
    print(f"  {'v (m/s)':<9}{'K':>6}{'v med':>8}{'order1':>8}{'order2':>8}   "
          f"{'6-9 Hz':>22}{'18-22 Hz':>22}{'24-28 Hz':>22}{'40-49':>18}")
    rows = {}
    for i, nm in enumerate(VN):
        if not K[i]:
            print(f"  {nm:<9}{0:>6}   -- UNPOWERED")
            continue
        P = acc[i] / K[i]
        R = G.prom_spectrum(f, P)
        vm = float(np.median(vsum[i]))
        o1, o2 = vm / CIRC, 2 * vm / CIRC
        cells = {}
        s = f"  {nm:<9}{K[i]:>6}{vm:>8.2f}{o1:>8.2f}{o2:>8.2f}   "
        for lo, hi, lab in ((6, 9, "6-9"), (18, 22, "18-22"), (24, 28, "24-28"), (40, 49, "40-49")):
            f0, p0 = G.locate(f, P, lo, hi, R=R)
            cells[lab] = dict(f0=f0, prom=p0)
            w = 22 if lab != "40-49" else 18
            s += f"{f0:>8.2f}Hz p{p0:>6.2f}".rjust(w)
        rows[nm] = dict(K=K[i], v=vm, order1=o1, cells=cells)
        print(s)
    res["strict"] = rows
    print("\n  order1 = v/2.080 m (tyre circumference, memory accord-v57-confirms-wheel-order).")
    print("  🛑 a 6-9 Hz reading is CONTAMINATED by tyre order 1 for v in [12.5, 18.7] m/s.")

    # ---------------------------------------------------------------- ss7 sidebands -------------
    L.hdr("ss7  SIDEBAND CHECK at creep -- true AM of a 20.9 Hz carrier at 7.79 Hz => 13.1 / 28.7 Hz")
    P02 = acc[0] / K[0] if K[0] else None
    P24 = acc[1] / K[1] if K[1] else None
    for nm, P in (("0-2 m/s", P02), ("2-4 m/s", P24)):
        if P is None:
            continue
        R = G.prom_spectrum(f, P)
        fc, pc = G.locate(f, P, 18, 22, R=R)
        fr, pr = G.locate(f, P, 6, 9, R=R)
        print(f"\n  {nm}:  carrier {fc:.3f} Hz (prom {pc:.2f})   ratchet {fr:.3f} Hz (prom {pr:.2f})"
              f"   predicted sidebands {fc-fr:.3f} / {fc+fr:.3f} Hz")
        for lab, target in (("lower sideband", fc - fr), ("upper sideband", fc + fr),
                            ("2x ratchet", 2 * fr), ("3x ratchet", 3 * fr)):
            j = int(np.argmin(np.abs(f - target)))
            w = slice(max(0, j - 3), j + 4)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            print(f"    {lab:<16} predicted {target:>7.3f} Hz  ->  local max "
                  f"{f[k]:>7.3f} Hz prominence {R[k]:>6.2f}")
        res.setdefault("sidebands", {})[nm] = dict(
            fc=fc, fr=fr, spectrum=[[float(f[j]), float(R[j])]
                                    for j in range(len(f)) if 4 <= f[j] <= 34])

    # ---------------------------------------------------------------- ss8 coherence -------------
    L.hdr("ss8  COHERENCE: is the 6-9 Hz signal the ENVELOPE of the 12-28 Hz carrier?")
    print("  MSC(bandpass(tq,5-12) , |analytic(tq,12-28)|) at 6-9 Hz, over engaged runs >= 20.5 s.")
    print("  NULL = circular shift of the envelope by a random lag >= 5 s (both spectra preserved).")
    NSEG, NRUN = 256, 2048
    for label, (vlo, vhi) in (("creep 0-4", (0.0, 4.0)), ("mid 4-15", (4.0, 15.0)),
                              ("fast 15+", (15.0, 1e9))):
        obs, null, nrun = [], [], 0
        for b in BUILDS:
            for s, d in segs_of(b):
                fs = G.fs_of(d)
                x = np.asarray(d["tq"], float)
                v = np.abs(np.asarray(d["cs_v"], float))
                m = np.asarray(d["cc_lat"], float) > 0.5
                for a, e in C.runs_of(m, d["t"], NRUN):
                    xw = x[a:e]
                    if not np.all(np.isfinite(xw)) or not (vlo <= float(np.mean(v[a:e])) < vhi):
                        continue
                    lo = bandpass(xw, fs, 5.0, 12.0)
                    env = np.abs(hilbert(bandpass(xw, fs, *CARRIER)))
                    env = env - env.mean()
                    c, fc = msc(lo, env, fs, NSEG)
                    if c is None:
                        continue
                    band = (fc >= 6) & (fc <= 9)
                    obs.append(float(np.max(c[band])))
                    lag = int(RNG.integers(int(5 * fs), len(env) - int(5 * fs)))
                    c2, _ = msc(lo, np.roll(env, lag), fs, NSEG)
                    null.append(float(np.max(c2[band])))
                    nrun += 1
        if nrun < 5:
            print(f"  {label:<12} -- underpowered, {nrun} runs")
            continue
        obs, null = np.array(obs), np.array(null)
        d_ = obs - null
        draws = np.array([np.median(d_[RNG.integers(0, len(d_), len(d_))]) for _ in range(4000)])
        lo_, hi_ = np.percentile(draws, [2.5, 97.5])
        print(f"  {label:<12} runs={nrun:<4d}  peak MSC in 6-9 Hz  OBS {np.median(obs):.3f}   "
              f"SHIFTED {np.median(null):.3f}   paired diff {np.median(d_):+.3f} "
              f"[{lo_:+.3f}, {hi_:+.3f}]")
        res.setdefault("coherence", {})[label] = dict(
            nrun=nrun, obs=float(np.median(obs)), null=float(np.median(null)),
            diff=float(np.median(d_)), lo=float(lo_), hi=float(hi_))

    # ---------------------------------------------------------------- ss9 channels --------------
    L.hdr("ss9  WHICH CHANNEL?  prominence of each line per channel, engaged creep (< 4 m/s)")
    chans = ["tq", "cs_tq", "ang", "cs_ang", "rate_c", "rate_f", "e4tq"]
    print(f"  {'channel':<10}{'K':>6}   {'6-9 Hz':>24}{'18-22 Hz':>24}")
    for ch in chans:
        accu, kk, fr = None, 0, None
        for b in BUILDS:
            for s, d in segs_of(b):
                if ch not in d:
                    continue
                x = np.asarray(d[ch], float)
                if not np.any(np.abs(x) > 0):
                    continue
                fs = G.fs_of(d)
                fr = np.fft.rfftfreq(512, 1 / fs) if fr is None else fr
                v = np.abs(np.asarray(d["cs_v"], float))
                m = np.asarray(d["cc_lat"], float) > 0.5
                for a, e in C.runs_of(m, d["t"], 512):
                    for i in range(a, e - 511, 256):
                        if float(np.mean(v[i:i + 512])) >= 4.0:
                            continue
                        P = C.periodogram(x[i:i + 512], fs, 512, True)
                        if P is None:
                            continue
                        accu = P.copy() if accu is None else accu + P
                        kk += 1
        if not kk:
            print(f"  {ch:<10}{0:>6}   -- absent / all-zero on this corpus")
            continue
        P = accu / kk
        R = G.prom_spectrum(fr, P)
        a1 = G.locate(fr, P, 6, 9, R=R)
        a2 = G.locate(fr, P, 18, 22, R=R)
        print(f"  {ch:<10}{kk:>6}   {a1[0]:>10.3f} Hz prom {a1[1]:>6.2f}"
              f"{a2[0]:>10.3f} Hz prom {a2[1]:>6.2f}")
        res.setdefault("channels", {})[ch] = dict(K=kk, f69=a1[0], p69=a1[1],
                                                  f1822=a2[0], p1822=a2[1])

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


def msc(a, b, fs, nseg):
    """Welch magnitude-squared coherence, Hann, 50% overlap. Returns (C, f) or (None, None)."""
    n = min(len(a), len(b))
    if n < 4 * nseg:
        return None, None
    w = np.hanning(nseg)
    Saa = Sbb = Sab = 0.0
    k = 0
    for i in range(0, n - nseg + 1, nseg // 2):
        A = np.fft.rfft((a[i:i + nseg] - a[i:i + nseg].mean()) * w)
        B = np.fft.rfft((b[i:i + nseg] - b[i:i + nseg].mean()) * w)
        Saa = Saa + np.abs(A) ** 2
        Sbb = Sbb + np.abs(B) ** 2
        Sab = Sab + A * np.conj(B)
        k += 1
    if k < 6:
        return None, None
    den = Saa * Sbb
    Cc = np.where(den > 0, np.abs(Sab) ** 2 / np.where(den > 0, den, 1), 0.0)
    return Cc, np.fft.rfftfreq(nseg, 1 / fs)


if __name__ == "__main__":
    main()
