#!/usr/bin/env python3
"""CONTROLS FIRST.  Every damping estimator in this re-score, fed synthetic modes of KNOWN Q
through the EXACT pipeline that scored the car, with the recovered values reported.

WHY THIS EXISTS.  The linewidth family has a structural defect: the local floor is the median of
the search band excluding +-0.6 Hz of the peak, so a BROAD mode (Q=2.4 => FWHM 3.2 Hz) IS the
floor -- the peak barely clears it, the half-power points collapse onto the peak, and Q comes back
enormous.  The 2-DOF periodogram compounds it: the tallest single bin is a few bins wide whatever
the true Q, so the width measured is the FFT's, not the mode's.  `catA_linewidth.py`,
`C31.q_of`/`_grind2_lib.q_of`/`_r47_imu_lib.q_of`, and `qd_lib.linewidth` are all in that family.

FIVE ESTIMATORS, ONE TABLE:
  lw      qd_lib.linewidth               raw zero-padded periodogram FWHM  (the suspect)
  welch   4 x 50%-overlap sub-windows    averaged periodogram FWHM        (8-DOF, less spiky)
  phase   qd_phase.phase_q               phase structure-function slope   (non-spectral)
  env     qd_lib.envelope_stats          burst duty / CV / duration       (non-spectral)
  ring    qd_lib.ringdown_zeta           envelope decay after the drive stops (the physical one)

TWO INJECTION CONVENTIONS, because they answer different questions:
  prom  : amplitude solved so the recovered PROMINENCE is 70x   (what studies/damping-q/qd_power.py used)
  snr   : injected band power fixed at 40x the bed's own 6-10 Hz power -- the realistic one,
          matching the measured engaged/manual band-power excess, and it does NOT let the
          estimator renormalise its way out of a broad line

Usage:  python studies/damping-q/qd_control.py
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
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                       # noqa: E402
import qd_win as W                                                       # noqa: E402
from qd_phase import phase_q                                             # noqa: E402

RNG = np.random.default_rng(20260809)
F0 = 7.79
QGRID = [1, 2, 3, 5, 10, 25, 50, 100, 250, np.inf]
NREP = 50
OUT = {}


def hdr(s):
    print("\n" + "=" * 118 + "\n" + s + "\n" + "=" * 118, flush=True)


def band_power(x, fs, lo=6.0, hi=10.0):
    b = butter(2, [lo, hi], btype="band", fs=fs)
    return float(np.var(filtfilt(*b, np.asarray(x, float))))


def welch_linewidth(x, fs, nsub=4, flo=Q.FLO, fhi=Q.FHI):
    """FWHM of the WELCH-averaged spectrum: nsub half-overlapped sub-windows, so ~8 DOF per bin
    instead of 2.  Costs a factor nsub/2 in frequency resolution and buys a spectrum whose
    single-bin spikes are averaged down."""
    x = np.asarray(x, float)
    n = len(x)
    nw = n // ((nsub + 1) // 2) if nsub > 1 else n
    nw = max(nw, 64)
    hop = nw // 2
    P = None
    cnt = 0
    for j in range(0, n - nw + 1, hop):
        seg = x[j:j + nw]
        r = np.arange(nw)
        c = np.polyfit(r, seg, 1)
        seg = seg - (c[0] * r + c[1])
        S = np.abs(np.fft.rfft(seg * np.hanning(nw), n=nw * Q.PAD)) ** 2
        P = S if P is None else P + S
        cnt += 1
    if cnt == 0:
        return dict(f0=np.nan, fwhm=np.nan, q_app=np.nan)
    P /= cnt
    f = np.fft.rfftfreq(nw * Q.PAD, 1.0 / fs)
    m = (f >= flo) & (f <= fhi)
    idx = np.flatnonzero(m)
    j = int(idx[np.argmax(P[idx])])
    f0, P0 = float(f[j]), float(P[j])
    far = m & (np.abs(f - f0) > 0.6)
    floor = float(np.median(P[far])) if far.any() else 0.0
    lo = Q._cross(f, P - floor, j, (P0 - floor) / 2.0, -1)
    hi = Q._cross(f, P - floor, j, (P0 - floor) / 2.0, +1)
    if lo is None or hi is None or hi <= lo:
        return dict(f0=f0, fwhm=np.nan, q_app=np.nan, wl=1.4416 / (nw / fs))
    return dict(f0=f0, fwhm=float(hi - lo), q_app=float(f0 / (hi - lo)),
                wl=1.4416 / (nw / fs), prom=P0 / floor if floor else np.inf)


def inject_snr(bed, fs, f0, q, snr, fam, rng):
    """Injected 6-10 Hz band power fixed at `snr` x the bed's own.  No renormalisation."""
    s = (Q.resonance if fam == "mode" else Q.diffusing_tone)(len(bed), fs, f0, q, rng)
    bp_s = band_power(s, fs)
    bp_b = band_power(bed, fs)
    if bp_s <= 0:
        return np.asarray(bed, float)
    return np.asarray(bed, float) + s * np.sqrt(snr * bp_b / bp_s)


