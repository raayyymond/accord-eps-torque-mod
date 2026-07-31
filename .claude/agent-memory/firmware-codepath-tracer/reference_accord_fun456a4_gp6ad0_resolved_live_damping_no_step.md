---
name: reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step
description: Resolves the golden model's gp-0x6ad0 self-contradiction -- the CELL is write-only (zero readers, 5 methods) yet the VALUE is live, because st.h r6 and add r6,r12 use the same register. FUN_000456a4 is a continuous viscous DAMPER (deadband + linear ramp + ceiling), NOT a 0->2560 chattering comparator; that premise is FALSIFIED. Reaches gp-0x6b98 via gp-0x6acc -> FUN_00042af8. 13 cal cells dumped, all with zero consumers elsewhere.
metadata:
  type: reference
---

# `FUN_000456a4` / `gp-0x6ad0` / `gp-0x6a10` — fully resolved (2026-07-30, stock `code.bin`)

## 1. The "self-contradiction" is not one — both halves are TRUE [VERIFIED @0x458C4]

Byte-decoded, consecutive instructions:
```
0x458C4:  64 37 30 95    st.h  r6, -0x6ad0[gp]     <- telemetry mirror, NEVER read back
0x458C8:  c6 61          add   r6, r12             <- r12 = gp-0x6ace + r6   (SAME register)
0x45932/0x45942:         st.h  -> gp-0x6acc        (+ lockstep shadow gp-0x4cc8)
```
`gp-0x6ad0` has **exactly ONE access image-wide** — that single store. Zero readers under **five**
methods: disp16 (per-opcode rules), disp23 extended, LE32 literal, movhi/movea, and
`movea disp,gp,rX` address-take. Also checked: no 32-bit access at `gp-0x6ad2` could straddle it.

**So: the CELL is inert telemetry AND the QUANTITY is live.** Patching the memory cell does nothing;
the computation is what matters. The golden model's `motor_torque_governor()` is right that
`gp-0x6acc = gp-0x6ace + <term>` and right that `gp-0x6ad0` has no readers — it just misdescribes the
mechanism as a memory read.

## 2. It DOES reach the motor command [VERIFIED]

`gp-0x6acc` readers: `0x431C4` -> **`FUN_00042af8` (body `0x42af8-0x43e43`) — the shaper that produces
`gp-0x6b98`**; `0x4467A` -> `FUN_00043e44`; `0x45B16` -> `FUN_00045a20` (monitor).
Task order inside `FUN_0002214a`: `FUN_000456a4` @`0x22984` runs BEFORE `FUN_00042af8` @`0x229ce`, same
tick. Both gated on `r23 = phase & 0xD30` = **5/16 phases {4,5,8,10,11}** — the same mask as
`FUN_00041464`.

## 3. 🛑 The "0 -> 2560 one-cycle step" premise is FALSIFIED [VERIFIED]

Exact integer mirror (`0x45716-0x458C8`):
```python
thr = LERP1(gp_6a10)                                   # 0x45716..
if not (thr < gp_6ac0):        comp = 0                # 0x45780  THE GATE
else:
    exc = ((gp_6ac0 - thr) & 0xFFFF) * 3072 >> 10      # 0x457a4  gain 0xC6204 = 3072/1024 = 3.000
    comp = min(exc, LERP2(gp_6a10))                    # 0x45886  ceiling
    if gp_6abe > 0: comp = -comp                       # 0x458A6 ld.h -0x6abe / cmp r0,r16 / ble
```
At the gate `gp_6ac0 == thr` the excess is **0**, so the output is **0**. Measured through the gate
(idx=4150, thr=1000): `999->0, 1000->0, 1001->+3, 1002->+6, 1005->+15, 1100->+300`. **The transfer is
piecewise-linear and CONTINUOUS — a deadband + ramp + ceiling, i.e. a textbook viscous damper with a
dead zone. There is no discontinuity to chatter.** The 2560 ceiling is only reached 853 counts above
threshold. The sign discontinuity at `gp-0x6abe == 0` is masked because `gp-0x6ac0 = |gp-0x6abe| ~ 0`
there, which is below any positive threshold.

Sign is `-sign(gp-0x6abe)` => it **opposes** motor rotation => **damping**, and per
[[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]] the net phase vs true velocity at
21 Hz is -40.4 deg (cos +0.76), so it damps rather than injects.

## 4. Why it is almost certainly INACTIVE during the creep grinding [VERIFIED thresholds]

`gp-0x6ac0` full scale is 13000 (the upstream clamp). Threshold table:

| `gp-0x6a10` | thr (LERP1) | ceil (LERP2) | \|rate\| to reach ceiling | % of full scale |
|---|---|---|---|---|
| <=3800 | 5000 | 512 | 5171 | 39.8% |
| 4000 | 3037 | 1901 | 3671 | 28.2% |
| >=4150 | 1000 | 2560 | 1854 | 14.3% |

The grinding is **creep-only with 9 deg of steering and effort 205** — motor rate is small, so
`gp-0x6ac0` sits far below even the most permissive 1000-count threshold. **The gate is shut and
`comp == 0` under exactly the conditions where the grinding occurs.** [INFERRED from the operating
point — the absolute counts of `gp-0x6ac0` during the event are UNMEASURED.]

## 5. Cal cells (byte-read LE, stock) — all 13 have zero consumers outside `FUN_000456a4`

Format is `[count][X0 X1 X2][Y0 Y1 Y2]`:
```
0xC6830: 0003  0ED8 0FA0 1036  1388 0BDD 03E8   LERP1 X=[3800,4000,4150] Y=[5000,3037,1000]
0xC67D0: 0003  0C80 0ED8 1036  0200 0400 0A00   LERP2 X=[3200,3800,4150] Y=[512,1024,2560]
0xC6204: 0C00 = 3072  (gain, /1024 = 3.000 exact)
```
X row base `0xC6832` / Y row base `0xC6838`; X row base `0xC67D2` / Y row base `0xC67D8`.
(tp=0xBF000: `tp+0x7832`=`0xC6832`, `tp+0x77d2`=`0xC67D2`, `tp+0x7204`=`0xC6204`. Anchor check
`tp+0x746c`=`0xC646C` OK.) Still the cleanest isolated patch surface found — but see section 3/4:
there is no chatter here to fix.

## 6. `gp-0x6a10` — the LERP index [VERIFIED producer, scale OPEN]

Sole producer `FUN_0003fc16` (`0x3fc16-0x3fd8d`), 3 writers total (`0x3E852` st.h r0, `0x3FCA4` st.h r10,
`0x3FD3E` st.h r0 — two are store-zero, invisible to a naive scan):
```python
gp_6a02 = gp_69ca - bias(cal tp+0x733a, enabled by tp+0x74a8)   # 0x3fcXX
gp_6a10 = min(abs(gp_6a02), LIMIT)      # FUN_00049a5a = abs, FUN_00049a78 = min
# forced to 0 unless gp-0x67fe in {1,2} (assist active)
```
**[OPEN]** `gp-0x69ca`'s physical identity and hence `gp-0x6a10`'s units. The LERP breakpoints
3200/3800/4000/4150 are suspiciously voltage-like (/256 => 12.5/14.8/15.6/16.2 V) but that is a GUESS,
not evidence — `gp-0x6a10` is built by `abs()` of a difference, which does not read like a bus voltage.
Resolving `gp-0x69ca` would settle which row of the table the car actually operates on.

## Related
[[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]] — where `gp-0x6abe`/`gp-0x6ac0` come from.
[[reference-accord-post-governor-comp-add]] / [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]
— the earlier partial reads this supersedes on the step/chatter question.
