---
name: reference_accord_gp6b98_aggregator_definitive_lane_table_v57
description: Definitive fresh re-disassembly of FUN_0003aa2c (11 summands, not 8/9) for the post-V56 (gp-0x6ad4 eliminated) lane audit. Identifies r24/r26 (torque-RATE lanes) as the new top 21Hz-carrier suspect (0dB, unfiltered, same-signed-reinforcing, confirmed 1kHz, never previously ranked this way) and gp-0x6bbe (boost) as the second, contingent on FUN_00022ca0's unresolved task rate. Corrects the FUN_00036682 alpha (6, not 14) and its dB (-46 to -58dB, not -26.6dB), and a tp+0x718a/tp+0x727e cal conflation in the prior inventory.
metadata:
  type: reference
---

# gp-0x6b98 aggregator: definitive lane table, re-traced 2026-07-29 for team-lead's post-V56 "which lane next" audit

Full fresh disassembly of `FUN_0003aa2c` on stock `code.bin` (2086-function analysis). Builds on and
partially corrects [[reference_accord_gp6b98_aggregator_full_lane_inventory]]. Dispatched after V56
(FLASHED, per `docs/BUILD-LINEAGE.md`) empirically eliminated `gp-0x6ad4`/`FUN_0003a382` as the 21Hz
driver — this session's job was to re-rank what's left with hard addresses.

## [VERIFIED, disasm 0x3aca8-0x3ace6] The full combine has 11 summands, not 8 or 9

```
0003acc8 mov  r26,r6      r6  = r26-lane (adaptive torque-RATE lane, physical reg r26)
0003acca add  r24,r6      r6 += r24-lane (physical reg r24)
0003accc add  r6,r8       r8  = gp-0x6b86 (magnitude/peak-hold)
0003acce add  r8,r12      r12 = gp-0x6bd0 (damping)
0003acd0 add  r12,r10     r10 = gp-0x6bbe (boost)
0003acd2 add  r10,r15     r15 = gp-0x6b26 (friction)
0003acd4 add  r15,r16     r16 = gp-0x6b62 (return-centre)
0003acd6 add  r16,r13     r13 = gp-0x6ad4 (resonance/PID -- ELIMINATED V56)
0003acd8 add  r13,r7      r7  = gp-0x6b4c (LKAS)
0003acda add  r7,r28      r28 = gp-0x6ade (feedforward)
0003acdc jarl 0x00036682,lp
0003ace6 add  r14,r10     r10 = running total + FUN_00036682()'s return
```
Clamps (verified `addi`/`cmovc` range-gate idioms immediately above): 6b62 +/-0x2000(8192), 6b4c
+/-0x2800(10240), 6ade +/-0x400(1024), 6ad4 +/-0x2800(10240), 6b26 +/-0x400(1024), 6bbe +/-0x800(2048),
6bd0 +/-0x800(2048), 6b86 +/-0x3000(12288), r26 +/-0x2000(8192), r24 +/-0x2000(8192). `FUN_00036682`
self-clamps internally (pre-filter +/-0x200, per [[reference_accord_c646c_gain_feedback_vs_forward_classification]]).

**r24/r26 (the torque-rate lanes documented in [[reference-accord-r26-adaptive-lane-full-trace-and-sign]])
reproduce byte-for-byte this session** (`0x3ab3a` etc match exactly) and ARE two of the 11 summands --
they were missing from the team-lead's brief and from the prior inventory's headline count. They're
computed unconditionally every cycle (stored to telemetry `gp-0x6adc`/`gp-0x6ada` at `0x3ad4e`/`0x3ad5a`
regardless of branch) but only ADDED to the torque total in the full (`gp-0x67ac`!=1) path.

