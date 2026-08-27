---
name: accord-verify-a-lerp-axis-before-designing-to-it
description: "A LERP's INDEX has been misidentified three times in this kit, each time producing a confident lever proposal against a table the car does not index the way the proposal assumed. Verify the axis from its WRITER, not from a label, before designing any dose."
metadata:
  type: feedback
---

# 🛑 VERIFY A LERP'S AXIS FROM ITS WRITER — three instances, all the same shape

**The table was real, the cells were virgin, the arithmetic was right, and the AXIS was something else.**

| # | table | assumed axis | ACTUAL axis | how it was caught |
|---|---|---|---|---|
| 1 | FactorD (`0xD778C`/`0xD77A4`) | a tracking error | **ABSOLUTE STEERING ANGLE** (`gp-0x6a10`) | the relation held in the **MANUAL** arm, where a tracking error is not even defined |
| 2 | mixer output scale `0xC6ABA`/`0xC6ACA` | raw vehicle speed | **Q15-normalised 0…1 ratio** | X knots are exactly `[0,.2,.4,.6,.7,.8,.9,1.0]×32768`; 32768 ct would be **512 km/h** at 64 ct/km/h |
| 3 | the same table, re-proposed 2026-08-13 as *"the speed LERP on the PID reference"* | vehicle speed | **`gp-0x69aa` = a Q15 governor DERATE product, unity `0x8000`, MIN-only, sole writer `0x45342`** (`mulu` / `shr 0xf` / `st.h`) | instance 2's own correction-of-record, `docs/traces/TRACE-2026-08-10-damping-axis-hunt.md:257`, found by grep |

⇒ 🛑 **Instance 3 is instance 2 repeated by a later session that never found the correction.** The
orchestrator handed a subagent the label *"speed LERP"* and the subagent correctly re-derived the
arithmetic without ever being asked to check the axis.

## WHY IT IS EXPENSIVE

A misidentified axis **does not fail loudly**. It produces a lever that looks **virgin, mode-proof and
well-sized**, and is **INERT BY OPERATING POINT** — the FactorC/FactorE dead-zone failure class.
Instance 3's index is **MIN-only and seeded at unity**, so in normal driving it sits **pinned at the top
knot**: six of its eight Y cells could never have done anything. ⚠ Its `X[7]` also reads `0x8000` =
**−32768 signed**, so the only live knot is degenerate in its own encoding.

## HOW TO APPLY — before designing ANY dose to a table

1. **Find the index's WRITER and read it.** A label in a decompile mirror (`speed_lerp(...)`) is a guess
   by whoever typed it. `gp-0x69aa`'s writer is `0x45342`: `mulu` / `shr 0xf` / `st.h` = a **Q15 product**.
2. **Sanity-check the X knots against a known scale.** Exact fractions of `0x8000` mean a **normalised
   ratio**, not a physical unit. **THE TELL IS THE VALUE** — the same rule that catches off-by-one cells.
3. **Ask where the index SITS in normal driving, not just what it can reach.** A MIN-only quantity seeded
   at unity is **pinned** at unity; a table whose index never leaves segment 0 is a **scalar**, not a schedule.
4. **Grep the kit for the axis symbol before trusting any label.** Instance 3 was already refuted in the
   record and nobody looked.

⭐ **The same discipline applies to a GATE's ENABLE, not only to a LERP's index.** In the same session
`gp-0x6806` was carried as *"the low-speed lockout"* from a memory that had measured a **speed
correlation on a creep-dominated corpus** — where "engaged" and "below 4 mph" are nearly the same set.
It is **the LKAS engagement flag** (`== latActive` on **150,302/150,327 frames = 99.983 %**; written by
`FUN_00028ea6`'s engage-ramp SM alongside `gp-0x3d38 = 3`). **Route `0x85` broke the confound outright**
— engaged p50 **39.6 km/h**, 45.5 s above 80 km/h. **A correlation measured on a confounded corpus is
not an identification.**

⊕ Companion to [[feedback-search-the-kit-before-naming-a-cause]] and
[[feedback-size-probe-rungs-against-lane-reachable-output]]: those say *which signal* and *what value*;
this one says **which AXIS** — and, by extension, **which ENABLE**.
