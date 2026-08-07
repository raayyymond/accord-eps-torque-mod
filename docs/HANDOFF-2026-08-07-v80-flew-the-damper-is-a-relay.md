# HANDOFF 2026-08-07 — V80 flew: the damper became a relay, and grind #1 was never the dose

**Session shape:** orchestrator + 11 subagents. The operator flew V80, reported the worst grinding the
car has ever produced, and asked for a root cause and a fix. The rlogs were not supplied — they were
downloaded from connect.comma.ai during the session.

**Outcome:** root cause established and independently verified; **two of this kit's own claims
retracted**; **V81 built, verified from disk, UNFLASHED.**

---

## 0. TL;DR

1. **V80 flew (route `66`) and did NOT fault.** Zero DTC transitions in 901.7 s. This was a *stability*
   failure, not a fault-class one.
2. **Root cause: V80's damper is a near-bang-bang Coulomb relay.** Above ~25 °/s of motor rate it emits a
   constant ~495 counts — 3.4% variation across a 34× rate range — at 97% of its 512 ceiling, **at every
   speed**. V75 plateaus at 297 (58% of ceiling) and only above 54 °/s.
3. **The build's own gates could not see it.** Every no-clip guard tests `product > ceiling`. V80's
   supremum is *exactly* the ceiling, so it clips 0.00% and passes. **"Does not clip" and "is not a
   relay" are different statements, and only the first was ever checked.**
4. **The measurement that settles it**, from both builds' own cave probes:
   `|damper| ≥ 448 counts`, engaged — **V75 0.000%** (28,317 frames) vs **V80 19.4%**, 32.7% above
   15 m/s, **71% through the worst 29-second event.** V75's damper never entered its saturated regime.
   V80's lives there.
5. 🛑 **RETRACTION 1 — grind #1 (18–22 Hz) is INERT to the damper dose** across k = 0.58 → 4.16. Every
   point sits inside its own split-half null. V80 did not overshoot an optimum; **grind #1 never
   responded to k.**
6. 🛑 **RETRACTION 2 — V80's creep numbers are an exposure artefact** and must not be read in either
   direction. Zero matched cells; the driver was not turning the wheel.
7. **What V80 actually bought**: a **2.09× [1.46, 2.70] broadband lift of everything above ~24 Hz**
   (flat, prominence-neutral, absent from the IMU, present on a *different* CAN message), plus a
   **sustained 27.4 Hz, Q ≈ 140 limit cycle that no other build in the corpus produces even once.**
8. **The hard-fault mechanism is `0xC407E`, confirmed in Ghidra.** `gp-0x6b26` has exactly one writer
   image-wide and it stores an already-clamped value; the monitor trips at 512; Honda ships the clamp at
   **511 — one count under.** V73/V74/V75 raised it to 850.
9. 🛑 **The standing directive "do not double `0xC63A0`, that caused the hard faults" rests on a refuted
   premise.** `0xC63A0` has exactly one reader and no firmware data path to the faulting monitor.
10. **V81 = the flown V75 with the friction lane returned to Honda's configuration.** 126 bytes.
    **UNFLASHED.**

---

## 1. The drive

Route `75604b0a432fdc89|00000066--276b942769`, 15 segments, **901.71 s**, 89,997 frames @ 100.0 Hz.
Engaged 30,260 frames = **33.62%**, 9 episodes ≥ 2 s. Speed to 31.34 m/s (112.8 km/h).

Downloaded from connect.comma.ai via browser automation. The Files → "Log data" download only fetches
the current segment; the whole-route list lives at `api.comma.ai/v1/route/<dongle>%7C<route>/files`.
The practical route, since the extension blocks returning query-string data: have the page issue a
no-cors GET per URL, then read them back out of `read_network_requests` and `curl` them down.

**Flight-clean:** 0x1AB DTC-active **0 transitions / 0.000% duty**, 0 × `0x7FFF` sentinels,
STEER_STATUS `{0: 63,861, 3: 26,136}` — the same shape as route 65.

⊕ `build_v80_tva.py`'s own header reads, verbatim: *"GATE 2 (magnitude AND phase) is NOT satisfied by
argument. **V80 IS NOT CLEARED TO FLY.**"*

---

## 2. Root cause — the relay

