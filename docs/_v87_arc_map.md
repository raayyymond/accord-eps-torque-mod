# THE V87 ARC MAP — V38 → V86B AS ONE ARC, READ FROM THE IMAGES

**Built 2026-08-08 for the V87 session.** Purpose: prove novelty rather than assert it. The operator's
requirement is explicit — *"Do NOT give me a repeat of any previous route. I need something novel or not
done before at all, or a combination of things not done before."*

> **READER** [EVIDENCE]: `analysis-2020accord/arc_map_v87_reader.py` — extends
> `analysis-2020accord/ledger_v38_to_v85_bytes.py` to **V86 and V86B** (the old reader stops at V85 and
> could not score the current candidates at all) and adds three scans the old one lacks: a full-block
> virginity sweep of `[0xC4000, 0xC4200)`, a whole-image diff-vs-stock census, and pairwise V85→V86 /
> V85→V86B byte diffs. **58 images** (57 builds + stock). LE (`struct.unpack_from('<h'|'<H'|'<I')`);
> factor records dereferenced through their pointer arrays, never a hard-coded address.
> Anchors asserted and passing: stock `0xC646C`=891 · `0x454FE`=0xBA · `0xC407E`=511 · `0xC40BC`=600 ·
> `0x2A1F0`=0x746C · len `0x100000`.
> **Relationship to `docs/_session_v86_arc_map.md`:** that document is verified and largely correct; this
> one extends it to V86/V86B and **corrects it in three places** (§0 below). Where the two disagree,
> `docs/STATE.md` §6 ("LEVERS KILLED ON EVIDENCE", 2026-08-09 late) is newer than both and wins.

---

## §0 — WHERE I DISAGREE WITH THE RECORD

| # | claim as recorded | where | my finding [EVIDENCE, image read] |
|---|---|---|---|
| **C1** | *"the entire plant-model cal block is virgin across all 84 builds"* | `STATE.md` V85 block §5 | 🛑 **FALSE.** `[0xC4000, 0xC4200)` = 256 halfwords; **4 have been written**: `0xC407E` (V73/V74/V75/V76g/V77/V77b → 850 — *the hard-fault mechanism*), `0xC4120` (V48A, byte `01`→`00`, the type-8 slot mute), `0xC40BC` (V85), `0xC40D4` (V86). **252/256 = 98.4% virgin** is the honest number. The block is not a virgin frontier — it already contains the kit's worst safety incident |
| **C2** | *"FREEZE the damper cells in every future build"* (V84 flight directive) | `STATE.md` V84 §1; `_session_v86_arc_map.md` E3 | ⚠ **V86B VIOLATES IT BY DESIGN.** V86B writes FactorC m26 `Y[0]` 0→**908** and m27 `Y[0]` 0→**875** — re-arming the engaged damper V84 deleted. This is deliberate and documented in `STATE.md`, but it means **V86 and V86B are not the same silent-loss state**, and any V87 built "on the current candidate" must say *which one* |
| **C3** | F17's damper-as-S1 falsification table lists **V83a at `k` = 0.2265** | `LEDGER-V38-TO-V84.md` 3(a) F17; §2.3 V83a row | ⚠ **That dose is refuted by the same image read that retracted F18.** V83a left **mode 27 carrying V81's entire damper**, so its true engaged dose was route-dependent between V81's and 0.23 — not 0.23. **F17's verdict survives, but via V84** (both engaged columns Honda, S1 ≈ 1.10× V81 ⇒ S1 flat in `k`), **not via the mis-dosed V83a point.** The row still quotes 0.2265 and should be annotated |

