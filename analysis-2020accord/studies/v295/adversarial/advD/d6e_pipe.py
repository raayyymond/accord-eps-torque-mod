"""ADV-D 6e: outer-loop margins at the longer round-trip pipes (42 / 62 ms; the V293 r75 read put the round trip at ~60 ms),
unchanged fork law r1, V295 vs V294, identified corners + the prior."""
import sys
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295")
c4 = H.Cells.v294()
fam = H.family()
ff = np.logspace(-2, np.log10(20.0), 2500)
worst = []
for pipe in (22, 42, 62):
    for pl in ("nominal", "b_lo", "J_hi", "light_b"):
        for v in (5.0, 8.0, 12.0, 17.0, 26.9):
            for relay in (True, False):
                p = fam[pl].at(v)
                m5 = H.margins(ff, H.outer_frf(c5, p, v, ff, relay=relay, pipe_ms=pipe))
                m4 = H.margins(ff, H.outer_frf(c4, p, v, ff, relay=relay, pipe_ms=pipe))
                worst.append((pipe, pl, v, relay, m5["GM_min"], m4["GM_min"], m5["Ms"], m4["Ms"], m5["PM_min"], m4["PM_min"]))
print("rows %d" % len(worst))
print("GM ratio V295/V294 min %.3f at %s" % min((w[4] / w[5], w[:4]) for w in worst))
print("Ms ratio V295/V294 max %.3f at %s" % max((w[6] / w[7], w[:4]) for w in worst))
print("PM change min %+.1f at %s" % min((w[8] - w[9], w[:4]) for w in worst))
for w in worst:
    if w[1] == "light_b" and w[2] in (17.0, 26.9) or (w[4] < 3 or w[5] < 3):
        print("  pipe %2d %-8s %4.1f relay %-5s GM %.2f / %.2f  Ms %.3f / %.3f  PM %.1f / %.1f" % w)
print("\nidentified family (nominal, b_lo, J_hi): worst PM change per pipe, and the Ms there")
for pipe in (22, 42, 62):
    W = [w for w in worst if w[0] == pipe and w[1] != "light_b"]
    w = min(W, key=lambda t: t[8] - t[9])
    print("  pipe %d: PM %+.1f deg at %s %.1f relay %s (PM %.1f / %.1f, Ms %.3f / %.3f, GM %.2f / %.2f)" % (pipe, w[8] - w[9], w[1], w[2], w[3],
          w[8], w[9], w[6], w[7], w[4], w[5]))
