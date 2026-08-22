---
name: feedback_audit_your_own_claims_before_others_act_on_them
description: "PRACTICE, not just an incident list: after making a decision-bearing claim, go back and check it yourself before anyone builds on it. On 2026-08-22 this caught four of my own errors in one session -- a cal mis-described as a gain, a 'novel lever' that was the wrong shape, a stale line in my own memory file, and a false alarm I had raised myself. The orchestrator called it the most valuable habit shown that day."
metadata:
  type: feedback
---

**Practice: a claim you have just made is the one most likely to be wrong and least likely to be
checked. After stating anything decision-bearing, go back and verify it YOURSELF — especially when it
has already been accepted, and especially when it is your own flag, your own lever, or your own memory
file.**

**Why:** the orchestrator's words, 2026-08-22 — *"That is the single most valuable habit anyone has shown
today... Two agents were retired today partly because claims they made early went unchecked and had to be
unwound by others; you have been unwinding your own."* In a no-false-summits domain the cost of a wrong
claim is paid by whoever acts on it, and the cheapest moment to catch it is before that happens.

**Four catches in one session, all self-inflicted, all caught by re-checking my own output:**
1. **`0xC6202` = 4762 mis-framed as a "Q10 x4.65 gain".** It is a **MIN/ceiling**; the `/1024` decode and
   `*1024` re-encode cancel. Found by re-reading the decompile I had already quoted from. Changed the
   governor swing from 10.4x to **9.30x**.
2. **A "genuinely novel lever" I proposed and then killed.** I pitched reviving `cal(0xC63CC)`=0 as
   switching on a dormant LKAS slew limiter. Re-checking the structure showed the rate-limited state is an
   **additive term**, so enabling it ADDS command content rather than filtering it - the opposite of the
   intent. **Reported the correction before it reached a build.**
3. **A stale line in a memory file I had written 20 minutes earlier**, which by then contradicted an
   explicit ruling ("1-ULP deviations are cosmetic" after being told to hold the line and re-cut).
4. **A false alarm I raised myself** - that a cave repoint would cost the notch's `|gp-0x6b86|` dose gate.
   A census showed **zero** `gp-0x6b86` readers inside the cave and the tap living at `0x55DF0` in the CAN
   packer. **Retracted with evidence within the hour.** ⭐ And the retraction produced something better
   than the flag: `0x55DF2` = `0x7a` **IS** the dose gate, not the routine bookkeeping line it had been
   listed as - one byte separating a decisive build from a wasted drive.

**How to apply:**
- **Grade first, then re-check the EVIDENCE-graded ones too.** The EVIDENCE/BELIEF split tells you what to
  re-check first; it does not exempt anything.
- **Re-check your own memory writes**, not just your messages - a file written this session can already
  contradict a ruling made since.
- **Retract loudly and early.** *"I raised this, I checked it, it is wrong, here is the evidence"* costs
  one message; a phantom constraint carried into a build costs a drive.
- **This is distinct from [[feedback_check_own_memory_before_retracing_and_variable_reuse_trap]]** - that
  one is about reading memory *before* work; this one is about auditing your own output *after* it.
- Pairs with [[feedback-run-the-control-before-the-measurement]]: control-test the instrument, then
  audit the claim the instrument produced.
