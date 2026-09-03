# Sizing "flatten Kp(idx) to its low-demand value" against the 6.5–7.4 Hz strong-turn ripple on V280 rev 2 (2026-09-03, subagent `kpflat`)

Script: `kpflat_sizing.py` (beside this file; full output `_scratch/kpflat_sizing.txt`). SIZING ONLY — nothing was built.
Inputs: the V280 rev 2 image (`_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`), caches r31/r32/r33
(`_scratch/cache/v280/`), the FUN_00028ea6 chain mirror (`v280_map_profiles.py`), the tap plant ID (`plant_id_v278r3_tap.py`), the
F7 episodes of `HIGHANGLE-r32-r33-2026-09-02.md`. Ghidra was connected (stock `code.bin`); the Kp record bytes at `0xE5378` read
`05 00 | 00 44 70 88 d0 | f8 0002 8502 b802 b802` in Ghidra and in the V280 image alike. EVIDENCE unless marked BELIEF.

## 0. Headline

1. **The 7 Hz line is the crossover limit cycle of a linear inner loop that is UNSTABLE at the as-is Kp in the loaded high-angle
   regime, amplitude-regulated by the P clamp.** With the tap-identified plant (v ≤ 10 m/s, |angle| ≥ 30°, three parametric fits on
   two estimators agreeing to ±5 %), Kp 512–696 (idx 68–173, where 6 of the 7 episodes sit) gives **GM 0.50–0.86× at 8.2–9.1 Hz and PM
   −5…−25°**; Kp 349 (idx 26) is marginal (PM 10°, GM 1.32×). [EVIDENCE, model; coherence 0.7–0.94 over 5.5–8.6 Hz]
2. **Two independent methods put the critical Kp at ≈ 425.** (a) Linear: the flat Kp at which GM = 1 with Kd 128 is **425 / 443 / 426**
   on the three plant fits. (b) Describing function on the episodes themselves, no plant needed: the P clamp's fundamental gain on the
   chain's own P is N = 0.60–0.83, so the loop self-regulates to **K_eff = N·Kp(idx) = 394–575 (median 439)** on the six idx ≥ 106
   episodes, and 225 on the one idx-26 episode (2.2 m/s, 265°, a stiffer operating point). Same number from the wire and from the model.
3. **Flattening to Kp(12) = 295 puts every idx ≥ 68 episode below its measured K_eff (295 vs 394–575) and gives the linear loop PM 18–21°,
   GM 1.64–1.74× — the cycle cannot sustain there. It leaves a lightly damped ~9 Hz mode (Ms 3.6–4.0) and does NOT help the idx-26 class
   (K_eff 225; Kp there is already 349 → 295 stays above it).** Flat 341 is the thinnest flatten that clears all six (PM 11–14°, GM 1.36–1.43×).
   Flat 248 = Kp(0) gives PM 27–30°, GM 2.0–2.2× and clears the idx-26 episode too, at a larger authority cost.
4. **Cost, read from the chain: full-demand P-rail error 22.9 → 53.9 deg/s (flat 295); under a 1000-count load the steady full-demand
   rate falls 124 → 112 deg/s (−10 %), at the tap rail 111 → 80 (−28 %); a STALLED wheel at idx 58 gets 1474 instead of 2364 counts
   (−38 %) and does not reach the full push until idx ≈ 100 (as-is: idx ≈ 58).** That is precisely the low-command stall authority V280
   was built to restore. Flat 341: −28 % at idx 58, full push from idx ≈ 80.
5. **The lever is INERT on the highway lane-change symptom** — that regime runs at idx 2–12 where Kp is already 256–295 (Kp(12) = 295);
   a flat at 295 changes nothing there, up or down. [EVIDENCE: idx p50 4–5 per LOWCMD A4; Kp(idx ≤ 12) ≤ 295 from the table]
6. **Best alternative for the same margin at less authority cost: the feedback filter pole (0xC63E8/EA, 16.5 → 33 Hz, DC held) — it
   adds ~10° at 7–9 Hz at zero DC cost and combines: Kp 341 + fb 33 Hz ≈ PM 21°, GM 1.78×; Kp 295 + fb 33 Hz ≈ PM 28°, GM 2.07×.** Kd
   alone cannot fix the as-is Kp (best GM 0.76× at Kd 384), the output-lag pole cannot either (GM ≤ 1.06×), and Kd 0 makes it worse
   (the D term is what keeps the present cycle as mild as it is). [EVIDENCE on the model; BELIEF that the fb cells are otherwise unconstrained — see §4]
