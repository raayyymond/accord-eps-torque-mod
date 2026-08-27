---
name: reference_accord_c63b4_8hz_bandpass_in_fun3b66a
description: "0xC63B4=51 is a 2-stage EMA (8.13 Hz/pole) sitting on a differentiator inside FUN_0003b66a, making a 2nd-order BANDPASS peaking at 8.14 Hz on the boost-index path at 1 kHz -- the only band-limited gain element found in the control region, never touched by any of 83 builds. Also records why the 3-tap FIR slots CANNOT be made into a usable notch."
metadata:
  type: reference
---

# `0xC63B4` — an 8.14 Hz bandpass on the torque path (2026-08-09, FILTER-A-STRUCTURAL task)

Found while adversarially testing the standing closure claim *"no resonant/biquad structure exists
anywhere in the chain; every gain element is a flat Q10 scalar or a differentiator."*
**That premise is FALSE.** [EVIDENCE]

## 1. Structure `[EVIDENCE — decompile 0x3b66a + full disassemble_function, program="code.bin"]`

`FUN_0003b66a` holds THREE filter elements, not the one the golden model records:

| element | states | cal | value (STOCK == V86B) | order |
|---|---|---|---|---|
| 3-tap FIR on `gp-0x6abc` | `gp-0x365c`, `gp-0x3658` | `0xC4018/1C/20` (f32) | **(1.0, 0.0, 0.0) = identity** | 2 zeros, 0 poles |
| EMA-T, 2-stage, on `4×gp-0x4f60` | `gp-0x364c`, `gp-0x3648` | `0xC63BA` | 512 ⇒ α=0.5 | 2 real poles |
| **EMA-D, 2-stage, on the DERIVATIVE** | `gp-0x3654`, `gp-0x3650` | **`0xC63B4`** | **51 ⇒ α=0.049805** | **2 real poles** |

Output gain `0xC63B8` = 41, final `K` = `0xC63B6` = 1. Ratio-term enable `0xC64BE` = **0 ⇒ that branch
dead by CAL** (already noted in `builds/v50_v79/build_v61_tva.py:41`).

Key instructions:
```
0003b7e8: ld.hu 0x73b4[tp],r11      ; EMA-D stage 1   (tp+0x73b4 = 0xC63B4)
0003b806: ld.hu 0x73b4[tp],r10      ; EMA-D stage 2
0003b80a: ld.hu 0x73b8[tp],r11      ; output gain
0003b7d8: subf.s r11,r12,r7         ; d = f[n] - f[n-1]   (of the SLEW-LIMITED value)
0003b7ec: mov 0x418ba058,r10        ; 17.453293 = 1000*pi/180  -> per-tick delta to rad/s
```

Full rate branch:
`gp-0x6abc` → FIR(identity) → ×1159/32768×6 = ×0.212219 → clamp ±2000 → slew ±565/tick →
**d/dt ×17.4533 → 2-stage EMA(α=0.0498) → ×41/1024 → clamp ±10 → ×1024** → summed with the EMA-T'd
torque → `gp-0x6b9a` (signed) / `gp-0x6ba6` (magnitude).

## 2. The composite is a BANDPASS peaked in the ratchet band `[EVIDENCE, computed from the literal arithmetic, fs=1000]`

```
EMA-D single-pole -3dB = 8.133 Hz;  2-stage -3dB = 5.234 Hz
EMA-T 2-stage -3dB     = 73.07 Hz  (wide open -- this is the one V60 looked at and dismissed)

differentiator x 2-pole LP  ->  PEAK at 8.14 Hz, |H| = 3.8795, -3dB band 3.38-19.64 Hz, Q = 0.501
   5.00 Hz 3.4619 | 7.00 3.8363 | 7.79 3.8759 | 12.80 3.5123 | 21.09 2.6059 | 27.40 2.1185 | 35.00 1.7135
```
Neither the ±2000 clamp (needs `gp-0x6abc` ≈ 9424) nor the ±565 slew limiter (needs ≈52,900) can bind
at these frequencies ⇒ **linear up to the ±10 clamp.**

🛑 **It is NOT resonant.** Both poles real and coincident at z = 0.9502 ⇒ Q = 0.5 exactly, cannot ring.
It cannot CREATE the Q=14-29 mechanical mode — it *shapes and drives* that band.
See [[accord-ratchet-is-a-lightly-damped-resonance]].

## 3. Clamp reachability — a live, heavily-exercised term

