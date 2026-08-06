---
name: reference_accord_shaper_rail_companion_guard_0x41852
description: FUN_00041464 re-tests gp-0x6b98 against the SAME +-0x2000 window (0x41852-0x4185E) as the shaper's own hard clamp, gating an opposing-motion/back-drive detector (gp-0x6ac2, 4+ downstream readers). Raising the shaper's rail without co-editing this companion site is a real GATE-1 cost, never checked by any build (0x41852/0x41856 appear in zero build scripts).
metadata:
  type: reference
---

2026-08-05, team-lead mission "mixer headroom + the 20.9Hz gain peak", Part 2d ("raise the rail").
Program: code.bin (stock).

## The finding [EVIDENCE, disassemble_bytes dry_run 0x41840-0x4189f]

`FUN_00041464` (the same function producing `gp-0x6c2c`/`gp-0x6abe`, see
[[reference_accord_gp6c2c_transfer_function_triple_verified]]) reads `gp-0x6b98` (the shaper's final
output) and re-applies the IDENTICAL `+-0x2000` validity window the shaper itself enforces at
`0x43B52`/`0x43DFC` ([[reference-accord-shaper-fun42af8]]):

```
0x41846: ld.h -0x6b98,gp,r9        ; r9 = gp-0x6b98
0x41852: addi 0x2000,r9,r11        ; r11 = r9 + 8192
0x41856: addi -0x4001,r11,r0       ; flags = r11 - 16385 (discarded)
0x4185E: bc  0x000418ee            ; branch on the ±0x2000 window test
0x41860: ld.hu -0x6ac2,gp,r10      ; (fall-through path) opposing-motion/back-drive detector logic
          ... sign(filtered speed) vs sign(gp-0x6b98) -> gp-0x6ac2 = |filtered speed|>>10 or 0
```
Taking the branch at `0x4185E` (gp-0x6b98 outside today's ±8192 window) **skips the normal
opposing-motion detector computation and jumps straight to `0x418EE`** — a different code path for
`gp-0x6ac2`. I did not fully trace what `0x418EE` sets `gp-0x6ac2` to (open item below), but the
detector's downstream footprint is already established: **`gp-0x6ac2` feeds back into the app region at
readers `0x346A4`, `0x347C0`, `0x42F42`, `0x4434E`, `0x41C78`** (per
[[reference_accord_below_gp6b98_foc_delivery_path_swept]]) — a real inner-loop-to-outer-loop feedback
route, not a dead-end monitor.

## Consequence for "raise the rail"

**Raising the shaper's ±0x2000 hard clamp (`0x43B52`/`0x43DFC`) WITHOUT also raising this companion
window at `0x41852`/`0x41856` means any command that newly exceeds 8192 (the whole point of raising the
rail) will hit a DIFFERENT code path in the opposing-motion detector than it did before** — the detector
was structurally built assuming ±0x2000 is the ceiling. This is a genuine GATE-1 (blast-radius) cost for
the "raise the rail" lever that a naive single-immediate-edit price tag would miss.

**Grep confirmed** (`build_v*_tva.py`, all builds): `0x41852` and `0x41856` appear in **zero** build
scripts — this companion site has never been examined or edited by any build in this kit's history.

## RESOLVED 2026-08-05 follow-up — the fail path is a stale-hold, not a sentinel/zero

`disassemble_bytes(0x418ee, dry_run)`: the fail branch **re-reads `gp-0x6ac2`** and compares it against
its own lockstep shadow `gp-0x4cc6` (the `FUN_0006b9fa` dual-write-consistency idiom used throughout this
image), then leaves it unchanged. **`gp-0x6ac2` is simply FROZEN at its last in-range value when
`gp-0x6b98` exceeds ±0x2000 — not zeroed, not sentinel'd.** Lower severity than initially flagged:
raising the rail without co-editing this guard means the back-drive detector goes **stale** above 8192
(a bounded, non-catastrophic failure mode), not actively wrong. Still a real GATE-1 item to price
(a stale detector during exactly the high-command episodes a "raise the rail" build is meant to help
is not free), but not a correctness hazard.

## Remaining open item
Whether the ±0x2000 immediates at `0x41852`/`0x43B52`/`0x43DFC` would need to move together as a
matched set, or whether the companion guard could be widened independently without touching the
shaper's own clamp — not evaluated.

## Related
[[reference-accord-shaper-fun42af8]] — the shaper's own clamp stack this companion guard mirrors.
[[reference_accord_below_gp6b98_foc_delivery_path_swept]] — source of `gp-0x6ac2`'s downstream reader
map.
