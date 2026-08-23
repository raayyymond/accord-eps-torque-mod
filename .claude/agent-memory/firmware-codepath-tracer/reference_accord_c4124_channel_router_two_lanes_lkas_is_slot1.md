---
name: reference-accord-c4124-channel-router-two-lanes-lkas-is-slot1
description: "0xC4124[i] is a per-channel ROUTER cal, not an enable: mode 0/3/6 sends a channel into the governed aggregator lane (gp-0x6b4c), mode 5/7 sends it into gp-0x6afe which joins the command AFTER the aggregator, governor, comp-add and shaper. LKAS is slot 1 and is on the governed lane; slots 2/4/5/9 are already on the direct lane. Includes the byte-exact final-summation arithmetic and the verified task-1 order."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THERE ARE **TWO** LANES TO THE MOTOR COMMAND, AND `0xC4124` PICKS WHICH ONE A CHANNEL USES

2026-08-22, traced end to end in `code.bin` (stock) with GhidraMCP + a Python LE byte scan.

## The router [EVIDENCE — `FUN_00026c80` @`0x26c80`, dispatch pointer `movea 0x5124,tp,r23` @`0x26cdc`]
`tp+0x5124` = **`0xC4124`**. Bytes, identical on STOCK and V106:
`0xC4124[0..10] = [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0]`  ·  `0xC4118[0..10] = all 1` (admit), `[11]=0`.

| mode | `gp-0x62b0[i]` (+shadow `gp-0x4b40`) | `gp-0x62c8[i]` (+shadow `gp-0x4b58`) |
|---|---|---|
| **0 / 3 / 6** | = `gp-0x62f8[i]` (the request) | 0 |
| **5 / 7** | 0 | = `gp-0x62f8[i]` (the request) |
| 1 / 2 | 0 | 0 (genuinely dead) |
| 4 | `clamp((gp-0x633c[i]·0xC646A)>>14, ±0x2800)` | 0 |

⭐ **Mode 5 is line-for-line identical to mode 0 with only the destination array swapped.** Every other
copy (`gp-0x6298`, `gp-0x625c`, `gp-0x6324`, `gp-0x61e8`, `gp-0x61d0`, `gp-0x61b8`, `gp-0x4b28`,
`gp-0x4af8`) is the same in both.

Then, over the 11 slots:
- `gp-0x3d88` = Σ `gp-0x62b0[i]` **gated by `0xC4118[i]`** → `gp-0x6b4c` (`0xC63CC`=0 kills the extra term)
- `gp-0x3d8c` = Σ `gp-0x62c8[i]` **UNGATED** → clamp ±0x2800 → `gp-0x6b4e` → `FUN_00042ac6` → **`gp-0x6afe`**

🛑 **CORRECTS [[accord-gp6b4c-is-an-11-slot-assist-sum]]**, which says *"mode in (1,2,5,7) → 0 ⇒ slots
{2,4,5,9} FORCED ZERO"*. **Modes 5 and 7 RE-ROUTE, they do not zero. Slots {2,4,5,9} are alive on the
direct lane.**
⚠ Do not confuse the **cal** `0xC4124[i]` (routing, values 0–7) with the **RAM** per-slot state
`gp-0x61a0[i]` (values 0–5, written by `FUN_00025c32`). Same value range, different meaning.

## LKAS IS SLOT 1 [EVIDENCE, three hops]
1. `FUN_00028ea6` @`0x2a1ee` `ld.h 0x746c[tp],r7` — the forward gain (`0xC646C` stock; V57+ repointed this
   one instruction to `0xC6CD0`) × polarity `gp-0x6752`, `>>15`, clamp ±`0xC61B4` → `gp-0x6b3c` @`0x2a2ea`.
   (`gp-0x6b38` @`0x2a23c` is a **UDS telemetry mirror only** — sole reader `FUN_0004e82e`, a DID packer.)
2. `FUN_0002b422` @`0x2b422` reads `gp-0x6b3c` (+`gp-0x697e`/`gp-0x697c`, which become the ≤0x400 Q10
   authority fields), clamps ±`0xC61B2`, builds a 16-byte struct with **`[0] = 1` (the channel ID)**,
   calls `FUN_00025c32`.
3. `FUN_00025c32` @`0x25c32`: `slot = min(param_1[0], 10)`; `gp-0x62f8[slot] = clamp(struct[4], ±0x2800)`
   plus shadow `gp-0x4b88[slot]`.

