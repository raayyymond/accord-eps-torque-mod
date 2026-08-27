---
name: reference-accord-vibration-levers-falsified-vs-untested
description: The ~21 Hz vibration levers split into VALIDLY-FALSIFIED (cal-only lane cuts that flashed+drove) vs UNTESTED (the gp-0x4f60 signal-filter — V48B bricked catastrophically before testing efficacy, V50 never flashed). Filtering the shared torsion-bar signal to kill the buzz is the leading OPEN hypothesis, not a dead one.
metadata:
  type: reference
---

When reasoning about the ~21 Hz LKAS vibration, keep two categories strictly separate (operator correction,
2026-07-24 — a build that catastrophically FAILED did not TEST its lever):

**VALIDLY FALSIFIED (flashed cleanly, drove, observed no effect) — all CAL-ONLY, lane-specific cuts:**
- r24 direct Sensor-B rate lane — V39.
- r26 adaptive rate lane — V42 (Change 2).
- `FUN_0003a382` Stage C / dirty-derivative pole `0xC644A` (1024→32) — V43.
- `FUN_0003a382` Stage A pole `0xC6450` (1024→32, "~4.8 Hz low-pass") — V46.
- ~~hands-off damping (Factor C, V44; Factor C+E, V47).~~ 🛑 **STRUCK 2026-08-06 — STALE AND VOID UNDER
  RULE 7.** V44 and V47 wrote **modes 10/11** on a **modes-24/26** car
  ([[reference-accord-car-is-tvca4-mode-24-26]], [[accord-damper-is-mode-table-selected]]) ⇒ their edits
  were **never in force**; the nulls are **UNINTERPRETABLE, not falsifications.** **The FactorC/FactorE
  damping approach was never actually tested until V74** — which then measured a real, band-specific
  dose-response ([[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]]). Do **not** cite V44/V47
  to block a damper lever.
These are REAL falsifications — do not re-propose them. ⚠ **`0xC6450` and `0xC644A` are BOTH dead**: the
`FUN_0003a382` → `gp-0x6ad4` "resonance lane" was tested via BOTH its poles and neither moved the vibration.
(A 2026-07-24 backward-chain trace `foc-backward-map` mis-ranked `0xC6450` as a "genuinely new, untouched"
top lever — WRONG, verified against `builds/v18_v49/build_v46_tva.py`/`builds/v18_v49/build_v47_tva.py`; that agent's structural aggregator
map is good, its filter ranking is not.)

**UNTESTED (never got a valid on-car efficacy test) — the CODE-CAVE filter of the shared torsion-bar signal
`gp-0x4f60`:**
- **V48B** (21.4 Hz notch on a filtered copy of `gp-0x4f60`) was FLASHED → **CATASTROPHIC brick** (full-
  authority wheel oscillation) from a RAM collision (`gp-0x14FA`) + an unmodeled closed-loop resonator. It
  bricked BEFORE it could demonstrate whether the notch attenuates the buzz → **efficacy untested.**
- **V50** (first-order EMA low-pass on `gp-0x4f60`) was **never flashed** (`gp-0x1500` is a live I/O-mailbox
  writer — see [[reference-accord-b7260-io-mailbox-array]]) → **untested.**

**Consequence:** "filter `gp-0x4f60` to kill the 21 Hz" is the **leading OPEN hypothesis, NOT falsified** —
and the most physically plausible one, since `gp-0x4f60` is the torsion-bar sensor picking up the mechanical
resonance and feeding most base-assist lanes. The operator's 2026-07-24 strategy refines HOW to do it: filter
**as late and as few signals as possible** (one late summand producer output), not V48B/V50's early/broad
"filter the root feeding 7+ carriers." The four-frame telemetry (`builds/telemetry/build_vfourframe_tva.py`, logs the
FOC-setpoint-backward contribution list) exists to identify WHICH lane carries the 21 Hz first, so the filter
lands on the right signal, late, once — instead of guessing (which has failed on every lever above). See
[[reference-accord-can-tx-architecture-new-id]] and [[feedback-account-for-prior-iterations-before-new-build]].
