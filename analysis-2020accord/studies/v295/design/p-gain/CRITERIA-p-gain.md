# CRITERIA — the "p-gain" design lens (V295), written BEFORE any candidate number was computed

Subagent `p-gain`, 2026-09-30 10:36 PDT. Design only. Pre-registered here so the result cannot move the goalposts.
Every number below is a V294-relative difference unless it says otherwise; the harness rules (V295-HARNESS.md §7) bind.

## What the lens is allowed to touch
- Kp bank 0xCB994 (all 28 records; X knots and Y), the demand map 0xC9A88 (all 28 records, Y only unless stated),
  and — only as a diagnostic, never as the recommendation of THIS lens unless argued — the fb gain b 0xC63EA and the
  trim clamp C 0xC62E6 (to separate the feedforward effect of Kp from its trim effect, and to hold the trim cap).
- No opcode change unless the gain is large and argued (none expected: Kp is a free u16 per knot).
- No fork change.

## Hard gates on a candidate (any one fails -> the candidate is NOT recommendable)
- G1 rail: delivered rail +2461 / -2463 exactly (m_safe), lane clamp 3072 untouched.
- G2 int32: min margin >= 2.0 (m_safe int32), b <= b_max, map Y <= 32767, no static problem from Cells.problems().
- G3 monotone surface: T(idx) at fb = 0 non-decreasing over idx 0..240 (no torque reversal as the command grows).
- G4 HF: |P/x| at 20 Hz <= 3 x V294 (6.24) unless evidence is given; stress-member damping (mode13/mode20/mode20_lo
  at 5/12/25 m/s) zeta >= 0.9 x V294's; every scored + stress member stable incl. delay x1.5 (M_LOOP).
- G5 outer loop (linear, M_DRIVE outer, relay on AND off, idx_op 60 and at the candidate's small-signal operating
  point): on the identified members Ms <= 1.6 and GM >= 3 at every speed 5..26.9 m/s; on light_b GM must not fall
  below min(V294's, 1.5) at any speed, and Ms must not exceed max(V294's x 1.25, 2.0).
- G6 closed-loop sim (mode B, lp AND full, nominal AND light_b, every speed band): no divergence / bail storm
  (n_bail rise), 1-5 Hz limit-cycle peak not up > 3 dB vs V294 in the same batch on either plant, hard-turn
  1.6-3 Hz rms (hard16) not up > 10 % vs V294 at 5-10 or 15-22 m/s under full on either plant.
- G7 attribution: every changed value readable from ONE short drive on the existing wire (427 tap FF identity by
  demand index, trim-footprint regression, 0x18F/0x14A, 0xE4). A changed value with no wire read = not shippable.
- G8 trim cap / zero-command torque / restart pulse: may rise with Kp; if > 1.5 x V294 (924 T) the design must say
  why it is acceptable or hold it with C (and then C's own on-car record must be stated).

## What "better" means for this lens (scored per complaint, pre-registered direction and size)
- "Loose on straights and turns at low speed": mode-B lp tracking gain AND straight delivery at 0-5 and 5-10 m/s,
  turn-hold at 5-10: a win is >= +0.05 absolute on tracking gain or turn-hold with no G5/G6 failure.
- "Loose/understeer at highway turns": tracking gain + turn-hold at 15-22 and 22+ (lp): a win is >= +0.05.
- "Jerky on hard turns at medium speed": hard16 at 5-10 and 15-22 (full, and lp), and the limit-cycle peak:
  a win is a >= 10 % fall on BOTH nominal and light_b; a loss is a >= 10 % rise on either.
- Goal metric (cmd vs wheel angular acceleration): mode-A literal fit R2 and phase in 1-3 Hz and 3-8 Hz, and the
  closed-form |alpha/cmd| flatness (small/large amplitude). Pre-registered expectation (BELIEF, to be tested): a
  flat Kp multiple scales |alpha/cmd| by ~g and leaves R2 / phase nearly unchanged; a small-idx schedule raises the
  small-amplitude gain relative to the large (flatness toward 1).

## The lens-level FAIL sentence (written now)
> If no flat Kp multiple, Kp(idx) schedule or map shape raises the lp tracking gain or turn-hold by >= 0.05 in any
> band >= 8 m/s while passing G1-G8 on BOTH nominal and light_b, the P gain cannot close the under-delivery from the
> firmware without an outer-loop penalty, and this lens recommends NO CHANGE.

## Rules on the harness's own limits (from V295-HARNESS.md)
- Quote the plant-alone (lp) sim only for outer-loop metrics (tracking gain, turn-hold, i-share, cmd rms, J_err);
  wheel-motion metrics (rate bands, hard16) only as V294-relative differences under full, bracketed by light_b.
- Never quote simulated dwells/min.
- 15-22 m/s tracking under lp is DIRECTIONAL only (harness H4); say so wherever it is used.
- A ranking that flips between nominal and light_b, or between full and lp, is not supported by this drive.
