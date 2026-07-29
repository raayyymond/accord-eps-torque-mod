# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

---

## Part 1 — Lever index, by address

**FALSIFIED** = flashed and demonstrably changed nothing for its target symptom. It is not "untested".

| address | what it is | build | flashed? | on-car result |
|---|---|---|---|---|
| `0x2A1F0` disp `0x746C`→`0x7CD0` + `0xC6CD0`←3564 + `0xC646C`→891 | **the `0xC646C` DECOUPLING** — forward LKAS path gets a private gain word; the four feedback readers revert to stock | **V57** | ❌ **BUILT 2026-07-29, UNFLASHED** | 🛑 **CORRECTNESS FIX — expected NULL for the grinding** (≤0.28 dB at 22 Hz; of the **11** aggregator summands only `FUN_00036682` reads the cal, at −46 to −58 dB). Reader set independently re-enumerated: exactly **6** (1 forward, 1 dead in the `>0x2a30d` dead-copy region, 4 feedback). ✅ **no float mirror** — fresh 32-bit scan of `[0x7440,0x74A0)` → 0 hits ⇒ no V27 desync class. ⚠ **manual feel WILL change** (readers #3-#6 are not engagement-gated). ⚠ Reader #6 is **not** a second additive path — it modulates #5's hysteresis dead-band *width*. **Flash V55 first** | ⊕ **ALSO CARRIES THE DEADBAND-GATE PROBE** (V55's cave payload replaced, same base `0xC4B34` / hook `0x55C0E` / 68-byte extent): `0x14A` byte4 bit7=liveness, **bit6=(gp-0x6806==0) — the EXACT gate test the bus cannot give**, bit5=(gp-0x69b0!=0), bit4=(gp-0x6b30==0), bit3=(gp-0x6b30<0). Closes the parity hole in the deadband elimination (the packer's `andi 0x1` transmits bit0; the gate tests equality). Expected NEGATIVE |
| **`0xC6AFC` + `0xC6AFE`** 32768→0 | `FUN_0003a382` output-bound LERP Y[0]/Y[1] — the **branch-agnostic mute** of the whole `gp-0x6ad4` lane | **V56** | ✅ | 🛑 **FALSIFIED FOR THE VIBRATION *AND* HARMFUL — 2026-07-29, route `24`.** 21 Hz unchanged (**786×** engaged/disengaged speed-matched, vs V55's 877×) and the command's 21 Hz did **not** drop ⇒ **the lane is ELIMINATED as the 21 Hz source, all three branches at once.** ★ It also **cost damping**: operator reports damping removed, and an intermittent **8.69 Hz** line appears (1.18e8, 6.7× its neighbours, 15-20 m/s, engaged+hands-off). **REVERT TO V55.** 🛑 A 50% partial restore (`Y=16384`) is **not** a candidate — 0% and 100% already agree, so intermediate authority is bounded between two agreeing measurements |
| `0xC6450` | `FUN_0003a382` **Stage-A = the P term's own extra smoothing EMA** (1024 = exact unity) | **V46** | ✅ | ⚠ **RE-FRAMED twice.** 1024→32 = −12.6 dB at 21 Hz, one of three branches — *and* 2026-07-29: it was **re-introducing a defeated pole**, not filtering the lane. Moot now: V56 eliminated the lane |
| `0xC644A` | `FUN_0003a382` **Stage-C = the D term's own extra smoothing EMA** (1024 = exact unity) | **V43** | ✅ | ⚠ **RE-FRAMED — same reason.** 1024→64 = −7.1 dB, one branch of three. Moot: lane eliminated by V56 |
| `0xC643E` / `0xC6445` + `0xC6A72/86/9A/AE` | `r26` adaptive torque-rate gain surface | **V42** ch.2 | ✅ | 🛑 **FALSIFIED.** ⚠ **RE-PROPOSED AS "NEVER PREVIOUSLY PROPOSED" BY A SUBAGENT ON 2026-07-29** — r24/r26 are the two *unfiltered, 1 kHz, same-signed* torque-rate summands, so they look irresistible in any fresh lane audit. **They are both already flashed and null.** V42's own builder records why the combined-kill argument is weak: *"r24 carries a ±3 DEADZONE (cal `0xC61F6`) which is why V39's r24 kill was a no-op near zero"* — so V42 already killed the branch that was live near zero |
| `0xC6440/42/46`, `0xC61F6` | `r24` direct Sensor-B rate lane | **V39** | ✅ | 🛑 **FALSIFIED** — and near-inert by construction (±3 deadzone). See the r26 row's re-proposal warning |
| `0xD27C6` / `0xD27DA` | damper Factor C Y[0] — **variant-coded, entries 10/11**. 🛑 **2026-07-29: the axis is SPEED, not driver torque** — index load in `FUN_00034350` is `gp-0x6a5e` (voted vehicle speed, settled), X=(2240,3840,5120,8960) ≈ **35/60/80/140 km/h**, so `Y[0]=0` means *below ~35 km/h*. **V44 tested a mechanism that does not exist**; its on-car result stands, its rationale is withdrawn. The "2240 counts driver torque" figure is a **number collision** with the unrelated override curve at `0x29a74`. Invalid speed ⇒ factor defaults to **unity**, not zero | **V44** | ✅ | 🛑 **FALSIFIED** (Factor E re-zeroes the product). ✅ **2026-07-28: confirmed it hit the LIVE table.** PN `39990-TVA-A160` → key `TVAA1` → config row 2 → INDEX **10** → `0xD27BC`, exactly what V44 edited. ⚠ one-bit residual: the coded row is in EEPROM, not the flash dump, and the TVA family splits ({TVAA0,2,4}→idx 4). **V55 carries a telemetry bit for it** |
| `0xD2802/04/06`, `0xD2816/18/1A` | damper Factor E (motor-rate) deadzone — **variant-coded, entries 10/11** | **V47** | ✅ | 🛑 marginally quieter at 5 mph, **no effect in motion**. ✅ **2026-07-28: confirmed it hit the LIVE table** (same INDEX 10 chain as V44 → `0xD27F8`). ⇒ **the missing-damping hypothesis was genuinely tested and IS falsified** — do not resurrect it on a "wrong variant" theory |
| `0xC4120` + `FUN_0003a382` `uVar27`→256 | type-8 carrier mute | **V48A** | ✅ | ⚠ **RE-FRAMED — one branch of three, like V43/V46** |
| `gp-0x4f60` broad EMA (19 carriers → `gp-0x1300`) | V52C code cave | **V52C** | ✅ | ⚠ **WEAKER THAN IT LOOKS.** `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only **−6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the mode's content, it did not remove it. **Did change manual feel** (so the cave fired) |
| `0xC6206` (hands-off slew) | governor slew | **V45** | ✅ | 🛑 **FALSIFIED** |
| `0xC6206`/`0xC6208` ← `0xFFFF` | governor slew, both | **V40** | ✅ | ☠ **EPS lamp + no power steering at ignition.** Magnitude, not direction: `0xFFFF` made the guard never fire → snap-to-target → DTC 0x1d → motor off |
| `0xC5030`, `0xC521A`, `0xC5232` | motor-rate cap table | V40/**V41** | ✅ | 🛑 **FALSIFIED** (V41 = clean subtractive test) |
| `0x454FE` `0x65BA`→`0x65B5` | state-4 governor ratchet `bne`→`br` | **V42** ch.1 | ✅ | ✅ **CONFIRMED ROOT CAUSE** — fixed the hard-turn ratchet. Carry forward. ⚠ **NOT present in V38/FOURFRAME** |
| `0xC646C` 891→**1782**→**3564** | the LKAS gain — **shared sensor-scale, 6 readers, 4 on feedback paths** | **V22** (1782), **V38** (3564) | ✅ | 🛑 **CORRECTION 2026-07-29: this was TWO doublings, not one.** Byte-verified across the plain-image archive: stock/V9 = 891, V22-V37 = **1782**, V38+ = **3564**, with clamps `0xC61B2`/`0xC61B4` tracking each step (512→1024→2048). The old "891→3564 at V22" entry was wrong. ★ **The operator has driven all THREE values and reports NO change in manual steering feel** — and when disengaged the forward reader `0x2A1EE` is idle, so manual feel depends only on the four FEEDBACK readers. That is V57's experiment, already run in both directions, null. ⚠ What did NOT track the doublings: the pre-gain deadband `0xC61B8`, still 102 |
| `0xC61B2`/`0xC61B4` 512→**1024**→**2048** | forward-path clamps, doubled with the gain at BOTH steps | **V22**, **V38** | ✅ | correct and intentional. ⚠ `0xC61B8` (the pre-gain deadband, 102) was left behind at both steps — see the deadband box above |
| `0xC62EA` 320→**0** | low-speed steer lockout, 4.995 km/h → 0 | **V53** | ✅ | ✅ **CONFIRMED WORKING** on-car 2026-07-27. Route `1a`: `STEER_STATUS=0` in 5,995/5,995 frames (ST=3 never fires) and **226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h** — a cell that is structurally EMPTY on V38. No fault, no dash light |
| `0xC64B8` 112→0xFF | DTC-0x49 fail-counter gate | **V37** | ✅ | ✅ **gentle EME RESOLVED**, no dash-light regression |
| `0xC64B4-B7`, `0xC61C0-C5`, `0xC64E2` | `STEER_STATUS` debounce SM cals | **V36** | ✅ | ⚠ fixed gentle EME but **unmasked DTC 0x49** → superseded by V37 |
| `0xC6312` 320→65535 | gentle-EME decider torque gate | **V33** | ❌ | wrong gate (fires ~10 Hz benign) |
| `0xC65C4/C8/CC` + `0xC6768/6A/6C` | soft-EME boost floor (matched int/float) | **V31** | ✅ | ✅ soft EME resolved. **Do not desync the mirror pair.** ⚠ **V31 set the floor to 4096; V38 RAISED it to 5120** (float 5.0) — byte-verified in `_v54_plain_image.bin` vs stock `0/1536/2048`, and the golden model carries both. The V31 memory's 4096 is correct *for V31*; the car runs V38+, so 5120 is the live value. ★ **On-car proof 2026-07-28:** V54's authority probe read `gp-0x6966` pinned at the bottom bucket for 5,989/5,989 frames *including 17% of requesting frames at openpilot's ±4096 rail* ⇒ the V31 fixpoint is **self-stable and attracting, measured under railed command**, not merely argued |
| `0xC6202` | governor nominal | — | ❌ | **investigated and REJECTED** — buys nothing (4762 > max command), and `gp-0x4f64` is shadowed → fault `0x17`, hard-fault-eligible |
| `0xC6194` | "LKAS-only rate limiter" | — | — | **DEAD calibration** — its gain cal `0xC63CC` = 0 |

### 🛑 `0xC61B8` / `0xC64A3` — the pre-gain deadband + sign relay: ELIMINATED ON-CAR 2026-07-29

`0xC61B8` (=102) is genuinely **un-rescaled** — its siblings `0xC61B2`/`0xC61B4` went 512 → 2048 (×4) with
the gain and it never moved in 30+ builds — and the block **is** on the LKAS forward path (verified:
`r9` → `add r9,r11` @`0x2a1fc` → ×POLARITY×GAIN → clamp → `mov r11,r1` @`0x2a226` →
`cmove 0x0,r1,r16` @`0x2a2c2` → `st.h r16,-0x6b3c` @`0x2a2ea`; the `-0x6b38` store at `0x2a23c` is a
**diagnostic copy**, and a subagent stopped there and wrongly called the whole block diagnostic-only).

**But the gate is inert where the symptom lives, and this is MEASURED, not argued.** `gp-0x6806` — the
enable — is **transmitted**: CAN `0x18F` byte4 bit3 = `STEER_CONTROL_ACTIVE`. Route 24, 18,000 frames,
180 s: **`==1` in 96.26%, TWO transitions, max possible toggle 0.1 Hz** against a 20-25 Hz mode.

⇒ **Do not propose either cal as a vibration lever.** `0xC61B8 → 26` remains a legitimate *engage-ramp*
correctness fix (finishing the lockstep scaling) and needs its own justification. Deliberately excluded
from V57. Full detail: `memory/reference-accord-deadband-signgate-eliminated-on-car.md`.

### Untested levers currently on the table
| address | what | status |
|---|---|---|
| **`gp-0x6bbe` angle-rate tributary** (`FUN_00034a72`, reads `gp-0x6a56` at `0x34AB8`/`0x34E8E`) | the boost lane's **UNFILTERED steering-angle-rate error term**, scaled by two speed-indexed LERPs | ★★ **UNBUILT — and the lever INVERTS.** The mode is **996×** on `STEER_ANGLE_RATE` vs **877×** on torque, and this is that exact variable, unfiltered. First candidate ever outside the torque domain. 🛑🛑 **GATE 2 ANSWERED AGAINST CUTTING IT:** the torque EMA is a *multiplicative amplitude scale*, not an additive branch, and the core term is `rate_error = baseline − angle_rate` (`sub r6,r28` @`0x34e96`) with all-positive downstream multipliers and polarity +1 ⇒ **`gp-0x6bbe` ≈ −(gain)·angle_rate = viscous DAMPING.** **Cutting/muting it would REMOVE damping and likely worsen the grinding — the V56 error one build later.** ⇒ **the direction of interest is RAISING the gain to ADD damping at 22 Hz.** Cleanest single point: **`K1` @`0xD200C` = 43** (Q7; pointer base `0xCA324` = 1 hit image-wide). Others: `clampBound` `0xD2000`=666, speedLERP1 Y `0xD2834+0xE..0x18`, speedLERP2 `0xD20C0+0xC..0x14` — all inside the shared `DAMP_BLOCK` but **not** overlapping V44/V47's bytes (grep-checked). ⚠ **INFERRED, not time-domain simulated** — rests on `baseline` being slow at 22 Hz. 🛑 **Certify the sign by simulation before building.** ⚠ speedLERP2 is **FLAT** (5×512 = a fixed ±512 clamp); speedLERP1 is a hump peaking at 40 km/h, not a monotonic speed rise |
| ~~`0xC6AFC` + `0xC6AFE`~~ | moved to the flashed table above — **V56, falsified and harmful 2026-07-29** | 🛑 **DONE. Do not re-propose, at any authority value.** The GATE-2 "damping sign OPEN" caveat resolved *against* the mute on-car |
| `0xC6372` / `0xC636E` | boost-assist + damping lane **input EMAs**, `alpha = 205/1024` ⇒ only **−1.29 dB at 21 Hz** | **UNTESTED** — V44 pins both in `STOCK_CALS` as "the rejected candidate B". Candidate #2. 🛑 **GATE 2 severe**: `gp-0x6bbe` is base power steering; 60-73° of added assist-loop lag is the **V48B brick class** |
| ~~`0x2a1ee` retarget → `0xC6CD0`~~ | decouple 4× forward from the feedback readers | ✅ **BUILT AS V57, 2026-07-29 — moved to the flashed-candidates list below.** Still UNFLASHED |

### 🛑 The `0xC646C` readers are ELIMINATED — the elimination STANDS, on its structural leg

⚠ **Correction of a correction, 2026-07-29.** An earlier pass this session downgraded this elimination to
"not yet tested" on the grounds that the flat-transfer measurement came through a ~1-bit probe. **That
downgrade was wrong and is withdrawn.** Two things were established:

1. **Quantisation is EXONERATED, by construction.** Ground-truth lanes of known shape pushed through the
   exact encoder `clamp((x>>9)+8,1,15)`, Monte Carlo K=30 × 60 trials: the encoder reproduces H1's
   **shape** to within a few percent, including a true 0.93 Hz pole (true H1 ratio @21/@1 = 0.069,
   measured 0.071 ± 0.022). A memoryless nonlinearity applies one describing-function gain at every
   frequency — **it cannot flatten a pole.** H1 bias is −6%/−8% and shape-preserving; **coherence bias is
   DOWNWARD** (0.963-0.976 measured for a true 1.000), so the recorded 0.93 is a **lower bound**.
2. **But the transfer argument is still weak — for a different reason.** With K=3 and ±19.6% error bars,
   a single pole at fc=16.8 Hz (rel-sse 0.215) and flat (0.245) are **statistically indistinguishable**.
   ⇒ "the transfer is flat 1→21 Hz" is **UNCONFIRMED**, not refuted, and the rise 0.192→0.216 is **not
   significant** at ±20%.

⇒ **Rest the elimination on the STRUCTURAL kill, which is a byte fact and untouched by any of this:
`0xC646C` has 0 matches across all 468 instructions of `FUN_0003a382`**, so the carrier cannot read it.
The transfer argument is **corroborating only**. **No candidate cause returns to scope.**

#### The 2026-07-28 arithmetic, retained — still correct *given* a measured 0.221
```python
# FUN_00036682 (readers #5/#6) -- and it is not even a plain EMA: y[n-1] is subtracted twice,
# giving y[n] = y[n-1]*(1-2a) + a*K*x[n], so DC gain is K/2, not K.
alpha = u16le(img, 0xC63D2)        # == 6, NOT 14 -- byte-verified 3 ways, stock and V55 identical
fc    = (6/1024) / (2*pi*1e-3)     # 0.933 Hz
att21 = 1/sqrt(1 + (21/fc)**2)     # 0.0444  = -27.1 dB
(3564/32768) * att21               # 0.0048  contribution at 21 Hz
# MEASURED total sensor->command transfer at 21 Hz = 0.221  =>  reader #5 is 2.2% of it.
# Reverting the gain to stock removes 1.6% of loop gain = 0.14 dB.
```
And the measured transfer is **flat from 1 Hz to 21 Hz** — a lane behind a 0.93 Hz pole cannot do that.

### 🛑 `0xD_xxx`-region LERPs are VARIANT-CODED — resolve the pointer before editing
The damper factor tables (and the output clamp) are reached through **three** stages, and the selector is
an **EEPROM** value absent from every flash dump:

```
5-byte coded ID -> FUN_00057f8e() match vs 16 ASCII PN keys @0xCD000 (stride 0x24) -> ROW  (0-15)
                -> index byte @0xCD012 + ROW*0x24                                   -> INDEX (0-57)
                -> ptr_array[INDEX]                                                 -> the live table
```

**ROW is NOT INDEX.** Conflating them inverts the answer — it happened this session and nearly resurrected
a correctly-falsified hypothesis. Our car: `TVAA1` → row 2 → **INDEX 10**. Arrays: Factor B `0xC9CCC`,
D `0xC9DB4`, C `0xC9E9C`, E `0xC9F84`, clamp ptr `0xC77A0` — 58 entries each, one shared selector at
`gp+0x63fd` (**positive** gp offset). Assume any `0xD_xxx` LERP is variant-coded until proven otherwise.

### 🛑 New-mailbox CAN TX is an UNOBSERVABLE channel — do not build another one
`FOURFRAME` (STRB defect) and `FOURFRAME2`/`V53` (defect fixed) both produced **zero** frames of
`0x6A0`-`0x6A3` at the comma. The V53 null is **uninterpretable**, not negative: six IDs the stock
firmware genuinely broadcasts (`0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723`) are equally absent
from the same rlog while the three openpilot's DBC knows (`0x14A`, `0x18F`, `0x1AB`) run at 97-100 Hz.
Non-DBC IDs *are* logged (`0x669`, `0x750`, `0x674` appear and are in no Honda DBC), so "openpilot didn't
know the ID" is excluded. **Any future firmware telemetry must ride the `0x14A` byte4 bits 7:3 piggyback**
(4 successful flashes, hook at `0x55C0E` before the checksum) until a tap upstream of the gateway exists.

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

**Built and UNFLASHED:** **V55** (the one to flash — dual probe: damper variant bit + 4-bit `gp-0x6b98`
motor command, 82 bytes off V38), plus V49, V50, V51P, V52, VCANTX-TEST, FOURFRAME2. V53 and V54 are both
now flashed and no longer candidates.

★ **V55 is a PARTITION, not a lever.** Every falsified vibration lever in Part 1 — V39, V41, V42 ch.2,
V43, V45, V46, V48A, V52C — sits on the **command path** and assumes the ~20 Hz is *commanded*. V55
samples `gp-0x6b98`, the final merged command and the only path to FOC, to test that assumption directly:
if the mode is absent there, all eight were doomed by construction and the search moves to the plant.
A null BOUNDS the command's 20 Hz content to ~<512 counts (one level) against the sensor's ~550 rms; it
does not prove zero, and a 100 Hz probe still cannot separate 20 Hz from 80 Hz.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
