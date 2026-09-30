"""ADV-D 6c: the one large outer PM change (light_b 17 m/s, relay off, -35.6 deg): which crossover, and is it a margin
loss or a new crossover near |L| = 1 with Ms improving?"""
import sys
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295")
c4 = H.Cells.v294()
fam = H.family()
ff = np.logspace(-2, np.log10(20.0), 4000)
for pl, v, relay in (("light_b", 17.0, False), ("light_b", 17.0, True), ("light_b", 26.9, True), ("b_lo", 5.0, True), ("nominal", 5.0, True)):
    p = fam[pl].at(v)
    for nm, c in (("V294", c4), ("V295", c5)):
        L = H.outer_frf(c, p, v, ff, relay=relay)
        m = H.margins(ff, L)
        mag = np.abs(L)
        print("%-8s %4.1f relay %-5s %s: crossovers %s PMs %s | GM %.2f | Ms %.3f @ %.2f Hz | max|L| between xovers %s" % (
            pl, v, relay, nm, [round(x, 3) for x in m["crossovers_hz"]], [round(x, 1) for x in m["PM_deg"]], m["GM_min"], m["Ms"],
            m["f_Ms"], "%.3f" % mag[(ff > min(m["crossovers_hz"] or [0])) & (ff < max(m["crossovers_hz"] or [0]))].max()
            if len(m["crossovers_hz"]) > 1 else "-"))