7. **Recommendation: Kp flat 341 on all reachable slots (0–9), Kd untouched, in one build, read by the tap.** Reason in §5. Flat 295 is
   the operator's literal ask and also clears the six episodes, at 10 percentage points more stall-authority cost; 341 is the smallest
   dose the two methods agree on with a 1.36× margin. If the operator would rather keep low-command stall authority, the fb-pole lever is
   the next thing to size for a build — not Kd.

## 1. The tables, read from the V280 rev 2 image [EVIDENCE: Python LE read of the pointer banks; raw byte scan; Ghidra read of slot 7]

Pointer bank `0xCB994` (Kp, 28 × 4-byte pointers → 5-knot LERP records `hdr=5, X[5], Y[5]`) and `0xCB7D4` (Kd, 4-knot). Kp records
live at `0xE4360…0xE43D8` (slots 0–5), `0xE5360…0xE53D8` (6–11), `0xE6360…` (12–17), `0xE7360…` (18–23), `0xE8240…` (24–27); Kd at
`0xE4108…`, `0xE5108…`, `0xE6108…`, `0xE7108…`, `0xE80B0…` with the same stride. Raw scan: the 5-knot X pattern `0 68 112 136 208`
occurs at exactly the six record X-fields of slots 0/1/3/4/6/7 and nowhere else in `[0x13000, 0x100000)`; the Kd X pattern `0 11 22 32`
occurs 28 times, all 28 being the bank's records. Only slots 0–9 are reachable (selector max 9, kit record); the live slot is 7.

| slots | Kp X | Kp Y | Kd Y (X 0 11 22 32) |
|---|---|---|---|
| 0, 4 | 0 68 112 136 208 | 205 461 614 696 696 | 128 |
| 1, 6 | 0 68 112 136 208 | 266 532 696 696 696 | 128 |
| 2, 5 | 0 48 128 160 208 | 205 410 717 717 717 | 64 |
| **3, 7 (LIVE)** | **0 68 112 136 208** | **248 512 645 696 696** | **128** |
| 8, 9 | 0 64 112 136 208 | 248 517 717 717 717 | 128 |
| 10–27 (dead) | 0 48 112 160 208 | 307 563 666 666 666 | 64 |

Slot 7 Kp at idx: 0:248 · 12:295 · 26:349 · 40:403 · 58:473 · 68:512 · 90:578 · 112:645 · 136:696 · 173–240:696 (P = E·Kp>>8, i.e.
0.97–2.72 per count of E). Kd's X axis ends at 32, so D = 16·ΔE everywhere that matters. A "flatten to the low-demand value" build
would set Y[1..4] = Y[0]-class value on the eight reachable records (or all 28); the X knots need not change.

**Lineage:** neither `0xCB994`/`0xCB7D4` nor any Kp/Kd record address appears in `BUILD-LINEAGE-PART1-LEVER-INDEX.md`. The Kp/Kd tables were
touched only by V275 (÷6, withdrawn unflashed) and V279 (Kp 256 flat + Kd 0 + fb clamp 0, a different loop, not flown). **Never flown edited.**

## 2. Inner-loop margins vs Kp [EVIDENCE for the shape and the ratios; the absolute numbers carry the plant fit]

Plant: G = wheel rate / tap T in the v ≤ 10 m/s, |angle| ≥ 30° stratum (175 s, 91 windows pooled over r31/r32/r33). The raw Welch grid
(0.39 Hz bins) is coherent 0.7–0.94 over 5.5–8.6 Hz and collapses above 8.6 Hz — exactly where the −180° crossing sits — so margins
were taken on parametric fits weighted by √coherence over 3–9.5 Hz:

