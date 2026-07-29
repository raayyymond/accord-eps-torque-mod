---
name: reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction
description: "gp-0x6ad6 (FUN_00037fe6's 'reference model' output) has EXACTLY 3 static references image-wide (1 write, 2 reads), both reads inside FUN_0003a382 itself -- the model's output reaches NOWHERE ELSE in the firmware, closing team-lead's decisive question. Also CORRECTS reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md's '2-state +-8192 selector' claim: disassembly proves a REAL continuous clamp(gp-0x6ad6,+-8192) with pass-through in the middle band. Plus: the model's own authority-scale LERP is a verified no-op (flat 1024 at all 8 breakpoints), all 7 lane weights independently confirmed =1, and a SECOND, previously undocumented validity/plausibility gate found in FUN_0003a382."
metadata:
  type: reference
---

# gp-0x6ad6 reference-model closure + bias-clamp correction — traced 2026-07-29 for team-lead's "reference model" audit

Dispatched to answer 5 questions about FUN_0003a382's "reference model": is it dynamic/LERP/filtered-copy;
what feeds it; where ELSE does its output go (the decisive one, since V56 already muted `gp-0x6ad4`'s
output on-car with zero effect on the 20-25Hz mode); quantify command-blindness; is there a second
residual pattern elsewhere. Full fresh decompile + disassembly + Python byte-scan of `FUN_0003a382` and
`FUN_00037fe6` on `code.bin` (stock, 2086 functions, most-analyzed program per prior sessions' own
recommendation).

## [VERIFIED, 3 independent methods] `gp-0x6ad6` has EXACTLY 3 static references in the WHOLE image — its output reaches NOWHERE outside the FUN_00037fe6/FUN_0003a382 pair

This is the answer to team-lead's central question. Three independent methods agree exactly:
1. `search_instructions(operand_pattern="6ad6")`, program-scoped, 183,429 instructions scanned,
   `truncated:false` → 3 matches.
2. Raw Python disp16 4-byte-form byte scan over the full 1MB `code.bin` (per-opcode rules from
   [[v850e2-extended-disp23-encoding-solved]], target disp `0x952A` = `-0x6AD6 & 0xFFFF`) → same 3
   addresses, byte-identical.
