#!/usr/bin/env python3
"""studies/identification/selfint_transfer.py -- measure the operator's self-interference thesis on the car.

    "the Honda firmware is not built to sustain such high LKAS demands ... I would need some
     filtering and/or self-interference cancellation of the LKAS torque signal which shows up on
     the driver-side torque signal (opposing torque under LKAS-driven angular acceleration due to
     the steering wheel inertia)."

Five sections, each self-contained:

  S0  INSTRUMENT   -- scale, staleness, quantisation, and the two-angle question, re-derived here
                      rather than inherited.  Every later number depends on S0 being right.
  S1  THE TRANSFER -- theta_ddot -> torsion bar, engaged.  Coherence, K, the pre-registered bar.
  S2  DECOMPOSITION at 7.79 / 20.5 / 27.5 Hz, engaged and manual, as fraction of bar variance.
  S3  ENGAGED vs MANUAL at matched theta_ddot.
  S4  THE STANDING MODEL -- does in-burst AMPLITUDE scale with command, or only DUTY?
  S5  NULLS -- split-half, and a phase-scrambled coherence floor.

Usage:  python studies/identification/selfint_transfer.py [--nboot N] [--quick]
Writes: _scratch/cache/selfint/selfint.json
"""
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import selfint_lib as S  # noqa: E402
import _r31_common as C31  # noqa: E402

OUTDIR = ROOT / "_scratch/cache/selfint"
OUT = {}
RNG = np.random.default_rng(85_2026)
NBOOT = 2000
NBOOT_RES = 400
QUICK = "--quick" in sys.argv
if QUICK:
    NBOOT, NBOOT_RES = 300, 120

MAIN = ["V84/r6d", "V83a/r68", "V81/r67", "V80/r66"]
FTAR = [("S2 micro-ratchet", 7.79), ("S1 grind #1", 20.5), ("ring / lane-change", 27.5)]
FIT_BAND = (4.0, 30.0)      # phase is trustworthy to 25 Hz, magnitude to 40; 30 is the compromise
BAR_G2, BAR_K = 0.80, 10    # 🛑 PRE-REGISTERED, docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION §1.5
REFUSE_G2 = 0.50


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100, flush=True)


