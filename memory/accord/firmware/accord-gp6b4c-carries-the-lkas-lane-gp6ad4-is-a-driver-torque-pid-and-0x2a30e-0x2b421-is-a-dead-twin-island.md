---
name: accord-gp6b4c-carries-the-lkas-lane-gp6ad4-is-a-driver-torque-pid-and-0x2a30e-0x2b421-is-a-dead-twin-island
description: "🛑⭐⭐⭐⭐⭐ ADJUDICATED 2026-09-13 (GhidraMCP, analysis SAVED): the LKAS lane reaches the aggregator as gp-0x6b4c (unit weight) via T @0x2A23C → gated copy @0x2A2EA → gp-0x6b3c → FUN_0002b422 clamp ±0xC61B2 → ep-relative request array → FUN_00026c80 → gp-0x6b4c; gp-0x6ad4 is a DRIVER-TORQUE tracking PID (err = bar − ref) that LKAS only perturbs indirectly. 0x2A508–0x2B421 was undefined and is an UNCALLED TWIN of the LKAS output path (6 functions, 0 callers, 3 odd-target false hits rejected) — the 0x2B41C 'forward' the record cites is DEAD; 0xC646C has 5 LIVE readers, 0xC61B4 4."
metadata:
  node_type: memory
  type: reference
---

Agent `ghidrafill`, 2026-09-13, `docs/traces/TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`.
Functions 2086 → 2090 (FUN_0002a508 906 B, FUN_0002a892 168 B, FUN_0002b070 746 B, FUN_0002b35a 200 B;
FUN_0002a93a pre-existing) tile the 3,866-byte hole exactly; ZERO bytes remain undefined; `save_program` done.

- **Which memory is wrong:** the tracer store's new file (2026-09-13) was wrong to favour gp-0x6ad4 — it
  scanned FUN_00026c80 for LKAS cell NAMES, but LKAS enters `ep`-relative (`movea -0x62f8,gp,ep` + `sst.h`),
  the false-zero class the store's own `reference_accord_two_lkas_routes_gp6b4c_bypasses_auth` documents.
  `reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain` is RIGHT ("gp-0x6b4c is the only LKAS
  summand"; its "resonance, eliminated V56" label for gp-0x6ad4 is stale). `reference_accord_aggregator_
  11term_loop_census_units_and_fork` is right in its math (§7 derives the torque-tracking error) and only
  its "PID P+I+D" shorthand invites the LKAS reading — add the word "driver-torque". (Neither file edited;
  ask-first convention.)
- **The live path, instruction-anchored:** 0x2A1EE `ld.h 0x746c[tp]` (gain; V282 repoints the operand to
  0xC6CD0 @0x2A1F0) · 0x2A23C `st.h r1,-0x6b38[gp]` T · 0x2A2C2 `cmove 0x0,r1,r16` gate · **0x2A2EA `st.h
  r16,-0x6b3c[gp]`** · 0x2B42E ld → clamp ±[0xC61B2] → 0x2B45C gp-0x6b3a (telemetry mirror) · 0x2B52C `sst.h
  r12,0x4[ep]` (0x2B52A writes a literal 0 to field +2 ⇒ term 0 gp-0x6b4a gets nothing) · jarl 0x25C32 →
  gp-0x62f8[1] (slot 1 = MODE 0 per 0xC4124) → gp-0x62b0[1] → 0x2730C sum gp-0x3d88 → **0x276F0 `st.h
  r8,-0x6b4c[gp]`** (clamp ±0x2800) → 0x3AA3E aggregator, unit weight. Second, indirect route: 0x3816C
  → gp-0x6b70 → gp-0x6ad6 (the torque-PID reference) → gp-0x6ad4 → 0x3ACA8 (magnitude unquantified).
- **Census deltas after analysis (all new sites in the dead island, hence inert):** gp-0x6b38 3 → 5,
  gp-0x6b3c 2 → 3, 0xC646C 5 → 6 (the 0x2A904 site the `firmware-decompile` skill records as missed —
  real, and dead), 0xC61B4 4 → 8. Unchanged: gp-0x6b3a, gp-0x6b94, gp-0x6ad4, gp-0x6b4c, gp-0x6ada,
  tp+0x73E8/EA/7446. 0xC6CD0 reads 0 on STOCK correctly (the repoint exists only on V57+ images).
- **Method note:** reject any Format-V `jr`/`jarl` hit whose target is ODD (the `prepare` alias) — that one
  filter killed all three false callers of the island. "Uncalled" is EVIDENCE for direct calls and address
  constants; "dead" is BELIEF (register-indirect dispatch not excluded; the 32-bit-pointer scan's positive
  control failed for every known entry).

Related: [[accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz]] ·
[[accord-gp6b38-is-the-delivered-lane-torque-and-forwards-to-gp6b3c]] (the forward site it names, 0x2B41C, is
the dead twin — the live one is 0x2A2EA)
