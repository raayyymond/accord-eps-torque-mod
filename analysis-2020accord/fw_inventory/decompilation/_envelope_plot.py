import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ============================================================================
# Accord EPS rate-shaper authority ENVELOPE  (FUN_00042af8 monitor integrator)
#
# Two velocity-indexed saturating LUTs feed the deadband the LKAS command must
# exceed to wind the SM2/SM3 authority integrator (gp-0x3570).
#
# Layout per table (BYTE-VERIFIED at flash, little-endian s16):
#   [count][X0..X(n-1)][Y0..Yn]      n breakpoints, n+1 output segments:
#     v < X0           -> Y0
#     X0 <= v <= X(n-1)-> linear interp Y0..Y(n-1)
#     v >  X(n-1)      -> Yn   (high-saturation)
#
# Table 1 "upper" @ tp+0x7748 (0xC6748): count=2  X={-8192,-1024} Y={1024,1024,0}
# Table 2 "lower" @ tp+0x7754 (0xC6754): count=2  X={ 1024, 8192} Y={-1024,-1024,0}
# X axis = gated column angular velocity gp-0x4f60, Q10 (raw/1024 ~ deg/s);
#          hardware gate zeroes |v| >= 25600 (=25.0).
# Y      = envelope bound in raw LKAS-command LSB; then x polarity gp-0x6752 (+-1).
#
# VERIFIED this session: table bytes (read_memory), envelope is LIVE during turns
# (gp-0x6752 = +-1, never 0).  NOT re-traced this session: the exact min/max +
# polarity combine at decompile L600-645 (on-disk disasm was mislabeled). The raw
# per-table LERP curves below are faithful to the byte-verified tables + standard
# saturating-LUT idiom; treat the *combined* signed deadband as indicative.
# ============================================================================

LSB = 1024  # one Q10 unit on the X axis

def lut(x_q10, X, Y):
    """N-breakpoint, N+1-value saturating piecewise-linear LUT."""
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    out = np.empty_like(x_q10, float)
    for i, x in enumerate(x_q10):
        if x < X[0]:
            out[i] = Y[0]
        elif x > X[-1]:
            out[i] = Y[-1]            # high-saturation segment (Yn)
        else:
            out[i] = np.interp(x, X, Y[:len(X)])
    return out

# velocity sweep in deg/s-ish (Q10/1024); hardware gate at +-25
xv = np.linspace(-25, 25, 2001)
xq = xv * LSB

# ---- stock tables ----
T1_X = [-8192, -1024]; T1_Y = [1024, 1024, 0]     # upper bound
T2_X = [ 1024,  8192]; T2_Y = [-1024, -1024, 0]   # lower bound

def scaled_Y(Y, k):
    # scale only the nonzero plateau values; leave the 0 high-sat slot at 0 (minimal edit)
    return [ (k*y if y != 0 else 0) for y in Y ]

scales = [(1, "#1f77b4", "stock  (band +-1024)", "-"),
          (2, "#2ca02c", "2x     (band +-2048)", "--"),
          (3, "#d62728", "3x     (band +-3072)", "-")]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(15, 6))

# ===== Panel A: the actual LERP curves (Y vs velocity), stock vs 2x vs 3x =====
for k, c, lbl, ls in scales:
    up = lut(xq, T1_X, scaled_Y(T1_Y, k))
    lo = lut(xq, T2_X, scaled_Y(T2_Y, k))
    axA.plot(xv, up, color=c, ls=ls, lw=2, label=f"upper {lbl}")
    axA.plot(xv, lo, color=c, ls=ls, lw=2, alpha=0.7)

# breakpoints
for bp in (-8, -1, 1, 8):
    axA.axvline(bp, color="gray", ls=":", lw=0.8, alpha=0.6)
axA.axhline(0, color="k", lw=0.6)
axA.axvspan(-25, -25, color="none")  # noop keep limits
axA.set_title("Envelope LERP curves (byte-verified tables)\n"
              "upper = T1@0xC6748, lower = T2@0xC6754;  Y2=0 => collapse past top breakpoint")
axA.set_xlabel("gated column angular velocity  (Q10/1024 ~ deg/s);  HW gate |v|>=25 -> 0")
axA.set_ylabel("envelope bound  (raw LKAS-command LSB)")
axA.legend(loc="upper center", fontsize=8, ncol=2)
axA.grid(alpha=0.25)
axA.annotate("upper collapses to 0 for v > -1\n(LSB)", xy=(-1, 0), xytext=(2, 600),
             fontsize=7.5, color="#1f77b4",
             arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.8))
axA.annotate("lower collapses to 0 for v > 8", xy=(8, 0), xytext=(9, -700),
             fontsize=7.5, color="#1f77b4",
             arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.8))

# ===== Panel B: wind-up consequence =====
# Per-cycle wind-up = max(0, |cmd| - band).  Band = plateau magnitude (k*1024)
# in the symmetric (low-velocity) zone where both bounds are at full plateau.
cmd = np.linspace(0, 8192, 1000)
for k, c, lbl, ls in scales:
    band = k * 1024
    windup = np.maximum(0, cmd - band)
    axB.plot(cmd, windup, color=c, ls=ls, lw=2, label=f"band {band}")
axB.set_title("Per-cycle wind-up = max(0, |cmd| - band)   [1 ms/cycle]\n"
              "wider band -> slower wind-up -> later/no SM cut (symmetric low-v zone)")
axB.set_xlabel("internal windowed command magnitude (LSB, cap 8192)")
axB.set_ylabel("integrator increment per ms (LSB)")
axB.grid(alpha=0.25)
axB.legend(loc="upper left", fontsize=9)

# ms-to-SM3-cut annotations (V19 clamp 61440) at cmd=4096
for k, c, _, _ in scales:
    band = k*1024; rate = max(1, 4096-band); ms = 61440/rate
    axB.annotate(f"@cmd4096: {ms:.0f} ms", xy=(4096, max(0,4096-band)),
                 xytext=(4300, max(0,4096-band)+150), fontsize=7.5, color=c)

fig.suptitle("Accord rate-shaper authority envelope  -  stock vs 2x vs 3x  (envelope-widening lever)",
             fontsize=12, y=1.01)
fig.tight_layout()
out = r"analysis-2020accord\_envelope_lerp_plot.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
print("wrote", out)

print("\n--- per-cycle wind-up (LSB/ms) by sustained command vs band ---")
print(f"{'cmd':>6} {'stock1024':>10} {'2x2048':>8} {'3x3072':>8}")
for c0 in (2048, 4096, 6144, 8192):
    print(f"{c0:>6} {max(0,c0-1024):>10} {max(0,c0-2048):>8} {max(0,c0-3072):>8}")
print("\n--- ms to SM3 cut (V19 clamp 61440, 1 ms/cycle) ---")
for c0 in (2048, 4096, 6144, 8192):
    f=lambda b: 61440/max(1,c0-b)
    print(f"cmd={c0:>5}: stock={f(1024):>8.0f}  2x={f(2048):>8.0f}  3x={f(3072):>8.0f}")
