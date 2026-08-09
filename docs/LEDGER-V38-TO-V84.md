# LEDGER — V38 → V84, DELIVERED BYTES vs MEASURED OUTCOMES

**Built 2026-08-08 for the V85 design session.** Purpose: ground V85 in **what was actually on the car**,
not in what the build scripts intended. Every value in Part 1 was read from the **plain image on disk**,
never from a build script.

> **Method for Part 1** [EVIDENCE]: **`analysis-2020accord/ledger_v38_to_v84_bytes.py`** (landed in the
> repo so every claim below is re-runnable) loads all 54 plain images
> (`C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v*_plain_image.bin`) plus
> `stock_fw_dump/code.bin`, and reads each site with `struct.unpack_from('<h'|'<H'|'<I'|'<f')`
> (V850 is little-endian). Mode-indexed factor tables are **dereferenced through their pointer array**
> (`u32(ptr_array + mode*4)`), never quoted from a hard-coded record address, and decoded as
> `[npt:u16][X × npt][Y × npt]` with `Y` at `base + 2 + 2*npt`.
> **Anchors asserted before any read**: stock `0xC646C == 891`, stock `0x454FE == 0xBA`, image length
> `0x100000`. Plain images are flat: file offset == firmware address.
> 🛑 **Everything below `0x13000` in a plain image is NOT comparable to `code.bin`** — all 53 build
> images are byte-identical to each other there and all differ from `code.bin` (50,284 bytes). That is
> a dump-provenance artefact, not a build difference. Every comparison in this file is `≥ 0x13000`.

---

## 🛑 THE FOUR HEADLINES

1. **The V38 LKAS-authority package is byte-identical on ALL 53 builds V38 → V84.** Not one of its
   cells has ever been reduced, on any build, flown or unflown. **Delivered forward LKAS gain = 3564 =
   4.00× stock on every build from V38 to today.** [EVIDENCE — Part 4]
