---
name: accord-c61d6-slew-is-rejected-not-fresh
description: "🛑 0xC61D6 (delivered-command slew step, 0 -> 14) is REJECTED, not untested: an 11-round 4-analyst review found slew=0 FREEZES a dormant 2D shaping lane and 0->14 ACTIVATES an uncalibrated map onto the live command. 'Highest-risk lever; last/never.' It was re-proposed as fresh on 2026-07-30 because it appears nowhere in BUILD-LINEAGE.md."
metadata:
  type: reference
---

# 🛑 `0xC61D6` is REJECTED, and it is the highest-risk lever in the file

**Do not propose it.** From `memory/project_accord_torque_mod_v0.md` (the V18 block, 2026-05-27), after an
**11-round, 4-analyst, decode-verified** Ghidra review:

> **V16 REJECTED:** slew `0xC61D6` 0→14 does not "re-enable a damper" — slew=0 **FREEZES** a dormant
> speed×torque 2D shaping lane (`gp-0x356c`, fed by curves `0xC6770`×`0xC69E8`); 0→14 **ACTIVATES an
> uncalibrated map onto the live command** (mux `0xC64C9`=0). **Highest-risk lever; last/never.**

Byte-verified 2026-07-30 across `_v31/_v38/_v42/_v53/_v55/_v57_plain_image.bin`: `0xC61D6` = **0**,
`0xC6424` = **29491**, `0xC64C9` = **0** in all of them — stock throughout the current lineage. V16 was
built (`old_tools/build_v16_tva.py:61`) but **never flashed**; there is no V16 `.rwd` or plain image on
disk.

## Settled by the same review

- **`0xC6424` (V17, deadband-only) is INERT** — it gates only the `gp-0x356c` limiter, and with slew=0
  that state is pinned at 0. **Deadband and slew are COUPLED**; neither is independently useful.
- **The real EME cut node is the override SM `gp-0x6960`**, not the shaper deadband.
- **`0xC64DE` (re-engage ramp) is the lever that actually targeted the recovery ratchet**, and it
  **LENGTHENS** re-engage (it was mislabelled "faster"). V18 flashed it 17→27 and the operator
  road-validated it — byte-verified 2026-07-30: still **27** in V31/V38/V42/V53/V55/V57. ⚠ It targets the
  **~10 s recovery** ratchet — the wrong timescale for the ~7.4 Hz ratchet.
- **There is NO output rate limiter available as a calibration.** `gp-0x6b98` has only ±0x2000 plus a ±5
  change detector; an asymmetric down-rate limiter would need a trampoline code patch
  (`0x43b52` → cave), scoped in that review and deliberately never built.

## 🛑 Why this memory exists — a process failure worth not repeating

On 2026-07-30 a subagent hunting a rate-limiter cause for the ~7.4 Hz ratchet surfaced this as a **fresh
candidate**. Two things allowed it:

1. **`0xC61D6` appears nowhere in `docs/BUILD-LINEAGE.md`** — that file covers V9→V58, and V16 is a
   pre-V18 `old_tools/` build. The lineage doc now carries the pre-V18 rejections and a rule saying so.
2. `.claude/agent-memory/firmware-codepath-tracer/reference_accord_slew_limiter.md` still **recommended**
   the edit ("FIX = set 0xC61D6 to 14 (V16)"). Corrected 2026-07-30 with a header; its addresses,
   encodings and structural notes remain accurate — only the recommendation was wrong.

⇒ **A "FIX =" line in a reference memory is not a lever recommendation unless the lineage agrees.**
Check `docs/BUILD-LINEAGE.md`, `analysis-2020accord/build_v*_tva.py`, **and** `old_tools/` +
`project_accord_torque_mod_v0.md` before calling any address untested.

Related: [[accord-check-build-lineage-before-proposing-lever]],
[[accord-ratchet-and-grinding-are-two-symptoms]]
