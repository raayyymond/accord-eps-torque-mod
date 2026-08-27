# HANDOFF 2026-08-27 — V107 FLEW AND THE DAMPER IS A RELAY; V108/V109/V110 BUILT; THE VISIBLE OSCILLATION IS OPENPILOT'S

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

🛑 **CORRECTED 2026-08-27 — `gp-0x69b0` IS A Q15 MULTIPLIER, NOT A GATE, SO THE RELEASE IS A CROSSFADE.**
An earlier census over its 45 accesses found **zero `mul` instructions** and concluded "gate". That does
not follow: **the multiply's operand is a REGISTER loaded ~2,700 bytes earlier**, and an operand-text
search over accesses to a symbol finds loads and stores but cannot see what is done with the value —
the same blind spot `CLAUDE.md` already records for register-indirect writes.
**The multiply is `0x2A1E6  mul r14,r9,r0`, then `0x2A1EA sar 0xf,r9`, `0x2A1EC sxh r9`** ⇒
`LKAS_lane = sxh((lane × gp-0x69b0) >> 15)`. Register liveness proved mechanically: all 41 accesses to
`gp-0x69b0` sit in `0x2936A`–`0x2972A`, every read is `ld.hu …,r14`, and **`r14` is never written across
the 1015 instructions between the state machine's exit at `0x29734` and the multiply** (the only
instruction with `r14` last is `0x29A48 cmp r0,r14`, PSW-only), with **zero `jarl`/`callt`/`trap`** in
that span so no callee can clobber it.
⊕ **The sign objection dissolves too**: the cell is *stored* with `st.h` but *read exclusively* with
`ld.hu`, and the SM saturates it at `0x8000` (`0x29490 ori 0x8000,r0,r14`). 32768 does not fit a signed
int16, so it stores as −32768 and reads back as **+32768 unsigned** — "signed, resting at 0/−32768" is
exactly what an unsigned Q15 0…32768 looks like in a raw halfword dump. **Range 0.000–1.000.**
⇒ **During the ~2.05 s tail there IS a decaying LKAS command while the engaged-only damper is still in
force** — a crossfade, not a hold-then-snap. The measured 2.05 s release stands unchanged; what changes
is what the car is doing during it.

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

---
---

# PART 2 — THE SESSION CONTINUED. V109 AND V110 BUILT; THE VISIBLE OSCILLATION IS NOT OURS.

**Six more subagents: `a2gate`, `ratchet`, `freegates`, `closedloop`, `lowfreq`, `ratchlever`.** All
confirmed stopped from the harness. Two further agents (`rezband`, `blanked`) were open at the time of
writing — their results are NOT in this handoff.

---

## 11. ⭐⭐ THE VISIBLE OSCILLATION IS OPENPILOT'S WEAVE — CLOSED, AND IT IS NOT A FIRMWARE PROBLEM

This is the largest single result of the session and it removes one of the operator's five goals from
the firmware's reach entirely. Full note:
`memory/accord/mechanism/accord-visible-oscillation-is-openpilots-weave.md`.

**It took two operator questions to find, and both were decisive.** Asked how far the rim travels he said
**"a centimetre or more"**; asked whether it TURNS or SHAKES he said **"turning — the spoke swings."**
The first killed the ~8 Hz line as a candidate (it is 0.7 mm); the second said it must be in the
steering-angle channel.

**46 events, 17.3 % of engaged time, up to 24.02° p2p = 77.6 mm at the rim, at 0.44–2.93 Hz** [EVIDENCE].
🛑 **His "under or around 10 Hz" is really 0.4–1.6 Hz.** Ceiling by band, max p2p over all engaged
windows: 0.4–0.6 Hz **24.02°** · 1.0–1.6 **9.54°** · **4.0–6.3 1.33° (4.3 mm)** · **6.3–10 1.12°
(3.6 mm)**. ⇒ **Above 4 Hz the angle NEVER reaches a centimetre.** Every prior search scanned 4–10 Hz
and was structurally incapable of finding it.

