---
name: reference_accord_gp4f60_identity_conflict_and_producer_traced
description: gp-0x4f60's actual producer (FUN_0007f3f8) traced for the first time in this kit (previously flagged UNSWEPT in STATE.md) — a dual-channel plausibility/cross-check SM with a cal-gated scale+offset+clamp compensation, NO EMA/IIR. Surfaces an unresolved identity conflict between two kit memories: torque (the dominant, DBC-grounded view) vs. an older memory's "signed motor/column angular velocity."
metadata:
  type: reference
---

# gp-0x4f60 producer traced + identity conflict flagged — 2026-08-10, `fw-driver-model` task

`docs/STATE.md` listed "the raw CAN → gp-0x4f60 producer" as one of two UNSWEPT regions in the kit's
"no notch/biquad anywhere" sweep. Swept this session.

## Producer, traced via search_instructions (get_xrefs_to gave a FALSE "no references" — the
misleading-zero trap on gp-relative displacements; search_instructions found it)

Writers: `FUN_0007ec34` (1 site, zero-write, fault/reset path) and `FUN_0007f3f8` (4 sites: 2
zero-writes on fault paths, 1 direct passthrough, 1 the "valid" compensated write). Caller of
`FUN_0007f3f8`: `FUN_0006bb08`.

`FUN_0007f3f8` decompiled in full: a **dual-channel plausibility/cross-check state machine**. Reads two
redundant candidate channels indexed by a channel byte (`gp-0x27fa`), computes a candidate via
`FUN_0006af38`/`FUN_0007f300`, plausibility-gates it against `gp-0x4f60`'s OWN prior value
(`|candidate-gp-0x4f60| vs threshold gp-0x4f56`), escalates DTC-maturing counters on failure
(`FUN_0005bb04`/`FUN_0005ae6a`/`FUN_0005b650`). On the valid path, a cal-gated correction runs
(`tp+0x74c3`=`0xC63C3`, byte-read = **4, ENABLED on stock**):
```
iVar8 = clamp(gp-0x6b50 + ((iVar8 * gp-0x698c) >> 10), ±gp-0x4f54)
gp-0x4f60 = iVar8
FUN_0007e74a()          # called AFTER the store — consumer/dispatcher, not a filter
```
**No EMA/IIR/z⁻¹ anywhere in this store path** — confirms (with the actual producer now traced)
`docs/STATE.md`'s existing "gp-0x4f60 is a SINGLE physical measurement... no EMA/IIR" claim. A
reaction torque appearing physically in the sensor at any frequency reaches gp-0x4f60 with zero
firmware-side attenuation.

## 🛑🛑 IDENTITY CONFLICT — FLAGGED, NOT RESOLVED

`reference_accord_gp6af8_fight_trigger.md` (2026-05-29, this kit's own memory) labels this SAME cell
"SIGNED MOTOR/COLUMN ANGULAR VELOCITY," citing the identical `FUN_0007f3f8`/`gp-0x6b50`/`gp-0x698c`
writer chain independently re-derived this session (structurally correct — the writer trace matches).
Every later, more-corroborated source calls it **torque**: the golden model, `docs/STATE.md`, dozens of
`reference_accord_gp4f60_*` memories, and — decisively — `reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md`'s
direct CAN399 bridge: `CAN399.STEER_TORQUE_SENSOR = -floor(gp-0x4f60*125/128)`, an externally
DBC-documented torque field.

**Working conclusion: torque** (BELIEF — the DBC bridge is inherited evidence, not independently
re-derived this session). The old fight-trigger memory's physical LABEL is likely wrong even though its
writer-trace mechanics are right; a velocity signal driving a documented torque CAN field would be a
much larger anomaly than one old memory mislabeling a quantity. **Flagging for whoever next needs
gp-0x4f60's identity pinned with certainty — do not silently trust either memory without re-deriving.**

## Related
[[reference-accord-gp6a5e-sensorA-magnitude-no-can-bridge]] — the CAN399 bridge this leans on.
`reference_accord_gp6af8_fight_trigger.md` — the conflicting older memory (not renamed/fixed this session).
