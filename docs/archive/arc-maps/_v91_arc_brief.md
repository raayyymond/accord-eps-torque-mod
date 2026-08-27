# V91 ARC BRIEF — the record, read from the images — 2026-08-10

**Scope:** D1 arc V84→V90 · D2 candidate ledger + the threshold re-openability audit · D3 cross-build
cell matrix from the IMAGES · D4 the complete non-stock delta of V90 vs STOCK.
**Method:** all byte work is Python, little-endian, on `../accord-firmwares/analysis-2020accord/*.bin`.
**No Ghidra was used** (two other agents own the disassembler this session). Where a structural claim
comes from the kit's own trace docs rather than my own decompile, it is marked **[RECORD]**, not EVIDENCE.

**Stock reference chosen:** `stock_fw_dump/code.bin`. Why: it is the only 1 MiB image in the tree that
is non-`0xFF` below `0x13000`, and it passes the kit's own three anchors — `len == 0x100000`,
`s16(0xC646C) == 891`, `u8(0x454FE) == 0xBA`. Every `_v*_plain_image.bin` is a 0xFF canvas with the flash
region `[0x13000, 0x100000)` laid in (verified: `set(v90[0:0x13000]) == {0xFF}`), so **every diff below is
restricted to `[0x13000, 0x100000)`.** Diffing whole-file returns 2,041 runs / 50,499 bytes of pure
canvas artefact and is meaningless.

---

## D1 — THE ARC, V84 → V90, IN CLASSES OF INTERVENTION

`docs/review/ARC-AUDIT-2026-08-10.md` §2 already builds this for V38→V89 and is correct where I can check it
from the images. This table **corrects and extends** it. Cells are read from the images; on-car results
are the operator's own words where recorded.

| build | base | CLASS | exact cells moved (image-verified) | operator's words | instrument's verdict |
|---|---|---|---|---|---|
| **V84** | V83a | **rate lane restored + damper reverted to Honda** | `0x3AA96` C5→FB · `0xC6446` 512→5244 · FactorC `Y[0]` 566→0 at `0xD77DA` (m26) and `0xD77EE` (m27) · FactorE m27 `0xD7822/24/2C`→60/400/140 · probe rungs | 🛑 *"None of these have been fully fixed in V84."* | ONE band moved: 26–31 Hz burst duty 25.1%→2.54% on 3.4–4.9× the exposure. S2/S3/S4 pre-registered tests **FAIL**. Retracts V83a's "damper-dose model FALSIFIED" |
| **V85** | V84 | **plant-model nonlinearity (new class)** | **ONE cell**: `0xC40BC` 600→**6000** + 4-rung probe | grinding *"a little better"* · micro-ratcheting *"barely, perceptibly better (somewhat unsure)"* · **ratcheting STILL UNFIXED** | Lever delivered (relay saturation 33.3%→4.6% engaged, 7.21×) but **bands clean-null**: 6–9 Hz 1.088 [0.746,1.451], 18–22 Hz 1.347 [0.947,1.758]. Exposure-limited: 35.6 s ≥50 km/h |
| **V86** | V85 | **plant-model PHASE (new class)** | **ONE cell**: `0xC40D4` 573→**286** (α 0.1399→0.0698) + 5-rung probe | grinding/micro-ratcheting *"maybe a smidge better, if at all"*; **ratcheting definitely perceptible**; second grinding complaint present | 🛑 **pre-registration FALSIFIED, well-powered.** `f(V86)/f(V85)` = 1.001 [0.976,1.060], CI disjoint from the predicted [0.797,0.875]; line stayed at 8.00 Hz. Parking-lot only |
| **V86B** | V85 | **damper zero-point test** | `0xD77DA` FactorC m26 `Y[0]` 0→**908**, `0xD77EE` m27 `Y[0]` 0→**875**. `0xC40D4` stays 573 | *"still present, dampened I think"*, ratcheting definitely perceptible, **plus "extra dampening on LKAS and in general at slow speed"** | Predicted heavier-at-creep cost **CONFIRMED as felt**. Recovery test unscoreable — parking-lot only, 1.5 engaged min |
| **V87** | **V38 (deliberate rebase)** | 🛑 **SUBTRACTIVE — the only one in the arc** | strips 49 builds of levers back to V38, then re-adds: `0x2A1F0`/`0xC6CD0` (V57 decouple), `0x454FE`→B5, `0xC62EA`→0, `0x55DF2` 427-source repoint → `gp-0x6b98`, cave | grind #1, micro-ratcheting and ratcheting **all present** | **Predicted** — V87 is byte-stock at all four grind-#1 cells (`0x3AB76`,`0x3AC20`,`0x3AA96`,`0xC6446`). ★ The probe fired: 427 non-zero 99.02%, 946 distinct, first honest measurement of the delivered command |
| **V88** | V87 | **rate lane restored + probe sign fix** | `0x3AA96` C5→FB · `0xC6446` 512→5244 · cave source `gp-0x6b70`→`gp-0x6b98`, rung 64→256 (**5 bytes**) | ★★★★ **the audible GRINDING IS FIXED** · hints of grind #2 but could not elicit it · **micro-ratcheting and ratcheting now the main remaining issues** | Command 15–22 Hz **0.549 [0.407,0.844]**; 0.5–3 Hz **1.192 [0.780,1.812] = NULL** ⇒ HF halved at zero LF cost. Identity 0.9654 vs V87 control 0.4022 (chance 0.6028). First real highway: 119.6 s engaged ≥50 km/h |
| **V89** | V88 | **PLANT MODEL — first build ever to touch it** | **8 bytes**: `0xC40D2` 102→**204** (K1, modelled Coulomb friction ×2.000) + cave rung `gp-0x6ae2` | 🛑 *"fixed nothing, still only as good as V88."* | 🛑 **H2 FAIL.** Order-clean stratum contrast **0.947 [0.827,0.979]** against a same-build placebo band of **[0.900,1.111]** = 0.92σ, FLAT. Largest exposure in the corpus (695 s engaged ≥50 km/h). ⊕ The probe explains why: the term is `sign(rate)`-gated and `\|friction\| ≥ 0.0625` on **0.9%** of micro-ratcheting frames |
| **V90** | V89 | **PROBE-ONLY — zero calibration change** | **9 runs / 68 bytes vs V89**: cave 62→**74 bytes** (`0xC4B34`–`0xC4B7D`), `0x55DF2` 68→da (427 → `gp-0x6b26`), CRC `0xC4FFC`. **`0xC40D2` stays 204** | 🛑 **grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on highway-speed curves or lane changes** (parking lot + street + highway) | pending route `00000077--7411859c54` |

### What this arc actually is, stated in one line each
- **V84** — undo V83a's regression. **V85/V86** — two single-cell probes of the 1 kHz plant model
  (nonlinearity, then phase). **V86B** — one damper cell. **V87** — throw all of it away and measure.
  **V88** — put back the one lever that had ever worked, correctly instrumented. **V89** — the first
  lever inside the plant model. **V90** — measure the cell a dose would act on, before dosing it.
- 🛑 **V85 → V90 is six consecutive builds of ONE-CELL-OR-ZERO-CELL changes.** The arc has already
  narrowed to the smallest possible interventions. A V91 that is "another single cell on the observer
  path" is **the seventh in that series**, not a new class.

---

## D2 — THE CANDIDATE LEDGER, AND THE THRESHOLD RE-OPENABILITY AUDIT

Current values are **V90, read from `_v90_..._plain_image.bin`**. Stock from `code.bin`.

### D2a — the ledger

