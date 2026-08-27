---
name: reference-accord-v42-fix-was-the-r26-kill
description: "V42's confirmed fix was the r26 kill, not 0x454FE. 🛑 CORRECTED 2026-08-08 — 0xC643E and 0xC6444 are UNREACHABLE (gp-0x671a's only writer is fed by gp-0x67df, never non-zero), so V42's only live change vs stock was gain_A -> 0."
metadata:
  type: reference
---

> 🛑 **CORRECTED 2026-08-08 — TWO OF THE FOUR "LIVE" ROWS ARE UNREACHABLE.**
> The table below lists **`0xC643E` (1536 → 0)** and **`0xC6444` (512 → 0)** as live changes. **They are
> not.** Both are read only through the `lp` arm, whose gate derives from **`gp-0x671a`**, and
> `gp-0x671a` has **exactly ONE writer, @`0x42A12`, fed only by `gp-0x67df` — which has never been
> non-zero in this kit.** ⇒ **those two loads never execute; zeroing them changes nothing.**
> *(Consistent with [[accord-r26-is-structurally-inert]]'s `0xC6444` strike, and with
> [[accord-gp671a-blast-radius-not-a-free-lever]].)*
>
> ⇒ **V42's ONLY live change vs stock was `gain_A` → 0.** That narrows this note's attribution rather
> than overturning it — but it also means the r26 kill was **not** as deep as the four-row table implies.
> ⚠ And the pattern table further down is separately weakened: **grind #1 follows r24, not r26** —
> [[accord-r24-is-the-grind1-actor-r26-nearly-blind]]. The **ratchet** column is untouched by that
> finding (different symptom, still operator-report-only).

# ★★★★ V42's CONFIRMED FIX WAS THE **r26 KILL**, not `0x454FE` — a two-session [OPEN] closed

**Byte diff of `_v42_plain_image.bin` vs `_v41_plain_image.bin` over `[0x13000, 0x100000)`, 2026-08-05.**
For eleven months `BUILD-LINEAGE.md` read *"`0x454FE` — CONFIRMED ROOT CAUSE, fixed the hard-turn
ratchet, carry forward."* That attribution is **wrong**, and the correct one was sitting in the same
table marked **FALSIFIED**.

## V42's functional delta over V41 — [EVIDENCE]

| site | V41 → V42 | live? |
|---|---|---|
| `0x454FE` | `ba` → `b5` (`bne`→`br`) | 🛑 **never executes** — `gp-0x67fa == 4` reads 0/123,277 and 8/92,826, all in PARK |
| `0xC5030` · `0xC521A` · `0xC5232` | **reverted to stock** — undoes V40/V41's motor-rate cap test | live (confound) |
| **`gain_A` all four records** `0xC6A68` · `0xC6A7C` · `0xC6A90` · `0xC6AA4` | `[3072,3072,2434,2048]` etc. → **`[0,0,0,0]` × 4** | ✅ **LIVE — `gain_A` is NOT mode-indexed** |
| **`0xC643E`** 1536 → **0** · **`0xC6444`** 512 → **0** | r26's arms | live |

⇒ **V42 killed the r26 rate lane completely.** Since ch.1 never executes, the live candidates for V42's
confirmed hard-turn-ratchet improvement are **the r26 kill** and, as a confound, the V41 cap revert.

## Why it hid — [[feedback-rule7-mode-proof-or-a-bet]] corollary (b)

V42 ch.2 was scored **FALSIFIED against the VIBRATION**. It was never scored against the **ratchet**,
which is what V42 actually fixed. **A verdict without a named symptom is not a verdict.** V47 failed the
same way one lane over.

## ⚠ The wider pattern — [BELIEF, suggestive but NOT established]

An exhaustive scan of every image whose r26 lane is non-stock:

| build | net live r26 | ratchet, operator report |
|---|---|---|
| **V42** | **×0 — killed** | ✅ **FIXED** (hard-turn) |
| V62 · V65 | **×2 — raised** (`sar`, mode-proof) | present |
| V67 · V68 | ÷6 — cut (gate + `0xC6444`) | not separately reported |
| V69 · V70 | **stock** (`gain_B` m10 ⇒ inert) | present |
| V71C | **cut REMOVED → ≥ stock** | present — corpus-record 8,521 counts p-p |
| **V72 · V73** | **÷6 — cut** (`gain_A` rec0/rec1 → 512) | ✅ **FIXED** (macro) |

**The only two builds reported as ratchet improvements are the only two that cut r26 through a mode-proof
path**, and the build that *removed* an r26 cut carries the worst amplitude.

🛑 **Read this as a leading hypothesis, not a result.** n = 2; the verdict column is **operator report,
not measurement**; every instrument built for the macro ratchet **failed its own positive control**; and
**the one quantity that IS measured points the other way** — the micro ratchet (7.79 Hz) has never moved
on any build, V72 included (attenuation 1.0, three instruments). V71C's 8,521 p-p is a *micro*-ratchet
number and must not be read as macro evidence.

⚠ **V72/V73's cut is PARTIAL**: `gain_A` `rec0`/`rec1` → flat 512 but **`rec2` `0xC6A90` and `rec3`
`0xC6AA4` are byte-stock** ⇒ creep-only by record selection; ≥50 km/h is untouched. Leave it exactly as
is — do not restore, do not deepen.

Related: [[accord-0x454fe-test-was-vacuous-state4-never-occurs]], [[accord-r26-is-structurally-inert]],
[[accord-v42-ratchet-fix-lost-since-v53]], [[accord-two-ratchets-micro-is-the-779hz-line]].
