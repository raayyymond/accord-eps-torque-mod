---
name: reference_accord_c6384_slopecap_role_confirmed_binding_unresolved
description: "0xC6384's role as the gp-0x6b86 assist-map's per-segment slope ceiling is CONFIRMED a third independent time (fresh decompile of FUN_000352b4 this session, float arithmetic: fVar38=cal(0xC6384)/1024, compared against the natural ΔY/ΔX slope, X pushed outward on exceedance). GATE 1 closed: exactly 2 readers (0x353ac/0x353c2, both inside FUN_000352b4), 0 writers, byte-verified virgin stock/V108/V109; 16 raw-scan extras adjudicated (5 spot-checked) as the known sst.b EP-relative-short-form false-positive class. Not LKAS-gated (dispatcher mask 0x830, same finding as the sibling Kd memory). BUT whether the cap is CURRENTLY BINDING anywhere is UNRESOLVED from a static image -- it depends on live, history-dependent Branch-B slew state the prior trace (TRACE-2026-08-21) already flagged as needing a full pipeline simulation nobody has done. Structural GATE-2 argument (robust regardless of the binding question): this term is MEMORYLESS -- flat magnitude, 0 deg phase, IDENTICAL at every frequency DC to Nyquist -- unlike Kd's high-pass-shaped, DC-free contribution, making it a strictly blunter, less frequency-selective instrument if it is live at all."
metadata:
  type: reference
---

# `0xC6384` (assist-map slope cap) — role re-confirmed, GATE 1 closed, binding UNRESOLVED — task `ratchlever`, 2026-08-27

Briefed by team-lead/`main`: candidate 2, "named today as the largest single L lever... 7.8x the entire
PID... value byte-verified, ROLE is tracer-reported and is BELIEF — establish the role yourself before
pricing." Program: stock `code.bin`. Fresh `decompile_function` + `disassemble_function` on `0x352b4`
this session (full function, ~450 lines/instructions) — my OWN independent read, not inherited; matches
`[[reference_accord_aggregator_11term_loop_census_units_and_fork]]`'s §2 and the prior subagent trace
`docs/traces/TRACE-2026-08-21-assist-map-rom-source.md` §1 exactly, now a THIRD confirmation.

## 1. Role, re-derived from a fresh decompile [EVIDENCE — upgraded from BELIEF]

`FUN_000352b4` runs a 9-iteration piecewise-table-construction loop EVERY 1kHz tick it is called
(dispatcher gating, §4 below), rebuilding `gp-0x37fc[]`(X)/`gp-0x37e8[]`(Y) from raw seed/target inputs,
THEN evaluates the just-built table against the current clamped input to produce `gp-0x6b86` in the
SAME tick (`0x35aa4-0x35ae2`, shadow-checked against `gp-0x4cde` via `FUN_0006b9fa`). The slope-cap
logic, decompiled fresh (float arithmetic; `0.0009765625 = 1/1024`, Q10→float):
```c
fVar22 = target_Y/1024 - Y[k]/1024;                    // ΔY
fVar37 = fVar22 / (X[k+1]/1024 - X[k]/1024);            // natural slope = ΔY/ΔX
if (fVar37 >= 0 && cal(0xC6384)/1024 <= fVar37) {       // 0x353ac/0x353c2: ld.hu 0x7384[tp]
    fVar38 = cal(0xC6384)/1024;                         // slope FORCED to the cap, exactly
    X[k+1] pushed outward (re-seeded via FUN_000352a0) so the delivered segment's slope == fVar38 exactly
}
```
Matches the task's stated bound and both prior sessions' findings exactly: **`0xC6384` is a hard
per-segment slope ceiling, applied at TABLE-CONSTRUCTION time, downstream of everything else in the
build pipeline.** Confirmed independently a third time, different session, different method (full
disassembly this time, not just the decompile).

## 2. GATE 1 [EVIDENCE, dual method, every raw hit adjudicated]

Byte-verify: `0xC6384`=2048 (Q10=2.000), byte-identical across stock/V108/V109 (Python raw read, this
session). `get_bulk_xrefs(0xC6384)` → `[]` (misleading-zero trap, reproduced again). Raw Python LE scan
(both disp16 forms): 18 raw hits total. **Full `disassemble_function(0x352b4)`** (not just the byte
scan) shows exactly **2 real readers**, `0x353ac` and `0x353c2`, both `ld.hu 0x7384[tp],rX`, both
inside this function, ~20 bytes apart (the `if`-condition read and the capped-value re-read). The other
**16 raw hits are OUTSIDE this function's range**, scattered `0x180ec`-`0x5a008`; **5 spot-checked**
via `disassemble_bytes(dry_run=true)` (`0x180e0`,`0x5090a`,`0x4d4d2`,`0x59e6e`,`0x1ed2e`) — **all 5
decode as `sst.b rX,N,ep`**, a 2-byte EP-relative short-format store whose opcode+operand bits (`73 84`/
`73 85`/`73 86`, etc.) coincidentally match the LE `0x7384`/`0x7385` byte pattern. This is the kit's
already-catalogued "ep-relative short-format" trap (`accord_v850_scan_traps_formatv_and_storezero`,
`ep_relative_short_format`), now hit and excluded a further 5 times. Remaining 11 not individually
disassembled but are the same address-range/byte-pattern class; **flagging as adjudicated-by-pattern,
not individually verified** — cheap to close fully if it becomes load-bearing (see Open Items).
**0 writers** (tp-relative ROM constant, architecturally none possible).

