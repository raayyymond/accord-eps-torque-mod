---
name: reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse
description: "FUN_0003a382's 3 parallel branches are a genuine discrete PID (P=torque-proportional zero-phase, I=true anti-windup-clamped integrator, D=raw backward-difference derivative) on an ERR term that is torque sensor minus a PIECEWISE-CONSTANT (+-8192) bias -- NOT a continuous subtraction of the gp-0x6ad6 model as previously framed. gp-0x6ad4 is proven ADDED (never subtracted) into the FUN_0003aa2c aggregator sum at the disassembly level, with the shared polarity flag gp-0x6752 boot-initialized to +1 (no inversion). Computed z-domain frequency response at 3/5/8/21Hz: P-dominated (near-zero phase) at 3-8Hz, D becomes comparable to P by 21Hz (phase leads to +42..+55 deg). Also closes Q4: byte-scan-confirmed FUN_0003a382 is the SOLE consumer of the 0xC6AF0 LERP table image-wide."
metadata:
  type: reference
---

# FUN_0003a382 full P/I/D decode + aggregator sign proof + frequency response — traced 2026-07-28 for team-lead's V56 damping-sign question

Dispatched after V56 (0xC6AF0 Y[0]/Y[1] 32768->0, unconditionally zeroing gp-0x6ad4 per
[[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]]) was flashed and the operator
reported: 21Hz unchanged, but damping felt REMOVED with a NEW resonance at a few Hz. Task: settle
whether gp-0x6ad4 is net-damping from the code. Full fresh decompile+disasm of `FUN_0003a382` and its
consumer `FUN_0003aa2c` on stock `code.bin`, plus direct Python byte reads of every constant (2 methods:
Ghidra `read_memory` + raw file read, agree exactly).

## [VERIFIED] The three combine branches are literally P, I, D — not "3 similar lag stages"

