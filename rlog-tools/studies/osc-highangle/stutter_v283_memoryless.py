# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_memoryless.py -- pricing the MEMORYLESS (static, feed-forward)
replacements for the P-only deadband, against the 7 Hz ring margin that Kp flat 248 bought.

Orchestrator's constraint (operator, structural): openpilot models the EPS output as a TORQUE, so integral
action inside the EPS turns it into a rate/position servo and changes the interface the outer tune was
calibrated against.  Rank fixes that raise delivered torque at a given command WITHOUT adding state.

M1  the command -> rate DC GAIN per route, matched frames (handed to oversteer283; ONE definition, several
    strata, so both agents quote the same number)
M2  the RING MARGIN vs Kp, derived from the MEASURED loop shares.  r24_deembed's split is normalised:
    Ls = zT/(zT+zr), Lr = zr/(zT+zr), so Ls + Lr == 1 identically.  The SERVO arm scales linearly with Kp
    and the r24 arm does not, so the return ratio at f0 scales as
        L_tot(Kp) / L_tot(248) = | Ls * (Kp/248) + Lr |
    which is computable per window from data already measured.  Solving |...| = 1/|L_tot(248)| gives the Kp
    at which the cycle re-arms.  Reported alongside the EMPIRICAL bracket, which is the trustworthy number.
M3  WHERE THE RING LIVES: the demand-index distribution of the ring windows, so a partial Kp un-flattening
    can be sited in the idx band where the stalls are and away from the band where the ring is.
M4  WHAT THE DEADBAND FIX HAS TO DELIVER: the torque at which strong-turn frames stop stalling, measured
    within V283 and against r35, and what each memoryless lever must be multiplied by to reach it.
M5  the map lever's SELF-CANCELLATION on statistic (b): raising the assist map raises the delivered torque
    AND the reference in the same proportion, so it breaks stalls without moving rate/reference.

Run: python stutter_v283_memoryless.py     Subagent stutter283, 2026-09-03.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV  # noqa: E402
import strongturn_r35 as S35  # noqa: E402
import r24_deembed as RD  # noqa: E402

V = SV.V
FS = SV.FS
CPD = SV.CPD
ROUTES = SV.ROUTES
KI_ONCAR = SV.KI_ONCAR

