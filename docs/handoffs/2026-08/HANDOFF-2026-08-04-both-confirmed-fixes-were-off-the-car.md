# HANDOFF 2026-08-04 — BOTH OF THE KIT'S CONFIRMED FIXES WERE OFF THE CAR, AND THE DOSE AXIS WAS THE WRONG LANE

**Predecessors:** `docs/handoffs/2026-08/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md` (route `4f`, the ×4 dose,
the non-monotone ladder) → `docs/handoffs/2026-08/HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md` →
`docs/handoffs/2026-08/HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md` →
`docs/handoffs/2026-08/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`. Read the V69-flew handoff for the dose
ladder this session re-prices; read this one for **why the ladder was mispriced in the first place**.

**V70 flew route `75604b0a432fdc89_00000050--50f2e00e8f`** (segments 0–2, **181.6 s**, 18,010 frames on
the 100 Hz grid). **FLIGHT-CLEAN:** `ST == 4` **0** and `ST == 3` **0**, on the gridded cache *and* on
the raw un-gridded `0x18F` stream; watchlist absent (`steerUnavailable` / `canError` /
`controlsMismatch` / `immediateDisable` all 0). **The zero-EME streak extends.**
⚠ **Route 50 is a SMALL route and the exposure census matters more than usual:** engaged **72.4 s**,
manual **107.8 s**, **engaged creep 28.9 s**, **highway ≥ 50 km/h 7.9 s**, and **zero manual highway
exposure at all**. **Segment 0 is PARKED — it is boot only.** Every null below is read against that
census, not against `4f`'s 481.7 s.

🛑 **Every decision-bearing claim below is marked [EVIDENCE] or [BELIEF].** Where the wording says
*"not established"*, *"under-powered"*, *"one episode"*, *"lower bound"* or *"[OPEN]"*, that wording is
load-bearing. Do not upgrade it in the next session's summary.

---

## 1. 🛑🛑 THE HEADLINE: THE CAR WAS MISSING BOTH OF ITS CONFIRMED FIXES

**[EVIDENCE — byte-read across all 60 `_v*_plain_image.bin` in `../accord-firmwares/analysis-2020accord/`.]**

| lever | what it did | recorded as | actually carried by | how it was lost |
|---|---|---|---|---|
| **`0x454FE`** `65BA` (`bne`) → `65B5` (`br`) | V42's **state-4 governor ratchet** kill | *"CONFIRMED ROOT CAUSE, carry forward"* | **V42–V52C only**; **stock in V53 → V70** | 🛑 **silent rebase loss** — V53+ descends from the V38/FOURFRAME branch point, which is *before* V42. **Nobody decided this.** |
| **`0x3AB76` + `0x3AC20`** `sar 0xa` → `0x9` | V62's **×2 on BOTH rate lanes** — the kit's only measured grind-#1 fix (8× at creep, 42× at \|rate\| 16–32) | the reference "2×" rung of the dose ladder | **V62 and V65 only** | ⚠ removed as **V66's confirmatory control**, and **never restored**. The effect was then re-created twice in encodings that dose **r24 only**, and the ladder kept calling those "2×" |

⇒ **From V66 to V70 the car carried NEITHER.** Ten builds of reasoning ran against a record that read as
though both were on the car.

**The `0x454FE` case is worse than bookkeeping.** The argument that later retired it as a cause of the
*current* ratchet — *"`STEER_STATUS == 4` fires 0/37,922"* — was **voided** when bus `STEER_STATUS` was
shown not to be `gp-0x67fa` (state 4 sits inside all three of the gate masks). **It was never actually
eliminated; it was mis-eliminated and then mis-recorded as absent-because-unnecessary.**

**The `0x3AB76`/`0x3AC20` case is the more dangerous general form:** a lever removed *on purpose* as an
experimental control is, six builds later, **indistinguishable from a lever that was never needed.**

⇒ **`RULE 3` is now at the top of `docs/BUILD-LINEAGE.md`:** *for every lever you cite, byte-check
whether the CURRENT build's plain image still carries it before reasoning from its result.* And: **when
you remove a confirmed fix to run a control, write the restore into the next build's spec.**

---

## 2. ★★★★ THE STRUCTURAL FINDING: THE DOSE AXIS THIS KIT HAS USED SINCE V62 IS THE WRONG LANE

### 2.0 🛑 There IS a clean single-variable r24 series, and it says r24 is NEAR-INERT

**[EVIDENCE — medians recomputed from `_grind2_lib.wrecs`, not quoted from the record.]**
**stock → V70 → V69 is a pure r24 dose series with r26 held at ×1:**

| build | r24 | r26 | median `e_18-22` (engaged creep) |
|---|---|---|---|
| stock | **×1** | ×1 | **879** |
| **V70** | **×2** | ×1 | **729** |
| **V69** | **×4** | ×1 | **746** |

**All three CIs mutually overlapping** ⇒ 🛑 **r24 is close to INERT for grind #1 across a 4:1 dose
range.** And across the whole corpus: **every build that FIXED grind #1 changed r26** (V62 ×2;
V67/V68 ÷6.00), and **every build that changed only r24 did not.**

⇒ **The headline is NOT "nothing is single-variable."** It is: **the dose axis this kit has used since
V62 is the wrong lane.** Everything in §2.1 below explains *why that was invisible* until now.

### 2.1 The structure — two selectors, one gate

