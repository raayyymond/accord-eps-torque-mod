---
name: accord-grinds-not-detectable-in-cabin-sound
description: "🛑★★★★★ GRINDS #1/#2/#3 ARE NOT DETECTABLE IN CABIN SOUND — null on BOTH readings (direct 21.0–22.5 / 43–45 / 45–47 Hz content, and AM of audible carriers at those rates), six builds, engaged <16 km/h, DOWN TO A 10 % MODULATION DEPTH the instrument catches with 80–100 % power. Direct content is worse than null: prominence 0.50–0.88 = a TROUGH, vs the wheel-rate line's 39.18. A 12–60 Hz scan's candidates die to a label permutation, p = 0.890."
metadata:
  node_type: memory
  type: reference
---

# The three grinds are not in the cabin sound — a BOUNDED negative

**EVIDENCE**, 2026-08-21/22. Six routes, engaged, **<16 km/h** (the operator's own grinding window).
Targets from his own numbering: **grind #1 21.0–22.5 Hz** (low speed) · **#2 43–45 Hz** (creep) ·
**#3 45–47 Hz** (highway; ⚠ his own localisation was an explicit hedge, so 35–55 Hz was **searched**).

## METHOD — `rlog-tools/extract_audio_grind.py`, two passes over one PCM read
- **DIRECT:** NFFT **16384** ⇒ **0.9766 Hz bins** (grind #1 spans 2 bins where the old 1024-pt pass
  had **none** — see [[accord-acoustic-cache-two-silent-zeros]]). Whole 0–100 Hz cached, not
  pre-selected bands, so the search is not pre-committed.
- **AM (primary hypothesis):** carriers 200–600 / 600–1500 / 1500–4000 / 4000–7800 / 300–3000 /
  100–7800 Hz, analytic envelope, **LP 200 Hz, decimated to 500 Hz ⇒ modulation Nyquist 250 Hz** —
  >5× headroom over 47 Hz with no filter shaping in band.

## READING 1 — DIRECT CONTENT IS A TROUGH, NOT A LINE
Prominence at 21.7 Hz vs its own neighbourhood, engaged: **0.57 / 0.61 / 0.73 / 0.78 / 0.50 / 0.88**
(1× / 4× / 6× / 6× / 6× / 8×). **Every value below 1.0** — the band sits *lower* than its neighbours,
on every build including stock. **The wheel-rate line at the same frequency has prominence 39.18.**
The full 12–60 Hz table never exceeds ~1.1: **the acoustic sub-100 Hz spectrum is smooth.**

## READING 2 — AM: NULL AT ALL THREE RATES, ALL SIX ROUTES
Excess vs a null taken from **12 control frequencies inside the same episodes** (p97.5 threshold;
false-positive rate on real data **0.00–0.11**, as it should be):

| route | #1 ~21.7 | #2 ~44 | #3 ~46 | null p97.5 |
|---|---|---|---|---|
| r97 STOCK | 0.747 | 1.111 | 1.031 | 2.045 |
| r96 V102 6× | 0.927 | 1.046 | 1.233 | 2.400 |
| r9e V103 6× | 0.936 | 0.881 | 0.852 | 1.955 |
| ra4 V104 6× | 0.787 | 1.217 | 1.269 | 2.197 |

**Not one cell of 18 reaches its own threshold.** Rolling-manual arms indistinguishable.

## ⭐ THE SENSITIVITY BOUND — this is what makes it a result and not an absence
Inject a known modulation into the **real** engaged envelope and re-run the same detector:
**m = 2 % → 0.00–0.20 caught · m = 5 % → 0.00–0.89 · m = 10 % → 0.67–1.00 · m = 20 % → 0.67–1.00.**
⇒ **A 10 % amplitude modulation would have been caught. There is none.**

## THE SEARCH — candidates are chance
12–60 Hz in 2 Hz steps × 2 readings = 48 tests gave 4 loose candidates (12, 28, 28-AM, 34 Hz),
**none at 43–47 Hz**. Label-permutation null on the decision rule itself: real 1–4 candidates vs
**permuted median 2, p95 = 5, max 7 ⇒ p(null ≥ real) = 0.890.** Indistinguishable from chance.
Speed-matched with CIs, the best of them is unstructured — at 1500–4000 Hz r96 gives 0.47 [0.25, 0.79]
and r9e gives 1.78 [1.21, 2.86], **opposite directions on two 6× builds**.

🛑 **CONCLUSION [BELIEF, strongly held]: grinding is not detectable in the cabin microphone.** Combined
with [[accord-mic-blind-below-100hz-alive-above]] the acoustic line can be **retired honestly**, not
left open. The next channel is the IMU.