Two further precision notes, not disagreements:
- **V86B's dose vs V81 is rate-dependent.** `STATE.md` quotes **10.1%** of V81's flown dose. Computing the
  FactorC×FactorE product from the bytes: at 42 °/s the ratio is **0.11×**, at 85 °/s it is **0.42×**
  (V86B keeps Honda's FactorE `X`=[60,400,…] `Y`=[0,140,539,927]; V81 had `X`=[12,200,…] `Y`=[0,539,539,927]).
  **The single "10.1%" figure holds at one operating point only.**
- **Frozen-N counted back from V86B walks through V86** in build order. V86 and V86B are *siblings* on the
  same V85 base, so an N quoted against V86B is one larger than the causally meaningful number.

---

# A. THE CLASS TABLE — V38 → V86B

Operator quotes are verbatim from `docs/LEDGER-V38-TO-V84.md` §2.1–2.3 and `docs/STATE.md`.
"On car today" = present on **V86 / V86B**, read from the images.

## A.1 THE CAUSE — V38

| build | flew | CLASS | cells · direction | measured | **operator's words** | on car today |
|---|---|---|---|---|---|---|
| **V38** | ✅ | **AUTHORITY ↑** (cal-only, 0 code edits) | `0xC646C` 1782→**3564** · `0xC61B2`/`B4` 1024→**2048** · corridor ±1024→±5120 · boost floor →5120 · setpoint 15360→**16384**. Net **2.00× → 4.267×** | S1 **CREATED**: 20–30 Hz **63.66×** vs the 2×-era over 201 matched s; 0.5–5 Hz control **0.37×**. S3 created | *"hard turns appear authority-limited by a feedback loop"* | ✅ **ALL OF IT, FROZEN 56/57 IMAGES** |

## A.2 V39–V52c — RATE GUARDS · SLEW CAPS · POLES · FILTERS · CAVES

| build | flew | CLASS | cells · direction | measured | **operator** | today |
|---|---|---|---|---|---|---|
| V39 | ✅ | cave: conditional lane kill | zero r24 when `driver<320 ∧ \|LKAS\|≥417` | S1/S3 null | *"fixed neither symptom"* | ❌ |
| **V40** | ✅ | governor slew removed | `0xC6206`/`0xC6208` → `0xFFFF` + flat cap | — | ☠ **EPS lamp, no power steering at ignition** | ❌ |
| V41 | ✅ | motor-rate cap flattened | cap table → flat 5325 | S1/S3 null ⇒ cap **FALSIFIED** | *"boots and drives cleanly, fixed neither"* | ❌ |
| **V42** | ✅ | 🛑 **six groups at once** | `0x454FE` `BA`→`B5` **+ all four `gain_A` records → 0** + `0xC643E`→0 + `0xC6444`→0 + V41 revert | S3 fixed (felt). ⚠ attribution **VOID** — `gp-0x67fa==4` fires **0/123,277** | *"FIXED THE HARD-TURN RATCHET"* (ch.1); *"No effect"* (ch.2) | `0x454FE` ✅ (**inert**); the r26 kill ❌ |
| V43 | ✅ | derivative pole ↓ | `0xC644A` 1024→**32** | S1 null | *"fixed neither symptom"* | ❌ (frozen 43) |
| V44 | ✅ | damper floor ↑ | FactorC **m10/m11** | 🛑 **INERT-BY-MODE** | (null) | ❌ |
| V45 | ✅ | slew step ↓ | `0xC6206` 512→205 | S1 null | (null) | ❌ |
| V46 | ✅ | EMA pole ↓ | `0xC6450` 1024→32 | S1 null | *"no noticeable change"* | ❌ (frozen 47) |
| V47 | ✅ | damper shape | FactorC+E **m10/m11** | 🛑 **INERT-BY-MODE** | *"marginally quieter at 5 mph"* (causal verdict withdrawn) | ❌ |
| V48A | ✅ | carrier mute | **`0xC4120` 1→0** + `0xC67B8/BA/BC` 1024→256 | S1 null | *"did NOT fix the vibration"* | ❌ |
| **V48B** | ✅ | **cave: 21.4 Hz notch biquad** | RBJ Q≈3.2, `gp-0x1500` | — | ☠ **wheel spun full-authority at startup** | ❌ — **created GATE 1 + GATE 2** |
| V49/V50/V52 | ❌ built | — | — | — | — | ❌ |
| V52C | ✅ | **broad 12 Hz EMA on 19 carriers** | α=74/1024 | S1 null; *"halved the mode"* **STRUCK** (no rlog) | *"did not fix the vibration; clearly changed manual feel"* | ❌ — ⇒ **the low-pass STRATEGY is closed** |

## A.3 V53–V61 — TELEMETRY PROBES AND LANE MUTES

| build | flew | CLASS | cells | measured | **operator** | today |
|---|---|---|---|---|---|---|
| **V53** | ✅ | feature + telem | `0xC62EA` 320→**0** | steer-to-zero **CONFIRMED** | *"the steer-to-zero feature worked"* | ✅ **PRESENT** |
| V54 | ✅ | probe only | authority probe | ★★ authority **~0 by design**; mode moves with speed 20.12→21.68 Hz | *"this drive exhibits the vibration issue"* | — |
| V55 | ✅ | probe only | partition probe | ★★ **the ~21 Hz is generated INSIDE the EPS** (877×/996×, γ²=0.93) | — | — |
| V56 | ✅ | **lane MUTE** | `0xC6AFC`/`0xC6AFE` 32768→**0** | S1 **null** ⇒ `gp-0x6ad4`/`FUN_0003a382` **ELIMINATED** | *"damping removed and a new few-Hz resonance"* ⇒ revert | ❌ (frozen 33) |
| **V57** | ✅ | **decouple** (hygiene) | `0x2A1F0`→`0x7CD0`, `0xC6CD0`=3564, `0xC646C`→891 | null both, ≤0.28 dB. ★★ S2 characterised: ~7.4 Hz | *"grinding is not 7.4 Hz, that is the ratcheting"* | ✅ **PRESENT** |
| V58/V59 | ✅ | probes only | no cal change | pump real (42.19 Hz, 11.10× engaged) but **UNDECIDABLE** | — | — |
| V60 | ✅ | boost blend ↓ | `0xD2006` 102→43 | 🛑 **NULL** (pre-registered) ⇒ **parametric-pump arc CLOSED** | *"It did not fix the vibration issue."* | ❌ |
| **V61** | ✅ | **rate taps KILLED (0×)** | `0x3AB6C`, `0x3AC16` | ★★★ **WORSE**: `e_18-22` = **2501**, 18.25 Hz, ×7.9 power | LKAS on *"significantly worse"*; **off** *"grinding newly present"* | ❌ ⇒ 🛑 **the rate lane is the DAMPER** |

## A.4 V62–V73 — THE RATE LANE (r24 / r26)

| build | flew | CLASS | cells · direction | measured | **operator** | today |
|---|---|---|---|---|---|---|
| **V62** | ✅ | **LEVER A** — `sar` ×2, BOTH lanes, ungated | `0x3AB76`+`0x3AC20` `AA`→**`A9`** | ★★★★ **KIT'S FIRST MEASURED FIX.** pooled **0.39 [0.32, 0.48]** vs null [0.88,1.13]; `e_18-22`=**168**. S2 not moved | *"Original grinding at 2–5 mph is gone!"* | 🛑 **ABSENT — 18 images (V86) / 19 (V86B)** |
| V63 | ❌ built | detector arms ↑ | `0xC6440`→4096, `0xC643E`→3072 | inert (V64) | — | ❌ |
| V64 | ✅ | V63 + detector probe | | 🛑 **NULL IS ON THE GATE** — 0/14,980 | *"The vibration/grinding at low speeds is not fixed."* | ❌ |
| V65 | ✅ | = Lever A + saturation ladder | | ★★★ **aggregator NEVER rails** ⇒ the loop is LINEAR there | *"makes the entire car vibrate, almost like I have a subwoofer… **regardless of LKAS engagement**"* | ❌ |
| V66 | ❌ built | **revert Lever A** | | 🛑 **the revert flew anyway, as the base of V67–V72** | — | — |
| **V67/V68** | ✅ | **LEVER B** — `latActive`-gated r24 arm | `0x3AA96` `C5`→**`FB`** + `0xC6446` 512→**5244** | ★ **BEST S1 IN KIT 0.40 [0.27,0.58]**, `e_18-22`=**109**; suppression in ONE arm only; gate ≡ `latActive` 99.983%. 🛑 **HIGHWAY NULL** | V67 *"Grind #2 seems mostly gone… but a higher-speed grind #2 on lane changes/turns, only LKAS-engaged"* | ✅ **PRESENT** |
| V69 | ✅ | intended ×4 → **delivered: Lever B OFF** | mode-10 `gain_B` = **byte-stock** | S1 back (746). ★★ **RATCHET characterised: 7.79 Hz, speed-invariant, in the bar and angle rate but NOT in the command** | — | ❌ |
| V70 | ✅ | **byte-stock** | mode-10 `gain_B` | ★★ ratchet is **engagement-REQUIRED** (83.0% vs 0/118, p=3.8e-41) and **build-independent ⇒ NO BUILD HAS EVER MOVED IT** | *"stiffer"* — mechanism refuted | ❌ |
| V71a | ❌ built | Lever A + `0x454FE` | | ★★ **the only artefact carrying both — never flew** | — | ❌ |
| V71b | ✅ | r26 ×2 alone (ungated) | `gain_A` rec0/rec1 ×2 | `e_18-22` = **545** — inside the stock band. Grind #2 **absent** | *"I definitely experienced grind #1."* | ❌ |
| V71c | ✅ | r26 arm ↑ with the gate | `0xC6444` 512→**3072** | `e_18-22`=**223**; **grind #2 PRESENT** (7 bursts, 44.31 Hz). ★ carries **neither** `sar` byte ⇒ *"grind #2 is V62's sar"* **REFUTED** | *"attenuated but still present"* | ❌ |
| V72 | ✅ | damper weight + r26 cut (rest INERT) | `0xC63A0`→2048, `gain_A` rec0/1→512 | ★★★★★ **THE PROBE MADE RULE 7** — 0/87,940 ⇒ **the car is NOT in mode 10/11**. Creep grind #2 fixed | 🛑 **he settled the naming: TWO ratchets — MACRO (fixed), MICRO = the 7.79 Hz line** | ❌ |
| **V73** | ✅ | **interlock clamp ↑** (rest INERT) | `0xC407E` 511→**850** | live ~80% of burst frames, **no band change** | *"same vibration frequency; grind #1 audible, micro-ratchet not"* | ❌ ⇒ **the hard-fault mechanism** |

## A.5 V74–V83a — THE BASE-ASSIST (ENGAGED-ONLY COULOMB) DAMPER

🛑 **This damper is OURS, not Honda's.** Stock ships m24 ≡ m26 and `FactorC Y[0]==0` in all 13 distinct
stock records. It was **armed at V74**, never before.

| build | flew | CLASS | dose `k` | measured | **operator** | today |
|---|---|---|---|---|---|---|
| **V74** | ✅ | **first arming of the engaged damper** | 0.58 | live 67.44% engaged creep vs 0.29% manual = **230.7×**; band split **none** | — | ☠ **HARD FAULT** (from `0xC407E`=850) |
| **V75** | ✅ | damper ↑ | 1.58 | best symptom result to date: grind **0.349 [0.192,0.784]**; S2: 5/6 down, **none clears its null** | *"got rid of the audible grind #1 and strongly attenuated the micro-ratcheting… **then a hard fault**, lost power steering"* | ☠ **HARD FAULT** |
| V76 | ✅ | V38 rebase (⚠ silently reverted 4 fixes) | 1.39 | S1 slope −0.614; **S2 slope flat** | *"There is still grind #1 and micro-ratcheting at creep"* | ❌ |
| V77–V79 | ❌ built | dose ladder | — | V79 rails 38.9% | — | ❌ |
| **V80** | ✅ | **damper flattened → RELAY** | **4.16** | 🛑 **WORST GRINDING EVER, NO FAULT** ⇒ stability failure. `N(50)/N(500)` = **3.27**; 27.34 Hz limit cycle ~30 s. **S2 0.418 [0.33,0.61] — the ONLY dose that clears its null** | *"loud, strong, felt through the whole car, ~90% of LKAS-engaged time, **noticeable vehicle instability**"* | ❌ |
| **V81** | ✅ | **interlock reverted to Honda** | 1.58 | **FAULT-FREE — the clamp revert worked.** Ring 11.25 s @ 27.75 Hz, actively sustained | *"all grinding stopped the instant LKAS disengaged; highway was worst; **manual steering much heavier when engaged, even turning WITH the command**"* | `0xC407E`=511 ✅ **PRESENT** |
| **V83a** | ✅ | partial damper revert (⚠ **m27 left armed**) | "0.23" ⚠ **refuted, §0/C3** | 🛑🛑 **WORST IN THE MODERN LINEAGE ON BOTH SCORED SYMPTOMS.** S1 **2.674 [1.956,3.885]** · S2 **1.526 [1.174,2.019]** | **"Feels just like V38, like we have made no progress since then."** | `0xC63A0`=1024 ✅ |

## A.6 V84 → V86B — THE CURRENT ERA

| build | flew | **CLASS** | cells · direction | measured | **operator** | today |
|---|---|---|---|---|---|---|
| **V84** | ✅ `6d` | **damper DELETED in both engaged columns** + Lever B re-armed | FactorC/E m26 **and** m27 → Honda; `0x3AA96`=`FB`, `0xC6446`=5244 | fault-free. **Ring burst duty 96.6%(V80) → 25.1%(V81) → 2.54%**, longest ring 18.29 → 11.25 → **1.34 s** on 3.4× exposure | *"grind #1 barely got better, might just be placebo… 2 instances of grind #2… **Both microratcheting and ratcheting were very obviously present**"* | ✅ on V86; ⚠ **PARTIALLY REVERSED on V86B** |
| **V85** | ✅ `6e` | **Coulomb relay → viscous** (nonlinearity linearised) | **`0xC40BC` 600→6000** (1 cell, 2 bytes) | ✅ **DELIVERED**: relay saturation 33.3%→4.6% engaged (**7.21×**), both pre-registered duties hit. 🛑 **ALL BANDS A CLEAN NULL** vs V84 | *"grind #1 still barely perceptible, got a little bit better"* · *"micro-ratcheting barely, perceptibly better (somewhat unsure)"* · **"Ratcheting was still unfixed"** · no grind #2 | ✅ **6000, FROZEN — spent** |
| **V86** | ✅ **route `6f`** | 🛑 **PHASE / LAG — a new class.** Moves the loop's −180° crossing, changes no gain | **`0xC40D4` 573→286** (command EMA α 0.1399→0.0698) | pre-registered as a **FREQUENCY RATIO** `f(V86)/f(V85) ∈ [0.797, 0.875]`. 🛑 **UNSCORED — and the route CANNOT score the highway (0.0 s ≥50 km/h)** | not yet recorded | flown |
| **V86B** | ✅ **route `70`** | **damper creep RE-ARM** — same class as V74–V81, opposite direction to V84 | `0xD77DA` m26 `Y[0]` 0→**908** · `0xD77EE` m27 `Y[0]` 0→**875** | 🛑 **UNSCORED — same zero highway exposure** | not yet recorded | flown |

🛑🛑 **RECORD DEFECT, FOURTH CONSECUTIVE INSTANCE — `STATE.md` still reads *"✅ BUILT, VERIFIED, UNFLASHED —
V86 ← THE CURRENT CANDIDATE"* and the same for V86B. Both have flown.** [EVIDENCE: build identity is
`EXTRACT`'s, parameter-free from the exclusive `0x14A` byte-4 alphabets, with the cave payloads verified
against the built images.] This is the defect the kit's own method rule names — *a flown build recorded as
unflashed WILL be re-proposed* — after V83a, V84 and nearly V85. **The first draft of this arc map inherited
it and recorded both as unflashed; corrected here.**

