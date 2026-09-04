# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_f7_by_index.py -- WHERE DOES THE 7 Hz RING LIVE, BY DEMAND INDEX?

The decision: oversteer283's band-limited un-flattening is Kp Y = 248,512,512,248,248 on X = 0,68,112,136,208,
i.e. Honda's gain restored over the STALL band and flat 248 elsewhere.  It is only free if the 7 Hz ring lives
at a demand index OUTSIDE the band that table raises.  This script settles it from the frames themselves.

F1  every F7 episode on r32/r33/r34 (fixed-103 detector, |angle| >= 30, fdom >= 6) tabulated by the demand
    index ACTUALLY PREVAILING during the episode -- per-episode p10/p50/p90 and a TIME-WEIGHTED histogram over
    the episode frames, pooled per route and across routes.  Not the window-selection index.
F2  the same tabulation for r35/r36/r37/r38's SUB-DETECTOR ring (thresholds 60 and 40 wire), since the residual
    ring is what a Kp change would move.
F3  the LERP the proposal actually delivers, evaluated at the ring's own index distribution, and the resulting
    ring ratio |Ls*(Kp_eff/248) + Lr| using the measured loop shares (stutter_v283_memoryless.py M2).
F4  does Kp 512 over idx 40-136 BUY BACK the P-desaturation-on-a-stalled-wheel signature?  The proposed table
    run through the chain on r35's (Ki 0) and r36-r38's own frames: |P| p50, P-rail duty, sum-clamp duty,
    delivered |T| in the stall cell.

Run: python stutter_v283_f7_by_index.py     Subagent stutter283, 2026-09-03.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV  # noqa: E402
import strongturn_r32_r33 as ST  # noqa: E402

V = SV.V
FS = SV.FS
CPD = SV.CPD

# the proposal under test, and the alternatives
KP_X = V.KP_X                                            # 0, 68, 112, 136, 208
KP_BAND = np.array([248, 512, 512, 248, 248], float)     # oversteer283's band-limited un-flattening
KP_FLAT248 = np.full(5, 248.0)
KP_FLAT341 = np.full(5, 341.0)
KP_STOCK = V.KP_Y                                        # 248, 512, 645, 696, 696

# per-route build cells: r32/r33 = V278 rev 3 (map x2, fb clamp 15360); r34-r38 = V280 rev 2 (line x6, 46080)
CELLS = {"r32": ST.REV3, "r33": ST.REV3, "r34": SV.V280R2,
         "r35": SV.V280R2, "r36": SV.V280R2, "r37": SV.V280R2, "r38": SV.V280R2}
OLD = ("r32", "r33", "r34")
NEW = ("r35", "r36", "r37", "r38")
BANDS = ((0, 20), (20, 40), (40, 68), (68, 112), (112, 136), (136, 200), (200, 242))
BANDLAB = " ".join("%3d-%3d" % b for b in BANDS)


