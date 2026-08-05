---
name: reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found
description: Closes "FactorA" (it IS the seed, gp-0x698a -- no separate table exists) and FULLY CLOSES the seed-explains-V72's-null hypothesis -- all 11 redundancy-voter channels (10 live-traced + channel 10's .data boot value read from flash) are pinned at exactly 1024 on both stock and V72. Independently byte-confirms all V72 Lever B/C values. Finds two NEW engagement-branching mechanisms (FUN_0002a93a binary gate, FUN_00042746 table-selector) answering the "what generates the ratchet" question. The gp-0x6bd0-always-0 mystery is NOT resolved -- narrowed to the FactorE saturation gate or something outside the multiply chain (task-5 scheduling / probe read site).
metadata:
  type: reference
---

# gp-0x6bd0 null investigation, round 2 -- 2026-08-05, extends [[reference_accord_gp698a_seed_factora_ceiling_and_v72_probe_null_investigation]]

Task: team-lead asked (1) find "FactorA", explain why V72's damper-presence probe (`|gp-0x6bd0|>=64`)
read 0/87,940 frames incl. 0/34,275 above 35 km/h, (2) recommend a cal-only lever if deliverable,
(3) independently find what generates the ratchet, tying to engagement.

## (1) "FactorA" is CLOSED -- it does not exist; it IS the seed [EVIDENCE, fresh decompile of FUN_00034350]

The 5-factor product in `FUN_00034350` (0x34350) is, byte-exact from the decompile:
```c
uVar7 = ((((uVar10*min(uVar10,1024) * uVar7_B >>10) * uVar13_C >>10) * uVar21_D >>10) * uVar16_E >>10);
if (gp-0x6abe > 0) uVar7 = -uVar7;
```
`uVar10 = *(gp-0x698a)` = **seed** (MIN-clamped to 1024). `uVar7`=table@`0xC9CCC[mode]`=team's **FactorB**.
`uVar13`=table@`0xC9E9C[mode]`=**FactorC**, keyed on `gp-0x6a5e` (voted SPEED), gated by flag
`gp-0x67f4==1` (else defaults unity 1024, does NOT zero). `uVar21`=table@`0xC9DB4[mode]`=**FactorD**,
keyed on `gp-0x6a10` (angle, near-centre chain), gated similarly (defaults unity). `uVar16`=table@
`0xC9F84[mode]`=**FactorE**, keyed on `|gp-0x6ac0|` (motor rate) -- but FactorE's OUTER gate is
different in kind: `if (gp-0x6ac0 < 0x32c9(13001) && gp-0x6abe<=12936) {...} else { uVar7=0; }` --
**this is the ONLY branch in the whole chain that zeroes the ENTIRE PRODUCT, not just its own factor.**
Semantically this reads as a near-saturation-rail guard on the resolver/motor-rate signal (13001 ~= the
representable ceiling), not something that should persistently fail in ordinary driving.

Independently byte-dereferenced the 4 mode-10 pointer tables (different method than team-lead's dump,
same numbers, confirms both):
| Table | ptr table | mode10 target | stock Y | V72 Y |
|---|---|---|---|---|
| FactorB | `0xC9CCC` | `0xD2738` | `[1024,1024,1024,1024]` (flat) | unchanged |
| FactorC | `0xC9E9C` | `0xD27BC` | `[0,235,430,877]` | `[430,430,430,877]` |
| FactorD | `0xC9DB4` | `0xD2774` | `[1024,1024,1024,1024,1024]` (flat) | unchanged |
| FactorE | `0xC9F84` | `0xD27F8` | `[0,140,539,927]` | `[927,927,927,927]` |
`0xC63A0` (LEVER C weight in `FUN_00038148`): stock=1024, V72=2048, confirmed. Ceiling `0xD209C`
X=[300,800] Y=[512,1024ish], byte-stock in V72, confirmed. **Every one of team-lead's numbers checks out
exactly**, via pointer-table dereference rather than their span-diff method.

## (2) UPDATE 2026-08-05 round 3: seed hypothesis now FULLY CLOSED, not just weakened [EVIDENCE]

