# HANDOFF 2026-08-27 — V107 FLEW AND THE DAMPER IS A COULOMB RELAY; V108 IS SUBTRACTIVE

**Session:** score V107's two drives → V108 built. Six subagents: `rlogs`, `arc-delta`, `modehold`,
`ratecap`, `hfmech`, `inherit-audit`. All confirmed stopped from the harness before any collateral was
written. Three pre-existing `classify-*` agents appeared in the roll-call; neither repo shows any file
touched by them.

**Predecessor:** `docs/handoffs/2026-08/HANDOFF-2026-08-23-v107-the-schedule-is-the-lever.md`.

---

## 0. THE ONE-PARAGRAPH VERSION

V107 flew as routes `1b` and `1e` — 988.6 s engaged on `1e`, fault-free — and the operator reported a
symptom that has never appeared in this arc: **audible grinding at a higher pitch, several hundred Hz,
between 15 and 40 mph**, with a visible sub-10 Hz wheel oscillation, a complete drop-off below 5–6 mph,
a return during hard turns at 50 mph, and **grinding that outlives disengagement by a few seconds**.
Every clause is now explained by one mechanism. **`gp-0x6b26` — the "damper" V106 and V107 dosed — is
not a damper above ~30 Hz. It is a bandpass peaking at 61.1 Hz, and V107 pushed it hard enough that it
RAILS at its ±511 clamp 33.5 % of the time at 10–25 km/h and 21.3 % at 24–40 km/h**, against a build
that predicted ≤1.05 % and rejected its own alternative at 6.2 % as "V80 relay territory". A railed
acceleration term is a bang-bang Coulomb relay. **V108 is the first subtractive build in this arc**: it
reverts V105's failed notch to Honda's coefficients, reverts the damper's Y1 knot to V106's, returns one
friction cell to Honda, and fixes a telemetry scaler that was sized against a 5× arithmetic error. A
fifth edit — the first-ever raise of the LKAS request clip — was built and then **PULLED on its own
pre-registered null.**

---

## 1. WHAT V107 DID — measured

### 1.1 🛑 THE DAMPER IS A RELAY [EVIDENCE]
V107's own re-aimed 427 tap put `gp-0x6c2c` — the lane's raw pre-gain, pre-clamp input — on the wire for
the first time. Reconstructed `P(|gp-0x6b26| = 511)` on route `1e`, engaged, episode-bootstrapped over
the 10 engaged episodes:
```
   bin      n eng   thr_V107   V107 rail duty          V106, same samples   wire-sat
   <10       6248     1118     1.68% [0.86, 2.58]      1.47% EXACT            0.72%
   10-25    14950     1306    32.32% [29.93, 35.68]    <= 15.46% (bounded)   15.46%
   24-40    15483     1381    21.27% [19.93, 22.51]    <= 10.45% (bounded)   10.45%
   40-64    30250     1580     4.27% [4.35, 6.31]      <=  3.43% (bounded)    3.43%
   65-90    21649     1809    <= 0.23% (bounded)       <=  0.23% (bounded)    0.23%
     90+    11775     1963    <= 0.03% (bounded)       <=  0.03% (bounded)    0.03%
```
**Duty is EXACT where the clamp threshold sits at or below the 1636.8-count wire rail, and two-sided
bounded above it** — `rlogs` corrected my own "these are all floors" framing and the correction is the
right one.

The arithmetic, verified two ways (mine and `hfmech`'s, independently, from `FUN_00036c12`'s own
two-stage shift):
```
|gp-0x6b26| = clamp( ((|c2c| * |Y_eff(v)|) >> 6) * 273 >> 18 , +-cal(0xC407E)=511 )
                                                              [0x36CBE .. 0x36CCA]
 km/h  mph  | V106 Y   rails at |c2c| | V107 Y   rails at |c2c| | shrink
    8  5.0  |  24575        1278      |  27294       1151      | 1.11x   <- Y[0] BYTE-IDENTICAL
   24 14.9  |  16556        1897      |  23543       1334      | 1.42x
   40 24.9  |  13972        2248      |  21714       1446      | 1.55x
   64 39.8  |  10097        3110      |  18971       1655      | 1.88x
   90 55.9  |   5898        5324      |  16000       1963      | 2.71x
```
🛑 **THE SYMPTOM MAP AND THE RAIL-DUTY MAP ARE THE SAME MAP.** V107 shrank the rail threshold 1.42–2.71×
across 24–90 km/h and left Y[0] byte-identical below 20 km/h — and the operator reports the grinding at
15–40 mph and its complete absence below 5–6 mph.

### 1.2 THE LANE IS A BANDPASS PEAKING AT 61 Hz, NOT A DIFFERENCER [EVIDENCE, two independent derivations]
```
H(f) = 64 * H1(f) * (1 - z^-1) * H2(f)    H1,H2 = one-pole EMAs
       a0 = 37/128 = cal(0xC643C)          a2 = 22/64 = cal(0xC40DC)      fs = 1000 Hz
 f Hz     1     7.79   21.73    40    61.1    100    200    300    499
 |H|    0.40   3.08    7.72   11.15  12.14  10.86   7.15   5.45   4.49
```
**PEAK 61.1 Hz. −3 dB span 25.1 → 153.0 Hz. Never below 4.49× anywhere to Nyquist.** At 100 Hz the lane
runs at 10.86× — **40 % MORE gain than at the 21.7 Hz mode it was designed to damp.** V106 multiplied
this ×3.0 uniformly; **V107 delivers ×3.0 at creep, ×4.19 at 20 km/h and ×8.14 at ≥90 km/h.**
`arc-delta` derived it from the kit's own 2026-08-10 trace and reproduced that trace's recorded phase
table to 2 dp at all six of its points; `hfmech` derived it independently from the image and reproduced
the peak to 3 dp. **Two derivations, one answer.**