def ringdown_zeta(env, fs, f0, i0, fit_s=2.0, floor_from=2.5):
    """The EXACT decay fit studies/damping-q/qd_final.py used on the car, isolated so it can be controlled."""
    post = env[i0:]
    if len(post) < int((floor_from + 0.5) * fs):
        return np.nan
    floor = float(np.percentile(post[int(floor_from * fs):], 25))
    tt = np.arange(len(post)) / fs
    m = tt <= fit_s
    y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
    if np.count_nonzero(y > 1e-4) < 20:
        return np.nan
    c = np.polyfit(tt[m], np.log(y), 1)
    lam = -float(c[0])
    return lam / (2 * np.pi * f0)


# =============================================================================================
hdr("C1  THE HEADLINE CONTROL -- feed KNOWN Q through the exact pipelines that scored the car")
beds = {}
for nw, tlab in [(1024, "10.1 s"), (2048, "20.3 s")]:
    beds[tlab] = [r for b in W.ROUTES for r in W.windows(b, nw, engaged=False)]
res = {}
for tlab, nw in [("10.1 s", 1024), ("20.3 s", 2048)]:
    pool = beds[tlab]
    qfloor = F0 * nw / (Q.HANN_FWHM * 101.1)
    for conv in ("snr", "prom"):
        print(f"\n  ---- T = {tlab}   injection = {conv}   "
              f"(linewidth window-limited ceiling Q = {qfloor:.1f}) ----")
        print(f"      {'Q_true':>7s} | {'lw':>22s} | {'welch':>22s} | {'phase':>22s} | "
              f"{'env CV':>7s} {'duty':>6s}")
        rows = []
        for qt in QGRID:
            lw, we, ph, cv, du = [], [], [], [], []
            for _ in range(NREP):
                bed = np.asarray(pool[RNG.integers(0, len(pool))]["x"], float)
                fs = pool[0]["fs"]
                if conv == "snr":
                    y = inject_snr(bed, fs, F0, qt, 40.0, "mode", RNG)
                else:
                    y, _ = Q.inject(bed, fs, F0, qt, 70.0, "mode", RNG)
                a = Q.linewidth(y, fs)
                b = welch_linewidth(y, fs)
                c = phase_q(y, fs, F0)
                d = Q.envelope_stats(y, fs, F0, thresh_k=1.5)
                for arr, v in ((lw, a["q_app"]), (we, b["q_app"]), (ph, c["q_phase"]),
                               (cv, d["cv"]), (du, d["duty"])):
                    if np.isfinite(v):
                        arr.append(v)

            def med(a):
                return (float(np.median(a)), float(np.percentile(a, 16)),
                        float(np.percentile(a, 84))) if a else (np.nan, np.nan, np.nan)
            L, Wl, Ph = med(lw), med(we), med(ph)
            rows.append(dict(q_true=float(qt), lw=L, welch=Wl, phase=Ph,
                             cv=float(np.median(cv)) if cv else np.nan,
                             duty=float(np.median(du)) if du else np.nan))
            print(f"      {str(qt):>7s} | {L[0]:8.1f} [{L[1]:5.1f},{L[2]:6.1f}] | "
                  f"{Wl[0]:8.1f} [{Wl[1]:5.1f},{Wl[2]:6.1f}] | "
                  f"{Ph[0]:8.1f} [{Ph[1]:5.1f},{Ph[2]:6.1f}] | {rows[-1]['cv']:7.3f} "
                  f"{rows[-1]['duty']:6.3f}")
        res[f"{tlab}/{conv}"] = rows