**[EVIDENCE — orchestrator-disassembled, both selectors read out of the image.]** r24 and r26 have
**separate gain selectors** that share **one** gate `lp`:

**`r26 → gain_A`**
```
0x3AB5E  ld.hu 0x7444[tp],r8     ; 0xC6444 = 512, taken when lp != 0
0x3AB68  ...                      ; 0xC643E
else                              ; gain_A's own LERP — 3072 at creep
```

**`r24 → gain_B`**
```
0x3ABFE  0xC6442 = 1024           ; the gp-0x671d mask arm — OUTRANKS ALL
0x3AC08  0xC6446                  ; taken when lp != 0
0x3AC12  0xC6440 = 2048
else                              ; the mode-10 speed×rate surface
```

⇒ **V67/V68's one-byte gate repoint at `0x3AA96` raises r24 AND cuts r26 6.00× at the same time.**
Net delivered vs stock is a function of `a = gp-0x69a4 / 1024`:

| `a` | net vs stock = `(5244 + 512·a) / (3072 + 3072·a)` |
|---|---|
| 0 | **1.707×** |
| 0.848 | **1.000× — PARITY** |
| > 0.848 | **BELOW stock** |

**V69 and V70 edited gain_B only.** ⇒ **every published multiplier in this kit is an r24-only number
computed at `a = 0` — a number on the lane §2.0 shows to be near-inert.**

★ **Four supporting byte facts, all [EVIDENCE]:**
1. **gain_A's four records `0xC6A68` / `0xC6A7C` / `0xC6A90` / `0xC6AA4` are BYTE-IDENTICAL across all
   11 images** ⇒ **V67/V68's ÷6.00 (= 512/3072) is EXACT, and engaged-only.**
2. **The two LERPs live in separate RAM** — `gp-0x6e40`/`gp-0x6e38` for gain_B, `gp-0x6e30`/`gp-0x6e28`
   for gain_A — filled by the **two halves of `FUN_0003ad74`**.
3. **gain_B is filled from the MODE-INDEXED arrays; gain_A from FIXED, non-mode-indexed records.**
   That is why V69/V70's mode-10 surface edit could not reach r26 **even in principle**.
4. **There is NO `gp-0x671d` mask arm on the r26 side** — gain_A is **2 arms + default**, not 3.

### 🛑 r26 IS LIVE — existence proof [EVIDENCE]

V70's probe read `gp-0x6adc` (r26's post-clamp mirror) **strictly negative on 1,644 of 18,010 frames**.
**A pinned-zero cell cannot clear a `>= 0` test.** ⇒ **"r26 is inert / r24 carries the lane" is
REFUTED on-car**, not merely downgraded. See §7.1 for what that retires.

★ **A new asymmetry worth recording [EVIDENCE]: `bit3 ⇒ bit4` STRICTLY** — **0 of 18,010** frames had
r24 ≥ 0 while r26 < 0. **[BELIEF]** the natural reading is *"r26 is ZERO part of the time, and
same-signed with r24 otherwise"* — consistent with the shared polarity load (`ld.b -0x6752[gp],r14`
@`0x3AB78`, reused at `0x3AB7E` for r26 and `0x3AC3E` for r24).

### ⚠⚠ CARRY THIS UNEXPLAINED — do not smooth it

**r26 ×2 (V62/V65) AND r26 ÷6.00 (V67/V68) BOTH HELPED, and ÷6 helped MORE** — median 168 vs 109
against stock's 879. **A monotone "more r26 damping is better" story and a monotone "less is better"
story are both refuted by the same two rows. The corpus cannot say why, and that is the leading open
question of this session.**
🛑 **Anyone proposing an r26 dose must state which direction they are betting on and why** — the record
does not supply it.

★ **Independent bus-side support for the r26 attribution, arrived at without the disassembly
[EVIDENCE]:** median `e_18-22` by **bar-torque reversal count**, engaged creep — in the **rev ≥ 40**
regime (where the ratchet lives), **V62 reads 396 against 1155–1403 for V59 / V64 / V69 / V70.**
**V62 is the odd one out, and it is the only build with r26 ×2.**

### ✅ V62's `sar` route is the ONLY dose-exact encoding

`0x3AB76`/`0x3AC20` scale **both** lanes identically, so **2.000× on the total for every value of `a`.**
Every other encoding in the kit's ladder is `a`-dependent. That property is why V71 restores this route
rather than re-deriving the dose through a cal arm.
★★ **And it tells you which half of V71 is load-bearing: `0x3AB76` — the r26 `sar` — IS THE LEVER.**
`0x3AC20` (the r24 `sar`) is restored **for exact V62 parity, NOT because r24's dose is expected to
matter.** Write it that way, so a null on r24 is not later read as a null on the build.

### The ladder, re-read against what each build actually carried

Median `e_18-22`, engaged creep:

| build | r24 | r26 | median `e_18-22` |
|---|---|---|---|
| V61 | ×0 | ×0 | **2501** |
| stock | ×1 | ×1 | **879** |
| **V70** | ×2 | ×1 | **729** |
| **V69** | ×4 | ×1 | **746** |
| **V62 / V65** | **×2** | **×2** | **168** |
| **V67 / V68** | gated (arm) | **÷6** | **109** |

