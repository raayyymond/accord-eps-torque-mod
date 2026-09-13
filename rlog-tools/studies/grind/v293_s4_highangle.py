# -*- coding: utf-8 -*-
"""v293_s4_highangle.py -- DELIVERABLE 4: the HIGH-ANGLE STALL under torque mode.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

THE CLAIM UNDER TEST.  The V278 rev 3 high-angle stutter was `E` swinging across P's linear window
because E = 32*sp - fb and fb carried a +-6000 rate ripple while the wheel sat stalled at 10-20 deg/s
against a 36-45 deg/s reference.  With fb == 0 there is NO feedback ripple in E at all, so the
mechanism cannot exist.  That is an arithmetic entailment; what is NOT entailed is what the delivered
torque then looks like on the SAME recorded episodes, and that is what this measures.

THREE POPULATIONS
  (a) r31, V278 rev 3 -- the only route where the STALL class was measured (7 of 10 F7 episodes).
      The A arm is V278 rev 3's OWN cells, so the disturbance inversion reproduces the recording; the
      B arms swap the electronics for V282 / V292 / V293.
      ⚠ DECLARED EXTRAPOLATION: r31's openpilot was commanding against the x2 map, so replaying the
      same recorded 0xE4 through V282's x6 map asks for ~3x the reference.  The stall MECHANISM
      transfers; the absolute torque level on the B arms does not.  Both are reported.
  (b) r39 / r35 -- V282 / V281 rev 3 loaded high-angle windows (the "at the reference" class that
      replaced the stall class).  Same build cells on both sides, no extrapolation.
  (c) r6d / r6e / r6f -- the V292 flight routes, if cached, as the freshest high-angle population.

READOUTS, all the record's own (ARC-GROUNDING section 8):
  * tap ripple/level = 6-8.5 Hz ripple of T divided by its level, in-episode, idx >= 68, wheel moving.
    Threshold 0.25, carried unchanged from V280 through V281, V291 and V292.
  * the P-rail duty -- the V278r3 mechanism's own signature ("P railed ~50 % of ticks").
  * F7-style 2-8 Hz rate envelope, fixed threshold 103 wire (the prereg's own, NOT moved).

Run:  python v293_s4_highangle.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np                                  # noqa: E402,F811
import creep20_loop_id as C20                       # noqa: E402
import design290b_candidates as D                   # noqa: E402
import grind_incident_r35 as GI                     # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG         # noqa: E402
import v292_replay_lib as R                         # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K, CPD = 100.0, 1000.0, 8.0
OUT = []
NAMED = [225, 215, 38, 117]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def load_route(tag, img):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    cells = GI.read_cells(img)
    g["cells"] = cells
    g["idx_live"], g["sgn_live"] = GI.demand_live(np.round(g["cmd"]), g["bar"], cells)
    g["sp_live"] = g["sgn_live"] * GI.lerp(cells["map_X"], cells["map_Y"], np.round(g["idx_live"]))
    g["f0"] = 20.0
    return g


def stall_windows(g, n=8, half=75, rate_lo=10.0, rate_hi=20.0, ref_lo=30.0, ref_hi=50.0,
                  ang_min=30.0, dens_min=0.30):
    """the STALL class, as HIGHANGLE-V278R3 defines it: the wheel is moving at 10-20 deg/s while the
    reference asks 30-50, |angle| >= 30 deg, lateral engaged."""
    rate = np.abs(g["wire"]) / CPD
    ref = np.abs(g["sp_live"]) / CPD
    ang = np.abs(g["ang"]) if "ang" in g else np.full(len(rate), np.nan)
    m = g["eng"] & (rate >= rate_lo) & (rate <= rate_hi) & (ref >= ref_lo) & (ref <= ref_hi)
    if np.isfinite(ang).any():
        m = m & (ang >= ang_min)
    out, used = [], []
    # rank candidate centres by how much of the window satisfies the gate
    dens = np.convolve(m.astype(float), np.ones(2 * half) / (2 * half), mode="same")
    order = np.argsort(-dens)
    for p0 in order:
        if dens[p0] < dens_min:
            break
        if p0 - half < 60 or p0 + half > len(g["t"]) - 20:
            continue
        if any(abs(p0 - q) < 2 * half for q in used):
            continue
        if not g["eng"][p0 - half:p0 + half].all():
            continue
        out.append((int(p0 - half), int(p0 + half), int(p0)))
        used.append(p0)
        if len(out) >= n:
            break
    return out


def ripple_level(T, lo=6.0, hi=8.5, fs=FS1K):
    """the record's tap statistic: band ripple amplitude / |level|."""
    amp = R.band_amp(T, lo, hi, fs)
    lev = float(np.median(np.abs(np.asarray(T, float))))
    return amp, lev, (amp / lev if lev > 1e-9 else np.nan)


