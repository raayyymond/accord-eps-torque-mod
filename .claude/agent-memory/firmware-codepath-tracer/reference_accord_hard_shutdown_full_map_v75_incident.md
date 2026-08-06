---
name: reference_accord_hard_shutdown_full_map_v75_incident
description: Full hard-shutdown actuator + trip-condition map built for the V75 stoplight-launch EPS-lamp/total-assist-loss incident. Confirms the governor's authority-gain-collapse actuator, finds a NEW undebounced monitor (FUN_00045a20), enumerates 6 shadow-lockstep pairs directly downstream of the damper output gp-0x6bd0, and byte-confirms per-DTC hard-latch eligibility via FUN_00018738's threshold table.
metadata:
  type: reference
---

Built 2026-08-06 for the V75 incident (stop->launch, engaged, hard EPS-lamp fault, latched total loss of
power steering). Program: stock `code.bin`. Method: decompile-first throughout, byte reads for every
cal/threshold claim.

## The actuator is a GAIN COLLAPSE, not a discrete motor-off write [EVIDENCE]

`FUN_0001a16a` (called from the shutdown branch of `FUN_00019f7c`) does exactly 4 things:
```
FUN_00018950()                    ; per-DTC status/freeze-frame housekeeping (iterates 0x19=25 records)
FUN_00045608(0, 0, 0x8000, 0x8000) ; channel 0 <- {target=0, min=0x8000, max=0x8000}
FUN_00046372(4)                   ; gp-0x3514 = 4 (mode/state word)
FUN_00018f4a()                    ; post-shutdown state sequencer, writes 0x14 to a hw-mapped byte
                                   ;   at DAT_fedf1008-relative addr; handles states 6/8 specially
```
🛑 **Correction of record**: `reference_accord_consistency_monitor_hardshutdown.md` (this same directory)
states the call as `FUN_00045608(3, 0, 0x8000, 0x8000)` — **channel 3**. Fresh decompile of
`FUN_0001a16a` on stock `code.bin` shows **channel 0**. `FUN_00045608` has **16 callers** image-wide
(`get_function_callers` — not motor-off-specific, a shared authority-slot setter). Flagging for the
operator to confirm before that file is edited (per memory conventions, asking before touching another
session's memory).

`FUN_00045608(ch, target, min, max)` writes into 3 parallel arrays `gp-0x652c[ch]` / `gp-0x64fc[ch]` /
`gp-0x6514[ch]` (7 slots, `ch<7`). These are read **every 1 kHz cycle** inside
**`FUN_0004503c`** (= `m_motor_torque_governor`, dispatched from the 1 kHz task `FUN_0002214a`
`w_steer_control_task`). There, the channel-0..2 slots produce rate-limited multiplicative authority
factors (`uVar17`, `uVar6`, `uVar15`, `uVar9`, via helper clamps `FUN_00049a90`/`FUN_00049a70`/
`FUN_00049a78`), which are applied to **`gp-0x6b94`** (the aggregator's summed torque command — see
below) BEFORE the per-cycle slew limit (`cal tp+0x7206=0xC6206=512` or `tp+0x7208=0xC6208=205`,
selected by `gp-0x67f5`) writes the result to **`gp-0x6ace`**.

**⇒ `FUN_00045608(0,0,0x8000,0x8000)` forces channel-0's authority target to 0 with a degenerate
min/max (0x8000 = -32768), collapsing the multiplicative authority factor toward zero over at most one
rate-limited step — this is how "motor off" is implemented: not a PWM/GPIO disable I could locate, but
an upstream GAIN COLLAPSE that zeroes the torque command before it reaches `gp-0x6ace` -> `gp-0x6acc`
-> `gp-0x6b98` -> FOC delivery.** [BELIEF for "this is what the driver feels as total assist loss" —
consistent with the symptom (commanding literal zero motor current through a still-running FOC loop
reads exactly as "wheel becomes manual-effort"), but I did not trace a literal H-bridge/PWM disable
register; `FUN_00018f4a`'s `DAT_fedf1008` write and the mode byte `gp-0x6762` (gates the FOC core at
`0x71298` per `reference_accord_below_gp6b98_foc_delivery_path_swept.md`) are candidates for a harder
disable not chased this session.

## The dash EPS lamp candidate [BELIEF]

`FUN_00019f7c`'s trip block also calls `FUN_00021e46()` -> `FUN_0005db02(FUN_0005daa2()|8)` — sets bit 3
of a status byte at `gp-0x2d2c`, which round-trips through `FUN_0005a3a0(0xe, &DAT_0000db00, uVar2, 0)`
and a readback `FUN_0005a3a0(0xe, 0x3000, 0, gp-0x2d2c)` (peripheral-ID-0xE request/response pattern —
not identified further this session; plausible candidates are an on-die data-flash/NVRAM channel or a
cluster-status broadcast). This is the best-evidenced candidate for the dash MIL, but the literal
lamp-driver wire was not traced to closure.

## THE AGGREGATOR — confirms `gp-0x6bd0` (V75's damper) feeds the SAME command chain the hard monitors watch

`FUN_0003aa2c` (`m_torque_aggregator`, called every cycle) sums, in the live (non-reduced,
`gp-0x67ac==0` per `reference_accord_gp67ac_reduced_branch_unreachable.md`) branch:
```
total = gp-0x6ade(rangegated +-0x400) + gp-0x6b4c[LKAS](+-0x2800) + gp-0x6ad4(+-0x2800)
      + gp-0x6b62(+-0x2000) + gp-0x6b26[friction](+-0x400) + gp-0x6bbe[angle-rate](+-0x1000)
      + gp-0x6bd0[DAMPING, V75's lever](+-0x1000) + gp-0x6b86[peak-hold](+-0x3000)
      + base-assist-clamped(+-0x2000) + friction/deadband-clamped(+-0x2000) + FUN_00036682()
clamp to +-0x2800 (10240) -> gp-0x6b94 / shadow gp-0x4ce0 (FUN_0006b9fa on mismatch)
```
`gp-0x6adc`/`gp-0x6ada` at the end are the known dead telemetry mirrors (0 readers, matches
`accord-aggregator-lane-mirrors-6ada-6adc.md`).

## SIX shadow-lockstep pairs directly downstream of the damper [EVIDENCE, fresh this session]

Every one of these fires `FUN_0006b9fa(addr)` (-> `gp-0x4d6c=addr; FUN_0006ce7c(4)` -> writes status
byte 4 into `gp-0x444f`/`gp-0x4e53` -> read by `FUN_0006ce90`, a generic "channel 8" RTOS-style
dispatcher reached only via `FUN_0006be18` — **whether this escalates to a DTC/motor-off or just
resyncs was NOT traced to closure this session**, flagged open) on ANY same-value mismatch between the
primary and shadow copy:

| pair | function | primary | shadow |
|---|---|---|---|
| aggregator sum | `FUN_0003aa2c` | `gp-0x6b94` | `gp-0x4ce0` |
| governor output | `FUN_0004503c` | `gp-0x6ace` | `gp-0x4cca` |
| governor sub-term A | `FUN_0004503c` | `gp-0x6934` | `gp-0x4c54` |
| governor sub-term B | `FUN_0004503c` | `gp-0x6946` | `gp-0x4c56` |
| governor sub-term C | `FUN_0004503c` | `gp-0x6948` | `gp-0x4c58` |
| post-governor comp | `FUN_000456a4` | `gp-0x6acc` | `gp-0x4cc8` |

⚠ The user's cross-session memory index refers to "4 shadow lockstep pairs ruled out as V40 candidates"
in a file I could not locate this session (`reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs.md`
is absent from both `.claude/agent-memory/firmware-codepath-tracer/` and the user auto-memory dir as of
2026-08-06) — I cannot confirm whether those four overlap with the six above. Treat the six above as a
**fresh, independently-derived census**, not a re-verification of the missing memory.

## FUN_00045a20 — a REAL, UNDEBOUNCED monitor, confirmed this session [EVIDENCE, fresh decompile]

```
fVar5 = gp-0x6a10(angle-tracking-error) * 0.1
fVar4 = LERP(fVar5; X=[350,410] Y=[5000,400], cal tp+0x7610..0x761c = 0xC6610..0xC661C) -> gp-0x6ab4
fVar7 = (fVar4 <= gp-0x6abe) ? -cal(tp+0x702c=0xC602C) - 0.001 : -0.001      ; lower bound
fVar3 = (gp-0x6abe <= -fVar4) ?  cal(tp+0x702c) + 0.001 :  0.001            ; upper bound
comp  = (gp-0x6acc - gp-0x6ace) / 1024                                     ; -> gp-0x6ad2, gp-0x68f6
if (comp > fVar3 || comp < fVar7):
    FUN_000462e6(0x3a09, comp, 0, fVar3, fVar7)   ; -> FUN_00016de6(0x1d, 0x3a09, 1, 1) EVERY TIME, no local debounce
```
`FUN_000462e6` unconditionally calls `FUN_00016de6(0x1d, param_1, 1, 1)` regardless of `param_1`'s value
(confirmed by decompile — the corridor-lockstep Monitor 2 call with code `0x3f1b` and this call with code
`0x3a09` both land on DTC index **0x1d**). Sole caller of `FUN_00045a20`: `FUN_0002214a` (the 1 kHz task).

`gp-0x6acc`/`gp-0x6ace` are the post-governor / pre-comp torque values (see aggregator section — both
descend from `gp-0x6b94`, which sums `gp-0x6bd0`). `gp-0x6abe` is the column/motor rate signal that
`reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain.md` already ties to `gp-0x6ac0` (FactorE's
own index) as "ONE signal, net different filtering" — **⇒ the SAME physical rate signal that gates the
damper's FactorE activation also gates this monitor's tolerance band width.** [BELIEF, structural
coincidence noted, causal link from damper magnitude to a comp-bound violation NOT numerically closed]

## Per-DTC hard-latch eligibility, byte-confirmed [EVIDENCE, raw read of stock code.bin]

`FUN_00018738`'s own trip-counter table lives at `tp-0x72a8 + idx*0x1c` (threshold at record-0x1a;
latch-eligibility bit-test reads `*(uint*)(record-0x1c+8)`, bit index from cal bytes `tp-0x58c0`
(=0xB9740, value **0**) and `tp-0x58bf` (=0xB9741, value **6**)):

