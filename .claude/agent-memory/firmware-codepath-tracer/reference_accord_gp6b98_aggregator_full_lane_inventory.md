---
name: reference_accord_gp6b98_aggregator_full_lane_inventory
description: Full lane-by-lane inventory of FUN_0003aa2c (the gp-0x6b98 command aggregator) with bandwidth/attenuation-at-20Hz for every summed term; identifies gp-0x67ac as a hard on/off gate that zeroes 5 of the 9 lanes wholesale; new finding that gp-0x6bbe/gp-0x6bd0 (FUN_00034a72/FUN_00034350) are near-transparent to 20Hz (-1.2dB), previously unflagged as carriers.
metadata:
  type: reference
---

# gp-0x6b98 aggregator: complete lane inventory, traced 2026-07-28 for team-lead's "which lanes can carry 20Hz" audit

Entry point: `FUN_0003aa2c` (the aggregator), fully decompiled on `code.bin` (stock). Task rate 1000Hz per
[[control-task-tick-confirmed-1khz]]. Total sum clamps to ±0x2800 (10240), shadow-lockstep-written to
`gp-0x6b94`/`gp-0x4ce0` (`FUN_0006b9fa` on mismatch).

## THE gate that matters most: `gp-0x67ac`

`FUN_0003aa2c` has two mutually exclusive modes selected by `(byte)(gp-0x67ac * (gp-0x67ac<2)) == 1`, i.e.
true only when `gp-0x67ac` is **exactly 1**:
- **==1 (suppressed):** ONLY `gp-0x6b62`, `gp-0x6ade`, and `gp-0x6b4c` (LKAS) contribute. Every other lane
  below is hard-zeroed, no matter its own bandwidth.
- **0 or ≥2 (normal):** all lanes below sum, plus a call to `FUN_00036682`.

This is the SAME `gp-0x67ac` as [[reference_accord_gp67ac_aggregator_lane_suppression_gate]]
("wholesale on/off, trigger UNRESOLVED"). **Its trigger condition is still not traced** and is the single
biggest open variable for any 20Hz-carrier verdict — if it's ==1 during an on-car measurement, only the
LKAS lane (heavily attenuated, see below) is even in play.

## Lane table (bound = this function's own clamp on that lane before summing)