🛑 **WHY THE SAFETY CASE COULD NOT SEE IT.** Every duty number behind V107 came off CAN 427, which
arrives at **49.8 Hz — Nyquist 24.9 Hz.** *The lane's entire −3 dB band is above that Nyquist.* The
instrument was structurally blind to the passband of the thing it was sizing. 🛑 **REFINED 2026-08-27 — that sentence is right about SPECTRA and WRONG about DUTY.** Rail duty is `P(|c2c| >= thr(v))`, a functional of the **MARGINAL** distribution; the 427 tap samples instantaneous values, so its marginal is UNBIASED and only its SPECTRUM is aliased. **The measured duties are sound.** What the 49.8 Hz tap genuinely cannot do is see the 25-153 Hz band the lever ACTS ON — which is why an alpha2 dose cannot be sized from it, and why V107's error was a **MODELLING** error (an open-loop push-through on a closed loop) rather than an instrument error.

### 1.3 TWO MORE MECHANISMS IN THE SAME BAND
**[a] A PHASE SECTOR CROSSING AT 74.5 Hz [EVIDENCE].** The standing conclusion *"`gp-0x6b26` can never
RAISE a resonance — its phasor is stuck in 180–270°"* was only ever verified **to 40 Hz**. Swept to
Nyquist, the phasor **crosses into 90–180° at 74.5 Hz** — the one sector that raises a resonance's
frequency while nominally damping it — and stays there continuously to 500 Hz. That is a **linear**
mechanism for a new higher-pitched mode appearing when this term's dose goes up, independent of the relay.
⚠ Labelled by its author as *structurally supported, not proven*, and used that way throughout.

**[b] ALIASING [EVIDENCE for the structure, BELIEF for the content].** `gp-0x4f50`, the cascade's raw
input, is **decimated 4 kHz → 1 kHz in `FUN_00068fbe`** with no anti-alias filter beyond a 2-tap boxcar
(~8 % attenuation at 500 Hz). Content at 900/1100/1900/2100/2900/3100/3900 Hz folds onto **exactly
100 Hz**. The 4 kHz domain has never been measured, so whether that content exists is unknown.

**A sub-perceptible input is enough.** At V107's 24 km/h dose, the peak column displacement that fully
rails the ±511 clamp is **1.88° at 7.79 Hz, 0.27° at 21.7 Hz, and 0.042° (2.5 arcminutes) at 100 Hz.**

### 1.4 ⭐ "IT PERSISTS AFTER DISENGAGE" — MEASURED AT ~2.05 s, AND IT IS OURS [EVIDENCE]
The engaged mode records 26/27 — the **only** cells V106/V107 dosed — are not released when `latActive`
drops. `FUN_00042746` may only flip the mode pair once `gp-0x69b0` has ramped to exactly 0, and that
ramp runs in `FUN_00028ea6` at 1 kHz on one of five calibrated per-tick rates (328/66/33/16 ct/tick over
a 32768 range = 100/497/993/2048 ms) plus a ~40 ms commit hold (`cal(0xC624E)` = 40).

**`rlogs` measured it on a model-free channel** — wire-saturation duty, no Y assumption, no acoustic
level — pooled over the 3 usable transitions on route `1e`:
```
  window s   pooled duty   n         last railed sample per transition
  -1.5..-1.0    13.3%     75           T1  1.81 s
  +0.5..+1.0    12.0%     75           T2  0.85 s
  +1.0..+1.5     4.0%     75           T3  0.40 s
  +1.5..+2.0     4.0%     75
  +2.0..+2.5     0.0%     75         ZERO from +2.0 s onward
  +3.0..+4.0     0.0%    149
```
Pre-registered against `modehold`'s four firmware candidates: **0.10 s EXCLUDED · 0.50 s EXCLUDED ·
0.99 s EXCLUDED · 2.05 s CONSISTENT.** ⇒ **the branch that fires when nothing is wrong is the one the
car takes.**

**Both controls passed, and the second is decisive.** T2 and T3 *speed up* across the disengagement
(28.9 → 33.8 and 33.2 → 34.8 km/h) and still go to exactly zero, so the speed confound that killed the
audio decay does not apply. And *"it stops because nobody is steering"* is refuted: at matched steering
rate (|rate| ≥ 30.1 °/s) and matched speed, **968 post-disengage frames give `|c2c|` p50 = 72 and rail
duty EXACTLY 0.00 %, against 1,473 engaged frames at p50 = 1080 and 20.43 %.**

⚠ Honest limit: 3 transitions is too few for a CI and no τ was fitted. The safe statement is **release
≥ 1.81 s, duty exactly zero from 2.0 s.**

⭐ **It is a near-unique discriminator.** Nothing else in the build has a multi-second latch: Lever B's
gate is `gp-0x6806` = latActive (same tick), the biquad arms on the same flag with a 99 % ring-down of
89.7 ms, the 6× gain lane goes idle with the command, and `0xC64DE`'s dither is amplitude-zero.

### 1.5 ⭐ THE 2×2 — THE RELAY IS MOSTLY PLANT, NOT MODE RECORD [EVIDENCE]
Matched speed, counterfactual Y applied to each state's own `|c2c|`:
```
                          |c2c| from ENGAGED   |c2c| from MANUAL
  10-25 km/h  V107 Y         33.49% EXACT         1.22% EXACT    <- 27x, SAME Y
  24-40 km/h  V107 Y         21.04% EXACT         4.07% EXACT    <- 5.2x
  40-64 km/h  V107 Y          5.12% EXACT         0.00% EXACT    <- inf
```
**Holding Y fixed, engaged `|c2c|` alone produces 27× the rail duty of manual `|c2c|`.** The dominant
term is not the mode record — **engaging makes the motor acceleration itself far larger, and Y then
amplifies what is already there.** That is a feedback signature.

