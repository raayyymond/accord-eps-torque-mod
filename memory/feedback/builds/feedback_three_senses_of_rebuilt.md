---
name: feedback-three-senses-of-rebuilt
description: When claiming "we rebuilt X", disambiguate three distinct senses; Joey caught this conflation after the stock TVA .rwd reconstruction
metadata:
  type: feedback
source: user
---

When claiming "we rebuilt X" or "X is done", **explicitly disambiguate which of three senses applies**:

1. **Round-trip-equal to my input**: the output, when fed back through the inverse pipeline, returns my original input bytes. Proves the encoding pipeline is bijective.
2. **Byte-identical to the canonical/upstream version**: the output matches what the authoritative source (Honda's actual stock .rwd, the upstream library, etc.) would produce. Requires the canonical version for comparison.
3. **Would actually work in production**: the output would succeed in its real use case (flashing a real ECU, accepted by the real tester, etc.). Requires real-world validation.

**Why:** Joey caught me conflating these three after the stock TVA-A160 reconstruction landed. I'd been writing "we rebuilt his thing" in a way that suggested sense 2 or 3 when we'd only achieved sense 1. The framing matters because rayy's actual ECU is at stake — claiming the artifact is "ready to flash" when only sense 1 holds is the kind of confident-wrong that bricks hardware.

The exchange: Joey asked "how is a flashable artifact blocked also if you're saying we rebuilt his thing" — the contradiction surfaced because I'd let the three senses blur. I had to back up and acknowledge: payload round-trip is sense 1 (achieved); byte-vs-Honda is sense 2 (untestable without Honda's source); would-flash is sense 3 (blocked on the SA-key handshake).

This same pattern recurred during the SA-key chain: "algorithm verified" turned out to need 3-sense disambiguation too — math-verified vs ISA-decode-verified vs hardware-validated.

**How to apply:**
- Before claiming "X is done" or "we rebuilt X", state which sense
- Sense 1 (round-trip) is usually the cheap proof — claim it explicitly, not by implication
- Sense 2 (canonical match) requires the canonical version; if absent, say so
- Sense 3 (production behavior) almost always requires real-world test; never imply without it
- When senses diverge, name each one's status separately — don't let strong sense-1 evidence rhetorically carry weaker sense-2/3 claims

Related pattern: the kit's existing [[feedback-rigorous-validation]] memory captures the build-side equivalent (full byte diff > spot diff; ghidra before declaring victory). This memory is the framing-side equivalent.
