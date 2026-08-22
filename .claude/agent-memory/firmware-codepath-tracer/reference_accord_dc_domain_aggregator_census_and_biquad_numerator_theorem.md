---
name: reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem
description: Two results from the V104 steering-feel-impact task (2026-08-22). (1) DC-domain (not 6-9Hz AC) classification of all 11 terms in FUN_0003aa2c's aggregator sum -- which lanes are driver-torque-proportional (DC-capable, nonzero at a steady hold) vs rate/acceleration-only (zero at steady hold) vs openpilot's own LKAS command (not driver effort at all); gp-0x6b86 has the WIDEST single-lane ceiling (+-12288) in the whole sum, wider than the final aggregate clamp (+-10240) itself; fresh decompile of FUN_00036682 (the 11th, ungated summand) shows it is internally self-limited to ~+-512, not a large hidden DC term. (2) A numerically-verified theorem about FUN_000352b4's biquad topology: because the numerator is hardwired palindromic (1+b1 z^-1+z^-2, leading/trailing coeffs are bare adds, no multiply -- opcode-confirmed), NO (a1,a2,b1,c4) quadruple in the entire stable coefficient space reaches |H(7.79Hz)| above ~1.19x while holding |H(0)| within +-2%; reaching 1.8x at 7.79Hz requires an explicit near-degenerate pole-at-7.79Hz design with +104.5 deg phase and 1.4+ cycles of ring, plus a numerator forced to b1=-1.999 (near its own singularity) producing a wrecked passband shape (crushes 5Hz, then rises monotonically past 15Hz). Includes the exact quadruple + LE float32 bytes for that disqualified design, for reference if anyone proposes it later.
metadata:
  type: reference
---

# DC-domain aggregator census + the biquad numerator's structural boost ceiling — 2026-08-22

`feel-impact` task (team-lead orchestrated), quantifying V104's (`0xC60B4` c4 boost, 0.81731->1.51202,
x1.85) steering-feel impact. Program: stock `code.bin` (V104's only edit is this one coefficient, no
cave/control-flow change, confirmed via `build_v104_tva.py` grep — this trace transfers to V104
unmodified). Fresh `decompile_function` on `FUN_0003aa2c` (0x3aa2c) and `FUN_00036682` (0x36682) this
session, cross-checked against `reference_accord_gp67ac_reduced_branch_unreachable.md` /
`reference_accord_gp67ac_resolved_zero_and_path1_always_live.md` (both already proved, two independent
ways each — deterministic code trace AND boot-flash-value read — that the aggregator's reduced-sum
branch can NEVER fire; the FULL 11-term sum below is what always executes, every tick, every build).

## 1. The full 11-term Path-1 sum, classified for DC (steady-state / driver-holds-a-turn) content

```c
// FUN_0003aa2c, full branch (gp-0x67ac provably always 0, see the two memories above):
iVar19 = iVar9(gp-0x6ade) + iVar19(gp-0x6b4c) + gp-0x6ad4 + iVar14(gp-0x6b62)
       + gp-0x6b26 + gp-0x6bbe + gp-0x6bd0 + gp-0x6b86 + iVar21(r24) + iVar16(r26)
iVar14 += FUN_00036682()
sum = clamp(iVar19+iVar14, +-0x2800)   // +-10240, THE FINAL AGGREGATE CLAMP -> gp-0x6b94
```

