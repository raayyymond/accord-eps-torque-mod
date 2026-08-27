"""
Visualize how a LKAS STEER_TORQUE command x = 4096 (full-scale, CAN 0xE4)
is transformed into a motor torque/current reference and finally TSG20 PWM,
for the 2020 Accord TVA EPS (39990-TVA-A160).

Source of truth: analysis-2020accord/notes/TORQUE_PATH_AND_TABLE.md (sections 0.5, 0.3, 1).
Trust markers per panel title:
  [V]   instruction/byte-verified in disasm
  [LK]  structurally strong but role not pinned to a live read

** SUPERSEDED IN PART 2026-05-25 (§0.6) ** Panel C here uses the 0xC6534 speed->limit
row, which the arbitration code does NOT read. The live LKAS setpoint limit is the
mode/gear-indexed 0xE4xxx LERP family. For the corrected limit + the x=4096 bottleneck
chain see accord_bottleneck_and_limit_family.png; for plot C split by mode/gear see
accord_plotC_by_mode.png (generators: accord_aggregator_analysis.py, accord_plotC_by_mode.py).
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

X_IN = 4096                      # full-scale STEER_TORQUE (int16 BE bytes[0:1])
C_BLUE   = "#1f4e79"
C_RED    = "#c0392b"
C_GREEN  = "#1e7d44"
C_GREY   = "#888888"
C_ORANGE = "#d4760a"

plt.rcParams.update({
    "font.size": 9,
    "axes.titlesize": 9.5,
    "axes.titleweight": "bold",
    "figure.dpi": 130,
})

fig, axes = plt.subplots(2, 3, figsize=(15.5, 8.6))
fig.suptitle(
    "Accord TVA EPS — transformation of a full-scale LKAS command  x = 4096  →  motor PWM\n"
    "39990-TVA-A160  (CAN 0xE4 STEER_TORQUE → FOC q-current reference → TSG20 duty)",
    fontsize=12.5, fontweight="bold", y=0.99,
)

# ---------------------------------------------------------------------------
# Panel A — Stage (1)(2)(3): CAN input, int16 BE, range +/-4096
# ---------------------------------------------------------------------------
ax = axes[0, 0]
ax.set_title("A.  CAN 0xE4 input  →  routed buffer  [V]")
ax.hlines(0, -4096, 4096, color=C_GREY, lw=3, zorder=1)
ax.vlines([-4096, 0, 4096], -0.25, 0.25, color=C_GREY, lw=1.5)
ax.plot(X_IN, 0, "o", color=C_RED, ms=13, zorder=5)
ax.annotate("x = 4096\n(= 0x1000, full scale)", xy=(X_IN, 0), xytext=(X_IN, 0.55),
            ha="center", color=C_RED, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_RED))
ax.text(-4096, -0.45, "-4096", ha="center", color=C_GREY)
ax.text(0, -0.45, "0", ha="center", color=C_GREY)
ax.text(4096, -0.45, "+4096", ha="center", color=C_GREY)
ax.text(0, 0.95,
        "STEER_TORQUE = signed16, bytes[0:1] big-endian\n"
        "dispatcher routes 0xE4 → slot 17 → RAM 0xFEDF6BD8",
        ha="center", va="top", fontsize=8, color="#333")
ax.set_xlim(-5200, 5200); ax.set_ylim(-1.0, 1.3)
ax.set_yticks([]); ax.set_xlabel("raw CAN count")

# ---------------------------------------------------------------------------
# Panel B — Stage (3b): setpoint = clamp(-4 * x, +/-0x4000)   FUN_00052676
# ---------------------------------------------------------------------------
ax = axes[0, 1]
ax.set_title("B.  x-(-4) then clamp(+/-0x4000)  →  0xFEDF1652  [V]")
xs = np.linspace(-4096, 4096, 800)
ys = np.clip(-4.0 * xs, -16384, 16384)
ax.plot(xs, ys, color=C_BLUE, lw=2.2, label="setpoint = clamp(-4x, +/-16384)")
ax.axhline(16384, color=C_GREY, ls="--", lw=1)
ax.axhline(-16384, color=C_GREY, ls="--", lw=1)
ax.text(4096, 16384, " +0x4000", va="center", fontsize=8, color=C_GREY)
ax.text(4096, -16384, " -0x4000", va="center", fontsize=8, color=C_GREY)
y_B = np.clip(-4.0 * X_IN, -16384, 16384)   # = -16384
ax.plot(X_IN, y_B, "o", color=C_RED, ms=11, zorder=5)
ax.annotate(f"x=4096 -> {int(y_B)}\n(= -0x4000, on the rail)",
            xy=(X_IN, y_B), xytext=(-300, -8000), ha="center",
            color=C_RED, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_RED))
ax.axvline(X_IN, color=C_RED, ls=":", lw=1, alpha=0.6)
ax.set_xlabel("STEER_TORQUE in"); ax.set_ylabel("LKAS setpoint")
ax.grid(alpha=0.25); ax.set_xlim(-4500, 4500)

# ---------------------------------------------------------------------------
# Panel C — Stage (4): speed-dependent LIMIT  |setpoint| <= limit(speed)
#                       table 0xC6518/0xC6534
# ---------------------------------------------------------------------------
ax = axes[0, 2]
ax.set_title("C.  arbitration speed-limit  |setpoint| <= L(v)  [LK]")
speed = np.array([0, 10, 25, 50, 80, 120, 200])           # km/h, 0xC6518
limit = np.array([12000, 10000, 10000, 7000, 7000, 7000, 7000])  # 0xC6534
v_fine = np.linspace(0, 200, 400)
L_fine = np.interp(v_fine, speed, limit)
setp_mag = 16384                                          # |value from panel B|
out_mag = np.minimum(setp_mag, L_fine)                    # capped magnitude
ax.plot(v_fine, L_fine, color=C_ORANGE, lw=2, label="limit L(v)")
ax.plot(speed, limit, "o", color=C_ORANGE, ms=5)
ax.axhline(setp_mag, color=C_RED, ls=":", lw=1.5, label="|incoming| = 16384")
ax.plot(v_fine, out_mag, color=C_GREEN, lw=2.6, label="output magnitude")
ax.fill_between(v_fine, out_mag, L_fine, where=(L_fine >= out_mag),
                color=C_GREEN, alpha=0.08)
# mark two operating points
for v, txt in [(0, "standstill"), (120, "highway")]:
    Lc = np.interp(v, speed, limit)
    oc = min(setp_mag, Lc)
    ax.plot(v, oc, "o", color=C_RED, ms=9, zorder=5)
    ax.annotate(f"{txt}\n-> {int(oc)}", xy=(v, oc), xytext=(v + 18, oc - 2600),
                fontsize=8, color=C_RED, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_RED))
ax.set_xlabel("vehicle speed (km/h)"); ax.set_ylabel("|torque setpoint|")
ax.set_ylim(0, 18000); ax.legend(fontsize=7.5, loc="lower left")
ax.grid(alpha=0.25)

# ---------------------------------------------------------------------------
# Panel D — Stage (4): near-unity blend GAIN (table 0xC6BA0/0xC6BD4, 0x400=unity)
# ---------------------------------------------------------------------------
ax = axes[1, 0]
ax.set_title("D.  arbitration blend gain  (x0x400 = unity)  [LK]")
gax = np.array([0, 34, 64, 85, 100, 120, 140, 157.6, 173.6, 191.6, 208.4, 228, 477.6])
gain = np.array([0.878, 0.887, 0.958, 1.0348, 1.0573,
                 1.0589, 1.0589, 1.0589, 1.0589, 1.0589, 1.0589, 1.0589, 1.0589])
ax.plot(gax, gain, color=C_BLUE, lw=2, marker="o", ms=3)
ax.axhline(1.0, color=C_GREY, ls="--", lw=1)
ax.text(477.6, 1.0, " unity (0x400)", va="bottom", ha="right", fontsize=8, color=C_GREY)
ax.set_xlabel("breakpoint axis (units OPEN)"); ax.set_ylabel("gain")
ax.set_ylim(0.82, 1.10); ax.grid(alpha=0.25)
ax.text(0.5, 0.05,
        "summed with driver torque-sensor assist path,\nintegrators (Q10/Q15) + rate limits  ->  0xFEDF14C4",
        transform=ax.transAxes, fontsize=7.8, color="#333", ha="center")

# ---------------------------------------------------------------------------
# Panel E — Stage (4)(5): shared distribute+clamp  FUN_00025c32  [V, instr-verified]
# FUN_00025c32 is a GENERIC distributor with 10 callers. It clamps 4 independent
# command lanes, each to a fixed saturation limit, then fans them to per-index
# RAM banks. The LKAS packer FUN_0002b422 fills only lane +4 (the steering
# command, from arbitration out 0xFEDF14C4) and ZEROES lanes +2/+6/+8.
# ---------------------------------------------------------------------------
ax = axes[1, 1]
ax.set_title("E.  shared distribute+clamp  FUN_00025c32  [V]")
# rows top->bottom: lane +4 (LKAS steering) highlighted; others zero on this path
lanes = [("+2  lane A", 16384, "0x4000", False),
         ("+4  STEER_TORQUE (LKAS)", 10240, "0x2800", True),
         ("+6  lane C", 900,   "0x384",  False),
         ("+8  lane D", 20000, "0x4e20", False)]
ypos = np.arange(len(lanes))
for y, (lbl, v, hx, active) in zip(ypos, lanes):
    fc = "#f3d9b1" if active else "#e7e9ec"
    ec = C_ORANGE if active else "#aab0b8"
    ax.barh(y, 2 * v, left=-v, color=fc, edgecolor=ec, height=0.6,
            lw=2.0 if active else 1.0)
    ax.text(v, y, f" +/-{hx}", va="center", fontsize=7.5,
            color=(C_ORANGE if active else "#aab0b8"))
    if not active:
        ax.text(0, y, "= 0 on LKAS path", va="center", ha="center",
                fontsize=7, color="#888", style="italic")
ax.set_yticks(ypos); ax.set_yticklabels([c[0] for c in lanes], fontsize=7.8)
# LKAS command saturates at the +/-0x2800 rail (sign = -4 x torque -> negative)
ax.plot(-10240, ypos[1], "o", color=C_GREEN, ms=12, zorder=6)
ax.annotate("arbitration out 0xFEDF14C4\n(rate-limited @ tp+0x71b2)\nclamped to -0x2800 = -10240",
            xy=(-10240, ypos[1]), xytext=(1500, ypos[1] + 0.02),
            color=C_GREEN, fontweight="bold", fontsize=7.2, va="center",
            arrowprops=dict(arrowstyle="->", color=C_GREEN))
ax.set_xlabel("command-lane count  (shared by 10 callers; LKAS uses +4 only)")
ax.set_xlim(-22000, 22000); ax.set_ylim(-0.6, len(lanes) - 0.2)
ax.grid(alpha=0.2, axis="x")

# ---------------------------------------------------------------------------
# Panel F — Stage (5): mixer -> FOC q-current ref -> TSG20 3-phase PWM duty
# ---------------------------------------------------------------------------
ax = axes[1, 2]
ax.set_title("F.  mixer -> FOC -> TSG20 3-phase PWM  [V path]")
theta = np.linspace(0, 2 * np.pi, 500)
# illustrative: clamped command sets the amplitude of the q-axis-driven 3-phase duty.
# magnitude scaled to a duty fraction for display only (FOC constants are ABSENT, panel is schematic).
amp = 0.45       # SCHEMATIC amplitude only - FOC scale not pinned (Hard Ceiling)
duty_u = 0.5 + amp * np.sin(theta)
duty_v = 0.5 + amp * np.sin(theta - 2 * np.pi / 3)
duty_w = 0.5 + amp * np.sin(theta + 2 * np.pi / 3)
ax.plot(theta, duty_u, color=C_RED, lw=1.8, label="CMPU")
ax.plot(theta, duty_v, color=C_GREEN, lw=1.8, label="CMPV")
ax.plot(theta, duty_w, color=C_BLUE, lw=1.8, label="CMPW")
ax.axhline(0.5, color=C_GREY, ls="--", lw=0.8)
ax.set_xlabel("electrical angle (rad)"); ax.set_ylabel("duty fraction")
ax.set_xlim(0, 2 * np.pi); ax.set_ylim(0, 1)
ax.legend(fontsize=7.5, ncol=3, loc="upper center")
ax.text(0.5, 0.04,
        "q-current ref -> Park/Clarke/PI/SVPWM (FUN_00071272)\n"
        "-> CMPU/V/W @ 0xFFFFCCB0/B4/B8 (scale /51200.0)  = MOTOR\n"
        "FOC numeric constants ABSENT from dump - amplitude schematic",
        transform=ax.transAxes, fontsize=7.3, color="#333", ha="center")

# ---------------------------------------------------------------------------
# Flow arrows between panels (A->B->C top row, D->E->F bottom row, C->D wrap)
# ---------------------------------------------------------------------------
def flow(x, y, label):
    fig.text(x, y, label, ha="center", va="center", fontsize=15,
             color=C_GREY, fontweight="bold")

flow(0.343, 0.74, "→")
flow(0.676, 0.74, "→")
flow(0.343, 0.30, "→")
flow(0.676, 0.30, "→")

plt.tight_layout(rect=[0, 0, 1, 0.95])
out = "torque_transform_x4096.png"
plt.savefig(out, bbox_inches="tight")
print("wrote", out)