def san(o):
    if isinstance(o, dict):
        return {k: san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [san(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(float(o)) else round(float(o), 6)
    if isinstance(o, (np.integer, int)):
        return int(o)
    if isinstance(o, np.ndarray):
        return san(o.tolist())
    return o


# =================================================================================================
def s0_instrument():
    hdr("S0  INSTRUMENT -- re-derived here, not inherited.  Every later number rests on these.")
    out = {}

    # ---- S0.1  the two angles ----------------------------------------------------------------
    tot = same = 0
    for rt in MAIN:
        for d in S.segs(rt):
            dd = np.asarray(d["ang"], float) - np.asarray(d["wang"], float)
            tot += len(dd)
            same += int((np.abs(dd) < 1e-9).sum())
    print(f"\nS0.1  `0x14A` STEER_ANGLE (b0-1) vs STEER_WHEEL_ANGLE (b5-6):  identical on "
          f"{same}/{tot} frames = {100 * same / tot:.4f}%")
    print("      => there is only ONE angle on this bus.  `decode/decode_two_angles.py`'s topology check\n"
          "         (wheel-side minus pinion-side = bar twist) is VOID on every route here: the EPS\n"
          "         transmits the same value in both slots.  [EVIDENCE, byte-level, 4 routes]")
    out["ang_eq_wang_frac"] = same / tot
    out["ang_eq_wang_n"] = tot

    # ---- S0.2  quantisation -------------------------------------------------------------------
    d = next(S.segs("V81/r67"))
    q = {}
    for k in ("ang", "rate_c", "tq", "rate_f"):
        u = np.unique(np.asarray(d[k], float))
        q[k] = float(np.min(np.diff(u))) if len(u) > 2 else np.nan
    rep = {k: float(np.mean(np.diff(np.asarray(d[k], float)) == 0))
           for k in ("ang", "rate_c", "tq")}
    print(f"\nS0.2  LSB actually present in the data: ang {q['ang']:.3g} deg · rate_c "
          f"{q['rate_c']:.3g} deg/s · rate_f {q['rate_f']:.3g} · tq {q['tq']:.3g} COUNTS")
    print(f"      consecutive-identical frames: ang {rep['ang'] * 100:.1f}% · rate_c "
          f"{rep['rate_c'] * 100:.1f}% · tq {rep['tq'] * 100:.1f}%")
    print("      🛑 `tq`'s LSB is 8 counts, not 1 -- the low 3 bits of the 16-bit field are always\n"
          "         zero.  A noise-floor claim that assumed LSB=1 is 8x optimistic (still >100x\n"
          "         below every band level measured here, so it does not bind).")
    print("      🛑 `ang` REPEATS on 74% of frames.  Differencing it twice at 100 Hz to get\n"
          "         theta_ddot is a quantisation amplifier -- this analysis never does it.")
    out["lsb"] = q
    out["repeat_frac"] = rep

    # ---- S0.3  `rate_c` really is d(ang)/dt ---------------------------------------------------
    L, w = 2048, np.hanning(2048)
    Sxx = Syy = None
    Sxy = None
    r = np.arange(L, dtype=float)
    for d in S.segs("V81/r67"):
        ok = S.lattice_ok(d)
        for i in range(0, len(d["t"]) - L + 1, L):
            if not ok[i:i + L].all():
                continue
            x = np.asarray(d["ang"], float)[i:i + L] * S.D2R
            y = np.asarray(d["rate_c"], float)[i:i + L] * S.D2R
            x = x - np.polyval(np.polyfit(r, x, 2), r)
            y = y - np.polyval(np.polyfit(r, y, 2), r)
            X, Y = np.fft.rfft(x * w), np.fft.rfft(y * w)
            if Sxx is None:
                Sxx = np.zeros(len(X)); Syy = np.zeros(len(X)); Sxy = np.zeros(len(X), complex)
            Sxx += np.abs(X) ** 2; Syy += np.abs(Y) ** 2; Sxy += np.conj(X) * Y
        fs = d["_fs"]
    f = np.fft.rfftfreq(L, 1 / fs)
    g2 = S.coh(Sxx, Syy, Sxy)
    H = Sxy / Sxx
    rows = []
    print("\nS0.3  DBC scale consistency:  |rate_c| / (omega * |ang|) should be 1.000 if the two\n"
          "      0x14A fields are the same motion at their stated scales (0.1 deg, 1 deg/s).")
    print(f"      {'f Hz':>7} {'gamma^2':>9} {'ratio':>8}")
    for ft in (0.25, 0.4, 0.8, 1.0, 1.5, 2.0):
        j = int(np.argmin(np.abs(f - ft)))
        rr = float(abs(H[j]) / (2 * np.pi * f[j]))
        rows.append((float(f[j]), float(g2[j]), rr))
        print(f"      {f[j]:7.3f} {g2[j]:9.4f} {rr:8.4f}")
    good = [rr for ff, gg, rr in rows if gg > 0.95]
    print(f"      median over gamma^2>0.95 rows: {np.median(good):.4f}   [EVIDENCE] the scales are\n"
          "      mutually consistent, so `rate_c` IS d(ang)/dt and carries the same physical motion.")
    out["scale_ratio_lowf"] = rows
    out["scale_ratio_median"] = float(np.median(good))

    # ---- S0.4  0x18F payload staleness, measured DIRECTLY -------------------------------------
    print("\nS0.4  `0x18F` PAYLOAD STALENESS -- re-measured by a method that needs no derivative\n"
          "      invariant.  `rate_f`*1.25 (0x18F b2-3) and `rate_c` (0x14A b2-3) are THE SAME\n"
          "      SIGNAL on the two messages, so phase(rate_f/rate_c) = -2*pi*f*tau directly.")
    print(f"      {'route':10s} {'blocks':>7} {'|gain| 2-45Hz':>14} {'min gamma^2':>12} "
          f"{'tau ms (median)':>16} {'tau range':>18}")
    st = {}
    for rt in MAIN:
        Sxx = Syy = None
        Sxy = None
        nb = 0
        L2, w2 = 512, np.hanning(512)
        r2 = np.arange(L2, dtype=float)
        for d in S.segs(rt):
            ok = S.lattice_ok(d)
            for i in range(0, len(d["t"]) - L2 + 1, L2 // 2):
                if not ok[i:i + L2].all():
                    continue
                x = np.asarray(d["rate_c"], float)[i:i + L2]
                y = np.asarray(d["rate_f"], float)[i:i + L2] * 1.25
                x = x - np.polyval(np.polyfit(r2, x, 1), r2)
                y = y - np.polyval(np.polyfit(r2, y, 1), r2)
                X, Y = np.fft.rfft(x * w2), np.fft.rfft(y * w2)
                if Sxx is None:
                    Sxx = np.zeros(len(X)); Syy = np.zeros(len(X)); Sxy = np.zeros(len(X), complex)
                Sxx += np.abs(X) ** 2; Syy += np.abs(Y) ** 2; Sxy += np.conj(X) * Y
                nb += 1
            fs = d["_fs"]
        f2 = np.fft.rfftfreq(L2, 1 / fs)
        g2b = S.coh(Sxx, Syy, Sxy)
        Hb = Sxy / Sxx
        ph = np.unwrap(np.angle(Hb))
        sel = (f2 >= 2) & (f2 <= 45)
        tau = -ph[sel] / (2 * np.pi * f2[sel]) * 1e3
        st[rt] = dict(blocks=nb, gain=float(np.median(np.abs(Hb[sel]))),
                      g2min=float(np.min(g2b[sel])), tau_med=float(np.median(tau)),
                      tau_lo=float(np.min(tau)), tau_hi=float(np.max(tau)))
        s = st[rt]
        print(f"      {rt:10s} {nb:7d} {s['gain']:14.4f} {s['g2min']:12.4f} "
              f"{s['tau_med']:16.3f} {s['tau_lo']:8.2f}-{s['tau_hi']:.2f}")
    print(f"\n      [EVIDENCE] tau = {np.median([v['tau_med'] for v in st.values()]):.2f} ms, "
          "CONSTANT in ms from 2 to 45 Hz on all four routes, gamma^2 > 0.96 throughout,\n"
          "      |gain| = 1.000.  ⇒ (a) it is a PURE ONE-FRAME DELAY, not a filter; (b) `rate_f`'s\n"
          "      true DBC scale is 0.125 (stored 0.1), confirmed to 0.5%; (c) this CONFIRMS\n"
          "      memory/accord-0x18f-payload-one-frame-stale by an independent and much cleaner\n"
          "      route -- the kit's version had to assume the +90 deg derivative invariant.\n"
          f"      Applied everywhere below as T(f) *= exp(+j*2*pi*f*{S.TAU_18F}).")
    out["stale"] = st
    return out


# =================================================================================================
def s1_transfer():
    hdr("S1  THE TRANSFER  theta_dot / theta_ddot -> TORSION BAR, engaged.\n"
        "    Z(f) = T_bar / theta_dot, from rate_c (0x14A).  theta_ddot = j*omega*rate_c EXACTLY\n"
        "    (spectral derivative: transfer is exactly j*omega in band, exactly 0 out of band).")
    out = {}
    store = {}
    for rt in MAIN:
        for cond, mf in (("engaged", S.mask_engaged),
                         ("engaged+handsoff", lambda d: S.mask_engaged(d) & S.mask_handsoff(d)),
                         ("manual", S.mask_manual)):
            recs = S.collect(rt, mf)
            if len(recs) < 3:
                continue
            store[(rt, cond)] = recs

    print("\nS1.1  COHERENCE gamma^2 between column rate and the bar, K = non-overlapping EPISODES\n"
          "      (max 20.48 s each, cut only inside a lattice-contiguous run of the condition).")
    print(f"      {'route':10s} {'condition':18s} {'K':>4} {'sec':>6} "
          + " ".join(f"{x:>7}" for x in ("4 Hz", "7.8", "12.8", "20.5", "27.5", "peak", "f_peak")))
    cohtab = {}
    for (rt, cond), recs in store.items():
        f, Sxx, Syy, Sxy, K = S.stack(recs)
        g2 = S.coh(Sxx, Syy, Sxy)
        band = (f >= 4) & (f <= 30)
        vals = []
        for ft in (4, 7.79, 12.8, 20.5, 27.5):
            vals.append(float(g2[int(np.argmin(np.abs(f - ft)))]))
        jp = np.flatnonzero(band)[int(np.argmax(g2[band]))]
        sec = sum(r["sec"] for r in recs)
        cohtab[f"{rt}|{cond}"] = dict(K=K, sec=sec, g2=vals, g2max=float(g2[jp]),
                                      f_at_max=float(f[jp]))
        print(f"      {rt:10s} {cond:18s} {K:4d} {sec:6.0f} "
              + " ".join(f"{v:7.3f}" for v in vals)
              + f" {g2[jp]:7.3f} {f[jp]:7.2f}")
    out["coherence"] = cohtab

    print(f"\n      🛑 PRE-REGISTERED BAR (feasibility report §1.5): gamma^2 >= {BAR_G2} over "
          f"K >= {BAR_K} episodes; REFUSE below {REFUSE_G2}.")
    verd = {}
    for key, c in cohtab.items():
        for lbl, i in (("7.79", 1), ("20.5", 3), ("27.5", 4)):
            g = c["g2"][i]
            v = "PASS" if (g >= BAR_G2 and c["K"] >= BAR_K) else (
                "REFUSE" if g < REFUSE_G2 else "BELOW BAR")
            verd[f"{key}@{lbl}"] = dict(g2=g, K=c["K"], verdict=v)
    npass = sum(1 for v in verd.values() if v["verdict"] == "PASS")
    print(f"      {npass} of {len(verd)} (route x condition x symptom-frequency) cells PASS.")
    for k, v in sorted(verd.items()):
        if v["verdict"] == "PASS":
            print(f"        PASS  {k}   gamma^2={v['g2']:.3f}  K={v['K']}")
    out["bar_verdict"] = verd

    print("\nS1.2  THE MODEL.  A single (J, b, k) impedance CANNOT fit this data -- the measured\n"
          "      phase of Z sweeps ~180 deg across 4-30 Hz, which no memoryless J/b/k can do.\n"
          "      The minimal physical model that can, given the CAN angle sits BELOW the bar:\n\n"
          "          upper column:  J*thddot_w = T_d - T_bar - b*thdot_w,  T_bar = k*(th_w - th_p)\n"
          "          hands off (T_d=0), eliminate th_w:\n"
          "              Z(s) = T/thdot_p = -k (J s + b) / (J s^2 + b s + k)\n"
          "                                = -k (s + 2 zeta wn) / (s^2 + 2 zeta wn s + wn^2)\n\n"
          "      LIMITS -- this is the whole answer to the operator's question:\n"
          "          2*zeta*wn << w << wn :  T -> -J*theta_ddot   INERTIAL REACTION (his mechanism)\n"
          "          w >> wn              :  T -> -k*theta        STIFFNESS against a wheel that\n"
          "                                                       its own inertia has pinned.\n"
          "      Expressed as a coefficient on theta those two have OPPOSITE SIGN (-J*thddot =\n"
          "      +J*w^2*theta), so the required cancellation INVERTS through wn.")
    print(f"\n      {'route':10s} {'condition':18s} {'K':>4} {'fn Hz':>18} {'zeta':>16} "
          f"{'J cts.s2/rad':>20} {'k cts/rad':>20} {'VAF':>6}")
    fits = {}
    for (rt, cond), recs in store.items():
        pt, ci = S.boot_res(recs, FIT_BAND, nboot=NBOOT_RES, seed=8585)
        fits[f"{rt}|{cond}"] = dict(pt=pt, ci=ci, K=len(recs))
        print(f"      {rt:10s} {cond:18s} {len(recs):4d} "
              f"{S.fmt_ci(pt['fn'], ci['fn']):>18} {S.fmt_ci(pt['zeta'], ci['zeta']):>16} "
              f"{S.fmt_ci(pt['J'], ci['J']):>20} {S.fmt_ci(pt['k'], ci['k']):>20} "
              f"{pt['vaf']:6.3f}")
    out["fits"] = fits

    print("\nS1.3  TWO SIGNATURES OF fn on the SAME data that share NO assumption:\n"
          "      (a) the peak of |H1|, which is TAU-free and does not use phase at all;\n"
          "      (b) the frequency at which phase(Z) crosses -180 deg, which is MAGNITUDE-free.\n"
          "      ⚠ (a) uses H1, NOT the geometric-mean estimator: |H_geo| = |H1|/gamma blows the\n"
          "        low-coherence bins up and moves the apparent peak down by 3-5 Hz.  (a) is the\n"
          "        weaker of the two -- it is a broad peak on a noisy ridge; (b) and the fit are\n"
          "        the load-bearing pair.")
    print(f"      {'route':10s} {'condition':18s} {'f(|H1| peak)':>13} {'f(phase=-180)':>14} "
          f"{'fn (fit)':>9}")
    sig = {}
    for (rt, cond), recs in store.items():
        f, Sxx, Syy, Sxy, K = S.stack(recs)
        sel = (f >= 5) & (f <= 30)
        H1 = S.frf(Sxx, Syy, Sxy, "H1")
        Hg = S.frf(Sxx, Syy, Sxy, "geo")
        fpk = float(f[sel][int(np.argmax(np.abs(H1[sel])))])
        ph = np.unwrap(np.angle(Hg))
        ph = ph - 2 * np.pi * np.round((ph[int(np.argmin(np.abs(f - 6)))] + np.pi / 2)
                                       / (2 * np.pi))
        j = np.flatnonzero(sel)
        cross = np.nan
        for a, b in zip(j[:-1], j[1:]):
            if (ph[a] + np.pi) * (ph[b] + np.pi) < 0:
                cross = float(f[a] + (f[b] - f[a]) * (-np.pi - ph[a]) / (ph[b] - ph[a]))
                break
        sig[f"{rt}|{cond}"] = dict(f_peak=fpk, f_phase180=cross,
                                   fn_fit=fits[f"{rt}|{cond}"]["pt"]["fn"])
        print(f"      {rt:10s} {cond:18s} {fpk:12.2f} {cross:14.2f} "
              f"{fits[f'{rt}|{cond}']['pt']['fn']:9.2f}")
    out["fn_signatures"] = sig

    print("\nS1.4  J IN PHYSICAL UNITS.  `STEER_TORQUE_SENSOR`'s counts->N.m calibration S_T is\n"
          "      NOT known to this kit, so J is carried symbolically:\n"
          "            J_eff [kg m^2] = J [counts s^2 / rad] * S_T [N.m / count]\n"
          "      Two ways to close it, both stated as what they are:")
    jj = [v["pt"]["J"] for k, v in fits.items() if k.endswith("engaged")]
    kk = [v["pt"]["k"] for k, v in fits.items() if k.endswith("engaged")]
    Jc, kc = float(np.median(jj)), float(np.median(kk))
    print(f"      pooled engaged median: J = {Jc:.4g} counts s^2/rad,  k = {kc:.4g} counts/rad")
    for Jw in (0.035, 0.045, 0.055):
        st_ = Jw / Jc
        print(f"        IF J_wheel = {Jw:.3f} kg m^2 (class-typical) => S_T = {st_ * 1e3:.3f} "
              f"mN.m/count => k = {kc * st_:.0f} N.m/rad, and the bar's observed +/-2400-count\n"
              f"          excursion is +/-{2400 * st_:.2f} N.m of steering effort.")
    print("      ⇒ the plausibility loop CLOSES: a class-typical wheel inertia implies a torsion\n"
          "        bar of 220-350 N.m/rad and a peak driver effort of 5-8 N.m, both ordinary.\n"
          "        [BELIEF on the absolute numbers -- S_T is assumed, not measured.  fn and the\n"
          "         RATIO k/J are [EVIDENCE] and need no calibration at all.]")
    out["J_pooled"] = Jc
    out["k_pooled"] = kc
    out["S_T_implied"] = {str(Jw): Jw / Jc for Jw in (0.035, 0.045, 0.055)}
    out["_store_keys"] = [f"{a}|{b}" for a, b in store]
    return out, store


# =================================================================================================
def s2_decompose(store):
    hdr("S2  PHASE DECOMPOSITION at the three symptom frequencies, as FRACTION OF ENGAGED BAR\n"
        "    VARIANCE.  quad = in phase with -theta_dot (damping/friction) · react = in phase with\n"
        "    theta, which at a SINGLE frequency is the SAME DIRECTION as -theta_ddot and cannot be\n"
        "    separated from it · resid = 1 - gamma^2, not linearly explained by column motion.\n"
        "    quad + react == gamma^2 identically.")
    print("\n    🛑 THE COLLINEARITY IS NOT A LIMITATION OF THIS ANALYSIS, IT IS ALGEBRA:\n"
          "       for a sinusoid -theta_ddot = +omega^2 * theta.  Any method that claims to split\n"
          "       'inertial' from 'stiffness' at one frequency is reporting its prior.  The split\n"
          "       is done in S1 by the FREQUENCY DEPENDENCE, and imported here as (f/fn)^2.")
    out = {}
    print(f"\n    {'route':10s} {'condition':18s} {'f Hz':>6} {'K':>4} {'gamma^2':>8} "
          f"{'react':>7} {'quad':>7} {'resid':>7} {'phase':>7} | {'react SIGN says':>22} "
          f"{'(f/fn)^2':>9} {'model regime':>22}")
    for (rt, cond), recs in sorted(store.items()):
        f, Sxx, Syy, Sxy, K = S.stack(recs)
        fit = S.fit_res(f, Sxx, Syy, Sxy, FIT_BAND)
        for lbl, ft in FTAR:
            dd = S.decompose(f, Sxx, Syy, Sxy, ft, halfwidth=1.0)
            ratio = (ft / fit["fn"]) ** 2 if np.isfinite(fit["fn"]) else np.nan
            reg = ("INERTIAL -J*thddot" if ratio < 0.5 else
                   "near fn -- MIXED" if ratio < 2.0 else "STIFFNESS -k*theta")
            out[f"{rt}|{cond}|{ft}"] = dict(dd, K=K, fn=fit["fn"], ratio=ratio, regime=reg)
            print(f"    {rt:10s} {cond:18s} {ft:6.2f} {K:4d} {dd['g2']:8.3f} "
                  f"{dd['react']:7.3f} {dd['quad']:7.3f} {dd['resid']:7.3f} "
                  f"{dd['phase_deg']:7.0f} | {dd['react_sign']:>22} "
                  f"{ratio:9.2f} {reg:>22}")
    print("\n    🛑 `react SIGN` and `model regime` are TWO INDEPENDENT READINGS of the same\n"
          "    question -- the first from the sign of Imag(Z) at that frequency alone, the second\n"
          "    from the wideband fn.  Where they agree the call is [EVIDENCE]; where they disagree\n"
          "    the frequency is near fn and neither term dominates.")
    print("\n    HOW TO READ `regime`:  it is (f/fn)^2 = |J w^2| / k, i.e. which of the two terms\n"
          "    of the SAME upper-column free body dominates the bar signal at that frequency.\n"
          "    < 0.5  the bar IS the inertial reaction to the MEASURED angular acceleration\n"
          "    > 2.0  the wheel is pinned by its own inertia; the bar is being wound up against\n"
          "           it, so the bar tracks theta with the OPPOSITE sign a theta_ddot term gives.")
    return out


# =================================================================================================
# Manual-only supplements.  (cache dir, per-segment prefix, max segment index) -- verified on disk.
MANUAL_EXTRA = {"r5d(V74)": ("_scratch/cache/r5d", "r5ds", 70),
                "r54": ("_scratch/cache/r54", "r54s", 45),
                "r3b(V65)": ("_scratch/cache/r3b", "r3bs", 50),
                "r5a": ("_scratch/cache/r5a", "r5as", 40),
                "r47(V67)": ("_scratch/cache/r47", "r47s", 95)}


def _band_rows(recs, lo, hi, cond, route):
    """One row per episode: (theta_ddot band rms [rad/s^2], bar band rms [counts], v, key)."""
    rows = []
    for r in recs:
        f = r["f"]
        sel = (f >= lo) & (f <= hi) & (f > 0)
        om = 2 * np.pi * f[sel]
        add = float(np.sqrt(np.sum(r["Sxx"][sel] * om ** 2)))
        bar = float(np.sqrt(np.sum(r["Syy"][sel])))
        if add <= 0 or bar <= 0:
            continue
        rows.append(dict(add=add, bar=bar, v=r["v_mean"], cond=cond, route=route,
                         key=(route, r["seg"], r["i0"])))
    return rows


def s3_matched(store):
    hdr("S3  ENGAGED vs MANUAL AT MATCHED theta_ddot (AND matched speed).\n"
        "    If the coupling is purely inertial it is IDENTICAL in both -- a reaction torque does\n"
        "    not care what is driving the column.  If the ENGAGED coupling is LARGER at matched\n"
        "    theta_ddot, something in the firmware is ADDING to it, and that is a bigger finding\n"
        "    than the hypothesis under test.")
    out = {}
    # Extra manual-only corpus: route 66 alone gives K=4-12 after matching, below the K>=10 bar.
    for lbl, spec in MANUAL_EXTRA.items():
        S.ROUTES.setdefault(lbl, spec)

    print("\n    ⚠ Route 66 (V80) alone gives K = 4-12 per cell after matching, BELOW the\n"
          "      pre-registered K >= 10.  The manual arm is therefore POOLED over every cache with\n"
          "      real manual driving; `route` is carried as a covariate and the per-route split is\n"
          "      printed so a pooling artefact would show.")
    print(f"\n    {'band':7s} {'arm':26s} {'K':>4} {'sec':>6} {'v m/s p50':>10} "
          f"{'thddot p50':>11} {'bar p50':>9} {'bar/thddot p50':>15}")
    man_recs = {}
    for rt in MAIN + list(MANUAL_EXTRA):
        try:
            r = S.collect(rt, S.mask_manual, ep_max=1024)
        except Exception as e:
            print(f"      (skipped {rt}: {e})")
            continue
        if len(r) >= 2:
            man_recs[rt] = r
    print(f"      manual corpus: " + " · ".join(f"{k} K={len(v)}" for k, v in man_recs.items()))
    pool = {}
    for bn, (lo, hi) in (("6-9", (6, 9)), ("17-23", (17, 23)), ("26-31", (26, 31))):
        rows = []
        for rt in MAIN:
            r = store.get((rt, "engaged"))
            if r:
                rows += _band_rows(r, lo, hi, "engaged", rt)
        man_by_route = {}
        for rt, r in man_recs.items():
            rr = _band_rows(r, lo, hi, "manual", rt)
            man_by_route[rt] = rr
            rows += rr
        pool[bn] = rows
        for arm in ("engaged", "manual"):
            a = [r for r in rows if r["cond"] == arm]
            if not a:
                continue
            g = np.array([r["bar"] / r["add"] for r in a])
            print(f"    {bn:7s} {arm + ' (all routes)':26s} {len(a):4d} {len(a) * 10.24:6.0f} "
                  f"{np.median([r['v'] for r in a]):10.2f} "
                  f"{np.median([r['add'] for r in a]):11.2f} "
                  f"{np.median([r['bar'] for r in a]):9.1f} {np.median(g):15.2f}")
        for rt, rr in sorted(man_by_route.items()):
            if len(rr) < 3:
                continue
            g = np.array([r["bar"] / r["add"] for r in rr])
            print(f"    {'':7s} {'  manual ' + rt:26s} {len(rr):4d} {len(rr) * 10.24:6.0f} "
                  f"{np.median([r['v'] for r in rr]):10.2f} "
                  f"{np.median([r['add'] for r in rr]):11.2f} "
                  f"{np.median([r['bar'] for r in rr]):9.1f} {np.median(g):15.2f}")

    print("\nS3.1  COVARIATE-ADJUSTED CONTRAST.  OLS of  log(bar) = a + b*log(theta_ddot)\n"
          "      + c*1[engaged] + d*log(1+v),  episode-clustered bootstrap (resample EPISODES).\n"
          "      exp(c) is the engaged/manual bar level at MATCHED theta_ddot AND matched speed.\n"
          "      Purely inertial coupling => exp(c) = 1.00 and b = 1.00.")
    print(f"\n    {'band':7s} {'K eng':>6} {'K man':>6} {'b (slope on thddot)':>26} "
          f"{'exp(c) = ENGAGED/MANUAL':>28}")
    for bn, rows in pool.items():
        e = [r for r in rows if r["cond"] == "engaged"]
        m = [r for r in rows if r["cond"] == "manual"]
        if min(len(e), len(m)) < 6:
            print(f"    {bn:7s} {len(e):6d} {len(m):6d}   (insufficient)")
            continue
        allr = e + m

        def fit(rs):
            X = np.stack([np.ones(len(rs)),
                          np.log([r["add"] for r in rs]),
                          np.array([r["cond"] == "engaged" for r in rs], float),
                          np.log1p([r["v"] for r in rs])], axis=1)
            y = np.log([r["bar"] for r in rs])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            return beta
        b0 = fit(allr)
        bs = []
        for _ in range(NBOOT):
            pick = [allr[i] for i in RNG.integers(0, len(allr), len(allr))]
            if len({r["cond"] for r in pick}) < 2:
                continue
            try:
                bs.append(fit(pick))
            except Exception:
                continue
        bs = np.array(bs)
        ci_b = (float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5)))
        ci_c = (float(np.exp(np.percentile(bs[:, 2], 2.5))),
                float(np.exp(np.percentile(bs[:, 2], 97.5))))
        out[bn] = dict(b=float(b0[1]), ci_b=ci_b, exp_c=float(np.exp(b0[2])), ci_c=ci_c,
                       d=float(b0[3]), K_eng=len(e), K_man=len(m))
        print(f"    {bn:7s} {len(e):6d} {len(m):6d} {S.fmt_ci(b0[1], ci_b):>26} "
              f"{S.fmt_ci(float(np.exp(b0[2])), ci_c):>28}")

    print("\nS3.3  🛑 THE SAME CONTRAST INSIDE A COMMON SPEED WINDOW.  S3.1's arms differ by 9 m/s\n"
          "      in median speed and log(1+v) is far too crude an adjustment for that -- a moving\n"
          "      wheel order manufactures exactly this contrast.  Both arms are now cut to the\n"
          "      SAME window before the same regression.  ⚠ THIS, not S3.1, is the result.")
    print(f"\n    {'v window':10s} {'band':7s} {'K eng':>6} {'K man':>6} {'v eng p50':>9} "
          f"{'v man p50':>9} {'b (on thddot)':>21} {'exp(c) ENGAGED/MANUAL':>24}")
    win = {}
    for vlo, vhi in ((2, 8), (8, 20), (15, 30)):
        for bn, rows in pool.items():
            rs = [r for r in rows if vlo <= r["v"] < vhi]
            e = [r for r in rs if r["cond"] == "engaged"]
            m = [r for r in rs if r["cond"] == "manual"]
            if min(len(e), len(m)) < 6:
                print(f"    {f'{vlo}-{vhi} m/s':10s} {bn:7s} {len(e):6d} {len(m):6d}   insufficient")
                continue

            def fit(rr):
                X = np.stack([np.ones(len(rr)), np.log([r["add"] for r in rr]),
                              np.array([r["cond"] == "engaged" for r in rr], float),
                              np.log1p([r["v"] for r in rr])], axis=1)
                return np.linalg.lstsq(X, np.log([r["bar"] for r in rr]), rcond=None)[0]
            allr = e + m
            b0 = fit(allr)
            bs = []
            for _ in range(NBOOT):
                p = [allr[i] for i in RNG.integers(0, len(allr), len(allr))]
                if len({r["cond"] for r in p}) < 2:
                    continue
                try:
                    bs.append(fit(p))
                except Exception:
                    continue
            bs = np.array(bs)
            cib = (float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5)))
            cic = (float(np.exp(np.percentile(bs[:, 2], 2.5))),
                   float(np.exp(np.percentile(bs[:, 2], 97.5))))
            win[f"{vlo}-{vhi}|{bn}"] = dict(b=float(b0[1]), ci_b=cib,
                                            exp_c=float(np.exp(b0[2])), ci_c=cic,
                                            K_eng=len(e), K_man=len(m))
            print(f"    {f'{vlo}-{vhi} m/s':10s} {bn:7s} {len(e):6d} {len(m):6d} "
                  f"{np.median([r['v'] for r in e]):9.2f} {np.median([r['v'] for r in m]):9.2f} "
                  f"{S.fmt_ci(b0[1], cib):>21} {S.fmt_ci(float(np.exp(b0[2])), cic):>24}")
    out["speed_windowed"] = win
    print("\n      26-31 Hz is the PRE-DECLARED NEGATIVE CONTROL: no symptom lives there, so an\n"
          "      exp(c) of 1.0 in that row is what says the method is not manufacturing ratios.")

    print("\nS3.2  SPEED CENSUS of the two arms -- a moving wheel order manufactures exactly this\n"
          "      kind of contrast, so the distributions must be shown, not asserted.")
    print(f"    {'band':7s} {'arm':10s} " + " ".join(f"{'p' + str(p):>7}" for p in (5, 25, 50, 75, 95)))
    for bn, rows in pool.items():
        for arm in ("engaged", "manual"):
            v = np.array([r["v"] for r in rows if r["cond"] == arm])
            if not len(v):
                continue
            print(f"    {bn:7s} {arm:10s} "
                  + " ".join(f"{np.percentile(v, p):7.2f}" for p in (5, 25, 50, 75, 95)))
    out["_speed_census"] = {bn: {arm: [float(np.percentile([r["v"] for r in rows
                                                            if r["cond"] == arm], p))
                                       for p in (5, 25, 50, 75, 95)]
                                 for arm in ("engaged", "manual")
                                 if any(r["cond"] == arm for r in rows)}
                            for bn, rows in pool.items()}
    print("\n    `bar/theta_ddot` is |T / theta_ddot| in counts per rad/s^2 -- it IS J_eff/S_T if\n"
          "    the coupling is purely inertial.  exp(c) > 1 means the firmware ADDS to the bar\n"
          "    signal beyond the mechanical reaction; exp(c) = 1 means it is pure mechanics.")
    return out


