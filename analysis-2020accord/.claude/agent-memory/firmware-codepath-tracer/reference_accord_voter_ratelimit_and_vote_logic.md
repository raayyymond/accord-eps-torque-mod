---
name: reference-accord-voter-ratelimit-and-vote-logic
description: Accord TVA-A160 voter FUN_00041eec — full byte-verified rate-limiter/vote-average mechanics for gp-0x6a62 (gate/MAX), gp-0x6a5e (AVG/boost-axis), gp-0x6a64 (sibling), complementing reference-accord-voter-0xffff-sentinel. gp-0x6a60 confirmed NOT produced here (separate function FUN_0003f776, angle-rate derived).
metadata:
  type: reference
---

# Accord 39990-TVA-A160 voter FUN_00041eec — rate-limit + vote/average mechanics (Session 2026-07-06)

Stock code.bin. gp=0xFEDF8000, tp=0xBF000. r2 5.5.0 `-a v850.gnu`. All addresses hand-walked with linear `pd` (not `af`/`pdf`, which under-detect this function per [[reference-accord-voter-0xffff-sentinel]]). This memory ADDS to that one — read both together. [V] = disasm-verified this session; [V-prior] = confirmed from an earlier session's memory and cross-checked; [I] = inferred/reasoned, not fully byte-pinned.

## Three independent outputs, three independent limiters [V]

`FUN_00041eec` computes THREE separate rate-limited accumulators and stores each to a public gp-var + its lockstep shadow. All three share the same per-channel range-validity gate (see sentinel memory) for whether they get a fresh value or stay `0xFFFF`/frozen.

| Output | gp-offset (abs) | shadow twin | source register | limiter step (cal, byte value) | limiter direction |
|---|---|---|---|---|---|
| gp-0x6a62 (gate/MAX) | `0xFEDF159E` | gp-0x4cae (`0xFEDF35B2`) | `r24` | cal `0xC64ED` = **16** (`ld.bu tp+29933`) | **decay-only**: caps the FALL to ≤16/cycle; RISE passes through unfiltered |
| gp-0x6a5e (AVG/boost axis) | `0xFEDF15A2` | gp-0x4caa (`0xFEDF35AA`... shadow at -19626) | `r28` | adaptive threshold `r21` (derived from cal `0xC6318`, see below) | rise AND fall both bounded by `old ± r21` (two-sided, cmov-based) |
| gp-0x6a64 ("sibling") | `0xFEDF159C` | gp-0x4cb0 (shadow at -19632) | `r22` | cal `0xC64EE` = **27** (`ld.bu tp+29934`, adjacent byte to 0xC64ED) | same two-sided `old ± step` cmov structure as r28's block, but with fixed step 27 instead of adaptive r21 |

Store addresses [V]: gp-0x6a62 at `0x4231c`/`0x42320` (r24 path, r25==0) or `0x42312`/`0x42316` (r28 path, r25==1 — sentinel-recovery, see below); gp-0x6a5e at `0x42342`/`0x42346` (unconditional, always r28); gp-0x6a64 at `0x42360`/`0x42364` (unconditional, always r22). All three gated by a shadow-mismatch lockstep check (`cmp` against the twin; on mismatch, `jarl 0x0006b9fa` — the same lockstep-fault handler seen elsewhere in this codebase, e.g. `gp-0x6752` polarity mismatch).

**Read order matters**: gp-0x6a62's OLD value is reloaded fresh at `0x421c0` specifically to test whether it was `>=32001` (only possible if it held the `0xFFFF` sentinel from last cycle, since normal operation never exceeds the 32000 clamp) — that reload sets `r25=1` and substitutes `r28` (the SAME value about to become gp-0x6a5e) for the store, rather than the freshly computed `r24`. **This means: the cycle immediately after a sentinel event, gp-0x6a62 briefly equals gp-0x6a5e (the smoothed value) instead of the raw max — a one-cycle smoothing bridge out of the invalid state, not a jump straight back to instantaneous peak.**