⇒ **r24's dose is FLAT from ×1 through ×4 (879 / 729 / 746 — §2.0), and both builds that fixed grind #1
changed r26.** [EVIDENCE] is the **flatness of the r24 rung** and the **co-occurrence**; ⚠ the
**direction** of the r26 effect is **not** established — see the unexplained ×2-and-÷6 result above.

---

## 3. ROUTE 50 — WHAT THE CAR SAID

### 3.1 🛑 GRIND #1 IS BACK AT THE STOCK LEVEL [EVIDENCE]

Median `e_18-22`, engaged creep: **729.1**. Resampling **V70's exact 5-block structure** from each arm:

| arm | verdict |
|---|---|
| stock | **CONSISTENT** (P = 0.635) |
| V69 | **CONSISTENT** (P = 0.495) |
| **V62 / V65** | **EXCLUDED** (P = 0.0000) |
| **V67 / V68** | **EXCLUDED** (P = 0.0000) |

Survives **(effort, |rate|)-matching**.

⚠ **Two honest caveats, both of which must travel with the number.**
1. **The 24–28 Hz negative control is NOT flat** — V70 reads **1.88× stock** there, because provoked
   steering raises the whole floor. Subject-band **excess over control** vs V62 is still **2.59×**, so
   the exclusion survives; but the raw ratio is inflated by a floor shift.
2. **On the scale-free 18-22 / 24-28 ratio, V70 (37.4) sits BELOW stock (76.0).** 🛑 **That view does not
   rank-order the builds the way `e_18-22` does.** **Report both; pick neither.** The two views
   disagreeing is itself the finding.

