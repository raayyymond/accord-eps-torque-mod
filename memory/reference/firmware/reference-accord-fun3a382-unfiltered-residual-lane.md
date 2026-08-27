---
name: reference-accord-fun3a382-unfiltered-residual-lane
description: "FUN_0003a382 (gp-0x6ad4) is an UNFILTERED model-vs-reality residual lane on the physical Sensor-B torque sensor; its two \"lag\" gains are 1024 (unity passthrough), NOT 4 as the model recorded, so it carries tens-of-Hz content straight into the aggregator."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1b5347d0-4bca-4b24-acf8-731450f48b64
  modified: 2026-07-20T06:29:57.981Z
---

`FUN_0003a382` → `gp-0x6ad4` is the third, never-tested route by which Sensor-B column torque reaches
the aggregator. It is **unfiltered**.

```
errorterm = clamp( gp-0x4f60 − clamp(gp-0x6ad6, ±8192), ±0x2800 )
            gp-0x6ad6 (from FUN_00037fe6) = a FEEDFORWARD MODEL of expected column torque
            ⇒ errorterm is a MODEL-vs-REALITY RESIDUAL, recomputed every cycle
Stage A  (state gp-0x367c, gain cal 0xC6450 @0x3a7f0)  proportional branch
Stage C  (state gp-0x3680, gain cal 0xC644A @0x3a860)  RAW one-sample DIFFERENCE × L3, then this lag
         gp-0x3684 @0x3a840 is a PURE one-sample delay, rewritten unconditionally, unfiltered
→ gp-0x6ad4 → aggregator gp-0x6b94 → which IS the governor's slew target
  (verified: FUN_0004503c's first instruction @0x453e0 is `ld.h -0x6b94[gp],r6`)
```

**THE CORRECTION THAT MATTERS.** The golden model recorded both lag gains as **4** (τ≈256 cycles, *"VERY
heavily damped … argues against this lane resonating"*). **They are 1024** — Q10 unity. Byte-read by two
independent agents with different tooling across stock, V38 and V42. At unity,
`state += ((target*32 − state) × GAIN) >> 10` reduces to `state = target*32` exactly: **direct
assignment, not a lag**. The false verdict had been actively steering the investigation away from this
lane for multiple builds.

**Why it beats the gain-rescaling invariance argument.** That argument covers *digital* replay of counts
downstream of the gain. This term is sourced from a **physical sensor reacting to real delivered torque**.
Motor ripple scales with delivered torque (standard PMSM); V38 delivers ~4× the torque, so the *real*
ripple on `gp-0x4f60` is ~4× larger and passes unattenuated. The amplification happens in the **plant**,
so nothing digital compensated. ⚠ `[INFERRED, physical]` — the one link disassembly cannot close.

**Why V39/V41/V42 all missed it.** None of them touch `FUN_0003a382`, `gp-0x6ad4`, `gp-0x6ad6`,
`0xC6450`, `0xC644A` or L1/L2/L3. Same input family as r24/r26 (Sensor-B torque), completely independent
computational path — so falsifying two of three routes never falsified the family. See
[[v42-flashed-ratchet-fixed-r26-falsified]].

**Verified safety surface** (exhaustive 185,693-instruction operand scan): `gp-0x6ad4` has exactly TWO
touches image-wide (writer @`0x3a8a0`, aggregator reader @`0x3aca8`). `0xC644A` and `0xC6450` have
exactly ONE read each, both `ld.hu`, both inside this function — no `0xC61B8`-style signed/unsigned
split. All four internal states (`gp-0x367c/3680/3684/3688`) have zero reads outside it. The function is
a **pure leaf — zero `jarl`** — so nothing inside it can raise a shadow-mismatch fault, and no `-0x4c`
displacement (this kit's lockstep-shadow idiom) appears anywhere in it.

Also on record here: the aggregator's gate on `gp-0x6ad4` is a **ZERO-type** gate at ±0x2800 —
out-of-window contributes *exactly 0*, not a clipped value. A ripple crossing that boundary on peaks
makes the lane snap to zero and back at the ripple's own rate. Independent chatter candidate; unquantified.

Related: [[v43-dirty-derivative-pole-built]] · [[reference-accord-gain-rescaling-invariance-partition]]