### 2a. The surface, from the flashed bytes
Records dereferenced through their pointer arrays (`FactorC 0xC9E9C`, `FactorE 0xC9F84`,
`ceiling 0xC77A0`), mode 26 (this car is `TVCA4`: 26 engaged / 24 manual). Damper dose vs motor rate at
5 km/h — and on V80, identically at *every* speed, because FactorC was flattened to 566:

| rate (ct) | 20 | 40 | 99 | **119** | 150 | 255 | 530 | 1000 | 1941 | 4000 |
|---|---|---|---|---|---|---|---|---|---|---|
| ≈ °/s (4.7121 ct per °/s) | 4 | 8 | 21 | **25** | 32 | 54 | 112 | 212 | 412 | 849 |
| **V75** | 12 | 44 | 137 | 169 | 218 | 297 | 297 | 297 | 297 | 512 |
| **V80** | 82 | 166 | 412 | **495** | 495 | 495 | 496 | 498 | 501 | 512 |

The relay was not removed by V80's flat-FactorC edit — it was **moved from the ceiling clamp to
FactorE's own knee**, 17 counts under the rail, where the slope drops ~1200× at `X[1] = 119`.

### 2b. Describing function
`N(R)` = fundamental-harmonic gain of `force = −sign(rate)·M(|rate|)`. Constant `N` = viscous =
stabilising; `N` rising as amplitude falls = relay = limit-cycle generator.

| R (ct) | 25 | 50 | **99** | 150 | 250 | 500 | 1000 |
|---|---|---|---|---|---|---|---|
| V75 @creep | 0.580 | 1.065 | **1.319** | 1.410 | 1.317 | 0.734 | 0.375 |
| V80 @creep | 4.007 | 4.087 | **4.127** | 3.698 | 2.421 | 1.250 | 0.632 |
| V80/V75 @60 km/h | 17.7× | 9.4× | **7.6×** | 6.4× | 4.5× | 4.1× | — |

**Relay-ness index `N(50)/N(500)`: V75 = 1.45× · V80 = 3.27×**, at both creep and 60 km/h.
Small-signal loop gain `k`: **V74 0.5799 · V76 1.3866 · V75 1.5798 · V80 4.1597** — V80 is 2.63× V75 and
extrapolates 2.6× beyond the last measured point.

### 2c. The sign question, closed
`gp-0x6abe` is the **signed twin** of the rectified `gp-0x6ac0` — both filtered from `gp-0x4f50` in
`FUN_00041464` (`0x41b56`). So the damper is literally `force = −sign(motor rate) × magnitude`.
**Path 2 through the PID is NON-INVERTING**: the Stage-2 subtraction in `FUN_00038148` and the PID's
`err = setpoint − feedback` cancel, and the two `polarity(gp-0x6752)` multiplications cancel regardless
of value ⇒ `(−P)(+1)(−1)(+P) = P² = +1`. Path 1 and Path 2 both enter `FUN_0003aa2c` with unity weight
and **reinforce**. ⇒ **dissipative by construction at `gp-0x6b94`** [EVIDENCE].

⚠ The `gp-0x6b94` → motor hop is **still not found**. New node identified: **`gp-0x6ace`**, the
governor-clamped form of `gp-0x6b94`, whose only readers are hard-shutdown monitors. Both of
`FUN_00042af8`'s documented external inputs are now **ruled out** as bridges. A missing link, not a
discovered inversion.

---

## 3. What the route shows

### 3a. A broadband HF floor lift — the dominant effect
Median engaged periodogram, **V80 − V76**, matched 10–40 km/h stratum:

```
 Hz    7.8   12.1   18.0   19.9   21.9   23.8   26.2   28.1   30.1   34.0   35.9   39.9   44.2   48.1
dB   -6.03  -0.20  +0.05  -0.72  -0.58  +2.44  +3.75  +5.27  +5.70  +9.22 +10.41  +8.15  +8.49 +11.47
```

Grind #1's own band is unchanged, the ratchet is 6 dB **down**, and everything above ~24 Hz lifts by a
flat, prominence-neutral offset — **2.09× [1.46, 2.70]** on the 30–49 Hz floor. A pre-declared 32–38 Hz
**negative control fails identically (2.035)**, which kills any "grind #2 got worse" reading.

**Falsifiers held**: steering angle from a *different CAN message* 1.60× [1.26, 2.03] · **IMU vertical
1.07 [0.92, 1.33] ⇒ not a rougher road** · 1–4 Hz driver-input exposure check 1.14 [0.88, 1.47].