## gp-0x6a62's decay-limiter block, byte-by-byte [V]

```
0x000421c0  e4579f95   ld.hu -27234[gp], r10      ; r10 = OLD gp-0x6a62
0x000421c4  0a06ff82   addi -32001, r10, r0        ; test r10 vs 32001 (unsigned overflow => CY set iff r10>=32001)
0x000421c8  811d       bl 0x000421f8               ; CY=1 (r10>=32001, i.e. OLD was the 0xFFFF sentinel) -> jump: r25=1, r24=32000, go compute r28 path
0x000421ca  f4c9       cmp r20, r25                ; (fallthrough, OLD<32001 = normal) r24 = MAX(r20=ch5 deviation, r25=ch1-4 running extreme)
0x000421cc  f4cf26c3   cmov nh, r20, r25, r24
0x000421d0  d800       zxh r24
0x000421d2  f851       cmp r24, r10                 ; compare new candidate r24 vs OLD r10  (cmp reg1,reg2 => reg2-reg1; V850 CMP convention)
0x000421d4  d30d       bnh 0x000421ee                ; r10<=r24 (RISING or flat) -> skip decay check entirely, accept r24 as-is
0x000421d6  a537ed74   ld.bu 29933[r5], r6           ; FALLING: r6 = cal_0xC64ED = 16
0x000421da  0a40       mov r10, r8
0x000421dc  b841       sub r24, r8                    ; r8 = OLD - new  (fall magnitude, positive since r10>r24 here)
0x000421e0  e641       cmp r6, r8
0x000421e2  e305       bnh 0x000421ee                 ; fall<=16 -> accept r24 as-is (small fall, no need to cap)
0x000421e4  a57fed74   ld.bu 29933[r5], r15           ; fall>16: reload step
0x000421e8  af51       sub r15, r10                    ; r10 = OLD - 16  (cap the fall to exactly one step)
0x000421ea  cac6ffff   andi 65535, r10, r24            ; r24 = capped value
0x000421ee  1806ff82   addi -32001, r24, r0            ; (rejoin) clamp r24 to 32000 ceiling, r25 flag logic
```
**Branch-condition calibration note**: this reading relies on the standard V850 convention `CMP reg1,reg2 ≡ reg2-reg1 (flags only)`, `BNH ≡ (CY|Z)` i.e. unsigned `reg2<=reg1`, confirmed via r2's own `aoj`/esil dump for the `bnh` mnemonic (`cy,z,|,?{...}` — matches). This is the SAME convention used to independently re-derive the sentinel-recovery branch (`bl` on the `addi -32001` test), which reproduces exactly the mechanism [[reference-accord-voter-0xffff-sentinel]] already established from the store side. Two independent derivations agreeing is the confidence basis here — **not** a from-scratch guess.

**This CONFIRMS (not just repeats) [[reference-accord-lkas-engage-sm-disengage-trigger]]'s claim: "rate-limiter is decay-only... on a rising transient gp-0x6a62 tracks the instantaneous peak coil with no attenuation."** A bump/torque transient that RAISES the max-coil value is passed to gp-0x6a62 with ZERO filtering, in the same cycle. Combined with the disengage decider `FUN_00040d58` having no debounce on its `>=320` test, **there is no debounce anywhere in the rising-edge chain from coil ADC to disengage** — the only two places debounce/latching exist are (a) the fall-limiter above (irrelevant to a rising spike) and (b) the separate `gp-0x67f4` plausibility latch, which does not gate the store decision (per sentinel memory, confirmed independently in this session, see below).

## Vote/average logic — spread-gated average vs extremal fallback [V structural, I on exact divide]

