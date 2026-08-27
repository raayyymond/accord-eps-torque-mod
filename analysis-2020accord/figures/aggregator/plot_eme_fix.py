"""plot_eme_fix.py — Explanatory plots for the 2020 Accord 2x-LKAS EME fix.

Three panels:
  A) Re-engage soft-start ramp gp-0x6756: stock (step byte 0xC64de=17 -> +9/tick)
     vs proposed fix (step byte -> 5 -> +3/tick).  VERIFIED constants.
  B) Schematic delivered-LKAS torque through one EME (1x / 2x / 2x+rate-fix).
     ILLUSTRATIVE MODEL — not measured data; shape only.
  C) Table alternative: speed-scheduled LKAS gain (flat 2x vs low-speed taper).

Constants (VERIFIED from stock code.bin this session):
  0xC646C GAIN          891 (V14: 1782)
  0xC71D6 SLEW STEP     14
  0xC6288 init-wait     300 ticks
  0xC628A ramp ceiling  408
  0xC64DE ramp step     17 -> eff (17>>1)+1 = 9 / tick
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "plots")
os.makedirs(OUT, exist_ok=True)

fig, ax = plt.subplots(1, 3, figsize=(18, 5.2))

# ---------- Panel A: re-engage ramp ----------
INIT_WAIT = 300            # 0xC6288 ticks at zero
CEIL = 408                # 0xC628A ramp ceiling (gain units)
def ramp_profile(step_byte, n=900):
    eff = (step_byte >> 1) + 1
    g = np.zeros(n)
    val = 0
    for t in range(n):
        if t < INIT_WAIT:
            g[t] = 0
        else:
            val = min(CEIL, val + eff)
            g[t] = val
    return g, eff

g_stock, eff_stock = ramp_profile(17)
g_fix,   eff_fix   = ramp_profile(5)
t = np.arange(len(g_stock))
ax[0].plot(t, g_stock, lw=2.2, label=f"stock: step byte 17 -> +{eff_stock}/tick (~{INIT_WAIT}+{int(np.ceil(CEIL/eff_stock))} ticks)")
ax[0].plot(t, g_fix,   lw=2.2, label=f"FIX: step byte 5 -> +{eff_fix}/tick (~{INIT_WAIT}+{int(np.ceil(CEIL/eff_fix))} ticks)")
ax[0].axvspan(0, INIT_WAIT, color="0.85", label="300-tick init-wait (LKAS held at 0)")
ax[0].set_title("A. Re-engage soft-start ramp  (gp-0x6756)\n1-byte cal @0xC64DE — smooths the post-kill RATCHET")
ax[0].set_xlabel("ticks since kill"); ax[0].set_ylabel("re-engage gain (0 -> 408)")
ax[0].legend(fontsize=8, loc="lower right"); ax[0].grid(alpha=0.3)

# ---------- Panel B: schematic EME ----------
n = 600
tt = np.arange(n)
base = np.full(n, 1.0)            # steady LKAS demand (normalized to 1x stock)
KILL = 150
# stock 1x: small dip imperceptible
def event(amp, recover_ticks):
    y = np.full(n, amp, float)
    # smooth ramp-down over ~15 ticks then 0, then re-ramp
    drop = np.clip((tt - KILL) / 12.0, 0, 1)
    y = amp * (1 - drop)
    re = np.clip((tt - (KILL + 60)) / recover_ticks, 0, 1)
    y = np.where(tt < KILL + 60, y, amp * re)
    return y
y1 = event(1.0, 30)
y2 = event(2.0, 30)                # 2x: drop twice as big, fast re-ramp (ratchet)
y2fix = event(2.0, 140)            # 2x + slower re-engage ramp
ax[1].plot(tt, y1, lw=2.0, label="stock 1x  (dip ~imperceptible)")
ax[1].plot(tt, y2, lw=2.4, label="V14 2x  (snap + fast ratchet)")
ax[1].plot(tt, y2fix, lw=2.4, ls="--", label="V14 2x + rate-limit FIX  (smoothed)")
ax[1].axvline(KILL, color="r", ls=":", alpha=0.6, label="kill fires (driver override)")
ax[1].set_title("B. Delivered LKAS torque through one EME\n(ILLUSTRATIVE MODEL — shape only, not measured)")
ax[1].set_xlabel("time (ticks)"); ax[1].set_ylabel("delivered LKAS torque (x stock)")
ax[1].legend(fontsize=8, loc="upper right"); ax[1].grid(alpha=0.3)

# ---------- Panel C: speed-scheduled gain (table alternative) ----------
spd = np.array([0, 5, 10, 15, 20, 30, 45, 70, 120])   # km/h-ish axis
flat2x = np.full_like(spd, 2.0, float)
# taper: ~1x at the low-speed sharp-turn regime, full 2x by ~25-30 km/h
taper = np.interp(spd, [0, 8, 16, 25, 120], [1.0, 1.0, 1.4, 2.0, 2.0])
ax[2].plot(spd, flat2x, lw=2.2, marker="o", label="V14: flat 2x at all speeds (scalar gain 0xC646C)")
ax[2].plot(spd, taper, lw=2.2, marker="s", label="TABLE alt: low-speed taper (2x only where wanted)")
ax[2].axvspan(0, 16, color="#ffe9e9", label="sharp low-speed turn regime (EME lives here)")
ax[2].set_ylim(0.8, 2.2)
ax[2].set_title("C. Table alternative: speed-scheduled LKAS gain\nback off 2x where the driver fights; keep 2x on the highway")
ax[2].set_xlabel("vehicle speed (km/h, approx)"); ax[2].set_ylabel("LKAS torque multiplier")
ax[2].legend(fontsize=8, loc="lower right"); ax[2].grid(alpha=0.3)

fig.suptitle("2020 Accord 39990-TVA-A160 — keeping 2x LKAS while resolving the driver-override EME", fontsize=13, y=1.02)
fig.tight_layout()
p = os.path.join(OUT, "eme_fix_explained.png")
fig.savefig(p, dpi=130, bbox_inches="tight")
print("WROTE", p)