| lane | zero-reject window | DC character [EVIDENCE unless noted] |
|---|---|---|
| gp-0x6b62 (return-centre) | +-8192 | measured DUTY 0.0000 while engaged, 75,227 frames (prior memory) — ~0 whenever the c4 boost is even armable |
| **gp-0x6b4c (LKAS command x4)** | +-10240 | **openpilot's own steering demand**, NOT driver torque — confirmed via `reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map.md` ("the 4x -> gp-0x6b4c only"). DC-capable but is not "driver effort." |
| gp-0x6ade | +-1024 | permanently dead, 0 writers (same-day sibling memory) |
| gp-0x6ad4 (Path-2 PID output) | +-10240 | DC-capable (torque-tracking error), a separate closed loop — magnitude NOT re-derived this session [BELIEF: structure known, typical value not] |
| gp-0x6b26 (friction-comp) | +-1024 | = -K*(motor-rate ACCELERATION), prior memory -> ~0 at steady hold |
| gp-0x6bbe (boost) | +-2048 | SAME-DAY reversal (a sibling task, same date): prop. to -K1*(column RATE) -> ~0 at steady hold. NOTE: an older memory called this "viscous+DC pedestal, p50 73.6ct flat" — tension with today's re-derivation flagged, not resolved here. |
| gp-0x6bd0 (damping) | +-2048 | reverted to byte-identical Honda stock this session (0 diffs vs V103, sibling same-day memory) |
| **gp-0x6b86** | **+-12288 — WIDEST single-lane ceiling in the sum, wider than the FINAL AGGREGATE CLAMP (+-10240) itself** | DC-capable by construction (torque-map-driven feedforward) — see `reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved.md` Round 3 |
| iVar21 (r24-derived) | +-8192 | separate well-covered topic (grep `*r24r26*` in MEMORY.md), not re-traced into this DC picture this session [BELIEF] |
| iVar16 (r26-derived) | +-8192 | same [BELIEF] |
| FUN_00036682() | **no external gate — added unconditionally** | see section 2 below: internally self-limited, NOT a large hidden term |

**Structural fact worth flagging for any future lane-weighting question**: `gp-0x6b86` alone, near its
own ceiling, can single-handedly saturate the ENTIRE aggregate (12288 > 10240) — no other single lane
has that property (the next-widest, gp-0x6b4c/gp-0x6ad4, are exactly at the aggregate's own clamp, not
past it).

**What this does NOT close**: a validated "% of the DC total" number for `gp-0x6b86`. No simultaneous
multi-lane telemetry exists in the corpus as far as searched this session. Best empirical anchor:
`docs/HANDOFF-2026-08-21-v104-built-c4-boost-and-lever-b.md` §4.3's flown clip-duty study (V102/V103,
1704s across 5 builds) measured `gp-0x6b86`'s own worst observed excursion at k=1.85 as **6799/12288
(~55% of its own ceiling)**, clip duty 0.000000. **Closing this needs a comparator cave rung
(`|gp-0x6b86|` vs `|gp-0x6b94|`) or simultaneous multi-lane telemetry** — cheap, matches the kit's own
comparator-over-threshold design law.

## 2. `FUN_00036682()` — the 11th, ungated summand — decompiled fresh, is NOT a large hidden DC term

Complex rate-limited/hysteresis tracker, uses `gp-0x4f60` (same raw torque sensor as `gp-0x6b86`'s own
input) scaled by cal `0xC646C` (`tp+0x746c`) — **the SAME shared sensor-scale cell already on record**
(`reference-accord-c646c-shared-gain-not-lkas-only.md`, "6 readers across 3 subsystems", now a 7th
confirmed use). Internally: builds an intermediate `iVar8` self-clamped to +-0x200(512) before a final
first-order IIR (`iVar14 += (iVar8*0x400-iVar14)*cal(tp+0x73d2)>>10`, output `sVar10=iVar14>>10`). At
steady state the EMA just tracks its input 1:1, so **the function's own output ceiling is bounded to
roughly +-512** by this internal clamp — **~24x smaller than `gp-0x6b86`'s +-12288 ceiling and ~20x
smaller than `gp-0x6b4c`'s +-10240**, regardless of it having no external gate. Exact typical value NOT
resolved (would need cal `tp+0x746c`/`tp+0x73d2`/`gp-0x6b48`/`gp-0x6b44` numeric values, not pulled this
session) — but the STRUCTURAL ceiling rules out it dominating the sum.

## 3. The biquad numerator's structural boost ceiling — verified by direct numerical sweep, not cited

`H(z) = c4*(1+b1*z^-1+z^-2)/(1+a1*z^-1+a2*z^-2)`, fs=1000 (matches
`reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md` and this session's own
fresh disassembly — numerator leading/trailing coeffs are bare `addf.s`, no multiply, confirmed
hardwired to 1.0, not cal-editable).