⇒ **Consequences for this document, stated where they land:**
- **V86 is not a candidate for V87 to build on — it is a flown, unscored predecessor.** Same for V86B.
- **The damper partial-revert on V86B was ON THE CAR** for route `70`, not a candidate property.
- 🛑 **Neither route carries ANY highway exposure (0.0 s engaged ≥50 km/h on both).** ⇒ the highway grind —
  the symptom Lever B is falsified against (F13) and the one §E rank 9 targets — **is still completely
  untested by every build since V84**, and two more flights have gone by without touching it.

## A.7 THE CLASS ARC, CORRECTED

The brief's stated arc is **correct** with three amendments read from the images:

| era | builds | class | amendment |
|---|---|---|---|
| the cause | V38 | authority ×2.13 → 4.27× total | — |
| guards/poles/filters/caves | V39–V52c | rate guards, slew caps, EMA poles, notch, broad low-pass | 2 bricks (V40, V48B). ⚠ **V48A also wrote inside the "virgin" plant block** (`0xC4120`) |
| telemetry + mutes | V53–V61 | measure, then mute | V61 (0× rate lane) is the signed result that made the rate lane the damper |
| **the rate lane** | V62–V73 | `sar` ×2, then the gated r24 arm | ⚠ **V73 is not a rate-lane build** — it is the `0xC407E` clamp raise, i.e. the *interlock* class, and it is the hard-fault mechanism |
| the base-assist damper | V74–V83a | arm and dose an engaged-only Coulomb damper | ⚠ **V81 is the interlock revert**, not a damper build |
| damper → Honda | V84 | delete the damper in m26 **and** m27 | — |
| relay → viscous | V85 | `0xC40BC` — remove a **nonlinearity** | ✅ as stated |
| **phase / lag** | V86 | `0xC40D4` — move a **pole** | ✅ **genuinely a new class since V38** |
| damper creep re-arm | V86B | FactorC m26/m27 `Y[0]` | 🛑 **NOT a new class — V74–V81's lever, at a new operating point** |

