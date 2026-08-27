---
name: reference-accord-v50-gp4f60-repoint-asymmetry-carryover-and-completeness-gap
description: Adversarial pre-flash review for V50 (EMA low-pass, same gp-0x4f60->gp-0x1500 hook/repoint topology as V48B) — the prior V48B monitor-asymmetry review carries over cleanly (topology-only, filter-shape-agnostic), but a fresh full-image re-scan found 3 gp-0x4f60 readers (FUN_0002ec52, FUN_0002eda8, FUN_00055f2e) never classified by either prior session. One (FUN_00055f2e) closed clean this session as a 3rd CAN-TX packer; two remain UNRESOLVED, most notably FUN_0002eda8 which runs in the same confirmed ~1kHz task as the 7 filtered carriers.
metadata:
  type: reference
---

# V50 gp-0x4f60 repoint asymmetry review + completeness gap (2026-07-23)

Adversarial pre-flash review requested by team-lead for V50 (`builds/v50_v79/build_v50_tva.py` — EMA low-pass on
`gp-0x4f60`, code cave). V50 uses the **identical hook point (`0x7FEAC`) and identical 7-site/2-dormant
repoint set** as V48B (the notch) — confirmed by re-reading `memory/reference/builds/reference-accord-v50-lowpass-ema-cave.md`
("Gate-1 reconfirmed sites" = the same 7 addresses byte-for-byte) — so the prior V48B adversarial review
([[reference-accord-v48b-repoint-asymmetry-review]] + [[reference-accord-v48b-monitor1-dtc1c-notch-safety-closed]],
previously misfiled at `analysis-2020accord/.claude/agent-memory/...`, relocated here this session) is
directly reusable: it is a TOPOLOGY analysis (who reads raw vs filtered `gp-0x4f60`, does any comparator
span both) which does not depend on what filter sits in the shared cell.

## Fresh re-verification this session (program: `code.bin`, stock, 2148 functions, fully analyzed)

- `search_instructions(operand_pattern="4f60")`: **74 matches, 186,069 instructions scanned,
  truncated:false** — exact reproduction (same count, same address list) of the two prior 2026-07-21
  sessions. Three-way cross-session reproduction on the same fully-analyzed image.
- `read_memory` spot checks at the 7 repoint addresses, the 2 dormant addresses, and both monitor
  addresses all show unmodified stock bytes `24 <reg> A0 B0` = `ld.h -0x4f60[gp],rX`. Byte-for-byte
  matches search_instructions' own decode at every address checked.
- `read_memory(0xC6498,4)` = `01 01 00 00` — **3rd independent confirmation** that both dormant-mux gate
  bytes (`0xC6498`/`0xC6499`) are `0x01` in stock, i.e. `FUN_00034350`@0x34392 / `FUN_00034a72`@0x34ace's
  own raw reads are genuinely bypassed by the mode==1 branch (feeding the filtered
  `gp-0x6ba6`/`gp-0x6b9a` from `FUN_0003b66a` instead). Leaving these 2 raw remains correct.
- `get_xrefs_to(0xFEDF30A0)` = "No references found" — reconfirms the documented gp-relative xref-engine
  false-zero is still present; not relied on as the sole method anywhere in this review.
- A `search_byte_patterns` attempt at a raw 4-byte template scan (`2400a0b0`/mask `ff00ffff`) returned "No
  matches" — a tooling/mask-syntax issue on my part, NOT a real null (contradicted by the read_memory spot
  checks at the same addresses). Not used as evidence; flagged so a future session doesn't repeat it as if
  it were informative.

## Carried-over verdict (V48B's, re-applied to V50): no V27-class asymmetry found

Full detail in the two linked files. Summary:
- Shadow-lockstep (`gp-0x4f60` vs shadow `gp-0x4486`, fault idx 0x17): untouched — hook is strictly
  downstream of the producer's settled shadow-pair store, never writes `gp-0x4f60`/`gp-0x4486`.
- Type-8 lockstep `FUN_00027b0a`: matched — both sides trace to the SAME single filtered read
  (`FUN_0002c478`→`gp-0x6b12`→`FUN_0002caa2`→`FUN_00025c32`).
- `FUN_000352b4`'s internal shadow-pair check, `FUN_0003a382`/`FUN_00037fe6` chain: 0 raw reads at any
  intermediate stage — clean.
- `FUN_0003b66a`→damper/boost Factor-A mux: only raw-vs-filtered split candidate is the dormant fallback,
  proven cal-disabled (see above).
- The two hard-shutdown monitors `FUN_00042af8`(DTC 0x1c)/`FUN_00043e44`(DTC 0x1d): both read raw
  `gp-0x4f60` directly, NOT among the 7 repointed sites — raw-vs-raw, not raw-vs-filtered. DTC-0x1c's
  terminal trip is a matched int/float shadow-computation of the SAME `gp-0x6b4a`-derived wall (±5-count
  tolerance) — filter-shape-agnostic argument: attenuating (no passband peaking) can only shrink the
  per-tick delta this tolerance absorbs, never grow it. Holds at least as strongly for V50's monotonic
  first-order EMA as for V48B's verified-non-peaking biquad.
- One item stays OPEN from the original review (not re-closed this session): `FUN_00042af8`'s OTHER raw
  term `gp-0x6af8` (raw-only, no filtered sibling) feeds a 7-site debounce/hysteresis state machine whose
  terminal threshold-crossing compare was never traced to completion — low risk (regime-selector, not a
  bit-exact trip) but not closed.

