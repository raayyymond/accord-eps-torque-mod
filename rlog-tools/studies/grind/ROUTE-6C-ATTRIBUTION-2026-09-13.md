# Route 6c build attribution, from the wire (2026-09-13)

**Route:** `75604b0a432fdc89_0000006c--2bc842dbac` (62 segments on disk, 0..61).
**Verdict: V282.** Not V289 rev 1. Attributed from the 0x14A byte-4 tap, per the record's rule
"attribute the build from the tap, not the label" (`memory/feedback/feedback-attribute-the-build-from-the-tap-not-from-the-label.md`).

Method: **8 segments read independently** (0, 8, 17, 26, 35, 44, 53, 61 — spread across the route, not
concatenated across the large real gaps between them) via `cereal.log` + `zstandard`, following the same
decode as `extract_r62_r63_v280cache.py` (0x18F src=1: driver torque b0-1, STEER_ANGLE_RATE b2-3, SCA
b4.3; 0x14A src=1 byte 4: the cave telemetry bits; 0x1AB src=1: the 427 torque tap; 0xE4 src=129:
command b0-1, STEER_REQUEST b2.7; carState: vEgo). "Engaged" = LATERAL engaged = SCA (0x18F byte4 bit3)
AND STEER_REQUEST (0xE4 byte2 bit7), same definition as `v289_qlive_r62_r63.py`.
Script: `rlog-tools/studies/grind/_scratch/route6c_extract.py`. Raw output:
`rlog-tools/studies/grind/_scratch/route6c_attribution.{txt,json}`.

## The discriminator [reference: docs/BUILD-LINEAGE.md lines 326-372; HANDOFF-2026-09-09-V289-FLEW-...;
`v289_qlive_r62_r63.py` header]

| bit | V289 rev 1 | V282 |
|---|---|---|
| b5 | `sign(S-y)`, zero-mean → duty **~0.50** while engaged | `\|r24\| >= \|aggregator\|` comparator → duty **~0.13-0.23** (regime-dep.) |
| b6 | kept, V282's `\|r24\| >= \|T\|` comparator on both | same → duty **~0.11-0.23** |
| b7 | `\|S-y\| >= \|y\|` → **~0.95-1.00** on SCA=0 frames **>3 s** after SCA falls, ~0.10 engaged | "three-sign rung" → **~0.00** on SCA=0, **~0.56** engaged |
| b0-2 | stock Honda, 1.000 on every build (not discriminating) | same |

## Measured (EVIDENCE: wire bits, pooled over the 7 segments with engaged-lateral time; n given per cell)

| bit | engaged duty | SCA=0 duty | SCA=0, **>3 s** since SCA fell |
|---|---|---|---|
| b5 | **0.156** (n≈32,577 eq. engaged 0x14A frames) | 0.007 | — |
| b6 | **0.144** | 0.982 | — |
| b7 | **0.614** | 0.018 | **0.000** (n=3,057) |
| b4 | 0.374 | 0.146 | — |
| b3 | 0.468 | 0.429 | — |
| b0-2 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | — |

**b7 by time since SCA fell** (the V289 test — its own docstring predicts this climbs toward 1.0):
`0-0.2s: 1.000 (n=42) → 0.2-1s: 0.654 (n=159) → 1-3s: 0.347 (n=300) → >3s: 0.000 (n=3057)`.
It does the opposite of the V289 prediction — it **decays toward zero**, and is flat at 0.000 well
before 3 s. This is the single most decisive cell: the V289 rule requires ≥0.95 here; the wire reads 0.000.

**b5 toggle rate** (a live 20 Hz notch state should toggle ~20-40/s even while draining): 17.5/s in the
first 0.2 s after SCA falls, decaying to 6.4, 2.7, then 0.8/s by >3 s. Consistent with a bit tracking a
slower kinematic sign/comparator (V282), not a sustained 20 Hz cave state (V289).

