# -*- coding: utf-8 -*-
"""rj8_sweep_read.py -- lens robust-joint: read rj6_sweep.json per COMPLAINT, per member, per disturbance model, as the
DIFFERENCE from V294 in the same batch (the harness rule), with the measured drive beside it.

Complaint proxies (M_DRIVE, harness drive_metrics):
  C1 "Jerky on hard turns at medium speed"  : hard16 (1.6-3 Hz wheel rate in hard turns) at 5-10 and 15-22 m/s (ratio),
                                               r_mid (1-3 Hz wheel rate) at 5-10 / 10-15 / 15-22 (ratio), limit-cycle peak (lp)
  C2 "Loose on straights and turns at low speed" : track_gain, straight_delivery, turn_hold at 0-5 / 5-10 (difference)
  C3 "Loose/understeer at highway turns"    : track_gain, turn_hold at 15-22 / 22+ (difference)
  guard: track_gain + turn_hold must not exceed ~1.0 when added to the MEASURED V294 value (oversteer; V283's class)
Magnitudes under lp for 1-8 Hz wheel motion are NOT FIT (harness): only the sign across members is read there.
ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "rj6_sweep.json")))
PL = ("nominal", "light_b", "b_lo", "F_hi", "J_hi", "tau6")
CANDS = sorted({k.split("|")[1] for k in R if "|" in k and k.split("|")[1] != "V294"})
BANDS = ("0-5", "5-10", "10-15", "15-22", "22+")


def g(dist, c, p, band, key):
    x = R.get("%s|%s|%s" % (dist, c, p), {}).get(band, {})
    return x.get(key, float("nan")) if isinstance(x, dict) else float("nan")


def main():
    meas = R["measured"]
    print("MEASURED r71b (hands-off chunks): " + "  ".join(
        "%s: tg %.3f th %.3f str %.2f hard %.2f rmid %.2f" % (b, meas[b]["track_gain"], meas[b]["turn_hold"],
                                                           meas[b]["straight_delivery"], meas[b]["hard16"], meas[b]["r_mid"])
        for b in BANDS if b in meas))
    for c in CANDS:
        print("\n" + "=" * 150 + "\n%s  (difference / ratio vs V294, same batch)" % c)
        for dist in ("lp", "full"):
            print("  dist %s" % dist)
            print("    %-8s | C1 hard16 5-10 15-22 | rmid 5-10 10-15 15-22 | LC dB(c/294) | C2 tg 0-5 5-10 | str 0-5 5-10 | th 5-10 |"
                  " C3 tg 15-22 22+ | th 15-22 22+ | ish 5-10 15-22 | cmd 5-10" % "member")
            for p in PL:
                def rat(b, k):
                    return g(dist, c, p, b, k) / g(dist, "V294", p, b, k)

                def dif(b, k):
                    return g(dist, c, p, b, k) - g(dist, "V294", p, b, k)
                lc = R.get("%s|%s|%s" % (dist, c, p), {}).get("limit_cycle", {})
                lc0 = R.get("%s|V294|%s" % (dist, p), {}).get("limit_cycle", {})
                print("    %-8s |      x%.2f  x%.2f       |  x%.2f  x%.2f  x%.2f  | %+.1f/%+.1f   | %+.3f %+.3f     | %+.3f %+.3f  | %+.3f  |"
                      "   %+.3f %+.3f   | %+.3f %+.3f  | %+.3f %+.3f | x%.3f"
                      % (p, rat("5-10", "hard16"), rat("15-22", "hard16"), rat("5-10", "r_mid"), rat("10-15", "r_mid"),
                         rat("15-22", "r_mid"), lc.get("dB", np.nan), lc0.get("dB", np.nan),
                         dif("0-5", "track_gain"), dif("5-10", "track_gain"), dif("0-5", "straight_delivery"),
                         dif("5-10", "straight_delivery"), dif("5-10", "turn_hold"), dif("15-22", "track_gain"),
                         dif("22+", "track_gain"), dif("15-22", "turn_hold"), dif("22+", "turn_hold"), dif("5-10", "i_share"),
                         dif("15-22", "i_share"), rat("5-10", "cmd_rms")))
        # oversteer guard: measured + worst-member delta (lp)
        print("  OVERSTEER GUARD (lp): measured V294 + max over members of the sim delta  -> must stay <= ~1.00")
        for b in BANDS:
            dtg = [g("lp", c, p, b, "track_gain") - g("lp", "V294", p, b, "track_gain") for p in PL]
            dth = [g("lp", c, p, b, "turn_hold") - g("lp", "V294", p, b, "turn_hold") for p in PL]
            dth = [x for x in dth if np.isfinite(x)]
            print("    %-6s track_gain %.3f + [%+.3f .. %+.3f] -> <= %.3f ; turn_hold %.3f + [%s] -> <= %s"
                  % (b, meas[b]["track_gain"], min(dtg), max(dtg), meas[b]["track_gain"] + max(dtg), meas[b]["turn_hold"],
                     ("%+.3f .. %+.3f" % (min(dth), max(dth))) if dth else "n/t",
                     ("%.3f" % (meas[b]["turn_hold"] + max(dth))) if dth and np.isfinite(meas[b]["turn_hold"]) else "n/t"))
    # the lp absolute levels for V294 by member (context for the directional reads)
    print("\nV294 sim lp by member: track_gain per band")
    for p in PL:
        print("   %-8s " % p + " ".join("%.3f" % g("lp", "V294", p, b, "track_gain") for b in BANDS))


if __name__ == "__main__":
    main()
