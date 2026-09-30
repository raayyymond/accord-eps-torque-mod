"""ADV-D 6d: simulated delivered 5-30 Hz torque under dist lp (the loop's own motion, no replayed road HF), mode B, V295 vs
V294 same batch -- score() records the 1 kHz torque only for its first dist (full)."""
import sys
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
c5 = H.Cells.from_image(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "V295")
c4 = H.Cells.v294()
fam = H.family()
PL = ("nominal", "light_b", "tau6", "mode20", "mode20_lo", "mode13")
ch = H.route_chunks()
R = H.simulate([c5, c4], [fam[p] for p in PL], ch, H.SimOpts(mode="B", dist="lp"), record_1k=True)
nM, nK = len(PL), len(ch)
for mi, p in enumerate(PL):
    hf = []
    for ci in range(2):
        rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
        h = [H.hf_content(R["T1k"][j, :R["lens"][j] * 10]) for j in rows]
        hf.append({k: float(np.sqrt(np.mean([x[k] ** 2 for x in h]))) for k in h[0]})
    print("  lp %-10s V295/V294: %s   (V294 abs %s)" % (p, "  ".join("%s x%.2f" % (k, hf[0][k] / hf[1][k]) for k in hf[0]),
          {k: round(v, 2) for k, v in hf[1].items()}))
