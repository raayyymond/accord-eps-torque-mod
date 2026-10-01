# -*- coding: utf-8 -*-
"""f0: probe the harness -- members, their per-speed parameters, the route toggles, the chunks, the V295 cells read
from the V295 IMAGE (second method vs Cells.v294().replace(fb_b=1050))."""
import sys, os, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import numpy as np
import v295_harness as H

V295_IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-"
            "FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V295_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"

c_img = H.Cells.from_image(V295_IMG, "V295", V295_SHA)
c_rep = H.Cells.v294().replace(fb_b=1050, name="V295")
print("V295 from image vs V294.replace(fb_b=1050): diff =", c_img.diff(c_rep))
print("V295 vs V294:", c_img.diff(H.Cells.v294()))
print("problems:", c_img.problems())

fam = H.family()
print("members:", list(fam))
for nm in ("nominal", "b_lo", "b_hi", "F_lo", "F_hi", "J_lo", "J_hi", "tau0", "tau6", "light_b", "ms_free"):
    if nm not in fam:
        print("  missing", nm); continue
    m = fam[nm]
    for v in (3.1, 5.0, 8.0, 12.0, 17.0, 22.0, 26.9):
        a = m.arrays_at(np.array([v]))
        print("  %-8s v %4.1f  J %.3f b %.2f k %.2f Fc %.1f Fs %.1f sat %.1f tau %d w %d" % (
            nm, v, a["J"][0], a["b"][0], a["k"][0], a["Fc"][0], a["Fs"][0], a["sat"][0], m.tau_ms, m.rate_win_ms))

d = H.route()
tg = d["toggles"]
keys = ["steerKp", "accord_torque_ki", "accord_torque_ki_high", "latAccelFactor", "friction", "steerRatio",
        "use_custom_latAccelFactor", "use_custom_friction", "keep_learned_lat_accel_offset", "accord_jerk_lp_hz",
        "accord_rate_plant_ff", "steer_delay", "use_auto_steer_delay"]
print("route toggles:", {k: tg.get(k, "<absent>") for k in keys})
ch = H.route_chunks()
vm = [float(np.mean(d["v"][a:b])) for a, b in ch]
print("chunks:", len(ch), "total s", sum(b - a for a, b in ch) / 100.0)
print("chunk mean speeds:", np.round(vm, 1).tolist())
print("ltp_off (learned offset) over chunks: p5/p50/p95", np.percentile(np.concatenate([d["ltp_off_f"][a:b] for a, b in ch]), [5, 50, 95]))
print("delay_f over chunks: unique", np.unique(np.round(np.concatenate([d["delay_f"][a:b] for a, b in ch]), 4))[:10])
print("roll p50:", np.median(np.concatenate([d["lpar_roll_f"][a:b] for a, b in ch])))
