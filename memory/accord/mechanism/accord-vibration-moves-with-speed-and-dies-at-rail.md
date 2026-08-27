---
name: accord-vibration-moves-with-speed-and-dies-at-rail
description: "Route 1b (V54, parking lot) — the vibration reproduces at 3.4 mph creep, its frequency MOVES with speed (20.12 Hz @1.0 m/s -> 21.68 Hz @4.0 m/s), and command saturation suppresses it 141x speed-controlled; a fixed-frequency notch is the wrong shape and the null pattern of every command-path lever may have one common explanation."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 421be5bf-160c-42b6-820e-911dcec5caa9
  modified: 2026-07-28T05:21:49.156Z
---

From route `75604b0a432fdc89_0000001b` (V54, 61.5 s parking lot, vEgo max **1.50 m/s = 3.4 mph**, 49%
engaged) cross-checked against route `1a` (V53, vEgo max 5.55 m/s).

## ★ The mode MOVES with speed — so it is not a fixed digital artifact

Welch, 0.195 Hz resolution, engaged runs only:

| route | engaged mean speed | peak | Q |
|---|---|---|---|
| `1b` | 1.03 m/s | **20.12 Hz** | ≈34 |
| `1a` | 3.99 m/s | **21.68 Hz** | ≈22 |

8 bins apart — resolved, not noise. Consequences:
- **A fixed 21 Hz notch is the wrong shape** — it misses at creep. (Moot for openpilot now, see
  [[feedback-no-openpilot-side-modifications]], but it also constrains any *firmware* notch.)
- It argues against a fixed digital artifact pinned at 21.09 Hz.
- ⚠ It does **NOT** resolve the 21.09-vs-78.91 Hz aliasing question — CAN 399 samples at exactly
  100.000 Hz and both aliases shift together. **Any 100 Hz probe inherits the same ambiguity.**

## ★ It reproduces at parking-lot creep

Route `1b` never left the sub-5 km/h cell that V53's `0xC62EA` unlock made reachable — previously
structurally empty. **771×** engaged/disengaged in the 15–26 Hz band; onset sharp at engagement, collapse
at disengagement. Disengaged shows no mode at all, just a road-input shelf at 12.3 Hz present in both
routes. The speed/applied-torque collinearity that route 13 could not break is now broken.

## ★★ Command saturation SUPPRESSES it — 141×, speed-controlled

| speed | unsaturated (<5% railed) | partial | railed (>50%) |
|---|---|---|---|
| 0.8–1.2 m/s | 1.06e9 | 7.6e8 | 1.2e8 (**8.8×** down) |
| 1.2–1.6 m/s | 1.22e9 | 6.3e8 | 8.6e6 (**141×** down) |

At the ±4096 rail openpilot's output stops responding to the sensor — the loop opens and the oscillation
dies. ⚠ **A mechanical operating-point shift (backlash/stiction take-up under high torque) predicts the
same observation**, and this data cannot separate the two. Do not overclaim "closed-loop" from this alone.

Related: hands-on correlates **negatively** with the mode (r = −0.197) — physical damping reduces it,
which is suggestive for the damper line of attack ([[v44-built-handsoff-damping]], V47).

## The ~20 Hz is in the openpilot command, but barely

Same peak bin, **0.091%** of command power. Coherence remains symmetric — direction still not established.

## ⇒ The hypothesis that explains the null pattern

**Every falsified vibration lever was on the command path** — V39 (r24 lane), V41 (motor-rate cap),
V42 ch.2 (r26 surface), V43 (Stage-C pole), V45 (governor slew), V46 (Stage-A pole), V48A (type-8
carrier), V52C (`gp-0x4f60` EMA). If the ~20 Hz is **not present in the final motor command**, all of them
were doomed by construction regardless of which was chosen, and the search belongs in damping/plant.

**The decisive measurement is `gp-0x6b98`** — the final merged command, the ONLY path to FOC. That is what
V55 should sample at 100 Hz on the proven `0x14A` byte4 bits 7:3 piggyback
([[v54-flashed-authority-measured]]).
