# -*- coding: utf-8 -*-
"""s13_compare.py -- p-gain lens: the finalists' SHARED score() dicts (s8) side by side, every number a difference from
V294 in the SAME batch (harness rule 1), under both disturbance models and all six default plants.  Also the goal
metric (mode-A literal fits, amplitude flatness), M_SAFE, M_HF, and the worst inner margins.  ANALYSIS ONLY."""
import json
import os

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
NAMES = ["R1.3_8_100", "R1.35_4_100", "R-offset", "g1.2"]
PLANTS = ["nominal", "b_lo", "F_hi", "J_hi", "light_b", "tau6"]
BANDS = ["0-5", "5-10", "10-15", "15-22", "22+"]


def main():
    R = {n: json.load(open(os.path.join(OUT, "s8_score_%s.json" % n))) for n in NAMES}
    summ = {}
    for n, r in R.items():
        sim = r["M_DRIVE"]["sim"]
        print("\n" + "=" * 100 + "\n%s   harness sha %s  score hash %s" % (n, r["meta"]["harness_sha256"][:12], r["meta"]["hash"][:16]))
        s = r["M_SAFE"]
        print(" M_SAFE rail %+d/%d  subrail(polyfit) %.4f  trim cap %d T (%.1f%%)  int32 min %.2f  restart %s" % (
            s["rail_pos"], s["rail_neg"], s["subrail_T_per_wire"], s["trim_cap_T"], s["trim_cap_pct_rail"],
            min(v["margin"] for v in s["int32"].values()), {k: v["peak"] for k, v in s["restart"].items()}))
        ml = r["M_LOOP"]
        worst = min((v["GM_min"], k) for k, v in ml.items())
        wMs = max((v["Ms"], k) for k, v in ml.items())
        wMs15 = max((v["Ms_delay15"], k) for k, v in ml.items())
        unstable = [k for k, v in ml.items() if v["stable"] is not True]
        print(" M_LOOP inner: GM min %.1f (%s)  Ms max %.2f (%s)  Ms(delay x1.5) max %.2f  not-stable: %s" % (worst[0], worst[1], wMs[0], wMs[1], wMs15[0], unstable))
        h = r["M_HF"]
        print(" M_HF |P/x| 20 Hz %.3f (V294 %.3f, V282 %.2f) ; stress zeta cand/V294: %s" % (
            h["P_per_x"][4], h["P_per_x_V294"][4], h["P_per_x_V282"][4],
            {k: "%.3f/%.3f" % (v["zeta"], v["zeta_V294"]) for k, v in h["stress_modes"].items()}))
        for key in ("sim_A", "sim_B"):
            rat = []
            for k, v in h.get(key, {}).items():
                if "V294" in k:
                    continue
                kv = k.replace(n, "V294")
                if kv in h[key]:
                    rat.append({b: v[b] / h[key][kv][b] for b in v})
            if rat:
                print(" M_HF %s delivered-torque ratio cand/V294 per band, max over plants: %s" % (
                    key, {b: round(max(x[b] for x in rat), 2) for b in rat[0]}))
        fl = r["M_TRACK"]["flatness"]
        for p in ("nominal", "b_lo", "F_hi"):
            a = [fl["%s|%s|%s" % (n, p, amp)] for amp in ("30.0", "100.0", "300.0")]
            b = [fl["V294|%s|%s" % (p, amp)] for amp in ("30.0", "100.0", "300.0")]
            print(" goal: flatness %s  |a/cmd| 1-3 Hz @30/100/300 counts rms  cand %s (small/large %.2f)  V294 %s (%.2f)" % (
                p, np.round(a, 3).tolist(), a[0] / a[2], np.round(b, 3).tolist(), b[0] / b[2]))
        ma = r["M_TRACK"]["modeA"]
        for p in ("nominal", "light_b"):
            c, v = ma["%s|%s" % (n, p)], ma["V294|%s" % p]
            print(" goal: mode-A literal %s: R2 0.3-1/1-3/3-8 cand %.3f/%.3f/%.3f V294 %.3f/%.3f/%.3f ; phase cand %+.0f/%+.0f/%+.0f V294 %+.0f/%+.0f/%+.0f ; |G| x%.2f/x%.2f/x%.2f" % (
                p, c["lit_0.3-1"]["R2"], c["lit_1-3"]["R2"], c["lit_3-8"]["R2"], v["lit_0.3-1"]["R2"], v["lit_1-3"]["R2"], v["lit_3-8"]["R2"],
                c["lit_0.3-1"]["ph"], c["lit_1-3"]["ph"], c["lit_3-8"]["ph"], v["lit_0.3-1"]["ph"], v["lit_1-3"]["ph"], v["lit_3-8"]["ph"],
                c["lit_0.3-1"]["G"] / v["lit_0.3-1"]["G"], c["lit_1-3"]["G"] / v["lit_1-3"]["G"], c["lit_3-8"]["G"] / v["lit_3-8"]["G"]))
        rows = {}
        for dist in ("lp", "full"):
            for key, f in (("track_gain", "d"), ("turn_hold", "d"), ("straight_delivery", "d"), ("J_err", "r"), ("i_share", "d"),
                           ("r_mid", "r"), ("hard16", "r"), ("r_hi", "r")):
                for b in BANDS:
                    vals = []
                    for p in PLANTS:
                        c = sim.get("%s|%s|%s" % (dist, n, p), {}).get(b, {}).get(key, np.nan)
                        v = sim.get("%s|V294|%s" % (dist, p), {}).get(b, {}).get(key, np.nan)
                        vals.append((c - v) if f == "d" else (c / v if v else np.nan))
                    vals = np.array(vals, float)
                    if np.all(np.isnan(vals)):
                        continue
                    rows[(dist, key, b)] = (float(np.nanmin(vals)), float(np.nanmax(vals)), float(vals[PLANTS.index("nominal")]),
                                            float(vals[PLANTS.index("light_b")]))
            lcs = [sim["%s|%s|%s" % (dist, n, p)]["limit_cycle"]["dB"] - sim["%s|V294|%s" % (dist, p)]["limit_cycle"]["dB"] for p in PLANTS]
            rows[(dist, "lc_dB", "all")] = (min(lcs), max(lcs), lcs[0], lcs[4])
        print(" M_DRIVE (candidate vs V294 same batch; d = difference, r = ratio): [min over 6 plants, max over 6 plants] nominal / light_b")
        for dist in ("lp", "full"):
            for key in ("track_gain", "turn_hold", "straight_delivery", "J_err", "i_share", "r_mid", "hard16", "r_hi", "lc_dB"):
                line = []
                for b in BANDS + ["all"]:
                    if (dist, key, b) in rows:
                        lo, hi, nm, lb = rows[(dist, key, b)]
                        line.append("%s [%+.3f,%+.3f] %+.3f/%+.3f" % (b, lo, hi, nm, lb) if key in ("track_gain", "turn_hold", "straight_delivery", "i_share", "lc_dB")
                                    else "%s [%.2f,%.2f] %.2f/%.2f" % (b, lo, hi, nm, lb))
                print("  %-4s %-17s %s" % (dist, key, "  ".join(line)))
        summ[n] = {"|".join(k): v for k, v in rows.items()}
        meas = r["M_DRIVE"]["measured"]
        summ[n]["measured"] = meas
    json.dump(summ, open(os.path.join(OUT, "s13_compare.json"), "w"), indent=1)
    m = R[NAMES[0]]["M_DRIVE"]["measured"]
    print("\nmeasured (r71b, same chunks, same code): " + "  ".join("%s track %.3f hold %.3f str %.2f" % (b, m[b]["track_gain"], m[b]["turn_hold"], m[b]["straight_delivery"]) for b in BANDS if b in m))
    sim = R[NAMES[0]]["M_DRIVE"]["sim"]
    for dist in ("lp", "full"):
        print("V294 sim %s nominal: " % dist + "  ".join("%s track %.3f hold %.3f str %.2f" % (b, sim["%s|V294|nominal" % dist][b]["track_gain"], sim["%s|V294|nominal" % dist][b]["turn_hold"],
                                                                                    sim["%s|V294|nominal" % dist][b]["straight_delivery"]) for b in BANDS))


if __name__ == "__main__":
    main()