def arm_run(g, a0, b0, cA, cB, pl, kd_b=128.0, fbB=None):
    """A arm = the route's OWN build (reproduces the recording).  B arm = the candidate."""
    WA = R.prep_window(g, a0, b0, cA)
    WB = R.prep_window(g, a0, b0, cB)
    elA = R.Elec(cA, fb=(cA["fb_a"], cA["fb_b"]), ef=False, two_floor=True, kd=float(cA["kd_Y"][0]))
    d, S_ol = R.invert_d(elA, R.PlantIIR(pl), WA, WA["wire1k"])
    Aarm = R.closed_run(R.Elec(cA, fb=(cA["fb_a"], cA["fb_b"]), ef=False, two_floor=True,
                               kd=float(cA["kd_Y"][0])), R.PlantIIR(pl), WA, d)
    recon = float(np.max(np.abs(Aarm["T"] - S_ol["T"])))
    fbb = fbB if fbB is not None else (cB["fb_a"], cB["fb_b"])
    Barm = R.closed_run(R.Elec(cB, fb=fbb, ef=(fbb == R.V292_FB), two_floor=True, kd=float(kd_b)),
                        R.PlantIIR(pl), WB, d)
    return Aarm, Barm, WA, WB, recon, d


def prail_duty(c, W, fb):
    """fraction of ticks at which |E*Kp/256| >= the P clamp -- the V278r3 mechanism's signature."""
    E = 32.0 * W["sp"] - fb
    return float(np.mean(np.abs(E * W["kp"] / 256.0) >= c["p_clamp"]))


