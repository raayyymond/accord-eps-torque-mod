---
name: reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive
description: FUN_00036388 (return-centre, gp-0x6b62) fully traced at instruction level for the 7.5 Hz ratchet hunt -- not a self-oscillating source by its own arithmetic; V69's bit5 already probed it on-car but was underpowered, not falsified.
metadata:
  type: reference
---

**Session: 2026-08-04, ratchet-trace teammate, task "trace the 7.5 Hz ratchet loop inside the EPS."**

## FUN_00036388 (0x36388-0x365ce) fully traced [EVIDENCE, decompile + disassembly, code.bin stock]

Writes `gp-0x6b62` (return-to-centre lane, one of the aggregator's 8 ZERO-type range-gated lanes,
`+/-0x2000`). Called only from `FUN_0002214a` (task 1, 1 kHz), state-gated on mask `0x830` = states
`{4,5,11}` -- **same mask as the oscillation detector `FUN_000428d4`, and excludes state 10** (confirmed
against `docs/STATE.md` section 6's table, exact match, no new finding there).

**Two internal counters, both bounded and asymmetric -- NEITHER is a free-running relaxation
oscillator on its own arithmetic:**

1. `gp-0x6a82` (0x36432-0x36472): `+1/tick` if `abs(gp-0x6b64) < CAL_718A` (`tp+0x718a` = `0xC618A`,
   read = **1024**) unless already `> CAL_727E` (`tp+0x727e` = `0xC627E`, read = **20**, the ceiling);
   `-1/tick` otherwise, floored at 0. Full 0->20 sweep = 20 ticks = 20 ms; a bounce would give ~25-50 Hz,
   not 7.5 Hz, and it only bounces if `gp-0x6b64` itself crosses 1024 periodically -- it does not create
   that crossing.
2. `gp-0x6990` (0x363e8-0x3641c): steps by `+/-CAL_73C0` (`tp+0x73c0` = `0xC63C0`, read = **33**) per
   tick, clamped `[0, 0x7fff]`, gated on whether `gp-0x6bda` (the driver-torque peak-hold margin) rose
   since last tick (compared against its own 1-tick-delayed shadow `gp-0x37b0`) AND `CAL_7132`
   (`tp+0x7132` = `0xC6132`, read = **1**, nonzero so this gate passes). Full-scale sweep is ~993 ticks
   (~1 s) -- far too slow for 7.5 Hz unless only a small fraction of its range is exercised each
   half-cycle, which is undetermined without live RAM.

`gp-0x6b64`'s sole writer is `FUN_000360fe` (0x360fe-0x361be) [EVIDENCE, `search_instructions`
`-0x6b64` = exactly 2 hits image-wide, one write one read, cross-checked against the known undercount
trap]: a 5-point LERP over `gp-0x6bda` (table `tp+0x795e..0x7970`) multiplied by `gp-0x6abc` (>>10,
Q10) then by `CAL_73BE` (`tp+0x73be` = `0xC63BE`, read = **1024 = Q10 unity**), negated, clamped
`+/-0x2800`. `gp-0x6abc`'s only writers are inside `FUN_00041464` (the already-memoried "sign-filter
phase" function, `fs_eff` 312.5 Hz) -- part of the same motor/resolver-rate-derivative chain as
`gp-0x6abe`/`gp-0x6ac0` (the "common-mode rate bus", net -40.4 deg phase vs velocity per existing
memory). **`gp-0x6b64` therefore has NO direct vehicle-speed or torque-sensor term** -- confirmed
independently by `docs/STATE.md` line ~1969: *"`FUN_00036388` (`gp-0x6b62`) read[s] no torque signal at
all -- speed- and motor-rate-keyed only"* (this session's own trace and that pre-existing note agree,
two independent methods).

**Conclusion:** `FUN_00036388`'s own counters cannot be shown to generate a 7.5 Hz (133 ms) period from
their own step sizes/bounds -- the candidate period computed directly (20-40 ms or ~1 s) does not match.
Its gate variable `gp-0x6b64` is a PRODUCT of a torque-margin LERP and a motor-rate derivative, so if
either upstream signal already carries 7.5 Hz content, `FUN_00036388` would inherit/shape it (as a
nonlinear follower with hysteresis and ZERO-gating -- exactly the kind of hard nonlinearity a
describing-function argument implicates) rather than create it from nothing. **Open, not ruled out.**

