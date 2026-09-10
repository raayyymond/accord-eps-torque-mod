---
name: accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature
description: V289 rev 1 (notch on the LKAS rate loop's clamped output + fb lag pole 16.5->25 Hz) flew 2026-09-09 on routes r62/r63 and hit its own pre-registered revert signature. CORRECTED READING (see the UPDATE section, it supersedes the body) -- the NOTCH WORKED COMPLETELY, the 18-22 Hz band is EMPTY (0 of 1414 windows); what became dominant is a DIFFERENT, PRE-EXISTING 15-17 Hz pole whose phase margin the notch skirt spent; measured zeta 0.029 on BOTH builds. Episodes are louder, not quieter, and come in trains. Operator -- "Grinding is still an issue." The V282-yardstick census is BLIND to the relocated line. The "20 Hz is a pinned plant mode" picture SURVIVES and is stronger -- "under adjudication" is WITHDRAWN. Outcome: the operator chose to revert to V282 and cut no V290.
metadata:
  type: project
---

# V289 rev 1 flew (2026-09-09): the ring moved to 15–17 Hz, not gone

| claim | status | method |
|---|---|---|
| both routes confirmed V289 from the wire | EVIDENCE | b5 (sign of the notched-out component) duty 0.500 engaged on both; b7 reads 0.95–1.00 on SCA=0 frames > 3 s post-disengage — V289's signature (V282/V288 read 0.00 there) |
| the 20 Hz line is gone route-wide; a 16.5–17.0 Hz line replaces it | EVIDENCE | pooled Welch PSD of the 0x18F wheel rate, engaged runs ≥ 4 s, independent of the census gate; peak ×9.6–23.2 above floor vs V282/V288's ×5–11 at 20 Hz |
| at the two operator bookmarks the dominant line is 15.92 Hz (r62) / 15.09 Hz (r63) | EVIDENCE | 10 s pre-bookmark Hann periodogram, same code as `V288-MARKS-R5E-2026-09-08.md` |
| not quieter — several unmarked episodes louder than any prior bookmark | EVIDENCE | envelope peaks 725–826 raw (r63) / 581–599 (r62) vs V288's loudest bookmark 651 and loudest route-wide episode 640 |
| events shorter (decaying bursts, ζ_eff 0.02–0.13) but recur in trains, one every 1.5–2 s for 10 s | EVIDENCE | half-peak duration + log-envelope decay fit, 7 events per route |
| the V282-census gate (18–22 Hz ≥ 40 raw) is blind to this line — its 2.1–2.2 % presence is a gate artefact, not an improvement | EVIDENCE | same census recipe reproduces exactly on r39/r3a/r3c/r5e_v288; independent pooled-PSD band-power ratio flips 0.32–0.62 → 4.9–9.9 |
| the notch cave keeps executing 1–3 s after SCA falls (Honda's disengage fade) | EVIDENCE | b5 keeps toggling 28–41/s for 1–3 s post-disengage; b7 climbs 0.10→1.00 over the same window; score engaged-only |
| trigger class unchanged: full-lock intersection turns at 2–5 m/s, command rail-to-rail at the slew cap | EVIDENCE | both bookmarks + 6 loudest unmarked episodes |
| "20 Hz is a pinned plant mode the loop de-damps" is now UNDER ADJUDICATION | BELIEF, argued from the drive | a pinned mode should not relocate when only the loop's phase changed (Kp unchanged V282→V289); the notch moved the line 20→15–17 Hz, crossover-like behaviour |

**Why it matters:** first on-car test of an in-loop filter on the LKAS rate loop's own output; it falsifies (or seriously doubts) the plant-mode picture the V290 damping-addition design was ranked on. `docs/specs/design/DESIGN-V290-2026-09-09.md` §12 (written after these reads landed) resolves its own decision tree to "revert, re-fit the plant" and finds every ranked in-loop candidate Nyquist-unstable on this plant. See [[accord-v289r1-sum-notch-plus-fb-pole-built-b3-accepted-the-20hz-line-is-a-plant-mode]] (the pre-drive design this corrects).

**How to apply:** do not quote V289's V282-yardstick census numbers (2.1–2.2 % presence) as an improvement — re-gate at 13–18 Hz first. Before proposing another in-loop damping filter for this loop, re-fit the plant model against r62/r63. The parked cal-only fallback (Kd 128→96 + fb pole 25 Hz, 4 bytes, no cave change) is a class the operator has previously rejected in spirit as "a gain cut" — flag that if it is ever proposed again.

---

## 🛑 UPDATE 2026-09-09 (later same day) — "under adjudication" is RESOLVED; the "notch failed" reading was wrong

**This memory's title/framing is a REVERT SIGNATURE, correctly** — a new line did appear where none was
predicted, louder, in trains — **but the implied reading "the notch failed to do its job" is WRONG.**
`MODE-NATURE-V289-RECENSUS-2026-09-09.md` (11 routes, 14,678 windows) settled the adjudication this memory
flagged as open:

- **The notch did exactly what it was designed to do.** It did not shift the 20 Hz mode — it removed the
  loop gain feeding it (|N| = 0.011, −39.3 dB). Demand-gated (`idx ≥ 20`), the 18–22 Hz band is **EMPTY on
  V289: 0 of 1414 present windows** (vs 17/222/279/12/4 counts at 18/19/20/21/22 Hz on V282). ζ is
  unchanged (0.029 median on both V282 and V289) — **the frequency moved, the damping at that frequency
  did not; the 20 Hz mode itself has ~zero energy left to measure.**
- **The 15–17 Hz line V289 shows is a DIFFERENT, pre-existing pole**, one V282 already carried at |L| 1.13
  with ~30° of phase margin — margin the notch's own skirt (−41.6° at that frequency) plus the new fb pole
  (+11.5°) spent. Not a relocation of the same mode; a trade of margin from one pole to expose another.
- **The "20 Hz is a pinned plant mode" picture is NOT under adjudication any more — it SURVIVES and is
  now better supported**, and the alternative (crossover) explanation this memory's line 20 raised is
  falsified: no plant-family fit puts |L(20 Hz)| ≥ 1 on V282 (all sit at 0.43–0.61), and the clamp
  explanation for the Kp-pinning is independently falsified by direct measurement (clamps bind 0.0 % of
  the time at every tested demand stratum).

See [[accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census]] for the full
recensus. **Practical consequence for scoring the next build:** a revert-signature line appearing where
none was predicted is not automatically a failed edit — check whether it is a genuinely new object or a
pre-existing pole whose margin the edit spent, before concluding the intervention didn't work.