**The narrow-path gate reuses the SAME final add, not a separate sum** [NEW, this session]:
```
0003ac5c be 0x3ac78     [gate==1 -> narrow path, skips the whole 0x3ac78-0x3acdc block]
0003ac6a cmove r28,r14,r14   r14 = (cal 0xC74AB==0) ? gp-0x6ade : 0
0003ac70 cmovne 0,r16,r10    r10 = (cal 0xC74AC==0) ? gp-0x6b62 : 0
0003ac74 add  r7,r14         r14 += gp-0x6b4c (LKAS, always ungated)
0003ac76 br   0x3ace2  -> falls into the SAME "add r14,r10" at 0x3ace6 the full path uses.
                           FUN_00036682 is not called in this branch.
```
Confirms [[reference-accord-gp67ac-aggregator-lane-suppression-gate]]'s narrow-path term list exactly,
now with the exact reuse mechanism.

## [VERIFIED, fresh byte reads] Frequency response, corrected/extended

**r24/r26 -- UNFILTERED, 0dB, confirmed 1kHz.** Input is `dtorque=clamp(gp-0x4f62,+/-0x1400)` (first
difference of the torque sensor). No EMA/IIR anywhere in either lane -- only static LERP gain tables and
a +/-0x2000 output clamp. `FUN_0003aa2c`'s sole caller is `FUN_0002214a` (confirmed 1kHz per
[[control-task-tick-confirmed-1khz]]). **Structurally identical in shape to the just-eliminated gp-0x6ad4
D-branch: unfiltered, same-signed as the sensor's own rate of change.** NEW FRAMING: prior sessions
tracked r24/r26 only for their own sign-consistency question, never ranked them as 21Hz carriers -- with
6ad4 gone, they are now the single cleanest 0dB/same-signed-reinforcing lane on record.

**gp-0x6bbe (boost) / gp-0x6bd0 (damping) -- same primary EMA, NEW decisive rate ambiguity.**
`FUN_00034a72`/`FUN_00034350`: `y[n]=y[n-1]+((gp-0x4f60[n]*32-y[n-1])*alpha)>>10` (single-subtraction,
confirmed NOT the double-subtract danger form). Alpha freshly read: boost `tp+0x7372`=`0xC6372`=**205**
(`cd 00`), damping `tp+0x736e`=`0xC636E`=**205** (`cd 00`) -- identical, alpha=205/1024=0.2002.
**`get_function_callers` shows BOTH are called by `FUN_00022ca0`, the assist-shaping task -- NOT
`FUN_0002214a` (confirmed 1kHz).** `FUN_00022ca0`'s own rate is still unresolved (its own
`get_function_callers` returns null -- consistent with an RTOS task-table entry, per the kit's task-table
precedent, not a static call site). Effect of this ambiguity, computed both ways at 21Hz:
- fs=1000Hz: |H|=0.2002/sqrt(1-2*0.7998*cos(2*pi*21/1000)+0.7998^2)=0.8614 -> **-1.30dB** (near-transparent)
- fs=100Hz: same formula, different omega -> |H|=0.1797 -> **-14.9dB** (real attenuation)
**Single most decisive open question for boost/damping.** Next step: find `FUN_00022ca0`'s actual RTOS
task period (table, not caller).

**gp-0x6bbe polarity -- NEW finding.** `FUN_00034a72`'s final combine only multiplies by
`assist_polarity(gp-0x6752)` -- no motion/velocity sign flip anywhere in the function (full decompile
checked). **Boost is SAME-SIGNED as the raw torque sensor -- reinforcing, not opposing.** Damping
(`FUN_00034350`, sign flip at `0x3469e-0x346a2` per [[reference-accord-fun34350-damping-term-live-and-gated]])
explicitly negates by `sign(gp-0x6abe)` (filtered MOTOR rate) -- genuinely velocity-opposing. **Boost and
damping are NOT symmetric in sign character despite sharing alpha=205/1024** -- boost is the
proportional-dominated-AND-positive-feedback shape the team lead is hunting for, not just the eliminated
6ad4.