# V280 rev 2's assist map (on the car since V280) and the stock slot-7 map, from build_v283_tva.py / v280_map_profiles
MAP_X = V.MAP_X
MAP_V280R2 = SV.V280R2[0]
MAP_STOCK = V.MAP_Y
KP_X = V.KP_X
KP_STOCK = V.KP_Y                     # 248, 512, 645, 696, 696 at idx 0, 68, 112, 136, 208
KP_FLAT248 = np.full(5, 248.0)


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes, gs, b4s, SIM = {}, {}, {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
        gs[tag] = RD.load(tag)
        b4s[tag] = SV.load_b4(tag, routes[tag])
        SIM[tag] = SV.sim_ki(routes[tag], *SV.V280R2, kpY=KP_FLAT248, ki=KI_ONCAR[tag])
        print("  simulated %s" % tag, flush=True)

    pr("=" * 175)
    pr("MEMORYLESS DEADBAND FIXES vs THE 7 Hz RING -- pricing, from measured data.  Subagent stutter283, 2026-09-03")
    pr("=" * 175)

    # -------------------------------------------------------------------------------------------- M1
    pr("\nM1 -- COMMAND -> RATE DC GAIN per route (handed to oversteer283; quote THIS line).")
    pr("   (i) rate / map-reference: the inner loop's own DC gain, matched on demand index.  Frames: engaged, |angle| >= 30,")
    pr("       hands-light (|tq_raw| < 1216).  This is prereg (b) generalised across the whole index range.")
    pr("   (ii) LS slope of wheel rate on the map reference over the same frames (no binning, forced through 0).")
    pr("   (iii) rate per unit 0xE4 command, LS slope, engaged hands-light moving frames -- the gain openpilot's outer loop sees.")
    hdr = "  %-5s | %s | %8s %8s | %8s %8s" % ("route", " ".join("idx%3d-%3d" % (a, b) for a, b in ((20, 40), (40, 80), (80, 120), (120, 200), (200, 241))),
                                               "LS r/ref", "corr", "LS r/cmd", "corr")
    pr(hdr)
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        cells = []
        for lo, hi in ((20, 40), (40, 80), (80, 120), (120, 200), (200, 241)):
            m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= lo) & (r.idx < hi) & (np.abs(r.tq_raw) < 1216)
            cells.append("   %.2f    " % (np.median(w[m]) / max(np.median(ref[m]), 1e-9)) if m.sum() >= 30 else "     --    ")
        m = r.eng & (np.abs(r.ang) >= 30) & (np.abs(r.tq_raw) < 1216) & (r.idx >= 20) & (ref > 3)
        sl = float(np.sum(w[m] * ref[m]) / np.sum(ref[m] ** 2))
        cc = float(np.corrcoef(w[m], ref[m])[0, 1])
        mc = r.eng & (np.abs(r.tq_raw) < 1216) & (r.idx >= 20)
        c = np.abs(r.cmd[mc])
        sl2 = float(np.sum(w[mc] * c) / np.sum(c ** 2))
        cc2 = float(np.corrcoef(w[mc], c)[0, 1])
        pr("  %-5s | %s | %8.3f %8.3f | %8.4f %8.3f" % (tag, " ".join(cells), sl, cc, sl2, cc2))
    pr("   (reference deg/s = 32*|sp|/FB_DC/CPD through the V280 rev 2 line map; 'r/cmd' is deg/s per raw 0xE4 count.)")

    # -------------------------------------------------------------------------------------------- M2/M3
    pr("\nM3 -- WHERE THE RING LIVES: the demand-index distribution of the ring windows (hands-light strong-turn 1 s windows,")
    pr("   ranked by 6-8.5 Hz tap ripple/level).  A partial Kp un-flattening is only safe if the stall band and the ring band are disjoint.")
    disc = {}
    for tag in ROUTES:
        r = routes[tag]
        RD.KP_Y = KP_FLAT248
        rows = [S35.disc_row(gs[tag], t0, dur, b4s[tag], r) for t0, dur in S35.strong_windows(r, tq_max=2240)]
        disc[tag] = rows
        if not rows:
            continue
        idxs = np.array([x["idx"] for x in rows])
        rl = np.array([x["rl"] for x in rows])
        top = idxs[rl >= np.percentile(rl, 60)]
        pr("  %s n %2d windows: idx p10/p25/p50/p75/p90 = %3.0f/%3.0f/%3.0f/%3.0f/%3.0f | the top-40%% ripple windows sit at idx p25-p75 %3.0f-%3.0f (median %3.0f)"
           % (tag, len(rows), *np.percentile(idxs, [10, 25, 50, 75, 90]), np.percentile(top, 25), np.percentile(top, 75), np.median(top)))
        for lo, hi in ((40, 68), (68, 120), (120, 200), (200, 241)):
            s = (idxs >= lo) & (idxs < hi)
            if s.sum():
                pr("       idx %3d-%3d: %2d windows, rip/L median %.3f, rate@f0 %.1f deg/s, f0 %.2f Hz" % (lo, hi, s.sum(), np.median(rl[s]),
                   np.median([x["Arate"] for x, k in zip(rows, s) if k]), np.median([x["f0"] for x, k in zip(rows, s) if k])))

    pr("\nM2 -- THE RING MARGIN vs Kp, from the MEASURED loop shares (Ls + Lr == 1 by construction; only the SERVO arm scales with Kp).")
    pr("   ratio(Kp) = | Ls*(Kp/248) + Lr |  = the return ratio at f0 relative to its value at Kp 248.")
    pr("   The cycle re-arms when the ABSOLUTE return ratio reaches 1.  |L_tot(248)| is NOT measured on this drive -- the prereg's")
    pr("   plant-free model put it at 0.88-0.91, so the headroom is 1/0.90 = 1.11x.  Kp_crit below uses 0.90; the row 'at 0.95' is the")
    pr("   pessimistic case.  BELIEF on |L_tot(248)|; EVIDENCE on Ls and Lr and therefore on the SHAPE of the curve.")
    KPS = (248, 300, 341, 400, 450, 512, 600, 696)
    pr("  %-5s | %-22s | %s | %s" % ("route", "measured Ls / Lr at f0", " ".join("Kp%4d" % k for k in KPS), "Kp_crit @|L(248)|=0.90 / 0.95"))
    for tag in ROUTES:
        rows = disc[tag]
        if not rows:
            continue
        Ls = np.median([x["Ls"].real for x in rows]) + 1j * np.median([x["Ls"].imag for x in rows])
        Lr = np.median([x["Lr"].real for x in rows]) + 1j * np.median([x["Lr"].imag for x in rows])
        Lr = 1.0 - Ls                                    # enforce the identity exactly
        rat = [abs(Ls * (k / 248.0) + Lr) for k in KPS]
        crit = []
        for L0 in (0.90, 0.95):
            grid = np.arange(248.0, 900.0, 0.5)
            g = np.array([abs(Ls * (k / 248.0) + Lr) for k in grid]) * L0
            j = np.flatnonzero(g >= 1.0)
            crit.append(grid[j[0]] if j.size else np.nan)
        pr("  %-5s | %5.2f@%+4.0f / %5.2f@%+4.0f | %s | %5.0f / %5.0f"
           % (tag, abs(Ls), np.degrees(np.angle(Ls)), abs(Lr), np.degrees(np.angle(Lr)),
              " ".join("%6.3f" % v for v in rat), crit[0], crit[1]))
    pr("   Pooled over all four routes' windows:")
    allr = [x for t in ROUTES for x in disc[t]]
    Ls = np.median([x["Ls"].real for x in allr]) + 1j * np.median([x["Ls"].imag for x in allr])
    Lr = 1.0 - Ls
    pr("     Ls %5.2f@%+4.0f  Lr %5.2f@%+4.0f (n %d windows) | %s" % (abs(Ls), np.degrees(np.angle(Ls)), abs(Lr), np.degrees(np.angle(Lr)), len(allr),
       " ".join("Kp%4d %6.3f" % (k, abs(Ls * (k / 248.0) + Lr)) for k in KPS)))
    pr("   THE EMPIRICAL BRACKET (this is the number to trust): the cycle is ABSENT at flat 248 on r35/r36/r37/r38 (F7 0.00 per 100 s,")
    pr("   4 routes, 168 s of high-angle time) and PRESENT at the stock LERP on r32/r33/r34 (F7 4.3-8.1), whose Kp at the ring's own")
    pr("   demand indices is 512-696.  So the turn-on lies in 248 < Kp <= 512 AT THE RING'S INDEX -- a factor of at most 2.06, untested inside.")

    # -------------------------------------------------------------------------------------------- M4
    pr("\nM4 -- WHAT A MEMORYLESS DEADBAND FIX HAS TO DELIVER.  Within-route split of strong-turn hands-light frames at idx 40-80 into")
    pr("   STALLED (rate/ref < 0.5) and MOVING, by the tap's own delivered torque -- i.e. how much more torque the stalled frames needed.")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        base = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx < 80) & (np.abs(r.tq_raw) < 1216) & (ref > 5)
        st = base & (w < 0.5 * ref)
        mv = base & (w >= 0.5 * ref)
        if base.sum() < 50:
            continue
        pr("  %s idx 40-80: STALLED n %4d |T| p50 %4.0f p90 %4.0f, v %4.1f, |ang| %3.0f | MOVING n %4d |T| p50 %4.0f p90 %4.0f, v %4.1f, |ang| %3.0f | stalled share %.3f"
           % (tag, st.sum(), np.median(np.abs(r.T_meas[st])) if st.sum() else np.nan, np.percentile(np.abs(r.T_meas[st]), 90) if st.sum() else np.nan,
              r.vego[st].mean() if st.sum() else np.nan, np.median(np.abs(r.ang[st])) if st.sum() else np.nan,
              mv.sum(), np.median(np.abs(r.T_meas[mv])), np.percentile(np.abs(r.T_meas[mv]), 90), r.vego[mv].mean(), np.median(np.abs(r.ang[mv])),
              st.sum() / base.sum()))
    pr("   And the Kp counterfactual on r35's OWN stalled frames: the chain's delivered torque at each candidate flat Kp,")
    pr("   open loop on the measured rate (so it answers 'what would a bigger Kp have delivered INTO that stall').")
    r = routes["r35"]
    R0 = SIM["r35"]
    ref = R0["ref_deg"][r.i100]
    w = np.abs(r.wire) / CPD
    st = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216) & (ref > 5) & (w < 0.5 * ref)
    cells = []
    for kp in (248, 300, 341, 400, 450, 512, 696):
        Rk = SV.sim_ki(r, *SV.V280R2, kpY=np.full(5, float(kp)), ki=0)
        cells.append("Kp%4d: |T| %4.0f" % (kp, np.median(np.abs(Rk["T"][r.i100][st]))))
    pr("   r35 stalled frames (n %d): measured tap |T| p50 %4.0f | %s" % (st.sum(), np.median(np.abs(r.T_meas[st])), "  ".join(cells)))
    pr("   V283's integrator on the SAME class (its own stalled+recovered frames, modelled |I| p50 3377-7004 counts of a 10240 limit)")
    pr("   raised the delivered torque enough that the stalled share fell 0.387 -> 0.085/0.089/0.177.")

    # -------------------------------------------------------------------------------------------- M5
    pr("\nM5 -- THE MAP LEVER SELF-CANCELS ON STATISTIC (b).  In a stall fb ~ 0, so E ~ 32*sp and the DC chain is")
    pr("   T ~ 0.1603 * E * Kp / 256 (lag DC 0.990 x SUM_MULT 254/256 x GAIN 5346/32768).  Raising the map by m multiplies BOTH the")
    pr("   delivered torque AND the reference by m, so it can break a static stall but cannot move rate/reference.  Raising Kp by m")
    pr("   multiplies the torque ONLY.  Verified numerically below on r35's stalled frames.")
    for m_ in (1.0, 1.25, 1.5, 2.0):
        Rm = SV.sim_ki(r, MAP_V280R2 * m_, SV.V280R2[1], kpY=KP_FLAT248, ki=0)
        Rk = SV.sim_ki(r, *SV.V280R2, kpY=KP_FLAT248 * m_, ki=0)
        pr("   x%.2f : MAP raise -> |T| %4.0f, reference %5.1f deg/s (ratio %.2f) || Kp raise -> |T| %4.0f, reference %5.1f deg/s (ratio %.2f)"
           % (m_, np.median(np.abs(Rm["T"][r.i100][st])), np.median(Rm["ref_deg"][r.i100][st]),
              np.median(np.abs(Rm["T"][r.i100][st])) / max(np.median(Rm["ref_deg"][r.i100][st]), 1e-9),
              np.median(np.abs(Rk["T"][r.i100][st])), np.median(Rk["ref_deg"][r.i100][st]),
              np.median(np.abs(Rk["T"][r.i100][st])) / max(np.median(Rk["ref_deg"][r.i100][st]), 1e-9)))
    pr("\n   The assist map now on the car (V280 rev 2, the 'line x6') vs stock slot 7, at MAP_X = %s:" % list(MAP_X.astype(int)))
    pr("     stock    %s" % list(MAP_STOCK.astype(int)))
    pr("     V280 r2  %s   (already non-stock; the low-index knots are 52/86/103/138 at idx 12/20/24/32)" % list(MAP_V280R2.astype(int)))
    pr("   Kp LERP knots at KP_X = %s:  stock %s  ->  V281 rev 3 / V282 / V283 flat %s"
       % (list(KP_X.astype(int)), list(KP_STOCK.astype(int)), list(KP_FLAT248.astype(int))))

    out = os.path.join(HERE, "_scratch", "stutter_v283_memoryless.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