---

# B. THE FROZEN-CELL CENSUS — THE NOVELTY PROOF

`N` = consecutive build images back from **V86** holding V86's value (STOCK excluded). **N = 56 means
"never written by any build image ever made."**

## B.1 THE CELLS THAT HAVE ACTUALLY MOVED (N < 56)

| addr | what | V86 | stock | **N** | who ever moved it |
|---|---|---|---|---|---|
| `0x3AA96` | Lever B gate repoint | `FB` | `C5` | **3** | V67,V68,V71c,V76g,V84,V85,V86,V86B |
| `0xC6446` | Lever B r24 arm | 5244 | 512 | **3** | same set |
| `0xC63A0` | Path-2 damper weight | 1024 | 1024 | **4** | V72–V75,V76g,V81 → 2048 |
| `gain_A` rec0/rec1 (8 cells) | r26 low-speed gain | STOCK | — | **4** | V42(→0), V71b(×2), V72–V75/V76g–V77b/V81(→512) |
| `0xC646C` / `0xC6CD0` / `0x2A1F0` | the V57 decouple triple | 891/3564/`7CD0` | 891/–/`746C` | **5** | V38–V56, V76, V78–V80 used the shared cell |
| `0xC62EA` | steer-to-zero | 0 | 320 | **5** | on since V53; lost twice (V76, V78–V80) |
| `0x454FE` | V42 ratchet byte | `B5` | `BA` | **6** | lost 3× (V49p, V50probe–V51probe, V53–V70, V76, V78–V79) |
| `0xC407E` | **hard-fault interlock** | 511 | 511 | **8** | V73,V74,V75,V76g,V77,V77b → 850 ☠ |
| `0xC40BC` | V85 Coulomb linearisation | 6000 | 600 | **2** | **V85, V86, V86B only** |
| `0x3AB76` / `0x3AC20` | **LEVER A `sar`** | `AA` | `AA` | **18** | **V62, V65, V71a ONLY** |
| `0xC6444` | r26 engaged arm | 512 | 512 | **16** | V42(→0), V71c(→3072) |
| `0xC643E` / `0xC6440` | detector arms | STOCK | — | **25** | V63, V64 (detector never armed) |
| `0x3AB6C` / `0x3AC16` | rate taps | STOCK | — | **28** | **V61 only** |
| `0xD2006` | boost blend | 102 | 102 | **29** | **V60 only** |
| `0xC6AFC` / `0xC6AFE` | V56 mute | −32768 | — | **33** | **V56 only** |
| `0xC644A` | derivative pole | 1024 | 1024 | **43** | V43(→32), V49(→64) |
| `0xC6450` | Stage-A EMA pole | 1024 | 1024 | **47** | **V46 only** |
| `0xC6206` / `0xC6208` | governor slew | 512/205 | — | **48/53** | V40(→0xFFFF ☠), V45(→205) |
| `gain_A` rec2/rec3 (8 cells) | **r26 ≥50 km/h** | STOCK | — | **51** | **V42 only, ever** |
| `0xC61B2`/`B4`, corridor ×4, boost floor ×3, `0xE41BC`, V36/V37 gates | **the V38 authority package + the gentle-EME defeat** | non-stock | — | **56** | **V38 — and never touched again by anything** |