## THE PER-CHANNEL AUTHORITY GATE IS **UPSTREAM OF THE ROUTER** — both lanes inherit it
[EVIDENCE — `FUN_00025c32` `0x25c32`–`0x25c7c`, the first thing the function does, before the payload is
even loaded (`ld.h 0x2[r6]` @`0x25c7c` is the first payload read)]
```
0x25c3a ld.hu -0x69aa[gp],r10   ; global authority fraction
0x25c40 cmovh 0xa,r8,r1         ; slot = min(struct[0], 10)
0x25c44 authority == 0x8000 ?  -> latch gp-0x6188[slot]=1, inhibit=FALSE
0x25c5c ld.hu 0x50f4[ep],r12    ; else r12 = 0xC40F4[slot]  (LKAS slot 1 = 29491 = 0.900)
0x25c6a below threshold        -> clear latch, inhibit=TRUE
0x25c72 else HYSTERESIS: stay inhibited until authority returns to exactly 0x8000
```
`0xC40F4 = [29491, 29491, 0, 21299, 29491, 21299, 0,0,0,0,0]`.
🛑 **NOT an unconditional "channel dropped".** It is an **inhibit flag with hysteresis**; its effect depends
on the request-type byte `struct[1]`: types **0/1/5** force state 5 and zero the slot arrays; types
**2/3/4** write the real request anyway and only change the reported state (2/3 → 4). Either way it acts
**before** the router (`FUN_0002b422` is task-1 slot `0x12`, `FUN_00026c80` is slot `0x15`), so a
`0xC4124` re-route loses nothing here.
⭐ **`FUN_00049a78(a,b) = min(a,b)`** (one-line decompile) ⇒ the governor's authority factors A and B are
**min-cascades seeded at 0x8000, so both ≤ 1**, and `gp-0x69aa = (A·B)>>15`. Uninhibited ⇒ `A·B ≥ 0.8999`
⇒ **`B ≥ 0.8999`** ⇒ **the governor's `×B` fade is at most −10 %, so the direct lane can be at most
+11.1 % hotter than the governed lane.** ⚠ Unclosed premise: the rate-limiter arm on `uVar6`/`uVar17`
(`0xC6492`=33/tick, gated on `gp-0x6a64 ≥ 0xC6316`=640) sets `prev + 33`; a one-step (0.1 %) overshoot of
0x8000 is not excluded.

## 🛑 THE FEEDFORWARD SUM IS UNGATED — `0xC4118` gates only the governed side
```c
iVar14 += gp-0x62c8[i];                                    // gp-0x3d8c UNCONDITIONAL -> gp-0x6afe
if (*(char*)(tp+0x5118+i) != 0) iVar11 += gp-0x62b0[i];    // gp-0x3d88 GATED -> gp-0x6b4c
if (*(char*)(tp+0x5118+i) != 0) iVar47 += gp-0x6298[i];    // gp-0x3d80 GATED-ON  -> gp-0x6b4a
if (*(char*)(tp+0x5118+i) == 0) iVar13 += gp-0x6298[i];    // gp-0x3d84 GATED-OFF (complement)
```
`0xC4118 = [1]*11` on stock and V106 ⇒ inert today. **The direct lane has no per-slot enable at all**, but
since mode 5 writes `gp-0x6298[i]` identically to mode 0, the `gp-0x3d80`/`gp-0x3d84` split is untouched
by a re-route. Ownership proven clean — see [[reference-accord-slot-array-asil-monitors-and-shadow-arrays]].

⇒ **`0xC4124[1] = 0` ⇒ LKAS goes through the aggregator and the governor.** Setting it to **5** moves LKAS
onto the post-governor lane — the whole feedforward question, in one calibration byte.

## THE FINAL SUMMATION, INSTRUCTION-EXACT [EVIDENCE — `FUN_00042af8` `0x43ae0`–`0x43b12`]
```
0x43ae0 ld.h  -0x6afe[gp],r13     ; the DIRECT lane
0x43ae4 ld.hu -0x4f64[gp],r10     ; the ceiling (UNSIGNED)
0x43af0 cmovc 0x0,r13,r12         ; ff   = |gp-0x6afe| <= 0x2800 ? gp-0x6afe : 0
0x43af4 add   r20,r12             ; sum  = ff + r20     (r20 = the governed aggregator leg)
0x43afa cmovc 0x0,r10,r14         ; ceil = gp-0x4f64 <= 0x2800 ? gp-0x4f64 : 0
0x43afe..0b0a                     ; cmd  = clamp(sum, ±ceil)
0x43b0e                           ; cmd  = clamp(cmd, ±0x2000)   -> gp-0x6b98
```
🛑 **The ±0x2000 hard clamp is DEAD**: `gp-0x4f64`'s source table `0xC520C` maxes at **5325 < 8192**, so
`gp-0x4f64` is always the binding ceiling. Bank A re-read: count 5, X=[1050,1700,2500,3700,4100],
**Y=[5325, 3584, 2406, 1587, 512]**; mirror `0xC5224` byte-identical. `gp-0x4f64` is written only by
`FUN_0007b022` (`0x7c2e2`/`0x7c3b4`/`0x7c47c`) as `trunc(float × 1024)` ⇒ Q10 counts.