| lever | cell | stock | **V90** | moved by | on-car result | **BUCKET** |
|---|---|---|---|---|---|---|
| **Lever B — r24 engaged arm** | `0xC6446` | 512 | **5244** | V67/V68, V71c, V84–V86B, **V88–V90** | **the kit's only measured grinding fix**; command 15–22 Hz 0.549× | ✅ **FLOWN-AND-WORKED** |
| **Lever B — gate byte** | `0x3AA96` | C5 | **FB** | same | paired with above | ✅ **FLOWN-AND-WORKED** |
| **Lever A — `sar` ×2, both lanes** | `0x3AB76`/`0x3AC20` | AA | **AA** *(stock; frozen 21 builds since V71b)* | V62–V66 | V62 = first measured fix (18–22 Hz down 8–42×); **V65: *"makes the entire car vibrate, almost like I have a subwoofer… regardless of LKAS engagement"*** | 🛑 **STRUCTURALLY-DEAD** — the `sar` is UNGATED so it hits the MANUAL arm too. Not a dose problem |
| **r26 engaged arm** | `0xC6444` | 512 | **512** *(frozen 19 builds since V72)* | V71c → 3072 | 🛑 V71c **WORSE on every axis** — grind #1 higher, grind #2 returned, ratchet at corpus record | 🛑 **FLOWN-AND-FALSIFIED** (harmful) |
| **V42 macro-ratchet fix** | `0x454FE` | BA | **B5** *(since V80)* | V42, lost/restored 3× | "ratchet fixed" at V42; **MEASURED INERT since** — `gp-0x67fa`'s reachable set excludes the guarded state | 🛑 **STRUCTURALLY-DEAD** (kept because free) |
| **K1 modelled Coulomb friction** | `0xC40D2` | 102 | **204** | **V89 only** | flat (contrast 0.947, inside placebo) | 🛑 **FLOWN-AND-FALSIFIED — but see D2b row 1** |
| **Coulomb relay normaliser** | `0xC40BC` | 600 | **600** *(back to stock at V87, 4 builds)* | V85 → 6000 | bands clean-null AND full-corpus says 6000 was **WORSE** (6.58× vs 600's 2.89×, contrast +0.682 [+0.213,+1.166]) | 🛑 **FLOWN-AND-FALSIFIED IN BOTH DIRECTIONS.** Car is correctly at 600 |
| **command-branch EMA α** | `0xC40D4` | 573 | **573** *(back to stock at V86B, 5 builds)* | V86 → 286 | pre-registration falsified, well-powered; `\|H(0)\|=1` for every α | 🛑 **STRUCTURALLY-DEAD** (phase lever; the linear-loop hypothesis died with it) |
| **Path-2 damper weight** | `0xC63A0` | 1024 | **1024** *(9 builds since V83a)* | V72–V77, V81 → 2048 | inert: `ch₀ = (FactorC×FactorE)>>10` is exactly 0 on 98.8% of engaged frames | 🛑 **STRUCTURALLY-DEAD** — 2 × 0 = 0 |
| **base-assist damper** | FactorC/E m26/m27 | Honda | **Honda** *(m26 stock since V87; m27 since V84)* | V74–V80, V86B | **V80 = WORST GRINDING EVER** at the LARGEST dose | 🛑 **FLOWN-AND-FALSIFIED — but see D2b row 2** |
| **friction-comp Y row ×1.5** | `0xCBE74`[m] | Honda | **Honda** *(all 32 modes)* | V73 (m10 only), V74/V75/V76g/V77/V77b (**12 modes**) | 🛑 **2 hard faults, ZERO clean flights on a live column** | 🛑 **OPEN SUSPECT — blocked on SAFETY, not on a null** |
| **friction-comp clamp / DTC-0x1d interlock** | `0xC407E` | 511 | **511** *(13 builds since V78)* | V73–V77b → 850 | V74 + V75 hard-faulted | 🛑 **NEVER RAISE** (RULE 11). Honda ships it 1 count under the monitor's own trip |
| **`0xC4080` (K0)** | `0xC4080` | 0 | **0** *(untouched on all 87 images)* | never | — | 🛑 **NEVER-RAISE** — pure Coulomb relay, no `\|model\|` factor |
| **`0xC63AE` LERP index scale** | `0xC63AE` | 1024 | **1024** *(87/87)* | never | — | 🛑 **NEVER →0** — output ≡ ±Y[0] = full-authority relay |
| **`0xC6200`** | `0xC6200` | 8192 | **8192** *(87/87)* | never | — | 🛑 **NEVER < Y[0]**; 3 of 15 readers still unidentified |
| **V43 dirty-derivative pole** | `0xC644A` | 1024 | **1024** *(42 builds since V50)* | V43 → **32** *(image; `memory` says 64 — **image wins**)* | null | 🛑 **STRUCTURALLY-DEAD** — the lane was eliminated by V56; and lowering a pole adds LAG, the anti-damping direction |
| **V46 Stage-A EMA** | `0xC6450` | 1024 | **1024** *(46 builds since V47)* | V46 → 32 | null | 🛑 **STRUCTURALLY-DEAD**, same two reasons |
| **V56 lane mute** | `0xC6AFC`/`0xC6AFE` | −32768 | **−32768** *(31 builds since V57)* | V56 → 0 | *"mute bought nothing and it COST damping"* — **scored 15–26 Hz, NEVER 6–9 Hz** | 🛑 **FLOWN-AND-FALSIFIED for 15–26 Hz. See D2b row 3 — the opposite direction is NEVER-TRIED** |
| **r24 lane deadband** | `0xC61F6` | 3 | **3** *(frozen all 55 builds since V38)* | never | — | 🛑 **STRUCTURALLY-DEAD both ways**: lowering adds small-signal gain; raising clips LF first (LF `dtorque` is ~12× smaller). Worth 0.4% of full scale either way |
| **observer FIR taps** | `0xC404C`/`0xC4050` | 0.0f | **0.0f** *(87/87)* | never | — | 🛑 **NOT A LEVER** — multiplies the additive *sensor* term; no coefficient alters the command's transfer function |
| **`0xC61D6` shaper slew step** | `0xC61D6` | 0 | **0** *(87/87)* | never | — | 🛑 **STRUCTURALLY-DEAD** — struck twice; activates a dormant uncalibrated 2D map, not a slew ramp |
| **`FUN_00036388` relay-with-dwell** | `0xC618A`/`0xC627E`/`0xC63C0` | 1024/20/33 | **1024/20/33** *(87/87)* | never | — | **NEVER-TRIED**, disfavoured by the no-comb evidence |
| **aggregator mode selector / blend mux** | `0xC64C8`/`0xC64C9` | 0/0 | **0/0** *(87/87)* | never | — | 🛑 **STRUCTURALLY-DEAD** — mode 2 is a byte-exact no-op because `0xC61D4` = 0 |
| ★ **friction-lane weight at the observer summing node** | **`0xC63A6`** | **1024** | **1024** | 🛑 **NEVER MOVED — 87 of 87 images, stock included** | — | ★ **NEVER-TRIED. See D2c — this is the one genuinely virgin cell in the family, and it needs ONE Ghidra query before it can be classified** |
| **its five siblings** | `0xC63A0/A2/A4/A8/AA` | 1024 ea | 1024 ea | only `0xC63A0` ever moved | — | context: `0xC63A6` is the only weight in the six-lane sum that has never been touched by anything |

### D2b — 🛑 THE THRESHOLD RE-OPENABILITY AUDIT (the point of this task)

Handoff §2a: *"this kit's core method is dose ladders, and it reads small-dose nulls as falsification.
That inference is valid for a linear mechanism and INVALID [under friction-induced vibration]."*

**I audited every FALSIFIED label on a damping-class lever. The headline is negative, and it is
decision-relevant: the threshold argument re-opens ONE row, and that row is immediately re-blocked by a
sizing constraint that was derived independently of it.**

The argument only applies to a lever that **adds dissipation**. It does **not** re-open (a) gain levers,
(b) filters/poles — a filter adds *lag*, which *subtracts* effective damping, (c) mutes, (d) levers that
were inert, wrong-mode, or wrong-axis, or (e) levers that were flown at a **large** dose and made things
**worse** — a large-dose harm is not a small-dose null.

| FALSIFIED damping-class lever | dose actually flown | small-dose null? | verdict |
|---|---|---|---|
| **base-assist damper** (FactorC/E) | V74 `k`=1.3866 → V79 `k`=4.16, dose 206→412; **V80 is the largest** | 🛑 **NO — the largest dose was the WORST result** | ⚠ **RE-OPENED, NARROWLY, THEN RE-BLOCKED.** Re-opened because V80's harm is attributable to **SHAPE**, not magnitude: a flat FactorC delivered a **constant 495 counts across a 34× rate range**, i.e. a Coulomb relay 17 counts under the rail — that *subtracts* damping. A genuinely **ramped** (viscous) damper at high dose has never flown. **Re-blocked** because sizing kills it independently: `ch₀` is zero on **100% of the micro-ratcheting regime**, and 25% authority at 10 °/s requires `FactorE Y[0]` off zero = a step at zero rate = **exactly V80's move**. ⇒ **stays dead in practice** |
| **`0xC63A0` 1024→2048** | ×2 | n/a | 🛑 **STAYS DEAD.** 2 × 0 = 0. There is no signal to threshold |
| **`0xC644A` 1024→32**, **`0xC6450` 1024→32** | 32× | n/a | 🛑 **STAYS DEAD.** Filters, not dampers — they push the anti-damping way. Threshold argument does not apply |
| **`0xC40D4` α ×0.5** | ×0.5 | n/a | 🛑 **STAYS DEAD.** Phase lever; `\|H(0)\| = 1` for every α |
| **`0xC40BC` 600→6000** | ×10 | 🛑 NO | 🛑 **STAYS DEAD, and doubly** — the null was at ×10 *and* the full-corpus contrast says the high value was **worse** |
| **`0xC40D2` K1 ×2 (V89)** | ×2.000 | 🛑 **NO — it is an OUT-OF-REGIME null, a different failure** | 🛑 **STAYS DEAD as a dose question.** The term is `sign(rate)`-gated and non-negligible on **0.9%** of micro-ratcheting frames. Raising it further is structurally blocked: the ceiling `K1 ≈ 1024` binds where the term **saturates** (13% of frames) while the effect is wanted on the ramp (the other 87%); conflict **1.4–3.8×**. **One scalar cannot serve both** |
| **`0xC6444` 512→3072 (V71c)** | ×6 | 🛑 NO | 🛑 **STAYS DEAD** — large dose, worse on every axis |
| **`0xCBE74` ×1.5** | ×1.5, 12 modes | small dose, but irrelevant | 🛑 **BLOCKED ON SAFETY.** 2 flights, 2 hard faults, 0 clean flights on a live column. The threshold argument would argue for a *larger* dose, which is exactly what cannot be flown |
| **V56 mute → 0** | full mute | n/a — subtractive | ⚠ **RE-OPENED IN THE OPPOSITE DIRECTION ONLY.** Muting the lane **cost damping** ⇒ the lane is dissipative ⇒ **raising it has never been tried.** 🛑 Two caveats: V56 was scored on 15–26 Hz and **never on 6–9 Hz**, and stock is `0x8000` = −32768, which is a sentinel-shaped value, not an obvious gain — its arithmetic must be traced before any dose |

> 🛑 **BOTTOM LINE FOR V91: the threshold argument does NOT re-open this arc.** Of eight FALSIFIED
> damping-class labels, **zero** were small-dose nulls that a bigger dose would answer. Six die on
> structure, one dies on safety, and the one genuinely re-opened row (the damper's *shape*) is re-blocked
> by a sizing constraint derived before the threshold argument existed. **The kit's dose-ladder method is
> not what cost it these levers.** ★ **The live consequence: if damping is the answer, the dose has to
> come from a cell nobody has moved — which makes `0xC63A6` and the V56 lane the only two damping-class
> candidates on the board, and both need one structural query before they can be proposed.**

### D2c — ★ `0xC63A6`: what I can and cannot say

**[EVIDENCE, my own byte scan of all 87 images]** `0xC63A6` = **1024 on every image in the tree,
including stock.** It is the only one of the six lane weights in the observer's summing node that no
build has ever touched (`0xC63A0` moved on 8 images; `A2`/`A4`/`A8`/`AA` never moved either, but they
weight lanes with no damping story). `docs/traces/TRACE-2026-08-10-damping-axis-hunt.md:276` independently
records *"zero mentions, ever"*.

**[RECORD — `traces/TRACE-2026-08-10-lkas-command-visibility.md:161-168`, NOT my own decompile]** the arithmetic is
```python
S = ( clampv(gp_0x6b4e, 0x2800)*u16(0xC63A8)     # 0x3817c
    + clampv(gp_0x6b4c, 0x2800)*u16(0xC63AA)     # 0x3816c  the LKAS lane
    + clampv(gp_0x6b26, 0x400 )*u16(0xC63A6)     # 0x3815c  THE FRICTION LANE
    + clampv(gp_0x6b46, 0x400 )*u16(0xC63A4)
    + clampv(gp_0x6bd0, 0x800 )*u16(0xC63A0)     # the damper
    + clampv(gp_0x6bbe, 0x800 )*u16(0xC63A2) ) >> 10
```
Two things follow arithmetically, and they are the attractive part:
1. **The window can never bind.** `gp-0x6b26` is clamped to **±511** by `0xC407E` four instructions
   upstream, and the window here is **±1024**. The clamp is applied *before* the weight, so raising
   `0xC63A6` to 2048 is clean. ⇒ **this is dose on the friction lane WITHOUT touching `0xC407E`**, the
   cell RULE 11 forbids, and **without touching `0xCBE74`**, the row with two hard faults.
2. It is a bare `tp` scalar, so **RULE 7 is satisfied by construction** — mode-proof, no mode table.

🛑 **AND HERE IS WHY I AM NOT PROPOSING IT.** `FUN_00038148` is the **observer's reconstruction**, whose
output is `gp-0x6b70` — the residual. Per `accord-friction-polarity-more-assist`, raising the
reconstruction lowers the residual, which is **the same direction V89's K1 pushed**. If `gp-0x6b26`'s
*only* consumer is this sum, then **`0xC63A6` is the same lever as V89 through a different cell — and
V89 flew and changed nothing.** That is precisely the *"same lever pushed the other way is not a new
lever"* trap.

> **THE ONE QUERY THAT DECIDES IT, and the Ghidra agents can answer it in one call:**
> **does `gp-0x6b26` have any consumer other than `FUN_00038148` (@`0x3815c`) and the DTC-0x1d monitor
> `FUN_00036d74`?**
> - **If YES (a motor-side consumer exists)** — `0xC63A6` is a NEVER-TRIED, mode-proof, interlock-free
>   dose knob on the one lane whose dissipative sign is closed *structurally* (`TRACE` §5 Leg 3: phase of
>   `−gp-0x6c2c` vs rate never reaches −90° at any frequency to Nyquist). That is the best GATE-2
>   position of any dynamics lever in the kit.
> - **If NO** — it is observer-only ⇒ **it is V89 again** ⇒ do not fly it.
>
> ⚠ Note the asymmetry: if it is observer-only, `0xC63A6` scales the reconstruction while `0xC40D2`
> scales the model — **opposite sides of `res = MODEL − ACTUAL`** — so it is V89's direction *inverted*,
> not repeated. That is still "the same lever the other way", and V89's own probe says the lane is
> negligible on 99.1% of the target regime either way.

---

## D3 — CROSS-BUILD CELL MATRIX, READ FROM THE IMAGES

`analysis-2020accord/studies/ledger/ledger_v38_to_v84_bytes.py` extended to V90 (a `studies/ledger/ledger_v38_to_v89_bytes.py` also
exists). Values LE from the images. **"frozen" = number of consecutive builds back from V90, counting
V38 as build 1 of 55, that hold V90's value.**

| addr | w | STOCK | V84 | V85 | V86 | V86B | V87 | V88 | V89 | **V90** | **FROZEN** | what it is |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `0xC40D2` | 1 | 102 | 102 | 102 | 102 | 102 | 102 | 102 | **204** | **204** | 2 (V89) | K1 modelled Coulomb friction |
| `0xC4080` | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | **55 — every build** | K0, latent pure-Coulomb relay 🛑 |
| `0xC40BC` | 2 | 600 | 600 | **6000** | **6000** | **6000** | 600 | 600 | 600 | **600** | 4 (V87) | Coulomb relay normaliser |
| `0xC40D4` | 2 | 573 | 573 | 573 | **286** | 573 | 573 | 573 | 573 | **573** | 5 (V86B) | command-branch EMA α |
| `0xC407E` | 2 | 511 | 511 | 511 | 511 | 511 | 511 | 511 | 511 | **511** | 13 (V78) | DTC-0x1d interlock clamp 🛑 |
| `0xC404C`/`0xC4050` | 4f | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** | **55** | observer FIR taps |
| `0xC6446` | 2 | 512 | **5244** | 5244 | 5244 | 5244 | 512 | **5244** | 5244 | **5244** | 3 (V88) | r24 engaged arm — Lever B |
| `0xC6444` | 2 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | **512** | 19 (V72) | r26 engaged arm |
| `0xC643E`/`0xC6440` | 2 | 1536/2048 | = | = | = | = | = | = | = | **=** | 28 (V65) | gain_A arm / third arm |
| `0xC6442` | 2 | 1024 | = | = | = | = | = | = | = | **1024** | **55** | `gp-0x671d` arm |
| `0xC644A` | 2 | 1024 | = | = | = | = | = | = | = | **1024** | 42 (V50) | V43 pole |
| `0xC6450` | 2 | 1024 | = | = | = | = | = | = | = | **1024** | 46 (V47) | V46 lever |
| `0xC61F6` | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | **3** | **55 — every build** | r24 lane deadband |
| `0xC62EA` | 2 | 320 | **0** | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 10 (V81) | low-speed steer lockout — disabled |
| `0xC63A0` | 2 | 1024 | 1024 | = | = | = | = | = | = | **1024** | 9 (V83a) | Path-2 damper weight |
| **`0xC63A6`** | 2 | **1024** | 1024 | 1024 | 1024 | 1024 | 1024 | 1024 | 1024 | **1024** | **🛑 87/87 IMAGES — NEVER MOVED BY ANYTHING** | **friction-lane weight** |
| `0xC63A8` | 2 | 1024 | = | = | = | = | = | = | = | **1024** | **55** | observer LKAS-overlay weight (unity) |
| `0xC63AC` | 2 | 102 | = | = | = | = | = | = | = | **102** | **55** | Path-2 accumulator IIR |
| `0xC63AE` | 2 | 1024 | = | = | = | = | = | = | = | **1024** | **87/87** | LERP index scale 🛑 |
| `0xC646C` | 2 | 891 | 891 | = | = | = | = | = | = | **891** | 10 (V81) | SHARED sensor scale |
| `0xC6CD0` | 2 | −1 | **3564** | = | = | = | = | = | = | **3564** | 10 (V81) | V57 private forward LKAS gain (4×) |
| `0x2A1F0` | 2 | 29804 | **31952** | = | = | = | = | = | = | **31952** | 10 (V81) | V57 decouple displacement |
| `0xC64B0` | 2 | 257 | = | = | = | = | = | = | = | **257** | **55** | (brief-listed) |
| `0xC6200` | 2 | 8192 | = | = | = | = | = | = | = | **8192** | **87/87** | residual output clamp 🛑 |
| `0xC61B2`/`0xC61B4` | 2 | 512 | **2048** | = | = | = | = | = | = | **2048** | **55 (V38)** | ARB / LKAS-GAIN output clamps |
| `0xC61B8` | 2 | 102 | = | = | = | = | = | = | = | **102** | **55** | pre-gain deadband |
| `0x454FE` | 1 | BA | B5 | B5 | B5 | B5 | B5 | B5 | B5 | **B5** | 11 (V80) | V42 macro-ratchet fix |
| `0x3AA96` | 1 | C5 | **FB** | FB | FB | FB | **C5** | **FB** | FB | **FB** | 3 (V88) | r24/r26 gate byte |
| `0x3AB76`/`0x3AC20` | 1 | AA | AA | AA | AA | AA | AA | AA | AA | **AA** | 21 (V71b) | Lever A `sar` |
| `0x55DF2` | 2 | −27672 | −27672 | = | = | = | **−27544** | = | = | **−27430** | 1 (V90) | CAN 427 source |

### Mode-indexed records (dereferenced `ptr + mode*4`, Y at the record's own offset — an address is not a mode)

| family | mode | record | Y offset | STOCK | V84…V90 | frozen |
|---|---|---|---|---|---|---|
| **friction `0xCBE74`** | **24** | `0xD6A64` | `0xD6A6C` | `[−9830,−5734,−1966]` | **identical on ALL 87 IMAGES** | 🛑 **never changed by any build, ever** |
| **friction `0xCBE74`** | **26** | `0xD7A54` | `0xD7A5C` | `[−9830,−5734,−1966]` | Honda on V84–V90 | 9 builds (since V78) |
| friction | 27 | `0xD7A64` | `0xD7A6C` | same | Honda on V84–V90 | 9 builds |
| FactorC | 24 | `0xD67E4` | `0xD67EE` | `[0,234,429,908]` | **identical on all 87 images** | never touched |
| FactorC | 26 | `0xD77D0` | `0xD77DA` | `[0,234,429,908]` | Honda; V86B put `Y[0]`=908 | 4 (since V87) |
| FactorC | 27 | `0xD77E4` | `0xD77EE` | `[0,233,426,875]` | Honda; V86B put `Y[0]`=875 | 4 (since V87) |
| FactorE | 24 | `0xD6820` | `0xD682A` | `X=[60,400,2500,4000] Y=[0,140,539,927]` | **identical on all 87 images** | never touched |
| FactorE | 26 | `0xD780C` | `0xD7816` | same | Honda since V83a | 8 |
| FactorE | 27 | `0xD7820` | `0xD782A` | same | Honda since V84 | 7 |
| FactorB / FactorD / ceiling | 24/26/27 | — | — | flat unity / `[512,1024]` | **identical on all 87 images** | never touched |

🛑🛑 **RETRACTED, 2026-08-10, BY ME — THIS PARAGRAPH ORIGINALLY SAID THE RECORD'S "13 ENGAGED MODES"
WAS WRONG AND THE TRUE COUNT WAS 12. THAT WAS MY ERROR, NOT THE RECORD'S.** I scanned
`for m in range(32)` and **truncated the pointer array**, which walks cleanly to mode 62. V74/V75 changed
**14** friction records: `{2,3,5,10,11,14,15,17,23,26,27,29,32,33}` = **13 ENGAGED modes + mode 10**.
**`BUILD-LINEAGE.md` RULE 11's 14-site address list matches my re-measurement EXACTLY, all 14, sorted** —
`0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C 0xD3A5C 0xD3A6C 0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C
0xD9A5C 0xD9A6C`. **The record is right; I was wrong.** ⊕ The one genuinely wrong clause in the record is
RULE 11's *"so it never saw m10"* — m10 **is** written and **is** in its own 14-site list beside it; an
internal inconsistency, not a bad address. ⊕ What survives from my original paragraph, re-verified:
**mode 24 is byte-stock on all 92 build artefacts** — nothing has ever written it — so the record's
refinement stands. V73 wrote **mode 10 alone** — confirmed.
📋 **Lesson, and it is the kit's own RULE-7 trap in a new costume: a mode-indexed sweep must walk the
pointer array to exhaustion, never to a guessed bound.** `range(32)` looks like "all the modes" and is not.
⚠ **V76 discriminator confirmed from the images:**
`_v76_v38base_relu_damper` (the flown one) carries **0 changed friction modes**;
`_v76_gate_fb_arm5244_gateprobe` carries **all 12**. A glob answers the opposite question.

### What the matrix says at a glance
- **Twelve of the ~20 load-bearing cells have sat at STOCK for all 55 builds since V38** — `0xC4080`,
  `0xC404C`, `0xC4050`, `0xC6442`, `0xC61F6`, `0xC61B8`, `0xC64B0`, `0xC6200`, `0xC63A8`, `0xC63AC`,
  plus `0xC63A6` and `0xC63AE`, which are stock on **all 87 images in the tree** (I scanned every one).
  Three are frozen because they are **forbidden** (`0xC4080`, `0xC63AE`, `0xC6200`); several because
  they were shown structurally dead. **`0xC63A6` is frozen for no recorded reason at all.**
- **Every damper, friction and phase excursion between V72 and V86B has round-tripped to stock.** V90 is
  V38's foundation + V57's decouple + V42's byte + V53's steer-to-zero + Lever B + the cave + K1.
- **`0xC6446` and `0x3AA96` are the only two behavioural cells that are non-stock and measured to work.**

---

## D4 — 🛑 THE COMPLETE NON-STOCK DELTA OF V90 vs STOCK

**Method [EVIDENCE]:** byte diff of `_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin`
against `stock_fw_dump/code.bin` over `[0x13000, 0x100000)`, grouped into runs, then **each run's value
trajectory printed across all 56 images V38→V90** so the introducing build is read from the images, not
assumed. **107 runs / 215 bytes**, of which **4 runs / 16 bytes are CRC trailers** (listed separately) ⇒
**103 runs / 199 functional bytes. Zero unattributed.**

Reconciliation against the prior audit: V89 vs stock was **107 runs / 203 bytes**; V90 adds exactly
**12 bytes of cave** (62 → 74) and changes 1 byte of the 427 repoint, so 203 + 12 = **215** ✓.
V90 vs V89 directly = **9 runs / 68 bytes** ✓ (the handoff's "80 bytes" counts bytes *written*: 74 cave +
2 repoint + 4 CRC, not bytes *changed* vs base — both are right, they count different things).

### The cumulative delta, grouped and attributed

| # | address(es) | bytes | stock → V90 | what the variable physically is | what it does to the car | introduced | status |
|---|---|---|---|---|---|---|---|
| 1 | `0x13109`, `0x14120` | 2 | `'-'` → `','` | the part-number **string** `39990-TVA-A160` at `0x13100` / `0x14117` | **nothing** — lets a flashed ECU be told from stock at a glance | **V18** | cosmetic |
| 2 | `0xC61B3`, `0xC61B5` (high bytes of `0xC61B2`/`0xC61B4`) | 2 | 512 → **2048** each | ARBITRATION and LKAS-GAIN **output clamps** | **4× the LKAS authority ceiling** | **V38** | ✅ **measured on-car**, fault-free on 55 builds |
| 3 | `0xC659A`,`9E`,`AE`,`B2`,`C6`,`CA`,`CE` | 7 | floats `1.0→5.0`, `−1.0→−5.0`, `0.0/1.5/2.0→5.0` | **FLOAT** corridor / boost soft walls | the FP twin of #4, kept in lockstep so the dual-path monitor cannot trip | **V38** | ✅ measured (this is the V27 brick mechanism done *correctly*) |
| 4 | `0xC674F`,`51`,`5B`,`5D`,`69`,`6B`,`6D` | 7 | `±1024 → ±5120` (and `0/1536/2048 → 5120`) | **INT** corridor / boost soft walls, driver column-torque pushback | widens the direction corridor and boost floor **5×** to match #2's raised authority | **V38** | ✅ measured |
| 5 | `0xE4195`…`0xE4245` + `0xE5195`…`0xE521D` | 72 | u16 `15360 → 16384` (high byte `0x3C→0x40`) in **all 8** selector-reachable records | **ARB SETPOINT LIMIT** — a symmetric ± clamp on the LKAS setpoint, on the driver-pushback axis | recovers the top **6.25%** of the command range openpilot's `torqueBP` was clipping | **V38** | ✅ measured |
| 6 | `0xC61C0`–`0xC61C5` | 6 | `1600, 896, 1280` → `0xFFFF` ×3 | gentle-EME **debounce RATE channel** thresholds | unsigned `cal < signal` becomes permanently false ⇒ **the debounce SM can never fire** | **V36/V38** | ✅ measured — resolved the gentle-EME complaint |
| 7 | `0xC64B4`–`0xC64B8` | 5 | `24688, 16438, 112` → `0xFF`s | gentle-EME **debounce TORQUE channel** + the **DTC-0x49 fault counter** gate | same mechanism; `0xC64B8`→255 makes DTC 0x49 unfirable. ⚠ **Accepted side effect**: for torque in (112,255] the live arb no longer takes its high-torque cutoff branch | **V36 / V37** | ✅ measured, side effect operator-accepted |
| 8 | `0xC64DE` | 1 | `0x11 → 0x1B` (17→27) | legacy "RAMPSTEP" — **label disputed**, corrected 2026-07-18 (the real slew limiter is elsewhere) | ⚠ **unverified** — carried since V18, road-validated but never isolated | **V18** | ⚠ **carried; not measured as a lever** |
| 9 | `0x2A1F0` | 2 | disp `0x6C74 → 0xD07C` | repoints the **forward** LKAS gain read to `0xC6CD0` | decouples the LKAS forward gain from the shared sensor scale, so feedback readers stay un-boosted | **V57**, lost at V76/V78–V80, restored **V81**, carried since | ✅ measured |
| 10 | `0xC6CD0` | 2 | unset(`−1`) → **3564** | V57's **private 4× forward LKAS gain** | delivers the 4× without the 5 other readers of `0xC646C` seeing it | **V57** / restored V81 | ✅ measured. 🛑 `0xC646C` itself is **stock 891** — the 4× lives here |
| 11 | `0x3AA96` | 1 | `0xC5 → 0xFB` | rate-lane **gate selector**: dead constant → `latActive` | **arms the r24 rate-derivative lane only while LKAS is engaged** — "Lever B" | **V67**, lost at V87's rebase, **restored V88** | ✅ **measured — the kit's only grinding fix** |
| 12 | `0xC6446` | 2 | 512 → **5244** | r24 **engaged arm magnitude** — 2.000× the mode-24/26 LERP value of 2622 | doubles the rate-derivative feedback when engaged ⇒ **more damping** ⇒ command 15–22 Hz content **halved** at zero LF cost | **V67** / restored **V88** | ✅ **measured.** 🛑 Dose is **rail-limited**: hot-end margin 1.50× at 5244, **1.00× at 7866** ⇒ ≥2.5× turns it into a relay |
| 13 | `0x454FE` | 1 | `0xBA (bne) → 0xB5 (br)` | makes a state-4 governor branch unconditional | V42's macro-ratchet fix | **V42**, lost/restored **3×**, present since V80 | 🛑 **MEASURED INERT** — `gp-0x67fa`'s reachable set excludes the guarded state. Kept because it is free, **not** because it acts |
| 14 | `0xC62EA` | 2 | 320 → **0** | low-speed steer **lockout window** (~5 km/h) | "steer to zero" — LKAS keeps authority below 5 km/h instead of dropping to `STEER_STATUS=3` | **V53**, restored **V81** | ✅ measured |
| 15 | `0x55C0E` | 4 | `2436e8ea → 86ff26ef` | the **trampoline** into the cave — a `movea` replaced by `jarl` | mechanical: reaches #17 | **V53** era (hook itself dates to V31P) | mechanical |
| 16 | `0x55DF2`–`0x55DF3` | 2 | `0xE893 → 0xDA94` | source displacement of the **CAN 427 `MOTOR_TORQUE`** packer | stock: a stale sensor value. **V87**: `gp-0x6b98` = the real delivered command. **V90**: `gp-0x6b26` = the **friction lane**, ~9 unclipped effective bits | `0x55DF3` at **V87**, `0x55DF2` at **V90** | ✅ V87's repoint measured (it closed the H2 fork). **V90's is unmeasured — that is the flight's deliverable** |
| 17 | `0xC4B34`–`0xC4B7D` | **74** | `0xFF` fill → cave payload | **the telemetry cave** — 100 Hz, 5 bits onto CAN `0x14A` byte 4 bits 7:3 | **reads nothing, writes nothing to the control path.** V90's rungs: `b7` = `gp-0x6b26 < 0` (sign; the only channel reaching 18–28 Hz) · `b6` = `\|gp-0x6bf6\| ≥ 512` (`\|model\|`) · `b5` = `gp-0x6ae2 ≠ 0` (friction non-zero; V89's rung, unchanged, apples-to-apples) · `b4` = `gp-0x6c00 < 0` (**the observer gate — never once measured**, and the build-identity discriminator) · `b3` = fingerprint | cave lineage **V39 → V90**; this payload **V90** | ⏳ **unmeasured** — route `77` pending. 🛑 Gate-1/Gate-2 both clean: the cave is read-only |
| 18 | `0xC40D2` | 1 | `102 → 204` (`0x66→0xCC`) | **K1** — the `\|model\|`-proportional **modelled Coulomb friction** coefficient inside `FUN_0003b8f6`, the 1 kHz disturbance-observer plant model. **2.000×** | doubles how much Coulomb friction the observer *believes* the plant has ⇒ residual `= MODEL − ACTUAL` falls ⇒ tracking reference falls ⇒ error rises ⇒ PID rises ⇒ **more assist, lighter wheel** | **V89** | 🛑 **MEASURED AND FLAT** on the largest exposure in the corpus (contrast 0.947, inside its own placebo band). Left on the car deliberately so V90 observes it |
| — | `0xC4FFC`, `0xC6FFC`, `0xE4FFC`, `0xE5FFC` | **16** | recomputed | **bootloader CRC trailer words**, 4 of the 50-block chain | mechanical | tracks the edits above | 🛑 `walk_all_blocks == 0` is **necessary, not sufficient** — derive the trailer set in code from the touched addresses, never from a list |

### Cumulative, in one sentence
**V90 = V38's authority foundation (4× LKAS gain + matched corridor/boost walls + raised setpoint limit +
gentle-EME/DTC-0x49 disabled) + V57's private-gain decouple + V42's inert byte + V53's steer-to-zero +
Lever B (V67, restored V88) + the read-only telemetry cave + V89's K1 = 204 — and NOTHING ELSE.**
- **Measured on-car and working:** #2, #3, #4, #5, #6, #7, #9, #10, **#11, #12** (Lever B is the only
  behavioural lever with a measured symptom fix), #14, #16 (V87 half).
