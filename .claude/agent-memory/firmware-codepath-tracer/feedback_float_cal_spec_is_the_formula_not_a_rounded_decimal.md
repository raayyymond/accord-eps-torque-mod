---
name: feedback_float_cal_spec_is_the_formula_not_a_rounded_decimal
description: "For float32 calibration cells the SPECIFICATION is the FORMULA (or >=9 significant digits) -- a 6-dp decimal quoted in prose does NOT round-trip a float32, and hex in a message is never the spec. Root-caused 2026-08-22 on the V105 notch build when THREE agents each encoded correctly and still produced THREE different byte strings for the same coefficient. Includes the full causal chain, because the rule alone reads as pedantry without it."
metadata:
  type: feedback
---

**Rule: when specifying a float32 calibration value, ship the FORMULA at full double precision (or at
least 9 significant decimal digits). A rounded decimal in prose is NOT a specification, and hex in a
message is never one. The receiving agent recomputes from the formula and ASSERTS the
`struct.pack('<f', ...)` round-trip rather than typing the bytes as source.**

## The story — this is the load-bearing part; skip it and the rule reads as fussiness
2026-08-22, designing the V105 26 Hz notch. I solved the biquad coefficients, printed them with `%.6f`,
and sent the orchestrator the decimals **and** the float32 bytes. The orchestrator — correctly applying
its own standing *"compute from the decimals, never copy hex"* rule — recomputed the bytes from my
printed decimals and **got different bytes.** A third agent got a third answer. It looked exactly like an
encoding bug in somebody's build script, on the most consequential build of the session.

**It was not a bug. Every one of us encoded correctly. We encoded three DIFFERENT NUMBERS.**

```
a1  exact from the formula  = -1.8818767088236372  -> float32  56e1f0bf
    printed as "%.6f"       = -1.881877            -> float32  58e1f0bf    <- a DIFFERENT float32

b1  exact from the formula  = -1.9743840279896383  -> float32  9eb8fcbf
    printed as "%.6f"       = -1.974384            -> float32  9db8fcbf    <- a DIFFERENT float32
```

**The precision was lost at my `%.6f` PRINT — upstream of everyone's `struct.pack`.** Six decimal places
cannot round-trip an IEEE-754 float32. Shortest decimals that actually do, for these two:
`-1.8818767` (**8** sig digits) and `-1.97438403` (**9** sig digits).

🛑 **And here is the part that made it genuinely deceptive: `a2` and `c4` survived their 6-dp rounding BY
LUCK** — their rounded decimals happen to land on the same float32. So only 2 of 4 cells disagreed, which
made the failure look **selective**, which made it look like a **bug in one code path** rather than a
systematic property of decimal printing. **A uniform failure would have been diagnosed in a minute; the
lucky survivors are what cost the time.**

## How to apply
- Ship the generating expression — `b1 = -2*math.cos(2*math.pi*25.5/1000)` — not `b1 = -1.974384`.
  ⭐ Embedding the formula in the build script also makes it **self-documenting and re-derivable**: a
  future session re-centres the notch by changing one number instead of reverse-engineering four magic
  floats. That is a better artifact, not just a safer one.
- If a bare number must travel, use `repr()` / `%.17g`, or state the shortest round-tripping form.
- **Tell a byte-exact verifier which encoding is intended**, or it will flag a 1-ULP difference on a
  perfectly good build and burn a cycle.
- 🛑 **But do NOT let it ship either way.** I proposed grading a 1-ULP deviation "cosmetic, not a defect";
  **the operator/orchestrator OVERRULED that, and was right.** Reasons to keep: (1) a re-cut is one cheap
  round trip on a build that gets flashed to a car; (2) **"cosmetic, not a defect" is exactly the phrasing
  that lets a real defect through later** — this kit's record is full of small deviations waved past and
  then cited as precedent; (3) **never silently pass a byte you did not predict.**
  ⇒ **The artifact matches the specification exactly, or it gets re-cut.**
- The standing *"compute from the decimals, never copy hex"* rule is **necessary but not sufficient** —
  it needs *"...and the decimals must be a formula or full precision."*

## ⭐ The generalisation (same class, hit twice in one hour)
Also caught on this build: a builder block whose **comment** read `a2 = R_POLE*R_POLE  # 0.9024999999999999`
while the actual product is `0.90249999999999997` — a different double. **Zero impact on the artifact**
(it is a comment, and both give float32 `3d0a673f`) — but flagged and fixed anyway, because a wrong
comment beside right code is how someone later "corrects" the code in the **wrong** direction.

> **In both cases the failure was not in today's bytes. It was in what a future reader would BELIEVE.**
> That is the class of defect this rule exists to catch, and why it is worth the pedantry.

Applies to every IEEE-754 float cal in this firmware — the `FUN_000352b4` biquad block
`0xC60A8`-`0xC60B4`, the `0xC5xxx` model-coefficient floats, `0xC559C`, `0xC5648`, `0xC664C`, ...
**Integer/Q-format cals are unaffected**; this trap is specific to float cells.

See [[reference_accord_biquad_26hz_notch_design_and_dc_hf_traps]] for the build it arose on, and
[[feedback-run-the-control-before-the-measurement]] — the verifier for that build was itself
control-tested against V104 first, for the same reason.
