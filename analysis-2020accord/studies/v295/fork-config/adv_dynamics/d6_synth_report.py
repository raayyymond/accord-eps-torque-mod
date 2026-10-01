# -*- coding: utf-8 -*-
"""d6_synth_report -- tables from d5_synth json (paired rows across configs)."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
fn = sys.argv[1] if len(sys.argv) > 1 else "d5_synth_p22_s3.json"
res = json.load(open(os.path.join(HERE, "out", fn)))
C = ("V294+r1", "V295+r1", "V295+r2alt")
n = len(res[C[0]])
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
P("source %s" % fn)
# ---------------- S1 hunt
P("\n== S1 HUNT (straight, zero demand, crown x Fs), last 30 s: angle p-p deg [slow-weave 0.1-1.5 Hz p-p | chatter 3-6 Hz p-p] (fpk Hz) ==")
rows = [j for j in range(n) if res[C[0]][j]["kind"] == "S1"]
flags = []
worst = {c: {} for c in C}
for j in rows:
    a, b, c = (res[k][j] for k in C)
    for k, s in zip(C, (a, b, c)):
        worst[k][s["v"]] = max(worst[k].get(s["v"], 0.0), s["pp"])
    # X6 flags: r2alt new slow hunt > 0.5 deg at >= 15 m/s where V295+r1 has < 0.25; chatter > 0.2 deg p-p where r1 has < 0.1
    if (c["v"] >= 15 and c["pp_w"] > 0.5 and b["pp_w"] < 0.25) or (c["pp_c"] > 0.2 and b["pp_c"] < 0.1) or \
       (c["pp"] > max(2 * b["pp"], 0.25) and c["pp"] - b["pp"] >= 0.25):
        flags.append((c["member"], c["v"], c["crown"], b["pp"], c["pp"], b["pp_w"], c["pp_w"], c["pp_c"], c["fpk"]))
    if c["pp"] >= 0.5 or b["pp"] >= 0.5 or a["pp"] >= 0.5 or c["pp_c"] > 0.15 or b["pp_c"] > 0.15:
        P("  %-8s v%5.1f crown %.1f | V294r1 %.2f [%.2f|%.2f] (%.2f) | V295r1 %.2f [%.2f|%.2f] (%.2f) | r2alt %.2f [%.2f|%.2f] (%.2f) | stuck %.2f/%.2f/%.2f" % (
            c["member"], c["v"], c["crown"], a["pp"], a["pp_w"], a["pp_c"], a["fpk"], b["pp"], b["pp_w"], b["pp_c"], b["fpk"],
            c["pp"], c["pp_w"], c["pp_c"], c["fpk"], a["stuck"], b["stuck"], c["stuck"]))
P("  worst p-p by speed:")
for k in C:
    P("    %-11s " % k + " ".join("%4.1f:%.2f" % (v, worst[k][v]) for v in sorted(worst[k])))
P("  X6-type flags for r2alt vs V295+r1 (member, v, crown, pp r1, pp r2alt, weave r1, weave r2alt, chatter r2alt, fpk): %d" % len(flags))
for f in flags:
    P("    %s" % (f,))
# identity check below 8 m/s: r2alt must equal V295+r1 exactly (same noise, same code path)
ident = [(res[C[1]][j]["member"], res[C[1]][j]["v"], res[C[1]][j]["crown"]) for j in rows
         if res[C[1]][j]["v"] <= 8.0 and any(abs(res[C[1]][j][k] - res[C[2]][j][k]) > 1e-12 for k in ("pp", "r_w", "r_c", "cmd_pp"))]
P("  r2alt == V295+r1 exactly at v <= 8 m/s (paired noise): %s" % ("YES" if not ident else "NO: %s" % ident[:5]))
# ---------------- S2 curve
P("\n== S2 CURVE (ramp 2 s, hold 20 s, ramp down 2 s): hold ratio (last 5 s) | droop min | peak in | exit overshoot m/s^2 | settle s | "
  "2.0-2.7 Hz rate rms (hold) | hunt p-p in hold ==")
rows = [j for j in range(n) if res[C[0]][j]["kind"] == "S2"]
x7, x11, x8 = [], [], []
for j in rows:
    a, b, c = (res[k][j] for k in C)
    P("  %-8s v%5.1f a %.1f | hold %.3f %.3f %.3f | droop %.2f %.2f %.2f | peak %.2f %.2f %.2f | exit_os %.3f %.3f %.3f | settle %.1f %.1f %.1f | c24 %.3f %.3f %.3f | hunt %.2f %.2f %.2f | stuck %.2f %.2f %.2f" % (
        c["member"], c["v"], c["a"], a["hold"], b["hold"], c["hold"], a["hold_min"], b["hold_min"], c["hold_min"],
        a["peak_in"], b["peak_in"], c["peak_in"], a["exit_os"], b["exit_os"], c["exit_os"], a["settle"], b["settle"], c["settle"],
        a["c24"], b["c24"], c["c24"], a["hunt_pp"], b["hunt_pp"], c["hunt_pp"], a["stuck"], b["stuck"], c["stuck"]))
    if c["hold"] > 1.05 or c["peak_in"] > 1.05:
        x7.append((c["member"], c["v"], c["a"], c["hold"], c["peak_in"]))
    if (c["exit_os"] > 1.5 * b["exit_os"] and c["exit_os"] > 0.15) or (c["settle"] > 2 * b["settle"] and c["settle"] > 2.0):
        x11.append((c["member"], c["v"], c["a"], b["exit_os"], c["exit_os"], b["settle"], c["settle"]))
    if c["v"] >= 19 and b["c24"] > 0 and 20 * np.log10(max(c["c24"], 1e-9) / b["c24"]) > 3.0:
        x8.append((c["member"], c["v"], c["a"], b["c24"], c["c24"]))
P("  X7 (r2alt hold or in-curve peak > 1.05): %s" % x7)
P("  X11 (exit overshoot > 1.5x r1 and > 0.15, or settle > 2x r1 and > 2 s): %s" % x11)
P("  X8 (2.0-2.7 Hz rate in the hold > +3 dB vs V295+r1 at >= 19 m/s): %s" % x8)
# ---------------- S3 / S3P
P("\n== S3 light driver resistance 150 T for 4 s NOT flagged pressed / S3P flagged pressed: push excursion | post-release peak |la| | "
  "post-release overshoot | integrator change during the push (m/s^2) ==")
for kind in ("S3", "S3P"):
    for j in [j for j in range(n) if res[C[0]][j]["kind"] == kind]:
        a, b, c = (res[k][j] for k in C)
        P("  %-3s %-8s v%5.1f | push %.3f %.3f %.3f | post pk %.3f %.3f %.3f | post os %.3f %.3f %.3f | di %.3f %.3f %.3f" % (
            kind, c["member"], c["v"], a["push"], b["push"], c["push"], a["post_pk"], b["post_pk"], c["post_pk"],
            a["post_os"], b["post_os"], c["post_os"], a["i_at_rel"], b["i_at_rel"], c["i_at_rel"]))
# ---------------- S5
P("\n== S5 lane change (+-1.5 m/s^2 one sine, 4 s): peak in | post peak |la| | post rms (5 s) ==")
for j in [j for j in range(n) if res[C[0]][j]["kind"] == "S5"]:
    a, b, c = (res[k][j] for k in C)
    P("  %-8s v%5.1f | peak %.2f %.2f %.2f | post pk %.3f %.3f %.3f | post rms %.3f %.3f %.3f" % (
        c["member"], c["v"], a["peak_in"], b["peak_in"], c["peak_in"], a["post_pk"], b["post_pk"], c["post_pk"],
        a["post_rms"], b["post_rms"], c["post_rms"]))
open(os.path.join(HERE, "out", fn.replace(".json", "_report.txt")), "w").write("\n".join(L) + "\n")