- **Measured and INERT:** #13 (`0x454FE`), #18 (`0xC40D2` = 204 — **flat**).
- **Unverified / carried:** #8 (`0xC64DE`, label disputed since V18), #1 (cosmetic).
- **Unmeasured, pending:** #16's V90 half, #17's V90 rungs.
- **Carried by accident: NONE.** I checked all seven of the V38 rebase's silent reverts against the
  images: `0xC63A0` = 1024 ✓ stock, `0xC407E` = 511 ✓ stock, friction row = Honda in all 32 modes ✓,
  `0xC62EA` = 0 (deliberately restored) ✓, the V57 triplet restored ✓, `0x454FE` = B5 restored ✓,
  `gain_A` rec0/rec1 = 3072/… = stock ✓. **Everything non-stock on V90 is there on purpose.**

---

---

# ADDENDUM (T1–T3) — THE `FUN_00038148` WEIGHT NODE, SWEPT

## T1 — the whole block, 0xC6390–0xC63C2, across **93 images** (1 stock + 86 `_v*` + 6 `SUPERSEDED-*`)

**[EVIDENCE — my own Python sweep, u16 LE, every image in the tree.]**

| addr | stock | V90 | # images ever non-stock | which |
|---|---|---|---|---|
| `0xC6390`,`92`,`94`,`96`,`98`,`9A`,`9C`,`9E` | 2048,2048,1331,10,102,204,204,717 | = | **0** | virgin |
| **`0xC63A0`** damper lane `gp-0x6bd0` | 1024 | 1024 | **12** (8 distinct build numbers) | V72, V73, V74, V75, V76g, V81 + 4 SUPERSEDED twins + SUPERSEDED-V83a |
| **`0xC63A2`** boost lane `gp-0x6bbe` | 1024 | 1024 | **0** | 🛑 **virgin on every image** |
| **`0xC63A4`** torque-domain lane `gp-0x6b46` | 1024 | 1024 | **0** | 🛑 **virgin on every image** |
| **`0xC63A6`** FRICTION lane `gp-0x6b26` | 1024 | 1024 | **0** | 🛑 **virgin on every image** |
| **`0xC63A8`** LKAS-class lane `gp-0x6b4e` | 1024 | 1024 | **0** | 🛑 **virgin on every image** |
| **`0xC63AA`** LKAS lane `gp-0x6b4c` | 1024 | 1024 | **0** | 🛑 **virgin on every image** |
| `0xC63AC` accumulator EMA α | 102 | 102 | **0** | virgin |
| `0xC63AE` LERP index scale | 1024 | 1024 | **0** | virgin |
| `0xC63B0`…`0xC63C2` | −32768, 13107, 51, 1, 41, 512, 0, 1024, 33, 1024 | = | **0** | virgin |

