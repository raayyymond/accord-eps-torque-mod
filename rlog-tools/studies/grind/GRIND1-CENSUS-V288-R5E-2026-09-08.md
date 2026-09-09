# GRIND #1 (18-22 Hz) census on the first V288 rev 2 route (r5e_v288) — the V282 yardstick, unchanged

Subagent `census288`, 2026-09-08. Script `grind1_census_v288_r5e.py` (this folder; full output
`_scratch/grind1_census_v288_r5e.txt`, stage cache `_scratch/grind1_census_v288_r5e_cache.pkl`).
Analysis only: builds nothing, sends nothing.

Route **r5e_v288** = `75604b0a432fdc89_0000005e--03a9714d78` (2026-09-08, 15 segs, 868.8 s, **641.6 s
laterally engaged**), V288 rev 2 (image sha256 `94cabdef…bdbd8c`, re-hashed). Comparators **r39 / r3a /
r3c** (V282). "Engaged" = LATERAL engaged throughout. Bookmarks at route-relative 129.3 / 331.5 / 820.1 s.

## 0. Method fidelity [EVIDENCE]

- `GI.read_cells` on the V288 image is **identical to the V282 image on all 28 cell keys** (map, Kp/Kd
  banks, fb, lag, fade/taper arms), so V282 cells are used for r5e_v288 — the calibration claim in STATE
  is confirmed from the bytes.
- `grind1_census_v282.py` keeps its pipeline inside `main()`; the window census, episode extraction /
  classification and both enrichment tests were **copied verbatim into functions** (thresholds untouched)
  and the script **asserts reproduction** against the stored `_scratch/grind1_census_v282.txt` before any
  V288 table prints: windows 1742/939/1162, present 364/78/144, episodes 79/13/38, class splits
  32-25-22 / 3-6-4 / 13-20-5, enrichment 1.25× [1.23, 1.26] and 2.80× [2.10, 3.57], thresholds 122 / 9.0 —
  **all identical.**
- D-bind mirror: `GI.simulate` copied with ONE insertion (the cave's setpoint filter, mirrored
  integer-exact from `build_v288_tva.sp_filter_tick`, y := sp at the start of each engaged run = the
  engage init); with the filter off it reproduces `GI.simulate` bit-for-bit (asserted). Setpoint is
  rounded to an integer before the filter (the firmware's map lerp is integer; the mirror's is float).

## 1. Exposure — the two arms are not the same drive [EVIDENCE]

| stratum (engaged s) | r39 | r3a | r3c | V282 pool | **V288** | flag |
|---|---|---|---|---|---|---|
| ALL engaged | 880 | 483 | 594 | 1957 | **642** | |
| FB: hands-on \|bar\|>700 | 90 | 26 | 55 | 170 | 67 | |
| FB: \|ang\|>60° | 72 | 26 | 50 | 147 | 69 | |
| FB: wheel>25°/s | 92 | 28 | 55 | 176 | 76 | |
| FB-dominated (any) | 157 | 53 | 94 | 303 | 117 | |
| REF-dominated (none) | 723 | 431 | 500 | 1654 | 525 | |
| REF & creep 1-3 m/s | 51 | 17 | 29 | 97 | 34 | thinnest, ≥ 30 s |
| REF & 3-8 m/s | 149 | 29 | 47 | 226 | 77 | |
| REF & 8-15 m/s | 296 | 100 | 108 | 504 | 92 | |
| REF & ≥15 m/s | 219 | 276 | 307 | 803 | 318 | |
| REF & hands-off \|bar\|<400 | 689 | 421 | 484 | 1594 | 505 | |

No V288 stratum is under 30 s. Speed p10/p50/p90: V288 2.7/15.0/29.0 m/s (r39 2.9/9.6/22.9, r3a
5.0/16.4/29.5, r3c 3.4/15.2/29.5); hands-on share 10.5 % (r39 10.2, r3a 5.3, r3c 9.2); median idx 6
(r39 11, r3a 6, r3c 7). **V288's drive resembles r3c/r3a in speed and r39 in hands-on share.** One more
difference that matters below: V288 is **the most slew-capped route of the four** (7.8 % of engaged
frames on the 122/123 wall vs 4.0 / 0.7 / 2.2 %) — openpilot was rate-limited twice as often, which is a
property of the drive and the fork tune, not of the EPS.

