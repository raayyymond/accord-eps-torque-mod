---
name: reference_accord_pump_hunt_comparator_probe_candidates
description: "Concrete, GATE-1-clean candidate RAM cells for a future comparator probe to settle the 6-9Hz anti-damping pump's identity in the real closed loop (D-term vs r24/r26), instead of trusting isolated-stage phase arithmetic (which failed by ~227 degrees for gp-0x6b26). Also re-confirms r24/r26 have NO editable phase structure -- the lane is closed as a LEVER but NOT exonerated as a physical SOURCE."
metadata:
  type: reference
---

# Comparator probe candidates for the 6-9Hz pump hunt, and r24/r26's phase-lever closure

Traced 2026-08-20, task `damphunt round 3`. Companion to
[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]] (the D-term Re(Z) evidence status).

## Why a comparator, not a guessed filter

Per the kit's own design law and the `gp-0x6b26` precedent (isolated-stage phase wrong by ~227° once
measured closed-loop — [[reference_accord_gp6b26_closed_both_directions_v94_aborted]]), neither D nor
r24/r26's real sign relative to velocity can be trusted from code-domain reasoning alone. The following
cells are all already GATE-1-clean (fresh `search_instructions`, 183,569 instructions scanned,
program=`code.bin`, whole-image scope) and would let a cave settle "pumping or damping, right now" by
direct sign comparison against a velocity reference, without inventing new phase arithmetic.

| cell | holds | census [EVIDENCE, this session] | notes |
|---|---|---|---|
| `gp-0x3680` | D_state (D's own EMA-smoothed contribution) | **1R/1W**, both inside `FUN_0003a382`: read `0x3a85c` (`ld.w`), write `0x3a87a` (`st.w`). Zero other consumers image-wide. | Raw `search_instructions("3680")` returns 6 hits; the other 4 are `movhi -0x3680,r0,rX` (32-bit immediate construction, unrelated) and one coincidental literal `mov 0x3b53680d,r8` — all excluded by disassembly, not assumed. |
| `gp-0x3684` | ERR_prev (PID's own error history) | **1R/1W**, `0x3a832`/`0x3a840`, both inside `FUN_0003a382`. Zero other consumers. | Raw hits at `0x36838`/`0x53674` are `bgt`/`bne` branch-target coincidences, excluded. |
| `gp-0x6ada` | r24, post-±0x2000-clamp | **0R/1W**, write only, `0x3ad5a` (`st.h r24,-0x6ada,gp`), inside `FUN_0003aa2c`. Re-confirms [[accord-aggregator-lane-mirrors-6ada-6adc]] (repo `memory/`) unchanged. | 5 other raw hits are branch-target coincidences inside unrelated `FUN_0006ac1a`, excluded. 🛑 That memory's own trap: `ld.h` vs `st.h` differ by one opcode bit — a probe MUST assert the opcode byte-exact, not just the displacement. |
| `gp-0x6adc` | r26, post-±0x2000-clamp | 0R/1W pattern established in the same source memory (not re-verified fresh this pass — do so before building). | |
| `gp-0x6806` | engagement flag (`latActive`, 99.983% agreement per prior record) | plain `ld.bu -0x6806,gp,rX`, 4 bytes, trivially reachable from ANY hook site (gp-addressing is uniform on V850, not locality-dependent). | Confirmed via 21-hit whole-image census; none of the 21 real hits are near `FUN_0003a382`/`FUN_0002214a`, but that's irrelevant to reachability — a NEW read is a single instruction regardless of hook location. |
| `gp-0x6c2c` | filtered EPS-motor rate first difference (used by `gp-0x6b26`/`0xCBE74`'s own velocity reference) | pre-established, see [[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]] lineage | natural common velocity reference for BOTH a D-term comparator and an r24/r26 comparator, so one probe design serves both suspects. |

**Design sketch (NOT sized, NOT a build proposal — a next-step spec)**: read `sign(gp-0x3680)` (or
`sign(gp-0x6ada)`/`sign(gp-0x6adc)`) and `sign(gp-0x6c2c)` at the hook, XOR/compare, accumulate a duty
cycle per engaged episode, optionally gated on `gp-0x6806` for engaged-only attribution. Zero blast
radius: every read is of a cell nothing else in the image consumes (mirrors) or that already has an
established, unperturbed 1R/1W pair (D_state/ERR_prev — a NEW external read does not touch the existing
read/write, GATE-1 for a read-only tap is categorically weaker than for a write).

## r24/r26 — CLOSED as an editable phase lever, NOT exonerated as a physical source

Re-confirmed this session against [[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]]
(2026-08-09, 3-way corroborated) — unchanged, still current. **r24 has zero state cells anywhere in its
path** (a memoryless per-tick LERP, no history). **r26 has exactly one averaging structure, a hardcoded
2-tap boxcar on the GAIN SCHEDULE `gp-0x69a4`, not the differentiated signal** — `|H(7.79Hz)|=0.9997`,
first null at 500Hz, not cal-adjustable. **Both lanes multiply the SAME shared upstream 4-tap
difference `gp-0x4f62`** (cal `0xC6C42`=4); its phase `90 - 180·N·f/fs` declines slowly and does not
cross zero until f=125Hz — **there is no break frequency near 20-26Hz to find, because there is no
phase-shaping element on r24 or r26's own path.** A brief asking to "check whether the break frequency
sits near the measured 24-26Hz sign flip" cannot be answered as posed — the premise (a break frequency
exists to check) is false, verified structurally, not just unmeasured.

**This closes r24/r26 as something you can cheaply RE-TUNE for phase. It does NOT close r24/r26 as the
PHYSICAL SOURCE of the anti-damping** — the lane is structurally exactly the carrier class
`analysis-2020accord/studies/models/eps_loop_gain_model.py`'s own docstring names as the textbook destabilizing shape
("dominant carriers are RATE (command/torque-derivative) feedbacks... through a resonance at its -90°
peak => L ~ real positive => direct anti-damping"), unfiltered, entering the same aggregator
(`gp-0x6b98`) the D-term does. Nobody has measured its real closed-loop phase relative to velocity.
**Adding a phase-shaping element to it (if a future session wants to actually change it) requires a
brand-new cave-inserted filter — new GATE-1 RAM state, new GATE-2 closed-loop review — not a cal edit;
budget it as a new lever proposal, not a quick fix.**

## Related
[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]] — the D-term evidence status this
probe design answers to. [[accord-aggregator-lane-mirrors-6ada-6adc]] (repo `memory/`) — original
r24/r26 mirror discovery, re-confirmed here. [[reference_accord_gp6b26_closed_both_directions_v94_aborted]]
— why a comparator beats isolated-stage phase arithmetic on this specific car.
