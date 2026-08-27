---
name: accord-v74-hard-faulted-in-manual-over-a-bump
description: 2026-08-06 — V74 hard-faulted in MANUAL (LKAS disengaged) over a bump, latched total loss of power steering. The FactorC/FactorE edits were NOT in force (mode 24 is byte-stock). Voids k* in (0.580, 1.580] and voids "V74 flew 1,011 s clean" as a safety anchor.
metadata:
  type: reference
---

# ★★★★★ V74 HARD-FAULTED IN MANUAL, OVER A BUMP — and its damper edits were NOT in force

**2026-08-06.** The operator reported a **latched total loss of power steering with LKAS DISENGAGED,
driving over a bump.** EPS lamp on continuously; **still on after an engine restart**; extinguished
after ~30 s of driving.

That lamp sequence is the classic **DTC-maturation** signature and it is self-consistent: fault set with
`warningIndicatorRequested` → assist latched off → power cycle restores assist but **not** the lamp →
the monitor re-runs clean on the new cycle → the indicator is dropped. Nothing about it requires a
second, separate fault.

## 🛑 [EVIDENCE, orchestrator-verified TWICE] The FactorC/FactorE edits were NOT in force

Disengaged = **mode 24**, and **all five mode-24 damper records are byte-identical to STOCK on V74 and
V75**:

| factor | address | mode-24 content (stock == V74 == V75) |
|---|---|---|
| **FactorC** | `0xD67E4` | `X=[2240,3840,5120,8960]` `Y=[0,234,429,908]` |
| **FactorE** | `0xD6820` | `X=[60,400,2500,4000]` `Y=[0,140,539,927]` |
| FactorB | `0xD6760` | stock |
| FactorD | `0xD67A4` | stock |
| Ceiling | `0xD60B4` | stock |

Independently, from the other direction: **0 of the 54 non-CRC V73→V74 diff runs land inside any mode-24
record.** Two methods, same answer. See [[reference-accord-car-is-tvca4-mode-24-26]] — the engaged
(mode 26) and disengaged (mode 24) column sets are disjoint, which is exactly what the V74 design relied
on and exactly what makes this fault *not* attributable to the damper.

## 🛑🛑 THE CONSEQUENCE — two load-bearing claims are VOID

1. **`k* ∈ (0.580, 1.580]` is VOID.** That bracket was constructed from "V74 (k = 0.5799) flew clean,
   V75 (k = 1.5798) hard-faulted." The lower end of the bracket has now hard-faulted too.
2. **"V74 flew 1,011 s clean" is no longer a safety anchor.** Every gain-margin argument in the V75
   analysis rested on it, including the refutation ledger's dwell/duty arithmetic
   ([[reference-accord-v75-fault-refutation-ledger]]).

⇒ **No build in the current lineage has demonstrated safety.** Treat every "V74 is the known-good base"
statement anywhere in the record as withdrawn until a build flies clean again.

## ★ What IS live in manual and non-stock on V74

None of these is mode-indexed, so all of them are in force with LKAS off:

| cal | value | since |
|---|---|---|
| `0xC63A0` | **2048** (stock 1024) | V72 — the Path-2 loop weight, see [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]] |
| `0xC407E` | **850** (stock 511) | V73 |
| `0xC61B2` / `0xC61B4` | **2048** | V38 |
| boost floor | **5120 / 5.0** | V38 |
| `0xC62EA` | **0** | V53 (steer-to-zero) |

🛑 **None of these is NEW at V74.** V72 and V73 carried the same manual-mode configuration and produced
**no manual fault** ⇒ **n = 1**, and the trigger may simply be *the first sufficient bump*. Do not read
the manual-mode config as identified; read it as the surviving candidate set.

Related: [[accord-v75-fault-pinned-to-the-frame]] · [[accord-descriptor-bit13-is-the-fault-fingerprint]] ·
[[accord-dtc-read-is-structurally-blind-here]] · [[reference-accord-v74-v75-damper-is-a-sampled-relay]] ·
[[feedback-rule7-mode-proof-or-a-bet]]
