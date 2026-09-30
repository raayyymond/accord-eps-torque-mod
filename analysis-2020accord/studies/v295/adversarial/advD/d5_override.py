"""ADV-D step 5: what a driver meets when he OVERRIDES the lane -- synthetic swerves through the golden-exact lanes
(harness Lane == golden model, H1a) of V294, V295 (cells from the IMAGE) and V282 (the flown rate servo), wheel held to a
prescribed motion (the worst case: the lane cannot move the wheel), driver torque sets the taper.
  trim = T(lane) - T(same lane with the fb operand muted, C = 0) = the part of the lane torque that reacts to wheel motion.
Raised-cosine rate pulse: omega(t) = (A/Tm)(1 - cos(2 pi t/Tm)), peak 2A/Tm, peak accel 2 pi A/Tm^2.
Sign: the kit march convention (x = +8*omega for this sweep; the answer is |.|, and the sign of the trim relative to the
motion is reported: 'opp' = the fraction of |trim| > 20 ticks where the trim opposes the wheel acceleration)."""
import sys
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295", "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")
c4 = H.Cells.v294()
c2 = H.Cells.v282()
builds = [("V294", c4), ("V295", c5), ("V282", c2)]
PROF = [("evasive 30 deg / 0.25 s", 30.0, 0.25), ("swerve 90 deg / 0.30 s", 90.0, 0.30), ("parking 180 deg / 0.60 s", 180.0, 0.60),
        ("slow 45 deg / 1.0 s", 45.0, 1.0)]
print("%-26s %-9s %-7s | %s" % ("manoeuvre", "bar(wire)", "demand", "  ".join("%-34s" % b for b, _ in builds)))
print("%-26s %-9s %-7s | %s" % ("", "", "", "  ".join("%-34s" % "trim pk / T pk / impulse T*s / opp" for _ in builds)))
for pn, A, Tm in PROF:
    n = int((Tm + 0.5) * 1000)
    t = np.arange(n) / 1000.0
    om = np.where(t < Tm, (A / Tm) * (1 - np.cos(2 * np.pi * t / Tm)), 0.0)
    al = np.gradient(om) * 1000.0
    x = np.round(8 * om).astype(np.int64)
    for bar_w in (600.0, 2000.0, 3600.0):
        for wire in (0.0, 1000.0):
            row = []
            for bn, c in builds:
                L = H.Lane([c, c.replace(fb_clamp=0, name="null")])
                idx, sp, m = L.demand(np.array([wire, wire]), bar=np.array([bar_w / 1.024] * 2))
                # warm up at rest on the held demand
                for _ in range(1500):
                    L.tick(np.zeros(2, np.int64), sp, idx, m)
                T = np.zeros((2, n))
                for i in range(n):
                    tt, _ = L.tick(np.array([x[i], x[i]]), sp, idx, m)
                    T[:, i] = tt
                trim = T[0] - T[1]
                big = np.abs(trim) > 20
                # the lane's T (tap sign) opposes the motion when it has the sign of +x's acceleration in this convention?
                # determine empirically on the dominant lobe: correlation of trim with -al (opposing accel) vs +al
                opp = float(np.mean(np.sign(trim[big]) == np.sign(-al[big]))) if big.any() else float("nan")
                row.append("%5.0f / %5.0f / %6.1f / %.2f   " % (np.abs(trim).max(), np.abs(T[0]).max(), np.abs(trim).sum() / 1000.0, opp))
            print("%-26s %-9.0f %-7.0f | %s" % (pn, bar_w, wire, "  ".join("%-34s" % r for r in row)))
print("\n(peak rate, peak accel) per manoeuvre:", [(p, 2 * A / Tm, 2 * np.pi * A / Tm ** 2) for p, A, Tm in PROF])
