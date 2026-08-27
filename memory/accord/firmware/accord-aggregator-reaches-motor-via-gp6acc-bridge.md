---
name: accord-aggregator-reaches-motor-via-gp6acc-bridge
description: RESOLVED — the 11-lane aggregator does reach the motor command, via gp-0x6ace to gp-0x6acc to gp-0x6b08; eleven prior methods missed it because they all asked "who reads gp-0x6b94".
metadata:
  type: reference
---

★★★★★ **THE `gp-0x6b94` → MOTOR GAP IS CLOSED.** The 11-lane aggregator — damper, friction, boost,
r24/r26, resonance, all at unity weight — **does** reach the delivered motor command. Every hop is
instruction-verified.

```
gp-0x6b94   aggregator (FUN_0003aa2c, 1 kHz) — damper gp-0x6bd0, friction gp-0x6b26,
            boost gp-0x6bbe, r24/r26 … summed, clamped ±0x2800
  -> FUN_0004503c  THE GOVERNOR — slew-limits toward that target, step size from
                   0xC6206 (512, below 16.6 km/h) / 0xC6208 (205, above), selected by gp-0x67f5
                                                                    -> gp-0x6ace  [0x4545A-0x455C0]
  -> FUN_000456a4  post-governor comp-add:  gp-0x6acc = gp-0x6ace + comp   [st.h @0x45932]
  -> FUN_00042af8  SHAPER reads gp-0x6acc  [ld.h @0x431C4]
                   validity gate |x| <= 0x2000, then the 0xC64C8 mode switch
                                                                    -> gp-0x6b08  [st.h @0x43206]
  -> SM2/SM3 integrator (gp-0x3570), iVar22 = cmd << 15
  -> gp-0x6b98  -> FUN_000757a2 (1 kHz torque model) -> Iq_ref/Id_ref -> FOC PI+FF (4 kHz) -> SVPWM -> duty
```

## The crux, byte-verified by the orchestrator independently [EVIDENCE]

Encodings predicted from the V850 instruction format, then matched against the image:

| site | predicted | actual (V81) | |
|---|---|---|---|
| `0x431C4` `ld.h -0x6acc,gp,r9` (op `0x39`, reg1=gp=4, reg2=9) | `244f3495` | **`244f3495`** | MATCH |
| `0x43206` `st.h r11,-0x6b08,gp` (op `0x3B`, reg2=11) | `645ff894` | **`645ff894`** | MATCH |
| `0x45932` the `gp-0x6acc` writer | — | `6447 3495` ⇒ hw1 `0x4764`: reg2=8, op=`0x3B`, reg1=4 ⇒ **`st.h r8,-0x6acc,gp`** | |
| `0xC64C8` mode selector (= `tp+0x74C8`) | — | **`0x00`** on STOCK, V76, V80 **and** V81 | |

**All four byte-identical across every build — no build has ever touched this code.**

## 🛑 The `0xC64C8` mode switch — stock is the pass-through case

Disassembled `0x431c4`–`0x43206`:
- **mode 1** → `r11 = tp+0x71d4`, a **static cal; `gp-0x6acc` is DISCARDED entirely**
- **mode 2** → `r7 += r11`, blended with the cal, clamped ±0x3000
- **mode 0 (stock, and every build)** → neither branch taken; the validity-gated `gp-0x6acc`
  goes **straight to `gp-0x6b08`, unmodified, every cycle**

⇒ `0xC64C8` is a one-byte switch that can **delete or statically replace the entire aggregator
contribution.** An extraordinarily clean experimental control and an extraordinarily dangerous one.
🛑 **UNTESTED. Writer census not yet run. Do not propose it as a lever without one.**

## Why eleven methods missed it — the durable lesson

Every check asked **"does `FUN_00042af8` reference `gp-0x6b94`?"** It does not, and that is true.
**Nobody asked about `gp-0x6acc`, two hops removed.** Three rounds, two independent tracers, six scan
methods (disp16, disp23, LE32 literal, movhi/movea, ep-materialisation, pcode dataflow) and two
register-return checks all returned the same null — **because they were all answering the same
wrongly-framed question.**

Compounding it: `gp-0x6b08` was characterised as *"self-referential ramp state, exactly one writer inside
`FUN_00042af8` itself, not an external forward-path input."* **Individually true, collectively
misleading** — the check asked whether anything *outside* the function reads it and stopped, never asking
whether the function's **own next instructions** consume it as the live command. They do, at `0x4320a`.

⊕ And the chain was **already documented**. `reference_accord_post_governor_comp_add.md` (2026-05-26 /
07-19) carried it including the exact address `0x431c4`. It was never cross-checked against the newer
"cannot reach" conclusion. ⇒ **When a new negative contradicts an old positive, diff them explicitly.**

📋 **METHOD RULE: to find what a value reaches, trace the FUNCTION'S OUTPUTS forward hop by hop — do not
enumerate one cell's readers and stop when they look like monitors.** A "monitor-only" output two hops
from the motor is a red flag, not a conclusion.

## What this resolves

