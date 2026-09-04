# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_m8_knots.py -- M8: a band-limited Kp bump using BOTH axes of the
LERP record, with the knots PICKED FROM THE DATA rather than sketched.

Gate settled first (stutter283, from the image -- see the report): the five X knots are explicit, editable
halfwords at record offsets 0x2..0xA, read every tick by the LERP in FUN_00028ea6 (0x29DC6..0x29E30).
X[0] is NOT implicit; offset 0x0 is a knot COUNT (=5) the LERP does not read.  Honda itself ships FOUR
different X axes across the 28 records.  Hard constraint from 0x29E2C `divq r6,r9`: X must be STRICTLY
increasing -- a duplicate knot is a divide by zero.

K1  the engaged-time and stall/ring index populations, so the knots are placed on measured mass
K2  grid search over X = [0,a,b,c,d], Y = [248,248,K,K,248]: stall benefit vs ring cost, Pareto front
K3  the named candidates (the orchestrator's sketch, the data-picked best, M1/M2) scored side by side --
    per-route ring ratio including the WORST EPISODE, chain |T| into r35's stalls, expected (b)
K4  P-rail duty and |P| in the stall cell for every candidate -- the must-not-reintroduce gate

Run: python stutter_v283_m8_knots.py     Subagent stutter283, 2026-09-03.
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV  # noqa: E402
import strongturn_r32_r33 as ST  # noqa: E402

V = SV.V
FS = SV.FS
CPD = SV.CPD
KP_X = V.KP_X
ROUTES = ("r35", "r36", "r37", "r38")

# per-route measured loop shares at f0 (stutter_v283_memoryless.py M2)
SHARES = {"r35": 0.57 * np.exp(1j * np.radians(104.0)), "r36": 0.69 * np.exp(1j * np.radians(85.0)),
          "r37": 0.47 * np.exp(1j * np.radians(99.0)), "r38": 0.42 * np.exp(1j * np.radians(95.0))}
LTOT248 = 0.90            # BELIEF: the prereg's plant-free model.  ratio * LTOT248 >= 1 => the cycle re-arms


def lerp_tab(X, Y, idx):
    return np.interp(np.asarray(idx, float), np.asarray(X, float), np.asarray(Y, float))


def ratio(Ls, kp_eff):
    return abs(Ls * (kp_eff / 248.0) + (1.0 - Ls))


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes = {t: V.Route(t) for t in ROUTES}
    SIM248 = {t: SV.sim_ki(routes[t], *SV.V280R2, kpY=np.full(5, 248.0), ki=0) for t in ROUTES}

    pr("=" * 178)
    pr("M8 -- A BAND-LIMITED Kp BUMP ON BOTH AXES, KNOTS PICKED FROM THE DATA.  Subagent stutter283, 2026-09-03")
    pr("  Record layout CONFIRMED from _v283_..._plain_image.bin and from the LERP at 0x29DC6..0x29E30:")
    pr("    [0x00] knot count = 5 (NOT read by this LERP) | [0x02..0x0A] X[0..4] | [0x0C..0x14] Y[0..4] | [0x16] pad; stride 0x18")
    pr("    X[0] is EXPLICIT (rec+0x02), not implicit.  Live slot 7 @0xE5378: X [0,68,112,136,208], Y [248]*5.")
    pr("    Honda ships FOUR distinct X axes across the 28 records ([0,68,112,136,208] / [0,48,128,160,208] /")
    pr("    [0,64,112,136,208] / [0,48,112,160,208]) -- the X words are per-record data the LERP reads.  EDITABLE.")
    pr("    HARD GATE: 0x29E2C `divq r6,r9` divides by (X[i]-X[i-1]).  X MUST be strictly increasing.")
    pr("=" * 178)

    # -------------------------------------------------------------------------------------------- K1
    pr("\nK1 -- THE POPULATIONS the knots have to separate (time-weighted index histograms).")
    BINS = [0, 12, 20, 32, 40, 54, 68, 80, 96, 112, 136, 160, 208, 241]
    lab = " ".join("%3d-%3d" % (BINS[i], BINS[i + 1]) for i in range(len(BINS) - 1))
    pr("   %-34s %7s | %s" % ("population", "seconds", lab))

    def hist(ix):
        return " ".join("%7.3f" % np.mean((ix >= BINS[i]) & (ix < BINS[i + 1])) for i in range(len(BINS) - 1))

    # engaged time overall
    eng = np.concatenate([routes[t].idx[routes[t].eng] for t in ROUTES])
    pr("   %-34s %7.1f | %s" % ("ALL ENGAGED (r35-r38)", len(eng) / FS, hist(eng)))
    # the ring: sub-detector F7 episodes
    ringpop, ringep = {}, {}
    for thr in (60, 40):
        per, eps_all = {}, []
        for t in ROUTES:
            r = routes[t]
            ep = [e for e in ST.fixed_thr_episodes(r, thr=thr) if e["ang"] >= 30 and e["fdom"] >= 6]
            ixs = [r.idx[int(e["t0"] * FS):int((e["t0"] + e["dur"]) * FS)] for e in ep]
            if ixs:
                per[t] = ixs
                eps_all += [(t, ix) for ix in ixs]
        ringpop[thr] = per
        ringep[thr] = eps_all
        allix = np.concatenate([ix for _, ix in eps_all])
        pr("   %-34s %7.1f | %s" % ("RING, sub-detector thr %d" % thr, len(allix) / FS, hist(allix)))
    # the stalls
    stalls = {}
    for t in ROUTES:
        r = routes[t]
        R = SIM248[t]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        st = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216) & (ref > 5) & (w < 0.5 * ref)
        stalls[t] = st
        pr("   %-34s %7.1f | %s" % ("STALLED frames, %s" % t, st.sum() / FS, hist(r.idx[st])))
    ALLST = np.concatenate([routes[t].idx[stalls[t]] for t in ROUTES])
    pr("   %-34s %7.1f | %s" % ("STALLED frames, all four", len(ALLST) / FS, hist(ALLST)))
    r35st = routes["r35"].idx[stalls["r35"]]

    # -------------------------------------------------------------------------------------------- K2
    pr("\nK2 -- GRID SEARCH.  X = [0,a,b,c,d], Y = [248,248,K,K,248]: flat 248 below a (highway idx 2-12 untouched),")
    pr("   ramp a->b, plateau K over b..c, ramp c->d, flat 248 above d.  Scored on:")
    pr("     BENEFIT  = mean Kp_eff over r35's stalled frames / 248   (the stall torque multiplier, since fb ~ 0 there)")
    pr("     RING     = max over sub-detector-thr-60 EPISODES of ratio(that episode's mean Kp_eff) on that route's OWN shares,")
    pr("                times |L_tot(248)| = %.2f.  >= 1.00 means the cycle re-arms on that episode." % LTOT248)
    pr("   Constraint: strictly increasing X; a >= 16 so idx 2-12 stays exactly 248.")

    def score(X, Y):
        ben = float(lerp_tab(X, Y, r35st).mean() / 248.0)
        worst, worst_t = 0.0, ""
        for t, ix in ringep[60]:
            k = float(lerp_tab(X, Y, ix).mean())
            v = ratio(SHARES[t], k) * LTOT248
            if v > worst:
                worst, worst_t = v, t
        return ben, worst, worst_t

    cands = []
    AS = (16, 24, 32, 40)
    for a in AS:
        for b in range(a + 8, 121, 8):
            for c in range(b + 8, 177, 8):
                for d in range(c + 8, 233, 8):
                    for K in (341, 380, 420, 460, 512):
                        X = [0, a, b, c, d]
                        Y = [248, 248, K, K, 248]
                        ben, worst, wt = score(X, Y)
                        cands.append((ben, worst, wt, tuple(X), K))
    pr("   searched %d tables" % len(cands))
    pr("\n   PARETO FRONT (max benefit at each ring-safety level; only tables whose worst episode stays under 1.00):")
    safe = [c for c in cands if c[1] < 1.00]
    pr("   %8s %8s %6s | %-28s %5s" % ("benefit", "ring max", "route", "X", "K"))
    front = []
    for lim in (0.90, 0.92, 0.94, 0.96, 0.98, 0.995):
        pool = [c for c in safe if c[1] <= lim]
        if not pool:
            continue
        best = max(pool, key=lambda c: c[0])
        if front and best[3] == front[-1][3] and best[4] == front[-1][4]:
            continue
        front.append(best)
        pr("   %8.3f %8.3f %6s | %-28s %5d   (<= %.3f)" % (best[0], best[1], best[2], str(list(best[3])), best[4], lim))
    pr("   ABSOLUTE BEST BENEFIT among safe tables: %s" % str(max(safe, key=lambda c: c[0])[:5]) if safe else "   none safe")

    # -------------------------------------------------------------------------------------------- K3
    pr("\nK3 -- NAMED CANDIDATES, scored side by side.")
    named = [
        ("V283 on car          flat 248", [0, 68, 112, 136, 208], [248] * 5),
        ("M1  flat 341", [0, 68, 112, 136, 208], [341] * 5),
        ("M2  flat 400", [0, 68, 112, 136, 208], [400] * 5),
        ("BAND (Y-only, oversteer283)", [0, 68, 112, 136, 208], [248, 512, 512, 248, 248]),
        ("M8-sketch  X 0,32,40,80,112", [0, 32, 40, 80, 112], [248, 248, 420, 420, 248]),
    ]
    if front:
        best = max(safe, key=lambda c: c[0])
        named.append(("M8-data    X %s K %d" % (",".join(str(x) for x in best[3][1:]), best[4]), list(best[3]), [248, 248, best[4], best[4], 248]))
        mid = front[len(front) // 2]
        named.append(("M8-cons    X %s K %d" % (",".join(str(x) for x in mid[3][1:]), mid[4]), list(mid[3]), [248, 248, mid[4], mid[4], 248]))
    pr("   %-32s | %5s %5s %5s %5s %5s %5s | %7s | %s" % (
        "candidate", "idx8", "idx26", "idx60", "idx70", "idx92", "idx140", "benefit", "ring ratio x0.90 per route (worst episode) : r35 r36 r37 r38"))
    for nm, X, Y in named:
        ben, worst, wt = score(X, Y)
        per = []
        for t in ROUTES:
            wv = 0.0
            for tt, ix in ringep[60]:
                if tt != t:
                    continue
                wv = max(wv, ratio(SHARES[t], float(lerp_tab(X, Y, ix).mean())) * LTOT248)
            per.append("%.3f" % wv if wv else "  -  ")
        pr("   %-32s | %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f | %7.3f | %s   worst %.3f on %s"
           % (nm, *[lerp_tab(X, Y, i) for i in (8, 26, 60, 70, 92, 140)], ben, " ".join(per), worst, wt))

    # -------------------------------------------------------------------------------------------- K4
    pr("\nK4 -- THE MUST-NOT-REINTRODUCE GATE: |P| and P-RAIL DUTY in the stall cell, and delivered |T|, through the chain")
    pr("   at Ki 0 on each route's own strong-turn hands-light frames.  V283 measured: |P| p50 ~1900, rail duty 0.000-0.002.")
    pr("   %-32s %-5s | %8s %8s %9s | %8s %8s" % ("candidate", "route", "|P| p50", "P-rail", "sum-clamp", "|T| p50", "|T| stall"))
    for nm, X, Y in named:
        Yv = np.asarray(Y, float)
        Xv = np.asarray(X, float)
        for t in ROUTES:
            r = routes[t]
            base = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)
            if base.sum() < 100:
                continue
            kp1k = lerp_tab(Xv, Yv, r.idx1k)
            R = SV.sim_ki(r, *SV.V280R2, kpY=np.full(5, 248.0), ki=0)   # for E / sp (Kp-independent)
            E = R["E"]
            P_raw = np.floor(E * kp1k / 256)
            P = np.clip(P_raw, -V.P_CLAMP, V.P_CLAMP)
            Dt = np.clip(R["D_raw"], -V.D_CLAMP, V.D_CLAMP)
            S_raw = np.floor(V.SUM_MULT * (P + Dt) / 256)
            Sc = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
            Sc[~r.eng1k] = 0.0
            T = np.clip(np.floor(-V.output_lag(Sc) * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
            i = r.i100[base]
            isl = r.i100[stalls[t]]
            pr("   %-32s %-5s | %8.0f %8.4f %9.4f | %8.0f %8.0f" % (
                nm if t == "r35" else "", t, np.median(np.abs(P_raw[i])), float(np.mean(np.abs(P_raw[i]) >= V.P_CLAMP)),
                float(np.mean(np.abs(S_raw[i]) >= V.SUM_CLAMP)), np.median(np.abs(T[i])),
                np.median(np.abs(T[isl])) if stalls[t].sum() > 20 else np.nan))
        pr("")

    out = os.path.join(HERE, "_scratch", "stutter_v283_m8_knots.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