## NEW FINDING — completeness gap: 3 gp-0x4f60 readers never classified by either prior session

Diffing this session's fresh 74-hit function list against both prior sessions' named function lists
(V48B notch-feasibility + V48B reader-closure) turned up **3 functions neither prior pass ever named**:
`FUN_0002ec52` (2 hits, `0x2ec66`/`0x2ecba`), `FUN_0002eda8` (3 hits, `0x2f318`/`0x2f330`/`0x2f33e`),
`FUN_00055f2e` (1 hit, `0x55f3e`). Also excluded 1 false positive from the raw hit list:
`FUN_00064438`@`0x64f42`, `bne 0x00064f60` — a branch-target address that textually contains "4f60", not
a `gp`-relative access (mnemonic `bne`, no `gp` operand).

### FUN_00055f2e — CLOSED this session, Y (safe, CAN-TX packer, same class as 2 already-cleared broadcasts)
`get_function_callers` falsely reports "No callers found" — **the SAME misleading-zero tool trap already
on record for `FUN_0004d8f0`/`FUN_0004de0c`** (register-indirect/table-dispatched functions; this is now
a 3rd independent instance of that specific trap on this kit). Corroborated via `get_xrefs_to(0x55f2e)` →
a DATA xref from `0xB72CC`; `read_memory(0xB72CC,16)` decodes as 3 consecutive little-endian function
pointers: `0x00055F2E`, `0x00055C42` (**the confirmed CAN 399 `STEER_TORQUE_SENSOR` packer**),
`0x00055A98` (**the confirmed V31P CAN-330-piggyback packer**) — i.e. `0xB72CC` is a CAN-TX packer
dispatch table and `FUN_00055f2e` sits in it beside two already-classified CAN broadcasters. Its own
decompile: `raw*10>>9` scale, negate, clamp ±127 via the known generic clamp helper `FUN_00049a90`, pack
into a byte with critical-section wrappers (`FUN_0001fa42`/`FUN_0001fa72`) — a 3rd CAN-TX signal packer,
no comparator, no fault-dispatch call anywhere in the function. **Y, safe, matches precedent exactly.**

### FUN_0002ec52 — UNRESOLVED
Called by `FUN_00022ca0` (the ~100 Hz assist-shaping task — same family as the already-flagged
`FUN_0002b62c`/`FUN_0002db94`/`FUN_00033d10` blockers from the prior reader-closure session). Decompile:
raw-torque finite difference (own local `gp-0x3c64` prior-sample cell, separate from the `gp-0x4f62`
producer) → Q16-scaled rate written to `gp-0x6e00`, a magnitude peak-hold to `gp-0x6e04`, a per-channel
gain factor to `gp-0x6c8c`, a lookback short to `gp-0x6a4a`. No fault-dispatch call visible in the
function body. Downstream consumers of these 4 outputs were **not traced this session**.

### FUN_0002eda8 — UNRESOLVED, highest-priority gap found this session
Called by **`FUN_0002214a` — the SAME confirmed ~1 kHz control task as the producer, both hard-shutdown
monitors, and all 7 repointed carriers** (see [[control-task-tick-confirmed-1khz]]). Large (~200-line
decompiled) angle/position-domain state machine. Reads raw `gp-0x4f60` twice near its tail and combines
it against a stored angle-domain state variable (`gp-0x3c2a`/`gp-0x3c48`, sourced from a SEPARATE
per-channel angle table, not from `gp-0x4f60`) in a scaled-difference computation; the result runs through
a sign-compare debounce/peak-hold idiom (the same idiom seen throughout this firmware's hysteresis logic),
then a CORDIC/atan-style fixed-point polynomial (same constant family — `0x3243f7`,`0x1921fb`,`0x6487ed`
etc. — as the confirmed torque-sensor CORDIC in `FUN_0006af38`, see
[[reference_accord_torque_sensor_zero_and_assist_bias_mechanism]]). Final stores:
`gp-0x6b6c` and `gp-0x69fa`. **No `FUN_0006b9ee`/`FUN_0004613e`/`FUN_00016de6`/`FUN_0006ce7c` fault-dispatch
call is visible anywhere in this function** — evidence AGAINST it being a monitor, not proof. Downstream
consumers of `gp-0x6b6c`/`gp-0x69fa` were **not traced this session** — cannot rule out either feeding a
comparator whose other input derives from a now-filtered carrier.

## Overall verdict

No V27-class raw-vs-filtered comparator asymmetry found among the 7 repointed lanes or their traced
downstream consumers, including both hard-shutdown monitors — corroborated across 3 independent sessions
now landing on identical byte-level facts. The 2 dormant reads are confirmed cal-gated-off (3rd
independent byte confirmation). **This is a conditional-SAFE verdict, not a full closure**: 2 readers
(`FUN_0002ec52`, `FUN_0002eda8`) found this session were never classified before and were not traced to
their consumers. `FUN_0002eda8` in particular runs in the exact same hot 1 kHz task as everything else in
this review and deserves the same scrutiny the confirmed carriers got before this is called fully closed.

## Related
[[reference-accord-v48b-repoint-asymmetry-review]], [[reference-accord-v48b-monitor1-dtc1c-notch-safety-closed]]
— the carried-over base review.
[[reference_accord_gp4f60_notch_filter_feasibility_v48b]], [[reference_accord_gp4f60_v48b_reader_closure_and_mode_gated_bypass]]
— the two prior full-classification sessions this one diffed against to find the 3 new readers.
[[control-task-tick-confirmed-1khz]] — rate confirmation for FUN_0002eda8's task membership.
