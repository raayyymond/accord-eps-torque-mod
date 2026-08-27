---
name: reference_accord_gp6adc_lane_gate_polarity_and_tp_cal_offby1000
description: "Three corrections to the record, each byte- or disassembly-verified. (1) My own memory reference_accord_r24r26_live_gain_is_default_lerp states the r26/lane-A block is 'skipped only when BOTH gp-0x6b5e!=0 AND the rare gp-0x671a>=5' -- that is INVERTED. Lane A (gp-0x6adc) is zero-forced whenever gp-0x6b5e!=0 in the COMMON regime; it is live only because gp-0x6b5e computes to EXACTLY 0 when gp-0x6bda rides outside +-384, which route 79 measured at 100% of 75,227 engaged frames. The conclusion (lane live) survives; the reason is opposite, and the real gate SWITCHES THE LANE OFF near centre. (2) TRACE-2026-08-10 section 5's aggregator table carries the off-by-0x1000 tp trap on every rate-lane cal: 0xC743E/0xC7440/0xC7442/0xC7444/0xC7446/0xC71F6/0xC719C/0xC71A6/0xC73D2 should all be 0xC6xxx -- sixth recurrence. (3) The 'gp-0x683c has zero writers' claim SURVIVES a raw scan, but only after the op-specific displacement rule: the four candidate st.b sites decode to gp-0x683b, not gp-0x683c."
metadata:
  type: reference
---

# Three corrections found while re-censusing `FUN_0003aa2c` — 2026-08-27, task `agg-census`

Program `code.bin` (stock). Fresh `disassemble_function(0x3aa2c)` + `decompile_function(0x361c8)` +
raw Python LE byte reads.

## 1. 🛑🛑 The `gp-0x6adc` (register `r26`) lane gate — polarity INVERTED in my own memory

`disassemble_function(0x3aa2c)`, the exact rungs:
```
0003aa70  ld.bu -0x671a[gp],r12
0003aa78  ld.bu 0x74fa[tp],r14        ; cal(0xC64FA) = 5
0003aa7c  cmp   r14,r12               ; r12 - r14
0003aa7e  bc    0x0003aa88            ; taken iff gp-0x671a < 5   (measured 100% of the time)
0003aa80  mov 0x1,r2 / ld.hu 0x7136[tp],r22   ; NOT taken (671a>=5): r22 = cal(0xC6136) = 0
0003aa88  mov 0x0,r2 / ld.hu 0x7138[tp],r22   ; TAKEN     (671a< 5): r22 = cal(0xC6138) = 1
0003aa92  cmp 0x1,r22 / 0003aa98 setfe r10    ; r10 = (r22 == 1)  = 1 in the live regime
0003aaa0  cmp r0,r9 / 0003aaa2 setfne r6      ; r6  = (gp-0x6b5e != 0)
...
0003ab2a  cmp   r0,r6
0003ab2c  be    0x0003ab36            ; gp-0x6b5e == 0  -> COMPUTE the lane
0003ab2e  cmp   r0,r10
0003ab30  cmovne 0x0,r6,r6            ; r10 != 0  ->  r6 = 0
0003ab34  bne   0x0003ab78            ; r10 != 0  ->  SKIP the compute, lane value = 0
```
Bytes verified: `0xC6136 = 00 00`, `0xC6138 = 01 00` (dump `0xC6130..0xC6141` =
`00 00 01 00 e8 03 00 00 01 00 …`).

⇒ **Lane A is computed iff `gp-0x6b5e == 0` OR `gp-0x671a >= 5`.** The second arm is starved
(0/186,321 + 0/53,991 on-car). ⇒ **in practice the lane is live iff `gp-0x6b5e == 0`.**
`reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy` says the block is
*"skipped only when BOTH `gp-0x6b5e!=0` AND the rare `gp-0x671a>=5` hold"* — **that is backwards.**

**Why it is nevertheless live** — the reason nobody had written down. `decompile_function(0x361c8)`:
```
gp-0x6b5e = POL · ((LERP(gp-0x6bda) · cal(0xC63C2)) >> 10)      # sign flipped by gp-0x6bf0
  X @0xC66CE = [-384, -128, 128, 294, 384]     Y @0xC66D8 = [0, 4762, 4762, 717, 0]
  |gp-0x6bda| >= 384  ->  Y = cal(0xC66E0) = 0   ;  cal(0xC63C2) = 1024
```
Route 79 (V92) measured `gp-0x6bda ∈ (−397, 384)` at duty **0.0000 over 75,227 engaged frames**
(a kit memory puts its hands-off value at ~9262) ⇒ `gp-0x6b5e ≡ 0` engaged ⇒ **lane A LIVE.**

