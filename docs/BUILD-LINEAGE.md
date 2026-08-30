# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

> 🛑🛑 **THIS LINEAGE STOPS AT V121. V122–V178 HAVE NO ROWS — INCLUDING THE FLYING BUILD.**
> Discovered 2026-08-29. **`grep V122` in these files returns nothing**, so the standing rule
> *"grep the lineage before naming any address"* **silently passes** for every cell V122
> moved. V122's undocumented delta: `0xC40D2` 204→1020 · `0xC40BC` 600→3000 · `0xC40DC`
> 22→8. **THAT IS ALL** — twelve bytes, five payload runs. 🛑 The `0xC6598`… float block is
> **NOT V122's**: it is a V31/V38 **authority ladder** (1.0→2.0→4.0→5.0) and must NOT be
> reverted — doing so would cut LKAS authority ~5x. V178 tried and is RETRACTED.
> ✅ **PARTIALLY BACKFILLED 2026-08-29 — see `docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md`**,
> a GENERATED address index covering **V122–V210 (71 images, 44 cells)**. It carries no
> reasoning — that is in `STATE.md` and the handoffs — but it restores the one thing that
> matters: **`grep <address>` now tells you which build moved a cell.**
> **Still diff against the STOCK IMAGE for anything load-bearing.**
> ✅ **2026-08-29: 8 of its 44 rows sit on ODD addresses** — the HIGH BYTE of an even u16
> cell, because e.g. 1024→512 moves one byte. A grep on the CELL address used to miss
> them. Each odd row now carries the even address as a searchable alias, so
> `grep 0xC63AE`, `grep 0xC63A6` and `grep 0xC61B2` all resolve.
> Details and the builds that revert them: `docs/STATE.md`.


**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

🛑 **THIS FILE IS SPLIT ACROSS THREE FILES — READ THE POINTER TABLE BEFORE CONCLUDING SOMETHING IS ABSENT.**
Every mandatory-read file must stay under the **256 KB `Read` cap**; past it a file loads with its tail
**SILENTLY TRUNCATED and no warning**. This file is the **ENTRY POINT** — start here.

| file | contents |
|---|---|
| **`docs/BUILD-LINEAGE.md`** (this file) | RULES 3–13 · struck hypotheses and **struck LEVERS killed on evidence** · ledger corrections · the current-build block · **Part 2 — code caves / GATE 1 / GATE 2** · Part 3 — per-build byte delta · Part 4 — flash status at a glance |
| [`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`](BUILD-LINEAGE-PART1-LEVER-INDEX.md) | **Part 1 — the lever index, by address.** 🛑 **Grep it by address before proposing any calibration edit.** |
| [`docs/BUILD-LINEAGE-CATCHUP-V76-V100.md`](BUILD-LINEAGE-CATCHUP-V76-V100.md) | the **per-build CATCH-UP ledger, V76 → V100** — 24 rows plus the per-build artifact / route / hash notes |

⚠ **`Part 2` means the code-cave section IN THIS FILE**, which has not moved. The catch-up file is
deliberately not numbered `PART2` so the two can never be confused.

---

## ✅ V199–V210 — BUILT 2026-08-29, NONE FLASHED. The notch rebuilt twice and the census closed.

🛑 **Grep these before proposing any of their cells.** Full narrative:
`docs/handoffs/2026-08/HANDOFF-2026-08-29-census-closed-notch-recentred.md`.
Per-cell history: `docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md` (44 cells / 71 builds).

| build | base | delta | status |
|---|---|---|---|
| **V199** | V196 | biquad **poles BELOW zeros** — zeros 19.75, poles 17.45, r 0.9675. Fixes the trap V188–V198 all carried (`max`max|H|`` 1.35–1.72 vs the 1.0 bar) | BUILT, not flashed. `c86646ab…` |
| V200/V201 | V199 | probes (r24 lane; pedestal) | SUPERSEDED |
| **V202** | V199 | poles dropped to 15.25 — wider shoulder | SUPERSEDED by V208 |
| V203–V205 | V202 | probes (pedestal; `gp-0x6b4e`; `gp-0x6b70`) | SUPERSEDED — V205's question answered from cache |
| **V206** | V202 | **`0xC63AE` 1024⇒512** — halves the soft relay's small-signal gain | SUPERSEDED by V210 (old notch base) |
| V207 | V202 | probe on `gp-0x6acc` | 🛑 **RETIRED BEFORE FLYING** — its question closed analytically |
| **V208** | V202 | **notch re-centred 19.75 → 20.50 Hz**, poles 15.50, r 0.9575, on the measured per-episode peak distribution | BUILT. `e27b4fcc…` |
| **V209** | V208 | + the 427 probe on `gp-0x6b4e` | BUILT. `984dfe55…` ⭐ the one to fly |
| **V210** | V208 | `0xC63AE` 1024⇒512 on the current notch | BUILT. `ab49ca76…` |

**Cells touched:** `0xC60A8`/`AC`/`B0`/`B4` (the biquad, three times) · `0xC63AE` (V206/V210) ·
`0x55DF2`/`0x55E10` (the 427 probe, repointed five times). Everything else carried from V196.

🛑 **CLOSED THIS SESSION — do not re-propose:** the saturation census (no clamp saturates and no
gate fires anywhere in the command→motor path or the delivery chain) · `gp-0x6b70` clip duty
(1 frame / 72,916) · the governor clip (0.000000 / 49,021) · the `gp-0x6acc` zero-reject (bounded
870 counts under its window) · LKAS authority (`0xC6CD0` is the ONLY firmware lever).

## 🛑 V111 / V109 / V110 — BUILT, **NONE FLASHED**. 2026-08-27.

### ⚠⚠ V109 AND V111 **DRIVE IDENTICALLY** — THE CHOICE IS THE INSTRUMENT, NOT THE FIX
Verified from the images: `0xC40DC` (α2) = **14 on both**, `0xC40BC` knee 600, `0xC6CD0` gain 5346,
`0xD7A5C` `gp-0x6b26` row, `0xC60A8` biquad — **every dynamics cell byte-identical.**
**V111 = V109 + 3 telemetry bytes.** ⚠ An earlier recommendation of *"V109 first, then V111"* was
**WRONG** and is corrected here.
```
  V108 -> V109 :  0xC40DC  16 -> 0e                          1 payload byte  + CRC
  V109 -> V111 :  0x55DF2  d493 -> 4495 ; 0x55E10  a5 -> a3   3 payload bytes + CRC
```

| build | edit | image / .rwd | verdict |
|---|---|---|---|
| **V111** | 427 tap `gp-0x6c2c` → **`gp-0x6abc`** (the relay input), sar 5 → 3 | `9c4865cf…` / `221d99c6…` | ⭐ **RECOMMENDED NEXT.** 36/36. **No cave edit** ⇒ outside the bricking class |
| **V109** | `0xC40DC` α2 22 → 14 (band-limit) | `e9eb51fc…` / `83047f0f…` | 30/30. Same dynamics as V111; keeps the `gp-0x6c2c` tap for the Y-row solve |
| **V110** | `0xC6AE6` 2048 → 1024 | `3de48a49…` / `becaab6d…` | 🛑 **PARKED — DO NOT FLASH.** Killed twice |
| **V121** | `0xC40BC` 1800→3000 + `0xC40D2` 612→1020 | `ce565da7…` / `8c154edb…` | ✅ **BUILT, UNFLASHED.** The **maximal gain-matched knee**: small-signal gain held EXACTLY at V112's 0.0039844 while the relay saturates 31.8→53.1 deg/s. 🛑 **Dose set by a hard ceiling** — `K1/1024` is the friction's max as a fraction of `|model|`, so `K1 >= 1024` inverts the residual's sign; V121 sits at **0.996**, and knee 4000 (K1 1360 = 1.328) is **REFUSED**. **V116 is a half-step** — its 42.4 deg/s is still below the oscillation's own median p95 rate of 47.06, so its relay is still a signum where the symptom lives. Feel is **bit-identical to V112 ≤ 31.8 deg/s**, then 1.571×/1.667× more friction ⇒ **more assist** at high rate. 4 payload bytes, cal-only, alpha2 held. ⚠ manual feel changes >31.8 deg/s; does NOT address grind #1. **Falsifier:** harmonic ratio should drop below V112's 1.213. |

### WHY V111 IS RECOMMENDED OVER V109 FOR A SINGLE DRIVE
**GATE 2 on the relay knee** shows a knee raise only bites **below ~200–400 counts** of
`|gp-0x6abc|` — describing-function ratio **0.96–0.99 above ~400**, i.e. it does essentially nothing
there. **That amplitude decides whether the ratchet lever exists at all**, and whether the priced
**~1.28:1 trade** is even on the table. ⊕ Both builds deliver the identical α2 test on the low-speed
grinding, so **nothing about the fix is given up.** ⚠ What is given up: the `gp-0x6c2c` channel goes
dark, so the `gp-0x6b26` Y-row solve waits for another drive.

### 🛑 WHY V110 IS PARKED — TWO INDEPENDENT KILLS
1. **THE SIGN.** `cos(argZ + argH_D)` = **−0.802 at 7.79 Hz but +0.894 at 20 Hz** ⇒ D pumps at the
   ratchet and **DAMPS at 18–31 Hz**, the operator's own grinding bands. Replicated on three drives
   (628 windows / 74 episodes / 2145 s); 18–22 needs a channel skew ≥ **+8.6 ms** to flip and 26–31
   needs ≤ **−5.9 ms** — **opposite directions, so no single skew saves it.** Cost ≈ **2.96×** at
   18–22 and **3.92×** at 26–31 against a +0.039 ratchet benefit.
2. **IT IS NOT "Kd 2048→1024".** `0xC6AE6` is **one knot of a FLAT four-knot LERP** —
   X = (50, 400, 1500, 3000) @ `0xC6ADE/E0/E2/E4`, Y = (Y0..Y3) @ `0xC6AE6/E8/EA/EC`, **all 2048 in
   stock**. Y0 acts alone only below axis 50 and is **never read at or above 400**. ⭐ **On a flat
   table a one-knot edit is never a gain change** — it converts a constant into a rate-dependent
   nonlinearity. 🛑 **The Kd lever is CLOSED entirely, not just this build** — the correct
   four-knot form is exactly what makes kill #1's cost real. **Do not rebuild it properly.**
⚠ **`Ki` (`0xC6B12/14/16/18`, flat 98) is the SAME SHAPE, and line 397 of this file floats Ki as a
candidate.** Read all four knots before proposing it. **`Kp` (`0xC6B26/28/2A/2C`) is SHAPED**
(256/256/225/153) — the flat-table argument does **not** carry to it.

## ✅ V108 — **FLEW 2026-08-27. HIGH SPEED FIXED; LOW SPEED UNCHANGED. THE PREDICTION LANDED.** (routes `1b` / `1e`, 988.6 s engaged on `1e`, fault-free)

🛑 **OPERATOR REPORT (no rlogs — his words are the ENTIRE readout, and the PRIMARY one):**
*"High speed behavior is good overall... no oscillations even on hard turns at speed. **So that has been
fixed.**"* · *"Twenty miles an hour and above, generally, **this is the best that it has ever been in
that regime at six x**."* · *"Low speed below ten miles an hour, **grinding is still there**... it seems
like it is made up of **TWO MODES**, one maybe around a hundred hertz, and another **significantly
higher in pitch**."* · *"At low speed, the **maximum steering angular velocity is still limited**."* ·
*"Around ten to fifteen, maybe ten to twenty, there is **oscillation and grinding**."* · *"Around sixty
to sixty five... a whole vehicle vibration... **I am not really completely sure this is our firmware's
fault. It might have just been the road because it is not consistent.**"*

⭐⭐ **THE RAIL-DUTY PREDICTION HELD, ACROSS A BUILD CHANGE:**

**Where the duty fell he reports it fixed; where it stayed highest he still hears it; where the
calibration was deliberately left byte-identical, nothing changed.** ⚠ EVIDENCE for the duties and the
report; **BELIEF that the mapping is causal** -- one build, no rlogs, no matched control.
⇒ **The residual is the SAME defect UNDER-DOSED, not a new one**, and his "two modes, ~100 Hz and
higher" is exactly what **V109's alpha2** cuts (-34 % at 100 Hz, -39 % at 200 Hz, 0 % at manoeuvre
frequencies). ⇒ **V109 IS THE NEXT BUILD.**
⚠ **The 60-65 mph vibration is probably NOT ours**: rail duty there is **<=0.03 %** and that regime is
**byte-identical between V107 and V108**, so a firmware change cannot explain a change there. **His own
instinct was right.**

**CLASS: SUBTRACTIVE. The first build in this arc to REMOVE kit-added loop gain rather than add more,
and the first ever designed against the 50–500 Hz band.** Four cal edits plus one telemetry shift
immediate. **No cave change — the cave is byte-identical to V107.**

| artifact | sha256 |
|---|---|
| `_v108_V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5_plain_image.bin` | `7a9577dd181a235845e87e592fbd1a191957674aef7b0f17caac6907c114a9e4` |
| `39990-TVA,A160-V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5-0x13000-0x100000.rwd` | `4fbfda0d76af2f1b592bd9e510cd926dbfabb6a02b7a25730e7018f07cf4c4d1` |

builder `analysis-2020accord/builds/v108_plus/build_v108_tva.py`, **54/54 assertions**, BASE = V107.
**20 payload + 11 CRC = 31 bytes vs V107 in 11 runs. ZERO unattributed. Three CRC trailers
(`0x0C4FFC`, `0x0C6FFC`, `0x0D7FFC`). Reproduced bit-for-bit on four separate runs.**
Exactly ONE V108 `.rwd` on disk.

| edit | address | V107 → V108 | what it does |
|---|---|---|---|
| **E1** | `0xC60A8`–`B7` | V105's 25.5 Hz notch → **Honda's own 16 bytes** | removes **+14.0 dB at 61.1 Hz** and restores Honda's 55.2 Hz null. **Arm KEPT** — unarmed is a BYPASS (`H ≡ 1`), worse than Honda at every frequency |
| **E2** | `0xD7A5C`/`0xD7A6C` | `(−29490,−24000,−16000)` → `(−29490,−17202,−16000)` | V106's Y0+Y1 exactly, V107's Y2 kept. De-rails at the Y1 knot; ≥65 km/h costs nothing measurable |
| **E4** | `0xC40BC` | 300 → **600 (Honda)** | the V99 Coulomb ramp normaliser — retracted as a fix by its own session **before it flew** |
| **E5** | `0x55E10` | `sar 3` → `sar 5` | the 427 tap was sized against a **5× arithmetic error** and censored its own answer |
| ~~E3~~ | `0xC61BE` | **PULLED** — byte-stock | built at 16384, killed by its own pre-registered null. See below |

**Spec discipline on E1:** the four float32 coefficients are **copied byte-for-byte from
`stock_fw_dump/code.bin` and asserted equal**. No float is ever typed — `feedback-float-spec-must-be-the-formula`
applied in its strongest available form.

### WHY — `gp-0x6b26` IS A 61 Hz BANDPASS AND V107 RAILED IT
`H(f) = 64·H1·(1−z⁻¹)·H2`, EMAs α0 = 37/128 = `cal(0xC643C)`, α2 = 22/64 = `cal(0xC40DC)`, fs = 1000.
**Peak 61.1 Hz, −3 dB span 25.1→153.0 Hz, never below 4.49× to Nyquist; 10.86× at 100 Hz — 40 % MORE
than at the 21.7 Hz mode it was meant to damp.** Measured rail duty `P(|gp-0x6b26| = 511)` on route `1e`:
**32.32 % at 10–25 km/h, 21.27 % at 24–40, 9.69 % engaged overall**, against V107's own predicted
**≤1.05 %** and its rejection of RESHAPE_A at 6.2 % as *"V80 relay territory"*.
🛑 **The safety case could not see it — CAN 427 arrives at 49.8 Hz (Nyquist 24.9) and the lane's entire
−3 dB band is above that.** And the prediction method itself is void: `gp-0x6b26` feeds aggregator →
motor → motor rate → `gp-0x6c2c`, so the **open-loop push-through assumption that the input distribution
is invariant to K is false** — a **32× miss**, reached independently from the code and from the data.

### E3 — BUILT AND PULLED. The pre-registration was written first and honoured.
`0xC61BE` = 15360 is a symmetric saturation at `0x2A13E`..`0x2A15E`, **UPSTREAM of the 6× gain**, so the
LKAS lane's reach is `(clip × cal(0xC6CD0)) >> 15` and has been **81.5 % of its own output clamp on
EVERY build since V14** — which is the long-unexplained mechanism behind *"`0xC61B2`/`0xC61B4` are 0 %
of the effect"*: **they are inert BECAUSE this clip caps the lane 18.5 % below them.** Anchored two
ways: `(15360 × 891) >> 15 = 417` = the separately recorded stock-V9 maximum.
**GATE 1 clean** — 8 accesses image-wide, all loads, zero writers, no lockstep twin, no ASIL monitor, no
`0xC5000` mirror (`0xC51BE` = 220). **NOT in series** with `0xC61BC` (15360), `0xC61B6` (10240) or
`0xC61BA` (10240): those clamp **three parallel branches** whose sum reaches 35,559 = **2.32× the clip**.
**THE NULL:** route `1e`, authority-ramp-complete, 93,356 frames / 924 s, `|e4tq|` p99 = max = 4096 so
the saturation region *is* exercised — p90 achieved `|rate_c|`, low half vs top, episode-bootstrapped:
**10–25 3.89× [2.42,5.48] · 25–40 3.12× [2.22,4.45] · 40–64 2.91× [2.38,3.13] · 64–90 2.62× [2.10,2.62]
· 90–200 2.14× [1.67,2.14].** Still rising where a bound clip would pin it flat, at all five speeds,
every CI excluding 1.0 ⇒ **the clip is IDLE. PULLED.**
⚠ Not proof it can never bind: the clipped quantity carries int32 recursive state (`gp-0x6cf8`,
`gp-0x6dd0`, 4 accesses each, all inside `FUN_00028ea6` or its dead copy, zero external access), so it
is also **not reconstructible from logs.** ⭐ Zero-firmware confirmation exists — **stock UDS DID
`0x48AC` bytes 7–8 = `gp-0x6b38`** (RDBI entry `0xB7864`, handler `0x4E82E`, default session, **no
security access**): a bound clip pins it at **~2481**, and **anything above 2505 falsifies the model.**

### 🛑 RECORD CORRECTIONS MADE THIS SESSION — read these before reusing the cells
- **`0xC64DE` is NOT a "re-engage authority ramp".** It is the **hold count of a sign-flipping square
  wave** (`if counter < cal: counter++ else { counter = 1+(cal>>1); gp-0x6b2c = −gp-0x6b2c }`, 8 live
  read sites in `FUN_00028ea6`, 0 writers, tick = 1 ms settled two ways). V18's 17→27 moved it from
  **29.41 Hz to 18.52 Hz — into grind #1's band.** Burst ≈ 381 ms (`cal(0xC6288)` = 300 pre-delay, ends
  at `cal(0xC628A)` = 408). 🛑 **Its amplitude LERP at `0xC6736` is Y = (0,0,0,0) in stock AND V107, and
  every other writer of `gp-0x6b2c` is a store-zero ⇒ STRUCTURALLY INERT.** ⚠ **It is a latent,
  engagement-triggered 18.5 Hz square-wave torque injector wired into the 6× gain path, four halfwords
  from being live, eight bytes from `0xC674E` which this kit edits.** `BUILD-LINEAGE-PART1-LEVER-INDEX.md:76`
  carries the wrong label.
- **The 11-slot lane mixer `FUN_00026c80` is FULLY TRACED, and its delivery-bound output is DEAD.**
  Decoded 2026-08-29. `FUN_00025c32` is the slot writer: a 16-byte request record (slot, type 0-5,
  four values, three weights) with **exactly ten callers**, one per accumulated slot. Value A ->
  `gp-0x6298` -> `gp-0x3d80` -> **`gp-0x6b4a`**, which has 8 readers **including the delivery chain
  `FUN_00042af8`** (`0x42BF6`). Value B -> `gp-0x6b4c`; value D -> **`gp-0x6bfa`**, the observer's bias
  term (provenance previously open; **slot 6 / `FUN_0003aff4` is its only writer**).
  🛑 **NINE OF THE TEN SLOTS STORE VALUE A AS LITERAL `r0`.** The tenth (slot 2, `FUN_0003405a`)
  carries `gp-0x6b76` = `-clamp(gp-0x4f60, +-cal(0xC616C))`, and **`0xC616C` = 0** -> 0 when valid,
  `0x7FFF` when not, and `0x7FFF` fails slot 2's own `<=0x5000` gate and is rejected to 0.
  ⇒ **`gp-0x3d80` == `gp-0x3d84` == 0, so `gp-0x6b4a` == 0.** The mixer reaches delivery with nothing.
  ⊕ **This also RETRACTS an earlier claim in this same entry** (written hours before, same session):
  that zeroing one `0xC4118` arm byte would arm the mixer's rate limiter (`0xC6194`=3/tick, 256-ct
  residual clip) in the live delivery path. **It cannot** -- the limiter's input is the value-A sum on
  the other side of the arm gate, and that is zero too. The lesson is the reusable part: **the plumbing
  was traced correctly and the conclusion was still wrong, because the PAYLOADS were never checked.**
  The close-out assertion on `0xC4118`/`0xC4124` is kept as a *leave-Honda's-wiring-alone* guard with
  its reason corrected; **`0xC616C` = 0 is the real interlock** and is now asserted too (198 checks).