🛑 **AND IT EXPLAINS A 32× MISS.** V107's clamp-duty prediction used
`|b26|_X(v) = |b26|_measured(v) × Y_X/Y_route` — an **open-loop push-through that assumes the `gp-0x6c2c`
distribution is invariant to K.** But `gp-0x6b26` feeds the aggregator → motor → motor rate →
`gp-0x6c2c`. **It is a closed loop.** Predicted ≤1.05 %; measured 33.49 %. `hfmech` reached this from the
code and `inherit-audit` from the data, independently, and **neither has a competing explanation. Cite it
as jointly held.** ⇒ **no open-loop duty prediction on this lane can be trusted again**, including for
future candidates.

---

## 2. V108 — WHAT WAS BUILT

```
image  7a9577dd181a235845e87e592fbd1a191957674aef7b0f17caac6907c114a9e4
.rwd   4fbfda0d76af2f1b592bd9e510cd926dbfabb6a02b7a25730e7018f07cf4c4d1
file   39990-TVA,A160-V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5-0x13000-0x100000.rwd
builder analysis-2020accord/builds/v108_plus/build_v108_tva.py, 54/54 assertions, BASE = V107
31 bytes vs V107 in 11 runs (20 payload + 11 CRC... 3 trailers), ZERO unattributed.
CAL-ONLY. THE CODE CAVE IS BYTE-IDENTICAL TO V107.
```

| | address | V107 → V108 | what it does |
|---|---|---|---|
| **E1** | `0xC60A8`–`B7` | V105's notch → **Honda's own 16 bytes** | removes **+14.0 dB at 61.1 Hz**, restores Honda's 55.2 Hz null |
| **E2** | `0xD7A5C`/`0xD7A6C` | Y → `(−29490, −17202, −16000)` | de-rails at the Y1 knot; keeps V107's high-speed dose |
| **E4** | `0xC40BC` | 300 → **600 (Honda)** | a friction cell retracted by its own author before it flew |
| **E5** | `0x55E10` | `sar 3` → `sar 5` | the tap was sized against a 5× error and censored its own answer |
| ~~E3~~ | `0xC61BE` | **PULLED** — byte-stock | built at 16384, killed by its own pre-registered null |

### 2.1 E1 — THE NOTCH REVERT, AND WHY IT IS PRIMARY RATHER THAN HOUSEKEEPING
V105 retuned Honda's biquad from a **55.225 Hz** zero (a true null, −103 dB) to 25.5 Hz, **failed on its
own endpoint**, and was never reverted — it has flown unexamined on V106 and V107. From the image floats:
```
 f Hz    |H|stock  |H|V105   V105/stock      dB
  54.0     0.0348    0.7601      21.84     +26.79
  55.2     0.0000    0.7648   61516.       +95.78   <- Honda's null, DELETED
  61.1     0.1556    0.7828       5.03     +14.03   <- the damper lane's own peak
 100.0     0.7071    0.8256       1.168     +1.35
 127.0     0.8344    0.8340       1.000      0.00   <- crossover; above this V105 is BETTER
```
⭐ **Honda notched 55.2 Hz. The kit's own acoustic inversion independently places a high-speed grind
excess at 63.5 Hz [54, 80]. The lane we dosed ×8 peaks at 61.1 Hz. Three numbers inside a 10 Hz window,
and V105 removed the only thing attenuating it.**

**The argument that decided it is an asymmetry in how well the two legs are measured** (`inherit-audit`):
> V106-vs-V105 measures the **damper** leg cleanly — **0.347, clearing route a6's own split-half null
> [0.482, 1.982], the first band-power result in this kit's history to do so.** V105-vs-V104 measures the
> **notch** leg — **0.769 [0.548, 1.135], a CI spanning 1.**
> ⇒ **The damper's contribution is measured and significant. The notch's has never been measured to be
> different from zero.** Reverting spends an unmeasured fix to remove a +14.0 dB amplifier.

🛑 **THE ARM STAYS ON.** Unarmed, `FUN_000352b4` passes `gp-0x6b82` through **UNFILTERED (`H ≡ 1`)** —
it is a **bypass, not a mute** — and Honda's armed notch has `max|H| = 1.000033` over 0.05–500 Hz, i.e.
it can only ever *remove* loop gain. **Disarming is worse than Honda at every frequency.**
**Spec: copy the 16 bytes from `stock_fw_dump/code.bin` and assert byte-for-byte. No float is typed.**