## V69's bit5 ALREADY probed gp-0x6b62 on-car -- inconclusive, not falsified [EVIDENCE, build script + flight handoff]

`analysis-2020accord/build_v69_tva.py` (~line 198-411) built a CAN 0x14A telemetry cave with
`bit5 = gp-0x6b62 >= +4096`, explicitly labelled *"the operator's own hypothesis, never probed in 69
builds."* Flown on route `4f` (`docs/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md` section 5.2).
Result: **"bit5 was insensitive, not vacuous"** -- `gp-0x6b62`'s reachable max is 5786
(`|gp-0x6b5e| <= 4762` from trapezoid `0xC66CC`, plus a latched `|sVar8| <= 1024`), so the 4096 threshold
sat at 71% of full range, seeing only the top 29%. **The record does NOT report an explicit observed
hit-rate/count for bit5** (unlike bit6, which got an explicit "observed 0, p=0.37"). The section header
is "ALL THREE RUNGS FAILED", implying bit5 also produced no usable signal, but this is inferred, not
quoted verbatim -- **the actual bit5 time series from route 4f's decoded probe has not been surfaced in
the written record I found.** Re-decoding `rlog-tools/decode_v69_ratchet.py`'s route-4f output for
bit5's raw 0/1 series (not just a summary stat) would settle whether `gp-0x6b62` ever fired at all, which
is the single fastest way to move this candidate from OPEN to CONFIRMED or KILLED.

## Other gp-0x6806 consumers enumerated and ruled out [EVIDENCE, decompile of each]

19 access sites total (`search_instructions -0x6806`, cross-checked against the known undercount trap --
count not independently byte-scanned this session, flag if load-bearing later). 8 writers all inside
`FUN_00028ea6` (arbitration, the flag's producer). External readers, all checked:
- `FUN_0002eda8` -- already CLOSED per existing memory (lane-9 raw torque command path).
- `FUN_0002fab6` -- a huge steering-angle/yaw plausibility MONITOR with parallel 1000 ms-tick debounce
  state machines timing out at 11000 ms (11 s). Reads `gp-0x6806` once, to detect an engagement
  transition edge and reset rolling history buffers. Debounce timescale (1-11 s) is two orders of
  magnitude too slow for 7.5 Hz. RULED OUT.
- `FUN_00030c26` -- a large vehicle-dynamics/wheel estimator, called only from `FUN_0002351e` = **task 6,
  10 Hz** (per the golden model's rate table). Nyquist for a 10 Hz task is 5 Hz; it structurally CANNOT
  carry a clean 7.5 Hz component. RULED OUT by task rate alone.
- `FUN_00042746` -- sensor-fault failover reselector (per existing model comment); static reselection,
  not periodic. RULED OUT.
- `FUN_0004fbde` -- a freeze-frame/diagnostic snapshot logger (16-entry circular buffers), event-driven
  on a multi-flag AND-gate, not a periodic timer. RULED OUT.
- `FUN_00055c42` -- pure CAN 399 TX bit-packer (packs `gp-0x6806` into byte4 bit3, per the existing
  `can_tx_399_427_bitmap` memory); no dynamics. RULED OUT.

## FUN_00045608 (authority-slot setter) is NOT itself dynamic [EVIDENCE, decompile + 16 callers]

Trivial: `if (slot&0xff) < 7: write 3 params into 3 parallel 7-slot arrays at gp-0x652c/-0x64fc/-0x6514`.
No timer, no accumulator. 16 callers spanning many unrelated state-machine handlers (including the
oscillation detector `FUN_000428d4` itself as one caller) -- a shared generic utility, not a dedicated
"authority ramp." RULED OUT as a standalone oscillator source; the real ramp/period logic (if any) lives
in whichever caller drives repeated re-arming, not traced this session.

See [[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] for the motor-rate-derivative
chain `gp-0x6b64` draws on, and [[reference_accord_r26_is_structurally_inert]] for `gp-0x6b5e`'s
trapezoid (the same LERP `gp-0x6b62`'s ceiling is built from).