**Adjacent cells in the same observer pipeline:**

| addr | what | stock | V90 | ever non-stock |
|---|---|---|---|---|
| `0xC6468` | **model / recon OUTPUT scale (shared by both sides)** | 2639 | 2639 | **0 — virgin** |
| `0xC6200` | residual output clamp | 8192 | 8192 | **0 — virgin** |
| `0xC613A` | column-torque scale into the model | 1159 | 1159 | **0 — virgin** |
| `0xC646E` | INERTIA gain | 1428 | 1428 | **0 — virgin** |
| `0xC4080` | K0, latent pure Coulomb relay | 0 | 0 | **0 — virgin** 🛑 forbidden |
| `0xC40D2` | K1 modelled Coulomb (byte) | 102 | **204** | 2 (V89, V90) |
| `0xC40BC` | Coulomb relay normaliser | 600 | 600 | 3 (V85, V86, V86B) |
| `0xC40D4` | command-branch EMA α | 573 | 573 | 1 (V86) |
| `0xC407E` | friction clamp / DTC-0x1d interlock | 511 | 511 | 10 (V73–V77b + 3 SUPERSEDED) 🛑 |

> 🛑 **HEADLINE: of the SIX lane weights in the node, the kit has ever moved exactly ONE — `0xC63A0`.
> The other five, the accumulator α, the LERP scale, the shared output scale `0xC6468`, the residual
> clamp and the two model-input scales are ALL virgin on all 93 images.**

