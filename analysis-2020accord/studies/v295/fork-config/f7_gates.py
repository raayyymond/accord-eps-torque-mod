# -*- coding: utf-8 -*-
"""f7: apply the PRE-REGISTERED drive gates (CRITERIA-fork-config.md G5-G11) and the WIN condition to a sweep JSON
(out/f4_<stage>.json), every candidate against V295+r1 ("r1") from the same run.
  G5  tracking > 1.05 or turn-hold > 1.10 in any band, any member, lp or full
  G6  straight-line 1-3 Hz wheel rate (s13) > 1.3 x r1 on an identified member (lp), any band
  G7  1-5 Hz limit-cycle line > r1 + 3 dB on any member (lp)
  G8  hard-turn 1.6-3 Hz > 1.10 x r1 at 5-10 or 15-22 m/s on nominal or light_b (lp or full)
  G9  straight-line 0.3-1 Hz wheel rate (s03) > 1.3 x r1 on an identified member (lp)
  G10 divergence, or slew-limited share > 2 x r1 (+0.1 % floor) in any band
  G11 J-style error at 15-22 / 22+ > 1.10 x r1 on nominal or light_b (lp)
  WIN pooled 8-22 m/s: d tracking >= +0.05 AND d turn-hold >= +0.05 on nominal AND light_b (lp); straight delivery at
      0-5 and 5-10 not lowered (d >= -0.005).
Usage: python f7_gates.py <stage> [--brief]"""
import sys, json
import numpy as np

ID = ("nominal", "b_lo", "b_hi", "F_lo", "F_hi", "J_lo", "J_hi", "tau0", "tau6")
BANDS5 = ("0-5", "5-10", "10-15", "15-22", "22+")


def load(stage):
    J = json.load(open("out/f4_%s.json" % stage))
    res = {tuple(k.split("|")): v for k, v in J["res"].items()}
    return J["meta"], res


def gates(meta, res):
    dists = sorted({k[0] for k in res})
    members = sorted({k[2] for k in res}, key=lambda m: (m != "nominal", m))
    names = [n for n in meta if n not in ("r1",)]
    out = {}
    for n in names:
        f = []
        for d in dists:
            for m in members:
                r, b = res[(d, n, m)], res[(d, "r1", m)]
                if r.get("diverged"):
                    f.append("G10 %s/%s diverged" % (d, m))
                for band in BANDS5 + ("8-22",):
                    if band not in r:
                        continue
                    x, y = r[band], b[band]
                    if x["track_gain"] > 1.05 or (np.isfinite(x["turn_hold"]) and x["turn_hold"] > 1.10):
                        f.append("G5 %s/%s %s trk %.3f hold %.3f" % (d, m, band, x["track_gain"], x["turn_hold"]))
                    if band == "8-22":
                        continue
                    if d == "lp" and m in ID and np.isfinite(x["s13"]) and x["s13"] > 1.3 * y["s13"]:
                        f.append("G6 %s %s s13 x%.2f" % (m, band, x["s13"] / y["s13"]))
                    if d == "lp" and m in ID and np.isfinite(x["s03"]) and x["s03"] > 1.3 * y["s03"]:
                        f.append("G9 %s %s s03 x%.2f" % (m, band, x["s03"] / y["s03"]))
                    if band in ("5-10", "15-22") and m in ("nominal", "light_b") and np.isfinite(y["hard16"]) \
                            and x["hard16"] > 1.10 * y["hard16"]:
                        f.append("G8 %s/%s %s hard16 x%.2f" % (d, m, band, x["hard16"] / y["hard16"]))
                    if np.isfinite(x["slew_share"]) and x["slew_share"] > 2 * y["slew_share"] + 0.001:
                        f.append("G10 %s/%s %s slew %.4f vs %.4f" % (d, m, band, x["slew_share"], y["slew_share"]))
                    if d == "lp" and band in ("15-22", "22+") and m in ("nominal", "light_b") and x["J_err"] > 1.10 * y["J_err"]:
                        f.append("G11 %s %s J x%.2f" % (m, band, x["J_err"] / y["J_err"]))
                if d == "lp" and r["limit_cycle"]["dB"] > b["limit_cycle"]["dB"] + 3.0:
                    f.append("G7 %s lc %.1f dB vs %.1f" % (m, r["limit_cycle"]["dB"], b["limit_cycle"]["dB"]))
        win = {}
        for m in ("nominal", "light_b"):
            if ("lp", n, m) not in res or "8-22" not in res[("lp", n, m)]:
                continue
            r, b = res[("lp", n, m)], res[("lp", "r1", m)]
            win[m] = (r["8-22"]["track_gain"] - b["8-22"]["track_gain"], r["8-22"]["turn_hold"] - b["8-22"]["turn_hold"],
                      min(r[bb]["straight_delivery"] - b[bb]["straight_delivery"] for bb in ("0-5", "5-10")))
        is_win = len(win) == 2 and all(w[0] >= 0.05 and w[1] >= 0.05 and w[2] >= -0.005 for w in win.values())
        out[n] = dict(fails=f, win=win, is_win=is_win)
    return out


if __name__ == "__main__":
    stage = sys.argv[1]
    meta, res = load(stage)
    G = gates(meta, res)
    print("GATES + WIN for stage %s (every candidate vs V295+r1 in the same run)" % stage)
    for n, g in G.items():
        cls = sorted({x.split()[0] for x in g["fails"]})
        w = " ".join("%s:%+.3f/%+.3f/%+.3f" % (m, *v) for m, v in g["win"].items())
        print("  %-30s %-10s %-26s 8-22 d(trk/hold/min straight) %s" % (
            n, "WIN" if g["is_win"] else "-", "PASS" if not g["fails"] else "FAIL " + ",".join(cls), w))
        if "--brief" not in sys.argv and g["fails"]:
            print("        " + "; ".join(g["fails"][:8]))
    json.dump(G, open("out/f7_gates_%s.json" % stage, "w"), indent=1)
