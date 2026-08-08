---
name: accord-v81-carries-neither-grind1-fix
description: V81 is byte-stock at both of the kit's measured grind-#1 fixes; the grinding on route 67 is an absence of any fix, not a regression.
metadata:
  type: reference
---

★★★★★ **V81 carries NEITHER of the two levers this kit has ever measured to fix grind #1.** Route 67's
grinding is therefore **not a regression — there was no fix on the car.**

**[EVIDENCE]** Orchestrator's own Python LE byte scan, 2026-08-08, across all 76
`_v*_plain_image.bin` plus `stock_fw_dump/code.bin`.

| lever | bytes | measured on-car | carried by | V81 |
|---|---|---|---|---|
| **A — V62's rate-lane `sar` ×2** | `0x3AB76` `AA`→`A9` (**r26**) + `0x3AC20` `AA`→`A9` (**r24**) | grind #1 **0.39 [0.32, 0.48]**, operator "gone"; 8× at creep, 42× at rate 16–32. ⚠ the **r24** half raised 40–49 Hz ×11.7 ⇒ **it caused grind #2** | **V62, V65, V71a ONLY** | ❌ `AA`/`AA` stock |
| **B — V67/V68's LKAS-gated r24 arm** | `0x3AA96` `C5`→`FB` (repoints `ld.bu -0x683c[gp]` → `-0x6806[gp]`, the LKAS gate; gate == `latActive` **99.983%**) + `0xC6446` 512→**5244** | grind #1 **0.40 [0.27, 0.58] — best in the kit** — AND **creep grind #2 → 0 bursts** (P(0)=0.0005). Mode-proof | **V67, V68, V71c ONLY** | ❌ `C5` / 512 stock |

V81's only grinding lever is the V74+ engaged-only FactorC/E damper — and the V80 four-point ladder shows
grind #1 is **INERT** to that dose across `k` = 0.58 → 4.16 (every point inside its own split-half null
[0.63, 1.60]). See [[accord-v80-damper-relay-and-grind1-inert]] and
[[accord-stock-mode24-equals-mode26-damper-is-ours]].

## 🛑 The same silent-loss pattern, for the THIRD time

Lever A was removed **deliberately as V66's confirmatory control and never restored**. Lever B was dropped
at V69. `0x454FE` (V42's ratchet fix) was lost at the V53 rebase. **Three confirmed fixes, each lost
without a decision, each leaving the record reading as though it were still on.**
⇒ `BUILD-LINEAGE.md` **RULE 3**: byte-check the current image before reasoning from any recorded result.
⇒ **When you remove a confirmed fix to run a control, write the restore into the next build's spec.**
Related: [[accord-v42-ratchet-fix-lost-since-v53]], [[accord-both-confirmed-fixes-were-off-the-car]].

## V81 vs V67/V68 — the entire functional delta is five cells

Everything else is already identical: `0xC646C`=891, `0xC6CD0`=3564 (**4× LKAS, decoupled**),
`0x2A1F0` disp=`0x7CD0`, `0xC61B2`/`0xC61B4`=2048, `0xC62EA`=0, `0xC407E`=511, friction stock,
**mode 24 byte-stock**.

| cell | V67/V68 | V81 |
|---|---|---|
| `0x3AA96` gate repoint | **`FB`** armed | `C5` dead |
| `0xC6446` gated r24 arm | **5244** | 512 |
| `0x454FE` V42 ratchet | `BA` | `B5` (on, but structurally inert — state 4 never occurs) |
| `0xC63A0` Path-2 damper weight | 1024 | **2048** |
| mode-26 FactorC/E | stock | **V75 damper armed**, `k` = 1.5798 |

## 🛑 The caveat that blocks the obvious build

Restoring lever B is **not** a complete answer: **V67/V68 had lever B on the car and the highway grind was
still present** — the handoff is titled *"the highway grind is NOT the rate lane"*. V81 has the damper and
no lever B, and still grinds at highway. **The highway symptom survives both levers and is unexplained.**
Lever B is well-supported for the *low-speed* scenario (turn-at-stops) only.

## Cave state on V81 (for any build that needs room)

`[0xC4B34, 0xC4FF0)`: V81 uses **68 B**, leaving **1,144 B free at `0xC4B78`**. The 330 hook `0x55C0E` is
taken (`86ff26ef`); **399's hook `0x55D50` and 427's hook `0x55EFA` are byte-stock on every build ever
made** — virgin. See [[accord-can-tx-gateway-whitelist-and-20-free-bits]].