## T2 — bucket, per cell, with intent-vs-fact checked

**[EVIDENCE]** Build scripts *mention* `0xC63A2`/`A4`/`A6`/`A8`/`AA` — but I read every mention and
**all of them are `FROZEN_CELLS` guards asserting stock, not edits**: `builds/v80_v107/build_v90_tva.py:175-179`
(`0xC63A6: (2, 1024, "loop-gain family")`), `builds/v50_v79/build_v79_tva.py:146` / `builds/v80_v107/build_v80_tva.py:129`
(`C63A0_BLOCK = tuple(range(0xC63A0, 0xC63AC, 2))` … *"all == STOCK. NOT DOUBLED"*).
⇒ **INTENT AND FACT AGREE for all five. No divergence to flag.** (The V38-rebase precedent does not
bite here, because nothing was ever declared as an edit.)

| cell | bucket | basis |
|---|---|---|
| `0xC63A0` | 🛑 **FLOWN-AND-FALSIFIED (as INERT)** | 2048 flew on V72, V73, V81 (+V74/V75). Struck: `ch₀ = (FactorC×FactorE)>>10` is **exactly 0 on 98.8 % of engaged frames** ⇒ 2 × 0 = 0 |
| `0xC63A2`, `0xC63A4`, `0xC63A6`, `0xC63A8`, `0xC63AA` | ★ **NEVER-TRIED** | 0/93 images; every script mention is a stock-assertion guard |
| `0xC63AC`, `0xC63AE` | **NEVER-TRIED**; `0xC63AE` additionally 🛑 **NEVER →0** (relay hazard) | 0/93 |
| `0xC6468`, `0xC6200`, `0xC613A`, `0xC646E` | **NEVER-TRIED**; `0xC6200` 🛑 **NEVER < Y[0]** and **3 of its 15 readers are still unidentified** | 0/93 |

⊕ **NEW ARTEFACT-COLLISION FINDING, and it NARROWS the recorded hazard rather than widening it.**
Eight build numbers have >1 artefact on disk (V31P, V72, V73, V74×3, V75, V76×3, V83a, V84).
**Only TWO disagree on any RULE-11 / Lever-B cell:**
- **V76** — disagrees on **all five** (`0xC63A0`, `0xC407E`, `0xC6446`, `0x3AA96`, `0x454FE`). 🛑 It is the
  **only** collision where *two non-`SUPERSEDED`-prefixed artefacts* disagree
  (`_v76_gate_fb_arm5244_gateprobe` vs `_v76_v38base_relu_damper`) ⇒ a `_v76*` glob really can pick either.
- **V83a** — disagrees on `0xC63A0` only (**2048** vs the flown **1024**), and this is **NOT in the record**.
  ⊕ But its disagreeing twin *is* correctly prefixed `SUPERSEDED-DO-NOT-FLASH-`, and the flown file's own
  name encodes the value (`-C63A0.1024`) ⇒ a `_v83a*` glob resolves **correctly**. Lower hazard than V76.
- The other six collisions are **byte-identical on all five cells** — no hazard.

## T3 — 🛑 THE COUNTER-ARGUMENT, MADE AS HARD AS I CAN, AND THEN ADJUDICATED

**The counter-argument, steelmanned in three steps:**

1. **Every weight in that node moves ONE scalar.** Downstream of the sum there is exactly one path:
   `S → ×pol×0xC6468 → ×16 → one-pole EMA (0xC63AC) → recon → res = model − recon → LERP → clamp(±0xC6200)
   → gp-0x6b70`. So `0xC63A6`, `0xC63A0` and `0xC63A8` are **not independent mechanisms** — they are the
   same mechanism with different input weighting.
2. **V89 already moved that scalar from the other side and measured FLAT** on the largest exposure in the
   corpus. `res = MODEL − ACTUAL`: +δ on the model and −δ on the reconstruction are **the same residual
   perturbation**. So "`0xC63A6` is a new lever" requires that it can deliver a residual perturbation
   K1×2 could not.
3. **And the node's one moved weight returned a null** (`0xC63A0` on V72/V73/V81).

**Adjudication — I ran the arithmetic rather than arguing it.** Integer mirror of the node
(`clampv`/`>>10`/`×0xC6468`/`×16`/EMA/`>>4`, all constants byte-read):

```
d(recon)/d(gp-0x6b26)  =  0xC6468 / 1024  =  2.5771   EXACTLY, and LINEAR
 => 0xC63A6: 1024 -> 2048 delivers  d(res) = -2.5771 x gp-0x6b26
```

| `\|gp-0x6b26\|` | Δrecon | as % of the ±8192 residual clamp |
|---|---|---|
| 0 ct | **0** | **0.0 %** |
| 32 | 82 | 1.0 % |
| 64 | 165 | 2.0 % |
| 128 | 330 | 4.0 % |
| 256 | 660 | 8.1 % |
| **511 (lane railed)** | **1317** | **16.1 %** |

Now each leg:

- **Leg 3 FAILS outright.** `0xC63A0`'s null is fully explained by its **LANE** being zero, not by the
  node being inert: `gp-0x6bd0` is exactly 0 on 98.8 % of engaged frames. **Doubling a weight on a zero
  lane is an arithmetically guaranteed null and carries ZERO information about any other weight.** The
  record does **not** say "four weights moved and all were null" — it says **one** weight moved, and that
  one was untestable by construction. ⇒ **the node's weights have never actually been tested as levers.**
- **Leg 2 — and this is the crux — FAILS TOO, and NOT by special pleading.** The distinction is not
  "Coulomb vs derivative" as a story; it is a **measured magnitude**. V89's own probe says its term was
  `≥ 0.0625` model units on **0.9 %** of micro-ratcheting frames ⇒ **K1×2 perturbed the model by
  approximately NOTHING in the target regime.** A null from a ~zero perturbation does not bound a
  non-zero one. **V89 did not test the residual axis at a real dose; it tested it at ~no dose.**
- **Leg 1 STANDS, and it is the binding one.** Same scalar, same single downstream path. So the *entire*
  question reduces to one measurable number.

