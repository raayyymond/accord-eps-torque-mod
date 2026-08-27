---
name: stress-test-external-llm-advice-2026-06-03
description: "When Joey relays external-LLM (Gemini) advice on firmware, stress-test every load-bearing claim against the actual binary BEFORE implementing — it has been confidently wrong repeatedly. External AI is a good idea generator but a poor oracle for car-bricking specifics."
metadata:
  type: feedback
---

# Stress-test relayed LLM advice against the bytes before implementing

**Surfaced 2026-06-03.** Joey often relays multi-target firmware advice from an external LLM (Gemini). It is a useful **idea generator** but a **poor oracle for the byte-level specifics that brick ECUs** — it reasons from docs/summaries, not the binary. Treat every relayed claim as a hypothesis; the disasm/build stress-test is non-negotiable before any candidate `.rwd` exists.

## Why (the 2026-06-03 instances — all caught by a build-then-adversarially-verify horde)

- Gemini's **"recommended" 0x22 DID hook** for the EPS observability read = byte-verified **DEAD** (the RDBI framework ignores the DID and always returns a fixed metadata block; the only interception point is below 0x4000, outside the app-flash window). We'd have built on sand.
- Gemini's **RDX tune shortcut** ("edit 0x62FC2, tail-slot-only checksum") = the **exact NRC-0x72 trap** that bricked the owner's friend's build: 0x62FC2 is *inside* the CP3 window, so editing it breaks CP3 @0x6380C. The real recipe needs the full dual-checkpoint rebalance.
- Both Gemini **Accord EME fixes** (0xC61D6 slew, 0x43b52 code patch) **REFUTED** by kit ground truth in favor of the already-road-validated V18; the slew framing was inverted and the code patch needs a never-built trampoline.
- Gemini's radar **"forward AEB / block ACC as whole frames"** was wrong — AEB and ACC **co-reside as bits in one message 0x1DF**, so it needs a signal-aware bit-mux + checksum recompute, not frame forwarding.

In every case the stress pass corrected the error and **built NO confident-wrong artifact** — the right outcome.

## How to apply

- Relayed LLM advice → enumerate its load-bearing claims → verify each against the actual binary (disasm + a real build run) before implementing. Where it conflicts with byte-verified kit ground truth, **kit ground truth wins.**
- The reusable harness: a **stress-test → implement-survivors-only** horde that adversarially verifies before producing any candidate. It will (correctly) often build nothing — that is success, not failure.
- Same discipline as [[feedback_verify_subagent_claims]] (sub-agents were confidently wrong twice in a prior session) and [[feedback_rigorous_validation]] (full byte diff / ghidra before victory).

## Cross-links

- [[feedback_verify_subagent_claims]] — the sibling rule for sub-agent (not external-LLM) claims
- [[feedback_rigorous_validation]] — the validation bar this enforces
