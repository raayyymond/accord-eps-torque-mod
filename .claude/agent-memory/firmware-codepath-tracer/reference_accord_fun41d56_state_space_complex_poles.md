---
name: reference_accord_fun41d56_state_space_complex_poles
description: "FUN_00041d56 is a 3x3 state-space angle observer at 1 kHz with 15 raw-float cals at 0xC60E8-0xC6123 and a GENUINE complex-conjugate pole pair (zeta=0.975, Q=0.513) -- the only complex-pole structure in the control region -- but ALL THREE of its outputs have ZERO external readers, so it is a fault detector, NOT a usable filter site."
metadata:
  type: reference
---

# `FUN_00041d56` — a 3rd-order state-space filter, cal-defined, wrong signal (2026-08-09)

Found while adversarially testing the closure claim *"no resonant/biquad structure exists anywhere."*
**This is the counter-example — and it is also the reason the closure's CONCLUSION still holds.**

## 1. Structure — a full 3×3 recursion `[EVIDENCE, decompile 0x41d56, program="code.bin"]`

Three float states, each updated from **all three** — the cross-coupled shape, not a cascade:
```c
fVar4=*(float*)(gp-0x3598); fVar8=*(float*)(gp-0x3590); fVar11=*(float*)(gp-0x3594);
fVar10 = tp+0x70fc*fVar11 + tp+0x70f8*fVar8 + tp+0x70f4*fVar4 + tp+0x7114*u1 + tp+0x7118*u2;
fVar9  = tp+0x70f0*fVar11 + tp+0x70ec*fVar8 + tp+0x70e8*fVar4 + tp+0x710c*u1 + tp+0x7110*u2;
fVar3  = tp+0x7108*fVar11 + tp+0x7104*fVar8 + tp+0x7100*fVar4 + tp+0x711c*u1 + tp+0x7120*u2;
*(float*)(gp-0x3598)=fVar9; *(float*)(gp-0x3590)=fVar10; *(float*)(gp-0x3594)=fVar3;
```
`x[n+1] = A·x[n] + B·u[n]`. **15 raw f32 cals, contiguous at `0xC60E8`–`0xC6123`**, byte-identical
STOCK vs V86B (sha256 `37fbb80903e2bba4`). Code region `0x41d56-0x41ee0` also identical
(sha `d5f5565633b1f4ea`).

Inputs: `u1 = gp-0x4fd8 × 0.0015339808` (= 2π/4096 ⇒ a **resolver angle in radians**), `u2 = gp-0x501c`.
Caller: `get_function_callers` → **`FUN_0002214a` ONLY** ⇒ 1 kHz confirmed.

```
A = [ -0.5      +0.001    -0.006  ]     B = [ +1.5     +0.006  ]
    [ -687.5    +1.0      -11.751 ]         [ +687.5   +11.751 ]
    [ +10.637    0.0       +1.0   ]         [ -10.637   0.0    ]
      (order [x1=gp-0x3598, x2=gp-0x3590, x3=gp-0x3594])
```
`B[:,0] = −A[:,0] + [1,0,0]` ⇒ it operates on the tracking error `e = u1 − x1`, and `x2`/`x3` are two
integrators with cross-coupling ⇒ **literally the Chamberlin / state-variable topology.**
It is an **angle observer** (687.5 and 10.637 are observer gains).

## 2. Eigenvalues — a REAL complex pair, but it cannot ring `[EVIDENCE, char poly + Durand-Kerner]`

```
char poly: l^3 -1.5 l^2 +0.751322034 l -0.126326635
z = +0.45886448 ±0.07999017j   |z|=0.46578   COMPLEX  zeta=0.9754, Q=0.513, pole angle -> 27.47 Hz
z = +0.58227104                               REAL     tau 1.849 ms, corner 86.07 Hz
```
🛑 ζ = 0.975 ⇒ **no magnitude peak** (a peak needs ζ < 0.707) and |z| = 0.466 decays in ~1.3 ms.
⇒ **the closure claim's premise is false, but its conclusion is right**: nothing in the control region
has Q > 0.52, so the firmware cannot create the Q=14-29 mode. See
[[accord-ratchet-is-a-lightly-damped-resonance]].

