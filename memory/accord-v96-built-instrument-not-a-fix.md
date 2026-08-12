---
name: accord-v96-built-instrument-not-a-fix
description: "V96 is an instrument build on a V92 base with ZERO calibration bytes — it measures gp-0x6b70 against gp-0x374c>>4 to get the LERP slope that blocks every FUN_00038148 weight lever. The number V95 is VACATED; three artefacts wore it."
metadata:
  type: project
---

# ★★★★ V96 — BUILT, VERIFIED, UNFLASHED. AN INSTRUMENT, EXPLICITLY NOT A FIX

```
image  876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3
.rwd   7e9a65f11cab4ffc6286f0365ce5196c11dc461468b9ec85022775e35ebdf093
39990-TVA,A160-V96-V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6-0x13000-0x100000.rwd
builder: analysis-2020accord/build_v96_tva.py   166/166, reproduces bit-for-bit
```

**107 bytes vs V92 in 7 runs. ZERO calibration** — no diff in `[0xC6000,0xC7000)` or
`[0xD6000,0xD8000)`, all four authority-curve records byte-identical to stock. **112-byte cave inside
V92's proven 116-byte footprint — no growth**, 4 bytes back to virgin. V94's `0xCBE74` cut is reverted
**by construction** (V92 base, every cal cell asserted against V92's *image*, not against a script).
⊕ Both measured on-car wins carried and asserted **as a pair**: `0xC6446` = 5244 **and** `0x3AA96` =
`0xFB`. Plus `0x454FE` = `0xB5`, carried but **MEASURED INERT** and claimed for nothing.

## WHY THIS PAIR AND NOTHING ELSE

**`gp-0x6b70` is a PID REFERENCE that gets SUBTRACTED, not an aggregator addend** ⇒ **no
`FUN_00038148` weight can be moved until the LERP's local slope is measured.**
⇒ [[accord-fun38148-weights-have-an-unresolved-sign]]

The pair yields that slope directly, because
**`d(gp-0x6b70)/d(gp-0x374c>>4) = −f′` independently of `sign(iVar6)`, `gp-0x6bfe` and `gp-0x6bfa`** —
the two sign factors square to +1 and cancel. **No third channel is needed.**

- **CAN 427** ← `gp-0x6b70`, `sar 6`. **LSB 12.8 ct**, no-clip (`8192×5>>6 = 640 ≤ 1023`), 6–9 Hz floor
  ≈ 3.6 ct.
- **`0x14A`** ← **`gp-0x374c >> 4`** using **Honda's own shift `@0x38236`** — the instruction that forms
  this very term of `iVar6`. **Saturating at 12288, LSB 2048**, deliberately below the 68,614
  structural bound because **neither cell has ever been on the wire**; the **saturation duty and the
  8-code histogram are first-class reported outputs** so the next build sizes off data.
- `b3` = `gp-0x674e < 28` — settles **RULE 7** for the authority curve permanently.
- **Identity:** `byte7 b6 ≡ 1` ⇒ any single frame with `0x14A` byte7[7:6] ≠ 0 proves V96. V94 carries
  the 74-byte V90 cave and *cannot* write byte 7.

## PRE-REGISTERED: TWO SLOPES, NEVER MERGED
- **S1** lag-0/1 ⇒ **open-loop `f′`. Its SIGN decides whether any Path-2 weight lever helps or inverts.**
- **S2** coherence-weighted, longer window ⇒ **closed-loop**, folding in `L`.
- ⚠ Errors-in-variables attenuates both magnitudes and **preserves both signs** ⇒ magnitudes are lower
  bounds.
- 🛑 **If S1's CI spans zero the answer is "`f′` is NOT RESOLVED by this flight" — NOT "`f′` is zero" —
  and the weight class stays blocked.**

## 🛑 TWO HONEST WEAKNESSES, BOTH SELF-DECLARED BY THE BUILDER
1. **Separation from V92 is BELIEF, not EVIDENCE** — a step *down* from an earlier cut. V92 also writes
   byte 7; the separator is its b6 measuring **duty 0.0000 over 75,227 engaged frames**, which is a
   measured duty, **not an impossibility**. The structural byte4 codeword was spent on the saturating
   regressor.
2. **The freeze exclusion is a WIRE-SIDE HEURISTIC, not a gate read.** `FUN_00038148` sits behind a
   `gp-0x67fa` state gate; when it shuts, **both** members of the pair freeze and would enter the
   regression as **spurious zero-slope samples**. 🛑 **The exact gate is UNREADABLE BY A CAVE** — the
   boolean is **never stored** (`r28` written once `@0x221D6`, tested `@0x22672`, no store in
   `[0x2214A,0x22700)` sources it), recomputing needs a **Format IX `shl reg,reg,reg`** (the
   hand-encoding class that bricked V24/V27/V48B), **and the affordable `4 ≤ s ≤ 11` approximation is a
   SUPERSET that would silently read "live" while the pair is held — worse than no bit, because it
   would be trusted.** Fallback: drop runs of ≥5 frames where the 427 code **and** byte4 are both
   bit-exactly unchanged, and report the dropped fraction.

## 🛑🛑 THE NUMBER V95 IS VACATED — NEVER REUSE IT
Three artefacts wore it inside two hours while the spec moved. **Retiring the number is cheaper than
disambiguating it forever.** `build_v95_tva.py` was deleted.
```
DEAD  lane build (6B4C/6B4E)   image ad8643c1f37ac128c57606c60ad6225420884f3fa250ffd978f9efa6a5fb7faf
DEAD  lane build (6B4C/6B4E)   .rwd  3a791446c268b2b0660e4035a82c51f93572b662faa6225167f16e331277c9d6
DEAD  pair build numbered V95  image 876cf2be…  .rwd 7e9a65f1…   <- SAME BYTES, now correctly V96
```
⊕ **Cause, and it is a process lesson:** the orchestrator **reported hashes to the operator while the
spec was still moving**, then the design changed twice. **The freeze rule exists for exactly this.**
⇒ [[feedback-name-superseded-hashes-dead-not-merely-omitted]]

## ⊕ THE LANE DESIGN IS NOT LOST — IT IS V97
`gp-0x6b4c` / `gp-0x6b4e` are the **disjoint partition sums of the same 11-slot request array
`gp-0x62f8[]`**, split by the mode bytes at `0xC4124` (`00 00 05 00 05 05 00 00 00 05 00`) — the two
halves of the EPS's own internal torque-request bus, **±10240 each, 5× and 10× the other two lanes**.
`gp-0x6b4c` is **also a direct unity-weight aggregator summand** (`0x3AA3E`, both branches) ⇒ it reaches
the motor by **both** paths. **Both gates are structurally always open** (producer clamps to exactly
±0x2800; the gate passes ±10240 inclusive) ⇒ **the V64-class null is excluded BY ARITHMETIC.**

Links: [[accord-fun38148-weights-have-an-unresolved-sign]] · [[accord-v94-flew-and-the-lane-is-a-damper]] ·
[[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]] ·
[[accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee]] ·
[[feedback-name-superseded-hashes-dead-not-merely-omitted]] · [[accord-v64-null-is-on-the-gate]]