3. Raw Python 6-byte extended-disp23-form scan (same file's decoding formula) → **0 hits**. LE32 literal
   scan for the resolved absolute address `0xFEDF152A` → **0 hits**.

The 3 references:
| Addr | Instr | Function | Role |
|---|---|---|---|
| `0x38142` | `st.h r6,-0x6ad6,gp` | `FUN_00037fe6` | THE WRITE — model producer |
| `0x3a6ba` | `ld.h -0x6ad6,gp,r15` | `FUN_0003a382` | validity/plausibility-gate read (see new finding below) |
| `0x3a798` | `ld.h -0x6ad6,gp,r7` | `FUN_0003a382` | the bias-clamp read (feeds ERR) |

**No other aggregator summand, fault/plausibility check, gain scheduler, or rate limiter anywhere in the
image reads this variable.** Combined with the already-established fact that `FUN_0003a382`'s only output
is `gp-0x6ad4` ([[reference_accord_gp6ad6_engagement_gate_and_36682_closed_loop_math]] — sole reader of
`0xC6AF0`, output-bound branch-agnostically muted by V56), and that **V56 was flashed and moved the
20-25Hz mode by 0% (786x vs 877x, per [[v56-flashed-mute-null-and-costs-damping]])** — this closes the
entire "hidden reference-model side-channel" hypothesis. There is exactly one exit door
(`gp-0x6ad6→...→gp-0x6ad4→aggregator`) and it has already been tested end-to-end on-car with a null result
for the periodic mode.

## [CORRECTION, disassembly-verified] The "bias" is a REAL continuous clamp, NOT a 2-state selector

[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] claimed: *"bias[n] in
{+8192,-8192} ONLY — a 2-state selector... NOT a continuous subtraction of the model."* **This is wrong.**
Register-level trace of `0x3a798-0x3a7ce` (both the decompile's C and a manual instruction-by-instruction
walk agree exactly):

```
0x3a798  ld.h  -0x6ad6[gp],r7      ; r7 = gp-0x6ad6 (model, signed)
0x3a7a2  ld.h  0x7200[tp],r6       ; r6 = cal(tp+0x7200) SIGNED  -- byte-read THIS session: 0xC6200 = 00 20 -> 0x2000 = 8192
0x3a7b0  cmp   r6,r7               ; flags for (model <= +8192)?
0x3a7b2  ld.hu 0x7200[tp],r11      ; r11 = cal UNSIGNED = 8192
0x3a7b6  ble   0x3a7bc             ; if model<=+8192, go check the LOWER bound
0x3a7b8  mov   r11,r7              ; else (model>+8192): r7 = +8192  [clamp-hi]
0x3a7ba  br    0x3a7ca
0x3a7bc  subr  r0,r11              ; r11 = -8192
0x3a7be  sxh   r11
0x3a7c0  cmp   r11,r7              ; flags for (model >= -8192)?
0x3a7c2  bge   0x3a7ca             ; if model>=-8192: r7 STAYS = model, UNCHANGED  <-- PASS-THROUGH
0x3a7c4  ld.hu 0x7200[tp],r7       ; else (model<-8192): r7 = 8192 (unsigned)
0x3a7c8  subr  r0,r7               ; r7 = -8192  [clamp-lo]
0x3a7ca  ld.h  -0x4f60[gp],r8      ; r8 = gp-0x4f60 (raw torque sensor)
0x3a7ce  sub   r7,r8               ; r8 = sensor - r7(bias)
```

`r7` at `0x3a7ca` = **`clamp(gp-0x6ad6, -8192, +8192)`** — a real 3-region clamp. When `-8192<=model<=8192`
the middle branch (`0x3a7c2 bge` taken) leaves `r7` **unchanged from its `0x3a798` load** — i.e. the model
passes through to the bias **continuously and exactly**, not snapped to one of two literals. Saturation to
`±8192` only occurs when `|model|>8192`. Python mirror:
```python
CAL_8192 = 8192   # tp+0x7200 = 0xC6200, byte-read this session: 00 20 -> 0x2000 = 8192
bias = max(-CAL_8192, min(CAL_8192, gp_6ad6))     # REAL clamp, continuous pass-through in [-8192,8192]
ERR  = max(-0x2800, min(0x2800, gp_4f60 - bias))  # 0x3a7ca-0x3a7e6, unchanged from prior sessions
```
**Practical nuance, not a further correction**: whether the bias USUALLY sits at the ±8192 rails in real
driving is a separate, still-open empirical question — it depends on the magnitude of the untraced lanes
below, which nobody has measured. The mechanism claim ("only 2 values, ever") is what's being corrected;
whether saturation is common in practice is unresolved either way.

## [VERIFIED] The model (`FUN_00037fe6`) is a STATIC weighted sum, not a dynamic model, not a sensor copy

Full decompile has **no `z^-1`/persisted state anywhere in this function** — every input is read fresh
each call, no accumulator, no EMA, no plant-like coefficient. Answers team-lead's Q1 directly: it is
case **(b)**, a static per-cycle linear combination — specifically, it is built from **other command/lane
signals**, not from the sensor (`gp-0x4f60` does not appear in `FUN_00037fe6` at all) and not from
motor current or the final aggregated command (`gp-0x6b98` also does not appear).

```python
def model_gp6ad6(gp_6b4a, gate_67ab_ne_1, lanes7, gp_69aa):
    # ALWAYS-included term (unconditional), NEGATED -- 0x37fea/0x38006ish
    iVar4 = -gp_6b4a if (-0x6400 <= gp_6b4a <= 0x6400) else 0
    if gate_67ab_ne_1:      # reduce(gp-0x67ab) != 1 -- open trigger, per prior memory
        def gated(x, half): return x if (-half <= x <= half) else 0
        iVar4 += gated(lanes7['6bc2'], 0x2800)*1   # tp+0x74ae=1 (byte-read this session)
        iVar4 += gated(lanes7['6b60'], 0x3c00)*1   # tp+0x74b2=1
        iVar4 += gated(lanes7['6b2a'], 0x2800)*1   # tp+0x74b3=1
        iVar4 += gated(lanes7['6bce'], 0x2800)*1   # tp+0x74ad=1
        iVar4 += gated(lanes7['6b6e'], 0x2800)*1   # tp+0x74b1=1
        iVar4 += gated(lanes7['6bbc'], 0x2800)*1   # tp+0x74af=1
        iVar4 += gated(lanes7['6b70'], 0x2800)*1   # tp+0x74b0=1  <- LKAS-derived, see below
    uVar3 = 1024      # LERP(gp-0x69aa) -- VERIFIED FLAT 1024 at every breakpoint, see below: NO-OP
    return max(-0x6400, min(0x6400, (iVar4*uVar3) >> 10))   # == clamp(iVar4, +-25600) since uVar3/1024=1.0
```
**All 7 weight bytes independently byte-read this session**: `0xC64AD..0xC64B3` = `01 01 01 01 01 01 01`
(tp+0x74ad..0x74b3) — confirms the prior memory's "unity" claim by fresh read, not inheritance.

**NEW, independently verified this session: the authority-scale LERP (indexed by `gp-0x69aa`) is a
COMPLETE NO-OP.** Byte-read `0xC6ABA-0xC6AD8` (X breakpoints `0,6554,13107,19661,22938,26214,29491,32768`)
— **every single Y value = `0x0400`=1024** (Q10 unity), and the out-of-range fallback `cal(tp+0x7448)` =
`0xC6448` = **also 1024**. So `gp-0x69aa` (the governor-voted Q15 product,
[[reference-accord-fun3a382-engagement-gated-residual-loop]]'s already-resolved identity) has **zero
effect on the model's magnitude at stock cal** — the model's value is determined ENTIRELY by the raw
8-term lane sum, clamped ±25600. This closes an item the prior session flagged as "not independently
re-verified" for a *different* table (L4/gainD_raw) — this is the model's OWN scale, a different LERP,
now fully closed with a clean flat result across all 8 breakpoints plus the fallback.

**Does the model include the commanded/aggregated motor torque?** Answering team-lead's Q2 directly:
- `gp-0x6b98` (final aggregated command) — **NOT present**, checked the whole decompile.
- Motor current — **NOT present**.
- `gp-0x6b70` (LKAS-derived) — **YES, present**, unity weight, own clamp ±8192. Per
  [[reference-accord-fun3a382-engagement-gated-residual-loop]]'s already-traced chain: arb output
  (same 4x-gained `0xC646C` path as the real LKAS command) → `gp-0x6b3c`/`gp-0x6b4c` → `FUN_00038148`
  (6-lane mixer, unity weights, ~16Hz EMA, gain 2.58x) → `gp-0x6b70`. So the model is **partially
  command-aware**: it includes a filtered, gained copy of the LKAS arbitration output, but NOT the final
  delivered torque and NOT any current-loop feedback.
- `gp-0x6b4a` (always-included, negated, unconditional) — **written by `FUN_00026c80`** (the 11-channel
  mixer/classifier, same function that produces `gp-0x67ab`/`gp-0x67ac`/`gp-0x6b4c`), via a genuinely
  complex chain (a torque-rate-`gp-0x6a62`-indexed LERP + a rate-limited/slew accumulator toward it, per
  full decompile at `0x27722-0x277be`). **NOT fully characterized physically this session** — flagged
  open, next step is isolating the slew-rate cal `tp+0x7194`/`0xC6194`(⚠ different register than the
  already-known-dead `0xC6194` LKAS rate limiter, DOUBLE CHECK before reusing that address) and the
  `gp-0x6a62`-indexed LERP endpoints (`tp+0x7700-0x770c`). **Read by 4 functions besides its own
  writer**: `FUN_000352b4` (the `gp-0x6b86` aggregator lane), `FUN_00042af8` (the shaper/AUTHORITY
  producer), `FUN_00043e44` (Monitor M2, hard-shutdown), and `FUN_00037fe6` (this model) — i.e. it's a
  widely-shared synthetic signal, not exclusive to the model.
- Other 5 lanes (`gp-0x6bc2`,`gp-0x6b60`,`gp-0x6b2a`,`gp-0x6bce`,`gp-0x6bbc`): partial producer map only —
  `gp-0x6bc2`←`FUN_00036f30`(`0x36fea`), `gp-0x6b2a`←`FUN_0003b49a`(`0x3b664`), `gp-0x6b6e`←`FUN_0003b338`
  (`0x3b410`). **`gp-0x6b60`, `gp-0x6bce`, `gp-0x6bbc` show ZERO writers** via `search_instructions`
  (unrestricted mnemonic) — **NOT corroborated with a disp16/disp23 Python byte scan this session**
  (budget) — flag as OPEN, not declared dead, per this kit's own standing policy on null results.

**Bottom line for Q1/Q2**: the "reference model" is not a physical/dynamic model at all — it is a static
per-cycle recomposition of several of the SAME assist-chain lanes (friction/damping/boost-family signals
plus one LKAS-derived term) that separately also feed the real aggregator (`FUN_0003aa2c`). It partially
"knows about" the LKAS command (via `gp-0x6b70`) but is blind to the actual delivered torque and to motor
current.

## [NEW FINDING] A second, previously-undocumented gate zeroes `gp-0x6ad4` outright — independent of the authority-ceiling gate

Disassembled `0x3a698-0x3a6e2` (upstream of the bias/ERR code above). This is a validity/plausibility
check, structurally separate from the already-documented authority-ceiling mute
([[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]]'s `0xC6AF0` mechanism):
```
bVar1 = NOT( hw_status_nibble_flag(gp-0x2584 or gp-0x2588, bit 31 via shr 0x1c + carry) )
        AND |gp-0x6ad6| <= 0x6400   (uses THE FIRST of gp-0x6ad6's 2 reads, 0x3a6ba)
        AND |gp-0x4f60| <= 0x6400
        AND gp-0x6ac0 (motor rate) < 0x32c9 (12996)
if not bVar1:
    gp-0x6767 = 0            ; a "valid" flag, also read elsewhere in the function
    gp-0x6ad4 = 0            ; EARLY EXIT -- entire P/I/D skipped this cycle
    return
```
This is a THIRD kill-path for `gp-0x6ad4` (alongside the authority-ceiling mute and the `gp-0x67fe==0`
EPS-assist-down gate already on record) — a sensor/model-range sanity check plus a motor-rate ceiling.
Not obviously engagement-linked (no `STEER_STATUS`/`gp-0x6806` read here). Not pursued further this
session — flagged for whoever next audits `gp-0x6ad4`'s full gate inventory.

## [Q5] Second "measured minus predicted" pattern — already on record, not re-derived fresh

`FUN_00036682` (readers #5/#6 of the `0xC646C` gain,
[[reference_accord_c646c_gain_feedback_vs_forward_classification]]) has the SAME shape:
`sVar15 = gp-0x6b48 + POLARITY*(gp-0x4f60*GAIN>>15) - gp-0x6b46[prior own output]` — a closed-loop
measured-minus-prior-estimate error feeding a hysteretic tracker whose output sums into the SAME
aggregator (`gp-0x6b98`). Already characterized in
[[reference_accord_gp6ad6_engagement_gate_and_36682_closed_loop_math]]: `y[n]=y[n-1](1-2α)+αK·x[n]`,
DC gain K/2, **~0.005-0.011 counts/count at 21Hz — decisively ruled out as a 21Hz carrier**, though real
as a structural pattern. **No exhaustive image-wide search for OTHER instances of this shape was run this
session** (budget) — flagged open if a broader sweep is ever wanted.

## Open items
- `gp-0x67ab`'s trigger (whether the 7-lane sum is usually included or usually skipped) — inherited open
  item, not re-investigated.
- `gp-0x6b4a`'s exact physical identity — partially traced (torque-rate/`gp-0x6a62`-indexed, slew-limited),
  not fully closed.
- `gp-0x6b60`/`gp-0x6bce`/`gp-0x6bbc` zero-writer results — NOT corroborated with a raw byte scan, treat as
  "at least this many" per this kit's undercounting history, not as confirmed-dead.
- Whether the bias term actually SATURATES at ±8192 often in real driving (a measurement question, not a
  structural one) — the mechanism correction above does not resolve this.

## Related
[[reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse]] — the file whose "2-state
selector" claim this entry corrects; its P/I/D structure, ADD-sign proof, and frequency response are
UNAFFECTED by this correction (they concern the combine stages downstream of the bias, not the bias itself).
[[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]] — the authority-ceiling mute this
entry's new validity-gate finding is a SEPARATE, additional kill-path alongside.
[[reference-accord-fun3a382-engagement-gated-residual-loop]] — source of the `gp-0x6b70`/LKAS-chain and
`gp-0x69aa` identity this entry reuses and (for the authority-scale LERP) newly closes as a no-op.
[[v56-flashed-mute-null-and-costs-damping]] — the on-car test that makes the gp-0x6ad6-closure finding
decisive: this whole lane's only exit is already known to be a null for the periodic mode.
[[v850e2-extended-disp23-encoding-solved]] — the byte-scan methodology used for the 3-method closure.
