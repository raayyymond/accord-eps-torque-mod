---
name: reference_accord_fb_filter_floor_bias_is_32_counts_of_phantom_error
description: "The LKAS fb-lag filter's two `sar 0xa` floors each lose 0.5 LSB/tick and the state integrates it, so the feedback signal carries a CONSTANT DC OFFSET of -2*2*0.5*1024/(1024-a) counts at EVERY amplitude -- -32 on V291 (a=962), -20 on V282 (a=923). Against E = 32*sp - fb that is +32 counts of PHANTOM ERROR, one whole extra setpoint count, forever. This, not the 1.07-count quantum, is the mechanism behind ADV-V291-B's B4 failure, and it is why a LOWER pole costs more: the bias scales as 1/(1024-a)."
metadata:
  type: reference
---

Measured 2026-09-13 by subagent `cavedesign` while designing the V292 error-feedback cave.
Mirror: `rlog-tools/studies/grind/v292_cave_mirror.py`. Design: `docs/specs/design/DESIGN-V292-FBLP-CAVE-2026-09-13.md`.

## The finding

`FUN_00028ea6` @ `0x28F8E-0x28FA8` computes `s_new = (a*s >> 10) + (b*x >> 10)` with **two separate
`sar 0xa`**, each flooring toward -inf. Each floor loses **0.5 LSB per tick on average**. The state
integrates that loss:

```
bias(s) = 0.5 * 1024/(1024 - a)  per term,  x2 terms
bias(out) = 2 * bias(s)          because `out` is the TWO-SAMPLE SUM s_old + s_new
         = 2 * 2 * 0.5 * 1024/(1024 - a)
```

| build | a | predicted bias | MEASURED (20.3 Hz sine, integer filter minus exact linear filter, 20k ticks) |
|---|---|---|---|
| V282 | 923 | -20.3 counts | (not re-run) |
| V291 (C10) | 962 | -33.0 counts | **-32.67 / -31.21 / -32.24 / -32.93 / -32.44** at A = 1, 3, 8, 64, 512 |

🛑 **It is CONSTANT in amplitude.** Not a small-signal effect that washes out when the wheel moves --
the same -32 counts at A = 512 as at A = 1. What changes with amplitude is only its *relative* size.

## Why it matters more than the "quantum" framing

`ADV-V291-B` §5.2/§11.4 attributed the B4 failure to the input quantum widening from 0.66 to 1.07 raw
counts. That is true but is the smaller half of the story. The error is formed at `0x29D78` as
`E = 32*sp - r26`, so a **-32 offset in `fb` is +32 counts added to E -- exactly one extra setpoint
count, permanently.** At `sp = 3` (E = 96 nominal) that is +33 % of demand. Byte-exact closed loop on
design290b's family median fit: `sp = 3` gives V291/V282 = **x1.4155**, inside the adversary's
x1.34-1.80 band; error feedback takes it to **x1.00000**.

⇒ **The bias scales as `1/(1024-a)`, so EVERY future pole-lowering build pays it, and pays more.**
A 2 Hz pole (a = 1011) would carry `2*2*0.5*1024/13` = **-157 counts** = ~5 setpoint counts of phantom
demand. Price this before proposing any lower pole.

## The fix, and the identity that makes it cheap

Carry each floor's residue into the next tick (first-order error feedback, V289's device):
`t = mul + rem ; step = t sar 10 ; rem = t & 0x3FF`.

🛑 **`t & 0x3FF` IS `t - ((t >> 10) << 10)` EXACTLY, for two's-complement `t` of either sign**, because
arithmetic shift right satisfies `t == ((t>>k)<<k) + (t & (2**k - 1))`. Check: `t = -1025` -> `sar 10`
= -2, `-2<<10` = -2048, `t-(-2048)` = 1023; and `(-1025) & 0x3FF` = `0xFFFFFBFF & 0x3FF` = 1023. ✔
**One `andi imm16` (4 B) replaces `mov`/`shl`/`sub` (6 B)** -- this is what fits the V292 cave in 52 bytes.

Proven by telescoping: `step_b[n] = (b*x[n] + rem[n-1] - rem[n])/1024`, so the mean is exact and the
quantisation error is `(1 - z^-1)`-shaped -- **zero DC, bounded by 1 LSB per term**.

**EXHAUSTIVE result**: over the whole unclamped range `x = -1491..1491` (2,982 amplitudes, both signs),
`mean(out)/x - 2b/(1024-a)` is **EXACTLY ZERO**. Above `|x| = 1491` the pre-existing `+-[0xC62E6]`
= 46080 output clamp binds and both builds sit on the rail identically -- a first run reported that as
a "FAIL" before it was diagnosed.

## Two side-effects worth knowing

1. **The `s = -1` absorbing state is released.** `floor(-a/1024) = -1` for every `a < 1024`, so on
   stock/V282/V291 a small negative state NEVER returns to zero. Measured: V291 from `s0 = -500`,
   `x = 0` sticks at **-16 forever**; with error feedback it reaches exactly 0 in **110 ticks**.
2. **V291's `0x14A` bit 3 publishes `sign(gp-0x3d30)`** (the repoint at `0xC4BAA`, `81 c9` -> `d1 c2`,
   is 2 of V291's 15 non-V282 bytes). So the absorbing state is ALREADY ON THE WIRE: idle bit-3 duty
   measured over 400 stop phases is **0.517-1.000 on V291 and 0.000 with error feedback**, at every
   oscillation amplitude 1..64. A free, pre-registered, zero-cost positive control for any build that
   changes this quantiser.

Related: [[accord-fb-lag-filter-bytes-and-gate1-private]],
[[accord-fb-filter-sentinel-reset-runs-disengaged-and-deadzone]],
[[reference_accord_0x28f8e_zero_liveness_hook_in_the_fb_filter]].