| DTC idx | threshold (cycles) | flagword | bit0 test | bit6 test | hard-latch eligible? |
|---|---:|---|---|---|---|
| 0x1c (Monitor 1, shaper) | **1** | 0x3d01 | 1 | 0 | **YES, single-cycle** |
| 0x1d (Monitor 2 AND FUN_00045a20) | **1** | 0x3d01 | 1 | 0 | **YES, single-cycle** |
| 0x18 (cadence watchdog) | **1** | 0x3d01 | 1 | 0 | **YES, single-cycle** |
| 0x2f (FUN_00018738's own secondary log) | **1** | 0x2d01 | 1 | 0 | **YES, single-cycle** |
| 0x49 (torque-arb Counter B, V37-disabled) | 1 | **0x0** | **0** | 0 | **NO — structurally excluded** |
| 0x26 (`FUN_00070a98` delivery-consistency, not traced this session) | **3000** | 0x1c00 | 0 | 0 | not this path (bit0/6 both 0 at this record; may use a different bit or a different escalation route — not traced) |

**Threshold=1 means: once a caller's own internal debounce (Monitor 1's `gp-0x3564` int accumulator,
~10 cycles/0.1s; Monitor 2's `gp-0x3550` float accumulator, same ~0.1s) finally calls
`FUN_00016de6(idx,...)`, the outer latch fires on that VERY FIRST call — the ~0.1s figure already on
record for Monitors 1/2 is the ONLY debounce, not stacked with a second one.** For `FUN_00045a20`, which
has NO internal accumulator (calls `FUN_00016de6` every cycle its bound is violated), this means **the
very first bad cycle can latch the hard shutdown** — the fastest path to the V75 incident's "sudden,
complete, at-the-instant-of-launch" signature found this session.

**DTC 0x49's flagword is exactly 0x00000000 — cannot satisfy the bit-test at ANY bit position** —
independently confirms, from a completely different angle than the V37 handoff's on-car observation,
that DTC 0x49 (torque-arbitration Counter B) **cannot** reach this hard-latch path. Matches "LKAS drops,
base assist survives" being a DIFFERENT (softer) fault class.

## Related
[[reference_accord_consistency_monitor_hardshutdown]] (Monitor 1/2 structure — channel-3 claim corrected
above) · [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]] (the
damper's own headroom math) · [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]
(FactorC/E, gp-0x6ac0/gp-0x6abe) · [[reference_accord_below_gp6b98_foc_delivery_path_swept]] (downstream
of gp-0x6b98) · [[reference_accord_mixer_channels_independent_not_4x_replica]] (gp-0x6b4c LKAS lane, one
of the aggregator's inputs)

## Open items
1. `FUN_0006ce90`'s "channel 8" dispatcher's ultimate consequence (silent resync vs DTC escalation) — one
   more hop from the shadow-lockstep mismatch handler.
2. `FUN_00070a98` (DTC 0x26, commanded-vs-achieved delivery-consistency monitor, shrinking threshold) not
   decompiled this session — a strong candidate class per the task brief's own hint list, deferred.
3. Exact OBD-visible DTC number for internal index 0x1d (is it really `0xF00049`/`0x00F00049` as an older
   memory infers, or a distinct code? needs `FUN_00047d06` / the index-to-DTC binding table trace).
4. `gp-0x6762` mode byte and `DAT_fedf1008` hardware write in `FUN_00018f4a` — candidates for a harder
   (non-gain-collapse) motor disable, not chased.
5. Whether `0xC64B8` (DTC 0x49 gate) is still `0xFF` in the actual V75 built image (only grepped
   `build_v75_tva.py` for a re-touch — found none — did not byte-read the built image itself this
   session).
