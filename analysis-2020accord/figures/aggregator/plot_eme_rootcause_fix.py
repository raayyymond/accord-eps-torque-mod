"""plot_eme_rootcause_fix.py — the verified EME root-cause fix for the 2020 Accord 2x build.

Panel A: delivered combined motor command (gp-0x6b98) through one override event.
  STOCK (slew step tp+0x71d6 = 0xC61D6 = 0): the deadband zeroes the command and,
  with the rate-limiter disabled, it HOLDS at 0 then JUMPS back  = the felt cut + ratchet.
  FIX (slew step -> 14): the delivered command is rate-limited; the dip and recovery
  are smooth. 2x steady-state magnitude is unchanged (rate-of-change only).
Panel B: re-engage ramp gain (gp-0x6756) — init-wait 300 (0xC6288) + step (0xC64DE).

ILLUSTRATIVE timing model; the constants (0xC61D6=0, 0xC6424=29491, 0xC6288=300,
0xC628A=408, 0xC64DE=17) and the mechanism are disasm-verified this session.
"""
import os, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
os.makedirs(OUT, exist_ok=True)
fig, ax = plt.subplots(1, 2, figsize=(15, 5.4))

# ---- Panel A: delivered command through the override ----
n = 420
t = np.arange(n)
LVL = 2.0                     # 2x steady level (normalized; stock 1x would be 1.0)
KILL = 120                    # deadband fires (net-demand zero-crossing during override)
REBUILD = 250                 # demand rebuilds after override eases

# STOCK: hard zero, hold (slew=0 cannot ramp), then jump back when demand returns
stock = np.full(n, LVL, float)
stock[KILL:REBUILD] = 0.0     # hard cut + hold at 0
stock[REBUILD:] = LVL         # jump back (step)

# FIX (slew=14): rate-limit the delivered command; smooth dip + smooth recovery
fix = np.full(n, LVL, float)
slew = LVL / 35.0             # 14/tick on the real scale -> ~35 ticks full-scale
val = LVL
target = np.where((t>=KILL)&(t<REBUILD), 0.0, LVL)
for i in range(n):
    tg = target[i]
    if val < tg: val = min(tg, val+slew)
    elif val > tg: val = max(tg, val-slew)
    fix[i] = val

ax[0].axhline(LVL, color="0.8", lw=1, ls="--")
ax[0].plot(t, stock, lw=2.4, color="#c0392b", label="STOCK 2x (slew=0): cut → HOLD at 0 → jump = the EME")
ax[0].plot(t, fix,   lw=2.4, color="#2e7d32", label="FIX (slew 0→14 @0xC61D6): smooth dip + recovery")
ax[0].axvspan(KILL, REBUILD, color="#fff2cc", label="driver override (net demand near 0)")
ax[0].annotate("whole power steering\ncuts out (no DTC)", xy=(KILL+4, 0.06), xytext=(KILL+22, 0.7),
               fontsize=8, arrowprops=dict(arrowstyle="->", color="#c0392b"))
ax[0].annotate("jump back = ratchet", xy=(REBUILD, LVL*0.55), xytext=(REBUILD-95, LVL*0.18),
               fontsize=8, color="#c0392b", arrowprops=dict(arrowstyle="->", color="#c0392b"))
ax[0].set_title("A. Delivered combined command gp-0x6b98 through a mid-turn override\n"
                "(base PS assist + LKAS share the same trunk — both cut)")
ax[0].set_xlabel("time (ticks)"); ax[0].set_ylabel("delivered torque (× stock)")
ax[0].set_ylim(-0.1, 2.3); ax[0].legend(fontsize=8, loc="lower right"); ax[0].grid(alpha=0.3)

# ---- Panel B: re-engage ramp gain ----
INIT, CEIL = 300, 408
def ramp(step_byte, m=900):
    eff=(step_byte>>1)+1; g=np.zeros(m); v=0
    for k in range(m):
        if k>=INIT: v=min(CEIL, v+eff)
        g[k]=v
    return g, eff
g17,e17 = ramp(17); g27,e27 = ramp(27)
tt=np.arange(len(g17))
ax[1].axvspan(0, INIT, color="0.9", label="init-wait 300 (0xC6288): held at 0")
ax[1].plot(tt, g17, lw=2.2, label=f"stock step 17 → +{e17}/tick")
ax[1].plot(tt, g27, lw=2.2, ls="--", label=f"optional step 27 → +{e27}/tick (faster re-engage)")
ax[1].set_title("B. Re-engage ramp gain gp-0x6756 after a dropout\n(secondary tuning levers 0xC64DE / 0xC6288)")
ax[1].set_xlabel("ticks since dropout"); ax[1].set_ylabel("re-engage gain (0→408)")
ax[1].legend(fontsize=8, loc="lower right"); ax[1].grid(alpha=0.3)

fig.suptitle("2020 Accord 39990-TVA-A160 — verified EME root cause & fix: re-enable the delivered-command slew limiter",
             fontsize=13, y=1.02)
fig.tight_layout()
p=os.path.join(OUT,"eme_rootcause_fix.png")
fig.savefig(p, dpi=130, bbox_inches="tight"); print("WROTE", p)