> ### ⇒ VERDICT: **a real distinction, NOT special pleading — but currently UNEVIDENCED, and V90's
> flight is precisely the evidence.**
> `0xC63A6` ×2 delivers **`2.577 × gp-0x6b26` counts of residual perturbation and nothing else.** If
> `gp-0x6b26` is near zero in the micro-ratcheting regime, **it is V89 again, exactly**, and will return
> the same flat result for the same reason. If it is a few hundred counts, it is a genuinely new dose on
> an axis that has never been tested at a real dose.
> 🛑 **DO NOT CUT V91 ON THIS BEFORE ROUTE 77 IS SCORED.** V90 repointed CAN 427 at `gp-0x6b26` for
> exactly this number — *"the baseline that would let a future dose be SIZED rather than guessed."*

**★ FREE AND WORTH DOING NOW — pre-register the threshold before the route is scored:**
- **p50 `|gp-0x6b26|` in the 1–13 °/s engaged regime ≲ 32 ct** ⇒ Δres ≤ 1 % of clamp ⇒ **`0xC63A6` is
  V89 repeated. Do not fly it.**
- **≳ 256 ct** ⇒ Δres ≥ 8 % ⇒ **a genuinely new dose**, and V89's own placebo band ([0.900, 1.111], an
  11 % band) is the resolvability yardstick it must beat.
- Between 32 and 256 ⇒ **underpowered; say so rather than flying it.**

**Safety precedent for doubling a weight in this node [EVIDENCE, from the images]:** `0xC63A0` = 2048
flew **fault-free on V72 and V81 with the interlock at stock 511**, and on **V73 with the interlock at
850**; V74/V75 faulted and both carried `0xC407E` = 850. ⇒ **3 clean flights, 0 faults at a stock
interlock.** Thin but positive.
⚠ **Ceiling, two-method:** `gp-0x6b26` is pre-clamped ±511, the node's window on that lane is ±1024. At
w = 2048 the weighted term is 1022 — **under the window under BOTH readings of where the window sits**
(before or after the multiply). At w = 4096 it is 2044, which is safe only if the window precedes the
multiply, as the record's arithmetic shows. ⇒ **×2 is safe under either reading; ×4 depends on an
ordering claim I have not verified myself. Do not exceed ×2 without a decompile.**

---

---

# ADDENDUM 2 (T1′–T3′) — THE `0xCBE74` BUILD TARGET

🛑 **T1–T3 (the `0xC63A0` block sweep) is CANCELLED** by the orchestrator: the `gp-0x6b26` consumer
census found a motor-side reader at `0x3ac98` inside `FUN_0003aa2c`, so `0xC63A6` is **observer-only ⇒
V89's axis ⇒ dead**, and `0xCBE74` — which scales `gp-0x6b26` itself, hence **both** paths — is the lever.
My T3 counter-argument predicted this outcome for `0xC63A6` and it is retained above as written.

## T1′ — the records, dereferenced, with the mode number beside every address

**[EVIDENCE — my own Python, `0xCBE74 + mode*4`, X at record `+2`, Y at record `+2+2n` = `+8` for n=3.]**

| mode | ptr slot | record | n | X array (`+2`) | **Y array (`+8`)** |
|---|---|---|---|---|---|
| **24** *(manual)* | `0xCBED4` | `0xD6A64` | 3 | `0xD6A66` = `[0, 1280, 5760]` | **`0xD6A6C` = `[−9830, −5734, −1966]`** |
| **25** | `0xCBED8` | `0xD7A44` | 3 | `0xD7A46` = `[0, 1280, 5760]` | **`0xD7A4C` = `[−9830, −5734, −1966]`** |
| **26** *(engaged)* | `0xCBEDC` | `0xD7A54` | 3 | `0xD7A56` = `[0, 1280, 5760]` | **`0xD7A5C` = `[−9830, −5734, −1966]`** |
| **27** | `0xCBEE0` | `0xD7A64` | 3 | `0xD7A66` = `[0, 1280, 5760]` | **`0xD7A6C` = `[−9830, −5734, −1966]`** |

- 🛑 **Stock Y CONFIRMED as `[−9830, −5734, −1966]`** on all four. Raw 16 B, identical in every record:
  `03000000000580169ad99ae952f80000`.
- 🛑 **V90 is BYTE-STOCK on all four** — pointer, `n`, X, Y and pad all identical. `True` on every field.
- **All four modes have distinct records** — no aliasing, so a write to 26 cannot leak into 24.
- ⚠ **Mode 25's record is `0xD7A44` = exactly `0x10` BELOW mode 26's.** A −0x10 slip lands on a
  **disengaged** column with a plausible-looking result. Assert mode 25 byte-identical, not just mode 24.

## T2′ — the dose table

| mult | Y[0] | Y[1] | Y[2] | trunc == round? | int16 | headroom on Y[0] |
|---|---|---|---|---|---|---|
| **×1.5** | **−14745** | **−8601** | **−2949** | ✔ exact | OK | 18,023 |
| **×2.0** | −19660 | −11468 | −3932 | ✔ exact | OK | 13,108 |
| **×2.5** | −24575 | −14335 | −4915 | ✔ exact | OK | 8,193 |
| **×3.0** | −29490 | −17202 | −5898 | ✔ exact | OK | 3,278 (10.0 %) |
| ×3.3 | −32439 | −18922 | −6488 | ✘ rounding matters | OK | 329 |
| **×3.34** | **−32832** | −19152 | −6566 | — | 🛑 **OVERFLOW** | −64 |
| **×4.0** | **−39320** | −22936 | −7864 | — | 🛑 **OVERFLOW by 6,552** | −6,552 |

- ⊕ **Self-check: ×1.5 reproduces the flown V74/V75 bytes EXACTLY** (`[−14745, −8601, −2949]`, read from
  their images). My arithmetic and the flown artefacts agree bit-for-bit.
- 🛑 **LARGEST NON-OVERFLOWING MULTIPLIER, COMPUTED NOT RECALLED: `k_max = 32768 / 9830 = 3.33347`.**
  The binding element is **`Y[0] = −9830` against int16 MIN −32768** (not MAX — the row is negative).
  At `k_max` exactly, `Y[0] = −32768` = the rail. **`|Y|×4` overflows — the record is CONFIRMED.**
  ⇒ **×3.0 is the largest round multiplier with real headroom (10.0 %), and it is also the recorded
  `DampAxis` safety ceiling. ×1.5, ×2.0, ×2.5, ×3.0 all round exactly — no rounding convention needed.**
- ✅ **X arrays are UNCHANGED by the edit — asserted as a boolean, not assumed.** The write touches only
  `base+8 .. base+13`; X lives at `base+2 .. base+7` and is not in the written span.

### Exact write targets — the builder writes these bytes and nothing else

```
MODE 26  record 0xD7A54  n=3
    WRITE  0xD7A5C .. 0xD7A61      6 BYTES   3 x int16 LE   <- Y only
    KEEP   0xD7A54 .. 0xD7A55  (n=3)
    KEEP   0xD7A56 .. 0xD7A5B  (X = 0, 1280, 5760)
    KEEP   0xD7A62 .. 0xD7A63  (pad 00 00)
MODE 27  record 0xD7A64  n=3
    WRITE  0xD7A6C .. 0xD7A71      6 BYTES   3 x int16 LE   <- Y only
    KEEP   0xD7A64 .. 0xD7A65 / 0xD7A66 .. 0xD7A6B / 0xD7A72 .. 0xD7A73
TOTAL LEVER BYTES = 12.
CRC: BOTH records are in [0xD7000, 0xD7FFC)  =>  ONE trailer, 0xD7FFC.
     (mode 24's record is in the 0xD6000 block and is NOT touched.)
```

