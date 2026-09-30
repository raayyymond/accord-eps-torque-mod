"""ADV-D 7c: the closed-loop LOW-frequency modes (wheel/spring mode, lane-vs-J pair), V294 vs V295, identified family +
the prior -- the inertia cost below the 2 Hz pole, as damping ratios."""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295")
c4 = H.Cells.v294()
fam = H.family()
for pl in ("nominal", "b_lo", "J_hi", "J_hi2", "light_b", "tau9"):
    for v in (3.1, 8.0, 12.0, 17.0, 26.9):
        p = fam[pl].at(v)
        m4, _ = H.closed_loop_modes(p, c4); m5, _ = H.closed_loop_modes(p, c5)
        f4 = [(round(f, 2), round(z, 3)) for f, z in m4 if 0.1 < f < 8]
        f5 = [(round(f, 2), round(z, 3)) for f, z in m5 if 0.1 < f < 8]
        print("%-8s %5.1f  V294 %-40s V295 %s" % (pl, v, f4, f5))
