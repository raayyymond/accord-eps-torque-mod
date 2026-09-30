# -*- coding: utf-8 -*-
"""a9 -- (e) do the claimed DIRECTIONS hold across the WHOLE family (not only the designer's 6 default plants), plus the
two record-calibrated worlds from a7?  Uses the harness's sweep_drive (mode B, r1 fork port, r71b's 21 chunks) AFTER a
spot check: (i) the harness Lane with the candidate cells == my MyLane tick for tick; (ii) one retrodiction row
(V294, lp, nominal tracking gain by band == 0.840/0.865/0.586/0.764/0.917 in V295-HARNESS.md section 8)."""
import json
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import adv_lib as A  # noqa: E402
import v295_harness as H  # noqa: E402

out = open(os.path.join(HERE, "a9_family_directions_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    out.write(s + "\n")
    out.flush()


base = H.Cells.v294()
cand = base.replace(kp_x=A.CAND_X, kp_y=A.CAND_Y, name="cand")
# (i) harness Lane vs my lane
b294, _ = A.load(A.IMG_V294, A.SHA_V294)
cc = A.cells(A.write_candidate(b294))
my = A.MyLane(cc)
HL = H.Lane([cand])
rng = np.random.default_rng(5)
mism, wire, x = 0, 0, 0
for n in range(5000):
    if n % 10 == 0:
        wire = int(np.clip(wire + rng.integers(-150, 151), -3900, 3900))
        i1, s1 = my.demand(wire)
        i2, s2, m2 = HL.demand(np.array([wire]))
        mism += int(i1 != int(i2[0]) or s1 != int(s2[0]) or int(m2[0]) != 254)
    x = int(np.clip(x + rng.integers(-60, 61), -11000, 11000))
    t1, _ = my.tick(x, s1, i1)
    t2, _ = HL.tick(np.array([x]), s2, i2, m2)
    mism += int(t1 != int(t2[0]))
P("(i) harness Lane(cand) vs my lane: %d mismatches in 5000 ticks" % mism)

# the two record-calibrated worlds (a7: consistent with r71-old's limit cycle AND r71b's clean curves; C-soft ok)
fam0 = H.family()
lb = fam0["light_b"]
extra = {}
for nm, beta, gamma in (("cw_b1_J.5", 1.0, 0.5), ("cw_b1.25_J1", 1.25, 1.0), ("cw_b.75_J.5", 0.75, 0.5)):
    m = replace(lb, name=nm, J=lb.J * gamma, b=lb.b * beta, note="light_b calibrated on the record (adversary a7)")
    m.kappa = False
    extra[nm] = m
_orig_family = H.family


def fam_patched(include_stress=True):
    f = _orig_family(include_stress)
    f.update(extra)
    return f


H.family = fam_patched
plants = ("nominal", "J_lo", "J_hi", "J_hi2", "J_0.3", "b_lo", "b_hi", "F_lo", "F_hi", "tau0", "tau6", "ms_free",
          "nominal_kappa", "light_b", "cw_b1_J.5", "cw_b1.25_J1", "cw_b.75_J.5")
res = H.sweep_drive([cand], plants=plants, dists=("lp", "full"))
json.dump(H.to_jsonable(res), open(os.path.join(HERE, "a9_family_directions.json"), "w"))
bands = ("0-5", "5-10", "10-15", "15-22", "22+")
# (ii) retrodiction row
row = [res[("lp", "V294", "nominal")].get(b, {}).get("track_gain", np.nan) for b in bands]
P("(ii) V294 lp nominal tracking gain by band: %s (harness report 0.840/0.865/0.586/0.764/0.917)" % np.round(row, 3))

metrics = ("track_gain", "turn_hold", "straight_delivery", "hard16", "r_mid", "r_hi", "J_err", "i_share")
P("\nDIFFERENCES cand - V294 (ratios for hard16 / r_mid / r_hi / J_err), per plant, per band; dist lp then full")
flags = []
for dist in ("lp", "full"):
    P("== dist %s" % dist)
    for p in plants:
        a, c = res[(dist, "V294", p)], res[(dist, "cand", p)]
        cells = []
        for b in bands:
            if b not in a or b not in c:
                cells.append("%s: -" % b)
                continue
            tg = c[b]["track_gain"] - a[b]["track_gain"]
            th = c[b]["turn_hold"] - a[b]["turn_hold"]
            sd = c[b]["straight_delivery"] - a[b]["straight_delivery"]
            h16 = c[b]["hard16"] / a[b]["hard16"] if a[b]["hard16"] == a[b]["hard16"] and a[b]["hard16"] > 0 else np.nan
            rm = c[b]["r_mid"] / a[b]["r_mid"]
            rh = c[b]["r_hi"] / a[b]["r_hi"]
            je = c[b]["J_err"] / a[b]["J_err"]
            cells.append("%s: tg %+.3f th %+.3f sd %+.3f h16 x%.2f r13 x%.2f r38 x%.2f J x%.2f" % (b, tg, th, sd, h16, rm, rh, je))
            if b in ("22+",) and tg < 0.0:
                flags.append((dist, p, b, "22+ tracking DOWN", tg))
            if b in ("15-22", "22+") and th == th and th < 0.0:
                flags.append((dist, p, b, "turn-hold DOWN", th))
            if b in ("5-10", "15-22") and h16 == h16 and h16 > 1.10:
                flags.append((dist, p, b, "hard16 up > 10 %", h16))
        lc_a, lc_c = a["limit_cycle"], c["limit_cycle"]
        P("  %-13s LC %.2fHz %+.1fdB -> %.2fHz %+.1fdB | %s" % (p, lc_a["f"], lc_a["dB"], lc_c["f"], lc_c["dB"], " | ".join(cells)))
        if lc_c["dB"] > lc_a["dB"] + 3:
            flags.append((dist, p, "LC up > 3 dB", lc_a["dB"], lc_c["dB"]))
P("\nflags (claimed direction reversed, or G6-type rises):", len(flags))
for f in flags:
    P("  ", f)
out.close()
