"""SIGNATURE TABLE and the gain/deficit split.

Part 1: each mechanism's |H| signature (frequency, speed, amplitude) stated BEFORE looking, then the
measured surface's verdict on it.  Part 2: the arithmetic that splits the measured gap into a
multiplicative GAIN difference and V282's own constant-magnitude DEFICIT, from the fitted shapes.
ALGEBRA on measured cells only.
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
from surf import OUT

SIG = [
    ("(a) LOOP DELAY 55-75 ms",
     "freq: NONE in magnitude (|e^-jwD| = 1 exactly); phase grows linearly with f.  "
     "speed: flat (measured).  amplitude: none (linear term).",
     "ABSENT as a magnitude mechanism BY CONSTRUCTION, and the leg is COMMON to both builds: the "
     "controls->bus lag measures 10 ms on 7/8 routes, V282 and V293 alike (verify.py A).  It can own "
     "0.000 of any |H| gap and 0.000 of any lag DIFFERENCE.  What it does own is the absolute phase "
     "floor and the ceiling on curing the 1-2 Hz amplification with loop damping."),
    ("(b) ACTUATOR SATURATION",
     "freq: broadband, strongest where the demand is largest.  speed: only below 8 m/s (measured).  "
     "amplitude: |H| DROOPS at large amplitude -- the only one of the four with that shape.",
     "SIGNATURE ABSENT WHERE IT SHOULD BE STRONGEST, and the sign of the between-build contrast is "
     "REVERSED: the V282 REFERENCE rails 2.264 % of its laterally-engaged hands-off time below 8 m/s "
     "(16.63 s / 734.6 s, 159 episodes, longest 1.705 s) against torque mode's 0.10-0.16 % (0.35 s / "
     "213 s, 6 episodes, longest 0.081 s).  Above 8 m/s NEITHER build rails at all (0.00 s in 4,500 s).  "
     "No admissible cell shows droop-with-amplitude in torque mode; the only groups that do are V282 and "
     "V282old at 22-40 m/s, where the duty is exactly zero, so that droop is not saturation either."),
    ("(c) HOLD-FF ADDITIVE DEFICIT +0.0231 torque",
     "freq: DC to the integrator's corner, so <~0.3 Hz.  speed: 2-8 m/s only.  amplitude: a CONSTANT "
     "term, so its |H| effect falls as 1/A -- and it is a DEFICIT, so |H| should RISE with amplitude.",
     "NOT TESTABLE on this route set in its own regime, and I will not pretend otherwise: the 20.48 s "
     "instrument yields 3 blocks = 61 s below 8 m/s across three DIFFERENT torque routes (per-route "
     "H_tot 0.43 / 0.86 / 1.55, bootstrap CI [0.43, 1.55] at 0.25-0.50 Hz).  Budget: 0.0231 is 24 % of "
     "the measured median |command| at 0-8 m/s on the torque routes, so it is not negligible if it is "
     "there.  In the one low-speed band that IS measurable (0.50-1.00 Hz) the torque-V282 gap is "
     "+0.48 -- the WRONG SIGN for a deficit, and above the integrator's corner anyway."),
    ("(d) DISTURBANCE OBSERVER",
     "freq: its own 2-pole 0.6 Hz corner, so full authority below 0.6 Hz falling to 0.05 by 2.5 Hz; the "
     "claim on record is that it FEEDS 1.5-3.5 Hz.  speed: much stronger at >=15 m/s than below 8 "
     "(b_eq -2.5..-3.4e-4 vs -0.2..-1.4e-4).  amplitude: none stated.",
     "THE ON/OFF CONTRAST DOES NOT TRACK THE GAP AND CHANGES SIGN.  On the goal metric it closes the "
     "whole gap in one cell (0.10-0.25 Hz, 8-15 m/s: share +1.01) and 5 % in the next (0.25-0.50 Hz, "
     "8-15: +0.05), then goes NEGATIVE at 0.50-1.00 Hz in every speed bin (-0.36 to -0.75), i.e. the "
     "observer-OFF drive is FARTHER from V282 there.  In 1.5-3.5 Hz unexplained output power the OFF "
     "route is the HIGHEST of all torque routes below 8 m/s (x6.69 V282) and above T64 at every speed.  "
     "That is one route carrying SIX simultaneous parameter changes, so it is an UPPER BOUND on the "
     "observer and the bound does not have a consistent sign."),
]


def main():
    print("=" * 150)
    print("1  SIGNATURE TABLE -- what each mechanism WOULD look like on this surface, and what the surface says.")
    print("=" * 150)
    for name, sig, verdict in SIG:
        print(f"\n{name}")
        print(f"   WOULD LOOK LIKE: {sig}")
        print(f"   MEASURED:        {verdict}")

    print("\n" + "=" * 150)
    print("2  SPLITTING THE GAP: a multiplicative GAIN difference vs V282's own constant-magnitude DEFICIT.")
    print("   From the fitted H = a + c/A on the ADMISSIBLE amplitude bins (out/shape.json).  a is the")
    print("   large-amplitude asymptote (the gain); -c/A is the fixed-magnitude part, in m/s^2 of lateral accel.")
    print("=" * 150)
    S = json.load(open(OUT / "shape.json"))
    print(f"{'band':11s} {'v':7s} {'grp':8s} {'a (gain)':>9s} {'c':>9s} {'R2':>5s} "
          f"{'|c|/A at A small':>17s} {'A small':>8s} {'|c|/A at A large':>17s} {'A large':>8s}")
    for r in S:
        A = np.array(r["A"]); H = np.array(r["H"])
        if r["r2c"] < 0.5:
            continue
        c = r["c"]
        a = float(np.mean(H - c / A))
        lo, hi = A.min(), A.max()
        print(f"{r['band']:11s} {['0-8','8-15','15-22','22-40'][r['si']]:7s} {r['g']:8s} {a:9.3f} {c:9.5f} "
              f"{r['r2c']:5.2f} {abs(c)/lo:17.3f} {lo:8.4f} {abs(c)/hi:17.3f} {hi:8.4f}")
    print("\n   Reading: where V282 and a torque group are both fitted in the same band x speed, the GAIN")
    print("   difference (a_T - a_V282) is amplitude-independent and is the part a gain change could address;")
    print("   the |c|/A column is the part that is a FIXED-MAGNITUDE lateral-accel error, biggest on the")
    print("   smallest corrections, and it belongs to WHICHEVER build carries the negative c.")


if __name__ == "__main__":
    main()
