#!/usr/bin/env python3
r"""IS THE 6-9 Hz RATCHET THE ENVELOPE OF THE 20-26 Hz GRIND?

WHY THIS FILE EXISTS -- `hf_lf_03` looked in the WRONG LOW-FREQUENCY WINDOW
  The brief asked for 0.3-3 Hz.  `hf_lf_03` found low-frequency envelope structure there, but it
  sits at the very bottom bin on EVERY arm including STOCK, the pre-declared control band, and the
  parked/manual arm, and it does not phase-lock to the column's own low-frequency motion.  Two
  independent things then pointed higher:

    * the firmware trace of the governor loop: the rate-scheduled ceiling's own filter is FAST
      (f_-3dB = 54.8 Hz, tau = 2.93 ms) so no cal-defined time constant lives at 0.3-3 Hz, while
      the PLANT's envelope time constant  tau_env = Q/(pi f)  = 171-440 ms at Q 14-29 / 21-26 Hz
      predicts a relaxation at **2.8-7.2 Hz**;
    * the kit's own ratchet is a **7.79 Hz** line in the torsion bar that has never been explained.

  If the 6-9 Hz ratchet is the AMPLITUDE ENVELOPE of the 20-26 Hz grind, then the operator's
  sentence -- "the grind at high speed is also somehow resulting in a lower ratcheting-like mode"
  -- is literally true, and the two symptoms are ONE mechanism.

FOUR INDEPENDENT TESTS, each with its own null run first
  A  ENVELOPE LINE + COHERENCE in a 3-9 Hz window.  coh2(env(HF), tq band-passed 6-9 Hz), null by
     CIRCULAR TIME SHIFT (preserves both series entirely, destroys only alignment).
  B  BICOHERENCE b^2(f1,f2) over f1 in 0.3-12, f2 in 14-36.  This is the canonical test for
     quadratic phase coupling and it is EXACTLY ZERO for any linear Gaussian process, so the null
     is principled rather than assumed.  Null = full phase randomisation, 60 draws.
  C  SIDEBAND TRIPLET.  If the 20-26 Hz carrier is amplitude-modulated at f_m the raw spectrum
     carries f_c +- f_m.  Scored as the symmetric-sideband excess against the local background.
  D  AMPLITUDE-AMPLITUDE correlation, env(HF) vs env(6-9), Spearman, with the same shift null.

CONTROL BAND 32-38 Hz and the STOCK route (97) carry every test.  ⚠ wheel order 3 is 32.7-40.1 Hz
at these speeds, so 32-38 is a control for the ESTIMATOR, not a clean silence.

OUTPUT `rlog-tools/_scratch/out/_hf_lf_sidebands.json`
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402
from hf_lf_03_envelope_coupling import (analytic_env, blocks_with_native,  # noqa: E402
                                        episodes, reg, ROUTE_LABEL)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, KMH, CIRC = L.FS, 3.6, 2.0805
ROUTES = ["9e", "97", "96", "85"]
HF_BANDS = {"15-22": (15.0, 22.0), "20-26": (20.0, 26.0), "22-26": (22.0, 26.0),
            "26-31": (26.0, 31.0), "32-38": (32.0, 38.0), "40-49": (40.0, 49.0)}
CTRL = "32-38"
RATCHET = (6.0, 9.0)
LFWIN = (3.0, 9.0)          # the window this file adds over hf_lf_03's 0.25-3.0
NSEG, HOP = 512, 256        # 5.12 s -> 0.195 Hz bins; many segments for bicoherence
NSURR, NBIC = 200, 60

_W = np.hanning(NSEG)
_R = np.arange(NSEG, dtype=float)
_SCALE = float(np.mean(_W ** 2))
FREQ = np.fft.rfftfreq(NSEG, 1.0 / FS)


def hdr(s):
    print("\n" + "=" * 112)
    print(s)
    print("=" * 112, flush=True)


def parts(series):
    Xs = []
    for x in series:
        x = np.asarray(x, float)
        for s in range(0, len(x) - NSEG + 1, HOP):
            y = x[s:s + NSEG]
            c = np.polyfit(_R, y, 1)
            Xs.append(np.fft.rfft((y - (c[0] * _R + c[1])) * _W))
    return np.asarray(Xs)


def welch_P(X):
    P = (np.abs(X) ** 2).mean(0) * 2.0 / (NSEG ** 2) / _SCALE
    P[0] /= 2.0
    P[-1] /= 2.0
    return P


def coh_band(A, B, lo, hi):
    Sab = (A * np.conj(B)).mean(0)
    g = (np.abs(Sab) ** 2) / np.maximum((np.abs(A) ** 2).mean(0) * (np.abs(B) ** 2).mean(0), 1e-30)
    m = (FREQ >= lo) & (FREQ <= hi)
    i = int(np.flatnonzero(m)[np.argmax(g[m])])
    return float(g[m].mean()), float(FREQ[i]), float(g[i])


def bandpass(x, lo, hi):
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1.0 / FS)
    X[(f < lo) | (f >= hi)] = 0.0
    return np.fft.irfft(X, n=len(x))


def norm_env(envs):
    return [(e - e.mean()) / max(e.mean(), 1e-9) for e in envs]


# ------------------------------------------------------------------ B  bicoherence --------------
def bicoherence(X, f1s, f2s):
    """b^2(f1,f2) = |<X1 X2 X*(1+2)>|^2 / (<|X1 X2|^2> <|X(1+2)|^2>).  Zero for linear Gaussian."""
    i1 = np.searchsorted(FREQ, f1s)
    i2 = np.searchsorted(FREQ, f2s)
    out = np.full((len(i1), len(i2)), np.nan)
    for a, ia in enumerate(i1):
        Xa = X[:, ia]
        for b, ib in enumerate(i2):
            isum = ia + ib
            if isum >= X.shape[1]:
                continue
            prod = Xa * X[:, ib]
            num = np.abs(np.mean(prod * np.conj(X[:, isum]))) ** 2
            den = np.mean(np.abs(prod) ** 2) * np.mean(np.abs(X[:, isum]) ** 2)
            out[a, b] = num / max(den, 1e-30)
    return out


def phase_rand_full(x, rng):
    X = np.fft.rfft(np.asarray(x, float))
    X = np.abs(X) * np.exp(1j * rng.uniform(0, 2 * np.pi, len(X)))
    X[0] = np.abs(X[0])
    return np.fft.irfft(X, n=len(x))


# ------------------------------------------------------------------ C  sideband triplet ---------
def sideband_score(P, fc, fm, half=1.5, gap=0.4):
    """(P[fc-fm] + P[fc+fm]) / local background, both sidebands required."""
    def val(f0):
        i = int(np.argmin(np.abs(FREQ - f0)))
        bg = (np.abs(FREQ - f0) <= half) & (np.abs(FREQ - f0) > gap)
        return P[i] / max(float(np.median(P[bg])), 1e-30)
    lo, hi = val(fc - fm), val(fc + fm)
    return float(min(lo, hi)), float(lo), float(hi)


# ------------------------------------------------------------------ per arm ---------------------
def score_arm(rt, eps, label, seed=0):
    rng = np.random.default_rng(seed)
    car = [e["tq"] for e in eps]
    lens = [len(e["t"]) for e in eps]
    Xtq = parts(car)
    Ptq = welch_P(Xtq)
    ratchet = [bandpass(x, *RATCHET) for x in car]
    Xr = parts(ratchet)
    env69 = norm_env([analytic_env(x, *RATCHET) for x in car])
    Xe69 = parts(env69)
    res = dict(label=label, n_ep=len(eps), s=float(sum(lens) / FS),
               v_med=float(np.median([e["_v"] for e in eps])),
               wo1=float(np.median([e["_v"] for e in eps]) / KMH / CIRC),
               nseg=int(Xtq.shape[0]), bands={})

    # where the HF energy actually is, so the sideband test uses the REAL carrier
    mhf = (FREQ >= 15.0) & (FREQ <= 35.0)
    fc_hat = float(FREQ[mhf][np.argmax(Ptq[mhf])])
    # the ratchet's own line
    mr = (FREQ >= 5.5) & (FREQ <= 9.5)
    fm_hat = float(FREQ[mr][np.argmax(Ptq[mr])])
    res["f_carrier"], res["f_ratchet"] = fc_hat, fm_hat

    for bn, (lo, hi) in HF_BANDS.items():
        envs = [analytic_env(x, lo, hi) for x in car]
        ne = norm_env(envs)
        Xe = parts(ne)
        Pe = welch_P(Xe)
        # --- A: coherence env(HF) vs the 6-9 Hz ratchet band, circular-shift null -----------
        obs, fpk, gpk = coh_band(Xe, Xr, *LFWIN)
        null = np.empty(NSURR)
        for k in range(NSURR):
            rolled = [np.roll(e_, int(rng.integers(int(2.0 * FS), max(L_ - int(2.0 * FS), int(2.0 * FS) + 1))))
                      for e_, L_ in zip(ne, lens)]
            null[k] = coh_band(parts(rolled), Xr, *LFWIN)[0]
        # --- D: amplitude-amplitude, same null -------------------------------------------
        aa_obs, aa_null = [], []
        cat_e = np.concatenate(ne)
        cat_r = np.concatenate([x for x in env69])
        aa_obs = float(np.corrcoef(np.argsort(np.argsort(cat_e)),
                                   np.argsort(np.argsort(cat_r)))[0, 1])
        for k in range(60):
            rolled = np.concatenate([np.roll(e_, int(rng.integers(int(2.0 * FS),
                                                                  max(L_ - int(2.0 * FS),
                                                                      int(2.0 * FS) + 1))))
                                     for e_, L_ in zip(ne, lens)])
            aa_null.append(float(np.corrcoef(np.argsort(np.argsort(rolled)),
                                             np.argsort(np.argsort(cat_r)))[0, 1]))
        aa_null = np.asarray(aa_null)
        # --- envelope spectrum peak inside 3-9 Hz -----------------------------------------
        mm = (FREQ >= LFWIN[0]) & (FREQ <= LFWIN[1])
        ipk = int(np.flatnonzero(mm)[np.argmax(Pe[mm])])
        res["bands"][bn] = dict(
            coh_obs=obs, coh_null_med=float(np.median(null)),
            coh_null_p95=float(np.percentile(null, 95)),
            coh_p=float((1 + np.sum(null >= obs)) / (NSURR + 1)),
            coh_fpeak=fpk, coh_peak=gpk,
            env_fpk_3to9=float(FREQ[ipk]),
            aa_rho=aa_obs, aa_null_p95=float(np.percentile(aa_null, 95)),
            aa_p=float((1 + np.sum(aa_null >= aa_obs)) / (len(aa_null) + 1)),
        )
    # --- C: sideband triplet at the measured carrier and the measured ratchet ------------
    res["sideband"] = {}
    for fm in (fm_hat, 1.0, 2.0):
        s, a, b = sideband_score(Ptq, fc_hat, fm)
        res["sideband"]["fm=%.2f" % fm] = dict(both=s, lower=a, upper=b)
    # null for the sideband statistic: phase-randomised whole record
    sn = []
    for k in range(NBIC):
        Ps = welch_P(parts([phase_rand_full(x, rng) for x in car]))
        sn.append(sideband_score(Ps, fc_hat, fm_hat)[0])
    res["sideband"]["null_p95"] = float(np.percentile(sn, 95))
    res["sideband"]["p"] = float((1 + np.sum(np.asarray(sn) >= res["sideband"]
                                             ["fm=%.2f" % fm_hat]["both"])) / (NBIC + 1))
    # --- B: bicoherence map --------------------------------------------------------------
    f1s = np.arange(0.4, 12.01, 0.4)
    f2s = np.arange(14.0, 36.01, 1.0)
    B = bicoherence(Xtq, f1s, f2s)
    Bn = np.zeros_like(B)
    for k in range(NBIC):
        Bn += bicoherence(parts([phase_rand_full(x, rng) for x in car]), f1s, f2s)
    Bn /= NBIC
    ratio = B / np.maximum(Bn, 1e-12)
    ij = np.unravel_index(int(np.nanargmax(np.where(np.isfinite(ratio), ratio, -1))), ratio.shape)
    res["bicoh"] = dict(f1=[float(x) for x in f1s], f2=[float(x) for x in f2s],
                        best_f1=float(f1s[ij[0]]), best_f2=float(f2s[ij[1]]),
                        best_b2=float(B[ij]), best_null=float(Bn[ij]),
                        best_ratio=float(ratio[ij]),
                        mean_b2=float(np.nanmean(B)), mean_null=float(np.nanmean(Bn)),
                        b2=[[None if not np.isfinite(v) else float(v) for v in row] for row in B])
    # bicoherence restricted to the ratchet row (f1 nearest f_ratchet) and the carrier column
    i1 = int(np.argmin(np.abs(f1s - fm_hat)))
    i2 = int(np.argmin(np.abs(f2s - fc_hat)))
    res["bicoh"]["ratchet_x_carrier"] = dict(
        f1=float(f1s[i1]), f2=float(f2s[i2]), b2=float(B[i1, i2]), null=float(Bn[i1, i2]),
        ratio=float(B[i1, i2] / max(Bn[i1, i2], 1e-12)))
    return res


def main():
    out = {}
    arms = [("ENGAGED hwy", True, 70.0, 200.0), ("manual hwy", False, 70.0, 200.0),
            ("ENGAGED mid", True, 40.0, 70.0), ("ENGAGED low", True, 0.0, 40.0)]
    for rt in ROUTES:
        if not reg(rt):
            continue
        out[rt] = {}
        for lab, eng, vlo, vhi in arms:
            eps = episodes(rt, engaged=eng, vlo=vlo, vhi=vhi, minlen=NSEG)
            if not eps:
                continue
            r = score_arm(rt, eps, lab, seed=abs(hash((rt, lab, "sb"))) % 10000)
            out[rt][lab] = r
            hdr("ROUTE %s (%s)  ARM %s  %d ep, %.1f s, %d segments, v=%.1f km/h"
                % (rt, ROUTE_LABEL.get(rt, rt), lab, r["n_ep"], r["s"], r["nseg"], r["v_med"]))
            print("  carrier peak (15-35 Hz) = %.2f Hz | ratchet peak (5.5-9.5 Hz) = %.2f Hz"
                  % (r["f_carrier"], r["f_ratchet"]))
            print("  %-6s | %-40s | %-28s | %s"
                  % ("band", "coh2(env_HF, tq[6-9Hz]) 3-9 Hz window",
                     "amp-amp rho vs env(6-9)", "env peak in 3-9"))
            for bn, b in r["bands"].items():
                tag = " CTRL" if bn == CTRL else ""
                print("  %-6s | obs %.3f null95 %.3f p %.3f  peak %.3f@%.2fHz | "
                      "rho %+.3f null95 %+.3f p %.3f | %.2f Hz%s"
                      % (bn, b["coh_obs"], b["coh_null_p95"], b["coh_p"], b["coh_peak"],
                         b["coh_fpeak"], b["aa_rho"], b["aa_null_p95"], b["aa_p"],
                         b["env_fpk_3to9"], tag))
            sb = r["sideband"]
            print("  SIDEBANDS at carrier %.2f Hz: %s | null p95 %.2f, p=%.3f"
                  % (r["f_carrier"],
                     "  ".join("%s both=%.2f (lo %.2f / hi %.2f)" % (k, v["both"], v["lower"],
                                                                     v["upper"])
                               for k, v in sb.items() if k.startswith("fm=")),
                     sb["null_p95"], sb["p"]))
            bc = r["bicoh"]
            rx = bc["ratchet_x_carrier"]
            print("  BICOHERENCE: max b2=%.4f at (f1=%.1f, f2=%.1f) null %.4f ratio %.2f | "
                  "mean b2 %.4f vs null %.4f | ratchet x carrier (%.1f,%.1f) b2=%.4f null %.4f "
                  "ratio %.2f"
                  % (bc["best_b2"], bc["best_f1"], bc["best_f2"], bc["best_null"],
                     bc["best_ratio"], bc["mean_b2"], bc["mean_null"],
                     rx["f1"], rx["f2"], rx["b2"], rx["null"], rx["ratio"]))
    (HERE / "_scratch/out/_hf_lf_sidebands.json").write_text(json.dumps(out, indent=1))
    print("\nwrote", HERE / "_scratch/out/_hf_lf_sidebands.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