## B.2 🛑 VIRGIN — NEVER WRITTEN BY ANY BUILD IMAGE (N = 56)

All verified by direct LE reads of all 57 build images. ✅ = confirmed virgin this session.

| addr | stock | what it is | status of the direction |
|---|---|---|---|
| ✅ `0xC6C42` | 4 | **differentiator delay D — THE PHASE LEVER**, named in V62's own handoff as the follow-up | **NEVER BUILT** |
| ✅ `0xC63AC` | 102 | Path-2 accumulator one-pole IIR ⇒ **fc ≈ 16.7 Hz, inside the grinding band** | **NEVER BUILT**, either direction |
| ✅ `0xC64C8` / `0xC64C9` | 0 / 0 | **aggregator MODE SELECTOR** (1 = discard the whole aggregator, 2 = blend); 0 writers, 1 reader | untraced, dangerous |
| ✅ `0xC64AD`–`0xC64B3` | `01`×7 | **seven per-term ENABLE BYTES on the assist aggregator** (`0xC64B0` gates `gp-0x6b70`) | **NEVER BUILT** — the only subtractive census available |
| ✅ `0xC40D0` / `0xC40D2` | 408 / 102 | **the friction lane's ONLY pole** + its scale | **NEVER BUILT** — a second phase lever |
| ✅ `0xC40D6` / `0xC40D8` | 246 / 3686 | inertia-EMA α · torque-EMA α (siblings of V86's `0xC40D4`) | **NEVER BUILT** |
| ✅ `0xC4048`/`4C`/`50` | 0/0/0 | plant-model **FIR taps** — currently a pass-through | **NEVER BUILT** |
| ✅ `0xC613A` | 1159 | FIR path scale | **NEVER BUILT** |
| ✅ `0xC6200` | 8192 | clamp on `gp-0x6b70`; **15 readers, 3 unidentified** | RULE-11 census incomplete |
| ✅ `0xC63AE` | 1024 | `gp-0x6b70` LERP index scale | ⛔ **never → 0** (relay hazard) |
| ✅ `0xC6468` / `0xC646E` | 2639 / 1428 | output scale on `gp-0x6bfc` · INERTIA gain | **NEVER BUILT** |
| ✅ `0xC4080` | 0 | friction constant | ⛔ **NEVER RAISE** — latent pure Coulomb relay |
| ✅ `0xC6B66`–`0xC6B99` | 13-pt LERP | angle LERP in `FUN_0003b8f6` | 🛑 **KILLED** — 88.6% in the flat first segment |
| ✅ `0xC6ABA`–`0xC6ADB` | flat 1024 | aggregator speed LERP | **NEVER BUILT** (flat unity ⇒ shaping available) |
| ✅ `0xC618A` / `0xC627E` / `0xC63C0` | 1024/20/33 | **`FUN_00036388` relay-with-dwell** (snaps to 1024 past 20 ticks) | **NEVER BUILT**; disfavoured by the no-comb evidence |
| ✅ `0xC61B8` | 102 | pre-gain deadband — **never rescaled while its clamp siblings went ×4** | **NEVER BUILT** |
| ✅ `0xC61F6` | 3 | rate-lane deadband | 🛑 `→0` **KILLED**; `→raise` never considered |
| ✅ `0xC6442` | 1024 | `gp-0x671d` arm — **outranks the repointed gate** | **NEVER BUILT** |
| ✅ `0xC6194` / `0xC63CC` | 3 / 0 | LKAS rate limiter + its gain | **DEAD CAL** (gain = 0) |
| `0xC63AA` | 1024 | `w_LKAS`, 1 reader 0 writers | chain terminates at a V56-zeroed cell ⇒ null |
| `0xC407C`, `0xC64FA`, `0xC61DA`, `0xC6316`, `0xC6158` | — | interlock neighbour, CEIL byte, Q10 scale, governor speed cal, ceiling fallback | **NEVER BUILT** |
| **FactorB** all modes | flat 1024 | — | **NEVER BUILT, ANY MODE** |
| **FactorD** all modes | flat 1024 | — | 🛑 **STRUCTURALLY INERT** (FactorC `Y[0]`=0 multiplies it out) |
| **ceiling table** `0xC77A0` all modes | X[300,800] Y[512,1024] | **the clamp V80's relay pinned against** | **NEVER BUILT, ANY MODE** |
| **`gain_B` m24/25/26/27** | — | **16 of 16 records never written, any build, any array** | ★ this is what V69/V70 *meant* to do |
| friction m12/m24/m25 | — | — | **NEVER BUILT** |

## B.3 THE PLANT-MODEL BLOCK `[0xC4000, 0xC4200)` — THE DIRECT ANSWER

🛑 **STATE.md's claim is FALSE as written.** [EVIDENCE — every halfword of the block, every image]

```
256 halfwords in [0xC4000, 0xC4200)
  EVER written:  4        →  252 / 256 = 98.4 % virgin
    0xC407E   511 → 850   V73, V74, V75, V76g, V77, V77b   ☠ TWO HARD FAULTS
    0xC4120   257 → 256   V48A  (byte 01→00, type-8 slot mute)   S1 null
    0xC40BC   600 → 6000  V85, V86, V86B                    delivered, bands null, FROZEN
    0xC40D4   573 → 286   V86 ONLY                          unflashed
```
⇒ **The block is a near-virgin frontier, but it is not untouched, and one of its cells is the kit's only
recorded hard-fault mechanism.** Any V87 proposal inside it must say so.

---

# C. THE KILL LIST — FOUR VERDICTS, NOT ONE

🛑 **FALSIFIED ≠ INERT-BY-MODE ≠ STRUCTURALLY IMPOSSIBLE ≠ SAFETY-BLOCKED.**

## C.1 FALSIFIED — flown, delivered in force, measured, did not work

| lever | addr | build(s) | why dead |
|---|---|---|---|
| conditional r24 kill (cave) | hook `0x3AC78` | V39 | S1/S3 null — **and the direction was backwards** (V61) |
| motor-rate cap flattened | `0xC5218`/`0xC5230` | V41 | S1/S3 null, clean subtractive test |
| dirty-derivative pole | `0xC644A` →32 | V43 | S1 null |
| governor slew step ↓ | `0xC6206` →205 | V45 | S1 null |
| Stage-A EMA pole | `0xC6450` →32 | V46 | *"no noticeable change"* |
| type-8 slot mute | `0xC4120`+`0xC67B8/BA/BC` | V48A | S1 null ⇒ anti-damping is **distributed** |
| broad 12 Hz EMA, 19 carriers | — | V52C | S1 null. ★ closed as a **STRATEGY**: lag scales with attenuation |
| `gp-0x6ad4` lane mute | `0xC6AFC`/`FE` | V56 | 786× vs 877× ⇒ **whole lane ELIMINATED**, and it cost damping |
| LKAS-gain decouple | `0x2A1F0`,`0xC6CD0`,`0xC646C` | V57 | null — falsifies the **feedback** readers only |
| boost-amplitude blend | `0xD2006` | V60 | null (pre-registered) ⇒ **parametric-pump arc CLOSED** |
| **both rate taps → 0×** | `0x3AB6C`,`0x3AC16` | V61 | **WORSE** — `e_18-22` 2501 ⇒ the rate lane is the **damper** |
| **Lever B for the HIGHWAY grind** | `0x3AA96`+`0xC6446` | V67, V68 | 0.970 / 0.938 vs null [0.73,1.37], two independent statistics |
| rate-lane dose vs the ~28 Hz transient | — | V68, V69 | dose-independent ⇒ **excitation, not gain** |
| `0xC407E` **RAISED** | `0xC407E` →850 | V73/V74/V75 | no band change **+ it is the hard-fault mechanism** |
| friction ×1.5, engaged | `0xCBE74` m26/27 | V74, V75 | no benefit; implicated in both faults |
| **the engaged damper as an S1 lever** | FactorC/E m26/27 | V74…V83a | ladder all inside null. ⚠ **survives via V84, not V83a — see §0/C3** |
| **`0xC40BC` linearisation** | `0xC40BC` | **V85** | **DELIVERED 7.21× and every band is a null** ⇒ spent. **FREEZE at 6000** |
| more authority / 8× / governor slew | — | analysis + 3 measured lines | ach/dem 1.88 >86 km/h ⇒ **CLOSED** |

## C.2 INERT-BY-MODE — the edit landed in a table this car does not read ⇒ **UNTESTED, NOT FALSIFIED**

| build | intended | delivered | correct status |
|---|---|---|---|
| V44 | raise the damper floor at low speed | mode 10/11 ⇒ **byte-stock** | **UNTESTED** — and its stated mechanism never existed |
| V47 | damper shape | mode 10/11 ⇒ **byte-stock** | 🛑 *"FALSIFIED — do not resurrect"* is **FALSE** |
| V69/V70 | r24 ×4 / ×2 speed-shaped | mode-10 `gain_B` ⇒ **byte-stock** | ⇒ **the r24 dose ladder NEVER EXISTED** |
| V72 Levers B/C | FactorC/E damper shaping | modes 10/11 | **UNTESTED** |
| V73 Levers D/E | friction ×1.5; FactorC/E `Y[0]:=Y[1]` | m10 / m0–5,12,14 | **UNTESTED**; Lever E's shape never delivered |

## C.3 STRUCTURALLY IMPOSSIBLE / ELIMINATED — no direction is testable

| lever | why it cannot act |
|---|---|
| **`0x454FE`** (V42's ratchet byte) | `gp-0x67fa`'s reachable set is effectively **{11} alone**: state 4 = **0/123,277**, state 10 = 0.0000%, state 5 structurally dead. **Keep the byte, but no build may be justified on it** |
| **`gain_A` rec0/rec1 LOWERED, engaged arm** | with the gate at `FB`, `0x3AB5E` **OVERWRITES** `gain_A` with `[0xC6444]`=512 ⇒ **V84/V85/V86 already deliver 512 engaged at every speed.** Pre-registered twice; FAIL both |
| **FactorD m26/m27** | FactorC multiplies in **before** it with `X[0]`=2240 ct = 34.97 km/h, `Y[0]`=0 in all four of this car's modes. **Zero × anything = 0.** Three independent confirmations |
| **`0xC63A0` → 2048** | `ch₀` is exactly **ZERO on 98.8% of engaged frames** (route `6e`, p50 and p90 both 0.00 against ±25600) ⇒ **V84's own revert of it was INERT** |
| **13-pt LERP `0xC6B66`/`0xC6B80`** | axis is **absolute steering angle** (99.94%), **88.6% of engaged driving in its flat first segment** ⇒ a 0.878× broadband trim |
| **`0xC6194`** | its gain `0xC63CC` = 0 multiplies it out. DEAD CAL |
| **all 8 aggregator zero-type range gates** | each capped by its own producer's ceiling inside its gate window, every build |
| **`0xC6444` alone with the gate at `C5`** | read only at `0x3AB5E`, only when `lp != 0` ⇒ null by construction |
| **V63/V64 detector arms** | the detector never armed: 0/14,980; `gp-0x67fa==10` = 0.0000% |
| **a new CAN mailbox ID** | the gateway is a **WHITELIST** — only `0x14A`/`0x18F`/`0x1AB` cross |
| **`FUN_00038148`/`gp-0x6b70` as the ~8 Hz generator** | no odd/even comb (0.858 vs a positive control at 1.204 with 15% injection); no 3:1 PLV; no 3rd harmonic |

## C.4 SAFETY- OR CONSTRAINT-BLOCKED — might work; forbidden

| lever | blocked by |
|---|---|
| **`0xC407E` RAISED** | 🛑 Honda ships the clamp **one count under its own 512 trip**; V74 and V75 both **latched total loss of assist** |
| `0xC4080` raised · `0xC63AE` → 0 · `0xC6200` < `Y[0]` | each converts a shaped nonlinearity into a **full-authority relay** — the V72/V80 error |
| lowering `0xC6CD0` / `0xC61B2` / `0xC61B4` / the setpoint records | ⛔ reduces peak EPS torque from a rail-pinned command **in exact proportion** ⇒ collides head-on with *"without limiting the max steering angle rate"*. **Diagnostic arm only** |
| raising friction · raising the damper · lowering `0xC40BC` | ⛔ all **add impedance** ⇒ same constraint |
| any **code cave** | V24, V27, V48B all bricked. GATE 1 + GATE 2 mandatory |
| a **cancellation biquad** in any form | poles at r≈0.99878 while `f₀` moves −14% with load ⇒ delivered **fully INVERTED** |
| **`0xC61D6`** (shaper slew step) | an 11-round review: *"highest-risk; last/never"* — it activates a dormant uncalibrated 2D map |
| **Lever A restore** (`0x3AB76`/`0x3AC20`) | ⚠ **see C.5 — this kill is a JUDGEMENT, not a measurement** |
| **`0xC61F6` → 0** | ⚠ **see C.5 — analytical, not measured** |

## C.5 🛑 KILLS THAT DO **NOT** MEET THE BAR — flag these before re-using them

**(a) Retracted or voided already:**

| "kill" | why it was not a kill | correct status |
|---|---|---|
| V83a's damper-ring falsifier | **mode 27 carried V81's ENTIRE damper** and route 68 gave only **19.2 s** >80 km/h ⇒ the lever was never removed and could not have been tested | **RETRACTED** — the damper-ring model is **SUPPORTED** by V84's 4-point dose-response |
| V42's *"`0x454FE` is the CONFIRMED root cause"* | state 4 never runs while driving; V42 moved six groups at once | **VOID as an attribution** (byte separately ELIMINATED) |
| V47 *"FALSIFIED, do not resurrect"* · V44 *"falsified"* · V72 *"the damper was tested"* · V73 Lever D | all mode-10/11 ⇒ byte-stock | **UNTESTED** ×4 |
| *"r24 is near-inert across a 4:1 dose range"* | three replications of **one byte-stock condition** | **VOID** — r24 is the actor |
| V85's damper abort criterion | 22.4 s engaged ≥80 km/h — **could not have fired** | **"that is not a pass"** |
| V84's `b7`/`b6` falsifier | tested `\|r24\| ≥ 1024` on a lane whose input never exceeded `\|r1\| = 201` | **could not have fired**, in either arm |
| V69's three probe rungs | `b4` **structurally vacuous** (≥4096 vs a ceiling of 164–341) | all three void |

**(b) 🛑 STANDING ON A BELIEF, NOT A MEASUREMENT — the two the V87 session should know about:**

| lever | the kill as written | what it actually rests on |
|---|---|---|
| **LEVER A** — the kit's **first and best-replicated measured grinding fix** (0.39 [0.32,0.48], replicated V62 **and** V65) | *"DO NOT RESTORE"* | **Leg (a):** the `sar` is **UNGATED**, so it reproduces V62/V65 in the **manual** arm — `[EVIDENCE]` for the byte identity, **`[BELIEF]` for the outcome transfer**. **Leg (b):** *"r24 ≥ ~2 is necessary for grind #2"* — `[BELIEF, whole-corpus]`, 6 builds. **Leg (c) — the int16 overflow ceiling — is WITHDRAWN.** ⇒ **a measured fix is currently blocked by two beliefs.** It has been off the car for **18 build images** |
| **`0xC61F6` → 0** | *"DO NOT — it pushes the destabilising way"* | a **describing-function argument** (deadband is the dual of a relay). No measurement. The raise direction was never even considered |

---

# D. THE SILENT-LOSS AUDIT — WHAT IS NOT ON V86 / V86B RIGHT NOW

Read from the two candidate images. [EVIDENCE]

| historically confirmed fix | cells | **V86** | **V86B** |
|---|---|---|---|
| V37 gentle-EME + DTC-0x49 defeat | `0xC61C0`/`C2`/`C4`, `0xC64B4`/`B6`/`B8` | ✅ PRESENT | ✅ PRESENT |
| V53 steer-to-zero | `0xC62EA`=0 | ✅ | ✅ |
| V57 LKAS decouple | `0x2A1F0`,`0xC6CD0`,`0xC646C` | ✅ | ✅ |
| **LEVER A — V62's `sar` ×2, the kit's first measured fix** | `0x3AB76`, `0x3AC20` | 🛑🛑 **ABSENT, BYTE-STOCK, FROZEN 18 IMAGES** | 🛑🛑 **ABSENT (19)** |
| LEVER B — gated r24 arm | `0x3AA96`=`FB`, `0xC6446`=5244 | ✅ | ✅ |
| V81 hard-fault interlock revert | `0xC407E`=511 | ✅ | ✅ |
| V83a Path-2 damper weight | `0xC63A0`=1024 | ✅ (inert) | ✅ (inert) |
| **V84 damper deletion, both engaged columns** | FactorC/E m26+m27 | ✅ **PRESENT** — all six families byte-stock | 🛑 **PARTIALLY REVERSED BY DESIGN** — FactorC m26 `Y[0]` 0→**908**, m27 `Y[0]` 0→**875** |
| V42 macro-ratchet byte | `0x454FE`=`B5` | ⚠ present but **MEASURED INERT** | ⚠ same |
| *(not a fix — the suspected cause)* V38 authority package | 12 cells | 🛑 all present, **FROZEN 56 IMAGES** | 🛑 same (57) |

## 🛑 THE THREE THINGS THIS SECTION SAYS TO V87

1. **LEVER A IS THE ONLY HISTORICALLY CONFIRMED FIX MISSING FROM BOTH**, and it has been off
   the car for **18 build images** (last carried by V71a, which never flew; last *flown* on **V65**).
   **Lever A and Lever B have never flown together on any build, ever.** Its block is C.5(b).
   ⊕ **Updated:** V86 and V86B have now both FLOWN without it ⇒ that is **two more flights** added to the
   run, and the count is now in flown builds, not just images.
2. **V86 and V86B are NOT the same base for silent-loss purposes.** V86B re-arms part of what V84
   deleted, and V84's damper deletion is the strongest causal chain the kit owns (4-point monotone
   dose–response on the 26–31 Hz ring). Any V87 built on "the current build" must name **which**.
   ⊕ **Updated:** this is no longer a candidate property — **V86B's partial damper re-arm was ON THE CAR**
   for route `70`. Whether it cost anything is unscored, and **route `70` has zero highway exposure, so the
   ring band it would most affect cannot be scored on it at all.**
3. **`gain_A` rec0/rec1 has been at stock for 4 images** — but it is no longer a silent loss: it is
   **structurally inert in the engaged arm** (C.3). Do not resurrect it as a loss.

---

# E. WHAT IS GENUINELY VIRGIN — the V87 novelty surface, ranked by novelty (not by merit)

Everything below is `N = 56` (never written by any build image). Merit, blast radius and GATE-2 arguments
are **not** assessed here — this is the novelty proof only.

| # | surface | why it is novel *as a class*, not just as a cell |
|---|---|---|
| **1** | **`0xC64AD`–`0xC64B3` — seven per-term aggregator ENABLE bytes** | **SUBTRACTIVE CENSUS.** Every build in the arc has been *additive* or *scalar*: change a gain, a clamp, a pole, a table. **No build has ever removed a term from the assist sum and asked which symptom moves.** Highest information per build in the document. 🛑 Each byte deletes a term feeding the motor — same danger class as `0xC64C8` |
| **2** | **`0xC40D0` (friction-lane pole) · `0xC40D6` / `0xC40D8` (inertia / torque EMA α)** | **PHASE, and the siblings of V86's own lever.** V86 opened the phase class with `0xC40D4`; these are the other three poles on the same estimator, none ever moved. ⚠ Moving one *with* `0xC40D4` destroys V86's interpretability |
| **3** | **`0xC6C42` = 4, the differentiator delay D** | The kit's **only pure delay lever**. Named in V62's own handoff as the follow-up *"if V62 comes back null"* and **never built in 56 images** |
| **4** | **`0xC63AC` = 102, Path-2 accumulator pole (fc ≈ 16.7 Hz)** | A first-order pole sitting **inside the grinding band**, never moved either way. Sets magnitude **and** phase |
| **5** | **`gain_B` m26/m27 — 16 of 16 records, never written, any array** | ★ **exactly what V69 and V70 were designed to do, and they wrote mode 10.** Gives the r24 lane a native **speed axis**, which a flat arm cannot have (Lever B is 1 DOF against 2 constraints). Engaged-only by construction |
| **6** | **`0xC4048`/`4C`/`50` FIR taps (currently a pass-through) + `0xC613A`** | The estimator has a **dormant 3-tap FIR** that no build has ever enabled. A genuinely different filter topology from every EMA the kit has tried |
| **7** | **`0xC6ABA`–`0xC6ADB` — the aggregator's speed LERP, flat unity ×8** | A **speed-schedule on the whole aggregator output**, never shaped. Orthogonal to every per-term lever |
| **8** | **ceiling table `0xC77A0` — the clamp V80's relay pinned against** | Never written, any mode. Lowering it is the one *shape-preserving* way to bound the damper |
| **9** | **`gain_A` rec2/rec3 (`0xC6A9A`–`A0`, `0xC6AAE`–`B4`)** | Frozen **51 images**; touched by **V42 only**. The **only untouched cells that reach the HIGHWAY regime on r26** — and the highway grind is exactly what Lever B does not fix |
| **10** | **`0xC6442` = 1024** | The arm that **outranks the repointed gate** — the one cell on the rate lane nobody has ever written |
| **11** | **`0xC64C8` = 0 — aggregator MODE SELECTOR** | A **one-byte ON/OFF for the entire compensation stack**. Diagnostic, not a fix. 🛑 Writer census never run; V40's brick came from deleting a lane's governor |
| **12** | **`0xC61B8` = 102, pre-gain deadband** | Never rescaled while its clamp siblings went ×4 ⇒ it now covers ~4× more of the LKAS range than Honda validated. An **engage-ramp correctness fix**, not a grinding lever |
| **13** | **FactorB, `0xC9CCC`, all modes** — flat unity `[1024]×4` | ⊕ **CROSS-CHECK, two independent methods agreeing.** My census (LE read of all 57 build images) and `FACTORS`' census (grep of all 83 build scripts + a 3-image byte dump) both return **never written, any mode, any build**. **The axis identification is `FACTORS`' finding, not mine** — take it from them. What my half adds: it is virgin on **every image that has ever existed**, so the "flat unity" starting condition is a fact about the whole arc, not just the current candidates. ⚠ Being flat means the V72/V80 *flatten-a-curve* hazard cannot apply as a starting condition — but the **inverse** hazard does: any first edit necessarily introduces new shape, and a 2-point step recreates the relay pattern |

**The two things that are NOT novel and will read as novel if not stated:**
- **`0x3AB76`/`0x3AC20` → `A8` (4×)** — the *cell* is famous but the *value* was never built. It is still
  **the same lever pushed further**, and it inherits both of Lever A's blocks (C.5b).
- **V86B's FactorC `Y[0]`** — the V74–V81 damper lever at a new operating point, **not a new class**.

---

# F. THE ONE-LINE SUMMARY FOR V87

Since V38 the kit has moved **gains, clamps, arms, poles, tables, mode records and one nonlinearity**, in
**both directions on almost everything that matters** — and the two symptom classes the operator still
reports (grinding, ratcheting) have never both responded to the same build. **What has never been tried at
all is: (i) removing a term from the assist sum, (ii) any pole on the estimator other than V86's, (iii)
the delay `0xC6C42`, (iv) a speed axis on the r24 lane in the engaged column, and (v) the dormant FIR.**
And **one measured fix — Lever A — is off the car and blocked by two beliefs rather than a measurement.**
