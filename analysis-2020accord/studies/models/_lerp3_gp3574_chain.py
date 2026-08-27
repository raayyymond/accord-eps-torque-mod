"""
gp-0x3574 upstream chain — pseudocode + data visualization
FUNC_00042af8 (s_motor_torque_rate_shaper), 2020 Honda Accord EPS firmware
V850:LE:32, image base 0x00000000, tp=0xBF000, gp=0xFEDF8000

=============================================================================
PSEUDOCODE: full chain from inputs to gp-0x3574
=============================================================================

CONFIRMED FLASH DATA (read from Ghidra, tp+0xNNNN = 0xC6NNN):
  LERP1  @ 0xC6770 (tp+0x7770): 7-pt step-down, X unsigned, Y unsigned
  LERP2  @ 0xC69E8 (tp+0x79E8): 7-pt FLAT at 1024 (unity gain)
  IIR α  @ 0xC6418 (tp+0x7418): alpha = 10
  X-step @ 0xC61E4 (tp+0x71E4): 3072  (used for LERP3 representative X)

RUNTIME RAM DATA (not readable from static analysis):
  LERP3 count   : gp-0x6430         (1 halfword, = 9 for 10-segment table)
  LERP3 X array : gp-0x642e..0x641c (10 halfwords, written from gp-0x3714 buffer
                                     by init loop in FUN_000389ec, spacing ~3072)
  LERP3 Y base  : gp-0x6444         (10 halfwords, float-computed from X values
                                     by FUN_000352b4 each cycle)

-- STEP 1: LERP1  (address 0x42b42) ----------------------------------------
   Input  : gp-0x6a28           unsigned, motion/assist magnitude
   Table  : X = [0, 576, 640, 12800, 13440, 14080, 14720]   (unsigned u16)
             Y = [2048, 2048, 512,   512,   512,   512,  512] (unsigned u16)
   Formula: standard integer LERP
             find i such that X[i] <= input < X[i+1]
             r25 = Y[i] + (input - X[i]) * (Y[i+1] - Y[i]) / (X[i+1] - X[i])
   Effect : STEP-DOWN at input ≈ 576-640:
             input < 576   → r25 = 2048   (high modulation)
             input > 640   → r25 = 512    (low modulation, clipped flat)

-- STEP 2: LERP2  (address 0x42c50) ----------------------------------------
   Input  : r22                 column velocity, signed Q10
   Table  : X = [-7168, -6144, -5120, 0, 5120, 6144, 7168]  (signed s16)
             Y = [1024,  1024,  1024, 1024, 1024, 1024, 1024] (unsigned, FLAT)
   Output : r8 = 1024  (constant regardless of velocity)
   NOTE   : LERP2 is a unity-gain pass-through; it always returns 1024.

-- STEP 3: Y-table modulation (address 0x42cb8–0x42cc4) ---------------------
   r25 = (r8 * r25) >> 10
       = (1024 * lerp1_out) >> 10
       = lerp1_out              (identity — LERP2 contributes nothing)

   LERP3 effective Y[i] = gp-0x6444[i] + r25
                         = gp-0x6444[i] + lerp1_out
   → LERP1 output additively shifts the LERP3 Y table UP or DOWN each cycle.
   → High LERP1 (2048) → large Y shift → wider envelope bound.
   → Low LERP1 (512)   → small Y shift → tighter envelope bound.

-- STEP 4: LERP3  (address 0x42d38) ----------------------------------------
   Input  : r22                         column velocity, signed Q10
   X array: gp-0x642e..gp-0x641c        10 runtime halfwords (spacing ~3072)
   Y array: [gp-0x6444[i] + r25]        10 runtime halfwords + LERP1 shift
   Formula: same integer LERP
             find i: X[i] <= r22 < X[i+1]
             lerp3_out = Y[i] + (r22 - X[i]) * (Y[i+1]-Y[i]) / (X[i+1]-X[i])

-- STEP 5: IIR smoother  (address 0x42dac–0x42dc8) -------------------------
   State  : gp-0x3574  stored at ×256 scale (actual value = stored >> 8)
   Alpha  : tp+0x7418 = 10  (Q10 division → τ = 1024/10 = 102.4 cycles)
   Cycle rate: 1000 Hz  →  τ ≈ 102.4 ms

   target_x256 = lerp3_out << 8              // scale up ×256
   iir_state  += (target_x256 - iir_state) * 10 >> 10   // alpha=10
   if iir_state > target_x256:               // anti-overshoot clamp (cmovle)
       iir_state = target_x256
   gp_0x3574 = iir_state                     // write (×256 stored)

=============================================================================
END PSEUDOCODE
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── confirmed flash constants ──────────────────────────────────────────────

LERP1_X = np.array([0, 576, 640, 12800, 13440, 14080, 14720], dtype=np.float64)
LERP1_Y = np.array([2048, 2048, 512, 512, 512, 512, 512],    dtype=np.float64)

LERP2_X = np.array([-7168, -6144, -5120, 0, 5120, 6144, 7168], dtype=np.float64)
LERP2_Y = np.array([1024,  1024,  1024,  1024, 1024, 1024, 1024], dtype=np.float64)

IIR_ALPHA   = 10
IIR_DIV     = 1024
IIR_SCALE   = 256          # state stored at ×256
CYCLE_RATE  = 1000         # Hz
TAU_CYCLES  = IIR_DIV / IIR_ALPHA          # 102.4 cycles
TAU_MS      = TAU_CYCLES / CYCLE_RATE * 1000  # 102.4 ms

# ── LERP3 runtime tables (not in static flash) ────────────────────────────
# X breakpoints: 10 halfwords from gp-0x642e..gp-0x641c (FUN_000389ec init
# loop writes these from gp-0x3714 buffer; spacing cal at 0xC61E4 = 3072).
# Using representative symmetric table for illustration.
X_STEP = 3072
LERP3_X_REP = np.array([X_STEP * (i - 4) for i in range(10)], dtype=np.float64)
# = [-12288, -9216, -6144, -3072, 0, 3072, 6144, 9216, 12288, 15360]

# Base Y (gp-0x6444): computed by FUN_000352b4 from X values via float math.
# Shape assumed monotone-increasing (softer bound at higher velocity), scaled
# to a plausible LKAS rate unit range.  EXACT VALUES ARE UNKNOWN from static
# analysis — these are representative.
LERP3_Y_BASE = np.array([200, 350, 600, 900, 1200, 1200, 900, 600, 350, 200],
                          dtype=np.float64)


# ── helper: piecewise linear interpolation ────────────────────────────────
def lerp_table(X, Y, inputs):
    """Integer-faithful LERP: clamp to endpoints, linear in between."""
    results = np.empty_like(inputs, dtype=np.float64)
    for k, x in enumerate(inputs):
        if x <= X[0]:
            results[k] = Y[0]
        elif x >= X[-1]:
            results[k] = Y[-1]
        else:
            i = np.searchsorted(X, x, side='right') - 1
            i = int(np.clip(i, 0, len(X) - 2))
            dx = X[i+1] - X[i]
            results[k] = Y[i] + (x - X[i]) * (Y[i+1] - Y[i]) / dx
    return results


# ── IIR simulation ────────────────────────────────────────────────────────
def simulate_iir(target_seq, alpha=IIR_ALPHA, div=IIR_DIV, scale=IIR_SCALE):
    """
    target_seq: sequence of raw (un-scaled) LERP3 outputs (integers)
    Returns state_seq in the same raw (un-scaled) units.
    """
    state = 0  # stored at ×scale internally
    out = []
    for t in target_seq:
        t_x = t * scale
        state += (t_x - state) * alpha // div
        if state > t_x:          # anti-overshoot clamp
            state = t_x
        out.append(state / scale)
    return np.array(out)


# ══════════════════════════════════════════════════════════════════════════
#  FIGURE
# ══════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 11), facecolor='#0f0f0f')
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.52, wspace=0.38)

AXBG   = '#1a1a2e'
GRID_C = '#2a2a4a'
TXT    = '#e0e0e0'
ACCENT = '#00aaff'
GOLD   = '#ffcc44'
GREEN  = '#44dd88'
RED    = '#ff5566'

def style_ax(ax, title):
    ax.set_facecolor(AXBG)
    for sp in ax.spines.values():
        sp.set_color(GRID_C)
    ax.tick_params(colors=TXT, labelsize=8)
    ax.xaxis.label.set_color(TXT)
    ax.yaxis.label.set_color(TXT)
    ax.set_title(title, color=GOLD, fontsize=9, pad=6)
    ax.grid(True, color=GRID_C, linewidth=0.5, linestyle='--')

# ── Panel 1: LERP1 ────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
style_ax(ax1, 'LERP1  (0xC6770)  — amplitude modulator')

x_dense = np.linspace(0, 16000, 2000)
y1      = lerp_table(LERP1_X, LERP1_Y, x_dense)

ax1.plot(x_dense, y1, color=ACCENT, linewidth=1.8, zorder=3)
ax1.scatter(LERP1_X, LERP1_Y, color=GOLD, s=50, zorder=5)
ax1.axvline(576,  color='#ff8800', linewidth=0.8, linestyle=':', alpha=0.8)
ax1.axvline(640,  color='#ff8800', linewidth=0.8, linestyle=':', alpha=0.8)
ax1.axhline(2048, color=GRID_C, linewidth=0.5, linestyle='-.')
ax1.axhline(512,  color=GRID_C, linewidth=0.5, linestyle='-.')
ax1.annotate('step-down\n576→640', xy=(608, 1280), color='#ff8800',
             fontsize=7, ha='center')
ax1.set_xlabel('gp-0x6a28  (motion magnitude, unsigned u16)', fontsize=8)
ax1.set_ylabel('r25 = LERP1 output', fontsize=8)
ax1.set_xlim(-200, 16000)
ax1.set_ylim(0, 2400)

ax1_note = (
    "X = [0, 576, 640, 12800, 13440, 14080, 14720]\n"
    "Y = [2048, 2048, 512, 512, 512, 512, 512]\n"
    "→ high modulation at low input, flat low at high input"
)
ax1.text(0.98, 0.97, ax1_note, transform=ax1.transAxes, color=TXT,
         fontsize=6.5, va='top', ha='right',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#111133', alpha=0.8))

# ── Panel 2: LERP2 ────────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
style_ax(ax2, 'LERP2  (0xC69E8)  — unity gain (always 1024)')

x2_dense = np.linspace(-8000, 8000, 500)
y2       = lerp_table(LERP2_X, LERP2_Y, x2_dense)

ax2.plot(x2_dense, y2, color=GREEN, linewidth=2.0, zorder=3)
ax2.scatter(LERP2_X, LERP2_Y, color=GOLD, s=50, zorder=5)
ax2.axhline(1024, color=RED, linewidth=0.8, linestyle='--', alpha=0.7,
            label='constant 1024')
ax2.set_xlabel('r22  (column velocity, signed Q10)', fontsize=8)
ax2.set_ylabel('r8 = LERP2 output', fontsize=8)
ax2.set_ylim(0, 1300)
ax2.legend(fontsize=7, facecolor=AXBG, labelcolor=TXT, edgecolor=GRID_C)

ax2_note = (
    "X = [-7168..7168]\n"
    "Y = [1024, 1024, 1024, 1024, 1024, 1024, 1024]\n"
    "→ FLAT — LERP2 ≡ 1024 ≡ unity\n"
    "→ Y-shift = (1024 × LERP1) >> 10 = LERP1"
)
ax2.text(0.98, 0.97, ax2_note, transform=ax2.transAxes, color=TXT,
         fontsize=6.5, va='top', ha='right',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#111133', alpha=0.8))

# ── Panel 3: LERP3 with dynamic Y modulation ──────────────────────────────
ax3 = fig.add_subplot(gs[1, :])
style_ax(ax3, 'LERP3  — velocity → rate bound  (dynamic RAM tables, Y shifted by LERP1 output)')

x3_dense = np.linspace(LERP3_X_REP[0] - 1000, LERP3_X_REP[-1] + 1000, 1000)

# three example LERP1 outputs: max (2048), mid (1280), min (512)
examples = [
    (2048, ACCENT,  'LERP1=2048  [input<576: max mod]'),
    (1280, '#cc88ff', 'LERP1=1280  [mid-range]'),
    (512,  GREEN,   'LERP1=512   [input>640: min mod]'),
]

for lerp1_val, col, label in examples:
    Y_eff = LERP3_Y_BASE + lerp1_val
    y3    = lerp_table(LERP3_X_REP, Y_eff, x3_dense)
    ax3.plot(x3_dense, y3, color=col, linewidth=1.6, label=label)
    # mark breakpoints
    ax3.scatter(LERP3_X_REP, Y_eff, color=col, s=25, zorder=5, alpha=0.7)

ax3.axvline(0, color=GRID_C, linewidth=0.7, linestyle='-')

# annotate the LERP1 shift arrows at one breakpoint
bk_idx = 4  # middle breakpoint (x≈0)
for i, (lerp1_val, col, _) in enumerate(examples):
    if i == 0:
        ax3.annotate('', xy=(LERP3_X_REP[bk_idx] + 100, LERP3_Y_BASE[bk_idx] + lerp1_val),
                     xytext=(LERP3_X_REP[bk_idx] + 100, LERP3_Y_BASE[bk_idx] + 512),
                     arrowprops=dict(arrowstyle='<->', color=GOLD, lw=1.2))
        ax3.text(LERP3_X_REP[bk_idx] + 300, LERP3_Y_BASE[bk_idx] + 1280,
                 f'ΔY = LERP1\n(512..2048)', color=GOLD, fontsize=7.5)

ax3.set_xlabel('r22  (column velocity, signed Q10)  /  X from gp-0x642e (RAM, step ~3072)', fontsize=8)
ax3.set_ylabel('LERP3 output  (rate bound, pre-IIR)', fontsize=8)
ax3.legend(fontsize=8, facecolor=AXBG, labelcolor=TXT, edgecolor=GRID_C, loc='upper right')

ax3_note = (
    "X breakpoints: gp-0x642e..gp-0x641c  (10 halfwords, RUNTIME — set by FUN_000389ec from gp-0x3714 buffer)\n"
    "Y base values: gp-0x6444  (10 halfwords, RUNTIME — computed by FUN_000352b4 via float from X values)\n"
    "Y effective  : gp-0x6444[i] + LERP1_out  →  LERP1 additively shifts entire Y curve up/down\n"
    "X-step cal   : tp+0x71E4 (0xC61E4) = 3072  (used for representative X above; actual values runtime)"
)
ax3.text(0.01, 0.03, ax3_note, transform=ax3.transAxes, color=TXT,
         fontsize=6.8, va='bottom', ha='left',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#111133', alpha=0.85))

# ── Panel 4: IIR step response ────────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, :])
style_ax(ax4, f'IIR smoother  (α=10, τ={TAU_MS:.1f} ms @ {CYCLE_RATE} Hz)  →  gp-0x3574')

n_cycles = 600
# target sequence: step-up at t=50, step-down at t=300, step-up at t=450
target_raw = np.ones(n_cycles) * 800.0
target_raw[0:50]   = 200.0
target_raw[300:450] = 400.0

iir_out = simulate_iir(target_raw.astype(int))
t_ms    = np.arange(n_cycles)

ax4.plot(t_ms, target_raw, color=GOLD,  linewidth=1.0, linestyle='--', label='LERP3 target (raw)')
ax4.plot(t_ms, iir_out,    color=ACCENT, linewidth=1.8, label='gp-0x3574  (IIR state ÷256)')

# annotate tau
tau_idx = 50 + int(TAU_CYCLES)
ax4.axvline(tau_idx, color=RED, linewidth=0.8, linestyle=':')
ax4.annotate(f'τ = {TAU_MS:.0f} ms\n(63% rise)',
             xy=(tau_idx, iir_out[tau_idx]),
             xytext=(tau_idx + 30, iir_out[tau_idx] - 100),
             color=RED, fontsize=7.5,
             arrowprops=dict(arrowstyle='->', color=RED, lw=0.9))

ax4.set_xlabel('cycle  (1 cycle = 1 ms @ 1000 Hz)', fontsize=8)
ax4.set_ylabel('value  (raw, ÷256 for Q10 output)', fontsize=8)
ax4.legend(fontsize=8, facecolor=AXBG, labelcolor=TXT, edgecolor=GRID_C)

iir_note = (
    "Formula  (per cycle @ 0x42dac):\n"
    "  target_x256 = LERP3_out × 256\n"
    "  iir_state  += (target_x256 − iir_state) × 10 >> 10    // α=10, Q10\n"
    "  if iir_state > target_x256: iir_state = target_x256    // anti-overshoot\n"
    "  gp_0x3574 = iir_state   [read as actual_value = iir_state >> 8]"
)
ax4.text(0.99, 0.97, iir_note, transform=ax4.transAxes, color=TXT,
         fontsize=6.8, va='top', ha='right', family='monospace',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#111133', alpha=0.85))

# ── title ─────────────────────────────────────────────────────────────────
fig.suptitle(
    'gp-0x3574 upstream chain  ·  s_motor_torque_rate_shaper (0x42af8)  ·  2020 Accord EPS',
    color=GOLD, fontsize=11, fontweight='bold', y=0.98
)

plt.savefig('analysis-2020accord/_lerp3_gp3574_chain.png',
            dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print("Saved: analysis-2020accord/_lerp3_gp3574_chain.png")
plt.show()
