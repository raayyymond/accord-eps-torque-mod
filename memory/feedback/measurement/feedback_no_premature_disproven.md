---
name: feedback_no_premature_disproven
description: "Operator calibration (2026-06-01): before declaring anything 'disproven / doesn't-exist / dead / blocked', ask whether that's positively established or whether I'm rushing to a negative verdict to end a long, uncomfortable search. Absence of evidence != evidence of absence. Use three states: confirmed / disproven-with-evidence / UNRESOLVED."
metadata:
  type: feedback
---

# Don't say "disproven" to end a long search

**The rule (operator, 2026-06-01):** Every time I'm about to say *disproven /
doesn't-exist / dead / blocked / impossible*, stop and ask: **is this true, or am I
jumping to a negative conclusion because the search is taking too long / I'm
frustrated?** A negative verdict is a strong claim that needs **positive evidence of
absence** (an exhaustive reachable-path search that came back empty; a structural
reason it cannot exist). "Zero hits so far," "I didn't find it," or "this is taking
forever" = **UNRESOLVED**, not disproven.

**Why (load-bearing):** in this project, premature negatives have repeatedly been
WRONG.
- The framing-audit horde returned `really_blocked = EMPTY` — almost every laptop
  "blocked" was a tooling/framing artifact, not a real block. [[reference_laptop_uds_framing_bug]]
- I led horde w15p1o3qh with "0x3E god-mode DOES-NOT-EXIST" — over-flattening a verdict
  whose own body left the programming-session path UNCONFIRMED and found the Civic
  carries the same dispatcher bytes as Clarity. [[reference_sa_dispatch_crossimage_verdict]]
- The "Clarity has more SA levels" claim I'd have dismissed turned out byte-true.
- "0x07/0x08 dead on A030" was really "not on the *default-session* demux" — a different,
  narrower, true statement than "dead."
Absence of evidence ≠ evidence of absence. The cost of a false "disproven" here is high:
it stops the operator from pursuing a real path.

**How to apply:**
- Three-valued verdicts everywhere: **confirmed / disproven-with-evidence / unresolved.**
  Default to *unresolved* when the search was not provably exhaustive.
- Reserve "disproven/doesn't-exist" for affirmative absence-evidence; otherwise say
  "not found yet via X; would need Y to settle it."
- Lead reports with *what's established + what's still open*, never a flattened negative
  headline that buries the open thread.
- In adversarial verify agents: a skeptic's "couldn't confirm" must NOT collapse into
  "disproven." Weight the confirm-side search; treat a refute default as "not-yet-found"
  unless it cites exhaustive evidence.
- This is the same failure mode as laptop Claude "giving up too easily," but in MY
  reasoning. Watch for it under time pressure / fatigue framing.

**Recurring traps (2026-06-01, caught by operator TWICE in one session):**
- **The evidence must COVER the question to close it.** If the deciding region is *outside* the bytes
  examined — on-chip **mask ROM** (e.g. A030 boot vector 0xFFF84000, absent from the flash dump), or
  **live runtime behavior** — then "not found in flash" = **UNRESOLVED**, never DISPROVEN. Name the
  arbiter (here: each EPS into god-mode + hard-reset boot-mode, tested live). Static narrows; it
  doesn't close what it can't see. (I wrongly headlined the x11/boot-mode hypothesis "DISPROVEN".)
- **Never infer behavior from a NAME/convention — read the bytes.** UDS "RequestDownload (0x34)"
  sounds like write, but data DIRECTION is implementation-defined; I asserted "no UDS read-out" from
  the service name instead of tracing the 0x36 memcpy direction. Same class as the disproven-bias:
  a confident label standing in for verification.
- **A different SAMPLE/REGION lacking X ≠ the target lacks X — especially BOOTLOADERS** (operator,
  2026-06-01). I found A030's bootloader has no 0x35 and generalized to "the C120 family has no UDS
  read-out, probably needs physical." Wrong twice: (a) C120's bootloader is UNMAPPED (zero C120 BL
  bytes) — UNKNOWN, not absent; (b) bootloaders vary WITHIN a family (Tier-1 supplier rev / plant /
  era / team) — PROVEN here: the V850 Accord BL HAS 0x35 while the A030 BL does NOT. Cousins don't
  settle the target, especially in the BL/integrity/boot layers that are often supplied separately.
- **Hacker posture: assume a path EXISTS and find it; don't declare a floor from a cousin's absence.**
  Calibration ("every specific claim byte-grounded") and hacker-mentality ("assume reachable, keep
  hunting") are NOT in tension — the failure is sliding from "this sample lacks X" to "X is probably
  unreachable / we'll need the hard fallback." Keep three-valued AND keep searching.

Sibling: [[feedback_rigorous_validation]] (full diff > spot diff; ghidra before victory)
— this is its mirror: don't claim *failure/absence* prematurely either.
