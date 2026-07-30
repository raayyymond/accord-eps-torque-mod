# Golden model distilled 2026-07-29 — keep comments/docstrings terse going forward

`analysis-2020accord/eps_lkas_chain_model.py` had ballooned to 4,709 lines / 347 KB — comments and
function docstrings had grown into full research essays (dated "LATEST" changelogs, multi-hundred-line
findings reports embedded in docstrings, e.g. `vibration_hands_off_analysis` alone carried a ~430-line
docstring). Operator instruction: distill it back to pseudocode + terse address ties.

**Result:** 4,709 → 2,200 lines (347 KB → 145 KB). Verified two ways before accepting: (1) an AST-equality
diff (module/class/function bodies with only the leading bare-docstring statement stripped) proved zero
code changes — only docstring text differs; comments aren't part of the AST at all; (2) `python
eps_lkas_chain_model.py` (`_self_check()` + `_demo()`) produced byte-identical stdout before and after.

**Standing rule, going forward:** inline `#` comments ≤1 sentence; function/class docstrings ≤1
paragraph — state what the code models, the memory address(es) tied to it, a confidence tag
([CONFIRMED]/[VERIFIED]/[INFERRED]/[OPEN]) if relevant, and any non-obvious Q-format/branch-condition
note needed to read the arithmetic. The full narrative belongs in `docs/HANDOFF-*.md`, `docs/STATE.md`,
`docs/BUILD-LINEAGE.md`, and `memory/` — not in the model file. When a new finding lands, put the terse
fact in the model and the story in a handoff, not both in the model.

**Two content corrections made in passing** (not just compression):
- A stale "4-of-16 phase-gated" reading survived in a couple of spots even though the module docstring's
  own EXECUTION MODEL section had already corrected it to "state-gated, not phase-gated" — removed rather
  than perpetuated.
- Two of the densest functions (`vibration_hands_off_analysis`, `motor_torque_governor`) were left at
  ~20-28 lines rather than a strict one-liner, because they carry the two most load-bearing CONFIRMED
  root-cause chains in the file (the V44 damping fix and the V42 ratchet fix) and a stricter cut risked
  losing addresses/formulas future sessions will need. Revisit if the operator wants them terser still.

See `docs/HANDOFF-2026-07-29-golden-model-distillation.md` for the session narrative.