Team-lead independently found the same `FUN_00026c80` dispatch (`tp+0x5124`=`0xC4124`=`[0,0,5,0,5,5,0,0,0,5,0]`,
distinct={0,5}, matches my byte read exactly) and argued: no channel ever reaches states 6/7 (the flat-1024
reset path), so every `gp-0x61e8[i]` comes from the rolling `gp-0x6230[i]` -- therefore if `gp-0x6230[i]`
is not itself 1024, the seed sits below unity. **This is correct as far as it goes** (I'd already found
states 0 AND 5 -- not just 6/7 -- ALSO copy from `gp-0x6230[i]`, so the conclusion "gp-0x61e8[i] comes from
gp-0x6230[i] for every channel" holds) **but it resolves the OTHER way**: I closed what `gp-0x6230[i]`
actually holds, for the one channel (10) that has NO runtime writer at all.

**Channel 10 (index 10 of 0-10) is never passed to `FUN_00025c32` by anything** -- confirmed via BOTH
`get_function_callers` and `get_xrefs_to(0x25c32)` (same 10 sites, covering only indices 0-9), PLUS a raw
LE-pointer scan of the whole image for the bytes `32 5c 02 00` (0x25c32 as a 32-bit pointer) -- **zero
hits**, ruling out an indirect/function-pointer call path too (the kit's documented RTOS-table blind spot
does not apply here; there is no pointer to find).

**So channel 10's value is whatever it boots to, forever. I checked.** Reused this kit's own
[[reference_accord_app_ram_layout_and_boot_init_loops]] (GATE-1 RAM map): `.data` covers RAM
`0xFEDF11B0..0xFEDF5A68` sourced from flash `0x86260+`; `gp-0x6230` (RAM base `0xFEDF1DD0`) sits inside it.
Read all 11 elements of ALL FOUR parallel MIN-reduce arrays directly from flash, both builds:
```
gp-0x6230[0..10]  flash 0x86E80-95: stock=[1024]x11   v72=[1024]x11
gp-0x61e8[0..10]  flash 0x86EC8-DD: stock=[1024]x11   v72=[1024]x11   (feeds the seed gp-0x698a)
gp-0x61b8[0..10]  flash 0x86EF8-0D: stock=[1024]x11   v72=[1024]x11   (feeds gp-0x6986)
gp-0x61d0[0..10]  flash 0x86EE0-F5: stock=[1024]x11   v72=[1024]x11   (feeds gp-0x6988)
```
Channel 10 boots at 1024, byte-identical to the other 10, on both builds -- a deliberate compile-time
initializer, not a BSS-zero accident (the surrounding region IS otherwise BSS-zeroed by the boot loop at
`0x146C0`, but `.data`'s explicit flash-sourced copy at `0x1475C` overrides that for this whole range).

**⇒ `gp-0x698a`/`gp-0x6986`/`gp-0x6988` are structurally pinned at 1024 at every instant, live or at boot,
on both stock and V72. There is no path by which any of the 11 channels pulls the seed down on this
calibration. The seed does NOT explain V72's null; Levers B/C are NOT vacuous on this specific point.**

## (2-prior) Seed hypothesis SUBSTANTIALLY WEAKENED, not fully closed [superseded by the above, kept for the trace]

The seed (`gp-0x698a`) is a MIN-reduce over an **11-channel generic redundancy/plausibility-voter
framework** (`FUN_00026c80`, sole caller `FUN_0002214a`/task 1/1kHz; the per-channel FSM is
`FUN_00025c32`, called from **10 distinct sites** covering channel indices 0,1,2,3,4,5,6,7,8,9 --
channel 10's caller not found this session, a real gap). Traced ALL 10 callers' struct-build code:

**9 of 10 channels (0,2,3,4,5,6,7,8,9) hardcode their three confidence-input fields to flat `0x400`
(1024)** at the call site -- these channels can NEVER pull the seed below ceiling, structurally,
regardless of their own FSM state, because `FUN_00025c32`'s clamp (`sVar6=min(input,1024)`) only ever
returns exactly what's handed in when input is already <=1024.

**Channel 1 (`FUN_0002b422`, 0x2b422) is the SOLE exception** -- it feeds two LIVE confidence fields
(`gp-0x697c`, `gp-0x697e`) computed by `FUN_00028ea6` (**the SAME LKAS engage-ramp state machine that
owns `gp-0x6806`/`gp-0x69b0`**, see [[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]]).
The formula (`0x2a26c`/`0x2a2a2`ish, decompiled): `gp-0x697e/697c = 1024 - ramp*(1024-floor_cal)>>15`,
active only when channel-1's own gate state `gp-0x67a4` in {2,3}; otherwise flat 1024. **This looked
like the smoking gun** (a confidence value that legitimately degrades with sustained LKAS-engagement
ramp progress, `uVar18`=`gp-0x69b0`) -- **but byte-read all 4 candidate floor cals
(`tp+0x73dc/73da/73e0/73de` = `0xC63DC/DA/E0/DE`) and every one reads exactly `1024` on BOTH stock and
V72.** With floor=1024 the blend formula collapses to flat 1024 regardless of ramp position.
**⇒ Channel 1's degrade path is a calibrated NO-OP on this firmware; the seed should be effectively
pinned near 1024 given everything traced.** [BELIEF, conditional on channel 10 -- not traced -- also
being benign]

Also re-confirmed from the prior session's memory: the write to `gp-0x6bd0` is a standard shadow-lockstep
symmetric clamp (would show as recorded faults if failing, not a silent zero); the Q-format closure holds
given the near-unity finding above is now stronger, not just assumed.

**⇒ VERDICT: could NOT find a structural reason inside the 5-factor multiply chain for gp-0x6bd0 reading
persistently 0, including above 35 km/h.** Every factor traced checks out as either correctly-edited
(FactorC/E) or provably-unity (seed, FactorB, FactorD). This is an unresolved contradiction between the
calibration (which should deliver ~389 counts at creep, team-lead's own math, now independently
corroborated) and the observed telemetry. Two remaining candidates, NEITHER verified this session:
(a) FactorE's outer saturation-rail gate, if `gp-0x6ac0`/`gp-0x6abe` behave unexpectedly on this vehicle;
(b) something OUTSIDE the multiply chain entirely -- e.g. whether task 5 (100 Hz, `FUN_00034350` +
`FUN_00034a72`/boost) is actually executing during the probed drive. **Cheap on-telemetry check for the
team: does `gp-0x6bbe` (boost, SAME task-5 lane) ALSO read persistently near-zero on the same V72 drive?**
If boost is fine and only damping is null, task-5-dead is ruled out and the mystery narrows back to
`FUN_00034350`'s own body or the probe's read site.

## (3) Ratchet-generating mechanism: TWO engagement-branching candidates found [EVIDENCE, from existing memory this session corroborated + read]

Confirms and extends [[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]]:
`gp-0x6806` is **99.98% correlated with LKAS-engaged** (V67 on-car probe, per that memory). Two places
where the assist chain **structurally branches** on it/its sibling `gp-0x69b0` (the 0..0x8000 Q15 ramp):

1. **`FUN_0002a93a` -- a BINARY (non-proportional) gate on the whole arb-curve sub-computation.**
   `if (gp-0x69b0==0 && gp-0x6805!=1) { curve computation held at a defined ZERO/sentinel; }` else the
   FULL computation runs, **not scaled by ramp magnitude within this function**. Its outputs
   (`gp-0x6b2e/32/34/36`) feed the confirmed-LIVE PATH-A chain into `gp-0x6b3c`. This is a genuine
   structural DISCONTINUITY at the instant of engagement (ramp departs from 0), not a smooth transition --
   a real candidate for a relay-like element right at engagement onset.
2. **`FUN_00042746` -- coefficient-TABLE SELECTION on settled engagement transitions.** When `gp-0x6806`
   changes AND the ramp has settled at an endpoint (0 or full-scale 0x8000), it selects between 6 distinct
   tables (`DAT_0000e012..e018`, stride 0x24). **NOT characterized this session or prior**: what those
   tables represent, or downstream consumers of `gp-0x674f`/`gp-0x63fd`. Flagged (again) as the single
   most promising unexplored lead for a mechanism whose FILTER/GAIN SET literally changes on engagement.

Both feed off the same ramp SM (`FUN_00028ea6`) whose dynamics are known: dir-0 ramp-up +33/cycle (~1s
to full scale), dir-2 +328/cycle (~100ms), decay -328/cycle (~100ms) -- all 1kHz-task cycles, so state
transitions at engagement/disengagement complete within roughly 0.1-1s, not fast enough to BE the 7.8 Hz
oscillation itself, but plausibly fast enough to seed a transient that a lightly-damped 7.8 Hz mode
(measured Q~=40) rings down slowly from.

## Related
[[reference_accord_gp698a_seed_factora_ceiling_and_v72_probe_null_investigation]] -- prior pass this same
investigation extends. [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] -- base trace.
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]],
[[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]] -- source of the engagement-gate
material, corroborated not re-derived. [[reference-accord-fun2eda8-lane9-raw-torque-command-path]] --
the SAME `FUN_00025c32`/`FUN_00026c80` 11-lane framework, documented independently for lane 9 (a
DIFFERENT lane than the seed's own 11-channel voter -- same generic library, two different instantiations,
do not conflate).