def hist_time(idx, bands=BANDS):
    n = max(len(idx), 1)
    return [float(np.mean((idx >= lo) & (idx < hi))) for lo, hi in bands]


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes = {}
    for tag in OLD + NEW:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)

    pr("=" * 178)
    pr("WHERE THE 7 Hz RING LIVES, BY DEMAND INDEX -- settling oversteer283's band-limited Kp proposal.  Subagent stutter283, 2026-09-03")
    pr("  Proposal under test: 0xE5378 Y = 248,512,512,248,248 on X = 0,68,112,136,208.  The LERP it delivers:")
    for i in (0, 20, 40, 55, 68, 80, 92, 103, 112, 120, 134, 136, 150, 200, 240):
        pass
    pr("    idx  " + " ".join("%5d" % i for i in (0, 20, 40, 55, 68, 80, 92, 103, 112, 124, 136, 150, 200, 240)))
    pr("    Kp   " + " ".join("%5.0f" % V.lerp(KP_X, KP_BAND, i) for i in (0, 20, 40, 55, 68, 80, 92, 103, 112, 124, 136, 150, 200, 240)))
    pr("    (flat 341 alternative is 341 at every index; V283/V282 on the car is 248 at every index)")
    pr("=" * 178)

    # ------------------------------------------------------------------------------------------- F1
    pr("\nF1 -- EVERY F7 EPISODE ON r32/r33/r34 (V280 rev 2 / V278 rev 3, the builds the ring was MEASURED on),")
    pr("   fixed-103 detector, |angle| >= 30, fdom >= 6, tabulated by the demand index PREVAILING DURING THE EPISODE.")
    pr("   %-5s %7s %5s %5s %5s | %5s %5s %5s %5s | time-weighted idx histogram over the episode frames: %s" % (
        "route", "t0", "dur", "fdom", "ang", "idxp10", "idxp50", "idxp90", "idxmax", BANDLAB))
    pool = {t: [] for t in OLD}
    for tag in OLD:
        r = routes[tag]
        eps = [e for e in ST.fixed_thr_episodes(r) if e["ang"] >= 30 and e["fdom"] >= 6]
        for e in eps:
            a, b = int(e["t0"] * FS), int((e["t0"] + e["dur"]) * FS)
            ix = r.idx[a:b]
            pool[tag].append(ix)
            pr("   %-5s %7.1f %5.1f %5.2f %5.0f | %5.0f %5.0f %5.0f %5.0f | %s" % (
                tag, e["t0"], e["dur"], e["fdom"], e["ang"], *np.percentile(ix, [10, 50, 90]), ix.max(),
                " ".join("%7.3f" % v for v in hist_time(ix))))
        if not eps:
            pr("   %-5s  (no F7 episodes at the fixed-103 threshold)" % tag)

    pr("\n   POOLED per route and across r32+r33+r34 (time-weighted over all F7 episode frames):")
    allix = []
    for tag in OLD:
        if not pool[tag]:
            continue
        ix = np.concatenate(pool[tag])
        allix.append(ix)
        pr("   %-5s n %5d frames (%5.1f s), %2d episodes | idx p10/p50/p90 %5.0f/%5.0f/%5.0f | %s | INSIDE idx 40-136: %.3f"
           % (tag, len(ix), len(ix) / FS, len(pool[tag]), *np.percentile(ix, [10, 50, 90]),
              " ".join("%7.3f" % v for v in hist_time(ix)), float(np.mean((ix >= 40) & (ix < 136)))))
    A = np.concatenate(allix)
    pr("   %-5s n %5d frames (%5.1f s), %2d episodes | idx p10/p50/p90 %5.0f/%5.0f/%5.0f | %s | INSIDE idx 40-136: %.3f"
       % ("ALL", len(A), len(A) / FS, sum(len(pool[t]) for t in OLD), *np.percentile(A, [10, 50, 90]),
          " ".join("%7.3f" % v for v in hist_time(A)), float(np.mean((A >= 40) & (A < 136)))))

    # ------------------------------------------------------------------------------------------- F2
    pr("\nF2 -- THE SUB-DETECTOR RING on r35 (Ki 0) and r36/r37/r38 (V283), same tabulation, at thresholds 60 and 40 wire.")
    pr("   The residual ring is what a Kp raise would move, so its index distribution is the one that prices the proposal.")
    subpool = {}
    for thr in (60, 40):
        pr("\n   -- threshold %d wire --" % thr)
        pr("   %-5s %7s %5s %5s %5s | %5s %5s %5s | %s" % ("route", "t0", "dur", "fdom", "ang", "idxp10", "idxp50", "idxp90", BANDLAB))
        for tag in NEW:
            r = routes[tag]
            eps = [e for e in ST.fixed_thr_episodes(r, thr=thr) if e["ang"] >= 30 and e["fdom"] >= 6]
            ixs = []
            for e in eps:
                a, b = int(e["t0"] * FS), int((e["t0"] + e["dur"]) * FS)
                ix = r.idx[a:b]
                ixs.append(ix)
                pr("   %-5s %7.1f %5.1f %5.2f %5.0f | %5.0f %5.0f %5.0f | %s" % (
                    tag, e["t0"], e["dur"], e["fdom"], e["ang"], *np.percentile(ix, [10, 50, 90]),
                    " ".join("%7.3f" % v for v in hist_time(ix))))
            if ixs:
                subpool[(tag, thr)] = np.concatenate(ixs)
            else:
                pr("   %-5s  (none)" % tag)
        got = [subpool[(t, thr)] for t in NEW if (t, thr) in subpool]
        if got:
            ix = np.concatenate(got)
            subpool[("ALL", thr)] = ix
            pr("   %-5s POOLED n %5d frames (%5.1f s) | idx p10/p50/p90 %5.0f/%5.0f/%5.0f | %s | INSIDE idx 40-136: %.3f"
               % ("r35-38", len(ix), len(ix) / FS, *np.percentile(ix, [10, 50, 90]),
                  " ".join("%7.3f" % v for v in hist_time(ix)), float(np.mean((ix >= 40) & (ix < 136)))))

    # ------------------------------------------------------------------------------------------- F3
    pr("\nF3 -- WHAT THE PROPOSAL COSTS AT THE RING.  Effective Kp under each candidate table, evaluated over the ring's OWN")
    pr("   index distribution, and the resulting return ratio |Ls*(Kp_eff/248) + Lr| with the measured shares.")
    pr("   Pooled measured shares (stutter_v283_memoryless M2, 63 windows): Ls 0.55 @ +96 deg, Lr = 1 - Ls = 1.19 @ -27 deg.")
    Ls = 0.55 * np.exp(1j * np.radians(96.0))
    Lr = 1.0 - Ls
    cands = (("V283 on car  flat 248", KP_FLAT248), ("BAND 248,512,512,248,248", KP_BAND),
             ("flat 341 (V281 rev 2)", KP_FLAT341), ("stock LERP", KP_STOCK))
    pr("   %-40s | %-38s | %s" % ("ring population", "Kp_eff over that population p10/p50/p90/mean", "ring ratio at Kp_eff p50 / mean"))
    pops = [("r32+r33+r34 F7 episodes (fixed-103)", A)]
    for thr in (60, 40):
        if ("ALL", thr) in subpool:
            pops.append(("r35-r38 sub-detector ring, thr %d" % thr, subpool[("ALL", thr)]))
    for nm, table in cands:
        pr("   --- %s" % nm)
        for pn, ix in pops:
            k = V.lerp(KP_X, table, ix)
            p10, p50, p90 = np.percentile(k, [10, 50, 90])
            km = k.mean()
            pr("       %-38s | %5.0f / %5.0f / %5.0f / %5.0f            | %.3f / %.3f"
               % (pn, p10, p50, p90, km, abs(Ls * (p50 / 248.0) + Lr), abs(Ls * (km / 248.0) + Lr)))
    pr("\n   The same, per route's OWN measured shares (A9.3), evaluated at the r35-r38 thr-60 ring population's Kp_eff:")
    SH = {"r35": 0.57 * np.exp(1j * np.radians(104.0)), "r36": 0.69 * np.exp(1j * np.radians(85.0)),
          "r37": 0.47 * np.exp(1j * np.radians(99.0)), "r38": 0.42 * np.exp(1j * np.radians(95.0))}
    ixr = subpool.get(("ALL", 60))
    if ixr is not None:
        pr("       %-8s | %s" % ("shares", " | ".join("%-24s" % nm for nm, _ in cands)))
        for tg, Lsr in SH.items():
            Lrr = 1.0 - Lsr
            cells = []
            for nm, table in cands:
                km = V.lerp(KP_X, table, ixr).mean()
                cells.append("Kp_eff %3.0f -> ratio %.3f" % (km, abs(Lsr * (km / 248.0) + Lrr)))
            pr("       %-8s | %s" % (tg, " | ".join("%-24s" % c for c in cells)))
        pr("       (multiply by |L_tot(248)| ~ 0.90 for the absolute return ratio; >= 1.0 means the cycle re-arms)")

    # ------------------------------------------------------------------------------------------- F4
    pr("\nF4 -- DOES Kp 512 OVER idx 40-136 BUY BACK THE P-DESATURATION SIGNATURE?  The proposed table through the chain")
    pr("   (Ki 0, as the proposal is 'remove Ki'), on each route's own strong-turn hands-light frames (|angle| >= 30,")
    pr("   idx 40-200, |tq| < 1216).  Compare against V283's measured signature: |P| p50 ~1900, rail duty 0.000-0.002.")
    pr("   %-5s %-26s | %6s %8s %8s %8s %8s %8s" % ("route", "Kp table", "n", "|P| p50", "P-rail", "sum-clamp", "|T| p50", "|T| stall"))
    for tag in NEW:
        r = routes[tag]
        base = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)
        if base.sum() < 100:
            continue
        R248 = SV.sim_ki(r, *CELLS[tag], kpY=KP_FLAT248, ki=0)
        ref = R248["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        st = base & (ref > 5) & (w < 0.5 * ref)
        for nm, table in cands:
            R = SV.sim_ki(r, *CELLS[tag], kpY=table, ki=0)
            i = r.i100[base]
            isl = r.i100[st]
            pr("   %-5s %-26s | %6d %8.0f %8.4f %8.4f %8.0f %8.0f" % (
                tag, nm, base.sum(), np.median(np.abs(R["P_raw"][i])), float(np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP)),
                float(np.mean(np.abs(R["S_raw"][i]) >= V.SUM_CLAMP)), np.median(np.abs(R["T"][i])),
                np.median(np.abs(R["T"][isl])) if st.sum() > 20 else np.nan))
        pr("   %-5s %-26s | %6d %8s %8s %8s %8.0f %8.0f" % (
            tag, "MEASURED on the wire", base.sum(), "-", "-", "-", np.median(np.abs(r.T_meas[base])),
            np.median(np.abs(r.T_meas[st])) if st.sum() > 20 else np.nan))
        pr("")

    out = os.path.join(HERE, "_scratch", "stutter_v283_f7_by_index.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