★★ **A METHODOLOGICAL CORRECTION WORTH ITS OWN LINE: CI OVERLAP IS NOT A TEST.** The
subsample-at-matched-exposure test above (resample V70's exact 5-block structure from each arm)
**excludes V62's level at P < 5 × 10⁻⁵**, where a CI comparison called the same contrast undecided.
⇒ **"V70 is not at V62's level" IS ESTABLISHED. Where V70 sits BETWEEN stock and V62 is NOT.** Both
halves of that sentence are load-bearing; quote them together.

🛑 **AND GRIND #1 IS BLIND TO r24 GAIN — this retires a MEASUREMENT TOOL, not just a hypothesis.**
Log-log slope of median `e_18-22` on r24 gain: **−0.144 [−0.991, +0.347]** — contains 0; stock / V70 /
V69 pairwise **indistinguishable** (P = 0.667 / 0.610 / 0.426). ⇒ **grind #1 cannot be used as an
in-force check for the r24 lane on ANY future build.** **Structural**, not a power limit — more exposure
will not fix it. ⊕ It also means **grind #1 cannot adjudicate the bit6 (a)-vs-(b) question** (§4.1), so
the bit6 zero carries that diagnostic load alone and is in tension with nothing.

### 3.2 GRIND #2 — not a regression, but "gone" is NOT established [EVIDENCE + power]

**0 bursts everywhere**, max **94.6** vs V62/V65's **1830.7**. But at V62's own burst rate:

| cell | P(0) | power |
|---|---|---|
| engaged creep | **0.34** | 66% |
| corner | **0.56** | 44% |
| highway | **0.98** | **2%** |

⇒ **the highway cell says nothing at all.** And **V67 already eliminated engaged-creep grind #2**
(P(0) = 0.0005), so a clean V70 creep arm **REPLICATES an already-clean arm — it does not credit V70.**
🛑 Do not write this up as "V70 fixed grind #2".

### 3.3 ★★★★ THE RATCHET — ENGAGEMENT-**REQUIRED**, Q ≈ 40, AND NO BUILD HAS EVER MOVED IT

#### 3.3.1 🛑 Engagement-**REQUIRED**, not engagement-conditional — the grip confound is removed

**[EVIDENCE]** Both arms **hands-off** (`|lowpass(tq, 3 Hz)| ≤ 300`), **creep < 4 m/s**, pooled over
**four routes and four builds**:

| route | engaged hands-off | manual hands-off | Fisher p |
|---|---|---|---|
| V70 `r50` | 4/5 = **80%** | 0/35 = **0%** | 5.5 × 10⁻⁵ |
| V69 `r4f` | 22/27 = **81%** | 0/20 = **0%** | 9.4 × 10⁻⁹ |
| V62 `r37` | 31/39 = **79%** | 0/39 = **0%** | 2.3 × 10⁻¹⁴ |
| V59 `r2c` | 16/17 = **94%** | 0/24 = **0%** | 1.7 × 10⁻¹⁰ |
| **POOLED** | **73/88 = 83.0%** | **0/118 = 0.0%** | **3.8 × 10⁻⁴¹** |

**ZERO hits in 118 manual hands-off creep windows / 302 s across four builds.**
⇒ 🛑🛑 **the rate is BUILD-INDEPENDENT (80 / 81 / 79 / 94%) — NO BUILD IN THIS KIT HAS EVER MOVED THE
RATCHET.** ⚠ **This SUPERSEDES the earlier "engagement-conditional, 44/46 windows" statement** — same
phenomenon, far better-controlled data, far stronger claim.
★ **Converse: a hand on the wheel SUPPRESSES it while engaged** — V59 94% → 14% (p = 3.5 × 10⁻⁴),
V69 81% → 37% (p = 4.5 × 10⁻³).

#### 3.3.2 ★★★★ The transition trace — the mechanism, second by second, at constant speed

**[EVIDENCE — 4th-order Butterworth 6–9 Hz, `sosfiltfilt`, 2.56 s windows, hop 64; seg-local `t`,
mono = t + 100.6; orchestrator-verified from `_scratch/cache/r50/r50s1.npz`.]**

| seg1 `t` | mono | `lat` | effort | **RAW p-p** | **6–9 Hz p-p** |
|---|---|---|---|---|---|
| 27.5 | 128.1 | 0.00 | 2646 | **6502** | **190** |
| 28.2 | 128.8 | 0.00 | 2235 | **6502** | 255 |
| 33.3 | 133.9 | 0.00 | 942 | 3237 | 136 |
| **33.9** | **134.5** | **0.06** | **320** | 1423 | **134** |
| **34.6** | **135.2** | **0.31** | **441** | 3182 | **1179** |
| 35.2 | 135.8 | 0.56 | 645 | 4039 | 2156 |
| 36.5 | 137.1 | 1.00 | 998 | 5070 | **2452** |
| 46.1 | 146.7 | 1.00 | 1548 | 4204 | 910 |
| 46.7 | 147.3 | 1.00 | 2129 | 3019 | **273** |

★★ **The headline pair — use this one.** `t = 33.9` (`lat` 0.06, effort 320) → **134 counts**;
`t = 34.6` (`lat` 0.31, effort 441) → **1,179 counts**. **8.8× in 0.7 s**, with **speed FALLING
(1.75 → 1.60 m/s)** and effort roughly flat — **speed moves the wrong way for any confound.**
**The death is as sharp:** effort **1,548 → 2,129** over **0.6 s** collapses the band **910 → 273**.
⇒ **it comes on tracking `latActive` and goes off when the driver grips.**

✅ **THE 6,502-vs-591 INSTRUMENT DISCREPANCY IS SETTLED, NOT OPEN.** At mono 127.5–128.1 the car is at
`lat = 0.00`, effort **2,550–2,646**, speed 0.6–0.8 m/s, and the **6–9 Hz content is 190 counts**.
⇒ **the 6,502 peak is RAW BROADBAND — the operator cranking the wheel, not the ratchet.**
★ **The ratchet proper runs seg1 `t` ≈ 34.6 → 46.1 (mono 135.2 → 146.7), ~11.5 s.** 🛑 **Burst #0's
ratchet onset is mono ≈ 135.2 — NOT 123.69.** That is the clean-material window.

#### 3.3.3 🛑 A correction to the operator's framing — the causal order, not the facts

**His hard MANUAL provocation produced NO ratchet at all** (effort 2,500–2,900; 6–9 Hz p-p only
**422–797**, prominence **1–6**). **The manoeuvres SET UP the condition** — creep, loaded wheel, LKAS
about to take over — **and the ratchet fires when LKAS ENGAGES AND HE LETS GO.**
★ **Both parts of his account are correct; the causal order is the other way round. His report is
corroborated, not contradicted** — he identified the setup and the event, and named the right segments
before the data did.

#### 3.3.4 ★★★ Q ≈ 40 at f0 = 7.793 Hz [EVIDENCE] — and measured on the RIGHT data

From a **12.81 s provoked episode**. **The invariance test is what makes it real:** Q reads **39.0 with
a window cap of 54** and **40.0 with a cap of 111**. A window-limited estimate would have **doubled**
when the cap doubled. It did not. ⇒ **ζ ≈ 0.0125 — about 3× more lightly damped than the 21 Hz mode.**

✅ **Q ≈ 40 CONFIRMS the record's Q ≈ 36.** 🛑 **The only thing SUPERSEDED is *"Q is not measurable at
NFFT 256"* — the claim that it could not be measured, not the value.**
✅ **And it is not contaminated by the driver's input** — the episode reconciles exactly with §3.3.2
(envelope-based p-p, 2 × 2,452 = 4,904 ≈ 4,894; speed span matches `t` ≈ 33–46, the **post-engagement**
window, not the cranking). **That was the one real risk in the discrepancy, and it is closed.**
⚠ **It rests on ONE episode.** A second ≥ 10 s episode would make it two. And **f0 drift inside the
window would DEFLATE Q**, so **40 is a lower bound**, not a point estimate.

Everything else on the ratchet from route 50, all [EVIDENCE]:
- **10 windows / 25.6 s at ≥ 1200 counts p-p, max 4,894.** Zero-crossing f0 **7.75 Hz**.
- **Speed-invariant:** Theil-Sen slope **+0.068 [+0.005, +0.247]** Hz per m/s, against wheel-order-1's
  **0.482**. (The CI excludes 0 but is an order of magnitude below an order line.)
- **Where the line lives:** bar (prominence **59**), angle-rate (**22**), angle (**15**), and **NOT in
  openpilot's command (1.25)** ⇒ **the loop closes inside the EPS + plant.** This replicates `4f`.
- **Per-engaged-window ratchet rate is identical across builds: V70 32.1%, V69 34.4%, V62 32.8%**
  ⇒ **V70 did not add ratchet events**, consistent with §3.3.1's build-independence.

#### 3.3.5 ⇒ What the build-independence buys

★★ **`0x454FE` is a genuinely UNTESTED lever for the ratchet** — it has **not been on the car during a
single one of the four measurements in §3.3.1** (V59, V62, V69, V70 are all post-V53, all stock at
`0x454FE`). ⚠ **That is a reason it is worth restoring; it is NOT evidence that it will work**, and §5's
symmetry tension still argues against the mechanism.
★★ **And four facts now fit one picture:** *engagement-required* + *hands-off-conditional* + *Q ≈ 40* +
*base-assist damping exactly ZERO below ~35 km/h* ⇒ **at creep, the driver's hand is the only damping in
the system.** That is what makes §8's deferred FactorC/FactorE lever materially more compelling.

### 3.4 "STIFFER" — not detected by any bus-side instrument, and the proposed mechanism is REFUTED

**[EVIDENCE — arithmetic.]** The orchestrator's pre-drive story was *"V69 ran just under saturation, so
V70 feels stiffer."* **The clamp at `0x3AC42` is HARD** (`clamp(., ±0x2000)`), **exactly linear below the
rail**, and **V69 spent 0.0000% of engaged time at or above its 683 rail** (max **633.9**).
⇒ **there is no compression difference to feel. REFUTED.**

Bus-side effort/impedance puts V70 at **0.79–0.97×** every predecessor, **every CI containing 1**.

**[BELIEF]** The likeliest referent for "stiffer" is **the ratchet itself** — **4,894 counts at Q ≈ 40**
arriving **0.8 s after engagement**. That is a large, lightly-damped, engagement-locked event, and it is
exactly what the operator described. It is a belief because no instrument separates "stiffer steering"
from "a big ratchet event early in the drive."

---

## 4. THE PROBE READOUTS

### 4.1 🛑🛑 bit6 READ ZERO — 0/18,010 — AND IT IS NOT VACUOUS [EVIDENCE]

bit6 = `gp-0x6ada >= +512` (r24's post-clamp lane output).

**A replay through the shipped surface, driven by route 50's OWN data, predicts 311 hits. Stock predicts
52.** Observed: **0**. And `|dtorque|` computed off a 100 Hz grid is a **LOWER bound**, so the true
excursions are larger — **the gap cannot be closed by measurement error in the safe direction.**

⇒ **delivered gain < ~1574 Q10, below stock's 3072.** ⇒ **`0xC6442` = 1024 — the `gp-0x671d` mask arm —
is the only arm in the selector that predicts exactly 0.**

✅ **The identification is NOT the problem.** The orchestrator verified first-hand that
`0x3AC42`–`0x3AC54` is `r24 = clamp(r6, ±0x2000)` and that `0x3AD5A st.h r24,-0x6ada,gp` stores exactly
that, with r24 unclobbered through the add chain.

⚠⚠ **BUT THE ARM-SELECTION READING IS THE WEAKER ONE — SOFTENED, and this matters.** **The same rung
read 0 / 47,990 frames on V69's route `4f`, at DOUBLE V70's dose**, where it needed only **49 counts**
of `|dtorque|` against a repo max of **839**. **That anomaly is far larger than V70's, and it does NOT
fit arm selection**: under (b) the mask arm is **1024 on every build**, so it cannot produce a
**dose-dependent** miss. And **V67's probe read `gp-0x671d` 0 / 150,327 on route 47**, so the mask would
have to be set near-continuously on `4f` *and* `50` but never on `47`.
⇒ **[BELIEF] (a) — an under-ranged or MIS-RECONSTRUCTED rung — is the better-supported reading.** The
`dtorque` figure is a **4-sample 1 kHz difference rebuilt from a 100 Hz bus copy of a different,
filtered torque cell**; polarity is the other candidate. **(b) arm selection is possible but less
parsimonious. The corpus cannot settle it** — and per §3.1, grind #1 cannot adjudicate it either.

🛑 **THE DURABLE PART IS THE LESSON, NOT THE MECHANISM: this is the FOURTH probe in a row to return an
uninterpretable zero by reading a lane OUTPUT.** ⇒ **read the GAIN IN FORCE, not a lane output.**
✅ **V71 answers it both ways** — `gp-0x671d` **directly** (bit6), plus a **two-sided, low-threshold**
r24 mirror rung so an under-ranged reconstruction cannot hide again.

### 4.2 ★★ bit5 = `gp-0x67fa == 10` READ **0.0000%** [EVIDENCE] — five builds vindicated

Encoding independently verified from the image bytes. ⇒ **the aggregator ran** ⇒ **state ∈ {4, 5, 11}**
⇒ **`FUN_00036388` and `FUN_000428d4` WERE INVOKED.**

⇒ 🛑 **the `gp-0x67df` detector nulls on V64 / V67 / V68 are GENUINE, and the state-gate explanation for
them is REFUTED.** The pre-registered prediction (*"bit5 reads LOW"*) held, which is what makes this
interpretable rather than a lucky null.

⚠ **It licenses "the call was made", NOT "the body ran."** `FUN_00046ea6(5)` on `gp-0x18d0` bit 5 —
the detector's **second, independent** entry gate — **remains OPEN.**

### 4.3 bit4 / bit3 — the r26 pair

See §2. **bit4 tracked bit3** ⇒ **r26 is LIVE.** `bit3 ⇒ bit4` holds **strictly** (0/18,010 violations).

---

## 5. THE STATE MACHINE — THE CADENCE IS REFUTED AT INSTRUCTION LEVEL

**[EVIDENCE — instruction level, both gp-relative and absolute encodings checked.]**

**`gp-0x68ad` can NEVER be set in the field.** Both SET paths require permanently-zero flags:
- `gp-0x437c` — a UDS artifact.
- `gp-0x679d` — **newly closed this session.** Its sole writer `FUN_000567c0` @`0x567e2` reads
  `gp-0x67ba`, and `gp-0x67ba` has **exactly one access image-wide and ZERO writers.**

`FUN_00019970` opens with `if (gp-0x68ad != 1) return;` ⇒ **4 → 5 NEVER FIRES. State 5 is dead code on
the road.**

**`gp-0x6d78` bit 15 is a ONE-WAY, OR-ONLY latch** — 15 sites, one writer (`FUN_000197b8` @`0x197ca`,
`|= 1 << n`), **no clear anywhere image-wide.** ⇒ **4 → 10 is a ONE-SHOT DRIFT; 10 → 4 can never fire
afterwards.**

⇒ 🛑 **State 4 is STICKY once entered, and then leaves permanently. There is NO periodic cadence** —
**refuted structurally, not merely unconfirmed.** Combined with bit5's 0.0000%, **the reachable set on a
normal drive is {4, 11}.**

⚠ **A TENSION THAT MUST BE CARRIED, not resolved by assertion.** The V42 substitution is
**ASYMMETRIC** — it clamps command-magnitude increases and passes decreases — so if it were
continuously active it should print a **rectified** waveform. **Yet the ratchet measures SYMMETRIC**:
skew **−0.16 … +0.06**, crest **2.07–2.45** against a sine's 1.414. **That is evidence AGAINST the
state-4 substitution shaping the CURRENT ratchet.** It is not evidence that restoring `0x454FE` is
wrong — see §6 for how V71 states its justification.

✅ **Safety re-verified against `_v70_plain_image.bin` [EVIDENCE]:** `FUN_0004595a` `[0x4595A, 0x45A1F)`
and `FUN_000462e6` `[0x462E6, 0x46360)` are **0 diff bytes vs stock**; the DTC-0x1d-no-debounce path is
unchanged. The *"the substitution only ever makes `gp-0x6ace` smaller ⇒ safe side"* argument
**transfers**, but it remains **[INFERRED]**, not verified. `0x454FE` sits inside the bridged main CRC
block `[0x13000, 0xC4FFC)`.

**[OPEN]** what sets `gp-0x6d78` bits 15/16 mid-drive. `FUN_000197b8` has **21 callers, untraced.**
That decides whether state 4 is sticky for a whole drive or only briefly.

---

## 6. THE AGGREGATOR IS ELIMINATED

**[EVIDENCE — every ceiling byte-read.]** **All EIGHT zero-type range gates are STRUCTURALLY VACUOUS** —
each is capped by its own producer's ceiling at or inside its gate window, **on every drive, every
build**:

| lane | producer ceiling | gate window |
|---|---|---|
| boost | 512 | 2048 |
| damping | **exactly 0 at creep** (FactorC `0xD27BC` Y[0] = 0, multiplicative; ≈ 35 km/h onset), ≤ 1024 at highway | 2048 |
| friction | 511 | 1024 |
| magnitude | ±0x3000 | **== window, exactly, inclusive** |
| LKAS | ±0x2800 | **== window, exactly** |
| `gp-0x6ade` | **0 writers** | — |
| resonance | max 1024 (**164–341** at the ratchet's speeds) | 2800 |
| return-centre `gp-0x6b62` | max 5786 | 8192 |

⇒ **the aggregator stage contains NO reachable hard nonlinearity**, joining the aggregator **SUM**
(eliminated by V65 over 120,049 frames). **The relay / limit-cycle framing for the aggregator is
REFUTED.**

★ Also [EVIDENCE]: `FUN_00036388`'s own counters give periods of **~20–40 ms or ~1 s** — nowhere near
7.8 Hz. ⇒ **it INHERITS the ratchet, it does not GENERATE it.**

---

## 7. RETRACTIONS — recorded as retractions, with what replaced each

### 7.1 🛑 "r26 is INERT / r24 carries the entire lane" — **REFUTED ON-CAR**
LEG 2 (the magnitude leg) was the last thing holding it up, and V70's bit4 killed it: **1,644/18,010
frames strictly negative.** **Replaced by:** §2 — two selectors, one gate, every published multiplier
in this kit is an r24-only number at `a = 0`, and **the r24 lane is itself near-inert** (§2.0).

### 7.2 🛑 The **"peak-velocity / rateKey collapse"** hypothesis — **DEAD ON SCALE B; on scale A it survives only at the ~90th-percentile worst instant**
**That is a sharper retraction than "refuted", and it is the honest one.**

🛑 **Its founding number was never a burst measurement.** `A_rk = 1927` is
`studies/sessions/v70/v70_parametric_gain_collapse.py:132` — **the top decile of the WHOLE-DRIVE `|rate|` distribution (hard
manoeuvres)**, not the rate index during a grind. **Measured directly over 424 burst windows**, the
oscillation's own 18–22 Hz rate swing is **p50 140 / p90 327 counts**; even **raw** max `|rate_c|`
in-window is **p50 542**. The monotone window needs **A_rk ≳ 1400**, reached by **9.20%** of windows on
**scale A** and **0.00%** on **scale B**.

Corroborating, from the independent direction: grind #1 lives **97.8% (scale A) / 100% (scale B)**
inside the **flat `[0, 400]` rate segment**, over **19,378 burst samples across 11 routes**; re-pricing
made Spearman **worse** (−0.638 → −0.657).
⚠ **The two analysts disagreed and the orchestrator adjudicated — record the adjudication, not just the
verdict.** The outcome data (V70 excluded from V62's class at P < 5 × 10⁻⁵) is **sound**. But the
rateKey axis is the **bus angle rate converted by an assumed scale**, while `gp-0x6ac0` is the
**motor/resolver rate** — **a proxy that cannot settle the question either way.**
**Replaced by:** §2 — r24 is near-inert and the lane was never the r24 lane, which accounts for the same
outcomes **with no rateKey claim at all**.

### 7.3 🛑 The **aggregator zero-gate / relay** hypothesis — **REFUTED** (§6, all 8 vacuous).

### 7.4 🛑 **"V69 ran just under saturation, so V70 feels stiffer"** — **REFUTED** (§3.4; hard clamp,
0.0000% at the rail).

### 7.5 🛑 **"The state-4 entry/exit cadence sets the ratchet's period"** — **REFUTED** (§5; state 5 is
unreachable, 4 → 10 is one-way, there is no cadence).

### 7.6 ⚠ **"Q is not measurable at NFFT 256"** — **SUPERSEDED** (§3.3.4).
🛑 **Note the scope precisely: Q ≈ 40 CONFIRMS the record's Q ≈ 36. The only thing superseded is the
claim that Q could not be MEASURED — not the value.** ⚠ one episode; lower bound.

### 7.7 ⚠ **The "non-monotone dose–response with a minimum near 2×" is RETIRED.**
It priced **every** build on r24 alone at `a = 0`. With r26 live, V62/V65's "2×" and V69/V70's "2×/4×"
were never the same quantity. **Replaced by:** §2.0 and the two-selector table in §2.1.

### 7.8 ⚠ **"The ratchet is engagement-CONDITIONAL (44/46 windows)" — SUPERSEDED by a stronger claim.**
It is **engagement-REQUIRED**: **0 of 118** manual hands-off creep windows across **four builds**, with
the grip confound removed (§3.3.1). **Replaced by:** the pooled four-route table, which also shows the
rate is **build-independent**.

### 7.9 🛑 **"Grind #1 can be used to check whether an r24 dose is in force" — RETIRED as an INSTRUMENT.**
Log-log slope **−0.144 [−0.991, +0.347]**; pairwise **P = 0.667 / 0.610 / 0.426** (§3.1). **Structural,
not a power limit.** **Replaced by:** V71's `gp-0x671d` mask rung, which reads the gain in force
directly.

### 7.10 ⚠ **The bit6 "arm-selection" reading is DOWNGRADED to the weaker of two candidates** (§4.1).
It cannot explain the **dose-dependent** miss on route `4f` (0/47,990 at double the dose, needing only
49 counts). **Replaced by:** [BELIEF] an under-ranged or mis-reconstructed rung — with the corpus unable
to settle it.

### 7.11 🛑 **`0xC6444` is STRUCK as a lever — it is a NULL BY CONSTRUCTION, not "untested upward".**
**[EVIDENCE]** it is read **only** at `0x3AB5E` and **only when `lp != 0`**; on every **gateless** build
(stock, V62, V65, V69, V70, **V71**) the gate `0x3AA96` is `c5`, so `lp` derives from `gp-0x683c`, which
has **0 writers image-wide** ⇒ **the load never executes.** Raising it changes **nothing** unless
`0x3AA96` is also repointed — which reintroduces the control path the operator rejected. **This
supersedes the standing "candidate, not a recommendation" framing.**

---

## 8. V71 — BUILT THIS SESSION BY A SEPARATE AGENT

**THREE siblings were built, all unflashed, all restoring `0x454FE`. Orchestrator-verified from the
image bytes.** 🛑 **Not separable on the wire — the filename is the only pre-drive discriminator.**

| | image SHA256 | rwd SHA256 | probe |
|---|---|---|---|
| **V71A** | `acc62e0930c9fa8f5176e22d1751f3f9544b1228c90d0b1e09188c67448c78e5` | `5c5138d960192d7d0a4e37301a0c82ad29e02ccff0cc116b62d6ac1cb0337e9e` | `gp-0x6ada` (r24) |
| **V71B** | `d4543d02b2fa113df7ab394ba0131859e3193a8c75604ddf3165768b6e5dd3f4` | `3bc9347aa54449b2ccfe7896b076f57bf0b932ed1de3d41ae45be838ceaa8157` | `gp-0x6adc` (r26) |
| **V71C** | `30b63fdd59bdf9221fec0942d9ccdbc6f0582d2e8c3acbc4d30b0acd89ff1607` | `4ce568b6fd85ad0ad2a5a6159ede09276f705a1e00d66ac129b8f60679c4e609` | `gp-0x6ada` (r24) |

**A** = both `sar` → `0x9`, flat 2.000× everywhere (V62's lane exactly).
**B** = `gain_A` rec0/rec1 Y[0..3] ×2 ⇒ 2.000× ≤10 km/h → **exactly 1.000× ≥50 km/h**, r24 stock.
**C** = V67/V68's gate + arm 5244, with **`0xC6444` 512→3072 removing the ~6× r26 cut**; 71 bytes off V67.

**Recommended: V71B** — the minimal change from V70 (the configuration the operator reports as having
grind #2 gone), keeping V70's structural highway-stock property while adding r26 movement, which every
build that fixed grind #1 had. **V71C is the fallback**, carrying V67/V68's best-in-kit creep numbers.

⚠ **Recorded because it cost time:** the orchestrator recommended A, then C, then B. The reversals were
forced by two real corrections — the r24/r26 confound, then the finding that **a scalar gated arm can
never be highway-clean while dosing at creep** — but the second was derivable from V70's own build note
*before* V71C was specced, and was not. ⚠ Also recorded: a subagent was reused to **~700k tokens**
against the kit's ~50% context budget, and the replacement was spawned on a **stale brief** that nearly
overwrote finished artifacts. Both were process failures, not analysis failures.

**V70 carrier, plus:**
1. **`0x454FE` `ba` → `b5`** — restore V42's ratchet fix.
2. **`0x3AB76` / `0x3AC20` `aa` → `a9`** — restore V62's ×2 on **BOTH** lanes.
3. **Surface `0xD2A7E` / `0xD2A80` / `0xD2ABA` / `0xD2ABC` reverted to stock.**

⇒ **the rate lane is byte-identical to V62/V65**, which flew **twice**, both flight-clean. CRC blocks
`0xC4FFC` + `0xD2FFC`.

★★ **WHICH HALF IS LOAD-BEARING, now that §2.0 is in: `0x3AB76` — the r26 `sar` — IS THE LEVER.**
`0x3AC20` (the r24 `sar`) is restored **for exact V62 parity, NOT because r24's dose is expected to
matter** — the clean single-variable r24 series reads flat across a 4:1 range. **Say it that way in the
pre-flight note, so a null on r24 is not later read as a null on the build.**

**The probe:**

| bit | test | why |
|---|---|---|
| 7 | liveness | field == 0 ⇒ VOID |
| **6** | **`gp-0x671d != 0`** | ★★ **THE MASK — which gain is actually in force.** The direct answer to §4.1's four-in-a-row zero |
| **5** | **`gp-0x67fa == 4`** | 📋 **pre-registered BIMODAL, ~100% / ~0%** — a **complete** discriminator now that 5 and 10 are excluded |
| 4 | `gp-0x6ada >= +512` | positive control, and **stronger here** — the `sar` doubles r24 under **every** branch. ⊕ V71 also carries a **two-sided, low-threshold** r24 mirror rung, so an under-ranged reconstruction (§4.1) cannot hide again |
| 3 | `gp-0x671a >= 5` | — |

🛑 **STATE THE `0x454FE` JUSTIFICATION HONESTLY, AND KEEP IT STATED.** It is restored because it is a
**confirmed fix that was lost by accident** — **NOT** because it is established to cause the current
ratchet. §5's symmetry tension is evidence against that mechanism, and V71 does not resolve it.

⚠ **KNOWN RISK, disclosed:** **V62 is also the build that introduced creep grind #2.** Restoring its
lane may bring it back. Given r26 is now known live, that may have been **r26's doubling** rather than
r24's — **untested.**

### Deferred to V72 — ONE lever, deliberately not stacked on V71

★★ **FactorC + FactorE TOGETHER, re-read against the RATCHET — and it is now materially more compelling
than when it was filed.**
**Base-assist damping is EXACTLY ZERO below ~35 km/h** (FactorC `0xD27BC` Y[0] = 0, multiplicative)
while **the ratchet lives at 4.9–8.0 km/h with Q ≈ 40.** And **V47 — FactorC and FactorE raised
TOGETHER — reported *"marginally quieter at 5 mph"*** and was filed **null against the 21 Hz
vibration.** 🛑 **That positive whisper has never been evaluated against the RATCHET.** It is the most
under-examined result in the archive.
★★ **§3.3 is what strengthens it:** *engagement-required* + *hands-off-conditional* + *Q ≈ 40* +
*damping exactly zero below ~35 km/h* ⇒ **at creep, the driver's hand is the only damping in the
system.** ⚠ **Still deferred** — a two-cal change on a lane V47 already touched deserves its own
single-variable drive.

🛑🛑 **`0xC6444` IS NO LONGER ON THIS LIST — it is STRUCK as a null by construction. See §7.11.**

---

## 9. WHAT THIS SESSION CHANGES ABOUT HOW THE KIT WORKS

1. **`RULE 3`** — a "CONFIRMED" result is about a *lever*, not about *the car you are driving*.
   **Byte-check the current image before reasoning from any recorded result.**
2. **When you remove a confirmed fix to run a control, write the restore into the next build's spec.**
   V66 did not, and it cost ten builds.
3. **Probe the GAIN IN FORCE, not a lane OUTPUT.** Four consecutive probes returned uninterpretable
   zeros by reading outputs. A selector/mask bit is one bit and it is never ambiguous.
4. **A dose ladder is only a ladder if every rung is the same quantity.** Two of this kit's rungs
   were not — and once re-priced, **the axis the ladder was built on turned out to be the wrong lane.**
5. **CI overlap is not a test.** A subsample-at-matched-exposure test excluded a level that the CI
   comparison had called undecided (§3.1). Say what is established *and* what is not, in the same
   sentence.
6. **Check that a lever is REACHABLE before calling it untested.** `0xC6444` sat on the candidate list
   as "untested upward" when the load that reads it never executes on any build this kit flies (§7.11).
7. **A "provoked" measurement needs its provocation separated from its subject.** The 6,502-count peak
   was the operator's own hand, and the 6–9 Hz content there was 190 counts (§3.3.2). Band-limit before
   attributing.
