"""
Accord TVA EPS (39990-TVA-A160, V850) — demand-aggregator deep dive.

Emits two figures, all values instruction/byte-verified against code.bin this
session (Ghidra port 8193):

  1. accord_demand_pipeline_v2.png
        The aggregator from the DISTRIBUTOR onward: per-slot 6-state machine,
        4 clamped lanes + 3 blend gains, per-slot banks (primary + ASIL mirror),
        the mixer's cross-slot MAX/SUM reduction, final clamps, the mixed torque
        command, and the shaper/companion-term blend.

  2. accord_bottleneck_and_limit_family.png
        (LEFT)  the clamp WATERFALL for a full-scale LKAS input x=4096 — where the
                value gets cut and by which instruction/table. Answers "what is the
                first bottleneck in increasing this value".
        (RIGHT) the arbitration speed/signal LIMIT is NOT a single 1-D list. It is a
                FAMILY of LERP curves selected by a mode/gear byte (gp-0x674e). Shows
                the real cb844[0] curve read by the live code (const 15360) vs the
                0xC6534 row the old plot C used (which the arbitration never reads).

Verified anchors:
  s_lkas_process_steer_cmd  0x52676 : setpoint = clamp(STEER_TORQUE * -4, +-0x4000) -> 0xFEDF1652
  m_steer_torque_arbitration 0x28ea6: |setpoint| <= LERP(curve[mode], axis@gp-0x6a5e);
                                       8 ptr arrays 0xCB844.. ; cmd -> st.h@0x2a2ea -> 0xFEDF14C4
  m_motor_cmd_distribute_clamp 0x25c32: lanes +-0x4000/+-0x2800/+-0x384/+-0x4e20; gains <=0x400
  m_motor_cmd_mixer 0x26c80          : cross-slot MAX/SUM; clamps +-0x4e20(0x2739e)/+-0x6400(0x27772)
  FUN_00042ac6 -> 0xFEDF1502 (+-0x2800)  ;  shaper FUN_00042af8 clamp +-0x2000
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

C_BLUE, C_RED, C_ORANGE, C_GREEN, C_GREY, C_PURPLE = (
    "#1f4e79", "#c0392b", "#d4760a", "#1e7d44", "#9aa0a8", "#6c3483")

# ---------------------------------------------------------------------------
# Real decoded table bytes (this session)
# ---------------------------------------------------------------------------
# cb844[0] @ 0xE4180 : N=9 breakpoints, value row CONSTANT 15360
CB844_0_BP  = [3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320]
CB844_0_VAL = [15360] * 9
# cba74[0] @ 0xE4468 : a different 4-point curve (sharp attenuation)
CBA74_0_BP  = [70, 72, 78, 80]
CBA74_0_VAL = [254, 234, 12, 0]
# the OLD plot-C row (0xC6518 speed / 0xC6534 limit) — NOT read by arbitration
OLD_SPD = [0, 10, 25, 50, 80, 120, 200]
OLD_LIM = [12000, 10000, 10000, 7000, 7000, 7000, 7000]


# ===========================================================================
# FIGURE 1 — the aggregator pipeline (distributor -> mixer -> shaper)
# ===========================================================================
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.suptitle(
        "Accord TVA EPS — demand AGGREGATOR from the distributor onward\n"
        "39990-TVA-A160   |   all clamps/states/reductions instruction-verified in code.bin",
        fontsize=13, fontweight="bold", y=0.985)

    def box(x, y, w, h, text, fc="#eef2f6", ec=C_BLUE, lw=1.4, fs=8.2, fw="normal", tc="black"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0",
                                    fc=fc, ec=ec, lw=lw, zorder=2))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fs, fontweight=fw, color=tc, zorder=3)

    def arrow(x1, y1, x2, y2, color=C_BLUE, lw=2.0, ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                     mutation_scale=14, color=color, lw=lw, ls=ls, zorder=1,
                     shrinkA=2, shrinkB=2))

    # ---- 10 producers feeding the distributor ----
    ax.text(15, 96, "10 DEMAND PRODUCERS (slots 0-9)", ha="center", fontsize=9.5,
            fontweight="bold", color=C_BLUE)
    ax.text(15, 93.4, "each writes one cmd struct, then calls the shared distributor",
            ha="center", fontsize=7.4, color=C_GREY, style="italic")
    prod = ["slot0 0x2e52e", "slot1 0x2b422  *LKAS STEER*", "slot2 0x3405a",
            "slot3 0x2c246", "slot4 0x23ad2", "slot5 0x23fe2", "slot6 0x3aff4",
            "slot7 0x3a8a8 (idle)", "slot8 0x2caa2", "slot9 0x339cc"]
    for i, p in enumerate(prod):
        y = 90.5 - i*3.0
        steer = (i == 1)
        box(2, y-1.3, 26, 2.4, p, fc="#f7e2c0" if steer else "#eef2f6",
            ec=C_ORANGE if steer else C_GREY, lw=1.8 if steer else 0.8,
            fs=7.2, fw="bold" if steer else "normal")
        arrow(28, y, 35, 70, color=C_ORANGE if steer else C_GREY,
              lw=1.6 if steer else 0.7)

    # ---- per-producer command struct (what the distributor reads from r6) ----
    box(34, 74, 33, 12.5,
        "CMD STRUCT (r6)  passed to distributor\n"
        "+0 byte  slot index  (clamped to 0..10)\n"
        "+1 byte  STATE  (the per-slot state machine 0..5)\n"
        "+2 s16  lane A     +4 s16  lane B (TORQUE)\n"
        "+6 s16  lane C     +8 s16  lane D\n"
        "+a/+c/+e u16  blend gains (companion terms)",
        fc="#fff8ee", ec=C_ORANGE, fs=7.6, fw="normal")
    arrow(50, 74, 50, 70.5, color=C_ORANGE)

    # ---- DISTRIBUTOR ----
    box(30, 60, 40, 10,
        "DISTRIBUTOR  m_motor_cmd_distribute_clamp  (0x25c32)\n"
        "CLAMP each lane to a fixed rail (code literals):\n"
        "+2 -> +-0x4000   +4 -> +-0x2800   +6 -> +-0x384   +8 -> +-0x4e20\n"
        "blend gains +a/+c/+e -> clamped <= 0x400 (unity, Q10)\n"
        "global gate: u16@0xFEDF1656 vs per-slot threshold tp+0x50f4[slot]",
        fc="#e7eef7", ec=C_BLUE, fs=7.7, fw="bold")

    # state machine chip
    box(72, 60.5, 26, 9,
        "PER-SLOT STATE MACHINE  (byte+1)\n"
        "0 normal  1 clear/zero-lanes  2 active-write\n"
        "3 active-write  4 fault-arm  5 zero+unity-gain\n"
        "default -> hold last (gp-0x3da4)\n"
        "state recomputed from gp-0x61a0[] scans",
        fc="#f3eef7", ec=C_PURPLE, fs=7.0)
    arrow(70, 65, 72, 65, color=C_PURPLE, lw=1.2)

    arrow(50, 60, 50, 56.5)

    # ---- per-slot banks ----
    box(30, 49.5, 40, 6,
        "PER-SLOT BANKS  (11 slots x lanes)\n"
        "PRIMARY  gp-0x62e0/-0x62f8/-0x6274/-0x633c[+slot*2]   (e.g. 0xFEDF1D20)\n"
        "ASIL MIRROR  gp-0x4b70/-0x4b88/-0x4ba0/-0x4b10   gains gp-0x6230/-0x6218/-0x6200",
        fc="#eef2f6", ec=C_BLUE, fs=7.4)
    arrow(50, 49.5, 50, 46.5)

    # ---- MIXER ----
    box(28, 35.5, 44, 10.5,
        "MIXER  m_motor_cmd_mixer  (0x26c80)   run from w_steer_control_task 0x2214a\n"
        "loop slots 0..10:  per-slot STATE-route (state 1..7)\n"
        "state 4 -> gain: mul tp+0x746a; sar 0xe; clamp +-0x2800\n"
        "CROSS-SLOT REDUCTION:  running MAX on some lanes, SUM on others\n"
        "   -> accumulators gp-0x3d70..3d98\n"
        "FINAL CLAMPS:  +-0x4e20  +-0x6400  +-0x2800  +-0xe10   (each ASIL-mirrored)",
        fc="#e7eef7", ec=C_BLUE, fs=7.5, fw="bold")
    arrow(50, 35.5, 50, 32.5)

    # ---- mixed cmd ----
    box(33, 27, 34, 5,
        "MIXED TORQUE CMD   0xFEDF1502  (gp-0x6afe)\n"
        "via FUN_00042ac6 range-check +-0x2800 (else sentinel 0x7fff) ; 1 writer / 1 reader",
        fc="#f7e2c0", ec=C_ORANGE, fs=7.6, fw="bold")
    arrow(50, 27, 50, 24)

    # ---- shaper + companion terms ----
    box(30, 17.5, 40, 6,
        "SHAPER  FUN_00042af8\n"
        "blend with COMPANION TERMS (e.g. 0xFEDF309C); sign-consistency checks\n"
        "clamp +-0x2000 ; ASIL state (feeds back 0xFEDF1468 read by slot 6)",
        fc="#e7eef7", ec=C_BLUE, fs=7.4, fw="bold")
    arrow(50, 17.5, 50, 14.5)

    box(31, 9, 38, 5,
        "DEMAND STRUCT  0xFEDF16E0..16EA  (tag 0x38c7, FUN_0004613e)\n"
        "-> serializer FUN_000564ce -> CSIG0 clocked-serial dispatch",
        fc="#eef2f6", ec=C_BLUE, fs=7.5)

    # downstream note
    box(74, 9, 24, 8,
        "GAP 2 (sharpened)\n"
        "principal cmd routes to a\n"
        "SERIAL FRAME; no st to the\n"
        "gp-0x2bf0 FOC q-ref found.\n"
        "on-chip FOC handoff NOT proven.",
        fc="#fdf0ee", ec=C_RED, fs=7.0, tc=C_RED)
    arrow(69, 11.5, 74, 12, color=C_GREY, lw=1.8, ls=(0, (5, 4)))

    leg = [Line2D([0], [0], color=C_BLUE, lw=2.4, label="verified data flow [V]"),
           Line2D([0], [0], color=C_ORANGE, lw=2.4, label="steering-torque carrier / struct"),
           Line2D([0], [0], color=C_PURPLE, lw=2.4, label="per-slot state machine"),
           Line2D([0], [0], color=C_GREY, lw=2.0, ls="--", label="NOT statically proven")]
    ax.legend(handles=leg, loc="lower left", fontsize=7.8, framealpha=0.95,
              bbox_to_anchor=(0.005, 0.005))

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = "accord_demand_pipeline_v2.png"
    plt.savefig(out, dpi=140, bbox_inches="tight"); print("wrote", out)
    plt.close(fig)


# ===========================================================================
# FIGURE 2 — bottleneck waterfall + the limit-curve FAMILY
# ===========================================================================
def fig_bottleneck():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(16, 7.2))
    fig.suptitle(
        "Accord TVA EPS — where a full-scale LKAS input (x=4096) gets capped, and why the\n"
        "arbitration speed/signal limit is a FAMILY of curves, not a single speed->torque list",
        fontsize=12.5, fontweight="bold", y=0.99)

    # ---- LEFT: clamp waterfall --------------------------------------------
    stages = [
        ("CAN STEER_TORQUE\n|x| = 4096", 4096, "raw count", C_GREY),
        ("x * -4\n(s_lkas 0x52676)", 16384, "0x4000", C_BLUE),
        ("clamp +-0x4000\n(s_lkas 0x52676)  FIRST WALL", 16384, "0x4000  (exactly on rail)", C_RED),
        ("arb limit  |sp|<=LERP\ncb844[0] const  (0x28ea6)", 15360, "0x3c00  FIRST data-driven cut", C_ORANGE),
        ("distributor +4 lane\n+-0x2800  (0x25c32)", 10240, "0x2800", C_BLUE),
        ("mixer torque clamp\n+-0x2800  (0x26c80)", 10240, "0x2800", C_BLUE),
        ("shaper clamp +-0x2000\n(0x42af8)  TIGHTEST", 8192, "0x2000  binding wall", C_GREEN),
    ]
    y = np.arange(len(stages))[::-1]
    vals = [s[1] for s in stages]
    cols = [s[3] for s in stages]
    axL.barh(y, vals, color=cols, edgecolor="black", lw=0.8, height=0.62, alpha=0.85)
    for yi, s in zip(y, stages):
        axL.text(s[1] + 250, yi, f"{s[1]}  ({s[2]})", va="center", fontsize=8, color="black")
        axL.text(-300, yi, s[0], va="center", ha="right", fontsize=7.6, fontweight="bold")
    axL.axvline(16384, color=C_RED, ls=":", lw=1, alpha=0.5)
    axL.set_xlim(0, 23000); axL.set_ylim(-0.6, len(stages)-0.4)
    axL.set_yticks([]); axL.set_xlabel("torque-command magnitude (counts)")
    axL.set_title("CLAMP WATERFALL for x=4096  —  descending staircase of caps", fontsize=10)
    axL.text(0.98, 0.02,
             "x*-4 lands a full-scale input EXACTLY on the +-0x4000 rail.\n"
             "First DATA-driven cut = arbitration limit table (mode-dependent).\n"
             "Tightest final wall = shaper +-0x2000 = 8192.",
             transform=axL.transAxes, fontsize=7.6, ha="right", va="bottom",
             bbox=dict(boxstyle="round,pad=0.4", fc="#f4f7fb", ec=C_GREY))
    axL.grid(alpha=0.2, axis="x")

    # ---- RIGHT: the limit FAMILY ------------------------------------------
    axR.set_title("Arbitration limit = a FAMILY of LERP curves (selected by mode/gear @gp-0x674e)",
                  fontsize=10)
    # real curve cb844[0] (constant 15360) on its own breakpoint axis
    axR.plot(CB844_0_BP, CB844_0_VAL, color=C_ORANGE, lw=2.6, marker="o", ms=4,
             label="LIVE: cb844[0]@0xE4180 (const 15360)")
    axR.fill_between(CB844_0_BP, 0, CB844_0_VAL, color=C_ORANGE, alpha=0.06)
    # the OLD plot-C row, drawn on the SAME x for contrast (its native axis is km/h, so annotate)
    axR.plot(OLD_SPD, OLD_LIM, color=C_GREY, lw=1.8, ls="--", marker="s", ms=4,
             label="OLD plot C: 0xC6534 (NOT read by arbitration)")
    # illustrative sibling curves to convey "family" (schematic shapes on the cb844 axis)
    bp = np.array(CB844_0_BP)
    for frac, lab in [(0.72, "mode 1 (illustrative)"), (0.5, "mode 2 (illustrative)")]:
        axR.plot(bp, np.full_like(bp, 15360*frac), color=C_BLUE, lw=1.0, ls=(0, (2, 2)), alpha=0.55)
    axR.text(bp[-1], 15360*0.72, " other modes:\n same table shape,\n different value rows",
             fontsize=7, color=C_BLUE, va="center")
    axR.axhline(16384, color=C_RED, ls=":", lw=1)
    axR.text(bp[0], 16384, " incoming setpoint = 16384 (on the -0x4000 rail)",
             fontsize=7.5, color=C_RED, va="bottom")
    axR.set_xlabel("LERP axis (uVar20 @gp-0x6a5e; cb844 breakpoints 3200..8320)  /  km/h for the dashed row")
    axR.set_ylabel("|torque setpoint| limit  (counts)")
    axR.set_ylim(0, 18000)
    axR.legend(fontsize=7.6, loc="lower right")
    axR.grid(alpha=0.25)
    axR.text(0.02, 0.04,
             "8 pointer arrays (0xCB844/CBA74/CB924/C9A88/CB7D4/CBB54/CBC34/CBAE4).\n"
             "mode/gear byte picks ONE curve; a 2nd selector (axis<32000) blends a hi/lo pair.\n"
             "=> plot C's single speed->limit list is a SLICE of this family, and from a table\n"
             "   the live arbitration does not even read.",
             transform=axR.transAxes, fontsize=7.4, ha="left", va="bottom",
             bbox=dict(boxstyle="round,pad=0.4", fc="#fff8ee", ec=C_ORANGE))

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    out = "accord_bottleneck_and_limit_family.png"
    plt.savefig(out, dpi=140, bbox_inches="tight"); print("wrote", out)
    plt.close(fig)


if __name__ == "__main__":
    fig_pipeline()
    fig_bottleneck()
