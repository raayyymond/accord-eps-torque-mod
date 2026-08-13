---
name: accord-v97-is-a-loop-pole-and-the-direction-is-measured
description: V97 = 0xC63AC 102->150, ONE BYTE on a V96 base — the arc's first loop-pole lever. Direction settled by TWO independent on-car measurements agreeing to <7°, after one of them was caught inverted by a scipy csd sign convention.
metadata:
  type: project
---

**V97 is `0xC63AC` 102 → 150 — the Path-2 IIR pole in `FUN_00038148`. BUILT, VERIFIED, UNFLASHED.**

```
39990-TVA,A160-V97-V96BASE-C63AC.102to150-0x13000-0x100000.rwd
  .rwd  78c674a899971a6a9763c2d7c89bf4c9169f35dfba3fbe4ce62d9bc445a17372
  image 7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3
  builder analysis-2020accord/build_v97_tva.py   131/131   BASE = V96 (on the car)
```

**The whole delta is ONE BYTE.** 102 = `0x0066`, 150 = `0x0096` — the high byte is `0x00` in both, so
only the low byte moves, plus its own CRC trailer at `0xC6FFC`.
`gp-0x374c += ((target − gp-0x374c) × A) >> 10`, sole reader `@0x38202`, **1 reader / 0 writers**
established five ways. **Virgin across all 99 images** (orchestrator-verified from disk).

🛑 **DC gain is 1.000000 at ANY A — it is a POLE, not a GAIN.** It cannot change how hard the car
pulls, only *when*. **That is the entire reason it escapes the sign problem** that disqualified all six
Path-2 lane weights (`0xC63A0`…`0xC63AA`).

## THE DIRECTION IS MEASURED, AND IT IS **UP**
Two independent instruments, agreeing to **<7°** after a bug was removed:
1. **`Q = −d(gp-0x6b70)/d(T)`** — 427 magnitude + sign bit vs `0x18F` STEER_TORQUE_SENSOR, hands-off
   engaged returns, episode-bootstrapped (`rlog-tools/v97_measure_Q.py`):
   **|Q| = 1.233 on BOTH routes**, arg Q −133.7°/−131.5°, coherence **0.974/0.978**.
   The criterion (fw-loop) is *inversion iff `|Q| < 1` AND `cos(arg Q) < −|Q|`* ⇒ **`|Q| > 1` excludes
   inversion at ANY phase**, so the ±28° CAN-join uncertainty — the dominant error term — is **moot**.
2. **The V96 cave's own sign bits**: `arg(V) − arg(B′) = −178.1°` on both routes (reproduced
   independently at +179.8°/+178.6°, coherence 0.215/0.107 vs shuffled 0.0066/0.0041) ⇒ `iVar6`'s
   6–9 Hz phase is set by the **B branch**, so this pole rotates essentially all of `Q`.

**`arg(V)` sits just below −90° ⇒ `cos < 0` = ANTI-DAMPING** — the corpus `Re(Z) < 0` seen on a
firmware-internal signal for the first time. **Adding lead rotates it toward the damping axis.**

## 🛑🛑 THE DIRECTION WAS INVERTED ONCE, AND ONLY DISAGREEMENT CAUGHT IT
`scipy.signal.csd(x, y)` returns **`arg(Y) − arg(X)`**. An agent labelled every cross-spectrum
backwards and recommended **lowering** this cell — which would have made the car worse. The tell was a
**replicated ~90°** disagreement with instrument 1: a bug signature, not physics.
⇒ **Run two independent instruments and let them disagree.** See [[feedback-run-the-control-before-the-measurement]].

## THE COST — stated, not hidden
**+2 %…+13 % at 21 Hz on the total command** (Path-1 dilution — a MODEL, not a measurement), where
V62 bought grinding (18–22 Hz down 8–42×) and V88's Lever B lives. Worst case 1.13 × 0.549 = 0.620,
inside V88's CI. 🛑 **Exchange rate is FLAT at 0.33° per 1 % of 21 Hz — no sweet spot.**
**A = 150 was the operator's own choice with the trade stated.** RULE 9 applies.

🛑 **V97 IS NOT A RETURN-SPEED FIX.** Clause 2 of the operator's spec has **no mechanism** — see
[[accord-the-return-to-centre-crux-and-what-died-for-it]]. Do not score it as one.

Links: [[accord-v96-flew-as-7e-7f-and-the-record-said-v94]] ·
[[accord-ram-lerp-is-flash-derived-and-fprime-is-nonneg]] ·
[[accord-check-build-lineage-before-proposing-lever]]
