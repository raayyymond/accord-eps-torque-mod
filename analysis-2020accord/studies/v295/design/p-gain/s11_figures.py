# -*- coding: utf-8 -*-
"""s11_figures.py -- p-gain lens figures (static PNGs for the report; the close-out artifact is the orchestrator's).
Every curve is READ from the golden model / harness on the candidate cells, never retyped:
  fig1_kp_lerp.png       Kp(idx) LERP, V294 vs the recommendation, with r71b's operating points (s2 census) marked
  fig2_surface.png       delivered steady torque T vs 0xE4 command, V294 vs recommendation (golden march, fb = 0)
  fig3_ratios.png        static ratio and local-slope ratio vs idx (both "x V294", one axis)
  fig4_outer_lightb.png  outer-loop Ms on light_b at the band operating points: V294 / flat x1.3 / map x1.3 / rec
ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
C1, C2, C3, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8a85"
INK, INK2 = "#1a1a19", "#5f5e58"


def style(ax, title, xl, yl):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.set_xlabel(xl, color=INK2)
    ax.set_ylabel(yl, color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c0")
    ax.tick_params(colors=INK2)
    ax.grid(True, color="#ecebe4", lw=0.8)


def main(rec_name="R1.3_8_100"):
    from s8_finalists import finalists
    base, F = finalists()
    rec = {c.name: c for c in F}[rec_name]
    idx = np.arange(241)
    kp0, kp1 = H.lerp_table(base.kp_x, base.kp_y, 241), H.lerp_table(rec.kp_x, rec.kp_y, 241)
    ops = [("straights >=10 m/s", 5, 7), ("hold 22+", 16, 23), ("hold 15-22 / 10-15", 29, 39), ("hold 5-10", 43, 55),
           ("hard turns 5-10", 65, 92)]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, (lab, a, b) in enumerate(ops):
        ax.axvspan(a, b, color=GRAY, alpha=0.10 + 0.04 * (i % 2), lw=0)
        ax.text((a + b) / 2, 1330, lab, ha="center", va="bottom", fontsize=7, color=INK2, rotation=90)
    ax.plot(idx, kp0, color=C1, lw=2, label="V294 (960 flat)")
    ax.plot(idx, kp1, color=C2, lw=2, label="%s  X %s  Y %s" % (rec.name, list(rec.kp_x), list(rec.kp_y)))
    ax.plot(rec.kp_x, rec.kp_y, "o", color=C2, ms=6)
    ax.set_ylim(800, 1500)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style(ax, "Kp LERP 0xCB994 (all 28 records) vs demand index - shaded: where r71b drove", "demand index idx (16.13 wire counts / LSB)",
          "Kp (P = E*Kp >> 8)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_kp_lerp.png"), dpi=130)
    plt.close(fig)
    S0, S1 = G.surface_table(base), G.surface_table(rec)
    w = idx * H.WIRE_PER_IDX
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(w, S0, color=C1, lw=2, label="V294")
    ax.plot(w, S1, color=C2, lw=2, label=rec.name)
    ax.axhline(2461, color=GRAY, lw=1, ls="--")
    ax.text(50, 2480, "rail 2461 (P clamp) - unchanged", fontsize=8, color=INK2)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style(ax, "Delivered steady torque vs command (golden-model march, wheel still, no driver)", "0xE4 command (wire counts)",
          "T at the 427 tap (T counts)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_surface.png"), dpi=130)
    plt.close(fig)
    ii = np.arange(1, 231)
    ratio = S1[ii] / np.maximum(S0[ii], 1)
    ls = np.array([G.local_slope(rec, i) / G.local_slope(base, i) for i in ii])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(ii, ratio, color=C2, lw=2, label="static ratio T/T_V294 (= Kp(idx)/960; what closes the hold)")
    ax.plot(ii, ls, color=C3, lw=2, label="local-slope ratio dT/dwire (the fork's small-signal loop gain)")
    ax.plot(ii, kp1[ii] / 960.0, color=GRAY, lw=1, ls=":", label="trim ratio Kp(idx)/960 (acceleration feedback)")
    ax.axhline(1.0, color=C1, lw=1)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    style(ax, "%s relative to V294, by demand index" % rec.name, "demand index idx", "x V294")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_ratios.png"), dpi=130)
    plt.close(fig)
    try:
        O = json.load(open(os.path.join(OUT, "s12_outer_final.json")))
        labs = [k for k in O["labels"]]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        names = O["names"]
        cols = [C1, GRAY, C3, C2]
        wbar = 0.8 / len(names)
        for k, nm in enumerate(names):
            ax.bar(np.arange(len(labs)) + (k - (len(names) - 1) / 2) * wbar, O["Ms_light_b"][nm], width=wbar * 0.92,
                   color=cols[k % 4], label=nm)
        ax.set_xticks(np.arange(len(labs)))
        ax.set_xticklabels(labs, rotation=30, ha="right", fontsize=7)
        ax.legend(frameon=False, fontsize=8)
        style(ax, "Outer-loop peak sensitivity Ms on light_b (the pessimistic prior), fork r1 unchanged", "", "Ms")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "fig4_outer_lightb.png"), dpi=130)
        plt.close(fig)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main(*(sys.argv[1:2]))
