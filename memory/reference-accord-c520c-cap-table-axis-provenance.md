---
name: reference-accord-c520c-cap-table-axis-provenance
description: "SETTLED: the 0xC520C table index IS clamp(gp-0x6ac0,0,10000) = motor resolver/FOC electrical-angle rate, and 0xC5224 is a redundant MIRROR not a composed stage. Consequence: flattening the cap makes NO difference at rest."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2a888703-82cf-4378-8b23-ce6677f440d5
  modified: 2026-07-19T23:45:45.857Z
---

## VERIFIED — `gp-0x6ac0` is motor resolver / FOC electrical-angle RATE

Independently re-derived 2026-07-19 from scratch (not read back from the prior memory), five hops each
with a sole-writer confirmation via image-wide `search_instructions`:

1. `gp-0x6ac0` ← written in `FUN_00041464`: `gp-0x6ac0 = |IIR(gp-0x4f50 × 1024, gain tp+0x743c)| >> 10`
2. `gp-0x4f50` ← **sole writer** `FUN_00068fbe` @`0x68fde` (12 refs image-wide, exactly one `st.h`)
3. `FUN_00068fbe` = IRQ-protected snapshot: `di; sVar2 = gp-0x29c4; ei;` then lockstep write to
   `gp-0x4f50`/`gp-0x4484`. Straight copy, no math.
4. `gp-0x29c4` ← **sole writer** `FUN_00068f52` @`0x68fb4`: **wraparound-corrected delta on a 14-bit
   modulus** (`if d>0x2000: d-=0x4000; if d<-0x2000: d+=0x4000`), scaled `×120000>>14`, 2-sample
   averaged with `gp-0x4f4e`, clamped **±13000**.
5. `FUN_00068f52` ← **sole caller** `FUN_00065afe`: branch 0 calls
   `FUN_0006adfe(gp-0x4f26-0x800, gp-0x4f2a-0x800, 0)` — a **sin/cos ADC pair** with 2048 differential
   bias removal into an atan2/CORDIC decoder, output masked `&0x3fff` (matches the `0x4000` modulus).
   The FOC branch adds a literal `+0x4800` phase offset before re-wrapping mod `0x4000`.

⇒ Unambiguously the rate of change of a wrapping electrical angle. **This claim is GOOD.** An earlier
blanket doubt cast on it (because it shared a session with the retracted CRC-gap error) was
over-correction — see [[reference-crc-chain-is-50-blocks-c5000-not-a-gap]].

⚠ Correction: `gp-0x6ac0`'s own write has **no** sign-gate against `gp-0x6b98`. That gating belongs to
the sibling `gp-0x6ac2`. Fix this wherever the old note claims otherwise.

## VERIFIED cals (raw bytes)

| Address | Bytes | Value |
|---|---|---|
| `0xC559C` | `00401c46` | **10000.0f** |
| `0xC50D4` | `4003` | 832 → ×0.015625 = **13.0** |
| `0xC50D6` | `ba02` | 698 → ×0.015625 = **10.90625** |
| `0xC664C` | `0000c0c0` | **-6.0f** (a float — looks like u16 `0`, it is not) |

## ✅ SETTLED — the index IS the electrical-angle rate, essentially unscaled

Re-derived from RAW DISASSEMBLY after the decompile's float-temp reuse produced two wrong answers:

```text
0x7b080  cvtf.uws r9,r26          r26 = (float)(unsigned) gp-0x6ac0
0x7b3fe  cmpf.s le,r26,r15,cc1    r15 = cal 0xC559C = 10000.0f  (VERIFIED bytes 00401c46)
0x7b40a  cmovne r15,r26,r26       => r26 = MIN(gp-0x6ac0, 10000.0)   <-- MIN, not MAX
0x7b410  maxf.s r0,r26,r26        floor at 0
0x7b564  ld.w 0x6648,tp,r8        cal 0xC5648 = 1.0f exactly (VERIFIED bytes 0000803f)
0x7b5fc  mulf.s r26,r8,r15        index = r26 * 1.0
```

⇒ **`index = clamp(gp-0x6ac0, 0, 10000)`** on the dominant path — taken whenever the `gp-0x4f0c`-derived
channel is ≥ cal `0xC5598` = **42.0f** (VERIFIED bytes 00002842). The alternate path computes
`42.0² / max(floor, x)²`, which is always **≥ 1.0** — it can only push the index further out, never
into a nonsensical range.

So the table's X axis **is** motor resolver/FOC electrical-angle rate, unscaled. The kit's original
claim was RIGHT; the dimensional objection that made it look impossible came from a `MAX`/`MIN`
inversion in the decompile. Rates of 1050–4100 sit squarely in the table's domain.