- **A dormant Honda float PI controller sits at `0xC60B8`-`0xC60D8`, ADJACENT TO THE BIQUAD WE EDIT.**
  `FUN_00033d10` writes both slot-2 payloads via two float PI lanes: lane-1 D/I/P = `0xC60BC`/`0xC60C4`/
  `0xC60C8` = 0/0/**14**, I clamp `0xC60C0`=1; lane-2 D/I/P = `0xC60CC`/`0xC60D4`/`0xC60D8` =
  0/**0.002**/**0.03**, I clamp `0xC60D0`=5, pre-filter `0xC60B8`=0.01. **Byte-stock on all 152
  flashable builds** (checked). The whole controller is gated out **three independent ways**: lane 1 by
  `0xC649D`=0, lane 2's output `gp-0x6b78` **discarded by `0xC4124[2]`=5**, and the torque term by
  `0xC616C`=0. ⚠ **The notch builders write four floats at `0xC60A8`-`0xC60B4`; one float of offset
  error lands in this block.** ⚠ **NOT a lever yet** -- `gp-0x6b4a`'s sign/scaling in `FUN_00042af8` is
  untraced and the PI inputs (`gp-0x6bf0`, `gp-0x6be0`, `gp-0x6a58`) are unidentified; raising
  `0xC616C` admits a **driver-torque**-proportional term, which on the wrong sign is added friction.
  Re-runnable: `analysis-2020accord/studies/mixer/mixer_fun26c80_decoded.py`.
- **`0xC520C`/`0xC5224` STRUCK as a lever.** Index formula fully reconstructed (`gp-0x6ac0` = |filtered
  motor rate|, scale **4.7121 ct per column °/s** externally anchored via Honda's own 0x14A rate field at
  r ≥ 0.985; X = [1050,1700,2500,3700,4100] = [223,361,530,785,870] col °/s; Y = [5325,3584,2406,1587,512]
  then `min(·, cal(0xC6202) = 4762)`). **Measured on route `a6`: peak 1462 ct, 0.11 % of engaged time
  above X[0], NEVER above X[1]; `gp-0x4f64` sits at its max 4762 for 99.9 %+ of engaged time.** That
  reconciles `b6` = 0.000000 and explains V41's null. **A documented mechanism, not a lever.**
- **`0xC61BC` = 15360, `0xC61B6` = 10240, `0xC61BA` = 10240** — three parallel branch clamps in
  `FUN_00028ea6`, 0 writers, byte-stock V99→V107, **never named anywhere in this lineage until now.**
- **The `0xE4`/`0xE5` taper "skip" is NOT a bug** — `gp-0x674e` is a boot-time variant selector whose
  reachable set is {0,1,3,4,6,7,8,9}, and the skipped records are **exactly its complement.** Our car is
  **TVCA4 → slot 11 → selector 7 → `0xE51A8`, and it IS raised.** ⊕ The V38 handoff names the wrong slot
  for our car; **V74's naming is correct** (`LEDGER-V38-TO-V84.md:509` records the dispute unresolved —
  it is resolved).
- **V102 is marked "NOT FLASHED" at line 248 of this file, but `0xC6CD0` = 5346 is demonstrably on the
  car.** The twelfth stale flight-status row.
- **`gp-0x4f62`'s "peaks at 125 Hz"** does not follow from the code — `FUN_0007e74a` uses an 8-slot ring
  buffer with a **variable, table-looked-up elapsed-tick counter** and is called **conditionally**.
  `D = cal(0xC6C42) = 4` is byte-confirmed; the **effective delay is unresolved. Do not reuse 125 Hz.**

### V109's LEVER, ALREADY PRICED — `0xC40DC` (α2), VIRGIN ON ALL 102 IMAGES
At K2 = 14 the delivered response is **flat across 18–30 Hz (1.024→0.966) and cuts 20–35 % over
61–300 Hz** — it de-rails **without giving back mode-band damping**, which lowering Y cannot do. GATE 1
is the cleanest possible (**exactly ONE gp/tp access image-wide**, zero writers). **HELD OUT of V108**:
the phase sector-entry moves DOWN (74.1 → 54.0 Hz), `gp-0x6c2c` fans out to **three** consumers of which
two are unverified against a *reshaped* signal, and the only duty-prediction method available was just
measured 32× wrong. 🛑🛑 **It must ship WITH the notch revert or not at all** — across 54–74.5 Hz V105's
coefficients leave the base-assist lane a geometric-mean **5.15× (+14.2 dB)** louder than Honda's.
⊕ Take it **uncompensated**: `29490 × 1/0.90 = 32,767` against an int16 floor of 32,768, so a **−10 % α2
cut is the LAST one Y[0] can compensate.**

---

## ⚠ V107 — FLEW as routes `1b` / `1e` (2026-08-26), fault-free. **SUPERSEDED BY V108 BELOW** (route `a6`, 1,224.0 s engaged, fault-free)

**CLASS: the SPEED SCHEDULE of `gp-0x6b26` — the second axis of the cell V106 doses, because the
uniform axis is arithmetically EXHAUSTED.** Plus a telemetry re-aim. Cal + one instruction
displacement + one shift immediate. **No cave change.**

| artifact | sha256 |
|---|---|
| `_v107_V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3_plain_image.bin` | `c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45` |
| `39990-TVA,A160-V107-V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3-0x13000-0x100000.rwd` | `78eae7da20a87f1a95295eca11da0d08f4cf2b3b823785594cde4be93a7b24ff` |

builder `analysis-2020accord/builds/v80_v107/build_v107_tva.py`, **55/55 assertions**, BASE = V106.
**10 payload + 8 CRC = 18 bytes vs V106. ZERO unattributed vs stock. Two CRC trailers
(`0x0C4FFC`, `0x0D7FFC`).** Exactly ONE V107 `.rwd` on disk.

```
E1  0xD7A5C / 0xD7A6C  modes 26/27 Y   (-29490,-17202,-5898) -> (-29490,-24000,-16000)
                       X untouched at (0,1280,5760) counts = (0,20,90) km/h
E2  0x55DF2  7a 94 -> d4 93    427 tap source: gp-0x6b86 -> gp-0x6c2c
    0x55E10  a4 -> a3          427 tap scaler: sar 4,r6 -> sar 3,r6
```

### WHY — the uniform axis is int16-EXHAUSTED
Y is signed int16; **Y[0] stock = −9830 ⇒ k_max = 32768/9830 = 3.3335**, and V106 at ×3.0 sits at
**90.00 %** of the floor. ×4/×5/×6 stock are **OVERFLOW**, not merely risky. Room to the floor:
Y[0] ×1.11 · Y[1] ×1.90 · **Y[2] ×5.56** — and Y[2] is the ≥90 km/h knot, which is exactly where
V106's residual line survives (55–70 km/h is measured **at stock**: prominence 1.4 vs 1.6).
Honda's taper delivers **−24,546 at creep but −5,898 at ≥90 km/h — 4.2× weaker where the line is.**

