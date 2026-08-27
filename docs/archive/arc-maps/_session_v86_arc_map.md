# ARC MAP FOR THE V86 SESSION — V38 → V85 AS ONE STORY

**Built 2026-08-08 by the ARC-SYNTHESIS agent.** Purpose: stop this session re-proposing a lever that is
already flashed, already falsified, already inert, or already on the car. Supersedes nothing — it
**extends** `docs/archive/LEDGER-V38-TO-V84.md` (still authoritative for V38→V84 detail) with V85, with a
32-slot mode sweep the old reader could not do, and with the four symptoms the operator named on V85.

> **Reader** [EVIDENCE]: `analysis-2020accord/studies/ledger/ledger_v38_to_v85_bytes.py` — a NEW file; the V84 reader is
> left intact. 56 plain images + `stock_fw_dump/code.bin`, LE (`struct.unpack_from('<h'|'<H'|'<I')`).
> Mode tables dereferenced through their pointer arrays, never a hard-coded record address.
> **Anchors asserted before any read, all pass:** stock `0xC646C`=891 · `0x454FE`=0xBA · `0xC407E`=511 ·
> `0xC40BC`=600 · `0x2A1F0`=0x746C · len `0x100000`.
> 🛑 Everything below `0x13000` is a dump-provenance artefact and is excluded from every diff.

---

## 0. THE OPERATOR'S FOUR SYMPTOMS ON V85, AND THE KIT JARGON THAT MAPS TO THEM

🛑 **His words are the symptoms. The bands are the instrument.** Never report a band as a symptom.

| operator's word (V85, verbatim) | kit jargon | band | V85 verdict, HIS words |
|---|---|---|---|
| **grinding** — *"grind #1 is still barely perceptible"*, *"got a little bit better"* | S1 / "grind #1" | 18–22 Hz | **still present**, marginal improvement |
| **micro-ratcheting** — *"seems like it got barely, perceptibly better (somewhat unsure)"* | S2 / "micro ratchet" | 6–9 Hz, median **7.79 Hz** | **still present**, improvement uncertain |
| **ratcheting** — *"was still unfixed"* | S3 / "macro ratchet" | 🛑 **NO INSTRUMENTED BAND EXISTS** | **UNFIXED — the hardest verdict in the report** |
| **(absence)** — *"I did not experience any grind #2 from my hard turning or on the highway"* | G2 / "grind #2" + "the ring" | 40–49 Hz / 26–31 Hz | 🛑 **AN ABSENCE OF COMPLAINT IS NOT A CURE.** Weak negative evidence only |
| *(not raised on V85)* | S4 / friction, impedance | DC | last scored on V84: **2.052 [1.089, 3.936] — FAIL and REVERSED** |

🛑 **THE SINGLE MOST IMPORTANT LINE IN THIS DOCUMENT:** *ratcheting* (macro) is the symptom the operator
says is unfixed, and it is **the only one of the four with no measurement, no band, no probe and no
instrumented history since V72.** Every statistic this kit owns (`e_18-22`, burst duty, ring length,
episode bootstraps, split-half nulls) is aimed at the other three. **A V86 aimed at macro-ratcheting
without a probe is flying blind, and will produce another uninterpretable null.**

---

# A. THE CROSS-BUILD CELL MATRIX, READ FROM THE IMAGES

Values are LE reads of the plain images. `FROZEN-N` counts consecutive build images back from V85 that
hold V85's value (STOCK excluded from the count; 55 = "every build image ever made").

## A.1 The cells that decide the four symptoms