OUT["C1"] = res

# =============================================================================================
hdr("C2  MONOTONICITY -- can ANY of them even ORDER two builds correctly?")
mono = {}
for key, rows in res.items():
    qt = np.array([r["q_true"] for r in rows if np.isfinite(r["q_true"])])
    print(f"\n  {key}")
    for est in ("lw", "welch", "phase"):
        v = np.array([r[est][0] for r in rows if np.isfinite(r["q_true"])])
        ok = np.isfinite(v)
        if ok.sum() < 4:
            print(f"    {est:6s}  too few finite values")
            continue
        rho = np.corrcoef(np.log(qt[ok]), np.log(np.clip(v[ok], 1e-9, None)))[0, 1]
        span = np.nanmax(v[ok]) / max(np.nanmin(v[ok]), 1e-9)
        # scatter of a single window, geometric, averaged across the grid
        sc = np.nanmedian([r[est][2] / max(r[est][1], 1e-9) for r in rows
                           if np.isfinite(r[est][1]) and r[est][1] > 0])
        print(f"    {est:6s}  log-log r = {rho:+.3f}   readout span over Q_true 1..inf = "
              f"{span:6.2f}x   typical p16-p84 spread of ONE window = {sc:6.2f}x")
        mono[f"{key}/{est}"] = dict(r=float(rho), span=float(span), spread=float(sc))
    for est in ("cv", "duty"):
        v = np.array([r[est] for r in rows if np.isfinite(r["q_true"])])
        ok = np.isfinite(v)
        if ok.sum() >= 4:
            rho = np.corrcoef(np.log(qt[ok]), v[ok])[0, 1]
            print(f"    {est:6s}  log-Q vs value r = {rho:+.3f}   range "
                  f"{np.nanmin(v[ok]):.3f} -> {np.nanmax(v[ok]):.3f}")
            mono[f"{key}/{est}"] = dict(r=float(rho))
OUT["C2"] = mono

# =============================================================================================
hdr("C3  RING-DOWN CONTROL -- synthetic decays of KNOWN zeta through the exact edge fit")
pool = [np.asarray(r["x"], float) for b in W.ROUTES for r in W.windows(b, 1024, engaged=False)]
fs = 101.1
npre = int(3 * fs)
rows = []
print(f"      {'zeta_true':>9s} {'Q_true':>7s} | {'zeta_hat':>22s} | {'Q_hat':>8s}  "
      f"(n usable / {NREP})")
for zt in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20):
    got = []
    for _ in range(NREP):
        bed = pool[RNG.integers(0, len(pool))]
        n = int(7 * fs)
        bed = np.resize(bed, n)
        tt = np.arange(n) / fs
        lam = zt * 2 * np.pi * F0
        amp = np.where(tt < 3.0, 1.0, np.exp(-lam * (tt - 3.0)))
        # amplitude set to the measured engaged/manual band-power excess (~40x power = 6.3x amp)
        s = amp * np.sin(2 * np.pi * F0 * tt + RNG.uniform(0, 2 * np.pi))
        y = bed + s * np.sqrt(40.0 * band_power(bed, fs) / max(band_power(s, fs), 1e-12))
        b = butter(2, [F0 - 1.5, F0 + 1.5], btype="band", fs=fs)
        env = np.abs(hilbert(filtfilt(*b, y)))
        z = ringdown_zeta(env, fs, F0, npre)
        if np.isfinite(z) and z > 0:
            got.append(z)
    g = np.array(got) if got else np.array([np.nan])
    rows.append(dict(zeta_true=zt, q_true=1 / (2 * zt), zeta_med=float(np.median(g)),
                     zeta_p16=float(np.percentile(g, 16)), zeta_p84=float(np.percentile(g, 84)),
                     n=len(got)))
    print(f"      {zt:9.3f} {1/(2*zt):7.1f} | {np.median(g):8.4f} "
          f"[{np.percentile(g,16):6.4f},{np.percentile(g,84):7.4f}] | "
          f"{1/(2*np.median(g)):8.1f}  ({len(got)}/{NREP})")
