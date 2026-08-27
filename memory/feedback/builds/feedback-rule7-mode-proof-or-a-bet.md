# 🛑🛑 RULE 7 — a lever is MODE-PROOF, or it is a BET

**Adopted 2026-08-05, `docs/BUILD-LINEAGE.md`.** Classify every lever before proposing it.

- **MODE-PROOF** — code edits, and `tp` scalars reached **without an index**: `0x3AB76`/`0x3AC20` (the
  `sar` sites), the `0x3AA96` gate, `0xC6446`/`0xC6444`, `gain_A` `0xC6A68`/`0xC6A7C`, `0xC407E`.
- **MODE-INDEXED** — anything reached through a `mode*4` pointer array: `gain_B`
  (`0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`), FactorC `0xC9E9C`, FactorE `0xC9F84`, the friction records
  `0xCBE74`, the ceiling `0xC77A0`.

★★ **EVERY MEASURED FIX IN THIS KIT CAME FROM A MODE-PROOF LEVER; EVERY MODE-INDEXED LEVER WAS INERT.**

**Why:** the car is `TVCA4`, modes 24/26 — not the 10/11 assumed for a dozen builds
([[reference-accord-car-is-tvca4-mode-24-26]]). A mode-indexed edit written at the wrong mode is **not a
weak lever, it is NO lever**, and it looks flashed, verified and driven. It cost V44, V47, V72's Levers
B/C, both of V73's levers, and the entire r24 dose of V69/V70/V72/V73 — and it manufactured a
"dose–response" that never existed.

**How to apply:**
1. Before naming any address, ask *"is this reached through a `mode*4` pointer array?"* Dereference the
   array on the image; do not infer from the address alone.
2. If mode-indexed: **write every mode, or probe the selector.** There is no third option. Prefer the
   **engaged columns (e014/e015) of all 16 rows** — those sets are disjoint from the disengaged ones, so
   dosing them leaves manual byte-stock and is robust to the row inference.
3. Record the classification in the build's own docstring, next to the address.

## 🛑 Two corollaries, both earned the hard way

**(a) Several "symptoms" this kit chased were created by its own earlier fixes.** Grind #2 is V62's
`sar` — a grind-#1 fix. Stock has no grind #2; near-stock builds have no grind #2. The operator reached
this independently: *"Grind #2 was never an independent issue. It only ever came to be through some
proposed fixes for grind #1."*
⇒ **Before adding a lever for symptom X, check whether X first appeared in the build that introduced the
previous lever.** *A build that changes nothing is a real and sometimes correct option*, and "retain the
fix" can mean **an absence** — do not reintroduce the thing that caused it.

**(b) "FALSIFIED" must name the SYMPTOM.** V42 ch.2 was filed *falsified* — against the **vibration**,
never scored against the **ratchet** — and it turns out to be V42's actual fix
([[reference-accord-v42-fix-was-the-r26-kill]]). V47 was filed *null* against the 21 Hz vibration and
never against the ratchet. **Both were live levers retired for the wrong question**, two years apart in
the ledger. A verdict without a named symptom is not a verdict.

Related: [[accord-check-build-lineage-before-proposing-lever]], [[accord-damper-is-mode-table-selected]],
[[feedback-probe-the-gate-not-just-the-output]].