**Assertions the builder must EMIT AS BOOLEANS** (*"a check that produces no output is not a check that
passed"*): `u16(0xD7A54)==3` · `u16(0xD7A64)==3` · `s16x3(0xD7A56)==(0,1280,5760)` ·
`s16x3(0xD7A66)==(0,1280,5760)` · pad at `0xD7A62`/`0xD7A72` == `0000` ·
`u32(0xCBED4)==0xD6A64 ∧ u32(0xCBEDC)==0xD7A54 ∧ u32(0xCBEE0)==0xD7A64` ·
**records for modes 24 AND 25 byte-identical to base** · **and walk the pointer array to exhaustion
(it runs to mode 62), asserting every OTHER mode byte-identical to base** — a count-only census is blind
to a write into an already-non-stock record.

## T3′ — 🛑 THE LINEAGE PARAGRAPH, FOR THE OPERATOR, UNSOFTENED

**[EVIDENCE — mode-26 Y read from all 92 build artefacts + stock.]**

| artefact | m24 | m26 | `0xC407E` | flew? | on-car |
|---|---|---|---|---|---|
| `_v74_engagedcols_x0_12_addonly` | stock | **×1.50** | **850** | ✅ | 🛑 **HARD FAULT, latched loss of assist** (in MANUAL) |
| `_v75_CY0.566-EX1.200_magprobe` | stock | **×1.50** | **850** | ✅ | 🛑 **HARD FAULT, latched** (ENGAGED) |
| `_v75_CY0.566_magprobe` | stock | ×1.50 | 850 | — | twin artefact |
| `_v76_gate_fb_arm5244_gateprobe` | stock | ×1.50 | 850 | ❌ | never flew |
| `_v77_C63A0.1024_v74base` | stock | ×1.50 | 850 | ❌ | never flew |
| `_v77b_C63A0.1024_v75base` | stock | ×1.50 | 850 | ❌ | never flew |
| 2 × `SUPERSEDED-…_v74_…` | stock | ×1.50 | 850 | ❌ | never flew |

**mode 26 Y is non-stock on 8 of 92 artefacts. mode 24 Y is non-stock on ZERO — nothing has ever written
the manual column.** V74/V75 wrote **14** records (13 engaged modes + mode 10).

> ### The paragraph, as it must read before he drives it
> **This row has flown live exactly twice, and both flights hard-faulted with a latched total loss of
> power steering.** It is **not** a new lever — it is **the same lever, at the same ×1.5 dose, with the
> interlock corrected.** What is different is one cell: every artefact that has ever carried this dose
> also carried **`0xC407E` = 850**, and V91 would carry Honda's **511**. At 511 the friction lane is
> clamped one count below the DTC-0x1d monitor's own 512 trip, so that monitor is untrippable by
> construction, at any multiplier.

🛑 **THREE THINGS THAT PARAGRAPH MUST NOT BE ALLOWED TO HIDE, and I am stating them as the reason the
flight decision is the operator's:**

1. **The record contains ZERO artefacts separating the dose from the 850 interlock.** All 8 carry both.
   ⇒ **no flight, ever, has tested this dose at a stock interlock.** The separation is **purely
   structural** (clamp 511 < trip 512), not empirical. That structural argument is EVIDENCE and I am not
   disputing it — but it is the *only* thing separating them, and it should be stated that way rather
   than as "the faults were the clamp's fault".
2. 🛑 **"Untrippable by magnitude" is exactly the claim RULE 8b says is structurally blind.** V75's fault
   is pinned to **one 100 Hz frame** and characterised as a **fast-transient** sensitivity, with a
   **20.0 Hz oscillation 300 ms before the latch absent from openpilot's command**; the faulting launch
   was the *mildest* of four and had **0.00 % rail contact**. And RULE 11 itself marks *"`0xC407E` = 850
   caused BOTH faults"* as **BELIEF — the DTC number was never confirmed on-car.** ⇒ **"DTC 0x1d cannot
   fire at 511" is EVIDENCE. "Therefore V91 cannot fault" is NOT** — it inherits the BELIEF that 0x1d was
   the mechanism. If it was something else, the clamp argument does not cover it.
3. **Its own advocates struck it as the mechanism.** `HANDOFF-2026-08-10` §4a: `gp-0x6c2c` is
   acceleration-like ⇒ a term driven by it **scales with rate**, and the corpus says the amplification is
   **rate-independent** ⇒ *"defensible as a damper, not as the mechanism."* And **the dose cannot be
   sized** — that handoff records both sizing inputs as struck. ⇒ V91 is a **threshold bet**, which is
   coherent under the FIV account (§2a) but must be *called* a bet.

⊕ **What is genuinely better this time, stated fairly:** the ×1.5 dose has never flown with (a) the
interlock at stock 511, (b) mode 24 byte-stock **and** the damper reverted to Honda, or (c) Lever B on
board. And **V81 is the nearest positive control** — `0xC407E` reverted 850→511 on a V75 base, flew route
67 **fault-free**. So the clamp revert has a clean flight behind it; the clamp revert *plus this dose*
does not.
⚠ **Scope note:** writing only modes 26/27 is **narrower than V74/V75's 14**. For this car that is
correct and conservative (TVCA4, manual 24 / engaged 26, both proven) — but say it is a deliberate
narrowing, not a reproduction.

## ⊕ Record-only note, relayed from the orchestrator (NOT my own measurement)
Route `00000074--ef6c21294f` is **stationary**: `vEgo` max exactly 0.00 over 5,246 samples, `latActive`
never true, 56.8 s of post-flash key-on. **It contributes zero exposure to the V88 or V89 arm and must
not inflate any route-count denominator.** Recorded here so it is not re-counted; I did not verify it.

---

---

# ADDENDUM 3 (U1–U3) — ROUTE 77 SCORED: `0xC63A6` KILLED, AND THE `0xCBE74` DOSE IS FORCED TO ×1.5

## U1 — `0xC63A6`: **NEVER-TRIED → KILLED-ON-PRE-REGISTERED-SIZING**

**The pre-registration I wrote in Addendum 1 fired against my own preferred candidate.**

| written before the data existed | measured on route 77 |
|---|---|
| p50 `\|gp-0x6b26\|` in **1–13 °/s engaged** **≲32 ct** ⇒ Δres ≤1 % ⇒ **V89 repeated, do not fly** | **p50 = 7.1 ct** (437.6 s engaged exposure) |
| ≳256 ct ⇒ genuinely new | p99 96.7, max 303.1 |

Through my own integer mirror, `d(recon)/d(gp-0x6b26) = 0xC6468/1024 = 2.5771`, exact and linear:

| point | Δresidual | % of the ±8192 clamp |
|---|---|---|
| **micro-regime p50 (7.1 ct)** | **18.3 ct** | **0.22 %** |
| p99 (96.7) | 249 ct | 3.0 % |
| max (303.1) | 781 ct | 9.5 % |

⇒ **`0xC63A6` is 4.5× below my own do-not-fly line. DEAD.**

> 🛑 **AND THE BUCKET MATTERS — this is `INERT-IN-THIS-REGIME`, NOT `FALSIFIED`, NOT `STRUCTURALLY-DEAD`.**
> `0xC63A6` is killed on **LANE MAGNITUDE**, measured on one route's distribution — **not on structure.**
> The cell is still a real, mode-proof, interlock-free weight on a lane whose dissipative sign is closed
> structurally. **If a future session measures a materially larger `gp-0x6b26` in the micro regime — a
> different route, a different base build, or after a `0xCBE74` dose raises the lane itself — this row
> RE-OPENS on its own terms.** Conflating "inert in this regime" with "falsified" is the exact error this
> brief's D2 audit was written to catch; do not let this row become an example of it.
> ⊕ Note the self-reference: **a `0xCBE74` dose scales `gp-0x6b26` itself**, so it would raise the very
> input that made `0xC63A6` negligible. The two are not independent.

⊕ My T3 legs survive the result: Leg 3 (`0xC63A0`'s null carried zero information — its lane is zero by
construction) and Leg 2 (V89 tested the axis at ~no dose) both hold. **The residual axis still has never
been tested at a real dose — and now we know it cannot be, from this cell, because the lane is small
where the symptom is.**

## ⊕ Your Path 1 / Path 2 distinction — **I agree with it, and here is the number**

| knob | path | delivered effect at the micro-regime p50 | dynamics in between |
|---|---|---|---|
| `0xC63A6` ×2 | **Path 2 only** (observer) | 18.3 ct residual = **0.22 %** of the ±8192 clamp | LERP + EMA + full PID, **transfer unknown at 6–9 Hz** |
| `0xCBE74` ×1.5 | **Path 1 + Path 2** | **3.8 ct into `gp-0x6b98`** = **1.8 %** of the 208-ct engaged median command | **NONE** — direct unweighted addend at `0x3ac98` |

**≈8× more delivered effect per unit dose, and — more importantly — through a transfer that is known
and dynamics-free rather than one that is unknown.** The distinction is **correct** and I am not
disputing it. **But it does not clear `0xCBE74` on sizing**, and the same route-77 number now constrains
the dose. That is U2b.

## U2 — the `0xCBE74` dose table *(re-verified from disk this message; stock sha `3f1d55a98aac6e73`, V90 sha `28ac817bc3f76958`)*

| mode | ptr slot | record | n | X (`+2`) | **Y (`+8`)** | V90 byte-stock |
|---|---|---|---|---|---|---|
| **24** *(manual)* | `0xCBED4` | `0xD6A64` | 3 | `0xD6A66` = `[0,1280,5760]` | **`0xD6A6C` = `[−9830,−5734,−1966]`** | ✅ `True` |
| **25** | `0xCBED8` | `0xD7A44` | 3 | `0xD7A46` = `[0,1280,5760]` | **`0xD7A4C` = `[−9830,−5734,−1966]`** | ✅ `True` |
| **26** *(engaged)* | `0xCBEDC` | `0xD7A54` | 3 | `0xD7A56` = `[0,1280,5760]` | **`0xD7A5C` = `[−9830,−5734,−1966]`** | ✅ `True` |
| **27** | `0xCBEE0` | `0xD7A64` | 3 | `0xD7A66` = `[0,1280,5760]` | **`0xD7A6C` = `[−9830,−5734,−1966]`** | ✅ `True` |

| mult | Y[0] | Y[1] | Y[2] | per-element int16 in-range | verdict |
|---|---|---|---|---|---|
| **×1.5** | **−14745** | **−8601** | **−2949** | `[True, True, True]` | OK |
| ×2.0 | −19660 | −11468 | −3932 | `[True, True, True]` | OK |
| ×2.5 | −24575 | −14335 | −4915 | `[True, True, True]` | OK |
| ×3.0 | −29490 | −17202 | −5898 | `[True, True, True]` | OK |
| ×4.0 | **−39320** | −22936 | −7864 | `[False, True, True]` | 🛑 **OVERFLOW by 6,552** |

`k_max = 32768 / 9830 = 3.33347`, binding element **`Y[0] = −9830` against int16 MIN −32768** (the row is
negative — the floor binds, not the ceiling). All four working multipliers round exactly.

```
MODE 26  rec 0xD7A54   WRITE 0xD7A5C..0xD7A61  = 6 BYTES (Y only)
MODE 27  rec 0xD7A64   WRITE 0xD7A6C..0xD7A71  = 6 BYTES (Y only)
TOTAL 12 BYTES.  Both in [0xD7000,0xD7FFC) -> ONE trailer 0xD7FFC.
Mode 24's record 0xD6A64 is in the 0xD6000 block and is NOT touched.
```
✅ **X UNTOUCHED, asserted as a boolean, not assumed:** write span `[0xD7A5C,0xD7A61]` vs X span
`[0xD7A56,0xD7A5B]` → disjoint = `True`; same for mode 27 → `True`.
⚠ **Mode 25's record `0xD7A44` is exactly `0x10` BELOW mode 26's** — a −0x10 slip lands on a *disengaged*
column and looks plausible. **Assert mode 25 byte-identical too.**

## 🛑 U2b — THE SAME ROUTE-77 NUMBER FORCES THE DOSE. **×1.5 IS THE ONLY CLIP-FREE OPTION.**

`gp-0x6b26 = clamp(lerp(speed,X,Y) · gate(gp-0x6c2c), ±511)` — **the Y row is scaled BEFORE the ±511
clamp**, so raising Y pushes the peaks into the rail. Route 77 measured the lane at stock with
**clamp duty 0.000000 over 62,180 unsaturated samples**, engaged max **319.1 ct**:

| k | peak would reach | vs the 511-ct rail | verdict |
|---|---|---|---|
| **×1.5** | **478.7 ct** | **6.3 % margin** | ✅ **CLIP-FREE** |
| ×1.6 | 510.6 ct | 0.1 % | ✅ clip-free, no margin |
| ×2.0 | 638.2 ct | — | 🛑 **CLIPS — RELAY HAZARD** |
| ×2.5 | 797.8 | — | 🛑 CLIPS |
| ×3.0 | 957.3 | — | 🛑 CLIPS |

> 🛑🛑 **RULE 8, RUN BOTH WAYS, AND THEY DISAGREE BY 2.08×.**
> - **int16 overflow — the cheap static bound: `k < 3.33`.**
> - **Observed-envelope clip check — the claim that matters: `k < 1.60`.**
> **The envelope bound binds first, and it is the one to quote.** Reporting ×3.0 as "the largest
> multiplier with 10 % headroom" would be quoting the convenient number — that headroom is *int16*
> headroom, a different constraint entirely.

🛑 **WHY CLIPPING IS DISQUALIFYING HERE, not merely lossy.** `gp-0x6b26 = −k · gp-0x6c2c`: its **sign
comes from `gp-0x6c2c`** and, at the rail, **its magnitude is a constant 511**. That is
*sign(velocity-derivative) × constant* — **literally the Coulomb relay this kit forbids**, and it is the
V80 mechanism verbatim: *"a railed factor whose sign comes from a different cell than its index IS the
Coulomb relay"*, delivered on-car as **the worst grinding in this car's history**. A dose that clips
does not merely lose the peaks — **it converts a damper into the exact thing we are trying to remove.**

⇒ **RECOMMENDED DOSE: ×1.5, and it is not a free choice — it is the only dose the measured envelope
permits.** ⊕ It converges with U3: ×1.5 is also exactly the dose that flew twice. **So V91 is precisely
"the same lever, the same dose, the interlock corrected" — and the sizing now forces that independently
of the lineage.**
⚠ **The 6.3 % margin rests on ONE route's maximum.** RULE 8b: state what the envelope does *not*
contain. Route 77 has 437.6 s in the micro regime; it does not bound emergency manoeuvres, kerb strikes,
or the launch transient that faulted V75. **A single peak 7 % above route 77's maximum clips at ×1.5.**

## 🛑 U2c — AND THE HONEST SIZE OF WHAT ×1.5 BUYS

| k | Δ`gp-0x6b98` @ micro p50 | as % of the 208-ct engaged median | @ p99 |
|---|---|---|---|
| **×1.5** | **3.8 ct** | **1.8 %** | 51.5 ct (24.8 %) |
| ×2.0 *(clips)* | 7.6 | 3.6 % | 103 (49.6 %) |
| ×3.0 *(clips)* | 15.1 | 7.3 % | 206 (99.1 %) |

**At the only permitted dose, the delivered effect in the regime where the operator names the symptom is
1.8 % of the median command — well below the kit's own resolvability floor** (V89's placebo band is
**11 %** wide). ⇒ **If ×1.5 works, the operator will feel it before the instrument can see it; and if it
does not, the null will be UNINTERPRETABLE — underpowered by construction, not informative.** That is
coherent under the FIV/threshold account (§2a: below threshold nothing visible happens, above it the
vibration is quenched entirely) — **but it must be pre-registered as a threshold bet with an
operator-scored primary endpoint, not as a band-ratio experiment.**

