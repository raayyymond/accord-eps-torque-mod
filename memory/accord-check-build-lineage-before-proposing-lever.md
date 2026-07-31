# 🛑 Check the build lineage before proposing ANY calibration lever — FALSIFIED != untested

**2026-07-27: two independent agents, in the same session, proposed `0xC6450` 1024 -> 32 as a "new,
never-flashed" vibration lever. It is V46 verbatim — flashed, null.** A third nearly repeated it with
`0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the on-car result was buried in prose. This is
the **second and third recorded occurrence** — CLAUDE.md already carried an explicit warning about
`0xC6450`, and it still happened twice in one day.

## The rule
**Before naming any calibration address as a lever:**
1. `grep` it in `analysis-2020accord/build_v*_tva.py`
2. check **`docs/BUILD-LINEAGE.md`** (created for exactly this — a per-address table of what was flashed
   and what it did on-car)
3. **state its on-car result in the recommendation**

Apply this to yourself and put it in every subagent brief.

## 🛑 Fourth occurrence — 2026-07-30, the ORCHESTRATOR, on damper FactorC
Proposed "V61" = `0xD27C6` `Y[0]` 0 → 64. **That is `V44` verbatim** — which used **235**, i.e. 3.7×
stronger — flashed, **NULL**, because **Factor E (`0xC9F84[mode]`) re-zeroes the product downstream**.
`V47` then attacked Factor E itself and got only *"marginally quieter at 5 mph, no effect in motion."*
Both confirmed on-car to hit the LIVE table. `BUILD-LINEAGE.md` already said *"do not resurrect it on a
'wrong variant' theory."* **The operator caught it; the script was written and deleted unexecuted.**

**Two generalisable lessons, both new:**

1. **A withdrawn RATIONALE is not a withdrawn RESULT.** V44's stated mechanism had been retracted (it
   thought FactorC's axis was driver torque; it is voted vehicle speed), and that made the lever *feel*
   reopened. It was not. **Grep the address, do not re-litigate the reasoning.** An on-car null stands
   regardless of why the build was made.
2. **In a multiplicative chain, raising one factor is worthless while any other still zeroes the
   product.** The damper is four chained Q10 multiplies; V44 raised one while Factor E zeroed another.
   **Before proposing a change to one element of a product chain, check every other element.**

⚠ The trigger pattern to watch for: a **new mechanism** makes an **old address** look freshly
motivated. That is the moment the check gets skipped, because the lever feels like a fresh deduction
rather than a rediscovery.

## Why it keeps happening
A structurally sound trace naturally rediscovers the same small set of levers — the analysis can be
*correct* and the conclusion still worthless. **Structural plausibility is not evidence of novelty.** An
agent that has just derived a satisfying mechanism is at its most likely to skip the check, because the
lever feels like its own discovery.

## Corollary — why CLAUDE.md was restructured
The fact was *present* in the old 704-line CLAUDE.md but not *findable*. On 2026-07-27 the operator
directed a restructure into an index with progressive disclosure, and `docs/BUILD-LINEAGE.md` was created
as a lookup table. **Keep flashed results in a table, not in narrative.**

Related: [[reference-accord-c646c-shared-gain-not-lkas-only]],
[[reference-accord-vibration-needs-applied-torque]], [[reference-accord-fourframe-strb-ssam-defect]].