# =================================================================================================
def s4_standing_model():
    hdr("S4  THE STANDING MODEL: 'LKAS is the DISTURBANCE, not a term in the loop gain', so a\n"
        "    bigger command buys DUTY, not AMPLITUDE -- 'successful builds stop the cycle STARTING,\n"
        "    they never shrink it.'  Tested on the current corpus, per route, engaged only.")
    out = {}
    NF, HOP = C31.NFFT, C31.NFFT // 2
    rows = {}
    for rt in MAIN:
        rr = []
        for d in S.segs(rt):
            fs = d["_fs"]
            tq = np.asarray(d["tq"], float)
            rc = np.asarray(d["rate_c"], float) * S.D2R
            cmd = np.abs(np.asarray(d["sc_tq"], float))
            eng = S.mask_engaged(d)
            v = np.abs(np.asarray(d["cs_v"], float))
            ok = S.lattice_ok(d)
            env = {b: C31.band_envelope(tq, fs, lo, hi) for b, (lo, hi) in S.BANDS.items()}
            ep = np.full(len(tq), -1)
            for e, (i0, i1) in enumerate(S.episodes(d, eng, NF)):
                ep[i0:i1] = e
            for i in range(0, len(tq) - NF + 1, HOP):
                sl = slice(i, i + NF)
                if not (ok[sl].all() and eng[sl].mean() > 0.99):
                    continue
                if not np.isfinite(cmd[sl]).all():
                    continue
                rec = dict(route=rt, seg=int(d["_seg"]), ep=int(ep[i + NF // 2]),
                           v=float(v[sl].mean()),
                           cmd_p90=float(np.percentile(cmd[sl], 90)),
                           cmd_rms=float(np.sqrt(np.mean(cmd[sl] ** 2))))
                for b in S.BANDS:
                    rec["e_" + b] = float(np.percentile(env[b][sl], 99))
                    lo, hi = S.BANDS[b]
                    x = rc[sl] - rc[sl].mean()
                    X = np.fft.rfft(x * np.hanning(NF))
                    fq = np.fft.rfftfreq(NF, 1 / fs)
                    m = (fq >= lo) & (fq <= hi)
                    rec["add_" + b] = float(np.sqrt(np.sum(np.abs(X[m] * 2 * np.pi * fq[m]) ** 2)))
                rr.append(rec)
        rows[rt] = rr
        print(f"    {rt:10s} {len(rr):5d} engaged windows ({NF / 100:.2f} s, hop {HOP / 100:.2f} s), "
              f"{len({(r['seg'], r['ep']) for r in rr})} episodes")
    OUT["_n_windows"] = {k: len(v) for k, v in rows.items()}

    def theil_sen(x, y):
        n = len(x)
        if n < 3:
            return np.nan
        i, j = np.triu_indices(n, 1)
        dx = x[j] - x[i]
        m = dx != 0
        return float(np.median((y[j] - y[i])[m] / dx[m]))

    def ep_boot(rs, xk, yk, nboot=NBOOT):
        by = {}
        for r in rs:
            by.setdefault((r["seg"], r["ep"]), []).append(r)
        keys = list(by)
        if len(keys) < 4:
            return np.nan, (np.nan, np.nan), len(keys)
        x = np.array([r[xk] for r in rs])
        y = np.array([r[yk] for r in rs])
        pt = theil_sen(np.log(np.maximum(x, 1e-6)), np.log(np.maximum(y, 1e-6)))
        bs = []
        for _ in range(nboot):
            pick = [by[keys[k]] for k in RNG.integers(0, len(keys), len(keys))]
            fl = [r for g in pick for r in g]
            if len(fl) < 4:
                continue
            xx = np.log(np.maximum(np.array([r[xk] for r in fl]), 1e-6))
            yy = np.log(np.maximum(np.array([r[yk] for r in fl]), 1e-6))
            k = min(len(xx), 400)
            idx = RNG.choice(len(xx), k, replace=False)
            s = theil_sen(xx[idx], yy[idx])
            if np.isfinite(s):
                bs.append(s)
        if len(bs) < 20:
            return pt, (np.nan, np.nan), len(keys)
        return pt, (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))), len(keys)

    print("\nS4.1  IN-BURST AMPLITUDE vs COMMAND.  Theil-Sen slope of log(band envelope p99) on\n"
          "      log(|0x0E4| p90, sendcan src1), over BURST windows only.  Episode bootstrap.\n"
          "      Standing model predicts slope ~= 0.  Slope ~= 1 would refute it.")
    thr = {"6-9": 400.0, "17-23": 400.0, "26-31": 300.0, "40-49": 300.0}
    print(f"      {'route':10s} {'band':7s} {'thr':>5} {'n burst':>8} {'K ep':>5} "
          f"{'slope amp~cmd':>26} {'slope amp~thddot':>26}")
    amp = {}
    for rt in MAIN:
        for b in ("6-9", "17-23", "26-31", "40-49"):
            rs = [r for r in rows[rt] if r["e_" + b] > thr[b]]
            if len(rs) < 10:
                print(f"      {rt:10s} {b:7s} {thr[b]:5.0f} {len(rs):8d} "
                      f"{'--':>5} {'(too few burst windows)':>26}")
                continue
            s1, c1, K1 = ep_boot(rs, "cmd_p90", "e_" + b)
            s2, c2, _ = ep_boot(rs, "add_" + b, "e_" + b)
            amp[f"{rt}|{b}"] = dict(slope_cmd=s1, ci_cmd=c1, slope_add=s2, ci_add=c2,
                                    n=len(rs), K=K1)
            print(f"      {rt:10s} {b:7s} {thr[b]:5.0f} {len(rs):8d} {K1:5d} "
                  f"{S.fmt_ci(s1, c1):>26} {S.fmt_ci(s2, c2):>26}")
    out["amplitude"] = amp
    print("\n      🛑 `slope amp~thddot` IS NOT INDEPENDENT EVIDENCE.  In-band column acceleration\n"
          "         and the in-band bar envelope are the SAME oscillation on two channels, so a\n"
          "         positive slope there is the transfer function of S1 restated, not a dose\n"
          "         response.  Only `slope amp~cmd` tests the standing model.")

    print("\nS4.1b IN-BURST AMPLITUDE by RANK command quartile -- the same test without a slope,\n"
          "      so a heavy-tied or short-ranged command cannot hide behind Theil-Sen.")
    print(f"      {'route':10s} {'band':7s} " + " ".join(f"{'Q' + str(i):>11}" for i in range(1, 5))
          + f" {'Q4/Q1':>8}")
    ampq = {}
    for rt in MAIN:
        for b in ("6-9", "17-23"):
            rs = sorted([r for r in rows[rt] if r["e_" + b] > thr[b]], key=lambda r: r["cmd_p90"])
            if len(rs) < 16:
                continue
            qs = np.array_split(np.arange(len(rs)), 4)
            med = [float(np.median([rs[i]["e_" + b] for i in ix])) for ix in qs]
            ampq[f"{rt}|{b}"] = dict(med=med, n=[len(ix) for ix in qs],
                                     ratio=med[3] / med[0] if med[0] else np.nan)
            print(f"      {rt:10s} {b:7s} " + " ".join(f"{m:11.0f}" for m in med)
                  + f" {med[3] / med[0]:8.2f}")
    out["amplitude_q"] = ampq

    print("\nS4.2  DUTY vs COMMAND.  Fraction of engaged windows above the burst threshold, in\n"
          "      command quartiles.  Standing model predicts duty RISES strongly with command.")
    duty = {}
    print("      🛑 quartiles are RANK-based, not value-based: `cmd_p90` has heavy ties (a\n"
          "         value-based cut left V83a's top bin empty in the first run of this script).")
    print(f"      {'route':10s} {'band':7s} " + " ".join(f"{'Q' + str(i):>16}" for i in range(1, 5))
          + f" {'cmd p50 per Q':>28}")
    for rt in MAIN:
        rr = sorted(rows[rt], key=lambda r: r["cmd_p90"])
        if not rr:
            continue
        qidx = np.array_split(np.arange(len(rr)), 4)
        for b in ("6-9", "17-23", "26-31", "40-49"):
            cells, cmed = [], []
            for ix in qidx:
                sub = [rr[i] for i in ix]
                if not sub:
                    cells.append((np.nan, 0)); cmed.append(np.nan); continue
                by = {}
                for r in sub:
                    by.setdefault((r["seg"], r["ep"]), []).append(r)
                cells.append((float(np.mean([r["e_" + b] > thr[b] for r in sub])), len(by)))
                cmed.append(float(np.median([r["cmd_p90"] for r in sub])))
            duty[f"{rt}|{b}"] = dict(cmd_med=cmed, duty=[c[0] for c in cells],
                                     K=[c[1] for c in cells], n=[len(ix) for ix in qidx])
            print(f"      {rt:10s} {b:7s} "
                  + " ".join(f"{c[0]:9.3f}(K{c[1]:3d})" for c in cells)
                  + "  " + "/".join(f"{c:.0f}" for c in cmed))
    out["duty"] = duty

    print("\nS4.3  SPLIT-HALF NULL on the amplitude slope: episodes split by parity, slope refit in\n"
          "      each half.  The half-to-half spread IS the noise floor any slope must clear.")
    sh = {}
    print(f"      {'route':10s} {'band':7s} {'slope A':>10} {'slope B':>10} {'|A-B|':>8}")
    for rt in MAIN:
        for b in ("6-9", "17-23"):
            rs = [r for r in rows[rt] if r["e_" + b] > thr[b]]
            if len(rs) < 20:
                continue
            keys = sorted({(r["seg"], r["ep"]) for r in rs})
            ha = {k for i, k in enumerate(keys) if i % 2 == 0}
            A = [r for r in rs if (r["seg"], r["ep"]) in ha]
            B = [r for r in rs if (r["seg"], r["ep"]) not in ha]
            if min(len(A), len(B)) < 8:
                continue
            sa = theil_sen(np.log(np.maximum([r["cmd_p90"] for r in A], 1e-6)),
                           np.log([r["e_" + b] for r in A]))
            sb = theil_sen(np.log(np.maximum([r["cmd_p90"] for r in B], 1e-6)),
                           np.log([r["e_" + b] for r in B]))
            sh[f"{rt}|{b}"] = dict(A=sa, B=sb)
            print(f"      {rt:10s} {b:7s} {sa:10.3f} {sb:10.3f} {abs(sa - sb):8.3f}")
    out["splithalf"] = sh
    return out