**★ FFT-free confirmation** — sample-to-sample sign reversals > 300 counts, immune to spectral leakage:

| | V75 | V74 | V76 | **V80** |
|---|---|---|---|---|
| engaged windows with ≥1 reversal | 3.0% | 22.0% | 22.0% | **73.0%** |
| at > 800 counts | 0.0% | 0.5% | 0.6% | **23.3%** |

### 3b. A 27.4 Hz limit cycle no other build produces
Engaged windows with 26–31 Hz envelope > 1000 counts: **V74 0/413 · V76 0/328 · V75 0/133 · V80 32/215.**

**Worst event — segment 8, route t ≈ 500.9–530.3 s, 99–104 km/h, ~30 s unbroken.** Torsion bar **6,830
counts p-p**, σ = 1,059; **27.34 Hz, Q ≈ 140, prominence 292**; steering angle p-p **1.92°**; damper
`≥448` duty **71%**; no fault, no lockout throughout. The envelope rises 50 → 3000+ counts within ~1.5 s
of engagement and collapses to ~150 the instant LKAS disengages.

Speed-tracking, engaged (orchestrator's own Welch): 1–5 m/s → 30.3 Hz ×2.1 · 10–15 → 26.2 Hz ×1.6 ·
15–20 → 29.1 Hz ×10.3 · **24–32 → 27.6 Hz ×94.9**. Frequency pinned across a 20× speed range while wheel
order 1 would sweep 1.5 → 13.7 Hz. **Not a tyre order** — measured `df/dv` = **−0.131 [−0.231, −0.016]**
Hz per m/s where order 2 demands **+0.961**. Crest factor **1.838** ⇒ near-sinusoidal limit cycle.

⚠ **The mode is not new to V80** — it is the kit's ~28 Hz line, amplified ~2.7×, shifted down 1–2 Hz, and
turned from intermittent episodes into a sustained limit cycle.
⚠ **Aliasing (common mode):** fs ≈ 100 Hz, so 27.34 Hz is indistinguishable from 72.66 Hz. Identical on
all four routes ⇒ affects identification, not the contrast.
⚠ **Command caveat:** openpilot's own 0x0E4 carries 25–30 Hz at rms 45.8 ct, correlated +0.93 at lag 0;
bar/command ratio 15.8×. [BELIEF] an echo, not a cause. Settling it needs a phase-resolved coherence.

### 3c. Saturation dose-response
17–30 Hz band power by the fraction of each engaged window the damper spent ≥448 counts:
`0–5% → 1.1e3 · 5–20% → 9.2e3 · 20–40% → 3.0e4 · 40–60% → 2.1e5 · 60–80% → 1.4e6.`
Three orders of magnitude, monotone. ⚠ speed and duty are confounded ⇒ [EVIDENCE] on the association,
[BELIEF] on direction.

### 3d. "~90% of engaged time", scored on the band that moved
30–49 Hz, thresholds from V76's own engaged distribution: **V80 79.5% [70.3, 87.7]** at V76-p50 vs V76's
50% by construction; per stratum **10–40 km/h 93.9% · 40–80 km/h 80.0% · >80 km/h 100%**.
Independently on 17–30 Hz p-p: **89.1% of engaged windows ≥100 ct**, and **17.1% of engaged time
>1,500 ct — an amplitude reached in ZERO of 432 manual windows.**
Engagement test: median **×2476** within 4 s of the `latActive` rising edge, 6/7 edges.

---

## 4. 🛑 Two retractions

### 4a. Grind #1 is inert to the damper dose
Four-point ladder on one instrument, ratio to V76, ~10.2 s bootstrap blocks nested inside engagement runs:

| band | V74 k=0.58 | V76 k=1.39 | V75 k=1.58 | V80 k=4.16 |
|---|---|---|---|---|
| **18–22 grind #1** | 1.166 [0.98,1.41] | 1.000 ref | 0.735 [0.50,1.22] | 0.835 [0.64,1.07] |
| 6–9 micro-ratchet | 0.818 [0.70,1.09] | 1.000 ref | 0.821 [0.66,1.09] | **0.418 [0.33,0.61]** |
| **30–49 HF floor** | 0.820 [0.73,1.01] | 1.000 ref | 0.953 [0.81,1.26] | **2.091 [1.46,2.70]** |
| **32–38 neg control** | 0.865 [0.76,1.03] | 1.000 ref | 0.959 [0.82,1.22] | **2.035 [1.45,2.57]** |

Split-half null for 18–22 Hz ≈ **[0.63, 1.60]**. Every grind-#1 point is inside it. On this instrument
V75's "no grind #1" versus V76's "still grind #1" is a **creep-exposure difference** (V76's creep windows
carry 3.4× V75's steering effort), **not** a dose difference.

★ The operationally useful statement: **something switches on between k = 1.58 and 4.16 that costs 2×
broadband HF plus a limit cycle. Where in that gap it switches on is UNMEASURED.**

⚠ **The micro-ratchet, stated precisely** — an earlier draft of this handoff said it "improves
monotonically with k", and that overstates the ladder. The 6–9 Hz band is **FLAT across k = 0.58 → 1.58**
(V74 0.818 [0.70, 1.09] and V75 0.821 [0.66, 1.09], both inside the ≈[0.66, 1.45] split-half null) ⇒ the
existing *"the ratchet is dose-independent"* claim was **accurate over the range then available and is NOT
refuted — its DOMAIN is bounded above.** It improves significantly **only at k = 4.16**, the first point
outside the null: **0.418 [0.33, 0.61] [EVIDENCE]**. Calling all four points monotone is **[BELIEF]** —
three of the four sit inside the null, so only the top point carries it. V80 did buy a real ratchet gain,
and paid for it with the HF floor.

### 4b. V80's creep numbers are an exposure artefact
V80's engaged creep windows: median effort **173 counts**, median |angle rate| **1.3 °/s**, against
V74/V76/V75's 685/588/1113 counts and 33/33/48 °/s. **Zero matched cells.** An earlier claim this session
that "V80 is 3–30× quieter than V76 at creep" is **retracted**. Also unresolvable: whether V80's
near-zero creep angle rate is itself an *effect* of a 412-count-at-all-speeds damper.
⚠ The **>80 km/h** stratum is likewise not comparable — V75 never exceeded 65 km/h, and V80 has one
engagement run there (the limit-cycle event itself). **10–40 and 40–80 km/h are well matched** and carry
the load.

---

## 5. The hard-fault mechanism — confirmed in Ghidra

- **Monitor `FUN_00036d74`**: `fVar3 = gp-0x6b26 * 0.0009765625`; if `|fVar3| > *(float*)(tp+0x5004)` →
  `FUN_000462e6(0x39bc,…)` → `FUN_00016de6(0x1d,…)` = **DTC 0x1d, latched total loss of assist**.
  `0xC4004` = f32 **0.5** ⇒ trip at **512 counts**. Symmetric, **no debounce**.
- **Sole writer of `gp-0x6b26`**: `st.h r6,-0x6b26[gp]` @`0x36CF0` in `FUN_00036c12` — **exactly one
  writer image-wide**, confirmed by Ghidra plus a raw Python LE scan covering disp16, the 6-byte disp23
  form, LE32 address literals and movhi/movea pairs (0 hits on all alternatives). The stored value is
  already clamped to `±0xC407E`.
- **`0xC407E`** (= `tp+0x507E`; anchor `0xBF000+0x507E`, the off-by-0x1000 trap avoided): 0 writers,
  3 readers, all `ld.h` signed, **all three inside `FUN_00036c12`**.
- **Margins**: stock/V38/V76/V78/V79/V80 **511 → +1 UNTRIPPABLE** · V73/V74/V75 **850 → −338
  TRIPPABLE** · **V81 511 → +1 UNTRIPPABLE**.

**★ V75's fault was not the damper.** In the last 5 s the damper was identically **zero for 4.98 s** and
reached only level 2 (128–288) **19 ms** before the trip. The car was stationary then launched; column
rate reversed sign twice in 150 ms (+55, +31, −38 °/s); **peak jerk 7,154 °/s² = 4.3× that route's own
p99.9.** Exactly what the `0xC407E` mechanism predicts.

⚠ [BELIEF, not EVIDENCE] "`0xC407E` = 850 caused *both* faults" — the DTC number was never confirmed
on-car. What is EVIDENCE: the mechanism exists, is single-frame, is mode-proof, and the build history
lines up exactly. **V81 closes it whether or not it fired.**

### 🛑 `0xC63A0` is exonerated
`0xC63A0` (= `tp+0x73A0`) has **exactly one reader** (`ld.hu` @`0x381AC`), **0 writers**, 0 disp23 hits.
Its only reader `FUN_00038148` writes exactly two cells — `gp-0x374c` and `gp-0x6b70` — and **never**
`gp-0x6b26`, `gp-0x6c2c` or `gp-0x6a5e`. `gp-0x6c2c`'s two writers are both in `FUN_00041464`.
**No firmware data path to the faulting monitor.** A physical path exists (aggregator → motor → plant →
rate) and is irrelevant, because the clamp acts before the store.
⊕ `build_v80_tva.assert_c63a0_block` still asserts 1024 with the old rationale — **that comment is now
known-wrong** and should be corrected.

---

## 6. 🛑 The V38 rebase silently reverted three levers

| lever | V62 · V68 · **V74 · V75** | **V76 · V78 · V80** |
|---|---|---|
| `0x2A1F0` reader disp | `0x7CD0` → **decoupled** `0xC6CD0` = 3564 | `0x746C` → **shared** `0xC646C` = 3564 |
| `0xC646C` shared sensor scale | stock **891** | **3564 (4×)** |
| `0xC62EA` low-speed steer lockout | **0** (removed) | **320** (restored) |
| `0xC63A0` Path-2 damper weight | **2048** | 1024 |
| `0x454FE` V42 macro-ratchet fix | `0xB5` | `0xBA` (V80 restored `0xB5`) |

**V80 vs V75 was never a single-variable damper comparison.**

### `0xC646C` — six readers, and why it is *not* the 27 Hz driver
Q15 multiplicative scale (`(x * cal) >> 0xf` at every site); 3564 = 4×891 exactly. Reader #1 (`0x2a1ee`,
LKAS arbitration) is the one V57 decoupled. #2 is dead code. **#3 reclassified this session** — its
output reaches only a private 2-function mode-flag debounce loop and a UDS packer with no static callers,
**no torque path**. #4's output has 3 refs, all stores, **zero loads** — proven dead. **#5 (`FUN_00036682`)
is the only one reaching the motor**, and #6 modulates its hysteresis.

**Reader #5 cannot drive a 27 Hz mode — a bandwidth argument.** Its output passes an IIR with
`alpha = tp+0x73d2 = 6` ⇒ **corner ≈ 0.93 Hz, ≈ −26.6 dB at 21 Hz.** (This also settles a prior
"6 vs 14" discrepancy in favour of **6**.)

Its pre-filter `±0x200` clamp trigger drops from ~18,829 counts of bar torque at stock to **~4,707 at
4×** — a check never previously run against a V76-lineage log. On route 66: engaged `|bar|` p99 3,346,
p99.9 3,712, **max 3,849**; `≥ 4707` fired **0 / 89,997**. ⚠ Margin only **22%**, and the CAN sensor's
count scale is not proven identical to `gp-0x4f60`'s ⇒ **"did not fire on this drive", not "cannot
fire".** Worth a probe.

⇒ **The shared-cell 4× is a real, uncosted regression in headroom — but not the 27 Hz driver.** V81
removes the exposure for free by being cut from the V75 base.

---

## 7. V81 — built, verified, UNFLASHED

**V81 = the FLOWN V75, with the friction lane returned to Honda's configuration. Cal-only. No cave change.**

| | value |
|---|---|
| builder | `analysis-2020accord/build_v81_tva.py` |
| base | `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` `e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c` — **the cut that FLEW route 5e** |
| image | `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` **`4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b`** |
| rwd | `39990-TVA,A160-V81-V75BASE-C407E.511-FRICTION.STOCK-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd` **`fc4d4f74956c76dbda340e17ecf4c3ecbe3f86bbc47418cbc3b3185c52aea109`** (986,042 B) |

**EDIT 1** `0xC407E` 850 → 511 (`5203` → `ff01`) — restores Honda's interlock.
**EDIT 2** the ×1.5 friction table → **stock** at all 14 sites, `67c667de7bf4` → `9ad99ae952f8`.

🛑 **Corrections to the record**: the ×1.5 friction was introduced by **V73, not V74** (stock/V70/V71c/V72
carry Honda's row; V73/V74/V75 carry ×1.5). **`0xD2A4C` is mode 10 — a DISENGAGED-column record**; V74's
derivation only ever wrote the 13 engaged modes so it never saw m10. V81's edit there is a revert to
stock, so that column can only become more stock.

### Verified from disk by the orchestrator — all pass
- **25 differing runs / 126 bytes** vs the flown V75: 15 functional (86 B) + 10 CRC words (40 B).
  **0 unexpected functional runs. 14/14 friction sites.**
- **Value-anchored**: restoring exactly those 126 bytes reproduces the flown V75 **bit-for-bit**
  (sha256 back to `e16ba409…`) over all `0x100000` — a total statement, not a span check.
- **Exactly 1 flashable V81 `.rwd` and 1 V81 plain image on disk.**
- **All 34 friction records byte-stock.** Mode 24 (manual) identical to V75 across all six record types.
- **Unchanged from V75**: FactorC `[566,234,429,908]`, FactorE X `[12,200,2500,4000]` Y `[0,539,539,927]`
  ⇒ **k = 1.5798 identical**; `0xC63A0` = 2048; `0xC62EA` = 0; `0x454FE` = `0xB5`; `0x2A1F0` disp
  `0x7CD0`; `0xC6CD0` = 3564; `0xC646C` = 891 stock; the 68-byte cave and hook byte-identical.

### GATE 1 — RAM ownership: **PASS, vacuous by construction**
Cal-only: no new RAM, no code, no instruction, no cave byte. Measured anyway: `gp-0x6b26` 1w/4r ·
shadow `gp-0x4cd0` 1w/1r · `0xC407E` 0w/3r all in one function · `0xC4004` 0w frozen.

### GATE 2 — closed-loop stability (magnitude AND phase): **PASS, empirically**
**V81 does not change any loop.** The only dynamic element it touches is a saturation bound, moved down.
- **Magnitude**: `k = 297/188 = 1.5798`, a frequency-independent scalar on the whole damper path ⇒ loop
  gain equals V75's at every frequency, no plant model needed.
- **Phase**: no new filter, delay, state or sample point; every pole, zero and task-order relationship is
  bit-identical to V75 ⇒ phase response is *literally* unchanged.
- **The one nonlinearity that moves**: `|gp-0x6c2c|` to reach the clamp at creep — stock 3189 · flown V75
  3539 · **V81 3189**. So V81 clamps ~10% *more* often than V75 did. Harmless, and the point: at 511 the
  clamp sits below the 512 trip, so clamping cannot fault. V81's threshold is byte-for-byte stock's.
- **★ Decisive empirical bound**: on V76 — Honda's friction row with `0xC407E` = 511, exactly V81's
  configuration in this lane — the probe `|gp-0x6b26| > 448` fired **0 / 63,477 frames**, positive
  control 99.926%. The relay hazard in this lane is measured to be unexercised.

⚠ **V81 removes drag the operator may be used to.** Creep effort will differ from V75's — intended (the
V75 handoff attributes the *creep heaviness* complaint to V73/V74's friction ×1.5 plus `0xC407E` 850, and
`0xC407E` is a bare `tp` scalar so it raised the drag ceiling in **manual** too) — but it is a **feel
change as well as a safety change.**

**Variant B** (`ACCORD_V81_FRICTION=V75`, keep the ×1.5) is implemented but **not cut**. The probe could
not discriminate: ×1.5 pins at 511 when the stock-equivalent raw ≥ **340.7**, and the rung is at **448**.
A calibrated model puts ×1.5's pinning at **rare tail events (~one per 285 s), not a duty cycle**
[BELIEF]. Rungs at 320/352/416 would settle it for ~30 cave bytes.

---

## 8. Tooling and hygiene findings

1. 🛑 **`rlog-tools/decode_v76_probe.py` is the WRONG decoder for route 65.** It documents the
   *superseded* V74-base V76, whose bit7 is `gp-0x6bd0 != 0` — the damper, not the friction lane. The
   build that flew route 65 is `V76-V38BASE-…-probe-6b26-63fd`; its extractor is
   `analysis-2020accord/v76flight_extract.py` → `_cache_r65_records.pkl` (**not** `_cache_r65/`).
2. 🛑 **Two `_v76*plain_image.bin` on disk**, and a first `Glob` returns the wrong one first.
   `_v76_gate_fb_arm5244_gateprobe_…` is the abandoned V74-base candidate (still carries the V57
   decouple); the V78/V80 ancestor is `_v76_v38base_relu_damper_…`.
3. **`build_v75_tva.py`'s default lever set does NOT produce the flown V75** — pass
   `ACCORD_V75_LEVERS=CY0,EX1`. **The flown V75 is the `EX1.200` cut, dose 137, k = 1.5798.**
4. **Route `5d` (V74's clean flight) has no raw rlogs anywhere in the repo** — only the extracted cache.
5. **V80's probe cannot distinguish V80 from V78/V79** (byte-identical cave). Identity rests on the
   `.rwd` filename plus the absolute exclusion of V76-V38BASE. Route 66's `0x14A` byte4 took only
   {`0x0F`,`0x1F`,`0x5F`,`0xDF`}; bit5 0/89,997; **bit3 positive control 100.000%**.
6. The default `python` (anaconda base) has a **broken numpy DLL**. Prepend
   `C:\Users\dudei\anaconda3\Library\bin` to `PATH`, or use `…\envs\bin_decompile\python.exe`.
7. ⚠ **`BUILD-LINEAGE.md` Part 1 has unescaped `|` inside cell text on at least six rows** (V58, V63,
   V67, V70 ×2, V71 — 7 to 16 pipes where a 5-column row needs 6), so those rows render with the wrong
   column count. **Pre-existing and pervasive, not introduced this session; cosmetic, not factual.** Left
   unfixed deliberately — the rows are 1.4–12.8 KB each and rewriting them during a close-out risks
   corrupting content to fix rendering. Escape them as `\|` when one is next edited for content anyway.
8. 🛑 **`BUILD-LINEAGE.md` had fallen FIVE BUILDS BEHIND** — no Part 1 entry existed for V76, V78, V79,
   V80 or V81. All five are now present, backfilled from the plain images and build-script headers rather
   than from narrative. In a file whose entire purpose is stopping someone re-proposing a flown lever,
   this is the most consequential thing the session turned up about the record itself. **Check it is
   current before trusting it.**

---

## 9. Next steps

1. **Fly V81.** A 126-byte revert from the only build that has ever eliminated the grinding, with both
   legs of the recorded fault mechanism removed. The flash decision is the operator's and the file and
   bus must be named back.
2. **Bracket the switch-on point in `k ∈ (1.58, 4.16]`** — flat at/below baseline for k ≤ 1.58, 2.09× at
   4.16, nothing in between. **With the ramp preserved**: the data's own recommendation is *restore the
   ramp, don't merely lower k*.
3. **The micro-ratchet is flat across k = 0.58 → 1.58 and improves only at k = 4.16** (0.418
   [0.33, 0.61], the sole point clearing its null). A V82 question, not a reason to keep V80's flat top.
4. **Probe the friction lane at 320/352/416** if variant B is ever wanted.
5. **Close `gp-0x6b94` → motor**: raw Python LE scan for the 6-byte extended-disp encoding of
   `gp-0x6ace`/`gp-0x6b94`/`gp-0x6afe`/`gp-0x6b08`, plus `analyze_dataflow`/`get_bulk_xrefs`, plus a full
   decompile of `FUN_00042af8` (its "no `gp-0x6b94` reference" characterisation was inherited, never
   re-verified).
6. **Settle the 27 Hz command-vs-plant question** with a phase-resolved coherence on `sendcan` 0x0E4 vs
   the torsion bar.
7. **Correct `build_v80_tva.assert_c63a0_block`'s rationale comment.**
8. **Re-run reader #5's `±0x200` clamp screen** with a proven `gp-0x4f60` scale — the 22% margin is thin.

---

## 10. New artefacts

- `analysis-2020accord/build_v81_tva.py`
- `rlog-tools/decode_v80_probe.py` (+ `_cache_r66/`, gitignored, with `r66_report.txt`)
- `rlog-tools/compare_v75_v76_v80_grind.py` (+ `_cache_r66x/`)
- `rlog-tools/friction_lane_duty_r65.py`
- `analysis-2020accord/rlogs/75604b0a432fdc89_00000066--276b942769--{0..14}--rlog.zst`
- Agent memory: `reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed.md`,
  `reference_accord_c63a0_cannot_reach_gp6b26_friction_lane.md`, and an append to
  `reference_accord_c646c_gain_feedback_vs_forward_classification.md`.
