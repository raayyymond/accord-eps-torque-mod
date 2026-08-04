---
name: feedback-size-probe-rungs-against-lane-reachable-output
description: "🛑 Size a probe rung against the PRODUCING lane's own reachable output at the operating point — never against a downstream gate's width. V69's bit4 was sized off an input clamp and could never have fired on any build, any drive."
metadata:
  type: feedback
---

# 🛑 SIZE A RUNG AGAINST THE LANE'S OWN REACHABLE OUTPUT, NOT A DOWNSTREAM GATE WIDTH

**Why:** V69 spent its entire telemetry budget — all three rungs, the only channel this kit has — and
got nothing back, and **the failure was arithmetic, not luck.** Two of the three thresholds were set
from the width of a *consumer's* gate rather than from what the *producing* lane can actually emit.

## The rule
> Before choosing a threshold, compute the producing lane's reachable output range **at the operating
> point you care about** — its own clamp, its LERP ceiling, its index axis — and **state that number in
> the build note**. A downstream gate's width is not that number.

A gate's width tells you what the consumer will accept. It says nothing about what the producer emits.

## The three failures, worth knowing individually
- 🛑 **bit4 (`gp-0x6ad4` ≥ +4096) was STRUCTURALLY VACUOUS — it could never have fired, on any build,
  on any drive.** The lane is clamped to **±CEILING = MIN of three LERPs**; the binding one is
  `0xC67C2`/`0xC67C8`, indexed on **voted vehicle speed**, **max 1024**, starting at **ZERO**. At the
  four ratchet episodes' speeds (4.9/6.8/7.8/8.0 km/h) CEILING was **164–341** ⇒ the test sat
  **12–25× above the lane's entire reachable range.**
  **ROOT CAUSE: the design read the ERR *input* clamp `±0x2800` as the lane's OUTPUT range.**
  ★ It also explains why **V56's mute of this same lane changed nothing** — there was little to mute.
- **bit5 (`gp-0x6b62` ≥ +4096) was INSENSITIVE, not vacuous** — reachable max **5786**, so 4096 was
  **71% of full range** and the rung saw only the **top 29%**.
- **bit6 (`gp-0x6ada`) had NO EXPOSURE** — replay predicts ~1 one-sided hit on route `4f`, observed 0,
  **p ≈ 0.37**. A power problem, **not** the V64 gate failure — but **not a positive control either**,
  so bits 5/4 could not be interpreted against it.

## How to apply
Budget a probe the way you budget a cave: **enable + raw input + a rung whose range you have computed.**
Write the reachable range into the build note next to the threshold, so a reviewer can divide.
All three of V69's rungs were also **one-sided**, which is fine as a stated residual and fatal when
combined with a threshold nobody bounded.

Companion to [[feedback-probe-the-gate-not-just-the-output]] (V64: probe the enable and the input, not
just the output) — that one is about *which* signal, this one is about *what value*.
See [[accord-v69-ratchet-probe]], [[accord-v69-flew-dose-response-non-monotone]],
[[feedback-telemetry-must-reserve-a-did-not-fire-value]].