```
ERR[n] = clamp(gp-0x4f60[n] - bias[n], +-0x2800)        # 0x3a7ca-0x3a7e6
  bias[n] in {+cal(0x7200)=+8192, -cal(0x7200)=-8192} ONLY -- a 2-state selector keyed on
  gp-0x6ad6's own value crossing +-8192, NOT a continuous subtraction of the model.
  ==> CORRECTS the "residual = sensor minus continuous model" framing in prior memory/briefs:
  for AC content faster than the rate gp-0x6ad6 crosses +-8192, bias is DC, and ERR's AC content
  IS gp-0x4f60's AC content at unity gain / zero phase.

# Stage A = PROPORTIONAL (0x3a7e8-0x3a826)
P[n] = ((gainA_raw[motor_rate] * ERR[n]) >> 10) * 32
  gainA_raw = L1 table (X=[300,2000,4000], Y=[256,256,225,153] at 0xC6B1C.., byte-confirmed)
  Stage A's own "lag" pole = cal 0xC6450 = 1024 = unity -> state_new==target EXACTLY (identity, zero phase)

# Stage B = INTEGRAL, anti-windup clamped (0x3a7e6-0x3a83c)
I_raw[n] = I[n-1] + (gainB_raw * ERR[n]) >> 10
  gainB_raw = L2 table, FLAT 98/1024 at 0xC6B08.. (byte-confirmed, all 4 Y points =98)
  I[n] = clamp(I_raw[n], headroom relative to ceiling and P[n])   # real anti-windup, not evaluated in linearized model

# Stage C = DERIVATIVE, raw backward difference (0x3a832-0x3a87a)
Draw[n] = clamp(((ERR[n]-ERR[n-1]) * gainC_raw) >> 10, +-0x2800)
  gainC_raw = L3 table, FLAT 2048/1024=2.0 at 0xC6ADC.. (byte-confirmed, all 4 Y points =2048)
D[n] = Draw[n] * 32
  Stage C's own smoothing pole = cal 0xC644A = 1024 = unity -> identity again (raw derivative reaches combine unattenuated)

# Combine (0x3a874-0x3a8a0)
combine[n] = ((D[n] + I[n] + P[n]) >> 5) * gainD_raw>>10 * polarity(gp-0x6752) * validity
gp-0x6ad4[n] = clamp(combine[n], -ceiling[n], +ceiling[n])
```
`gainD_raw` (L4, tp+0x77b0-region, gp-0x671a-indexed): inherited from
[[reference-accord-fun3a382-engagement-gated-residual-loop]] as ~1024/1024=1.0 no-op — attempted a fresh
byte read this session but could not cleanly re-derive the table's exact field layout in the time available
(the walker's header/gate/X/Y offsets didn't line up the way L1/L2/L3's did); **NOT independently
re-verified this session**, flagged explicitly rather than silently re-asserted.

All 6 numeric constants above (0xC6450, 0xC644A, and the 3 LERP tables' full X/Y arrays) were confirmed
by BOTH Ghidra `read_memory` AND a raw Python file read of `code.bin` — identical results both ways.

## [VERIFIED, disassembly-level] gp-0x6ad4 is ADDED, never subtracted, into the aggregator

`FUN_0003aa2c` (the gp-0x6b98 aggregator, 9 lanes) at `0x3aca8-0x3acda`:
```
0x3aca8  ld.h -0x6ad4[gp],r6        # load gp-0x6ad4
0x3acbc  addi 0x2800,r6,r9          # range-gate bias (|gp-0x6ad4|<=0x2800 validity check)
0x3acc4  cmovc 0x0,r6,r13           # r13 = in-range(gp-0x6ad4) ? gp-0x6ad4 : 0  -- NO SIGN FLIP
0x3acd6  add r16,r13                # r13 += (gp-0x6b62 term)
0x3acd8  add r13,r7                 # r7  += r13   <- gp-0x6ad4's term folded in via plain ADD
0x3acda  add r7,r28                 # r28 += r7    <- running total
```
Every term in this 9-lane chain (`gp-0x6b62,-0x6b4c,-0x6ade,-0x6ad4,-0x6b26,-0x6bbe,-0x6bd0,-0x6b86` plus
`FUN_00036682`'s return) reaches the sum via a plain `add` instruction — none are negated at this stage.
This total is clamped +-0x2800 and stored to `gp-0x6b94`/`gp-0x4ce0` (shadow-lockstep pair), read onward by
the governor `FUN_0004503c` (`0x453e0`) per existing chain docs
([[reference_accord_gp6b98_aggregator_full_lane_inventory]], [[reference_accord_tva_downstream_chain]]).

**Polarity resolved**: `gp-0x6752` (the shared polarity/validity byte multiplied into gp-0x6ad4's own
combine AND into two other aggregator pre-sum terms) is set to literal `1` at boot in `FUN_000490ac`
(`0x490b6-0x490c0`, shadow-checked against `gp-0x4c2d`) — i.e. **polarity = +1, no inversion**, in normal
running. So gp-0x6ad4 reaches the aggregator with the SAME sign its own P+I+D combine produces from ERR
(torque sensor), and is added exactly like the other reinforcing lanes (`gp-0x6bbe` boost, `gp-0x6b26`
friction, `gp-0x6bd0` damping) — no hidden inversion anywhere in this chain.

## [VERIFIED, z-domain, small-signal] Frequency response at 3/5/8/21Hz (fs=1000Hz, non-saturating assumption)

Linearized (clamps/anti-windup ignored — valid only while not saturating), computed both by direct
time-domain simulation AND closed-form z-transform (agree to 4 decimal places):
```
H(z) = [ gainA_raw/1024 + (gainB_raw/1024)/(32*(1-z^-1)) + (gainC_raw/1024)*(1-z^-1) ] * gainD_raw/1024
```
| gainA_raw (motor-rate) | 3Hz gain/phase | 5Hz | 8Hz | 21Hz |
|---|---|---|---|---|
| 256 (low rate)  | 0.279 / -25.7 deg | 0.255/-7.3 | 0.257/+9.2 | 0.361/+41.8 |
| 225 (mid rate)  | 0.252 / -28.6 deg | 0.225/-8.3 | 0.228/+10.4| 0.339/+45.2 |
| 153 (high rate) | 0.194 / -38.7 deg | 0.155/-12.0| 0.159/+15.0| 0.294/+55.0 |

Per-branch magnitude breakdown (as fraction of the /32 combine, gainA=256 row): P/32=0.250 (flat, all f);
|I|/32 falls 0.159->0.023 (3Hz->21Hz, integrator rolls OFF with frequency as expected); |D|/32 RISES
0.038->0.264 (3Hz->21Hz, derivative rises with frequency as expected). **At 3-8Hz the combine is
P-dominated (near-zero digital phase relative to ERR — a torque/stiffness-like term)**; **by 21Hz D has
grown to be comparable to or exceed P**, pulling phase to a leading +42..+55 deg.

**This differs materially from the hand-symbolic phase estimate in
[[reference-accord-fun3a382-engagement-gated-residual-loop]] ("-3.3 to -5.4 deg net lag... proportional-
dominated 8-10:1 over I+D")** — that estimate is not reproduced by this session's rigorous z-domain calc,
most likely because it was evaluated at a different (probably much lower, near-DC) operating condition
where D's magnitude (which scales with frequency) is genuinely small. Flagging as an open discrepancy
rather than silently overwriting; this session's numbers are cross-validated two independent ways
(simulation + closed-form) and are for the FEW-HZ AND 21HZ band specifically, which the prior estimate's
range ("across L1's full range") may not have targeted the same way.

## [VERIFIED, 2 methods] Q4 — FUN_0003a382 is the SOLE reader of the 0xC6AF0 LERP table image-wide

Ghidra `search_instructions` on "7af0"/"7afc"/"7afe" PLUS a raw unaligned Python byte scan over
`[0x13000,0xC4FFC)` for the literal displacement (including the `ld.hu`-family `disp|1` quirk) both found
only the two already-known reader instructions inside `FUN_0003a382` (`0x3a636` base, `0x3a650` Y[0]).
Every other raw byte-pattern hit was individually adjudicated and excluded: branch-target-address text
collisions (Ghidra's own false-positive class), an EP-relative (not TP-relative) coincidence at `0x20ddc`,
an R0-relative store at `0xc92`, and 2 hits that decoded to non-memory instructions (`divq` operand-free,
and mid-bytes of an unrelated 32-bit immediate `mov`) on manual disassembly check. `Y[1]` (0x7afe) has
**zero literal-displacement occurrences anywhere**, which is architecturally expected, not a scan gap: the
LERP walker reaches Y[1] exclusively via pointer increment (`r13+2`) from the Y[0] base, never as its own
literal operand. **Not separately re-checked against the 6-byte V850E2 extended-disp23 encoding this
session** — flagged as a residual gap, though both known real readers use the cheaper 4-byte form despite
sitting deep in cal space, which weakens (does not eliminate) the concern.

## Related
[[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]] — the ceiling/mute mechanism this
session's P/I/D decode and ADD-sign proof sit downstream of; V56 built from that file's finding.
[[reference-accord-fun3a382-engagement-gated-residual-loop]] — source of the gainD~1024 claim (inherited,
unverified this session) and the differing phase estimate flagged above.
[[reference_accord_gp6b98_aggregator_full_lane_inventory]], [[reference_accord_tva_downstream_chain]] —
downstream path from the aggregator's gp-0x6b94/gp-0x4ce0 output through the governor toward gp-0x6b98.