2. **Modes 24 and 25 (this car's MANUAL columns) are byte-CONSTANT across all 54 images for every one of
   the six factor families.** Every damper edit before **V74** landed in mode 10/11/12 and was
   **INERT BY TABLE SELECTION**. [EVIDENCE — Part 1.3]
3. **`gain_B` in the ENGAGED columns (modes 24/25/26/27) has NEVER been written by any build.** V69's and
   V70's speed-shaped r24 dose, and V72's flat 5244, all went to **mode 10**. The lever they were
   designed to pull has never been pulled. [EVIDENCE — Part 1.4]
4. **Almost every lever in this arc was only ever pushed ONE WAY.** `0xC407E` only up. `0xC63A0` only up.
   LKAS gain only up. The output clamps only up. The `sar` pair only toward *more* gain. The friction
   table only up. See Part 3(b).

---

# PART 1 — THE DELIVERED-BYTES LEDGER

## 1.1 The V38 baseline — what V38 delivered, and what has never come back off

[EVIDENCE — Python byte diff `_v37_plain_image.bin` vs `_v38_plain_image.bin`, `≥0x13000`:
**19 runs, 102 bytes**, of which 12 bytes are the three CRC trailers `0xC6FFC` / `0xE4FFC` / `0xE5FFC`.]

| # | cells | stock | V22 | V37 | **V38** | vs stock | what it is |
|---|---|---|---|---|---|---|---|
| **G1** | `0xC646C` | 891 | 1782 | 1782 | **3564** | **×4.00** | LKAS **forward gain** — Q15 scale on the CAN setpoint → command (`FUN_00028ea6` @`0x2A1EE`) |
| **G2** | `0xC61B2`, `0xC61B4` | 512 | 1024 | 1024 | **2048** | **×4.00** | arbitration output clamp + LKAS-gain output clamp |
| **G3** | `0xC674E`,`0xC6750` / `0xC675A`,`0xC675C` | ±1024 | ±1024 | ±4096 | **±5120** | **×5.00** | soft-EME **corridor** bound arm (V30/V31 lineage) |
| **G4** | `0xC6768`,`0xC676A`,`0xC676C` | 0,1536,2048 | same | 4096×3 | **5120×3** | flattened up | V31 **boost floor** |
| **G5** | f32 `0xC6598`,`0xC659C` = **5.0**; `0xC65AC`,`0xC65B0` = **−5.0**; `0xC65C4`,`0xC65C8`,`0xC65CC` = **5.0** | 1.0 / −1.0 / 0,1.5,2.0 | same | ±4.0 | **±5.0** | ×5.00 | float mirrors of G3/G4 |
| **G6** | setpoint limit, **8 records × 9 halfwords**: `0xE4194`,`0xE41BC`,`0xE420C`,`0xE4234`,`0xE5194`,`0xE51BC`,`0xE51E4`,`0xE520C` | 15360 | 15360 | 15360 | **16384** | ×1.0667 | LKAS setpoint limit |
| (inherited, not V38) | `0xC61C0`,`0xC61C2`,`0xC61C4` = **0xFFFF**; `0xC64B4`,`0xC64B6` = **0xFF**; `0xC64B8` = **0xFF** | 1600/896/1280; 112/54; 112 | stock | maxed | same | — | **V36/V37** `STEER_STATUS` debounce SM + DTC-0x49 counter gate, defeated |

🛑 **`builds differing from V38` for every one of G2–G6, and for the debounce cals: `NONE`.**
All 53 build images V38…V84 carry these bytes unchanged. [EVIDENCE]

## 1.2 The delivered scalar ledger, V38 → V84

Run-length compressed along build order. `[NEVER]` = never written by any build.
🛑 **RULE 7 marks**: `INERT-BY-MODE` only applies to mode-indexed tables (Part 1.3/1.4); everything in
this table is a bare `tp`-relative cal or a code byte and is therefore **MODE-PROOF**.

| addr | what | stock | delivered history |
|---|---|---|---|
| `0x3AA96` | r24/r26 **gate byte** (`C5` = dead `−0x683C` / `FB` = `latActive −0x6806`) | `C5` | `FB` on **V67, V68, V71c, V76g, V84** only; `C5` everywhere else |
| `0x3AB76` | `sar 10,r6` → r26 lane (`AA`=÷1024, `A9`=÷512 ⇒ **×2**) | `AA` | `A9` on **V62, V65, V71a** only |
| `0x3AC20` | `sar 10,r8` → r24 lane | `AA` | `A9` on **V62, V65, V71a** only |
| `0x454FE` | V42 macro-ratchet fix (`BA`=`bne` stock / `B5`=`br`) | `BA` | `B5`: V42–V49, V50, V52–V52c, **V71a–V75**, V76g–V77b, **V80–V84**. `BA` (LOST): V49p, V50probe/V51probe, **V53–V70**, **V76**, V78, V79 |
| `0xC643E` | gain_A arm | 1536 | **0** V42 · **3072** V63/V64 · else 1536 |
| `0xC6440` | third arm (`gp-0x671a`) | 2048 | **4096** V63/V64 · else 2048 |
| `0xC6442` | `gp-0x671d` arm (outranks the gate) | 1024 | **[NEVER]** |
| `0xC6444` | **r26 engaged arm** | 512 | **0** V42 · **3072** V71c · else 512 |
| `0xC6446` | **r24 engaged arm (Lever B)** | 512 | **5244** on V67, V68, V71c, V76g, **V84** · else 512 |
| `0xC644A` | V43 dirty-derivative pole | 1024 | **32** V43 · **64** V49 · else 1024. 🛑 **Lineage/memory say V43 = 64. The image says 32.** |
| `0xC6450` | V46 lever | 1024 | **32** V46 only |
| `0xC646C` | **SHARED sensor scale** | 891 | **3564** V38–V56 **and V76, V78, V79, V80** · 891 V57–V75, V81–V84 |
| `0xC6CD0` | **V57 private forward LKAS gain** | (unused `0xFFFF`) | **3564** V57–V75, V76g, V77, V77b, V81–V84 |
| `0x2A1F0` | V57 decouple displacement | `0x746C` | `0x7CD0` V57–V75, V76g/V77/V77b, V81–V84 |
| `0xC61B2` / `0xC61B4` | arbitration / LKAS output clamps | 512 | **2048 on every build V38–V84** |
| `0xC61B8` | pre-gain deadband | 102 | **[NEVER]** |
| `0xC61F6` | r24 lane deadzone | 3 | **[NEVER]** |
| `0xC62EA` | low-speed steer lockout | 320 | **0** V53–V75, V76g–V77b, **V81–V84** · **320 (restored)** V76, V78, V79, V80 |
| `0xC63A0` | Path-2 damper weight | 1024 | **2048** V72–V75, V76g, **V81** · 1024 elsewhere (incl. V83a, V84) |
| `0xC63AC` | Path-2 IIR coeff | 102 | **[NEVER]** |
| `0xC407E` | **friction clamp / DTC-0x1d interlock** | 511 | **850** V73, V74, V75, V76g, V77, V77b · 511 elsewhere |
| `0xC407C` | interlock clamp neighbour | 461 | **[NEVER]** |
| `0xC64C8` | **aggregator mode selector** | 0 | **[NEVER]** |
| `0xC64C9` | blend mux | 0 | **[NEVER]** |
| `0xC64FA` | CEIL byte cal | 5 | **[NEVER]** |
| `0xC6206` | speed-selected slew step A | 512 | **65535** V40 (☠ brick) · **205** V45 · else 512 |
| `0xC6208` | speed-selected slew step B | 205 | **65535** V40 (☠ brick) · else 205 |
| `0xC61DA` | Q10 integrator scale | 1092 | **[NEVER]** |
| `0xC6316` | governor speed cal (~10 km/h) | 640 | **[NEVER]** |
| `0xC6158` | ceiling `tp+0x7158` fallback | 512 | **[NEVER]** |
| `gain_A` **rec0** Y `0xC6A72`–`0xC6A78` | r26 gain, record 0 | 3072/3072/2434/2048 | **0** V42 · **×2** V71b · **512** V72–V75, V76g–V77b, **V81** · stock elsewhere |
| `gain_A` **rec1** Y `0xC6A86`–`0xC6A8C` | r26 gain, record 1 | 3072/3072/2488/1536 | same pattern as rec0 |
| `gain_A` **rec2** Y `0xC6A9A`–`0xC6AA0` | r26 gain, **≥50 km/h** | 2664/2664/2243/1436 | **0 on V42 only** — otherwise untouched in the whole arc |
| `gain_A` **rec3** Y `0xC6AAE`–`0xC6AB4` | r26 gain, **≥50 km/h** | 2560/2560/2145/1331 | **0 on V42 only** |

### 🛑 CORRECTION FOUND WHILE BUILDING THIS LEDGER — V42 was never a single-variable ratchet test
[EVIDENCE — Python byte diff `_v41_plain_image.bin` vs `_v42_plain_image.bin`: **12 runs**]

V42 is on record as *"`0x454FE` = the CONFIRMED root cause of the ratchet"*. The image shows V42 changed
**six functional groups at once**:

| V42 cell | V41 → V42 |
|---|---|
| `0x454FE` | `BA` → `B5` (state-4 governor substitution killed) |
| `0xC643E` | 1536 → **0** (gain_A arm) |
| `0xC6444` | 512 → **0** (r26 engaged arm) |
| `gain_A` rec0 Y | `[3072,3072,2434,2048]` → **`[0,0,0,0]`** |
| `gain_A` rec1 Y | `[3072,3072,2488,1536]` → **`[0,0,0,0]`** |
| `gain_A` rec2 Y | `[2664,2664,2243,1436]` → **`[0,0,0,0]`** |
| `gain_A` rec3 Y | `[2560,2560,2145,1331]` → **`[0,0,0,0]`** |
| `0xC521A`/`0xC5232`/`0xC5030` | V41's cap-table edits reverted to stock |

⇒ **V42 zeroed the ENTIRE r26 gain surface, all four records, plus two arms, in the same flight that
"fixed the ratchet".** `0x454FE` is separately known to be **structurally dead** on this car
(`gp-0x67fa` never reaches 4 while driving). ⇒ the r26 kill is the **only live delta V42 had**, and
**`gain_A` rec2/rec3 (the ≥50 km/h records) have never been touched by any other build.**

## 1.3 The mode-indexed factor tables — RULE 7 applied to every build

🛑 **This car is `TVCA4`: modes 24/25 MANUAL, 26/27 ENGAGED.** Read through the pointer arrays
`FactorB 0xC9CCC · FactorC 0xC9E9C · FactorD 0xC9DB4 · FactorE 0xC9F84 · ceiling 0xC77A0 ·
friction 0xCBE74`.

| family | m24 | m25 | m26 | m27 | m10 / m11 / m12 |
|---|---|---|---|---|---|
| **FactorB** | **[CONSTANT all 54 images]** `[1024]×4` | CONSTANT | CONSTANT | CONSTANT | CONSTANT — **never written by any build, any mode** |
| **FactorD** | **CONSTANT** `n=5, X=[0,50,100,150,700], Y=[1024]×5` | CONSTANT | CONSTANT | CONSTANT | CONSTANT — **never written, any mode** |
| **ceiling** | **CONSTANT** `X=[300,800] Y=[512,1024]` | CONSTANT | CONSTANT | CONSTANT | CONSTANT — **never written, any mode** |
| **FactorC** | **CONSTANT** `[0,234,429,908]` | **CONSTANT** `[0,233,426,875]` | first touched at **V74** | first touched at **V74** | V44, V47 (m10/m11), V72 (m10/m11), V73 (m12) — **all INERT** |
| **FactorE** | **CONSTANT** `[0,140,539,927]` | **CONSTANT** | first touched at **V74** | first touched at **V74** | V47 (m10/m11), V72 (m10/m11), V73 (m12), V74/V75 (m11) — **all INERT** |
| **friction** | **CONSTANT** | **CONSTANT** | first touched at **V74** | first touched at **V74** | V73 wrote **m10 only** — **INERT** |

**⇒ Every damper / friction / FactorC / FactorE edit made before V74 was INERT BY TABLE SELECTION.**
That covers **V44, V47, V72 (Lever families B/C), and both V73 damper levers**. [EVIDENCE]

### The ENGAGED-column history (modes 26 / 27), from first arming to today

| build | FactorC m26 Y | FactorC m27 Y | FactorE m26 (X;Y) | FactorE m27 (X;Y) | friction m26/m27 |
|---|---|---|---|---|---|
| **stock … V73** | `[0,234,429,908]` | `[0,233,426,875]` | `[60,400,2500,4000]; [0,140,539,927]` | same | `[-9830,-5734,-1966]` |
| **V74** | `[429,234,429,908]` | `[426,233,426,875]` | `[12,400,…]; [0,539,539,927]` | `[12,400,…]; [0,539,539,927]` | **×1.5** `[-14745,-8601,-2949]` |
| **V75** | `[566,…]` | `[566,…]` | `[12,200,…]; [0,539,539,927]` | `[12,200,…]; [0,539,539,927]` | ×1.5 |
| **V76** (V38 base) | `[566,566,566,908]` | **stock** | `[0,119,…]; [0,300,539,927]` | **stock** | **stock** |
| **V78** | `[566,566,566,908]` | stock | `[0,119,…]; [0,449,539,927]` | stock | stock |
| **V79** | `[566,566,566,908]` | stock | `[0,119,…]; [0,897,912,927]` | stock | stock |
| **V80** | `[566,566,566,566]` | stock | `[0,119,…]; [0,897,912,927]` | stock | stock |
| **V81** | `[566,234,429,908]` | `[566,233,426,875]` | `[12,200,…]; [0,539,539,927]` | `[12,200,…]; [0,539,539,927]` | stock |
| **V83a** | `[566,234,429,908]` | `[566,233,426,875]` | **Honda** `[60,400,…]; [0,140,539,927]` | **`[12,200,…]; [0,539,539,927]`** ← V81's full damper, live and unnoticed | stock |
| **V84** | **`[0,234,429,908]` = Honda** | **`[0,233,426,875]` = Honda** | **Honda** | **Honda** | stock |

⇒ **V84 is the first build since V73 with a byte-Honda damper in BOTH engaged columns.** [EVIDENCE]

## 1.4 `gain_B` — the r24 rate-lane gain

Four pointer arrays: `0xCBF5C`, `0xCC044`, `0xCC12C`, `0xCC214`.

| record set | ever written? |
|---|---|
| **mode 10** `0xD2A74`, `0xD2AB0` (arr0/arr1) | **V69** `[12288,12288,…]`/`[10244,10244,…]` · **V70** `[6144,…]`/`[5122,…]` · **V72–V75, V76g–V77b, V81–V84** `[5244]×4` |
| **mode 10** arr2 `0xD2AEC`, arr3 `0xD2B28` | never |
| **modes 24, 25, 26, 27** — `0xD6A9C`/`0xD7A74`/**`0xD7A88`**/`0xD7A9C` (arr0), `0xD6AD8`/`0xD7AB0`/**`0xD7AC4`**/`0xD7AD8` (arr1), `0xD6B14`/`0xD7AEC`/**`0xD7B00`**/`0xD7B14` (arr2), `0xD6B50`/`0xD7B28`/**`0xD7B3C`**/`0xD7B50` (arr3) | 🛑 **NEVER WRITTEN BY ANY BUILD, ANY ARRAY, ANY MODE** |

⇒ **V69's and V70's entire dose ladder, and V72's flat 5244, were delivered to a table this car does not
read — and `[5244]×4` at mode 10 is STILL on V81/V83a/V84, still inert.** [EVIDENCE]

---

# PART 2 — THE MEASURED-OUTCOME LEDGER

Symptom labels are the operator's: **S1** grind #1 18–22 Hz · **S2** micro-ratchet 6–9 Hz (median
7.79 Hz) · **S3** macro ratchet · **S4** friction/impedance (DC) · **G2** grind #2 40–49 Hz ·
**RING** 26–31 Hz.

🛑 **Statistical-era boundary:** **no build before ~V62 has a confidence interval or a split-half null.**
Every ratio quoted for V38–V57 is a **mean-Welch engaged-vs-disengaged** number, and engagement and
motion are collinear on those routes. Treat all of them as upper bounds of unknown looseness.

*(Sections 2.1–2.3 below are compiled from `docs/BUILD-LINEAGE.md`, `docs/STATE.md` and the full
`docs/HANDOFF-*.md` chain. Where a result's premise was later voided, the row carries a ⚠ or 🛑 flag and
the reason.)*

## 2.1 V38 → V57