🛑 **But the gate is NOT robust the way the old wording implied.** The moment `gp-0x6bda` enters
±384 — which is what a return-to-centre / detent event does — `gp-0x6b5e` jumps to `POL·4762` and
**the whole `gp-0x6adc` lane switches to hard zero at 1 kHz.** A switching lane inside a lightly
damped loop is a structural nonlinearity, and it shares its gate quantity with the return-centre
lane `gp-0x6b62` (`FUN_00036388` also reads `gp-0x6b5e` @`0x36390`).

⊕ Register→cell naming re-confirmed from the stores: `0x3AD4E st.h r26,-0x6adc[gp]` and
`0x3AD5A st.h r24,-0x6ada[gp]`. So **`r26` ⇒ `gp-0x6adc`** (the `gp-0x69a4`-weighted lane, cals
`0xC643E`/`0xC6444`) and **`r24` ⇒ `gp-0x6ada`** (the deadband lane, cals `0xC6440`/`0xC6442`/`0xC6446`).
This matches `TRACE-2026-08-10 §5`'s own flagged correction and contradicts
`accord-aggregator-lane-mirrors-6ada-6adc` — **that memory is in the kit's `memory/` tree; ASK before editing it.**

## 2. 🛑 Off-by-0x1000 on the tp cals in `TRACE-2026-08-10-lkas-command-visibility.md` §5 — 6th recurrence

`tp = 0xBF000`. The decompile's displacements and the byte-read values:

| §5 says | actually | value (LE) | role |
|---|---|---|---|
| `0xC743E` | **`0xC643E`** | 1536 | r26 flat gain (gp-0x683c==0, gp-0x671a>=5) |
| `0xC7444` | **`0xC6444`** | 512 | r26 flat gain (gp-0x683c!=0) |
| `0xC7440` | **`0xC6440`** | 2048 | r24 flat gain |
| `0xC7442` | **`0xC6442`** | 1024 | r24 flat gain (gp-0x671d!=0) |
| `0xC7446` | **`0xC6446`** | 512 | r24 flat gain — **this is Lever B's cell (V88 512→5244)** |
| `0xC71F6` | **`0xC61F6`** | 3 | r24 deadband (Coulomb, already on record) |
| `0xC719C`/`0xC71A6`/`0xC73D2` | **`0xC619C`(1024)/`0xC61A6`(20)/`0xC63D2`(6)** | | `FUN_00036682` hysteresis + EMA |

Cross-check that catches it instantly: the golden model independently names `0xC63D2 = 6` and
`BUILD-LINEAGE` names `0xC6446`. **Anchor `0xC63AC`=102 / `0xC6200`=8192 / `0xC6468`=2639 first —
all three confirmed OK this session.**

## 3. ✅ `gp-0x683c` "zero writers" SURVIVES — but only with the op-specific displacement rule

A naive raw scan accepting `hw2 ∈ {disp, disp|1}` returns four `st.b` candidates
(`0x052E54`, `0x052FA8`, `0x05303A`, `0x053196`). All four have `hw2 = 0x97c5`. **`st.b` (op 0x3A)
carries a PLAIN disp16**, so `0x97c5 = −0x683B`, a different cell. Only `ld.bu` (op 0x3C/0x3D)
uses `disp = (hw2 & 0xFFFE) | ((hw1>>5)&1)` — which is why the reader at `0x3AA94`
(`hw1=0x7f84, hw2=0x97c5`) really is `gp-0x683c`.
⇒ **`disp|1` may be allowed ONLY for the `ld.*u` family. Applying it to `st.b`/`st.h` manufactures
false positives one cell off.** Same trap family as `accord-v850-scan-traps-formatv-and-storezero`.

## Related
[[reference_accord_aggregator_11term_loop_census_units_and_fork]] (the census this came out of) ·
[[reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy]] (corrected here) ·
[[reference_accord_r26_adaptive_lane_full_trace_and_sign]] (its "hard zero-force gate" reading was
right after all) · [[feedback_audit_your_own_claims_before_others_act_on_them]]