| fit | params | model \|G\|×10⁻³ / phase at 4 / 6 / 7 / 8 / 10 Hz |
|---|---|---|
| pole + delay, driver-torque IV | K 0.382, pole 0.80 Hz, delay 8.4 ms | 74.8/−91 · 50.4/−101 · 43.3/−105 · 38.0/−109 · 30.4/−116 |
| pole + delay, direct | K 0.264, pole 1.09 Hz, delay 9.0 ms | 69.7/−88 · 47.4/−99 · 40.8/−104 · 35.8/−108 · 28.7/−116 |
| 2nd-order + delay, tq IV | K 0.252, fn 4.34 Hz, ζ 1.74 | 78.5/−87 · 51.5/−101 · 43.2/−106 · 36.8/−110 · 27.7/−118 |
| raw tq-IV | — | 73.8/−83 · 53.4/−99 · 48.6/−109 · 36.8/−111 · (14.9/−40, coh 0.09) |

L_in = [Kp/256 + 16(1−z⁻¹)] · 254/256 · H_lag · 5346/32768 · H_fb · 8 · z⁻¹ · G (as in LOWCMD §3), fine grid 0.5–40 Hz. Fit 1 shown;
fits 2 and 3 are within 2° / 0.05× everywhere (see the script output):

| Kp | \|L\| @ 4 / 6 / 7 / 8 / 10 Hz | phase @ 7 | PM @ f_c | GM @ f_180 | Ms (peak \|1/(1+L)\|) |
|---|---|---|---|---|---|
| as-is idx 26 = 349 | 3.22 1.82 1.43 1.16 0.80 | −157° | 10° @ 8.7 Hz | 1.32× @ 10.3 Hz | 7.0 @ 9.2 Hz |
| as-is idx 68 = 512 | 4.62 2.54 1.97 1.57 1.05 | −165° | −9° @ 10.3 | **0.77× @ 8.9** | 7.0 |
| as-is idx 112 = 645 | 5.77 3.15 2.43 1.93 1.27 | −169° | −21° @ 11.3 | **0.56× @ 8.3** | 3.0 |
| as-is idx 173 = 696 | 6.22 3.38 2.61 2.06 1.36 | −170° | −25° @ 11.7 | **0.50× @ 8.2** | 2.5 |
| flat 473 (Kp58) | 4.28 2.36 1.84 1.47 0.99 | −164° | −5° @ 9.9 | 0.86× @ 9.1 | 12.3 |
| flat 400 | 3.66 2.04 1.60 1.28 0.88 | −160° | 3° @ 9.3 | 1.09× @ 9.7 | 22.0 |
| **flat 341 (Kp24)** | 3.15 1.78 1.41 1.14 0.79 | −157° | **11° @ 8.7** | **1.36× @ 10.4** | 6.3 @ 9.2 |
| **flat 295 (Kp12)** | 2.77 1.59 1.26 1.03 0.72 | −153° | **18° @ 8.1** | **1.64× @ 11.1** | 4.0 @ 9.1 |
| flat 248 (Kp0) | 2.38 1.39 1.12 0.92 0.66 | −149° | 27° @ 7.6 | 2.00× @ 12.0 | 2.9 |
| flat 200 | 1.99 1.20 0.98 0.82 0.60 | −143° | 38° @ 6.9 | 2.43× @ 13.0 | 2.2 |
| **K_crit (GM = 1, Kd 128)** | | | | **425 / 443 / 426** on the three fits | |

- **Is the 6.5–7.4 Hz line the crossover?** Not quite — it is the −180° crossing region of an unstable linear loop (f_180 8.2–8.9 Hz at
  Kp 512–696, |L| there 1.2–2.0). A saturating limit cycle sits slightly BELOW the linear f_180 because the clamp's phase lag and the
  wheel's own amplitude pull the effective gain down (and the fits' phase is a few degrees optimistic at 7 Hz: raw −109° vs model −105°).
  7 Hz is where the model puts |L| ≈ 1.4–2.6 with phase −157…−170°, i.e. the cycle's own frequency. [EVIDENCE for the numbers;
  BELIEF for the 1–2 Hz offset explanation]
- **Direction:** lowering Kp moves the unity crossing DOWN in frequency (11.7 → 8.1 Hz from 696 → 295) and the −180° crossing UP
  (8.2 → 11.1 Hz) — the two separate, which is what a margin is. Raising Kp (pinning P harder, as rev 3 → V280 did) pushes them together.