No shadow-lockstep twin on the cal itself (unnecessary, ROM). Its output `gp-0x6b86` DOES carry one
(`gp-0x4cde`, `FUN_0006b9fa` on mismatch, `0x35aa4-0x35ae2`) — and the table-build's own X/Y arrays are
INDIVIDUALLY shadow-checked too (`gp-0x37e8[]`↔`gp-0x4c0c[]`, `gp-0x37fc[]`↔`gp-0x646c[]`, plus
`gp-0x69a4`↔`gp-0x4c66`, `gp-0x6b7a`↔`gp-0x4cdc`), all inside this same function. This is a heavily
ASIL-monitored function — a cal-only edit (no writer added) cannot desync these pairs since both shadow
copies are produced by the same instruction stream reading the same (new) cal value, but their presence
is a real, existing safety net against any runtime computation anomaly.

## 3. 🛑 Not LKAS-gated — resolved from the 1kHz dispatcher, same session as the sibling Kd memory

`FUN_0002214a` gates `FUN_000352b4` on state-mask `uVar2 & 0x830` (bits {4,5,11}) — see
`[[reference_accord_kd_ratchet_gate2_verdict_and_dispatcher_gating]]` §2b for the full mask table.
**Not LKAS-specific** — this is the base power-assist curve; it must and does run during manual
steering. A dose here is felt in every driving mode, not just LKAS-engaged.

## 4. 🛑🛑 IS IT CURRENTLY BINDING? — UNRESOLVED, and this is the crux [neither EVIDENCE nor closed BELIEF]

The natural (uncapped) slope `fVar37` depends on `target_Y` (`gp-0x6444`-family), which is **NOT** a
static ROM value — it is the output of a separate, history-dependent slew/slot-fill mechanism ("Branch
B" in `TRACE-2026-08-21-assist-map-rom-source.md` §2), itself downstream of a ROM record lookup
(`FUN_000382d8`, mode+speed indexed) and a K1/K2 rescale (`FUN_000389ec`). **Whether any segment's
natural slope currently reaches 2.000 (making the cap load-bearing) or stays comfortably below it
(making the cap a dormant, never-touched ceiling) cannot be determined from a static image read** — it
needs either live telemetry of `gp-0x37e8[]`/`gp-0x6444`-family at the operating point, or the full
byte-exact pipeline simulation that trace's own Open Item 1 already flagged as unfinished (needs
`tp+0x713e/0x7140/0x717a/0x717c`, the boost-curve LERP feeding `uVar48`, `cal(0xC613A)`, and the live
`0xD7130`-family Y-knot content). **I did not close this gap either** — flagging explicitly rather than
assuming either way. `[[reference_accord_aggregator_11term_loop_census_units_and_fork]]`'s "0.5-2.000"
range for `gp-0x6b86` in its `L`-table should be read as **the structural bound (min plausible to the
cap)**, not a confirmed-reached operating value — that memory's own phrasing ("magnitude = the local
slope `s ≤ 2.000`") is consistent with this reading; I am making the distinction explicit because the
brief's "7.8x the entire PID" framing could otherwise be read as an already-measured fact.

## 5. GATE-2 structural argument — robust regardless of §4 [EVIDENCE]

The evaluation step (§1) is memoryless: **for a FIXED table (i.e., linearizing around an operating
point), `d(gp-0x6b86)/d(input)` = the local delivered slope, a REAL number, 0° phase, by construction —
at EVERY frequency simultaneously, DC through Nyquist.** This is structurally different from Kd
(`[[reference_accord_kd_ratchet_gate2_verdict_and_dispatcher_gating]]` §5), whose magnitude is
proportional to `|1-z^-1|` and therefore near-zero at DC/low frequency and grows with `f` — i.e. Kd is
naturally high-pass-shaped and DC-free; `gp-0x6b86`'s slope term is NOT shaped at all. **Consequence: IF
this term is live (§4 unresolved), a dose changes the loop's real-axis gain by the exact same fraction
at 1, 7.79, 21.73, 40 and 100Hz simultaneously — there is no way to target the 7.8Hz ratchet without
proportionally touching the 18-22/26-31Hz grinding bands (separately being addressed by V108/V109) AND
the DC/steady-state base-assist feel (unlike Kd, whose DC cost is exactly zero by construction) AND
manual steering (§3).** This magnitude-shape comparison needs no knowledge of the plant transfer
`G_bar(f)` — both candidates are driven by the same `gp-0x4f60`-domain signal and therefore share
whatever `G_bar(f)` multiplies onto them; the ASYMMETRY in how each candidate's OWN internal transfer
shapes that same input is what the argument rests on, and that part is 100% firmware-derived.

## Open items — exact next step to close each

1. **Is the cap currently binding?** Next: live telemetry of `gp-0x37e8[]`/`gp-0x6444`-family (or the
   full ROM→Branch-B pipeline simulation TRACE-2026-08-21 left open) at representative creep/ratchet
   operating points (25-40 km/h, per the ratchet's own speed profile).
2. **Full adjudication of the remaining 11 raw-scan hits** (only 5/16 individually disassembled). Cheap:
   `disassemble_bytes(dry_run=true)` on each; expected to resolve as the same `sst.b` EP-short-form class.
3. **`gp-0x37e8[]`'s actual operating-point content** (not read this session) would directly answer #1
   without needing the full simulation, if a live dump or a rlog capture of the RAM region is available.

## Related
[[reference_accord_kd_ratchet_gate2_verdict_and_dispatcher_gating]] — Candidate 1, the sibling verdict
and the magnitude-shape comparison this file's §5 depends on.
[[reference_accord_aggregator_11term_loop_census_units_and_fork]] — the loop topology and `L`-table.
`docs/traces/TRACE-2026-08-21-assist-map-rom-source.md` — the original role trace, now re-confirmed.