| addr | what it physically is | stock | **V85** | FROZEN-N | who ever moved it |
|---|---|---|---|---|---|
| `0x3AB76` | `sar` imm5 on the **r26** rate lane (`AA`=÷1024=1×, `A9`=÷512=2×, `A8`=4×) | `AA` | **`AA`** | **17** | V62, V65, V71a **only** |
| `0x3AC20` | `sar` imm5 on the **r24** rate lane | `AA` | **`AA`** | **17** | V62, V65, V71a **only** |
| `0x3AA96` | Lever B **gate repoint** (`C5` = dead `gp-0x683c` / `FB` = `latActive gp-0x6806`) | `C5` | **`FB`** | 2 | V67, V68, V71c, V76g, V84, V85 |
| `0xC6446` | Lever B's **r24 engaged arm** | 512 | **5244** | 2 | V67, V68, V71c, V76g, V84, V85 |
| `0xC6444` | r26 engaged arm — **null by construction unless `0x3AA96`=`FB`** | 512 | **512** | 15 | V42 (→0), V71c (→3072) |
| `0x454FE` | V42 macro-ratchet byte (`BA`=`bne` / `B5`=`br`) | `BA` | **`B5`** | 5 | lost twice; back since V80 |
| `gain_A` rec0 Y `0xC6A72`–`78` | **r26** low-speed gain, record 0 | 3072/3072/2434/2048 | **STOCK** | **3** | V42(→0), V71b(×2), V72–V75/V76g–V77b/V81(→512) |
| `gain_A` rec1 Y `0xC6A86`–`8C` | **r26** low-speed gain, record 1 | 3072/3072/2488/1536 | **STOCK** | **3** | same as rec0 |
| `gain_A` rec2 Y `0xC6A9A`–`A0` | **r26 ≥50 km/h** | 2664/2664/2243/1436 | **STOCK** | **50** | **V42 only, ever** |
| `gain_A` rec3 Y `0xC6AAE`–`B4` | **r26 ≥50 km/h** | 2560/2560/2145/1331 | **STOCK** | **50** | **V42 only, ever** |
| `0xC40BC` | `FUN_0003b8f6` Coulomb-relay normaliser (V85's one cell) | 600 | **6000** | **1** | V85 only |
| `0xC407E` | friction clamp / **DTC-0x1d hard-fault interlock** | 511 | **511** | 7 | V73/V74/V75/V76g/V77/V77b → 850 ☠ |
| `0xC63A0` | Path-2 damper weight | 1024 | **1024** | 3 | V72–V75, V76g, V81 → 2048 |
| `0xC62EA` | low-speed steer lockout (V53 steer-to-zero) | 320 | **0** | 4 | on since V53, twice lost |
| `0xC6CD0` | **V57 private forward LKAS gain** | (unused) | **3564 = 4.00×** | 4 | never lowered, ever |
| `0x2A1F0` | V57 decouple displacement | `746C` | **`7CD0`** | 4 | — |
| `0xC646C` | shared sensor scale | 891 | **891** | 4 | 3564 on V38–V56, V76, V78–V80 |

## A.2 The cells FROZEN FOR EVERY BUILD IMAGE EVER MADE (N = 55)

These have **never** been written by any build. They are not "tried and failed"; they are **virgin**.

| addr | value | what it is |
|---|---|---|
| `0xC64C8` / `0xC64C9` | 0x00 / 0x00 | **aggregator MODE SELECTOR** (1 = discard the whole aggregator contribution) + blend mux. 0 writers, 1 reader |
| `0xC63AC` | 102 | Path-2 accumulator one-pole IIR ⇒ **fc ≈ 16.7 Hz, inside S1** |
| `0xC63AA` | 1024 | `w_LKAS` (1 reader, 0 writers) |
| `0xC6C42` | 4 | **differentiator delay D — the PHASE lever.** Named in V62's handoff as the follow-up, never built |
| `0xC61B8` | 102 | pre-gain deadband — **never rescaled while its clamp siblings went ×4** |
| `0xC61F6` | 3 | r24 lane deadzone |
| `0xC61DA` | 1092 | Q10 integrator scale |
| `0xC6442` | 1024 | `gp-0x671d` arm — **outranks the Lever B gate** |
| `0xC64FA` | 5 | CEIL byte cal |
| `0xC407C` | 461 | interlock clamp neighbour |
| `0xC6158` | 512 | ceiling `tp+0x7158` fallback |
| `0xC6316` | 640 | governor speed cal ≈10 km/h |
| **V38 authority package** | `0xC61B2`/`0xC61B4` = 2048 · corridor `0xC674E`/`50`/`5A`/`5C` = ±5120 · boost floor `0xC6768`/`6A`/`6C` = 5120 · setpoint 16384 · f32 mirrors ±5.0 | 🛑 **frozen at V38's values for 55 images. Never lowered. Never even built lower.** |

## A.3 The mode-indexed families — a full 32-slot / 58-record sweep

🛑 This is **new**; the V84 reader only looked at modes {10,11,12,24,25,26,27}. I dereferenced **all 58
pointer-array slots** for all six families across all 80 images on disk.

| family | m24 | m25 | **m26** | **m27** | verdict |
|---|---|---|---|---|---|
| **FactorB** | stock | stock | stock | stock | 🛑 **NEVER WRITTEN — any record, any mode, any build.** Pointer array never moved |
| **FactorD** | `n=5, X=[0,50,100,150,700], Y=[1024]×5` | same | same | same | 🛑 **NEVER WRITTEN — any record, any mode, any build.** Flat unity everywhere |
| **ceiling** | `X=[300,800] Y=[512,1024]` | same | same | same | 🛑 **NEVER WRITTEN — any record, any mode, any build** |
| **FactorC** | **STOCK** `[0,234,429,908]` | **STOCK** `[0,233,426,875]` | **STOCK** | **STOCK** | ✅ V84's revert holds on V85 |
| **FactorE** | **STOCK** `[60,400,2500,4000];[0,140,539,927]` | **STOCK** | **STOCK** | **STOCK** | ✅ V84's revert holds on V85 |
| **friction** | **STOCK** `[-9830,-5734,-1966]` | **STOCK** | **STOCK** | **STOCK** | ✅ reverted at V78, holds |
| **`gain_B`** (4 arrays) | `@0xD6A9C/0xD6AD8/0xD6B14/0xD6B50` | `@0xD7A74/…` | `@0xD7A88/0xD7AC4/0xD7B00/0xD7B3C` | `@0xD7A9C/0xD7AD8/0xD7B14/0xD7B50` | 🛑 **16 of 16 records NEVER WRITTEN BY ANY BUILD** |

**⇒ [EVIDENCE] All four columns this `TVCA4` car reads are byte-Honda on V85 for all six factor
families.** The damper package is fully off the car. V85's edit did not disturb it.

### 🛑 BUT — 14+ RESIDUAL RECORDS OUTSIDE THOSE COLUMNS STILL CARRY V72–V81-ERA DAMPER EDITS
FactorC and FactorE at modes **0, 1, 2, 3, 4, 5, 10, 11, 12, 14, 15, 17, 23, 29** (and two more in the
`0xD9…` block) are still non-stock on V85 — e.g. `FactorE m11 = [927,927,927,927]`, a full bang-bang
plateau; `m14`/`m15`/`m23` carry V81's `[0,539,539,927]`.
**This is not a live-defect claim** — none is reachable on a row-11 `TVCA4` car [BELIEF, structural: the
variant row selects exactly {24,25,26,27}; only modes 10/11 have a *measured* refutation, V72's probe
0/87,940]. **But it is the V83a/mode-27 failure one row over**, and it means the 7-mode view is not a
sufficient audit. **Any V86 touching a factor table must be checked over all 58 slots.**

## A.4 Three cells in the cumulative stock→V85 delta are UNATTRIBUTED
`0x13109` `0x2D`→`0x2C` · `0x14120` `0x2D`→`0x2C` · **`0xC64DE` `0x11`→`0x1B` (a cal: 17 → 27)**.
All three are identical on **all 80 build images including `_v22`** ⇒ they predate V38 and are not a
post-V38 lever. **The kit's "what is non-stock about this ECU" account does not mention them.**
Reported, not fixed. (`0x55C0E` — the 330 TX hook — is accounted: taken since V31p.)

**Cumulative stock → V85, ≥`0x13000`: 175 runs, 364 bytes** (13 of them CRC trailers).
**V84 → V85: 10 runs, 63 bytes** = `0xC40BC` (2 B) + 57 cave bytes at `0xC4B38`–`0xC4B77` + `0xC4FFC`
CRC — **exactly matching `STATE.md`'s claim of 63.** [EVIDENCE]

---

# B. THE LEVER LEDGER, PER SYMPTOM

Status ∈ {**CONFIRMED-FIX**, **FALSIFIED**, **INERT-BY-MODE**, **NEVER-DELIVERED**, **NEVER-TRIED**,
**BRICKED**, **ELIMINATED**}.
🛑 `FALSIFIED` ≠ `INERT-BY-MODE` ≠ `NEVER-TRIED`, and **"the same lever pushed the other way" is a
different claim from "a new lever."**

## B.1 GRINDING / VIBRATING — S1, 18–22 Hz

| address | what it physically is | build(s) | delivered? | on-car | status |
|---|---|---|---|---|---|
| `0x3AB76`+`0x3AC20` `sar`→`A9` | **Lever A** — ×2 on BOTH rate lanes (r24 via `gain_B`, r26 via `gain_A`). Both are gain-scalings of one value `r1 = clamp(gp-0x4f62, ±5120)` | V62, V65, (V71a unflown) | ✅ byte, **mode-proof** (a code byte) | ★★★★ **first measured fix in the kit.** Pooled **0.39 [0.32, 0.48]** vs split-half null [0.88, 1.13]; `e_18-22` 879→**168**. Operator: *"Original grinding at 2–5 mph is gone!"* | **CONFIRMED-FIX** 🛑 **AND BYTE-STOCK ON V85 (17 images)** · ⚠ its **r24 half CAUSED grind #2** (40–49 Hz corner tail 11.71×, p=0.0003) |
| `0x3AA96`→`FB` + `0xC6446`→5244 | **Lever B** — the same r24 arm, but **gated on `latActive`** ⇒ engaged-only by construction | V67, V68, V71c, V76g, V84, **V85** | ✅ byte, mode-proof; gate == `latActive` in 150,302/150,327 = **99.983%** | ★ **best single S1 in the kit: 0.40 [0.27, 0.58]**, `e_18-22` = **109**; suppression in the ENGAGED arm only (0.321 vs 1.151). But on V84 it read **1.10× V81** after negative-control correction ⇒ it only undid V83a's regression | **CONFIRMED-FIX, AT ITS CEILING.** Delivered **three times**; tops out at V67's level, which the operator still calls grinding |
| `0x3AB6C`+`0x3AC16`→0 | kill BOTH rate taps | V61 | ✅ mode-proof | 🛑 **WORSE**: 18.25 Hz, ×7.9 power, `e_18-22`=**2501**; newly present in MANUAL | **FALSIFIED, and it proved the rate lane is the DAMPER** |
| FactorC `Y[0]`>0 + FactorE plateau (m26/m27) | the engaged-column **Coulomb damper** — **OURS, armed at V74**, never Honda's | V74 (k=0.58), V75 (1.58), V76 (1.39), V80 (4.16), V81 (1.58), V83a (0.23) | ✅ engaged columns from V74 | ladder vs V76: 1.166 / 0.735 / 0.835 against split-half null **[0.63, 1.60] ⇒ ALL INSIDE**. V83a k→0.23 gave **2.674 [1.956, 3.885]** | 🛑 **FALSIFIED as an S1 lever** — *"grind #1 never responded to k"* |
| same, at m10/m11/m12 | V44, V47, V72 Levers B/C, V73 Lever E | V44, V47, V72, V73 | ❌ **mode 10/11/12 on a `TVCA4` car** | V72's probe: `\|gp-0x6bd0\|≥64` fired **0/87,940** | **INERT-BY-MODE** — untested, **NOT** falsified |
| `0xC644A` 1024→32 | dirty-derivative pole | V43 | ✅ | null | **FALSIFIED** ⚠ record says 64; the image says **32** |
| `0xC6450` 1024→32 | Stage-A EMA pole | V46 | ✅ | *"no noticeable change"* | **FALSIFIED** |
| `0xC6AFC`/`0xC6AFE` 32768→0 | full mute of `gp-0x6ad4` / `FUN_0003a382` | V56 | ✅ | 786× vs V55's 877× ⇒ no change, **and it cost damping** | **FALSIFIED — lane ELIMINATED.** Do not re-propose at any authority |
| `0x2A1F0`/`0xC6CD0`/`0xC646C` | LKAS-gain **decouple** | V57 | ✅ | ≤0.28 dB, null | **FALSIFIED for the feedback readers.** ⚠ It did **not** change delivered forward gain |
| `0xD2006` 102→43 | boost-amplitude blend | V60 | ✅ | null, pre-registered as a discriminator | **FALSIFIED ⇒ the parametric-pump arc is CLOSED** |
| `0xC6440`/`0xC643E` raised | oscillation-detected arms | V63, V64 | ✅ cal, ❌ **detector never armed** (0/14,980; `gp-0x67fa==10` = 0.0000%) | premise voided | **NEVER-DELIVERED** (approach closed on the threshold) |
| `0xC6206`/`0xC6208`→0xFFFF | governor slew steps | V40 | ✅ | ☠ EPS lamp, no power steering at ignition | **BRICKED** |
| 21.4 Hz notch biquad in a cave | V48B | ✅ | ☠ wheel spun full-authority at startup | **BRICKED** — created GATE 1 + GATE 2 |
| `0xC646C` 3564→891 alone | the ×4 forward LKAS gain, **DOWN** | 🛑 **NONE** | — | — | **NEVER-TRIED. NOT ONE BUILD IN 47 HAS FLOWN BELOW 4×** |

## B.2 MICRO-RATCHETING — S2, 6–9 Hz (median 7.79 Hz)

| address | what it is | build(s) | delivered? | on-car | status |
|---|---|---|---|---|---|
| the m26/m27 damper, as an **S2** lever | FactorC/FactorE | V74…V83a | ✅ | 6–9 Hz slope **−0.089 [−0.350, +0.163]** and **−0.094 [−0.291, +0.098]** ⇒ **flat over k ≤ 1.58**. **Only V80 (k=4.16) clears its null: 0.418 [0.33, 0.61]** | ⚠ **NOT a flat falsification.** The only working dose came with *"worst grinding ever, noticeable vehicle instability"* + a 30 s 27.4 Hz limit cycle ⇒ **restore the RAMP, don't merely raise k** |
| Lever A (`sar` ×2) | rate lanes | V62, V65 | ✅ | **S2 NOT moved** — every CI covers 1 against a 2.2× floor | **FALSIFIED for S2** (it is an S1 lever) |
| Lever B | gated r24 arm | V67/V68/V84 | ✅ | V84: **S2 1.548× V67, outside the null — FAIL** | **FALSIFIED for S2** |
| `0xC40BC` 600→6000 | **V85's one cell**: linearise the 1 kHz Coulomb relay in `FUN_0003b8f6` (relay index 7.87 → 1.00) | **V85** | ✅ mode-proof `tp` scalar, 1 reader / 0 writers | operator: *"barely, perceptibly better (somewhat unsure)"* — **no scored route exists yet** | ⚠ **UNSCORED.** Its own pre-registration says *"if S2 does not improve, revert `0xC40BC` — N is already flat at 6000, there is no larger dose"* |
| `0xC407E` 511→850 | friction clamp raised | V73/V74/V75 | ✅ live ~80% of burst frames | no band change | **FALSIFIED upward — and it is the HARD-FAULT mechanism** |
| friction table ×1.5, engaged cols | V74, V75 | ✅ | no attributable benefit; implicated in both faults | **FALSIFIED upward** |
| **FactorD m26/m27** | angle-error LERP, **the only frequency-selective lever** | 🛑 **NONE** | — | — | **NEVER-TRIED** (see D2) |

## B.3 RATCHETING (MACRO) — S3, ★ NO BAND, NO PROBE, NO INSTRUMENT

| address | what it is | build(s) | delivered? | on-car | status |
|---|---|---|---|---|---|
| `0x454FE` `BA`→`B5` | kill the state-4 governor command-magnitude substitution | V42 …V85 (lost twice) | ✅ byte present on V85 | 🛑 `gp-0x67fa == 4` fires **0/123,277** driving frames (and 8/92,826 on another route, **all eight in PARK**) | 🛑 **ELIMINATED — the byte CANNOT EXECUTE.** Carrying it on V85 is **not** addressing macro-ratcheting. Its V42 "CONFIRMED root cause" attribution is **VOID** |
| **`gain_A` rec0/rec1 LOWERED** | **the r26 low-speed gain** — `gain_A` is **not** mode-indexed ⇒ mode-proof | V42 (→0), V72–V75/V76g–V77b/V81 (→512) | ✅ **delivered, mode-proof** | see the correlation below | ⚠ **DELIVERED BUT NEVER ISOLATED, AND CURRENTLY OFF THE CAR** |
| `0xC63A0` 1024→2048 | Path-2 damper weight | V72–V75, V76g, V81 | ✅ | no benefit ever shown; **exonerated for the faults** | direction tried; **never lowered below 1024** |
| everything else | — | — | — | — | **nothing else in the arc was ever aimed at macro-ratcheting** |

### 🛑 THE ONE CORRELATION THE ARC OFFERS FOR MACRO-RATCHETING [BELIEF — confounded, stated fully]

| build | `gain_A` rec0/rec1 | r26 low-speed dose | operator on the **macro / hard-turn** ratchet |
|---|---|---|---|
| V42 | **0** | **0×** | *"FIXED THE HARD-TURN RATCHET"* (drive 1) |
| V72 | **512** | ≈**0.17–0.25×** | 🛑 he **settled the naming**: two ratchets, **MACRO = fixed**, MICRO = the 7.79 Hz line |
| V73 | **512** | ≈0.17–0.25× | *"S3 still fixed"* |
| V81 | **512** | ≈0.17–0.25× | (not raised either way) |
| **V83a / V84 / V85** | **STOCK 3072/3072/2434/2048** | **1.00×** | V84: *"Both microratcheting and ratcheting were very obviously present"* · **V85: *"Ratcheting was still unfixed"*** |

**Every build on which the operator explicitly called the macro ratchet FIXED carried `gain_A` rec0/rec1
BELOW stock. Both builds on which he calls ratcheting present carry it at stock.** `gain_A` went back to
stock at **V83a** and has been stock for 3 images.

🛑 **The confounds, in full, because this is a BELIEF not an EVIDENCE claim:**
- V42 changed **six functional groups** at once (`0x454FE`, `0xC643E`→0, `0xC6444`→0, all four `gain_A`
  records→0, plus reverting V41's cap table).
- V72 also carried `0xC63A0` = 2048 and a pile of INERT mode-10/11 writes.
- **Counter-evidence:** V76 / V78 / V79 / V80 carried `gain_A` at stock and no macro-ratchet complaint is
  recorded on them — but nor is a macro-ratchet *check*; the record is silent, which is not a negative.
- **`gain_A` has never been moved as a single variable in either direction.** V71b doubled rec0/rec1
  (the opposite direction) and scored `e_18-22` = 545, inside the stock band — that is an **S1**
  measurement, and it says nothing about S3.

## B.4 GRIND #2 (40–49 Hz) AND THE RING (26–31 Hz)

| lever | build(s) | on-car | status |
|---|---|---|---|
| Lever A's **r24 half** | V62, V65 | 🛑 **CREATED grind #2**: corner tail 11.71× (p=0.0003), IMU p95 6.27×, acoustic +9.7 dB(A) | **a KNOWN RISK of restoring Lever A** ⚠ but V71c produced grind #2 carrying **neither** `sar` byte ⇒ *"grind #2 is V62's `sar`"* is **REFUTED; its origin is OPEN** |
| Lever B for the **highway** grind | V67, V68 | 40–49 Hz **0.970 [0.787, 1.154]** and **0.938 [0.764, 1.184]** vs null [0.73, 1.37]; event rate inside null; positive control fires | 🛑 **FALSIFIED for the highway grind, on two independent statistics** |
| rate-lane dose vs the **~28 Hz lane-change transient** | V68, V69 | ratio **1.176 [0.641, 2.320]**; Theil-Sen on dose **+5.736 [−25.4, +34.9]** | 🛑 **DOSE-INDEPENDENT ⇒ excitation, not gain.** Do not chase the rate lane for it |
| the m26/m27 damper as the **RING** driver | V74→V84 | four-point monotone dose–response: burst duty V80 96.6% → V81 25.1% → **V84 2.54%**, longest ring 18.29 → 11.25 → **1.34 s**, on 3.4× the exposure. Negative control and IMU falsifier both pass | ✅ **SUPPORTED** (V83a's "falsified" verdict was **retracted** — V83a left mode 27 carrying the whole damper and had 19.2 s of highway ⇒ it never removed it) ⇒ 🛑 **FREEZE the damper cells** |

---

# C. THE SILENT-LOSS AUDIT — WHAT IS AND IS NOT ON V85 RIGHT NOW

Read from `_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin`. [EVIDENCE]

| historically confirmed fix | cells | V85 | verdict |
|---|---|---|---|
| V37 gentle-EME debounce + DTC-0x49 defeat | `0xC61C0`/`C2`/`C4`=0xFFFF, `0xC64B4`/`B6`/`B8`=0xFF | all match | ✅ **PRESENT** (55 images) |
| V53 steer-to-zero | `0xC62EA`=0 | 0 | ✅ **PRESENT** (4) |
| V57 LKAS decouple | `0x2A1F0`=`0x7CD0`, `0xC6CD0`=3564, `0xC646C`=891 | all match | ✅ **PRESENT** (4) |
| **LEVER A — V62 `sar`×2, both rate lanes** | `0x3AB76`, `0x3AC20` | **`AA` / `AA`** | 🛑🛑 **ABSENT — BYTE-STOCK, FROZEN 17 IMAGES (V71b…V85)** |
| LEVER B — V67/V68 gated r24 arm | `0x3AA96`=`FB`, `0xC6446`=5244 | match | ✅ **PRESENT** (2) |
| V81 hard-fault interlock revert | `0xC407E`=511 | 511 | ✅ **PRESENT** (7) |
| V83a Path-2 damper weight | `0xC63A0`=1024 | 1024 | ✅ **PRESENT** (3) |
| V84 damper → Honda, **both** engaged columns | FactorC/E m26 + m27, all six families | **all byte-stock** | ✅ **PRESENT** — and confirmed over all 58 slots |
| V42 macro-ratchet byte | `0x454FE`=`B5` | `B5` | ⚠ **PRESENT BUT ELIMINATED** — it cannot execute |
| *(not a fix — the suspected cause)* V38 authority package | `0xC61B2`/`B4`=2048, corridor ±5120, boost 5120×3, setpoint 16384, `0xC6CD0`=3564 | all present | 🛑 **FROZEN 55 IMAGES. Never lowered, never even built lower** |

## 🛑 THE THREE ACTIONABLE FINDINGS

1. **LEVER A IS OFF THE CAR AND HAS BEEN FOR 17 BUILD IMAGES.** The kit's first and best-replicated
   measured grinding fix (0.39 [0.32, 0.48] vs null [0.88, 1.13]) has only ever been on **V62, V65 and
   V71a** — and V71a never flew. **This is the fourth silent loss of a confirmed fix** (after `0x454FE`
   twice and the V81 double-absence). **Lever A and Lever B have NEVER flown together on any build.**
2. **`gain_A` rec0/rec1 IS OFF THE CAR** (back to stock at V83a, 3 images). It is the only lever with any
   recorded association to the macro ratchet, and it is mode-proof and cal-only.
3. **The V38 authority package is the longest-frozen thing in the kit and the operator's own premise
   names it.** 47 builds have shaped the loop that 4.27× drives; not one has moved the drive level.
   ⛔ Lowering it collides head-on with *"without limiting the max steering angle rate under strong LKAS
   command"* ⇒ **diagnostic arm only, never the fix.**

---

# D. THE UNTRIED SURFACE — RANKED FOR V86

**Legend** — `MODE-PROOF` = bare `tp`/`gp` scalar or code byte. `⛔` = collides with the operator's
standing hard constraint (must not limit max LKAS-commanded angle rate).

### D0 — 🛑 **RESTORE LEVER A: ADJUDICATED, AND THE ANSWER IS DO-NOT-RECOMMEND**
*(This entry replaces the "rank 1 / missing conjunction" framing in the first draft of this document.
That framing was right that the conjunction has never flown and wrong about what it would deliver.)*

**Step 1 — the delivered multipliers, computed from the bytes.** [EVIDENCE for the byte table;
[EVIDENCE, structural] for the arithmetic]

Both lanes are `out = (r1 × gain_Q10) >> shift`, `r1 = clamp(gp-0x4f62, ±5120)`. The `sar` immediate **is**
the Q10 normaliser of the gain multiply, so it is necessarily **downstream of the arm substitution** —
`0xC6444`=512, `0xC6446`=5244 and the stock LERP ≈2630 are all Q10 gains, and a Q10 shift cannot precede
its own multiply. Changing `sar 10` → `sar 9` therefore **doubles whatever gain is in force, armed or not.**

Byte state, read from the images:

| build | gate `0x3AA96` | `sar` r26 / r24 | r26 arm `0xC6444` | r24 arm `0xC6446` | **r26 ×** | **r24 ×** |
|---|---|---|---|---|---|---|
| STOCK / V69 / V70 | `C5` | `AA`/`AA` | 512 (dead) | 512 (dead) | 1.000 | 1.000 |
| V61 | `C5` | taps killed | — | — | 0.000 | 0.000 |
| V62 / V65 (**Lever A**) | `C5` | **`A9`/`A9`** | 512 (dead) | 512 (dead) | **2.000** | **2.000** |
| V71b | `C5` | `AA`/`AA` | dead | dead | 2.000 (`gain_A`×2) | 1.000 |
| V71c | **`FB`** | `AA`/`AA` | **3072** | **5244** | **1.000** | 1.994 |
| V67 / V68 / V84 / **V85** (**Lever B**) | **`FB`** | `AA`/`AA` | 512 | **5244** | **0.177** | **1.994** |

🛑 **[EVIDENCE] V85 is byte-identical to V67 AND V68 at all five rate-lane cells** (verified directly,
image to image). **And no image in the kit has ever carried `gate=FB` together with `sar=A9`** — the
conjunction is real. But here is what it delivers:

| scenario | engaged arm r24 | engaged arm r26 | **MANUAL arm r24** | **MANUAL arm r26** |
|---|---|---|---|---|
| **(i) V85 as flown** | 1.994 | 0.177 | **1.000** | **1.000** |
| **(ii) + `0x3AB76`→`A9` (r26 half)** | 1.994 | 0.354 | 1.000 | **2.000** |
| **(iii) + `0x3AC20`→`A9` (r24 half)** | **3.988** | 0.177 | **2.000** | 1.000 |
| **(iv) + both** | **3.988** | 0.354 | **2.000** | **2.000** |

**Step 2 — is any of these a new point in dose-space?**
- **Engaged arm:** r24 ≈ **4× has never been delivered mode-proof.** V69's "×4" was mode-10 `gain_B` and
  byte-stock. The real ladder is 0× (V61, much worse) → 1× (stock) → 2× (V62/V65 **and** V67/V68/V84/V85).
  So (iii)/(iv) **would** be a new engaged point. **Nearest flown build: V67/V68/V84/V85 at exactly half.**
- 🛑 **Manual arm: (iv) is V62/V65 VERBATIM.** Lever A is a `sar` immediate in the shared arithmetic — it
  is **UNGATED** and applies in both arms, unlike Lever B's arm which only loads when `lp != 0`
  (`latActive`). V65's operator report on that exact manual condition:
  *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."*
  ⇒ **(iv) is not one new point. It is a new engaged point bolted to a re-run of the worst grind-#2 build
  in the corpus on the manual side**, and it destroys Lever B's *"manual is byte-for-byte Honda"*
  property — the operator's standing 2026-07-31 objection.

**Step 3 — the grind-#2 dose table, at the operator's forbidden regression.**

| build | r24 × | r26 × | grind #2 |
|---|---|---|---|
| V71b | **1.000** | 2.000 | **ABSENT**, P(0)=0.0000 |
| V72 | 1.000 | 0.177 | creep **FIXED** (0 vs V71c's 7, p=0.0078) |
| V67 / V68 | 1.994 | 0.177 | creep 0 bursts — **but** *"a higher-speed grind #2 on lane changes/turns, only LKAS-engaged"* |
| V71c | 1.994 | 1.000 | 🛑 **PRESENT** — 7 bursts, 44.31 Hz, p99 = 12.2× any non-bursting build |
| V62 / V65 | 2.000 | 2.000 | 🛑 **CREATED, worst in corpus**, engagement-independent |
| **V85** | 1.994 | 0.177 | operator: **none from hard turning or on the highway** |

**⇒ [BELIEF] `r24 ≥ ~2` is NECESSARY for grind #2 across the whole corpus.** V71b is the only build with
a doubled rate-lane dose and no grind #2, and it is the only one with r24 at 1.000. r26 modulates the
severity and the speed regime (0.177 → creep clean; 1.000 → 7 bursts; 2.000 → worst) but does not by
itself produce it. **This corrects the recorded attribution both ways:** *"the r24 half caused grind #2"*
is directionally supported, but *"grind #2 is V62's `sar`"* stays **REFUTED** (V71c carried neither `sar`
byte and produced it) — the discriminator is the **delivered r24 dose**, not which cell delivers it.

**Step 4 — ~~THE ARITHMETIC CEILING~~ 🛑 WITHDRAWN 2026-08-08.**
> ~~*This section argued that `r1`'s ±5120 clamp plus a recorded ≤6553 Q10 overflow ceiling made r24 ≈ 4×
> a sign-wrap hazard and capped the lane at ≈2.49×.*~~ **RETRACTED IN FULL. The premise was wrong.**
>
> **[EVIDENCE — orchestrator's own Ghidra `disassemble_bytes`, boundary-confirmed, stock image]** the
> intermediate is **32-BIT**:
> ```
> 0003ac12  ld.hu  0x7440, tp, r10     ; r10 = cal(0xC6440) = 2048   (the Q10 gain)
> 0003ac16  mov    r1, r8              ; <- V61's r24 rate-tap byte
> 0003ac18  mul    r10, r8, r0         ; 32x32 -> 64; LOW word into r8, HIGH discarded
> 0003ac1c  ld.hu  0x71f6, tp, r12     ; r12 = cal(0xC61F6) = 3
> 0003ac20  sar    0xa, r8             ; <- LEVER A's r24 byte. SAR on the FULL 32-bit r8.
> 0003ac24  cmp    r12, r8 / ble / subr r8,r6      ; DEADBAND: |x| <= 3 -> 0, else x -/+ 3
> ```
> `5120 × 5244 = 26,849,280`; `>>10 = 26,220`; `>>9 = 52,440` — **both fit int32 with enormous headroom.
> There is no wrap.** The ≤6553 figure inherited from the sibling `0xC6444` does not describe this site.
> ⊕ ✅ **What this DOES confirm is Step 1's structural claim**: the `sar` operates on the product of the
> selected Q10 gain, i.e. it is **downstream of the arm substitution**, so Lever A doubles whatever gain
> is in force. The multiplier table above stands.
> ⊕ **And it identifies a new object: `0xC61F6` = 3 is a live DEADBAND on the rate lane** (`|x| ≤ 3 → 0`),
> **virgin across all 75 images.** A deadband is the *dual* of a relay — its describing-function gain
> **rises** with amplitude. See E12.
> 📋 *Retained visibly rather than deleted: the kit has been burned by retracted premises surviving in a
> doc. This one is dead — do not cite an r24 overflow ceiling.*

### 🛑 VERDICT ON LEVER A — **UNCHANGED. It rested on three legs and the withdrawn one was the weakest.**
- **(iii) and (iv) — DO NOT RECOMMEND for V86.** Two independent reasons remain, either sufficient:
  **(a)** the manual arm is a verbatim re-run of **V62/V65** — the engagement-independent worst-grind-#2
  condition in the corpus — and it destroys Lever B's *"manual is byte-for-byte Honda"* property, the
  operator's standing 2026-07-31 objection; **(b)** `r24 ≥ ~2` is necessary for grind #2 in every build
  that has ever produced it, and (iii)/(iv) roughly double past that, against a **forbidden regression**
  the operator explicitly reports **absent on V85**.
  ~~**(c)** the int16 overflow bound~~ — **withdrawn, see Step 4.**
- **(ii) — `0x3AB76` alone (r26 half) — NOT RECOMMENDED EITHER, but for a different reason: it is safe
  and near-worthless.** Engaged r26 0.177 → 0.354 on a lane that swings **11.3× at fixed r24 while grind
  #1 barely moves**; its manual side (r26 2.000) has a measured benign precedent in V71b (`e_18-22` = 545,
  inside the stock band, grind #2 absent). ⇒ **low risk, low expected value. Does not earn a build slot.**
- **What IS still open on this lane:** `0xC6446` above 5244 is arithmetically unbounded (32-bit
  intermediate) and **engaged-only by construction**, so an arm-only r24 increase avoids leg (a) entirely.
  It does **not** avoid leg (b) — it is precisely the "raise r24 past 2" move that every grind-#2 build
  shares. ⇒ **available, but it spends the operator's forbidden regression to buy marginal S1 on a lever
  already measured at its practical ceiling three times.** Not recommended without a grind-#2 abort rung.
- ★ **`0xC61F6` = 3, the rate-lane DEADBAND, is newly identified and virgin.** It is on this lane, it is
  mode-proof, and it has never been moved. Unlike everything else here it is **not** a gain — see E12 and
  the note in D8.

**⇒ The rate lane's GAIN dimension is closed for V86. Its DEADBAND dimension has just opened.**

### ★ DNEW (rank 1) — THE `FUN_00038148` COULOMB FRICTION-COMPENSATOR CHAIN — **ENTIRELY VIRGIN**
`FUN_00038148` → `gp-0x6b70 = clamp(SIGN(resid) × LERP(|resid|), ±cal(0xC6200))` → assist aggregator
`FUN_00037fe6`, per-term enable byte `0xC64B0`.

🛑 **VIRGINITY: [EVIDENCE] — every cell in this chain is byte-identical to stock on ALL 75 build images
from V22 to V85. Not one has ever been written by any build.** Method: LE reads of all 75 plain images in
explicit build order, with the **V36/V37 bytes `0xC64B4`–`0xC64B8` carried as a positive control** — they
correctly report WRITTEN (`70 60 36 40 70` → `FF`×5, at V36 for the first four and **V37** for `0xC64B8`),
which proves the scan discriminates and that the adjacent `0xC64AD`–`0xC64B3` result is not contamination.

| cell(s) | stock | frozen | note |
|---|---|---|---|
| `0xC6200` | **8192** | **75 images** | the clamp bound on `gp-0x6b70` |
| `0xC63AE` | 1024 | 75 | |
| `0xC64AD`–`0xC64B3` | **`01 01 01 01 01 01 01`** | **75** | ★ **SEVEN per-term ENABLE BYTES on the assist aggregator** |
| `0xC6468` / `0xC646E` | 2639 / 1428 | 75 | output scale on `gp-0x6bfc` / INERTIA gain |
| `0xC4080` | 0 | 75 | friction constant ⇒ FRICTION is purely `\|model\|`-proportional |
| `0xC40D0` / `D2` / `D4` / `D6` / `D8` | 408 / 102 / 573 / 246 / 3686 | 75 | friction pole · friction scale · command / inertia / torque EMA alphas |
| `0xC6B66`–`0xC6B99` | X `[0,340,640,850,1000,1200,1400,1576,1736,1916,2084,2280,4776]`; Y `[899,908,981,1060,1083,1084,1084,1084,1084,1084,1084,1084,1084]` | **75** | ★ **the 13-point angle-error LERP in `FUN_0003b8f6`** |
| `0xC6ABA`–`0xC6ADB` | X `[0,6554,13107,19661,22938,26214,29491,-32768]`; Y `[1024]×8` | **75** | the aggregator's speed LERP, **flat unity** |

**Why this is now the leading candidate for the operator's UNFIXED symptom:** a **Coulomb friction
compensator** is exactly the physics of ratcheting — stick-slip. This is the only untried chain in the
kit that is mechanistically matched to **macro-ratcheting**, the one symptom with no lever and no
instrument. And unlike FactorD it is **MODE-PROOF**: these are bare `tp`-relative cals and arrays, not
pointer-array-dereferenced records ⇒ RULE 7 is moot.

**Ranked sub-levers within the chain:**
1. ★★ **`0xC64AD`–`0xC64B3` — seven single-byte per-term enables, all `0x01`.** The cleanest **subtractive
   census** available anywhere in this firmware: turn one term off, see which symptom moves, one byte at a
   time. Higher information per build than anything else in this document.
   🛑 **Blast radius: each byte deletes a term feeding the motor** — the same danger class as `0xC64C8`
   (D7). **A writer/reader census and a GATE-2 argument are mandatory before any of the seven is moved**,
   and the term each byte gates must be identified first — moving an unidentified one is a blind cut.
2. 🛑 **`0xC6B66`/`0xC6B80`, the 13-point LERP — MEASURED AND KILLED AS PROPOSED.**
   Same axis as FactorD, now known to be **absolute steering angle** (D2b), so X = `[0, 34, 64, 85, 100,
   120, 140, 157.6, 173.6, 191.6, 208.4, 228, 477.6]` **degrees**. Engaged time per segment, route `6d`:

   | segment | [0,34°) | [34,64°) | [64,85°) | [85,100°) | [100,120°) | ≥120° |
   |---|---|---|---|---|---|---|
   | engaged time | **88.62%** | 3.78% | 2.72% | 1.46% | 1.14% | **2.26%** |

   **88.6% of engaged driving sits in its FLAT FIRST SEGMENT**, where Y moves 899 → 908 — a **1.010×**
   change. Y does not reach its 1084 plateau until **120° of steering = 2.26% of engaged time.**
   ⇒ In practice this LERP delivers a **near-constant 0.878× broadband attenuation** and nothing else.
   Rewriting its Y row is therefore **a broadband gain trim on an always-on 1 kHz term**, not a shaped
   lever — the same class as V56's mute (null, and it cost damping) and the `0xC646C` work (null).
   🛑 **Do not propose it as a frequency-selective or shaped lever. Its only honest description is
   "±12% broadband gain on the friction lane", and that class has been falsified twice.**
3. ⚠ **`0xC6200` = 8192 — the clamp. DISCUSS ONLY AFTER A READER CENSUS.** Per RULE 11, *a clamp may be
   an interlock*: `0xC407E` looked like an ordinary output limit, sat one count under its own monitor's
   trip, was raised, and cost two mid-drive total losses of assist. **And `0xC6200` sits immediately
   beside `0xC6206`/`0xC6208`, the governor-slew cals V40 set to `0xFFFF` and bricked the ECU with.**
   That neighbourhood has already produced one brick. **Reader/writer census and a monitor search first.**
   ⊕ Note the asymmetry that makes *lowering* safer than raising: lowering a clamp loosens no monitor.
4. ⚠ **`0xC40D0` = 408 — the friction lane's ONLY pole.** A genuine **phase** lever, and phase is the
   dimension this kit has never moved. 🛑 **But it is on the lane V85 just linearised** — moving both in
   one build destroys V85's own interpretability, and V85 is still **unscored**. **Hold until V85 has a
   scored route.**

### D1 (rank 2) — `gain_A` rec0/rec1 LOWERED, AS A SINGLE VARIABLE, WITH AN S3 PROBE
`0xC6A72`–`0xC6A78`, `0xC6A86`–`0xC6A8C`. **Cal-only, 16 bytes, MODE-PROOF** (`gain_A` is not
mode-indexed — which is exactly why V69/V70's mode-10 `gain_B` edits could never reach r26).
**Why:** the only lever with a recorded association to the symptom the operator says is unfixed (B.3).
**Never isolated:** V42 moved six groups, V72 moved it alongside `0xC63A0`. 512 is the delivered value
with the best macro-ratchet history.
**What would falsify it:** an S3 probe that shows no change with a dose that is byte-proven in force.
**Blast radius:** r26 low-speed only; rec2/rec3 (≥50 km/h) untouched ⇒ **exactly 1.000× at and above
50 km/h by construction**. ⚠ r26's saturation rail depends on the **unmeasured** `avg(gp-0x69a4)` —
size it before moving. ⚠ **It removes damping from the rate lane, which V61 proved is the damper** ⇒
GATE 2 argument required, and it may worsen grinding. **This is the direction V61 got catastrophically
wrong at 0×; 512 is not 0, but the sign is the same.**

### D2 (rank 3) — **FactorD, modes 26 AND 27** — `0xD778C` / `0xD77A4`
`n=5, X=[0,50,100,150,700], Y=[1024]×5`. 🛑 **NEVER WRITTEN — verified over all 58 records, all six
families, all 80 images. The pointer array has never moved either.** [EVIDENCE, this session]
🛑🛑 **MEASURED THIS SESSION, AND IT CHANGES WHAT THIS LEVER IS. [EVIDENCE — route `6d`, 68,235 frames,
`_scratch/cache/r6d/r6d.npz`, V84's probe, fingerprint 100%]**

**(a) The liveness gate is OPEN.** `b5 = (gp-0x67fe ∈ {1,2})` reads **1.000000 over all 68,235 frames**,
in both arms. Recorded as *"NOT settled"* — **now settled.** The structural self-check
`v84_axis_without_gate` = 0.0 also passes.
⊕ *Correction of record:* `STATE.md` quotes the route-`6d` field alphabet as `{0x2F, 0x3F}`; the cache's
masked histogram is **`{0x28: 4231, 0x38: 64005}`** — the same field with bits 2:0 (the live
`STEER_SENSOR_STATUS`) masked off. Quote the masked form.

**(b) 🛑 `gp-0x6a10` IS NOT AN ANGLE-TRACKING ERROR. IT IS THE ABSOLUTE STEERING ANGLE.**
`b4 = (gp-0x6a10 ≥ 8 counts)` is reproduced by the pure predicate `|steering angle| ≥ 0.85°` at
**99.93% agreement engaged / 99.94% overall**, after excluding 361 frames where `cs_ang` is exactly 0.0
at zero speed (a stale-decode artefact, 0.5%). The transition is a knife-edge:

| \|steering angle\| | 0.40–0.60° | 0.60–0.70° | 0.75–0.80° | 0.80–0.85° | **0.85–0.90°** | 1.2–2.0° | >2° |
|---|---|---|---|---|---|---|---|
| P(b4) | 0.0000 | 0.0020 | 0.0417 | 0.0446 | **0.9500** | 0.9992 | **1.0000** |

Two independent reasons this is identity, not correlation: the step sits at **exactly the threshold's own
numeric value** (8 counts × 0.1 °/count = 0.8°), which is a **third independent confirmation of the
0.1 °/count scale**; and the same relation holds in the **manual** arm (97.7%), where there is no LKAS
command to track, so a *tracking error* is not even defined.

**⇒ 🛑🛑 THE FREQUENCY-SELECTIVITY ARGUMENT IS REFUTED, AND WITH IT THE HEADLINE CLAIM.**
The case for FactorD was: *angle amplitude ∝ 1/ω, so at 7.79 Hz the excursion is 3.6× that at 27.75 Hz ⇒
a FactorD rising with angle error preferentially damps the low-frequency micro-ratchet.* **That requires
the axis to be the OSCILLATION amplitude. It is the WHEEL POSITION.** A 1.29° p-p ring riding on the
engaged median cornering angle of **4.40°** indexes at ~44 counts of DC with ~±6 counts of ripple on top —
the ring is a **1.5% perturbation of the index**, not the index.
⇒ **FactorD is a STEERING-POSITION-SCHEDULED GAIN, in the same family as FactorC (speed) and FactorE
(motor rate). `memory/accord/calibration/accord-factord-is-the-angle-error-lever.md` should be corrected: *"the only
frequency-selective lever in this firmware"* is wrong — THIS FIRMWARE HAS NONE.**

**(c) But FactorD is NOT structurally inert — it has real coverage.** Engaged time by segment
(X = 0/5/10/15/70°):

| segment | [0,5°) | [5,10°) | [10,15°) | [15,70°) | ≥70° (flat tail) |
|---|---|---|---|---|---|
| engaged time | **63.86%** | 19.44% | 2.33% | 7.76% | 6.61% |

**36.1% of engaged time is above 5°, spanning three of its four segments.** Engaged `|angle|` percentiles:
p25 3.43° · **p50 4.40°** · p75 6.30° · p90 48.07° · p95 84.00°.

**⇒ REVISED VERDICT: FactorD survives, DEMOTED and RE-AIMED.** It cannot target a frequency band. What it
*can* do is schedule the damper on how far the wheel is turned — which maps onto the operator's own
*"grinding at slow-turn-while-braking"* and *"grind #2 from my hard turning"*, both **cornering**
descriptions. **Propose it as a cornering-regime lever with that rationale, or not at all.** `n=5` ⇒
cal-only; **MODE-INDEXED, write 26 AND 27**; multiplies into the same damper product as FactorC/E ⇒
**GATE 2 applies**, and now a magnitude-only argument *is* sufficient, because it changes no phase.

### D3 (rank 4) — `gain_B` in the ENGAGED columns (`0xD7A88`/`0xD7AC4`/`0xD7B00`/`0xD7B3C` m26; `…9C`/`…D8`/`…14`/`…50` m27)
🛑 **16 of 16 records never written by any build, any array, any mode.** [EVIDENCE, this session]
**Why:** this is **exactly what V69 and V70 were designed to do, and they wrote mode 10.** r24 is the
identified S1 actor. Lever B's flat arm has **one DOF against two constraints** (creep needs boost,
highway needs ≈1×); `gain_B`'s **speed axis** (`[0,400,1400,3000]` counts on the `0xC6010` cross-axis)
gives that shape natively. Leaving m24/m25 at Honda makes it **engaged-only by construction.**
**What would falsify it:** a probe rung sized to the lane's own reachable output (V69 spent all three
rungs on gates that were structurally vacuous — do not repeat).
**Blast radius:** 8 records, manual columns untouched. Cal-only. **MODE-INDEXED — write 26 AND 27.**

### D4 (rank 5) — `gain_A` rec2/rec3 (`0xC6A9A`–`0xC6AA0`, `0xC6AAE`–`0xC6AB4`) — the ≥50 km/h r26 records
**Touched by V42 only, ever; frozen for 50 images.** The **only untouched cells that reach the HIGHWAY
regime on the r26 lane** — and the highway grind is the one symptom Lever B demonstrably does not fix
(F13). Cal-only, mode-proof. ⚠ Once `0x3AA96`=`FB` is armed, `gain_A` becomes the **manual-only** path in
the arms' shadow — check that before writing.

### D5 (rank 6) — `0xC63AC` = 102, the Path-2 accumulator one-pole IIR
Never written, 55 images. 102/1024 ⇒ **fc ≈ 16.7 Hz, sitting directly in the S1 band.** A first-order
pole this close sets both the magnitude **and the phase** the damper arrives with, and it has never been
moved in either direction. 1 reader family (`FUN_00038148`). ⚠ **GATE 2 — moving a pole changes phase in
a closed loop; this is the class that bricked V48B.**

### D6 (rank 7) — `0xC6C42` = 4, the differentiator delay D
Never written, 55 images. **The PHASE lever**, specified in V62's own handoff as the follow-up *"if V62
comes back null"* and never built. Everything else in this kit changes magnitude; this changes when.
⚠ GATE 2, same class as D5.

### D7 (rank 8) — `0xC64C8` = 0x00, the aggregator MODE SELECTOR
Never written, 55 images; **0 writers, 1 reader.** Mode **1 DISCARDS the entire aggregator contribution**;
mode 2 blends. The aggregator is now **known** to reach the motor via the `gp-0x6acc` bridge
(`gp-0x6b94` → `FUN_0004503c` → `gp-0x6ace` → `FUN_000456a4` → `gp-0x6acc` → shaper `@0x431C4` →
`gp-0x6b08 @0x43206` → integrator → `gp-0x6b98` → FOC → PWM).
🛑 **UNTRACED AND DANGEROUS** — a one-byte switch that deletes a lane feeding the motor, and removing the
governor's slew from that same lane is what bricked V40. **Writer census never run. Do not fly without a
GATE-2 argument.** Value as a **diagnostic ON/OFF for the whole compensation stack**, not as a fix.

### D8 (rank 9) — the virgin plant-model cal block around `0xC40xx`
`0xC407C` = 461 (interlock neighbour) · `0xC40D0` = 408 (**the friction lane's ONLY pole**) · `0xC40D2` =
102 · `0xC4080` = 0 · `0xC40D4`/`D6`/`D8` (command / inertia / torque EMA alphas) · `0xC4048`/`4C`/`50`
(the FIR taps — currently a pass-through) · `0xC613A`, `0xC6468`, `0xC646E`.
**All frozen at stock across the whole arc; V85 asserts them as `LANE_CALS` and moves none.** `0xC40BC`
is the only cell of this block ever written, and only by V85. ⚠ **`0xC40D0` is a phase lever on the same
lane V85 just linearised** — moving both at once destroys V85's own interpretability.
⛔ Anything here that **adds** friction/dissipation collides with the max-angle-rate constraint.

### D9 (rank 10) — `0xC61B8` = 102, the pre-gain deadband
Never moved in 55 images **while its clamp siblings `0xC61B2`/`0xC61B4` went ×4** ⇒ the deadband now
covers ~4× more of the LKAS range than the factory validated. `→ 26` is a never-tried
**engage-ramp correctness fix**, not a grinding lever. Low expected value for the four symptoms; listed
because it is a real, cheap, unexamined inconsistency introduced by V38.

### D10 — `0x3AB76`/`0x3AC20` = `A8` (4×)
The reachable set is `{AB=÷2, AA=1×, A9=2×, A8=4×, A7=8×}`. **Only `AA` and `A9` have ever been built.**
The famous "×4 rung" that made the ladder look non-monotone was **mode-10 `gain_B` and inert** ⇒ the real
mode-proof ladder is **0× (V61, much worse) → 1× (stock) → 2× (V62/V65, the only measured fix)** and
**above 2× is wholly unexplored.** ⚠ Same grind-#2 risk as D0, amplified.

### 🛑 THE THREE ANALYSES THE RECORD SAYS ARE OWED AND STILL HAVE NEVER BEEN DONE
1. **`FUN_00036c12`'s SIGN** — ranked #1 of 4 in the feasibility doc. Static, one session, no drive.
   **`0xC407E` LOWERED (511→384→256) is blocked on this and nothing else.** Note: only ever RAISED;
   lowering a clamp loosens no monitor and **cannot re-open the DTC-0x1d fault.** ⚠ Its input `gp-0x6c2c`
   is filtered motor **acceleration** ⇒ ≈0 under steady motion ⇒ it costs **zero DC impedance** and does
   **not** collide with the max-angle-rate constraint.
2. **Aggregator saturation + zero-reject census** at the proposed operating point — blocked on
   `gp-0x6c2c`'s physical scale, OPEN since V76.
3. **Engagement-edge impulse-response estimate**, ≥40 edges, γ² ≥ 0.8 over K ≥ 10 non-overlapping
   **episodes**. Uses corpus already on disk.
📋 **And a fourth, new and cheap: decode `b5`/`b4` from route `6d` to unblock FactorD (D2).**

---

# E. THE REGRESSION GUARD — a checklist any V86 candidate must pass

Every item is derived from a recorded failure, not invented.

### E1 — HARD-FAULT INTERLOCK
- [ ] **`0xC407E` == 511.** Honda ships this clamp **one count under its own 512 trip** (`FUN_00036d74`
      tests `|gp-0x6b26|/1024 > cal(0xC4004)` = float 0.5, single-frame, un-debounced, mode-proof, called
      unconditionally at 1 kHz). V73 raised it to 850; **V74 and V75 both hard-faulted with latched total
      loss of assist.** 🛑 **DO-NOT-RAISE. And do not "fix" it by raising `0xC4004`.**
- [ ] **RULE 11 generally: before raising ANY clamp, saturation or output limit, search for a monitor
      that tests the same cell.** Two methods; a null here is load-bearing.

### E2 — THE BRICKING CLASS
- [ ] Is this a **code cave**? V24, V27 and V48B all bricked the ECU. Every success since V29 has been
      cal-only or a **single in-place branch/displacement edit** — a different, far lower risk class.
- [ ] **GATE 1 — RAM OWNERSHIP.** Every byte of the full footprint proven free **including writers and
      register-indirect / 6-byte extended-displacement accesses**. `gp-0x1401..0x1502` is poison.
      🛑 **Static clearance is NOT sufficient — `gp-0x1500` passed both static methods and still failed
      on-car.** A live probe is the only reliable test.
- [ ] **GATE 2 — CLOSED-LOOP STABILITY: magnitude AND phase, in EVERY loop the touched signal is in**,
      especially the always-on base-assist loop. Never a single-frequency magnitude.
- [ ] **GATE 2 COROLLARY (V80's defect):** *"does not clip"* and *"is not a relay"* are different
      statements and **only the first was ever checked.** Required shape tests: **flatness ratio**,
      **describing function `N(50)/N(500)`** (Honda viscous = 0.00×, V75 1.45×, V80 **3.27×**, V85's
      pre-edit relay **7.87**), **distance to the rail in counts** (V80 sat at ceiling − 17 and passed
      every `> ceiling` guard), and **a probe rung sized to the SATURATED regime**.
- [ ] **A cancellation biquad in any form is NOT RECOMMENDED** — its poles sit at r ≈ 0.99878 while `f₀`
      moves −14% with load ⇒ delivered fully INVERTED. And the wheel-on-torsion-bar mode at
      **12.8 Hz [12.1, 13.6]** sits **between** the two symptom bands ⇒ a single-gain `θ̈` feedforward
      tuned at 7.79 Hz **arrives at 20 Hz inverted.**

### E3 — THE FROZEN CELLS (from `builds/v80_v107/build_v85_tva.py`; assert each from the BUILT image)
| cell | must be | why |
|---|---|---|
| `0xD77DA` | 0 | FactorC m26 `Y[0]` → Honda. **The engaged-only damper, deleted at V84** |
| `0xD77EE` | 0 | FactorC m27 `Y[0]` → Honda |
| `0xD7822` / `0xD7824` / `0xD782C` | 60 / 400 / 140 | FactorE m27 → Honda |
| `0xC6446` | 5244 | Lever B's r24 arm — the flown V67/V68 value |
| `0xC6444` | 512 | r26's engaged arm — stock, deliberately |
| `0xC407E` | 511 | the DTC-0x1d interlock |
| `0xC6CD0` | 3564 | V57's decoupled forward reader — the 4× LKAS setpoint |
| `0xC63A0` | 1024 | Path-2 damper weight, Honda's |
| `0x3AA96` | `0xFB` | Lever B's gate repoint |
| `0x454FE` | `0xB5` | V42's macro-ratchet byte — **lost twice already; KEEP** (even though eliminated) |
🛑 **The damper stays frozen** — the ring's four-point dose–response is the strongest causal chain the
kit owns. **Any 26–31 Hz regression toward V81's 25.1% burst duty is an abort signal.**

### E4 — MODE PROOF (RULE 7) — 🛑 EXTENDED THIS SESSION
- [ ] The car is **`TVCA4`, row 11**: modes **24/25 MANUAL, 26/27 ENGAGED**. Mode 27 is a **second
      engaged column** — V83a forgot it and shipped V81's whole damper live, unnoticed.
- [ ] A mode-indexed lever must be written in **26 AND 27**, or it is a bet.
- [ ] 🛑 **NEW: audit over all 58 pointer-array slots, not the 7-mode view.** V85 still carries 14+
      residual damper records at modes 0–5/10–12/14/15/17/23/29. They are unreachable on this car
      [BELIEF, structural], but the 7-mode reader cannot see them at all.
- [ ] Builds that delivered **byte-stock** and must never be cited as tested: V44, V47, V69, V70, V72
      (Levers B/C), V73 (Levers D/E).

### E5 — THE MAX-ANGLE-RATE CONSTRAINT (the operator's standing hard constraint)
⛔ **Reject or flag explicitly any V86 that:**
- [ ] lowers `0xC6CD0` (forward LKAS gain), `0xC61B2`/`0xC61B4` (output clamps), or the setpoint-limit
      records — **all reduce peak EPS torque from a rail-pinned command in exact proportion.**
      *(These are legitimate as a labelled one-flight DIAGNOSTIC arm, never as the fix.)*
- [ ] **raises** friction (`0xCBE74` engaged rows — falsified upward, F16, implicated in both faults),
      raises `0xC407E`, or lowers `0xC40BC` back toward a relay.
- [ ] raises the damper (FactorC/E m26/m27) — frozen, and it is DC-**opposing**: sign is
      `−sign(motor rate)` ⇒ it fights the **driver** too, even turning WITH the command.
- [ ] 🛑 **RAISES authority.** *Three independent lines say more authority makes it worse.* ach/dem =
      1.09 creep · 1.22 at 14–40 · **1.88 above 86 km/h** ⇒ the *"LKAS angle rate is limited"* claim is
      **REFUTED**; what the operator felt is **impedance**. Do not raise openpilot's 123 ct/frame cap;
      the 8× path and the governor-slew lever are **CLOSED**.

### E6 — DO NOT RE-PROPOSE (each already flashed and null, or structurally dead)
`0xC6450`→32 (V46) · `0xC644A`→32/64 (V43) · `0xC6206`/`0xC6208` (V40 ☠, V45) · the cap table (V41) ·
`0xC6AFC`/`0xC6AFE` mute (V56 — **at any authority value**) · `0xD2006` (V60) · `0xC6440`/`0xC643E`
(V63/V64, detector never arms) · `0xC6444` alone (**null by construction** unless `0x3AA96` is also
repointed) · `0xC6194` (dead cal, `0xC63CC`=0 multiplies it out) · the eight aggregator zero-type range
gates (structurally vacuous) · a **new CAN mailbox ID** (the gateway is a **whitelist**; only `0x14A`,
`0x18F`, `0x1AB` cross — telemetry must ride `0x14A` byte 4 bits 7:3) · `0xC646C` moved alone (5 readers;
2 scale raw driver torque on a feedback path to the motor) · `0xC6C42`… *(no — that one is untried; see
D6)*.

### E9 — 🛑 THE OPERATOR'S EXPLICIT FORBIDDEN LIST (V86 session, 2026-08-08)
A V86 candidate must not reintroduce **any** of these. They are his words, not kit bands:
- [ ] **HARD FAULTS.** V74 and V75 both latched a total loss of power steering mid-drive. ⇒ E1.
- [ ] **GRIND #2.** He reports **none on V85** from hard turning or on the highway. 🛑 [BELIEF, whole-
      corpus] **`r24 ≥ ~2` is necessary for grind #2 in every build that has produced it** ⇒ any proposal
      that raises the delivered r24 dose above V85's 1.994 must state this and justify it.
- [ ] **ANY CHANGE THAT LIMITS MAX LKAS-COMMANDED STEERING ANGLE RATE (°/s).** ⇒ E5. Note this rules out
      *adding* dissipation as well as *lowering* authority: friction up, `0xC407E` up, damper up,
      `0xC40BC` back toward a relay, and the D0 (ii)/(iv) r26 increases all add impedance.

### E10 — 🛑 THE 32-SLOT MODE-MAP RULE (new this session)
- [ ] **Any V86 touching a factor table must be audited over all 58 pointer-array slots, not the 7-mode
      view.** The old reader looks at modes {10,11,12,24,25,26,27} only. V85 still carries **14+ residual
      damper records** at modes 0–5/10–12/14/15/17/23/29 that the 7-mode view cannot see. They are
      unreachable on a row-11 `TVCA4` car [BELIEF, structural — only modes 10/11 have a *measured*
      refutation, V72's probe 0/87,940], but **V83a shipped V81's entire damper live in mode 27 and nobody
      noticed for a whole flight.** That is this exact failure one row over.
- [ ] Confirm the **pointer arrays themselves** are unmoved (they are, on all 80 images — verified).

### E11 — 🛑 THE `0xC6200` NEIGHBOURHOOD NEEDS A READER CENSUS BEFORE IT IS EVEN DISCUSSED
- [ ] `0xC6200` sits immediately beside **`0xC6206`/`0xC6208` — the governor-slew cals V40 set to
      `0xFFFF`, which bricked the ECU (EPS lamp, no power steering, at ignition).** One brick has already
      come out of this address neighbourhood.
- [ ] Combine with RULE 11: `0xC6200` is a **clamp**, and a clamp may be an interlock. **Reader/writer
      census + a search for a monitor testing the same cell, two methods, before any proposal.**

### E12 — ★ `0xC61F6` = 3 IS A LIVE DEADBAND ON THE RATE LANE — newly identified, virgin
- [ ] `0xC61F6` is **not** a gain and **not** a clamp. Decompiled at `0x3AC1C`–`0x3AC32`, it implements
      `|x| ≤ 3 → 0, else x ∓ 3` on the r24 lane output, immediately after `sar 0xa`.
      **Never written by any build; frozen 75 consecutive images.**
- [ ] 🛑 **A deadband is the DUAL of a relay.** V85's whole thesis is that a relay is bad because its
      describing-function gain **rises as amplitude falls**. A deadband's gain does the opposite — it
      **rises with amplitude** and is **zero for small signals**. ⇒ at the small rate-lane excursions
      where micro-ratcheting lives, this deadband may be **deleting the damping entirely**. Lowering it
      3 → 0 is a candidate; raising it is the opposite bet. **Neither has ever been built.**
- [ ] ⚠ **It is on the same lane as Lever B**, so it is *not* independent of the r24 dose — size it
      against the lane's reachable output before proposing (see E13).

### E13 — 🛑 V84's `b7`/`b6` RUNGS WERE MIS-SIZED. DO NOT FIRE THEIR FALSIFIER.
- [ ] `studies/probes/decode_v84_probe.py` pre-registered: *"the predicted step is 0.24 manual → 0.64 engaged (~2.6×).
      If that step is absent, Lever B is not in force and no S1 verdict may be drawn from the flight."*
      **Measured: `b7` = 0.0 and `b6` = 0.0 — 0 of 68,235 frames, in BOTH arms.**
- [ ] 🛑 **That is NOT evidence Lever B was out of force. The rung could not have fired either way.**
      `b7`/`b6` test `|r24| ≥ 1024`. With the armed gain 5244, `r24 = (r1 × 5244) >> 10` needs
      **`|r1| ≥ 200`** — and the record already states **`|gp-0x4f62| < 201` for the entire drive**.
      The rung sits exactly at the edge of its input's observed range. [EVIDENCE: the 0.0000 duty and the
      recorded input bound are two independent facts that agree.]
- [ ] ⇒ **This is the recorded failure mode repeating**: *size a probe rung against the LANE's own
      reachable output, not a downstream gate's width* — V69 spent all three rungs this way and its `b4`
      was structurally vacuous. **Apply RULE 5 to the falsifier: it only fires if it COULD have fired.**
- [ ] ⇒ Any V86 rung on the rate lane must be sized against `|r1| < 201`, i.e. thresholds in the
      **tens-to-low-hundreds** of counts, not thousands.

### E7 — BUILD AND RECORD HYGIENE
- [ ] **CRC 50/50.** Value-anchored verifier, not span-based (`verify/diff_build_vs_stock.py` is span-based and
      will miss a value regression).
- [ ] **Exactly ONE flashable `.rwd` per build number on disk.** Byte-identical duplicates deleted;
      differing ones renamed `SUPERSEDED-DO-NOT-FLASH-…`. 🛑 A re-cut under the same build number
      **destroys its predecessor's plain image** — hazard still OPEN, fix recommended not applied.
- [ ] **Re-verify every reported artefact from disk at close-out.** Agent replies are not evidence.
- [ ] **Write the flight result into `STATE.md` in the SAME pass that scores it.** V83a and V84 were
      *both* left recorded as unflashed after flying — **a flown build recorded as unflashed WILL be
      re-proposed.**

### E8 — PRE-REGISTRATION AND SCORING
- [ ] State the falsifier **before** the flight, and name the abort signal.
- [ ] 🛑 **A pre-registered falsifier only fires if the lever was IN FORCE and the exposure was
      ADEQUATE. Check both before scoring it** (RULE 5 applied to a falsifier — this is what wrongly
      killed the damper-ring model at V83a).
- [ ] **Bootstrap over EPISODES, not windows**; compute the split-half null **FIRST**.
- [ ] **Matched speed distributions** with a per-window census — a moving wheel order manufactures an
      "only on route X" line, and the band-centre test is not sufficient.
- [ ] **Probe the GATE and the INPUT, not just the output** — budget cave bits for enable + raw input.
- [ ] **Size probe rungs against the LANE's own reachable output**, not a downstream gate's width. V69
      spent all three rungs for nothing; its `b4` was **structurally vacuous**.
- [ ] 🛑 **Score bands; let the operator score symptoms. Never call anything FIXED that he has not
      called fixed.** An absence of complaint is not a cure. A band moving is not a symptom being fixed.
      **Never let a secondary instrument win over a primary symptom failure.**

---

# F. WHAT CLASS OF INTERVENTION EACH ERA WAS — so V86 can say how it differs

| era | builds | class of intervention | outcome |
|---|---|---|---|
| the cause | **V38** | LKAS **authority** ×2.13 (cal-only, zero code edits) | grinding + ratcheting first appear in the record the very next session |
| authority / filters / poles / caves | V39–V52c | rate guards, slew caps, EMA poles, notch biquads, broad low-passes | all null; **V40 and V48B bricked**; the low-pass **strategy** closed (lag scales with attenuation) |
| telemetry probes and lane mutes | V53–V61 | measure, don't fix; then mute lanes | characterised S1 and S2; **V56 mute null and cost damping; V61 (0× rate lane) much WORSE ⇒ the rate lane is the damper** |
| **the rate lane** | V62–V73 | `sar` ×2 (Lever A), then the `latActive`-gated r24 arm (Lever B) | ★ **the only two measured grinding fixes in the kit** — and **grind #2 was created here** |
| the base-assist damper | V74–V83a | arm and dose an engaged-only Coulomb damper (which is **ours**, not Honda's) | **falsified for S1 and S2**; **two hard faults** (from `0xC407E`, not the damper); V80 = worst grinding ever |
| damper reverted to Honda | **V84** | delete the damper in both engaged columns + re-arm Lever B | fault-free; **fixed nothing**; the **ring** collapsed to 2.54% burst duty |
| **linearise the 1 kHz Coulomb relay** | **V85** | one `tp` scalar, mode-proof, touches no gain / rate limit / filter / pole | *"grind #1 a little better, micro-ratcheting barely better, **ratcheting still unfixed**, no grind #2"* — **UNSCORED** |

🛑 **What V86 must be able to say about itself:** which of these classes it belongs to; whether it is a
**new lever** or **the same lever pushed the other way**; if a cell has been frozen for N builds, **the
value of N** (this document gives it); and if it is a re-run, **what is different this time that makes a
different result likely.**

**The honest reading of the arc:** the rate lane produced the only two measured fixes and is now at its
ceiling *with only half of it on the car*; the damper era produced two faults and no symptom fix; and
the one variable the operator's own premise names — **the V38 drive level** — has been frozen for 47
builds and never once tested. Macro-ratcheting, the symptom he calls unfixed, has **no instrument at
all** and has not been the target of a single build since V42, whose attribution is void.