- **The D term is 40 % of P at 4 Hz and is load-bearing:** Kd 0 at any of these Kp values is worse (§4). The phase at 7 Hz from the
  firmware alone is −38° (controller +5° with D, lag −54°, fb sum −23°, tick −2.5°); the plant supplies −105…−110°.
- Highway (v ≥ 20, |angle| < 8, hands light): PM 52–59° at 13 Hz for every Kp in 248–349 — nothing to fix and nothing at risk there.

## 3. Describing function on the episode frames [EVIDENCE — the wire and the chain mirror, open loop]

For each F7 episode (V280 rev 2 chain on the recorded 0x18F rate, line map, clamp 46080): N = 6–8.5 Hz amplitude of clip(P, ±15360) ÷ the
same of the unclipped P — the clamp's fundamental gain on the chain's own operating point; K_eff = N·Kp(idx50). Open-loop P-linear
fraction and T ripple/level under Kp scales and flats; steady tracking error = |T_meas| p50 ÷ (Kp/256 · 0.1603) in deg/s (247 counts of E per deg/s):

| route t0 | idx | Kp | N | **K_eff** | P-linear x1.0 / x0.8 / x0.62 / x0.5 / F473 / F341 / F295 / F248 | sim rip/L x1.0 / x0.8 / x0.62 / x0.5 / F473 / F341 / F295 / F248 | err deg/s @ Kp / ×0.62 / F295 (ref, rate) |
|---|---|---|---|---|---|---|---|
| r32 620.7 | 120 | 662 | 0.60 | **394** | .62 .71 .81 .86 .73 .85 .88 .93 | .44 .49 .53 .57 .51 .58 .62 .67 | 9.3 / 15.0 / 20.9 (66.8; 43.2) |
| r32 692.8 | 109 | 636 | 0.67 | **424** | .66 .77 .85 .89 .78 .89 .93 .97 | .61 .64 .69 .75 .66 .72 .75 .81 | 8.7 / 14.1 / 18.8 (60.7; 52.3) |
| r32 726.5 | 173 | 696 | 0.63 | **439** | .66 .75 .87 .91 .76 .86 .90 .94 | .49 .56 .67 .75 .58 .68 .73 .81 | 9.7 / 15.7 / 22.9 (96.3; 91.3) |
| r33 100.8 | 26 | 349 | 0.64 | **225** | .70 .75 .82 .87 .54 .79 .86 .87 | .40 .44 .50 .57 .39 .47 .51 .53 | 19.7 / 31.8 / 23.3 (14.5; 33.3) |
| r33 212.5 | 136 | 696 | 0.83 | **575** | .69 .83 .94 .99 .89 .99 .99 1.0 | 1.04 1.09 1.12 1.15 1.04 1.14 1.18 1.22 | 5.5 / 8.8 / 12.9 (75.7; 89.1) |
| r33 224.1 | 106 | 625 | 0.76 | **472** | .63 .76 .92 .96 .76 .95 .99 1.0 | .67 .73 .80 .81 .73 .82 .86 .90 | 8.3 / 13.3 / 17.5 (58.7; 41.2) |
| r33 833.5 | 106 | 625 | 0.83 | **520** | .79 .86 .92 .95 .84 .92 .93 .94 | .89 .94 1.02 1.07 .85 .92 .92 .99 | 6.2 / 10.0 / 13.1 (58.7; 71.1) |

- **K_eff = 394–575 (median 439) on the six idx ≥ 106 episodes; 225 on the idx-26 one.** N = 0.60–0.83 — the clamp is taking 17–40 % of
  the gain out, which is the amplitude the cycle needs to sit at K_crit. This agrees with the linear K_crit ≈ 425 to within the spread
  of operating points. [EVIDENCE: two methods, one number]
- **Why the open-loop "Kp × 0.5 RAISES ripple/level" is not evidence against the lever:** on the recorded rate the rate ripple is fixed
  (it is the closed loop's product), so a lower Kp cuts the push (level) faster than the ripple — the table reproduces it (0.44 → 0.57
  at ×0.5, 0.62 at flat 295). The P-linear fraction rising to 0.86–1.0 says the same thing: at flat 295 the clamp no longer regulates,
  so the loop is either linearly stable (cycle dies) or linearly unstable without a limiter (cycle grows to the clamp again). The
  margin table settles which: PM +18°, GM 1.64× ⇒ it dies. Open-loop counterfactuals cannot see this; the closed-loop model and the
  K_eff measurement can. [EVIDENCE for the numbers; the inference is standard describing-function theory]
