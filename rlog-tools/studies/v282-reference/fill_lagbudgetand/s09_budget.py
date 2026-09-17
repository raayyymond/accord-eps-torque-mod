"""The deliverable: lag budget table (events and cells) + stacked figure.
gap components vs V282: shaping = model->setpoint; loop = setpoint->la_act (controller + EPS/plant + round trip);
vehicle = la_act->la_pose; total = model->la_pose; lead = the plan-lead difference (liveDelay_T - 0.20) that the COMMON
lead removes (total_common = total - lead)."""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

E = json.load(open("s06_events.json"))["results"]
C = json.load(open("s04_cells.json"))
LD = {"T64": 0.299, "T64B": 0.306, "T64+T64B": 0.302, "T5": 0.286, "T4": 0.280, "V282old": 0.20}
lines = ["# EVENTS (matched high-desired-jerk, s2 matcher): median paired gap vs V282, s  [route-2-sided 95% CI]",
         f"{'group':9s}{'speed':7s}{'pairs':>6s} | {'shaping':>20s} | {'loop+plant+RT':>20s} | {'vehicle':>20s} | {'TOTAL logged':>20s} | {'lead':>6s} | {'TOTAL common':>20s}"]
ev_tab = {}
for g in ["T64", "T64B", "T64+T64B", "T5", "T4", "V282old"]:
    for sn in [">=8", "8-15", "15-22", ">=22"]:
        d = E[g][sn]
        f = lambda k: f"{d[k]['med']:+.3f}[{d[k]['ci_rt2'][0]:+.2f},{d[k]['ci_rt2'][1]:+.2f}]"
        lead = LD[g] - 0.20
        lines.append(f"{g:9s}{sn:7s}{d['n_pairs']:6d} | {f('lag_x_sp'):>20s} | {f('lag_sp_act'):>20s} | {f('lag_act_pose'):>20s} | {f('lag_x_pose'):>20s} | {lead:+.3f} | {f('lag_xc_pose'):>20s}")
        ev_tab[(g, sn)] = dict(shaping=d["lag_x_sp"]["med"], loop=d["lag_sp_act"]["med"], vehicle=d["lag_act_pose"]["med"],
                               total=d["lag_x_pose"]["med"], common=d["lag_xc_pose"]["med"], lead=lead, n=d["n_pairs"])
lines.append("\n# CELLS (speed x band x demand tercile, phase lag at the power-weighted frequency): gap vs V282, s [hier. bootstrap CI]; pred = transfer-function shaping gap")
lines.append(f"{'group':6s}{'speed':6s}{'band':9s}{'terc':5s} | {'shaping (pred)':>27s} | {'loop+plant+RT':>20s} | {'vehicle':>20s} | {'TOTAL logged':>20s} | {'TOTAL common':>20s}")
for g in ["T64", "T64B", "T5", "T4", "V282old"]:
    for c in C:
        if c["group"] != g or c["band"].startswith("0.05") or c["vb"] == "2-8":
            continue
        f = lambda k: f"{c[k+'_gap']:+.3f}[{c[k+'_gap_ci'][0]:+.2f},{c[k+'_gap_ci'][1]:+.2f}]"
        lines.append(f"{g:6s}{c['vb']:6s}{c['band']:9s}{c['terc']:5s} | {f('model->setpoint'):>20s}({c['pred_shaping_gap']:+.3f}) | {f('setpoint->la_act'):>20s} | {f('la_act->la_pose'):>20s} | {f('model->la_pose'):>20s} | {f('COMMON model->la_pose'):>20s}")
open("s09_budget.txt", "w").write("\n".join(lines))
print("\n".join(lines[:30]))

# ---- figure: events, stacked components per group x speed, with the lead credit as a negative bar and total markers
col = dict(shaping="#2a78d6", loop="#eb6834", vehicle="#1baf7a", lead="#8a8984")
groups = ["T64", "T64B", "T5", "T4", "V282old"]
fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), sharey=True)
for ax, sn in zip(axes, [">=8", "8-15", "15-22", ">=22"]):
    for i, g in enumerate(groups):
        d = ev_tab[(g, sn)]
        pos = 0.0; neg = 0.0
        for k in ("shaping", "loop", "vehicle"):
            v = d[k]
            if v >= 0:
                ax.bar(i, v, bottom=pos, color=col[k], width=0.62, edgecolor="white", linewidth=2); pos += v
            else:
                ax.bar(i, v, bottom=neg, color=col[k], width=0.62, edgecolor="white", linewidth=2); neg += v
        ax.bar(i + 0.36, -d["lead"], width=0.14, color=col["lead"], edgecolor="white", linewidth=1)
        ax.plot(i, d["total"], marker="D", ms=8, color="#0b0b0b", zorder=5)
        ax.plot(i, d["common"], marker="o", ms=8, mfc="white", mec="#0b0b0b", zorder=5)
        ax.text(i, -0.17, f"n={d['n']}", ha="center", fontsize=8, color="#52514e")
    ax.axhline(0, color="#52514e", lw=0.8)
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(groups, fontsize=9)
    ax.set_title(f"matched jerk events, {sn} m/s", fontsize=10)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[0].set_ylabel("lag gap vs V282 (s), median paired")
axes[0].set_ylim(-0.2, 0.5)
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
fig.legend(handles=[Patch(color=col["shaping"], label="shaping: model->setpoint (AccordRefFilter + jerk LP)"),
                    Patch(color=col["loop"], label="loop+plant+round trip: setpoint->la_act"),
                    Patch(color=col["vehicle"], label="vehicle: la_act->la_pose"),
                    Patch(color=col["lead"], label="plan-lead credit (liveDelay - 0.20), removed by common lead"),
                    Line2D([], [], marker="D", color="#0b0b0b", ls="", label="total model->la_pose, logged lead"),
                    Line2D([], [], marker="o", mfc="white", mec="#0b0b0b", ls="", label="total, common lead")],
           loc="lower center", ncol=3, fontsize=8.5, frameon=False)
fig.suptitle("Torque-mode lag budget vs V282 on matched high-jerk events (medians; components need not sum exactly)", fontsize=11)
fig.tight_layout(rect=(0, 0.12, 1, 0.95))
fig.savefig("fig_lag_budget_events.png", dpi=130)
print("figure written")
