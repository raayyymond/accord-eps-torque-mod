---
name: reference_accord_tq_channel_producer_chain_no_filter_1khz
description: "tq (CAN 0x18F/399 bytes0:1, STEER_TORQUE_SENSOR) = -(gp-0x4f60*125/128); gp-0x4f60's producer FUN_0007f3f8 runs at task-1's 1kHz (unconditional dispatch, state-gated on gp-0x67fa in {4,5,8,10,11} which covers both road-reachable states {4,11}) and is FULLY MEMORYLESS -- no IIR/EMA anywhere in the chain. CAN 399 broadcasts at a measured 100.000Hz (Nyquist 50Hz), ZOH envelope <2% by 16Hz, <5% by 26Hz. The kit's 13-16Hz |Z| roll-off is NOT reproduced by this channel and is NOT explained by tq's firmware path."
metadata:
  type: reference
---

# tq's full producer chain is traced, timed, and contains NO filter — the 13-16 Hz |Z| roll-off is not here

2026-08-22, `tq-lowpass` subagent task. Ghidra `code.bin` (stock), decompile+disasm, cross-checked
against `rlog-tools/v86_probe_consolidate.py`'s PROV dict and `extract_ra4.py`/`r95_c_oscillation.py`.

## The chain, address by address [EVIDENCE — Ghidra decompile + disasm, code.bin stock]

