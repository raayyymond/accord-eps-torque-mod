# ★★ `gp-0x6ad4` / `FUN_0003a382` — and why `0xC6AF0` is a COMPLETE, branch-agnostic kill

**Verified 2026-07-28** in GhidraMCP on stock `code.bin`, twice independently (lead's pcode dataflow
walk + a subagent's raw register/instruction trace), plus little-endian byte reads of every constant.

## The lane

`FUN_0003a382` → `gp-0x6ad4`, summed into the aggregator `FUN_0003aa2c`, range-gated **±0x2800
(±10240 = the FULL aggregator range)** at `0x3aca8`/`0x3acbc-c4`. Three **parallel** branches:

```python
stage_A = ((x - bias) * lerpA(motor_rate)) >> 10   # 0xC6450 EMA alpha = 1024/1024 -> EXACT IDENTITY
stage_C = ((x[n] - x[n-1]) * uVar12) >> 10         # 0xC644A alpha = 1024/1024 -> EXACT IDENTITY
                                                   #   ...but this branch is a DISCRETE DERIVATIVE
accum  += (x * uVar16) >> 10                       # clamped/anti-windup accumulator
combined = (stage_C + accum + stage_A) >> 5
combined = (combined * uVar27) >> 10               # uVar27 = 1024 -> no-op
```

- `0xC6450` and `0xC644A` are **1024/1024 = algebraic identities — zero lag, not merely fast.**
- Stage C's `2*sin(w/2)` shape **rises ~21× from 1 Hz to 21 Hz**, which would tilt the spectrum; the
  measured transfer is flat, so Stage C is not what dominates. Stage A's LERP gain is **153-256/1024 =
  0.15-0.25**, which brackets the measured 0.19-0.22.
- Input is `gp-0x4f60` at **unity** (Q0), with only a slow hysteresis bias — **no Q15 haircut**, unlike
  `FUN_00036682`.

🛑 **`gp-0x6ad4` is NOT LKAS-gated.** Its ceiling chain is gated by `gp-0x67fe`, the EPS's own **FOC/assist
substate** (`gp-0x6772 == 5 → 2`), which V31P telemetry measured at **1 in 100% of frames including
disengaged stretches** — it means "the motor drive is running", i.e. power steering is on, all ignition
cycle. **The lane is live during manual driving, so muting it changes manual feel.** A subagent labelled
this an "engagement gate"; that is wrong. See [[eps-gp67fe-trump-engaged-holding-substate]].

## Why the `0xC6AF0` mute is a complete kill

The LERP result becomes a **Q15 multiplier on the ceiling that clamps the FINAL combined value**:

```python
lerp_y  = authority_lerp(u16le(img, 0xFEDF8000 - 0x6966))  #        @0x3a632/0x3a636
r15     = lerp_y if authority <= 0x8000 else 0x8000        # cmovnh @0x3a794
ceiling = (headroom * r15) >> 15                           # mul;sar 0xf @0x3a79e/0x3a7aa

def store(combined, ceiling):        # @0x3a88c-0x3a8a0
    if combined > ceiling:  return ceiling          # cmp r10,r14 ; bgt
    if -ceiling <= combined: return combined        # subr ; cmp ; cmovle
    return -ceiling
# ceiling == 0  =>  EVERY path returns 0  =>  st.h 0,-0x6ad4[gp]
```

⇒ **Muting zeroes the lane regardless of which branch dominates.** `r10` is never redefined between
`0x3a7aa` and `0x3a88c` (checked both by pcode def-use and by an explicit destination scan of all 477
bytes). This is why the mute is **not** a fourth try at V43/V46/V48A — those each attenuated **one of
three parallel branches** (`0xC644A`→64 = −7.1 dB; `0xC6450`→32 = −12.6 dB; one carrier muted) and each
was null, exactly as you'd predict for a three-branch lane filtered one branch at a time.

**Mute both Y[0] and Y[1]:** `bh` at `0x3a648` sends authority *exactly 0* down the below-knot path
(loads Y[0] at `0xC6AFC`), while 1..3276 interpolates Y[0]→Y[1]. V54 measured `gp-0x6966` ∈ **[0,127]**,
which straddles that boundary. Addresses are `0xC6AFC`/`0xC6AFE` — see
[[accord-lerp-tables-count-word-first]].

⚠ **Escape hatch:** `cmovnh` @`0x3a794` bypasses the LERP and forces unity if `gp-0x6966 > 32768`.
Not live (V54 measured ≤127; V31's boost floor makes wind-up unreachable), but it exists.

## GATE 2 status
- ✅ **Monitor divergence CLOSED** — `gp-0x6ad4` has exactly **2** true gp-relative accesses image-wide:
  writer `0x3a8a0` (plain `st.h`, no compare-and-fault) and reader `0x3aca8`. No lockstep/shadow/mirror,
  no monitor. That is the V27/V48B brick mechanism and it does not apply.
- ✅ **Protection removal CLOSED** — the derate arms Y[2..4] are never invoked (V54: authority pinned in
  the first flat segment, 5,989/5,989).
- 🛑 **Damping sign at 21 Hz OPEN** — undetermined; closed-loop ID with no external excitation cannot
  separate plant from controller. If the lane is net-damping, muting makes the vibration worse.
- 🛑 **Manual steering feel OPEN** — see the not-LKAS-gated note above. V52C is the precedent (null for
  the vibration, but it did change manual feel).

⇒ V56 is a **reversible experiment**, not a known-good fix. Revert = reflash V55.
See [[project-v56-c6af0-mute-built]], [[reference-accord-v55-flashed-oscillation-is-internal]].
