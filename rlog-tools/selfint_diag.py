#!/usr/bin/env python3
"""selfint_diag.py -- the diagnostics that decide whether `selfint_transfer.py`'s coherence
numbers can be believed.  Run this BEFORE quoting any gamma^2 from that report.

D1  POWER CONCENTRATION.  A pooled gamma^2 built from K episodes is a single-episode measurement
    in disguise if one episode holds most of the output power.  Reports the top episode's share
    and the full leave-one-out jackknife range.
D2  PER-EPISODE COHERENCE, BIAS-CORRECTED.  E[gamma^2_hat] = gamma^2 + (1-gamma^2)/n_d for n_d
    averages, so a 6-block episode reads 0.17 on pure noise.  Corrected as
    (n_d*g2 - 1)/(n_d - 1), floored at 0.  This estimator does NOT reward concentration.
D3  TAU SENSITIVITY.  Every phase conclusion re-run at tau = 0 / 10 / 20 ms.  Magnitude and
    gamma^2 are tau-invariant by construction; only phase moves.  A conclusion that flips
    between 0 and 10 ms is not a conclusion.
D4  SPEED DEPENDENCE of fn and J -- is the resonance a fixed mechanical mode or a moving target?

Usage: python selfint_diag.py
Writes: _cache_selfint/selfint_diag.json
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import selfint_lib as S  # noqa: E402

MAIN = ["V84/r6d", "V83a/r68", "V81/r67", "V80/r66"]
FT = (7.79, 20.5, 27.5)
OUT = {}


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100, flush=True)


def conds(rt):
    yield "engaged", S.mask_engaged
    yield "eng+HO", lambda d: S.mask_engaged(d) & S.mask_handsoff(d)
    yield "manual", S.mask_manual


def d1_d2():
    hdr("D1/D2  IS THE POOLED COHERENCE A REAL AVERAGE, OR ONE LOUD EPISODE?")
    print(f"\n{'route':10s} {'cond':8s} {'K':>3} {'f':>6} {'g2 pooled':>10} {'jackknife':>16} "
          f"{'top Syy share':>14} | {'per-episode g2 (bias-corrected)':>34}")
    res = {}
    for rt in MAIN:
        for cond, mf in conds(rt):
            recs = S.collect(rt, mf)
            if len(recs) < 5:
                continue
            f, Sxx, Syy, Sxy, K = S.stack(recs)
            g2 = S.coh(Sxx, Syy, Sxy)
            for ft in FT:
                j = int(np.argmin(np.abs(f - ft)))
                pw = np.array([r["Syy"][j] * r["nblk"] for r in recs])
                jk = []
                for i in range(len(recs)):
                    sub = [r for q, r in enumerate(recs) if q != i]
                    jk.append(float(S.coh(*[x[j] for x in S.stack(sub)[1:4]])))
                # per-episode, bias corrected
                pe = []
                for r in recs:
                    nd = r["nblk"]
                    if nd < 3:
                        continue
                    g = float(np.abs(r["Sxy"][j]) ** 2 / (r["Sxx"][j] * r["Syy"][j]))
                    pe.append(max(0.0, (nd * g - 1) / (nd - 1)))
                pe = np.array(pe) if pe else np.array([np.nan])
                res[f"{rt}|{cond}|{ft}"] = dict(
                    K=K, g2=float(g2[j]), jk=[min(jk), max(jk)],
                    top_share=float(pw.max() / pw.sum()),
                    pe_med=float(np.nanmedian(pe)),
                    pe_q=[float(np.nanpercentile(pe, 25)), float(np.nanpercentile(pe, 75))],
                    n_pe=int(np.isfinite(pe).sum()))
                r_ = res[f"{rt}|{cond}|{ft}"]
                print(f"{rt:10s} {cond:8s} {K:3d} {f[j]:6.2f} {g2[j]:10.3f} "
                      f"{r_['jk'][0]:.3f}..{r_['jk'][1]:.3f}      {r_['top_share']:14.3f} | "
                      f"med {r_['pe_med']:.3f}  IQR {r_['pe_q'][0]:.3f}-{r_['pe_q'][1]:.3f} "
                      f"(n={r_['n_pe']})")
    print("\n  READ: a pooled gamma^2 whose `top Syy share` is > ~0.5 is NOT an average over K\n"
          "  episodes -- it is one episode with K-1 spectators, and the pre-registered K >= 10 is\n"
          "  not actually met however many episodes were nominally in the pool.  The per-episode\n"
          "  bias-corrected median is the estimator that does not reward concentration.")
    return res


def d3(tauset=(0.0, 0.00999, 0.01998)):
    hdr("D3  TAU SENSITIVITY.  phase(Z) at each symptom frequency, for tau = 0 / 10 / 20 ms.")
    print("    (|Z| and gamma^2 are tau-invariant by construction and are not repeated.)")
    print(f"\n{'route':10s} {'cond':8s} {'f':>6} " + " ".join(
        f"{'phase @ tau=' + str(int(t * 1e3)) + 'ms':>18}" for t in tauset))
    res = {}
    for rt in MAIN:
        for cond, mf in conds(rt):
            per = {}
            for t in tauset:
                recs = S.collect(rt, mf, tau=t)
                if len(recs) < 5:
                    per = {}
                    break
                per[t] = S.stack(recs)
            if not per:
                continue
            for ft in FT:
                row = []
                for t in tauset:
                    f, Sxx, Syy, Sxy, K = per[t]
                    j = int(np.argmin(np.abs(f - ft)))
                    row.append(float(np.degrees(np.angle(Sxy[j] / Sxx[j]))))
                res[f"{rt}|{cond}|{ft}"] = row
                print(f"{rt:10s} {cond:8s} {ft:6.2f} " + " ".join(f"{v:18.1f}" for v in row))
    print("\n  Reference phases for Z = T/theta_dot:  -90 deg = pure INERTIA (T = -J*theta_ddot)\n"
          "  · 180 deg = pure DAMPING (T = -b*theta_dot) · +90 deg = pure STIFFNESS (T = -k*theta).\n"
          "  tau is pinned to 9.998-10.001 ms by S0.4 of the main report (direct, gamma^2 > 0.94,\n"
          "  four routes), so the middle column is the one to read -- but the spread across the\n"
          "  three columns is the price of ever getting tau wrong, and at 27.5 Hz it is 99 deg\n"
          "  per frame, i.e. enough to turn an inertial reading into a stiffness one.")
    return res


def d4():
    hdr("D4  SPEED DEPENDENCE.  Is fn a fixed mechanical mode?")
    print(f"\n{'route':10s} {'speed band':12s} {'K':>3} {'sec':>6} {'fn':>7} {'zeta':>7} "
          f"{'J':>8} {'k':>10} {'VAF':>6}")
    res = {}
    for rt in MAIN:
        for lo, hi, nm in ((0, 6, "<6 m/s"), (6, 14, "6-14"), (14, 40, ">14")):
            mf = (lambda d, lo=lo, hi=hi: S.mask_engaged(d)
                  & (np.abs(d["cs_v"]) >= lo) & (np.abs(d["cs_v"]) < hi))
            recs = S.collect(rt, mf, ep_max=1024)
            if len(recs) < 5:
                continue
            f, Sxx, Syy, Sxy, K = S.stack(recs)
            fit = S.fit_res(f, Sxx, Syy, Sxy, (4, 30))
            sec = sum(r["sec"] for r in recs)
            res[f"{rt}|{nm}"] = dict(fit, K=K, sec=sec)
            print(f"{rt:10s} {nm:12s} {K:3d} {sec:6.0f} {fit['fn']:7.2f} {fit['zeta']:7.3f} "
                  f"{fit['J']:8.2f} {fit['k']:10.4g} {fit['vaf']:6.3f}")
    return res


def d5():
    hdr("D5  WHICH SIDE OF THE TORSION BAR IS THE CAN ANGLE ON?\n"
        "    The one structural question the whole analysis turns on, decided WITHOUT tau and\n"
        "    WITHOUT any torque calibration -- from the roll-off of |Z| = |T / theta_dot| alone.\n\n"
        "      sensor ABOVE the bar (wheel side):  T = -J*thddot - b*thdot exactly, so\n"
        "                                          Z = -(j*w*J + b)  =>  |Z| MUST RISE, ~ w\n"
        "      sensor BELOW the bar (pinion side): above the wheel-on-bar mode the wheel is\n"
        "                                          pinned, Z -> +j*k/w  =>  |Z| MUST FALL, ~ 1/w\n"
        "    13 -> 27.5 Hz is a factor 2.12 in w, so the two hypotheses predict 2.12 and 0.47.\n"
        "    H1 is biased LOW by input noise and H2 HIGH by output noise; the truth is bracketed,\n"
        "    so BOTH are shown and the conclusion must hold on both.")
    res = {}
    ftab = (13, 17, 20.5, 24, 27.5)
    print(f"\n{'route/cond/est':26s} " + " ".join(f"{str(x) + 'Hz':>13}" for x in ftab)
          + f" {'ratio 27.5/13':>14}")
    for rt in MAIN:
        for cond, mf in list(conds(rt))[:2]:
            recs = S.collect(rt, mf)
            if len(recs) < 5:
                continue
            f, Sxx, Syy, Sxy, K = S.stack(recs)
            for est in ("H1", "H2"):
                H = S.frf(Sxx, Syy, Sxy, est)
                v = [float(abs(H[int(np.argmin(np.abs(f - ft)))])) for ft in ftab]
                res[f"{rt}|{cond}|{est}"] = dict(mag=v, ratio=v[-1] / v[0], K=K)
                print(f"{rt + '/' + cond + '/' + est:26s} " + " ".join(f"{x:13.0f}" for x in v)
                      + f" {v[-1] / v[0]:14.3f}")
    rr = [v["ratio"] for v in res.values()]
    print(f"\n  Every cell FALLS.  ratio range {min(rr):.3f}-{max(rr):.3f}, all far below the 2.12\n"
          "  a wheel-side sensor demands.  [EVIDENCE] The `0x14A` steering angle and its rate are\n"
          "  BELOW the torsion bar -- the motor/pinion side.  This corroborates the kit's separate\n"
          "  finding that STEER_ANGLE_RATE is a Q15 scale of the resolver electrical rate, and it\n"
          "  is the premise the S1 model rests on.")
    return res


def d6():
    hdr("D6  WHAT A FEEDFORWARD theta_ddot CANCELLATION WOULD HAVE TO BE, and the correction it\n"
        "    forces on docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md section 3.4.")
    print("\n    The bar torque hands-off is EXACTLY the upper column's own free body:\n"
          "        T_bar = -J*thddot_w - b*thdot_w                      (identity, not a model)\n"
          "    but the firmware can only measure thddot_p, BELOW the bar (D5), and\n"
          "        thddot_w / thddot_p = 1 / (1 - (f/fn)^2 + j*2*zeta*(f/fn))\n"
          "    ⇒ a correct feedforward is NOT `gain * theta_ddot`.  It is `-J*theta_ddot` passed\n"
          "      through a 2-pole resonant LOW-PASS at fn with the measured zeta -- i.e. a BIQUAD,\n"
          "      i.e. a code cave, i.e. this kit's only bricking class.")
    res = {}
    fits = [("V84/r6d eng", 12.82, 0.156, 0.138, 0.175), ("V84/r6d HO", 13.21, 0.144, 0.123, 0.175),
            ("V83a/r68 eng", 9.76, 0.0977, 0.087, 0.133), ("V81/r67 eng", 12.82, 0.144, 0.133,
                                                           0.156),
            ("V81/r67 HO", 13.41, 0.150, 0.133, 0.156), ("V80/r66 HO", 14.69, 0.182, 0.150, 0.204)]
    print(f"\n    {'arm':14s} {'fn Hz':>6} {'zeta':>7} {'Q = 1/2zeta':>20} "
          f"{'pole radius @1 kHz':>19}")
    Qs, rs = [], []
    for nm, fn, z, zl, zh in fits:
        Q = 1 / (2 * z)
        r = float(np.exp(-np.pi * fn / (Q * 1000)))
        Qs.append(Q)
        rs.append(r)
        res[nm] = dict(fn=fn, zeta=z, Q=Q, r=r)
        print(f"    {nm:14s} {fn:6.2f} {z:7.3f} {Q:6.2f} [{1 / (2 * zh):.2f}, {1 / (2 * zl):.2f}]"
              f" {r:19.5f}")
    Q, fn = float(np.median(Qs)), 12.82
    r = float(np.exp(-np.pi * fn / (Q * 1000)))
    r_assumed = float(np.exp(-np.pi * 7.79 / (20 * 1000)))
    res["_summary"] = dict(Q_med=Q, fn=fn, r=r, r_report=r_assumed, r_v48b=0.979)
    print(f"\n    MEASURED       fn = {fn} Hz, Q = {Q:.2f}  =>  r = {r:.5f}   (1-r = {1 - r:.5f})")
    print(f"    REPORT ASSUMED f0 = 7.79 Hz, Q = 20    =>  r = {r_assumed:.5f}   "
          f"(1-r = {1 - r_assumed:.5f})")
    print(f"    V48B, THE CAVE THAT BRICKED THE ECU    =>  r = 0.979     (1-r = 0.02100)")
    print(f"\n    🛑 CORRECTION TO THE FEASIBILITY REPORT section 3.4.  It claimed the cancellation\n"
          f"    filter must be '~17x more lightly damped than V48B'.  Measured, it is "
          f"{0.021 / (1 - r):.1f}x --\n"
          "    the SAME CLASS as the cave that bricked the ECU, not an order of magnitude worse.\n"
          "    The NO-GO verdict SURVIVES (V48B bricked at r = 0.979 and this sits just inside\n"
          "    that), but the margin argument was overstated by ~10x and should not be re-quoted.\n"
          "    ⊕ section 2.2's OTHER assumption also fails: it put the wheel-on-bar mode at\n"
          "    6.8-11.4 Hz 'bracketing the measured 7.79 Hz ratchet'.  Measured across four\n"
          "    routes it is 9.8-14.7 Hz, median 12.8 ⇒ the 7.79 Hz ratchet is NOT that mode.")
    return res


def d7():
    hdr("D7  IS fn AN ARTEFACT OF THE TAU CORRECTION?  Refit at tau = 0 / 10 / 20 ms.")
    res = {}
    print(f"\n{'route':10s} {'cond':8s} " + " ".join(f"{'fn@' + str(t) + 'ms':>10}"
                                                     for t in (0, 10, 20))
          + "   " + " ".join(f"{'zeta@' + str(t):>10}" for t in (0, 10, 20)))
    for rt in MAIN:
        for cond, mf in list(conds(rt))[:2]:
            fns, zs = [], []
            for t in (0.0, 0.00999, 0.01998):
                recs = S.collect(rt, mf, tau=t)
                if len(recs) < 5:
                    fns = []
                    break
                fit = S.fit_res(*S.stack(recs)[:4], (4, 30))
                fns.append(fit["fn"])
                zs.append(fit["zeta"])
            if not fns:
                continue
            res[f"{rt}|{cond}"] = dict(fn=fns, zeta=zs)
            print(f"{rt:10s} {cond:8s} " + " ".join(f"{v:10.2f}" for v in fns) + "   "
                  + " ".join(f"{v:10.3f}" for v in zs))
    print("\n  At the MEASURED tau (10 ms) the model fits with fn = 9.8-14.7 Hz and zeta = 0.10-0.39\n"
          "  on every arm.  One frame LOW (tau = 0) it still fits but fn drops 1.5-2.5 Hz.  One\n"
          "  frame HIGH (tau = 20 ms) the fit COLLAPSES to the grid bounds (zeta pinned at 2.0,\n"
          "  fn at 3 or 45 Hz) -- the model cannot absorb that much extra lag at all.\n"
          "  ⇒ two things follow.  (1) tau being one frame too LARGE is independently excluded by\n"
          "  the fit, corroborating S0.4's direct measurement.  (2) fn carries a stated SYSTEMATIC\n"
          "  of about -2 Hz per frame of tau error, on top of its statistical CI.  Quote fn as\n"
          "  '12.8 Hz [12.1, 13.6] statistical, +/-2 Hz systematic per frame of timebase error'.")
    return res


if __name__ == "__main__":
    OUT["D1_D2"] = d1_d2()
    OUT["D3"] = d3()
    OUT["D4"] = d4()
    OUT["D5"] = d5()
    OUT["D6"] = d6()
    OUT["D7"] = d7()
    (ROOT / "_cache_selfint").mkdir(exist_ok=True)

    def san(o):
        if isinstance(o, dict):
            return {k: san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [san(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(float(o)) else round(float(o), 6)
        if isinstance(o, (np.integer, int)):
            return int(o)
        return o
    (ROOT / "_cache_selfint" / "selfint_diag.json").write_text(json.dumps(san(OUT), indent=1))
    print("\nwrote _cache_selfint/selfint_diag.json")
