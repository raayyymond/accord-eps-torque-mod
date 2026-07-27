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