OUT["C3"] = rows
zt = np.array([r["zeta_true"] for r in rows])
zh = np.array([r["zeta_med"] for r in rows])
ok = np.isfinite(zh)
print(f"\n    log-log r(zeta_true, zeta_hat) = "
      f"{np.corrcoef(np.log(zt[ok]), np.log(zh[ok]))[0,1]:+.3f}   "
      f"median |bias| = {np.median(np.abs(zh[ok]/zt[ok] - 1))*100:.0f}%")

# =============================================================================================
hdr("C4  IS THE 'PEAK FOREST' REAL?  same census on manual and on a phase-randomised surrogate")


def census(x, fs, T_label):
    f, P = Q.hires_spec(x, fs)
    m = (f >= 4.0) & (f <= 12.0)
    fm, Pm = f[m], P[m]
    floor = np.median(Pm)
    wl = Q.HANN_FWHM / (len(x) / fs)
    cand = []
    for j in range(1, len(Pm) - 1):
        if Pm[j] >= Pm[j - 1] and Pm[j] > Pm[j + 1] and Pm[j] > 8 * floor:
            cand.append((float(Pm[j]), float(fm[j])))
    cand.sort(reverse=True)
    picked = []
    for p, fq in cand:
        if all(abs(fq - q) > 3 * wl for _, q in picked):
            picked.append((p / floor, fq))
        if len(picked) >= 8:
            break
    return picked


def surrogate(x, rng):
    """Phase-randomised surrogate: identical power spectrum, destroyed phase structure.  A peak
    that survives this is NOT evidence of coherence -- it is in the amplitude spectrum either way.
    Used here the other way round: to show what the PEAK COUNT does under a null with the same
    coloured background."""
    X = np.fft.rfft(x - x.mean())
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


for b, r in W.ROUTES.items():
    d = W.load(r)
    fsr = d["fs"]
    lat = np.asarray(d["cc_lat"], float) > 0.5
    x = np.asarray(d[W.SIG], float)
    eng = sorted(Q.contiguous_runs(lat, d["t"], int(20 * fsr)), key=lambda ab: ab[0] - ab[1])
    man = sorted(Q.contiguous_runs(~lat, d["t"], int(20 * fsr)), key=lambda ab: ab[0] - ab[1])
    a, bb = eng[0]
    ce = census(x[a:bb], fsr, "eng")
    print(f"\n  {b:5s}  ENGAGED {(bb-a)/fsr:6.1f} s : {len(ce)} peaks, prominence "
          f"{[round(p,0) for p, _ in ce]}")
    if man:
        c, dd2 = man[0]
        n = min(dd2 - c, bb - a)
        cm = census(x[c:c + n], fsr, "man")
        print(f"         MANUAL  {n/fsr:6.1f} s : {len(cm)} peaks, prominence "
              f"{[round(p,0) for p, _ in cm]}")
    # white-noise null of the SAME length -- what does the census return on pure noise?
    wn = census(RNG.standard_normal(bb - a), fsr, "wn")
    sg = census(surrogate(x[a:bb], RNG), fsr, "surr")
    print(f"         WHITE NOISE, same length: {len(wn)} peaks, prominence "
          f"{[round(p,0) for p, _ in wn]}")
    print(f"         PHASE-RANDOMISED surrogate: {len(sg)} peaks, prominence "
          f"{[round(p,0) for p, _ in sg]}")
    OUT.setdefault("C4", {})[b] = dict(eng=[[p, f] for p, f in ce],
                                       white=[[p, f] for p, f in wn],
                                       surr=[[p, f] for p, f in sg])

json.dump(OUT, open(ROOT / "_scratch/cache/r6f" / "qd_control.json", "w"), indent=1, default=float)
print("\nwrote _scratch/cache/r6f/qd_control.json")