| Lane (gp-) | Writer fn | Bound | Filter / cal (fresh `read_memory` on code.bin) | fc | Attenuation @20Hz |
|---|---|---|---|---|---|
| `0x6ad4` | `FUN_0003a382` | ±10240 | Two 32-bit EMA stages, both coeff=1024/1024 (unity, zero lag): `tp+0x7450`=`0xC6450`=1024, `tp+0x744a`=`0xC644A`=1024. Output-limit LERP (idx `gp-0x6966`) confirmed unity/no-op per [[v54-flashed-authority-measured]]. | ∞ | **0 dB** — widest-bandwidth lane structurally |
| `0x6bbe` | `FUN_00034a72` | ±2048 | 1st-stage EMA on raw Sensor-B torque (`gp-0x4f60`), coeff `tp+0x7372`=`0xC6372`=205/1024=0.2002 | 35.6 Hz | **-1.2 dB — NEW finding, not previously on record** |
| `0x6bd0` | `FUN_00034350` | ±2048 | Same pattern, coeff `tp+0x736e`=`0xC636E`=205/1024=0.2002 | 35.6 Hz | **-1.2 dB.** This is the function [[reference_accord_fun34350_damping_term_live_and_gated]] already flagged as "net-damps at 21.4Hz" — this session supplies the mechanism: its input EMA barely attenuates 20-21Hz at all |
| `0x6b86` | `FUN_000352b4` | ±12288 (largest single lane) | Adaptive integer EMA/peak-hold, α∈[2/2048,204/2048] gated by recent signal dynamics. 2nd-order float "resonant" branch (coeffs `0xC60A8`/`0xC60AC`/`0xC60B0`/`0xC60B4`) confirmed **gated OFF in stock**: enable byte `tp+0x749b`=`0xC649B`=**0** (fresh read, matches [[reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole]]'s biquad-dead finding). | 0.16–16.7 Hz (adaptive) | **-3.9 dB at max α** — weakest exactly when the signal is swinging fast (self-reinforcing under sustained oscillation) |
| `0x6b4c` (LKAS) | `FUN_00026c80` | ±10240 | Per team-lead's confirmed context: IIR `gp-0x3d3c`, pole 0.96875=31/32, before gain mult @`0x2a1ee` | 5.05 Hz | **-12.0 dB** |
| inline `iVar21` (friction/boost, dynamic) | inline in aggregator | ±8192 | Motor-rate(`gp-0x6ac0`)-indexed LERP × Sensor-B-derived scale (clamped ±5120 off `gp-0x4f62`); no time filter in this block | n/a | **0 dB structurally**, but amplitude driven more by motor RPM operating point than road torque |
| inline `iVar16` (friction/boost, deadbanded) | inline in aggregator | ±8192 | Same LERP family + deadband vs `tp+0x71f6`=`0xC61F6`; deadband doesn't band-limit AC content once past threshold | n/a | **0 dB structurally**, same caveat |
| `0x6b62` | `FUN_00036388` | ±8192 | Dominated by accumulator `gp-0x6a82` ramping **exactly ±1 LSB/cycle**, hysteresis `tp+0x718a`=`0xC618A`=20 | ~0 Hz | effectively fully blocked — a saturating integer ramp, not exponential, cannot track 20Hz regardless of input. Two untraced raw sub-terms (`gp-0x6b64`,`gp-0x6b96`) feed it additively — low-confidence this changes the verdict |
| `0x6b46`/`FUN_00036682` direct term | `FUN_00036682` | ±512 (smallest) | EMA coeff `tp+0x73d2`=`0xC63D2`=**6/1024=0.00586** (⚠ see [[reference_accord_c646c_gain_feedback_vs_forward_classification]]'s addendum — this contradicts that file's recorded "14", unresolved discrepancy, both read on code.bin) | 0.93 Hz | **-26.6 dB** |
| `0x6b26` | `FUN_00036c12` | ±1024 | Not decompiled — **open item** | — | — |
| `0x6ade` | none found | ±1024 | Unrestricted `search_instructions` for "6ade" (all mnemonics) finds exactly ONE hit in 183,429 analyzed instructions — the aggregator's own read at `0x3aa48`. Zero writers. Not corroborated with a raw 6-byte-encoding byte scan (budget) — flag as open, not declared dead | — | — |

## Ranking, most→least able to carry 20Hz at meaningful amplitude
1. `gp-0x6ad4` (`FUN_0003a382`) — 0dB, ±10240.
2. `gp-0x6bbe`/`gp-0x6bd0` (`FUN_00034a72`/`FUN_00034350`) — -1.2dB each, ±2048 each. **New this session.**
3. `gp-0x6b86` (`FUN_000352b4`) — -3.9dB at its fastest, ±12288 (largest lane in the whole aggregator).
4. `gp-0x6b4c` (LKAS) — -12.0dB, ±10240.
5. inline `iVar21`/`iVar16` — structurally wideband but indirect (motor-RPM-indexed, not road-torque-indexed).
6. `FUN_00036682` — -26.6dB, ±512. Weakest; confirms/strengthens the existing downgrade of this chain.
7. `gp-0x6b62` — ruled out (self-rate-limited to ~0Hz).
8. `gp-0x6b26`, `gp-0x6ade` — unresolved/likely negligible.

## What's still open
- `gp-0x67ac`'s own writer/trigger — decisive, not traced this session.
- `gp-0x6b26` writer (`FUN_00036c12`) — not decompiled.
- `gp-0x6ade` zero-writer result — needs a raw byte scan corroboration before treating as dead.
- Root-input filtering upstream of `gp-0x6ac0`/`gp-0x4f62` feeding the two inline friction terms.
- The `0xC63D2` = 6 vs 14 discrepancy (see addendum in [[reference_accord_c646c_gain_feedback_vs_forward_classification]]).

## Related
[[reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole]] — established the peak-hold
character of `gp-0x6b86` and the 0xC6450/0xC644A unity-gain facts this file reuses; this file adds the
aggregator-level bound (±12288, confirmed largest lane) and the adaptive-α attenuation-at-20Hz number.
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — the `FUN_00036682` chain this file's
`0x6b46` row summarizes; see its addendum for the 6-vs-14 discrepancy.
[[reference_accord_gp67ac_aggregator_lane_suppression_gate]] — the gate that decides whether 5 of these 9
lanes are even reachable; still the top open item for this whole inventory.
