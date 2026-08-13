# AUDIT 2026-08-12 — THE DEAD-LEVER CATALOGUE, THE FAILURE TAXONOMY, AND A PRE-FLIGHT LIVENESS CHECKLIST

**Why this file exists.** The operator flashed **V97** (`0xC63AC` 102 → 150) and felt **zero difference**
in grinding or micro-ratcheting during a deliberate parking-lot creep with LKAS engaged, provoking the
symptoms on purpose. He wrote:

> *"Perhaps this pole edit is dead somehow, either a mistaken cal address, or maybe the logic we touched
> isnt used. This has happened before, we need to be careful about determining whether some code actually
> gets executed in the way we think."*

He is right that it has happened before. **This file reconstructs exactly how often, by what mechanism,
and how long each one went undetected — and turns that into a checklist a build must pass before it is
cut.**

**Scope:** V38 → V97. **Method:** every claim below is cited to a file and line, a build number, or an
on-car route. Nothing here is recalled; where the record disagrees with itself, both readings are shown.

**Sources read for this audit:** `docs/STATE.md`, `docs/BUILD-LINEAGE.md`,
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`, `docs/ARC-AUDIT-2026-08-10.md`, the `docs/HANDOFF-*.md` chain
from 2026-07-31 forward, `memory/MEMORY.md`, and `analysis-2020accord/build_v97_tva.py`.

---

## 🛑 THE THREE VERDICTS, KEPT STRICTLY SEPARATE

The kit has conflated these before and it has cost builds. They are not interchangeable:

| verdict | means | what it licenses |
|---|---|---|
| **FALSIFIED** | The lever **was in force** on a drive and the pre-registered effect did not appear. | Retiring the *hypothesis* — **but only against the symptom that was actually scored** (RULE 7). |
| **INERT-BY-MODE / DEAD** | The edit **was never in force**: wrong mode record, gate never armed, dead zone, input bypass, or silently reverted. | **Nothing.** The hypothesis is untouched. The lever is **untested**. |
| **NEVER-TRIED** | The cell was never written by any build. | Nothing — but it is a *candidate*, not a re-run. |

⊕ And *"the same lever pushed the other way"* is a **different claim** from *"a new lever"*
(`docs/BUILD-LINEAGE.md:466`).

---

# PART 1 — THE CATALOGUE OF DEAD LEVERS

Twenty-nine entries, grouped by the mechanism that killed them. Columns: what was edited · how it was
found dead · how long it went undetected.

---

## A. WRONG MODE RECORD — the bytes were correct and the car read a different table

**The root fact.** The car is **`TVCA4`** — config row 11 — running **mode 24 disengaged / mode 26
engaged**. Settled 2026-08-05 by V73's probe over **104,061 frames**, 18 transitions, all on engagement
edges (`memory/reference-accord-car-is-tvca4-mode-24-26.md`). Every "mode 10/11" statement before that
date is wrong, and the error was inherited from *an assumption recorded in `BUILD-LINEAGE.md`* that
`39990-TVA-A160` reads as row 2 `TVAA1`. 🛑 **It was never a measurement**
(`docs/BUILD-LINEAGE.md:593`).

| # | build(s) | edit | how it was found dead | undetected for |
|---|---|---|---|---|
| **A1** | **V44, V47** | FactorC / FactorE raised on modes **10/11** | **V72's probe, arithmetically.** On V72, modes 10/11 give `\|gp-0x6bd0\| = 389` *unconditionally*, so the probe's `bit4` (`≥ 64`) would fire on **100 %** of frames. **It fired on 0 of 87,940**, including 0 of 34,275 above 35 km/h ⇒ the car is not in mode 10 or 11 (`BUILD-LINEAGE.md:597-600`, **RULE 6**) | **≈ 28 builds** (V44 → V72), ~16 days |
| **A2** | **V72** Levers B/C · **both** of V73's levers | mode-indexed damper edits | same probe, same session | ~1 build |
| **A3** | **V69, V70** (and V72/V73's r24 half) | the **entire `gain_B` r24 dose ladder**, written to **mode 10** | **RULE 4** — a machine byte-diff of **all 65 built plain images**, 2026-08-05: *"🛑 **V69 AND V70 DID NOTHING.** `sar` stock, gate `c5`, arms 512/512, and the only edit is `gain_B` **mode 10** ⇒ **byte-stock behaviour**"* (`BUILD-LINEAGE.md:534`) | ~1 day to the bytes — **but the false conclusion had already been recorded and propagated** |
| **A4** | **V73** | friction row ×1.5, written to **mode 10 only** — a **DISENGAGED** column | **Dereferencing `0xCBE74 + mode*4` on the images themselves** and printing the mode number beside the address, 2026-08-10 (`BUILD-LINEAGE.md:248-302`) | **~5 days** |

🛑 **A3's cost is the sharpest lesson in the file.** The record had carried:

> *"clean single-variable r24 series ×1 → ×2 → ×4 = 879 / 729 / 746, CIs overlap ⇒ r24 is near-inert."*

That was **three replications of ONE condition.** ⇒ **"r24's dose is UNTESTED, not near-inert"**
(`BUILD-LINEAGE.md:534`). A dose *ladder* that never existed had become a *negative result* about a lane.

🛑 **A4 inverted a standing attribution.** V73 was the only build claiming *"`0xC407E` = 850 alone is
survivable"* — and it is the same build that turns out never to have carried the friction row on a live
column. ⇒ **the friction row moved from EXONERATED to OPEN SUSPECT**, and *"×1.5 on a live column has
flown exactly TWICE, and BOTH flights hard-faulted. ZERO clean flights"* (`BUILD-LINEAGE.md:266-278`).

★★ **The general form, stated in the record:** *"a mode-indexed table makes a lever look flashed, verified
and driven while being structurally unreachable. Every prior 'damping is null' result on this kit (V44,
V47, V72) is now **uninterpretable**, not falsified"* (`BUILD-LINEAGE.md:606-608`).

---

## B. THE GATE NEVER ARMED

| # | build | edit | how it was found dead | undetected for |
|---|---|---|---|---|
| **B1** | **V64** | `0xC6440` 2048→4096, `0xC643E` 1536→3072 (oscillation-detector damping) | **The build's own probe.** `0x14A` byte4 read a **constant `0x87` across all 14,980 frames**, zero variance — bits 6/5/4/3 all clear on every frame ⇒ `gp-0x6c2c` never crossed T = 12800 ⇒ *"never in force for a single frame"*. Confirmed **four ways** (raw byte histogram, dedicated decoder, independent raw-CAN rederivation, V59-probe exclusion) (`HANDOFF-2026-07-31-v64…:8-9`) | **ONE DRIVE** — because the build carried a probe on its own gate |
| **B2** | **V67, V68** (and V64) | the same detector ladder, read at `≥ 5` then at `≥ 1` | bit5 (`gp-0x67df != 0`) fired **0 / 53,991 frames** across routes `4c`/`4e`, *including straight through the 1468-count 28 Hz lane-change burst*; bit4 likewise 0. With V67's 186,321 frames the ladder reads **zero across three builds** | **STILL OPEN** |

🛑 **B2 is B1 one layer down, and it is the more dangerous shape.**
> *"This cell has **NEVER been observed non-zero in this kit. There is NO POSITIVE CONTROL.** The null
> bounds oscillation amplitude *only if the detector is genuinely live*; 'the detector is disabled / its
> input is dead / `FUN_000428d4` is not reached in this operating mode' is **NOT excluded** by this
> measurement."* — `memory/accord-v68-detector-still-zero-no-positive-control.md`

⇒ **B1 is a solved null (we know why). B2 is an unsolved one (we cannot tell a quiet car from a dead
probe).** The difference is entirely whether a **positive control** exists.

⊕ Related: **`gp-0x67fa`'s reachable set is effectively `{11}` alone** — state 5 structurally dead, state
10 measured 0.0000 %, state 4 measured 0/123,277 ⇒ **V42's `0x454FE` is present on V85 and MEASURED
INERT** (`BUILD-LINEAGE.md:510-514`). And **RULE 5** was written for exactly this: `0x454FE` had been
recorded **FALSIFIED** mid-session because V71B/V71C flew with it "restored" and the operator reported no
change — *"That was wrong… State 4 never occurred while driving, so V42's substitution never ran on either
drive"* (`BUILD-LINEAGE.md:636-642`). ⚠ V71B/V71C did not carry V62's `sar` either (see F2).

---

## C. SILENTLY REVERTED BY A REBASE

| # | lever | what it fixed | carried by | how it was lost | undetected for |
|---|---|---|---|---|---|
| **C1** | **`0x454FE`** `bne`→`br` | the **ratchet** — state-4 governor magnitude substitution. Filed *"CONFIRMED ROOT CAUSE, carry forward"* | **V42 → V52C only**; byte-stock (`ba65`) in **V53–V70** | 🛑 **SILENT REBASE LOSS.** V53+ descends from V38/FOURFRAME, which branched *before* V42. **Nobody decided this.** Found 2026-08-04 by byte-reading all 60 plain images | **18 builds / ~8 days** |
| **C2** | **`0x3AB76` + `0x3AC20`** `sar 0xa`→`0x9` | **the kit's only measured grinding fix** — 8× at creep, 42× at \|rate\| 16–32 | **V62, V65 only** | ⚠ removed **on purpose** as V66's confirmatory control and **never restored** | V66 → V70 |
| **C3** | **The V38 rebase reverted SEVEN levers, not three** | — | — | see below | count walked 3 → 7 on **2026-08-08** |

**C1/C2 together:** *"From V66 to V70 the car carried NEITHER confirmed fix, while the record read as
though both were carried"* (`BUILD-LINEAGE.md:672`). ★ And the general form of C2 is the worse one:
**a lever removed on purpose as an experimental control is indistinguishable, six builds later, from a
lever that was never needed** (`:678-680`).

⚠ **C1 compounds.** The argument that had retired `0x454FE` as a cause — *"`STEER_STATUS == 4` fires
0/37,922"* — was **void**, because bus `STEER_STATUS` is not `gp-0x67fa`; state 4 sits inside all three
gate masks. ⇒ *"It was never actually eliminated"* (`:674-676`). ⊕ The byte has since been **silently lost
three times** (`:512`).

**C3 — the seven, read from the images** (`STATE.md:1497-1522`):

| lever | V62 · V68 · V74 · V75 | V76 · V78 · V79 · V80 | declared? |
|---|---|---|---|
| `0x2A1F0` reader disp | `0x7CD0` → decoupled | `0x746C` → shared | silent |
| `0xC646C` shared sensor scale | 891 | **3564 (4×)** | silent |
| `0xC62EA` low-speed steer lockout | 0 (removed) | **320** (restored) | silent |
| `0xC63A0` Path-2 damper weight | 2048 | 1024 | silent |
| `0x454FE` V42 ratchet fix | `0xB5` | `0xBA` — **the SECOND silent loss** | silent |
| 🆕 **`gain_A` rec0** `0xC6A72`–`78` | 512 | Honda's 3072/2434/2048 | **never logged anywhere until 2026-08-08** |
| 🆕 **`gain_A` rec1** `0xC6A86`–`8C` | 512 | Honda's 3072/2488/1536 | **never logged anywhere until 2026-08-08** |
| `0xC407E` friction clamp | 850 *(V73/74/75 only)* | 511 | declared |
| friction row, 14 sites | ×1.5 *(V73/74/75 only)* | stock | declared |

⇒ **"V80 vs V75 was NEVER a single-variable damper comparison — and the confound count is FIVE, not
four."** Any conclusion from a V80-vs-V75 or V76-vs-V75 contrast must name all five (`STATE.md:1518-1522`).

---

## D. RIGHT CELL — THE DEAD ZONE EXCLUDES THE OPERATOR'S REGIME

| # | lever | the arithmetic | verdict |
|---|---|---|---|
| **D1** | **the base-assist damper** (FactorC × FactorE, all builds V44 → V86B) | `ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)` — a **PRODUCT of two dead zones**: FactorC `Y[0]=0` below **2240 ct ≈ 35 km/h**, FactorE `Y[0]=0` below **60 ct ≈ 12.7 °/s** | **exactly ZERO on 95.91 % of engaged frames**, **100.0 %** of the micro-ratcheting regime (229 s at 1–13 °/s) and **100.0 %** of ratcheting at parking-lot speed (131 s) (`STATE.md:592-604`) |
| **D2** | **`0xC63A0` 1024→2048** (V72, V73, V76g, V81) | it weights a product that was **already zero at creep** ⇒ zero × 2 = zero | **flew FOUR times and measured INERT**; ⇒ **V84's own `0xC63A0` revert was itself inert** (`BUILD-LINEAGE.md:475`) |
| **D3** | **V89 `0xC40D2` (K1)**, the modelled Coulomb friction ×2.000 | the friction term is `sign(motor rate)`-gated: `\|friction\| ≥ 0.0625` on **0.000** of frames below 1 °/s and **0.009** of the micro-ratcheting regime (1–13 °/s, 782 engaged s) | **the cell K1 doubles is negligible on 99.1 % of the regime where he names the symptom** (`BUILD-LINEAGE.md:81-84`) |

★ **D1's most important line: NEITHER PRIOR TEST EVER HAD BOTH ZONES OPEN.** The `FactorE X[0]` lever was
withdrawn as *"structurally vacuous"* because FactorC was 0 at creep; **`FactorC Y[0]` WAS tested, as V86B
on route 70** — but FactorE stayed 0 below 12.7 °/s, so **V86B armed the damper only for *spinning
quickly*, never for *spinning at all*** (`STATE.md:605-610`). A **product** needs every factor checked, not
each factor checked once.

🛑 **And sizing kills D1 anyway, which is why it is closed rather than pending:** reaching even 25 %
authority at 10 °/s requires raising `FactorE Y[0]` off zero = **a step at zero rate = a relay in rate =
the V78/V79/V80 move, recorded as "WORST GRINDING EVER"** (`STATE.md:612-617`).

⭐ **D3 is the closest structural precedent to V97**: a correctly-addressed, single-reader, virgin cell,
flown, with the direction argued — and the build's **own probe** showed after the fact that the lever was
pointed away from the regime the operator uses.

---

## E. RIGHT CELL — THE LANE CARRIES ALMOST NONE OF THE DELIVERED SIGNAL, OR THE INPUT BYPASSES IT

Six deaths, five of them in the 2026-08-12 session, **each before a build was cut** (`STATE.md:84-93`).

| # | lever | why it is dead |
|---|---|---|
| **E1** | **`0xC6194`** LKAS slew limiter | **REAL and calibrated** — 3 ct/tick = 1.37 s full scale, *exactly the shape the operator described* — **but its input partition `0xC4118` is all-1, so 100 % of the request bypasses it.** ⚠ Arming it goes the **wrong** way |
| **E2** | **`0xC63A4`** | its lane carries **~1.1 ct of a 342 ct signal** |
| **E3** | **`0xC520C`** governor ceiling | `gp-0x6ac0` scale reconstructed at **4.7121 ct per column °/s** ⇒ first knot = **222.8 °/s**. Measured hands-off returns max **528 ct against a 1050 knot — 0.00 %** reach it |
| **E4** | **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]**, CI **excludes** the predicted +1 — and `gp-0x6b4c` is a **second LKAS route that never sees AUTH** |
| **E5** | **PID Ki `0xC6B12`** | at 6–10 km/h the **P term alone** (16,000 at e = 2000) already exceeds the anti-windup bound (**7,264**) ⇒ the integrator is **pinned** and Ki is marginally irrelevant |
| **E6** | **the pre-declared V97** (`gp-0x6b4c` / `gp-0x6b4e`) | `gp-0x6b4e` **provably ≡ 0**. §A5 had priced the gate's **WIDTH** when the failure mode is *the signal never being non-zero* — **which IS the V64 null** |
| **E7** | **the "return-to-centre lane"** | re-identified as a **RACK END-STOP CUSHION**: arms on `\|gp-0x6b98\| > 4096` **AND** motor rate `< 200` (a **stall** detector), splits by sign into left/right stop enums, **has no angle term anywhere**, gate needs `\|gp-0x6bf0\| > 8878`. **~99.3 % dead in MANUAL too** ⇒ its absence cannot explain any engaged-vs-manual difference (`BUILD-LINEAGE.md:500-508`) |

🛑 **E1 carries a second, independent defect: the record's stated reason was WRONG, and stayed wrong.**
`memory/reference-accord-lkas-only-rate-limiter-c6194.md` and the lineage recorded *"output ×0"*.
**That is `0xC6196`, a different cell.** The real reason was only found on **2026-08-12**
(`STATE.md:90`). ⇒ **a lever can be correctly filed DEAD for a reason that is itself false**, and the
false reason then blocks re-examination.

🛑 **E6 is a wrong-address death caught before the cut** — and the address error is instructive: the array
is `gp-0x62c8[]`, **not** `gp-0x62f8[]`; *"they are **two different arrays 0x18 apart**, not one split by
mode"* (`STATE.md:87`).

⚠ **E4 is also a wrong-address case**: *"The table header is `0xC67BE`; `0xC67C8` is its `Y[0]`"*.

---

## F. NEVER WRITTEN AT ALL — THE LEDGER SAID "TESTED" AND NO IMAGE CARRIED IT

**RULE 4**, added 2026-08-05 after a machine byte-diff of all 65 built plain images
(`BUILD-LINEAGE.md:614-632`). *"Both made a lever look **tested** when it was not — the direction that
suppresses work."*

| # | claim in the record | the bytes |
|---|---|---|
| **F1** | *"`0xC6440/42/46`, `0xC61F6` \| V39 \| ✅ \| FALSIFIED"* | **False.** V39's entire delta vs V38 is `0x3AC78` (4 bytes, a cave hook). **`0xC6442` written by 0 of 65 images** — UNTESTED, and separately **unreachable** (`gp-0x671d` reads 0 / 402,424 frames). **`0xC61F6` written by 0 of 65 images** — UNTESTED |
| **F2** | "V71B / V71C = V62 plus something" | **V71B and V71C do NOT carry V62's `sar`.** `0x3AB76`/`0x3AC20` = `a9` in **exactly three images: V62, V65, V71A** — and **V71A never flew.** The two builds flown 2026-08-04/05 carry **NEITHER** of V62's bytes |

> **RULE 4: attribute a lever to a build only from that build's own byte diff, never from this table's
> prose. Two of the entries here were wrong, and both errors ran toward "already tested."**

---

## G. TOOL-ZERO — THE SCAN WAS DEAD, NOT THE FIRMWARE

| # | instance | the number |
|---|---|---|
| **G1** | **`gp-0x6b94`'s reader census** — *"who reads this cell?"* asked over **three rounds** with disp16 and disp23 byte scans, LE32 absolute literals, movhi/movea pairs, ep-address materialisation, pcode dataflow and two register-return checks | **Eleven independent methods returned the same wrong answer** — against **six flashed on-car results** (V61, V62, V67/V68, V74, V75, V80) that could only have worked if that lane reached the motor. The bridge (`gp-0x6acc`) was **two hops past where every check stopped**, and had been documented **since May 2026** (`BUILD-LINEAGE.md:13-43`, **RULE 13**) |
| **G2** | **`get_xrefs_to` tp-relative blind spot** | known |
| **G3** | **`search_instructions` undercounts** — scans only already-analysed instructions and still reports `truncated:false` | known |
| **G4** | **`movea` + register-indirect** | `operand_pattern="-0x6350[gp]"` returned **0 / 183,570 / `truncated:false`** on an array with **nine real accesses** |
| **G5** | ⭐ **NEW CLASS, 2026-08-12 — `ep`-relative short-format aliasing.** An array based once via `movea <off>,gp,ep`, then every access is `sld`/`sst` off `ep` with **no offset in the operand text** | `-0x62f8` → **15 hits, 14 of them base setups, ZERO actual loads/stores.** 🛑 *"Worse than a zero: a healthy-looking non-zero count that misses 100 % of accesses"* (`STATE.md:113-116`) |
| **G6** | **`0xC64DE`** filed dead | *"8 of its 16 read sites are in a region Ghidra never analysed ⇒ 'dead' is a **tool zero**"* (`STATE.md:107`) |
| **G7** | a *filtered* zero | `operand_pattern="0x0[ep]"` returns 0 because Ghidra renders operands as `r6, 0x0, ep` — commas, no brackets |

★ **G1's acceptance test is the durable part:** *"A 'monitor-only' output two hops from the motor is a red
flag, not a conclusion. And a governor whose cals bricked the car (V40) is not on a dead path — **a
coherent account of V40 is the acceptance test for any claim about this chain.**"* ⊕ *"When a new negative
contradicts an old positive, diff them explicitly."*

---

## H. THE PROBE ITSELF WAS DEAD

| # | build | what happened |
|---|---|---|
| **H1** | **FOURFRAME** (on V52c) | The 4-frame CAN telemetry cave transmitted **nothing**. Cause: **our own bug** — the cave wrote `STRB = 0x80` leaving `SSAM = 0` (`memory/reference-accord-fourframe-strb-ssam-defect.md`) |
| **H2** | **FOURFRAME2 / V53** | The STRB defect was **fixed** — and it **still got zero frames**. Cause: **the CAN gateway is a WHITELIST.** Only `0x14A`, `0x18F` and `0x1AB` cross ⇒ **a new ID can NEVER reach openpilot** (`HANDOFF-2026-08-08-v81…:251`) |

⇒ **Two consecutive silent telemetry builds, two entirely different causes.** The first was ours, the
second was structural, and the first masked the second.

---

## I. THE LEVER WAS ALIVE — THE VERDICT WAS RETIRED AGAINST THE WRONG SYMPTOM

🛑 **This is a distinct, recurring failure from the mode problem, and the record says so explicitly**
(`BUILD-LINEAGE.md:354-358`):

| # | lever | filed as | scored against | actually |
|---|---|---|---|---|
| **I1** | **V42 ch.2** (`0x454FE`) | *falsified* | the **vibration** | **never scored against the ratchet — and it turns out to be V42's actual fix** |
| **I2** | **V47** | *null* | the **21 Hz vibration** | never scored against the ratchet |
| **I3** | **V56's lane mute** (`0xC6AFC`/`0xC6AFE` → 0) | FALSIFIED and harmful | **15–26 Hz** | 🛑 **NEVER scored on 6–9 Hz**, the ratcheting band (`ARC-AUDIT:168`). Band-scoped, carried as general |

> **"A verdict without a named symptom is not a verdict."**

⚠ **I3 is still load-bearing today.** `memory/accord-friction-polarity-more-assist.md` records exactly this
caveat: *"V56 muted this lane and got a null — but scored on 15–26 Hz, NOT 6–9 Hz, and route 24 is not on
disk."*

---

## J. ⭐ THE INSTRUMENT WAS INVARIANT TO THE LEVER — the lever was in force and could not be seen

🛑🛑 **This class is not in any prior enumeration, and it is the one that most resembles V97.**

| # | build | what happened |
|---|---|---|
| **J1** | **V91 / V92** — `0xCBE74` ×1.5 on modes 26/27 | Scored at the lane's **own single output** `gp-0x6b26`: engaged stratified ratio **0.99 [0.91, 1.26]** against a pre-registered **1.50**; MANUAL negative control held at **1.009**; duty flat at 0.167 / 0.161 / 0.165 against a needed 0.204. Filed as **"the dose did nothing"** |

**And then V94 cut the same cell 6× and the operator aborted the drive.** *"Made the stuttering and
grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to
drive."* Measured: motor acceleration **3–7× up above 9 Hz** (`BUILD-LINEAGE.md:53`).

⇒ **The cell reaches the car. The ×1.5 null was never a dead lever.** The kit's own RCA
(`HANDOFF-2026-08-12-v94…:82-84`):

> *"The motivating null was a measurement artifact. V91/V92's ×1.5 measured 0.99 because
> `gp-0x6b26 = K·α` and α is **what K damps** — in a stable closed loop **the product is invariant to K**.
> **Nobody asked whether the instrument could measure the thing it was pointed at.**"*

🛑 **Two consequences, both live:**

1. **Your brief's framing of V92 — *"the engaged mode record read ≠ the record written"* — was RETRACTED in
   the same session it was written.** `memory/accord-cbe74-dose-measured-inert-wrong-mode-record.md:39-49`:
   *"THE 'WRONG MODE RECORD' EXPLANATION IS **REFUTED**"* — because V73 probed the **same index byte**
   `gp+0x63fd` over 104,061 frames. ⚠ **That memory file's own frontmatter `description:` still asserts the
   refuted claim while its body refutes it**, and `memory/MEMORY.md`'s pointer line repeats the stale
   version. **This is a live defect in the recall layer** and it is exactly the class of error
   `memory/feedback-search-the-kit-before-naming-a-cause.md` was written to prevent.
2. The record now carries the honest label: **`0xC63A6` is *"a cliff edge, not a lever"*** — V91/V92's
   ×1.5 null and V94's ×0.25 catastrophe **fit closed-loop invariance, not a dose-response**
   (`STATE.md:93`).

⚠ **Carry the residual honestly.** The V92 leg is weaker than first written: *"V91 is telemetry-identical
to V90 … route 78 cannot prove V91 was ever on the car"*, so the conclusion rested on **V92's `byte7 b7`
duty test alone** — a 1-bit test (`memory/accord-cbe74…:64-74`).

---

## K. RECORD-STATE DEATHS — the firmware was fine; the bookkeeping was not

| # | defect | count / cost |
|---|---|---|
| **K1** | **"Row says UNFLASHED after it flew"** | **SEVEN instances** — V83a, V84, nearly V85, V86, V86B, V89, and V94/V96. 🛑 The seventh **cost work**: it sent an analyst to close a verdict with *"fly V96, S2 answers it"* when V96 had already flown and its regressor was 34× over-range (`BUILD-LINEAGE.md:1103-1110`) |
| **K2** | **`BUILD-LINEAGE-PART1-LEVER-INDEX.md` stops at ~V81** | **V83a → V97 — fifteen builds**, including **every cell the last four sessions moved** (`0xCBE74`, `0xC40D2`, `0xC40BC`, `0xC40D4`, `0xC640A`/`0xC640C`, `0xC63A6`, **`0xC63AC`**) return **NOTHING** to the by-address grep `CLAUDE.md` makes mandatory. It was already backfilled once (V76–V81) before falling ten further behind (`:1112-1119`) |
| **K3** | **a re-cut under the same build number destroys its predecessor's plain image** | OPEN; fix recommended, not applied (`memory/accord-recut-overwrites-the-previous-plain-image.md`) |
| **K4** | **a verified artefact for a superseded design is *more* dangerous than an unverified one** | A real, fully-verified V92 cut (**182/182 assertions**) carried the **old rung map** and was superseded before flight; *"the only tell left in the transcript was a `6ABC` token buried in the old filename"* ⇒ **write the DEAD hash out in full, next to the word DEAD** (`STATE.md:1087-1109`) |
| **K5** | **two artefacts share the V76 build number** and disagree on both cells of RULE 11 | 🛑 *"**A GLOB IS NOT A CHECK.** Any script, diff or ledger that resolves 'V76' by wildcard will pick one of the two arbitrarily and silently answer the opposite question"* (`BUILD-LINEAGE.md:292-296`) |

🛑 **K2 is live right now, and it is directly relevant:** a mandated by-address grep for **`0xC63AC`** — the
V97 cell — **returns nothing from the index the process requires you to check.**

---

# PART 2 — THE TAXONOMY

Eleven distinct classes. For each: the discriminating question, the canonical instance, and the
**cheapest instrument** that settles it.

| # | class | the question that discriminates it | canonical instance | cheapest settling instrument |
|---|---|---|---|---|
| **T1** | **WRONG ADDRESS** | Is the value at this address a *plausible calibration value*, and if it is a table entry, is this the entry or the header? | `gp-0x62f8[]` vs `gp-0x62c8[]` (E6) · `0xC67C8` is `0xC67BE`'s `Y[0]` (E4) · off-by-0x1000 on tp-relative cals, **recurred FIVE times** | Byte-read the value from the **base image** and sanity-check it. *"THE TELL IS THE VALUE"* — 512→2048 is a cal; 2→8 is nonsense (`STATE.md:1036-1041`) |
| **T2** | **RIGHT ADDRESS, WRONG MODE RECORD** | Is this cell reached through a `mode*4` pointer array? | A1–A4: V44, V47, V69, V70, V72, V73 | **Dereference `array + mode*4` on the image and print the mode number beside the address.** Never read the build script |
| **T3** | **GATE NEVER ARMS** | Has the arming condition ever been *observed true* in this kit — with a positive control? | B1 (V64, solved) · B2 (V68, unsolved) | A probe rung on **the gate**, plus a rung whose value is known-positive |
| **T4** | **DEAD ZONE / PRODUCT EXCLUDES THE REGIME** | Is the term exactly zero over the operator's own measured (speed, rate) distribution? | D1 (damper: 0 on 95.91 % engaged, **100 %** of micro) · D2 (`0xC63A0`) | Compute the delivered surface **from the built image** against the route's real distribution. A product needs **every** factor opened at once |
| **T5** | **LANE CARRIES NEGLIGIBLE SIGNAL / INPUT BYPASSES** | What fraction of the delivered command does this lane carry **in counts**, in his regime? | E2 (`0xC63A4`: **1.1 ct of 342**) · E1 (`0xC6194`: partition all-1, 100 % bypass) · E3 · E5 | Counts, not ratios, from telemetry that already exists |
| **T6** | **SILENTLY REVERTED BY A REBASE** | Is the lever present in the **current build's own image**? | C1 (`0x454FE`, 18 builds) · C2 (V62's `sar`) · C3 (seven at V38) | `diff` the built image against stock and against the base; assert every carried lever explicitly |
| **T7** | **NEVER WRITTEN — the ledger lied** | Which *image* carries this byte? | F1 (`0xC6442`, `0xC61F6`: 0 of 65 images) · F2 (V71B/C lack V62's `sar`) | A byte-read across **all** plain images. **RULE 4** |
| **T8** | **TOOL-ZERO** | Did two *independent* tools agree, and was every disagreement adjudicated? | G1 (eleven methods, one wrong answer) · G5 (**15 hits, 0 real accesses**) | Ghidra **and** a raw Python LE scan of both parities, both encodings, plus the `ep`-alias re-test. Set-difference, never union-on-trust |
| **T9** | **VERDICT AGAINST THE WRONG SYMPTOM / BAND** | Which symptom, **in his words**, was this scored against? | I1 (V42 ch.2) · I2 (V47) · I3 (V56: 15–26 Hz, never 6–9) | Name the symptom in the verdict. A band is the instrument, never the verdict |
| **T10** | ⭐ **INSTRUMENT INVARIANT TO THE LEVER** | Write the closed-loop expression for the observable and differentiate it w.r.t. the edited cell. Is `d(observable)/d(cell) ≈ 0`? | J1 (V91/V92: `y = K·α`, invariant to `K`) | Algebra, before the flight. **Zero cost, and it would have prevented V93 and V94** |
| **T11** | **RECORD-STATE** | Does the record agree with the identity bit from the most recent route? | K1 (seven instances) · K2 (index 15 builds behind) · K5 (a glob is not a check) | The mechanical grep in **LIVE-10** below |

**Merged / rejected from the brief's candidate list:**
- *"right cell, downstream clamp/saturation makes it irrelevant"* — **keep, but as a sub-case of T5.** Its
  instance is **E5 (PID Ki, integrator pinned by anti-windup)**; the `0xC6446` rail
  (`STATE.md:900-915`) is the same shape and is a *sizing* limit rather than a liveness failure.
- *"right cell, wrong assumed sample rate"* — **no instance found in the V38→V97 record.** The nearest
  misses are the `0x18F`-vs-`0x14A` **9.15 ms skew** (which inverted a build decision — `STATE.md:1002-1010`)
  and the kit-wide `raw14` off-by-one (`≈28° at 7.79 Hz`). Both are **analysis-side timing** faults, not
  firmware liveness. **Filed as an analysis trap, not a liveness class.**
- *"tool-zero"* — **kept and promoted (T8)**, with G5 as a new sub-class: *a healthy-looking count that
  misses 100 % of accesses.*

---

# PART 3 — 🛑 THE PRE-FLIGHT LIVENESS CHECKLIST

**Mandatory. Every item is answered *in the build spec*, before the `.rwd` is cut.**
Items marked **BLOCKING** stop the build; the rest must be answered but may be answered *"not applicable,
because…"*. Each item names the method that settles it.

---

### LIVE-1 — THE ADDRESS IS THE CELL **[BLOCKING]**
Byte-read the value at the address **from the base image** and state it. Confirm it is a plausible
calibration value; a byte diff reports the **first differing byte**, not the cell address.
If the cell is a table entry, **name the table header address and the entry's index separately.**
Anchor `tp`/`gp` arithmetic against a known value first — `tp = 0xBF000`, so `tp+0x6000` is `0xC5000`.
> Prevents **T1**. Off-by-0x1000 has recurred **five** times; `0xC67C8`-vs-`0xC67BE` is the latest.

### LIVE-2 — THE LINEAGE, FROM IMAGES NOT PROSE **[BLOCKING]**
`grep analysis-2020accord/build_v*_tva.py` for the address **AND** byte-read the cell across **every**
`_v*_plain_image.bin`. State its on-car result and name the images that carry it.
🛑 **The build-script grep alone is insufficient** (RULE 4 found four cals attributed to V39 that V39
never wrote), and 🛑 **a null from `BUILD-LINEAGE-PART1-LEVER-INDEX.md` is not a null — that file is
fifteen builds behind.**
> Prevents **T7**, **K2**.

### LIVE-3 — READER CENSUS, TWO TOOLS, EVERY DISAGREEMENT ADJUDICATED **[BLOCKING]**
Run **both**: (a) Ghidra operand search; (b) a raw Python LE scan covering **disp16 both parities**
(`hw2 = disp|1`, the `0x3C`/`0x3D` opcode-field trap), **the 6-byte disp23 form**, **LE32 absolute
literals**, **movhi/movea synthesis**, and **the `ep`-relative short-format re-test** (`movea imm,tp,ep`
sites within the 254-byte `sld` reach).
Set-difference the two. **Never take the union on trust; never stop at the first tool that answers.**
> Prevents **T8**. G5 is the reason the `ep` re-test is now mandatory: 15 hits, 0 real accesses.

### LIVE-4 — TRACE THE OUTPUT **FORWARD** TO THE MOTOR **[BLOCKING]**
Do not enumerate the cell's readers and stop. Follow each reader's **output** until it reaches
`gp-0x6b98` / the FOC, or is provably terminated. State the hop chain.
🛑 If any hop is described as *"monitor-only"* or *"self-referential state"*, **check whether the
function's own next instructions consume it** — that exact check is what eleven methods skipped on
`gp-0x6b94`.
> Prevents **T8/G1**. RULE 13.

### LIVE-5 — MODE CLASSIFICATION **[BLOCKING]**
Classify the cell **MODE-PROOF** or **MODE-INDEXED**.
If mode-indexed: name the pointer array, **dereference `array + mode*4` on the base image**, and print the
**mode number beside the address**. Bound the sweep by the array's **recorded extent** (the friction array
is 34 slots; `0xCBE74 + 34*4` holds a valid-*looking* pointer to a valid-*looking* record).
The car is **TVCA4**: manual = **24**, engaged = **26**. Engaged and disengaged column sets are
**disjoint across all 16 rows** ⇒ **write the engaged column of every row, or probe the selector. There is
no third option.**
Also state the **mode-proof residue**: in every *other* mode the build is its parent plus that residue
(RULE 10).
> Prevents **T2**. Cost of not having this: V74's fault was misattributed for a full session, `k*` was
> derived from it as a *safe* bracket, and **V75 latched the ECU.**

### LIVE-6 — THE GATE LADDER, WITH A POSITIVE CONTROL **[BLOCKING]**
Enumerate **every** gate between the cell and the motor. For each, state its **measured duty** from
existing telemetry, with the route and the frame count.
🛑 **If any gate has never been observed in its arming state anywhere in this kit, the build MUST carry a
probe rung on that gate — and a second rung whose value is known-positive.** A null with no positive
control cannot distinguish *"quiet car"* from *"dead probe"*.
> Prevents **T3**. V64 cost one drive because it had the rung. **V68 is still open because it did not have
> the control.** RULE 5: *"the build carried the byte" is not a test.*

### LIVE-7 — THE DEAD-ZONE / PRODUCT SURFACE, ON HIS DISTRIBUTION **[BLOCKING]**
If the cell feeds a product, a LERP or a clamped surface, compute the **delivered** surface **from the
built image** over the operator's **own measured (speed, rate) distribution**.
Report: **% of engaged frames the term is exactly zero**, broken out for the **micro-ratcheting regime
(1–13 °/s)** and the **ratcheting regime (13–50 °/s)** separately.
🛑 **A product needs every factor opened simultaneously.** Testing one factor at a time is what made
V86B's damper test vacuous.
> Prevents **T4**.

### LIVE-8 — SHARE OF THE DELIVERED SIGNAL, IN COUNTS **[BLOCKING]**
State how many **counts** of the delivered motor command this lane carries in his regime, against the
total: *"this lane carries X ct of a Y ct signal."*
🛑 **If you compute a dilution factor to argue the COST is acceptable, you have computed the same factor
for the BENEFIT. State both, in the same sentence.**
> Prevents **T5**. `0xC63A4` died at **1.1 ct of 342**. See the V97 appendix below — this item is the one
> V97's spec answered on one side only.

### LIVE-9 — REGIME MATCH, AND INSTRUMENT SENSITIVITY **[BLOCKING]**
Two parts, both required.

**(a) Regime.** In which regime was the lever's *direction* or *size* established, and is it the regime the
operator uses to **elicit** the symptom? The symptom regime is **ENGAGED + HANDS-ON + OVERRIDE at
parking-lot creep** — operator, 2026-08-12: *"Steering override is how I get the steering into such a
scenario where grinding and micro ratcheting can be observed."*
🛑 The kit's default `steeringPressed = |STEER_TORQUE_SENSOR| > 1200` hands-off mask **excludes that regime
by construction** — exposure is **7121.6 s hands-off against 994.9 s hands-on** (`STATE.md:163-171`).
If the direction was measured hands-off, **say so explicitly.**

**(b) ⭐ Instrument sensitivity — write the algebra.** Write the closed-loop expression for the observable
you will score and **differentiate it with respect to the edited cell.** If `d(observable)/d(cell) ≈ 0`,
**the test is void before it is run.**
🛑 Special case: **an edit with DC gain 1.000 at every value (a pole) cannot be verified by ANY amplitude
statistic.** Pre-register a **phase, bandwidth or group-delay** observable instead.
> Prevents **T10** and the D3 shape. **Zero cost. It would have prevented V93 and V94.**

### LIVE-10 — IDENTITY, AND THE NULL PLAN **[BLOCKING]**
**(a)** The build must carry a telemetry signature that proves **single-frame** which build flew, and it
must be *impossible* on the base. (V92's `0x14A byte7[7:6] != 0` is the model; **V91 had none and its
route could not corroborate its own flash.**)
**(b)** Before flight, write the sentence a null will license — **and name the symptom, in his words**, it
will attach to. If that sentence is *"the hypothesis is falsified"*, re-check LIVE-5 through LIVE-9 first.
> Prevents **T9** and the RULE-5 class. *"A verdict without a named symptom is not a verdict."*

### LIVE-11 — CARRY-FORWARD, READ FROM THE BUILT IMAGE
Enumerate the **cumulative** delta vs stock from the **built image**, not the build scripts, and assert
every confirmed fix still present.
When you remove a confirmed fix to run a control, **write the restore into the next build's spec.**
> Prevents **T6**. The V38 rebase reverted **seven**; `0x454FE` has been lost **three** times.

### LIVE-12 — THE MECHANICAL RECORD GATE (at close-out, not at cut)
```
grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md
```
Reconcile against the **identity bit from the most recent route**. Append the by-address row to
`BUILD-LINEAGE-PART1-LEVER-INDEX.md` **in the same pass**. Write superseded hashes out **in full, next to
the word DEAD**. **Resolve build artefacts by exact filename — a glob is not a check.**
> Prevents **T11**. Seven instances of "row says UNFLASHED after it flew", one of which cost an hour of the
> best analysis in its session.

---

### THE ONE-LINE VERSION, for a build spec header

> **A lever is LIVE only when: the address is the cell · the mode record is the one the car reads · every
> gate has been *observed* armed with a positive control · the term is non-zero in HIS regime · the lane
> carries a stated number of counts of the delivered command · the observable you will score has a
> non-zero derivative with respect to the cell · and the build can prove single-frame that it flew.
> Anything less is a bet, and the record says so seven ways.**

---

# PART 4 — WHAT HAS ACTUALLY MOVED A SYMPTOM

🛑 **TWO SEPARATE LISTS. THEY ARE NOT THE SAME THING AND THEY ARE NOT MERGED HERE.**

🛑 **"The ring", "grind #1", "grind #2", "S1…S4" are KIT JARGON for frequency bands. They are not symptoms
the operator named.** His words are: **grinding · vibrating · micro-ratcheting · ratcheting · excess
friction / heaviness**. Bands appear below only as the *instrument* behind a claim.

🛑 **An absence of complaint is NOT a report of improvement.** *"I did not experience any grind #2"* is weak
negative evidence, never a cure.

---

## LIST 1 — INTERVENTIONS WITH A MEASURED ON-CAR CHANGE

*(Instrument readings. A band moving is not a symptom being fixed.)*

| build | route | what moved, measured | direction |
|---|---|---|---|
| **V62** | `37` | **18–22 Hz engaged creep 0.124 [0.036, 0.387] = 8×; at \|rate\| 16–32 °/s 0.024 [0.016, 0.234] = 42×.** 30–40 Hz negative control ~1.0 ⇒ band-specific. Transient rate `\|d(tq)\|>1000` 0.338 [0.135, 0.672] | ✅ improvement |
| **V67** | `47` | grind-#1 band **0.55 [0.34, 0.65]**; creep burst blocks **0 in 113 s** against 24 at Kd = 2× | ✅ improvement |
| **V71C** | — | grind-#1 band **higher** (P = 0.0215); grind-#2 events **returned**; ratchet at **corpus record** | 🛑 worse on every axis |
| **V80** | `66` | **2.09× broadband HF lift** + a **30 s 27.4 Hz limit cycle**; damper `≥448 ct` duty **19.4 % engaged** (V75: 0.000 % over 28,317 frames) | 🛑 worse |
| **V83a** | `68` | **grind-#1 band 2.674× V81 [1.956, 3.885]** (null [0.63, 1.55], 10/10 cells > 1); micro-ratchet band **1.526× [1.174, 2.019]**; 26–31 Hz **flat 1.021** | 🛑 worse — **and its own pre-registered falsifier FIRED** |
| **V84** | `6d` | **26–31 Hz burst duty V80 96.6 % → V81 25.1 % → V84 2.54 %**; longest ring 18.29 → 11.25 → **1.34 s**, on **3.4–4.9×** the exposure. Negative control and IMU falsifier both pass | band moved ✅ — 🛑 **causally unestablished, and the operator said it fixed nothing** |
| **V85** | `6e` | **The lever delivered:** relay saturation **39.5 % → 11.1 % overall, 33.3 % → 4.6 % engaged (7.21×)**, both pre-registered duty predictions hit | ✅ lever confirmed in force — 🛑 **all symptom bands a clean null** (6–9 Hz 1.088 [0.746, 1.451]) |
| **V86** | `6f` | `f(V86)/f(V85)` = **1.001 [0.976, 1.060]**, CI **disjoint** from the pre-registered [0.797, 0.875] | 🛑 **falsified, well-powered** ⇒ the phase-lever hypothesis for the ~8 Hz mode is CLOSED |
| **V88** | `73` | **15–22 Hz delivered command 0.549 [0.407, 0.844]**; grind-#1 band absolute level **150.5 [118.5, 183.8]** vs V67's 110.7 ⇒ **V88/V67 = 1.101 [0.424, 2.206], a clean null against best-in-kit**. **0.5–3 Hz authority 1.192 [0.780, 1.812] = NULL** ⇒ no authority cost | ✅ improvement, **command untouched** |
| **V89** | `75`/`76` | **FLAT** — order-clean stratum contrast **0.947 [0.827, 0.979]** inside a same-build placebo band of [0.900, 1.111] = **0.92σ** | ⏸ null. 🛑 **The block-bootstrap CI excluded 1.00 and would have been reported as a resolvable 5 % fix — the placebo control earned its keep on first use** |
| **V91 / V92** | `78`/`79` | `gp-0x6b26` engaged stratified ratio **0.99 [0.91, 1.26]** vs a pre-registered 1.50; MANUAL control **1.009**; duty flat 0.167/0.161/0.165 | ⏸ read as null — 🛑 **now known to be closed-loop invariance (J1), not an inert lever** |
| **V94** | `7d` | **motor acceleration 3–7× up above 9 Hz**; column-torque ↔ wheel-rate coherence at 18–31 Hz **the highest of any drive in the corpus**. No fault of any kind | 🛑🛑 **much worse** — and it produced **the first measured `d(symptom)/dK` this lever has ever had, and the sign says UP** |

⊕ **Measurement-only builds that changed the kit's knowledge, not the car:** V54 (authority measured = **0
by design**), V55 (**21 Hz confirmed inside the EPS, not commanded**), V87 (the probe fired; `gp-0x6b98` is
broadband), V90 (probe-only, byte-identical to V89 in every calibration cell ⇒ **the kit's largest
same-firmware placebo set**, routes 77/78/79).

---

## LIST 2 — WHAT THE OPERATOR HIMSELF REPORTED, IN HIS OWN WORDS

*(Verbatim. Nothing here is called fixed that he did not call fixed.)*

| build | his words |
|---|---|
| **V38** | (foundation) — later, on V83a: **"Feels just like V38, like we have made no progress since then."** |
| **V42** | **ratchet fixed** — the kit's first confirmed fix (recorded against the *hard-turn recovery* ratchet) |
| **V60** | *"I drove on the V60 RWD. **It did not fix the vibration issue.**"* |
| **V62** | ⭐ **"Original grinding at 2–5 mph is gone!"** |
| **V64** | *"I drove disengaged then engaged after. **The vibration/grinding at low speeds is not fixed.**"* |
| **V65** | *"…makes the entire car vibrate, almost like I have a subwoofer… **happens regardless of LKAS engagement.**"* |
| **V67** | *"Grind #2 seems mostly gone. However… on the way, when doing somewhat significant turns, there is sometimes a resonance… This higher-speed [event] happens when changing lanes or on a somewhat significant turn on the highway. Also is only on during LKAS-engaged. …**Might just be dampened.**"* |
| **V68** | LKAS **off**, manual highway: *"No grind vibration felt"* · LKAS **on**, highway: *"**Definitely felt** the grind #2-like vibration when changing lanes"* |
| **V76** | *"I drove on V76. **There is still grind #1 and micro-ratcheting at creep.**"* |
| **V80** | 🛑 **the worst grinding the car has ever produced** |
| **V81** | grinding in (a) slow turn at stops while braking and (b) highway lane change; **all grinding stopped the instant LKAS disengaged**; adding hand mass did not damp it; **highway instability was the worst part**; LKAS angle rate felt severely limited; **"manual steering much heavier when engaged, even turning the same direction as the LKAS command."** |
| **V83a** | **"Feels just like V38, like we have made no progress since then."** |
| **V84** | 🛑 **"None of these have been fully fixed in V84."** ⊕ and, correcting the orchestrator: **"Not even sure what the ring is. We are working on grinding, vibrating, and ratcheting issues."** |
| **V85** | grinding: *"grind #1 is still barely perceptible"*, *"got a little bit better"* — **still present** · micro-ratcheting: *"seems like it got barely, perceptibly better (somewhat unsure)"* — **still present** · ratcheting: 🛑 **"was still unfixed"** · *"I did not experience any grind #2 from my hard turning or on the highway"* — 🛑 **an absence of complaint is NOT a cure** |
| **V86B** | *"still present, dampened I think"*; **ratcheting definitely perceptible**; second grinding complaint present; ⊕ **"extra dampening on LKAS and in general at slow speed"** — the predicted cost was **felt** |
| **V87** | *"I observed grind #1, micro-ratcheting, and ratcheting."* (predicted — V87 is byte-stock at all four grind cells) |
| **V88** | ⭐⭐ **GRINDING — HE SAYS FIXED.** ⊕ **"Micro-ratcheting and ratcheting… these are the main remaining issues."** ⊕ grind #2: *"hints, could not elicit"* — 🛑 exposure was **47.4 s = 29 % of the 166 s interpretability floor ⇒ formally UNINTERPRETABLE** |
| **V89** | 🛑 **"fixed nothing, still only as good as V88."** |
| **V90** | *"grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on the highway-speed curves or lane changes"* — 🛑 **all three present.** ⊕ V90 is **probe-only and byte-identical to V89**, so this is the **control condition**, not a failed fix |
| **V94** | 🛑🛑 **"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to drive."** — **ABORTED on-car** |
| **V96** | (instrument build) — during this drive he **renamed the target**: *"there is ringing in the driver torque, and a wiggle in the steering angle as it returns to center. Normally, without LKAS engaged, there is no ringing and no wiggle… it feels like effectively a **steer angle rate limit for LKAS engaged**."* |
| **V97** | 🛑 **ZERO difference in grinding or micro-ratcheting**, on a deliberate parking-lot creep with LKAS engaged, provoking the symptoms on purpose |

---

## THE HONEST SUMMARY OF PART 4

**Exactly TWO interventions in sixty builds have both a measured on-car change AND the operator's own
report of improvement:**

1. **V62** — `0x3AB76`/`0x3AC20` `sar 0xa`→`0x9`. Band 8–42× down; **"Original grinding at 2–5 mph is
   gone!"** ⚠ Carried by **V62 and V65 only**, then lost.
2. **V88** — Lever B restored (`0x3AA96` `c5`→`fb` + `0xC6446` 512→5244). Delivered command 15–22 Hz
   **0.549×** with authority untouched; **he says the grinding is fixed.**

Both are **rate-lane, mode-proof, command-side** levers. ★★ **Every measured fix in this kit came from a
MODE-PROOF lever; every mode-indexed lever was inert** (`BUILD-LINEAGE.md:332`).

**Nothing has ever moved micro-ratcheting or ratcheting.** They are reported present, in his words, on
V76, V81, V83a, V84, V85, V86B, V87, V88, V89, V90 and V97 — **and the two builds that moved them moved
them the WRONG WAY** (V83a's micro-ratchet band 1.526× [1.174, 2.019]; V94 aborted).

⇒ **V97 felt like nothing is, statistically, the modal outcome of this arc — not an anomaly.** The
question the checklist exists to answer is *which kind* of nothing it is.

---

# APPENDIX — V97 SCORED AGAINST THE CHECKLIST

Read from `analysis-2020accord/build_v97_tva.py` and `docs/HANDOFF-2026-08-12-v97-the-loop-pole.md`.
🛑 **This is a documentary scoring, not a firmware re-trace** — the crux items are for the tracer.

| item | V97 | verdict |
|---|---|---|
| **LIVE-1** address | `0xC63AC`, 102 = `0x0066` → 150 = `0x0096`; high byte `0x00` in both ⇒ **one byte**; sole reader `ld.hu 0x73ac,tp,r13` @`0x38202`, bytes `e5 6f ad 73` (`hw2 = 0x73AD = 0x73AC \| 1` — the parity trap explicitly handled) | ✅ **PASS**, and the census was **re-tested against the brand-new `ep`-aliasing trap and is clean** (98 `movea imm,tp,ep` sites image-wide, **0** within the 254-byte `sld` reach) |
| **LIVE-2** lineage | **virgin across all 99 images** | ✅ PASS — genuinely new, **not** a re-run in a different direction. ⚠ but see K2: the mandated by-address index returns nothing for this cell |
| **LIVE-3** census, two tools | **1 reader / 0 writers established FIVE ways**, three mutually independent | ✅ **PASS — the best blast-radius census in the arc** |
| **LIVE-4** trace forward | `gp-0x374c += ((target − gp-0x374c) × A) >> 10` → Path-2 accumulator → PID reference | ✅ PASS |
| **LIVE-5** mode | bare `tp` scalar, no index ⇒ **MODE-PROOF** | ✅ PASS |
| **LIVE-6** gate + positive control | 🛑 **NOT ANSWERED.** V96's cave is carried byte-for-byte, but *"its regressor is 34× over-range (M pinned at 0 on 99.9 % of frames) so S1/S2 stay VOID — V97 does not fix that either"* | 🛑 **FAIL — there is no on-car instrument that can distinguish "the pole moved and the car did not care" from "the pole did not move."** This is the V64 ambiguity one layer up |
| **LIVE-7** dead zone | n/a — a first-order IIR coefficient, no product, no LERP index | ✅ n/a |
| **LIVE-8** share of the delivered signal | ⚠ **ANSWERED ON ONE SIDE ONLY.** `build_v97_tva.py:65-67`: *"Path 1 is unweighted and unaffected by A, which **dilutes** the figure to +2 % .. +13 % on the TOTAL command."* That dilution was computed to argue the **COST** is acceptable | 🛑 **The identical dilution applies to the BENEFIT, and it was never stated as such.** No counts figure ("X ct of a Y ct signal") exists for Path 2's share in his regime. **This is the T5 class — the class that killed `0xC63A4` at 1.1 ct of 342.** [BELIEF — my inference from the build's own arithmetic; the tracer should price Path-2's actual share] |
| **LIVE-9(a)** regime | Direction measured on **hands-off engaged returns** (`\|Q\| = 1.233` both routes, coherence 0.974/0.978; `arg(V) − arg(B′) = −178.1°` both routes). The operator provoked the symptom **engaged + hands-on + OVERRIDE at parking-lot creep** | 🛑 **MISMATCH — and it is the V89 pattern verbatim.** `STATE.md:163-171` says that regime is the one *"every `Re(Z)` number this kit has ever produced excluded"* [EVIDENCE for the two regimes; **BELIEF** that the mismatch explains the null] |
| **LIVE-9(b)** instrument sensitivity | 🛑 **DC gain is 1.000000 at any A — it is a POLE, not a GAIN** (stated in the build's own header, correctly, as the reason it escapes the sign problem) | 🛑 **⇒ NO amplitude statistic can verify it, and none was pre-registered.** By T10 this is the **J1 shape**: the property that makes the lever safe is the same property that makes it invisible to every instrument the kit currently runs |
| **LIVE-10** identity + null plan | Identity: inherits V96's cave; V96's identity is proven single-frame (`0x14A` byte7 bit 6 = 1 on **100.0000 %** of 164,096 frames). Null plan: the build states 🛑 **"V97 IS NOT A RETURN-SPEED FIX… Do not score V97 as if it addressed the return speed"** | ⚠ **PARTIAL.** Identity ✅. But the build **explicitly declines to predict** an effect on grinding or micro-ratcheting — it prices only a **COST** at 21 Hz. ⇒ **"felt zero difference in grinding" is not a falsification of anything V97 claimed** |
| **LIVE-11** carry-forward | `BASE = V96`, every cal cell asserted equal to V96's **image**; 131/131 assertions | ✅ PASS |

### ⇒ WHAT THE AUDIT CAN AND CANNOT SAY ABOUT V97

**Can say [EVIDENCE]:**
- A **wrong-address** (T1) or **tool-zero** (T8) death is the *least* likely explanation. V97's census is
  the most thorough in the arc — five methods, including a re-test against the trap discovered the same
  day.
- A **wrong-mode** (T2) death is **excluded**: it is a bare `tp` scalar reached without an index.
- **V97 never predicted a grinding or micro-ratcheting improvement.** Its own header says it is not a
  return-speed fix, prices only a 21 Hz **cost**, and the direction argument is about **anti-damping phase
  on hands-off returns**. ⇒ **"He felt no difference" is consistent with the build working exactly as
  specified.**

**Cannot say — these are the open crux items, for the tracer and the next build [BELIEF]:**
1. **T5 / LIVE-8.** What fraction of the delivered command does the **Path-2 accumulator** carry in engaged
   hands-on override at creep — **in counts**? If it is the ~2–13 % the cost calculation implies, the
   benefit is diluted by the same factor and would be **below the kit's own ±16–22 % resolution floor**
   even if the physics is right.
2. **T10 / LIVE-9(b).** **DC gain 1.000 at every A** means the edit is *only* a phase/bandwidth change.
   **No amplitude instrument can see it, and none was pre-registered.** The next build must carry a
   **phase or group-delay** observable on `gp-0x374c`'s lane, or the question is unanswerable by driving.
3. **T3 / LIVE-6.** V96's regressor is **VOID (34× over-range, M pinned at 0 on 99.9 % of frames)**. Until a
   working rung exists on this lane, **a null on V97 is uninterpretable in exactly the V68 sense** — no
   positive control.

🛑 **The recommendation this audit supports:** do **not** re-dose `0xC63AC` and do **not** file it
FALSIFIED. Both would repeat the arc's most expensive mistake in opposite directions. **File it
UNINTERPRETABLE — a null with no positive control — and spend the next build on the instrument**
(a phase-capable rung on the Path-2 lane, sized to the override regime), exactly as V96 was spent.

---

## OPEN DEFECTS THIS AUDIT FOUND, REPORTED NOT FIXED

1. 🛑 **`memory/accord-cbe74-dose-measured-inert-wrong-mode-record.md`** — its **frontmatter
   `description:`** asserts *"Leading explanation: the ENGAGED mode record is not 26/27"*, which its **own
   body refutes** at lines 39–49. **`memory/MEMORY.md`'s pointer line repeats the stale version.** The
   filename itself encodes the retracted claim. ⚠ This is the same defect shape recorded at
   `STATE.md:883-885`: *"When a `reference_*` fact is corrected, correct BOTH copies."*
2. 🛑 **`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` is fifteen builds behind** — a by-address grep for
   `0xC63AC`, the cell now on the car, **returns nothing** from the index `CLAUDE.md` makes mandatory.
3. ⚠ **`memory/reference-accord-lkas-only-rate-limiter-c6194.md`** records the reason *"output ×0"*, which
   `STATE.md:90` establishes is **wrong** (that is `0xC6196`). The memory has not been corrected.
4. ⚠ **`analysis-2020accord/eps_lkas_chain_model.py` is 309 KB**, past the 256 KB `Read` cap ⇒ an agent told
   to *"read the golden model"* silently gets a truncated tail.
