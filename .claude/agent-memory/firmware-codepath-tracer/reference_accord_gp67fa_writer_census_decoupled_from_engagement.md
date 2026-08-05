---
name: reference_accord_gp67fa_writer_census_decoupled_from_engagement
description: "Full 33-writer census of gp-0x67fa (the ECU one-hot state, 0x830/0x930/0xc30 mask gate for return-centre/detector/arbitration/aggregator). All 10 sub-handler functions decompiled fresh 2026-08-04. Every guard condition traces to gp-0x6d78 bit tests (FUN_000197d0(N) = (gp-0x6d78>>N)&1, confirmed by decompile), a UDS/diagnostic force-state byte pair (tp+0x74f9==0xAA / tp+0x74d0), gp-0x4378/0x437c/0x3eec (UDS-session-adjacent), gp-0x68ad (dead), FUN_00046ea6(0)/(2) fault bits, and ONE branch testing gp-0x6b98==0 (delivered torque itself). NONE reference gp-0x67fe, gp-0x6806, gp-0x69ae, gp-0x1426, or any other CAN/LKAS-command-domain signal. Decisively answers team-lead's open question: gp-0x67fa does NOT change as a function of LKAS engagement."
metadata:
  type: reference
---

# gp-0x67fa: exhaustive 33-writer census, decoupled from LKAS engagement — 2026-08-04

Dispatched for team-lead's "does gp-0x67fa change value as a function of LKAS engagement?" question
(itself the item [[accord-gp67fa-state-gate-on-assist-chain]] flagged as "never directly established").
Builds on that memory (the 0x830/0x930/0xc30 mask discovery) and
[[accord-state4-cadence-refuted-state-is-sticky]] (gp-0x68ad dead, gp-0x6d78 bit15 one-way).

## Method [EVIDENCE]
`search_instructions(mnemonic="st.b", operand_pattern="67fa")` on stock `code.bin`: **33 hits, 0
truncated**, matching the prior memory's count exactly (no undercount). All but one (`0x57e94` in
`FUN_00057e5e`, a boot/init routine unconditionally setting state=1) sit in a 10-function dispatcher
family at `0x197ea-0x1a0ba`, headed by the true dispatcher `FUN_00019f7c` (confirmed: reads
`bVar7=gp-0x67fa`, `if(bVar7<6){if(bVar7==1)FUN_000197ea();...}` etc — a literal state->handler jump
table). All 10 sub-handlers (`FUN_000197ea/00019888/00019970/00019b10/00019bd0/00019cfa/00019d90/
00019e7c/00019f00`, plus the dispatcher itself) freshly decompiled via `batch_decompile`/
`decompile_function`.

## The guard-condition inventory, exhaustive over all 33 writes [EVIDENCE]

Every one of the ~20 distinct transition conditions across the 10 handlers reduces to:
1. **`tp+0x74f9 == 0xAA` (diagnostic/test-mode enable byte) + `tp+0x74d0` (forced-state selector,
   values 3/4/5/6/7/8/9/10/11)** — a UDS/RoutineControl-style test-mode override path, gated on a cal
   byte, not a runtime signal.
2. **`FUN_000197d0(N)` for N in {0,4,5,7,8,0xf,0x10}** — CONFIRMED by fresh decompile to be
   `return (gp-0x6d78 >> (N&0x1f)) & 1`, i.e. a single-bit test on **gp-0x6d78**, the SAME 32-bit
   fault/status word already established ([[accord-state4-cadence-refuted-state-is-sticky]]) as the
   one-way OR-only latch whose bit15 drives 4->10 and whose own writer (`FUN_000197b8`, 21 callers) is
   untraced.
3. **Direct `gp-0x6d78 & {0x5080, 0x5000, 0x2a10, 0x80000}` mask tests** — same word, different bit
   groups, same domain as #2.
4. **`gp-0x4378==1 && gp-0x3eec!=0`** (UDS-session-adjacent, per existing memory `gp-0x437c` is a UDS
   artifact; `gp-0x4378` is its neighbor, same family) and **`gp-0x68ad==1`** (state-5 entry — CONFIRMED
   dead per prior memory, this cell can never be 1 in the field).
5. **`FUN_00046ea6(0)` / `FUN_00046ea6(2)`** — fault-bit accessor (same family as the detector's
   `FUN_00046ea6(5)`/`(13)` gates elsewhere in the kit), used only in the dispatcher's own
   promotion-to-state-8 OR-gate.
6. **ONE torque-domain condition**: the dispatcher's promotion-to-state-8 OR-gate includes
   `(*(short *)(gp-0x6b98) == 0 && FUN_00046ea6(2) != 0)` — **`gp-0x6b98` IS the final aggregated motor
   command** (established elsewhere across this kit as the FOC-bound output). This is a DOWNSTREAM
   torque-idle check ("motor commanding exactly zero AND a fault bit set"), not an UPSTREAM
   engagement/CAN signal.
7. A single unrelated dwell-timeout: `FUN_00019f00`'s `(gp-0x3e54 - gp-0x3ee4) > 60000` (u16 wrap), a
   free-running-counter watchdog, state 6->7.

**`gp-0x67fe` (LKAS engage-SM state), `gp-0x6806` (deadband/latActive-proxy FSM), `gp-0x69ae` (raw CAN
torque setpoint), and `gp-0x1426` (the engage-request byte) appear in ZERO of the ~20 guard conditions
across all 10 functions.** Checked by reading every decompiled body in full, not by an xref null.

## Verdict [EVIDENCE]

**`gp-0x67fa` is a fault/diagnostic/power-mode state machine, structurally decoupled from LKAS
engagement.** Its entire transition graph is driven by `gp-0x6d78`'s fault/status bits, a UDS test-mode
byte pair, and (once) whether the motor is currently commanding idle torque with a fault flag raised —
never by whether openpilot is sending `STEER_TORQUE_REQUEST`. This closes the question
[[accord-gp67fa-state-gate-on-assist-chain]] left open and REMOVES `gp-0x67fa`/state-4 as a candidate
(c)-class ("state change caused by engagement") mechanism for any engagement-required symptom — the
0x830/0x930/0xc30 masks gate the assist chain on ECU HEALTH/MODE, not on LKAS presence, so whatever state
the ECU is in (state 4 or 11 on a normal healthy drive), it is in that state identically whether
openpilot is engaged or the driver is steering manually.

## Related
[[accord-gp67fa-state-gate-on-assist-chain]] — the mask discovery this census closes the open item on.
[[accord-state4-cadence-refuted-state-is-sticky]] — gp-0x6d78 bit15/gp-0x68ad backstory this reuses.
[[reference_accord_0x930_masks_are_state_not_phase_settled]] — the one-hot mask mechanism itself.