**Per-segment spread** (engaged duty, b7/b6/b5): seg8 0.648/0.091/0.158 · seg17 0.755/0.085/0.112 ·
seg26 0.774/0.146/0.135 · seg35 0.468/0.183/0.177 · seg44 0.438/0.095/0.107 · seg53 0.670/0.238/0.253 ·
seg61 0.265/0.064/0.120. Seg 0 never engaged in its 61.5 s span (SCA=0 throughout: b7 0.000, b6 1.000,
b5 0.010 — consistent with the same disengaged reading seen elsewhere, not a different build).

**Cross-check against the historical V282 record:** b6 engaged 0.144 sits inside the recorded V282 range
0.114-0.228 (`r39` 0.114, `r5e_v288`'s V282 baseline 0.146, `r63`'s V282 baseline 0.228) and is nearly
identical to the `r5e` reference (0.146). b7 engaged 0.614 is close to the recorded V282 reference ~0.56.
b5 engaged 0.156 is in the same family as the recorded ~0.13. **No cell matches the V289 predictions
(b5 engaged 0.40-0.60; b7 SCA=0->3s ≥0.95).**

**Verdict: V282**, evaluated against the same rule `v289_qlive_r62_r63.py` §7 applies (a V282 image is
defined there as failing all of the V289 admission tests (i)-(iii)): fails (i) (b7 SCA=0>3s 0.000 ≪ 0.90),
fails (ii) (b5 engaged 0.156 outside [0.40,0.60]). Both by a wide margin, consistently across every
segment with engaged time — this is not a borderline read.

## Engaged time and speed [EVIDENCE: wire, same 8 segments]

Engaged-lateral: **325.6 s** of the 462.2 s of span read across the 8 segments (segment 0 contributed
0 s — not yet engaged). Speed on engaged-lateral frames (n=32,577 samples): p10 13.0 mph, **p50 61.0
mph**, p90 74.4 mph, max 74.7 mph. By band: 11.5% at 0-15 mph, 33.3% at 15-40 mph, **55.2% at 40+ mph**.
Confirms the fork note's "mostly motorway" characterization for this route.

## 12-26 Hz object on 0x18F STEER_ANGLE_RATE, engaged windows [EVIDENCE: quick Welch check per segment,
nperseg 256 on the longest engaged run, NOT a census — main's existing census tools are the census]

Every segment with ≥1.5 s of engaged time (7 of 8) shows a spectral peak inside 12-26 Hz standing 5.9x
to 20.9x above the segment's own 3-45 Hz median floor:

| seg | engaged run | peak in 12-26 Hz | power / floor |
|---|---|---|---|
| 8 | 20.5 s | 19.92 Hz | 20.9x |
| 17 | 57.9 s | 21.09 Hz | 5.9x |
| 26 | 59.9 s | 16.02 Hz | 10.7x |
| 35 | 59.9 s | 13.28 Hz | 6.8x |
| 44 | 60.0 s | 19.92 Hz | 7.2x |
| 53 | 60.0 s | 13.67 Hz | 7.3x |
| 61 | 7.4 s | 19.92 Hz | 18.4x |

Bimodal: four segments peak near 19.9-21.1 Hz, three near 13.3-16.0 Hz. [BELIEF, not verified here: this
matches the "two-line census, split by demand not speed" reading already on record
(`memory/accord/accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census.md`) rather
than implying a V289-style notch relocation — the byte-4 tap above rules out V289 on this route directly,
so a 13-16 Hz line here is evidence for the two-line-on-V282 reading, not against the attribution. Not
re-derived from the plant model in this pass; flagging for main to fold in if useful.]

## Caveats

- 8 of 62 segments read (deliberately spread, per the brief — "cheap enough for attribution", not a
  full-route census). Each segment decoded independently; no cross-segment time axis, so the b7
  time-since-fall statistics only include disengage events that fall entirely inside one read segment.
- 427 (0x1AB) tap rail was decoded but not exhaustively reported here (out of scope for this ask); no
  frame in any read segment exceeded magnitude 310 in a spot check, consistent with both candidate builds.
- Speed/engaged-time figures are over the 8 segments read, not the full 62-segment route.
