"""
Accord TVA EPS (39990-TVA-A160) — "plot C" split by mode/gear.

The original plot C drew ONE speed->limit curve. The live arbitration
(m_steer_torque_arbitration 0x28ea6) actually indexes its curves by the
mode/gear byte @ gp-0x674e, so each curve is a FAMILY of slices.

This figure splits plot C into 3 mode/gear slices (mode 0,1,2), for the TWO
arbitration curve families that matter, with the real bytes read from code.bin:

  TOP ROW  g_pArbSetpointLimitCurves (0xCB844)  = the HARD setpoint magnitude
           limit clamped onto |setpoint|.  VERIFIED: all 12 gear slots are
           byte-identical (entries 6-11 are a 0x1000 block-mirror of 0-5), so
           the three slices COINCIDE -> this limit is mode/gear-invariant.

  BOTTOM ROW  g_pArbCurve_c9a88 (0xC9A88)  = a mode/gear-dependent torque
           shaping curve (indexed by a 0..255 byte).  VERIFIED: the three gear
           slices DIFFER -> here is where the "set of functions" really lives.

So plot C is a slice of a family: structurally a set of functions per gear; for
the hard clamp the data fills every gear the same, for the shaping curve it does not.
"""

import numpy as np
import matplotlib.pyplot as plt

C_BLUE, C_RED, C_ORANGE, C_GREEN, C_GREY = "#1f4e79", "#c0392b", "#d4760a", "#1e7d44", "#9aa0a8"
MODE_COL = ["#c0392b", "#1e7d44", "#6c3483"]

# ---- verified bytes (code.bin, port 8193, this session) -------------------
# cb844[mode] @ 0xE4180 + mode*0x28 : identical for all 12 gear slots
CB844_BP  = [3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320]
CB844_VAL = [15360] * 9                      # constant value row

# c9a88[mode] @ 0xE4000 + mode*0x2C : same breakpoint axis, DIFFERENT value rows
C9A88_BP   = [0, 12, 20, 24, 32, 64, 96, 128, 160, 240]
C9A88_VAL = {
    0: [0, 16, 28, 34, 48, 92, 124, 148, 162, 172],
    1: [0, 24, 42, 50, 62, 100, 126, 154, 166, 172],
    2: [0, 11, 26, 35, 56, 129, 158, 172, 174, 180],
}
GEARLBL = {0: "mode/gear 0", 1: "mode/gear 1", 2: "mode/gear 2"}

fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex="row")
fig.suptitle(
    "Accord TVA EPS — \"plot C\" split into 3 mode/gear slices  (arbitration FUN_00028ea6)\n"
    "TOP: hard setpoint limit g_pArbSetpointLimitCurves(0xCB844) — identical every gear   |   "
    "BOTTOM: shaping curve g_pArbCurve_c9a88(0xC9A88) — differs by gear",
    fontsize=12.5, fontweight="bold", y=0.99)

# ---- TOP ROW : cb844 setpoint limit (mode-invariant) ----------------------
for m in range(3):
    ax = axes[0, m]
    ax.plot(CB844_BP, CB844_VAL, color=MODE_COL[m], lw=2.6, marker="o", ms=5)
    ax.fill_between(CB844_BP, 0, CB844_VAL, color=MODE_COL[m], alpha=0.07)
    ax.axhline(16384, color=C_GREY, ls=":", lw=1)
    ax.text(CB844_BP[0], 16384, " incoming |setpoint| = 16384 (-0x4000 rail)",
            fontsize=7, color=C_GREY, va="bottom")
    ax.text(CB844_BP[-1], 15360, " 15360\n (0x3c00)", fontsize=8, color=MODE_COL[m],
            va="center", fontweight="bold")
    ax.set_title(f"cb844[{m}]  @ 0xE4180+{m}*0x28   ({GEARLBL[m]})", fontsize=9.5)
    ax.set_xlabel("LERP axis  (gp-0x6a5e; bp 3200..8320)")
    if m == 0:
        ax.set_ylabel("|torque setpoint| LIMIT  (counts)")
    ax.set_ylim(0, 18000); ax.grid(alpha=0.25)
axes[0, 1].text(0.5, 0.08,
                "ALL 12 gear slots byte-identical (verified) -> these 3 slices COINCIDE.\n"
                "The hard setpoint limit does NOT depend on mode/gear.",
                transform=axes[0, 1].transAxes, ha="center", va="bottom", fontsize=8,
                color=C_RED, bbox=dict(boxstyle="round,pad=0.4", fc="#fdf0ee", ec=C_RED))

# ---- BOTTOM ROW : c9a88 shaping curve (mode-varying) ----------------------
for m in range(3):
    ax = axes[1, m]
    # faint: the other two modes for contrast
    for mm in range(3):
        if mm != m:
            ax.plot(C9A88_BP, C9A88_VAL[mm], color=C_GREY, lw=1.0, ls=(0, (2, 2)), alpha=0.5)
    ax.plot(C9A88_BP, C9A88_VAL[m], color=MODE_COL[m], lw=2.6, marker="o", ms=5,
            label=f"gear {m}")
    ax.fill_between(C9A88_BP, 0, C9A88_VAL[m], color=MODE_COL[m], alpha=0.07)
    ax.set_title(f"c9a88[{m}]  @ 0xE4000+{m}*0x2C   ({GEARLBL[m]})", fontsize=9.5)
    ax.set_xlabel("LERP axis  (0..255 byte;  bp 0..240)")
    if m == 0:
        ax.set_ylabel("shaping output")
    ax.set_ylim(0, 200); ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5, loc="upper left")
axes[1, 1].text(0.5, 0.04,
                "Same breakpoint axis, DIFFERENT value rows per gear (verified) ->\n"
                "this is the real \"set of functions\": each gear is its own curve.",
                transform=axes[1, 1].transAxes, ha="center", va="bottom", fontsize=8,
                color=C_GREEN, bbox=dict(boxstyle="round,pad=0.4", fc="#eef7ee", ec=C_GREEN))

plt.tight_layout(rect=[0, 0, 1, 0.94])
out = "accord_plotC_by_mode.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)