**Three independent lines say openpilot drives it:**
```
  angle vs COMMAND        +46.8 deg [+29.4,+71.3] R=0.581, angle LAGS in 72 %
                          near-straight +63.3 deg  R=0.740, angle LAGS in 85 %
                          1.0-1.6 Hz median lag +0.088 s  <- on steerActuatorDelay = 0.100 s
  angle vs DRIVER TORQUE  -63.2 deg [-88.1,-24.8]  => the HANDS REACT to the wheel
  yaw follow ratio        p50 1.17, range 0.73-1.61 in EVERY event
```
⭐ **The command-leads signature is STRONGER near-straight than cornering** (R 0.740 vs 0.538) — the
opposite of what a road-driven artefact would do. And **engaged is 5–45× QUIETER than the driver at
matched speed** across 0.4–3.5 Hz: this is a controller weaving *less* than a human, but **periodically**,
and periodicity is what the eye catches.
🛑 **IT IS NOT THE GRINDING.** Rail duty inside events vs speed-matched baseline **1.01 [0.88, 1.22]**;
audio 100 Hz–2 kHz **+0.50 dB [−1.18, +2.54]** against a control spread of [−6.2, +7.9]. **Two
independent defects.**
⇒ **[BELIEF, strongly supported] a limit cycle in openpilot's lateral loop.** ⭐ **It explains why sixty
firmware builds never moved it: there was never a firmware lever on it.** 🛑 The operator was told; it is
his call under `feedback-no-openpilot-side-modifications`.
⚠ **Manual exposure above 24 km/h is 35.8 s total**, so the >24 km/h rate ratios rest on 0–2 manual
events while 5 of 13 near-straight events are at 39–76 km/h. **Closes with matched manual at 50–80 km/h.**

⭐ **METHOD LESSON:** a single wideband 0.4–3 Hz detector finds **NOTHING** — at these amplitudes a
0.45 Hz cornering input **destroys the zero-crossings** of a small 1.2 Hz limit cycle riding on it.
**Five sub-bands found it.** Controls ran first, including a **ringing control** (impulse/step/ramp
through every band filter, **zero spurious chains in 15 combinations**).

---

## 12. THE RATCHET'S CENSUS WAS THE WRONG TOPOLOGY — and that is why sixty builds failed

```
   T_bar = Z0*Om_w + P*(agg),   agg = F*Om_w + L*T_bar
     =>   Z = T_bar/Om_w = (Z0 + P*F) / (1 - P*L)
```
**Every aggregator lane fed by column torque or motor rate is a term in `L` — a DENOMINATOR term, not an
additive torque.** The kit had been summing denominator terms into a numerator. The numerator actually
required is **146–408 ct·s/rad — an order of magnitude BELOW what was already priced**, and
**`Q_eff/Q_passive` = 14.3 means the loop cancels ~93 % of the mode's own damping**, which no additive
term can produce.
⇒ **A cal lever CAN touch the ratchet, but ONLY through Q, and ONLY if sized as a loop gain.** Every
flown-null attempt (V39/V41/V43/V56/V97/V103/V105) was an additive lever. **That is the retro-explanation
this kit has been missing.**
🛑 **AND A UNITS DEFECT THAT INVALIDATES EVERY PUBLISHED LANE NUMBER:** `Re(Z_i)` computed as
`|lane counts|/|Om_w| · cos(phase)` is in **aggregator counts per rad/s**; the measured −3073…−4890 is in
**torsion-bar counts per rad/s**. Every published lane figure is missing `M(jω) = d(T_bar)/d(agg count)`
— firmware half ~1.00–1.07 ∠0°, **mechanical half NOT IN THE IMAGE**, bounded |M| ~ 0.35–0.53, which
makes every priced term *smaller* and the additive gap *worse*.

---

## 13. ⭐ THE HANDS-OFF MECHANISM, FOUND — a virgin four-table taper

