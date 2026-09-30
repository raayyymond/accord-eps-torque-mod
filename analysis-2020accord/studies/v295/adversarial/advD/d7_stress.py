"""ADV-D step 7: the 13-20 Hz stress modes at 2 / 6 / 9 ms delay after the tap (plus 4 and 12 ms), open (C = 0) vs V294 vs
V295 (cells from the IMAGE) vs V282 (the lane that ground at 20 Hz on car), exact 1 kHz linear closed loop
(harness closed_loop_modes, which supports the sum operand, D and any flat gains).  Sign convention: dzeta = zeta_lane -
zeta_open; negative = the lane REMOVES damping (anti-damping).  Also the inner Ms of the wider set the stability adversary
used (light_b + a 20 Hz flexible mode) at delay x1 / x1.5 / x3.  V282's r24 lane (5244, engaged) is NOT modelled (it damps
20 Hz on the record), so V282's own de-damping here is upper-leaning."""
import sys
import numpy as np
from dataclasses import replace
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
c5 = H.Cells.from_image(V295, "V295", "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")
c4 = H.Cells.v294()
c2 = H.Cells.v282()
print("V282 cells: fb_op %s e_shift %d a %d b %d C %d kp %s kd %s dcl %d" % (c2.fb_op, c2.e_shift, c2.fb_a, c2.fb_b, c2.fb_clamp,
      c2.kp_y, c2.kd_y, c2.d_clamp))
cO = c5.replace(fb_clamp=0, name="open")
fam = H.family()
lb = fam["light_b"]
extra = {}
for nm, (f2, z2, r2) in (("lb_mode20_lo", (20.0, 0.02, 0.5)), ("lb_mode20", (20.0, 0.05, 0.2)), ("mode16_lo", (16.0, 0.02, 0.5))):
    base = lb if nm.startswith("lb") else fam["nominal"]
    m = base.with_mode20(f2=f2, zeta2=z2, r2=r2)
    m.name = nm
    m.kappa = False
    extra[nm] = m
fam.update(extra)
band = {"mode13": (8, 20), "mode20": (14, 30), "mode20_lo": (12, 30), "lb_mode20_lo": (12, 30), "lb_mode20": (14, 30),
        "mode16_lo": (10, 26)}
print("\n%-13s %5s %4s | %-7s %-7s %-7s %-7s | dz V294  dz V295  dz V282 | V295/V282  (V295-V294)/V282" % (
    "member", "v", "tau", "open", "V294", "V295", "V282"))
worst = []
for nm in ("mode13", "mode20", "mode20_lo", "mode16_lo", "lb_mode20", "lb_mode20_lo"):
    for v in (5.0, 12.0, 25.0):
        p0 = fam[nm].at(v)
        for tau in (2, 4, 6, 9, 12):
            p = replace(p0, tau_ms=tau)
            res = {}
            for lab, cc in (("open", cO), ("V294", c4), ("V295", c5), ("V282", c2)):
                (f, z), rho = H.stress_damping(cc, p, band[nm])
                res[lab] = (f, z, rho)
            zo = res["open"][1]
            d4, d5, d2 = res["V294"][1] - zo, res["V295"][1] - zo, res["V282"][1] - zo
            r52 = d5 / d2 if d2 < -1e-6 else float("nan")
            r_inc = (d5 - d4) / d2 if d2 < -1e-6 else float("nan")
            unst = [k for k in res if res[k][2] >= 1.0]
            print("%-13s %5.1f %4d | %.4f  %.4f  %.4f  %.4f | %+.4f  %+.4f  %+.4f | %8s  %8s %s" % (nm, v, tau, zo, res["V294"][1],
                  res["V295"][1], res["V282"][1], d4, d5, d2, "%.3f" % r52 if np.isfinite(r52) else "-",
                  "%.3f" % r_inc if np.isfinite(r_inc) else "-", ("UNSTABLE:" + ",".join(unst)) if unst else ""))
            worst.append((nm, v, tau, d5, d4, d2, r52, res["V295"][1], res["V294"][1], unst))
anti = [w for w in worst if w[3] < 0]
print("\nV295 removes damping (dz < 0) in %d of %d rows; worst dz %.4f at %s" % (len(anti), len(worst),
      min(w[3] for w in worst), min(worst, key=lambda t: t[3])[:3]))
fin = [w for w in worst if np.isfinite(w[6]) and w[5] < -0.003]
if fin:
    print("V295 dz as a fraction of V282's dz (rows where V282 removes > 0.003): max %.3f at %s ; median %.3f" % (
        max(w[6] for w in fin), max(fin, key=lambda t: t[6])[:3], float(np.median([w[6] for w in fin]))))
print("rows with a stress zeta < 0.05 on V295 where V294 >= 0.05: %s" % [w[:3] for w in worst if w[7] < 0.05 <= w[8]])
print("rows unstable on V295 but not on V294: %s" % [w[:3] for w in worst if "V295" in w[9] and "V294" not in w[9]])

print("\n=== inner Ms / GM, the wider set (light_b + flexible modes), delay x1 / x1.5 / x3 ===")
fg = np.logspace(-1, np.log10(45.0), 2500)
for nm in ("light_b", "lb_mode20_lo", "lb_mode20", "mode20_lo", "tau9"):
    for v in (3.1, 8.0, 12.0, 26.9):
        p0 = fam[nm].at(v)
        row = []
        for k in (1.0, 1.5, 3.0):
            p = replace(p0, tau_ms=int(round(max(p0.tau_ms, 1) * k)))
            m5 = H.margins(fg, H.loop_frf(c5, p, fg)); m4 = H.margins(fg, H.loop_frf(c4, p, fg))
            row.append("x%.1f Ms %.3f/%.3f GM %.2f/%.2f" % (k, m5["Ms"], m4["Ms"], m5["GM_min"], m4["GM_min"]))
        print("  %-13s %5.1f tau0 %d | %s" % (nm, v, p0.tau_ms, " | ".join(row)))