⚠ The earlier "13.0 / 10.90625" ratio (`0xC50D4`/`0xC50D6`) is **retracted** — real cals, but they feed
an unrelated computation stored to `gp+0x8c`/`gp+0x90` (`0x7b056`/`0x7b070`), not this index.

## ✅ SETTLED — `0xC5224` is a redundant MIRROR, not a composed stage

From raw disassembly of `0x7b642`-`0x7b7e8`: the saturated query lands in `r24` once at
`0x7b642 trncf.sw r14,r24`. `0x7b656 mov r24,r7` feeds stage 1's binary search; `0x7b722 mov r24,r7`
feeds stage 2's search over the **dup** X array at `tp+0x6226`. **`r24` is never written between
them** — both searches query the identical original input, and stage 2 does not consume stage 1's
result (`r6`). Standard lockstep redundancy, same family as `gp-0x4f64`/`gp-0x448a`.

⇒ **V40's redundant-mirror assumption for patching both records was CORRECT.** Independently
corroborated numerically: composition would send a legitimate 5325 stage-1 output to **-2781**.
(An explicit stage1-vs-stage2 fault compare has not been located — secondary detail.)

## ✅ THE LERP CLAMPS AT BOTH ENDS — it does NOT extrapolate (VERIFIED)

Raw disassembly, table A (table B at `0x7b72c`-`0x7b74c` is byte-identical in structure):

```text
bottom  0x7b658 cmp r7,r13   (r13 = X[0] = 1050)
        0x7b65e blt 0x7b666  -> query above bottom, do the search
        0x7b660 ld.h 0,r20,r6 -> r6 = Y[0] = 5325 taken directly
        0x7b664 br  0x7b71a  -> skip interpolation entirely
top     0x7b66e ld.h 0,r14,r11 (r11 = X[4] = 4100)
        0x7b672 cmp r7,r11
        0x7b674 bgt 0x7b67c  -> query below top, do the search
        0x7b678 sld.h 0,ep,r6 -> r6 = Y[4] = 512 taken directly
        0x7b67a br  0x7b71a
```

Lead-verified: `0x7b664` = `0x5DB5` and `0x7b67a` = `0x5585` are both unconditional branches whose
displacements compute to **exactly `0x7b71a`**. Confirmed.

⇒ Returns exactly `Y[0]`=5325 for any rate ≤1050, exactly `Y[4]`=512 for any rate ≥4100.

⚠ **This RETRACTS earlier extrapolation-based numbers** (rate 0 → 8137, rate 10000 → -15348). Those
values are never computed. Reality is flatter in both directions.

## ⚠⚠ CONSEQUENCES — two, and they point in opposite directions

```text
rate     stock cap   V40 cap    stock->MIN(4762)   V40->MIN(4762)
   0          5325      5325                4762             4762   <- IDENTICAL
2500          2406      5325                2406             4762
>=4100         512      5325                 512             4762   <- 9.3x apart
```

1. **The cap flatten is PROVABLY INERT AT REST.** V40's `Y[0]` is 5325, byte-identical to stock, and the
   clamp returns exactly `Y[0]` below rate 1050. So the cap **cannot** explain the stationary ignition
   fault unless a startup transient pushes the rate above ~1050. That leaves the **slew removal** as the
   better-supported mechanism. See [[v40-governor-slew-root-cause]].
2. **The cap floor is the likely root of the HARD-TURN RATCHET.** At rate ≥4100 stock slams the cap to
   **512** — against V38's ~2806 command that is an **82% instantaneous cut** (motion toward zero is
   unlimited in the governor). Recovery is then limited to 205/cycle ≈ 14 cycles. Fast cut + slow
   recovery = a several-Hz limit cycle, matching the reported symptom.
   ⚠ **Stock V9's max LKAS command was 417 — below the 512 floor, so stock LKAS could NEVER be capped.
   V38's 4x raise is the first build to cross it.** That is why the ratchet appeared with V38.

## ⚠ NOT ESTABLISHED
`gp-0x4f0c`'s physical identity (traced only to the generic analog IIR block `FUN_00063818`
@`0x63be0`/`0x63bf2`). No longer load-bearing for index sanity.

⚠ **THIRD `+0x1000` SLIP THIS SESSION.** The floor cal was reported as `0xC564C` = -6.0f. Verified:
`0xC564C` = **1.0f**; the -6.0f lives at **`0xC664C`** (`tp+0x664c`). Three separate agents hit this
class of error in one session — always re-verify tp-relative addresses against raw bytes.