**THE RISK, STATED PLAINLY.** E1 raises 21.7 Hz loop gain ×2.047 on the base-assist lane, and it is the
only V108 edit that moves the mode's loop gain UP. The whole-loop number is **V105's own flight run
backwards: ×1.30 [0.88, 1.82], a CI spanning 1** — *not resolvable*, and "not resolvable on a5" is not
the same as "small" (a5's split-half null spans 0.26–3.8, a very weak instrument). **Mitigation by
construction: Y[0] is untouched, so creep — where V106's headline was measured — is unchanged**, and the
post-E1 creep state is V106's damper with Honda's filter, the most damped creep configuration in the
kit's history. The reverted lane state is V103/V104's, flown twice, fault-free.

### 2.2 E2 — THE Y ROW, AND WHY IT IS A TARGETED REVERT AND NOT A SOLVED OPTIMUM
🛑 **The solve could not be run, and the reason is important.** V106's own clamp threshold **exceeds the
1636.8-count wire rail everywhere above ~10 km/h**, so the empirical target — "hold rail duty at V106's
level" — is itself censored in 5 of 6 bins. Run naively, the optimiser drives `|Y_eff|` to ≈19,195,
exactly where the threshold crosses the rail, and **certifies "0.00 % duty" for a row that truly rails
15.46 %.** *That is V107's own failure reproduced one level up.* `rlogs` refused to ship the table.

`(−29490, −17202, −16000)` is V106's Y0 and Y1 exactly with V107's Y2 kept: **all the rail damage is at
the Y1 (20 km/h) knot** V107 raised 1.40×, and **≥65 km/h is bounded ≤0.23 %/≤0.03 % on BOTH builds**, so
V107's high-speed dose costs nothing measurable and is the half of the reshape aimed at V106's own >70 km/h
residual. Monotone, int16-safe, 1.04× V106 at 24 km/h and 2.15× V106 at 80 km/h.

### 2.3 E5 — ONE BYTE, AND THE NEXT DRIVE IS UNINTERPRETABLE WITHOUT IT
The 427 packer is `wire = clamp( (min(|src|,65535) * 5) >> sar , 0, 0x3FF )`. **V107's builder omitted the
`mul 0x5, r6, r0` at `0x55E06`** — Honda's own instruction — and printed full scale as 8184 when the truth
is `1023 × 2^sar / 5`. At `sar 3` that is **1636.8**, and route `1e` **saturated 4.95 % of engaged samples
(15.46 % at 10–25 km/h).** V107's drive card asked for the clamp duty above 70 km/h; at `sar 3` the rail
threshold there is above the wire's ceiling, so **that question was unanswerable by construction.**
```
 sar  byte   LSB   full scale   covers V108's own worst rail (1963)?   covers a V106-like Y2 (5324)?
  3   0xA3   1.6      1636.8            no                                  no
  4   0xA4   3.2      3273.6            yes                                 no
  5   0xA5   6.4      6547.2            yes                                 YES
```
**`sar 5` is the minimum that lets the NEXT drive size a WEAKER candidate row** — which is the exact
failure this byte exists to fix. Verified two ways: a byte scan showing the low byte is `0xA0 | imm5`,
and Ghidra on a real existing site (`0x29D7C` bytes `a5 32` → `sar 0x5, r6`).
⚠ **`inherit-audit` flagged `sar 5` as unusable at p50 — that flag repeated the 5× error** (it computed
LSB 32 and full scale 32,736). True: LSB **6.4**, p50 = 40 counts = **6.2 LSBs**, rail = 190–300 LSBs.
**Resolution is fine where the decision lives.** ⊕ The trade against `sar 4` is real and is recorded: half
the resolution, in exchange for the only range that can size a weaker Y.

### 2.4 🛑 E3 — BUILT, THEN PULLED ON A PRE-REGISTERED NULL
`0xC61BE` = 15360 is a symmetric saturation at `0x2A13E`..`0x2A15E`, **UPSTREAM of the 6× gain** at
`0x2A1EE`, so the LKAS lane's ceiling is `(0xC61BE × cal(0xC6CD0)) >> 15`:
```
 build          gain   out-clamp   reach   % of clamp
 stock 1x        891       512      417      81.45 %
 V38-V100 4x    3564      2048     1670      81.54 %
 V101 8x        7128      4096     3341      81.57 %
 V102-V107 6x   5346      3072     2505      81.54 %
```
⭐ **Every gain step this kit ever made raised the OUTPUT clamp and left the INPUT clip at Honda's 15360.
The reach has been 81.5 % on every build since V14.** That is also the long-unexplained mechanism behind
*"`0xC61B2`/`0xC61B4` are 0 % of the effect"*: **they are inert BECAUSE this clip caps the lane 18.5 %
below them.** Anchored independently: `(15360 × 891) >> 15 = 417`, and the kit separately recorded
*"stock V9's max LKAS command was 417"* from a different derivation.
GATE 1 clean: 8 accesses image-wide, all loads, zero writers, no lockstep twin, no ASIL monitor, no
`0xC5000` mirror. **NOT in series** with `0xC61BC` (15360), `0xC61B6` (10240) or `0xC61BA` (10240) —
those clamp **three parallel branches** whose sum can reach 35,559 = **2.32× the clip.**

**THE PRE-REGISTRATION, written before the measurement:** *if achieved rate keeps rising to the top of
the command range, nothing in this lane saturates, the clip is idle, and the raise buys zero — pull it.*
Route `1e`, authority-ramp-complete (>1 s engaged, >10 km/h), **93,356 frames / 924 s**, with `|e4tq|`
p99 = max = 4096 so the saturation region **is** exercised:
```
  speed     p90 |rate_c| low half   top (>=2048)   ratio   95% CI          knee?
  10-25            27.0                105.0        3.89   [2.42, 5.48]     NO
  25-40            25.0                 78.0        3.12   [2.22, 4.45]     NO
  40-64            15.0                 43.7        2.91   [2.38, 3.13]     NO
  64-90             8.0                 21.0        2.62   [2.10, 2.62]     NO
  90-200            7.0                 15.0        2.14   [1.67, 2.14]     NO
```
**Still rising 2.1–3.9× where a bound clip would have pinned it flat, at all five speeds, every CI
excluding 1.0. ⇒ PULLED.**
⚠ **Limit on the null, so it is not over-read:** the clipped quantity is **not** a memoryless function of
the command — `gp-0x6cf8` and `gp-0x6dd0` are int32 recursive state, 4 accesses each, every one inside
`FUN_00028ea6` or its dead copy, zero external readers or writers — so a clip binding only along
particular trajectories could smear across the command axis instead of showing a sharp knee. **Strong
evidence it does not ROUTINELY bind; not proof it never can.**
⭐ **The zero-firmware confirmation, if it is ever wanted:** stock UDS **DID `0x48AC`** (RDBI entry
`0xB7864`, handler `0x4E82E`, default session, **no security access**, 56 B, byte-identical in V107)
carries `gp-0x6b38` — the final clamped LKAS output — at payload **bytes 7–8**, plus the arb setpoint at
0–1 and the torsion bar at 3–4. A bound clip pins bytes 7–8 at **~2481** against the 3072 clamp;
**anything above 2505 falsifies the whole model.** 🛑 Known blocker: EPS UDS is bus-1 + OBD-mux only and
the red panda cannot poll during LKAS. **NOTHING WAS TRANSMITTED.**

### 2.5 WHAT WAS DELIBERATELY NOT DONE
- 🛑 **`0xC40DC` = 22 (α2, the cascade's second EMA pole) — VIRGIN on all 102 images, and the
  structurally CORRECT fix — is HELD OUT.** See §5; it is the V109 candidate and its sweep is done.
- **`0xC40D2` = 204 (K1) KEPT, knowingly.** A measured null, but the sign chain says 204 makes the wheel
  **LIGHTER**, so reverting makes it heavier — the wrong way for an operator who complains about excess
  friction and never about lightness.
- **`0xC63F6` = 16 ct/tick** would cut the post-disengage hold from ~2.05 s to ~0.54 s at 66. Not touched:
  the same ramp governs **engagement**, and **the tail is a symptom of the relay, not an independent
  defect** — fixing it without fixing the relay only shortens how long you hear it.
- **`0xC520C` STRUCK.** See §4.
- **THE CAVE IS BYTE-IDENTICAL.** Code caves are this kit's only bricking class (V24, V27, V48B).

---

## 3. THE DRIVE CARD FOR V108

1. **The operator's report, per scenario** — 5 mph, 15–40 mph, hard turns at 50 mph, highway. **THE
   PRIMARY READOUT.** In his words: grinding / vibrating / micro-ratcheting / ratcheting / excess friction.
   Specifically: **is the several-hundred-Hz grinding gone, and does the wheel still oscillate visibly?**
2. **Rail duty by speed bin off the new `sar 5` tap** — now uncensored at every speed for the first time.
   Predicted: the 32 %/21 % at 10–40 km/h should fall to V106's ≤15 %/≤10 % or below. ⭐ **If it falls
   MUCH further than the Y change alone predicts, a self-sustaining cycle broke** — that is the
   threshold-behaviour question `hfmech` and `inherit-audit` both flagged and could not resolve.
3. **`|gp-0x6c2c|` percentiles at ≥70 km/h** — V107's drive-card item #2, still unanswered, unanswerable
   before `sar 5`.
4. **18–30 Hz prominence and band power at low speed**, against a6, matched (speed × absolute demand),
   within-drive split-half null run FIRST. **This is E1's risk readout**: V105's flight run backwards
   predicts ×1.30 [0.88, 1.82]. If the mode comes back, the notch was load-bearing after all — which is
   itself a result the corpus cannot currently deliver.
5. **A within-drive third-octave audio split, 45–130 Hz, engaged vs manual, speed-stratified.** E1's
   mechanism predicts a **55–70 Hz fundamental with harmonics**, not flat broadband content above 200 Hz.
   **If it comes back flat and broadband, E1's HF case is wrong** and only its mode-band argument survives.
   🛑 **WITHIN-DRIVE ONLY, PERMANENTLY** — see §6.
6. **`b5` at matched α**, engaged vs manual. The cave is unchanged so the dose still reads itself out.
7. **Fault-free confirmation, rung duties, engaged exposure and speed census.**

🛑 **AND THE ONE THAT NEEDS NO BUILD, now with a new and specific requirement.** **The alternating
drive** — ~30 s engaged / 30 s manual at 5–15 km/h, same road, same session, command swept hard and soft
— **plus deliberate disengagements at CONSTANT speed with the throttle held steady for ~15 s afterwards.**
That last clause is new this session and it is why the audio decay failed: the operator disengaged three
times and changed speed every time (−13.6, −6.1, **+10.7** km/h), which is natural driving and fatal to
the measurement.

---

## 4. WHAT WAS RETIRED, STRUCK, OR CORRECTED

| # | claim | status |
|---|---|---|
| 1 | *"16384 is a principled stopping point — V38 gave the E4/E5 taper 16384, so the ceilings finally agree, closing a nine-build-old miss"* (`arc-delta`, then me) | 🛑 **VOID, retracted BEFORE the operator saw it.** The taper clamps `gp-0x69ae` = `clamp(wire × −4, ±16384)` from `FUN_00052676`; STEER_MAX = 4096 bounds it at 16384 **by construction**, so V38's edit was CORRECT AND COMPLETE and is a no-op by design. There was no miss. |
| 2 | `0xC520C`/`gp-0x4f64` is *"the first/tightest bind on a fast manoeuvre"* (`ratecap`) | 🛑 **RETRACTED BY ITS OWN AUTHOR.** Measured on route `a6`: peak `gp-0x6ac0` = 1462 ct (310 °/s) against a first knot at 1050, reached **0.11 % of engaged time**, **never** past the second. `gp-0x4f64` sits at its own max 4762 for **99.9 %+** of engaged time, dipping only to ~4221–4257 at the single most extreme moment of 1,238 s. **Struck as a lever; stands as a documented mechanism.** It also reconciles the measured `b6` = 0.000000 with no "b6 watched the wrong site" story, and explains V41's null. |
| 3 | The 4.7121 ct/(column °/s) scale *"disputed"* | **NOT a dispute — a regime mismatch.** The conflicting "528 raw" figure is **hands-off spring-return only**, flagged in its own source script. Scale externally anchored via Honda's 0x14A rate field, cross-validated at r ≥ 0.985. |
| 4 | `0xC64DE` = *"re-engage authority ramp, LENGTHENS re-engage"* (`BUILD-LINEAGE-PART1-LEVER-INDEX.md:76`) | 🛑 **WRONG LABEL.** It is the **half-period of a sign-flipping square wave**: `if (counter < cal) counter++ else { counter = 1+(cal>>1); gp-0x6b2c = −gp-0x6b2c }`. V18's 17→27 moved it **29.41 Hz → 18.52 Hz, into grind #1's band.** Burst is ~381 ms, **not "a few seconds"**, and its amplitude LERP at `0xC6736` is **Y = (0,0,0,0) in stock AND V107** ⇒ **structurally INERT.** Excluded as the persistence mechanism on both counts. |
| 5 | The `0xE4`/`0xE5` taper *"skip"* is a V38 bug | 🛑 **NOT A BUG.** `gp-0x674e` is a boot-time variant selector; the reachable set is {0,1,3,4,6,7,8,9} and **the skipped records are exactly its complement.** Our car is **TVCA4 → slot 11 → selector 7 → `0xE51A8`, and it IS raised.** ⊕ The V38 handoff names the wrong slot for our car; **V74's naming is the correct one** (`LEDGER-V38-TO-V84.md:509` records the dispute unresolved — it is resolved). |
| 6 | The soft-EME ramp flattening `(0,1536,2048)` → `(5120,5120,5120)` as a possible step/relay source | **BENIGN.** It **removed** three knees (a hard corner at X=700 off exactly zero, a slope break at 800, a knee at 1100); a constant is the smoothest possible schedule. Measured inert on-car at low rate. ⚠ **Never measured at `\|rate\| ≥ 1100`**, which is the operator's hard-turn regime. |
| 7 | *"the mic shows NULL 100 Hz–8 kHz across six builds"* | ⚠ **That is a BETWEEN-ROUTE contrast, i.e. the statistic the same document says cannot be computed** (3–12× per-drive acoustic gain). It is not evidence nothing is there — and **none of the six builds is V106 or V107.** |
| 8 | `gp-0x4f62` *"= 2(x[n]−x[n−4])/4, peaks at 125 Hz"* | 🛑 **DOES NOT FOLLOW FROM THE CODE.** `FUN_0007e74a` uses an 8-slot ring buffer with a **parallel variable elapsed-tick counter** and is called **conditionally**. `D = cal(0xC6C42) = 4` is byte-confirmed, but the effective delay is unresolved. **`hfmech` refused to give a peak frequency it could not stand behind. The 125 Hz number should not be reused.** |
| 9 | *"gp-0x6b26 can never RAISE a resonance; the phasor is stuck in 180–270°"* | **SCOPED, not retracted.** True **≤ 40 Hz**, which is all that was ever checked. Above **74.5 Hz** the phasor is in 90–180° continuously to Nyquist. |
| 10 | *"`H(0)=0`, so the term cannot rate-limit a held command"* | **SCOPED.** *"Cannot bias a HELD command"* stands. ***"Cannot cap achieved PEAK rate" does not, once railing is in play*** — a railed term is `sign(α)×511` = **10.7 % of governor authority** as constant DC drag through the whole acceleration phase. |
| 11 | *"the notch and the damper are perfectly confounded"* (`inherit-audit`, self-corrected) | **Right about the STATE, wrong about the DELTAS.** V104→V105 moved only the notch; V105→V106 moved only the Y row. Each leg has a genuine single-variable contrast. **What has never existed is the joint state Honda-biquad + high-damper — which is exactly what V108 creates.** |
| 12 | `sar 5` *"leaves p50 at 1.25 LSBs, unusable"* (`inherit-audit`) | **Arithmetic error — the same 5× omission that produced V107's mis-sizing.** True LSB is **6.4**, p50 = 6.2 LSBs. |
| 13 | `0xC674E`'s *"structural abort above ~9×"* as a constraint on `0xC61BE` | **Mis-scoped.** It constrains the **GAIN**: `0xC61B2`/`0xC61B4`'s own tracking formula `512×gain/891` crosses 5120 at gain = 8910 = **exactly 10.0×**. Unrelated to `0xC61BE` below the 18,830 stop. |
| 14 | `accord-4x-lkas-gain-is-the-frozen-variable` (★★★★★) | 🛑 **STALE.** 4× only through V100; **8× on V101; 6× since V102.** |
| 15 | `0xC62EA` as the ≤5–6 mph drop-off gate (mine) | **REFUTED.** It has been **0 since V53**, ~50 builds. The drop-off is explained without a gate: rail duty is **1.60 % below 10 km/h vs 33.49 % at 10–25**, because Y[0] is byte-identical to V106 there *and* `|c2c|` p50 is 62 vs 974. |
| 16 | `reference_accord_gp6abe_column_degps_scale_settled.md` | 🛑 **SELF-CONTRADICTING** — an unretracted earlier draft argues the opposite of its own header and would give anyone reading top-to-bottom an **8×-wrong scale.** Fixed by its author. |

---

## 5. THE V109 CANDIDATE — `0xC40DC`, PRICED AND GATED

**It is the structurally correct fix and its sweep is already done.** `α2 = 22/64` at `0xC40DC` sets the
cascade's rolloff. `hfmech`'s gate-quality sweep, Y auto-scaled to hold 21.73 Hz constant:
```
 K2  peak_Hz  -3dB span      @3Hz  @7.79  @21.73  @61    @100   @200   @300   sector entry
 22   61.1   25.1-153.0Hz   1.000  1.000  1.000  1.000  1.000  1.000  1.000    74.1 Hz  <- today
 16   50.3   20.7-124.3Hz   1.011  1.045  1.000  0.855  0.787  0.740  0.729    58.9 Hz
 14   46.5   19.0-115.5Hz   1.021  1.074  1.000  0.796  0.714  0.660  0.648    54.0 Hz  <- top pick
 11   38.5*  15.3- 98.4Hz   1.062  1.181  1.000  0.668  0.572  0.515  0.503
```
⭐ **At K2 = 14 the delivered response is FLAT across 18–30 Hz (1.024 → 0.966) and cuts 20–35 % over
61–300 Hz** — it de-rails **without giving back one count of mode-band damping**, which lowering the Y row
cannot do (Y is a flat multiplier, so any de-railing it buys is paid for one-for-one at 21.7 Hz).

**GATE 1 on the cell: cleanest possible** — exactly ONE gp/tp access image-wide (`ld.hu 0x50dc,tp,r11`
@`0x41626`), zero writers, `disp|1` trap handled, 6-byte form checked. Address anchored inside
`FUN_00041464`, the accel cascade — **not** the observer block where `0xC40D2`/`0xC40BC` live.
**GATE 2 at the mode: clean** — the phasor stays in the proven-safe 180–270° sector down to K2 = 3.

🛑 **WHY IT IS NOT IN V108 — three reasons, all from its own author:**
1. **The sector-entry moves DOWN, not up** (74.1 → 54.0 Hz at K2 = 14), *widening* the band in which the
   lane can structurally sustain oscillation. My hoped-for "second benefit" was refuted.
2. 🛑 **`gp-0x6c2c` fans out to THREE consumers** — the FOC motor-model float term, this friction lane,
   and the oscillation-detector FSM (`FUN_000428d4`, `cal(0xC620A)` = 12800) — and **two were never
   verified against a RESHAPED rather than merely rescaled signal.** A cal with clean ownership feeding a
   signal with unverified fan-out is not a cleared gate.
3. **The rail-duty prediction is unverifiable.** The only available method is the open-loop push-through
   that was just measured **32× wrong**. `hfmech` refused to give a number, and was right to.

🛑🛑 **AND THE COMBINATION TO AVOID: E3(α2) WITHOUT E1.** K2 = 14 moves the damper's dangerous sector
down to 54 Hz — and across **54–74.5 Hz, V105's coefficients leave the parallel base-assist lane a
geometric-mean 5.15× (+14.2 dB) louder than Honda's, 21.8× at the sector's new entry point.** Taking the
band-limit while leaving V105's notch on the car moves the dangerous sector **into the one band where we
deleted Honda's own attenuation.** ⇒ **ship them together or ship neither. V108 ships E1, so the
prerequisite will already be on the car.**
⊕ **Take K2 = 14 with ZERO Y compensation.** Uncompensated it delivers ×0.920 at creep — **below the ~9 %
perceptual floor on record** — and it *lowers* the creep dose slightly, nudging the 33.5 % creep relay
duty the right way. Compensating would push Y[0] to 97.8 % of the int16 floor to recover a number nobody
can feel, at the knot where the relay is worst. ⭐ **The exact int16 boundary: `29490 × 1/0.90 = 32,767`
against a floor of 32,768 — an α2 cut of −10 % is the LAST one that can be compensated at creep.**

---

## 6. INSTRUMENT FINDINGS

- 🛑 **CAN 427 (`0x1AB`) arrives at 49.8 Hz, Nyquist 24.9 Hz** — not 100 Hz. It cannot carry any spectral
  claim, and it is blind even to the 27 Hz residual line. Its **tail** remains informative because
  sampling is uncorrelated with vibration phase.
- 🛑 **The between-drive audio contrast is PERMANENTLY unavailable.** Parked, engine on, LKAS off,
  v < 1 km/h — no tyres, no wind, no steering — **the cabin sounds 3–12× different between drives**
  (`corr(log E, log M)` = +0.836/+0.914/+0.919). That is a per-drive multiplicative acoustic gain and
  **no openpilot-version finding touches it.** ⭐ Route `1e` has **35.4 s of matched manual inside the
  grinding window**, so the within-drive contrast is available and is strictly better. ⊕ A retroactive
  per-drive reference clip (parked / engine-on / LKAS-off segment at the start of a drive) would make the
  between-drive version estimable — worth checking before anyone concludes it cannot be done.
- **The device was reflashed** — route counter reset `a6` → `1b`, SSH host key regenerated, authorized_keys
  wiped. ⚠ **`0000001b` exists TWICE on disk with different hashes** (2026-07-27 pre-reflash, and
  2026-08-26 = V107). **Key every cache on `counter--hash`, never the bare counter**, and never assume
  low route number = old build.
- ✅ **The a6-vs-1e instrument confound is CLOSED for the CAN channels**: one openpilot commit advanced
  (`7c6741a9` → `36d0c074`), **AGNOS unchanged at 19.6.2**, and every lateral `CarParams` field identical
  including `torqueBP/torqueV = [0, 4096]`, `steerActuatorDelay 0.100`, `steerRatio 16.33`, the torque
  params and the whole `carFw` fingerprint. ⚠ `STEER_MAX`/`STEER_DELTA_*` are compile-time and unlogged.
- 🛑 **The whole extractor family was DEAD** — `ModuleNotFoundError: _grind2_lib`, because the 2026-08-26
  reorg moved `analysis-2020accord/_grind2_lib.py` into `lib/` while the `PATH BOOTSTRAP` block stops at
  the **first** `.pkgroot` above the file. **Fixed in 729 files**: the block now walks every `.pkgroot`
  root in the repo, nearest first.
- **`cs_v` / `v_rear` / `ws_*` are m/s, not km/h**, and `extract_ra6.py:derive()` mislabels them.
- **The audio pitch discriminator is a NULL with a cause**: no rate-selective band exists to track — every
  band moves together by ~−1.9 dB across steering-rate quintiles, a broadband level shift. **Loop-mode vs
  motor-order is NOT resolved.** The positive control passed (0.119–0.213 dB/km/h, R² to 0.71).

---

## 7. OPEN ITEMS, WITH WHAT WOULD CLOSE EACH

| # | open item | what closes it |
|---|---|---|
| 1 | 🛑 **The alternating drive**, now with **constant-speed disengagements, throttle steady ~15 s** | One drive. **No build needed.** Closes the ~8 Hz LINE null, the pitch-vs-amplitude cell, the engaged/manual contrast above 25 km/h, and the post-disengage decay. |
| 2 | **`0xC40DC` fan-out** — the FOC motor-model term and the oscillation-detector FSM against a *reshaped* `gp-0x6c2c` | A trace. **Gates V109's primary lever.** |
| 3 | **Rail duty vs K is threshold or smooth?** | V108's own drive. If duty falls much more than the Y change predicts, a self-sustaining cycle broke. |
| 4 | **≥70 km/h clamp duty** — V107's drive-card item #2 | V108's `sar 5` tap. Unanswerable before it. |
| 5 | **Is the several-hundred-Hz content a fixed loop mode or a motor order?** | Not resolvable acoustically on `1e`. Needs a drive with a rate-selective band present, or an IMU log at 208/416 Hz ODR. |
| 6 | **The 4 kHz domain's spectral content** (does 500–3500 Hz energy exist to fold onto 100 Hz?) | Unmeasurable from firmware. Needs a probe on `gp-0x29c4`/`gp-0x4f4e`. |
| 7 | **`0xC674E`'s query variable** — is `0xC61B2`/`0xC61B4` code-connected to that int-vs-float lockstep, or only numerically near it? | A trace. **Gates any `0xC61BE` raise past 18,830.** V27 hard-faulted the instant the wheel turned after touching one side of that family. |
| 8 | **`gp-0x6ac2` at `\|rate\| ≥ 1100`** — never probed, in exactly the operator's hard-turn regime | One cave rung, whenever the cave next opens. |
| 9 | ~~V100's rail duty, never harvested~~ 🛑 **CLOSED — AND THE 'NEVER HARVESTED' CLAIM WAS FALSE.** It was harvested **2026-08-14** (`rlog-tools/score/score_r85_v100.py`, cache `_scratch/cache/r85/`, written up in `HANDOFF-2026-08-14-v100-flew-and-six-levers-closed.md` §1). Re-run today: **d(b5) = 0.000000 over 24,925 engaged frames / 249.2 s / 6 episodes**, CI [0, 0.01862] by rule-of-three on n_eff (a constant bit has no bootstrap). `b6` (the PID ERROR clamp) is 0.000000 too. **The gate is proven live** — `b4` reads the SAME CELL with duty 0.6057 and 16.84 sign-flips/s. ⇒ **the dose is MERELY SMALL, NOT structurally zero: `0xC40D2` = K1 = 204 IS delivered, and so was every lever V89→V99.** The reference-clamp hypothesis is dead; do not re-propose it. ⚠ Envelope: |rate| p50 1.0–32.5 °/s, and total reachable is **17,152 = 2.09× the 8192 threshold** (not the ~12× the record claimed — that summed admission windows instead of writer clamps). | **Nothing. Already closed.** |
| 10 | **`gp-0x4f62`'s effective delay** — the 125 Hz claim does not follow from the code | Trace `cVar10`'s writers and the `gp-0x4e3d` tick-weight table. |
| 11 | **The ratchet** — ~7.4–8.6 Hz, demand-driven, hands-off, engagement-required. Nothing has moved it. | Item 1. ⚠ *"Nothing in sixty builds"* **overstates**: the formal instrumented base is **four builds / four routes** (V70/V69/V62/V59). |
| 12 | **`LEVER-INDEX` is 10 builds stale** — its own header says "current through V97"; V101–V107 have no rows | A pass over it. |
| 13 | **`BUILD-LINEAGE.md:248` marks V102 "NOT FLASHED"** but `0xC6CD0` = 5346 is demonstrably on the car | One-line fix; the twelfth stale flight-status row. |
| 14 | **Golden-model `assist_polarity` = 1** where `gp-0x6752` is −1 | Re-derive `_self_check()`'s expectations from the firmware. Unchanged from V107. |

---

## 8. HOW V108 DIFFERS FROM THE ARC SINCE V38

```
V38-V52    authority / filters / poles / caves
V53-V61    telemetry probes and lane mutes
V62-V73    the rate lane (r24/r26)
V74-V83a   the base-assist damper
V84        damper reverted to Honda
V85-V99    observer / plant-model probes
V100-V103  the gain ladder + arming the biquad
V104       c4, a flat lane gain                    FLOWN, NULL
V105       the biquad's SHAPE                      FLOWN, relocated the mode, NEVER REVERTED
V106       gp-0x6b26 Y row x3.0 uniform            FLOWN, EXTINGUISHED the mode at low speed
V107       gp-0x6b26's SPEED SCHEDULE              FLOWN, made the damper a RELAY
V108       ** SUBTRACTIVE, AND ABOVE 50 Hz **      <- a class this arc has never run
```
**V104 through V107 were four consecutive ADDITIVE builds on one lane, every one of them sized by a
25–50 Hz instrument.** V108 is the first build in this arc to **(a) REMOVE kit-added loop gain rather
than add more**, and **(b) be designed against the 50–500 Hz band at all** — a band in which this kit has
never measured anything, because every channel it owns is Nyquist-limited below it.

⭐ **And it is a genuinely new measurement, not a cleanup.** The V105 coefficients appear on exactly three
images (V105, V106, V107) and on every one the engaged damper is above stock; the raised damper appears
on exactly two and on both the notch is present. **The joint state "Honda's biquad + a high damper" has
never existed. V108 creates it.** If the mode stays extinguished, the notch was never doing the work and
16 bytes come off the car permanently. If it returns, the notch was load-bearing after all — and that is
something the corpus currently cannot tell us either way.

**Frozen across this whole arc:** `0xC6CD0` = 5346 (the 6× — **exactly 6.000×**, 891 = 1×; never lower
it), `0xC407E` = 511 (the interlock, one under its own 512 trip), the X breakpoints, both MANUAL mode
records, Lever B (`0x3AA96` + `0xC6446` = 5244 — the kit's only measured fix), `0x454FE`, and the 164-byte
cave.
