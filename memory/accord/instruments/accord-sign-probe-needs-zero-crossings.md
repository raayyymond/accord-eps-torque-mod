# 🛑 A 1-bit SIGN probe is a phase probe only for a signal that crosses zero at that frequency

**Type:** feedback / reference · **Learned:** V58's headline measurement returned nothing, 2026-07-30

## What happened
V58's primary result was `bit6 = (gp-0x6bbe < 0)`, intended to give the damping phase by cross-spectrum
against the bus angle-rate at 20–25 Hz. It returned **nothing**, and the reason is structural, not
statistical:

```
gp-0x6bbe sign transitions, route-wide:  0.00 – 1.10 /s
a 22 Hz sign flip requires:              ~44 /s        (2 crossings per cycle)
within the 4 low-speed engaged runs:     5 / 0 / 0 / 1 transitions
```

`gp-0x6bbe` is the **base assist boost curve** — DC-dominated during a turn. It never crosses zero, so a
comparator on it carries no phase information at the mode frequency.

## Why the pre-build validation didn't transfer
The build cited V57's bit3 scoring **coherence 0.958 at 21.31 Hz** from a 1-bit channel as proof the
method works. It does work — *for a signal that oscillates about zero*. V57's bit3 did; `gp-0x6bbe`
doesn't. **Validating "a 1-bit channel can carry phase" is not the same as validating "this cell crosses
zero at this frequency."** Check the second before spending a probe on it.

## 🛑 The trap that manufactures a false answer
Pooling runs to get enough samples **creates coherence out of nothing**. Concatenated, bit6 has std 0.5
and returns "coherence 0.5 at 25.24 Hz" — those are **step discontinuities at the splices**, because the
bit is constant *within* each run and different *across* them. Per-run it vanishes.
**Always check whether a 1-bit channel varies within runs before pooling.**

## The distinction to preserve
"Does not cross zero" ≠ "carries no content at that frequency". A lane sitting at +300 with ±50 ripple
has real AC and never crosses zero. **The probe is blind to it; the lane is not necessarily inert.**

## The fix
Probe the **magnitude**, not the sign — a thermometer at thresholds placed on the consumer's own table
breakpoints. That is V59 (on `gp-0x6ba6`) and, for the still-open damping question, V60 (on `gp-0x6bbe`).

## Related: phase resolution is capped by the mailbox skew
bit4's phase against the `0x18F` rate copy is consistently ~75° offset from the `0x14A`-native copy
across all four runs, and one sample at 100 Hz is `21.29 × 360 × 0.01 = 76.6°`. That **validates the
pairing** (and identifies the `0x14A`-native copy as skew-free) — **and caps absolute phase resolution at
±1 sample ≈ ±77° at 21 Hz**, which is not enough to call any sign question. Say so rather than reading a
number off it.

See [[accord-gp6ba6-is-the-boost-amplitude-index]], [[accord-v58-drive-grinding-engagement-gated-creep-only]],
[[accord-probe-underranges-to-one-bit-comparator]], [[accord-telemetry-conventions-that-produced-wrong-answers]].
