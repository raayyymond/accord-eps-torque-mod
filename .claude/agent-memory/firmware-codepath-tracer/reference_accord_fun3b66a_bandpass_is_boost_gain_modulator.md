---
name: reference-accord-fun3b66a-bandpass-is-boost-gain-modulator
description: FUN_0003b66a's 8.131 Hz band-pass (cals 0xC63B4/0xC63B8) does NOT inject damping torque — its output gp-0x6b9a/gp-0x6ba6 is the INDEX into the boost curve, so raising 0xC63B8 modulates a GAIN parametrically; plus the four-term entry gate proven to pass at creep, the sentinel semantics of the else branch, and gp-0x6752 proven never 0.
metadata:
  type: reference
---

Traced 2026-08-09 (`LOWSPEED-LANE-MAP`) for the team-lead's 8 Hz band-pass lever brief. Ghidra
`program="code.bin"` explicit on every call; cals Python-read from stock and
`_v86b_…_plain_image.bin`.

## The band-pass reproduces — but it is a GAIN MODULATOR, not a damper

Chain in `FUN_0003b66a` (task 1, 1 kHz): `gp-0x6abc` → 3-tap FIR → ×polarity ×`0xC613A`/32768×6
→ (+ a dead 2nd term) → clamp ±2000 → slew ±565/cycle → backward difference ×17.453293 → two EMAs
sharing α=`0xC63B4` → gain `0xC63B8` → clamp ±10 → ×1024, **added to** a double-EMA'd torque term
(α=`0xC63BA`) → ×`0xC63B6` → `gp-0x6b9a`; `|·|` → `gp-0x6ba6`.

α = 51/1024 = 0.04980 ⇒ corner **8.131 Hz**; peak 8.131 Hz, phase **+1.44°**, −3 dB at 3.37/19.64 Hz.
⊕ `17.453293 == 1000·π/180` is an **independent confirmation the task rate is 1000 Hz**.

**🛑 The output is the INDEX into the boost curve, not an aggregator lane.** `0xC6499` = 1 (stock and
V86B) ⇒ `FUN_00034a72` uses `gp-0x6ba6` as its `|trq|` LERP index, and that curve is **monotonically
decreasing** (m26 `X=[0,512,1490,2529,3645,5120]` `Y=[16384,14658,11676,9362,8245,8188]`, Q14).
⇒ raising `0xC63B8` swings the **boost gain** at 8.13 Hz. That is **multiplicative/parametric**, not an
additive damping torque — GATE 2 must treat it as a parametric-pump question (cf. the V59 finding),
not as linear damping.

**Blast radius is one lane.** `gp-0x6b9a`/`gp-0x6ba6` have exactly two consumers each: `FUN_00034350`
and `FUN_00034a72`. `0xC6498` = 1 so the damper *does* index FactorB with `gp-0x6ba6` — but **FactorB is
flat [1024]×4 in all four modes**, so the damper is insensitive to this lever entirely. Only
`gp-0x6bbe` (boost, ±512) moves.

## Dose ceiling — the ±10 clamp is AFTER the gain
```
D_pre_clamp = A(gp-0x6abc) x 0.21222 x |Hband(f)| x (0xC63B8/1024)
  7.79 Hz: k = 0.0037851 -> clamp at A = 2642 ct
  at 1.29 deg p-p / 7.79 Hz (31.6 deg/s = 148.9 ct): 5.64% of clamp
  => ~17.7x headroom; 0xC63B8 41 -> ~727 before clipping at that amplitude
```
Beyond that it is a **hard relay at the ring frequency** — the V80 failure mode.
[BELIEF on the `4.7121 ct per °/s` scale for `gp-0x6abc`; that figure is settled for `gp-0x6abe` only.]

## Cal census (stock == V86B for all of these)
`0xC4018/1C/20` (FIR b0/b1/b2) = **1.0 / 0.0 / 0.0 ⇒ the FIR is a PASS-THROUGH**, not a filter (second
degenerate FIR in this firmware, cf. `FUN_0003b8f6`). `0xC613A`=1159 · `0xC63B4`=51 · `0xC63B6`=**1**
(output gain — multiplies BOTH the D-term and the torque term, so **not** a clean lever) ·
`0xC63B8`=41 · `0xC63BA`=512 · `0xC63BC`=0 · **`0xC64BE`=0 ⇒ the whole `gp-0x4f62` summand is DEAD.**

## The four-term entry gate PASSES at creep — no speed term, no engagement term
```c
0x6400 + gp-0x4f60 < 0xc801   // torque sensor      in [-25600,+25600]
gp-0x6abc + 13000  < 0x6591   // resolver/motor rate in [-13000,+13000]
(char)gp-0x6752 + 1U < 3      // polarity in {-1,0,+1}
0x6400 + gp-0x4f62 < 0xc801   // torque 1st difference in [-25600,+25600]
```
All four are **plausibility/overflow rails plus a static config check**, not operating-point gates.
±0x6400 is the signal's own clamp value in `FUN_000352b4`; ±13000 is the same rail family as FactorE's
gate in `FUN_00034350`; `gp-0x4f62` is clamped ±0x1400 elsewhere (5× margin) **and is unused because
`0xC64BE`=0**.

## 🛑 The `else` branch writes SENTINELS (0x7FFF / 0xFFFF) and both consumers DETECT them
Not "saturated defaults that propagate". `FUN_00034350` range-tests them and falls back to
**FactorB = unity 1024**; `FUN_00034a72` range-tests them, sets its internal validity flag false and
**zeroes `gp-0x6bbe`**. ⇒ **a gate failure DISABLES boost and leaves the damper untouched.** A gate
failure is *safer* than the lane running, not worse.

## ★ `gp-0x6752` (assist polarity) is NEVER 0 — settles a recurring question
Writers: `FUN_000490ac` (init) → **1**; `FUN_000497e6` → **1** or **0xFF (−1)**, selected by a
**configuration-table byte** `*(char*)(*(int*)(gp-0x34b8)+4) == 0x2C`, not by any dynamic signal. Both
lockstep-shadowed at `gp-0x4c2d`. ⚠ `FUN_00048a40`'s two stores (`0x48E68`, `0x48E88`) NOT decompiled —
the one gap. **Structural proof it cannot be 0 while driving:** the same byte multiplies the base-assist
output in `FUN_000352b4` and is read at **59 sites** incl. the aggregator ⇒ polarity 0 = zero power
steering. Treat it as an LHD/RHD-class configuration constant, not a state.

## Tool note
`get_assembly_context` returned `{}` for every address tried this session. `decompile_function`
**rejected `"0x0003ad74"` but accepted `"0003ad74"` in the same state** — the `0x` prefix is unreliable
on that tool; retry unprefixed before concluding a function is absent.

## Related
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — the damper this feeds.
[[reference_accord_lowspeed_gate_census_and_friction_5x_schedule]] — the boost lane's own speed schedule
and the rest of the creep map. [[reference_accord_boost_index_input_is_resolver_rate_not_torque]] —
prior finding that the boost index is a rate, which this file now resolves *mechanistically*: the index
is `gp-0x6ba6`, i.e. `FUN_0003b66a`'s band-passed `gp-0x6abc`.
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] — the other degenerate FIR.
