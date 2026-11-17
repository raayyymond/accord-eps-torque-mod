---
name: accord-v300-a340-rev3-buzz-dampaxis-records-are-key-indexed-rev4-2026-11-17
description: 2026-11-17 — V300-A340 REV 3 flew on a user's 2.0T car and BUZZED (engaged 89 %, manual 48 % of near-centre time; stock same car quiet); cause = DampAxis rows ported by address but selected by CHASSIS KEY (A340 TWAA0/1 = records 26/27 in manual AND engaged); REV 4 (image e73278a1…, F181 A34D) leaves the lane stock, BUILT NOT FLOWN
metadata:
  type: project
---
DampAxis consumer (A340 FUN_00037794 / A160 FUN_00036c12) reads record ptr[mode]; mode = gp+0x63fd from the key table 0xCD000 + 0x24·row,
+0x12..15 = [manual, manual, engaged, engaged]. A160 TVCA4 (operator) = [24,25,26,27]; A340 TWAA0/1 = [26,26,27,27], A340 TVCA4 = 16..19.
All 34 records are identical on stock on both firmwares. **Any mode-indexed cal edit must be re-derived per key on each firmware.**

REV 3 route `27da1a2b0cde4a09|00000055--a39019e01a`, stock route `…|0000005d--ff985a4e01`. Metric BZ (0x14A rate, 10 Hz HP, 0.32 s rms; > 4 =
buzz). Lane's own loop −180° at 81–130 Hz, clamp ±511, aliases ≈ 16 Hz at 100 Hz sampling.

REV 4: image e73278a1…f2c6, rwd 4bc63270…bcdc, 825 B vs stock; = REV 3 − 13 DampAxis bytes, letter D. GATE 2 and lenses A/B/C
PASS_WITH_DEFECTS. Revert rwd re-packed for ,A34D (51be7dd8…).

**Why:** the stock lane-loop margin on that car is only bounded to (0, 7.5 dB]; no dose above stock is defensible without a drive.
**How to apply:** score the next A340 route with `rlog-tools/studies/a340_buzz/`; check ,A34D first; the user's coded key is still BELIEF
(TWA ECUs); A160 V300 on non-TVCA4 A160 keys = stock rows + α2 14, never scored. Detail: STATE A340 box, handoff 2026-11-17.
Related: [[accord-a340-port-v37a-built-v300-mapped-2026-11-01]].
