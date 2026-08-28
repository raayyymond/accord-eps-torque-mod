---
name: accord-v114-alpha2-rotates-mass-into-damping
description: "V114 moves ONE byte, 0xC40DC alpha2 14->8, and it is the first lever that satisfies the operator's both-at-once directive from a single cell: 6-16 Hz DAMPING x1.252 while 6-16 Hz apparent MASS x0.796. alpha2 sets the gp-0x6b26 bandpass's upper corner, so lowering it walks the peak DOWN from 46.5 to 34.2 Hz toward the band Re(Z) measures at -33..-67 - it ROTATES the vector rather than scaling it. Every magnitude falls (peak x0.669, broadband x0.604), so it is V107's failure mode inverted. 42/42."
metadata:
  node_type: memory
  type: project
---

# ⭐⭐★★★★★ V114 — **ONE BYTE THAT RAISES DAMPING AND LOWERS MASS AT THE SAME TIME**

2026-08-27. **The first lever in this kit to satisfy
[[feedback-do-not-buy-ratchet-with-mass-and-friction]] from a single cell.**

```
builder  analysis-2020accord/builds/v108_plus/build_v114_tva.py   42/42   BASE = V111
image    8c4f53ccf8be61f8d3ceee5dcd4ca2c4ef46abe36af7e8e51b59ade104491820
.rwd     26d2a6c10e7f2816338a698440ea454dffd2d15aadd6c3e76b7ebb906ef0f5c1
0xC40DC   14 -> 8   alpha2, the gp-0x6c2c EMA pole
1 payload byte (0e -> 08) + 1 CRC trailer.  NO CAVE EDIT.  Knee and K1 both HELD.
```

## ⭐⭐ WHY IT WORKS — α2 **MOVES** THE PASSBAND, IT DOES NOT **SCALE** IT
The lane is `H(f) = 64·H_lp·(1 − z⁻¹)·H_ema`, a **bandpass**
(`α0 = 37/128` = `cal(0xC643C)`, `α2` = `cal(0xC40DC)`, fs = 1000 Hz). **α2 sets the upper corner**,
so lowering it walks the peak DOWN toward the anti-damped band. Splitting `gp-0x6b26` against the
**velocity** phasor — `DAMPING ~ |H|·sin φ`, `MASS ~ |H|·cos φ`:
```
   α2   peak Hz   6-16Hz DAMPING   6-16Hz MASS   20-30Hz damping   broadband rms
   22     61.1        0.794            1.085          0.921            1.488     (V108)
   14     46.5        1.000            1.000          1.000            1.000     (V111)
    8     34.2        1.252            0.796          0.899            0.604     <- V114
    6     29.3        1.318            0.647          0.769            0.463
    4     23.7        1.274            0.422          0.564            0.316
```
🛑 **THE DAMPING RISES WHILE THE MASS FALLS.** That is only possible because α2 **rotates** the
vector — more of a *smaller* term lands on the damping axis. Every scaling lever the kit has tried
moved both together, which is why the directive looked like a contradiction. **It is not.**

## ⭐ WHY THIS BAND — THE Re(Z) MEASUREMENT
[[accord-antidamping-is-centred-at-9-12hz-not-20-30]]: engaged `Re(Z)` is **−33 to −67 across
6–16 Hz** (min at 9–12 Hz) while the **manual arm is damped at every band on every route**. 20–30 Hz
holds 36 % of the rate *power* but its `Re(Z)` is only −3 to −5 and crosses positive at f0 ≈ 23.3 Hz.
⇒ **damping belongs at 6–16 Hz**, and that is exactly where α2 moves it.

## ⭐ WHY THE DOSE IS 8
6–16 Hz damping peaks near α2 = 5–6, but the 20–30 Hz give-back grows fast and **21–27 Hz is where
V106's win was measured** (the kit's only band-power result to clear its own split-half null).
**α2 = 8 buys +25 % in the deep band for −10 % at 20–30 Hz.** It is also the same step *size* the
operator already read clearly: **V111's 22→14 was ×1.27 damping**, and he reported oscillations gone
and ratcheting reduced. **6 and 5 remain on a monotone axis if 8 reads well.**

## ✅ WHY IT CANNOT REPEAT V107
V107 railed because it multiplied the **Y row** — a magnitude change. α2 does the opposite:
**peak |H| 9.20 → 6.15 (×0.669), broadband rms ×0.604, and 100 Hz 7.13 → 4.05.** Every magnitude
falls ⇒ **rail duty must fall.** ⊕ The 100 Hz drop attacks V107's own *"higher-pitched, several
hundred Hz"* grinding complaint directly.

## GATES
✅ **GATE 1 — the cleanest in the kit.** `search_instructions` finds **exactly ONE** access
image-wide: `0x41626  ld.hu 0x50dc,tp,r11` in `FUN_00041464`. **Zero writers.** Matches the lineage's
own note (*"VIRGIN ON ALL 102 IMAGES"* before V109).
✅ **GATE 2** — a pole move on an existing first-order EMA. No new state, no new nonlinearity, and
every magnitude falls. Both lineage conditions on this lever are met: it ships **WITH the notch
revert** (V108 did it; V111 carries Honda's biquad, asserted byte-identical) and is taken
**UNCOMPENSATED** (Y untouched, so the int16 headroom argument never arises).
✅ Knee 600, K1 204, gain 5346, all four `gp-0x6b26` Y rows, the biquad and the 164-byte cave all
asserted **byte-identical to V111**.

## ⚠ THE KNOWN RESIDUAL RISK
`gp-0x6c2c` fans out to **three** consumers; only the `gp-0x6b26` damper is verified against a
reshaped signal. The second is the oscillation detector (`FUN_000428d4` vs `T` = `cal(0xC620A)`), and
**lowering α2 shrinks `|gp-0x6c2c|`, so the detector fires less — the safe direction.** The third is
unenumerated. ⊕ Mitigating: **V109/V111 already flew this exact axis (22→14) fault-free.**

Related: [[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]] ·
[[accord-v111-flew-alpha2-is-the-only-delta]] · [[accord-v113-built-knee-with-k1-held]] (orthogonal)