Clamp ±10240 counts; at 7.79 Hz saturates at `gp-0x6abc` amplitude 2642.
Against V68's measured `gp-0x6ac0` (p99 = 843, MAX = 2219): **~32% of clamp at p99, ~84% at MAX.**
Contrast `FUN_0003b8f6`'s inertia term at 0.4-6% — see
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]].
⚠ Amplitude figures inherit the `gp-0x6ac0`-for-`gp-0x6abc` substitution — **but that substitution is
now DERIVED, not assumed**: see [[reference_accord_gp671a_creep_value_and_friction_lane_schedule]] §4.

## 4. Blast radius CONTAINED, and never touched by any build `[EVIDENCE]`

Raw Python LE byte scan of all 1,048,576 bytes + Ghidra adjudication of every hit:
`0xC63B4` → 4 raw hits, **2 real (`0x3b7e8`, `0x3b806`, both in this function)**; the two at
`0x7af90`/`0x7af9c` are **mid-instruction false positives** (`disassemble_bytes(dry_run)` at `0x7af88`
shows `sst.b r14,0x34,ep` / `ld.bu 0x59,gp,r14`). `0xC63B8` → 1 reader. `0xC63BA` → 2 readers (matches
the older census, cross-validating the scanner).

**`0xC63B4` appears in ZERO of 83 `build_v*_tva.py`.** Its sibling `0xC63BA` appears in six and was
retired — and `builds/v50_v79/build_v60_tva.py:29` says why: *"...or than `0xC63BA` (which filters only the torque lane,
while **the index also carries a resolver-rate-derivative lane**)."* **The kit knew the lane existed,
dismissed the wrong filter, and never located this one.** FALSIFIED ≠ never-tried.

## 5. Downstream, and the one thing still open

`gp-0x6ba6 = |gp-0x6b9a|` is the LERP index into the boost amplitude tables (`0xD28DC`/`0xD2888`,
via `0xca4f4`); `gp-0x6b9a` itself is only a plausibility-gate input (`build_v58/59`).
**Direction settled by the orchestrator 2026-08-09**: mode byte `0xC6499` = 1 on STOCK/V85/V86B ⇒
`gp-0x6ba6` IS the index; table `Y = [16384, 14658, 11676, 9362, 8245, 8188]` over
`X = [0,512,1490,2529,3645,5120]` ⇒ **FALLING, 2.0× across the range ⇒ more 8 Hz motion ⇒ LESS assist.**
So it reads as Honda's own anti-oscillation gain backoff.
⇒ the parametric-drive reading is still live (a **rectified** index modulates gain at **2f**, the Mathieu
condition, and the kit measured exactly that in [[accord-v59-parametric-pump-marginal]] at 42.19 Hz vs a
21.09 Hz mode) but **its SIGN is the open question, not its existence.** [BELIEF]

## 6. The lever, and the FIR dead end

Lowering `0xC63B4` moves the peak down and monotonically cuts the whole lane — 2-byte cal edit:
```
0xC63B4  peak Hz  |H|@7.79  |H|@21   |H|@27.4   pole -3dB
  51 (stock) 8.14   3.876    2.606    2.119      8.133
  32         5.06   2.201    1.093    0.861      5.053
  24         3.78   1.414    0.625    0.488      3.775
  16         2.50   0.697    0.281    0.217      2.506
   8         1.24   0.186    0.070    0.054      1.248
```
🛑 It is a **loop-gain edit** (`gp-0x6abc` ← resolver ← motor ← assist ← boost gain ← `gp-0x6ba6` ← here),
so **GATE 2 applies**. Reducing is the safe direction; raising is not.

🛑🛑 **The two identity 3-tap FIR slots CANNOT be made into a usable notch. Do not propose it.**
`[EVIDENCE, computed]` A 2-zero FIR null at 7.79 Hz needs `(c1,c2,c0) = (1.0, -1.997604766, 1.0)`, which
gives **|H| at DC = 0.002395** — it nulls DC as hard as it nulls 7.79 Hz, and with no poles to narrow it
the "notch" is the entire low band (recovers to -3 dB of passband only above 318 Hz). Same for
`0xC4048/4C/50`. This is the arithmetic reason behind the older "FIR-3 has no sharp selectivity" note.

## 7. Provenance / verification

All Ghidra calls passed `program="code.bin"` explicitly (the session had a second, unanalysed program
open and `is_current` was observed **flipping between agents mid-session** — never trust a snapshot).
Code regions byte-identical STOCK vs V86B: `FUN_0003b66a` `0x3b66a-0x3b8f4` sha256 `be45150a875989ec`;
cal blocks `0xC63B4-0xC63BE`, `0xC4018`, `0xC4048` all identical (the two FIR slots are byte-identical to
**each other**, sha `480376c6bf738a02`).

Related: [[reference_accord_fun41d56_state_space_complex_poles]],
[[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]],
[[reference_accord_notch_biquad_search_negative_result]],
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]].
