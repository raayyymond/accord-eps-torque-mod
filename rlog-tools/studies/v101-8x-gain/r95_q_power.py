#!/usr/bin/env python3
r"""🛑 IS Q MEASURABLE FROM ONE 15-30 s EPISODE?  And what IS measurable instead?

The orchestrator's question, verbatim: *"at Welch df 0.099 Hz over one short episode, what is the
CI on Q?  If Q on a single 20 s episode has a CI so wide that 47.4 and 25 are indistinguishable,
then Q is the wrong primary endpoint."*

METHOD.  Draw 500 random CONTIGUOUS stretches of length T from route 95's engaged runs.  On each,
run three sharpness estimators and the peak-relative shape ratio.  Report the spread of the
ESTIMATE, against the whole-route reference.

  E1  WELCH -3 dB WIDTH.  nfft = the largest power of two that fits T/2, 50 % overlap.  Q = f/BW.
  E2  ACF DECAY.  Band-pass 17-30 Hz (MUCH wider than the 0.49 Hz resonance, so the RESONANCE sets
      the decay, not the filter), autocorrelate, take the analytic envelope, fit
      env(tau) ~ exp(-2*pi*f_n*zeta*tau) over lags 0.05-0.40 s.  Q = 1/(2*zeta).  This uses ALL
      ~2-3 k samples instead of ~5 spectral bins, so it should be far more efficient.
  E3  PEAK-RELATIVE SHAPE RATIO.  Locate the 18-30 Hz peak on the stretch, band = peak +- 2 Hz,
      control = 32-38 Hz, statistic = RMS(band)/RMS(control).

🛑 CONTROLS RUN FIRST (this kit's estimator returns Q 79.00 on white noise):
   C-WHITE      white noise band-passed 17-30 Hz -- true Q = 23.4/13 = 1.8.  An estimator that
                returns 47 here is measuring its own window, not the car.
   C-SURROGATE  phase-randomised tq -- IDENTICAL PSD, hence IDENTICAL true Q.  A good estimator
                must REPRODUCE the real value here.  This is a POSITIVE control.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import r95_lib as L  # noqa: E402

FS = L.fs()
lat = L.engaged()
tq = L.col("tq")
out = {}
RUNS = [(a, b) for a, b in L.episodes() if (b - a) >= int(15 * FS)]
print(f"FS {FS:.3f}   engaged runs usable: " +
      "  ".join(f"{(b-a)/FS:.1f}s" for a, b in RUNS))


def welch_q(x, nfft):
    if len(x) < nfft:
        return np.nan, np.nan, np.nan
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    P = np.zeros(len(f))
    K = 0
    for i in range(0, len(x) - nfft + 1, nfft // 2):
        seg = np.nan_to_num(x[i:i + nfft] - np.nanmean(x[i:i + nfft]))
        P += np.abs(np.fft.rfft(seg * win)) ** 2
        K += 1
    P /= K
    b = (f >= 18.0) & (f <= 30.0)
    fb, Pb = f[b], P[b]
    i = int(np.argmax(Pb))
    half = Pb[i] / 2
    j = i
    while j > 0 and Pb[j] > half:
        j -= 1
    k = i
    while k < len(Pb) - 1 and Pb[k] > half:
        k += 1
    bw = fb[k] - fb[j]
    return float(fb[i]), float(bw), float(fb[i] / bw) if bw > 0 else np.nan


def acf_q(x):
    """Q from the decay of the band-passed autocorrelation envelope."""
    x = np.nan_to_num(np.asarray(x, float))
    x = x - x.mean()
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    X[(f < 17.0) | (f > 30.0)] = 0
    y = np.fft.irfft(X, n=len(x))
    n = len(y)
    S = np.abs(np.fft.rfft(y, n=2 * n)) ** 2
    ac = np.fft.irfft(S)[:n]
    if ac[0] <= 0:
        return np.nan, np.nan
    ac = ac / ac[0]
    # dominant frequency, for f_n
    Pf = np.abs(np.fft.rfft(y)) ** 2
    ff = np.fft.rfftfreq(n, 1 / FS)
    fn = float(ff[np.argmax(Pf)])
    # analytic envelope of the ACF
    A = np.fft.fft(ac)
    fa = np.fft.fftfreq(n, 1 / FS)
    H = np.zeros(n, complex)
    sel = fa > 0
    H[sel] = 2 * A[sel]
    env = np.abs(np.fft.ifft(H))
    lo, hi = int(0.05 * FS), int(0.40 * FS)
    if hi >= len(env) or np.any(env[lo:hi] <= 0):
        return np.nan, fn
    tau = np.arange(lo, hi) / FS
    sl = np.polyfit(tau, np.log(env[lo:hi]), 1)[0]
    if sl >= 0 or fn <= 0:
        return np.nan, fn
    zeta = -sl / (2 * np.pi * fn)
    return float(1.0 / (2 * zeta)), fn


def shape(x):
    x = np.nan_to_num(np.asarray(x, float))
    x = x - x.mean()
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    P = np.abs(X) ** 2
    b = (f >= 18.0) & (f <= 30.0)
    fp = float(f[b][np.argmax(P[b])])
    m1 = (f >= fp - 2.0) & (f <= fp + 2.0)
    m2 = (f >= 32.0) & (f <= 38.0)
    r1 = np.sqrt(P[m1].sum())
    r2 = np.sqrt(P[m2].sum())
    return float(r1 / max(r2, 1e-12)), fp


rng = np.random.default_rng(77)


def draw(T, src, n=400):
    N = int(T * FS)
    nfft = 1 << int(np.floor(np.log2(max(64, N // 2))))
    qs, zs, ss, fs_ = [], [], [], []
    tries = 0
    while len(ss) < n and tries < n * 20:
        tries += 1
        a, b = RUNS[rng.integers(0, len(RUNS))]
        if b - a <= N:
            continue
        i = a + int(rng.integers(0, b - a - N))
        seg = src[i:i + N]
        fpk, bw, q = welch_q(seg, nfft)
        qa, _fn = acf_q(seg)
        sh, fp = shape(seg)
        qs.append(q)
        zs.append(qa)
        ss.append(sh)
        fs_.append(fp)
    return (np.array(qs, float), np.array(zs, float), np.array(ss, float),
            np.array(fs_, float), nfft)


# ---- CONTROLS FIRST -------------------------------------------------------------------
print("\n" + "=" * 100)
print("🛑 CONTROLS, at T = 25 s")
print("=" * 100)
white = rng.normal(size=len(tq))
bp = L.bandpass(tq, FS, 17.0, 30.0, mask=lat)
sur = np.copy(np.nan_to_num(bp))
for a, b in RUNS:
    X = np.fft.rfft(sur[a:b])
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    sur[a:b] = np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=b - a)
for nm, src in (("C-WHITE   (true Q = 23.4/13 = 1.8)", white),
                ("C-SURROGATE (same PSD as tq ⇒ same true Q)", sur),
                ("MEASURED tq", tq)):
    q, qa, sh, fp, nfft = draw(25.0, src)
    print(f"    {nm:44s} nfft {nfft:5d}  WELCH-Q p10/p50/p90 "
          f"{np.nanpercentile(q,10):6.1f}/{np.nanpercentile(q,50):6.1f}/"
          f"{np.nanpercentile(q,90):6.1f}   ACF-Q {np.nanpercentile(qa,10):6.1f}/"
          f"{np.nanpercentile(qa,50):6.1f}/{np.nanpercentile(qa,90):6.1f}")
    out.setdefault("controls", []).append(
        dict(name=nm, welch_q=[float(np.nanpercentile(q, p)) for p in (10, 50, 90)],
             acf_q=[float(np.nanpercentile(qa, p)) for p in (10, 50, 90)]))

# ---- whole-route reference ------------------------------------------------------------
fpk_ref, bw_ref, q_ref = welch_q(np.concatenate([tq[a:b] for a, b in RUNS]), 1024)
print(f"\n  WHOLE-ROUTE reference (all engaged, nfft 1024): peak {fpk_ref:.2f} Hz  "
      f"width {bw_ref:.2f} Hz  Q {q_ref:.1f}")

# ---- power vs episode length ----------------------------------------------------------
print("\n" + "=" * 100)
print("POWER vs EPISODE LENGTH -- 400 random contiguous stretches of route 95, engaged")
print("=" * 100)
print(f"    {'T (s)':>6s} {'nfft':>6s} {'df Hz':>7s} | {'WELCH-Q p10':>12s} {'p50':>7s} "
      f"{'p90':>7s} {'p90/p10':>8s} | {'ACF-Q p10':>10s} {'p50':>7s} {'p90':>7s} "
      f"{'p90/p10':>8s} | {'SHAPE p10':>10s} {'p50':>7s} {'p90':>7s} | {'f_pk p10-p90':>14s}")
for T in (15, 20, 25, 30, 45, 60, 90):
    q, qa, sh, fp, nfft = draw(float(T), tq)
    if not len(q):
        continue
    qq = [np.nanpercentile(q, p) for p in (10, 50, 90)]
    aa = [np.nanpercentile(qa, p) for p in (10, 50, 90)]
    ssh = [np.nanpercentile(sh, p) for p in (10, 50, 90)]
    ffp = [np.nanpercentile(fp, p) for p in (10, 90)]
    print(f"    {T:6d} {nfft:6d} {FS/nfft:7.3f} | {qq[0]:12.1f} {qq[1]:7.1f} {qq[2]:7.1f} "
          f"{qq[2]/max(qq[0],1e-9):8.2f} | {aa[0]:10.1f} {aa[1]:7.1f} {aa[2]:7.1f} "
          f"{aa[2]/max(aa[0],1e-9):8.2f} | {ssh[0]:10.2f} {ssh[1]:7.2f} {ssh[2]:7.2f} | "
          f"{ffp[0]:6.2f}-{ffp[1]:<7.2f}")
    out.setdefault("power", []).append(
        dict(T=T, nfft=nfft, df=float(FS / nfft), welch_q=[float(v) for v in qq],
             acf_q=[float(v) for v in aa], shape=[float(v) for v in ssh],
             fpk=[float(v) for v in ffp]))

# ---- the decision the orchestrator asked for ------------------------------------------
print("\n" + "=" * 100)
print("🛑 THE DECISION: can a single episode distinguish Q = 47.4 from Q = 25?")
print("   For each T, the fraction of draws whose WELCH-Q and ACF-Q land BELOW 36 (the midpoint")
print("   of 47.4 and 25), i.e. would be called 'damping restored'.  A useful endpoint needs")
print("   this near 0 % on V101 data -- if V101 itself reads 'restored' half the time, the")
print("   estimator cannot decide anything.")
print("=" * 100)
MID = 36.0
print(f"    {'T (s)':>6s} | {'P(WELCH-Q < 36) on V101 data':>30s} | "
      f"{'P(ACF-Q < 36) on V101 data':>29s}")
for T in (15, 20, 25, 30, 45, 60, 90):
    q, qa, sh, fp, nfft = draw(float(T), tq)
    pw = float(np.nanmean(q < MID))
    pa = float(np.nanmean(qa < MID))
    print(f"    {T:6d} | {pw*100:29.1f} % | {pa*100:28.1f} %")
    out.setdefault("decision", []).append(dict(T=T, p_welch_false=pw, p_acf_false=pa))

(L.CACHE / "r95_q_power.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_q_power.json'}")
