# -*- coding: utf-8 -*-
"""ATTACK 3 -- EXPOSURE-WEIGHTED RANKING STABILITY (leave-one-route-out), and
   ATTACK 5b -- is the wheel->yaw difference a comparison error or an input-noise bias?

The ranking metric is rebuilt here from scratch as the task defines it: NRMSE = RMS of
(achieved - desired) in units of the in-band demand RMS, per cell, in the frequency domain

    M_tot^2 = sum_band (Syy - 2 Re Sxy + Sxx) / sum_band Sxx        (includes incoherent motion)
    M_coh^2 = sum_band |H-1|^2 Sxx / sum_band Sxx                   (the demand-explained part only)

No |H| enters the ranking.  Cell score = exposure fraction x (M_torque - M_V282).
"""
import json
import numpy as np
import adv_lib as L

CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}
BANDS = [(0.15, 0.30, 2048), (0.30, 0.60, 1024), (0.60, 1.20, 1024), (1.20, 2.40, 512)]
MINWIN = 4


def loadn(n):
    R = {}
    for r in L.ROUTES:
        D = np.load(L.OUT / f"spec_{r}_n{n}.npz")
        R[r] = dict(F=D["F_lin_hann"], fr=D["m_fr"], v=D["m_v"], ap95=D["m_ap95"],
                    sa95=D["m_sa95"], n=n)
    return R


def nrmse(F, fr, f1, f2, ix="X", iy="Y"):
    b = (fr >= f1) & (fr < f2)
    X = F[:, CHI[ix]][:, :, b]
    Y = F[:, CHI[iy]][:, :, b]
    Sxx = (np.abs(X) ** 2).sum((0, 1))
    Syy = (np.abs(Y) ** 2).sum((0, 1))
    Sxy = (np.conj(X) * Y).sum((0, 1))
    tot = float((Syy - 2 * np.real(Sxy) + Sxx).sum() / max(Sxx.sum(), 1e-300))
    Hb = Sxy / np.maximum(Sxx, 1e-300)
    coh = float((np.abs(Hb - 1.0) ** 2 * Sxx).sum() / max(Sxx.sum(), 1e-300))
    return np.sqrt(max(tot, 0)), np.sqrt(max(coh, 0)), int(X.shape[0])


def cellsets(R, rts, sb, ab):
    lo, hi = L.SPD[sb]
    a0, a1 = L.ACUT[ab]
    Fs = []
    for r in rts:
        d = R[r]
        m = (d["v"] >= lo) & (d["v"] < hi) & (d["ap95"] >= a0) & (d["ap95"] < a1)
        if m.sum():
            Fs.append(d["F"][m])
    return np.concatenate(Fs, 0) if Fs else None


def build(vr, tr, Rn):
    """Return {cell: dict} of NRMSE for the two groups plus the torque exposure weight."""
    # exposure from the torque windows at the coarsest n (window seconds is exposure, by construction)
    Rex = Rn[1024]
    expo, tot = {}, 0.0
    for sb in range(4):
        for ab in range(3):
            lo, hi = L.SPD[sb]
            a0, a1 = L.ACUT[ab]
            s = 0.0
            for r in tr:
                d = Rex[r]
                m = (d["v"] >= lo) & (d["v"] < hi) & (d["ap95"] >= a0) & (d["ap95"] < a1)
                s += m.sum() * 1024 / 100.0
            expo[(sb, ab)] = s
            tot += s
    out = {}
    for f1, f2, n in BANDS:
        R = Rn[n]
        for sb in range(4):
            for ab in range(3):
                Fv, Ft = cellsets(R, vr, sb, ab), cellsets(R, tr, sb, ab)
                if Fv is None or Ft is None:
                    continue
                mv = nrmse(Fv, R[vr[0]]["fr"], f1, f2)
                mt = nrmse(Ft, R[tr[0]]["fr"], f1, f2)
                if mv[2] < MINWIN or mt[2] < MINWIN:
                    continue
                w = expo[(sb, ab)] / max(tot, 1e-9) / len(BANDS)
                out[(f"{f1:.2f}-{f2:.2f}", L.SPDN[sb], L.ACUTN[ab])] = dict(
                    Mv=mv[0], Mt=mt[0], Mvc=mv[1], Mtc=mt[1], nv=mv[2], nt=mt[2],
                    w=w, score=w * (mt[0] - mv[0]), score_coh=w * (mt[1] - mv[1]))
    return out