| build | flew | levers (delivered) | measured | operator | fault |
|---|---|---|---|---|---|
| **V38** | ✅ | G1–G6 above | 🛑 **S1 CREATED AND MEASURED**: 20–30 Hz **63.66×** the 2×-era routes over 201 matched s; 30–40 Hz 8.61×; 40–50 Hz 4.85×; **0.5–5 Hz 0.37× (LOWER)** — the internal control. Speed-matched hands-off vs assisting @19–23 Hz: **314× / 106× / 75×**. **S3 CREATED.** No CI | "hard turns appear authority-limited by a feedback loop" | none |
| **V39** | ✅ | cave: zero the r24 direct lane when `driver<320 AND \|LKAS\|≥417` | S1 null, S3 null, no numbers | "fixed neither symptom" | none |
| **V40** | ✅ | `0xC6206`/`0xC6208` → 0xFFFF + cap table flat | — | ☠ EPS lamp, no power steering, at ignition | ☠ **BRICK-CLASS** |
| **V41** | ✅ | cap table only (slew left stock) | S1/S3 null ⇒ **motor-rate cap FALSIFIED** | "boots and drives cleanly, fixed neither" | none |
| **V42** | ✅ | 🛑 **six groups** (see 1.2) — `0x454FE` **AND** the whole r26 surface zeroed | **S3 FIXED** (felt only). S1 null. ⚠ **attribution wrong**: `gp-0x67fa==4` fires **0/123,277** and 8/92,826 (all in PARK) ⇒ `0x454FE` cannot execute while driving ⇒ **the r26 kill is V42's only live delta** | ch.1 "FIXED THE HARD-TURN RATCHET"; ch.2 "No effect" | none |
| **V43** | ✅ | `0xC644A` 1024→**32** (image; lineage says 64 — **defect**) | S1 null | "fixed neither symptom" | none |
| **V44** | ✅ | FactorC **m10/m11** `Y[0]`→235/234 | 🛑 **INERT-BY-MODE (untested, NOT falsified)**. ⚠ Its stated mechanism ("driver-torque hands-off gate") also never existed — the axis is **voted vehicle speed** | (null) | none |
| **V45** | ✅ | `0xC6206` 512→205 | S1 null. ⚠ label "hands-off step" is wrong — selector flips on **16.6 km/h** | (null) | none |
| **V46** | ✅ | `0xC6450` 1024→32 | S1 null | "no noticeable change" | none |
| **V47** | ✅ | FactorC + FactorE **m10/m11** | 🛑 **INERT-BY-MODE.** The "confirmed it hit the LIVE table" verdict is **WITHDRAWN**. 🛑 **"FALSIFIED — do not resurrect" is FALSE: it was never tested** | "marginally quieter at 5 mph" (observation stands; causal verdict withdrawn) | none |
| **V48A** | ✅ | `0xC4120` 1→0, `0xC67B8/BA/BC` 1024→256 | S1 null | "did NOT fix the vibration" | none |
| **V48B** | ✅ | 21.4 Hz notch biquad in a cave | — | ☠ wheel spun full-authority at startup, parked | ☠ **BRICK.** Created GATE 1 + GATE 2 |
| **V49 / V50 / V52** | ❌ built, never flown | see Part 3(b) | — | — | GATE-1 fail (V50), polarity gate open (V49) |
| **V52C** | ✅ | 12 Hz EMA on all 19 `gp-0x4f60` carriers | S1 null. 🛑 **"V52C halved the mode" is STRUCK — there was never a number**; −6.1 dB is the filter's *designed* response. **No V52C rlog exists** | "did not fix the vibration; clearly changed manual feel" | none |
| **V53** | ✅ `1a` | `0xC62EA` 320→0 | ✅ steer-to-zero **CONFIRMED** (`STEER_STATUS=0` in 5,995/5,995; 226 frames of `STEER_CONTROL_ACTIVE` below 5 km/h). S1/S3 unanalysed | "the steer-to-zero feature worked" | none |
| **V54** | ✅ `1b` | authority probe | ★★ authority is **~0 by design** (`gp-0x6966 ∈ [0,127]` in 5,989/5,989). S1 reproduces **771×** at creep; **mode moves with speed** 20.12→21.68 Hz; saturation suppresses **141×** | "this drive exhibits the vibration issue" | none |
| **V55** | ✅ `1c` | partition probe | ★★ **the ~21 Hz is generated INSIDE the EPS**: 877× torque / 996× angle-rate; coherence 0.93; **while openpilot is railed its own 21 Hz is exactly 0 and the command still carries ~106 counts** ⇒ 38× over openpilot's budget | "demonstrated the vibration in a parking lot" | none |
| **V56** | ✅ `24` | `0xC6AFC`/`0xC6AFE` 32768→0 (mute `gp-0x6ad4`) | S1 **null** (786× vs V55's 877×) ⇒ `gp-0x6ad4` / `FUN_0003a382` **ELIMINATED**. Mode re-characterised `f = 0.177·v + 20.48` | "damping removed and a new few-Hz resonance" ⇒ revert | none. 🛑 the "new 8.69 Hz" is **wheel order 1, a tyre** |
| **V57** | ✅ `28`,`29` | LKAS-gain **decouple** (`0x2A1F0`→`0x7CD0`, `0xC6CD0`=3564, `0xC646C`→891) | Null for both, as predicted (≤0.28 dB). ★★ **S2 characterised for the first time: ~7.4 Hz, 2nd harmonic 15.0 Hz, 33% of burst variance; NOT commanded; not V42's state-4 ratchet** | "grinding is not 7.4 Hz, that is the ratcheting" | none |

## 2.2 V58 → V72

*(This slice's detail is carried in `docs/HANDOFF-2026-07-30…` → `docs/HANDOFF-2026-08-05-v72-flew…`
and in `docs/BUILD-LINEAGE.md`. The load-bearing points for V85:)*

The kit's statistical machinery (episode bootstraps, split-half nulls, pre-registered falsifiers) matures
here. `e_18-22` = median 18–22 Hz burst envelope, the range's S1 yardstick.

| build | flew | **DELIVERED** lever (mode-checked) | measured | operator | flag |
|---|---|---|---|---|---|
| **V58** | ✅ `2b` | **no cal change** — boost-lane probe only | S1 baseline. Engagement confound broken: speed-matched **13.4× [3.9, 19.8]** (p=6.1e-6); speed+effort matched **16.9×**, 17/18 pairs >1. Ceiling `0xD20C0` **ELIMINATED** (0/35,964). ★ `r2b` supplies the corpus's **only 227 s Kd=1 highway baseline** | (ordinary commute) | |
| **V59** | ✅ `2c` | **no cal change** — boost-index thermometer | pump is real: **42.19 Hz, prominence 11.10×** engaged vs **0.00×** disengaged; gain modulation 11.6/22.1/33.1% vs **0.30%** disengaged. 🛑 `eps` 0.020–0.169 vs `eps_crit` **0.147 ⇒ UNDECIDABLE**. `e_18-22` = **879** (the stock rung) | | |
| **V60** | ✅ (no rlogs) | `0xD2006` 102→43 | 🛑 **NULL**, pre-registered as a discriminator ⇒ **the parametric-pump arc is CLOSED** | *"It did not fix the vibration issue."* | |
| **V61** | ✅ `31` | `0x3AB6C`/`0x3AC16` — **both rate taps KILLED (0×)** | ★★★ **WORSE, the kit's first signed result.** Engaged creep **18.25 Hz / prom 486× / power 4.15e9** vs V59's 21.18 / 227× / 5.26e8 ⇒ **−2.93 Hz, ×7.9 power**. `e_18-22` = **2501**; ladder **1.50 [1.40, 1.61]** vs Kd=1 (null [0.88, 1.13]) | LKAS on: *"significantly worse"*; LKAS **off**: *"grinding newly present"*; reverse: *"definitely newly present"* | 🛑 **the rate lane is the DAMPER** — V39/V42/V61 all pushed the wrong side |
| **V62** | ✅ `37` | `0x3AB76`+`0x3AC20` `AA`→`A9` = **×2 on BOTH lanes, mode-proof** | ★★★★ **THE KIT'S FIRST MEASURED FIX.** 18–22 Hz creep **0.124 [0.036, 0.387]** vs V59; at \|rate\| 16–32 °/s **0.024 [0.016, 0.234]** = **42×**; 30–40 Hz control ≈1.0. Pooled **0.39 [0.32, 0.48]** vs null [0.88, 1.13]; `e_18-22` = **168**. **S2 NOT moved** (every CI covers 1 against a 2.2× floor) | *"Original grinding at 2–5 mph is gone!"* | 🛑 **grind #2 CREATED**: 40–49 Hz corner tail **11.71×, p=0.0003**; IMU p95 6.27×; acoustic +9.7 dB(A) |
| **V63** | ❌ built, never flown | `0xC6440`→4096, `0xC643E`→3072 | proven inert by V64. ⚠ even if armed: r24 ×1.78, **r26 ×1.00 = a no-op** | | |
| **V64** | ✅ `35` | V63's cals + detector probe | 🛑🛑 **NULL, AND THE NULL IS ON THE GATE.** byte4 constant `0x87`, all four rungs **0/14,980** ⇒ `\|gp-0x6c2c\|` never crossed T=12800 through 1,158 rate reversals ⇒ **the cals were never in force for one frame.** V64 ≡ V59 spectrally (21.30 vs 21.18 Hz; in the 2–3 m/s bin **20.99 vs 20.98 Hz, env99 1804 vs 1811**) | *"The vibration/grinding at low speeds is not fixed."* | premise voided |
| **V65** | ✅ `3a`+`3b`, 120,049 fr | = V62's `sar` pair + aggregator saturation ladder | ★★★ **THE AGGREGATOR NEVER RAILS** — ±8192 both signs **0/0**; only **54 frames** past ±4096 ⇒ **the loop is LINEAR at the aggregator**, so a linear lane-gain change propagates faithfully. ★ **all 54 sit INSIDE grind-#2 bursts** at 36–106× the segment median | *"…makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement"* | grind #2 worst in corpus with V62 |
| **V66** | ❌ built, never flown | **revert V62's `sar` to stock** | 🛑🛑 **the revert nevertheless FLEW — as the baseline of V67…V72.** V62's fix was removed as a control and **never restored**; it is carried only by V62, V65 and V71a (unflown) ⇒ **from V66 to V72 the car carried NEITHER confirmed fix** | | |
| **V67 / V68** | ✅ `47`, `4a` / `4c`, `4e` | **Lever B**: `0x3AA96` `C5`→`FB` + `0xC6446` 512→**5244** (r24 arm ×2.00, gated on `latActive`) | ★ **BEST S1 IN THE KIT: pooled 0.40 [0.27, 0.58]**, `e_18-22` = **109**. Arm-matched: **ENGAGED 0.321 [0.218, 0.541] / DISENGAGED 1.151 [0.698, 1.521]** ⇒ suppression in ONE arm only. Gate == `latActive` in **150,302/150,327 = 99.983%**. Creep grind #2 **0 bursts, P(0)=0.0005**. 🛑 **HIGHWAY NULL** (see F13). ★★ V68 captured the lane-change event: **27.34–28.90 Hz, envelope 20× route median**, and *"only when engaged"* is **REFUTED at 40–49 Hz** (ON 2.516 vs OFF 2.558) ⇒ **the engaged-conditional part is 18–28 Hz** | V67: *"Grind #2 seems mostly gone… but a higher-speed grind #2 on lane changes/turns, only LKAS-engaged"* · V68 `4e`: *"Definitely felt the grind-#2-like vibration when changing lanes"* | ⚠ V67/V68 ran `0x454FE` = `BA` (no V42 fix) |
| **V69** | ✅ `4f` | 🛑 **the ×4 was `gain_B` MODE 10 ⇒ INERT.** The **delivered** change was **switching V67's gated r24 arm OFF** (`0x3AA96`→`C5`, `0xC6446`→512) | S1 back: `e_18-22` = **746**; engaged/manual within-route **4.726 [1.082, 18.20]** vs null [0.36, 3.24]; creep vs V62 **2.244 [1.438, 3.191]**. ★★ **RATCHET first characterised**: median **7.79 Hz**, speed-invariant, peak 6,065 ct, **in the bar and angle rate but NOT in openpilot's command**, 44/46 windows engaged. 🛑 **ALL THREE PROBE RUNGS FAILED** — b4 **structurally vacuous** (tested ≥4096 against a lane whose ceiling at ratchet speeds is 164–341) | | premise voided |
| **V70** | ✅ `50` | 🛑 **mode-10 `gain_B` only ⇒ "THIS BUILD CHANGED NOTHING"; delivered behaviour is byte-stock** | `e_18-22` = **729**; consistent with stock (P=0.635) and V69 (P=0.495), **excluded** from V62/V65 and V67/V68 (both P=0.0000). ★★ **RATCHET is engagement-REQUIRED**: 73/88 = 83.0% engaged hands-off vs **0/118** manual hands-off, Fisher **p=3.8e-41**, and the rate is **build-independent (80/81/79/94%) ⇒ NO BUILD HAS EVER MOVED IT**. Probe: `gp-0x67fa==10` = **0.0000% ⇒ the V64/V67/V68 detector nulls are GENUINE** | *"stiffer"* — the proposed mechanism (near saturation) is **REFUTED** (0.0000% at the rail) | premise voided |
| **V71a** | ❌ **built, never flown** | `0x454FE`→`B5` **+ both `sar`→`A9`** | ★★ **the only artefact carrying V62's `sar` fix AND V42's byte together, on a mode-proof encoding — and it never flew** | | |
| **V71b** | ✅ `54` | `0x454FE`→`B5` + `gain_A` rec0/rec1 **×2** (r26 ×2 alone, **ungated**) | `e_18-22` = **545** — inside the stock band (P=0.044 vs stock; indistinguishable from V69 P=0.85 and V70 P=0.21). Grind #2 **absent**, P(0)=0.0000. 🛑 `gp-0x67fa==4` fired **0/123,277** ⇒ **`0x454FE`'s null is a null by construction** | *"I definitely experienced grind #1."* | |
| **V71c** | ✅ `58` | gate `FB` + `0xC6446`=5244 + **`0xC6444` 512→3072** (r26 cut REMOVED) | `e_18-22` = **223** — below stock (P=0.0006) but **excluded HIGHER than V67 (P=0.0215)**. **Grind #2 PRESENT**: 7 bursts, **44.31 Hz, p99 1741.9 = 12.2×** the max of any non-bursting build, engaged-only. **Ratchet 8,521 ct p-p = corpus record.** ★ **V71c carries NEITHER `sar` byte and still produced grind #2** ⇒ *"grind #2 is V62's `sar`"* is **REFUTED; its origin is OPEN** | *"attenuated but still present"*; ranked V71c > V71b | |
| **V72** | ✅ `59` | 🛑 **delivered = `0xC63A0`→2048 (live but functionally unarmed) + `gain_A` rec0/rec1→512 (r26 ×0.250).** Lever A's r24 half (`gain_B` m10) and **all of Lever B** (FactorC/E m10/m11) were **INERT** | ★★★★★ **THE PROBE MADE RULE 7**: `\|gp-0x6bd0\|≥64` fired **0 of 87,940**, including 0 of 34,275 above 35 km/h where modes 10/11 would give 389 counts **unconditionally ⇒ 100% duty** ⇒ **[EVIDENCE] the car is NOT in mode 10/11.** Creep grind #2 **FIXED** (0 vs V71c's 7, p=0.0078). **S2 NOT fixed, attenuation 1.0**, column moves **2.1–2.5× FURTHER**. `e_18-22` = **614 [311, 1187] = the STOCK band** | 🛑 **he settled the naming: there are TWO ratchets** — MACRO (fixed) and **MICRO == the 7.79 Hz line**, *"not audible, only felt in the column"* | premise partly voided |

