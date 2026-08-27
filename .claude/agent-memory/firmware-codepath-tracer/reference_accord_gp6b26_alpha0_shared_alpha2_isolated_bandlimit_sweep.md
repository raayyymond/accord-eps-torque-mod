---
name: reference_accord_gp6b26_alpha0_shared_alpha2_isolated_bandlimit_sweep
description: Fresh decompile of FUN_00041464 confirms alpha0 (0xC643C, EMA1) is SHARED between gp-0x6abe/gp-0x6ac0 (Honda's damper input AND the 0xC520C torque-ceiling index) and the whole gp-0x6c2c cascade, since both branch off the same y0 EMA1 state -- moving it changes the torque ceiling too. alpha2 (0xC40DC, EMA2-on-the-difference) is ISOLATED: doubly-independent GATE-1 (Ghidra + corrected Python LE scan honoring the disp|1 trap + 6-byte extended-disp scan) finds EXACTLY ONE gp/tp-relative access to this cal cell in the whole 1MB image. Full (peak/-3dB span/ratio-after-Y-compensation) sweep over integer K2 gives a genuine Pareto tradeoff: lowering K2 cuts 61-300Hz gain 21-66% but RAISES 3-8Hz gain proportionally MORE (up to 2.4x at K2=3) because Y must rise to hold 21.73Hz constant. K2=14 recommended (71% at 100Hz, +7.4% at 7.79Hz). GATE 2 (torque phasor stays in the proven-safe 180-270deg sector) holds for K2>=3; crosses out at K2<=2. 🛑 CORRECTED same day: the 90-180deg sector-entry frequency moves DOWN (74.1Hz->54.0Hz at K2=14), not up -- there is no "push the danger zone out of band" second benefit, that was a search-range-bug false negative. Also: Y[0]=-29490 int16 headroom binds below K2=13 (K2=11 only achieves 94.6% of target gain at creep).
metadata:
  type: reference
---

# `gp-0x6b26` band-limit lever — alpha0/alpha2 GATE 1, and the alpha2-only Pareto sweep

2026-08-26, `hfmech` task, same session as
[[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]]. Team-lead asked whether alpha0
(`0xC643C`) also feeds the `0xC520C` torque-ceiling index `gp-0x6ac0` (per `ratecap`'s fresh work),
and for a priced band-limit lever. Script: scratchpad `gp6b26_bandlimit_sweep.py` (not in repo).

## GATE 1 — fresh `decompile_function(0x41464)`, the whole function [EVIDENCE]
```
target = gp-0x4f50*1024
y0 = y0_prev + ((target-y0_prev)*cal(tp+0x743c)) >> 7        K0=cal(0xC643C)=37    <- EMA1
gp-0x6abe = y0>>10                    (Honda's damper input, shadow vs gp-0x4cc2)
gp-0x6ac0 = |y0|>>10                  (shadow vs gp-0x4cc4)  <-- CONFIRMS: same y0 state as gp-0x6abe
d = y0[n]-y0[n-1]                     (SAME y0 state)
d32 = clamp(d*32, +-0xFA0000)
gp-0x35a0 = gp-0x35a0_prev + ((d32-gp-0x35a0_prev)*cal(tp+0x50dc)) >> 6   K2=cal(0xC40DC)=22   <- EMA2
gp-0x6c2c = gp-0x35a0>>9               (plain write here, no shadow check at THIS site)
```
🛑🛑 **CONFIRMS `ratecap`'s claim: `0xC643C` (alpha0) is SHARED** between `gp-0x6abe`/`gp-0x6ac0` (feeds
`ratecap`'s freshly-reconstructed `gp-0x4f64=min(LERP_clamped(gp-0x6ac0,X,Y),4762)` torque ceiling) and
the entire `gp-0x6c2c`/`gp-0x6b26` cascade — both branch off the identical `y0` state. **Moving alpha0
changes the torque ceiling's own index, not just the damper.** Do not move it without pricing that
separately.

`0xC40DC` (alpha2) touches ONLY `d32→gp-0x6c2c`; does not touch `y0`, `gp-0x6abe`, or `gp-0x6ac0` at all.

## GATE 1 on `0xC40DC` itself — doubly independent, corrected for the disp|1 trap [EVIDENCE]
Ghidra `search_instructions("50dc")`: 2 hits — 1 real (`ld.hu 0x50dc,tp,r11 @0x41626` in
`FUN_00041464`), 1 branch-target text collision (`be 0x000250dc`, excluded).
Python: **first attempt scanned for raw `0x50DC` and found a SPURIOUS unrelated hit** — wrong target.
`ld.hu`/`ld.w` carry `disp|1` in hw2 (documented kit trap); bytes at `0x41626` are `e5 5f dd 50`,
hw2=`0x50dd` exactly. Rescanned for `0x50DD`: **exactly 1 hit in the whole 1MB image, at file offset
0x41628 — precisely +2 bytes into the SAME instruction Ghidra found.** A 6-byte extended-displacement
scan (`disp=(sext16(hw2)<<7)|((hw1>>4)&0x7F)`) found zero additional candidates.
⇒ **`0xC40DC` has exactly ONE gp/tp-relative access in the entire image. Zero writers (cal constant).**
Cleanest GATE-1 result obtainable in this kit. **Recommend alpha2-alone as the lever.**

## ⚠ Correction to a prior memory's "six shadow-lockstep pairs" framing
[[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]] lists "SIX shadow-paired
signals" but its own address table only names FOUR (`gp-0x6abc/-0x4cc0`, `gp-0x6abe/-0x4cc2`,
`gp-0x6ac0/-0x4cc4`, `gp-0x6ac2/-0x4cc6`). Fresh read confirms: **`gp-0x6c2c`/`gp-0x6c2e` are NOT
shadow-lockstep-paired at their write site in `FUN_00041464`** — it's a plain, unprotected store. The
shadow protection in this chain lands one hop further downstream, on `gp-0x6b26` itself (vs
`gp-0x4cd0`, per this session's item-1 work) — moving alpha2 changes gp-0x6c2c's VALUE, the downstream
shadow-check on gp-0x6b26 still runs unmodified on whatever that value becomes. Not a new exposure, but
"six pairs from this function" should not be repeated.

## GATE 2 — torque phasor at 21.73Hz across the candidate range [EVIDENCE]
Phasor (phase(H_accel)+180°, the established convention) stays in **180-270° (proven-safe,
damping+added-inertia) for K2 from 22 down to 3**. **Crosses out at K2=2 (174.95°) and K2=1
(168.45°)** — reproduces the independently-derived "pole-fork" finding
([[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]]) that this same sector-boundary
region is reachable-but-unverified from a different route. **Floor any candidate at K2>=3.**

## The sweep — K0 fixed at 37, K2 varied, Y auto-scaled to hold |H(21.73Hz)| constant [EVIDENCE]
`ratio(f) = |H_accel_new(f)|*Yscale / |H_accel_current(f)|` where `Yscale=|H_accel_cur(21.73)|/|H_accel_new(21.73)|`
— i.e. the delivered 21.73Hz damping is held IDENTICAL to today by construction; ratio shows what
happens elsewhere once that compensation is applied.
```
K2  peak_Hz  -3dB span      ratio@3Hz  ratio@7.79  ratio@61  ratio@100  ratio@150  ratio@200  ratio@300
22   61.1    25.1-153.0Hz    1.000      1.000       1.000     1.000      1.000      1.000      1.000   (current)
16   50.3    20.7-124.3Hz    1.011      1.045       0.855     0.787      0.754      0.740      0.729
14   46.5    19.0-115.5Hz    1.021      1.074       0.796     0.714      0.675      0.660      0.648   <- recommended
12   42.6    17.2-106.9Hz    1.036      1.115       0.733     0.641      0.600      0.584      0.572
10   38.5    15.3- 98.4Hz    1.062      1.181       0.668     0.572      0.531      0.515      0.503
 8   34.1    13.1- 90.1Hz    1.115      1.287       0.605     0.508      0.468      0.453      0.442
 6   29.3    10.6- 81.7Hz    1.246      1.627       0.547     0.452      0.414      0.400      0.390
 3   20.4     6.1- 68.8Hz    2.437      2.022       0.482     0.392      0.358      0.345      0.336
```
🛑 **The real cost: Y must rise to hold 21.73Hz constant, and that rise applies at EVERY frequency —
narrowing the peak toward 21-27Hz makes 61-300Hz better but makes the 3-8Hz RATCHET band worse, and
both effects grow together as K2 drops** (K2=6 more-than-doubles the ratchet gain; K2=3 doubles it).
**K2=14 recommended**: 100Hz cut to 71%, 150-300Hz to 65-68%, the lane's own 61Hz peak to 80%, for only
+7.4%@7.79Hz / +2.1%@3Hz — a modest cost against a term the kit's own V96 measurement already shows is
a NET STABILIZER at 6-9Hz (+518/+565ct real damping). K2=16 is the conservative fallback (minimal
ratchet cost, 21-27% HF cut).

## 🛑🛑 CORRECTION (same day, follow-up round) — sector-entry moves DOWN as K2 drops, NOT up
Team-lead hoped lowering K2 would push the 90-180° sector-entry (see the sibling HF-sector-crossing
memory) UP and out of the audible band — a hoped-for "second independent benefit." **A first quick scan
(search floor 40Hz) reported "none" for K2≤8, which was a search-range bug, not a real result.**
Corrected full 0.1-500Hz scan:
```
K2   sector-entry (90-180° begins)   phasor@21.73°
22   74.1 Hz  (today)                 233.64
18   63.9 Hz                          ~223
16   58.9 Hz                          226.30
14   54.0 Hz                          222.77
13   51.5 Hz
12   48.9 Hz                          218.42
10   43.8 Hz                          212.98
 8   38.5 Hz
 3   22.5 Hz                          181.22
 2   18.2 Hz                          174.95  (already crosses AT 21.73Hz -- the GATE-2 floor)
 1   12.8 Hz                          168.45
```
**The sector-entry frequency and the GATE-2 floor (K2≥3, keep 21.73Hz itself dissipative) are the SAME
constraint viewed two ways** — the whole phase curve compresses toward lower frequency as K2 drops, and
the 180° boundary slides down with it, monotonically, no reversal anywhere in 1-500Hz. ⇒ **Real,
previously-unpriced cost: lowering K2 WIDENS the frequency range sitting in the resonance-raising
sector** (K2=14: 54-500Hz vs today's 74-500Hz, +20Hz of coverage) even though it cuts magnitude there.
Net effect on the K2=14 recommendation is still very likely positive (the newly-covered 54-74Hz band's
OWN gain is also reduced, to 80-85% of today's), but "independent second benefit" is wrong — it's a
smaller, bundled version of the same magnitude win, not a separate one. **Generalisable lesson: when a
grid search over a monotonic parameter returns "no crossing found," widen the search range before
trusting it — a bounded scan window silently produces a false negative that looks identical to a real
one.**

## Rail-duty prediction — bounded, not solved [BELIEF where noted]
Railing is monotonic in `|c2c|`, so a ratio ≤1 at every excited frequency would guarantee lower duty —
but the ratio here is >1 at 3-8Hz and <1 at 61-300Hz for every candidate, so the net direction depends
on where route-1e's real spectral energy sits, which is NOT recoverable from percentile statistics
alone (only a real FFT/power-split of the raw `|c2c|` time series settles it). Not attempted — no raw
series available to this session, only team-lead-supplied percentiles.

## Related
[[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]],
[[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]] (the K2=1,2 boundary this
independently reproduces), [[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]]
(the "six pairs" wording this corrects).