def main():
    Rn = {n: loadn(n) for n in (512, 1024, 2048)}
    full = build(L.V282, L.TORQ, Rn)
    rows = sorted(full.items(), key=lambda kv: -kv[1]["score"])
    print("=" * 150)
    print("1. THE RANKING, rebuilt from scratch on NRMSE (not |H|).  M_tot includes the incoherent motion;")
    print("   M_coh is the demand-explained part.  w = torque exposure fraction of that speed x amp cell / 4 bands.")
    print("=" * 150)
    print(f"  {'band':11s} {'speed':6s} {'amp':3s} {'w%':>6s} {'M V282':>7s} {'M TORQ':>7s} {'dM':>7s} "
          f"{'score':>7s} | {'Mcoh V':>7s} {'Mcoh T':>7s} {'dcoh':>7s} {'nV':>4s} {'nT':>4s}")
    for k, d in rows[:18]:
        print(f"  {k[0]:11s} {k[1]:6s} {k[2]:3s} {100*d['w']:6.2f} {d['Mv']:7.3f} {d['Mt']:7.3f} "
              f"{d['Mt']-d['Mv']:+7.3f} {d['score']:7.4f} | {d['Mvc']:7.3f} {d['Mtc']:7.3f} "
              f"{d['Mtc']-d['Mvc']:+7.3f} {d['nv']:4d} {d['nt']:4d}")

    print("\n" + "=" * 150)
    print("2. LEAVE-ONE-ROUTE-OUT.  Drop one route, rebuild the whole surface and the whole ranking.")
    print("   'rank1' is the top cell; 'rank of full-#1' is where the full ranking's winner lands.")
    print("=" * 150)
    top_full = rows[0][0]
    print(f"  full ranking #1 = {top_full}  score {rows[0][1]['score']:.4f}")
    print(f"  {'dropped route':24s} {'grp':6s} {'new #1':40s} {'score':>8s} {'rank of full-#1':>16s} {'its score':>10s}")
    for drop in list(L.V282) + list(L.TORQ):
        vr = [r for r in L.V282 if r != drop]
        tr = [r for r in L.TORQ if r != drop]
        if not vr or not tr:
            continue
        o = build(vr, tr, Rn)
        rr = sorted(o.items(), key=lambda kv: -kv[1]["score"])
        pos = next((i + 1 for i, (k, _) in enumerate(rr) if k == top_full), None)
        sc = o.get(top_full, {}).get("score", float("nan"))
        print(f"  {drop:24s} {L.ROUTES[drop]['g']:6s} {str(rr[0][0]):40s} {rr[0][1]['score']:8.4f} "
              f"{str(pos):>16s} {sc:10.4f}")

    print("\n" + "=" * 150)
    print("3. THE V282 REFERENCE IS ONE ROUTE.  Engaged window-seconds behind each side of every top cell.")
    print("=" * 150)
    R = Rn[1024]
    for k, d in rows[:8]:
        sb = L.SPDN.index(k[1]); ab = L.ACUTN.index(k[2])
        lo, hi = L.SPD[sb]; a0, a1 = L.ACUT[ab]
        per = []
        for r in L.V282:
            dd = R[r]
            m = (dd["v"] >= lo) & (dd["v"] < hi) & (dd["ap95"] >= a0) & (dd["ap95"] < a1)
            if m.sum():
                per.append(f"{r[:8]}:{m.sum()}")
        print(f"  {k}  V282 windows by route: {', '.join(per) if per else 'NONE'}")

    print("\n" + "=" * 150)
    print("4. WHEEL -> YAW, the control, with an estimator that is UNBIASED FOR INPUT NOISE.")
    print("   H1 = Sxy/Sxx is biased DOWN by noise on the INPUT.  Torque mode puts x3-5 more 1.8-3.5 Hz")
    print("   motion on the steering wheel, so H1(W->Y) must read lower on torque mode even with an")
    print("   identical vehicle.  H2 = Syy/|Sxy| is unbiased for input noise and biased UP by output noise.")
    print("   The truth is bracketed by [H1, H2]; the two builds agree iff their brackets overlap.")
    print("=" * 150)
    R = Rn[1024]
    for sb in range(4):
        lo, hi = L.SPD[sb]
        for f1, f2 in ((0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)):
            o = []
            for rts in (L.V282, L.TORQ):
                Fs, vs = [], []
                for r in rts:
                    d = R[r]
                    m = (d["v"] >= lo) & (d["v"] < hi)
                    if m.sum():
                        Fs.append(d["F"][m]); vs.append(d["v"][m])
                if not Fs:
                    o.append(None); continue
                c = L.cell(np.concatenate(Fs, 0), CHI["W"], CHI["Y"], f1, f2, R[rts[0]]["fr"])
                c["v50"] = float(np.median(np.concatenate(vs)))
                o.append(c)
            cv, ct = o
            if cv and ct:
                s = (ct["v50"] / cv["v50"]) ** 2
                print(f"  {L.SPDN[sb]:6s} {f1:.2f}-{f2:.2f}  V282 [H1 {cv['H1']:.4f}, H2 {cv['H2']:.4f}] "
                      f"TORQ [H1 {ct['H1']/s:.4f}, H2 {ct['H2']/s:.4f}] (v-normalised)  "
                      f"brackets overlap: {'YES' if max(cv['H1'],ct['H1']/s) <= min(cv['H2'],ct['H2']/s) else 'NO '}"
                      f"   g2 {cv['g2']:.2f}/{ct['g2']:.2f}")


if __name__ == "__main__":
    main()
