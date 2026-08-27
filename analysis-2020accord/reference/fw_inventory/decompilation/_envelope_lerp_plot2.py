import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Envelope LERP tables read from firmware at 0xC6748 / 0xC6754 (V850 LE halfwords)
# T1 upper: count=2, X={-8192,-1024}, Y={1024,1024,0}
# T2 lower: count=2, X={1024, 8192}, Y={-1024,-1024,0}
# X input = gp-0x6af8 (gated gp-0x4f60) column angular velocity (Q10); HW gate zeros it when |v| >= 25600
#
# GATING — verified at 0x43116–0x43134 (s_motor_torque_rate_shaper):
#   Selection is by DRIVER ASSIST torque (gp-0x6bf0), NOT the LKAS command (gp-0x6acc).
#   Threshold = ±9216 (cal 0xC6156):
#     driver_assist < -9216  → T1 output is used (T2 zeroed)    [leftward driver override]
#     driver_assist > +9216  → T2 output is used (T1 zeroed)    [rightward driver override]
#     |driver_assist| < 9216 → BOTH T1 and T2 outputs = 0       ← hands-off LKAS / normal operation
#
#   CONSEQUENCE: During hands-off LKAS the entire LERP envelope is INACTIVE.
#   The integrator bounds in that mode come from velocity-based rate-shaper bounds only.
#   This is why stock 1× LKAS never causes EMEs (cmd ~418 < rate-shaper bound at all velocities).
#   2× EMEs occur when cmd exceeds the rate-shaper bound at stalled column (bound → 0), not LERP plateau.
#
# OPEN: velocity-breakpoint asymmetry — T1 releases at -1 deg/s, T2 at +8 deg/s.
#   Physical interpretation unresolved. May reflect a calibration convention rather than
#   asymmetric left/right behavior. Investigate in a future session.

T1_X = [-8192, -1024]
T1_Y = [1024, 1024, 0]

T2_X = [1024, 8192]
T2_Y = [-1024, -1024, 0]


def lerp_table(x_val, X_bp, Y_vals):
    if x_val <= X_bp[0]:
        return float(Y_vals[0])
    for i in range(len(X_bp) - 1):
        if X_bp[i] <= x_val <= X_bp[i + 1]:
            t = (x_val - X_bp[i]) / (X_bp[i + 1] - X_bp[i])
            return Y_vals[i] * (1.0 - t) + Y_vals[i + 1] * t
    return float(Y_vals[len(X_bp)])


v = np.arange(-30000, 30001, 50)
t1 = np.array([lerp_table(x, T1_X, T1_Y) for x in v])
t2 = np.array([lerp_table(x, T2_X, T2_Y) for x in v])

fig, ax = plt.subplots(figsize=(13, 7))

ax.plot(v, t1, color='steelblue', lw=2.2,
        label='T1  0xC6748  X={-8192,-1024}  Y={1024,1024,0}\n'
              '  Active only when driver_assist (gp-0x6bf0) < -9216  [leftward driver override]')
ax.plot(v, t2, color='darkorange', lw=2.2,
        label='T2  0xC6754  X={1024,8192}   Y={-1024,-1024,0}\n'
              '  Active only when driver_assist (gp-0x6bf0) > +9216  [rightward driver override]')

for sign in (-1, 1):
    ax.axvline(sign * 25600, color='crimson', ls='--', lw=1.2, alpha=0.75,
               label='HW gate ±25600  (|v| >= 25 deg/s -> gated to 0)' if sign == 1 else '')

for xb in T1_X:
    ax.axvline(xb, color='steelblue', ls=':', lw=0.9, alpha=0.55)
for xb in T2_X:
    ax.axvline(xb, color='darkorange', ls=':', lw=0.9, alpha=0.55)

ax.axhline(0, color='gray', lw=0.7)
ax.axvline(0, color='gray', lw=0.7)

ax.annotate('T1 plateau = +1024\n(leftward driver override only)', xy=(-8000, 1024),
            xytext=(-26000, 1200),
            arrowprops=dict(arrowstyle='->', color='steelblue', lw=1.2),
            color='steelblue', fontsize=9)
ax.annotate('T2 plateau = -1024\n(rightward driver override only)', xy=(4000, -1024),
            xytext=(10000, -1270),
            arrowprops=dict(arrowstyle='->', color='darkorange', lw=1.2),
            color='darkorange', fontsize=9)

# Key finding box — hands-off LKAS case
ax.text(0.015, 0.97,
        'HANDS-OFF LKAS (normal operation):\n'
        '  |driver_assist gp-0x6bf0| < 9216  ->  T1 = T2 = 0 (LERP inactive)\n'
        '  Integrator bounds = velocity-based rate-shaper bounds only\n'
        '  Stock 1x cmd ~418 < rate-shaper bound  ->  no wind-up, no EME\n'
        '  2x cmd ~835 exceeds rate-shaper bound at stalled column  ->  SM2/SM3 trip',
        transform=ax.transAxes, va='top', fontsize=8.5,
        bbox=dict(boxstyle='round,pad=0.45', fc='lightyellow', ec='goldenrod', alpha=0.93))

# Open question box
ax.text(0.015, 0.03,
        'OPEN: velocity-breakpoint asymmetry (T1 releases at -1 deg/s, T2 at +8 deg/s)\n'
        '  Physical meaning unresolved — investigate in future session',
        transform=ax.transAxes, va='bottom', fontsize=8,
        bbox=dict(boxstyle='round,pad=0.35', fc='#fff0f0', ec='#cc6666', alpha=0.9))

ax2 = ax.twiny()
ax2.set_xlim(ax.get_xlim())
tick_raw = np.array([-25600, -8192, -4096, -1024, 0, 1024, 4096, 8192, 25600])
ax2.set_xticks(tick_raw)
ax2.set_xticklabels([f'{r/1024:.1f}' for r in tick_raw], fontsize=8)
ax2.set_xlabel('Column velocity (deg/s,  Q10 / 1024)', fontsize=9)

ax.set_xlabel('Column angular velocity  gp-0x6af8 = gated(gp-0x4f60)  (Q10 raw units)', fontsize=10)
ax.set_ylabel('Envelope bound (LSB -- same scale as LKAS command)', fontsize=10)
ax.set_title(
    'Accord EME Envelope LERP Tables  (verified from firmware @ 0xC6748 / 0xC6754)\n'
    'T1/T2 gated by DRIVER ASSIST gp-0x6bf0 at +-9216 threshold (verified 0x43116-0x43134)\n'
    'LERP is INACTIVE during hands-off LKAS;  integrator (gp-0x3570) bounds from rate-shaper only in that mode',
    fontsize=10)

ax.set_ylim(-1500, 1500)
ax.yaxis.set_major_locator(ticker.MultipleLocator(256))
ax.grid(True, alpha=0.25)
ax.legend(loc='upper right', fontsize=8.5)

plt.tight_layout()
out = r'C:\Users\dudei\Desktop\Projects\firmware-analysis-kit\analysis-2020accord\_envelope_lerp_plot2.png'
plt.savefig(out, dpi=150)
print(f'Saved: {out}')