The 4-channel loop (`0x420b6-0x42108`) computes, per valid ch1-4 channel: `abs(raw)` and `deviation = abs(raw - r7)` where `r7 = OLD gp-0x6a5e` (the previous cycle's smoothed/fused value, loaded once at `0x41f2e`). It simultaneously accumulates:
- `r13` += `abs(raw)` for each VALID channel only (running SUM, confirmed: the `add r14,r13` at `0x41f0` sits AFTER the per-channel `ld.w 20[..],r8; cmp 1,r8; bne <skip>` validity gate, i.e. invalid channels do not pollute the sum) [V]
- `r28/r16/r11/r25(temp)` — four running extremal trackers via `cmov` (some min, some max across abs-value and deviation; exact per-register min/max assignment not fully disentangled — register `r25` is reused later for an unrelated purpose, a common source of confusion when hand-walking this function) [I on exact identity, V on existence]
- ch5 folds into `r28`/`r11` afterward (`0x42108-0x42136`) but does NOT increment the valid-count `r26` [V-prior, confirmed]

Then the average-vs-fallback decision (`0x4213a-0x4214c`):
```
0x0004213a  cmp 2, r26          ; need >=2 valid ch1-4 channels
0x0004213c  bl 0x00042150       ; <2 valid -> skip averaging, KEEP the extremal-tracked r28
0x0004213e  mov r25, r8
0x00042140  sub r11, r8         ; r8 = spread estimate (difference between two tracked extremes)
0x00042144  cmp r2, r8
0x00042146  bnl 0x00042150      ; spread >= threshold r2 -> skip averaging, KEEP extremal r28
0x00042148  fa fe 20 e3? (raw bytes vary by dest reg) -- UNDECODED 4-byte V850E2 opcode
0x0004214c  cde6ffff  andi 65535, r13, r28   ; r28 := r13 (the channel-abs SUM), zero-extended
```
**[I, high confidence]**: the undecoded 4-byte instruction at `0x42148` is almost certainly a **DIVIDE** (V850E2 `DIVHU`/`DIVU`-family, 4-byte encoding — the same opcode family the plugin also fails to decode at `0x41f8c`/`0x41fec` inside an unrelated preamble block per [[reference-accord-voter-0xffff-sentinel]]'s open item 1), dividing `r13` (sum) by `r26` (valid-channel count) to produce a true average, which is then moved into `r28` at `0x4214c`. This is INFERRED from context (a sum immediately followed by a "why keep the sum register value" pattern feeding straight into r28) — **not directly disassembled**. Confirming it requires either Ghidra's V850E2 processor module (not available this session — no Ghidra install found in this environment) or a manual V850E2 divide-opcode table lookup.

**Net vote/average logic**: `r2` (the spread threshold — see next section) gates whether `gp-0x6a5e`'s underlying candidate (`r28`, before its own two-sided rate limiter) is: **(a)** the AVERAGE of valid ch1-4 |raw| values, when >=2 channels valid AND their spread is under threshold; or **(b)** the extremal-tracked value carried from the loop (closer to a MAX/MIN-style fallback), when either too few valid channels or spread too wide. This is the "closest-to-fused vs average-of-valid" logic the mapping brief asked to pin — **confirmed structurally, with the exact divide operation inferred but not disassembled.**

## The spread threshold `r2` — adaptive, cal `0xC6318` [V struct, values V]

```
0x00041ff2  ld.bu -26622[gp], r10       ; gp-0x67FE (a MODE byte, not previously catalogued — distinct from gp-0x67fa)
0x00041ff6  andi 65535, r12, r21        ; r21 := (whatever r12 held from the preceding breakpoint-table lookup)
0x00041ffa  cmp 2, r10
0x00041ffc  bne 0x00042036               ; mode != 2 -> simple path
0x00041ffe  ld.hu -27152[gp], r15        ; gp-0x6a10 (an elapsed-cycle/tick counter, not previously catalogued)
0x00042002  addi -10001, r15, r0
0x00042006  bl 0x00042036                ; gp-0x6a10 < 10001 -> simple path
0x00042008  ld.hu 29464[r5], r13         ; cal_0xC6318 = 640 [V, byte-read this session]
0x0004200c  mov 0x33333, r12             ; fixed-point constant 0x33333 = 209715 (~ 0.2 in Q20, i.e. "1/5")
0x00042012  mulu r15, r12, r0            ; r12 := r15 * 0x33333 (mod 2^32), high bits discarded
0x00042016  ld.bu 29940[r5], r8          ; cal_0xC64F4 = 39 [V, byte-read this session]
0x0004201a  shr 14, r12
0x0004201c  mulu r8, r12, r0             ; scale by cal byte
0x00042020  mov r7, r10                  ; r7 = gp-0x6a5e OLD (loaded way back at 0x41f2e)
0x00042022  shr 15, r12
0x00042024  mulu r12, r10, r0            ; scale by current fused torque level
0x00042028  shr 7, r10
0x0004202a  addi 32, r10, r16
0x0004202e  cmp r13, r16
0x00042030  cmov h, r13, r16, r16        ; r16 := min(cal_0xC6318=640, computed-formula)  [cmov "h" semantics inferred from symmetry w/ bnh pattern above]
0x00042034  br 0x0004203c
0x00042036  ld.hu 29464[r5], r16         ; ELSE (mode!=2 or counter<10001): r16 = cal_0xC6318 = 640
0x0004203a  sar 1, r16                    ; r16 >>= 1  =>  r16 = 640/2 = 320   <-- matches the brief's "adaptive cal 0xC6318/2"
0x0004203c  ...
0x0004204e  andi 65535, r16, r2          ; r2 := final spread threshold
```
**Confirmed [V]: the DEFAULT/common-case spread threshold is `cal_0xC6318 >> 1 = 640/2 = 320`.** This is numerically IDENTICAL to the disengage-gate threshold `cal_0xC6312 = 320` from [[reference-accord-lkas-engage-sm-disengage-trigger]] — likely not a coincidence (same design constant reused), worth flagging to the operator as a structural note, not yet confirmed as intentional. The ADAPTIVE branch (mode byte `gp-0x67FE==2` AND elapsed counter `gp-0x6a10>=10001`) computes a more complex, torque-level- and time-scaled threshold via cal bytes `0xC64F4=39` and the running fused torque `r7`; the exact physical meaning of this formula (a warm-up ramp? a per-mode recalibration?) is **not pinned** — flagged as open.

`gp-0x67FE` and `gp-0x6a10` are NEWLY OBSERVED offsets this session, not in prior gp-offset catalogs ([[reference-accord-arb-input-cluster]]). Recommend adding to that inventory if the operator confirms.

## gp-0x6a60 — CONFIRMED NOT produced by this voter [V, fresh disasm this session]

Traced `FUN_0003f776` (0x3f776-0x3f884), the actual producer: it clamps a value to `±12000` at `gp-0x6a56` (angle-rate-derived per [[reference-accord-dual-torque-sensor-architecture]]/[[reference-accord-driver-override-plausibility-eme]]: "written by FUN_0003f776, lockstep-shadowed"), then at `0x3f7f6` calls `FUN_00049a5a` (documented elsewhere as an ABS() helper — [[reference-accord-engage-sm-second-gate-gp6cc4]]: "FUN_00049a5a=ABS()"), then `FUN_00049a78` (unresolved, likely a second clamp/scale), then stores the result to **gp-0x6a60 (`0xFEDF15A0`) at `0x3f810`/`0x3f814`**, with lockstep shadow gp-0x4c94 (`-19628[gp]`). **This independently reconfirms [[reference-accord-lkas-engage-sm-disengage-trigger]]'s "gp-0x6a60 = ABS magnitude of gp-0x6a56 (angle-rate-derived)" and [[reference-accord-voter-0xffff-sentinel]]'s "gp-0x6a60 is confirmed NOT written by this function."** `gp-0x6a60` is a RATE quantity, not a torque quantity — the engage-attempt gate `gp-0x6a60 >= cal 0xC6310=1600` is gating on steering angular rate, not column torque. This is fully out of the voter's scope; the actual acquisition chain for gp-0x6a60 is `FUN_0003f776` + its two callees, a separate segment from the torque-coil voter.

## Fault-persistence counter (partially resolved, likely NOT feeding gp-0x6a62/5e/64 directly) [I]

A separate byte counter `gp-0x18AC` (`-26452[gp]`) increments/resets based on comparing the tracked spread (`r28`, pre-average) against **cal `0xC631E` = 640** [V, byte-read], debounced against a count-threshold `cal 0xC64E7` (not read this session). This lives at `0x42246-0x42296`, structurally parallel to (but a separate mechanism from) the `gp-0x67f4` immediate plausibility latch. Its downstream consumer was **not traced this session** — flagged open. Do not conflate this with the `gp-0x67f4` "<65" recovery check (a literal immediate, not cal-driven) confirmed separately below.

## gp-0x67f4 clear/restore — independently re-derived this session, matches prior session exactly [V]

- **Clear-to-0 condition**: ch5 invalid (`r27!=1`) AND zero of ch1-4 valid (`r26==0`, i.e. `bl 0x42194` at `0x42160` after `cmp 1,r26`) — the "total loss" door, `0x42194-0x421aa`, force-clears both `gp-0x67f4` (`-26612[gp]`) and shadow `gp-0x4c38` (`-19512[gp]`) to 0. **Matches [[reference-accord-arb-input-cluster]] and [[reference-accord-voter-0xffff-sentinel]] exactly** — three independent derivations (two prior sessions + this one) now agree.
- **Restore-to-1 condition**: only reachable when the flag is currently 0 (`0x42168: bne 0x421b8` skips restore-check if already 1); requires `|r7(OLD gp-0x6a5e) - r28(new spread/avg candidate)| < 65` — **`65` is a literal ADDI immediate (`addi -65,...` at `0x4217a`), NOT a calibration-table read** — i.e. not adjustable via cal edit, it's baked into code. This is a NEW precision (prior memory didn't specify literal-vs-cal for the 65).

## Open items for next verification pass
1. Exact divide opcode at `0x42148` (and the two others at `0x41f8c`/`0x41fec` from the preamble) — needs Ghidra V850E2 module or manual opcode table; no Ghidra install found in this environment this session.
2. Exact min/max identity of loop trackers `r16`/`r11`/`r25(temp)` vs `r28` — structurally confirmed as "four running extremes across abs-value and deviation" but not disentangled register-by-register.
3. The breakpoint-table lookup at `0x41f2e-0x41ff2` (cal series `0xC6840-0xC686C`, keyed by `r7`=gp-0x6a5e) writes `gp-0x6a1a/1c/1e/20` (newly observed offsets) — does NOT appear to feed gp-0x6a62/5e/64 downstream in this function; likely a parallel adaptive-envelope computation for a DIFFERENT consumer. Not traced further — flagged open, low priority for the gate/EME question.
4. `cal 0xC631E=640` fault-persistence counter's downstream consumer — not traced.
5. **Flag for operator, not yet resolved**: [[reference-accord-assist-mode-eme-dropout]]'s "inter-channel delta threshold ~0x7D00=32000" claim was already flagged as likely-stale by [[reference-accord-voter-0xffff-sentinel]] (no such check found feeding the 0xFFFF path); this session's trace of the actual spread threshold (640/2=320, or the adaptive formula) further suggests that memory conflated the 32000 CLAMP CEILING with a nonexistent "delta threshold." Recommend asking the operator before editing that memory file.

[[reference-accord-voter-0xffff-sentinel]] [[reference-accord-lkas-engage-sm-disengage-trigger]] [[reference-accord-dual-torque-sensor-architecture]] [[reference-accord-arb-input-cluster]] [[reference-accord-assist-mode-eme-dropout]]
