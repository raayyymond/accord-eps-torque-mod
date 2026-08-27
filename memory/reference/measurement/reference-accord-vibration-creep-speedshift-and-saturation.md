---
name: reference-accord-vibration-creep-speedshift-and-saturation
description: "Route 1b (V54, parking lot): the vibration reproduces at 3.4 mph creep, its frequency MOVES with speed (20.12 Hz at 1.0 m/s -> 21.68 Hz at 4.0 m/s), and command saturation suppresses it 141x speed-controlled. A fixed-frequency notch is the wrong shape, and every falsified lever shares one testable assumption."
metadata:
  node_type: memory
  type: reference
---

# The vibration at creep: it moves with speed, and it dies at the rail

Route `75604b0a432fdc89_0000001b` (V54, 61.5 s, vEgo max **1.50 m/s = 3.4 mph**, 49% engaged), cross-
checked against route `1a` (V53, vEgo max 5.55 m/s). Welch, 0.195 Hz resolution, engaged runs only.

## The mode MOVES with speed -- 8 bins, resolved

| route | engaged mean speed | peak | Q |
|---|---|---|---|
| `1b` | 1.03 m/s | **20.12 Hz** | ~34 |
| `1a` | 3.99 m/s | **21.68 Hz** | ~22 |

=> **No fixed-frequency notch can track it**, in firmware or anywhere else. It also argues against a fixed
digital artifact pinned at 21.09 Hz. It does **NOT** resolve the 21.09-vs-78.91 Hz aliasing question --
CAN 399 samples at exactly 100.000 Hz and both aliases shift together. Any 100 Hz probe inherits this.

## It reproduces at parking-lot creep

Route `1b` sits entirely inside the sub-5 km/h cell that V53's `0xC62EA` unlock made reachable --
previously structurally empty. **771x** engaged/disengaged in the 15-26 Hz band; sharp onset at
engagement, collapse at disengagement. Disengaged shows no mode at all, only a road-input shelf at
12.3 Hz present in both routes. The speed/applied-torque collinearity is broken.

## Saturation SUPPRESSES it -- speed-controlled

| speed | unsaturated (<5% railed) | partial | railed (>50%) |
|---|---|---|---|
| 0.8-1.2 m/s | 1.06e9 | 7.6e8 | 1.2e8 (**8.8x** down) |
| 1.2-1.6 m/s | 1.22e9 | 6.3e8 | 8.6e6 (**141x** down) |

At the rail openpilot's output stops responding to the sensor -- the loop opens and the oscillation dies.
**A mechanical operating-point shift (backlash/stiction take-up under high torque) predicts the same
observation**, and this data cannot separate the two. Do not overclaim "closed-loop" from it alone.

Also: hands-on correlates **negatively** (r = -0.197). The ~20 Hz IS in the openpilot command at the same
peak bin, but at only **0.091%** of command power; coherence remains symmetric, so direction is unproven.

## The assumption every falsified lever shares

V39, V41, V42 ch.2, V43, V45, V46, V48A, V52C are **all on the command path** and all assume the ~20 Hz is
*commanded*. If it is absent from `gp-0x6b98` (the final merged command, the only path to FOC) they were
doomed by construction. **V55 measures exactly that** -- see [[reference-accord-v55-dual-probe-built]].