⚠ The pole angle corresponds to **27.47 Hz**, close to V80's 27.4 Hz limit cycle. With ζ=0.975 there is
no peak, so this is **explicitly NOT proposed as a mechanism** — recorded only so nobody rediscovers the
coincidence and over-reads it.

## 3. 🛑 IT IS NOT A FILTER SITE — zero torque-path readers `[EVIDENCE]`

Raw LE byte scan (both gp encodings) + Ghidra adjudication of every hit:

| output | writers | external readers |
|---|---|---|
| `gp-0x6cb4` (x1) | 1 (`0x41e1c`) | **0** — the `0x59344` hit has base=r31, not gp |
| `gp-0x6d80` (x2) | 1 (`0x41e26`) | **0** |
| `gp-0x6ad8` (x3×1024) | 1 (`0x41e5c`) | **0** — the apparent reader at `0x794f0` inside `FUN_000757a2` is **mid-instruction**: `disassemble_bytes(dry_run)` at `0x794e8` shows the real instruction is `sld.w 0x50,ep,r18`, whose 2-byte encoding **is literally `28 95` = `0x9528`**, the displacement being scanned for |

Its ONLY effect on the car: `|x3·1024|` → 2-threshold hysteresis (`0xC61F8` = 1024 / `0xC61FA` = 5530)
→ fault counter `gp-0x671d` → `FUN_00016de6(0x5e,…)` = **DTC 0x5e**. And `gp-0x671d` gates the r24 arm
(`gp-0x671d==0 && gp-0x683c!=0`) — so it couples to control as an **interlock**, never as a signal path.

⇒ **Editing its 15 floats does NOT filter torque. It changes fault-detection behaviour and can disarm
the rate lane.** Do not treat this as a free filter site.

**Its real value is as a TEMPLATE**: it proves this image already contains a working 3-state MAC
recursion whose entire dynamics are 15 contiguous editable floats — i.e. an arbitrary 3rd-order filter
*including a resonant one* is expressible in this codebase's own idiom. Relevant because the cave path
is effectively closed (see §5).

## 4. Search method and its SCOPE LIMIT

Census: `search_instructions` for every `ld.w`/`st.w` with a `gp` base (3013 loads / 2320 stores,
`instructions_scanned` 183,641, `truncated:false`), intersected per function in Python ⇒ **128 functions
hold ≥2 gp-relative 32-bit cells that are both loaded and stored.** The float-state arena is
`gp-0x3400`–`gp-0x3900`, one contiguous slice per owning function.
⚠ **A store census returned 0 functions on the first pass** because `st.w` renders operands as
`src, disp, base` while `ld.w` renders `disp, base, dst` — **a filter-syntax zero that reads exactly like
a fact.** Always locate the `gp` token, never assume operand position.

🛑 **Only 6 of the 128 were characterised** (`FUN_0003b66a`, `FUN_0003b8f6`, `FUN_00041d56`,
`FUN_00041464`, `FUN_00039702` [not a filter — slew limiters + plausibility monitor], `FUN_0003a382`).
⇒ **"no structure with Q > 0.52" is scoped to the ~40 kB control region, NOT the whole image.**
Deliberately deferred by the orchestrator: `FUN_00071272` (52 states / 106 FMA) and `FUN_000757a2`
(38 / 105), the FOC pair — `INSERTION-BLAST-RADIUS` independently found `FUN_000757a2`'s write-set ∩
`FUN_00071272`'s read-set = **0**, concluding the FOC core is a motor observer, not the torque servo.

## 5. 🛑 The cave path is effectively CLOSED — cal-only from here

`INSERTION-BLAST-RADIUS` found a **float twin of the shaper** (`FUN_00043e44`, branch point `0x4467a`)
that compares against the delivered command with a **±5-count tolerance** and raises
**DTC 0xF00049 — an EPS-disabling fault — after ~10 ms** of divergence. The two best cave hook sites
(`0x431C4`, `0x43206`) are **inside its coverage and would disable the steering** — the V74/V75
loss-of-assist class. ⇒ any new filter must be **cal-only**. That is what makes
[[reference_accord_c63b4_8hz_bandpass_in_fun3b66a]] the operative lever rather than a cut biquad.

Related: [[reference_accord_c63b4_8hz_bandpass_in_fun3b66a]],
[[reference_accord_gp671a_creep_value_and_friction_lane_schedule]],
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]].
