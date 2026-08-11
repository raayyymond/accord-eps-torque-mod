---
name: reference-accord-three-signal-identity-recurrences
description: "Three signal identities re-asserted wrongly in one session, each already settled elsewhere in the repo: gp-0x6a5e is VEHICLE SPEED not driver torque; gp-0x4f50 is a RATE not an angle; gp-0x6afe is the same cell as gp-0x6b4e. All three were caught by a teammate cross-checking an inherited claim, not by the agent that made it."
metadata:
  type: reference
---

**[EVIDENCE for each identity; the meta-point is the reason this file exists.]** 2026-08-10. Three
signal identities were asserted wrongly inside one session. **Every one was already settled in this
repo, and two had been settled weeks earlier.**

## 1. `gp-0x6a5e` is voted **VEHICLE SPEED**, not driver torque

Settled **2026-07-29** by two independent traces plus a byte-verified pointer chase — the voter is
`FUN_00041eec`, the validity window `-6400 ≤ x ≤ 32000` is nonsensical for a torque sensor, and there is
exactly **one** torque sensor in the traced data flow (`gp-0x4f60`). Full detail:
[[reference-accord-gp6a5e-is-speed-reclassifies-v44-v47]].

🛑 **The earlier version of this same error already cost two flashed builds.** V44 and V47 were built on
*"the damping product is multiplied by zero below 2240 counts of DRIVER TORQUE (hands-off)"*. It is a
**speed** breakpoint. Their on-car results stand; **their stated mechanism does not.** Re-asserting the
torque reading in 2026-08 would have re-run that mistake a third time.

## 2. `gp-0x4f50` is a **RATE**, not an angle

The proof is in the arithmetic, not in the name: the producer takes a **modular difference and then
wrap-corrects it**. A wrap-correction is only meaningful on a *difference of a wrapping quantity* — i.e.
it is producing a **rate**:

```python
d = (angle_now - angle_prev) & 0xFFFF        # modular difference
if d >  0x7FFF: d -= 0x10000                 # wrap correction  <-- this is the tell
if d < -0x8000: d += 0x10000
gp_0x4f50 = d                                # counts per tick == a RATE
```

⊕ **`0x8000` on the STORED ANGLE is an INIT/INVALID sentinel**, not a real reading — it is the "no valid
angle yet" marker, and treating it as data injects a half-scale step. Do not carry it into a difference.
⊕ Consistent with `gp-0x6abc ← gp-0x4f50` being the **motor rate** in the Coulomb identification
([[accord-friction-polarity-more-friction-is-more-assist]]).

## 3. `gp-0x6afe` ≡ `gp-0x6b4e` — the same cell under two names

The mixer's **tail-call `FUN_00042ac6` writes it**. They are not two signals to be reconciled, correlated
or separately probed; treating them as distinct manufactures a "coupling" that is an identity.
🛑 Consequence: **a probe rung on one is a probe rung on the other** — spending two cave bits on them
buys one bit of information.

## 🛑 The meta-point — this is the part worth remembering

**All three were caught by a TEAMMATE cross-checking an inherited claim, never by the agent that made
it.** An identity label is the cheapest thing in a brief to copy forward and the most expensive thing to
get wrong: it survives byte verification, CRC checks and a clean flight, because nothing in the build
pipeline tests what a signal *means*.

**How to apply:**
- **A signal label inherited from a brief, a memory, a variable name or a previous spec is a BELIEF
  until you re-derive it from the arithmetic.** Say which it is.
- **Re-derive from the producer, not the consumer** — the wrap-correction, the validity window, the
  units of the breakpoints. [[feedback-explain-with-python-mirroring-decompiled-arithmetic]].
- **Before quoting a breakpoint in physical units, confirm the INDEX variable's domain.**
- **Cross-check every decision-bearing identity against a second agent or a second method.** That is what
  worked all three times; nothing else did.

See [[feedback-a-count-is-not-a-physical-fact]], [[reference-accord-an-address-is-not-a-mode]],
[[feedback-neither-ghidra-nor-python-alone-is-complete]], [[accord-plant-model-residual-aggregator-chain]].
