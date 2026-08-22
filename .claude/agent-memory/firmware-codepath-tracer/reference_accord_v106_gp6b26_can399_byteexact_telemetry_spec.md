---
name: reference_accord_v106_gp6b26_can399_byteexact_telemetry_spec
description: Byte-exact cave-stub spec putting gp-0x6b26 (the acceleration-damping term, V106's lever, hard-clamped by Honda to exactly +-511) onto CAN 399/0x18F's 10 free bits with ZERO quantization loss -- 9-bit magnitude + 1 sign fits the confirmed +-511 clamp exactly. Full-function register-liveness trace (not a spot-check) finds r9/r11-r16 all dead-in at the 0x55D50 hook. Also documents the FUN_00055c42 dispatch mechanism (indirect via a function-pointer table at 0xB72AC, zero literal jarl callers) and the resulting open timing-alignment question.
metadata:
  type: reference
---

# gp-0x6b26 -> CAN 399/0x18F byte-exact telemetry spec (2026-08-22, `deadband` session, V106 critical path)

Supersedes the gp-0x6ada payload plan in [[reference_accord_can399_0x18f_10bit_telemetry_channel_and_6ada_gate1]]
for the SAME `0x18F` slot -- team-lead re-spec'd the payload mid-session once V106's actual lever (raising
`gp-0x6b26` x1.5->x3.0) was identified as reaching both symptoms. That file's hook-site/register/byte-map
work for `0x18F` itself is unaffected and this file reuses it; only the PAYLOAD differs.

## The clamp -- confirmed first-hand, exact match to team-lead's claim

`read_memory(0xC407E)` = `ff 01` LE = **511**. Fresh `disassemble_bytes(0x36cb0,0x36cf0)` (inside
`FUN_00036c12`, `gp-0x6b26`'s producer):
```
0x36cca  sar 0x12,r6                              ; pre-clamp scaled value
0x36ccc  cmp r16,r6 / ble 0x36cd6                  ; upper-bound test
0x36cd0  ld.h 0x507e,tp,r6   ; = cal(0xC407E) = 511   <- POSITIVE CLAMP  (tp+0x507e = 0xBF000+0x507E = 0xC407E)
0x36cd6  subr r0,r16 / cmp r16,r6 / bge 0x36ce4    ; lower-bound test
0x36cdc  ld.h 0x507e,tp,r13
0x36ce0  mov r0,r6 / sub r13,r6                    ; r6 = -511                <- NEGATIVE CLAMP
0x36ce4  ld.h -0x6b26,gp,r9                        ; shadow-lockstep readback follows
```
`|gp-0x6b26| in [0,511]` = exactly 9 bits, +1 sign = exactly 10 bits, zero slack, **no quantizer needed** --
unlike the `gp-0x6ada`/MODEL payloads which both needed a shift-based quantizer against a wider range.

## Bit layout, round-trip verified in Python across edge cases (0, 511, 255, powers of 2, all pass)

```
byte4 bits[2:0]  = mag bits[2:0]
byte5 bits[7:6]  = mag bits[4:3]
byte5 bits[3:0]  = mag bits[8:5]
byte6 bit[6]     = sign (1=negative, 0=positive/zero)
```
Decode: `mag = ((byte5&0x0F)<<5) | (((byte5>>6)&0x3)<<3) | (byte4&0x7)`; `sign=(byte6>>6)&1`;
`value = -mag if sign else mag`.

## Register discipline -- full-function trace, not a spot-check

Fresh `disassemble_function(0x55c42)`, all 60 instructions read start to finish (not just the local window
around the hook). Hook `0x55D50` (`movea -0x1420,gp,r6`) sits inside critical section #7 (`jarl 0x1fa42,lp`
@`0x55D4C` / `jarl 0x1fa72,lp` @`0x55D70`), which also covers the checksum call and the post-checksum
byte6[3:0] nibble write. **`r9, r11, r12, r13, r14, r15, r16` confirmed dead-in at `0x55D50`, never read
again anywhere in the function including the tail after the checksum call.** `r6/r7/r8/r10` all get
overwritten with fixed values (buffer base/DLC=7/ID=0x18F/checksum result) regardless of their value going
into the hook, so a stub only needs to leave `r6=gp-0x1420` on exit. Caveat carried from this kit's own
precedent: manual disassembly read, not `analyze_dataflow`/pcode-verified.

## Cave stub, ~82 bytes, mnemonic-level (NOT hand-encoded machine code -- needs real assembly before cutting)

```
ld.h  -0x6b26[gp],r9
mov   0,r14
cmp   r0,r9
bge   +6
subr  r0,r9
mov   1,r14
ld.bu -0x141c[gp],r11
andi  0xf8,r11,r11
mov   r9,r12
andi  0x7,r12,r12
or    r12,r11
st.b  r11,-0x141c[gp]
mov   r9,r13
shr   0x3,r13
ld.bu -0x141b[gp],r15
mov   r13,r16
andi  0x3,r16,r16
shl   0x6,r16
andi  0x3f,r15,r15
or    r16,r15
mov   r13,r12
shr   0x2,r12
andi  0xf,r12,r12
or    r12,r15
st.b  r15,-0x141b[gp]
ld.bu -0x141a[gp],r16
andi  0xbf,r16,r16
mov   r14,r15
shl   0x6,r15
or    r15,r16
st.b  r16,-0x141a[gp]
movea -0x1420,gp,r6
jmp   [lp]
```

## 🛑 Open item -- `FUN_00055c42` dispatch timing not resolved, matters only for phase/coherence use

`gp-0x6b26` updates at 1kHz (`get_function_callers(0x36c12)` = `FUN_0002214a`, the already-confirmed 1kHz
dispatcher). `FUN_00055c42` (the 399 packer) has **zero literal `jarl` callers** -- confirmed two ways this
session (`get_function_callers` returns null; LE32-literal scan finds its address at `0xB72D0`, a
function-pointer table entry). It is dispatched indirectly via `FUN_0001d68e` reading Table B
(`0xB72AC`, per [[reference-accord-can-tx-segmentb-scheduler-descriptor-table]], an older r2-era memory
this session's Ghidra findings independently corroborate). **Whether that indirect dispatch runs at a
fixed phase relative to the 1kHz loop, or with jitter, is unresolved** -- open question #3 in that same
2026-07-07 memory, not closed this session either; would need `FUN_0001d68e`'s 3 callers (`0x1d904`,
`0x1db32`, `0x1dc8e`) walked to their roots. **Does not affect dose-verification or clamp-duty use**
(amplitude/distribution statistics, insensitive to a fixed or sub-Nyquist-jitter timing offset) --
**does affect any phase/coherence estimate against a reference channel**, which should be treated as
provisional until this is closed.

## 🛑 Clamp-duty bias at 100Hz vs true 1kHz duty -- SIMULATED, not just reasoned, per team-lead's follow-up ask

Question: is `duty_100Hz(|gp-0x6b26|==511)` an unbiased estimate of the true 1kHz duty, given `gp-0x6b26`
updates at 1kHz and the CAN packer point-samples it at 100Hz? **Answer: unbiased in aggregate over a
multi-cycle capture; the real cost is VARIANCE on short fragments, not bias.**

Synthetic `A*sin(2*pi*21.73*t+phi)` clamped at +-511 (A solved for true duty~=12.8% as a test point),
1kHz truth grid vs 100Hz point-decimation, 400 random phases, three window lengths:
```
window   cycles  CAN samples  true duty(mean+-std)   100Hz-decimated duty(mean+-std, range)   bias
10.0s    ~217    1000         0.12828+-0.0002         0.12808+-0.0018 (0.125-0.131)            -0.15% rel
1.0s     ~22     100          0.12839+-0.0027         0.12832+-0.0050 (0.120-0.140)             -0.05% rel
0.2s     ~4.3    20           0.12840+-0.0082         0.12750+-0.0275 (0.050-0.150)             -0.7% (noisy)
```
Bias not distinguishable from zero at any window length tested, even down to 20 samples. Mechanism:
100Hz/21.73Hz = 4.60 samples/cycle, a non-integer ratio, so the sampling phase relative to the oscillation
rotates cycle-to-cycle instead of staying fixed -- a short excursion missed on one cycle is caught (and
over-weighted by exactly the compensating amount) on another, washing out in expectation. **This holds
regardless of whether `FUN_00055c42`'s dispatch timing (see open item above) is fixed or jittery** -- the
phase that matters for THIS question is oscillation-vs-sampler, set by real-world driving, not ECU task
scheduling. Does NOT resolve the separate coherence/phase-vs-reference-channel open item above, which needs
a fixed inter-channel latency, not just oscillation-vs-sampler randomness.
**Practical guidance**: score duty against a multi-second capture or several pooled bursts (std ~1-4%
relative there); do not trust an isolated short-burst-fragment duty number (can read 40% low to 15% high of
true value from sampling noise alone in the 20-sample case) -- same failure mode as
`feedback-episodes-not-windows`, now quantified for this specific channel/question. Band-power/RMS
statistics are unaffected (ordinary sub-Nyquist ZOH, no special-casing needed).

## Related
[[reference_accord_can399_0x18f_10bit_telemetry_channel_and_6ada_gate1]] -- the hook-site/byte-map/GATE-1
work for `0x18F` this file reuses; that file's ORIGINAL payload (`gp-0x6ada`) was superseded by this one.
[[reference-accord-can-tx-segmentb-scheduler-descriptor-table]] -- source of the Table-B dispatch mechanism
and the unresolved timing open question.