**gp-0x6b26 (friction) -- driven by MOTOR RATE not torque sensor, -14.5dB, ~0 net phase.**
`FUN_00036c12`'s only input is `gp-0x6c2c`, a 3-stage cascade off `gp-0x4f50` (NOT gp-0x4f60): (1) EMA
alpha=37/128 [[reference-accord-fun41464-sign-filter-phase-response]], phase-gated 5/16 -> fs_eff=312.5Hz;
(2) a discrete derivative (1-z^-1 highpass); (3) a 2nd EMA, NEW this session,
`tp+0x50dc`=`0xC40DC`=**22** (Q6, alpha=22/64=0.34375). At 21Hz/fs_eff=312.5Hz: stage1
|H|=0.633 <-39.65deg, stage2(delta) |H|=0.419 <+77.9deg, stage3 |H|=0.712 <-33.85deg -> combined
**|H|=0.189 (-14.5dB) <+4.4deg vs gp-0x4f50**. Whether this reads as damping or anti-damping re: the
SENSOR needs the plant's motor-rate-to-torque-sensor phase at 21Hz -- [OPEN, plant-dependent], not
resolvable from firmware. `FUN_00036c12` itself is called by `FUN_0002214a` (1kHz, confirmed) -- no extra
hold beyond the shared cascade's own 312.5Hz effective rate.

**gp-0x6c2e (cross-term feeding BOTH boost and damping) -- resolved, weaker 3rd pole.** Same first two
cascade stages as gp-0x6c2c, but its own 3rd-stage EMA uses `tp+0x50da`=`0xC40DA`=**3** (Q7,
alpha=3/128=0.0234) -> at 21Hz/312.5Hz: |H|=0.0150 <-36.5deg vs gp-0x4f50. Static scalar gains applied
after: boost `tp+0x7370`=`0xC6370`=**2560** (x80 after >>5), damping `tp+0x736c`=`0xC636C`=**4096** (x128
after >>5) -- pure scale, no shape change. Secondary to each lane's own primary torque-sensor EMA.

**gp-0x6b62 (return-centre) -- hard slew-rate ceiling, confirmed 1kHz.** `FUN_00036388` (caller
`FUN_0002214a`, confirmed): state `gp-0x6a82` moves by **exactly +/-1/cycle** (hysteresis vs
`tp+0x718a`=`0xC618A`=**1024** and `tp+0x727e`=`0xC627E`=**20**, both freshly read). ⚠ CORRECTS the prior
inventory's "hysteresis tp+0x718a=20" -- that conflated the two cals; both addresses now independently
confirmed by direct read this session. At confirmed fs=1000Hz: max trackable 21Hz peak amplitude =
1000/(2*pi*21) = **7.6 counts** -- any realistic assist-torque oscillation is structurally capped near
this ceiling. Ruled out by slew-rate, not attenuation math.

**gp-0x6ade (feedforward) -- corroborated dead, 2 independent methods.** Whole-image (no function filter)
`search_instructions` on "6ade": 2 hits total -- the known read at `0x3aa48`, and `0x56ad8: bnc
0x00056ade` (branch-target-address text collision, excluded, same false-positive class as elsewhere in
this kit). A from-scratch Python disp16 byte scan of the raw file (st.h op=0x3B AND st.b op=0x3A, all
reg2 including 0 per the store-zero trap in [[v850e2-extended-disp23-encoding-solved]]) over the whole
1,048,576-byte image: **0 stores**, 1 load matching Ghidra's exactly (same address/bytes). Did NOT
independently validate the 6-byte extended-disp23 STORE encoding this session (no calibration example
available for stores, only loads exist as precedent) -- corroborated 2 ways not 3, flagged not certified.
Best read: gp-0x6ade is very likely a permanently-zero RAM cell in production.

**FUN_00036682 -- settles the 6-vs-14 discrepancy, MORE attenuated than the last recorded estimate.**
Fresh read `tp+0x73d2`=`0xC63D2`=**6** (`06 00`) -- confirms the more recent value, not 14. Closed-loop
form (per [[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]]):
`y[n]=y[n-1]*(1-2a)+a*K*x[n]`, alpha=6/1024=0.00586, a=0.98828. Confirmed stock `0xC646C`=**891** (`7b
03`) -> K=0.0272 -> **|H|=0.00121 -> -58.3dB** at 21Hz/1000Hz. If the on-car 4x value (3564) is what's
flashed -> K=0.1088 -> |H|=0.00485 -> **-46.3dB**. Supersedes the older "-26.6dB" figure -- this lane is
far more deeply attenuated than previously recorded.

