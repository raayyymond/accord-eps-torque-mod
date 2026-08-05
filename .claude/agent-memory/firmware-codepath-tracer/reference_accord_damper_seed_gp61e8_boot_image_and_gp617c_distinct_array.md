---
name: reference_accord_damper_seed_gp61e8_boot_image_and_gp617c_distinct_array
description: Independent verification (parallel to sibling agent F7) of the FUN_00034350 base-assist damper's seed (gp-0x698a, MIN-reduced from gp-0x61e8[0..10]). Confirms gp-0x617c (V72-DESIGN's array) and gp-0x61e8 (F4's seed array) are DIFFERENT arrays inside the same FUN_00026c80 dispatch, with different role-to-value mappings -- but the practical conclusion (no channel gets unity on this car's 0xC4124 role table {0,5} only) survives via a corrected argument. DECISIVE: gp-0x6230[i]'s boot image (the value the seed pulls from in states 0/5) is 1024/unity for all 11 channels, not zero -- refutes "seed dead from boot." The writer FUN_00025c32 has explicit restore-to-1024 branches; the seed is not a monotone-down-only accumulator at this level. Runtime trajectory during an actual drive NOT traced.
metadata:
  type: reference
---

# Base-assist damper seed (`gp-0x698a`) — boot image and array-identity check (2026-08-05)

Team-lead dispatched two agents independently (this one, and sibling `F7-ratchet`) to check whether the
damper's seed (`gp-0x698a` = `FactorA`, `MIN`-reduced from `gp-0x61e8[0..10]`) is structurally dead from
boot, which would make Levers B/C (V72's damping-approach candidates) untested by construction. Standing
instruction: work independently, do not coordinate, so two derivations exist.

## "Check this first" — `gp-0x617c` and `gp-0x61e8` ARE different arrays [EVIDENCE, fresh full decompile of `FUN_00026c80`]

Confirmed by declared pointer type in the decompile itself: `gp-0x617c` walked as `undefined1*` (BYTE
array, `*puVar40 = 1`); `gp-0x61e8` walked as `undefined2*` (HALFWORD array, `*puVar27 = 0x400`). Two
physically separate RAM regions, 0x6c bytes apart, same loop index but independent pointer arithmetic.
Full 8-branch dispatch traced for both, keyed on `*(char*)(tp+0x5124+i)` (`0xC4124`, the SAME static
role table used elsewhere in this kit for the `gp-0x67ac` vacuity proof):
```
gp-0x617c[i] (V72-DESIGN §5's array, feeds gp-0x67ac):  role {6,7} -> 1  |  role {0,1,2,3,4,5} -> 0
gp-0x61e8[i] (F4's seed array):                          role {1,6,7} -> 1024 (unity)
                                                          role {0,2,3,4,5} -> gp-0x6230[i] (rolling value)
```
**Different mapping** (role 1 gives unity for the seed array, but NOT for `gp-0x67ac`'s array). Team-lead
was right to worry these might not be interchangeable. BUT: `0xC4124`'s actual byte content (team-lead's
own read, cross-checked) is `{0,0,5,0,5,5,0,0,0,5,0}` — distinct values `{0,5}` ONLY. Roles 1/2/3/4/6/7
never occur on this car. Since both roles that DO occur (0 and 5) map to `gp-0x6230[i]` (never unity) for
the seed array too, **the practical conclusion survives**: no channel's seed slot ever takes the unity
path — just via "the only two roles that exist both avoid unity," not "6/7 are the only unity roles."

## DECISIVE — `gp-0x6230[i]`'s boot image is 1024 (unity), not zero [EVIDENCE, boot-init .data chain]

Per [[reference_accord_app_ram_layout_and_boot_init_loops]]: `gp-0x6230` absolute =
`0xFEDF8000-0x6230 = 0xFEDF1DD0`, inside the `.data` region `[0xFEDF11B0, 0xFEDF5A68)`. Boot value =
`flash[0x86260 + (0xFEDF1DD0-0xFEDF11B0)] = flash[0x86E80]`. **Fresh read: `0x86E80..0x86E96` = eleven
repeats of `00 04` LE = 1024, for all 11 channels.** Unlike `gp-0x617c`'s all-zero boot image, this array
boots HEALTHY. On the very first tick, before `FUN_00026c80` ever runs, `gp-0x6230[0..10]` all read
1024, so `gp-0x61e8[0..10]` (via roles 0/5) also read 1024, so the outer `MIN(...)` = 1024 = full unity.
**The seed does not start at zero and cannot be described as "unable to ever be restored from a floor it
never touches at boot."**

## Restoration paths exist in the writer [EVIDENCE, full decompile `FUN_00025c32`]

`gp-0x6230[i]`'s actual writer is `FUN_00025c32`, NOT `FUN_00026c80` (confirmed: `FUN_00026c80` only
READS `gp-0x6230` via a local pointer alias `puStack_11c`, never writes it). `FUN_00025c32` is a large,
generic per-channel confirmation/debounce state machine (state byte `gp-0x61a0[i]`, 0-5), with **10
callers image-wide** (`FUN_00023ad2/23fe2/2b422/2c246/2caa2/2e52e/339cc/3405a/3a8a8/3aff4` — a shared
utility, not seed-dedicated; WHICH of these is wired to THIS specific 11-channel array not
disambiguated). Multiple branches **explicitly reset `gp-0x6230[i]` to `0x400`(1024)** on certain state
transitions (e.g. a "state 5" branch, and a fresh-entry sub-path). Other branches instead **pass through
a value from the CALLER's own input struct**, clamped only at the top (`sVar6 = clamp_high(param_1+10 as
u16, 1024)`, otherwise unclamped) — i.e. `gp-0x6230[i]` is periodically SET (not just floored) from
whatever the caller currently measures. **Not a monotone-down-only accumulator at this level** — that
framing may describe the outer `MIN` reduction into `gp-0x698a` itself (not re-traced this round), but
the thing feeding `gp-0x6230[i]` is not one-way.

## What remains open

The actual RUNTIME trajectory during a drive: which of the 10 `FUN_00025c32` callers feeds THIS array,
what real sensor/plausibility data it passes as `param_1+10`, and whether that data can plausibly drive
`gp-0x6230[i]` down and hold it down in practice. The boot-image finding refutes the WORST case (dead
from boot, no recovery possible) but does not by itself prove the seed is healthy during actual driving
-- that needs the caller trace this session did not complete.

## Bottom line

The specific worst-case hypothesis team-lead was checking ("seed dead by construction, Levers B/C never
actually tested") is REFUTED by the boot-image evidence: the seed boots at unity and has structural
restore paths. Whether it degrades and stays degraded in real operation is a separate, still-open
question requiring the `FUN_00025c32` caller trace.

## Related
[[reference_accord_app_ram_layout_and_boot_init_loops]] -- source of the boot-image derivation method.
[[reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor]] -- prior encounter
with `FUN_00025c32` characterized as "a generic N-channel redundant-sensor voter," consistent with this
session's finding that it's a shared, multi-caller utility.