- **Tracking cost in-episode:** the steady rate error a 590–1070-count push needs rises from 5.5–9.7 deg/s (as-is) to 12.9–22.9 deg/s
  at flat 295 — 17–34 % of these episodes' 59–96 deg/s references, vs 6–15 % now. The wheel in a strong turn would run that much
  further below its reference under the same load.

**Authority at full and mid demand (P-only steady state, line map, from the chain):**

| Kp | P-rail error deg/s | full push only below (deg/s) | full-demand rate under load 600 / 1000 / 1500 / 2472 counts | idx 100 (ref 55.7): rate @ 600 / 1000 |
|---|---|---|---|---|
| as-is 696 | 22.9 | 110.8 | 128.1 / 124.3 / 119.7 / 110.8 | 49.3 / 45.1 |
| flat 473 | 33.6 | 100.0 | 125.4 / 120.0 / 113.1 / 100.0 | 47.5 / 42.0 |
| flat 400 | 39.8 | 93.9 | 123.9 / 117.5 / 109.4 / 93.9 | 46.0 / 39.5 |
| **flat 341** | 46.7 | 87.0 | 122.3 / 114.7 / 105.2 / 87.0 | 44.3 / 36.7 |
| **flat 295** | 53.9 | 79.7 | 120.5 / 111.7 / 100.8 / 79.7 | 42.6 / 33.8 |
| flat 248 | 64.2 | 69.5 | 118.0 / 107.6 / 94.5 / 69.5 | 40.1 / 29.6 |

**Stalled wheel (rate 0), delivered T by idx — the V280 stall class:**

| idx (ref deg/s) | as-is | flat 473 | 400 | 341 | 295 | 248 |
|---|---|---|---|---|---|---|
| 26 (14.5) | 781 | 1059 | 896 | 764 | 661 | 555 |
| 40 (22.3) | 1392 | 1633 | 1381 | 1177 | 1018 | 856 |
| 58 (32.3) | 2364 | 2363 | 1998 | 1703 | 1474 | 1239 |
| 68 (37.8) | 2462 | 2462 | 2342 | 1997 | 1728 | 1452 |
| 80 (44.5) | 2462 | 2462 | 2462 | 2350 | 2033 | 1709 |
| 100 (55.7) | 2462 | 2462 | 2462 | 2462 | 2462 | 2137 |
| ≥ 120 | 2462 (rail) | = | = | = | = | = |

What the operator would lose: hands-light full-demand rate (measured 125/150 p50/p90 at ~690-count load) drops ~5–6 % at flat 295 and
~4 % at 341; loaded turns lose more (−10 % at 1000 counts, −28 % at the rail for 295); **the stalled low-command push (idx 40–80) loses
17–38 % at 295, 13–28 % at 341** — that is the r31 stall-stutter regime V280's line map was built to feed. Above idx ≈ 100 (295) /
≈ 80 (341) nothing is lost at stall.

## 4. Alternative levers for an inner-loop crossover limit cycle — same model, same margins

Kp as-is 645 (idx 112, the episode class) and Kp flat 341 / 295 for the combinations. Plant fit 1; fits 2–3 agree within a few degrees.

