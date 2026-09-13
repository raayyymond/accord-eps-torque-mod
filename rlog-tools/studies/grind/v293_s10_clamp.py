# -*- coding: utf-8 -*-
"""v293_s10_clamp.py -- IS THERE A BETTER DOSE?  0xC62E6 is a CLAMP, not a gain, and a small NONZERO
value is a third thing entirely: a COULOMB (relay) damper on wheel rate.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

THE ARITHMETIC, and why nobody has looked at this.
    r26 = clip(two-sample sum, +-0xC62E6) ,  two-sample sum = 30.891 * 8 * rate_deg_s = 247.13*rate
    E   = 32*sp - r26
At V282's 46080 the clamp binds only above 186 deg/s, so the feedback is LINEAR everywhere the car
drives.  At 0 the feedback vanishes -- torque mode.  IN BETWEEN, the clamp binds at |rate| > C/247.13,
so for any rate above that threshold the feedback contributes a CONSTANT -C*sign(rate) to E.  That is
not "less feedback": it is Coulomb damping, a relay in the rate's sign, of magnitude
    dT = (C * Kp >> 8) * gain >> 15  torque counts, opposing wheel motion.
It is PURE DAMPING in phase (in phase with velocity) and its describing-function gain RISES as the
signal gets smaller (4M/(pi*A)), which is the opposite of every linear lever the record has scored.

🛑 AND IT IS THE V276 SHAPE.  V276's failure was a relay in the sign of the ERROR (destabilising).
This is a relay in the sign of the RATE (stabilising).  Same class of nonlinearity, opposite sign, and
a relay closed around a lightly damped mode is the textbook limit-cycle generator either way.  So this
is scored on the byte-exact closed loop, on the operator's own recorded episodes, not on a phasor.

Run: python v293_s10_clamp.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_echo_sizing as ES                      # noqa: E402
import design290b_candidates as D                   # noqa: E402
import v292_replay_lib as R                         # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_s2_replay as S3                         # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
NAMED = [225, 215, 38, 117]
CLAMPS = [0, 256, 512, 1024, 2048, 4096, 8192, 15360, 46080]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in NAMED]
    c282 = L.read_cells(L.IMG282)

    pr("=" * 122)
    pr("0xC62E6 AS A CONTINUOUS LEVER -- torque mode with a COULOMB damper      tmdesign 2026-09-13")
    pr("=" * 122)
    dcfb = 2.0 * c282["fb_b"] / (1024.0 - c282["fb_a"])
    pr("feedback DC = 2*%d/(1024-%d) = %.4f counts per raw rate count = %.2f counts of E per deg/s"
       % (c282["fb_b"], c282["fb_a"], dcfb, dcfb * 8.0))
    pr("")
    pr("  %8s %14s %16s %16s %14s" %
       ("0xC62E6", "binds above", "Coulomb dT", "as a fraction", "as a fraction"))
    pr("  %8s %14s %16s %16s %14s" %
       ("", "deg/s", "counts (Kp119)", "of peak 2460", "of T at idx 24"))
    for C in CLAMPS:
        thr = C / (dcfb * 8.0)
        dT = (C * 119 // 256) * c282["gain"] // 32768
        pr("  %8d %14.2f %16d %16.3f %14.3f" % (C, thr, dT, dT / 2460.0, dT / 245.0))
    pr("")
    pr("  The 18-22 Hz ring on the wheel is ~16 raw counts = 2.0 deg/s.  A clamp at 512 binds above")
    pr("  %.2f deg/s, i.e. it is LINEAR through the ring and relay-like only on the slower motion."
       % (512 / (dcfb * 8.0)))
    pr("  A clamp at 256 binds above %.2f deg/s -- relay-like AT the ring."
       % (256 / (dcfb * 8.0)))

    g = S2.route("r39", (18.0, 22.0))
    wins = ES.loud_windows(g)
    pr("")
    pr("-" * 122)
    pr("THE SWEEP, byte-exact on r39's 10 loudest engaged windows, 4 named fits, Kp 119, Kd 0, r24 5244")
    pr("-" * 122)
    pr("  %8s %9s %9s %9s %9s %9s %9s %9s" %
       ("0xC62E6", "T 18-22", "W 18-22", "W 9-18", "W 5-9", "T 5-9", "auth oob", "auth |T|"))
    rows = {}
    for C in CLAMPS:
        cB = L.torque_mode(c282, kp=119)
        cB["fb_clamp"] = int(C)
        acc = {}
        for f in named:
            pl = D.mkplant(f)
            for (a0, b0, p0) in wins:
                rep = S3.replay_tm(g, a0, b0, c282, cB, pl, arm=5244)
                assert rep["recon"] == 0.0
                m = S3.measure(rep["A"], rep["B"], g["f0"])
                for k in ("T_ring", "W_ring", "W_shoulder", "W_low", "T_low", "auth_oob", "auth_absmean"):
                    acc.setdefault(k, []).append(m[k][2])
        rows[C] = {k: float(np.median(v)) for k, v in acc.items()}
        pr("  %8d %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f %9.3f" %
           (C, rows[C]["T_ring"], rows[C]["W_ring"], rows[C]["W_shoulder"], rows[C]["W_low"],
            rows[C]["T_low"], rows[C]["auth_oob"], rows[C]["auth_absmean"]))
    pr("")
    pr("  Every column is a ratio to V282 as flown (0xC62E6 = 46080, Kp 248, Kd 128) on the same")
    pr("  window, same command, same residual disturbance.  The bottom row is V293 with V282's own")
    pr("  clamp and is therefore a pure Kp/Kd contrast -- the CONTROL on the sweep.")

    # a limit-cycle check: does the relay ring?
    pr("")
    pr("-" * 122)
    pr("THE LIMIT-CYCLE CHECK -- does the relay self-excite?  (the V276 question, asked of THIS relay)")
    pr("-" * 122)
    pr("A relay closed around a lightly damped mode limit-cycles when the describing-function locus")
    pr("crosses -1/N.  Rather than a phasor, this measures the byte-exact closed loop's OWN 18-22 Hz")
    pr("and 5-9 Hz content with the command FROZEN at its window median -- no external excitation in")
    pr("those bands beyond the residual disturbance.  A clamp that self-excites shows a band amplitude")
    pr("that RISES above the disturbance-driven baseline (0xC62E6 = 0, no relay at all).")
    pr("")
    pr("  %8s %12s %12s %12s" % ("0xC62E6", "W 18-22", "W 5-9", "vs clamp 0"))
    base = None
    for C in (0, 256, 512, 1024, 2048, 4096):
        cB = L.torque_mode(c282, kp=119)
        cB["fb_clamp"] = int(C)
        acc = []
        pl = D.mkplant(byid[225])
        for (a0, b0, p0) in wins:
            W2 = R.prep_window(g, a0, b0, c282)
            W9 = R.prep_window(g, a0, b0, cB)
            W9 = dict(W9)
            W9["sp"] = np.full_like(W9["sp"], float(np.median(W9["sp"])))
            d, _ = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, W2["wire1k"])
            B = R.closed_run(R.Elec(cB, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0),
                             R.PlantIIR(pl), W9, d)
            acc.append((R.band_amp(B["wire"][800:], 18.0, 22.0), R.band_amp(B["wire"][800:], 5.0, 9.0)))
        a = np.array(acc, float)
        v = (float(np.median(a[:, 0])), float(np.median(a[:, 1])))
        if base is None:
            base = v
        pr("  %8d %12.2f %12.2f %12s" %
           (C, v[0], v[1], "x%.3f / x%.3f" % (v[0] / base[0], v[1] / base[1])))
    pr("")
    pr("  A value above x1.0 in either column is the relay ADDING motion that was not there with the")
    pr("  loop fully open -- the self-excitation signature.  Below x1.0 it is damping.")

    open(os.path.join(SCR, "v293_s10_clamp.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s10_clamp.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