## 2. Presence census (2 s windows, 0.5 s step; present = 15-26 Hz prominence ≥ 8 AND bar 18-22 ≥ 40 raw) [EVIDENCE]

| route | n win | present | % [CI] | f mean ± sd (p10/p90) | amp p50/p90/max raw |
|---|---|---|---|---|---|
| r39 | 1742 | 364 | 20.9 [19.2, 22.7] | 20.05 ± 1.03 (19.40/20.68) | 25/73/228 |
| r3a | 939 | 78 | 8.3 [6.7, 10.0] | 19.74 ± 1.34 (18.29/20.49) | 14/43/254 |
| r3c | 1162 | 144 | 12.4 [10.7, 14.5] | 19.88 ± 1.52 (18.74/20.74) | 19/60/265 |
| **V288** | 1266 | 198 | **15.6 [13.6, 17.8]** | **19.84 ± 1.40 (18.84/20.60)** | 20/65/**359** |
| V282 pool | 3843 | 586 | 15.2 [14.1, 16.4] | 19.97 ± 1.22 (19.26/20.68) | 20/64/265 |

Operator's stratum (creep 1-3 m/s, hands-off): V288 **44 %** present (n 98, amp p50 45, max 359) vs r39
43 %, r3c 29 %, r3a 0 %. Per stratum (window medians): FB-dominated V288 39.5 % vs V282 44.1 %;
REF-dominated 10.6 % vs 9.9 %; REF creep 35.5 % vs 34.1 %; REF 3-8 m/s **30.5 % vs 18.0 %**; REF ≥15 m/s
1.6 % vs 2.7 %. **Presence is inside V282's route-to-route spread in every stratum.**

## 3. Episodes [EVIDENCE for the counts; the class boundary is the census's BELIEF, unchanged]

| arm | n | eng s | **ep / engaged h [CI]** | BURST | SUSTAINED | RIDE-ALONG |
|---|---|---|---|---|---|---|
| r39 | 79 | 880 | 323 [252, 396] | 41 % | 32 % | 28 % |
| r3a | 13 | 483 | 97 [45, 155] | 23 % | 46 % | 31 % |
| r3c | 38 | 594 | 230 [132, 349] | 34 % | 53 % | 13 % |
| **V288** | **46** | 642 | **258 [157, 364]** | **33 % [20, 46]** | **52 % [39, 65]** | **15 % [7, 26]** |
| V282 pool | 130 | 1957 | 239 [190, 295] | 37 % [28, 45] | 39 % [31, 48] | 24 % [17, 32] |

Rate CI = block bootstrap over 30 s engaged blocks; class CIs resample episodes.

| arm | dur p50 [CI] / p90 / max s | env peak p50 [CI] / p90 / max raw | bar 18-22 p50 / p90 / max |
|---|---|---|---|
| **V288** | 1.75 [1.01, 2.25] / 4.00 / 8.50 | 126 [104, 170] / 439 / **640** | 61 / 104 / 197 |
| V282 pool | 1.51 [1.49, 2.00] / 4.99 / 13.50 | 127 [114, 146] / 317 / 528 | 60 / 103 / 197 |

Mann-Whitney V288 vs V282 pooled: env peak p = 0.92, duration p = 0.76. The **two loudest V288 episodes
(env 640 and 619 raw at t 671.4 and 666.9 s, and 600 at 813.6-822.1 s) exceed V282's loudest (528)**; the
813.6-822.1 s one is the third bookmark (SUSTAINED, 8.5 s, |ang| 108°, wheel 136°/s, idx 240 — squarely
FB-dominated). **All three bookmarks land on census episodes:** 129.3 → 122.3-124.8 RIDE-ALONG +
131.8-135.3 SUSTAINED; 331.5 → 329.2-332.7 RIDE-ALONG (+ 334.2-335.7); 820.1 → 813.6-822.1 SUSTAINED.

**Line frequency has NOT moved:** present-window f0 V288 19.84 ± 1.40 Hz, 74 % of windows in
19.5-20.5 Hz (V282 73 %), p10/p90 18.84/20.60; fine per-episode line p25/p50/p75 **19.91/19.99/20.13**
(V282 19.36/19.93/20.13); KS D 0.089, p 0.18; medians 20.06 vs 20.03 Hz. The 6c line-excess peak sits at
20.12 Hz on every V288 signal and stratum.

Onset predicates with the V282 thresholds frozen: loose transient 1.35× (1.00 of onsets, 0.74 baseline);
top-1 % tick (= the 122 slew cap) **2.56× [1.81, 3.30]** vs V282 2.80× [2.10, 3.57] (V288 baseline 0.204 vs
0.110 — twice as many capped frames); by class BURST 2.29× [0.98, 3.59], SUSTAINED 3.06× [2.04, 3.88],
RIDE-ALONG 1.40× [0.00, 2.80]. Steady-creep onsets 4 (9 %) vs 7 %. Onset medians: v 5.6 m/s, |ang| 16°,
rate 9.1°/s, idx 28 (V282: 7.9 / 11 / 8.4 / 27).

**Onsets per engaged hour by the onset frame's stratum (the prereg's split):**

| stratum | V282: n / s / ep·h⁻¹ | V288: n / s / ep·h⁻¹ | ratio V288/V282 [CI] |
|---|---|---|---|
| FB: hands-on | 28 / 170 / 592 | 9 / 67 / 483 | 0.82 [0.37, 1.55] |
| FB: \|ang\|>60° | 30 / 147 / 736 | 12 / 69 / 629 | 0.86 [0.44, 1.49] |
| FB: wheel>25°/s | 36 / 176 / 738 | 11 / 76 / 518 | 0.70 [0.35, 1.26] |
| **FB-dominated (any)** | 56 / 303 / 665 | 18 / 117 / 555 | **0.83 [0.49, 1.32]** |
| **REF-dominated (none)** | 74 / 1654 / 161 | 28 / 525 / 192 | **1.19 [0.79, 1.72]** |
| REF & creep 1-3 | 9 / 97 / 333 | 8 / 34 / 855 | 2.56 [1.11, 5.05] (34 s) |
| REF & 3-8 m/s | 18 / 226 / 287 | 8 / 77 / 376 | 1.31 [0.57, 2.58] |
| REF & 8-15 m/s | 28 / 504 / 200 | 6 / 92 / 234 | 1.17 [0.43, 2.54] |
| REF & ≥15 m/s | 18 / 803 / 81 | 6 / 318 / 68 | 0.84 [0.31, 1.83] |
| REF & hands-off | 68 / 1594 / 154 | 22 / 505 / 157 | 1.02 [0.64, 1.55] |

The prereg predicted FB strata would not move and REF strata would. **The reference-dominated strata did
not fall** — hands-off 1.02×, REF overall 1.19×, and the creep stratum reads 2.6× HIGHER (8 onsets in 34 s;
thin, and it is where the first two bookmarks cluster).

## 4. Pre-registered endpoint (a): the slew cap, the D clamp, and the rung bell [EVIDENCE]

**Capped-frame enrichment** (|Δcmd| ≥ 122; V288 has 687 + 4297 frames on 122/123, nothing above):

| route | baseline frac capped | in episodes | pre-onset 0.5 s | onset ±0.5 s | P(cap within ±0.5 s of onset) vs baseline |
|---|---|---|---|---|---|
| r39 | 0.018 | 0.125 (6.9×) | 0.070 (3.9×) | 0.082 (4.5×) | 0.544 vs 0.322 = 1.69× [1.34, 2.04] |
| r3a | 0.001 | 0.074 (60.5×) | 0.011 (8.8×) | 0.029 (23.7×) | 0.308 vs 0.075 = 4.11× [1.03, 8.22] |
| r3c | 0.011 | 0.096 (8.8×) | 0.125 (11.5×) | 0.113 (10.4×) | 0.447 vs 0.133 = 3.35× [2.17, 4.54] |
| **V288** | **0.052** | **0.220 (4.2×)** | **0.220 (4.2×)** | 0.209 (4.0×) | **0.696 vs 0.322 = 2.16× [1.75, 2.56]** |

The enrichment RATIOS are lower on V288 only because the baseline is 3-40× higher; in absolute terms
V288 episodes are the most capped (22 % of in-episode frames) and 70 % of onsets have a capped frame
within half a second. The cap-before-onset association survives on V288.

**D-clamp bind duty, 1 kHz mirror over every engaged run ≥ 1 s** (bind = |ΔE·128/8| > 10240):

| route / arithmetic | live ticks | binds | duty [CI] | in-episode | outside | P(cap \| bind) |
|---|---|---|---|---|---|---|
| r39 raw sp (as flown) | 879,840 | 5,512 | 0.00626 [0.00443, 0.00803] | 0.0161 | 0.0037 | 0.525 |
| r3a raw sp | 481,910 | 653 | 0.00136 [0.00047, 0.00244] | 0.0123 | 0.0004 | 0.432 |
| r3c raw sp | 593,860 | 2,309 | 0.00389 [0.00198, 0.00578] | 0.0147 | 0.0024 | 0.468 |
| **V288 with the cave filter (as flown)** | 641,560 | **181** | **0.00028 [0.00005, 0.00059]** | **0.0003** | 0.0003 | 0.243 |
| V288 route, filter REMOVED (counterfactual) | 641,560 | 6,081 | 0.00948 [0.00632, 0.01313] | 0.0258 | 0.0065 | 0.679 |

**The filter did what it was sized to do:** on V288's own drive the D-clamp bind duty falls **×0.030**
(in-episode 0.0258 → 0.0003), below every V282 route by 5-20×. The 181 residual binds cannot be setpoint
steps (|sp − y| ≤ 1032 ≪ 10240 after ÷16) — they are feedback-driven ticks (Δfb > 10240/tick), and their
P(cap | bind) of 0.24 (vs 0.43-0.68) says so. This is a mirror result on logged inputs (open-loop, as the
wire study's correction of record says), not a wire measurement of the D term.

**The rung-bell test — 18-22 Hz bar envelope triggered on capped-frame onsets** (first capped frame after
≥ 0.2 s uncapped; pre = median over −0.5..0 s, post = max over 0..+0.5 s; CI resamples events):

| arm | stratum | n events | pre p50 raw | post p50 raw | **post/pre [CI]** | rate post/pre [CI] | P(episode ≤ 0.5 s after) |
|---|---|---|---|---|---|---|---|
| V282 pool | ALL | 348 | 29.8 | 67.2 | 2.25 [1.94, 2.64] | — | 0.49-0.75 by route |
| **V288** | ALL | 133 | 18.5 | 44.7 | **2.41 [1.78, 2.96]** | 2.24 [1.82, 2.64] | 0.40 |
| V282 pool | FB-dominated | 138 | 25.1 | 68.9 | 2.74 [2.13, 3.41] | — | |
| **V288** | FB-dominated | 47 | 16.2 | 44.3 | **2.74 [1.80, 3.87]** | 1.98 [1.58, 2.72] | 0.34 |
| V282 pool | REF-dominated | 210 | 32.8 | 66.1 | 2.02 [1.75, 2.40] | — | |
| **V288** | REF-dominated | 86 | 21.4 | 45.7 | **2.14 [1.61, 2.95]** | 2.27 [1.73, 2.82] | 0.43 |
| V282 pool | REF hands-off | 193 | 30.3 | 62.8 | 2.07 [1.74, 2.47] | — | |
| **V288** | REF hands-off | 81 | 22.0 | 46.6 | **2.12 [1.61, 2.84]** | 2.13 [1.67, 2.83] | 0.41 |
| V282 pool | REF creep 1-3 | 62 | 29.0 | 61.4 | 2.12 [1.53, 2.99] | — | |
| **V288** | REF creep 1-3 | 31 | 25.7 | 46.6 | 1.81 [1.36, 3.25] | 2.07 [1.19, 3.13] | 0.39 |
| V282 pool | REF 3-8 m/s | 74 | 23.9 | 47.8 | 2.00 [1.44, 2.36] | — | |
| **V288** | REF 3-8 m/s | 45 | 18.4 | 43.8 | 2.39 [1.65, 3.22] | 2.13 [1.83, 3.21] | 0.49 |

Median envelope curve, REF-dominated onsets (raw, lag s): V282 pool 27.8 (−0.4) → 43.3 (0) → **45.8
(+0.1)** → 41.2 (+0.3) → 27.5 (+0.5); V288 19.3 → 24.7 → **29.3 (+0.1)** → 21.7 (+0.3) → 23.4 (+0.5). Same
shape, same latency to peak, ~0.65× the absolute level throughout (before the step as well as after).
**The bell's proportional response to a capped step is unchanged within CI in every stratum, including
the reference-dominated ones the filter was aimed at.** The lower absolute envelope on V288 is present
in the pre-step baseline too, so it is a property of the drive (speed/road) rather than of the step
response. ⚠ Almost every capped onset is a single capped frame (run = 1: 78 of 86 REF events on V288,
203 of 210 on V282); multi-frame ramps are too few to compare (7 vs 5).

## 5. Whole-route spectral shift and the > 22 Hz scan [EVIDENCE]

Pooled engaged Welch PSDs (Hann, 50 % overlap, 0.195 Hz bins; bar and wheel rate on the 100 Hz 0x18F
stream, T on the native 50 Hz 0x1AB tap). Band powers with segment-bootstrap CIs; ratio = V288 / route.

| stratum | signal | V288 18-22 Hz [CI] | ratio vs r39 / r3a / r3c | V288 6-10 Hz ratio vs r39 / r3a / r3c | (18-22)/(6-10): V288 vs V282 routes |
|---|---|---|---|---|---|
| ALL | bar raw² | 1.14e3 [766, 1.58e3] | 0.90 / 1.52 / 1.25 | 0.77 / 1.25 / 0.92 | 0.058 vs 0.050 / 0.048 / 0.043 |
| ALL | wheel rate (°/s)² | 2.04 [1.33, 2.89] | 0.89 / 1.49 / 1.16 | 0.78 / 1.38 / 0.98 | 0.789 vs 0.691 / 0.735 / 0.665 |
| ALL | T raw² | 444 [328, 592] | 0.87 / 1.53 / 1.27 | 0.85 / 1.41 / 1.02 | 0.375 vs 0.367 / 0.345 / 0.301 |
| REF | bar | 188 [142, 245] | 0.64 / 1.32 / 1.30 | 0.52 / 1.30 / 1.51 | 0.094 vs 0.077 / 0.092 / 0.110 |
| REF | wheel rate | 0.297 [0.223, 0.392] | 0.51 / 1.22 / 1.25 | 0.46 / 1.14 / 1.23 | 1.503 vs 1.350 / 1.397 / 1.475 |
| REF | T | 80.5 [61.7, 110] | 0.53 / 1.28 / 1.31 | 0.51 / 1.15 / 1.20 | 0.791 vs 0.752 / 0.711 / 0.727 |
| FB | bar | 2.63e3 [966, 5.03e3] | 1.07 / 0.37 / 1.05 | 1.20 / 0.63 / 0.61 | 0.039 vs 0.043 / 0.065 / 0.023 |
| FB | T | 844 [346, 1.47e3] | 0.86 / 0.31 / 0.77 | 1.14 / 0.70 / 0.60 | 0.161 vs 0.212 / 0.359 / 0.125 |

V288's 18-22 Hz band power sits **between r39 and r3a/r3c on every signal and stratum**, and the
18-22 / 6-10 ratio (the band's share of the low-frequency drive) is at the top of the V282 range (ALL:
0.058 vs 0.043-0.050; REF wheel rate 1.50 vs 1.35-1.48). No 18-22 Hz reduction is visible at the
whole-route level; the 6-10 Hz strong-turn companion is likewise inside the V282 spread.

**The 18-22 Hz line's own excess over its ±2 Hz shoulder** (dB, peak in 18-22): ALL stratum V288 bar
+5.5 [+4.0, +7.6] / wheel +5.9 / T +6.8 at 20.12 Hz, vs r39 +7.5 / +7.0 / +7.2, r3a +6.6 / +6.1 / +7.3, r3c
+4.0 / +4.4 / +5.9. REF stratum: V288 +4.7 / +4.8 / +6.1 vs r39 +4.2 / +4.9 / +5.2, r3a +1.8 / +3.5 / +3.4,
r3c +1.1 / +3.1 / +3.6 — **V288's reference-dominated line is as sharp as r39's and sharper than
r3a/r3c's.**

**Scan for a NEW line above 22 Hz (the operator's "higher frequency" hypothesis):** on bar and wheel
rate, 22.5-49 Hz, top peaks by excess with segment-bootstrap CIs. V288 ALL bar: 40.23 Hz +1.1 dB [+0.2,
+2.0], 33.0 +0.9, 27.3 +0.9, 35.2 +0.8, 48.4 +0.8; V288 ALL wheel: 25.0 Hz +1.0, 40.4 +0.8, 28.3 +0.8,
29.7 +0.7; V288 REF bar: 29.69 Hz +2.0 [+0.5, +3.2], 27.34 +1.6 [+0.3, +2.6]; REF wheel 29.7 +1.2, 27.5
+1.1. The V282 routes carry peaks of the same size at the same places (r39 25.6 Hz +1.5/+2.4, 39.8 Hz
+3.4 on wheel; r3a 27.5-28.5 Hz +2.3-3.4; r3c ≤ +1.1). **By the pre-stated rule (V288 excess ≥ 3 dB with
CI low > 1 dB and no V282 route within ±0.5 Hz at ≥ 2 dB) there is NO new line on V288** in any
stratum or signal. The 39.9 Hz second harmonic of the 20 Hz line is weaker on V288 (+0.8 dB wheel)
than on r39 (+3.4). The 0x1AB tap (50 Hz) cannot see above 25 Hz; this scan is the 0x18F streams
only and inherits TASK 5's unresolved 80/120 Hz fold on those streams.

## 6. What a fair reading of one route says [BELIEF, built on the EVIDENCE above]

On the V282 yardstick, unchanged, the 18-22 Hz band on V288's first route **did not move**: presence
15.6 % vs 15.2 %, 258 vs 239 episodes per engaged hour, the same class split, the same duration and
peak-amplitude distributions (MW p 0.9), the line pinned at 20.0-20.1 Hz, whole-route band power between
r39 and r3a/r3c on every signal, and no new line above 22 Hz. Stratified as pre-registered, the
feedback-dominated strata read 0.83× (as predicted, uninformative) and the **reference-dominated strata
read 1.02-1.19× — the strata where the lever was supposed to act show no reduction**, with the creep
stratum nominally higher on 34 s of exposure. Meanwhile the mirror confirms the filter removed the
excitation it targeted: D-clamp bind duty ×0.03 on this drive, in-episode binds effectively gone. The
one endpoint that would have shown a closed-loop benefit — the bell's proportional response to a
capped command step — is 2.41× on V288 vs 2.25× on V282 pooled, 2.14× vs 2.02× reference-dominated,
identical within CI. **The honest reading is a null with the instrument working**: the D-clamp-bind
path was a small share of what rings the 20 Hz mode, as the wire study's open-loop 8-13 % floor already
implied, and closing the loop did not multiply it into something visible. Caveats that keep this from
being a decision: one route, one day, a drive that was twice as slew-capped as any V282 route and
faster than r39; the operator's own three bookmarks all sit on census episodes, two of them in the
creep/3-8 m/s reference-dominated band. To turn this into a decision on the 18-22 Hz band: the per-route
rate CI here is ±40 % (n 46 episodes); detecting a 25 % reduction at the V282 route-to-route scatter
(97-323 ep/h) needs of order **4-6 V288 routes with ≥ 600 s engaged each, matched on speed profile and
hands-on share**, or, cheaper and sharper, the paired within-route test already available — the
capped-step envelope ratio — which at n ≈ 130 events per route resolves a 20 % change in the bell's
response with two more routes. The operator scores the symptom; this census only says the band is where
V282 left it.

## 7. Files

`grind1_census_v288_r5e.py` (this folder) · output `_scratch/grind1_census_v288_r5e.txt` · cache
`_scratch/grind1_census_v288_r5e_cache.pkl` (window census, episodes, whole-route mirror; delete to
recompute) · inputs `analysis-2020accord/_scratch/cache/v280/{r5e_v288,r39,r3a,r3c}{,_b4}.npz` (pre-existing)
· reused verbatim: `grind1_census_v282.{load helpers, onset_transient, steady_creep_at}`,
`wire_0xe4_20hz.{load_route, fine_line}`, `grind_incident_r35.{read_cells, demand_live, lerp}`,
`creep20_loop_id.{load, dejitter, runs, up1k}` · V288 filter mirrored from `build_v288_tva.sp_filter_tick`.