🛑 **After RULE 7, the whole V58→V72 "dose ladder" collapses to a THREE-POINT ladder on one mode-proof
encoding: 0× (V61, much worse) → 1× (stock) → 2× (V62/V65, the only measured fix)**, plus V67/V68's
gated ~2× arm. **V69's 4× and V70's 2× never happened.** The "non-monotone with a minimum at 2×" story
that shaped four builds does not survive.

🛑 **VOIDED BY RULE 7, explicitly**: the *"r24 is near-inert across a 4:1 dose range"* claim rested on
**stock → V70 → V69** = three replications of **one byte-stock condition**. It is **VOID**. The corrected
delivered-dose picture has r24 **monotone** 0× → 1× → 2× (2501 → 879 → 168/109) while r26 swings 11.3×
at fixed r24 and S1 does not move (0.953) ⇒ **r24 is the actor.**

## 2.3 V73 → V84

| build | flew | delivered levers | measured (ratio · CI · null) | operator | fault |
|---|---|---|---|---|---|
| **V73** | ✅ `5a` | `0xC407E` 511→**850** (LIVE, mode-proof) · friction ×1.5 at **m10 only** (INERT) · FactorC/E at m12 and m0–5/14 (INERT) | `0xC407E` live on ~80% of burst frames, **no band change** ⇒ weak falsification bounded at +339 counts. Lever E: **0/104,061 frames exposure** | "same vibration frequency; grind #1 audible, micro-ratchet not"; **G2 resolved**; S3 still fixed | none |
| **V74** | ✅ `5d`, then `61` | **first build ever to arm the ENGAGED damper**: FactorC m26/m27 `Y[0]`:=`Y[2]`, FactorE `X[0]` 60→12, `Y[1]`:=`Y[2]`, friction ×1.5 on 13 engaged modes. `k`=0.5799 | damper live: **67.44% engaged creep vs 0.29% manual = 230.7×** (V72's identical probe: **0/87,940**). Band split `R = 1.015 [0.901, 1.225]` ⇒ **none**. S2 leg ≤12% | — | ☠ **HARD FAULT** on reflash route `61`, while **disengaged, over a bump** |
| **V75** | ✅ `5e` | FactorC `Y[0]`→566, FactorE `X[1]`→200. `k`=1.5798 | **best symptom result to that date**: grind **0.349 [0.192, 0.784]** speed-matched; limit-cycle duty **0.034**, ratio **0.067 [0.000, 0.283]**. S2: 5 of 6 stats down, **none clears its null**. Dose slope 18–22 Hz **−0.599 [−0.856, −0.348]** (excludes 0); 6–9 Hz **−0.089 [−0.350, +0.163]** (**flat**) | "got rid of the audible grind #1 and strongly attenuated the micro-ratcheting… **then a hard fault**, lost power steering" | ☠ **HARD FAULT** |
| **V76** (V38 base) | ✅ `65` | rebase ⇒ `0xC407E`=511, friction stock, `0xC63A0`=1024, **and silently `0xC62EA`=320, the V57 decouple gone, `0x454FE`=`BA`, `gain_A` rec0/rec1 back to Honda** · FactorC m26 `[566,566,566,908]`, FactorE `[0,119,…];[0,300,539,927]`. `k`=1.3866 | flew clean. Friction-margin probe **0/63,477** with the positive control at 99.93% ⇒ a real null. S1 slope **−0.614 [−0.810, −0.416]**; S2 slope **−0.094 [−0.291, +0.098]** ⇒ dose-independent. 🛑 G2 prediction **falsified** (predicted 0.57×, measured **1.394 [1.017, 1.768]**) | "There is still grind #1 and micro-ratcheting at creep" | none |
| **V77 / V77b / V78 / V79** | ❌ built, never flown | see Part 3(b) | V77 later proved a **null experiment by construction**; V79 **rails 38.9%** of the envelope and shipped without `0x454FE` | — | — |
| **V80** | ✅ `66` | V79 + flat FactorC `[566]×4` + `0x454FE`→`B5`. `k`=4.1597 | 🛑 **WORST GRINDING EVER, NO FAULT** ⇒ a stability failure. Damper is a **near-Coulomb relay**: ~495 ct constant across a 34× rate range = 97% of the 512 ceiling. `N(50)/N(500)` V75 1.45× vs V80 **3.27×**. `\|damper\|≥448` engaged **0.000% (V75) vs 19.4% (V80)**. HF lift 30–49 Hz 2.091 — **but the 32–38 Hz negative control fails identically (2.035)** ⇒ NOT "G2 worse". **27.34 Hz limit cycle, ~30 s unbroken.** S1 ladder to V76: V74 1.166, V75 0.735, V80 0.835 against split-half null **[0.63, 1.60]** ⇒ **ALL INSIDE**. **S2: V80 0.418 [0.33, 0.61] — the only point outside its null** | "loud, strong, felt through the whole car, ~90% of LKAS-engaged time, **noticeable vehicle instability**" | none |
| **V81** | ✅ `67` | flown V75 + `0xC407E` 850→**511** + friction → stock | **FAULT-FREE — the clamp revert worked.** Ring **11.25 s @ 27.75 Hz**, amp 978 ct, column angle p-p 1.29°. **Q ≲ 6, τ ≲ 1.8 cycles** once quoted against a step control through the identical filter ⇒ **an actively sustained limit cycle, not a forced resonance**. Not a wheel order, not road input, not commanded, **not a relay** (5f/3f 0.023 vs 0.600). **S4: engaged/manual effort per °/s at 10–40 km/h 1.471 [0.980, 1.812], direction-independent** | "all grinding stopped the instant LKAS disengaged; hand mass did not damp it; highway was worst; **manual steering much heavier when engaged, even turning WITH the command**" | none |
| **V83a** | ✅ `68` | FactorE m26 → Honda (`k` 1.5798→0.2265) · `gain_A` rec0/rec1 → stock · `0xC63A0` 2048→1024. 🛑 **left mode 27 carrying V81's entire damper** | 🛑🛑 **WORST IN THE MODERN LINEAGE ON BOTH SCORED SYMPTOMS**, fault-free. **S1 2.674 [1.956, 3.885]** vs null **[0.63, 1.55]**, 10/10 cells >1 · **S2 1.526 [1.174, 2.019]** vs null **[0.69, 1.40]** · **RING 1.021 [0.817, 1.336] = FLAT** · G2 1.136, inside. 🛑 **Its pre-registered falsifier FIRED ⇒ THE DAMPER-DOSE MODEL OF THE RING IS FALSIFIED** | **"Feels just like V38, like we have made no progress since then."** — **and it was a byte fact** | none |
| **V84** | ✅ route `6d` (12 segs) ⚠ **repo records it as UNFLASHED — record defect** | Lever B (`0x3AA96`→`FB`, `0xC6446`→5244) + damper → Honda in **both** engaged columns | 🛑 **Pre-registered falsifier**: S1 ≈ 0.40× V83a; *"if it does not improve, LEVER B IS FALSIFIED ON A THIRD INDEPENDENT FLIGHT AND THE RATE LANE SHOULD BE ABANDONED AS AN S1 LEVER."* **No scored route-6d numbers exist in the repo yet** | "grind #1 barely got better, might just be placebo… 2 instances of grind #2… **Both microratcheting and ratcheting were very obviously present**" | not recorded |

## 2.4 🛑 RECORDED RESULTS WHOSE PREMISE WAS LATER VOIDED

| result as filed | why it is void | correct status |
|---|---|---|
| **V47 "FALSIFIED — do not resurrect"** | mode-10/11 edit on a `TVCA4` car | **UNTESTED.** Never delivered |
| **V44 "hands-off damping floor falsified"** | mode-10/11 **and** the mechanism never existed (axis is speed, not driver torque) | **UNTESTED** |
| **"r24 is near-inert across a 4:1 dose range"** | V69/V70 wrote **mode 10** `gain_B` | **VOID.** r24 is the actor |
| **"grind #1 is DOSE-LIMITED in k"** | V76 is the only ladder point at `0xC63A0`=1024, and V75-vs-V76 is a **creep-EXPOSURE** artefact (V76's creep windows carry 3.4× V75's steering effort) | **RETRACTED** |
| **"2× is a ramp" → "2× ≈ OPTIMUM in k"** | V80 | **RETRACTED framing.** *"grind #1 never responded to k"*; the replacement is **restore the RAMP, don't merely lower k** |
| **"`0xC63A0` = 2048 causes the hard faults; do not double it"** | 1 reader, 0 writers, **no firmware data path** to the faulting monitor | **EXONERATED.** `0xC407E` = 850 is the real mechanism |
| **"the damper was NOT in force when V74 faulted"** | probe read `bit7 = 1` continuously for 560 ms at the fault, at 33.29 km/h — below mode 24's `X[0]` where a manual column is arithmetically incapable of a non-zero damper | **REVERSED** — it WAS in force |
| **V72 "the damper was tested"** | every FactorC/E/`gain_B` cell V72 wrote was mode 10/11 | **UNTESTED**; only `0xC63A0` and the `gain_A` cut were delivered |
| **V73 Lever D "friction ×1.5 falsified"** | written at `FRICTION_MODE = 10` only | **UNTESTED** |
| **V42 "`0x454FE` is the CONFIRMED root cause"** | `gp-0x67fa` never reaches 4 while driving; and V42 changed six groups at once | **VOID as an attribution.** The r26 kill is the only live delta |
| **"the damper-dose model explains the 26–31 Hz ring"** | V83a's own pre-registered falsifier | **FALSIFIED** |
| **"V52C halved the mode / −6.1 dB"** | it is the filter's designed response, not a measurement; **no V52C rlog exists** | **STRUCK** |
| **"V56 introduced a new 8.69 Hz resonance"** | `f = 0.489·v − 0.186`, r=+0.997, circumference 2.088 m | **wheel order 1 — a tyre** |
| **"LKAS angle rate is limited by the firmware" (V81)** | ach/dem 1.09 creep · 1.22 @14–40 · **1.88 >86 km/h** | **REFUTED.** What was felt is **impedance** |
| **"the aggregator cannot reach the motor"** (11 independent methods) | the `gp-0x6acc` bridge, two hops out | **CLOSED — it does reach it** |

---

# PART 3 — THE TWO LISTS THE V85 DESIGN NEEDS

## 3(a) LEVERS GENUINELY FALSIFIED
**Flown · delivered (mode-proof or verified in force) · measured · did not work.**

| # | lever | build(s) | delivered dose | measurement | verdict |
|---|---|---|---|---|---|
| **F1** | r24 direct lane **zeroed** conditionally (cave, hook `0x3AC78`) | V39 | lane → 0 when `driver<320 ∧ \|LKAS\|≥417` | S1 null, S3 null | falsified — **and the direction was backwards** (V61 proved the lane is the damper) |
| **F2** | motor-rate cap flattened (`0xC5218`/`0xC5230`, slopes `0xC5030`) | V41 | flat 5325 | S1/S3 null, clean subtractive test | **motor-rate cap FALSIFIED** |
| **F3** | `0xC644A` dirty-derivative pole | V43 | 1024 → **32** (image; docs say 64) | S1 null | falsified |
| **F4** | `0xC6206` speed-selected slew step | V45 | 512 → 205 | S1 null | falsified downward |
| **F5** | `0xC6450` Stage-A EMA pole | V46 | 1024 → 32 | "no noticeable change" | falsified |
| **F6** | slot-8 SUM gate + `0xC67B8/BA/BC` | V48A | 1→0, 1024→256 | S1 null; predicted 10–12 dB | falsified ⇒ anti-damping is **distributed** |
| **F7** | broad 12 Hz EMA on all 19 `gp-0x4f60` carriers | V52C | α=74/1024 | S1 null (and no rlog) | falsified. ★ **Closed as a STRATEGY**: no low-pass both materially stronger than V52C and feel-neutral exists — lag scales with attenuation bought |
| **F8** | mute `gp-0x6ad4` / `FUN_0003a382`, all branches | V56 | `0xC6AFC`/`0xC6AFE` 32768→0 | S1 **786×** vs V55's 877× ⇒ no change | **the whole lane ELIMINATED**, and it cost damping |
| **F9** | LKAS-gain **decouple** (4 feedback readers → stock 891) | V57 | `0x2A1F0`→`0x7CD0`, `0xC6CD0`=3564, `0xC646C`=891 | null for both symptoms, ≤0.28 dB | falsified — ⚠ **this did NOT change delivered forward gain**; it falsifies the *feedback* readers only |
| **F10** | `0xD2006` boost-amplitude blend | V60 | 102 → 43 | null (pre-registered as a discriminator) | ⇒ **the parametric-pump arc is CLOSED** |
| **F11** | **kill BOTH rate taps** (`0x3AB6C`, `0x3AC16`) | V61 | r24 = r26 = **0×** | 18.25 Hz, **×7.9 power**, `e_18-22` = **2501**; newly present in MANUAL | 🛑 **falsified, WORSE** ⇒ the rate lane is the **damper** |
| **F12** | oscillation-detected arms `0xC6440`/`0xC643E` raised | V63/V64 | 2048→4096, 1536→3072 | detector **never armed** (0/14,980) | ⇒ the **approach** is closed on the threshold; the cals are untested |
| **F13** | **Lever B for the HIGHWAY grind** (`0x3AA96`=`FB` + `0xC6446`=5244) | V67, V68 | r24 arm ×2.00 gated on `latActive` | 40–49 Hz **0.970 [0.787, 1.154]** and **0.938 [0.764, 1.184]** vs null [0.73, 1.37]; event-rate 0.855/1.152 vs null [0.36, 2.50], MDE 1.61×; positive control fires | 🛑 **FALSIFIED for the highway grind** on two independent statistics |
| **F14** | the **~28 Hz lane-change transient** vs rate-lane dose | V68, V69 | 1× vs 2× | 2.000/1.000 = **1.176 [0.641, 2.320]**; Theil-Sen on dose **+5.736 [−25.4, +34.9]** | 🛑 **DOSE-INDEPENDENT ⇒ excitation, not gain.** Do not chase the rate lane for it |
| **F15** | `0xC407E` **RAISED** 511 → 850 | V73, V74, V75 | +339 counts | V73: live ~80% of burst frames, **no band change** | falsified **upward**, and it is the **hard-fault mechanism** ⇒ RULE 11, DO-NOT-RAISE |
| **F16** | friction table **×1.5** in the engaged columns | V74, V75 | `[-14745,-8601,-2949]` | no attributable symptom benefit; causally implicated in both hard faults | falsified upward |
| **F17** | 🛑 **the engaged-column Coulomb damper, as an S1 lever** — FactorC `Y[0]`>0 + FactorE plateau, **five delivered doses** | V74 (k=0.58) · V75 (1.58) · V76 (1.39) · V80 (4.16) · V81 (1.58) · V83a (0.23) | k spans **18×** | **S1 ladder vs V76: V74 1.166 [0.98,1.41] · V75 0.735 [0.50,1.22] · V80 0.835 [0.64,1.07] — split-half null [0.63, 1.60] ⇒ ALL INSIDE.** V83a (k→0.23) **2.674 [1.956, 3.885]** vs null [0.63,1.55] | 🛑 **FALSIFIED as an S1 lever.** *"grind #1 never responded to k."* The apparent V75 win was a **creep-EXPOSURE artefact** (V76's creep windows carry 3.4× V75's effort) |
| **F18** | the same damper, as the **RING (26–31 Hz)** driver | V83a | dose at the ring's operating point = **0.42× V76** | ring **1.021 [0.817, 1.336]** vs V81 (null [0.69,1.42]); **1.123 vs V76 — indistinguishable** | 🛑 **The build's OWN pre-registered falsifier FIRED ⇒ the damper-dose model of the ring is FALSIFIED** |
| **F19** | the same damper, as an **S2** lever | V74…V83a | k 0.58 → 4.16 | 6–9 Hz slope **−0.089 [−0.350, +0.163]** and **−0.094 [−0.291, +0.098]** ⇒ flat over k ≤ 1.58. **Only V80 (k=4.16) clears its null: 0.418 [0.33, 0.61]** — bought with a **2.09× broadband HF lift and a 30 s 27.4 Hz limit cycle**, operator: *"worst grinding ever, noticeable vehicle instability"* | ⚠ **not a flat falsification — the ONLY working S2 dose is at a stability price the car cannot pay in that form.** The replacement direction on record is **restore the RAMP, don't merely raise k** |
| **F20** | notch biquad in a code cave | V48B | RBJ 21.4 Hz, Q≈3.2 | ☠ full-authority wheel oscillation at startup | 🛑 **BRICK.** And a **cancellation biquad in any form is "not recommended"** — its poles would sit at r=0.99878, ~17× more lightly damped than V48B's, while `f₀` moves −14% with load ⇒ delivered fully INVERTED |
| **F21** | **raising LKAS authority further (8×) / governor slew** | analysis + 3 measured lines | — | ach/dem 1.09 / 1.22 / **1.88 >86 km/h**; 7128 with a 2048 clamp delivers like 4096 and flat-clips the top 42.5% | 🛑 **CLOSED, not deprioritised.** *Three independent lines say more authority makes it worse* |

### 🛑 NOT FALSIFIED — **ELIMINATED** (cannot execute, so no direction is testable)
- **`0x454FE`** (V42's macro-ratchet byte). `gp-0x67fa == 4` fires **0/123,277** (route 54) and **8/92,826** (route 58, all eight in **PARK**). The substitution never runs while driving, **on stock either** ⇒ structurally eliminated as a cause of the 7.79 Hz ratchet. ⚠ **[OPEN]** V42 was confirmed on-car against the *hard-turn* ratchet — if state 4 never occurs, that fix could not have acted either, which points back at V42's simultaneous **r26 kill**.
- **`0xC6194`** (LKAS rate limiter) — gain cal `0xC63CC` = 0 multiplies it out. DEAD calibration.
- All **eight** aggregator zero-type range gates — each is capped by its own producer's ceiling at or inside its gate window, on every build ⇒ structurally vacuous.

---

## 3(b) 🛑 LEVERS **NEVER ACTUALLY TESTED** — THE V85 CANDIDATE POOL

**Legend** — `MODE-PROOF` = bare `tp`/`gp` scalar or code byte, in force regardless of variant.
`MODE-INDEXED` = must be written in **modes 26 AND 27** (this car's two ENGAGED columns) to be delivered,
and leaving 24/25 at Honda makes it **engaged-only by construction**.
`⛔CONSTRAINT` = reduces max commandable steering angular velocity/acceleration ⇒ **collides head-on with
the operator's standing hard constraint** and must be flagged as such if proposed.

### TIER 1 — never written by ANY build, mode-proof or mode-indexed-and-engaged-only, and on a lane the record says matters

| # | address(es) | what · direction never tried | why it is the pool's best | blast radius | cal-only? | mode-proof? | ⛔ |
|---|---|---|---|---|---|---|---|
| **B1** | **`0xC407E`** (`tp+0x507E`) | **LOWER** 511 → 384 → 256. 🛑 **Only ever RAISED (to 850).** Zero builds below 511, ever | 🛑 **The feasibility doc's #1 ranked recommendation.** `FUN_00036c12` runs in **task 0 = 1 kHz** — *the only task in which anything aimed at 18–22 Hz can act* (task 5 carries 38–76° of lag at 21 Hz). Its input `gp-0x6c2c` is **filtered motor ACCELERATION** ⇒ ≈0 under steady motion ⇒ **it costs zero DC impedance** | **0 writers, 3 readers, all signed `ld.h`, all inside `FUN_00036c12`.** Lowering a clamp loosens no monitor and can only shrink the lane ⇒ **cannot re-open the DTC-0x1d fault**. Sits far inside the aggregator's ±1024 zero-reject window | ✅ 2 bytes | ✅ | **NO — this is the one Tier-1 lever that does NOT collide with the hard constraint** |
| **B2** | **`gain_B` ENGAGED columns**: arr0 `0xD7A88`(m26)/`0xD7A9C`(m27) · arr1 `0xD7AC4`/`0xD7AD8` · arr2 `0xD7B00`/`0xD7B14` · arr3 `0xD7B3C`/`0xD7B50` | **The r24 rate-lane gain, with a SPEED AXIS, in the engaged column. NEVER WRITTEN BY ANY BUILD, ANY ARRAY, ANY MODE** (m24/25/26/27 byte-constant across all 54 images) | ★★ **This is exactly what V69 and V70 were designed to do and they wrote mode 10.** r24 is now the identified actor. A flat arm (Lever B) has **one DOF and two constraints** — creep needs boost, highway needs ≈1×. `gain_B`'s speed axis gives that shape natively. Leaving m24/m25 at Honda makes it **engaged-only by construction**, which answers the operator's standing objection to rate-lane builds | 8 records. Manual columns untouched | ✅ | MODE-INDEXED — write **26 and 27** | NO (raises a damping gain) |
| **B3** | **FactorD** `0xC9DB4[26]` = `0xD778C`, `[27]` = `0xD77A4` | **n=5, flat-unity `[1024]×5` in EVERY mode on EVERY one of 54 images. NEVER WRITTEN** | ★★ **The ONLY frequency-selective lever in this firmware.** Axis is `gp-0x6a10` = angle-tracking-error magnitude at 0.1°/count, X = `[0,50,100,150,700]` = 0/5/10/15/70°. Angle amplitude scales as **1/ω**, so at 7.79 Hz the excursion is **3.6× larger** than at 27.75 Hz ⇒ **a FactorD rising with angle error preferentially damps the LOW-frequency micro-ratchet.** FactorE cannot do this — the damper's nonlinearity is memoryless ⇒ it scales every frequency identically and never changes phase. **n=5 already ⇒ no code edit** | multiplies into the same damper product as FactorC/E | ✅ | MODE-INDEXED — 26 and 27 | NO |
| **B4** | **`0xC64C8`** (+ `0xC64C9`) | **aggregator MODE SELECTOR. Never written by any build; 0x00 on stock and all 54 images. 0 writers, 1 reader.** Mode **1 DISCARDS the entire aggregator contribution**; mode 2 blends | The aggregator is now **known** to reach the motor (`gp-0x6acc` bridge). Mode 1 is the cleanest possible ON/OFF control for the entire compensation stack | 🛑 **UNTRACED and DANGEROUS** — a one-byte switch that deletes a lane feeding the motor. Writer census never run. **Do not fly without a GATE-2 argument** | ✅ 1 byte | ✅ | unknown |
| **B5** | **`0x3AB76` / `0x3AC20`** `sar` imm5 | reachable set is `{AB = ÷2, AA = 1× (stock), A9 = 2×, A8 = 4×, A7 = 8×}`. **Only `AA` and `A9` have EVER been built** (54-image scan) ⇒ **`A8` (4×) was NEVER BUILT, and neither was `AB`** | 🛑 The famous "×4 rung" that made the ladder look non-monotone was **mode-10 `gain_B` and inert**. The mode-proof ×4 does not exist on disk. **The dose-exact ladder is really 0× (V61, worse) → 1× (stock) → 2× (V62/V65, the only measured fix)** ⇒ above 2× is **wholly unexplored** | both lanes move together (one `lp` gates both); ⚠ **V62's r24 half CAUSED grind #2** ⇒ a known G2 risk. Also changes MANUAL feel | ❌ 1 code byte each | ✅ | NO |
| **B6** | **`gain_A` rec2/rec3** Y at `0xC6A9A`–`0xC6AA0`, `0xC6AAE`–`0xC6AB4` (records `0xC6A90`/`0xC6AA4`) | the **≥50 km/h r26 records**. Touched by **V42 only** (zeroed, alongside six other things). **No other build in the entire arc has touched them** | **The only untouched cells that reach the HIGHWAY regime on the r26 lane** — and the highway grind is the one symptom Lever B demonstrably does not fix | ⚠ once V84's gate is armed, `gain_A` becomes the **manual-only** path in the arms' shadow — check before writing | ✅ | ✅ (`gain_A` is **not** mode-indexed) | NO |
| **B7** | **`0xC63AC`** = 102 | Path-2 accumulator one-pole IIR coefficient. **Never written by any build.** 102/1024 ⇒ **fc ≈ 16.7 Hz — sitting directly in the S1 band** | a first-order pole this close to 18–22 Hz sets both the magnitude *and the phase* the damper arrives with. It has never been moved in either direction | 1 reader family (`FUN_00038148`); ⚠ **GATE 2 — moving a pole changes phase in a closed loop** | ✅ | ✅ | NO |
| **B8** | **`0xC63A0`** | **LOWER** below 1024. Only ever **raised** (1024→2048) | Path-2 only; Path 1 is unity-weighted straight into the aggregator. Its contribution passes a **PID** ⇒ frequency-dependent, not a scalar ratio | **1 reader (`0x381AC`), 0 writers**, no monitor path, no float mirror. **EXONERATED** for the faults | ✅ 2 bytes | ✅ | NO |
| **B9** | **`0xCBE74[26]` / `[27]`** friction speed-LERP Y | **LOWER** below stock `[-9830,-5734,-1966]`. Only ever **raised ×1.5** | The **gain** twin of B1's **clamp** — Feasibility §6.3 Step 3's ⚠ branch: *"if step 2 says the gain rather than the clamp is the lever, write the engaged column of every row"* | same lane as B1 | ✅ | MODE-INDEXED — 26 and 27 | NO |

### TIER 2 — never delivered because the edit landed in a table this car does not read (RULE 7 orphans)

| # | what was intended | what was delivered | how to actually test it |
|---|---|---|---|
| **B10** | V44/V47 — raise the damper floor at low speed | mode 10/11 ⇒ **byte-stock** | it is now known that FactorC's axis is **voted speed**, so V44's stated mechanism never existed. The engaged-column version of V47's shape has never been flown |
| **B11** | V69/V70 — speed-shaped r24 dose, 4× at creep → exactly 1× above 50 km/h | mode-10 `gain_B` ⇒ **byte-stock** | **= B2.** ⚠ verify the cross-axis before repeating the "exactly 1.000× above 50 km/h" claim |
| **B12** | V72 Levers B/C — FactorC/FactorE damper shaping | modes 10/11 ⇒ **byte-stock** ⚠ and had it been delivered, `FactorE Y[0..2] → 927` would have been a **near-bang-bang relay** = a limit-cycle generator | do not resurrect that shape |
| **B13** | V73 Lever D — friction ×1.5; Lever E — FactorC/E `Y[0]:=Y[1]` | `FRICTION_MODE = 10`; modes 0–5/12/14 ⇒ **0/104,061 frames exposure** | the ×1.5 direction was later delivered by V74 and is falsified (F16); **Lever E's shape has never been delivered** |
| **B14** | V63 — oscillation-detected arms | delivered but the **detector never armed** (0/14,980, and `gp-0x67fa == 10` = 0.0000% on V70) | ⚠ even if armed: r24 ×1.78, **r26 ×1.00 = a no-op**. Honda's own osc arms are gain **reductions**. Low value |

### TIER 3 — directions never tried on levers that WERE flown

| # | cell | flown direction(s) | 🛑 direction never tried | note |
|---|---|---|---|---|
| **B15** | **`0xC6CD0`** (forward LKAS gain, V57's private cell) | **UP only** — 891 → 1782 (V22) → **3564 (V38)**. **Never lowered on any of 54 images** | **LOWER** to 1782 (= V37's exact 2.00×) or 891 (stock) | ✅ safe to move alone on the V81/V83a/V84 lineage: **exactly ONE reader, `0x2A1EE`**, the forward arbitration path; 0 writers; no float mirror; structurally engaged-only. ⛔ **COLLIDES HEAD-ON WITH THE HARD CONSTRAINT** — propose as a **diagnostic arm**, never as the fix. ⚠ do NOT port onto a V76/V78/V79/V80 base (decouple is off there; the two cells are one cell) |
| **B16** | **`0xC61B2` / `0xC61B4`** | **UP only** — 512 → 1024 (V22) → **2048 (V38)**; **identical on all 53 builds since** | **LOWER** (must move in lockstep) | ⛔ same constraint collision. ⚠ mislabelled as a "deadband arm" in `BUILD-LINEAGE` and several build scripts — they are the **arbitration and LKAS output clamps** |
| **B17** | **setpoint limit** — 8 of 12 records raised; **live record `0xE51A8`** (selector `gp-0x674e` = 7) | **UP only**, 15360 → 16384 | **LOWER** back to 15360 | only ×1.0667 ⇒ low information on its own. ⚠ 4 records (`0xE41D0`, `0xE4248`, `0xE5220`, `0xE5248`) were **left stock by V38 and are still stock on V84** |
| **B18** | **`0xC6446`** (r24 gated arm) | 512 (stock) and **5244** only | **any intermediate value**, and **below stock**. The kit's own named follow-up — **5244 → ≈2151–2400**, giving ≈1.000× at highway while keeping the creep boost — was specified in `STATE.md` and **never built** | ⚠ a flat arm is 1 DOF against 2 constraints. **B2 is the structural answer to this** |
| **B19** | **`0xC6444`** (r26 gated arm) | 0 (V42) · 512-with-gate (V67/V68/V84) · 3072-with-gate (V71c) | **the r26 leg alone, with the gate.** V67/V68 changed r26 **and** r24 in one byte; V71c changed r26 **and** kept r24 up | ⚠ 🛑 On a build with the gate at `C5` this cell is **NULL BY CONSTRUCTION** — it is read only at `0x3AB5E` and only when `lp != 0` |
| **B20** | **FactorE `X[1]`** (ramp knee) | narrowed 400 → 200 → 119; restored to 400 | **WIDENED beyond 400** | ★ moves the dose at the operating point **without** raising the plateau that sets the surface maximum ⇒ free under **both** clip rules. This is the shape the V80 retraction asks for: *restore the RAMP* |
| **B21** | **`0xC6AFC`/`0xC6AFE`** | full mute only (32768 → 0) | **partial** (e.g. 16384) | proposed once and rejected as bounded between two agreeing measurements; the lane is otherwise eliminated |
| **B22** | **`0x3AA96`** gate cell | `−0x683C` (dead) and `−0x6806` (`latActive`) | **any other gate cell** | 🛑 a search of the plausible space found **no speed- or torque-conditional byte to repoint to** — the firmware idiom is *"always LERP, never threshold-and-latch"*. `gp-0x671d` got a hard NO (live fault path feeding DTC `0x5e`) |

### TIER 4 — never written by any build; identified but low-priority or unpriced
`0xC6442` = 1024 (**outranks the repointed gate** — never written) · `0xC61B8` = 102 (**never moved in 54
images while its clamp siblings went ×4** ⇒ the deadband now covers ~4× more of the LKAS range than the
factory validated; `→ 26` is a never-tried engage-ramp correctness fix) · `0xC61F6` = 3 (r24 lane deadzone;
the 1601 saturation threshold is derived from it) · `0xC61DA` = 1092 (Q10 integrator scale) · `0xC6158`,
`0xC407C`, `0xC64FA`, `0xC6316` · **FactorB `0xC9CCC`** (flat 1024, never written, any mode) ·
**ceiling `0xC77A0`** (`X=[300,800] Y=[512,1024]`, never written, any mode — **this is the clamp V80's
relay pinned against**) · `0xC63AA` `w_LKAS` = 1024 (1 reader, 0 writers; ranked #4 of 4, low expected
value — its chain terminates at `0xC6AF0`, already zeroed by V56 → null) · **`0xC6C42`** (differentiator
delay D 4→2 — **the PHASE lever**, specified in V62's handoff as the follow-up "if V62 comes back null",
**never built**).

### 🛑 THE THREE ANALYSES THE RECORD SAYS ARE OWED AND HAVE NEVER BEEN DONE
1. **`FUN_00036c12`'s SIGN** (Feasibility §6.3 Step 1). Ranked **#1 of 4**. Static, one session, no drive.
   **B1 is blocked on it and on nothing else.** Still the doc's OPEN #3.
2. **Aggregator saturation + zero-reject census** at the proposed operating point (§6.3 Step 2). Blocked in
   turn on `gp-0x6c2c`'s **physical scale**, OPEN since V76.
3. **Engagement-edge impulse-response estimate**, ≥40 edges, γ² ≥ 0.8 over K ≥ 10 non-overlapping
   **episodes**. Ranked #3 of 4. Uses corpus already on disk.

---

# PART 4 — THE V38 QUESTION

## 4.1 What V38 changed, exactly
[EVIDENCE — Python byte diff `_v37_plain_image.bin` → `_v38_plain_image.bin`, `≥0x13000`: **102 bytes**,
of which **12 are the three CRC trailers**. **Cal-only; zero code edits.**]

See the G1–G6 table in Part 1.1. In one line: **V38 doubled the LKAS forward gain and both output
clamps, raised the soft-EME corridor and boost floor 25% to track them, and raised the LKAS setpoint
limit 6.67%.**

Everything else on V38 (the V36 debounce-SM disables `0xC61C0/C2/C4` → `0xFFFF` and `0xC64B4/B6` → `0xFF`,
V37's `0xC64B8` → `0xFF`) was **already on V37, which flew clean**. ⇒ **V37 → V38 is a near-single-variable
step in the LKAS-authority dimension.**

## 4.2 The multiplier

Chain: openpilot `STEER_MAX` 4096 → `clamp(req × −4, ±0x4000)` → clamp to the setpoint-limit LERP →
`(setpoint × gain) >> 15` → clamp `0xC61B4`.

| era | gain (`0xC646C`/`0xC6CD0`) | setpoint limit | delivered at full openpilot scale | vs stock |
|---|---|---|---|---|
| **STOCK** | 891 | 15360 | 15360 × 891 / 32768 = **417.6** | **1.00×** |
| V14–V37 | 1782 | 15360 | 835.3 | **2.00×** |
| **V38 → V84, ALL 53 IMAGES** | **3564** | **16384** | **1782.0** | **4.267×** |
| clamp knee | 4096 | 16384 | 2048 | 4.904× |

**V38 itself delivered the step 835.3 → 1782.0 = ×2.133** (×2.000 gain × 1.0667 setpoint).
**Where did the rest of today's 4.00× / 4.27× come from? NOWHERE — V38 delivered 100% of it.**
V57 added no authority; it only changed **which cell** supplies the forward gain (`0xC646C` → private
`0xC6CD0`), magnitude unchanged at 3564, reverting the four *feedback* readers to stock 891.

## 4.3 🛑 THE CRUX

**Which build first put 4× LKAS on the car? → V38.** [EVIDENCE: `_v37` `0xC646C` = 1782;
`_v38` `0xC646C` = 3564.]

**Has ANY build since ever flown with LKAS authority at or near stock, everything else held?**

# → NO. NOT ONE. NOT EVEN BUILT.

[EVIDENCE — LE reads of all 53 plain images V38…V84, resolving the forward reader through its own
displacement at `0x2A1F0`:]

| builds | `0xC646C` | `0xC6CD0` | reader disp | **forward gain IN FORCE** | delivered |
|---|---|---|---|---|---|
| STOCK | 891 | (unused) | `0x746C` | 891 | 1.00× |
| V22…V37 | 1782 | (unused) | `0x746C` | 1782 | 2.00× |
| V38…V56 | **3564** | (unused) | `0x746C` | **3564** | **4.27×** |
| V57…V75, V76g, V77, V77b, V81, V83a, **V84** | 891 | **3564** | `0x7CD0` | **3564** | **4.27×** |
| V76, V78, V79, V80 | **3564** | (unused) | `0x746C` | **3564** | **4.27×** |

**Forward gain = 3564 on all 53 images. Setpoint limit = 16384 on all 53. Output clamps = 2048 on all 53.
The corridor, the boost floor and their float mirrors are byte-identical to V38 on all 53.**
Every flight after V38 — roughly 30 of them — flew at **4.27×**.

**⇒ THIS IS A MISSING SINGLE-VARIABLE ARM.** The operator's premise ("the symptoms date from V38") names
a variable that has been **frozen for 46 builds**, while the kit searched the shaping terms *inside* the
loop that variable drives.

**Corroborating (weaker, silence-based) evidence** [EVIDENCE — document census]: the first handoff in the
entire kit containing the words grind / ratchet / vibration is
`docs/HANDOFF-2026-07-18-v39-opposing-torque-rate-guard.md` — the session immediately after V38 flew. All
30 prior handoffs are silent on all three. `memory/v44-built-handsoff-damping.md` already says it outright:
*"Zero damping was equally true pre-V38 (which didn't vibrate) … V38's 4× authority excites the mode."*
And V38's own flight measured **63.66× at 20–30 Hz** vs the 2×-era routes over 201 matched seconds, with
the 0.5–5 Hz internal control at **0.37×** — i.e. **not a global scale change.**

## 4.4 Blast radius, and the hard constraint

**`0xC6CD0` is safe to move alone on the V81 / V83a / V84 lineage** [EVIDENCE — raw LE scan of BOTH `tp`
encodings, reproducing `memory/reference-accord-c646c-shared-gain-not-lkas-only.md` as a 4th independent
method]: **exactly ONE reader, `0x2A1EE` in `FUN_00028ea6`** (the forward arbitration path), 0 writers, no
float mirror. It is structurally engaged-only — `0x2A1EE` is idle when disengaged — and the operator has
already driven all three values of the shared cell (891 / 1782 / 3564) and reported **no manual-feel
difference**.

**`0xC646C` is NOT safe to move alone** — 5 remaining readers, two of which (`FUN_00036682`,
`FUN_00036828`) scale the raw driver-torque sensor `gp-0x4f60` on a feedback path that reaches the motor.
On V84 it is already at stock 891, so there is nothing to move.
⚠ **Do not port a `0xC6CD0` edit onto a V76/V78/V79/V80 base** — the decouple is off there and the two
cells are the same cell.

**Does lowering LKAS authority violate the operator's hard constraint?**
🛑 **YES, head-on.** *"Ratchet gone **without limiting the max steering angle rate under strong LKAS
command**."* Lowering `0xC6CD0` reduces peak EPS torque from a rail-pinned command in exact proportion
(4× → 1× ⇒ 1782 → 417 counts) and peak angular acceleration with it. **As a permanent fix it is
disqualified.**

**But it is the cheapest, lowest-risk, highest-information DIAGNOSTIC arm available, and it is the one arm
the kit has never run.** [BELIEF, evidence marked]
- The kit's own thesis — `FEASIBILITY` §4.2: *"self-interference is amplitude-INDEPENDENT … the forward
  LKAS gain appears in none of the loop terms"* and *"8× buys DUTY, not amplitude"* — is an **analytical**
  claim about a linear loop and has **never been checked against a flight**, because the gain has been
  frozen at 3564 for 46 builds. A stock-authority flight either confirms it at last, or shows that the
  post-V38 search has been shaping a loop whose **drive level** was the controlled variable all along.
- The symptoms are **LKAS-engaged-only** — precisely the signature of a term that is zero when `0x2A1EE`
  is idle.
- **Duty is exactly what the operator perceives** (*"grinding ~90% of LKAS-engaged time"* on V80). If
  raising drive raises a limit cycle's duty, lowering it should lower duty. ⚠ that dose statistic came
  from the **damper** ladder, not the LKAS gain — the transfer is an analogy, not a measurement.

⇒ **The recommendation is: run it as a one-flight diagnostic** (V84 base, `0xC6CD0` 3564 → 1782 = V37's
exact 2.00×, or → 891 = stock; 2 bytes, one reader, guard walls untouched), **and state to the operator
up front that it is a measurement, not the fix.** If it fires, the fix is still firmware-side shaping —
but it becomes possible to size that shaping against a **measured** amplitude dependence instead of an
assumed one.

---

# APPENDIX — RECORD DEFECTS FOUND WHILE BUILDING THIS LEDGER

*(Reported, not fixed, per the session's standing instruction.)*

| # | defect | evidence |
|---|---|---|
| **D1** | **V84 is recorded as "BUILT, VERIFIED, UNFLASHED" in `docs/STATE.md` and `docs/BUILD-LINEAGE.md`.** It flew as route `6d` with a verbatim operator verdict. This is the **same defect V83a's handoff §9 flagged one build earlier.** A flown build recorded as unflashed **will** be re-proposed | SESSION-BRIEF §2 vs `STATE.md` |
| **D2** | **`0xC644A` on V43 is 32, not 64**, in `BUILD-LINEAGE.md`, `memory/v43-dirty-derivative-pole-built.md` and the V43 handoff. The image says 32; `build_v43_tva.py:195 POLE_NEW = 32`; V44 reverts `32 → 1024`. **64 is V49's value** | byte read `_v43_plain_image.bin[0xC644A]` |
| **D3** | **V42 is recorded as a single-lever ratchet test. The image shows six functional groups**, including the complete zeroing of all four `gain_A` records — a change no other build has ever made to rec2/rec3. Every V42-derived attribution inherits this confound | byte diff `_v41` → `_v42`, 12 runs |
| **D4** | **`0xC61B2`/`0xC61B4` are labelled a "pre-gain deadband arm"** in `BUILD-LINEAGE.md` and several build scripts. They are the **arbitration and LKAS-gain OUTPUT clamps**; the pre-gain deadband is the *next* cell, `0xC61B8` = 102, which was **never rescaled alongside the ×4 gain** | `build_v84_tva.py` `KEEP_CELLS` already carries the correction; the lineage does not |
| **D5** | **`BUILD-LINEAGE.md:1388` lists V51P under "Built and UNFLASHED".** It was flashed and driven as route `07`, and its result (0/24,000 for both cells) is what licensed `gp-0x1300` for V52/V52C | `HANDOFF-2026-07-24-v51p` §2 |
| **D6** | **"The ×1.5 friction was introduced by V73, not V74"** (`…v80…` §7) is misleading in the direction that matters for causation. `build_v73_tva.py:191-193` writes it at **`FRICTION_MODE = 10` only** ⇒ inert; `build_v74_tva.py:77` writes it on the 13 engaged modes ⇒ **V74's copy is the live one** | build scripts + the mode-dereferenced byte read in Part 1.3 |
| **D7** | **The setpoint-limit table's live record is quoted two ways** — `0xE41BC` (V38 session) and `0xE51A8` (V74 session). **Both are right about a raised record and the naming is the problem**: the table is **12 records of n=9 at stride 0x28** in two blocks (`0xE4180`, `0xE5180`); `0xE41BC` is the **Y row** of the record based at `0xE41A8`, not a record base. ★ **8 of 12 are raised; `0xE41D0`, `0xE4248`, `0xE5220`, `0xE5248` were left stock by V38 and are still stock on V84** | record walk, Part 4 |
| **D8** | `build_v80_tva.assert_c63a0_block` still carries the **known-wrong** `0xC63A0` fault rationale in its comment (flagged in the V80 handoff §9.7, deliberately not fixed) | — |
| **D9** | Route `5d`'s raw rlogs are **missing** — every V74 conclusion runs against a cache. Route 68's scoring code and cache live in a session scratchpad, not `rlog-tools/`. `decode_v74_probe.py` / `decode_v75_probe.py` **do not exist** despite being referenced by their own build scripts | filesystem |
| **D10** | Plain images and `stock_fw_dump/code.bin` **differ in 50,284 bytes below `0x13000`** on every build. A naive whole-image diff reports these as build changes. All 53 build images are byte-identical to each other there | this ledger's own sweep |

