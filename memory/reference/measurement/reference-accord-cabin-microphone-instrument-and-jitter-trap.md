---
name: reference-accord-cabin-microphone-instrument-and-jitter-trap
description: A new, never-before-used instrument exists in the rlogs — the cabin microphone (rawAudioData, 16kHz mono) — but it currently fails its coupling control to the 6-9Hz mechanical band and must not be used to score the operator's audible report yet. Also records the logMonoTime jitter trap that manufactures a fake ~11Hz line.
metadata:
  type: reference
---

**`rawAudioData`** exists in the rlogs and has never been used by this kit before this session.
16 kHz mono int16, 800 samples (50 ms) per message, ~1,050–1,200 msgs/segment. `soundPressure` is
also available. [EVIDENCE, `scorer-v99`, `docs/traces/TRACE-2026-08-13-v99-flight-score.md`]

## Why it can't hear the ratchet directly, and what it CAN see
A microphone at 16 kHz cannot resolve an 8 Hz mechanical tone directly — but a ratchet's AUDIBLE
signature is not the 8 Hz fundamental, it is a **6–31 Hz amplitude modulation of a broadband rasp**
(the grinding/ratcheting SOUND is the envelope of higher-frequency noise being gated open and shut at
the mechanical rate). That envelope is well within audio range and is what this instrument targets.

## Current status: LIVE but UNINTERPRETABLE — do not use it to score audible reports yet
- The envelope IS live: envelope↔speed correlation up to **ρ = +0.55**.
- 🛑 **It FAILED its coupling control to the 6–9 Hz mechanical band**: only 1 nominal hit in 18 tests
  (chance rate), and that one hit was **wrong-signed**. ⇒ **currently uninterpretable as a proxy for
  the mechanical ratchet band.**
- ⇒ It was correctly NOT used to score the operator's audible report on V99. **Do not use it for that
  purpose until the coupling control passes.**

## 🛑 THE JITTER TRAP — will manufacture a fake periodicity if not handled
`logMonoTime` is the **publish** time of each audio message, not a sample clock, and it **jitters
±10 ms** around the nominal 50 ms cadence (measured dt: p10 41.3 ms / p50 50.0 ms / p90 61.0 ms).

**If you place resampling blocks at `round(t · SR)`** (i.e. snap each message to its nominal grid
position by sample rate), **the jitter punctures the stream every ~8 bins**, which manufactures a
**fake ~11 Hz periodicity landing INSIDE the 12–16 Hz band under test** — a completely artefactual
line that will look like a real finding if the block-placement method is not checked.

**Fix**: lay audio blocks **end to end** in actual received order (do not snap to a nominal grid), and
only start a new contiguous run at a genuine dropout (`dt > 75 ms`). This is the same class of error
as [[accord-averaged-spectrum-needs-matched-speed-distributions]] — an instrument that looks clean
until its own control is actually run against it.

**How to apply:** before citing anything from this instrument as evidence, (1) confirm blocks were
laid end-to-end per the fix above, not grid-snapped, and (2) re-run the coupling control to the 6–9 Hz
band and confirm it passes before trusting the envelope as a proxy for the mechanical symptom.