1. **V40's brick, mechanistically.** `0xC6206`/`0xC6208` → `0xFFFF` removes the governor's slew limit, so
   `gp-0x6ace` snaps to the aggregator target in one cycle instead of ramping, forcing an unbounded step
   into the SM2/SM3 integrator with a divergence monitor downstream. Snap-to-target trips the monitor —
   a continuous signal path, **not** a threshold/DTC story. See [[v40-governor-slew-root-cause]].
2. **The graded V74→V81 damper dose-response.** The governor-limited, comp-added aggregator value
   **additively reaches the delivered command every cycle. Dose in, dose out** — no threshold involved.
3. 🛑 **The DTC-0x1d side-channel hypothesis is SUPERSEDED, not merely abandoned.** It predicted threshold
   behaviour; four independent quantities show a smooth graded response across `k` = 0.58 → 4.16 with
   **zero DTC transitions on every drive.**
4. It retro-justifies the on-car results that made the null impossible to accept: **V61** (zeroing two
   rate-lane taps made manual steering worse), **V62**, **V67/V68**, **V74/V75**, **V80**.

## ✅ THE LAST STRETCH IS CLOSED — no inherited hop remains

`0x43226` → both `gp-0x6b98` writes, hand-walked:
```
uVar25 = gp-0x6acc, mode-gated (0xC64C8)                      -> also stored to gp-0x6b08
iVar45 = Q15 BLEND of uVar25 against a companion term, weighted by a 0..0x8000 ramp fraction
         (LERP cals 0xC6A0C-0xC6A14), the whole blend scaled by
         |integrator gp-0x3570 >> 15| * cal(0xC61DA) >> 10
uVar34 = (cal 0xC64C9 == 0) ? iVar45 (blended)  :  uVar25 (raw)      <- 0 = stock = BLENDED is live
iVar45 = gp-0x6afe (CAN/arbitration term, validity-gated) + uVar34   <- THE SUMMATION POINT
       -> clamp against governor ceiling gp-0x4f64 -> hard clamp ±0x2000 -> gp-0x6b98
```
★ **The delivered command is the CAN-arbitrated term PLUS a scaled copy of the aggregator's
governor-and-comp-added contribution. Straightforwardly ADDITIVE, same-signed, NO sign flip anywhere.**
**Both writes (`0x43b52`, `0x43dfc`) are sequential on the normal path — not fault-vs-normal branches** —
and store the identical value (`uVar15` assigned once, never reassigned).
⚠ The one item not reduced: a **single scalar gain** for the aggregator leg. At nominal blend it is near
`0xC61DA`/1024 = **1092/1024 ≈ 1.066** times the integrator's settled magnitude ratio, but the full
envelope/ramp/integrator interaction was not collapsed to one number.

## THREE CALS ON THIS STRETCH — all orchestrator-verified from disk, all NEVER TOUCHED

| cal | value | identical in STOCK/V76/V80/V81 | role |
|---|---|---|---|
| **`0xC64C8`** (`tp+0x74c8`) | **0** | ✅ | mode selector: **1 = DISCARD the aggregator** for a static cal `tp+0x71d4` · 2 = blend, ±0x3000 · **0 = pass through (stock)** |
| **`0xC64C9`** (`tp+0x74c9`) | **0** | ✅ | blend-vs-raw mux at the summation point; 0 ⇒ blended path live |
| **`0xC61DA`** (`tp+0x71da`) | **1092** | ✅ | Q10 scale on the integrator-magnitude term feeding the blend |

🛑 **`0xC64C8` is a PURE BUILD-TIME CAL: zero runtime writers** (whole-image `st.b` scan for `tp+0x74c8`,
0 hits / 183,570 instructions), **exactly one static reader** at `0x431CC`. ⇒ **one unwritten byte that,
set to 1, deletes the entire aggregator contribution to the delivered command.** An extraordinarily clean
experimental control and an extraordinarily dangerous one. **UNTESTED — zero hits in any
`build_v*_tva.py`, zero mentions in `BUILD-LINEAGE.md`.**
⚠ `0xC64C9` is *mentioned* in `build_v58/59/64` and in `BUILD-LINEAGE.md`, but only as a status note
attached to a **different, already-REJECTED** lever: raising `0xC61D6` (slew step, = **0** on every build)
from 0→14 *"activates an uncalibrated map onto the live command (mux `0xC64C9` = 0)"* — rejected on an
11-round, 4-analyst review. **`0xC64C9` itself has never been edited.**

⊕ **The `0x431CC` decode is a textbook instance of the documented `ld.bu` trap** — bytes `857fc974` give
`hw2 = 0x74C9` but the real displacement is `(hw2 & 0xFFFE) | ((hw1>>5)&1)` = **`0x74C8`**. A scan matching
`hw2` literally would look for the wrong cal. See [[accord-v850-scan-traps-formatv-and-storezero]].

## Corrects these records

🛑 `accord/builds/accord-v77-cannot-reach-the-monitors.md` and the `gp-0x6b94`-forward-gap memories assert the opposite
and must be corrected. `gp6b4c-lane-chain.md` — which claimed the path **does** reach the motor and was
flagged as stale — turns out to have been **right about the topology**.
Related: [[accord-stock-mode24-equals-mode26-damper-is-ours]], [[accord-v81-carries-neither-grind1-fix]].