| lever (cell) | at Kp 645 (as-is) | at Kp 341 | at Kp 295 | lineage | EVIDENCE / BELIEF | the sentence a null would license |
|---|---|---|---|---|---|---|
| **Kp flat** (`0xCB994` records Y[1..4]) | — | PM 11°, GM 1.36× | PM 18°, GM 1.64× | never flown edited (V275/V279 unflown) | E: model + DF agree on K_crit ≈ 425 | "A flat Kp ≤ 341 that leaves F7 episodes at ≥ 4/100 s with tap ripple/level ≥ 0.4 in idx ≥ 68 falsifies the P-gain limit-cycle mechanism; the ripple is then not set by the inner loop's Kp" |
| Kd 0 (`0xCB7D4`) | GM 0.39×, worse | GM 0.73× — UNSTABLE | GM 0.85× — unstable | V279 unflown | E on the model | (do not fly: predicted worse at every Kp) |
| Kd 64 | GM 0.46× | GM 1.03×, PM 1° | GM 1.26×, PM 8° | — | E | — |
| Kd 192 / 256 / 384 | GM 0.66 / 0.73 / 0.76× — never stable | 1.45 / 1.36 / 1.09× | 1.64 / 1.47 / 1.14× | — | E; BELIEF that D-rail duty stays low (0.01–0.06 at 128; rails at ΔE > 320/tick at 256) and that 0x18F quantisation noise ×2 is tolerable | "Kd 256 alone leaving the F7 rate unchanged says the 7 Hz lead is cancelled by the fb lag, as the model shows (crossover just moves to 11–13 Hz)" |
| output-lag pole 5 → 10/20/40 Hz (`0xC63EC/EE`, DC held) | GM 0.57 / 0.63 / 0.70× — never stable | 1.22 / 1.17 / 1.19× | 1.41 / 1.30 / 1.28× | struck in the lineage as "DEAD ON ARITHMETIC" for a different (6–9 Hz command) purpose | E on the model | "Removing 40° of lag at 7 Hz raises \|L\| at the new crossover as fast as it adds phase — the lever cannot stabilise the as-is Kp" |
| **fb pole 16.5 → 33 Hz (`0xC63E8/EA`, DC 30.89 held: a 832, b 2965)** | GM 0.74×, PM −10° | **PM 21°, GM 1.78×** | **PM 28°, GM 2.07×** | never flown edited | E on the model; BELIEF that the cell is private (readers not censused here) and that the fb clamp meaning (46080 at DC) is unchanged (DC held) | "fb pole 33 Hz alone at as-is Kp changing nothing is expected (GM 0.74×); it is only a companion to a Kp flatten" |
| fb pole → 66 Hz (a 676, b 5374) | GM 0.94× — marginal | PM 28°, GM 2.16× | PM 35°, GM 2.46× | — | E; more 0x18F noise into P (BELIEF: 2× at 30 Hz) | — |
| fb single-sample ×2 (drop the z⁻¹ sum; code edit, not cal) | GM 0.60× | GM 1.44× | GM 1.71× | — | E; a CODE edit, cave-class risk | not worth it: +2° at 7 Hz |
| Combined Kp 341 + Kd 192 + fb 33 Hz | — | PM 26°, GM 1.71× | — | | E on the model | |
| Combined Kp 295 + Kd 192 + fb 33 Hz | — | — | PM 32°, GM 1.86× | | E | |

- **Nothing stabilises the as-is Kp 645–696.** The best single alternative there is fb → 66 Hz at GM 0.94×. The plant's −105…−110° at
  7 Hz plus the firmware's −38° leaves too little phase for any lead the firmware can add without also raising |L| at the new crossover.
- **Kd is not the lever** the earlier study nominated ("the D term as phase lead"): more Kd moves the crossover up into the plant's steeper
  phase and gains nothing (GM 0.66–0.76× at Kp 645). Kd 0 is actively worse, at every Kp.
- **The feedback filter pole is the cheapest phase**: ~+10° at 7–9 Hz for free at DC, and it compounds with a Kp flatten. Its constraints
  are un-censused (reader census, and whether the fb lag is doing plant-side work on the highway where PM is already 50°+) — size it
  before any build touches it. [BELIEF]

## 5. Recommendation (do NOT build from this page; this is the sizing)

**Lever: Kp flattened to 341 (= Kp(24)) on Y[1..4] of every reachable Kp record (slots 0–9, uniformly; the eight distinct-shaped records
0/1/3/4/6/7/8/9 — or all 28 for tidiness), Kd and everything else untouched.** Why 341 over the operator's literal 295: both clear all
six idx ≥ 106 episodes' measured K_eff (394–575) and the model's K_crit (425–443); 341 keeps 10 percentage points more stall
authority at idx 40–80 (−13…−28 % vs −17…−38 %) and ~1.5 % more hands-light full-demand rate; its margin (GM 1.36×, PM 11°) is thin
but is the margin at which the six episodes' own K_eff (min 394) sits 16 % above it. **If the operator prefers headroom to stall authority,
295 (GM 1.64×, PM 18°) is the same lever one notch further and equally interpretable; 248 is the first value that also clears the idx-26
class (K_eff 225) — but at −25…−48 % stall authority.** Neither value touches the highway lane-change regime (idx ≤ 12).