## [VERIFIED] 0xC646C (4x gain) touches exactly ONE of the 11 lanes directly

Scoped `search_instructions(function=X, operand_pattern="746c")` this session on `FUN_00036c12` (121
instrs), `FUN_00036388` (206), `FUN_00034a72` (625), `FUN_00034350` (399), `FUN_000352b4` (712),
`FUN_00041464` (597), `FUN_0003aa2c` (280) -- **0 hits in every one.** Combined with the existing
exhaustive whole-image 6-reader enumeration in
[[reference_accord_c646c_gain_feedback_vs_forward_classification]]: of the 11 summands, only the
`FUN_00036682` return reads 0xC646C directly (readers #5/#6). `gp-0x6b4c`/LKAS carries it too but only
via the FORWARD/intended path (reader #1, arbitration). Given FUN_00036682 is now the MOST attenuated
lane in the table (-46 to -58dB), **the 4x gain is not reaching the aggregator through any
meaningful-magnitude feedback lane** -- its only material effect remains the intended LKAS-authority path.

## Ranking for the next lever (post-V56)

1. **r24/r26** -- 0dB, unfiltered, confirmed 1kHz, same-signed-reinforcing. Top suspect, never ranked
   this way before (prior work only examined r26 for its own sign-consistency question).
2. **gp-0x6bbe (boost)** -- -1.3dB if fs=1kHz / -14.9dB if fs~100Hz, same-signed-reinforcing. Contingent
   entirely on `FUN_00022ca0`'s unresolved rate.
3. gp-0x6bd0 (damping) -- same magnitude ambiguity as boost but genuinely velocity-opposing; not a
   suspect, a stabilizer.
4. gp-0x6b4c (LKAS) -- -12dB fixed, externally commanded.
5. gp-0x6b26 (friction) -- -14.5dB vs motor rate (different signal domain), plant-dependent verdict.
6. gp-0x6b86 (magnitude) -- peak-hold resists phase reproduction (prior finding, unchanged).
7. FUN_00036682 -- -46 to -58dB, ruled out by magnitude.
8. gp-0x6b62 (return-centre) -- ruled out by slew-rate (<=7.6 counts pk).
9. gp-0x6ade (feedforward) -- likely always 0, contributes nothing.
10. gp-0x6ad4 (resonance/PID) -- ELIMINATED on-car, V56.

## What's still open
- `FUN_00022ca0`'s actual task rate -- decisive for boost/damping's dB, unresolved this session (no
  static caller; get_function_callers returns null, consistent with an RTOS task-table entry).
- Friction's true damping/anti-damping character vs the torque sensor -- needs the plant's motor-rate-to-
  torque-sensor phase relationship at 21Hz, not a firmware fact.
- gp-0x6ade's 6-byte extended-disp23 STORE encoding not independently validated (no store calibration
  example existed to check against, only loads).

## Related
[[reference_accord_gp6b98_aggregator_full_lane_inventory]] -- the prior full inventory this session
re-derives and partially corrects (tp+0x718a/tp+0x727e conflation, FUN_00036682's alpha and dB).
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] -- r24/r26's internal structure, reproduced
byte-for-byte this session; this file adds the "0dB carrier" ranking framing that memory didn't have.
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] -- source of the 6-reader
enumeration this session's per-lane scoped search corroborates.
[[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]] -- source of FUN_00036682's
closed-loop transfer function form, whose alpha this session settles at 6 (not 14) with fresh dB numbers.
[[reference-accord-fun41464-sign-filter-phase-response]] -- source of the alpha=37/128 first stage this
session's friction/gp-0x6c2c cascade builds on, plus the new gp-0x6c2c/gp-0x6c2e 3rd-stage coefficients.
