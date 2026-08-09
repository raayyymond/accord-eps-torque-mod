---
name: reference_accord_fun38148_fun37fe6_channel_census_and_dead_lanes
description: Full channel census of FUN_00038148's SUM_6ch (gp-0x6bd0 family) and FUN_00037fe6's own 1-unconditional+7-gated sum — 2 permanently-dead channels found (gp-0x6bce, gp-0x6bbc), gp-0x6b60's writer needed a raw byte scan (orphaned/unbounded in Ghidra)
metadata:
  type: reference
---

Two DIFFERENT six/seven-term sums exist downstream of the plant-model estimator — do not conflate them (a prior brief did).

**`FUN_00038148`'s SUM_6ch** (weights tp+0x73a0..0x73aa = 0xC63A0..0xC63AA, feeds the residual-vs-model comparison, see [[reference_accord_ram_lerp_y0_zero_corrects_v86_relay_claim]] for the downstream LERP):
| weight | channel | gate | meaning | writer |
|---|---|---|---|---|
| 0xC63A0=1024 | gp-0x6bd0 | ±2048 | base-assist DAMPER (FactorC×FactorE) | FUN_00034350 |
| 0xC63A2 | gp-0x6bbe | ±2048 | base boost curve | FUN_00034a72 |
| 0xC63A4 | gp-0x6b46 | ±1024 | NEW: hysteresis-gated integrator on driver column torque gp-0x4f60 (hysteresis compare vs tp+0x719c/0x71a6, integrator alpha tp+0x73d2, rate-limit counter gp-0x6a80), ±512 pre-clamp | FUN_00036682 (full decompile 2026-08-09; structure=EVIDENCE, physical LABEL=BELIEF, not yet connected to a driver-facing name) |
| 0xC63A6 | gp-0x6b26 | ±1024 | FRICTION lane | FUN_00036c12 |
| 0xC63A8 | gp-0x6b4e | ±10240 | 3rd output of the 11-ch LKAS mixer (sibling of gp-0x6b4c, sourced from accumulator gp-0x3d8c) | FUN_00026c80 |
| 0xC63AA | gp-0x6b4c | ±10240 | LKAS mixed_command lane | FUN_00026c80 |

**`FUN_00037fe6`'s own sum** (feeds gp-0x6ad6, the PID's bias): **1 unconditional term + 7 gated terms (byte enables 0xC64AD..0xC64B3), NOT 6** — decompile-corrected count.
| term | gate byte | meaning | writer |
|---|---|---|---|
| gp-0x6b4a (unconditional, ±25600, negated) | none | LKAS mixer's WIDE/raw output (sibling of gp-0x6b4c, unscaled) | FUN_00026c80 |
| gp-0x6bce | 0xC64AD | **DEAD — 0 writers image-wide**, raw byte scan confirms only 1 halfword-aligned occurrence total (the read @0x38050) | none |
| gp-0x6b6e | 0xC64B1 | FUN_0003b338 output, mode table 0xC8198, gated gp-0x67fe!=0 AND gp-0x6996≤1024 AND \|gp-0x6a0a\|≲10000, keyed on gp-0x6a16; gp-0x6a0a is the established angle-rate-integrator accumulator | FUN_0003b338 |
| gp-0x6bbc | 0xC64AF | **DEAD — 0 writers**, same raw-scan confirmation (1 occurrence total = the read @0x38016) | none |
| gp-0x6b70 | 0xC64B0 | Path-2's residual output | FUN_00038148 |
| gp-0x6b60 | 0xC64B2 | 🛑 search_instructions UNDERCOUNTS this — genuine writer invisible to it. Raw byte scan found a 3rd hit search_instructions missed at 0x36352, in orphaned code (0x36320-0x36356) NOT bound to any Ghidra function (`get_function_by_address` returns null; confirmed real via `disassemble_bytes dry_run:true`, valid instruction stream). Computes `gp-0x6b60 = gp-0x6bf0 >> 10`, gated to 0 unless mode bytes gp+0x6440/gp+0x6441==2. gp-0x6bf0 = established driver-override/peak-hold-envelope signal (see [[reference_accord_lerp_envelope_gating]] family) | orphaned block @0x36352 |
| gp-0x6b2a | 0xC64B3 | FUN_0003b49a output, mode-indexed (gp+0x63fd), 2 cascaded LERPs (0xCBCA4 torque-domain off gp-0x4f60 EMA, 0xCBD8C speed-domain off gp-0x6a5e voted speed), combined with gp-0x6a56 (raw steering angle rate), sign-relay fallback to tp+0x71c6. Also writes gp-0x6b28 (internal magnitude tap) | FUN_0003b49a |

**Dead-lane finding**: gp-0x6bce and gp-0x6bbc are BOTH permanently 0 (dual-method confirmed: search_instructions AND raw byte scan agree there is exactly one halfword-aligned occurrence of each address image-wide — the read itself). 2 of 8 summands in FUN_00037fe6 contribute nothing on any build ever produced, stock included. Arming either needs a NEW producer (code cave), not a cal edit — GATE 1/GATE 2 territory.

None of gp-0x6b6e's (FUN_0003b338) or gp-0x6b2a's (FUN_0003b49a) producer functions have ever been written by any build script (grep-confirmed).

Traced 2026-08-09, `fw-lever-census` task, reported to team-lead in the same session.
