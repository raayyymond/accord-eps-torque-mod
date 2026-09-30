# -*- coding: utf-8 -*-
"""rj14_score_read.py -- lens robust-joint: condense the harness score() of the finalists (rj10_score_<name>.json) into
the per-block tables the report quotes (candidate vs V294 in the same batch).  ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def main(names):
    for nm in names:
        r = json.load(open(os.path.join(HERE, "rj10_score_%s.json" % nm)))
        print("=" * 120)
        print("%s  diff %s  class %s  harness sha %s  hash %s" % (nm, r["meta"]["diff_vs_V294"], r["meta"]["edit_class"],
                                                                 r["meta"]["harness_sha256"][:16], r["meta"]["hash"][:16]))
        s, s0 = r["M_SAFE"], r["M_SAFE_V294"]
        print("M_SAFE rail +%d/%d (V294 +%d/%d) sub-rail %.4f (V294 %.4f) trim cap %d (V294 %d) int32 min %.2f restart100 %d (V294 %d)"
              % (s["rail_pos"], s["rail_neg"], s0["rail_pos"], s0["rail_neg"], s["subrail_T_per_wire"], s0["subrail_T_per_wire"],
                 s["trim_cap_T"], s0["trim_cap_T"], min(v["margin"] for v in s["int32"].values()), s["restart"]["100.0"]["peak"],
                 s0["restart"]["100.0"]["peak"]))
        # M_LOOP worst
        L = r["M_LOOP"]
        worst = max(L.items(), key=lambda kv: kv[1]["Ms"])
        gmw = min(L.items(), key=lambda kv: kv[1]["GM_min"])
        print("M_LOOP worst Ms %.3f at %s ; worst GM %.1f at %s ; all stable: %s ; worst Ms delay x1.5 %.3f"
              % (worst[1]["Ms"], worst[0], gmw[1]["GM_min"], gmw[0], all(v["stable"] is True for v in L.values()),
                 max(v["Ms_delay15"] for v in L.values())))
        h = r["M_HF"]
        print("M_HF |T/x| 5,9,13,17,20,23,30 Hz x V294: %s ; |P/x| 20 Hz %.3f (V294 %.3f, V282 %.2f)"
              % (np.round(h["T_per_x_vs_V294"], 2).tolist(), h["P_per_x"][4], h["P_per_x_V294"][4], h["P_per_x_V282"][4]))
        for k, x in h["stress_modes"].items():
            print("   stress %-16s f %.1f zeta %.3f (V294 %.3f, open %.3f)" % (k, x["f"], x["zeta"], x["zeta_V294"], x["zeta_open"]))
        print("   staircase cand %s | V294 %s" % ({k: round(v, 2) for k, v in h["staircase"]["cand"].items()},
                                                {k: round(v, 2) for k, v in h["staircase"]["V294"].items()}))
        for key in ("sim_A", "sim_B"):
            keys = sorted(h[key])
            for k in keys:
                if k.startswith(nm) or ("|" + nm + "|") in k:
                    k0 = k.replace(nm, "V294")
                    a, b = h[key][k], h[key].get(k0)
                    if b:
                        print("   %s %-26s " % (key, k) + "  ".join("%s %.2f/%.2f (x%.2f)" % (bb, a[bb], b[bb], a[bb] / max(b[bb], 1e-9))
                                                              for bb in a))
        t = r["M_TRACK"]
        print("M_TRACK mode A (literal cmd->alpha, per-chunk medians, dist full; probe transfer dist lp) cand vs V294:")
        for k in sorted(t["modeA"]):
            if not k.startswith(nm + "|"):
                continue
            k0 = "V294|" + k.split("|", 1)[1]
            a, b = t["modeA"][k], t["modeA"][k0]
            print("   %-18s " % k + "  ".join("%s R2 %.3f/%.3f G %.3f/%.3f ph %+.0f/%+.0f" % (bb, a[bb]["R2"], b[bb]["R2"], a[bb]["G"], b[bb]["G"],
                                                                                     a[bb]["ph"], b[bb]["ph"])
                                              for bb in ("lit_0.3-1", "lit_1-3", "lit_3-8")))
            print("   %-18s " % "" + "  ".join("%s G %.3f/%.3f ph %+.0f/%+.0f coh %.2f" % (bb, a[bb]["G"], b[bb]["G"], a[bb]["ph"], b[bb]["ph"], a[bb]["coh"])
                                              for bb in ("probe_1-3", "probe_3-8")))
        print("   flatness |alpha/cmd| 1-3 Hz at 30/100/300 counts rms: " + str({k: round(v, 3) for k, v in t["flatness"].items()}))
        o = r["M_DRIVE"]["outer"]
        print("M_DRIVE outer (Ms / GM) light_b by speed, relay on: " + "  ".join(
            "%s: %.2f/%.1f" % (k.split("|")[1], v["Ms"], v["GM_min"]) for k, v in o.items() if k.startswith("light_b|") and k.endswith("True")))


if __name__ == "__main__":
    main(sys.argv[1:] or ["F1", "F3"])
