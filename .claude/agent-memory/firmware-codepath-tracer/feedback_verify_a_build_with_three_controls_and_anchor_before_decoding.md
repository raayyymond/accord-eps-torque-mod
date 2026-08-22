---
name: feedback_verify_a_build_with_three_controls_and_anchor_before_decoding
description: "How to verify a built firmware image so the PASS actually means something: three controls (all-different, nearly-identical, synthetic-correct), expectations DERIVED FROM THE FORMULA rather than typed constants, and ANCHOR any blob before decoding its offsets. Method that produced the first fully-characterised PASS of the 2026-08-22 session (V105), agreeing with an independent second leg on every quantity."
metadata:
  type: feedback
---

**Rule: a verifier is an instrument, and an instrument is worthless until it has been characterised.
Before a PASS on a real artifact is allowed to mean anything, run three controls, derive every expected
value from the formula, and anchor any blob before decoding its offsets.**

> ⭐ **"A verifier that rejects two wrong builds tells you nothing until it accepts a right one."**

## The three controls — all of them, in this order
| control | what it is | what it proves | V105 result |
|---|---|---|---|
| **all-different** | the unmodified base image (V104) | the checks fire at all | **16 correct FAILs** |
| **nearly-identical** | a superseded build differing only in the target quantity (the 26.0 Hz cut) | it discriminates, and does **not** over-trigger | **11 correct FAILs, 0 false positives** |
| **synthetic-correct** | the superseded build's body patched with the correct values, in the **scratchpad**, CRC deliberately left stale, named `POSCTRL_NOT_FLASHABLE_...` | **it can PASS** | **0 failures** |

🛑 **The nearly-identical control is the one that earns the PASS.** It was a *good* filter — DC, stability,
ring and `max|H|` all held — and only the design target was wrong. **A harness leaning on safety
properties alone would have passed it.** The discriminating assertions turned out to be the zero
frequency and `|H|` at 24.9 / 25.5 / 26.8 Hz, which separated the two builds by 2-20x; `|H(7.79)|`
separated them by only 0.0018 and is a *safety* assertion, not a discriminating one. **Know which of your
checks are which.**
⚠ The positive control must be **impossible to mistake for a build artifact**: scratchpad only, explicit
`NOT_FLASHABLE` name, and deliberately-invalid CRC.

## Derive expectations from the formula, never from typed constants
My first harness hardcoded `(7.79, 0.9863), (21.0, 0.4922) ...` — 4-dp numbers I had typed, needing a
2e-3 tolerance. Replacing them with a reference transfer function recomputed **from the formula** allowed
**1e-6**, and immediately converted a weak assertion into a real one (the 26 Hz build's `|H(7.79)|`
deviation of 1.78e-3 went from PASS to FAIL). On the real artifact all five deltas came back
**exactly 0.00e+00** — proof the built floats reproduce the formula bit-for-bit, which a tolerance-based
check could never have shown. Same rule as
[[feedback_float_cal_spec_is_the_formula_not_a_rounded_decimal]], applied to the instrument instead of
the build.

## 🛑 ANCHOR A BLOB BEFORE DECODING ITS OFFSETS
A headerless extract has no base. **Do not map its file offsets onto an image address** — that yields a
plausible, specific, wrong address and does not error. Instead:
```python
i = image.find(blob)      # i >= 0  -> base is i, and program offset N == absolute i+N
                          # i <  0  -> not a contiguous slice; offset arithmetic is MEANINGLESS
```
This exact defence, applied one hour after being written up, was what made the V105 Ghidra leg sound: a
164-byte cave extract with `image_base 00000000` anchored to **`0xC4B34`**, so `0xC4B36` was read at
program offset `0x02` rather than at `0x C4B36`. **Skipping it an hour earlier had produced a false `b5`
alarm on the session's most consequential build.** See
[[reference_v850_ghidra_cal_read_rendered_as_function_symbol_trap]] Companion trap 3.

## Report discipline that made the PASS auditable
- **Report actual deltas, not PASS/FAIL** — `|d| = 0.00e+00` carries information a green tick does not.
- **Promote the load-bearing bytes to their own named lines.** Two of V105's checks were the whole build:
  the **dose gate** (`0x55DF2` = `0x7a`, the CAN 427 tap on `gp-0x6b86` — wrong and the drive is
  uninterpretable) and the **`b5` non-eviction** (`0xC4B64`/`0xC4B70`, asserted **positively** against the
  base, never inferred from an absence of diff). Buried in a list of six they would have been skimmed.
- **Attribute every differing byte.** V105: 24 bytes / 8 runs, all attributed, CRC trailers asserted as
  *updated* rather than merely tolerated.
- **State the Ghidra program discipline in the report**: `list_open_programs` first (four were open and
  the current was **not** `code.bin`), `switch_program` deliberately, `dry_run: true`, no `close_program`,
  nothing saved.
- **Never `save_program` after exploratory disassembly**, and never let the verifier mutate the artifact.

Pairs with [[feedback-run-the-control-before-the-measurement]] (control the instrument) and
[[feedback_audit_your_own_claims_before_others_act_on_them]] (audit the claim it produced).