**The LKAS controller output is multiplied by two cascaded driver-torque-indexed Q8 curves**, at
`0x2A0B4` (`mulu r9,r23,r0` → `(A*B & 0xFFFF) >> 8` → `* controller` → `>> 8`), applied **before** the
`0xC61BE` clip and before the `0xC646C` forward scale. `gp-0x682f = min(|gp-0x4f60| >> 5, 255)`, so
**X · 32 = raw torque counts**. Pointer arrays `0xCBB54` / `0xCBC34` / `0xCBAE4` / `0xCBBC4`, all
**mode-indexed** and **VIRGIN on all 103 built images** — known to the record only as *"further LERP
curves (gain/limit; exact roles medium-confidence)"*.
```
  raw |t|      0-512    928    1768   2048   >=3072
  m26 B(!=2)   1.000   0.884  0.398  0.239  0.200
  m26 B(==2)   1.000   1.000  0.764  0.682  0.400->0.200
```
**Measured on route `1e`:** hands-OFF `|t|` p50/p75/p90 = 190/453/794 ⇒ B = **1.000/1.000/0.956**;
hands-ON = 1768/2577/3079 ⇒ B = **0.398/0.220/0.200**. ⇒ **a 2.5× command cut at the median hand-on
while hands-off sits at full transparency out to p90.**
The ratchet's dose-response against the taper's **own knots** (pre-registered, not chosen from the data):
`R_LINE` 2.51 → 4.21 → **9.55** → 6.60 → **0.63**, contrast **4.22× [1.17, 5.70]**, placebo flat.
🛑 **THE CONFOUND CANNOT BE REMOVED FROM LOGS**: a hand physically damping the wheel predicts the same
collapse. One argument favours the firmware — the suppression is **band-selective** (6–7.4 Hz falls 2.8×,
7.4–8.6 Hz falls 5.0×, **8.6–12 Hz unchanged**) where broadband mechanical loading would take all three.
⚠ **BELIEF, on 5 windows.**
🛑 **DO NOT propose the taper as a FIX.** The only edit direction that tests it (knots outward) gives
**more** command with hands on — which makes the ratchet *worse*. **It is a diagnostic, not a cure.**

---

## 14. V109 — `0xC40DC` (α2) 22 → 14. GATE 1 AND GATE 2 BOTH CLOSED.
```
image  e9eb51fcad9ffc8768cd3e8eb601619d0f2acc0f702f01c4732243c70cc7f4d6
.rwd   83047f0fd3b5b656720487d5f70755c3b2506c4293097b403abf003e972087c1
builder analysis-2020accord/builds/v108_plus/build_v109_tva.py, 30/30, BASE = V108
5 bytes vs V108 (1 payload + 4 CRC).  Cal-only.  Cave byte-identical.  UNCOMPENSATED.
```
α2 is the only axis of this lane **nobody has ever touched** — V106 moved its MAGNITUDE, V107 its SPEED
SCHEDULE, and both pay for HF reduction **one-for-one at 21.7 Hz** because Y is a flat multiplier.
**Shape does not.** Uncompensated ratios, verified against the integer cascade:
```
   f Hz     1      3    7.79  21.73    27     40    61.1   100    200    300
  ratio   1.000  0.998 0.988  0.920  0.888  0.816  0.732  0.657  0.607  0.596
```
⇒ **~0 % at manoeuvre frequencies (no steering-rate cost), 1.2 % at the ratchet, 8.0 % at the mode
(below the ~9 % perceptual floor) — and 27–40 % across 61–300 Hz.** Phasor at 21.73 Hz **222.77°**, safe.

**GATE 1 closed — and the fan-out is FOUR consumers, not three.** Cell: one access image-wide, zero
writers. Signal: friction lane = the target · **oscillation detector SAFE and margin IMPROVES** (arms at
`cal(0xC620A)` = 12800 vs a corpus max ~5,300; **V64 flew 1,158 reversals with ZERO arms**) ·
`FUN_00071272` writes byte 0x10 of a **36-byte-stride diagnostic log record at `gp-0x26e8`**, not the
torque path · `FUN_0007b022` has **four outputs with zero readers** and its fifth (`gp-0x4f64`) is
cleared by tracing **its own three producers**. `gp-0x6c2e`/`cal(0xC40DA)` = 3 are **independent AT THE
PRODUCER** with disjoint reader sets as a second reason.
🛑 **GATE 2's real cost: the 90–180° sector ENTRY slides DOWN 74.1 → 54.0 Hz.** ⇒ **V109 MUST sit on a
V108 base** — across 54–74.5 Hz V105's notch left the parallel lane **5.15× (+14.2 dB)** louder than
Honda's. **`build_v109_tva.py` ASSERTS the base and refuses to build on any other.**
🛑 **Rail duty under this dose is NOT predictable** — the only method available was measured **32× wrong**
on this lane, the loop term is 14–16×, and α2 sits upstream of the distribution any solve would need.
**V109 is a deliberate single-variable experiment against V108.** ⇒ **Fly V108 first if you want the
contrast; fly V109 if you want one drive instead of two.**

---

