"""
Accord TVA EPS (39990-TVA-A160) — the steering/torque demand AGGREGATOR pipeline.

Shows how 10 demand producers feed one shared distributor + mixer, and how the
mixed command flows forward toward the motor. Built from Ghidra disassembly of
FUN_00025c32 (distributor), FUN_00026c80 (mixer), and the forward chain
0x42ac6 -> 0xFEDF1502 -> 0x42af8 -> 0x4613e -> 0x564ce -> 0x16de6.

Trust:  solid box/arrow = instruction/decompile-verified [V]
        dashed grey     = not statically proven (sharpened GAP 2)
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

C_BLUE, C_RED, C_ORANGE, C_GREEN, C_GREY = "#1f4e79", "#c0392b", "#d4760a", "#1e7d44", "#9aa0a8"
plt.rcParams.update({"font.size": 8.5})

fig, ax = plt.subplots(figsize=(15.5, 10.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
fig.suptitle("Accord TVA EPS — steering/torque DEMAND AGGREGATOR pipeline (10 producers -> mixer -> motor)\n"
             "39990-TVA-A160   |   solid = disasm-verified [V]   dashed grey = not statically proven",
             fontsize=12.5, fontweight="bold", y=0.985)

def box(x, y, w, h, text, fc="#eef2f6", ec=C_BLUE, lw=1.4, fs=8.5, fw="normal", tc="black", style="round"):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"{style},pad=0.3,rounding_size=1.2",
                       fc=fc, ec=ec, lw=lw, zorder=2)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight=fw, color=tc, zorder=3)
    return (x + w / 2, y, x + w / 2, y + h)  # (cx, ybot, cx, ytop)

def arrow(x1, y1, x2, y2, color=C_BLUE, lw=2.0, ls="-", style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=15, color=color, lw=lw, ls=ls, zorder=1,
                 shrinkA=2, shrinkB=2))

# ---- The 10 producers / demand vector (left sidebar table) -----------------
slots = [
    ("0", "FUN_0002e52e", "0xFEDF14E6", "+4"),
    ("1", "FUN_0002b422  *STEER*", "0xFEDF14C4", "+4"),
    ("2", "FUN_0003405a", "0xFEDF148A/88", "+2&+4"),
    ("3", "FUN_0002c246", "tbl 0xC7090", "+4"),
    ("4", "FUN_00023ad2", "0xFEDF1498", "+4"),
    ("5", "FUN_00023fe2", "0xFEDF1470", "+4"),
    ("6", "FUN_0003aff4", "float interp", "+8"),
    ("7", "FUN_0003a8a8", "(idle/clear)", "none"),
    ("8", "FUN_0002caa2", "0xFEDF14EE", "+4"),
    ("9", "FUN_000339cc", "0xFEDF1494+acc", "+4"),
]
ax.text(15, 95, "DEMAND VECTOR  (RAM 0xFEDF1468..15A2)  +  10 producers",
        ha="center", fontsize=9.2, fontweight="bold", color=C_BLUE)
ax.text(15, 92.3, "task 0x2214a: slots 1,6,7,8,9     task 0x22ca0: slots 0,2,3,4,5",
        ha="center", fontsize=7.3, color=C_GREY, style="italic")
row_h = 6.0
y0 = 88
for i, (sid, fn, src, lane) in enumerate(slots):
    y = y0 - i * row_h
    is_steer = (sid == "1")
    fc = "#f7e2c0" if is_steer else "#eef2f6"
    ec = C_ORANGE if is_steer else C_BLUE
    box(2, y - row_h + 0.8, 26, row_h - 1.1,
        f"slot {sid}   {fn}\nsrc {src}      lane {lane}",
        fc=fc, ec=ec, lw=1.8 if is_steer else 1.0, fs=7.4,
        fw="bold" if is_steer else "normal")
    # converging arrow into the distributor
    arrow(28, y - row_h / 2 + 0.3, 38, 64, color=ec if is_steer else C_GREY,
          lw=1.6 if is_steer else 0.8)

# ---- Central vertical spine ------------------------------------------------
cx = 50
dist = box(38, 60, 24, 7,
           "DISTRIBUTOR  FUN_00025c32\nclamp 4 lanes (+2 0x4000 / +4 0x2800 / +6 0x384 / +8 0x4e20)\nwrite per-slot record (idx +0)",
           fc="#e7eef7", ec=C_BLUE, fs=7.6, fw="bold")
banks = box(38, 50.5, 24, 6,
            "PER-SLOT BANKS\nprimary gp-0x62xx  +  ASIL mirror gp-0x4bxx\n(11 slots x lanes)",
            fc="#eef2f6", ec=C_BLUE, fs=7.5)
mixer = box(35, 39, 30, 8.5,
            "MIXER  FUN_00026c80\nper-slot STATE-ROUTE (state 1..7)  ->  cross-slot MAX / SUM\n"
            "final clamps +/-0x4e20 / +/-0xe10 / +/-0x2800 / +/-0x6400\n(each ASIL-mirrored via FUN_0006b9fa)",
            fc="#e7eef7", ec=C_BLUE, fs=7.5, fw="bold")
out1 = box(39, 31, 22, 5.5,
           "0xFEDF1502  (gp-0x6afe)\nmixed torque cmd,  +/-0x2800\n(via FUN_00042ac6)",
           fc="#f7e2c0", ec=C_ORANGE, fs=7.6, fw="bold")
shaper = box(36, 22.5, 28, 6,
             "SHAPER  FUN_00042af8\nblend companion terms (0xFEDF309C ...),\nclamp +/-0x2000, ASIL state",
             fc="#e7eef7", ec=C_BLUE, fs=7.6, fw="bold")
struct = box(37, 14.5, 26, 5.5,
             "DEMAND STRUCT  0xFEDF16E0..16EA  (tag 0x38c7)\nFUN_0004613e",
             fc="#eef2f6", ec=C_BLUE, fs=7.6)
ser = box(35, 6.5, 30, 5.5,
          "SERIALIZER  FUN_000564ce  (BE-pack -> TX frame +0xA..+0x13)\n"
          "dispatch FUN_00016de6  ->  CSIG0 clocked-serial",
          fc="#eef2f6", ec=C_BLUE, fs=7.5)

arrow(50, 60, 50, 56.5)      # dist -> banks
arrow(50, 50.5, 50, 47.5)    # banks -> mixer
arrow(50, 39, 50, 36.5)      # mixer -> out1
arrow(50, 31, 50, 28.5)      # out1 -> shaper
arrow(50, 22.5, 50, 20)      # shaper -> struct
arrow(50, 14.5, 50, 12)      # struct -> serializer

# ---- Downstream FOC / PWM (verified-as-motor) + the unproven link ----------
foc = box(72, 33, 25, 7,
          "on-chip FOC  FUN_00071272\nPark/Clarke/PI/SVPWM  (ADC ISR 0x6404c)",
          fc="#eef7ee", ec=C_GREEN, fs=7.6, fw="bold")
pwm = box(72, 23.5, 25, 6.5,
          "TSG20 PWM  FUN_0006c5ce\nCMPU/V/W 0xFFFFCCB0/B4/B8  =  MOTOR",
          fc="#eef7ee", ec=C_GREEN, fs=7.6, fw="bold")
arrow(84.5, 33, 84.5, 30)    # foc -> pwm (verified motor drive)

# the unproven handoff: serialized frame / mixer output ==?=> FOC q-ref
arrow(65, 9.3, 84, 33, color=C_GREY, lw=2.0, ls=(0, (5, 4)))
ax.text(78, 17.5, "GAP 2 (sharpened)\nno st to gp-0x2bf0/-0x2be0 q-ref found;\n"
        "principal cmd routes to a serial frame\n-> on-chip FOC handoff NOT proven",
        ha="center", va="center", fontsize=7.2, color=C_RED, style="italic",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fdf0ee", ec=C_RED, lw=1.0))

# legend
leg = [Line2D([0], [0], color=C_BLUE, lw=2.2, label="verified flow [V]"),
       Line2D([0], [0], color=C_ORANGE, lw=2.2, label="steering-torque carrier"),
       Line2D([0], [0], color=C_GREEN, lw=2.2, label="on-chip FOC/PWM (drives motor, per doc)"),
       Line2D([0], [0], color=C_GREY, lw=2.0, ls="--", label="NOT statically proven")]
ax.legend(handles=leg, loc="lower left", fontsize=7.6, framealpha=0.95,
          bbox_to_anchor=(0.005, 0.005))

plt.tight_layout(rect=[0, 0, 1, 0.95])
out = "demand_aggregator_pipeline.png"
plt.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)
