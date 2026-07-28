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
| `0xC6450` | `FUN_0003a382` Stage-A carrier pole (1024 = exact unity) | **V46** | ✅ | ⚠ **RE-FRAMED 2026-07-28 — NOT a falsification of the lane.** 1024→32 = only −12.6 dB at 21 Hz, and it attenuated **one of three PARALLEL branches** |
| `0xC644A` | `FUN_0003a382` Stage-C dirty-derivative pole (a **discrete derivative**, `2·sin(w/2)`) | **V43** | ✅ | ⚠ **RE-FRAMED — same reason.** 1024→64 = −7.1 dB, one branch of three |
| `0xC643F` / `0xC6445` + `0xC6A72/86/9A/AE` | `r26` adaptive torque-rate gain surface | **V42** ch.2 | ✅ | 🛑 **FALSIFIED** |
| `0xC6440/42/46`, `0xC61F6` | `r24` direct Sensor-B rate lane | **V39** | ✅ | 🛑 **FALSIFIED** |
| `0xD27C6` / `0xD27DA` | damper Factor C hands-off deadzone Y[0] — **variant-coded, entries 10/11** | **V44** | ✅ | 🛑 **FALSIFIED** (Factor E re-zeroes the product). ✅ **2026-07-28: confirmed it hit the LIVE table.** PN `39990-TVA-A160` → key `TVAA1` → config row 2 → INDEX **10** → `0xD27BC`, exactly what V44 edited. ⚠ one-bit residual: the coded row is in EEPROM, not the flash dump, and the TVA family splits ({TVAA0,2,4}→idx 4). **V55 carries a telemetry bit for it** |
| `0xD2802/04/06`, `0xD2816/18/1A` | damper Factor E (motor-rate) deadzone — **variant-coded, entries 10/11** | **V47** | ✅ | 🛑 marginally quieter at 5 mph, **no effect in motion**. ✅ **2026-07-28: confirmed it hit the LIVE table** (same INDEX 10 chain as V44 → `0xD27F8`). ⇒ **the missing-damping hypothesis was genuinely tested and IS falsified** — do not resurrect it on a "wrong variant" theory |
| `0xC4120` + `FUN_0003a382` `uVar27`→256 | type-8 carrier mute | **V48A** | ✅ | ⚠ **RE-FRAMED — one branch of three, like V43/V46** |
| `gp-0x4f60` broad EMA (19 carriers → `gp-0x1300`) | V52C code cave | **V52C** | ✅ | ⚠ **WEAKER THAN IT LOOKS.** `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only **−6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the mode's content, it did not remove it. **Did change manual feel** (so the cave fired) |
| `0xC6206` (hands-off slew) | governor slew | **V45** | ✅ | 🛑 **FALSIFIED** |
| `0xC6206`/`0xC6208` ← `0xFFFF` | governor slew, both | **V40** | ✅ | ☠ **EPS lamp + no power steering at ignition.** Magnitude, not direction: `0xFFFF` made the guard never fire → snap-to-target → DTC 0x1d → motor off |
| `0xC5030`, `0xC521A`, `0xC5232` | motor-rate cap table | V40/**V41** | ✅ | 🛑 **FALSIFIED** (V41 = clean subtractive test) |
| `0x454FE` `0x65BA`→`0x65B5` | state-4 governor ratchet `bne`→`br` | **V42** ch.1 | ✅ | ✅ **CONFIRMED ROOT CAUSE** — fixed the hard-turn ratchet. Carry forward. ⚠ **NOT present in V38/FOURFRAME** |
| `0xC646C` 891→3564 | the 4× gain — **shared sensor-scale, 6 readers, 2 on feedback paths** | V22→ | ✅ | the change under investigation |
| `0xC61B2`/`0xC61B4` 512→2048 | forward-path clamps, raised ×4 with the gain | V22→ | ✅ | correct and intentional |
| `0xC62EA` 320→**0** | low-speed steer lockout, 4.995 km/h → 0 | **V53** | ✅ | ✅ **CONFIRMED WORKING** on-car 2026-07-27. Route `1a`: `STEER_STATUS=0` in 5,995/5,995 frames (ST=3 never fires) and **226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h** — a cell that is structurally EMPTY on V38. No fault, no dash light |
| `0xC64B8` 112→0xFF | DTC-0x49 fail-counter gate | **V37** | ✅ | ✅ **gentle EME RESOLVED**, no dash-light regression |
| `0xC64B4-B7`, `0xC61C0-C5`, `0xC64E2` | `STEER_STATUS` debounce SM cals | **V36** | ✅ | ⚠ fixed gentle EME but **unmasked DTC 0x49** → superseded by V37 |
| `0xC6312` 320→65535 | gentle-EME decider torque gate | **V33** | ❌ | wrong gate (fires ~10 Hz benign) |
| `0xC65C4/C8/CC` + `0xC6768/6A/6C` | soft-EME boost floor (matched int/float) | **V31** | ✅ | ✅ soft EME resolved. **Do not desync the mirror pair.** ⚠ **V31 set the floor to 4096; V38 RAISED it to 5120** (float 5.0) — byte-verified in `_v54_plain_image.bin` vs stock `0/1536/2048`, and the golden model carries both. The V31 memory's 4096 is correct *for V31*; the car runs V38+, so 5120 is the live value. ★ **On-car proof 2026-07-28:** V54's authority probe read `gp-0x6966` pinned at the bottom bucket for 5,989/5,989 frames *including 17% of requesting frames at openpilot's ±4096 rail* ⇒ the V31 fixpoint is **self-stable and attracting, measured under railed command**, not merely argued |
| `0xC6202` | governor nominal | — | ❌ | **investigated and REJECTED** — buys nothing (4762 > max command), and `gp-0x4f64` is shadowed → fault `0x17`, hard-fault-eligible |
| `0xC6194` | "LKAS-only rate limiter" | — | — | **DEAD calibration** — its gain cal `0xC63CC` = 0 |

### Untested levers currently on the table
| address | what | status |
|---|---|---|
| **`0xC6AFC` + `0xC6AFE`** (Y[0], Y[1] of the `0xC6AF0` LERP) | `FUN_0003a382` authority→output-bound LERP | ✅ **BUILT AS V56 2026-07-28.** Direction measured by V54; **completeness confirmed in Ghidra twice independently** — the LERP result is a Q15 multiplier on the ceiling that clamps the lane's **FINAL combined value** (`mul r15,r10`+`sar 0xf` @`0x3a79e`/`0x3a7aa` → the ±clamp @`0x3a88c-94` → `st.h` @`0x3a8a0`), so the mute is **branch-agnostic**, unlike V43/V46/V48A. 🛑 GATE 2: monitor risk CLOSED (1 writer/1 reader, no lockstep), **damping sign and manual feel OPEN** |
| `0xC6372` / `0xC636E` | boost-assist + damping lane **input EMAs**, `alpha = 205/1024` ⇒ only **−1.29 dB at 21 Hz** | **UNTESTED** — V44 pins both in `STOCK_CALS` as "the rejected candidate B". Candidate #2. 🛑 **GATE 2 severe**: `gp-0x6bbe` is base power steering; 60-73° of added assist-loop lag is the **V48B brick class** |
| `0x2a1ee` retarget → `0xC6CD0` | decouple 4× forward from the feedback readers | designed + **independently re-verified 2026-07-28**, still unbuilt. ⚠ **It cannot fix the vibration** — `FUN_0003a382` is not among the six readers (0 matches across its 468 instructions). Build it as a *correctness* fix |

### 🛑 The `0xC646C` readers are ELIMINATED as the vibration carrier (measured, 2026-07-28)
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