## 15. V110 — Kd `0xC6AE6` 2048 → 1024. BUILT, BUT PARKED, AND THE REASON IS A DISAGREEMENT I RESOLVED AGAINST MY OWN AGENT.
```
image  3de48a09735db35b74af88dfbe8a4d6a998bfb13d86ffc65a894e4e14db8f080
.rwd   becaab6d7ecce18df1bcba0112189d994fc048dad3720ea6e96bbf934a33410c
builder analysis-2020accord/builds/v108_plus/build_v110_tva.py, 29/29, BASE = V109
```
**D is the ONLY PID branch that PUMPS at 7.8 Hz** — `Re(Z)` **−458** against P **+844** and I **+296**
(net +682, so the PID as a whole damps and the pump cannot be removed without attacking D specifically).
`H_D = (Kd/1024)(1 − z⁻¹)`, so **Kd scales MAGNITUDE ONLY and D's phase never reverses 2–500 Hz**, and it
is **exactly zero at DC** — no steady-state assist cost, no steering-rate cost. **Virgin, 1 reader, 0
writers, no lockstep twin, no int/float mirror of the `0xC674E` class.**
⭐ **Leveraged**: |D| = 0.0979 against |L| 1.876–2.825 ⇒ D is **3.5–5.2 % of loop gain**; halving removes
1.7–2.6 %, which near a marginal loop (`Q ~ 1/(1−|PL|)`) is a **Q cut of 18–26 %** at the measured
`Q_eff/Q_pass` = 14.3, or **5–7 %** on a deliberately conservative 4.0.

🛑🛑 **WHY IT IS PARKED.** `ratchlever` gated it SHIP on the grounds that the standing memory
`accord-six-levers-closed-on-arithmetic`'s verdict — *"D damps 16–35 Hz, cost 3–4× the benefit"* — has
**"no computation behind it anywhere in the kit."** **I checked the crux myself and rejected that.** The
numbers **−0.217** (18–22 Hz) and **−0.336** (26–31 Hz) appear in **five** files including an archived
session state. And the refutation does not survive `ratchlever`'s own admission that the translation away
from 7.79 Hz needs `G_bar(f)`, **which is not in the image and is anchored only at 7.79 Hz.**
**My own arithmetic makes the risk concrete: D's phase in its own frame moves only −2.2° between 7.79
and 20 Hz** (+88.60 → +86.4). Carrying that alone from the one anchored rotation (7.79 Hz → −91.40°,
pumping) puts 20 Hz at −93.60°, cos = −0.063 — **still pumping**. For D to DAMP at 18–35 Hz the **plant**
must supply ~+90° across that span — **and a resonance at 7.8 Hz rotates ~180° through it, so that is
entirely possible.** ⇒ **The memory's claim is PLAUSIBLE and CANNOT BE REFUTED FROM THE IMAGE.**
⇒ **The risk is that halving Kd removes damping at 18–22 and 26–31 Hz — the exact bands V108/V109 exist
to fix. DO NOT FLY V110 until V108 or V109 has established a grinding baseline.**
🛑 **The memory is NOT marked stale.** `ratchlever` flagged it in good faith and its instinct is
reasonable — but *unverifiable cuts both ways*, and the safe reading is that **nobody knows D's sign
above 16 Hz.** ⚠ Kd also touches **MANUAL** steering (`FUN_0002214a` gates `FUN_0003a382` on states
{4, 5, 10, 11}), though its DC cost is exactly zero.

⭐ **REJECTED, and recorded so it is not re-proposed**: `0xC6384`, the assist-map per-segment slope cap
(2048 = Q10 2.000, also virgin, reported as 7.8× the entire PID). It is **memoryless — flat magnitude,
0° phase, identical DC to Nyquist** — so a dose moves loop gain by the same fraction at every frequency
simultaneously, re-litigating 18–35 Hz plus DC feel plus manual steering. **And whether it BINDS AT ALL
is unresolved**: the natural slope depends on a history-dependent slew mechanism that cannot be evaluated
statically. **DO NOT SHIP.**

---