# ================================================================================================
def main():
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in NAMED]

    c282 = L.read_cells(L.IMG282)
    c292 = L.read_cells(L.IMG292)
    c278 = L.read_cells(LG.FW + LG.IMAGES["V278r3"])
    c293 = L.torque_mode(c282, kp=119)
    c293b = L.torque_mode(c282, kp=160)

    pr("=" * 124)
    pr("V293 TORQUE MODE -- THE HIGH-ANGLE STALL          tmdesign 2026-09-13    ANALYSIS ONLY")
    pr("=" * 124)
    pr("%-10s %10s %8s %8s %10s %26s" % ("build", "0xC62E6", "Kp", "Kd", "gain", "map top / ref ceiling"))
    for nm, c in (("V278r3", c278), ("V282", c282), ("V292", c292), ("V293", c293)):
        pr("%-10s %10d %8d %8d %10d %16.0f / %6.1f deg/s" %
           (nm, c["fb_clamp"], c["kp_Y"][0], c["kd_Y"][0], c["gain"],
            max(c["map_Y"]), max(c["map_Y"]) / CPD))

    # --------------------------------------------------------------- (a) r31, the stall class
    pr("")
    pr("=" * 124)
    pr("(a) r31 -- V278 rev 3, the only route where the STALL class was measured")
    pr("=" * 124)
    g31 = load_route("r31", LG.FW + LG.IMAGES["V278r3"])
    w31 = stall_windows(g31)
    rate31 = np.abs(g31["wire"]) / CPD
    ref31 = np.abs(g31["sp_live"]) / CPD
    pr("  route %s: %.0f s, %.0f s engaged, %d stall windows found (rate 10-20 deg/s, ref 30-50, |angle| >= 30)"
       % ("r31", g31["t"][-1] - g31["t"][0], g31["eng"].sum() / FS, len(w31)))
    if not w31:
        pr("  !! no stall window survives the gate -- reporting the loaded high-angle class only")
    for (a0, b0, p0) in w31:
        pr("      t %7.1f s  rate p50 %5.1f deg/s  ref p50 %5.1f  idx p50 %5.0f  |bar| p50 %5.0f  v %4.1f m/s"
           % (g31["tr"][p0], np.median(rate31[a0:b0]), np.median(ref31[a0:b0]),
              np.median(g31["idx_live"][a0:b0]), np.median(np.abs(g31["bar"][a0:b0])),
              np.median(g31["vego"][a0:b0])))

    if w31:
        pr("")
        pr("  %-26s %9s %9s %9s %9s %9s %9s" %
           ("arm", "6-8.5 rip", "level", "rip/level", "P-rail", "T 2-8 Hz", "|T| mean"))
        pl = D.mkplant(byid[225])
        rows = {}
        for lab, cB, kdb, fbb in (("V278r3 (the recording)", c278, 128.0, None),
                                  ("V282", c282, 128.0, None),
                                  ("V292", c292, 0.0 if False else 128.0, R.V292_FB),
                                  ("V293 torque mode Kp119", c293, 0.0, None),
                                  ("V293 torque mode Kp160", c293b, 0.0, None)):
            acc = []
            for (a0, b0, p0) in w31:
                Aarm, Barm, WA, WB, recon, d = arm_run(g31, a0, b0, c278, cB, pl, kd_b=kdb, fbB=fbb)
                assert recon == 0.0, "the r31 A arm did not reproduce the recording"
                use = Aarm if lab.startswith("V278") else Barm
                W = WA if lab.startswith("V278") else WB
                el = R.Elec(cB, fb=(fbb or (cB["fb_a"], cB["fb_b"])), ef=False, two_floor=True, kd=kdb)
                fbser = np.array([el.fb_tick(-int(round(w))) for w in use["wire"]], float)
                amp, lev, rl = ripple_level(use["T"][500:])
                acc.append((amp, lev, rl, prail_duty(cB, W, fbser),
                            R.band_amp(use["T"][500:], 2.0, 8.0),
                            float(np.mean(np.abs(use["T"][500:])))))
            a = np.array(acc, float)
            rows[lab] = a
            pr("  %-26s %9.1f %9.1f %9.3f %9.3f %9.1f %9.0f" %
               (lab, np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]),
                np.median(a[:, 3]), np.median(a[:, 4]), np.median(a[:, 5])))
        pr("")
        pr("  rip/level threshold, carried unchanged since V280: <= 0.25.")
        pr("  P-rail is the V278 rev 3 mechanism's own signature: the record measured 'P railed ~50 %% of")
        pr("  ticks' on the stall episodes.  In torque mode E = 32*sp exactly, so P rails only where the")
        pr("  COMMAND rails -- there is no feedback ripple to cross the linear window with.")

    # --------------------------------------------------------------- (b) r39 / r35 loaded high angle
    pr("")
    pr("=" * 124)
    pr("(b) r39 (V282) and r35 (V281 rev 3) -- loaded high-angle windows, SAME cells both sides")
    pr("=" * 124)
    for tag in ("r39", "r35"):
        g = S2.route(tag, (18.0, 22.0))
        wins = S2.high_angle_windows(g, n=6)
        if not wins:
            pr("  %s: no loaded high-angle window survives the gate" % tag)
            continue
        rate = np.abs(g["wire"]) / CPD
        pr("")
        pr("  %s: %d windows" % (tag, len(wins)))
        for (a0, b0, p0) in wins:
            pr("      t %7.1f s  idx p50 %5.0f  rate p50 %5.1f deg/s  v %4.1f m/s  |bar| p50 %5.0f"
               % (g["tr"][p0], np.median(g["idx_live"][a0:b0]), np.median(rate[a0:b0]),
                  np.median(g["vego"][a0:b0]), np.median(np.abs(g["bar"][a0:b0]))))
        pr("")
        pr("  %-26s %9s %9s %9s %9s %9s %9s %9s" %
           ("arm", "6-8.5 rip", "level", "rip/level", "P-rail", "W 6-9", "T 18-22", "|T| mean"))
        for lab, cB, kdb, fbb in (("V282 (the recording)", c282, 128.0, None),
                                  ("V292", c292, 128.0, R.V292_FB),
                                  ("V293 torque mode Kp119", c293, 0.0, None),
                                  ("V293 torque mode Kp160", c293b, 0.0, None)):
            acc = []
            for f in named:
                pl = D.mkplant(f)
                for (a0, b0, p0) in wins:
                    Aarm, Barm, WA, WB, recon, d = arm_run(g, a0, b0, c282, cB, pl, kd_b=kdb, fbB=fbb)
                    assert recon == 0.0
                    use = Aarm if lab.startswith("V282") else Barm
                    W = WA if lab.startswith("V282") else WB
                    el = R.Elec(cB, fb=(fbb or (cB["fb_a"], cB["fb_b"])), ef=False, two_floor=True, kd=kdb)
                    fbser = np.array([el.fb_tick(-int(round(w))) for w in use["wire"]], float)
                    amp, lev, rl = ripple_level(use["T"][800:])
                    acc.append((amp, lev, rl, prail_duty(cB, W, fbser),
                                R.band_amp(use["wire"][800:], 6.0, 9.0),
                                R.band_amp(use["T"][800:], 18.0, 22.0),
                                float(np.mean(np.abs(use["T"][800:])))))
            a = np.array(acc, float)
            pr("  %-26s %9.1f %9.1f %9.3f %9.3f %9.1f %9.1f %9.0f" %
               (lab, np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]), np.median(a[:, 3]),
                np.median(a[:, 4]), np.median(a[:, 5]), np.median(a[:, 6])))

    # --------------------------------------------------------------- (c) the V292 flight routes
    pr("")
    pr("=" * 124)
    pr("(c) the V292 flight routes -- the freshest STALL-class population, and the one the operator")
    pr("    has just driven and called WORSE")
    pr("=" * 124)
    for tag in ("r6d_v292", "r6e_v292", "r6f_v292"):
        p = os.path.join(C20.CACHE, tag + ".npz")
        if not os.path.exists(p):
            pr("  %s: not cached" % tag)
            continue
        try:
            g = load_route(tag, L.IMG292)
        except Exception as e:                                   # noqa: BLE001
            pr("  %s: could not load (%s)" % (tag, e))
            continue
        rate = np.abs(g["wire"]) / CPD
        ref = np.abs(g["sp_live"]) / CPD
        m = g["eng"] & (g["idx_live"] >= 60) & (g["vego"] < 6.0)
        wins = stall_windows(g, n=6)
        pr("")
        pr("  %s: %.0f s, engaged %.0f s, loaded-high-angle frames %d, stall-class frames %d, windows %d"
           % (tag, g["t"][-1] - g["t"][0], g["eng"].sum() / FS, int(m.sum()),
              int((g["eng"] & (rate >= 10) & (rate <= 20) & (ref >= 30) & (ref <= 50)).sum()), len(wins)))
        if not wins:
            continue
        for (a0, b0, p0) in wins:
            pr("      t %7.1f s  rate p50 %5.1f deg/s  ref p50 %5.1f  idx p50 %5.0f  |bar| p50 %5.0f  v %4.1f"
               % (g["tr"][p0], np.median(rate[a0:b0]), np.median(ref[a0:b0]),
                  np.median(g["idx_live"][a0:b0]), np.median(np.abs(g["bar"][a0:b0])),
                  np.median(g["vego"][a0:b0])))
        pr("  %-26s %9s %9s %9s %9s %9s %9s" %
           ("arm", "6-8.5 rip", "level", "rip/level", "P-rail", "W 6-9", "|T| mean"))
        for lab, cB, kdb, fbb in (("V292 (the recording)", c292, 128.0, R.V292_FB),
                                  ("V282", c282, 128.0, None),
                                  ("V293 torque mode Kp119", c293, 0.0, None),
                                  ("V293 torque mode Kp160", c293b, 0.0, None)):
            acc = []
            for f in named:
                pl = D.mkplant(f)
                for (a0, b0, p0) in wins:
                    Aarm, Barm, WA, WB, recon, d = arm_run(g, a0, b0, c292, cB, pl, kd_b=kdb, fbB=fbb)
                    assert recon == 0.0
                    use = Aarm if lab.startswith("V292") else Barm
                    W = WA if lab.startswith("V292") else WB
                    el = R.Elec(cB, fb=(fbb or (cB["fb_a"], cB["fb_b"])), ef=False, two_floor=True, kd=kdb)
                    fbser = np.array([el.fb_tick(-int(round(w))) for w in use["wire"]], float)
                    amp, lev, rl = ripple_level(use["T"][500:])
                    acc.append((amp, lev, rl, prail_duty(cB, W, fbser),
                                R.band_amp(use["wire"][500:], 6.0, 9.0),
                                float(np.mean(np.abs(use["T"][500:])))))
            a = np.array(acc, float)
            pr("  %-26s %9.1f %9.1f %9.3f %9.3f %9.1f %9.0f" %
               (lab, np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 2]),
                np.median(a[:, 3]), np.median(a[:, 4]), np.median(a[:, 5])))

    open(os.path.join(SCR, "v293_s4_highangle.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s4_highangle.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