## TASK-1 ORDER, from the dispatcher itself [EVIDENCE — `FUN_0002214a`, `uVar2 = 1 << gp-0x67fa`]
`FUN_00028ea6`(0x11, mask 0x930) → `FUN_0002b422`(0x12) → `FUN_00028d22`(0x14, 0x830) →
`FUN_00026c80`(0x15) → `FUN_00027b0a`(0x16) → `FUN_00038148` → `FUN_0003a382`(0xc30) →
damping lanes 0x17–0x1f → **`FUN_0003aa2c`(0x20, 0xc30)** → `FUN_000428d4` → `FUN_00044cf0` →
**`FUN_0004503c`(0x21, 0xd30)** → `FUN_0004595a` → `FUN_000456a4`(0x22) → `FUN_00045a20` →
**`FUN_00042af8`(0x23)** → `FUN_00043e44`(0x24) → `FUN_00045d9e`(0x25).

## THE GOVERNOR, decoded [EVIDENCE — `FUN_0004503c`]
```
bound = (gp-0x4f64 · A) >> 15                     0x453f0-0x453fe   (A,B = Q15 authority fractions)
tgt   = (clamp(gp-0x6b94, ±bound) · B) >> 15      0x45400-0x4540c
step  = ((gp-0x67f5 ? 0xC6208=205 : 0xC6206=512) · C) >> 15
gp-0x6ace = slew(gp-0x138a -> tgt, ±step)          0x45410-0x4545a
gp-0x69aa = (A · B) >> 15                          0x45364   <- the GLOBAL authority fraction
```

## THE NUMBERS THAT SETTLE "WHAT LIMITS THE RATE"
- LKAS lane max = `(0xC61BE × gain) >> 15`. Stock: 15360×891>>15 = **417** (clamp `0xC61B4`=512).
  V102–V106 at 6×: 15360×5346>>15 = **2505** (clamp 3072). **Ratio 1.23 on every build ⇒
  `0xC61B2`/`0xC61B4` NEVER BIND;** the real ceiling is `0xC61BE`(15360) × the gain.
- LKAS max per-tick increment through the arbitration IIR (pole 992/1024) ≈ 2505·(1−0.96875) ≈
  **78 ct/tick** — below the governor's 205 (highway) and 512 (low speed) ⇒ **the governor slew limit
  cannot cap LKAS's own rise.** It bites only as a *shared* budget a fast damping transient can eat.

## 🛑 WHAT A LANE MOVE DOES **NOT** BUY — my own strong form, retracted 2026-08-22 same session
I wrote *"every count of damping is a count of LKAS authority, exactly"* as a property of the aggregator.
**Wrong twice.** (a) Below the ±0x2800 clamp the terms simply add, and `b6` (`|gp-0x6b94| ≥ |gp-0x4f64|`)
read **0.000000 / 65,959 frames** on route `a5` ⇒ the sum never reached even the ≤5325 ceiling, so the
clamp-squeeze mechanism is **not established**. (b) Worse, the count-for-count subtraction is a property of
the **final `cmd = ff + agg` add at `0x43af4`**, which **survives the lane move unchanged** — moving LKAS
to `gp-0x6afe` does **not** stop the damper opposing it.

**What the move DOES buy, by confidence:**
1. ⭐ **It takes LKAS out of the shaper's integrator/blend chain.** The governed leg arriving at the
   summation is a **Q15 blend against a companion term, scaled by `|gp-0x3570 >> 15| × 0xC61DA(1092) >> 10`**
   (mux `0xC64C9`=0 ⇒ blended live) — a state-dependent modulation of LKAS by an integrator's magnitude.
   On the direct lane LKAS is **algebraically flat from `gp-0x62f8[1]` to the final clamp.** Needs no clamp
   to bind to be true.
2. It decouples LKAS from the **shared** slew budget (not a cap on its own rise: 78 vs 205 ct/tick).
3. It removes the `×B` fade — **a cost, bounded ≤ 11.1 %** (above).
🛑 **It buys NO extra authority.** Lane max stays `(0xC61BE × gain)>>15` = 2505 at 6×; ceiling stays
`gp-0x4f64`. **A topology change, not an authority change** — pair it with flattening `0xC520C`/`0xC5224`
or raising `0xC61BE` if raw rate is the goal.

Related: [[accord-the-8x-gain-is-the-carrier]] · [[reference-accord-lkas-lane-is-a-lowpass]] ·
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]] · [[accord-4x-lkas-gain-is-the-frozen-variable]] ·
[[reference-accord-slot-array-asil-monitors-and-shadow-arrays]]