## 16. THE CLOSED-LOOP SIMULATOR — built, validated, and it refuses to answer the question
`analysis-2020accord/model/eps_closed_loop_sim.py` + `studies/closed_loop/`.
⭐ **ACCEPTANCE TEST PASSED with nothing fitted** — an exact-integer reimplementation of the cascade run
per-sample over route `1e` reproduces the measured rail duty on all five bins (1.60 vs 1.68 · 33.52 vs
32.32 · 21.15 vs 21.27 · 5.19 vs 4.27 · [0.00,0.16] vs ≤0.23 %), and **held out on route `1b`** — a
different drive, same build — **33.76 % vs `1e`'s 33.52 %.**
⇒ **V108's Y-row change alone is predicted to take 10–25 km/h rail duty from 33.52 % to 7.0–15.4 %.**
⚠ Duty is **strongly driving-dependent above 25 km/h** (`1b` gives 31.88 % at 24–40 vs `1e`'s 21.15 %).
🛑 **BUT A CLOSED-LOOP PREDICTION IS STRUCTURALLY UNAVAILABLE**: the identified column model's validity
band is **5–13 Hz** while the lane's −3 dB span is **25–153 Hz** ⇒ **100 % of it is extrapolation**, and
above 13 Hz `|Z|/ω` collapses 1.33 → 0.45 for reasons the record itself calls unresolved.
**`ClosedLoopSim` refuses to run without `allow_extrapolation=True` and no number came from it.**
🛑 **"Fit on a6, predict 1e" is NOT CONSTRUCTIBLE** — `x6c2c_mag` exists only on V107 routes; a6's tap
was aimed at `gp-0x6b86`. **The c2c instrument has only ever existed on one build.**

---

## 17. THE GHIDRA EMULATOR — three doors, three distinct reasons, and one of them nearly produced a lie
1. **`emulate_function` is hardcoded x86** — `"Undefined register: ESP"` on every V850 call regardless of
   arguments; `V850:LE:32:default` has no ESP. Server-side fix: `getDefaultCompilerSpec().getStackPointer()`.
2. **`run_script_inline` was gated** behind `GHIDRA_MCP_ALLOW_SCRIPTS=1`. **The operator enabled it**
   (the var had to be set at **User scope** — it was absent from User AND Machine — and Ghidra relaunched).
   The gate then opened, and a **second** blocker appeared: Ghidra's OSGi layer holds `$USER_HOME/ghidra_scripts`
   as a **placeholder** bundle. **Root cause found in the tool config: `BundleHost_ENABLE` entry [9] is the
   ONLY one of 23 set `false`.** ⇒ tick it in Script Manager → Manage Script Directories. **UNRESOLVED at
   time of writing.**
3. 🛑 **`get_function_pcode` is structurally insufficient to emulate from — and it WOULD HAVE PRODUCED A
   CONFIDENT WRONG ANSWER.** An agent built a p-code interpreter and ran it before finding the defects:
   **no block out-edges**, and the decompiler's condition-normalisation flips conditions while swapping
   edges (at `0x36C38`/`0x36CCE`/`0x36CEE` the inverted sense is right, at `0x36C48` the non-inverted one
   is) ⇒ **polarity unrecoverable**; and **SSA varnodes collapse onto one `(space,offset)` key**.
⇒ **The arithmetic is validated instead by three NON-EXECUTION methods that agree** — decompile,
assembly, p-code IR — and **the kit's mirrors are CORRECT.**
⊕ **Exact rail thresholds are 1063 / 1306 / 1959 ct** (`sar` FLOORS, ~0.2 % earlier than the closed form).
⊕ **The LERP divide is `INT_SDIV`** (truncates toward zero) — **a non-monotone Y row would make a
floor-division mirror off by one.**
⊕ 🛑 **An unpriced nonlinearity: the `d32` clamp (±0xFA0000)** saturates the lane above ~1,961 ct of input
at 61 Hz. **The whole α2 sweep table is a linear-`|H|` calculation** — safe for railing, **not** for
broadband claims.

---

## 18. RECORD CORRECTIONS MADE THIS SESSION — including two of my own

| # | claim | status |
|---|---|---|
| 1 | **"V100's rail duty was never harvested"** (mine, in §7 of Part 1 and in `STATE.md`) | 🛑 **FALSE.** Harvested **2026-08-14**; `score_r85_v100.py` and the `r85` cache exist. Re-run: **d(b5) = 0.000000 over 24,925 engaged frames**, gate proven live by `b4` on the SAME cell at duty 0.6057. ⇒ **the dose is MERELY SMALL, not structurally zero — `0xC40D2` = 204 IS delivered**, which vindicates V108 keeping it. ⊕ Total reachable is **17,152 = 2.09× the 8192 threshold**, not the ~12× the record claimed. |
| 2 | **"the instrument was structurally blind to the passband"** (mine) | **Right about SPECTRA, WRONG about DUTY.** Duty is a functional of the **marginal**, which an instantaneous tap samples unbiased. **The measured duties are sound.** V107's error was a **MODELLING** error — an open-loop push-through on a closed loop — not an instrument error. |
| 3 | **`gp-0x69b0` is a GATE, not a multiplier** | 🛑 **REFUTED with an address.** `0x2A1E6 mul r14,r9,r0` / `0x2A1EA sar 0xf` / `0x2A1EC sxh`. The census found no `mul` because **the operand is a register loaded ~2,700 bytes earlier** — an operand-text search cannot see that. `r14` is never written across the 1015 instructions between the SM exit and the multiply, with zero `jarl`/`callt`/`trap`. Stored `st.h`, read **exclusively** `ld.hu`, saturated at `0x8000` ⇒ **unsigned Q15 0…32768.** ⇒ **the mode release is a CROSSFADE, not a step** — during the ~2 s tail there IS a decaying command while the engaged damper is in force. |
| 4 | **`0xC61B2`/`0xC61B4` gated by `0xC674E` ("5120 > 3072")** | 🛑 **UNFOUNDED and already falsified on-car.** Three disjoint reader sets; the corridor's LKAS arm is annihilated by `cal(0xC64CB)` = 0; and `0xC674E` has been frozen at 5120 since V38 while the clamps went 2048 → **4096 (V101)** → 3072 — **V101 flew at ratio 1.25 without faulting.** ⭐ **The REAL interlock is an INT quad vs a FLOAT quad at `float == int/1024` ±5 LSB**, and the **V28→V29 diff is literally those four float cells**. It PREDICTS V27's symptom: the walls are × `pol = clamp(gp-0x6752,−1..+1)`, so **at pol = 0 a desynced pair still agrees** and the fault fires the instant the wheel leaves centre. |
| 5 | **`0xC520C` is "the first/tightest bind"** (`ratecap`, self-retracted) | **STRUCK as a lever.** Route `a6`: peak `gp-0x6ac0` **1462 ct**, **0.11 % of engaged time** above X[0], **never** past X[1]; `gp-0x4f64` at its max **4762 for 99.9 %+** of engaged time. Reconciles `b6` = 0.000000 and explains V41's null. ⊕ The disputed "528" was **hands-off spring-return only** — a regime mismatch, not a scale error. |
| 6 | **`accord-4x-lkas-gain-is-the-frozen-variable`** | **STALE** — 4× only through V100; **8× on V101, 6× since V102.** Correction banner added to both copies. |
| 7 | **`gp-0x4f62` "peaks at 125 Hz"** | **DOES NOT FOLLOW FROM THE CODE** — ring buffer + variable tick weights + a conditional call. `D = cal(0xC6C42) = 4` is byte-confirmed; the effective delay is **unresolved. Do not reuse 125 Hz.** |
| 8 | **memory index links** | **5 of 428 broken** by the reorg, repaired. ⊕ And I then **misreported a 6th as a dead file** — it was an **off-by-one in the relative path** (`../../.claude/` from `memory/` lands above the repo root). My checker only resolves paths and cannot distinguish "target absent" from "path malformed". |
| 9 | **`0xC64DE` "re-engage authority ramp"** | **WRONG LABEL** — the half-period of a **sign-flipping square wave**; V18 moved it **29.41 → 18.52 Hz, into grind #1's band**; **amplitude LERP all zeros ⇒ INERT.** ⚠ A latent 18.5 Hz injector into the 6× path, four halfwords from live. |
| 10 | **the `0xE4`/`0xE5` taper "skip"** | **NOT A BUG** — the skipped records are exactly the complement of the reachable selector set {0,1,3,4,6,7,8,9}. Our car is **TVCA4 → slot 11 → selector 7 → `0xE51A8`, RAISED.** V74's slot naming is right; V38's is wrong. |
| 11 | **`accord-aggregator-lane-mirrors-6ada-6adc`** | `gp-0x6ada`/`gp-0x6adc` are **SWAPPED** relative to the stores at `0x3AD4E`/`0x3AD5A`. Flagged 2026-08-10, still unfixed. |
| 12 | **the r26 gate polarity** | **INVERTED in the record** — lane A is zero-forced whenever `gp-0x6b5e != 0`, not only under the rare `gp-0x671a >= 5`. Live today only because `gp-0x6bda` sat outside ±384 on **0.0000/75,227** engaged frames. |
| 13 | **tp off-by-0x1000, SIXTH recurrence** | `TRACE-2026-08-10-lkas-command-visibility.md` §5's rate-lane cals are `0xC6xxx`, not `0xC7xxx`. Anchored via `0xC6446` = 512 = Lever B's own cell. |

---

## 19. REPO AND TOOLING FIXES
- 🛑 **The whole extractor family was DEAD** — `ModuleNotFoundError: _grind2_lib`, because the
  2026-08-26 reorg moved a module into `lib/` while the `PATH BOOTSTRAP` block stops at the **first**
  `.pkgroot`. **Fixed in 729 files**: it now walks every `.pkgroot` root in the repo, nearest first.
- **`BUILD-LINEAGE-PART1-LEVER-INDEX.md` was 10 builds stale** ("current through V97"). **V101–V108 rows
  added**, 168,811 → 192,780 B, all 30 addresses grep-tested, 76 rows checked for table integrity.
- **`cs_v` / `v_rear` / `ws_*` are m/s, not km/h**, and `extract_ra6.py:derive()` mislabels them.
- ⚠ **`0000001b` exists TWICE on disk with different hashes.** Key every cache on `counter--hash`.
- **`docs/DRIVE-CARD-NEXT.md`** written — the manoeuvres that close six stalled analyses.

---

## 20. OPEN ITEMS ADDED OR CHANGED IN PART 2

| # | item | what closes it |
|---|---|---|
| A | 🛑 **D's sign above 16 Hz** — gates V110 | On-car `Re(Z)` at 18–22 and 26–31 Hz. **`rezband` was testing whether existing three-drive `Re(Z)` data can anchor the plant phase across the band; result not in this handoff.** |
| B | **`0xC61C0`/`C2`/`C4` blanked to `0xFFFF` at V36** — 12 readers, 0 writers, **undocumented for 72 builds** | **`blanked` was tracing it; result not in this handoff.** |
| C | **`0xC6384` binding state** | Live telemetry of `gp-0x37e8[]`/`gp-0x6444` at 25–40 km/h, or the full ROM→Branch-B→table-build simulation. |
| D | **The mechanical half of `M(jω)`** — until it exists, **no lane `Re(Z)` in this kit is in bar-torque units** | A bench measurement, or motor Kt + gear ratio + bar stiffness from spec. |
| E | **`a` = `gp-0x69a4` live value** — r26's gain spans **−431…−5177** on it | A rung on `gp-0x69a4`, or on `gp-0x6adc` (free mirror, 0 readers). |
| F | **Which taper arm is live** (`gp-0x6803`) — the arms differ 2× at raw 2048 | One cave rung on `gp-0x6803`. |
| G | **Ghidra script bundle** — `BundleHost_ENABLE[9]` is the only `false` of 23 | Tick `$USER_HOME/ghidra_scripts` in Script Manager → Manage Script Directories. |
| H | **`gp-0x6ac2` at `\|rate\| >= 1100`** — never probed, in the operator's own hard-turn regime | One cave rung, whenever the cave next opens. |
| I | **openpilot's lateral tuning** — the ONLY route to the visible oscillation | **Operator's decision.** `feedback-no-openpilot-side-modifications` is standing. |

---

## 21. THE THREE CANDIDATES, IN FLIGHT ORDER

| build | `.rwd` sha256 | adds | fly |
|---|---|---|---|
| **V108** | `4fbfda0d76af2f1b592bd9e510cd926dbfabb6a02b7a25730e7018f07cf4c4d1` | notch → Honda · damper de-railed at the Y1 knot · `0xC40BC` → 600 · `sar 5` | **first** |
| **V109** | `83047f0fd3b5b656720487d5f70755c3b2506c4293097b403abf003e972087c1` | **+ α2 band-limit** — 61–300 Hz cut 27–40 %, 0 % at manoeuvre frequencies | first, if one drive not two |
| **V110** | `becaab6d7ecce18df1bcba0112189d994fc048dad3720ea6e96bbf934a33410c` | **+ Kd halved** — 5–26 % Q cut on the ratchet | **only after a grinding baseline** — see §15 |

🛑 **NOTHING HAS BEEN FLASHED. NO CAN, NO UDS, NO SSH AT ANY POINT.**