### WHY B AND NOT A — a flat schedule is V80 relay territory
Constant-free duty (measured wire × a ratio of two flash tables), r77 **undamped** = conservative:
`RESHAPE A` → **6.2 %** at 70–90 km/h · `RESHAPE C` → 3.4 % · **`RESHAPE B` → ≤1.05 % everywhere**
(≤0.09 % on a6's own damped α). **B's clamp knee (1963) sits ABOVE r77's undamped 70–90 p99 of
1836.** And **route a6 spent 809 of its 1,224 engaged seconds above 70 km/h** — the band the reshape
hits hardest is the majority of the operator's engaged driving.
🛑 **Highway α is 1.5–1.9× CREEP, not smaller** — "creep is the worst case" is FALSE, and it is why
A's ≥70 cell is worst in every table. **Y[0] is byte-identical**, so creep duty and the relay index
are unchanged BY CONSTRUCTION; only 4 bytes per row change.

### WHY THE TAP MOVED
It watched `gp-0x6b86`, the biquad lane — a filter this session decided not to build on. **No route
has ever measured `gp-0x6c2c` above 90 km/h near this dose** (r77: 1.1 s; r78: 99.8 s at ×1.5), and
every duty number above rests on it. ⭐ `|gp-0x6b26|` is bounded at ±511 **by construction**, so it
censors exactly the information needed — it can say *that* you clamped, never *how far past*.
`sar 3` = LSB 8, full scale 8184 vs a measured max of 5,286, **zero clipping** (`sar 2` clips 1.18 %
of the p99.9 tail, and the tail is the point).

### UNTOUCHED
`0xC407E` = 511 · `0xC6CD0` = 5346 (the 6× gain) · both MANUAL mode records · the X breakpoints ·
the biquad · **the whole cave, so `b5` still means what route a6 measured it against** · Lever B ·
`0xC640A`/`0xC640C` — the `gp-0x671a` fallback branch, **proven dead** (it needs five crossings of
`|gp-0x6c2c| > 12,800` against a corpus max of 5,320) and **NOT virgin: V93/V94 cut it ×0.75 and V94
flew as route `7d`, the drive the operator aborted as "not safe to drive."**

Narrative: `docs/handoffs/2026-08/HANDOFF-2026-08-23-v107-the-schedule-is-the-lever.md`.

---

## ⚠ V106 — **FLOWN as route `a6`. SUPERSEDED as the candidate by V107.** (route `a5`, wire-verified).

| artifact | SHA256 |
|---|---|
| `_v106_V105BASE-GP6B26.X3.0.D7A5C-D7A6C_plain_image.bin` | `78528aa35b9ea2fa1ea990b2c8d41c7adc784fc17f0b481d66ddcfd3667cb65a` |
| `39990-TVA,A160-V106-V105BASE-GP6B26.X3.0.D7A5C-D7A6C-0x13000-0x100000.rwd` | `e5ac6927a112a0cdf944971aebf7aa14efe6ad8597e17835bbc62d1589bfecbc` |

**Builder** `analysis-2020accord/builds/v80_v107/build_v106_tva.py`, **50/50 assertions**, reproduces bit-for-bit.
**16 bytes / 3 runs vs V105** (12 payload + 4 CRC), **zero unattributed**. **ONE CRC trailer, `0xD7FFC`.**

```
0xD7A5C  mode 26 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)
0xD7A6C  mode 27 (ENGAGED) Y[0..2]   (-14745,-8601,-2949) -> (-29490,-17202,-5898)
```
= **×3.0 of Honda's stock `(-9830,-5734,-1966)`**, computed from it by an integer multiple, never typed
as hex. `gp-0x6b26 = −K(speed)·angular_acceleration`, summed **unweighted** into `FUN_0003aa2c`.

**CLASS: DAMPING.** The first build since V38 to attack the mode by adding dissipation rather than by
reducing a level or reshaping a filter. The arc: V38–V52 authority/filters/poles/caves · V53–V61 probes
and lane mutes · V62–V73 the rate lane · V74–V83a the base-assist damper (**structurally ZERO in the
operator's window** — `FactorC` dead below 35 km/h, `FactorE` below 12.7 °/s) · V84 damper reverted ·
V85–V99 observer/plant probes · V100–V103 the gain ladder + arming the biquad · V104 `c4` flat gain
(FLOWN, NULL) · V105 filter SHAPE (FLOWN — **relocated the mode, band power conserved**) · **V106 the
first delivered damping into 18–28 Hz at low speed.**

**WHY:** the only lever with a **signed on-car precedent pointing this way** — V93/V94 LOWERED it and the
operator aborted the drive as unsafe. The RAISE direction was never tested at 18–28 Hz; the "closed both
directions" verdict rested on a **dose-VERIFICATION** check at 6–9 Hz. **FALSIFIED ≠ INERT ≠ UNTESTED.**
Reaches **both** bands (gain **1.478 @ 7.79 Hz**, **3.706 @ 21.73 Hz**), and 🛑 **`H(f=0) = 0` EXACTLY**
⇒ **cannot rate-limit a held 6× command at any multiplier.**

⭐ **IT PROVES ITS OWN PREMISE — RULE 7 closed at zero cost.** The carried cave rung
**`b5` = ( |gp-0x6ae2| ≥ |gp-0x6b26| )** — operand B at `0xC4B70` = `da94` = `-0x6b26`, **the exact cell
dosed**. Engaged duty must collapse from its **0.4019** baseline if the car reads modes 26/27 engaged;
unchanged confirms the V91/V92 mode-record suspicion. **MANUAL is the built-in control.**

🛑 **26/27 ONLY — the family has FOUR members.** `builds/v80_v107/build_v100_tva.py`'s `DOSE_FAMILY_Y` lists **three**
(`builds/v80_v107/build_v105_tva.py` already had four). Mode 24 (`0xD6A6C`) is **MANUAL** ⇒ dosing it is inert for an
engagement-conditional symptom and changes manual feel instead. Mode 25 (`0xD7A4C`) has an **unconfirmed
role** ⇒ the V69/V70 trap class. **Both left at Honda's stock.**

🛑 **`0xC407E` NOT TOUCHED, still 511** — one count under its own 512 monitor trip, so the RULE-11
interlock is **untrippable at any multiplier, by construction, not by care.** (V73 raised a *different*
cell's clamp past its trip; **V74 and V75 both hard-faulted mid-drive.**)

**Drive card — nine numbered questions:** `docs/handoffs/2026-08/HANDOFF-2026-08-22-v106-the-damper-and-the-one-mode.md` §5.

---

## V105 — **FLOWN as route `a5`** (wire-verified, 3 legs). Grinding and ratcheting both still present.

| artifact | SHA256 |
|---|---|
| `_v105_…NOTCH25.5HZ…_plain_image.bin` | `2666a000415a29fef98ac9cd6c183536269c3e61a61fc822c17586f2adde7e00` |
| `39990-TVA,A160-V105-…NOTCH25.5HZ…-0x13000-0x100000.rwd` | `5592f7ca52d07247152e5930c579b6ba35e2f5fa5a3adcafcb08b95fff6c89a8` |

**24 bytes / 8 runs vs V104** (16 payload + 8 CRC), **zero unattributed**. 165/165 assertions, 3 runs to
identical SHA256, both SHAs hard-asserted in `analysis-2020accord/builds/v80_v107/build_v105_tva.py`.
⚠ A superseded 26.0 Hz cut exists as `SUPERSEDED-DO-NOT-FLASH-NOTCH26HZ-…_plain_image.bin`
(`98f94e7e…44de52db`); **its `.rwd` was DELETED** (`4ee8ea11…d5a6a6fb`). **Exactly one flashable V105
`.rwd` on disk.**

| addr | V104 → V105 | lever | prior on-car result |
|---|---|---|---|
| `0xC60A8` | `f8c2c4bf` → `56e1f0bf` (`a1` −1.5372 → −1.881877) | **biquad pole angle 42.35 → 22.00 Hz** | **VIRGIN — byte-stock in all 74 built images V38→V104** |
| `0xC60AC` | `7576223f` → `3d0a673f` (`a2` 0.63462 → 0.9025) | **biquad pole radius 0.79663 → 0.95000** | **VIRGIN, same** |
| `0xC60B0` | `0ebef0bf` → `9eb8fcbf` (`b1` −1.8808 → −1.974384) | 🛑 **THE NOTCH CENTRE, 55.23 → 25.50 Hz** | **VIRGIN, same** |
| `0xC60B4` | `fc89c13f` → `b51a4e3f` (`c4` 1.512023 → 0.805095) | overall gain — **FORCED by the unity-DC constraint**, lands 1.5 % from stock 0.817310 | flew as V104 (×1.85). **NULL — dose 1.824× delivered, operator felt nothing** |
| `0xC4B36` · `0xC4B42` | `2695`→`6c94` · `2495`→`9cb0` | **cave `b6` repointed to `\|gp-0x6b94\| ≥ \|gp-0x4f64\|`** — aggregator sum vs governor ceiling, **clip duty on the wire for the first time** | `b6` previously `\|r24\| ≥ \|r26\|`, duty **1.0000 engaged** ⇒ carried no information |

**CARRIED UNCHANGED from V104:** Lever B (`0x3AA96`=`fb`, `0xC6446`=5244) · the 427 dose tap
(`0x55DF2`=`0x7a` → `gp-0x6b86`, `0x55E10`=`0xa4` → `sar 4`) · `0xC6CD0`=5346 (6× LKAS gain) ·
`0xC649B`=1 and the 4-byte arm repoint at `0x35A08/09/12/18` · `b5` at `0xC4B64`/`0xC4B70` **UNTOUCHED**.

### THE FILTER, AS BUILT
```
notch 25.499979 Hz  |z| = 1.000000000 (a TRUE null)    pole 21.999984 Hz  r = 0.949999986  STABLE
H(0) = 0.999999581        max|H| over 0-500 Hz = 0.999999564   <- NEVER reaches unity anywhere
|H|  7.79 0.9863 · 20.0 0.5893 · 21.73 0.4150 · 24.0 0.1601 · 24.9 0.0621
     25.5 2.09e-06 · 26.8 0.1229 · 42.3 0.6801          tau 19.496 ms · 99% ring 89.7 ms
```
**BLAST RADIUS ZERO** — each coefficient cell has **1 reader, 0 writers**, all four inside a 40-byte
window (`0x035A30`–`0x035A58`), and **0 `movea`/`movhi` hits on the imm16s** ⇒ nothing can reach them by
absolute addressing either. **PURE CAL — no cave, no code edit, nothing in this kit's only bricking class.**

### WHY IT IS NOT THE REFUSED NOTCH
`docs/review/GATE2-2026-08-20-notch-sign.md` refused re-centring **at 6–9 Hz**, killed on `Re(u/T)` phase.
**V105 targets 26 Hz — a different band and a different argument.** The 6–9 Hz cost here is
**+2.7–5.1° of lag with magnitude essentially unchanged** (0.9863 vs 0.9829).

### 🛑 TWO TRAPS THAT WOULD HAVE SHIPPED
1. **DC COLLAPSE 4.48×** — moving `b1` to the notch frequency drops the numerator's DC term from 0.11920
   to 0.026628. **`c4` and the poles must be re-solved together or the steering weight changes.**
2. 🛑 **THE HIDDEN ONE:** fixing DC with **poles at the notch angle** (the textbook narrow notch) forces
   `max|H|` to **1.098–1.608** and `|H(42.3)|` to **0.975 vs stock 0.385 = 2.53× WORSE** — because
   `(2−b1)/(2+b1)` = **149.2**. ⚠ **Exactly where V59 measured a MARGINAL parametric pump** (42.19 Hz,
   eps 0.013–0.169 vs threshold 0.147). **Fix: Honda's own poles-BELOW-zeros layout** (stock is poles
   42.3 / zeros 55.2). **Check `max|H|` over 0–500 Hz against stock's 1.0000 before shipping any biquad edit.**

### VERIFICATION — independent, three controls
An independent harness returned **PASS, 0 failures**, with **five transfer-function deltas EXACTLY
`0.00e+00`** (the built floats reproduce the formula bit-for-bit). Control-tested against **V104
(16 correct FAILs)**, the **superseded 26 Hz cut (11 correct FAILs, 0 false positives)** and a
**synthetic-correct build (0 FAILs)**. Ghidra's own decoder independently confirmed both repointed loads
after **anchoring** the cave extract with `image.find(blob)` → `0xC4B34`.

### 🛑 THE FLOAT-CAL SPECIFICATION RULE, LEARNED HERE
**A 6-decimal-place decimal does NOT round-trip a float32.** `a1` needs **8** significant digits and
`b1` needs **9**; `a2`/`c4` survived their rounding **by luck**, which made the failure look selective
and therefore look like an encoding bug. **THE FORMULA IS THE SPECIFICATION**; hex in a message is an
**assertion target, never the source**. `builds/v80_v107/build_v105_tva.py` embeds the formula and **asserts AGAINST**
the lossy encodings.

### DRIVE CARD
**PRIMARY:** 21–28 Hz **IN-BURST LEVEL** (🛑 **not duty — duty saturates at 4×**), engaged, **<16 km/h**,
stratified by steering rate with **15–40 °/s the headline cell**. Reference: V104 on `a4`, same window.
**SECONDARY:** `b6` duty = governor clip fraction. 🛑 **Discard the first ~1 s of each engaged episode** —
the ceiling is scaled by an authority ramp (`cal(0xC6492)`=33 ct/tick ⇒ **993 ms**) active above
`cal(0xC6316)`=640 ct ≈ **10 km/h**. **An early-episode `b6`=0 is uninformative, not headroom.**
**WATCH FOR:** a soft settle at engagement (ring 20 → 90 ms) and anything new at ~42 Hz (1.75×).

---


## 🛑🛑 V104 — ⚠ **FLEW AS ROUTE `a4`; V104 IS ON THE CAR.** (This header previously read "BUILT, NOT FLASHED, V103 IS ON THE CAR" — STALE, corrected 2026-08-22 from telemetry.) **FIXED NOTHING — operator: both symptoms still present.**

| artifact | SHA256 |
|---|---|
| `_v104_…-427.6B86.SAR4_plain_image.bin` | `b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03` |
| `39990-TVA,A160-V104-…-0x13000-0x100000.rwd` | `41e707121cf86d8fc8d8c27f98fa722632858466ebbce952a4adcf7234fd4fa2` |

**16 bytes / 7 runs vs V103** (8 payload + 8 CRC), zero unattributed. **Cave byte-identical to V103
(164 B). No new code cave, no hot-path insertion.** 119/119 assertions, 3 runs identical, SHAs
hard-asserted in `builds/v80_v107/build_v104_tva.py`. Hashes and diff re-verified from disk by the orchestrator.

| addr | V103 → V104 | lever | prior on-car result |
|---|---|---|---|
| `0xC60B4` | `3a3b513f` → `fc89c13f` (0.81731 → 1.51202, **×1.850**) | the dormant biquad's overall gain **`c4`** — a **flat scalar** on the torque-sensor assist lane, **engaged-only** | 🆕 **VIRGIN — byte-stock in all 73 built images V38→V103. Never proposed, priced or killed.** |
| `0x3AA96` · `0xC6446` | `c5`→`fb` · 512→5244 | **LEVER B RESTORED** | **0.40 [0.27, 0.58] on grind #1**; operator on V88: *"the audible grinding is fixed"*. 🛑 **Stock on V101/V102/V103 — a REGRESSION REPAIR, not an experiment.** |
| `0x55DF2` · `0x55E10` | `b4`→`7a` · `a6`→`a4` | CAN 427 → `gp-0x6b86`, `sar 4` | the dose instrument — 10-bit field, 3.20 ct/LSB, sized against the lane's own 2704-ct reachable output |

🛑 **`c4` IS A BROADBAND ×1.85 LANE RAISE, NOT "THE 6–9 Hz LEVER."** At fs = 1000 the null is at
**55.23 Hz**, `|H| < 1` only on **36.8–82.2 Hz**, ratio a **flat 1.8500 everywhere**, `|H| ≥ 1` on
**90.9 %** of the axis.
🛑 **THE DOSE-RESPONSE IS INVERTED — under-dosing is the dangerous end.** k = 1.05 has a corner
**4.26× WORSE**; k = 1.85 has **none of 204,000 corners worse**. On the measured `a` the `Re Z`
crossing is at **k = 1.545**, so **k = 1.35 would not have cleared it.**
✅ **Clip duty at k = 1.85 = 0.000000** — zero frames in 1,704 s across five builds, bound clean to
k ≤ 3.40. **The V80 relay mode is unreachable by this lever.**
⚠ **E5 (a 44 B comparator rung) was built against an explicit ruling, caught in verification, and
REVERTED.** It clobbered `0x14A` byte4 bit 0 = Honda's `gp-0x679a`. **`0x14A` has ZERO free bits.**
The superseded image (`e5f02fec…`) is retained with a `SUPERSEDED-DO-NOT-FLASH-` prefix.

**Pre-registered readouts, retractions and open items:**
`docs/handoffs/2026-08/HANDOFF-2026-08-21-v104-built-c4-boost-and-lever-b.md`.

---


## 🛑🛑 V103 — ⚠ FLEW as route `0x9e`; **V103 IS ON THE CAR.** (header corrected 2026-08-21) V102 flew as route `0x96`.

| build | base | delta | on-car result |
|---|---|---|---|
| **V103** | V102 | 🛑 **THE FIRST BUILD TO ARM A DORMANT HONDA FILTER, AND THE FIRST SINCE V85 WITHOUT A SINGLE-FRAME IDENTITY.** **4 in-place bytes + 1 cave rung. Gain UNCHANGED at 6× (`0xC6CD0` = 5346) — deliberately NOT a gain step.** **PART A — arms Honda's dormant biquad, ENGAGED-ONLY**: `0xC649B` `00`→`01` · `0x35A06` `84 4F E7 98`→`84 4F FB 97` (`ld.bu -0x671a[gp],r9` → `ld.bu -0x6806[gp],r9`, arm source → LKAS engagement flag) · `0x35A12` `EC 49`→`E0 49` (`cmp r12,r9`→`cmp r0,r9`) · `0x35A18` `E9 37 00 00`→`EA 37 00 00` (`setfnc`→`setfne`). The filter is **a NOTCH at 55.23 Hz** (zeros exactly on the unit circle), ζ=0.6497, **DC gain 1.0000** ⇒ −1.25 dB/−30° @21 Hz, −3.01 dB/−45° @30 Hz, **−0.02 dB @3 Hz** ⇒ **structurally cannot limit dθ/dt and adds no LF drag; response monotone ⇒ no new resonance.** **PART B — cave 154→164 B, exactly ONE rung changes**: `b3` forced-0 → **`sign(gp-0x3680) < 0`** (D_state's delivered sign, `ld.w -0x3680[gp],r6` = `24 37 81 c9`); **`b7`/`b6`/`b5`/`b4` all byte-identical to V102.** 🛑 **ALL FOUR GATES PASS**: GATE 1 — `gp-0x3814`/`gp-0x3818` boot to **exactly 0.0f** from the `.data` initialiser at flash `0x89898` (read in stock *and* V102), footprint clean on 5 methods, **and this is NOT claiming RAM from Honda — we change WHEN the path runs, not WHERE its state lives** ⇒ V62/V67 risk class, **no canary needed**; GATE 2 — **`max|H|` ≤ 1.000032 everywhere 0.1–500 Hz ⇒ the filter can only REMOVE loop gain, never add it**; margin improves at every frequency and every q ∈ [0.10, 1.00] (21 Hz: 1.01→2.26 dB at q=1); GATE 3 — the dropout is computed downstream and never feeds the filter state. 🛑🛑 **HONEST MAGNITUDE: ~+50 ct·s/rad at the extreme q=1 against a −488 gap ⇒ ~10 % of the way back; +2 to +13 at realistic q. In `f0` terms 0.06–0.3 Hz against a ~1.0 Hz detection floor. PREDICTED IN ADVANCE TO READ "NO CHANGE" ON ITS OWN PRIMARY ENDPOINT.** Four PASSes mean **safe**, not **sufficient**. ⚠ **`0xC649B` 0→1 ALONE WOULD BE INERT** — the real arm is `gp-0x671a ≥ 5`, **never observed true across 255,292 engaged frames on three builds** (V64/V67/V68). ⚠ **And `0xC64FA` 5→0 is the trap** — it is the SHARED detector CEIL with **18 in-code readers**; the private `cmp` patch at `0x35A12` avoids it, and `0xC64FA` is **asserted FROZEN at 5** to document that. 🛑 **IDENTITY: `b3` must VARY.** Both axes are exhausted (`byte7[7:6]` 4/4 codes; `b3`'s two states spent by V101=1 and V102=0). **A constant `b3` means the build is not V103 or the rung is dead — RUN-INVALIDATING, not a finding.** Expected duties: b7 ≈0.27 (rising 0.148→0.417 with rate) · b6 0.8991 (0.836→0.992) · b5 0.2481 · b4 0.4091. | 🛑 **BUILT, VERIFIED, NOT FLASHED. Operator has DEFERRED the decision.** image `df6104bdf8e4fcb69f3379f5b85fb591e4c64e4c33c16f6f9bf29cc88f48f71d` · rwd `a8e68185ba2b5bb5d1bf7b0f903a397b9c3961594b5e1054cd9bf5bf098e41ed` · builder `analysis-2020accord/builds/v80_v107/build_v103_tva.py`. **ORCHESTRATOR-VERIFIED FROM DISK**: both hashes re-computed · all four Part A edits re-read · nine frozen cells re-read (gain still 5346) · cave contents decoded independently (b5's two comparator operands at `0xC4B62`/`0xC4B6E`, b3's `ld.w` at `0xC4BA8`) · **85/85 assertions · 55 bytes in 13 runs, every one attributed · `[0xC5000,0xC5FFC)` identical · both CRC trailers (`0xC4FFC`, `0xC6FFC`) · bit-for-bit reproducible across two runs · exactly one `.rwd` on disk.** Drive card written and **HELD**: `docs/scoring/DRIVE-CARD-V103.md`. |
| **V102** | V101 | 🛑 **THE FIRST DOWNWARD GAIN STEP IN THE WHOLE POST-V38 ARC.** Three cal edits: **`0xC6CD0` 7128→5346 (8×→6×)**, `0xC61B2` 4096→3072 + `0xC61B4` 4096→3072 (tracking; `5346×512//891 = 3072` **exact**). Cave **154 B / 58 instructions** — **two COMPARATORS**: `b6` = `\|gp-0x6ada\| ≥ \|gp-0x6adc\|` (r24 vs r26 arm), `b5` = `\|gp-0x6ae2\| ≥ \|gp-0x6b26\|` (modelled friction vs inertia); `b4`/`b7` signs; **identity ID3 = 6** (`byte7[7:6]==3 AND b3==0`). 427 repointed `gp-0x6b94`→**`gp-0x6b4c`**, `sar 6` carried. **Lever B stays REMOVED**, **`0xC40D2` HELD at 204** (instrumented, not dosed). **EME audit ALL PASS**, `0xC674E`=5120 > 3072, `0xC407E`=511, CRC 50/50, zero unattributed bytes. image sha256 `61197f8c…dbfe32455`, .rwd `b49e7efa…2308b5cb`. **Dose chosen by the OPERATOR from a measured dose-response curve — do not "improve" it.** | **NOT FLASHED.** |
| **V101** | V99 | **8× LKAS GAIN + LEVER B REMOVED.** Five cal edits: `0xC6CD0` 3564→7128 (8× gain), `0xC61B2` 2048→4096 + `0xC61B4` 2048→4096 (fwd-path clamps tracking), `0x3AA96` 0xFB→0xC5 + `0xC6446` 5244→512 (Lever B reverted to Honda stock). Cave 114 B (−40 B vs V99). 427 repoint carried. `byte7[7:6]=3`. **EME audit PASSED** — all V25–V37 fixes carried, `0xC407E`=511, soft-EME floor 5120>4096. image sha256 `c8cb5c3a…1fcf50a6c7`. | ✅ **FLEW as route `0x95`, 2026-08-19.** Identity duty **1.000000** / 25,551 frames, fault-free, 176.1 s engaged in 3 episodes. 🛑🛑 **THE OPERATOR REPORTED GRINDING/VIBRATION AT ALL SPEEDS, ONLY WHILE LKAS COMMANDS, KILLED BY APPLYING DRIVER TORQUE, RETURNING AND GROWING WHEN HE LETS GO.** The peak **MOVED 20.3 → 23.0 Hz** (three separate 4× routes vs this one) ⇒ **a POLE MOVED**; de-confounded 2×2 vs route `71` gives **gain G = 2.7–3.9× at 22–26 Hz** against a 1.45× placebo floor. `b6` (`\|gp-0x6b4c\| ≥ 4096`) duty **0.000000** ⇒ **no clamp binds.** Aggregator sign reverses **25–37 /s** where V100 reverses 0.7–3.2. |

### 🛑 NINE LEVERS CLOSED 2026-08-20 — grep here before re-proposing any of them
| lever | status | why |
|---|---|---|
| **`0xC6CD0` (the LKAS gain)** | 🛑🛑 **THE MEASURED CAUSE of the ~23 Hz line** | G = **2.7–3.9×** for a 2× step, shape units vs a **1.45×** measured placebo floor, de-confounded against route `71`. Vibration scales **m^1.74**, authority only **m^0.88**. ⚠ **The build ABORTS at 10×** — `0xC674E`=5120 must stay > the tracking clamp ⇒ **structural cap below 10×.** |
| `0xC61B2` / `0xC61B4` | **INERT — 0 % of the effect** | Setpoint LERP-clipped to 15360 **upstream** of the gain ⇒ **81.5 % of rail on every build since V14**; `b6` duty 0.000000 over 17,614 engaged frames with all four positive controls passing. |
| **Lever B** `0x3AA96`/`0xC6446` | **NULL at 22–26 Hz** (0.84–1.30×, inside floor). Its **REMOVAL** is a **~3× win at 6–9 Hz AT CREEP ONLY** (0.45/0.26/0.58), **neutral at 35–65 km/h** | de-confounded 2×2. **Keep it removed.** ⚠ `0xC6446` is **NOT "10×"** — Honda's 512 is inert; **5244 = 2.00 × 2622** (the LERP at grind #1's point) and the ratio drifts elsewhere. |
| **`0xCBE74`** (accel lane) | **INERT at 22–26 AND 6–9 Hz** | Single-variable pair **V90 r77 vs V91 r78**, `k` = 0.86–0.90 vs a 1.45× floor. Replaces the T10-invalid null with a direct in-band measurement. |
| **`0xC40D2`** (K1) | **NULL at both bands, real exposure** | Single-variable pair **V88 r73 vs V89 r75+r76**, 8 cells, 163/270 windows, `imu_vert` control flat. ⊕ **Not** T10-invalid — scored on shape vs a measured floor. |
| **`0xC63AC`** | **Predicted WORSE** | Full-loop Bode sum: the stage's **1.38× HF gain at 21 Hz** beats its phase credit ⇒ `\|L\| = 0.875 × 1.38 = **1.208**` at cal 205, past the edge on magnitude alone. Robust across both anchors and all three attribution fractions; **no dose in a 102–600 sweep lowers predicted Q.** ⚠ Its α **matches `0xC40D0` to the last bit** — a genuine disturbance-observer constraint, not hygiene. |
| **`0xC63AA`** | **Sign is FREQUENCY-DEPENDENT, not fixed** | `d(iVar6)/d(0xC63AA) = −(1/16)·(gp-0x6b4c/1024)` ⇒ its sign **is** `gp-0x6b4c`'s instantaneous sign, the very thing ringing at 8.2 flips/s. ⊕ DC cost is **zero by construction** (the aggregator path is separate and unity-weighted), 1 reader / 0 writers, **virgin** ⇒ still the best *structural* lever, but it needs the **dilution ratio** first. |
| **dead biquad `0xC649B`** | **Guaranteed uninterpretable null** | Two agents independently derived 42.4 Hz / ζ 0.649 / −1.32 dB / −30.15° @21 Hz — **but its forcing input is gated on `gp-0x6b62 ≠ 0`, measured duty 0.0000 over 75,227 engaged frames.** The gate kills it, not the math. |
| **PID `Kd` `0xC6AE6`** | **NOT READY — sign unresolvable at the symptom frequency** | 22–26 Hz **is** the measured Re(Z) crossover, where three drives disagree in *sign*. 🛑 **And it changes MANUAL steering** — `FUN_0003a382` is gated on `gp-0x67fa & 0xc30` (the normal-driving cluster, torque-sensor plausibility), **not** an LKAS flag. ⊕ DC gain exactly 0 at every dose ⇒ legitimate *future* candidate. |
| **V100** | V99 | **ZERO CALIBRATION BYTES. Cave only — AN INSTRUMENT, NOT A FIX.** `0x55DF2` 427 repoint `gp-0x6b70`→`gp-0x6b94` + cave `0xC4B36..0xC4BCD` + `0xC4FFC` CRC = **128 B**. Cave **132 B / 49 instructions / 10.9 % of extent**. Rungs: `b5` = `\|gp-0x6ad6\| ≥ cal 0xC6200`, `b6` = `\|gp-0x4f60 − gp-0x6ad6\| ≥ 10240`, `b7`/`b4` signs, `b3` identity ≡ 1. | ✅ **FLEW, ON THE CAR.** Fault-free, identity duty **1.000000**, 427 unsaturated. **29,999 frames / 249.2 s engaged in 6 episodes — ~4× the best exposure ever.** Engaged p50 **39.6 km/h**, ≥50 km/h **88.4 s**, ≥80 km/h **45.5 s** — the first substantially non-creep engaged drive. 🛑🛑 **`d(b5)` AND `d(b6)` BOTH 0.000000** (all 8 rate bins; CI [0, 0.0186]) with `b4` = 0.6057 **on the same cell** ⇒ **THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND MUST NOT BE RE-PROPOSED.** `0.2565` stands unconditioned. 🛑 Zero cal bytes ⇒ **the control law he drove is V99's, bit for bit.** |

### SIX LEVERS CLOSED THIS SESSION — grep here before re-proposing any of them
| lever | status | why |
|---|---|---|
| `0xC6200` (PID reference clamp) | **MEASURED DEAD** | `d(b5)`=0.000000 over 249.2 s. Also **self-cancelling** as a global edit (clamps term 3 *and* the threshold with one cell). Unchased reader `0x39ff6` now chased = **a motor-phase fault threshold** ⇒ DO-NOT-EDIT stands with a reason. |
| **`0xC4118`** | 🛑🛑 **HARD NEVER-ARM** | The partition byte does **DOUBLE DUTY**: zeroing it to "arm" `0xC6194`'s limiter drives `gp-0x3d88`→0 ⇒ `gp-0x6b4c`→0 ⇒ **LKAS STEERING SILENTLY DEAD while openpilot believes it is steering.** Cal-only, 11 bytes, looks safe. **It is not.** |
| `0xC6194` | **DEAD TWICE** | Input ≡ 0 (partition all-1s); output reaches only `gp-0x6b4a` ≡ 0 (`0xC63CC`=0). ⚠ The recorded kill reason *"output ×0"* was **MISATTRIBUTED — it belongs to `0xC6196`** (`0xC6194`=3, `0xC6196`=0). |
| `0xC63AE` 1024→2048 | **NO-GO** | AC gain **non-monotone, REVERSES** across his amplitude range (0.70× @500 ct → 2.00× @6000). The old *"only candidate above the floor"* row is **WITHDRAWN**. |
| `0xC61B8` / `0xC64A3` | **STRUCTURALLY DEAD** | Enable is `gp-0x6806 == 0`, and **`gp-0x6806` IS THE ENGAGEMENT FLAG** ⇒ **MANUAL ONLY**, vs an engagement-required symptom (83.0 % vs 0.0 %, p = 3.8×10⁻⁴¹). ⚠ It is a **LATCHING KILLSWITCH, not a hysteresis.** |
| `0xC63EC` / `0xC63EE` | **DEAD ON ARITHMETIC** | Command 6–9 Hz = 8.08 % of its own RMS ⇒ a 0.564× band cut moves the whole command **0.223 %** — **39× below V85's not-felt 1.088.** Also **91.1 % of bar 6–9 Hz power is INCOHERENT with the command**, and **the bar LEADS the command by −18.5 ms.** ⭐ Its phase cost was **FREE** (exogenous input, outside the loop). |
| PID **Kp/Ki/Kd** (`0xC6B26`/`0xC6B12`/`0xC6AE6`) | **REFUSED — the SQUEEZE** | Virgin on 95/95 images, RULE-7 clean, but **Kp ×2 = 1.130× (ON the 1.088 not-felt bound); ×4 = 1.720× but 92 % rail duty hands-on.** Kd's sign flips on only **53.4°** of φ_G and −90° is *expected* for a motor/rack-side mode ⇒ **V94 verbatim.** **Ki ≡ Kp's question** (same inequality, same unmeasured AUTH). |
| **speed LERP `0xC6ABA`/`0xC6ACA`** | ⛔ **NOT A LEVER** | **`gp-0x69aa` is NOT vehicle speed** — a Q15 governor derate, MIN-only, **pinned at the top knot** ⇒ `Y[0..6]` inert by operating point. **Third axis misidentification in this record.** |

### ⭐⭐ THE RATE LANE IS CLOSED AT AN OPTIMUM — LEVER B OFF EVERY SHORTLIST, BOTH DIRECTIONS
Read from the images (`0x3AA96` gate · `0xC6444` · `0xC6446`), orchestrator-verified:
```
stock/V62/V65  gate 0xC5 DEAD   512 /  512      net = (5244 + 512a)/(3072 + 3072a)
V67/V68/V88    gate 0xFB ARMED  512 / 5244      1.707 @a=0  ->  0.937 @a=1
V71c           gate 0xFB ARMED 3072 / 5244      1.707 @a=0  ->  1.354 @a=1
V100 (on car)  gate 0xFB ARMED  512 / 5244      = V88
```
🛑 **At `a = 0`, V88 and V71c are ARITHMETICALLY IDENTICAL (both 1.707)** — yet on-car they are the
corpus **extremes** (V88 *"grinding fixed"*; **V71c the worst build ever recorded on all three
symptoms**, ratchet at the corpus record 8,521 ct p-p). ⇒ **`a` is materially non-zero; the r26 arm is
LOAD-BEARING. Proved from images, no drive.**
⇒ 🛑 **ACCOUNT A REFUTED** — *"more derivative feedback ⇒ more damping ⇒ less HF"* predicts the
**higher** dose (V71c) should be **better**; it was dramatically worse. ⚠ Correct
`memory/accord/builds/accord-v88-flew-grinding-fixed-command-intact.md`'s mechanism paragraph: **keep the coupling,
fix the direction.**
⇒ ⭐ **BOTH FLANKS MEASURED**: V61 (below V88) *"made it WORSE"*; V71c (above) worst in corpus.
**"2× ≈ OPTIMUM" now has both sides. V88 is sitting on the optimum.** ✅ `0xC6444`'s falsification
**verified in the safe direction** — V71c had the gate **ARMED**, so *"null by construction"* does not
reach it.

### 🛑 RULE 14 — **GATE 3 MUST ASK WHETHER A LANE HAS A *DROPOUT*, NOT ONLY A CLAMP**
This firmware uses **latching zero-output dropouts** as a design idiom in ≥2 places: the `gp-0x6b30`
sign-latch, and the aggregator's `0x3acc4 cmovc 0x0,r6,r13`, which **DROPS** a lane past ±10240 rather
than clamping it. **A dropout is invisible to every no-clip rule the kit runs.** This is the V80 lesson
(*"'does not clip' and 'is not a relay' are different statements"*) in a new form.

### 🛑 RULE 15 — **AN IMPLAUSIBLE NULL IS A BUG REPORT. SO IS AN IMPLAUSIBLE NON-NULL.**
**Five scan-blindness classes surfaced in one session, every one caught by a DECOMPILE disagreeing
with a scan, never by the scan itself:** ① `jarl` Format-V mask ⇒ zero callers for a function Ghidra
found instantly · ② `movea` base + runtime index ⇒ a live array reads as *"nothing reads slot 1"* ·
③ a byte written by a **WIDER** store (`0x27328 st.w` over `gp-0x3d94`) ⇒ false *"0 writers"* ·
④ wrong `st.b` opcode ⇒ **20 writers reported as ZERO** · ⑤ `hw2 = disp|1` applied to `st.b` ⇒
`gp-0x6805`'s stores conflated into `gp-0x6806` (`0x97FA|1 == 0x97FB`).
**Corrected width rule: `st.b`/`ld.b` → `hw2 == enc` EXACTLY; `ld.bu` → `enc|1`; halfword/word → either.**

---

## 🛑🛑 RULE 13 — **TRACE A FUNCTION'S OUTPUTS FORWARD. DO NOT ENUMERATE ONE CELL'S READERS AND STOP.**

**Added 2026-08-08, after eleven independent methods returned the same wrong answer.**

For three rounds the kit asked *"who reads `gp-0x6b94`?"* — disp16 and disp23 byte scans, LE32 absolute
literals, movhi/movea pairs, ep-address materialisation, pcode dataflow, and two register-return checks.
**All null.** Against six flashed on-car results (V61, V62, V67/V68, V74, V75, V80) that could only have
worked if that lane reached the motor.

**The lane does reach the motor.** The bridge is two hops past where every check stopped:

```
gp-0x6b94 -> FUN_0004503c (governor) -> gp-0x6ace -> FUN_000456a4 (comp-add) -> gp-0x6acc
          -> FUN_00042af8 reads gp-0x6acc @0x431C4 -> gp-0x6b08 @0x43206 -> ... -> gp-0x6b98
```

**Nobody asked about `gp-0x6acc`.** And `gp-0x6b08` had been dismissed as *"self-referential ramp state,
one writer inside the function itself"* — **individually true, collectively misleading**: that check asked
whether anything *outside* the function reads it and stopped, never asking whether the function's **own
next instructions** consume it. They do.

⊕ The chain was **already documented** in `reference_accord_post_governor_comp_add.md` (May 2026) with
the exact address `0x431c4`, and in `builds/v18_v49/build_v30_tva.py`'s own header. Neither was cross-checked against the
newer "cannot reach" conclusion. **When a new negative contradicts an old positive, diff them explicitly.**

★ **A "monitor-only" output two hops from the motor is a red flag, not a conclusion.** And a governor
whose cals bricked the car (V40) is not on a dead path — **a coherent account of V40 is the acceptance
test for any claim about this chain.**

Full detail: `memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md` and
`docs/handoffs/2026-08/HANDOFF-2026-08-08-v81-flew-and-the-aggregator-reaches-the-motor.md`.

---

## CATCH-UP: V76 → V100 — MOVED

🛑 **MOVED, 2026-08-21 — this section now lives in
[`docs/BUILD-LINEAGE-CATCHUP-V76-V100.md`](BUILD-LINEAGE-CATCHUP-V76-V100.md)**, verbatim, because
this file had reached **201 KB against the 256 KB `Read` cap** and a file past that cap loads with its
tail **silently truncated and no warning**. Nothing was deleted, reworded or re-ranked. **That file
holds the 24-row per-build table (V76 → V100) and every per-build artifact / route / hash note behind
it.** ⚠ It is NOT named `PART2` on purpose — **`Part 2` below is the code-cave section, which has not
moved.**

---

## 🛑🛑 RULE 12 — **A TABLE'S SHAPE IS BOUNDED BY ITS OUTPUT CLAMP, NOT BY ITS BREAKPOINT COUNT.**

**Added 2026-08-07.** A proposal arrived to make the damper's FactorC and FactorE literal ReLUs and, if
4 breakpoints proved too few, to build larger tables in free memory and repoint every reader. **Both
halves of that mechanism were wrong, and the reasons generalise.**

**(a) Count the DOF before asking for more points.** A ReLU is **2 DOF**. A 4-point record carries 8
numbers and spends 3 of them on collinearity. `n` buys **n−1 slope segments**; n=4 gives **three**, so
ReLU, ReLU+hold and ReLU+hold+rise are all reachable. **More points bought EXACTLY ZERO here**, proven
by explicit construction. 📋 **Ask which FOURTH segment is needed. If nobody can name it, n=4 is enough.**

**(b) The binding constraint was a clamp nobody had written down.** `gp-0x6bd0` is hard-clamped to
±`ceiling_LERP(gp-0x6ac2)` — **≤ 1024, and 512 at low ceiling index**. A ReLU FactorC is
speed-proportional, so `dose(v,99)/dose(515,99) = v/515` **whatever values are chosen**; pinning the
requested dose at 5 mph forces **7.02× the ceiling at 140 km/h** and rails from **3.2 °/s** upward.
★★ **A railed factor whose sign comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay this kit already forbids at `E_Y[0]` — the "ReLU" re-creates it at the ceiling.**
🛑🛑 **AND THE TEST WRITTEN FOR (b) DOES NOT ACTUALLY DISCRIMINATE (b) — V80 PROVED IT ON-CAR, 2026-08-07.**
A flat `FactorC` sized so the supremum equals the ceiling **exactly** clips 0.00% and passes every no-clip
guard, while delivering a **constant 495 counts across a 34× rate range** — the relay simply moves off the
ceiling clamp onto `FactorE`'s knee, **17 counts under the rail.** See **Part 2 → GATE 2 COROLLARY** for
the shape tests that would have caught it (flatness ratio, describing function `N(50)/N(500)`, distance to
the rail in counts, and a probe rung sized to the saturated regime).

**(c) Check how the operator used the shape word LAST time.** "Which factor isn't a ReLU" had two
readings indicting **opposite tables**: literal `max(0,k(x−x0))` indicts FactorC (nonzero 566 floor);
the operator's own recorded gloss in `studies/sessions/v76/v76_surface.py` — *"FLAT — no taper down, like a rectified linear
unit"*, read there as a **floor clamp** — indicts FactorE. **When a shape word is load-bearing for a
flash decision, grep the kit for how it was recorded before designing to it.**

⊕ Recorded for future use: relocating a **same-size** record IS cal-only — one u32 into the factor's
pointer array — and **`0xD7BB8`–`0xD7FEF` is 1,080 B of virgin `0xFF` in the same CRC block the build
path already recomputes. V74's "the six pointer arrays must stay byte-identical to stock" was a
SELF-IMPOSED BUILD GUARD, not a firmware requirement.** But **adding** breakpoints is a code edit to the
always-on base-assist damper — the V24/V27/V48B bricking class.

---

## 🛑🛑🛑 RULE 11 — **A CLAMP MAY BE AN INTERLOCK. NEVER RAISE ONE WITHOUT FINDING ITS MONITOR.**

**Added 2026-08-07, and it is the most expensive lesson in this file: it cost two mid-drive total
losses of power steering.**

**`0xC407E` is a DO-NOT-RAISE CELL.** It clamps the friction lane `gp-0x6b26`. Stock value **511**.
One instruction later, in the same 1 kHz tick, **`FUN_00036d74` — called *unconditionally* from
`FUN_0002214a` @`0x2290a` — tests `|gp-0x6b26| / 1024 > cal(0xC4004)`, where `0xC4004` = float `0.5`
= **512 raw counts**, and faults straight to DTC `0x1d`.**

⇒ **Honda set that clamp to exactly ONE COUNT below the monitor's own trip threshold.** It is an
interlock: a clamped signal cannot trip its own fault check. It looks like an ordinary output limit.
**It is not.**

**V73 raised `0xC407E` 511 → 850 — 338 counts past the ceiling — and removed the interlock without
knowing it was one.** **V74 and V75 both hard-faulted with latched total loss of assist.** The cell is
**mode-proof**, which is why V74 faulted with LKAS *disengaged* — no mode-indexed lever could have.

🛑 **CORRECTION OF RECORD, 2026-08-07 (orchestrator's own byte read across the lineage): the ×1.5 friction
table was introduced by V73, NOT V74.** stock / V70 / V71c / V72 carry Honda's row; **V73 / V74 / V75 carry
×1.5 — and V73 raised `0xC407E` in the SAME build.** ⇒ **the two-step narrative this rule used to carry
("V73 raised the clamp; V74 then multiplied the friction row, dropping the crossing requirement from
`gp-0x6c2c` ≈ 6258 to ≈ 4180") is WRONG.** V73 already carried **both** legs and flew clean anyway (n = 1).
**The mechanism and the rule are unaffected; only the attribution is.**
⊕ **The friction row is 14 sites, not one**: `0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C 0xD3A5C 0xD3A6C
0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C 0xD9A5C 0xD9A6C`, Honda's `9ad99ae952f8` → ×1.5 `67c667de7bf4`.
🛑 **`0xD2A4C` is mode 10 — a DISENGAGED-column record.** V74's derivation only ever wrote the 13 engaged
modes, so it never saw m10; any revert there is a revert TO stock and can only make that column more stock.

⚠ **[BELIEF, not EVIDENCE] "`0xC407E` = 850 caused BOTH faults."** The **DTC number was never confirmed
on-car.** What is EVIDENCE (2026-08-07, orchestrator's own Ghidra decompile + a raw Python LE scan of
disp16, the 6-byte disp23 form, LE32 literals and movhi/movea pairs): the monitor `FUN_00036d74` exists,
is **single-frame and un-debounced**, is **mode-proof**, `gp-0x6b26` has **exactly ONE writer image-wide**
(`st.h r6,-0x6b26[gp]` @`0x36CF0`, clamped at `0x36CCC`–`0x36CE2`), `0xC407E` has **0 writers / 3 signed
readers all inside `FUN_00036c12`**, and the build history lines up exactly. ⇒ **at 511 the monitor is
untrippable BY CONSTRUCTION**, whatever the plant, mode or lever set.
★ **V75's fault was NOT the damper**: the damper was identically **zero for 4.98 s** of the last 5 s and
reached only level 2 (128–288) **19 ms** before the trip; peak column jerk was **7,154 °/s² = 4.3× that
route's own p99.9** and the route maximum — exactly what this mechanism predicts.

**The rule, generally:** before raising any clamp, saturation or output limit, **search for a monitor
that tests the same cell**, and check whether the stock clamp sits just inside that monitor's
threshold. A clamp one count under a fault ceiling is a **design invariant**, not slack to be spent.
Two methods; a null here is load-bearing.

⚠ Corollary: **do not "fix" this by raising `0xC4004` instead.** That loosens the monitor rather than
the signal, and no other consumer of that ceiling has been surveyed.

---

### 🛑🛑 CORRECTION OF RECORD, 2026-08-10 — **THE `0xCBE74` FRICTION ROW HAS ZERO CLEAN FLIGHTS ON A LIVE COLUMN, AND IT IS NO LONGER EXONERATED**

**[EVIDENCE — byte-verified by dereferencing `0xCBE74 + mode*4` on the images themselves and reading the
Y array at `record + 8`, not by reading the build scripts.]** The 2026-08-07 correction above got the
*attribution* right (V73 introduced ×1.5, not V74) but left the record implying that V73's clean flight
tested the friction row. **It did not: V73 wrote mode 10 only, which is a DISENGAGED column on a car that
runs modes 24/26.** [[reference-accord-car-is-tvca4-mode-24-26]] · `docs/STATE.md` "AN ADDRESS IS NOT A MODE".

| build | ×1.5 on a **live** column (24/26)? | m24 (manual) | m26 (engaged) | on-car |
|---|---|---|---|---|
| stock / V70 / V71c / V72 | — | Honda | Honda | baseline |
| V73 | **NO** — mode 10 only, **DISENGAGED**, inert on this car | Honda | Honda | flew clean — **says NOTHING about this lever** |
| **V74** | **YES** — the 13 engaged modes | Honda | **×1.5** | 🛑 **HARD FAULT, latched loss of assist** |
| **V75** | **YES** | Honda | **×1.5** | 🛑 **HARD FAULT, latched** |
| **V76** — flown artefact `_v76_v38base_relu_damper` | **NO** — reverted by the V38 rebase | Honda | Honda | flew route 65 clean |
| ⚠ V76 — *other* artefact `_v76_gate_fb_arm5244_gateprobe` | **YES** | Honda | **×1.5** | **never flew** |
| V77 / V77B | **YES** | Honda | **×1.5** | **NEVER FLEW** |

⇒ **×1.5 on a live column has flown exactly TWICE, and BOTH flights hard-faulted. ZERO clean flights.**

🛑 **AND THIS INVERTS A STANDING ATTRIBUTION.** The record above blames `0xC407E` = 850 for the V74/V75
faults. **That attribution is NOT deleted — the monitor mechanism is EVIDENCE and RULE 11 stands** — but
its control has collapsed: **V73 carried `0xC407E` = 850 and flew clean** (byte-verified: V73/V74/V75/V77/
V77B = 850; V70/V72/V76-flown = 511). The only build that was supposed to show "850 alone is survivable"
is the same build that shows the friction row was never live. **V73→V74 is 64 differing runs (13 friction
sites + 51 others), so the friction row CANNOT be pinned** — but the control meant to exonerate it is the
thing that now implicates it.

> ⇒ **STATUS CHANGE: the `0xCBE74` ×1.5 friction row moves from EXONERATED to 🛑 OPEN SUSPECT.**
> **No dose of this row flies again until a probe measures the lane.** The previous "exonerated" status is
> preserved here as a superseded reading, not erased.

⚠ **REFINEMENT the correction does not cover, and it is RULE 10 applied to this row [EVIDENCE for the
bytes, BELIEF for what it implies about cause]:** the two faults are **not** in the same mode.
- **V74 faulted in MANUAL** (LKAS disengaged, over a bump — see RULE 10). Manual is **mode 24**, and
  m24's friction Y array is **byte-identical to Honda on V74** ⇒ **the friction row was NOT in force in
  the mode V74 faulted in.** By RULE 10 that fault cannot be laid at this row.
- **V75 faulted ENGAGED** (operator verbatim: *"after stopping at a stoplight and then continuing like
  normal, with openpilot engaged"*). Engaged is **mode 26**, where V75 carried **×1.5** ⇒ **the row WAS
  live for that one.**
⇒ **"2-for-2 fault association" is the flight-level fact; at the MODE level it is 1-for-1.** Both
statements are true and both belong in a flight decision. Neither restores exoneration: **zero clean
flights on a live column stands**, and V73 still fails to exonerate `0xC407E`.

⚠ **TWO ARTEFACTS SHARE THE V76 BUILD NUMBER**, and they disagree on both cells in this rule
(`_v76_v38base_relu_damper`: friction Honda, `0xC407E` = 511 · `_v76_gate_fb_arm5244_gateprobe`: friction
×1.5, `0xC407E` = 850). 🛑 **The lineage row's BASE column is the discriminator — `_v76_v38base_*` is the
flown one. A GLOB IS NOT A CHECK.** Any script, diff or ledger that resolves "V76" by wildcard will pick
one of the two arbitrarily and silently answer the opposite question.

🛑 **METHOD, and it is the whole reason this went unnoticed:** every row above was produced by
**dereferencing the pointer table and printing the mode number beside the address.** Reading the build
scripts, or matching addresses against a remembered list, is what produced three separate overstatements
about this cell in one session — in both directions. **An address is not a mode.**

---

Full detail: `memory/accord/calibration/accord-friction-lane-ceiling-is-the-hard-fault.md` and
`memory/reference/firmware/reference-accord-cbe74-friction-row-zero-clean-flights.md`.

---

---

## 🛑🛑 RULE 7, added 2026-08-05 — **A LEVER IS MODE-PROOF, OR IT IS A BET**

**The car is `TVCA4` — row 11 — running mode 24 disengaged / 26 engaged. It is NOT `TVAA1`, and it was
never modes 10/11.** [EVIDENCE] V73's probe read the mode over 104,061 frames and it **toggles with
engagement** (18 edges, all engagement edges). The 4-bit field drops bit 4, so an observed *v* means
true ∈ {*v*, *v*+16}; observed **8** ⇒ {8, 24}, and **raw 8 appears in no row of `0xCD000`** ⇒ manual =
**24**, forced. Only row 11 contains 24, and all four columns come from one row ⇒ engaged = **26**,
forced. ★ **It is the MANUAL arm that closes it — the engaged reading of 10 alone never would have,**
because rows 2/3/6/7 all carry raw 10.

> **RULE 7: classify every lever before proposing it.**
> - **MODE-PROOF** — code edits, and `tp` scalars reached without an index: `0x3AB76`/`0x3AC20`, the
>   `0x3AA96` gate, `0xC6446`/`0xC6444`, `gain_A` `0xC6A68`/`0xC6A7C`, `0xC407E`.
> - **MODE-INDEXED** — anything reached through a `mode*4` pointer array: `gain_B`
>   (`0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`), FactorC `0xC9E9C`, FactorE `0xC9F84`, the friction
>   records `0xCBE74`, the ceiling `0xC77A0`.
>
> **A mode-indexed edit written at the wrong mode is not a weak lever — it is NO lever, and it looks
> flashed, verified and driven.**

★★ **EVERY MEASURED FIX IN THIS KIT CAME FROM A MODE-PROOF LEVER; EVERY MODE-INDEXED LEVER WAS INERT.**
Inert by table selection: **V44, V47, V72's Levers B/C, BOTH of V73's levers, and the entire r24 dose of
V69/V70/V72/V73.**

⇒ **Write every mode, or probe the selector. There is no third option.** The engaged and disengaged
column sets are **disjoint** — engaged (e014/e015) = `{2,3,5,11,14,15,17,23,26,27,29,32,33}`,
disengaged (e012/e013) = `{0,1,4,10,12,13,16,22,24,25,28,30,31}`, **zero collisions across all 16 rows**
— so dosing the engaged columns of every row delivers whatever row is live **while leaving manual
byte-stock.**

🛑 **COROLLARY, and it is the expensive one: several "symptoms" this kit spent builds chasing were
created by its own earlier fixes.** ~~Grind #2 is V62's `sar`.~~ ⇒ **Before adding a lever for symptom X,
check whether X first appeared in the build that introduced the previous lever. A build that changes
nothing is a real and sometimes correct option.**

🛑 **CORRECTION 2026-08-08 (late): "GRIND #2 IS V62's `sar`" IS REFUTED.** **V71C carries NEITHER `sar`
byte** — `0x3AB76` = `AA` and `0x3AC20` = `AA`, byte-stock — **and it produced a spectrally identical
44.31 Hz event**, p99 **1741.9**, holding **3 of the corpus's 13 merged events in 5.28% of exposure**
(**P(≥3) = 0.028**). A symptom that appears on a build without the byte cannot be attributed to the byte.
[EVIDENCE] **The COROLLARY itself is unaffected — only this instance of it is.** Grind #2's origin is
**OPEN**; do not cite V62's `sar` as its cause.

🛑 **AND "FALSIFIED" MUST NAME THE SYMPTOM.** V42 ch.2 was filed *falsified* — against the **vibration**,
never scored against the ratchet, and it turns out to be V42's actual fix. V47 was filed *null* — against
the **21 Hz vibration**, never against the ratchet. **Both were live levers retired for the wrong
question**, and that is a distinct, recurring failure from the mode problem. A verdict without a named
symptom is not a verdict.

---

## 🛑🛑 RULE 8, added 2026-08-06 — **EVALUATE A NO-CLIP RULE ON THE OBSERVED ENVELOPE, NOT A RECTANGULAR GRID**

**V75's clip check produced two DIFFERENT verdicts from the SAME arithmetic, because two agents (and the
operator) policed two different envelopes.** A rectangular (speed × rate) grid rule checks every combination
the axes can independently reach — including corners the car never visits. On this build, the grid's worst
corner assumes **849°/s** of column rate. **Route 5d's actual measured maximum was ~~330°/s~~ 412°/s
(1,941 counts), and zero of its 101,118 frames exceeded 2000 counts** on the axis that matters. A lever
that clips at the grid's corner but never at the corridor the car actually drives is not unsafe — it is
untested at a speed/rate combination that does not occur.

🛑 **CORRECTION, 2026-08-06 (same day): the "330°/s" above was a UNITS ERROR and it flattered the margin
by 25%.** 330 is `|rate_f|`'s maximum in the extractor's own units — the fine CAN field carries a DBC
factor of 0.1 where the true LSB is 0.125 °/s, so the °/s figure under-states the counts by 1.25×. **The
counts figure — 1,941 — is convention-independent and both CAN channels (0x18F fine and 0x14A coarse)
agree on it exactly.** Quote counts, not °/s, whenever a margin depends on it.

🛑🛑 **AND THE BIGGER PROBLEM WITH THIS RULE, LEARNED THE HARD WAY WHEN V75 HARD-FAULTED:
A MAGNITUDE ENVELOPE IS NOT AN ENVELOPE.**

🛑 **CORRECTION 2026-08-06 (second correction, same day) — THE FACTUAL CLAIM THIS BLOCK USED TO MAKE IS
WITHDRAWN.** It read: *"Route 5d contains ZERO engaged stoplight stops … every check V75 passed ran on
telemetry that STRUCTURALLY COULD NOT CONTAIN THE REGIME THAT FAULTED."* **False.** What is true is
much narrower: 5d holds **0.0 s of `latActive` while STOPPED**. But the regime that faulted is a
**LAUNCH**, and **route 5d contains 5–6 engaged stoplight launches by two independent counts — and V74
flew them without faulting.** The envelope *did* contain the faulting regime. **The CHECK could not see
what was dangerous in it.**

**[EVIDENCE] V75's fault is pinned to ONE 100 Hz frame** — route `5e`, t = 284.7947 s: STEER_STATUS→7,
STEER_CONTROL_ACTIVE→0, `gp-0x6880`→1, `0x1AB`'s DTC-active flag→1, all three `0x14A` angle fields→
`0x7FFF`, STEER_SENSOR_STATUS 7→4, **all latched.** ★★ **The faulting launch was the MILDEST of four:**
an earlier one sat on the ±4096 rail **76%** of its window without faulting, the faulting one had
**0.00% rail contact**, and the damper **never reached the `≥448` probe rung (0/39,961 frames).**
300 ms before the latch there is a **20.0 Hz oscillation absent from openpilot's command.**
⇒ 🛑🛑 **MAGNITUDE-BASED MECHANISMS ARE DEAD FOR THIS FAULT — it is a FAST-TRANSIENT sensitivity**, and
a clip rule, a grid sweep and a peak-hold replay are all structurally blind to it.

> **RULE 8b: before citing an observed-envelope pass, state which regimes the envelope DOES NOT CONTAIN,
> and check that list against what the lever changes.** ⚠ **And state the pass as a BOUND, never a
> proof:** a clip rule tests **magnitude only** — it is structurally blind to **step size, switching rate
> and phase** — so an envelope that **does** contain the regime can still pass a build that faults in it.
> Those are GATE 2 questions, and no amount of telemetry coverage substitutes for them.

> **RULE 8: run BOTH checks, and say which is which.** The grid rule (`new > old AND new > ceiling` swept
> over the full rectangular domain) is the CONSERVATIVE, cheap-to-compute bound — pass it and you are safe
> everywhere the axes can reach, including combinations that may never occur. The observed-envelope check
> (the same rule swept over the ACTUAL (speed, rate) pairs seen in real telemetry) is the CLAIM THAT
> MATTERS for what the car has actually done. **A lever that passes only the second is not proven safe in
> general — say so explicitly** — but a lever that fails only the first, at a corner nobody visits, is not
> thereby dangerous. V75 passed BOTH: 0 new clips on the 98,988-point grid, 0 clips on the 101,118 frames
> actually driven (observed peak 354 = 69% of the 512 ceiling) — report both numbers, not just the
> convenient one. 🛑 **AND IT HARD-FAULTED ANYWAY (2026-08-06).** Passing both clip checks is not a
> safety verdict — see RULE 8b.

★ **The free-lever corollary this rule surfaced**: `FactorE X[1]` (400→200) steepens the low-rate ramp
without raising the plateau that sets the surface maximum, so it is free under EITHER check — neither the
grid rule nor the dose ladder found it by construction; route 5d's own telemetry (`probe-5d`) did, because
the observed envelope showed headroom the grid-only view could not see was usable.

---

## 🛑🛑 RULE 10, added 2026-08-06 — **"SINGLE-VARIABLE" IS RELATIVE TO THE MODE THE CAR IS ACTUALLY IN**

**V74 hard-faulted in MANUAL — LKAS disengaged, over a bump — and its headline lever could not have
caused it.** [EVIDENCE, verified two ways] Disengaged is **mode 24**, and all five mode-24 damper records
are **byte-identical to stock** on V74 and V75 — FactorC `0xD67E4`, FactorE `0xD6820`, FactorB `0xD6760`,
FactorD `0xD67A4`, ceiling `0xD60B4` — and **0 of the 54 non-CRC V73→V74 diff runs lands inside a mode-24
record.**

V74 was engaged-column-only **by design** (RULE 7's disjointness corollary — dose the engaged columns,
leave manual byte-stock). That is exactly what makes it **not single-variable in manual**: in manual, V74
is **V73 plus whatever MODE-PROOF cells it also carries**. That residue is the only place a manual fault
can come from — and on V74 the residue included **`0xC63A0` = 2048**, a bare `tp` scalar V72 doubled and
nobody reverted.

> **RULE 10: classify every cell in a build as MODE-INDEXED or MODE-PROOF before proposing it AND before
> exonerating it. A fault observed in mode X can only be caused by cells the car reads in mode X.**
> - A mode-indexed edit is single-variable **only inside the modes it writes**; in every other mode the
>   build is its parent plus the mode-proof residue. **Enumerate that residue in the build spec.**
> - ⇒ *"the lever was in force"* and *"the lever is exonerated"* are **both mode-scoped claims.** Say
>   which mode, every time.
> - ⇒ **A dose ladder built on mode-indexed cells has NO dose in the other mode**, so any `k` fitted from
>   it is defined only where those records are read.

★ **What not having this rule cost:** V74's fault was attributed to the damper dose for a full session,
**`k* ∈ (0.580, 1.580]` was derived from it as a *safe* bracket**, and V75 was built to k = 1.5798 on that
basis. **Both premises were false, and V75 latched the ECU.** The bracket is **VOID** — see the
`0xC9E9C`/`0xC9F84` row in Part 1.

---

## 🛑 Struck hypotheses, 2026-08-05 — do not re-propose

| hypothesis | why it is dead |
|---|---|
| **Saturation / clamp headroom** (`0xC61B2`/`0xC61B4`, `0xC61AA`/`0xC61AC`) | Falsified on **data** — engaged creep in-burst command sits at **27.7% of rail, 0 of 127 frames at rail**, and where it *does* rail burst duty **falls** 35.5% → 12.5% (the rail is protective) — **and on structure**: no reader of any of the four cells lies inside `FUN_00042af8`, and the four sum to **5120**, not 8192. The four mixer channels are **base assist, not LKAS**. `0xC61AA`/`0xC61AC` are dropped from the candidate pool |
| **A 7.8 Hz firmware divider** | mod-100 scheduler ⇒ only **{1000, 500, 200, 100, 10} Hz** are reachable. 7.8 Hz cannot be generated by the scheduler |
| **Stick-slip** | No harmonic series, no trigger, and f0 **falls** with load |
| **State 8, or any `gp-0x67fa` explanation of the damper null** | 🛑 **`0x830 ⊂ 0xc30` is arithmetic** ({4,5,11} ⊂ {4,5,10,11}) ⇒ **every state that runs the aggregator also runs the damper**, so *"aggregator live, damper inert"* cannot come from this variable at all. State 8 fails the converse way: `8 ∈ 0x930` only, so it runs **neither** ⇒ assist would be absent entirely |
| **`gp-0x67fa` aliasing** | All **33 writers store literal constants**; the complete value set is **{1,3,4,5,6,7,8,9,10,11}**, nothing ≥ 12 ⇒ `& 0xf` is a provable no-op, and V70's rung read the **full unmasked byte**. **State 10 really is excluded** |

---

## 🛑🛑 Struck LEVERS, 2026-08-09 (late) — do not re-propose; each killed on EVIDENCE this session

🛑 `FALSIFIED` ≠ `INERT-BY-MODE` ≠ `NEVER-TRIED`, and *"the same lever pushed the other way"* is a
different claim from *"a new lever"*. Every row below is a **structural or measured kill**, not a null.

| lever | status | why it is dead |
|---|---|---|
| **`gain_A` rec0/rec1 LOWERED** (`0xC6A72`–`78`, `0xC6A86`–`8C`) | 🛑 **ENGAGED-INERT — already run, twice failed** | Lever B's gate repoint (`0x3AA96`=`FB`) makes `lp = latActive`, and the armed path at **`0x3AB5E` OVERWRITES `gain_A` with `[0xC6444]` = 512**. ⇒ **V84 and V85 ALREADY deliver 512 engaged at EVERY speed**, deeper than V72/V73's 512/512/1050/2664/2560. This is V84's own §7a **pre-registered** experiment: **FAIL on V84, FAIL on V85.** ⚠ It remains live in the **manual** arm — but the symptom is engaged-only |
| **Lever A** — `0x3AB76` / `0x3AC20` `sar` `AA`→`A9` | 🛑 **DO NOT RESTORE** | the `sar` is **UNGATED**, so it applies in the **manual** arm too ⇒ it reproduces **V62/V65 verbatim** there, and the operator's V65 report on that exact condition is *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."* Second leg: **`r24 ≥ ~2` is necessary for grind #2 in every build that has ever produced it**, and restoring Lever A on a Lever-B base roughly **doubles past** that. ⚠ **The int16-overflow-ceiling leg is WITHDRAWN** — disassembled: `mul` writes a full 32-bit low word and `sar 0xa` operates on 32 bits, so `5120 × 5244 >> 9 = 52,440` fits with headroom. **The verdict stands on the manual-arm leg alone.** Retained visibly: do not cite an r24 overflow ceiling |
| **the 13-point LERP `0xC6B66` / `0xC6B80`** (in `FUN_0003b8f6`) | 🛑 **DEAD as a shaped lever** | its axis `gp-0x6a10` is **ABSOLUTE STEERING ANGLE**, not a tracking error — `b4` ≡ `\|angle\| ≥ 0.85°` at **99.94%**, the step sits **exactly on the threshold's own numeric value**, and the relation holds in the **MANUAL** arm where a tracking error is not even defined. **88.6% of engaged driving sits in its flat first segment** ⇒ its only honest description is a near-constant **0.878× broadband trim**, the same class as V56's mute (null, cost damping) and the `0xC646C` work (null) |
| **FactorD** (mode-record family, `0xD778C` m26 / `0xD77A4` m27) | 🛑 **STRUCTURALLY INERT where the symptoms live** | FactorC is multiplied in **BEFORE** FactorD and has `X[0]` = 2240 counts = **34.97 km/h** with `Y[0] = 0`, in **all four** of this car's modes. **Zero × anything = 0.** A third `gp-0x6a10` consumer — the boost LERP2 in `FUN_00034a72` — is **also** flat-zero in band0 (0–8 km/h) in all four modes. **Three independent confirmations.** 🛑 This also **REFUTES *"FactorD is the only frequency-selective lever in this firmware"* — THIS FIRMWARE HAS NONE**, which removes the argument that FactorE cannot do what FactorD can |
| **`0xC63A0` 1024 → 2048** | 🛑 **INERT — no mechanism** | `ch₀ = gp-0x6bd0 = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)`; Honda's shape has **two zero dead zones** (FactorC below 34.97 km/h, FactorE below 12.73 °/s, both `Y[0] = 0`) and the product truncates ⇒ **`ch₀` is exactly ZERO on 98.8% of engaged frames on route `6e`** (p50 **and** p90 both 0.00 counts, against a ±25600 clamp). ⊕ **V42 flew at 1024 and the operator called the ratchet fixed ⇒ 2048 is not necessary.** ⊕ **V72/V73 also carried Honda's damper**, so `ch₀` was zero on them too ⇒ **the V72/V73 correlation has NO mechanism.** ⊕ ⇒ **V84's own `0xC63A0` revert was itself INERT** and cannot be the cause of the V84 step |
| **`0xC61F6` = 3 → 0** (the rate-lane deadband) | 🛑 **DO NOT — it pushes the destabilising way** | a deadband is the **DUAL of a relay**: `N(A) → 0` as `A → 0` is precisely what *prevents* harmonic balance from closing. **Deleting it ADDS small-signal gain.** It costs **0.4%** at the lane's ~1029-count full scale and **exactly nothing** whenever the total sits >3 counts off zero. ⚠ This **reverses** the E12 framing that opened it as a candidate |
| **`0xC61D6`** (shaper slew step, stock 0) | 🛑 **ALREADY REJECTED — do not revive** | an 11-round review labelled it *"highest-risk; last/never"*: it does **not** re-enable an anti-snap ramp, it **activates a dormant, uncalibrated speed × torque 2D map** onto the live command. `0xC6424` is separately confirmed **inert** (coupled to slew = 0). ⇒ 🛑 **There is NO usable cal-only rate-limiter lever on this path.** (This is the second time a subagent has re-proposed `0xC61D6`; see the Part 1 note) |
| **`FUN_00038148` / `gp-0x6b70` as the ~8 Hz generator** | 🛑 **REFUTED** | odd/even harmonic comb **0.858 [0.739, 1.000]** against a positive control reading **1.204 [1.147, 1.566] at just 15% injection**; 3:1 PLV **z ≤ 1.05**; switching-surface time-locking **−0.0375**; a second method finds no third harmonic ⇒ **<15% of the ~8 Hz bar content can be relay-generated.** The chain stays interesting; **this hypothesis about it does not** |

### 🛑🛑 THREE NEW "FLATTEN-A-CURVE-INTO-A-RELAY" HAZARDS — the V72/V80 error, one address family over
Each of these is a **one-cell edit that converts a shaped nonlinearity into a full-authority relay.**
V80 is the recorded cost of doing exactly this once already: **the worst grinding in this car's history.**

| cell | stock | 🛑 forbidden move | what it produces |
|---|---|---|---|
| **`0xC4080`** | **0** | **NEVER RAISE** | `FRICTION += cal/1024 × ratio` with **no `\|model\|` factor** ⇒ a **latent PURE COULOMB RELAY**: amplitude-independent and unbounded in index |
| **`0xC63AE`** | 1024 | **never → 0** | the LERP index becomes ≡ 0 ⇒ output ≡ `±Y[0]`, a constant ⇒ **a pure relay at full authority**. 🛑🛑 **`0xC63AE` IS NO-GO AS A V100 LEVER — added 2026-08-13 (later), `tracer-c63ae`, crux verified by the team lead.** RULE 7 **PASSES** here (unconditional bare-`tp` scalar read at `0x38242`, no mode index — the V69/V70 wrong-record failure class cannot recur on this cell). But **the dose is a LEVEL shift, not an AC change**, and **the AC gain is NON-MONOTONE in scale and REVERSES SIGN across the operator's own amplitude distribution**: at scale 1536 the ratio is **0.773 at p10, 1.078 at p50, 1.277 at p90** (reproduced independently from the stock knots; matches the agent's own p50-only figures 0.902/1.076/1.242 to ~2%). **1280 is arithmetically WORSE than stock.** A gain rising with amplitude is the hardening nonlinearity that sets up a limit cycle — **V80 class.** ⭐ New structural fact: **`Y[9]` and the ±8192 clamp are the SAME cell, `0xC6200`** ⇒ the clamp is never the binding constraint on this lane (see the `0xC6200` row below) |
| **`0xC6200`** | 8192 | **never < `Y[0]`** | the clamp does the same thing from the other side. ⊕ Separately: `0xC6200` has **15 readers**, and the governor cals `0xC6202/04/06/08` cluster **disjointly** at `0x045410`–`0x0457de` ⇒ **`0xC6200` is NOT governor-shared** (confirmed twice; V40 wrote `0xFFFF` to `0xC6206`/`0xC6208` and left `0xC6200` untouched). 🛑 **CORRECTED 2026-08-13 (later) — this row used to say "3 of its 15 readers are still unidentified ⇒ RULE 11 census is not complete." RULE 11 IS NOW COMPLETE**: `tracer-6ad6` identified the three as `0x3a7a2`/`0x3a7b2`/`0x3a7c4` — **the PID's own clamp on `gp-0x6ad6`**, verified in Ghidra by the team lead (`read_memory(0xC6200)`=8192, `disassemble_bytes` reproduces the listing instruction-for-instruction). **Stop calling `0xC6200` "gp-0x6b70's clamp" — it is FOUR distinct things**: the friction lane (6 sites), `gp-0x6b70`'s own output clamp (4), the Stage-2 LERP's `Y[9]` (1, see the `0xC63AE` row above), and the PID reference clamp (3), plus `0x39ff6` unchased. ⭐ **Structural consequence**: the SAME 8192 value bounds Path-2's entire output AND the entire PID reference — Path-2's full scale is exactly the width of the window it must fit inside, and `\|gp-0x6ad6\| ≥ 8192` zeroes `∂(gp-0x6ad4)/∂(gp-0x6b70)` through P, I **and** D simultaneously (clamp sits upstream of all three, `FUN_0003a382`). Clamp duty is UNMEASURED. 🛑 **GENERALISABLE LESSON — every build script since V90 labelled this cell "gp-0x6b70's clamp" (one of its four roles), and that mislabel is what kept the PID-reference role invisible for ten builds.** A cal cell with multiple roles, labelled by only one, is a latent wrong answer — see `memory/MEMORY_CONSTELLATION.md`'s 2026-08-13 (later still) entry for the full discipline. |

⊕ **RECORDED, VIRGIN, UNTESTED AND NOT PROPOSED** — so it is not "discovered" as new next session:
`FUN_00036388` contains a **relay-with-dwell** — dwell counter `gp-0x6a82`, +1/tick while
**`|gp-0x6b64| > 0xC618A` (= 1024)** 🛑 *(corrected 2026-08-12 — this note previously read `<`; it is
`>`. Asm @`0x36448`: `cmp r16,r7` computes `r7−r16` with r7=`|gp-0x6b64|`, then `setfgt r16`; the
`be` @`0x3645a` takes the **decrement** path when not-greater. Operand order validated in-block by the
abs() idiom @`0x36436`. Decompile agrees.)*, ceiling `0xC627E` = 20; **past 20 ticks the output SNAPS
to 1024** (the snap value is the **same cal `0xC618A`**, dual-purpose), writing `gp-0x6b62`. Cals
`0xC618A` / `0xC627E` / `0xC63C0` were **never edited by any build** (grep-confirmed).
**Disfavoured by the same no-comb evidence that refuted `gp-0x6b70`.**

🛑 **RE-IDENTIFIED 2026-08-12 — this is a RACK END-STOP CUSHION, not a centring lane.**
`FUN_00035e00` @`0x35e00` arms the whole cluster on **`|gp-0x6b98| > cal(0xC618E)=4096` AND motor rate
`gp-0x6ac0 < cal(0xC620C)=200`** — high command with the motor not turning, i.e. a **STALL** — then
splits by `sign(gp-0x6bf0)` into two "at the stop" enums `gp+0x6440`/`gp+0x6441`. Its gate needs
`|gp-0x6bf0| > 8878` because the travel envelope's half-width is **floored by cal `0xC6150`** at
`18780>>1 = 9390` (which reproduces the measured hands-off `gp-0x6bda ≈ 9262` exactly). ⇒ **dead
engaged AND ~99.3 % dead in manual (V92 duty 0.0074)**, on stock and on every build. **Do not arm it:**
its absence cannot explain any engaged-vs-manual difference, and the snap flattens the one shaped
curve in the lane into a constant — the FLATTEN-A-CURVE-INTO-A-RELAY class in the table above.

### 🛑 `gp-0x67fa` — the reachable set is effectively **{11} ALONE**, and that KILLS `0x454FE`
State 5 is **structurally dead**, state 10 measured **0.0000%**, state 4 measured **0/123,277**.
⇒ **V42's `0x454FE` is present on V85 (`0xB5`) and MEASURED INERT.** Keep the byte — it has been silently
lost three times and costs nothing — but **carrying it is NOT addressing ratcheting**, and no build may be
justified on it. ⊕ **`gp-0x671a` is RULED OUT** as a lever axis: stuck at 0 across **1,158 reversals** on V64.

---

## 🛑 Ledger corrections, 2026-08-09 (late) — each from a byte read of the build's OWN image (RULE 4)

| # | correction |
|---|---|
| 1 | **`0xC63A0` was reverted at V83a, NOT at V84.** The lineage row previously implied V84. |
| 2 | **`V76g` ALSO carried `0xC63A0` = 2048.** It was missing from the "who ever moved it" list. |
| 3 | **`V76` and `V80` are `0xC63A0` = 1024**, not 2048. |
| 4 | **The V85 frozen-cell count is 12, not 14** — `builds/v80_v107/build_v85_tva.py` declares 10 `FROZEN_CELLS` + 2 `FROZEN_BYTES`. No 14-item list exists; the "14" in this file refers to the **14 friction sites**, a different set. |
| 5 | **The mode-record pointer space is 340 slots (10 arrays × 34 modes), not 58**, and there are **34 non-stock records**, including modes **32/33**. A count-only census is blind to a write into an **already-non-stock** record ⇒ **assert every record byte-identical to the BASE unless declared.** |

---

## 🛑 Ledger corrections, 2026-08-05 — each from a byte read of the build's OWN image (RULE 4)

| # | correction |
|---|---|
| 1 | 🛑 **V69 AND V70 DID NOTHING.** `sar` stock (`aa32`/`aa42`), gate `c5`, arms 512/512, and the only edit is `gain_B` **mode 10** ⇒ **byte-stock behaviour**. The recorded *"clean single-variable r24 series ×1→×2→×4 = 879/729/746, CIs overlap ⇒ r24 is near-inert"* was **three replications of ONE condition.** ⇒ **r24's dose is UNTESTED, not near-inert** |
| 2 | **V72's two-lane row is `r24 ×1.000 / r26 ×0.250`**, not `3.414 / 0.250` — its r24 half was mode-10 `gain_B`. Its grind-#2 result is therefore **confounded with stock**. 🛑🛑 **THE SECOND HALF OF THIS ROW IS RETRACTED 2026-08-06:** it read *"what governs grind #2 is V62's `sar`, which V72 does not carry"* — **that is hypothesis (A) and it is REFUTED.** `V71C` carries **neither** `sar` byte (`0x3AB76` = `aa32`, `0x3AC20` = `aa42`, byte-read) and produced a spectrally identical grind-#2 event: **44.31 Hz**, p99 **1741.9** = **12.2×** the max of any non-bursting build, against a same-segment non-burst floor of **25.5**. V71C holds **3 of the corpus's 13 merged events in 5.28% of the exposure, P(≥3) = 0.028.** ⇒ **a `sar`-stock build is NOT safe by construction** |
| 2b | **V62/V65's delivered r24 is `×2.000`, not `×3.414`** — `sar 0xa → 0x9` is a **flat doubling of BOTH lanes at every speed and rate** (mode-proof, one instruction each), not the `0xC6446` arm. The 3.414 figure was the *arm* value copied across the whole column. ⇒ **the two-lane rule's "r24 ≳ 3.4×" threshold is WRONG — V62/V65 burst at 2.000×.** The rule's *shape* ("both lanes elevated") survives; its *numbers* do not. Rebuilt table: `docs/STATE.md`; model: `analysis-2020accord/lib/_grind2_delivered_lib.py` |
| 3 | ★★★★ **V42's fix was the r26 KILL, not `0x454FE`.** V42 vs V41: `gain_A` **all four records → `[0,0,0,0]`**, `0xC643E` 1536→0, `0xC6444` 512→0, plus a revert of V41's motor-rate cap. `0x454FE` never executes. **This closes a two-session [OPEN]** — and V42 ch.2 sat in this table marked *FALSIFIED* the whole time (see RULE 7's last paragraph) |
| 4 | **V72/V73's r26 cut is PARTIAL** — `gain_A` `rec0`/`rec1` → flat 512, but **`rec2` `0xC6A90` and `rec3` `0xC6AA4` are byte-stock** ⇒ the cut is **creep-only by record selection**; at and above ~50 km/h r26 is untouched |
| 5 | **`tp+0x71b2` IS load-bearing** — LKAS reaches the motor via the second accumulator `gp-0x62b0[ch]` → `gp-0x3d88` → `gp-0x6b4c`. **No V14 correction is needed** (one was proposed and withdrawn). Lineage byte-verified over 66 images: stock **512** → **1024 by V22** → **2048 at V38**, `0xC61B2`/`0xC61B4` always in lockstep. ⚠ The V14/V15 first step is build-script prose only — no image exists before V22 |

---

## 🛑🛑🛑 RULE 9, added 2026-08-06 — **THE GRIND-#1 FIX AND GRIND #2 HAVE NEVER BEEN SEPARATED**

🛑🛑 **RULE 9's DRIVE PROTOCOL IS RETIRED, 2026-08-09, by operator decision.** The prescribed manoeuvre
(empty lot, openpilot engaged throughout, 4–11 km/h, wheel ≥100° from centre, continuous figure-eights at
100–500 °/s, 6–9 minutes, plus a 60 s LKAS-off control) has been **missed by four consecutive builds** —
route `6d` accumulated **5.1 s against its own 166 s floor (3.1%)**. It is retired rather than re-issued:
it asks for an artificial low-speed manoeuvre under LKAS, and **the 40–49 Hz events the operator actually
reports occur on ordinary roads at 56–62 km/h** (both route-`6d` events), not at engaged creep.
⇒ **Any claim about 40–49 Hz at engaged creep is UNMEASURED and must be labelled so. Do not schedule the
drive; do not quote a zero-count from it as evidence.** The rest of RULE 9 — that the grind-#1 fix and
grind #2 have never been separated — still stands.

**Before proposing any rate-lane lever for grind #1, read this row. It is the reason the trade looks
solved in the record and is not.**

**[EVIDENCE]** Split-half null computed **first** inside the stock-lane pool with the identical estimator
= **[0.663, 1.502]**; grind #1 = p90 of the 18–22 Hz envelope over engaged-creep windows, episodes
resampled. **The builds that measurably moved grind #1 are EXACTLY {V62, V65, V67, V68, V71C}.**

| moved grind #1? | build | grind-#2 events | engaged creep-CORNER s | engaged HIGH-RATE creep s |
|---|---|---|---|---|
| **YES** | V62 · V65 · V71C | **present** | 74.2 · 189.4 · 23.0 | 21.8 · 120.3 · 6.4 |
| **YES** | **V67 · V68** | not observed | **11.5 · 0.0** | **0.0 · 0.0** |
| no | V58·V59·V61·V64·V69·V70·V71B·V72·V73·V74 | none | 3.8 – 56.3 | 0.0 – 21.8 |

⇒ **EVERY BUILD WITH ADEQUATE GRIND-#2 EXPOSURE FAILED TO MOVE GRIND #1, AND EVERY BUILD THAT MOVED
GRIND #1 EITHER SHOWS GRIND #2 OR HAS ESSENTIALLY NO EXPOSURE IN THE BURST REGIME.**
The two are **perfectly collinear.** **No build has ever demonstrated one without the other at usable
power.** 18 of 21 creep burst windows sit at |ang| ≥ 100°, and V67/V68 hold **11.5 s** and **0.0 s** there.

🛑 **A "grind #2 = none" cell for V67/V68 is NOT a measurement — it is 11.5 s at P(0) = 0.80.** The
operator's own V67 report hedged precisely there (*"might still be there somewhat … more so LKAS-engaged
at low-speed … might just be dampened"*) and the hedge was recorded as "none".
✅ **The fix costs no bytes: ~90 s of deliberate ENGAGED hard cornering at creep on the next rate-lane
build** takes P(0) from ~0.61 to < 0.05 in one drive. **Ship that instruction with every such build.**
Scripts: `analysis-2020accord/studies/grind2/grind2_collinearity.py`, `studies/grind2/grind2_delivered_verdict.py`,
`studies/grind2/grind2_delivered_census.py`.

---

## 🛑🛑 RULE 6, added 2026-08-05 — **A LEVER IS ONLY IN FORCE IF THE CAR READS THE TABLE YOU EDITED**

**V72 raised the base-assist damper at creep. The bytes were correct, the arithmetic was correct, the
CRC passed, and the car never read them.**

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`, where `mode = *(byte)(gp + 0x63fd)`. **There are 13 mode variants.** V72
edited **modes 10 and 11 only**, because `39990-TVA-A160` *reads as* row 2 `'TVAA1'` in the config table
at `0xCD000` ⇒ modes 10/11.

🛑 **That part-number → key mapping is an ASSUMPTION recorded in this file. It was never a measurement.**
`builds/v18_v49/build_v44_tva.py` has patched modes 10 **and** 11 since V44 *because of it*, and every damping build
since inherited it.

**The probe settled it arithmetically.** On V72, modes 10/11 give `|gp-0x6bd0| = 389` **unconditionally**
(FactorC ≥ 430 at every speed, FactorE = 927 at every rate) ⇒ `bit4` (`|gp-0x6bd0| ≥ 64`) would fire on
**100%** of frames. **It fired on 0 of 87,940, including 0 of 34,275 above 35 km/h.**
⇒ **[EVIDENCE] the car is not in mode 10 or 11; Levers B and C were inert by TABLE SELECTION.**

> **RULE 6: before recording a cal edit as tested, establish that the car reads THAT RECORD — not merely
> that the bytes changed and the CRC passed. For any mode-, variant- or config-indexed table, the
> selector is part of the lever. Probe the selector, or treat the result as a null by construction.**

★ The general form is worse than this instance: **a mode-indexed table makes a lever look flashed,
verified and driven while being structurally unreachable.** Every prior "damping is null" result on this
kit (V44, V47, V72) is now **uninterpretable**, not falsified.
⚠ Still open: **which mode is live.** Modes 4/5 and 12 are fully consistent with the measurement, 0–3
marginally disfavoured, 10/11 excluded. **V73 reads `gp+0x63fd` directly.**

---

## 🛑🛑 RULE 4, added 2026-08-05 — **TWO LEDGER ERRORS FOUND, BOTH RUNNING THE DANGEROUS WAY**

A machine byte-diff of **all 65 built plain images** vs stock over `[0x13000,0x100000)` found two errors
in this file. Both made a lever look *tested* when it was not — the direction that suppresses work.

1. 🛑 **Part 1 attributes four cals to V39 that V39 NEVER WROTE.** The row
   `` `0xC6440/42/46`, `0xC61F6` | V39 | ✅ | FALSIFIED `` is **false**. **V39's entire delta vs V38 is
   `0x3AC78` (4 bytes, a cave hook).**
   - **`0xC6442`** — written by **0 of 65 images**. **UNTESTED**, and separately **unreachable**:
     `gp-0x671d` reads **0 / 402,424 frames** across four routes.
   - **`0xC61F6`** — written by **0 of 65 images**. **UNTESTED.**
   - `0xC6440` — V63/V64 only, null-by-construction. `0xC6446` — V67/V68/V71C only, and only with the gate.
2. 🛑 **V71B and V71C do NOT carry V62's `sar` fix.** `0x3AB76`/`0x3AC20` = `a9` in **exactly three
   images: V62, V65, V71A** — and V71A is unflashed. **The two builds flown 2026-08-04/05 carry NEITHER
   of V62's bytes.** Say this before anyone reads V71B/V71C as "V62 plus something".
✅ **No third silent loss exists** — every carried edit was checked across all 65 images.

> **RULE 4: attribute a lever to a build only from that build's own byte diff, never from this table's
> prose. Two of the entries here were wrong, and both errors ran toward "already tested".**

---

## 🛑🛑 RULE 5, added 2026-08-05 — **A NULL IS ONLY A NULL IF THE LEVER WAS IN FORCE**

**`0x454FE` was recorded mid-session as FALSIFIED for the ratchet because V71B and V71C flew with it
restored and the operator reported no change. That was wrong.** V71's own probe measured
**`gp-0x67fa == 4` at 0 / 123,277 (route 54) and 8 / 92,826 (route 58) — all eight in PARK.**
**State 4 never occurred while driving, so V42's substitution never ran on either drive.**
⇒ **a null by construction**, the same class as `0xC6444` on gateless builds.

> **RULE 5: before recording any lever as FALSIFIED, state HOW you know it was in force on that drive.
> If the answer is "the build carried the byte", that is not sufficient — a byte that never executes is
> not a test. Prefer a probe rung on the lever's own enabling condition.**

★ What survives is stronger than the retracted claim: since state 4 never occurs, the substitution
**never runs on stock either** ⇒ **structurally eliminated** as the 7.79 Hz ratchet's cause.
⚠ **[OPEN]:** V42 was CONFIRMED on-car against the *hard-turn recovery* ratchet. If state 4 never occurs,
that fix could not have acted either. Unresolved.

---

## 🛑🛑 RULE 3, added 2026-08-04 — **"CONFIRMED" DOES NOT MEAN "STILL ON THE CAR"**

**This file records what a lever DID. Until now it did not record whether the current build still
CARRIES it — and that gap cost this kit roughly ten builds.**

> **RULE: for every lever you cite, byte-check whether it is present in the CURRENT build's plain
> image (`../accord-firmwares/analysis-2020accord/_v<NN>_plain_image.bin`) before reasoning from its
> result. A confirmed fix that is no longer carried is not evidence about the car you are driving.**

**The two instances that motivated this rule — both found 2026-08-04, both by byte-reading all 60
built images:**

| lever | what it fixed | confirmed by | carried by | how it was lost |
|---|---|---|---|---|
| **`0x454FE`** `bne`→`br` | the **RATCHET** — state-4 governor magnitude substitution | **V42, "CONFIRMED ROOT CAUSE, carry forward"** | **V42→V52C only** | 🛑 **SILENT REBASE LOSS.** V53+ descends from V38/FOURFRAME, which branched *before* V42. Nobody decided this |
| **`0x3AB76` + `0x3AC20`** `sar 0xa`→`0x9` | **GRIND #1** — 8× at creep, 42× at \|rate\| 16–32; the kit's only measured grind fix | **V62** | **V62, V65 only** | ⚠ removed as **V66's confirmatory control** and **never restored**. The effect was then re-created twice in other encodings that dose **r24 only**, and the ladder still labels those "2×" |

⇒ **From V66 to V70 the car carried NEITHER confirmed fix**, while the record read as though both were
carried. The `0x454FE` case is worse than bookkeeping: the argument that later retired it as a cause of
the *current* ratchet — *"`STEER_STATUS == 4` fires 0/37,922"* — was **voided** when bus `STEER_STATUS`
was shown not to be `gp-0x67fa` (state 4 sits inside all three gate masks). **It was never actually
eliminated.**

★ **And the general form of the second case is the more dangerous one:** a lever removed *on purpose*
as an experimental control is indistinguishable, six builds later, from a lever that was never needed.
**When you remove a confirmed fix to run a control, write the restore into the next build's spec.**

---

## Part 1 — Lever index, by address

🛑 **MOVED, 2026-08-12 — this section now lives in
[`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`](BUILD-LINEAGE-PART1-LEVER-INDEX.md)** (137 KB), verbatim,
because this file had grown past the 256 KB `Read` cap and its tail was silently invisible.
**Grep that file by address before proposing any calibration edit.** Nothing was deleted.

---

## Part 2 — Code caves are the only bricking class

**Three of this kit's code caves bricked the ECU: V24, V27, V48B.** Every success since V29 has been
cal-only or a single in-place branch/displacement edit.

- **V27** — bricked from **ASYMMETRY**, not magnitude (float twin doubled wholesale vs int corridor-only).
- **V48B** — bricked from (a) RAM collision: biquad state `gp-0x14FA` aliased a live monitor status byte,
  and (b) an unmodelled lightly-damped resonator inserted into the always-on base-assist loop.
- **V40** — not a cave, but the same lesson: the defect was the **magnitude** of a cal write, not its
  direction.

⇒ **TWO MANDATORY GATES for any cave / filter / dynamics change** (apply without being asked):
- **GATE 1 — RAM OWNERSHIP.** Every byte of the full multi-byte footprint proven free *including writers*
  and register-indirect / 6-byte-extended-displacement accesses. `gp-0x1401..0x1502` is poison (it is a
  subset of the `0xb7260` I/O-mailbox array). **Static clearance is not sufficient — `gp-0x1500` passed
  both static methods and still failed on-car.** A live probe is the only reliable RAM-ownership test.
- **GATE 2 — CLOSED-LOOP STABILITY.** Magnitude *and* phase of **every loop the touched signal is in**,
  especially the always-on base-assist loop. Never a single-frequency magnitude.

**A 2-byte in-place displacement or branch-condition edit is a different, far lower risk class than a
trampoline + cave.** Do not conflate them.

### 🛑🛑🛑 GATE 2 COROLLARY, added 2026-08-07 — **"DOES NOT CLIP" AND "IS NOT A RELAY" ARE DIFFERENT STATEMENTS, AND ONLY THE FIRST WAS EVER CHECKED**

**This is the specific defect that let V80 through its own gates and produced the worst grinding this car
has ever made.** [EVIDENCE]

Every no-clip guard in this kit tests **`product > ceiling`**. V80's damper supremum is
`(566*927)>>10 = **512** = the ceiling **exactly**, so it clips **0.00%** — and the guard passed, twice,
on two different envelopes. **A guard of that shape is STRUCTURALLY BLIND to `product = ceiling − 17`.**

V80's flat-`FactorC` edit was adopted *because* it removed the clipping that made V79 a relay. It did not
remove the relay. **It MOVED it** — off the ceiling clamp and onto **`FactorE`'s own knee, 17 counts under
the rail**, where the slope drops ~1200× at `X[1] = 119`. The delivered surface is a **constant 495 counts
across a 34× rate range at every speed**: a near-bang-bang Coulomb law wearing a no-clip certificate.

> **THE RULE: a saturation test is not a linearity test.** Before flying any shaped surface, score the
> **shape**, not just the bound:
> - **Flatness over the operating range.** Quote `max/min` of the delivered output across the rate span
>   the car actually visits. V80's was **1.034 over 34×** and nobody computed it.
> - **The describing function `N(R)`.** Constant `N` = viscous = stabilising; `N` rising as amplitude
>   falls = relay = limit-cycle generator. **Report `N(50)/N(500)`.** V75 = 1.45×; V80 = **3.27×**.
> - **Distance to the rail, in counts.** "0.00% clipped" at `ceiling − 17` is not margin, it is a rail with
>   a rounding error in front of it.
> - **A probe rung sized to the saturated regime, and a flown build to compare it against.** V75 read
>   `|gp-0x6bd0| ≥ 448` at **0.000% of 28,317 engaged frames**; V80 read **19.4%**. That single pair is the
>   cleanest statement of the root cause in this file, and both numbers came from the builds' own caves.

⚠ **The hazard is not new and the kit had already named it** — RULE 12(b): *"a railed factor whose sign
comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`) IS the Coulomb relay this kit
forbids at `E_Y[0]`."* **The failure was that the test written for that rule only ever policed the
ceiling.** ⇒ **Whenever a rule names a hazard, check that the test actually discriminates it — not merely
one sufficient condition for it.**

### 🛑 A RE-CUT UNDER THE SAME BUILD NUMBER DESTROYS ITS PREDECESSOR'S PLAIN IMAGE — open, 2026-08-04

**The hazard, stated as it actually happened.** Two V70 cuts were built 19 minutes apart. **Both wrote
`_v70_plain_image.bin`**, so the second silently **overwrote** the first's snapshot. The first cut's
`.rwd` survived and was flashable. ⇒ **a flashable artefact existed that NO gate in this kit could
check**: `verify/verify_v70_image.py` asserts the *current* topology (`0x3AA96 == 0xC5`, `0xC6446 == 512`), so
it **fails on the superseded build by construction**, and `verify/diff_build_vs_stock.py` has no image to read.

⚠ **The only reason the superseded cut's bytes are documented at all is that they were read inside the
19-minute window before the overwrite.** That is luck, not process.
✅ The *flash* risk was closed by renaming it `SUPERSEDED-DO-NOT-FLASH-…` (`accord-firmwares` `9d44efc`).
🛑 **The verifiability hazard is NOT closed and applies to every future re-cut.**

**RECOMMENDED FIX FOR THE NEXT BUILDER — NOT DONE, and deliberately not retrofitted this session:**
- write **`_v<NN><tag>_plain_image.bin`** (tag from the build's own `TAG`), so a re-cut cannot collide;
  **or**
- **refuse to overwrite** an existing snapshot whose SHA differs from the one about to be written,
  unless explicitly forced.

**Every builder in the tree still writes the fixed `_vNN_plain_image.bin` name.** This entry is a
recommendation, not a description of a fix that exists — do not read it as done.

⚠ **The superseded V70 image cannot be trivially regenerated** — its builder configuration no longer
exists in the tree. In principle it could be recovered by decoding the surviving `.rwd` back to an
image. **That was NOT attempted**, and was judged not worth it for a superseded do-not-flash artefact;
recorded so the gap is explicit rather than ambiguous.

★ Related and distinct: **`bit6 ⇒ bit3` gives build-CLASS identity, never FILE identity** — a probe
cannot separate two cuts of the same version, because their caves are identical. **The filename is the
only pre-drive discriminator between re-cuts**, which is why the rename is load-bearing rather than
cosmetic.

### 🛑🛑 GATE 4 for PROBES, added 2026-08-04 — **read the GAIN IN FORCE, not a lane OUTPUT**

**Four consecutive probes have now returned an uninterpretable zero by reading a lane output** — V64,
V67, V68 (`gp-0x67df`) and **V70's bit6 (`gp-0x6ada >= +512`, 0/18,010)**.
★ **V70's is the informative one, because it is NOT vacuous:** a replay through the **shipped** surface
driven by **route 50's own data** predicts **311 hits**; **stock predicts 52**; observed **0**. And
`|dtorque|` off a 100 Hz grid is a **lower** bound, so the gap cannot be closed in the safe direction.
⇒ **delivered gain < ~1574 Q10, below stock's 3072**, and **`0xC6442` = 1024 (the `gp-0x671d` mask arm)
is the ONLY arm in the selector predicting exactly 0.**
✅ **The identification was verified and is not at fault** (`0x3AC42`–`0x3AC54` = `r24 = clamp(r6,
±0x2000)`; `0x3AD5A st.h r24,-0x6ada,gp` stores exactly that, r24 unclobbered through the add chain).

⚠⚠ **BUT ARM SELECTION IS THE WEAKER READING — SOFTENED 2026-08-04.** **The same rung read 0/47,990 on
V69's route `4f`, at DOUBLE V70's dose**, where it needed only **49 counts** of `|dtorque|` against a
repo max of **839** — a **much larger** anomaly, and one that **does not fit arm selection**: under (b)
the mask arm is **1024 on every build**, so it cannot produce a **dose-dependent** miss. And **V67 read
`gp-0x671d` 0/150,327 on route 47**, so the mask would have to be set near-continuously on `4f` *and*
`50` but never on `47`. ⇒ **[BELIEF] (a) — an under-ranged or MIS-RECONSTRUCTED rung — is the
better-supported reading** (the `dtorque` figure is a **4-sample 1 kHz difference rebuilt from a 100 Hz
bus copy of a different, filtered torque cell**; polarity is the other candidate). **(b) is possible but
less parsimonious; the corpus cannot settle it**, and grind #1 cannot adjudicate it either (it is blind
to r24 gain — see Part 1). 🛑 **The DURABLE part is the rule below, not the mechanism.**

> **RULE: spend a probe bit on the SELECTOR/MASK that decides which gain is in force, before spending
> one on the lane's output.** A mask bit is one bit and is never ambiguous; an output null cannot
> separate *"the lane is quiet"* from *"the gain you think you shipped is not the gain in force"*.
> V71's **bit6 = `gp-0x671d != 0`** is the first rung in this kit built to that rule — and it carries a
> **two-sided, low-threshold r24 mirror rung** alongside it, so an under-ranged reconstruction cannot
> hide again.

---

### 🛑 GATE 3 for PROBES, added 2026-08-04 — size a rung against the LANE's own reachable output

**A probe cannot brick an ECU, but it can waste the only telemetry budget this kit has, and V69 wasted
all three rungs at once.** The rule that would have caught it:

> **Before choosing a threshold, compute the producing lane's own reachable output range at the
> operating point you care about — its clamp, its LERP ceiling, its index axis — and state that number
> in the build note. A downstream GATE's width is not that number.**

🛑🛑 **SECOND INSTANCE, V84, and it nearly cost a verdict — 2026-08-09.** V84's `b7`/`b6` tested
`|r24| ≥ 1024` on a lane whose input **never exceeded `|r1| = 201`** ⇒ they read **0.0 across 68,235
frames in BOTH arms**, and that was read as *"the lever was out of force."* It was not: **the rung could
not have fired either way.**
📋 **THE RULE IN ITS SHARPEST FORM: a falsifier only fires if it COULD have fired.** Apply it to every
pre-registered falsifier and every abort criterion, **including the ones that come back clear** —
V85's damper abort criterion "passed" on **22.4 s** of engaged ≥80 km/h exposure, which is not a pass.
🛑 **This is RULE 5 (a null is only a null if the lever was in force) applied to the INSTRUMENT rather
than to the lever, and the kit has now made the error at both ends.**

**V69 bit4 — `gp-0x6ad4` ≥ +4096 — was STRUCTURALLY VACUOUS and could never have fired, on any build,
on any drive.** The lane is clamped to **±CEILING = MIN of three LERPs**; the binding one is
`0xC67C2`/`0xC67C8`, indexed on **voted vehicle speed**, **max 1024**, and it **starts at ZERO**. At the
four ratchet episodes' speeds (**4.9 / 6.8 / 7.8 / 8.0 km/h**) CEILING was **164–341** ⇒ the 4096 test
sat **12–25× above the lane's entire reachable range**.
🛑 **ROOT CAUSE: the design read the ERR *input* clamp `±0x2800` as if it were the lane's OUTPUT range.**
★ It also explains, retroactively, **why V56's mute of this same lane changed nothing** — there was
very little there to mute at creep.

Two more, from the same build, both worth carrying forward:
- **bit5 (`gp-0x6b62` ≥ +4096) was INSENSITIVE, not vacuous.** Reachable max **5786**
  (`|gp-0x6b5e| ≤ 4762` from the trapezoid `0xC66CC` X = [−384, −128, 128, 294, 384],
  Y = [0, 4762, 4762, 717, 0] with `0xC63C2` = 1024, plus a latched `|sVar8| ≤ 1024`), so 4096 was
  **71% of full range** and the rung only saw the **top 29%**.
- **bit6 (`gp-0x6ada`) had NO EXPOSURE.** The replay predicts **~1** one-sided hit on route `4f`;
  observed **0**; **p ≈ 0.37.** That is a power problem — **not** the V64 gate failure — but it is also
  **not a positive control**, so bits 5/4 could not be interpreted against it.

⇒ **All three rungs were one-sided, and both middle rungs were sized against a downstream gate width.**
Budget a probe the way you budget a cave: **enable + raw input + a rung whose range you have computed.**

### ★★★ THE RATCHET'S Q IS MEASURED — Q ≈ 40 at f0 = 7.793 Hz (2026-08-04, route `50`)

**[EVIDENCE]** From a **12.81 s provoked episode**. ★ **The invariance test is what makes it real:** Q
reads **39.0 with a window cap of 54** and **40.0 with a cap of 111** — a window-limited estimate would
have **doubled** when the cap doubled. It did not. ⇒ **ζ ≈ 0.0125, ~3× more lightly damped than the
21 Hz mode.**
✅ **Q ≈ 40 CONFIRMS the record's Q ≈ 36.** 🛑 **The only thing SUPERSEDED is *"Q is not measurable at
NFFT 256"* — the claim that it could not be measured, not the value.**
✅ **And it is NOT contaminated by the driver's input** — the episode reconciles exactly with the
transition trace below (envelope-based p-p, 2 × 2,452 = 4,904 ≈ 4,894; speed span matches seg1
`t` ≈ 33–46, the **post-engagement** window, not the cranking).
⚠ **It rests on ONE episode** — a second ≥10 s episode would make it two. ⚠ **f0 drift inside the
window would DEFLATE Q, so 40 is a LOWER BOUND**, not a point estimate.

#### 🛑🛑 ENGAGEMENT-**REQUIRED**, NOT CONDITIONAL — AND NO BUILD HAS EVER MOVED IT

**[EVIDENCE]** Grip confound removed (both arms **hands-off**, `|lowpass(tq,3Hz)| ≤ 300`, creep
< 4 m/s), pooled over four routes and four builds:

| route | engaged hands-off | manual hands-off | Fisher p |
|---|---|---|---|
| V70 `r50` | 4/5 = **80%** | 0/35 = **0%** | 5.5e-05 |
| V69 `r4f` | 22/27 = **81%** | 0/20 = **0%** | 9.4e-09 |
| V62 `r37` | 31/39 = **79%** | 0/39 = **0%** | 2.3e-14 |
| V59 `r2c` | 16/17 = **94%** | 0/24 = **0%** | 1.7e-10 |
| **POOLED** | **73/88 = 83.0%** | **0/118 = 0.0%** | **3.8e-41** |

**ZERO hits in 118 manual hands-off creep windows / 302 s.** ⇒ 🛑🛑 **the rate is BUILD-INDEPENDENT
(80/81/79/94%) — NO BUILD IN THIS KIT HAS EVER MOVED THE RATCHET.** ⚠ **This SUPERSEDES the earlier
"engagement-conditional, 44/46 windows" statement.** ★ Converse: **a hand on the wheel SUPPRESSES it
while engaged** — V59 94% → 14% (p = 3.5e-4), V69 81% → 37% (p = 4.5e-3).
★★ **What that buys: `0x454FE` is a genuinely UNTESTED lever for the ratchet** — it has not been on the
car during a single one of those four measurements (V59/V62/V69/V70 are all post-V53, all stock at
`0x454FE`). ⚠ **A reason to restore it; NOT evidence it will work.**

#### ★★★★ THE TRANSITION TRACE — the mechanism, second by second, at constant speed

**[EVIDENCE — 4th-order Butterworth 6–9 Hz, `sosfiltfilt`, 2.56 s windows, hop 64; mono = seg1 `t` +
100.6; orchestrator-verified from `_scratch/cache/r50/r50s1.npz`.]**

| seg1 `t` | mono | `lat` | effort | **RAW p-p** | **6–9 Hz p-p** |
|---|---|---|---|---|---|
| 27.5 | 128.1 | 0.00 | 2646 | **6502** | **190** |
| 33.3 | 133.9 | 0.00 | 942 | 3237 | 136 |
| **33.9** | **134.5** | **0.06** | **320** | 1423 | **134** |
| **34.6** | **135.2** | **0.31** | **441** | 3182 | **1179** |
| 36.5 | 137.1 | 1.00 | 998 | 5070 | **2452** |
| 46.1 | 146.7 | 1.00 | 1548 | 4204 | 910 |
| 46.7 | 147.3 | 1.00 | 2129 | 3019 | **273** |

★★ **THE HEADLINE PAIR:** `t = 33.9` (`lat` 0.06, effort 320) → **134 counts** vs `t = 34.6` (`lat`
0.31, effort 441) → **1,179 counts** — **8.8× in 0.7 s**, with **speed FALLING (1.75 → 1.60 m/s)** and
effort roughly flat, so **speed moves the WRONG way for any confound.** The death is as sharp: effort
**1,548 → 2,129** over 0.6 s collapses the band **910 → 273.**
✅ **THE 6,502-vs-591 INSTRUMENT DISCREPANCY IS SETTLED:** at mono 127.5–128.1 the car is at `lat` 0.00,
effort 2,550–2,646, and the 6–9 Hz content is **190 counts** ⇒ **6,502 is RAW BROADBAND — the operator
cranking, not the ratchet.** ★ **The ratchet proper runs seg1 `t` ≈ 34.6 → 46.1 (mono 135.2 → 146.7),
~11.5 s** ⇒ 🛑 **burst #0's ratchet onset is mono ≈ 135.2, NOT 123.69 — correct any text using the
older figure.**

#### 🛑 A CORRECTION TO THE OPERATOR'S FRAMING — the causal order, not the facts

**His hard MANUAL provocation produced NO ratchet at all** (effort 2,500–2,900; 6–9 Hz p-p only
**422–797**, prominence **1–6**). **The manoeuvres SET UP the condition** — creep, loaded wheel, LKAS
about to take over — **and the ratchet fires when LKAS ENGAGES AND HE LETS GO.** ★ **Both parts of his
account are correct; the causal order is the other way round. His report is corroborated, not
contradicted** — he named the right segments before the data did.

Also from route `50`, all [EVIDENCE]: **10 windows / 25.6 s at ≥1200 counts p-p, max 4,894**;
zero-crossing f0 **7.75 Hz**; **speed-invariant** (Theil-Sen **+0.068 [+0.005, +0.247]** Hz per m/s vs
wheel-order-1's **0.482**); present in the bar (prom **59**), angle-rate (**22**) and angle (**15**) but
**NOT in openpilot's command (1.25)** ⇒ **the loop closes inside the EPS + plant**; and
**per-engaged-window ratchet rate is identical across builds** (V70 **32.1%**, V69 **34.4%**, V62
**32.8%**) ⇒ **V70 did not add ratchet events**, consistent with the build-independence above.

⚠ **A DEFERRED LEVER THIS RE-OPENS, and it is the most under-examined result in the archive.**
**Base-assist damping is EXACTLY ZERO below ~35 km/h** (FactorC `0xD27BC` Y[0] = 0, multiplicative)
while **the ratchet lives at 4.9–8.0 km/h with Q ≈ 40.** **V47 raised FactorC and FactorE TOGETHER and
reported *"marginally quieter at 5 mph"*** — and was filed **null against the 21 Hz vibration**.
🛑 **That positive whisper has never been evaluated against the RATCHET.**
★★ **AND IT IS NOW MATERIALLY MORE COMPELLING:** *engagement-required* + *hands-off-conditional* +
*Q ≈ 40* + *base-assist damping exactly zero below ~35 km/h* fit into one picture — **at creep, the
driver's hand is the only damping in the system.** ⚠ **Still deferred**: it is a two-cal change on a
lane V47 already touched, and it deserves its own single-variable drive. **Do not stack it on V71.**

---

### 🛑 THE STATE-4 CADENCE IS REFUTED AT INSTRUCTION LEVEL (2026-08-04)

**[EVIDENCE — gp-relative *and* absolute encodings both checked.]**
**`gp-0x68ad` can NEVER be set in the field.** Both SET paths need permanently-zero flags: `gp-0x437c`
(a UDS artifact) and — **newly closed** — `gp-0x679d`, whose sole writer `FUN_000567c0` @`0x567e2` reads
`gp-0x67ba`, and **`gp-0x67ba` has exactly ONE access image-wide and ZERO writers.** `FUN_00019970`
opens with `if (gp-0x68ad != 1) return;` ⇒ **4 → 5 NEVER FIRES; state 5 is DEAD CODE on the road.**
**`gp-0x6d78` bit 15 is a ONE-WAY, OR-ONLY latch** — 15 sites, one writer (`FUN_000197b8` @`0x197ca`,
`|= 1<<n`), **no clear anywhere image-wide** ⇒ **4 → 10 is a ONE-SHOT DRIFT; 10 → 4 can never fire
afterwards.**
⇒ 🛑 **State 4 is STICKY once entered, then leaves permanently. There is NO periodic cadence** —
refuted structurally, not merely unconfirmed. With V70's bit5 at **0.0000%**, **the reachable set on a
normal drive is {4, 11}.**
⚠ **Carry the tension:** the V42 substitution is **asymmetric** (clamps increases, passes decreases) so
continuously active it should print a **rectified** waveform — **yet the ratchet measures SYMMETRIC**
(skew −0.16…+0.06, crest 2.07–2.45 vs a sine's 1.414). **Evidence against it shaping the CURRENT
ratchet.**
🛑 **[OPEN]** what sets `gp-0x6d78` bits 15/16 mid-drive — `FUN_000197b8` has **21 callers,
untraced**. That decides whether state 4 is sticky for a whole drive or only briefly.

---

### 🛑 THE AGGREGATOR IS ELIMINATED — all EIGHT zero-type range gates are VACUOUS (2026-08-04)

**[EVIDENCE — every ceiling byte-read.]** Each gate is capped by its own producer's ceiling at or
inside its gate window, **on every drive, every build**:

| lane | producer ceiling | gate window |
|---|---|---|
| boost | 512 | 2048 |
| damping | **exactly 0 at creep** (FactorC `0xD27BC` Y[0] = 0, multiplicative; ≈ 35 km/h onset); ≤ 1024 at highway | 2048 |
| friction | 511 | 1024 |
| magnitude | ±0x3000 | **== window, exactly, inclusive** |
| LKAS | ±0x2800 | **== window, exactly** |
| `gp-0x6ade` | **0 writers** | — |
| resonance | max 1024 (**164–341** at the ratchet's speeds) | 2800 |
| return-centre `gp-0x6b62` | max 5786 | 8192 |

⇒ **the aggregator stage contains NO reachable hard nonlinearity**, joining the aggregator **SUM**
(V65, 120,049 frames). **The relay / limit-cycle framing for the aggregator is REFUTED — do not
re-propose it.**
★ Also [EVIDENCE]: `FUN_00036388`'s own counters give **~20–40 ms or ~1 s** periods — nowhere near
7.8 Hz ⇒ **it INHERITS the ratchet, it does not GENERATE it.**

---

### ★★★★ `gp-0x67fa` STATE-GATES THE WHOLE ASSIST CHAIN, AND STATE 10 SPLITS IT IN HALF — 2026-08-04

✅✅ **SETTLED ON-CAR 2026-08-04 — V70's bit5 (`gp-0x67fa == 10`) read 0.0000% of 18,010 frames**,
encoding independently verified. ⇒ **the aggregator ran** ⇒ **state ∈ {4, 5, 11}** ⇒ **`FUN_00036388`
and `FUN_000428d4` WERE INVOKED** ⇒ 🛑 **the `gp-0x67df` detector nulls on V64/V67/V68 are GENUINE,
and the state-gate explanation for them is REFUTED. Five builds vindicated**, on a **pre-registered**
prediction. ⚠ **It licenses *"the call was made"*, NOT *"the body ran"*:** `FUN_00046ea6(5)` on
`gp-0x18d0` bit 5 — the detector's second, independent entry gate — **remains OPEN.**
⊕ Combined with the state-machine refutation above, **the reachable set on a normal drive is {4, 11}.**
**The structural mapping below stands as written.**

**[EVIDENCE — instruction level, `FUN_0002214a` `0x2214a`–`0x22a84`.]** 🛑 **The guard wraps the `jarl`
IN THE COMMON CALLER, not inside the four functions.** Each has exactly one call site, all in
`FUN_0002214a` (RTOS **task 1**, 1 kHz) ⇒ **in a masked-out state the callee is NEVER INVOKED — no stack
frame, 0% of body.** Index is a plain `1 << (gp-0x67fa & 0xf)`, **no off-by-one** (`0x2214e` `ld.bu` /
`0x22172` `andi 0xf` / `0x2217c` `shl`, recomputed identically @`0x221bc`–`0x221c6`). **THREE masks:**

| site | mask | states | what it gates |
|---|---|---|---|
| `0x221d6` | **`0x830`** | **{4, 5, 11}** | `FUN_00036388` @`0x22882` (return-to-centre) · `FUN_000428d4` @`0x22926` (**the OSCILLATION DETECTOR**) |
| `0x22518` | **`0x930`** | **{4, 5, 8, 11}** | `FUN_00028ea6` / `FUN_0002b422` / `FUN_0002b57a` (**ARBITRATION = `gp-0x6806`'s PRODUCER**) |
| `0x2269a` | **`0xc30`** | **{4, 5, 10, 11}** | `FUN_0003a382` @`0x226a0` (residual lane) · `FUN_0003aa2c` @`0x2291e` (**THE AGGREGATOR**) |

⇒ **IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE RETURN-TO-CENTRE LANE
AND ARBITRATION DO NOT. Assist is delivered from a stale `gp-0x6806`.**

★ **State 10 is REACHABLE IN NORMAL OPERATION** — written twice in `FUN_00019970` (the state-4 handler):
`0x199CC` (diagnostic, `tp+0x74d0 == 0xa`) and **`0x19A72` (the NORMAL path)**, the latter gated on
**bit 15 of `gp-0x6d78`** with bit 16 (→ state 11) taking priority. Writer set over **33 `st.b` sites**
(Ghidra and a raw LE byte scan agree exactly, no undercount): {1,3,4,5,6,7,8,9,10,11}, max 11.
⚠ **[OPEN] what bit 15 of `gp-0x6d78` means** — that decides how *often* state 10 is visited, not
whether it can be.

🛑 **THIS IS A LIVE ALTERNATIVE EXPLANATION FOR THE FIVE-BUILD DETECTOR NULL** (`gp-0x67df` 0/14,980
V64, 0/186,321 V67, 0/53,991 V68): *"`FUN_000428d4` was never CALLED"* has **never been on the table**
and has the **identical signature** to *"it ran and found nothing."* Every *"the detector is exhausted /
the oscillation-gated approach is closed"* verdict in this file inherits the caveat.

⚠ **BUT V67's OWN PROBE ARGUES AGAINST IT, AND THIS MUST BE QUOTED ALONGSIDE — NEVER WRITE THE CLAIM
WITHOUT IT.** State 10 is absent from `0x930` too, so arbitration — `gp-0x6806`'s producer — is **also**
skipped there and the flag would go **STALE**. V67 measured **`gp-0x6806` == `latActive` in
150,302/150,327 = 99.983%** of frames, all **25** disagreements single-frame transition edges. **A stale
flag cannot track transitions that closely** ⇒ **the ECU is predominantly NOT in state 10 while engaged,
and the detector nulls are probably GENUINE.** [BELIEF — indirect.]

✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and is NON-VACUOUS IN BOTH DIRECTIONS:**
**bit5 ≈ 0** ⇒ state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated**;
**bit5 materially non-zero** ⇒ **the nulls were on the gate** and the detector programme needs
replanning.

⚠ **THE DETECTOR HAS A SECOND, INDEPENDENT ENTRY GATE, AND IT IS STILL OPEN.** `FUN_000428d4` is also
gated on **`FUN_00046ea6(5)`** — bit 5 of `gp-0x18d0`/`gp-0x18d4`, a fault/DTC-style bitmask, falling to
a fixed `0x8000` sentinel if set. 🛑 **This file's earlier closure of that question established only
that the FUNCTION has one caller image-wide — NOT that the BIT is clear in operation. Those are
different claims**, and only the first was ever checked. The other three gated functions have no such
secondary gate.

🛑 **AND bus `STEER_STATUS` IS NOT `gp-0x67fa`.** Route `4f` reads `ST = 0` on 47,990/47,990 frames
*while the car steered*, and **state 0 is in no mask**. **Any reasoning that equated them** — e.g.
*"ST==4 fires 0/37,922"* as evidence about `gp-0x67fa == 4` — **is invalid.** [VERIFIED] **State 4 sits
inside all three masks** and is where the V42 governor ratchet substitution used to fire.

⚠ **PROVENANCE, carry it:** decompiled against **stock `code.bin`**, with the 33 writer sites
cross-checked **byte-identical in `_v68_plain_image.bin`**. The **dispatcher itself was NOT decompiled
from a V68/V69 image** — high confidence it is unchanged (far outside any cave region), but that is
**BELIEF by adjacency, not EVIDENCE.**
⚠ **`mcp__ghidra__get_xrefs_to` returned "No references found" for this RTOS task entry** — a null from
that tool is never load-bearing. A `jarl` Format-V scanner written to cross-check it returned **zero
hits for functions Ghidra had just given callers for**, from a mask bug: bits 15:11 are **reg2, not
opcode**, and `disp = ((hw1 & 0x3F) << 16) | hw2` sign-extended from **22 bits**. **Anchor any such
scanner on a known site and assert it.**

---

## Part 3 — Machine-generated per-build delta (vs stock `code.bin`, app region only)

Regenerate with a byte diff restricted to `[0x13000, 0x100000)`.
⚠ **A whole-file diff is meaningless** — `build_*.full_image()` writes `0xFF` filler below `0x13000` and a
naive diff reports 51,137 bogus bytes.

`0x13109` and `0x14120` appear in every build: they are the version-string bytes (`-`→`,`, giving
`39990-TVA,A160`). **Every modified build shares that string, so an rlog cannot identify which build is
flashed.**

| build | bytes | code edits (beyond version string) |
|---|---|---|
| v29–v33, v36, v37 | 27–42 | none — cal-only |
| v38 | 126 | none — cal-only (first to touch `0xE4000`/`0xE5000` bootloader blocks) |
| v39 | 174 | `0x3AC78` + cave `0xC4B34-C4B5F` |
| v40 / v41 | 162 | none — cal-only (`0xC5030`, `0xC521A`, `0xC5232`, `0xC6206/08`) |
| v42 | 153 | **`0x454FE`** (the ratchet fix) |
| v43–v48a | 129–145 | `0x454FE` only |
| v48b | 282 | `0x2C482`, `0x354D4`, `0x35AA6`, `0x3A6CC`, … + cave — ☠ **BRICKED** |
| v49 | 130 | `0x3A836`, `0x454FE` |
| v50 / v52 / v52c | 226–254 | multi-site repoints + cave `0xC4B34` |
| v49p / v50probe / v51probe | 183–216 | `0x55C0E` hook + cave (read-only probes) |
| vcantxtest | 340 | `0x55C0E` hook + cave — ⚠ carries the **STRB=0x80 defect** |
| vfourframe | 853 | `0x55C0E` hook + cave — ⚠ **STRB=0x80 defect, never transmitted** |
| **vfourframe2** | 853 | same, **STRB fixed to 0x01**, authority + reference-model signals |
| **v53** | 855 | FOURFRAME2 byte-for-byte **+ `0xC62EA` 320→0** (+ CAL CRC). Exactly 6 bytes off FOURFRAME2 |
| **v54** | 58 | `0x55C0E` hook + **44-byte** cave `0xC4B34` (5-bit `gp-0x6966` authority probe → `0x14A` byte4 bits 7:3) + `0xC62EA` 320→0. **No mailbox cave** |
| **v55** | 82 | `0x55C0E` hook + **68-byte** cave `0xC4B34` (dual probe: damper variant bit + 4-bit `gp-0x6b98`) + `0xC62EA` 320→0 |
| **v56** | 84 | V55 byte-for-byte **+ `0xC6AFC`/`0xC6AFE` 32768→0** (+ CAL CRC). Exactly **6 bytes** off V55 — and only **2** are cal, because `32768` = `00 80` LE so just the high byte of each halfword moves |

---

## Part 4 — Flash status at a glance

🛑🛑🛑 **CURRENT, 2026-08-12 LATE — THIS IS THE LINE TO READ. EVERYTHING BELOW IT IS HISTORY.**
⚠⚠⚠ **SUPERSEDED AGAIN, 2026-08-13 (later) — V98 has ALSO flown and been superseded. ON THE CAR IS
NOW V99** (route `0x82`, 2 segments, flown 2026-08-13; see its own row above and the head of
`docs/STATE.md`). This is the **tenth** instance of the "row says UNFLASHED / stale ON THE CAR after
a newer build flew" defect in this file's own count.
⚠⚠ **SUPERSEDED 2026-08-13 — the block below is a RECORD, not the current state. V96 and V97 have
BOTH flown and been superseded. ON THE CAR WAS THEN V98** (route `0x81`, identity single-frame,
`0x14A` byte7[7:6] == 2, duty **1.000000** over 17,983 frames, fault-free). See the head of
`docs/STATE.md`. 🛑 The "⏳ V97 IS BUILT, VERIFIED AND UNFLASHED" line below is **STALE** — V97 flew as
route `0x80`. **Eighth instance of the "row says UNFLASHED after it flew" defect.**

**ON THE CAR: V96.** Flew as routes **`7e`** (806 s) and **`7f`** (838 s), 2026-08-12, **both
fault-free** (DTC-active duty 0.000000, zero sentinels, `OUTPUT_DISABLED` duty 0.0001).
**Identity proven SINGLE-FRAME:** `0x14A` byte7 bit 6 = **1 on 100.0000 % of 164,096 frames**; V94
carries the 74-byte V90 cave and cannot write byte 7 at all.
⇒ **V94 is NO LONGER ON THE CAR, and its `0xCBE74` cut is already off it** — V96 carries V92's
calibration byte for byte. **No revert is pending.**
⏳ **V97 IS BUILT, VERIFIED AND UNFLASHED** — `0xC63AC` **102 → 150** on a V96 base, **ONE BYTE** plus
its CRC trailer at `0xC6FFC`; image `7ac00904…c2b3`, rwd `78c674a8…7372`; 131/131 assertions;
builder `analysis-2020accord/builds/v80_v107/build_v97_tva.py`. **The flash decision is the operator's.**

🛑🛑 **THIS FILE AND `STATE.md` BOTH SAID "V94 IS ON THE CAR" FOR A FULL SESSION AFTER V96 FLEW.**
Seventh instance of the "row says UNFLASHED after it flew" defect, and this time it **cost work** — it
sent an analyst to close a verdict with *"fly V96, S2 answers it"* when V96 had already flown and its
regressor was 34× over-range (S1 **and** S2 void).
⇒ **NEW MANDATORY CLOSE-OUT GATE, mechanical:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`, reconciled
against the identity bit from the most recent route. The previous rule ("write the flight result in
the same pass that scores the flight") only fires if someone remembers. This one fails loudly.

🛑 **DEFECT, OPEN: `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` stops at ~V81.** V83a→V97 — **fifteen
builds, including every cell the last four sessions actually moved** (`0xCBE74`, `0xC40D2`, `0xC40BC`,
`0xC40D4`, `0xC640A`/`0xC640C`, `0xC63A6`, `0xC63AC`) — return **NOTHING** to the by-address grep
`CLAUDE.md` makes mandatory before proposing a calibration edit. That is precisely the failure the file
exists to prevent, and it was already backfilled once (V76–V81, 2026-08-07) before falling ten further
behind. **Fix = APPEND** (the rows are hand-written narrative; there is nothing to regenerate from)
**AND make the row-write part of the four-part close-out deliverable**, or the next backfill is due at
~V110.

---

🛑 **SUPERSEDED, 2026-08-07 (night).**
Flash order since V70: **V71C → V72 → V73 → V74 → V75 (☠ hard fault, route `5e`) → V74 reflashed (☠ hard
fault, manual, over a bump) → V76 (route `65`, clean) → V80 (route `66`, NO fault — and the worst grinding
this car has ever produced).** **V78 and V79 were built and never flown**; V79 is renamed `SUPERSEDED-…`.
⏳ **V81 IS BUILT, VERIFIED AND UNFLASHED** — image `4ddbd0e2…d65b`, rwd `fc4d4f74…a109`; a **126-byte
cal-only revert from the flown V75** with `0xC407E` back to 511 and the friction table back to Honda's,
`k` = 1.5798 unchanged. **The flash decision is the operator's.**
✅ **V76, V78, V79, V80 and V81 all now have rows in Part 1** (backfilled 2026-08-07 from the build
scripts, the plain images on disk and the 08-06/08-07 handoffs — this file had been five builds behind,
which is precisely the gap it exists to prevent).
🛑 **The `k` ladder, for anyone reaching for a damper dose:** V74 **0.5799** (flown) · V76 **1.3866**
(flown clean) · V75 **1.5798** (flown, fixed the grind, hard-faulted on `0xC407E`) · V78 **2.0840**
(built, never flown) · V79/V80 **4.1597** (V79 never flown; V80 flown — worst grinding ever).
🛑 **`docs/STATE.md` remains the authority for what is on the car.**

🛑🛑 **STALE BELOW THIS LINE — 2026-08-06.** The "CURRENT" line that follows was written at V70 and has
not tracked V71→V76. **`docs/STATE.md` is the authority for what is on the car.** Two things this
section must not be read as saying: **V74 and V75 have BOTH been flashed and BOTH hard-faulted**
(see their row in Part 1 and RULE 8b), and **`k* ∈ (0.580, 1.580]` is VOID** — no build in the current
lineage has demonstrated safety. ⏳ **V77 and V77B are BUILT and UNFLASHED** (`0xC63A0` 2048→1024 on the
V74 and V75 bases respectively); **neither is clearance to fly** — Part 1 carries their SHAs.

🛑 **CURRENT, 2026-08-04: the image on the car is V70** (flashed, driven route `50--50f2e00e8f`;
image `3760d9c0…`, RWD `0bdfb0da…`). Flash order since V55: **V56 → V57 → V58 → V59 → V60 → V61 →
V62 → V64 → V65 → V67 → V68 → V69 → V70.**
⏳ **V71 IS BUILT AND UNFLASHED** — V70 carrier + **`0x454FE` `ba`→`b5`** (restore V42's ratchet fix) +
**`0x3AB76`/`0x3AC20` `aa`→`a9`** (restore V62's ×2 on BOTH lanes) + the mode-10 surface
(`0xD2A7E`/`0xD2A80`/`0xD2ABA`/`0xD2ABC`) reverted to stock + a probe that reads **the gain in force**
(bit6 `gp-0x671d != 0`) rather than a lane output. Its rate lane is **byte-identical to V62/V65**, which
flew twice, both flight-clean. CRC blocks `0xC4FFC` + `0xD2FFC`.

★★ **THREE V71 SIBLINGS WERE BUILT, ALL UNFLASHED, ALL RESTORING `0x454FE`. Orchestrator-verified from
the image bytes.** 🛑 **They are NOT separable on the wire — the filename is the only pre-drive
discriminator** (A and C share a byte-identical cave; B differs by one cave byte that never reaches the
payload).

| | image SHA256 | rate-lane levers | probe |
|---|---|---|---|
| **V71A** | `acc62e0930c9fa8f5176e22d1751f3f9544b1228c90d0b1e09188c67448c78e5` | both `sar` → `0x9`; flat 2.000× at every speed | `gp-0x6ada` (r24) |
| **V71B** ← recommended | `d4543d02b2fa113df7ab394ba0131859e3193a8c75604ddf3165768b6e5dd3f4` | `gain_A` rec0/rec1 Y[0..3] ×2 ⇒ 2.000× ≤10 km/h → **EXACTLY 1.000× ≥50**; r24 stock | `gp-0x6adc` (r26) |
| **V71C** | `30b63fdd59bdf9221fec0942d9ccdbc6f0582d2e8c3acbc4d30b0acd89ff1607` | gate `fb` + `0xC6446`=5244 + **`0xC6444` 512→3072 (r26 CUT REMOVED)**; `sar` stock | `gp-0x6ada` (r24) |

rwd SHAs: A `5c5138d960192d7d0a4e37301a0c82ad29e02ccff0cc116b62d6ac1cb0337e9e` · B
`3bc9347aa54449b2ccfe7896b076f57bf0b932ed1de3d41ae45be838ceaa8157` · C
`4ce568b6fd85ad0ad2a5a6159ede09276f705a1e00d66ac129b8f60679c4e609`.
**V71C is 71 bytes off V67** = **61 differing cave bytes** + `0x454FE` + `0xC6445` + 8 CRC (61+1+1+8 = 71),
in **9 strictly contiguous runs**. ⚠ **The cave is 68 bytes but only 61 of them DIFFER** — V67's cave and
V71C's coincide at 7 positions, so the cave region is **not** one contiguous run. *(Corrected: an earlier
figure of "5 runs / 66-byte cave" came from a diff script using a +3 merge tolerance, and summed to 76.
Re-derive run decompositions with STRICT contiguity.)*

🛑🛑 **A SCALAR GATED ARM CAN NEVER BE HIGHWAY-CLEAN WHILE DOSING AT CREEP** — the arm **replaces** a
LERP that rolls off with speed, so `arm/LERP` **rises** toward highway (V67/V68 and V71C both deliver
**r24 2.438× at 100 km/h** vs V69/V70's 1.000×). No `0xC6446` value fixes it: lowering it enough for
highway puts creep **below** stock. ⇒ **only the ungated speed-shaped surface can be structurally stock
at highway.** ⚠ Consequently **V67/V68 differs from the highway-clean builds in BOTH lanes** (r26 cut
~5× **and** r24 raised 2.438×), so **V71C removes only one of two candidate causes**; if the highway
symptom is r24's, V71C will not fix it. Named follow-up: `0xC6446` 5244 → ~2151–2400.

⚠ **INT32 headroom at `mul r8,r6` @`0x3AB72`:** stock / V71A / V71C = **46.87%**; **V71B = 93.75%** —
the band V62's own build note rejected. **No overflow is reachable** (`ld.hu` bounds `avg` at 65535),
but V71B carries half the margin. `0xC6444` ceiling **6553** = `2³¹ / ((5120 × 65535) >> 10)`.
🛑 **A first V70** (`…LKASGATED-V68CONTROLPATH…`) restored V67/V68's scalar arm and **the operator
overrode it** — it re-introduces the high-speed grind. ✅ **It is renamed
`SUPERSEDED-DO-NOT-FLASH-…`** (`accord-firmwares` `9d44efc`), filesystem-verified: **exactly ONE
flashable `V70` file remains.** ⚠ The rename was load-bearing — its cave is **byte-identical** to the
current one, so the probe could not have told them apart on-car and the filename was the only
discriminator. ⚠ Current SHAs and control path live in `docs/STATE.md` (they change on every re-cut);
V70's probe design is its own row in Part 1. ⚠ **The narrative below was written incrementally and its
"on the car now" sentences are stale as of the build they were written for — this line is the
authority.** V69's and V70's on-car results are in their Part 1 rows.

**Flashed and currently the on-car baseline lineage:** V38 (fault-free) → V42 (ratchet fixed) → V43, V44,
V45, V46, V47, V48A (all null) → V48B (☠ bricked, recovered by reflash) → V52C (null for vibration,
changed manual feel) → FOURFRAME (telemetry, silent — STRB defect) → V53 (2026-07-27: steer-to-zero
✅ CONFIRMED; four-frame telemetry absent and the null uninterpretable — see the box in Part 1) →
**V54** (2026-07-27: ★ **the probe FIRED** — first working firmware telemetry channel in this kit;
`0xC6AF0` direction measured and the block lifted; fault-free).

→ **V55** (2026-07-28: the dual probe FIRED and partitioned the hypothesis space — ★★ **the ~21 Hz IS in
`gp-0x6b98` and the loop is INTERNAL to the EPS**; openpilot is 8.7× too small even with the LKAS
low-pass deleted, and while RAILED its 21 Hz is exactly 0 yet the command still carries 105.8 counts;
sensor→command transfer is **flat 0.19→0.22 from 1 Hz to 21 Hz**; damper bit7 = 1 ⇒ V44/V47 hit the LIVE
tables). Fault-free.

**⚠ V55 is the image on the car now.** It does **not** carry the V42 ratchet fix (`0x454FE` is stock
`0x65BA`), same as V38/V53/V54/FOURFRAME.

★ **V54's telemetry result — the `0x14A` byte4 bits 7:3 piggyback is PROVEN end to end.** A/B against the
V53 drive is a single bit and it is exactly ours: byte4 = `0x07` ×5,994 (100%) on V53 → `0x0F` ×5,989
(100%) on V54, stock `STEER_SENSOR_STATUS` bits 2:0 preserved, `canValid` true in 5,711/5,713. **Use this
channel for all future firmware telemetry.**

→ **V56** (falsified, reverted) → **V57** (decouple + deadband probe, fault-free) → **V58** (angle-rate/
boost-lane probe, fault-free, 14 segments) → **V59** (2026-07-30, route `2c`: ★★ **the boost-index DEPTH
probe FIRED and answered** — 50,963 frames, 100% live, 100% thermometer-monotonic, fault sentinel 0.000%,
`ST==4` 0/50,963, FLIGHT-CLEAN. The 42.19 Hz pump = **2× the 21.09 Hz mode**, engagement-gated, **absent
disengaged** (bit5 never toggles in 61.2 s) — but **MARGINAL**: eps 0.013–0.169 across every combination
of task rate × series question, against a threshold that cannot be pinned because the passive Q is not
measurable (no ring-down exists: 66 candidates, longest **0.63 cycles**)).

★★ **The turn this drive produced — the OPERATOR's hypothesis, now the leading explanation.** The torque
sensor sits between wheel and road, so LKAS motor torque twists the column and is **read back as driver
input**, then boosted. A positive feedback loop, and **traced: there is NO motor-command feedforward
compensation anywhere in the chain** (`gp-0x6b98` appears only as a sign input to the `gp-0x6ac2`
ceiling detector, and in `FUN_00043e44` whose output has **zero readers**). Measured: the
**command→torsion-bar transfer function peaks at 21.09 Hz — the GLOBAL max over 3–46 Hz** — 15.6×
baseline hands-off (K=5, coh 0.654 vs null 0.527), 25.7× any-hands (K=53). ⇒ **the pump is probably a
passenger; the loop is the driver.**
🛑🛑 **CORRECTION OF RECORD, 2026-07-31 — V52C DID NOT "HALVE THE MODE". THERE WAS NEVER A NUMBER.**
This paragraph used to cite V52C as the loop hypothesis's best supporting evidence. **Struck.**
`−6.1 dB at 21 Hz` and `halved the mode` are **the same statement**: V52C's EMA (α = 74/1024, 1 kHz)
has `|H(20.9 Hz)| = 0.4963`. It is **the filter's designed attenuation, not a measurement.** The phrase
was authored in `HANDOFF-2026-07-28-v55-...md:205` as a **caveat on why V52C's NULL was weak evidence**
and mutated into a positive result two handoffs later. Every contemporaneous record — including the
operator's own words in `HANDOFF-2026-07-26-route13-...md:8` (*"V52C did not fix the vibration; it
clearly changed manual feel"*) — says **NULL**. **No V52C rlog exists** (routes on disk are
`13,1a,1b,1c,24,28,29,2b,2c`; the V52C window `08`–`12` is absent machine-wide and was never in git),
so the "re-derive it first" instruction was unexecutable. ⇒ The loop hypothesis rests **only** on the
21.09 Hz transfer peak and the traced absence of feedforward. ⚠ Not a falsification of the loop — a
2× gain cut carrying +57–61° of lag is a poor stabiliser — but it **is** weak-to-moderate evidence
against the `gp-0x4f60` **VALUE** path specifically.

### 2026-07-31 — V60 FLASHED → NULL, and V61 built

🛑 **V60 (`0xD2006` 102→43) FLASHED and driven 2026-07-31 → NULL on the vibration.** Operator: *"It did
not fix the vibration issue."* No rlogs (V60 carries V59's probe unchanged, so there was no new
telemetry). **This is a result, not a wasted drive** — V60 was built as a **discriminator** and the
record predicted the null in advance. Pump causality was not settleable observationally (the index is
`|x|` of a bar-derived signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a
passive Q that V59 could not measure. ⇒ **the V58/V59/V60 parametric-pump arc is CLOSED.**
★ **It also closes `0xC63BA`** — byte-scanned, the readers of `gp-0x6b9a`/`gp-0x6ba6` are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer and V59's probe, so that cal's only
effect is on the same amplitude LERPs V60 just falsified. **Do not propose it as a grinding fix.**
⚠ Two more lanes eliminated, byte-verified: `FUN_00036c12` (`gp-0x6b26`) and `FUN_00036388`
(`gp-0x6b62`, the return-centre lane) read **no torque signal at all** — speed/motor-rate keyed only.

★★ **A structural finding that reframes every damper null: RTOS task 5 runs at 100 Hz.** The rate
divider `FUN_00014be4` is mod-100 on the base tick; boost `FUN_00034a72` and damping `FUN_00034350`
fire once per 10 task-1 invocations (integer arithmetic — clock-independent). ⇒ a ZOH costs
**37.6° average / 75.2° worst-case** transport lag at 20.9 Hz before any plant phase, so the
velocity-proportional damper **structurally cannot damp this mode** and may be anti-damping there.
**That is a second, independent reason V44/V47 were null**, alongside the FactorC speed-axis argument.
⚠ A datasheet audit then refuted the kit's clock chain — **PCLK is 40 MHz, not 80, and OSTM0 is NOT the
RTOS tick** (no arm in the EI trampoline `FUN_0001492a`; the divider's trigger `gp-0x42fc` is written
only by `EIIC 0x340` = TAUJ1I2). The 1 kHz/100 Hz figures **survive on ON-CAR measurement**, which never
used that chain. But **the FOC/TSG20 "~8 kHz" carrier likely halves to ~4 kHz** — treat as OPEN.

| lever | what | build | flashed | result |
|---|---|---|---|---|
| `0x3AB6C` `mul r1,r6,r0`→`mul r0,r6,r0` + `0x3AC16` `mov r1,r8`→`mov r0,r8` | ★★ **kill the torsion-bar RATE lane at BOTH taps of its shared value** `r1 = clamp(gp-0x4f62, ±5120)` | **V61** | ✅ **BUILT, UNFLASHED** | **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, same sign, shared polarity load @`0x3AB78`. **V39 killed only r24 and only *conditionally*** (cave @`0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright. **Byte-checked every flashed image: NO build ever had both dead** ⇒ each recorded null was uninformative about the lane. Two single-**BIT** `reg1` r1→r0 changes, opcode/reg2 byte-identical, **no cave** ⇒ GATE 1 vacuous. 5 bytes off V59; CAL CRC and `0xD2000`-block CRC both unchanged. ⚠ Expect a manual-feel change (phase-lead term in **base** assist, no LKAS-only decoupling point); reversible via V59 |

🛑 **A CORRECTION THAT MATTERS FOR THE FACTOR-C/E RECORD.** V44 raised FactorC alone → null. **V47
raised FactorC AND FactorE together** — byte-verified 2026-07-31 across the images (`v47` has FactorC
`Y[0]` = 235 *and* FactorE = (700,750,800), vs stock 0 and (0,140,539)). **So the multiplicative-chain
concern WAS handled: the simultaneous test exists, was flashed, and gave "marginally quieter at 5 mph,
no effect in motion."** V61 is the *additive dual* of that same trap, and unlike C/E its simultaneous
test has genuinely never been run.

**Built and UNFLASHED:** ★★ **V61** (above), plus ~~V60~~ (now flashed, null — do not re-flash;
null), plus **V55** (dual probe: damper variant bit + 4-bit `gp-0x6b98`
motor command, 82 bytes off V38), plus V49, V50, V51P, V52, VCANTX-TEST, FOURFRAME2. V53 and V54 are both
now flashed and no longer candidates.

★ **V55 is a PARTITION, not a lever.** Every falsified vibration lever in Part 1 — V39, V41, V42 ch.2,
V43, V45, V46, V48A, V52C — sits on the **command path** and assumes the ~20 Hz is *commanded*. V55
samples `gp-0x6b98`, the final merged command and the only path to FOC, to test that assumption directly:
if the mode is absent there, all eight were doomed by construction and the search moves to the plant.
A null BOUNDS the command's 20 Hz content to ~<512 counts (one level) against the sensor's ~550 rms; it
does not prove zero, and a 100 Hz probe still cannot separate 20 Hz from 80 Hz.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
