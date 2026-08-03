# feedback — ground EVERY session in the golden model AND the post-V38 arc

**Operator instruction, 2026-08-03. Standing, for all investigation and firmware-fix sessions.**
Recorded in `CLAUDE.md` under "READ FIRST".

Every investigation or firmware-fix session must take into account **both**:

1. **`analysis-2020accord/eps_lkas_chain_model.py`** — the golden model of the **entire** EPS/LKAS
   driver-assist chain, end to end. A lever is not understood until you can say **where it sits in the
   chain, what feeds it, and what it feeds**. Keep the model updated when data beats it.
2. **All recent effort since V38, read as ONE ARC** — `docs/BUILD-LINEAGE.md` plus the whole
   `HANDOFF-*.md` chain, **not** just the latest handoff.

**Prime every subagent with both.** This is in addition to the standard priming block (GhidraMCP only,
`gp=0xFEDF8000`, `tp=0xBF000`, the relevant confirmed findings).

## Why

- The kit's strongest evidence form is a **dose-response across four or more builds** — e.g. grind #1 at
  Kd = 0 (V61) / 1.00× (V58+V59+V64) / gated (V67) / 2.00× (V62+V65). That structure is **invisible**
  from one session's slice, and a route mis-assigned to a dose corrupts it.
- **Direction matters as much as identity.** V39, V42 and V61 all tested the rate lane **downward**; the
  gradient pointed **up**, and V62 — the kit's first measured fix — came from finally pushing the other
  way. Reading a slice hides which way a lever has been pushed.
- Recorded failure mode: **two agents in one session re-proposed an already-flashed, already-falsified
  lever** because the result was buried in prose. Also `V44`/`V47` (FactorC/FactorE damping) was
  re-proposed as "V61" on 2026-07-30 and the operator caught it.

## How to apply

Before proposing or evaluating any lever, and in every subagent prompt:
- Locate the lever in the golden model's chain.
- Read the post-V38 arc, and **grep `analysis-2020accord/build_v*_tva.py`** for the address — state its
  on-car result **and which way it was pushed**. FALSIFIED ≠ untested; one-way-tested ≠ falsified.

Related: `accord-check-build-lineage-before-proposing-lever.md`,
`feedback_eps_lkas_chain_model_golden_reference.md`,
`feedback-delegate-firmware-tracing-to-subagents.md`, `feedback-episodes-not-windows.md`.
