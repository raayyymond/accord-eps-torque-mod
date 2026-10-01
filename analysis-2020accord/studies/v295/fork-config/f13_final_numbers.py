# -*- coding: utf-8 -*-
"""f13: the pre-registration numbers for the chosen config and the runner-ups.
  (1) the drive's own r71b values by band (H.drive_metrics on the measured series, same chunks, same code) -- the
      baseline drive (1) (V295 + r1) is expected to reproduce within the firmware's <= 0.004 outer-loop effect;
  (2) the sim delta (candidate - V295+r1) by band from the robustness replicates, min / max over {nominal, b_lo, F_hi,
      light_b} x {lp, full} x {seed 0, 5} -> the predicted drive (2) value = r71b + delta (a range);
  (3) the 100 Hz wire reads the config must produce: Kp, Ki(v) by speed, LAF, the friction plateau (m/s^2, torque,
      CAN counts), the relay small-signal slope, and what the r1 flight read for the same.
Usage: python f13_final_numbers.py <chosen> <runner-up> ..."""
import sys, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

names = sys.argv[1:]
ch = H.route_chunks()
meas = H.drive_metrics(H.drive_series_measured(ch), band_list=F.BANDS_X)
BB = ("0-5", "5-10", "10-15", "15-22", "22+", "8-22")
print("r71b MEASURED (V294 + r1), same chunks / code:")
for b in BB:
    m = meas[b]
    print("  %-6s tracking %.3f  turn-hold %s  straight %.3f  i-share %.2f  J %.3f  (%.0f s)" % (
        b, m["track_gain"], ("%.3f" % m["turn_hold"]) if np.isfinite(m["turn_hold"]) else " n/t ", m["straight_delivery"],
        m["i_share"], m["J_err"], m["sec"]))
reps = []
for tag in __import__("os").environ.get("REP_TAGS", "s4seed0,s4seed5,s4seed0_skip3,s4seed5_skip3").split(","):
    J = json.load(open("out/f4_%s.json" % tag))
    reps.append((tag, {tuple(k.split("|")): v for k, v in J["res"].items()}))
MEM = ("nominal", "b_lo", "F_hi", "light_b")
KEYS = ("track_gain", "turn_hold", "straight_delivery", "i_share", "J_err", "hard16", "s13", "s15", "s03")
out = {"measured": meas}
for n in names:
    print("\n%s: predicted drive (2) = r71b + sim delta [min, max over %s x lp/full x 2 seeds x 2 warm forms]" % (n, "/".join(MEM)))
    out[n] = {}
    for b in BB:
        row = {}
        for k in KEYS:
            ds = []
            for tag, res in reps:
                for d in ("lp", "full"):
                    for m in MEM:
                        r, y = res[(d, n, m)], res[(d, "r1", m)]
                        if b not in r or b not in y or not np.isfinite(r[b][k]) or not np.isfinite(y[b][k]):
                            continue
                        ds.append(r[b][k] - y[b][k] if k in ("track_gain", "turn_hold", "straight_delivery", "i_share")
                                  else r[b][k] / y[b][k])
            row[k] = (float(np.min(ds)), float(np.max(ds))) if ds else (float("nan"), float("nan"))
        out[n][b] = row
        tg, th = row["track_gain"], row["turn_hold"]
        mt, mh = meas[b]["track_gain"], meas[b]["turn_hold"]
        print("  %-6s tracking %+.3f..%+.3f -> %.2f..%.2f | turn-hold %+.3f..%+.3f -> %s | straight %+.3f..%+.3f | i-share %+.2f..%+.2f"
              " | J x%.2f..%.2f | hard16 x%.2f..%.2f | s13 x%.2f..%.2f | s15 x%.2f..%.2f" % (
                  b, tg[0], tg[1], mt + tg[0], mt + tg[1], th[0], th[1],
                  ("%.2f..%.2f" % (mh + th[0], mh + th[1])) if np.isfinite(mh) else "n/t", *row["straight_delivery"],
                  *row["i_share"], *row["J_err"], *row["hard16"], *row["s13"], *row["s15"]))
    fk = {f["name"]: f for sp in ("out/fin_spec.json", "out/s5_spec.json") for f in json.load(open(sp))["forks"]}.get(n)
    if fk:
        f = F.Fork(**fk)
        print("  WIRE: Kp %.4f (p/error) | Ki(v) %s | LAF %.4f | friction plateau %.4f m/s^2 = %.4f torque = %.1f CAN counts"
              " | relay slope (torque per m/s^2 err) %s" % (
                  f.kp, {v: round(float(f.ki_at(v)), 4) for v in (5, 8, 10, 12, 15, 18, 25)}, f.laf, f.fric * f.laf, f.fric,
                  f.fric * 4096, {v: round(F.relay_slope_torque(f, v), 3) for v in (3.1, 8, 17, 27)}))
json.dump(out, open("out/f13_final_numbers.json", "w"), indent=1)
