"""BUZZ SCORE from one drive's cache (build _features.npz first with a340_buzz_census2.py). usage: <cache dir> ...
BZ(t) = rms over 0.32 s (32 samples, centred) of the 0x14A wheel rate high-passed at 10 Hz (4th-order Butterworth, filtfilt), deg/s.
SCORE  = median BZ over samples with v > 8 m/s, |3 Hz-lp rate| < 2 deg/s (wheel still), |2 Hz-lp 0x18F torque| < 800, |angle| < 10 deg.
DUTY   = % of those samples with BZ > 4 deg/s.  Reported separately for ENGAGED (0xE4 request bit / latActive) and MANUAL."""
import sys, os
import numpy as np
for C in sys.argv[1:]:
    A = dict(np.load(os.path.join(C, "_features.npz")))
    base = (A["v"] > 8) & (np.abs(A["rlp"]) < 2) & (np.abs(A["tlp"]) < 800) & (np.abs(A["ang"]) < 10)
    out = []
    for lab, m in (("ENGAGED", base & A["eng"]), ("MANUAL", base & ~A["eng"])):
        if m.sum() < 100:
            out.append("%s n=%.0fs (too few)" % (lab, m.sum() / 100)); continue
        out.append("%s n=%4.0fs SCORE %5.2f deg/s DUTY %5.1f%%" % (lab, m.sum() / 100, np.median(A["bz"][m]), 100 * (A["bz"][m] > 4).mean()))
    print("%-24s | %s" % (os.path.basename(C.rstrip("/")), " | ".join(out)))
    # speed profile of duty, still wheel, |tq|<800, |a|<10
    prof = []
    for lo in range(2, 34, 4):
        for lab, e in (("E", A["eng"]), ("M", ~A["eng"])):
            m = (A["v"] >= lo) & (A["v"] < lo + 4) & (np.abs(A["rlp"]) < 2) & (np.abs(A["tlp"]) < 800) & (np.abs(A["ang"]) < 10) & e
            if m.sum() > 200: prof.append("%s%d-%d:%.0f%%(%ds)" % (lab, lo, lo + 4, 100 * (A["bz"][m] > 4).mean(), m.sum() // 100))
    print("     speed profile of DUTY: " + " ".join(prof))
