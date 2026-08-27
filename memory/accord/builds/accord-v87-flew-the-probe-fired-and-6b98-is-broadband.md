---
name: accord-v87-flew-the-probe-fired-and-6b98-is-broadband
description: "V87 flew as route 71 fault-free; its 427 probe measured |gp-0x6b98| for the first time — the ratcheting is a plant mode driven by BROADBAND command content, not a commanded tone."
metadata: 
  node_type: memory
  type: project
  originSessionId: 22c24ebf-36e0-4a19-97d3-9b2d73bedafd
  modified: 2026-08-09T17:05:07.590Z
---

**V87 FLEW as route `71`** (`75604b0a432fdc89_00000071--ac50da2a6a`, cache `_scratch/cache/r71/`), 2026-08-09.
23,765 frames / 239.6 s, 52.4 % engaged, **fault-free**, 0 sentinels, no EPS event in 1,262
`onroadEvents`. Operator: **grinding, micro-ratcheting AND ratcheting all present** — the PREDICTED
result, since V87 is byte-stock at all four measured grind-#1 addresses (`0x3AB76`/`0x3AC20` = `aa`,
`0x3AA96` = `c5`, `0xC6446` = 512). See [[accord-v81-carries-neither-grind1-fix]]; unlike V81's, this
absence was **documented, not silent** — the V38 rebase dropped Lever B on purpose.

## ✅ The 427 probe fired — the kit's biggest instrument gain since the cave
Re-measured with both predecessor routes as controls: `6f`/V86 **56.45 %** non-zero / 297 distinct,
`70`/V86B **66.98 %** / 240, **`71`/V87 99.02 % / 946 / range [0,1023] / railed 3.23 %.**
⊕ Supersedes `STATE.md`'s "22.4 %/20.2 % non-zero, 255/51 distinct" for the V86/V86B 427 stream.

**`|gp-0x6b98|` engaged: median 208 counts, p90 966, railed (≥1637) 2.35 %. 6–9 Hz ripple rms 29.0,
p-p 162 counts.** ⇒ 🛑 **the "assumed ~120 counts p-p, may swing 5×" unknown is CLOSED — low by
1.35×.** Any future filter's phase budget can be sized on a measurement. ⚠ 1637 is the **probe's**
ceiling (Honda's ×5/8 packer at 10 bits), not the command's.

## ★★★★★ The fork: a lightly-damped mode driven by BROADBAND content
On rectification-transparent unclipped engaged windows (white-noise p95 floor 10.5, nw = 256):
column torque **12.86 [5.73, 16.68]**, above floor in **50 %** of windows · **delivered command
`|gp-0x6b98|` 4.03 [3.54, 6.22], 7.1 % = chance** · openpilot 2.96, 7.1 %.
**But the link is real:** coherence cmd↔column **0.439 at 7.79 Hz** vs a **shuffled-pairs control of
0.178** (background 0.03–0.16, null 1/n = 0.071); per-window **corr = +0.62**, command prominence
12.67 in the top ratchet quartile. ⚠ The `|column/command|` ratio beats its shuffled control by only
**1.37–1.57×**, so the apparent "6× resonant peak" is mostly the two spectra — **do not claim it.**

⇒ **The lever class is "less broadband HF in the delivered command", NOT a notch.** There is no tone
in the command to notch. Consistent with [[accord-ratchet-is-a-lightly-damped-resonance]].

★ **Engagement, SPEED-MATCHED at 2–4 m/s** (the raw ratio is void — 59 % of manual frames are PARKED,
0 % of engaged are): 0.5–3 Hz **0.42×** · 3–6 0.73× · 6–9 1.73× · 9–12 1.76× · 12–15 1.79× ·
**15–22 Hz 3.37×, the only row with disjoint CIs.** Engagement REMOVES LF command motion and ADDS HF,
most in grind #1's own band.

## 🛑 Two instrument limits, and two retractions
1. **Rectification**: `abs()` is transparent only while the sign holds — **0 of 42** windows at
   10.28 s, 14 of 37 at 5.14 s. 7.79 Hz about zero folds to 15.58 Hz. **V88 fixes it** with
   `b7 = sign(gp-0x6b98)` at 100 Hz (cave `0xC4B38` → `6894`). See [[accord-v88-lever-b-restored]].
2. **Nyquist**: 427 runs at **49.81 Hz** ⇒ nothing above ~15 Hz is claimable; 28 Hz aliases to 21.8.
   On the 100 Hz channels engaged `tq` reads 337 (6–9), 254 (15–22), **41 (24–32)** ⇒ mostly real,
   not separably so.
3. 🛑 **RETRACTED — a "differentiator"** `op cmd → delivered` rising 9× with f. At coherence
   0.035–0.077 vs a `1/n_avg = 0.043` null, `sqrt(Pyy/Pxx)/sqrt(n_avg)` reproduces it in **all seven
   bands** (0.89–1.08). It was a very persuasive r24/r26 story and it was noise.
4. 🛑 **RETRACTED — the phase-randomised surrogate as a "no line" control.** Phase randomisation
   **preserves `|X(f)|`**, so it preserves a line's power for a single-window periodogram. Use the
   white-noise floor at the same `nw` and the paired column comparison. Reinforces
   [[feedback-run-the-control-before-the-measurement]].

🛑 Route `71` is **parking-lot only** — v_max 5.91 m/s, **0.0 s engaged ≥ 50 km/h, 2.1 engaged
minutes**; the in-route split-half null on 6–9 Hz power is **[0.18, 5.51]**. Fourth consecutive route
with no highway. See [[accord-averaged-spectrum-needs-matched-speed-distributions]].

⊕ `gp-0x6b70` (Coulomb friction compensator) on route `71`: non-zero **99.80 %**, `|v|≥64` **93.84 %**,
negative **67.19 %**, aggregator optional-term gate **open 100 %** of 23,766 frames.
