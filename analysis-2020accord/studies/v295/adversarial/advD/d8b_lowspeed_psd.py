"""ADV-D 8b: is the on-centre 0.2-1 Hz wheel-rate rise at 0-5 m/s on light_b (x1.50 under dist full) a NEW oscillatory
line (hunting) or a broadband rise?  Welch PSD of the wheel rate on the low-speed chunks (mean v < 6 m/s), V295 vs V294,
same batch, plus the peak in 0.15-2 Hz."""
import sys
import numpy as np
from scipy import signal
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295")
c4 = H.Cells.v294()
fam = H.family()
d = H.route()
ch = [c for c in H.route_chunks() if np.mean(d["v"][c[0]:c[1]]) < 6.0]
print("low-speed chunks:", len(ch), "total %.0f s" % (sum(b - a for a, b in ch) / 100))
PL = ("nominal", "light_b", "b_lo")
for dist in ("lp", "full"):
    R = H.simulate([c5, c4], [fam[p] for p in PL], ch, H.SimOpts(mode="B", dist=dist))
    nM, nK = len(PL), len(ch)
    for mi, p in enumerate(PL):
        out = []
        for ci, nm in enumerate(("V295", "V294")):
            Pw, f = 0, None
            for k in range(nK):
                j = ci * nM * nK + mi * nK + k
                n = R["lens"][j]
                x = R["rate18"][j, :n] - np.mean(R["rate18"][j, :n])
                f, pp = signal.welch(x, fs=100.0, nperseg=min(1024, n))
                Pw = Pw + np.interp(np.linspace(0, 50, 513), f, pp)
            f = np.linspace(0, 50, 513)
            m = (f >= 0.15) & (f <= 2.0)
            kk = np.flatnonzero(m)[np.argmax(Pw[m])]
            band = lambda lo, hi: np.sqrt(np.trapezoid(Pw[(f >= lo) & (f <= hi)], f[(f >= lo) & (f <= hi)]) / nK)
            out.append((nm, f[kk], Pw[kk], band(0.2, 1.0), band(1.0, 3.0)))
        print("  %-5s %-8s V295 peak %.2f Hz (P %.2f) rms0.2-1 %.2f rms1-3 %.2f | V294 peak %.2f Hz (P %.2f) rms0.2-1 %.2f rms1-3 %.2f | ratio 0.2-1 x%.3f, 1-3 x%.3f" % (
            dist, p, out[0][1], out[0][2], out[0][3], out[0][4], out[1][1], out[1][2], out[1][3], out[1][4], out[0][3] / out[1][3], out[0][4] / out[1][4]))
