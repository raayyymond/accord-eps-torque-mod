# -*- coding: utf-8 -*-
"""v292_replay_s1.py -- STAGE 1: the POSITIVE CONTROLS, before any V292 number is quoted.

  1a  the record's own mirror on r39's 10 loudest engaged 3 s windows -> must reproduce
      COMB-VS-ECHO section A1 / openloop_drive: T_total 57.21, CMD leg 11.56.
  1b  the mirror against the RECORDED 427 torque tap, per window, in 18-22 Hz.
  1c  MY byte-exact electronics against the record's mirror, open loop, same windows.
  1d  the single-floor / two-floor feedback-lag difference, measured.
Run: python v292_replay_s1.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np                                  # noqa: E402
from scipy import signal                            # noqa: E402
import burst_onset_triggers as B                    # noqa: E402
import burst_echo_sizing as ES                      # noqa: E402
import grind_incident_r35 as GI                     # noqa: E402
import creep20_loop_id as C20                       # noqa: E402
import v292_replay_lib as R                         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K, FST = 100.0, 1000.0, 50.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def bandstop(x, lo, hi, fs=FS):
    return signal.sosfiltfilt(signal.butter(4, [lo, hi], btype="bandstop", fs=fs, output="sos"),
                              np.asarray(x, float))


def main():
    lo, hi = 18.0, 22.0
    g = B.load_route("r39")
    c = g["cells"]
    g["f0"] = B.ring_f0(g, lo, hi)
    g["env"] = B.demod_env(g["bar"], g["f0"], FS)
    on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
    g["on"], g["pk"], g["amp"] = on, pk, amp
    wins = ES.loud_windows(g)
    pr("=" * 122)
    pr("STAGE 1 -- POSITIVE CONTROLS.  route r39 (V282), f0 %.3f Hz, %d loudest 3 s engaged windows" % (g["f0"], len(wins)))
    pr("=" * 122)

    # ---------------------------------------------------------------- 1a
    pr("")
    pr("1a  THE RECORD'S OWN MIRROR -- must reproduce COMB-VS-ECHO section A1 (57.21 / 11.56)")
    pr("-" * 122)
    cmd_flat = bandstop(g["cmd"], lo, hi)
    base, cmdleg, meas, fbleg = [], [], [], []
    wire_flat = bandstop(g["wire"].astype(float), lo, hi)
    for a0, b0, p0 in wins:
        S0 = GI.simulate(g, a0, b0, c)
        base.append(ES.band_amp(S0["T"], lo, hi, FS1K))
        g2 = dict(g); g2["cmd"] = cmd_flat
        cmdleg.append(ES.band_amp(GI.simulate(g2, a0, b0, c)["T"] - S0["T"], lo, hi, FS1K))
        g3 = dict(g); g3["wire"] = wire_flat
        fbleg.append(ES.band_amp(GI.simulate(g3, a0, b0, c)["T"] - S0["T"], lo, hi, FS1K))
    pr("    T_total  median %8.2f   (record 57.21)   %s" % (np.median(base), "MATCH" if abs(np.median(base) - 57.21) < 0.02 else "*** MISMATCH ***"))
    pr("    CMD leg  median %8.2f   (record 11.56)   %s" % (np.median(cmdleg), "MATCH" if abs(np.median(cmdleg) - 11.56) < 0.02 else "*** MISMATCH ***"))
    pr("    FB  leg  median %8.2f   (record 50.27)   %s" % (np.median(fbleg), "MATCH" if abs(np.median(fbleg) - 50.27) < 0.02 else "*** MISMATCH ***"))

    # ---------------------------------------------------------------- 1b
    pr("")
    pr("1b  THE MIRROR AGAINST THE RECORDED 427 TORQUE TAP, per window, 18-22 Hz")
    pr("-" * 122)
    pr("    the tap is the 0x1AB stream at its own 50 Hz instants; the mirror is sampled onto them.")
    pr("    %4s %8s %9s %9s %8s %8s %8s %7s" % ("win", "t (s)", "amp meas", "amp sim", "sim/meas", "corr_b", "phase", "coh"))
    rats = []
    for k, (a0, b0, p0) in enumerate(wins):
        o = GI.eval_window(g, a0, b0, c, lo=lo, hi=hi)
        rats.append(o["amp_sim"] / o["amp_meas"])
        pr("    %4d %8.1f %9.2f %9.2f %8.3f %8.2f %+8.0f %7.2f" %
           (k, g["t"][p0] - g["t"][0], o["amp_meas"], o["amp_sim"], rats[-1], o["corr_band"], o["phase"], o["coh"]))
    rats = np.array(rats)
    pr("    median sim/meas %.3f   (|error| median %.1f %%, range %.1f-%.1f %%)" %
       (np.median(rats), 100 * np.median(np.abs(rats - 1)), 100 * np.abs(rats - 1).min(), 100 * np.abs(rats - 1).max()))

    # ---------------------------------------------------------------- 1c / 1d
    pr("")
    pr("1c/1d  MY BYTE-EXACT ELECTRONICS vs THE RECORD'S MIRROR, open loop, same windows")
    pr("-" * 122)
    pr("    'record'    = grind_incident_r35.simulate            (float fb lag, ONE floor of the sum)")
    pr("    'mine 1flr' = my march with the record's single floor (isolates float-vs-integer)")
    pr("    'mine 2flr' = my march with the listing's TWO floors  (byte-exact; what V292's cave repairs)")
    pr("    %4s %10s %10s %10s %9s %9s" % ("win", "record", "mine 1flr", "mine 2flr", "1flr/rec", "2flr/rec"))
    A, Bm, Cm = [], [], []
    for k, (a0, b0, p0) in enumerate(wins):
        S0 = GI.simulate(g, a0, b0, c)
        W = R.prep_window(g, a0, b0, c)
        x = -np.round(W["wire1k"]).astype(np.int64)
        e1 = R.Elec(c, fb=R.V282_FB, ef=False, two_floor=False)
        e2 = R.Elec(c, fb=R.V282_FB, ef=False, two_floor=True)
        S1 = e1.run(x, W["sp"], W["kp"], W["m"], W["eng"])
        S2 = e2.run(x, W["sp"], W["kp"], W["m"], W["eng"])
        a_ = ES.band_amp(S0["T"], lo, hi, FS1K); b_ = ES.band_amp(S1["T"], lo, hi, FS1K); c_ = ES.band_amp(S2["T"], lo, hi, FS1K)
        A.append(a_); Bm.append(b_); Cm.append(c_)
        pr("    %4d %10.2f %10.2f %10.2f %9.4f %9.4f" % (k, a_, b_, c_, b_ / a_, c_ / a_))
    A, Bm, Cm = map(np.array, (A, Bm, Cm))
    pr("    median   %10.2f %10.2f %10.2f %9.4f %9.4f" % (np.median(A), np.median(Bm), np.median(Cm),
                                                          np.median(Bm / A), np.median(Cm / A)))
    pr("")
    pr("    DC offset of the two forms at a steady x (the reason the two-floor form matters):")
    for xv in (1, 3, 16, -16):
        r = []
        for tf in (False, True):
            e = R.Elec(c, fb=R.V282_FB, ef=False, two_floor=tf)
            for _ in range(5000):
                e.fb_tick(xv)
            r.append(np.mean([e.fb_tick(xv) for _ in range(5000)]))
        pr("      x %+4d : one-floor %10.3f   two-floor %10.3f   linear %10.3f" %
           (xv, r[0], r[1], 2 * 1560 * xv / (1024.0 - 923)))

    with open(os.path.join(B.SCR, "v292_replay_s1.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/v292_replay_s1.txt")


if __name__ == "__main__":
    main()
