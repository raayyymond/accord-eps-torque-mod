# -*- coding: utf-8 -*-
"""f1: positive controls for fc_lib before any candidate is scored.
  (a) VecPort with r1 rows == the harness's own ForkPort, bit for bit, in closed loop (V294 and V295 cells, nominal and
      light_b, dist lp): max |d| over ang / cmd / p / i / f.
  (b) V294 + r1 under lp on nominal reproduces the harness report's retrodiction row
      (tracking .840 / .865 / .586 / .764 / .917; turn-hold - / .780 / .592 / .636 / .940).
  (c) runtime of one batch, to size the sweep."""
import sys, time, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

c294 = H.Cells.v294()
c295 = F.cells_v295()
members = ["nominal", "light_b"]
ch = H.route_chunks()

t0 = time.time()
Rref = H.simulate([c294.replace(name="a"), c295.replace(name="b")], [H.family()[m] for m in members], ch,
                  H.SimOpts(mode="B", dist="lp", null_shadow=False))
t_ref = time.time() - t0
t0 = time.time()
R, idx = F.sim([(c294, F.R1), (c295, F.Fork("r1b"))], members, ch, dist="lp")
t_mine = time.time() - t0
dev = {k: float(np.max(np.abs(R[k] - Rref[k]))) for k in ("ang", "cmd", "p", "i", "f", "T", "la_act")}
print("(a) VecPort(r1) vs harness ForkPort, closed loop, %d lanes: max|d| %s" % (R["ang"].shape[0], dev))
assert all(v == 0.0 for v in dev.values()), "VecPort is not bit-identical to the harness port"
print("    PASS: bit-identical")
print("(c) runtime: harness %.1f s, fc_lib %.1f s for %d lanes" % (t_ref, t_mine, R["ang"].shape[0]))

m = F.metrics(R, idx[("r1", "nominal")])
row = {b: (round(m[b]["track_gain"], 3), round(m[b]["turn_hold"], 3) if np.isfinite(m[b]["turn_hold"]) else None)
       for b in ("0-5", "5-10", "10-15", "15-22", "22+")}
print("(b) V294+r1 lp nominal: tracking/turn-hold by band:", row)
want_tg = {"0-5": .840, "5-10": .865, "10-15": .586, "15-22": .764, "22+": .917}
for b, w in want_tg.items():
    assert abs(m[b]["track_gain"] - w) < 0.0015, (b, m[b]["track_gain"], w)
print("    PASS: matches the harness report to 3 decimals")
m5 = F.metrics(R, idx[("r1b", "nominal")])
print("    V295+r1 lp nominal:", {b: (round(m5[b]["track_gain"], 3), round(m5[b]["turn_hold"], 3)) for b in want_tg})
for mem in members:
    a = F.metrics(R, idx[("r1", mem)]); b = F.metrics(R, idx[("r1b", mem)])
    print("   %-8s V294 vs V295 (r1): lc %s / %s" % (mem, {k: round(v, 2) for k, v in a["limit_cycle"].items()},
                                                   {k: round(v, 2) for k, v in b["limit_cycle"].items()}))
    for band in want_tg:
        print("      %-6s trk %.3f/%.3f hold %.3f/%.3f s13 %.3f/%.3f s03 %.3f/%.3f hard16 %.2f/%.2f J %.3f/%.3f str %.3f/%.3f ish %.3f/%.3f"
              % (band, a[band]["track_gain"], b[band]["track_gain"], a[band]["turn_hold"], b[band]["turn_hold"],
                 a[band]["s13"], b[band]["s13"], a[band]["s03"], b[band]["s03"], a[band]["hard16"], b[band]["hard16"],
                 a[band]["J_err"], b[band]["J_err"], a[band]["straight_delivery"], b[band]["straight_delivery"],
                 a[band]["i_share"], b[band]["i_share"]))