**Instrument (already on the wire in V280):** the CAN-427 tap (`((b0&3)<<8)|b1`, sign bit 9, ×8) and 0x18F rate / angle / 0xE4 cmd.
One strong-turn drive, 2–9 m/s, |angle| ≥ 30°, hands light, ~60–90 s of high-angle engaged time:
- **Primary:** F7 episode rate (6–8.5 Hz rate envelope > 103 wire, ≥ 1 s, |angle| ≥ 30°) per 100 s high-angle — V280 rev 2 reads 5.3
  pooled (8.1 / 4.3); **PASS ≤ 2, FAIL ≥ 4.** And tap 6–8.5 Hz ripple/level on those frames — V280 reads 0.42–0.99 in-episode;
  **PASS ≤ 0.25 median in idx ≥ 68 frames, FAIL ≥ 0.4.**
- **Mechanism check:** the P-linear fraction is not on the wire, but N is: the tap's 6–8.5 Hz amplitude divided by the chain's unclipped
  P amplitude on the same frames. With flat 341 the chain predicts N → 1.0 (no clamping) if the ripple survives — a surviving ripple with
  N ≈ 1 says the loop is linearly unstable at 341 (K_crit measured wrong, plant stiffer than fitted); a surviving ripple with N ≈ 0.7
  says the ripple is not P's at all.
- **Cost check:** hands-light full-demand rate p50 (prereg (iv); V280 125/123) — expect ~120; **FAIL if < 105** (a 15 % loss says the loaded
  plant gain is lower than the chain's DC arithmetic); and the stalled-frame tap level at idx 40–80 — expect −13…−28 % vs r32/r33's
  same-idx stalled frames.
- **Collateral to watch:** a NEW lightly damped ~9 Hz ring on rough road at |angle| ≥ 30° (Ms 6.3 at 341) — score the 8.5–10 Hz rate band;
  and the r31-class stall stutter returning at idx 40–80 (P railed, wheel < 0.6× reference, 7 Hz) — the class V280 removed; if it returns
  at 341 the stall-authority cost is the binding constraint and the fb-pole companion (Kp 341 + fb 33 Hz, GM 1.78×) or 295 + fb is the next sizing.

**The FAIL sentence:** *"If, with Kp flat 341, F7 episodes still occur at ≥ 4 per 100 s of high-angle engaged time with tap 6–8.5 Hz
ripple/level ≥ 0.4 in the idx ≥ 68 frames, the 7 Hz ripple is not the P-gain limit cycle this page describes — the describing-function
K_eff and the plant fit both mis-sized it — and no further Kp reduction is licensed; the mechanism goes back to the outer loop or to a
plant-side (base-assist / V268 damper) resonance."* A null on the cost side reads: *"full-demand hands-light rate p50 < 105 deg/s
means the loaded plant gain is lower than the chain's DC arithmetic and the line map's ceiling is no longer reachable — revert."*

## 6. What is EVIDENCE and what is BELIEF, in one place

- EVIDENCE: the 28 Kp/Kd tables (bytes, two methods, Ghidra concurs on slot 7); the lineage null on the Kp/Kd addresses (grep of the lever
  index and the build scripts); the raw plant grid and coherences; the chain mirror's per-episode N, K_eff, P-linear fractions, ripple/level,
  tracking-error and stall-authority arithmetic; the highway idx range (LOWCMD A4).
- BELIEF (model-dependent): the absolute PM/GM/K_crit numbers (three parametric fits agree, but all descend from one 175-s stratum with
  coherence < 0.4 below 4.7 Hz and above 8.6 Hz); that the limit cycle dies rather than re-forms at a lower amplitude when Kp < K_crit
  (standard DF theory, and K_eff's 16 % gap over 341 is thin); that the fb-pole cells have no other reader; that D-rail and noise stay
  benign at Kd ≥ 192 (not needed for the recommended build).
- NOT sized here: whether the operator's "very slight" feel maps to ripple/level 0.4 or to the F7 count — score the bands, let him score
  the symptom; the r34 drive (`highangle34`) may add episodes at other operating points and should be folded into the K_eff table before
  a build is cut.