**Python/numpy brute-force sweep this session** (not a relay of anyone else's closed-form claim):
a1 in [-2,2], a2 in [-1,1], b1 in [-2,2] on a 241-point grid each; filtered to the standard discrete
2-pole stability triangle (`|a2|<1`, `a1<1+a2`, `a1>-(1+a2)`) -> 14,214 stable (a1,a2) pairs; c4 solved
EXACTLY from the `|H(0)|=1` constraint at every (a1,a2,b1) -> 3,227,381 valid stable+DC-pinned
combinations swept.

**Result: max |H(7.79Hz)| anywhere in this space, subject to |H(0)| within +-2%, is only ~1.187x.**
Zero of 3.2M combinations reach 1.8+-0.05. This is a genuine THEOREM about the topology (verified by
direct search, not intuition): **with a hardwired-palindromic numerator, you cannot selectively boost
6-9Hz without either raising DC (the c4 route V104 takes) or placing a pole essentially AT the target
frequency** — and even that route is disqualified:

```
Exact quadruple bisected to hit |H(7.79Hz)|~1.80 via pole-AT-7.79Hz, |H(0)|=1 pinned:
  r=0.975000  a1=-1.947665  a2=0.950625  b1=-1.999048  c4=3.110766
  |H(0)|=1.000000   |H(7.79Hz)|=1.799794   phase=+104.49 deg
  ring time to 1% = 181.9 ms = 1.42 cycles at 7.79Hz
  LE float32: a1=134df9bf  a2=295c733f  b1=d1e0ffbf  c4=cc164740
```
b1 is forced to -1.999 (the numerator's own near-degenerate singularity, |Num(0)|~=0.001) to make room
for the pole to do the work — and the resulting shape is NOT a clean band-boost: it near-notches 5Hz to
|H|=0.043, then RISES MONOTONICALLY past the target band, sitting at 3.2-3.3x from 15-30Hz and never
rolling back down (checked 1-30Hz explicitly). Phase +104.49 deg is not a lead, it is functionally an
inversion near the pole. Ring of 1.42 cycles at the excited frequency matches (independently, different
derivation) an already-recorded "~1.2 cycles of 8Hz ring" figure to the same order.

**Practical use**: if anyone proposes a "smarter" pole/zero placement to fix 6-9Hz without V104's flat
DC raise, this sweep is the pre-registered null — re-run `analysis-2020accord/`'s copy of the sweep
script (not yet committed to a shared script path this session; regenerate from this file's method if
needed) before spending build effort on a pole-relocation design.

🛑 **The global-max-1.187 solution CANNOT be substituted as a flat `k=1.187` into any dose model priced
against `c4`'s own perturbation** (e.g. an `a_filt`-style scalar sensitivity measured from arming/
disarming the STOCK biquad shape). That solution's `(a1,a2,b1,c4)` sits at `a1≈-1.967,a2≈0.983`
(pole essentially AT DC, not near 7.79Hz) with `b1=+2.0` (a zero at Nyquist) and `c4≈0.004` — its
`ΔH(f)` shape is NOT proportional to `c4`-alone's `ΔH(f)=(k-1)·H_stock(f)`. A same-shape assumption is
implicit in any single-scalar dose sensitivity; this solution violates it, so its peak magnitude alone
does not transfer into that kind of model. Raised 2026-08-22 in the `feel-impact` task when the
orchestrator asked whether "1.187 sits below a 1.545 Re(Z) crossing, therefore harmful" — the orchestrator
retracted that inference on this basis. See
[[reference_accord_v104_share_bound_and_tq_discriminator_results]] for the fuller exchange.

## Related
[[reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved]] — Round 3 of that file
(same task, same day) resolves the companion question (does gp-0x6b7e dilute the c4 boost — no, and its
EMA timing). [[reference_accord_gp67ac_reduced_branch_unreachable]] /
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] — the two independent closures this
file's lane table depends on. [[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]]
— the notch characterization and the flat-EMA-LERP byte-read this file's section-1 gp-0x6b86 entry and
the Round-3 sibling file both lean on.