CAN 0x18F(399) packer `FUN_00055c42`:
```
0x55c50  ld.h  -0x4f60[gp],r9      ; load torque cell
0x55c54  mulhi 0x7d,r9,r6          ; r6 = gp-0x4f60 * 125
0x55c58  sar   0x7,r6              ; r6 >>= 7          => Q7, scale 125/128 = 0.9765625
0x55c5a  subr  r0,r6               ; r6 = -r6  (SIGNED negate, NOT abs/rectify)
0x55c5e  jarl  0x218be,lp          ; write STEER_TORQUE_SENSOR bytes0:1
0x55c62  ld.h  -0x6a56[gp],r6      ; STEER_ANGLE_RATE, SAME frame, SAME 100Hz cadence
0x55c6a  jarl  0x218de,lp
0x55d5a  jarl  0x57b24,lp          ; checksum/counter helper, args (buf, 7, msgid=0x18F/399)
```
⇒ `tq` (as read by every rlog-tools extractor — `v86_probe_consolidate.py`'s PROV dict: *"raw CAN
0x18F(399) bytes0:1 x -1 == STEER_TORQUE_SENSOR negated... FUN_00055c42 @0x55c50"*) is this value,
unmodified between `gp-0x4f60` and the wire except the static Q7 scale and sign flip. **Not rectified**
— contrast CAN 427's `|cell|>>shift` (`accord-band-envelope-is-rectified-not-analytic`). STEER_ANGLE_RATE
(a candidate `Omega_w`/rate term) is bit-synchronous with `tq` — same frame, same instant, same task.

Producer `FUN_0007f3f8` (0xd arg = sensor-channel index via caller `FUN_0006bb08`):
raw dual-Hall/quadrature delta (`gp-0x5060..0x507c`, RAM shadow of an ADC/timer-capture read, NOT typed
by Ghidra — old memory's "ENCA0 struct decompile failure" did not recur this session, clean decompile) →
`FUN_0006af38` (**CORDIC atan2**, 8-iteration shift-add + quadrant fixup off a `tp-0x2c5e/0x2c60/0x2c64`
lookup table — confirmed MEMORYLESS: 3 scalar inputs, 1 scalar output, no persisted state) → per-sensor
gain `gp-0x25d4[idx]` (Q10, `>>10`) → `FUN_0007f300` phase nudge → rate-of-change **fault gate**
(`gp-0x4f56` threshold against the OLD `gp-0x4f60` — a plausibility DETECTOR, not a blend/smoother; on
the pass path the fresh value proceeds unmodified) → learned gain `gp-0x698c` / learned offset `gp-0x6b50`
(Q10, cal-gated `tp+0x74c3`) → symmetric saturating clamp `gp-0x4f54` → store `gp-0x4f60` (dual-store
safety pattern, `FUN_0006b9ee` resync on mismatch — a RAM-protection idiom, not filtering).

**No step feeds gp-0x4f60's own PRIOR output back into the computation of its NEW value.** The only read
of the old value is the fault-gate comparison; the diagnostic-monitor boilerplate wrapping the whole
function (`FUN_0005bb04`/`FUN_0005ae6a`/`FUN_0005afba`-style blocks, ~2/3 of the function body) is DTC
debounce-counter bookkeeping, unrelated to the signal's arithmetic.

`FUN_0007f300` disasm-confirmed **pure bounded ADD, not a filter**:
```
0x7f300  ld.h  -0x6b66[gp],r15
0x7f304  addi  0x134,r15,r14       ; r14 = r15 + 308
0x7f308  addi  -0x269,r14,r0       ; range test vs 617 (flags only)
0x7f30c  bc    0x7f312             ; in-range branch
0x7f30e  add   r15,r6              ; y = x + r15               (|r15| <= 308 case)
...      [out-of-range: y = x +- 0x134]                        (clamped case)
```
i.e. `y = x + clamp(gp-0x6b66, -308, +308)`. No feedback, no memory of its own past output — despite the
name "phase correction," it is a static per-sample additive nudge from an externally-tracked cal cell.

## Rate [EVIDENCE — call-graph + on-car, two convergent methods]

`FUN_0002214a` (task 1) → `FUN_0006bb08(3,uVar2)` **UNCONDITIONAL call, no enclosing `if`** →
`FUN_0007f3f8(0xd)` gated on `(uVar2 & 0xd30) != 0` where `uVar2 = 1 << (gp-0x67fa & 0xf)` — the
STATE-MASK idiom (a set-membership test on the assist SM's state nibble), **not a rate divider**.
`0xd30` = states `{4,5,8,10,11}`. `accord-state4-cadence-refuted-state-is-sticky.md` independently
establishes the ONLY states reachable on a normal drive are `{4, 11}` — **both inside `0xd30`.**
⇒ fires every task-1 tick, gaplessly, for the entire duration of any normal engaged drive.

Task 1 = **1000 Hz** is an ON-CAR MEASUREMENT (`STEER_STATUS=4` dwell, cal `0xC64DF`=100 counts measured
at 100.00 ms) — independent of the retracted PCLK/OSTM0 derivation chain
(`accord-task5-is-100hz-damper-cannot-damp-21hz.md`'s clock audit). See
[[control-task-tick-confirmed-1khz]]. CAN 399 itself wire-fitted at exactly **100.000 Hz** (3 independent
methods, `accord-can-tx-100hz-base-tick-and-gateway.md`) = 1000/10, self-consistent.
🛑 The brief that spawned this trace worried about task 5's unresolved rate — **moot for this signal**:
`gp-0x4f60`'s producer runs in task 1, not task 5, whose own rate is independently pinned.

## Verdict: the roll-off is NOT in this channel [EVIDENCE for the negative]

Sole frequency-dependent element found anywhere in the chain = the 100 Hz broadcast's sample/hold
envelope: `|H(f)| = |sinc(f/100)|`. At 12/14/16 Hz: **0.9765 / 0.9681 / 0.9584** — a **1.9% drop**
12→16 Hz, and only ~11% down at 26 Hz. Measured (`accord-column-cannot-host-q10-at-8hz.md`'s STOCK
`|Z|/w`): **1.33 / 1.15 / 0.45** — a **66% drop** 12→16 Hz, **~35× steeper** than predicted.
**`tq`'s firmware path (production + packing + broadcast) cannot produce this roll-off.** 26 Hz sits at
52% of the channel's 50 Hz Nyquist — no aliasing risk for the kit's 21–26 Hz band from this channel.
If the roll-off is real, it is either in the OTHER channel of the ratio (`Omega_w`/rate term — NOT
traced this session), the spectral estimator itself, or genuinely mechanical.

## Open / not fully closed [BELIEF, judged low materiality — not chased further this session]

- `gp-0x6b66` writers (`FUN_00048a40`@0x48fb2 real-value store, `FUN_000490ac`@0x490e0 zero-reset) and
  the learned gain/offset `gp-0x698c`/`gp-0x6b50` — their OWN update-rate/mechanism not traced. Bounded
  to ±308 ct and structurally additive/multiplicative-static from `gp-0x4f60`'s own frame, so even a slow
  external update cannot by itself synthesize a 13–16 Hz corner inside THIS function.
- SVD (`UPD70F3508_V850E2Px4.svd`) documents a real DNF (Digital Noise Filter) block in front of the
  ENCA0/ENCA1 encoder-timer inputs (`DNFA28CTL`+family, peripheral base `0xFF410000`, reset value
  `0x00` = OFF). Whether firmware enables a nonzero filter width on the torque sensor's specific input
  pair (vs. the motor resolver's) was NOT byte-verified — absolute MMIO writes need a movhi/movea
  constant scan, not a gp/tp-relative one. BELIEF: DNF blocks on encoder/timer captures are
  conventionally sized for microsecond-scale deglitch, architecturally implausible as a 13–16 Hz source,
  but this is inference, not an instruction-level read.
- Whether the kit's estimator (`rlog-tools/plant_phase_corner.py` et al.) analyzes tq/rate on a shared
  100 Hz grid (no roll-off predicted within Nyquist at all) or against a faster/differently-sampled
  partner (the ZOH model above) was not checked this session — read the estimator before trusting either
  envelope as the counterfactual.

Related: [[accord-column-cannot-host-q10-at-8hz]], [[control-task-tick-confirmed-1khz]],
[[reference-accord-gp4f60-is-sensor-b-column-torque]], [[reference-accord-can-tx-architecture-new-id]],
[[accord-state4-cadence-refuted-state-is-sticky]], [[accord-task5-is-100hz-damper-cannot-damp-21hz]]