★ **ONE CHEAP CUT WOULD TURN THIS FROM A GUESS INTO A SIZED DOSE, and it needs no new driving.**
The broadband p50 is the wrong statistic for a damper: what damps a resonance is the term's component
**at the mode frequency**. **Compute the 6–9 Hz band-limited rms of `gp-0x6b26` over the micro-regime
engaged windows of route 77** — the 427 stream is already on disk. If that rms is near the p50 (~7 ct)
the dose is hopeless; if it is nearer p99 (~97 ct) it is real. `HANDOFF-2026-08-10` §4a records **both
sizing inputs as struck** — **this un-strikes one of them for the cost of one FFT.**

## U3 — THE LINEAGE PARAGRAPH, RE-VERIFIED FROM DISK

**mode 26 Y non-stock on 8 of 94 artefacts. mode 24 non-stock on ZERO.**
🛑 **`0xC407E` across all 8 is the single-element set `{850}`.**

| artefact | m24 | m26 | `0xC407E` | flew | on-car |
|---|---|---|---|---|---|
| `_v74_engagedcols_x0_12_addonly` | stock | ×1.50 | **850** | ✅ | 🛑 **HARD FAULT, latched loss of assist** (MANUAL) |
| `_v75_CY0.566-EX1.200_magprobe` | stock | ×1.50 | **850** | ✅ | 🛑 **HARD FAULT, latched** (ENGAGED) |
| `_v75_CY0.566_magprobe` | stock | ×1.50 | 850 | ❌ | twin |
| `_v76_gate_fb_arm5244_gateprobe` | stock | ×1.50 | 850 | ❌ | never flew |
| `_v77_C63A0.1024_v74base` | stock | ×1.50 | 850 | ❌ | never flew |
| `_v77b_C63A0.1024_v75base` | stock | ×1.50 | 850 | ❌ | never flew |
| 2 × `SUPERSEDED-…_v74_…` | stock | ×1.50 | 850 | ❌ | never flew |

> ### For the operator, unsoftened
> **This row has flown live exactly twice, and both flights hard-faulted with a latched total loss of
> power steering.** It is **not a new lever**: it is **the same lever, at the same ×1.5 dose, with one
> cell different.** Every artefact that has ever carried this dose also carried `0xC407E` = **850**;
> V91 carries Honda's **511**, where the friction lane is clamped one count below the DTC-0x1d monitor's
> own 512 trip, so that monitor cannot fire at any multiplier.

🛑 **What that paragraph must not hide** (unchanged from Addendum 2, and it still stands):
**(1)** the `{850}` set is a *single element* — **no flight has ever tested this dose at a stock
interlock**, so the separation is purely structural, never empirical; **(2)** "untrippable by magnitude"
is exactly the claim RULE 8b calls structurally blind — V75's fault is pinned to **one 100 Hz frame**, a
fast transient, and RULE 11 marks *"850 caused BOTH faults"* as **BELIEF, DTC number never confirmed
on-car**; **(3)** §4a's own authors struck this lane as the *mechanism* (`gp-0x6c2c` is
acceleration-like ⇒ scales with rate; the corpus says the amplification is rate-independent) —
*"defensible as a damper, not as the mechanism."*
⊕ **Genuinely better this time:** V81 flew `0xC407E` 850→511 on a V75 base, route 67, **fault-free** —
the clamp revert has a clean flight behind it. The clamp revert *plus this dose* does not.
⚠ Writing only modes 26/27 is **narrower than V74/V75's 14 records**; correct and conservative for this
car, but call it a deliberate narrowing.

---

---

# ADDENDUM 4 — V81 CONFIRMED AS THE POSITIVE CONTROL, **AND A CORRECTION TO MY OWN BUILDER ASSERTION**

## The answer: **V81 IS byte-stock on the friction row. The positive control is exact, not approximate.**

**[EVIDENCE]** `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` — **one artefact only**, no collision.
sha256 `4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b`.

| mode | record | Y addr | stock | **V81** | 16-byte record identical |
|---|---|---|---|---|---|
| 24 | `0xD6A64` | `0xD6A6C` | `[−9830,−5734,−1966]` | **same** | ✅ `True` |
| 25 | `0xD7A44` | `0xD7A4C` | `[−9830,−5734,−1966]` | **same** | ✅ `True` |
| **26** | `0xD7A54` | `0xD7A5C` | `[−9830,−5734,−1966]` | **same** | ✅ `True` |
| 27 | `0xD7A64` | `0xD7A6C` | `[−9830,−5734,−1966]` | **same** | ✅ `True` |

**Across all 34 friction records: ZERO differ from stock.** And `0xC407E` = **511**, `0xC63A0` = 2048.

⇒ **The positive control can be stated exactly:** *V81 flew route 67 fault-free carrying the corrected
interlock (`0xC407E` = 511) and Honda's friction row, byte-for-byte, in every mode.* ⇒ **it isolates the
clamp revert cleanly — and it therefore says nothing whatever about the dose**, which is the point: it is
a control *for the interlock*, not for the lever.

## 🛑 CORRECTION TO MY OWN U2 ASSERTION LIST — "walk to exhaustion" IS NOT WELL-DEFINED. BOUND IT TO 34.

I told you the builder should *"walk the pointer array to exhaustion, asserting every untouched mode
byte-identical."* **That instruction is wrong as written and I am correcting it before it is
implemented.** My own loop, terminating on "pointer out of range or `n` implausible", ran to **mode 289**
and reported V81 differing at modes **68** and **126** — which would have looked like an unexplained
friction edit on the positive control.

**Neither is a friction record.** The friction pointer array is **34 slots (modes 0–33)**, per
`BUILD-LINEAGE.md` ledger correction #5 (*"340 slots = 10 arrays × 34 modes"*). The next array,
`gain_B[0]`, begins **58 slots later at `0xCBF5C`** — so slots 34–57 are unowned filler and everything
past that is a **different table** whose pointers and records are perfectly valid-looking:

```
0xCBE74 + 34*4 = 0xCBEFC   <- first slot PAST the friction array
"mode 68"  -> 0xCBF84 = gain_B[array 0] mode 10
"mode 126" -> 0xCC06C = gain_B[array 1] mode 10      <- V69/V70's known lever, inherited via V81's V75 base
```

**Properly bounded to modes 0–33, V81 differs from stock on ZERO friction records.**

> 📋 **THE RULE, CORRECTED — and it is the same trap as my `range(32)` error wearing the opposite face.**
> `range(32)` **under**-walked and hid two real modes. "Walk until it stops looking valid" **over**-walked
> and invented two fake ones. **Neither a guessed bound nor a sanity heuristic is a bound.**
> ⇒ **An array's extent must come from its own structure or from a recorded census — here, 34 — and the
> assertion must name it.** The builder assertion should read: **`for m in range(34)`, every mode except
> 26 and 27 byte-identical to base**, plus a separate guard that `0xCBE74 + 34*4 = 0xCBEFC` is not
> written. **Adjacent pointer arrays are not a fence; they are camouflage.**

---

## OPEN ITEMS I AM HANDING BACK (reports, not fixes)

1. **The one Ghidra query in D2c** — `gp-0x6b26`'s consumers. It decides whether `0xC63A6` is a lever
   or a repeat of V89.
2. **The `0xCBE74` "13 engaged modes" count is wrong in two documents** (`HANDOFF-2026-08-10` §4,
   `BUILD-LINEAGE.md` RULE 11). Images say **12**, set `{2,3,5,10,11,14,15,17,23,26,27,29}`, which
   includes mode 10 and excludes mode 24. **Not edited — reported.**
3. **`0xC644A`'s V43 dose is 32 in the image**, not the 64 recorded in `memory/builds/v43-dirty-derivative-pole-built.md`.
4. **V56's mute cells are `0x8000` = −32768 on stock**, which does not read like a gain. Before anyone
   acts on the "raise the muted lane" idea in D2b, that arithmetic needs tracing.
