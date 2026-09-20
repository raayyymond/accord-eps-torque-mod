# -*- coding: utf-8 -*-
"""S1 -- CENSUS of every dynamic term the fork already has on the Accord command/output path,
read from the source at HEAD (= 84766cdc5 = the commit rev 6.4 flew), with each term's EXACT
discrete response at the gap band (0.15-0.60 Hz) and the shake band (1.8-3.5 Hz).

Everything here is source-read + closed-form algebra.  No log is touched.  usage:
    python s1_census.py > out/S1-CENSUS.txt
"""
import numpy as np

import suplib as S

FQ = [0.2, 0.3, 0.6, 1.2, 1.8, 2.5, 3.5, 5.0]


def row(name, H, extra=""):
    mags = "  ".join(f"{abs(h):5.3f}/{np.degrees(np.angle(h)):+6.1f}" for h in H)
    print(f"  {name:38s} {mags}   {extra}")


def main():
    print(S._self_test())
    f = np.array(FQ)
    print("\n" + "=" * 140)
    print("1. WHAT IS ON THE PATH.  Every term, in execution order, from the fork source (HEAD = 84766cdc5,")
    print("   the commit rev 6.4 flew).  |H| / phase(deg) at each frequency.  dt = 0.01 s, exact discrete form.")
    print("=" * 140)
    print(f"  {'term':38s} " + "  ".join(f"{q:>6.2f} Hz  " for q in FQ))

    print("\n  -- SETPOINT / REFERENCE PATH (acts on the demand; a filter here cannot touch road-driven shake) --")
    # canceller's jerk LP: it is INSIDE an exact canceller, so its standalone response is not the stage's response
    row("jerk LP 4.0 Hz (HONDA_ACCORD_JERK_LP_HZ)", S.fof_H(f, 1 / (2 * np.pi * 4.0)),
        "latcontrol_torque.py:312, NOT toggle-reachable (const)")
    row("jerk LP 1.2 Hz (generic, every other rev)", S.fof_H(f, 1 / (2 * np.pi * 1.2)), ":90 LP_FILTER_CUTOFF_HZ")
    for rc in (0.06, 0.12, 0.5):
        row(f"ref filter x2, AccordRefFilter rc={rc}", S.fof_H(f, rc) ** 2,
            "toggle 0.0-0.5, :319-329" if rc == 0.12 else "")

    print("\n  -- ERROR / FEEDBACK PATH (inside the loop: attenuating here lowers |L|, not the FF command) --")
    for v in (15.0, 20.0, 28.0):
        f0 = S.mode_hz(v)
        for q in (1.0, 0.7, 0.5, 2.0, 4.0):
            row(f"error notch v={v:.0f} m/s f0={f0:.2f} Hz Q={q}", S.notch_H(f, f0, q),
                "AccordErrorNotchQ 0-4; CENTRE NOT toggle-reachable" if q == 1.0 else "")
        print()

    print("  -- INNER RATE LOOP (feedback on the MEASURED wheel rate; the only term that reaches road-driven shake) --")
    row("rate-meas LP rc=0.01 s (RATE_LOOP_RC)", S.fof_H(f, S.RATE_LOOP_RC), "tunes :286, NOT toggle-reachable")
    print(f"     gain g = AccordRateLoopGain * min(1, 12/v)  (tunes :2644).  toggle 0.0-0.003, default 0.0006,")
    print("     rev 6.4 flew 0.001.  Effective g by speed:")
    print("       " + "  ".join(f"v{v:>2.0f}: {S.rate_loop_gain(v, 0.001):.5f}" for v in (8, 12, 15, 18, 22, 28)))

    print("\n  -- DISTURBANCE OBSERVER (feedback on measured angle/rate + past command; AccordDobHz 0-3, flown 0.6) --")
    for hz in (0.6, 3.0):
        row(f"DOB two-pole LP at {hz} Hz", S.fof_H(f, 1 / (2 * np.pi * hz)) ** 2,
            "tunes :2735-2737, 60 ms internal delay on u, then a 0.3 clip")

    print("\n  -- OUTPUT PATH after the PID --")
    print("     NO output low-pass, NO rate limit and NO notch exist between output_torque and the CAN frame:")
    print("     latcontrol_torque.py:696-880 applies only per-car SCALES/CLIPS (none for Accord) and the")
    print("     optional AccordDither (flown 0.0).  The only output-side dynamics are the Honda safety rate")
    print("     limiter in the car interface and the firmware's own 5.05 Hz output-lag cell.")

    print("\n" + "=" * 140)
    print("2. THE ERROR NOTCH'S CENTRE IS ALREADY IN THE SHAKE BAND AT METRIC SPEEDS.")
    print("   centre = sqrt(k(v)/J)/2pi with k = HONDA_ACCORD_HOLD_K_V(v), J = 8e-5 (tunes :2630).")
    print("=" * 140)
    print(f"  {'v m/s':>6s} " + "".join(f"{v:>7.0f}" for v in (2, 4, 8, 12, 15, 18, 20, 23, 28)))
    print(f"  {'f0 Hz':>6s} " + "".join(f"{S.mode_hz(v):7.2f}" for v in (2, 4, 8, 12, 15, 18, 20, 23, 28)))
    print("  The brief's '1.28 Hz' is the value at 8 m/s.  The goal metric is scored at >= 15 m/s, where the")
    print("  centre is 1.73-2.25 Hz -- i.e. the notch ALREADY sits at the bottom edge of the 1.8-3.5 Hz shake band.")

    print("\n" + "=" * 140)
    print("3. WHAT Q BUYS AND WHAT IT COSTS.  Power-mean |H| over each band (equal weight per bin, 0.01 Hz grid),")
    print("   and the phase the notch adds at 0.30 Hz -- the frequency a raised-gain crossover would sit at.")
    print("=" * 140)
    grid_g = np.arange(S.GAP[0], S.GAP[1] + 1e-9, 0.005)
    grid_s = np.arange(S.SHAKE[0], S.SHAKE[1] + 1e-9, 0.01)
    print(f"  {'v':>4s} {'f0':>5s} {'Q':>5s} {'|H| 0.15-0.60':>14s} {'|H| 1.8-3.5':>12s} {'arg H @0.30':>12s} "
          f"{'arg H @0.20':>12s} {'|H| @2.5':>9s}")
    for v in (15.0, 20.0, 28.0):
        f0 = S.mode_hz(v)
        for q in (4.0, 2.0, 1.0, 0.7, 0.5, 0.3):
            hg = np.sqrt(np.mean(np.abs(S.notch_H(grid_g, f0, q)) ** 2))
            hs = np.sqrt(np.mean(np.abs(S.notch_H(grid_s, f0, q)) ** 2))
            p30 = np.degrees(np.angle(S.notch_H(0.30, f0, q)))
            p20 = np.degrees(np.angle(S.notch_H(0.20, f0, q)))
            h25 = abs(S.notch_H(2.5, f0, q))
            print(f"  {v:4.0f} {f0:5.2f} {q:5.2f} {hg:14.3f} {hs:12.3f} {p30:12.1f} {p20:12.1f} {h25:9.3f}")
        print()

    print("=" * 140)
    print("4. CANDIDATE ADDED TERMS (each IS a fork code change).  Same two bands, plus the phase at 0.30 Hz.")
    print("=" * 140)
    cands = {}
    for fc in (2.0, 3.0, 4.0, 6.0):
        cands[f"1st-order LP fc={fc} Hz"] = S.fof_H(np.arange(0.05, 6.0, 0.005), 1 / (2 * np.pi * fc))
    for f0, q in ((2.5, 1.0), (2.5, 0.7), (2.5, 1.5), (2.2, 1.0), (2.8, 1.0)):
        cands[f"notch f0={f0} Q={q} (on the COMMAND)"] = S.notch_H(np.arange(0.05, 6.0, 0.005), f0, q)
    grid = np.arange(0.05, 6.0, 0.005)
    ig = (grid >= S.GAP[0]) & (grid <= S.GAP[1])
    ish = (grid >= S.SHAKE[0]) & (grid <= S.SHAKE[1])
    j30 = int(np.argmin(np.abs(grid - 0.30)))
    j20 = int(np.argmin(np.abs(grid - 0.20)))
    j10 = int(np.argmin(np.abs(grid - 1.00)))
    print(f"  {'candidate':34s} {'|H| gap':>8s} {'|H| shake':>10s} {'arg@0.20':>9s} {'arg@0.30':>9s} "
          f"{'arg@1.0':>8s} {'|H|@1.0':>8s}")
    for k, H in cands.items():
        print(f"  {k:34s} {np.sqrt(np.mean(np.abs(H[ig])**2)):8.3f} {np.sqrt(np.mean(np.abs(H[ish])**2)):10.3f} "
              f"{np.degrees(np.angle(H[j20])):9.1f} {np.degrees(np.angle(H[j30])):9.1f} "
              f"{np.degrees(np.angle(H[j10])):8.1f} {abs(H[j10]):8.3f}")
    print("\n  A 2nd-order lead-lag / phase-compensated roll-off is not tabled here: every one of the above is")
    print("  minimum-phase, so its phase at 0.3 Hz is set by its magnitude slope below 2 Hz and cannot be")
    print("  cheated by adding order -- only by moving the corner up or narrowing the notch (higher Q).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