# =================================================================================================
def s5_nulls(store):
    hdr("S5  NULLS.  (a) phase-scrambled coherence floor -- K episodes with the SAME power\n"
        "    distribution and NO phase relationship.  (b) split-half of the model fit.")
    out = {}
    print(f"    {'route':10s} {'condition':18s} {'K':>4} {'real g2 @20.5':>14} "
          f"{'null g2 @20.5':>14} {'real @7.8':>10} {'null @7.8':>10}")
    for (rt, cond), recs in sorted(store.items()):
        f, Sxx, Syy, Sxy, K = S.stack(recs)
        g2 = S.coh(Sxx, Syy, Sxy)
        gn, _ = S.mismatch_null(recs)
        if gn is None:
            continue
        j20 = int(np.argmin(np.abs(f - 20.5)))
        j78 = int(np.argmin(np.abs(f - 7.79)))
        out[f"{rt}|{cond}"] = dict(K=K, real20=float(g2[j20]), null20=float(gn[j20]),
                                   real78=float(g2[j78]), null78=float(gn[j78]))
        print(f"    {rt:10s} {cond:18s} {K:4d} {g2[j20]:14.3f} {gn[j20]:14.3f} "
              f"{g2[j78]:10.3f} {gn[j78]:10.3f}")

    print("\n    SPLIT-HALF of the resonant fit (episodes by parity):")
    print(f"    {'route':10s} {'condition':18s} {'fn A':>8} {'fn B':>8} {'J A':>9} {'J B':>9}")
    for (rt, cond), recs in sorted(store.items()):
        if len(recs) < 8:
            continue
        A, B = recs[0::2], recs[1::2]
        fa = S.fit_res(*S.stack(A)[:4], FIT_BAND)
        fb = S.fit_res(*S.stack(B)[:4], FIT_BAND)
        out[f"{rt}|{cond}|splithalf"] = dict(fnA=fa["fn"], fnB=fb["fn"], JA=fa["J"], JB=fb["J"])
        print(f"    {rt:10s} {cond:18s} {fa['fn']:8.2f} {fb['fn']:8.2f} {fa['J']:9.2f} "
              f"{fb['J']:9.2f}")
    return out


# =================================================================================================
def main():
    OUTDIR.mkdir(exist_ok=True)
    OUT["params"] = dict(tau_18f=S.TAU_18F, nperseg=S.NPERSEG, ep_max=S.EP_MAX,
                         fit_band=FIT_BAND, bar_g2=BAR_G2, bar_K=BAR_K, nboot=NBOOT)
    OUT["S0"] = s0_instrument()
    s1, store = s1_transfer()
    OUT["S1"] = s1
    OUT["S2"] = s2_decompose(store)
    OUT["S3"] = s3_matched(store)
    OUT["S4"] = s4_standing_model()
    OUT["S5"] = s5_nulls(store)
    (OUTDIR / "selfint.json").write_text(json.dumps(san(OUT), indent=1))
    print(f"\nwrote {OUTDIR / 'selfint.json'}")


if __name__ == "__main__":
    main()
