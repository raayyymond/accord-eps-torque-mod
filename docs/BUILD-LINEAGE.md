# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

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
knowing it was one.** V73 flew clean only because crossing still needed a large motor-rate event
(`gp-0x6c2c` ≈ 6258). **V74 then multiplied the mode-26 friction table (`0xD7A54`) by 1.5, dropping
that to ≈ 4180. V74 and V75 both hard-faulted with latched total loss of assist.** The cell is
**mode-proof**, which is why V74 faulted with LKAS *disengaged* — no mode-indexed lever could have.

**The rule, generally:** before raising any clamp, saturation or output limit, **search for a monitor
that tests the same cell**, and check whether the stock clamp sits just inside that monitor's
threshold. A clamp one count under a fault ceiling is a **design invariant**, not slack to be spent.
Two methods; a null here is load-bearing.

⚠ Corollary: **do not "fix" this by raising `0xC4004` instead.** That loosens the monitor rather than
the signal, and no other consumer of that ceiling has been surveyed.

Full detail: `memory/accord-friction-lane-ceiling-is-the-hard-fault.md`.

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
created by its own earlier fixes.** Grind #2 is V62's `sar`. ⇒ **Before adding a lever for symptom X,
check whether X first appeared in the build that introduced the previous lever. A build that changes
nothing is a real and sometimes correct option.**

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

## 🛑 Ledger corrections, 2026-08-05 — each from a byte read of the build's OWN image (RULE 4)

| # | correction |
|---|---|
| 1 | 🛑 **V69 AND V70 DID NOTHING.** `sar` stock (`aa32`/`aa42`), gate `c5`, arms 512/512, and the only edit is `gain_B` **mode 10** ⇒ **byte-stock behaviour**. The recorded *"clean single-variable r24 series ×1→×2→×4 = 879/729/746, CIs overlap ⇒ r24 is near-inert"* was **three replications of ONE condition.** ⇒ **r24's dose is UNTESTED, not near-inert** |
| 2 | **V72's two-lane row is `r24 ×1.000 / r26 ×0.250`**, not `3.414 / 0.250` — its r24 half was mode-10 `gain_B`. Its grind-#2 result is therefore **confounded with stock**. 🛑🛑 **THE SECOND HALF OF THIS ROW IS RETRACTED 2026-08-06:** it read *"what governs grind #2 is V62's `sar`, which V72 does not carry"* — **that is hypothesis (A) and it is REFUTED.** `V71C` carries **neither** `sar` byte (`0x3AB76` = `aa32`, `0x3AC20` = `aa42`, byte-read) and produced a spectrally identical grind-#2 event: **44.31 Hz**, p99 **1741.9** = **12.2×** the max of any non-bursting build, against a same-segment non-burst floor of **25.5**. V71C holds **3 of the corpus's 13 merged events in 5.28% of the exposure, P(≥3) = 0.028.** ⇒ **a `sar`-stock build is NOT safe by construction** |
| 2b | **V62/V65's delivered r24 is `×2.000`, not `×3.414`** — `sar 0xa → 0x9` is a **flat doubling of BOTH lanes at every speed and rate** (mode-proof, one instruction each), not the `0xC6446` arm. The 3.414 figure was the *arm* value copied across the whole column. ⇒ **the two-lane rule's "r24 ≳ 3.4×" threshold is WRONG — V62/V65 burst at 2.000×.** The rule's *shape* ("both lanes elevated") survives; its *numbers* do not. Rebuilt table: `docs/STATE.md`; model: `analysis-2020accord/_grind2_delivered_lib.py` |
| 3 | ★★★★ **V42's fix was the r26 KILL, not `0x454FE`.** V42 vs V41: `gain_A` **all four records → `[0,0,0,0]`**, `0xC643E` 1536→0, `0xC6444` 512→0, plus a revert of V41's motor-rate cap. `0x454FE` never executes. **This closes a two-session [OPEN]** — and V42 ch.2 sat in this table marked *FALSIFIED* the whole time (see RULE 7's last paragraph) |
| 4 | **V72/V73's r26 cut is PARTIAL** — `gain_A` `rec0`/`rec1` → flat 512, but **`rec2` `0xC6A90` and `rec3` `0xC6AA4` are byte-stock** ⇒ the cut is **creep-only by record selection**; at and above ~50 km/h r26 is untouched |
| 5 | **`tp+0x71b2` IS load-bearing** — LKAS reaches the motor via the second accumulator `gp-0x62b0[ch]` → `gp-0x3d88` → `gp-0x6b4c`. **No V14 correction is needed** (one was proposed and withdrawn). Lineage byte-verified over 66 images: stock **512** → **1024 by V22** → **2048 at V38**, `0xC61B2`/`0xC61B4` always in lockstep. ⚠ The V14/V15 first step is build-script prose only — no image exists before V22 |

---

## 🛑🛑🛑 RULE 9, added 2026-08-06 — **THE GRIND-#1 FIX AND GRIND #2 HAVE NEVER BEEN SEPARATED**

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
Scripts: `analysis-2020accord/grind2_collinearity.py`, `grind2_delivered_verdict.py`,
`grind2_delivered_census.py`.

---

## 🛑🛑 RULE 6, added 2026-08-05 — **A LEVER IS ONLY IN FORCE IF THE CAR READS THE TABLE YOU EDITED**

**V72 raised the base-assist damper at creep. The bytes were correct, the arithmetic was correct, the
CRC passed, and the car never read them.**

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`, where `mode = *(byte)(gp + 0x63fd)`. **There are 13 mode variants.** V72
edited **modes 10 and 11 only**, because `39990-TVA-A160` *reads as* row 2 `'TVAA1'` in the config table
at `0xCD000` ⇒ modes 10/11.

🛑 **That part-number → key mapping is an ASSUMPTION recorded in this file. It was never a measurement.**
`build_v44_tva.py` has patched modes 10 **and** 11 since V44 *because of it*, and every damping build
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

**FALSIFIED** = flashed and demonstrably changed nothing for its target symptom. It is not "untested".

> **RULE 2, added 2026-07-30:** the table below covers **V9→V58 only**. Levers rejected in the
> **pre-V18 era** live in `memory/project_accord_torque_mod_v0.md`, and their absence here let a
> subagent re-propose `0xC61D6` — a lever an 11-round review had labelled *"highest-risk; last/never"* —
> as a fresh candidate. **The pre-V18 rejections are now folded into the table.** If an address is not
> here, grep `analysis-2020accord/old_tools/build_v*.py` and `memory/project_accord_torque_mod_v0.md`
> before calling it untested.

| address | what it is | build | flashed? | on-car result |
|---|---|---|---|---|
| ★★★★ **`0xC63A0`** stock **1024** → **2048** (V72) → **1024** (V77) | **the DAMPER's weight in PATH 2** — `tp+0x73a0`, the `gp-0x6bd0` term of `FUN_00038148` stage 1's six-term sum `Σ (x · gate · w) >> 10`. **MODE-PROOF: a bare `tp` scalar reached without an index ⇒ live in MANUAL and ENGAGED alike** (RULE 7). **1 reader (`0x381AC`), 0 writers, no monitor, no float mirror.** The **odd one out of six siblings** `0xC63A0`–`0xC63AA`, all stock 1024 — **the only one any build has ever moved** | **V72** (→2048) · **V77 / V77B** (→1024) | ✅ carried at **2048 by V72, V73, V74, V75, V76** | 🛑🛑 **THE GATE-2 SUSPECT, AND IT WAS INVISIBLE FOR FIVE BUILDS.** V72 doubled it, nothing reverted it, and the second-aggregator row below asserted *"all weights unity and stock"* the whole time (corrected 2026-08-06). ⚠ **It was only FUNCTIONALLY ARMED AT V74.** Path 2's damper term is `(gp-0x6bd0 · gate · w) >> 10`, and `gp-0x6bd0` was **0 at creep on every build through V73** (both FactorC/FactorE dead zones shut) — **×2 on zero is zero.** V74 opened both dead zones ⇒ **V74 is the first build where the doubled weight carried signal, and V74 is the first hard fault.** [EVIDENCE for the plumbing, the byte lineage and the arming; **BELIEF** for the causal link to the fault.] ⇒ **revert = −6.02 dB, ZERO phase change, ZERO cost to Path 1** — the term that actually delivers the damping is the `FUN_0003aa2c` aggregator's, **unity weight, zero phase, untouched.** 🛑 **OPEN, and the highest-value next trace: `0xC63A0` does NOT touch the RE-ENTRY term.** `gp-0x6b98` re-enters via `FUN_0003b8f6` **one sample later**, which is what makes Path 2 a **closed loop inside the firmware**; reverting the weight lowers the forward gain and leaves that term **unquantified** |
| **V77** = V74 base + `0xC63A0` **2048 → 1024** | ★★★ **single-variable, and the first build in this lineage aimed at LOOP GAIN rather than DOSE.** Reverts V72's undocumented doubling of the damper's Path-2 weight; everything else is **V74 byte-for-byte**. `V74 → V77 = 2 runs / 5 bytes` (`0xC63A1` `08`→`04` + `0xC6FFC` CRC). ⚠ **The edit is ONE CELL and ONE BYTE, not two** — `2048 = 00 08` and `1024 = 00 04` LE share their low byte. ***Count cells, not bytes.*** | **V77** | ⏳ **BUILT 2026-08-06, UNFLASHED** | 🛑🛑 **NOT CLEARANCE TO FLY.** rwd `fd8db4e2ed140035782a55b2e6808bcf87a0ea85692cbe547960a13de1cfc8c5`; image `a0f7c09c038931cabc419ccf79d4bb9819e647e88c0fb817ebc23cd44d102782`. **No build in the current lineage has demonstrated safety** — V74's *"flew 1,011 s clean"* is **withdrawn** (it hard-faulted) and V75 latched the ECU. What the build has going for it: it removes **the one mode-proof residue that could act in MANUAL**, which is where V74 faulted (RULE 10), at **−6.02 dB and zero phase**. What it does not have: **the Path-2 re-entry term is still unquantified**, so GATE 2 here is **ARGUED, NOT CLOSED** |
| **V77B** = the SAME `0xC63A0` revert on the **V75** base | keeps V75's dose (`FactorC Y[0]` 429→566, `FactorE X[1]` 400→200) and backs the loop gain off | **V77B** | ⏳ **BUILT 2026-08-06, UNFLASHED** | 🛑🛑 **NOT RECOMMENDED, and not clearance to fly.** rwd `f2c2dc0ba4f5e01bbd95925b8e42c1323a1b6b99bf658b795aa25cb2fa539dd7`; image `acbc218751af827d5ddc696e24d6ae44f11ef06dc04e11a3b383d366b4d4fc10`. It stacks the revert on **the base that hard-faulted**, so a clean drive could not separate *"the weight was the problem"* from *"the V75 dose is survivable"* — **two variables, one drive.** It exists so the pair is on the record, not as a candidate |
| cave payload @`0xC4B34` → the **boost-index DEPTH probe** | `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense "index < T"; monotone bit5⇒bit4⇒bit3, so a wrong build is detectable rather than plausible) | **V59** | ✅ **FLASHED 2026-07-30, route `2c`** (this column previously read UNFLASHED — stale, corrected 2026-08-01) | **NO calibration change** — 19 bytes off V58, cave + MAIN CRC only, **CAL CRC unchanged** (machine proof). Same base/hook/68-byte extent as V55/V57/V58, all flown clean. **No new encoder and no new condition code** (BGE + BNE only, both pinned to real instances). Answers the one thing V58 could not: **DEPTH.** `gp-0x6ba6 == \|gp-0x6b9a\|` indexes both boost amplitude LERPs, and V58 showed the signed sibling crosses zero at 20.93 Hz only when LKAS applies ⇒ the index is that signal rectified, sweeping the curve at ~2× the mode frequency. But a sign bit carries no amplitude: **if `\|gp-0x6b9a\|` never clears X1 = 512 the coefficient stays pinned at 16384 and NOTHING modulates.** Build asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| cave payload @`0xC4B34` → the **angle-rate/boost-lane probe** | `0x14A` byte4: bit7 liveness, **bit6 = `gp-0x6bbe < 0` (the damping phase)**, bit5 = `gp-0x6bbe == +512`, bit4 = `gp-0x6b9a < 0`, bit3 = `gp-0x6b9a == 0` | **V58** | ✅ **FLASHED 2026-07-30, route `2b`** | ✅ **FLIGHT-CLEAN** — 14 segments, 83,959 frames, zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`; `STEER_STATUS == 0` in 83,959/83,959 and **`ST==4` = 0** (extends V57's 0/37,922). ★★ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED**; `K1` keeps its headroom. 🛑 **bit6 VOID BY CONSTRUCTION** — `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s, so the damping sign is **still open**; ⚠ pooling the runs manufactures a splice artifact (5/0/0/1 transitions *within* runs). ★★ **bit4 fired**: 20.93 Hz, per-run coherence 0.649/0.970/0.769/0.881, and **13.69 toggles/s engaged vs 0.61 disengaged** at matched creep. 🛑 **This build's own docstring was WRONG about `gp-0x6b9a`/`0xD28DC`** — corrected in place; see `STATE.md` "Signal-identity corrections" | **NO calibration change** — 59 bytes off V57, cave + MAIN CRC only, and the **CAL CRC is unchanged** (machine proof). Same base/hook/68-byte extent as V55 and V57, both fault-free. Exists because every cal lever for both symptoms is closed and the `gp-0x6bbe` damping sign flipped three times under static analysis. Measures it on-car instead: cross-spectrum phase of bit6 vs `STEER_ANGLE_RATE` (already on the bus). **Method pre-validated** — V57's bit3, also a 1-bit sign channel, gave coherence **0.958 at 21.31 Hz**. bit5 decides whether `K1` is a lever at all: the ±512 ceiling is a SATURATING clamp, so if the lane pins, the damping derivative is ZERO at the peaks and the lever becomes the ceiling `0xD20C0`, not `K1`. Decoder `rlog-tools/decode_v58_boostlane.py`. RWD SHA `7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7` |
| 🛑 **`0xC61D6`** slew step `0` → 14 | `FUN_00042af8` delivered-command slew limiter, accumulator `gp-0x356c` | **V16** (`old_tools/`) | ❌ **REJECTED ON REVIEW, NEVER FLASHED** | 🛑🛑 **DO NOT PROPOSE. "Highest-risk lever; last/never."** An 11-round, 4-analyst, decode-verified Ghidra review found slew=0 **FREEZES** a dormant speed×torque 2D shaping lane (curves `0xC6770`×`0xC69E8`); 0→14 **ACTIVATES an uncalibrated map onto the live command** (mux `0xC64C9`=0). Byte-verified 2026-07-30: **`0xC61D6` = 0 in V31/V38/V42/V53/V55/V57** — stock throughout. ⚠ `.claude/agent-memory/…/reference_accord_slew_limiter.md` still *recommended* this; corrected 2026-07-30 with a header, addresses kept |
| `0xC6424` shaper deadband 29491→20000 | gates only the `gp-0x356c` limiter | **V17** (`old_tools/`) | ❌ rejected | **INERT** — with slew=0 that state is pinned at 0, so the edit is behaviourally null. **Deadband and slew are COUPLED**; neither is independently useful |
| `0xC64DE` re-engage ramp `0x11`→`0x1B` (17→27) | **LENGTHENS** re-engage; targets the **recovery ratchet**, not the initial snap | **V18** | ✅ | ✅ **ROAD-VALIDATED — "drives well."** Byte-verified 2026-07-30: still **27** in V31/V38/V42/V53/V55/V57, carried forward correctly. ⚠ Targets the ~10 s recovery ratchet — **wrong timescale for the ~7.4 Hz ratchet** |
| **`0xC4018`/`1C`/`20`** and **`0xC4048`/`4C`/`50`** | two **3-tap FIR** coefficient triples (32-bit floats), `FUN_0003b66a` / `FUN_0003b8f6` | — | ❌ never in any build | 🛑 **NOT A NOTCH LEVER — closed on arithmetic 2026-07-30.** Both are stock **(1.0, 0.0, 0.0) = identity**, exactly one consumer each, no variant-coding. It is a genuine transversal FIR (`y = b0·x[n]+b1·x[n−1]+b2·x[n−2]`, states `gp-0x365c`/`gp-0x3658`), **not a 2-pole IIR**, so it is unconditionally stable — but at **1 kHz** a 21 Hz notch needs `b = [1, −1.9826, 1]`, which costs **−35.2 dB at DC** (21 Hz is 2.1% of Nyquist, so the zeros sit essentially at DC). Normalising to unity DC needs `b ≈ (57.5, −114.0, 57.5)` with **229× peak gain**. Ill-conditioned; would amplify HF motor-rate noise. ⚠ A third float `1.0` at `0xC4024` is **not** an FIR coefficient — it is an EMA alpha in `FUN_00023850` (an unrelated PID) |
| **`0xD2006`** 102→**43** | ★ **the boost-amplitude BLEND rate** — `0xCA06C[mode 10]`. The slew on the **output** of BOTH amplitude LERPs, applied before they multiply anything. **Was not in the golden model at all until 2026-07-30.** Direction confirmed @`0x34be4` (`cmp r25,r10 / ble` ⇒ instant snap when raw ≤ old): **FALLING instant, RISING slowed** — a fast-attack/slow-release gain reducer | **V60** | ✅ **FLASHED 2026-07-31 → NULL. Do not re-flash** (this column previously read UNFLASHED — stale, corrected 2026-08-01) | Attenuates the 42.19 Hz parametric pump **without moving the static gain map** (the blend converges to the same steady state ⇒ DC assist and manual feel untouched). Q10 0.0996→0.0420; 42 Hz transmission ~0.37→~0.17; τ 10.0→23.8 ms @1 kHz. Predicted **eps p99 0.169 → 0.099**. 🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so it buys ~1.7× then flattens (cal 32 only reaches 0.086); **43 is the knee**. **5 bytes off V59** (1 cal byte + its `[0xD2000,0xD2FFC)` block CRC); ⭐ **MAIN and CAL CRCs both UNCHANGED** = machine proof the cave/probe and every `0xC6xxx` cal stayed put. GATE 1 vacuous. GATE 2: base-assist path, no LKAS-only fork exists — but a pure *dynamics* change on a gain-**scheduling** variable, no added gain, no static-map movement, no steady-state change. Blast radius byte-verified: one pointer (`0xCA094`); the three identical 102s in `0xD2000` are modes 10/11/12's **independent** entries, not an array. ⚠ **Expected to be NULL** given the loop finding — fly it as a **DISCRIMINATOR**. V59's probe rides along unchanged as the CONTROL |
| `0xC63A0`–`0xC63AC`, `0xC64AD`–`0xC64B3`, `0xC6200` | weights/gates on the **second aggregator** chain `FUN_00038148` → `gp-0x6b70` → `FUN_00037fe6` → `gp-0x6ad6` → `FUN_0003a382` → `gp-0x6ad4` | 🛑 **`0xC63A0` HAS been in builds since V72 — see its own row** | ⚠ the rest never in any build | 🛑🛑 **CORRECTION 2026-08-06 — RULE 4 CLASS, AND IT RAN THE DANGEROUS WAY.** This cell used to read *"⚠ Genuinely untouched — and NOT recommended. All weights are **unity (1024 = 1.0) and stock**, byte-read ⇒ **no hidden loop gain in the aggregation.**"* **That is FALSE, and it has been false since V72.** The six sibling weights `0xC63A0`–`0xC63AA` are stock **1024**, but **`0xC63A0` — the weight on `gp-0x6bd0`, the DAMPER — was set to 2048 by V72 and never reverted until V77.** Every build **V72 → V76** therefore carries **+6.02 dB of extra loop gain inside `FUN_00038148`**, while this row asserted the opposite for five builds. ⚠ **AND "already tested end-to-end by deletion" DOES NOT HOLD EITHER:** V56's `0xC6AF0` mute deletes `FUN_0003a382`'s contribution, but **`FUN_00038148` stage 1 is UPSTREAM of it**, and the chain's re-entry — `gp-0x6b98` back in via `FUN_0003b8f6` **one sample later** — closes a loop **inside the firmware** that no mute in this kit has ever opened. **Kept as written and still true:** the chain's only output-shaping cal is `0xC6AF0` (V56: NULL on the grinding + cost damping); `gp-0x6ad4` has only 2 accesses image-wide; and boost **and** damper re-enter this second aggregator in parallel with `FUN_0003aa2c` — ⚠ but **"at unity gain" is now wrong for the damper.** ⇒ **Do not cite this row as evidence of a flat aggregation. See the `0xC63A0` row** |
| `0xC6372` / `0xC636E` | boost + damping lane input EMAs (both 205) | — | ❌ | 🛑 **DEAD BRANCH — do not analyse or edit.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. The EMA still computes into its shadow pair but its result is never consumed. Any GATE-2 phase/dB table for these two cals is analysing a lever with **zero effect** |
| `0x2A1F0` disp `0x746C`→`0x7CD0` + `0xC6CD0`←3564 + `0xC646C`→891 | **the `0xC646C` DECOUPLING** — forward LKAS path gets a private gain word; the four feedback readers revert to stock | **V57** | ✅ **FLASHED 2026-07-29, route `29`/`2b`** (this column previously read UNFLASHED — stale, corrected 2026-08-01) | 🛑 **CORRECTNESS FIX — expected NULL for the grinding** (≤0.28 dB at 22 Hz; of the **11** aggregator summands only `FUN_00036682` reads the cal, at −46 to −58 dB). Reader set independently re-enumerated: exactly **6** (1 forward, 1 dead in the `>0x2a30d` dead-copy region, 4 feedback). ✅ **no float mirror** — fresh 32-bit scan of `[0x7440,0x74A0)` → 0 hits ⇒ no V27 desync class. ⚠ **manual feel WILL change** (readers #3-#6 are not engagement-gated). ⚠ Reader #6 is **not** a second additive path — it modulates #5's hysteresis dead-band *width*. **Flash V55 first** | ⊕ **ALSO CARRIES THE DEADBAND-GATE PROBE** (V55's cave payload replaced, same base `0xC4B34` / hook `0x55C0E` / 68-byte extent): `0x14A` byte4 bit7=liveness, **bit6=(gp-0x6806==0) — the EXACT gate test the bus cannot give**, bit5=(gp-0x69b0!=0), bit4=(gp-0x6b30==0), bit3=(gp-0x6b30<0). Closes the parity hole in the deadband elimination (the packer's `andi 0x1` transmits bit0; the gate tests equality). Expected NEGATIVE |
| **`0xC6AFC` + `0xC6AFE`** 32768→0 | `FUN_0003a382` output-bound LERP Y[0]/Y[1] — the **branch-agnostic mute** of the whole `gp-0x6ad4` lane | **V56** | ✅ | 🛑 **FALSIFIED FOR THE VIBRATION *AND* HARMFUL — 2026-07-29, route `24`.** 21 Hz unchanged (**786×** engaged/disengaged speed-matched, vs V55's 877×) and the command's 21 Hz did **not** drop ⇒ **the lane is ELIMINATED as the 21 Hz source, all three branches at once.** ★ It also **cost damping**: operator reports damping removed, and an intermittent **8.69 Hz** line appears (1.18e8, 6.7× its neighbours, 15-20 m/s, engaged+hands-off). **REVERT TO V55.** 🛑 A 50% partial restore (`Y=16384`) is **not** a candidate — 0% and 100% already agree, so intermediate authority is bounded between two agreeing measurements |
| `0xC6450` | `FUN_0003a382` **Stage-A = the P term's own extra smoothing EMA** (1024 = exact unity) | **V46** | ✅ | ⚠ **RE-FRAMED twice.** 1024→32 = −12.6 dB at 21 Hz, one of three branches — *and* 2026-07-29: it was **re-introducing a defeated pole**, not filtering the lane. Moot now: V56 eliminated the lane |
| `0xC644A` | `FUN_0003a382` **Stage-C = the D term's own extra smoothing EMA** (1024 = exact unity) | **V43** | ✅ | ⚠ **RE-FRAMED — same reason.** 1024→64 = −7.1 dB, one branch of three. Moot: lane eliminated by V56 |
| `0xC643E` / `0xC6445` + `0xC6A72/86/9A/AE` | `r26` adaptive torque-rate gain surface | **V42** ch.2 | ✅ | ★★★★ **THIS IS V42's ACTUAL FIX — RE-ATTRIBUTED 2026-08-05. [EVIDENCE, V42-vs-V41 byte diff]** V42 zeroed **all four `gain_A` records** (`0xC6A68`/`0xC6A7C`/`0xC6A90`/`0xC6AA4` → `[0,0,0,0]`) plus `0xC643E`→0 and `0xC6444`→0 ⇒ **the r26 rate lane was KILLED**, and `gain_A` is **not** mode-indexed so it was **LIVE**. ch.1 (`0x454FE`) never executes ⇒ this is the only live candidate for V42's confirmed hard-turn-ratchet improvement (with the V41 motor-rate-cap revert as a confound). 🛑 **The "FALSIFIED" below was against the VIBRATION and was never scored against the RATCHET** — see RULE 7. **Superseded reading:** 🛑 ~~FALSIFIED.~~ ⚠ **RE-PROPOSED AS "NEVER PREVIOUSLY PROPOSED" BY A SUBAGENT ON 2026-07-29** — r24/r26 are the two *unfiltered, 1 kHz, same-signed* torque-rate summands, so they look irresistible in any fresh lane audit. **They are both already flashed and null.** V42's own builder records why the combined-kill argument is weak: *"r24 carries a ±3 DEADZONE (cal `0xC61F6`) which is why V39's r24 kill was a no-op near zero"* — so V42 already killed the branch that was live near zero. 🛑🛑 **DIRECTION CORRECTION 2026-07-31: the combined kill WAS eventually run (V61) and it made the grinding WORSE, in engaged AND manual driving.** This lane is the mode's **damper**. The nulls above are real but they bracket the **wrong side of the optimum** — every one of V39/V42/V61 tested it DOWNWARD. **Cutting this lane is closed for good; RAISING it is V62.** ⚠ Note this is the *inverse* of the FactorC/V44 trap: there a withdrawn **rationale** was mistaken for a withdrawn **result**; here every result stands and only the **direction** was wrong. Both errors come from the same habit — reading a lever's history as a verdict on the *address* instead of on the *direction tested* |
| `0xC6440/42/46`, `0xC61F6` | `r24` direct Sensor-B rate lane | **V39** | ✅ | 🛑 **FALSIFIED** — and near-inert by construction (±3 deadzone). See the r26 row's re-proposal warning. ⚠ **DIRECTION CORRECTION 2026-07-31 — see the V61/V62 rows below: this lane is the mode's DAMPER and V39 tested it DOWNWARD.** |
| `0x3AB6C` `37E1`→`37E0` + `0x3AC16` `4001`→`4000` | **kill the torsion-bar RATE lane at BOTH taps** of its shared `r1 = clamp(gp-0x4f62, ±5120)`. Two single-bit reg1 `r1`→`r0` changes, no cave | **V61** | ✅ **FLASHED 2026-07-31** | ★★★ **WORSE — the kit's FIRST SIGNED on-car result, and it INVERTS the record.** Operator: grinding *significantly worse* with LKAS on (higher amplitude, louder), **and newly present in MANUAL driving** — unmistakably **in reverse**. ⇒ **r24/r26 are the mode's DAMPER, not its amplifier.** Sign verified from image bytes: polarity `gp-0x6752` is **one load @`0x3AB78` reused by both lanes and by `FUN_0003a382`'s P-term** (so it *cancels*), and the combine chain `0x3ACC8`–`0x3ACDA` is **ten `add`s, no `sub`** ⇒ `+Kd·d(T_bar)/dt` in phase with assist. For the wheel-inertia-on-bar mode that gives `phi'' + (Kd·k/J_c)·phi' + … = …` — **positive damping, linear in Kd; at Kd=0 there is no damping term at all.** 🛑 **A derivative is DC-neutral**, so "V61 removed assist" is ruled out — it changed *only* dynamics, which is what makes this a clean signed measurement. 🛑 **Falsifies `eps_lkas_chain_model.py:1792`'s "r26 = excitation-to-amplifier" framing** (struck and corrected in place). ⇒ **V39, V42 and V61 all tested this lane DOWNWARD**; their results stand but bracket the **wrong side of the optimum**. The gradient points **UP** |
| `0xC4B34` cave payload → **the oscillation-detector probe** (V63's cals unchanged) | ★★★ **V63 + telemetry that makes a NULL interpretable.** `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x671a >= 5` (the raised arm is selected) · **bit5** `gp-0x671a != 0` · **bit4** `gp-0x67df != 0` (FSM left neutral ⇒ `\|gp-0x6c2c\|` crossed ±12800) · **bit3** `gp-0x671d != 0` (r24's override active) | **V64** | ✅ **FLASHED 2026-07-31** | 🛑🛑 **NULL ON THE GRINDING — AND THE PROBE SAYS WHY: THE DETECTOR NEVER ARMED.** Route `35--77808fe7ce`, 14,980 frames / 149.8 s, all creep, disengaged-then-engaged. `0x14A` byte4 = **constant `0x87`, zero variance**: bit7 liveness **set**, bits 6/5/4/3 **all clear on every frame**. ⇒ `\|gp-0x6c2c\|` never crossed `T` and **the two cal edits were never in force for one frame.** ⇒ **this is a null on the GATE, not on the damping hypothesis** — the direction V61 signed is still untested on-car. Confirmed 4 ways (byte histogram · `decode_v64_detector.py` · independent raw-CAN rederivation · V59's probe ruled out, its bit5 was set essentially always vs 0/14,981 here). Spectra agree independently: **V64 ≡ V59** — engaged creep 21.30 Hz / 149× / 4.31e8 vs V59 21.18 Hz / 227× / 5.26e8, and in the best-populated 2–3 m/s bin **20.98 vs 20.99 Hz, env99 1811 vs 1804**. V61's spread into manual driving is **gone**. FLIGHT-CLEAN: `ST==4` 0, all six watched events 0, CAN 100.03 Hz. ⚠ **bit3 = 0% ⇒ r24 WAS covered** (the `gp-0x671d` override was idle). ✅ **The detector genuinely ran** — its whole body is gated on `FUN_00046ea6(5)==0`, which briefly looked like an alternative explanation; closed by raw byte scan of all **47** `jarl` sites (Ghidra found 44 — the known undercount): **bit 5 has exactly ONE caller image-wide, the detector itself**, and the only dynamic indices are cals `0xB9A14-16` = 0/2/6. ★★★ **Operator's proposal, and it fixed V63's fatal weakness.** V63 still carried V59's thermometer on `gp-0x6ba6` — the parametric-pump index **V60 already falsified** — so a V63 null could not distinguish "the detector never tripped" from "the rise was too small". **Actionable in EVERY failure mode:** bit4 clear ⇒ lower `T` (`0xC620A`); bit4 set + bit6 clear ⇒ lower `CEIL` (`0xC64FA`); bit6 live but no improvement ⇒ the rise was too small; bit3 set ⇒ also raise `0xC6442`. All single cal bytes. **60 bytes off V59** (50 cave + 2 cal + 8 CRC), **54 off V63 (cave + MAIN CRC only — CAL block byte-identical to V63, machine-verified)**, 90 off V38. Same base `0xC4B34` / hook `0x55C0E` / **68-byte extent** as V55/V57/V58/V59, all flown clean; **68/68 used, zero budget left.** GATE 1 vacuous (read-only; sole write is the existing CAN payload byte, bits 2:0 preserved). ⭐ Orchestrator-verified from the built image: all three cave loads decode to `gp-0x671a`/`gp-0x67df`/`gp-0x671d` and the `gp-0x671d` halfword is **byte-identical to the real instance @`0x3AB98`**. ⚠ **V850 `ld.bu` carries displacement bit 0 in `hw1` bit 5, not `hw2`** — a naive decode reports false mismatches on a correct build. Decoder `rlog-tools/decode_v64_detector.py` leads with **time-to-first-set** and **whether it ever clears** (occupancy saturates once the latch sets). 🛑 **Start the log BEFORE the first engagement.** Image SHA `e9dcd3b6…`; RWD SHA `7abbeba6…` |
| `0xC6440` 2048→**4096** + `0xC643E` 1536→**3072** | ★★★ **raise ONLY the OSCILLATION-DETECTED gain arms** of both rate lanes. Both lanes' gain priority chains end in `assist_state gp-0x671a >= 5`, and `gp-0x671a` is a **HARD-REVERSAL COUNTER** (`FUN_000428d4`, 1 kHz: the neutral state resets it to 0 **every tick** and only exits when `\|gp-0x6c2c\| > 12800`; a crossing of the *opposite* threshold increments it; 50 quiet ticks clear it). ⇒ it reads **0 during smooth steering**, so `state>=5` = **an oscillation is happening**. 🛑 **BUT THE OUTPUT IS A ONE-WAY LATCH WITH A 5 s HOLD** (output stage `0x429A0`–`0x42A12`): once held reaches CEIL it is re-pinned every tick, and the only way down is 5000 consecutive ticks (cal `0xC6270`) with driver torque ≥ 640 (cal `0xC62DE`) AND no reversals — torque dips below 640 on every direction change, so it is **sticky**. ⇒ the honest claim is *"V62, but only after an oscillation has happened"*, **not** "only while oscillating"; an earlier entry claimed the stronger thing and it is withdrawn. ✅ The latch is **protective** — a per-tick-gated gain would modulate *at* the mode frequency, i.e. a parametric pump | **V63** | ❌ superseded by V64 — **and V64's drive proved BOTH INERT. Do not flash either for the damping.** | 🛑🛑 **THE WHOLE OSCILLATION-GATED APPROACH IS CLOSED ON THIS THRESHOLD.** V64 carried these exact cal bytes and flew 2026-07-31: `gp-0x671a` and `gp-0x67df` read **zero on all 14,980 frames**, so the `state>=5` arms were never selected and these two cals never applied. ⚠ **AND EVEN IF ARMED, THE DELIVERED RISE IS SMALL** — byte-read defaults at the hands-off-creep LERP axis (X=0): **r24 default `0xD2AEC` = 2305** vs the osc arm's 2048, and **r26 default `gain_A` rec0/rec1 = 3072** vs the osc arm's 1536. ⇒ **Honda's oscillation arms are gain REDUCTIONS, not boosts**, so V63/V64 largely *cancel Honda's own de-escalation*: r24 ×1.78, **r26 ×1.00 (a no-op)** — against V62's clean ×2 on both lanes under every arm. 🛑 **Correction to this row's own earlier claim: "3072 is already `gain_A`'s own stock maximum" is right but was read as reassurance; it actually means r26's raise reaches only the value the LERP already gives at low driver torque.** ★★★ **Built in response to the operator's objection that V62 changes MANUAL feel to fix an LKAS-specific symptom — and it removes that cost by construction.** Raising only the `state>=5` arms adds damping **only while oscillating**; both smooth-steering LERP defaults stay stock. **A smaller edit than V62**: 6 bytes off V59 (2 cal bytes + CAL CRC), ⭐ **MAIN CRC UNCHANGED** = machine proof no code moved; V62's shifts and V61's kill both asserted absent ⇒ independent, not layered. ✅ **No new arithmetic risk — 3072 is already `gain_A`'s own stock maximum**, so worst-case `stage1×gain` stays at 47% of INT32_MAX. GATE 1 vacuous. 🛑 **POLARITY WAS DISPUTED BY TWO SUBAGENTS AND RESOLVED BY THE ORCHESTRATOR IN GHIDRA** — one trace read `0xC643E` as the `state<5` arm, which would have raised the **smooth-steering** gain: all the manual-feel cost, none of the benefit. Verified: `0x3AA7C cmp r14,r12`/`bc` ⇒ `r2=1` iff `state>=5`; `0x3AB66`/`0x3AC10` `be` skip the loads when `r2==0`. 🛑 **Residual — a NULL IS AMBIGUOUS:** whether `gp-0x6c2c` crosses ±12800 in the real vibration is unverified; if not, V63 is **inert**. **Resolve with no probe and no cave: fly V63 first, then V62 if null.** 🛑 `gate_671d` outranks r24's arm and is live ⇒ **expect r26 to carry it**. Image SHA `2f843bce…`; RWD SHA `5e5f83d7…` |
| 🛑🛑 **INERT — THIS BUILD CHANGED NOTHING. [EVIDENCE 2026-08-05]** `gain_B` is **mode-indexed** and these cells are **mode 10**; the car is **mode 24/26**. With `sar` stock, gate `c5` and arms 512/512, **V70's delivered behaviour is byte-stock.** See RULE 7 and ledger correction #1. · **`0xD2A7E`/`0xD2A80` 12288→6144** and **`0xD2ABA`/`0xD2ABC` 10244→5122** (mode-10 gain_B 0 and 10 km/h records, Y[0..1], **×2**) — gate `0x3AA96` stays `c5` and arm `0xC6446` stays 512, i.e. **V69's gateless topology at HALF the dose** + the cave rewritten as the **SIGN probe** | **V70** — the first build aimed at ALL THREE grinds at once. `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6ada >= +512` (ratchet SIZE + the positive control V69 never had) · **bit3** `gp-0x6ada >= 0` (SIGN — ratchet PRESENCE, amplitude-independent) · **bit5** `gp-0x67fa == 10` (the RTOS state gate) · **bit4** `gp-0x6adc >= 0` (SIGN — r26 liveness) | **V70** | ✅ **BUILT 2026-08-04, UNFLASHED** | ★★★ **BUILT ON AN OPERATOR OVERRIDE, AND THE OVERRIDE WAS RIGHT.** A first V70 restored V67/V68's control path; the operator rejected it — *"V70 just reverts back to V68, which has the high-speed grind #2 issue"* — and that build is now `SUPERSEDED-DO-NOT-FLASH-…-V68CONTROLPATH-…rwd` (image `8bfcb1fa…`, RWD `d716b1a5…`). 🛑 **THE LESSON, and it generalises: an instrument null inside a band the instrument cannot resolve is NOT evidence of absence.** CAN's Nyquist is 50.00 Hz and the comma IMU's 50.51, so both vibration instruments are **blind above 50 Hz**, while the acoustic inversion places the excess at **63.5 Hz [54, 80]** — on `gp-0x6c2c`'s 61 Hz band-pass peak. The operator is the only instrument in that band and his reports are a **dose–response**: the high-speed grind is present on V67/V68 (**2.44×** at highway) and he reported it **GONE** on V69 (**1.000×** = stock). ★ **The arithmetic agrees a scalar arm is the worst-shaped lever for that symptom**: it REPLACES a surface Honda rolls off 3072→2151, so `arm/LERP` **rises** with speed and peaks at highway (2.206× at creep → **2.436×** at highway), and the rate lane is a differentiator whose gain climbs with frequency. **Delivered multiplier, re-derived from the image:** grind #1 (rk 603) **1.836×** (2.000× on the alternate axis scale) · grind #2 creep (rk 1206) **1.282×** · engaged highway **1.000×**. ⇒ **it attacks all three rather than trading them**: highway is *structurally* stock (2-point record interpolation reads only rec2/rec3, untouched); grind #1 sits on the dose–response minimum near 2× that V62 flew to *"the original grinding at 2–5 mph is gone"*; and grind #2 creep gets **less than half V62's 2.00× that caused it**, because the edit raises only the flat `[0,400]` rate segment while **19 of 24** recorded bursts sit at rateKey ≥ 1126 — **better than V62 there, not a trade.** ★ **Sweep-asserted over 24,321 points: MAX anywhere 2.000000×, MIN 1.000000×** ⇒ every point inside the flown bracket [stock, V62/V65] and **never below stock**; all 12,221 points at ≥3200 counts **byte-identical to stock** on either axis scale. ★ **Halving also repairs V69's one regression vs V68**: peak gain 6144 rails at `\|dtorque\|` **1365** vs the recorded max 839 (margin **1.63×**), where V69's 683 sat *below* it; the builder now asserts `sat > 839`. ⚠ **Honest limits:** the high-speed evidence is the operator's **perception**, not an instrument (legitimate given the >50 Hz blindness, but the mechanism is inferred from the arm's shape, not measured); **1.836× at grind #1 is an interpolation** — the record has no measured dose between 2.00× and 4.00×; and the ×2 is exact only at the edited records' breakpoints, bounded to **0.0195%** between them (`divq` truncates toward zero). ★ **Build identity solved from the value set alone**: `bit3 = sign(gp-0x6ada)` is guaranteed non-constant ⇒ the hard invariant **bit6 ⇒ bit3** makes `bit6=1, bit3=0` an IMPOSSIBLE frame ⇒ **V53/V54/V65/V66/V67/V68/V69 excluded absolutely**; residual V55/V57/V58/V64, filename-only, 6+ builds back. 🛑 **One-bit trap live on THREE rungs**, incl. `ld.bu` 0x3C / `st.b` 0x3A on `gp-0x67fa` (128 readers); all asserted by value in builder and verifier, and both `ld.h` rungs sit on **zero-reader** mirrors. ✅ V70 vs V69 = **64 bytes**, 56 functional + 8 CRC, **0 unattributed**; 50/50 CRC, **77 anchors PASS**, RWD round-trips, reproducible bit-for-bit. ⭐ **Orchestrator verified first-hand from the image**: topology, surface, the full V69↔V70 diff and the CRC walk. image `3760d9c0…`, RWD `0bdfb0da…`. ✅ **FLASHED 2026-08-04, driven route `50--50f2e00e8f`** (segs 0–2, **181.6 s**, 18,010 frames; **seg 0 is PARKED**; engaged **72.4 s** / manual **107.8 s**; engaged creep **28.9 s**; highway ≥50 km/h **7.9 s**; **zero manual highway**). **FLIGHT-CLEAN** (`ST==4` 0, `ST==3` 0, gridded *and* raw `0x18F`; watchlist absent). 🛑 **GRIND #1 IS BACK AT THE STOCK LEVEL** — median `e_18-22` engaged creep **729.1**; resampling V70's exact 5-block structure from each arm gives **CONSISTENT** with stock (P = 0.635) and V69 (P = 0.495), **EXCLUDED** from V62/V65 and from V67/V68 (both P = 0.0000); survives (effort, \|rate\|)-matching. ⚠ the 24–28 Hz negative control is **not flat** (V70 1.88× stock — provoked steering raises the floor), subject-band **excess over control** vs V62 still **2.59×**; ⚠ on the scale-free 18-22/24-28 ratio V70 (37.4) sits *below* stock (76.0) — **that view does not rank-order the builds the way `e_18-22` does; report both, pick neither.** **GRIND #2: 0 bursts, max 94.6 vs V62/V65's 1830.7 — but "gone" is NOT established** (P(0) at V62's own rate = **0.34** engaged-creep / **0.56** corner / **0.98** highway; power 66/44/**2**%), and V67 had already eliminated engaged-creep grind #2 (P(0) = 0.0005) so this **replicates**, it does not credit V70. **RATCHET: Q ≈ 40 at f0 = 7.793 Hz** (see Part 2). ⚠ **"Stiffer" is not detected by any bus-side instrument** — effort/impedance 0.79–0.97× every predecessor, all CIs containing 1 |
| cave `0xC4B34`-`0xC4B77` → the **4-bit SIGN probe** (carried by every V70 cut; the build itself is the row above) | **V70's PROBE** — `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6ada >= +512` (`sar 0x9`; r24 lane out, post-clip) · **bit5** `gp-0x67fa == 10` (★★ **THE STATE GATE**) · **bit4** `gp-0x6adc >= 0` (**r26 mirror SIGN**) · **bit3** `gp-0x6ada >= 0` (**r24 mirror SIGN**, reusing the already-shifted `r6` — valid because `sar` preserves sign) | **V70** | — probe design, unchanged across V70 re-cuts | 🛑 **NO SHAs OR BUILD STATUS HERE ON PURPOSE — they change on every re-cut; the row above is the build.** ★★ **68 of the proven 68 cave bytes, ZERO spare**, base/hook/extent unchanged. ⭐ **Re-decoded from the image independently of the builder**: loads @`0xC4B38`/`0xC4B4C`/`0xC4B58` carry opcodes **`0x39` (`ld.h`) / `0x3C` (`ld.bu`) / `0x39` (`ld.h`)** on `gp-0x6ADA`/`gp-0x67FA`/`gp-0x6ADC`, `ld.bu` displacement parity handled (`hw2 = 0x9807` encodes `disp = 0x9806`), and **exactly ONE store in the cave** — `st.b` @`0xC4B6E` to the CAN payload byte `gp-0x1514`; **no `st.h` (`0x3B`) anywhere.** 🛑 **The one-bit trap is live on THREE rungs**, incl. **`ld.bu` `0x3C` vs `st.b` `0x3A` on `gp-0x67fa`, which has 128 readers** — a slipped opcode there writes the ECU state variable. ★ **V70 is structurally SAFER than V69 here**: V69's third rung read `gp-0x6ad4`, which the aggregator *consumes* @`0x3ACA8`, so a slip would have corrupted a live lane; **V70's two `ld.h` rungs are both on ZERO-READER mirrors**, where a slip could only produce a wrong reading. ★ **BUILD-CLASS IDENTITY FROM THE VALUE SET ALONE — a first for this kit**: `bit3 = sign(gp-0x6ada)` is **guaranteed non-constant** ⇒ the hard invariant **bit6 ⇒ bit3** (`bit6 = 1, bit3 = 0` is an **impossible frame**; only **12 of 16** payloads reachable), which excludes **absolutely V53, V54, V65, V66, V67, V68, V69** — every build from V65 on, **including the one on the car**. ⚠ Residual, kept on the record: **V55/V57/V58/V64** span all 16 payloads ⇒ **filename-only**, six-plus builds back; strictly smaller than V69's residual but not zero. 🛑 **And it cannot separate two V70 cuts from each other** — their caves are identical, so **build-class identity is not file identity.** 🛑 **bit4 IS THE SIGN, NOT A MATCHED `+512` THRESHOLD — a deliberate deviation from spec**: the cave was **exactly 2 bytes short**, and a `>= +512` null on r26 was the *predicted* outcome given `0xC6564` = 40 zero bytes, i.e. straight back into the uninterpretable-zero class that wasted all three of V69's rungs. **COST, STATED: V70 gives r26 LIVENESS, not the quantitative `a`** — **bit4 ~ 1.000 while bit3 toggles ⇒ r26 inert**; **bit4 tracking bit3 ⇒ r26 live** and V67/V68's gate has been cutting damping **6×**. ★ **UNPLANNED BENEFIT**: bit3 is **amplitude-independent**, so it carries the ~7.4 Hz line even when the lane never reaches +512 ⇒ **bit6 measures the ratchet's SIZE, bit3 its PRESENCE** — *if bit3 detects and bit6 does not, the ratchet is real and small*, which no prior probe could have said. 📋 **PRE-REGISTERED: bit5 reads LOW.** V67's `gp-0x6806` tracked `latActive` at **99.983%**, which a flag going stale in state 10 could not do ⇒ **bit5 ~ 0 ⇒ the five-build detector null is GENUINE and those builds are vindicated; bit5 materially non-zero ⇒ the nulls were on the gate.** **Non-vacuous in both directions** — the failure every V69 rung shared. 🛑 **THE SUPERSEDED FIRST V70 `.rwd` (`…LKASGATED-V68CONTROLPATH…`) IS STILL IN THE FLASH DIRECTORY and its cave is byte-identical to the current one** ⇒ the probe cannot separate them on-car; **rename it `SUPERSEDED-DO-NOT-FLASH-…`.** ⚠ It is also now unverifiable by the kit's own gates — both cuts write `_v70_plain_image.bin`, so the newer one **overwrote** the older image and only the `.rwd` survives. ⚠ **Lesson: a builder writing a fixed `_vNN_plain_image.bin` silently destroys the previous cut of the same version number.** Decoder `rlog-tools/decode_v70_probe.py`. ✅ **FLOWN, route `50`, 18,010 frames — READOUTS:** 🛑🛑 **bit6 = 0/18,010 AND IT IS NOT VACUOUS** — a replay through the **shipped** surface driven by **route 50's own data** predicts **311 hits**, **stock predicts 52**, and `\|dtorque\|` off a 100 Hz grid is a **lower** bound so the gap cannot be closed ⇒ **delivered gain < ~1574 Q10, below stock's 3072**, and **`0xC6442` = 1024 (the `gp-0x671d` mask arm) is the ONLY arm predicting exactly 0.** ✅ the identification is not at fault (`0x3AC42`–`0x3AC54` = `r24 = clamp(r6, ±0x2000)`, `0x3AD5A st.h r24,-0x6ada,gp` stores exactly that, r24 unclobbered) ⇒ 🛑 **the FOURTH probe in a row to return an uninterpretable zero by reading a lane OUTPUT — read the GAIN IN FORCE instead.** ★★ **bit5 (`gp-0x67fa == 10`) = 0.0000%**, encoding independently verified ⇒ the aggregator ran ⇒ state ∈ {4,5,11} ⇒ **`FUN_00036388` and `FUN_000428d4` WERE INVOKED** ⇒ **the `gp-0x67df` detector nulls on V64/V67/V68 are GENUINE and the state-gate explanation is REFUTED** — five builds vindicated, on a **pre-registered** prediction. ⚠ it licenses *"the call was made"*, not *"the body ran"*: `FUN_00046ea6(5)` on `gp-0x18d0` bit 5 stays **OPEN**. ★★ **bit4 tracked bit3 ⇒ r26 is LIVE** — `gp-0x6adc` strictly negative on **1,644/18,010** frames, and a pinned-zero cell cannot clear a `>= 0` test; **`bit3 ⇒ bit4` holds STRICTLY** (0/18,010 with r24 ≥ 0 while r26 < 0) |
| 🛑🛑 **INERT — THIS BUILD CHANGED NOTHING. [EVIDENCE 2026-08-05]** Same as V70: the `gain_B` cells are **mode 10** and the car is **mode 24/26**, so the "×4 dose" was never delivered. **The recorded non-monotone dose–response does not exist.** See RULE 7 and ledger correction #1. · `0x3AA96` `fb`→`c5` (**REVERT** the gate to the dead `gp-0x683c`) + `0xC6446` 5244→**512** + **`0xD2A7E`/`0xD2A80` 3072→**12288** and **`0xD2ABA`/`0xD2ABC` 2561→**10244** (mode-10 gain_B 0 and 10 km/h records, Y[0..1], **×4**) + the cave `0xC4B34`-`0xC4B77` rewritten as the **RATCHET probe** | **V69** — the highway lane-change fix: stop delivering a FLAT arm that peaks at highway, and shape Honda's own speed schedule instead. 🛑 **RE-CUT 2026-08-04 ON TWO OPERATOR INSTRUCTIONS: dose ×2→×4, and the probe re-aimed from the GRIND detector to the RATCHET.** `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6ada >= +4096` (r24's LANE OUTPUT after its ±0x2000 saturating clip — **0 readers / 1 writer image-wide**) · **bit5** `gp-0x6b62 >= +4096` (return-to-centre, ±0x2000 ZERO gate — **the operator's own hypothesis, never probed in 69 builds**) · **bit4** `gp-0x6ad4 >= +4096` (the UNFILTERED residual lane — ~~±0x2800 ZERO gate~~ 🛑 **STRUCTURALLY VACUOUS, see Part 2**) · **bit3 CONSTANT 0** | **V69** | ✅ **FLASHED 2026-08-04, driven route `4f--61171e660d`** | ★★★★ **ON-CAR RESULT — GRIND #1 IS BACK AT CREEP AND THE DOSE–RESPONSE IS NON-MONOTONE.** 8 segs, 481.7 s, 47,990–47,996 frames. ✅ **FLIGHT-CLEAN two ways**: `ST==4` **0** and `ST==3` **0**, gridded *and* on the raw un-gridded `0x18F` stream; watchlist absent; `steerSaturated` 2 / `steerOverride` 667 ordinary. ✅ **Build identity from the probe**: byte4 = `0x87` on **100%** of frames, bit7 set, **bit3 = 0 ⇒ V68 excluded absolutely**; V66/V67 excluded **empirically** (their bit6 ≈ `latActive` at 99.98% and `4f` is **345.7 s engaged with bit6 = 0 in every frame**); V69-×2 excluded **structurally** (`0xC4B54` `61`→`60` makes bit4 constant 1). ★★ **THE DOSE WAS FULLY DELIVERED — saturation ELIMINATED**: transfer-corrected `\|dtorque\|` max **633.9**, **0.0000%** above the 683 rail ⇒ ≥99.9% of engaged time got the full **4.000×**. The pre-flight 0.81× margin worry did not bite, so **the result cannot be explained as clipping.** 🛑 **GRIND #1 IS BACK**: engaged pooled 18–22 Hz **f0 20.42 Hz, prominence 13.47** (criterion >4), f0 identical across all 8 search bands, manual arm **1.25 = no line**, present in **6 of 8** segments (absent only on the pure-highway seg 6). Order veto cleared by the **engaged-vs-manual, within-route, speed-matched** contrast a tyre cannot fake: **4.726 [1.082, 18.20]** vs null [0.36, 3.24], with the 24–28 Hz negative control and 1–4 Hz validity both inside. Against the other builds: **V69/Kd2 (V62+V65) 1.381 [1.026, 1.724]** (null [0.83,1.16]), **V69/Kd2-gated (V67+V68) 1.654 [1.244, 2.167]** (null [0.88,1.13]), and **at creep <20 km/h vs V62/r37 alone 2.244 [1.438, 3.191] (block) / 2.235 [1.533, 3.429] (episode) — holding under BOTH resampling units.** ⚠ **The ALL-SPEEDS headline loses its CI under the conservative episode unit ([0.870, 2.598]); the creep result does not.** ★ **"Lands on stock at ≥50 km/h" CONFIRMED** — 1.066 [0.690, 1.677] vs the Kd1 pool and 0.789 [0.515, 1.252] vs V59/r2c, both inside null, validity passes. ⚠ The *"elevated vs V67/V68 at highway"* half is **WEAK** — its 24–28 Hz negative control moves as much as the subject band; **do not lean on it.** ★★★ **THE DOSE–RESPONSE IS NON-MONOTONE**, median `e_18-22` engaged creep: 0× (V61) **2501** · 1× stock **879** · 2× (V62/V65) **168** · 2× gated (V67/V68) **109** · **4× (V69) 746** ⇒ **minimum around 2×**. ⚠ cross-route medians without covariate matching — read them beside the matched contrasts, not instead. ★★ **THE EFFECT IS ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT**: V69's 4× applies identically in both arms, yet **manual at 4× is indistinguishable from stock (1.070 [0.383, 1.396], inside null)** while engaged is 2.244× ⇒ **the mechanism is inside the CLOSED LKAS LOOP, not open-loop damping quality.** 🛑 **Mechanism NOT uniquely determined — BELIEF, with the dose–response as the EVIDENCE.** Two candidates fit: **(a)** a plain derivative-feedback optimum overshot; **(b)** a **parametric gain collapse** — `gp-0x6ac0` is loaded **`ld.hu` (UNSIGNED) @`0x3AAC4`**, so the gain index sweeps **0→peak→0 twice per cycle**, and V69 turned Honda's 2.0× rate rolloff into **8.0×**, making the damper **weakest at peak velocity**; modulation depth at `A_rk` 1927 = **1.00×** (V67's flat arm) / **1.49×** (V62) / **5.96×** (V69), effective-gain crossover at `A_rk` ≈ **1300** (orchestrator) and **1200–1330** (RateLaneTrace, Fourier on the integer chain — two methods). 🛑 **GRIND #2: a REPLICATION, not a result** — creep 0 bursts at engaged P(0) = 0.0042, but **V67 already gave 0 bursts in 158.7 s at P(0) = 0.0005**; the corner cell is **under-powered on `4f`** (engaged 26.9 s P(0)=0.128, manual 42.2 s P(0)=0.079). ★ Genuine non-regressions: **4× did NOT re-introduce creep grind #2** (engaged max 142.2 vs V62/V65's 1830.7), and V69's manual creep is the **first DOSED manual arm since V65** — 0 bursts in 69.1 s, max **50.5**, lowest of any pool, 29× below V62/V65's 1469.6, P(0) = 0.0512 (*just short*). 🛑🛑 **V69's STATED PURPOSE FAILED — the ~28 Hz lane-change transient is DOSE-INDEPENDENT.** It survived and is **LARGER in p-p on V69** (2,599 and 4,094 counts vs V68's recorded 1,468), and **it runs at full amplitude on the STOCK rate lane**: V58/r2b at dose 1.000× gives ×floor p90 **14.93**, max **22.76**, **2,389 counts p-p @27.59 Hz**, and **V59/r2c at 1.000× carries the corpus's largest p-p, 3,283 @27.07 Hz** — non-monotone (V62 at 2.000× is *quieter* than V58 at 1.000×). Pooled speed-matched: **2.000×/1.000× 1.176 [0.641, 2.320]** inside null; **2.403×/1.000× 2.897 [1.271, 11.439]** does not clear; route-level Theil-Sen slope on dose **+5.736 [−25.432, +34.934]**, **0 inside**. ★ **Excitation, not gain, is the live candidate**: within dose = 1.000× exactly, **ALC vs driver-commanded = 2.389 [1.453, 4.898]** (null [0.44, 2.26], does not clear, one manual route), and holding excitation fixed collapsed the 2.403× contrast **2.849 → 2.013** with the CI crossing 1 — *"an excitation contrast wearing a dose label"*, the same class as the withdrawn 28 Hz "mode". ⇒ 🛑 **V70 MUST NOT CHASE THE RATE LANE FOR THIS SYMPTOM.** 🛑🛑 **ALL THREE PROBE RUNGS FAILED — see the bit4-vacuity box in Part 2.** ⇒ **DO NOT RE-FLASH V69 FOR GRIND #1.** Full narrative: `docs/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md`. ⊕ Original build note follows. ★★★ **BUILT AGAINST A CAPTURED SYMPTOM.** Route `4e` seg 33 t = 51.3 s, an openpilot ALC right lane change at 25.93 m/s: bar **1468 counts p-p**, 26–30 Hz envelope **614** (20× the route median), lines at 27.73/**28.12**/**28.51** Hz at prominence **100–107**, while **40–49 Hz reads 69 in the same window**. Not wheel order 2 (24.93 Hz) or 3 (37.40) — the 37.10/37.49 Hz lines in that same window ARE order 3, so the estimator finds orders when they exist — and not engine order 1 (26.10) or 2 (52.20). 🛑 **THE DESIGN IS FORCED, not chosen.** The gate branch `0x3AC04-0x3AC0C` is `cmp`(2)+`be`(2)+`ld.hu`(4)+`br`(2) = **10 bytes, zero slack**, and it **REPLACES** the LERP rather than scaling it ⇒ speed shaping can only reach the engaged lane if the gate is OFF. Composing *gated AND speed-shaped* needs new instructions on the 1 kHz path — a cave, the only bricking class. **Rejected.** ★ **THE HIGHWAY 1.000× IS STRUCTURAL, NOT TUNED**: the lane-change point (93.35 km/h = 5980 counts) lies in the cross-axis `[3200,6400]` segment, so the interpolation there reads **only rec2/rec3**, which this edit does not touch. Proven by a **12,221-point sweep**, not argued. ★ **AND IT DOES NOT BET ON THE OPEN AXIS SCALE** — the inner axis's counts-per-deg/s is [OPEN] (4.7121 vs 0.58901); V69 doubles the whole flat `[0,400]` segment rather than leaning on a breakpoint, so its creep dose is **2.000× on BOTH scales**. Multiplier: **2.000× to 10 km/h** → 1.886 @15 → 1.769 @20 → 1.526 @30 → 1.270 @40 → **1.000× at and above 50 km/h**. **MAX anywhere = exactly 2.000×** ⇒ inside the `[stock 1.00×, V62/V65 2.00×]` bracket, both flown flight-clean. 🛑 **~~Design A~~ (`0xD2ABC` alone → 7051) REJECTED on three counts**: its hump is **2.753×** (recorded as ~2.45×, which is only its value at 128 deg/s), it swings 2.00×→1.22× across the two axis scales, and at **\|rate\| 16–32 deg/s — where V62's fix measured LARGEST (42×)** — it delivers only **1.1–1.5×** because its boost is a ramp starting at the axis-400 breakpoint. Region min/median: V69 **1.75/2.00** vs Design A **1.09/1.45**. ⚠ **THE COSTS, STATED**: (1) **manual steering below ~50 km/h now gets the rate damping** — the operator was shown this trade with the cave alternative priced and chose it; manual highway is byte-identical to stock; (2) **saturation margin drops 1.91× → 1.63×** (peak gain 6144 saturates at \|dtorque\| 1366 vs the recorded max 839) — the one metric where V69 is WORSE than V68; (3) on the pessimistic axis scale **manual creep and creep grind #2 are both 2.000×**, exactly the dose V62/V65 flew. 🛑 **EDIT-ORDER INVARIANT, asserted in the builder**: writing `0xC6446 = 512` while the gate stays repointed leaves the arm **LIVE at ~5× BELOW the stock LERP** — worse than stock everywhere. 🛑 **NEIGHBOUR TRAP**: mode 11/12's 0 km/h records are **BYTE-IDENTICAL** to mode 10's, so the target pattern occurs **3× within 40 bytes** — every cell is addressed absolutely and all 8 neighbours asserted; `diff_build_vs_stock.py` is **span-based** and would not catch a stray hit. ✅ **GATES**: GATE 1 **vacuous** (no cave growth, no new instruction, no RAM claimed); GATE 2 — **phase unchanged everywhere** (no filter, pole, delay or `sar` edited), magnitude bracketed by two flown builds, 2f parametric-pump depth 1.122 vs stock 1.032 (Design A 2.753). ✅ **NO FLOAT MIRROR** on any Y value in four encodings over the whole image — a mirror must carry ALL the values and 2561/2247/1947/2322/1400/3000 are absent in every one; X values DO have f32 hits, which is why V69 edits **Y only**. ✅ 50/50 CRC across **3 blocks**; x31 PASS; **the RWD decodes exactly back to the image** and every gate re-runs on the readback. ✅ `verify_v69_image.py` **all value anchors PASS** (incl. `0xC6564`, which `verify_v68_image.py` does NOT check); `diff_build_vs_stock.py v69` **0 unattributed**, self-test still fails informatively. **8 edits / 11 changed bytes.** 🛑 The mechanism is **SUGGESTIVE, NOT ESTABLISHED** — the 26–30 Hz maneuver dose ratio is **3.334 [1.201, 6.492]** inside a split-half null of **[0.33, 3.36]**; the operator was offered the drive that would settle it and declined. Spec + 6 pre-registered predictions (2 negative controls): `docs/V69-DESIGN.md`. Image SHA `e6bcb2dd…`; RWD SHA `a0a7fd92…` 🛑🛑 **THE ×4 RE-CUT, AND WHAT IT COSTS.** Shape unchanged — **4.000× to 10 km/h → 1.000× at and above 50 km/h**, both axis scales, no hump. But **(a) the flown bracket is BROKEN**: at 2.000× GATE 2's magnitude leg interpolated between stock (1.00×) and V62/V65 (2.00×, flight-clean); **4.000× extrapolates to twice the largest dose ever driven**. Phase untouched, the lane is linear, V65 measured the aggregator never railing (120,049 frames), grind #1's dose-response monotone through 2.00×. **(b) SATURATION CROSSES THE RECORD**: peak gain 12288 rails r24 at \|dtorque\| **683** vs the recorded max **839** (margin **0.81×** ⇒ *it can rail*; at ×2 it could not). ⚠ every \|dtorque\| here is a **LOWER BOUND**. **(c) manual creep 4.000×** on the pessimistic scale. ★ **bit6 measures (b) on-car.** ⇒ **THE PROBE RATIONALE:** the grind detector is exhausted — `gp-0x67df` has **never** been non-zero in this kit (0/53,991 V68, 0/186,321 V67) so its null is uninterpretable; and **the ratchet is the one symptom a 100 Hz channel can RESOLVE** (~7.4–7.6 Hz ⇒ ~13.5 samples/cycle, so each bit's own series carries the line). The ratchet is **symmetric + amplitude-saturated** ⇒ a hard nonlinearity in the loop; V65 killed the aggregator SUM, but **each lane's own gate/clip upstream of the sum has never been measured**. 🛑 **ONE-BIT TRAP, LIVE HERE:** `ld.h` 0x39 vs `st.h` 0x3B, and `gp-0x6ada`'s only real instance IS the `st.h` with **the same displacement halfword** — asserted by value in builder AND verifier. **Cave 66 of the proven 68 B, extent NOT grown.** Decoder `rlog-tools/decode_v69_ratchet.py`, linked mechanically (the build FAILS on a stale `CAVE_HEX`). 🛑 **Residuals:** rungs are **one-sided**; **bits 5/4 have no positive control**; V69-vs-V66/V67 is **not structural** (V68 is excluded absolutely). Image SHA `48bb4192…`, RWD SHA `e62fcbba…`. |
| `0xC4B34` cave payload → the **4-LEVEL SYMMETRIC SATURATION LADDER** on `gp-0x6b94` (V62's two `sar` edits carried byte-identical) | **V65** — `0x14A` byte4: **bit7** liveness · **bit6** ≥ +8192 · **bit5** ≥ +4096 · **bit4** ≤ −4097 · **bit3** ≤ −8193, against the aggregator's own ±10240 clip | **V65** | ✅ **FLASHED, driven routes `3a--4e55c1e0f4` + `3b--a4a7f4dbf1` 2026-08-01** | ★★★ **THE PROBE ANSWERED: THE AGGREGATOR NEVER RAILS.** 120,049 frames, orchestrator-verified from the caches: liveness **100%** (`field == 0` on 0), **zero** invariant violations (`bit6⇒bit5`, `bit3⇒bit4`, never-both-sides), **+RAIL 0 / −RAIL 0**. Only **54** frames pass ±4096 (48 negative, 6 positive). `bit6↔bit3` alternation **0.0000 flips/s in every arm** — engaged-creep, manual-creep, corner-engaged, corner-manual — and not as a small number: **no rail frame exists**, so no flip sequence and no computable flip frequency. The sum never comes within 20% of its own clip. ⇒ **THE LOOP IS LINEAR AT THE AGGREGATOR**: no describing-function or saturation reasoning is needed in this chain, and a **linear gain change on any lane propagates faithfully** — which is precisely why V62's flat ×2 produced its band table. ★ **All 54 non-neutral frames sit INSIDE grind #2 bursts**, at **36.3–106.1×** the segment-median 30–49 Hz envelope (54/54) ⇒ the aggregator's only large excursions on either route are grind #2, independent corroboration that it is a real large-signal event **in the command path**, not only a sensor-side resonance. 🛑 **DO NOT apply V65's pre-committed *"all four quiet ⇒ NOT another lane gain"* clause to grind #2** — that branch was written to test whether the **RATCHET** is a rail-to-rail limit cycle, and grind #2's attribution rests on an **on-car dose-response on exactly a lane gain** (Kd 0/1×/2× → 40–49 Hz **11.71×**, p = 0.0003, replicated on 3 routes and on the comma IMU). **An intervention outranks an inference drawn from a different hypothesis.** What the null *does* close: the **ratchet** cannot be amplitude-saturated **at the aggregator** (if it saturates, it is further downstream), and the `0xD2AEC` gain_B **breakpoint** lever loses its *clipping* rationale. ⚠ **Stroboscopic caveat, real:** 100 Hz sampling a ~43 Hz burst **cannot** claim the sum touched ±4096 only 54 times — the true count is higher and the peak under-estimated. The **route-wide ±8192 null is unconditional**; *"never rails during a burst"* is the weaker claim. **Quote the null, never the 54 as a rate.** ⚠ `decode_v65_saturation.py` still prints its constant-`0x87` STOP text (its guard is a >99%-fraction test, not a distinct-value test); byte4 is **not** literally constant here (three distinct legal payloads) so this is not V64's frozen null — but confirming the flashed `.rwd` filename is cheap and should be done before this carries a build decision. ✅ **FLIGHT-CLEAN — V65 ADDS TO THE ZERO-EME STREAK**: `ST == 4` **0/120,049**, confirmed a second way by a raw-CAN recount off the `0x18F` src-1 frames rather than the gridded cache; `STEER_STATUS` only ever 0 or 3, every `ST == 3` in a park/reverse segment; zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`immediateDisable`; one `controlsMismatch` per route; three `steerSaturated` on 3b seg 5; `latActive` 88.2%/75.4%; CAN 99.94–100.04 Hz. ⚠ Route `3b`'s **highway starts seg 3 (t ≈ 25 s) — exclude segs 3–12** from parking-lot statistics; the demos are 3a segs 3/4 (LKAS **ON**, six bursts) and 3b seg 2 (LKAS **OFF**, `latActive` 0.00) |
| `0x3AA96` `c5`→`fb` (repoint the DEAD `gp-0x683c` gate to `gp-0x6806`) + `0xC6446` 512→**5244** | **V67** — V66 + the grind #1 fix **gated on LKAS**; both `sar` sites left STOCK | **V67** | ✅ **FLASHED 2026-08-01, driven route `47--3e0b6134c0` 2026-08-02** | ★★★★ **ON-CAR RESULT 2026-08-02 — THE BEST BUILD THIS KIT HAS MEASURED.** 26 segments / **150,327 frames** / 1,495 s, an ordinary street→highway→street→parking-lot commute. ✅ **PROBE LIVE AND LEGAL**: byte4 takes exactly two values `{0x87, 0xC7}`; **bit6 == `carControl.latActive` in 150,302/150,327 = 99.983%** (the 25 disagreements are single-frame transition edges) ⇒ the gate is confirmed on-car; **bit5 (`gp-0x671d`, the masking risk that would pin the gain to 1024 BELOW stock) = 0 in every frame**, as is bit4 ⇒ the arm was a **clean binary**, stock LERP vs `0xC6446` = 5244. ⚠ bit4 is a **wasted rung** — V64 already closed the oscillation-detector approach and this confirms it again. ★★ **GRIND #1 FIXED, and the WITHIN-ROUTE gate A/B proves the conditional design**: 18–22 Hz engaged-creep envelope p99, cell-stratified, episode-clustered — **ENGAGED arm 0.524 [0.337, 0.804]** vs the Kd=1 pool (1.183 [0.773, 1.617] vs Kd=2), **DISENGAGED arm 1.055 [0.669, 1.354]** vs Kd=1 ⇒ **suppression in ONE arm only**, which no other built artifact produces and which is the first evidence ever to separate V66 from V67. Orchestrator's independent pass agrees: 0.55 [0.35, 0.65] against a split-half null of [0.90, 1.12], on a monotone four-point ladder 1.50 (Kd=0) / 1.00 / **0.55 (V67)** / 0.39 (Kd=2). ★★ **CREEP GRIND #2 ELIMINATED**: 40–49 Hz bursts (window envelope p99 > 500; the V62/V65 bursts ran 2000–4000) — V67 **0 in 22 s engaged and 0 in 91 s manual**, max **83.5/48.8**, against Kd=2×'s **18 and 6** with max **1830.7/1469.6**. 🛑 **The two arms are NOT equally supported**: manual expects 3.91 bursts, **P(0) = 0.020** (solid); engaged expects only 1.04, **P(0) = 0.35 — UNRESOLVED**, matching the operator's own uncertainty. **It needs a parking lot, not a build.** 🛑🛑 **THE PREDICTED HIGHWAY COST DID NOT MATERIALISE, AND THE PREDICTION IS WITHDRAWN.** V67 genuinely delivers **2.44×** at highway — its maximum, 22% above V62's flat 2.00× — because a scalar arm replaces a surface Honda **rolls off with speed** (3072 at 0 km/h → 2151 at 100). But with route **`2b` (V58, Kd=1.00×, 227 s of highway** — a baseline two sessions had assumed did not exist) brought in, the three-dose highway comparison is **NULL**: 40–49 Hz ratios **0.970 [0.787, 1.154]** and **0.938 [0.764, 1.184]** against a split-half null of **[0.73, 1.37]**, no dose ordering, and the **corpus-maximum highway envelope (851.5 counts) sits on V58/`r2b` at Kd = 1.00× — the STOCK lane**. ⚠ **SUPERSEDED first-pass figures, kept visible:** this row previously read *"0.98 [0.71, 1.63]" and "0.77 [0.56, 1.44]" against a null of "[0.53, 1.86]", with "zero burst windows at any dose across ~1,400 s"* — those came from an envelope estimator that skipped the detrend + Hann taper `_grind2_lib.win_env` applies and ran **1.4–1.9× low**. ✅ **Re-tested 2026-08-03 with an EVENT-RATE statistic** (events per engaged-highway second, speed-stratified, 10 s block bootstrap): **0.855 [0.432, 1.702]** and **1.152 [0.496, 2.690]** against a split-half null of **[0.36, 2.50]**, **min detectable 1.61×** at 80% power ⇒ **two independent statistics reach the same null**, so it is not a statistic-choice artefact. Positive control fires both ways (18–22 Hz event rate **0.565 [0.329, 0.984]** → **0.319 [0.130, 0.661]**, monotone in dose). Identity settled by amplitude: creep grind #2 runs f0 43–45 Hz at prominence **48–1062×** and envelope **2000–4000**; the highway population runs f0 45–47 Hz at prominence **~6×** and envelope **155–370** ⇒ **not grind #2**. What IS real at highway is **broadband**: 21 maneuvers vs 21 matched controls give 6–9 Hz **2.78×** and 40–49 Hz **2.13×**, i.e. 6–9 rises *more*. 🛑 **BOTH INSTRUMENTS ARE BLIND ABOVE ~50 Hz** — CAN is **100.000 Hz exactly** ⇒ Nyquist **50.00**; the comma IMU lattice is **101.026 Hz** (route range 100.994–101.060) ⇒ Nyquist **50.51**, i.e. **0.51 Hz of headroom, not usable**. ⚠ **SUPERSEDED, kept visible:** this row previously read *"CAN Nyquist 50.2; comma IMU 49.97–50.26 — no headroom"*; `fs_of()` is biased +0.5–1.4% route-dependent and the IMU figure came from its dt *mean* (~10.000 ms, inflated by ~1% dropped samples) rather than its dt *median* (9.897–9.901 ms). The conclusion is unchanged and slightly strengthened. So every highway null is **silence, not absence**, about a >50 Hz vibration. ★★ **This is now an instrument limitation only** — Honda's own 1 kHz detector input `gp-0x6c2c` is a band-pass **peaking at ~61 Hz**, so the ECU has been watching that band the whole time (see `HANDOFF-2026-08-03-the-detector-was-always-there.md`). ✅ **FLIGHT-CLEAN**: `ST == 4` **0/150,327**, `ST == 3` = 12, zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`/`steerSaturated`. ✅ **THE ARM'S SIZING IS CORRECT** — an orchestrator claim that it contained a units error ("128 was bus counts, so the arm delivers 1.94×") was **made and retracted the same night**. Two measurements settle it: regressing `rate_c` on the differentiated ANGLE channel gives slope **0.95–1.00, r ≥ 0.985** ⇒ the bus field IS deg/s; and at 4.7121 counts/deg-s the inner breakpoints are **85/297/637 deg/s**, which real driving reaches (\|rate\| max **521 deg/s** over 407,617 frames), whereas the wrong scale puts them where Honda's rolloff could never engage. ⇒ **LERP 2622, arm 5244 = exactly 2.00× at grind #1**, and V67's delivered multiplier still rises to **2.44× at highway** because a flat arm replaces a speed-scheduled surface. ★ **Design A** (`0xD2ABC` 2561→7051, one halfword) would give 2.00× / 1.22× / **1.00×** at the three points — characterised, safe, and NOT recommended while V67 already has both symptoms at zero. ⇒ **RECOMMENDED: LEAVE V67 ON THE CAR; no control-path change is supported.** Reproduce with `analysis-2020accord/r47_orchestrator_checks.py`; surface arithmetic in `analysis-2020accord/v68_design_math.py`. **Original build note follows.** ★★★★ **THE FIX, AND THE OPERATOR'S CHOICE FOR THE LONG DRIVE.** V66's calibration and reverts, plus the grind #1 fix made conditional on LKAS. **LKAS off is byte-for-byte STOCK base steering; LKAS on gets 2.00× at grind #1's operating point** (creep 7.2 km/h, 128 deg/s, LERP 2622 ⇒ arm 5244). ✅✅ **THE GATE IS VALIDATED ON-CAR BEFORE THE FLASH** — V57's own probe put `(gp-0x6806 == 0)` on `0x14A` byte4 bit6 and flew routes `28`/`29` in July, and nobody had correlated it: **99.90% / 99.94% agreement with `carControl.latActive`** over **37,914 frames** at two very different duty cycles (21.73% / 49.88%), with **0.0505 / 0.0300 transitions per second**. ⇒ `gp-0x6806 != 0` **is** "LKAS is applying"; it does **NOT** drop out during steady engaged holding (the one ambiguity static analysis could not close — it is a ramp-FSM phase flag whose "settled" phases 5/6/7 could not be ruled out); and it toggles **three orders of magnitude** below the 21/45 Hz modes, so the parametric-pump criterion passes with enormous margin. Reproduce with `analysis-2020accord/validate_gp6806_gate.py`. ⭐ **Orchestrator-verified independently from the built image.** **15 bytes off V66**, restricted to `[0x13000,0x100000)`: `0x3AA96` (1), cave `0xC4B46`/`0xC4B52`/`0xC4B54`/`0xC4B56` (4), MAIN CRC (4), `0xC6446` (2), CAL CRC (4). The repoint leaves **hw1 untouched** and the result `84 7f fb 97` differs from the real `ld.bu -0x6806[gp],r12` = `84 67 fb 97` @`0x02A1B6` **only in the reg2 field**. `0xC6444` (r26's arm on the same gate) stays **stock 512** — ~~r26 is inert~~ ⚠ **CORRECTED 2026-08-04: that justification no longer stands on its own.** The GATE leg of the inertness claim is reversed and the MAGNITUDE leg is only BELIEF (see the r26 split box in Part 1). **If r26 is live, leaving `0xC6444` at 512 while the gate is repointed is a 6.00× CUT on r26 whenever LKAS applies** (its LERP value at creep is 3072) ⇒ V67/V68 would be *"r24 up 2×, r26 down 6×"*. ⚠ **The dose–response argues the other way** (`a` is probably small, else V67/V68 at ~0.94× total would sit on stock yet measure 8× better) — an inference, not a measurement. **V70's sign pair settles it.** Both `sar` sites confirmed **stock `0xa`**, `0x3AB70` untouched, `0xD2000` block and **all four** mode-10 `gain_B` records byte-identical to V66. 50/50 CRC; x31 checksum PASS; **the RWD decodes exactly back to the image**. GATE 1 **vacuous** — the repoint is a read-only load displacement claiming no RAM, and the cave's sole store is the existing CAN-330 payload byte with bits 2:0 preserved. GATE 2 is **measured, not argued**: the lane is a **derivative ⇒ DC-neutral**, so a gain step at engagement is not a torque step, and the gate's toggle rate is the table above. Arithmetic `5120 × 5244 = 26.8 M` = **1.25% of INT32_MAX**; the lane saturates at \|dtorque\| ≥ 1599 against a measured 123–839. **Probe** (`0x14A` byte4): **bit7** liveness · **bit6** `gp-0x6806 != 0` (**the gate** — low duty while engaged ⇒ wrong cell and V67 is inert) · **bit5** `gp-0x671d != 0` (**the masking risk** — it OUTRANKS the arm and pins the gain to `0xC6442` = 1024, *below* stock, so if it fires V67 is worse than V66) · **bit4** `gp-0x671a >= 5` (the third arm). Cave re-decoded from the built image; the odd displacement `-0x671d` (bit 0 in **hw1 bit 5**) and the even `-0x671a` / `-0x6806` all encoded correctly. ⚠ bit4 **hardcodes 5** rather than reading cal `0xC64FA`; the cal is 5 and V67 does not move it, but a future change to `0xC64FA` would silently desync the probe from the firmware. 🛑 **GRIND #2 SURVIVES UNDER LKAS**, at **2.21×** — slightly above V62's 2.00×, because a scalar arm does not follow the LERP's own rolloff. That is the stated cost of an LKAS gate: measured gating is **98.7%** engaged for grind #1 but **84.3%** for grind #2 against a **54.7%** base rate. `0xC6446` is one halfword and is the knob for that trade. 🛑 **Do not read a V67 null without decoding the probe first** — that is the V64 lesson. Decoder `rlog-tools/decode_v67_gate.py`. Image SHA `5e01bcc4b34a52831fd524cb9af765a01a8dfa3e2c4782d81b3efcb6c94f8c96`; RWD SHA `33457613ea8635686baf94833e75688fe200c616d76cb4b38b3152d4a47a1caf` |
| `0x3AC20` `42A9`→`42AA` + `0x3AB76` `32A9`→`32AA` (**revert V62**) + cave payload → the **GATE PROBE** | **V66** — the operator's requested stable long-drive build, and the confirmatory intervention. `0x14A` byte4: **bit7** liveness · **bit6** `gp-0x6806 != 0` · **bit5** `gp-0x67f5 != 0` · **bit4** `gp-0x67fe != 0` (gate candidate C — settles a disputed semantic) | **V66** | ✅ **BUILT 2026-08-01, UNFLASHED** | ★★★★ **BUILT BECAUSE V62's OWN FIX IS THE ROOT CAUSE OF "GRIND #2".** Corner-conditioned tail maxima, Kd=1× vs Kd=2×, 219 blocks: 1–4 Hz **1.01** · 6–9 Hz 1.20 · 10–16 Hz **0.80** · **18–22 Hz 0.35** · 24–28 Hz **2.66** · 30–40 Hz **2.98** · **40–49 Hz 11.71 (p = 0.0003)** — a **monotone response with a crossover at 22–24 Hz**, driver band flat as a control ⇒ **not generic roughness**. **One knob cut grind #1 by 2.9× and raised grind #2 by 11.7×.** ✅ **The comma IMU reproduces it on an independent sensor** (40–49 Hz p95 **6.27×**, max **6.71×**; 1–4 Hz 0.76, 24–28 Hz 0.65). **Mechanism:** `gp-0x4f62` is a 4-sample finite difference, so its gain RISES with frequency (**1.93×** at 41.6 Hz vs 20.9 Hz) and V62's *flat* ×2 is not frequency-selective. 🛑 **A FILTER CANNOT FIX IT** — differentiator +20 dB/dec vs one pole −20 dB/dec is FLAT above the corner; two poles cost −92° at 20.9 Hz and destroy the fix. Raising the delay cal `0xC6C42` fails identically (D=24 zeroes 41.7 Hz but leaves −0.3° at 20.9 Hz = a pure spring). **Do not re-propose either.** ⇒ reverting both `sar` immediates restores **exactly stock** base assist, which is what the operator asked for and also the confirmatory revert. **61 bytes off V65** (2 code + 52 cave + MAIN CRC); ⭐ **CAL block byte-identical to V65** and the `0xD2000` block identical, all four mode-10 `gain_B` records unchanged = machine proof no calibration moved; `0x3AB70` still `sar 0xa`; **`gp-0x683c`'s load at `0x3AA94` UNCHANGED** (V66 must not carry V67's repoint). Same base `0xC4B34` / hook `0x55C0E` / 68-byte extent as V55/V57/V58/V59/V64/V65 — all flown clean; **62/68 used**. GATE 1 **vacuous** (read-only; the sole store is the existing CAN-330 payload byte with bits 2:0 preserved). 50/50 CRC; x31 checksum PASS; **RWD decodes exactly back to the image**. ⭐ **Orchestrator-verified independently from the built image**, cave re-decoded from the bytes. 🛑 **Only THREE probe bits fit** (a 4th rung is 12 bytes against ~6 spare) ⇒ `gp-0x671d` and **`gp-0x67fe`** are NOT measured, leaving the `gp-0x67fe` LKAS-vs-base-assist semantic dispute open. Decoder `rlog-tools/decode_v66_gateprobe.py`. Image SHA `0d4a0a53…`; RWD SHA `41a4476a…` |
| `0x3AC20` `42AA`→`42A9` + `0x3AB76` `32AA`→`32A9` | **double the rate lane** — `sar 0xa` → `sar 0x9` on each lane's final shift | **V62** | ✅ **FLASHED 2026-07-31, driven route `37--6231e33f3d` 2026-08-01** | ★★★★ **THE GRINDING IS FIXED — the kit's FIRST MEASURED FIX.** Operator: *"Original grinding at 2–5 mph is gone!"* 86,278 frames. Engaged creep, speed-standardised, **episode-clustered** bootstrap: 18–22 Hz **0.124 [0.036, 0.387]** vs V59 (8×), **0.024 [0.016, 0.234] at \|rate\| 16–32 deg/s (42×)**, with a **30–40 Hz negative control at ~1.0** ⇒ band-specific. Transient rates **0.793/0.486/0.338** at >200/>500/>1000 counts per 10 ms — monotonically cleaner, **lowest p90/p99/>1000-rate of any build**. FLIGHT-CLEAN: `ST==4` **0/86,278** (zero-EME streak now >229,278). 🛑 **The reported "new grinding at 10–20 mph" is NOT an established regression**: the 43 excursions >2000 are **ONE 0.92 s burst (n = 1)**, V62's burst-rate CI **[0.00004, 0.00793] sits inside V59's [0, 0.00986]**, V61's rate is **72×** V62's, and an exposure-matched conditional test (16.14 s vs 15.75 s, one event) gives **p = 0.51**. Instant #2 is an ordinary burst **V59 produces ~3× MORE often**; instant #1 is a 38–46 Hz singleton at 5.4 mph, **not** 10–20. ⇒ **Next action is another V62 drive to count bursts, NOT a build.** 🛑🛑 ~~**AND `0x3AB76` WAS A NO-OP** — r26 is structurally inert (`avg`'s cal base `0xC6564` = 40 bytes of exact zero, no writer for the RAM adjustment) ⇒ **r24 carries the entire lane**, which re-attributes V42/V61/V62 and **supersedes** *"killing either alone leaves the other transmitting."*~~ **NO LONGER SUPPORTED AS WRITTEN, 2026-08-04 — see the r26 split box in Part 1. It is not refuted either.** The claim splits: **LEG 1 (the GATE) is REVERSED [EVIDENCE]** — the gate does not kill r26 in ordinary driving, least of all hands-off at creep. **LEG 2 (the MAGNITUDE) is DOWNGRADED to BELIEF** — `0xC6564` **is** 40 zero bytes, but **its link to `gp-0x69a4` was never verified** and the real producer is a **live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`**. ⇒ *"`0x3AB76` was a no-op / r24 carries the entire lane"* now rests on **LEG 2 alone** and the V42/V61/V62 re-attribution is **contingent on it**; ★ the indirect argument that LEG 2 holds is that at `a ≈ 1` V67/V68's 6.00× gain_A cut would put them at ~0.94× total, essentially stock, **yet they measured the best grind #1 result in the kit.** **V70's `gp-0x6adc`/`gp-0x6ada` sign pair settles it.** ⚠ The pre-committed r24 saturation caveat did **not** bind: measured dtorque is **123–839** (worst transient 739) against a clamp that needs 1820. **Original build note follows.** ★★★ **PROMOTED FROM FALLBACK TO PRIMARY.** V63/V64's gated route is closed (the detector never armed, and even armed it delivers ×1.78/×1.00 vs V62's ×2/×2). V62 carries **no detector anywhere in its path** — no gate, no threshold, no counter — so it is immune to the entire ambiguity that consumed V63/V64. ⭐ **Re-verified from the built image by the orchestrator 2026-07-31**: exactly 6 bytes vs V59 — `0x3AB76` `aa`→`a9` and `0x3AC20` `aa`→`a9` plus the MAIN CRC at `0xC4FFC`; `0x3AB70` correctly still `sar 0xa`; `0xC6440`/`0xC643E`/`0xC6442` all confirmed stock. ✅ **Lane clamps re-confirmed at ±8192 each** (`0x3AB82`/`0x3AC42`) **and the 11-lane aggregate at ±10240**, so it cannot produce an unbounded command. ⚠ **Quantitative caveat worth pre-committing:** r24 saturates at ±8192 once the input derivative exceeds `8192·1024/gain` — 3639 (71% of the ±5120 input ceiling) at its stock 2305 default, **1820 (36%) under V62**. Above that both clamp identically, so expect a **partial** improvement, not elimination; the benefit is that reaching the damping ceiling earlier in each cycle removes more energy per cycle from a limit cycle. ★★ **The matched inverse of V61**: V61 took `Kd`→0 and the mode diverged, V62 takes `Kd`→2× — the same-sized step back. Stock sustains with **no ring-down at all** ⇒ `zeta_net ≈ 0`, so doubling should move it to `+zeta_lead`. **6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38; ⭐ **CAL CRC and `0xD2000`-block CRC both unchanged** = machine proof no calibration moved. 🛑 **`sar` immediates chosen OVER the gain cals** for three traced reasons: (1) the gain is a **priority chain** whose live arm can't be pinned statically (`gp-0x671a` is a bounded [0,5] *persistence ramp* that plausibly never saturates during a 21 Hz oscillation; `gp-0x671d` is an event counter possibly self-excited by it); (2) **r24's default arm is MODE-INDEXED** via `gp+0x63fd` through four pointer arrays — `0xD2AEC`←`0xCC154` idx 10, `0xD6AEC`←`0xCC184` **idx 22**, so ⚠ **`0xD6AEC` is a different MODE, not a redundancy twin — the "V27 desync class" reading was wrong**; (3) `gp-0x683c` has **zero writers** ⇒ `0xC6446`/`0xC6444` are dead arms (single-method, wants a raw byte scan). A `sar` edit doubles the lane **under every arm and every mode**. 🛑 **`0x3AB76` not `0x3AB70`**: V850 `mul` discards the high word into `r0`, and doubling before the `×gain_A` multiply pushes the worst case to **94% of INT32_MAX** vs 47% (unchanged) after it. **Headroom is arm-dependent** — ~22×/~11×/**~7.3× worst case**; doubling keeps ≥3.6× margin. GATE 1 **vacuous** (no cave). ⚠ Residual: `avg(gp-0x69a4)` magnitude still unmeasured. ⚠ Manual feel will change. Image SHA `80d9e1f7…`; RWD SHA `1e0806a1…`. 🛑🛑 **2026-08-04 — CARRIED BY V62 AND V65 ONLY.** Removed as **V66's confirmatory control** and **never restored**; the effect was then re-created twice in encodings that dose **r24 only** (V67/V68's arm, V69/V70's surface) while the ladder kept calling those "2×". ⇒ **from V66 to V70 the car did not carry the kit's only measured grind-#1 fix.** See RULE 3 at the top of this file. ★ **AND THIS ENCODING IS NOW KNOWN TO BE THE ONLY DOSE-EXACT ONE:** it scales **both** lanes identically, so it is **2.000× on the total for every value of `a = gp-0x69a4/1024`** — which matters because **r26 is LIVE** (V70's bit4, 1,644/18,010 frames strictly negative). Every other rung in the ladder is an **r24-only number computed at `a = 0`**. ⏳ **Restored in V71** (`0x3AB76`/`0x3AC20` `aa`→`a9`), making V71's rate lane **byte-identical to V62/V65** |
| `0xD27C6` / `0xD27DA` | damper Factor C Y[0] — **variant-coded, entries 10/11**. 🛑 **2026-07-29: the axis is SPEED, not driver torque** — index load in `FUN_00034350` is `gp-0x6a5e` (voted vehicle speed, settled), X=(2240,3840,5120,8960) ≈ **35/60/80/140 km/h**, so `Y[0]=0` means *below ~35 km/h*. **V44 tested a mechanism that does not exist**; its on-car result stands, its rationale is withdrawn. The "2240 counts driver torque" figure is a **number collision** with the unrelated override curve at `0x29a74`. Invalid speed ⇒ factor defaults to **unity**, not zero | **V44** | ✅ | 🛑 **FALSIFIED** (Factor E re-zeroes the product). ✅ **2026-07-28: confirmed it hit the LIVE table.** PN `39990-TVA-A160` → key `TVAA1` → config row 2 → INDEX **10** → `0xD27BC`, exactly what V44 edited. ⚠ one-bit residual: the coded row is in EEPROM, not the flash dump, and the TVA family splits ({TVAA0,2,4}→idx 4). **V55 carries a telemetry bit for it**. 🛑🛑 **RE-PROPOSED 2026-07-30 BY THE ORCHESTRATOR as "V61" (`Y[0]` 0→64 — a *weaker* V44) and caught by the OPERATOR; script written and deleted unexecuted.** The new *mechanism* (an uncompensated positive-feedback loop through the torque sensor) made the old *address* look fresh, and V44's **rationale had been withdrawn** — which is not the same as its result being withdrawn. **A withdrawn rationale does not withdraw an on-car null.** ⚠ And note the arithmetic reason V44 failed: the damper is **four chained Q10 multiplies**, so raising one factor is worthless while any other still zeroes the product — Factor E did. **Before touching one element of a product chain, check every other element.** ✅ Salvage: the damper's int/float lockstep is **ceiling-only** — `FUN_000347b8` *reads* `gp-0x6bd0` and never recomputes the four-factor product (confirmed 4 ways incl. a split-encoding `movhi` check), and the two ceilings are the **same table in two formats** (`INT 0xD209C X=[300,800] Y=[512,1024]` vs `FLOAT 0xC6554 300.0,800.0,0.5,1.0`). Damper authority at creep is firmware-clamped to **±512 of the aggregator's ±10240 (≤5%)** |
| `0xD2802/04/06`, `0xD2816/18/1A` | damper Factor E (motor-rate) deadzone — **variant-coded, entries 10/11** | **V47** | ✅ | 🛑 marginally quieter at 5 mph, **no effect in motion**. ✅ **2026-07-28: confirmed it hit the LIVE table** (same INDEX 10 chain as V44 → `0xD27F8`). ⇒ **the missing-damping hypothesis was genuinely tested and IS falsified** — do not resurrect it on a "wrong variant" theory |
| `0xC4120` + `FUN_0003a382` `uVar27`→256 | type-8 carrier mute | **V48A** | ✅ | ⚠ **RE-FRAMED — one branch of three, like V43/V46** |
| `gp-0x4f60` broad EMA (19 carriers → `gp-0x1300`) | V52C code cave | **V52C** | ✅ | ⚠ **WEAKER THAN IT LOOKS.** `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only **−6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the mode's content, it did not remove it. **Did change manual feel** (so the cave fired) |
| `0xC6206` (hands-off slew) | governor slew | **V45** | ✅ | 🛑 **FALSIFIED** |
| `0xC6206`/`0xC6208` ← `0xFFFF` | governor slew, both | **V40** | ✅ | ☠ **EPS lamp + no power steering at ignition.** Magnitude, not direction: `0xFFFF` made the guard never fire → snap-to-target → DTC 0x1d → motor off |
| `0xC5030`, `0xC521A`, `0xC5232` | motor-rate cap table | V40/**V41** | ✅ | 🛑 **FALSIFIED** (V41 = clean subtractive test) |
| `0x454FE` `0x65BA`→`0x65B5` | state-4 governor ratchet `bne`→`br` | **V42** ch.1 | ✅ | 🛑🛑 **NOT THE FIX — RE-ATTRIBUTED 2026-08-05. [EVIDENCE]** This row read *"CONFIRMED ROOT CAUSE — fixed the hard-turn ratchet, carry forward"* for eleven months and it was **wrong**. `gp-0x67fa == 4` reads **0/123,277** and **8/92,826 (all in PARK)** ⇒ the substitution **never executes while driving, on stock either** ⇒ structurally eliminated. **V42's real live delta was ch.2 — the r26 kill** (see the ledger-corrections table). ⚠ Carried inertly by V71A/B/C, V72, V73. ⚠ **NOT present in V38/FOURFRAME**. 🛑🛑 **2026-08-04, BYTE-READ ACROSS ALL 60 BUILT IMAGES: CARRIED BY V42–V52C ONLY — STOCK IN V53 → V70.** Lost at the V38/FOURFRAME rebase, because V53+ descends from a branch point *before* V42. **Nobody decided this.** ⚠ **And the argument that later retired it as a cause of the CURRENT ratchet — *"`STEER_STATUS == 4` fires 0/37,922"* — was VOIDED** when bus `STEER_STATUS` was shown not to be `gp-0x67fa` (state 4 sits inside all three gate masks). **It was never actually eliminated.** ⏳ **Restored in V71.** 🛑 **State the justification honestly: restored because it is a confirmed fix lost by ACCIDENT, not because it is established to cause the current ratchet** — the substitution is **asymmetric** (clamps increases, passes decreases) while the ratchet measures **symmetric** (skew −0.16…+0.06, crest 2.07–2.45 vs a sine's 1.414), which is evidence *against* that mechanism. ✅ Safety re-verified against `_v70_plain_image.bin`: `FUN_0004595a` and `FUN_000462e6` are **0 diff bytes vs stock**; the *"only ever makes `gp-0x6ace` smaller ⇒ safe side"* argument **transfers** but stays **[INFERRED]**. Sits in the bridged main CRC block `[0x13000,0xC4FFC)`. 🛑🛑 **RETIRED FOR GOOD, 2026-08-06 — ON-CAR CONFIRMATION, not just static analysis.** V74's route-5d flight (101,118 frames) put `gp-0x67fa` at a **CONSTANT 5**, with state 4 on **exactly one frame** (the last of the route, vEgo −0.0, in PARK). State 5 clears every one of the three assist-chain masks (`0x830`/`0x930`/`0xc30`), so the byte is not merely statically unreachable-while-driving (RULE 4/5's finding) — it is now measured to be irrelevant on the actual live car, in the actual live state the car sits in almost all the time. **Do not re-propose this lever, and do not re-open the "state-4 governor" hypothesis for the ratchet without new evidence that state 4 is ever visited while driving** |
| `0xC9E9C` (FactorC) / `0xC9F84` (FactorE), engaged column of all 16 rows | base-assist damper speed/rate dead-zone-opening levers — `dose = (FactorC × FactorE) >> 10`; `FactorC Y[0]:=Y[2]`, `FactorE X[0]:60→12` / `Y[1]:=Y[2]` | **V74** (Lever E′) · **V75** (2.74× dose) | ✅ **BOTH FLASHED — BOTH HARD-FAULTED** | 🛑🛑🛑 **V74 HARD-FAULTED 2026-08-06, AND THESE EDITS WERE NOT IN FORCE WHEN IT DID.** Latched **total loss of power steering, LKAS DISENGAGED, over a bump**; EPS lamp on continuously, still on after restart, off after ~30 s of driving. **[EVIDENCE, verified two ways] the FactorC/FactorE edits were not in force:** disengaged = **mode 24**, and all five mode-24 damper records are **byte-identical to stock** on V74 *and* V75 — FactorC `0xD67E4`, FactorE `0xD6820`, FactorB `0xD6760`, FactorD `0xD67A4`, ceiling `0xD60B4` — and **0 of the 54 non-CRC V73→V74 diff runs lands inside a mode-24 record.** ⇒ **the fault sits in the MODE-PROOF residue, not in this row's lever** (RULE 10; and see the `0xC63A0` row — V74 is the first build in which V72's doubled Path-2 damper weight carried a non-zero signal). 🛑🛑 **CONSEQUENCES, ALL LOAD-BEARING: `k* ∈ (0.580, 1.580]` is VOID** — it was fitted from *V74 flew clean* + *V75 faulted*, and V74 did **not** fly clean; **"V74 flew 1,011 s clean" is WITHDRAWN as a safety anchor**; and **no build in the current lineage has demonstrated safety.** ⊕ The positive-control measurement below rests on V74's own probe data and **stands, kept as written.** ★★★★ **CONFIRMED LIVE ON-CAR, 2026-08-06 — the kit's first positive control on `gp-0x6bd0`.** `bit7=(gp-0x6bd0!=0)` fired 67.44% duty engaged-creep / 39.93% engaged-all-speed / 2.13% manual (23,603/101,118 frames, route `5d`); V72's IDENTICAL probe on the SAME cell read 0/87,940. Pre-registered abort gate (`5×f0` prominence) CLEAR — but only after investigation, see `docs/STATE.md`: the route-wide point estimate (2.227 NFFT 2048 / 1.719 NFFT 512 vs the 3.0 threshold) omitted a K-free per-window reading that put V74 at the corpus MAXIMUM (2.884, CI crossing 3.0) and a creep-only reading (5.844 at K=2); a cross-build tracking test (peak location correlates with 2×grind-1's frequency, r=0.759 p=0.007, NOT with 5×f0, r=0.144 p=0.673) plus an odd-harmonic check (V74's 3×f0 = 1.374, rank 5/11, unremarkable) both independently show the elevation is grind #1's pre-existing 2nd harmonic, not a new relay cycle — V74 simply has the corpus's highest f0, which puts its 5×f0 nearest that pre-existing line. Success UNDERPOWERED (9 episodes, planned ~40; MDE ≈ 2.0–2.9×) — duty 0.797/duration 0.934/envp99 0.835 all trend favourable vs V73, none clears its own CI. Both symptom bands remain measurably active (6-9 Hz 3.27×, 18-22 Hz 2.72× over the 24-28 Hz control, clean 9.4-12.5 m/s window) — **not eliminated, and not falsified either; an exposure-limited partial result.** ⇒ **V75** (`FactorC Y[0]` 429→566, `FactorE X[1]` 400→200, 2.74× V74's dose at rate 99) was built clip-free two ways — **FLASHED 2026-08-06, AND IT HARD-FAULTED TOO.** ★★★★★ **The fault is pinned to ONE 100 Hz frame**: route `5e`, t = 284.7947 s — STEER_STATUS→7, STEER_CONTROL_ACTIVE→0, `gp-0x6880`→1, `0x1AB`'s DTC-active flag→1, all three `0x14A` angle fields→`0x7FFF`, STEER_SENSOR_STATUS 7→4, **all latched.** 🛑 **The faulting launch was the MILDEST of four** — an earlier one sat on the ±4096 rail **76%** of its window and did **not** fault, the faulting one had **0.00% rail contact**, and the damper **never reached the `≥448` probe rung (0/39,961 frames).** 300 ms pre-fault: a **20.0 Hz oscillation absent from openpilot's command.** ⇒ **magnitude-based mechanisms are DEAD; this is a FAST-TRANSIENT sensitivity** — see RULE 8b, and note the observed-envelope argument that cleared V75 is **withdrawn** (5d *did* contain engaged launches; V74 flew 5–6 of them). ★★★★ **DOSE-RESPONSE across V72 (k=0) · V73 (k=0) · V74 (k=0.5799) · V75 (k=1.5798): 18–22 Hz slope −0.599 [−0.856, −0.348] = −5.20 dB per unit k, CI EXCLUDES ZERO; 6–9 Hz slope −0.089 [−0.350, +0.163], CI INCLUDES ZERO — FLAT.** The k needed for the ratchet is **4.2–13.5**, against the **1.5798 that faulted.** ⇒ 🛑 **the damper fixes the grind and CANNOT fix the micro-ratchet — stop sizing this lever for the ratchet** |
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

### 🛑🛑 THE `r26` INERTNESS CLAIM IS **REFUTED ON-CAR** — and NO post-V38 rate-lane build was single-variable

🛑🛑 **RESOLVED 2026-08-04 BY V70's PROBE. [EVIDENCE]** `gp-0x6adc` — r26's post-clamp mirror — read
**strictly negative on 1,644 of 18,010 frames** on route `50`. **A pinned-zero cell cannot clear a
`>= 0` test.** ⇒ **r26 is LIVE**, LEG 2 falls, and **"r24 carries the entire lane" is gone.**
★ **New asymmetry [EVIDENCE]: `bit3 ⇒ bit4` STRICTLY** — **0 of 18,010** frames with r24 ≥ 0 while
r26 < 0. **[BELIEF]** the natural reading is *"r26 is ZERO part of the time, same-signed otherwise"*,
consistent with the shared polarity load `ld.b -0x6752[gp],r14` @`0x3AB78`.

#### ★★★ TWO SELECTORS, ONE GATE — why every published multiplier in this kit is an r24-only number

**[EVIDENCE — orchestrator-disassembled, both selectors read out of the image.]**

**`r26 → gain_A`** — `0x3AB5E ld.hu 0x7444[tp],r8` (`0xC6444` = **512**, taken when `lp != 0`) ▸
`0x3AB68` `0xC643E` ▸ else **gain_A's own LERP (3072 at creep)**.
**`r24 → gain_B`** — `0x3ABFE` `0xC6442` = **1024** (the `gp-0x671d` mask arm, **outranks all**) ▸
`0x3AC08` `0xC6446` (when `lp != 0`) ▸ `0x3AC12` `0xC6440` = **2048** ▸ else **the mode-10 surface**.

⇒ **V67/V68's ONE-BYTE gate repoint at `0x3AA96` raises r24 AND cuts r26 6.00× at the same time.**
Net delivered vs stock = `(5244 + 512·a) / (3072 + 3072·a)`, with `a = gp-0x69a4/1024`:

| `a` | net vs stock |
|---|---|
| 0 | **1.707×** |
| **0.848** | **1.000× — PARITY** |
| > 0.848 | **BELOW stock** |

**V69 and V70 edited gain_B only.** ⇒ 🛑 **every published multiplier in this kit is an r24-only
number computed at `a = 0`, and the "dose ladder" was never one ladder.**
✅ **V62/V65's `sar` route (`0x3AB76`/`0x3AC20`) is the ONLY encoding whose dose is exact independently
of `a`** — it scales both lanes identically, **2.000× on the total for every `a`.**

**The ladder re-read against what each build actually carried** (median `e_18-22`, engaged creep):

| build | r24 | r26 | median `e_18-22` |
|---|---|---|---|
| V61 | ×0 | ×0 | **2501** |
| stock | ×1 | ×1 | **879** |
| **V70** | ×2 | ×1 | **729** |
| **V69** | ×4 | ×1 | **746** |
| **V62 / V65** | **×2** | **×2** | **168** |
| **V67 / V68** | gated arm | **÷6** | **109** |

🛑🛑 **AND THERE IS A CLEAN SINGLE-VARIABLE r24 SERIES INSIDE THAT TABLE. IT SAYS r24 IS
NEAR-INERT.** [EVIDENCE — medians recomputed from `_grind2_lib.wrecs`] **stock → V70 → V69 holds r26 at
×1 and steps r24 ×1 → ×2 → ×4, reading 879 → 729 → 746, all three CIs mutually overlapping.**
⇒ **r24 is close to INERT for grind #1 across a 4:1 dose range**, and **every build that FIXED grind #1
changed r26** (V62 ×2; V67/V68 ÷6.00) while **every build that changed only r24 did not.**
⇒ ★★ **the correct headline is not "nothing is single-variable" — it is THE DOSE AXIS THIS KIT HAS
USED SINCE V62 IS THE WRONG LANE.**

★ **Four supporting byte facts, all [EVIDENCE]:** (1) **gain_A's four records `0xC6A68`/`0xC6A7C`/
`0xC6A90`/`0xC6AA4` are BYTE-IDENTICAL across all 11 images** ⇒ V67/V68's **÷6.00 (= 512/3072) is EXACT
and engaged-only**; (2) the two LERPs live in **separate RAM** — `gp-0x6e40`/`gp-0x6e38` for gain_B,
`gp-0x6e30`/`gp-0x6e28` for gain_A — filled by the **two halves of `FUN_0003ad74`**; (3) **gain_B is
filled from the MODE-INDEXED arrays, gain_A from FIXED, non-mode-indexed records** ⇒ V69/V70's mode-10
surface edit **could not reach r26 even in principle**; (4) **there is NO `gp-0x671d` mask arm on the
r26 side** — gain_A is **2 arms + default**, not 3.

⚠⚠ **CARRY THIS UNEXPLAINED — DO NOT SMOOTH IT.** **r26 ×2 (V62/V65) AND r26 ÷6.00 (V67/V68) BOTH
HELPED, and ÷6 helped MORE** (168 vs 109 against stock's 879). A monotone *"more r26 damping is
better"* story and a monotone *"less is better"* story are **both refuted by the same two rows. The
corpus cannot say why, and that is the leading open question.** 🛑 **Anyone proposing an r26 dose must
state which direction they are betting on and why** — the record does not supply it.

★ **Independent bus-side support for the r26 attribution, without the disassembly [EVIDENCE]:** median
`e_18-22` by **bar-torque reversal count**, engaged creep — in the **rev ≥ 40** regime (where the ratchet
lives), **V62 reads 396 against 1155–1403 for V59/V64/V69/V70. V62 is the odd one out, and it is the
only build with r26 ×2.**

⚠ **The "non-monotone dose–response with a minimum near 2×" is RETIRED** — it priced every build on
r24 alone at `a = 0`.
🛑 **And grind #1 is BLIND to r24 gain, which retires a MEASUREMENT TOOL:** log-log slope of median
`e_18-22` on r24 gain **−0.144 [−0.991, +0.347]**, pairwise **P = 0.667 / 0.610 / 0.426** ⇒ **grind #1
cannot be used as an in-force check for the r24 lane on ANY future build.** Structural, not a power
limit. ★ **Methodological correction: CI OVERLAP IS NOT A TEST** — the subsample-at-matched-exposure
test excludes V62's level at **P < 5 × 10⁻⁵** where the CI comparison called it undecided. **"V70 is not
at V62's level" IS established; where it sits between stock and V62 is NOT.**

---

#### The reasoning that set up that measurement, kept as written (2026-08-04, pre-flight)

**This file, `docs/STATE.md`, `docs/V69-DESIGN.md` and `memory/` all carried:**

> *"r26 is structurally INERT (`avg`'s cal base `0xC6564` = 40 bytes of exact zero) ⇒ r24 carries the
> whole rate lane."*

🛑 **Do NOT read what follows as a flat reversal of that claim** — that would be the mirror image of the
original error. It rested on **two independent legs** and they resolved differently.

**LEG 1 — THE GATE: REVERSED. [EVIDENCE]**
- `r26 == 0 ⟺ gp-0x6b5e != 0` (since `0xC6138` = 1 ⇒ `r22 == 1` always, and `gp-0x671a` = 0 over 240k
  frames).
- `gp-0x6b5e = ((LERP(gp-0x6bda) × 0xC63C2) >> 10) × polarity` — producer `FUN_000361c8` @`0x36256`/
  `0x36264`, shadow pair `gp-0x4cd8`, `0xC63C2` = 1024 = Q10 unity — on the trapezoid `0xC66CC`
  (X = [−384, −128, 128, 294, 384], Y = [0, 4762, 4762, 717, 0]) ⇒ r26 is killed **only where the LERP
  is ZERO, i.e. `|gp-0x6bda| ≥ 384`.**
- ★ **`gp-0x6bda` is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque `gp-0x6bf0`**
  (`FUN_00036022` @ `0x36068`–`0x3608C`; envelope `gp-0x6bd8`/`gp-0x6bd6` maintained by `FUN_00035d38`,
  half-width **never below 9390**, `0xC614A` = ±10048, margin cal `0xC614C` = 128).
  **Hands-off: `gp-0x6bda` ≈ 9262 = 24× the 384 threshold.**

⇒ **THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of all hands-off at creep.** The kill
window is a **~512-count sliver at the DRIVER-OVERRIDE end** (cf. `0xC6156` = 9216). **This half is
settled, and it is a genuine reversal of how the gate was read.**

**LEG 2 — THE MAGNITUDE: STILL BELIEF, unresolved in either direction.**
`FUN_00039702` shows the RAM array `gp-0x641E`…`gp-0x6444` is an **adjustment added in Q10 float to a
fixed cal base at `tp+0x7564`**, and **`0xC6564`–`0xC658C` really is 40 bytes of EXACT ZERO** with **no
writer found for the RAM side (10 of 18 cells checked)** ⇒ `stage1 ≈ 0` — **IF that cal base is what
actually feeds `gp-0x69a4`.** 🛑 **THAT LINK WAS NEVER VERIFIED.** `gp-0x69a4`'s real producer is a
**live runtime 10-segment LERP at `0x355C6` in `FUN_000352b4`** (the local *slope* of the curve, gated
`|gp-0x4f60| ≤ 25600`) — **1 writer / 3 readers: `0x355A4`, `0x3575A`, `0x3AB3A` (= the aggregator).**

⇒ **"r24 carries the entire lane" is a BELIEF resting on LEG 2 ALONE**, and the single-lane
re-attribution of **V42 / V61 / V62 is CONTINGENT ON LEG 2**, not established. V42's null, V61's WORSE
and V62's fix are all still real *on-car results* either way.
★ **The one indirect argument that LEG 2 holds — and it is what keeps the dose–response coherent:** at
`a = gp-0x69a4/1024 ≈ 1`, V67/V68's gate (gain_A **3072 → 512**, a **6.00× cut**) would put their
engaged **TOTAL at ~0.94× stock** — essentially *on* stock — **yet V67/V68 measured the best grind #1
result in the kit (median `e_18-22` engaged creep 109 vs stock's 879).** ⇒ **the empirical record argues
`a` is small.** [BELIEF — indirect, but it is the only thing making the dose–response self-consistent.]

✅ **AND IT IS DIRECTLY MEASURABLE — V70 flies exactly the pair.** `gp-0x6adc` is r26's post-clamp mirror
(`st.h` @`0x3AD4E`, **0 readers / 1 writer** image-wide), and r24/r26 share **ONE polarity load** —
`ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` (r26) and `0x3AC3E` (r24) — so **they always
carry the same sign** (`gp-0x69a4` is an unsigned magnitude at both ends). Therefore `sign(gp-0x6adc)`
vs `sign(gp-0x6ada)` is a **matched pair**: **bit4 pinned at 1 while bit3 toggles ⇒ r26 is ZERO (LEG 2
holds); bit4 tracking bit3 ⇒ r26 is LIVE (LEG 2 falls).** **Non-vacuous in both directions.**

⇒ ⚠ **WHAT THIS DOES TO V67/V68.** Repointing `0x3AA96` makes **both** cal arms live; `0xC6446` was
raised to 5244 but **`0xC6444` stayed at 512** against r26's live LERP value of **3072** — recorded at
the time as harmless *because r26 was believed inert*, a justification that no longer stands on its own.
**If r26 is live, V67/V68 is "r24 up 2×, r26 down 6×"** and total engaged rate-lane damping falls
**BELOW stock** once `a` > **0.848** at 0 km/h. **The dose–response argues against that**, so the
leading reading is that V67/V68 is what it says it is — but it is an inference, not a measurement.
✅ **V62/V65's `sar` route is the only edit in this kit that is dose-exact independent of `a`** —
2.000× on the total for **every** value of `a`. That property is worth more than it has been credited.

### Untested levers currently on the table
| address | what | status |
|---|---|---|
| 🛑🛑 ~~**`0xC6444`**~~ **STRUCK — NULL BY CONSTRUCTION** (r26's `gp-0x683c`-gated arm, 512) | one reader / **zero writers**, **no float mirror**, same CRC block **#48** as `0xC6446`. On a build with the gate repointed to `gp-0x6806` it is the r26 arm that applies **while LKAS is engaged** | 🛑🛑 **STRUCK 2026-08-04 — NULL BY CONSTRUCTION. The framing that follows is SUPERSEDED; the reason is at the END of this cell.** ~~★★ A CANDIDATE, NOT A RECOMMENDATION — and genuinely UNTESTED IN THE RAISING DIRECTION.~~ V42 tested it **downward** (512 → 0) and that was **FALSIFIED** — the same *"tested downward ≠ tested upward"* distinction the **V61 → V62** correction turned on, and on a build where the gate is dead besides. **Overflow ceiling ≤ 6553.** ⚠ **If** r26 is live, leaving it at 512 on a gate-repointed build is a **6.00× cut** against r26's LERP value of 3072 at creep — which is what V67/V68 shipped. 🛑🛑 **V70 DOES NOT TAKE IT**, and neither should anything else until `a = gp-0x69a4/1024` is bounded: the delivered total is a function of `a`, the sign of the change flips around `a ≈ 0.848` at 0 km/h, and **V67/V68's control path is the best-measured arm on the two INSTRUMENTED symptoms** (it carries the high-speed grind, which is why restoring it was overridden). Do not trade a measured best against an unmeasured parameter. 🛑🛑 **STRUCK 2026-08-04 — THIS IS A NULL BY CONSTRUCTION, NOT AN UNTESTED LEVER, AND THAT SUPERSEDES THE WHOLE FRAMING ABOVE. [EVIDENCE]** `0xC6444` is read **ONLY** at `0x3AB5E`, and **only when `lp != 0`**. On **every gateless build — stock, V62, V65, V69, V70, V71 — the gate `0x3AA96` is `c5`**, so `lp` derives from `gp-0x683c`, which has **0 writers image-wide** ⇒ **that load NEVER EXECUTES.** ⇒ **raising it changes NOTHING** unless `0x3AA96` is *also* repointed — which reintroduces **the V67/V68 control path the operator rejected**. ⇒ **it is reachable only on a build whose control path is already ruled out. Do NOT re-propose it as a single-variable r26 test; there isn't one on the current topology.** ⚠ The *"untested upward / V42 tested it downward"* framing was correct arithmetic about the wrong question |
| ✅ **`gain_A` rec0 `0xC6A68` / rec1 `0xC6A7C`** — **THE SINGLE-VARIABLE r26 LEVER** | [EVIDENCE, orchestrator byte-read 2026-08-04] `gain_A` has the **same 4-record × 4-point layout on the same `0xC6010` speed cross-axis** as `gain_B` (`[0, 640, 3200, 6400]` counts = `[0, 10, 50, 100]` km/h): rec0 X=[0,400,1600,3000] Y=[3072,3072,2434,2048] · rec1 X=[0,250,1200,3000] Y=[3072,3072,2488,1536] · rec2 `0xC6A90` · rec3 `0xC6AA4`. **Byte-identical across all 11 images.** `gain_A` is **NOT mode-indexed** — which is why V69's and V70's mode-10 `gain_B` surface edits could never reach r26 | ★★★★ **THE LEVER THE CORPUS POINTS AT, and it is BUILT as V71B (unflashed).** Doubling rec0/rec1's **WHOLE rate axis (Y[0..3], not just Y[0..1] — that restriction is exactly V69/V70's mistake)** doses **r26 alone below 50 km/h** and is **EXACTLY 1.000× at and above 50 km/h by construction** (rec2/rec3 untouched — V69/V70's proven structural guarantee, applied to the lane that matters). Arithmetically **identical to V62's `0x3AB76` `sar` at creep**, without V62's flat 2× at highway. ⚠ **OPEN:** r26's saturation rail depends on the **unmeasured** `avg(gp-0x69a4)`, so unlike r24 it is **not bounded** — size it before doubling. ⚠ Confirm no other consumer reads these records (they are not mode-indexed) |
| **`gp-0x6bbe` angle-rate tributary** (`FUN_00034a72`, reads `gp-0x6a56` at `0x34AB8`/`0x34E8E`) | the boost lane's **UNFILTERED steering-angle-rate error term**, scaled by two speed-indexed LERPs | ★★ **UNBUILT — and the lever INVERTS.** The mode is **996×** on `STEER_ANGLE_RATE` vs **877×** on torque, and this is that exact variable, unfiltered. First candidate ever outside the torque domain. 🛑🛑 **GATE 2 ANSWERED AGAINST CUTTING IT:** the torque EMA is a *multiplicative amplitude scale*, not an additive branch, and the core term is `rate_error = baseline − angle_rate` (`sub r6,r28` @`0x34e96`) with all-positive downstream multipliers and polarity +1 ⇒ **`gp-0x6bbe` ≈ −(gain)·angle_rate = viscous DAMPING.** **Cutting/muting it would REMOVE damping and likely worsen the grinding — the V56 error one build later.** ⇒ **the direction of interest is RAISING the gain to ADD damping at 22 Hz.** Cleanest single point: **`K1` @`0xD200C` = 43** (Q7; pointer base `0xCA324` = 1 hit image-wide). Others: `clampBound` `0xD2000`=666, speedLERP1 Y `0xD2834+0xE..0x18`, speedLERP2 `0xD20C0+0xC..0x14` — all inside the shared `DAMP_BLOCK` but **not** overlapping V44/V47's bytes (grep-checked). 🛑🛑 **STATUS 2026-07-30: THE SIGN IS UNRESOLVED AND SIMULATION CANNOT SETTLE IT. V58 MEASURES IT INSTEAD.** The reasoning flipped three times in one session — (a) "net damping" off the torque-EMA framing; (b) "unresolved, `baseline` isn't slow"; (c) "damping, `baseline` reads no angle rate"; (d) **unresolved again**, because **`gp-0x6a56` is NOT independently sensed** — `FUN_0003f776` computes it as `clamp(polarity × ((gp-0x6abe × 48 × cal) >> 15), ±12000)`, a scale of MOTOR resolver rate — and `baseline`'s Branch A is **also** `gp-0x6abe`-derived, so the two may partially cancel. The golden model cannot simulate it: `base_driver_assist_lane` is flagged `[SIMPLIFIED]` at exactly this point and the tributary is absent. ⚠ **`K1` may also be moot**: the lane's own ceiling (`0xD20C0`, count=5, X=(0,640,2560,5760,6400), Y=**flat 512**) is a SATURATING clamp at ¼ of the aggregator's ±2048 ZERO-gate, so the gate can never fire — but if the lane pins at ±512 the damping derivative is **zero at the peaks** and the lever becomes the **ceiling**, not `K1`. Full order byte-verified: `term1=(K1×rate_err)>>7` → `×Y3>>10` → clamp ±666 (`0xD2000`) → `×((Y4blend×gp0x6988norm)>>10)>>14` → `×polarity` → clamp ±512 → `gp-0x6bbe`. Two fractional stages sit between the 666 clamp and the ceiling, so raising `K1` is **not** a guaranteed null. **V58's bit6/bit5 answer both questions on-car.** ⚠ speedLERP1 `0xD2834` is the boost curve (count=6, Y=541/639/653/551/439/439), not a monotonic speed rise. 🛑🛑 **STATUS 2026-07-30 AFTER THE V58 DRIVE: the CEILING is ELIMINATED and `K1` is still UNRESOLVED.** bit5 = `gp-0x6bbe == +512` fired in **0 of 35,964 frames** ⇒ the lane never pins, the saturating-clamp failure mode is off the table, **`0xD20C0` is NOT the lever**, and `K1` keeps its headroom. But bit6 was **void by construction** — `gp-0x6bbe` is DC-dominated (crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s), so a sign comparator carries no phase at the mode frequency. **The damping sign question needs a MAGNITUDE probe (thermometer on \|gp-0x6bbe\|), which is V60 — and it only matters once V59 says whether the amplitude path is live.** ⚠ Do not move `K1` on a pooled-run coherence: pooling manufactures a splice artifact |

### Untested levers ADDED 2026-07-30 — the boost-amplitude modulation path
| address | what | status |
|---|---|---|
| **`0xD28DC`** (LERP1, via ptr table `0xca4f4`) and **`0xD2888`** (LERP4, via `0xca23c`) | the two boost **amplitude** curves, both indexed by `gp-0x6ba6`. `0xD28DC`: count=6, X=(0,512,1490,2529,3645,5120), Y=(16384,14657,11672,9365,8244,8187). `0xD2888`: X=(0,307,1024,1741,3072,6144), Y=(16384,14392,10265,8997,8176,8176) | ★★ **UNBUILT, and GATED ON V59.** `gp-0x6ba6 == \|gp-0x6b9a\|` (byte-verified, `subr r0,r13` @`0x3b87a`), and V58 measured the signed sibling crossing zero at 20.93 Hz **only when LKAS applies** (13.69 vs 0.61 toggles/s at matched creep) ⇒ the index is that signal **rectified**, sweeping these curves at **~2× the mode frequency** across a 2:1 range. Flattening the Y rows removes the modulation. 🛑 **But DEPTH is unmeasured** — the delivered swing is set by how far up the curve the index climbs: `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert" below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero; a 12% modulation is weak but real. **V59 measures the regime. Do not build against these until it has flown.** 🛑 GATE 2 outstanding: both sit on the **BASE ASSIST** path, so they change manual feel, not just the LKAS lane. ⚠ `0xD28DC` is reachable ONLY from `0xca4f4` — `build_v58_tva.py` said `0xca23c` and was wrong |
| **`tp+0x73ba`** = `0xC63BA` = 512 | the cascaded-EMA alpha in `FUN_0003b66a` (two poles, α = 512/1024 = 0.5 at 1 kHz ⇒ corner ≈120 Hz for the pair, i.e. **wide open at 21 Hz**) | ★ **UNBUILT — the UPSTREAM candidate.** This is the filter that lets `gp-0x6b9a` carry 21 Hz in the first place; attenuate here and nothing downstream has anything to modulate with. Real filter authority, unlike the two identity FIR triples. 🛑 GATE 2 outstanding and non-trivial: it is on the base assist path and adds phase lag to assist. Gate on V59 |
| ~~`FUN_0003b66a` branch-A "biquad"~~ | `tp+0x5018/501c/5020` = `0xC4018/1C/20` | 🛑 **NOT A NOTCH LEVER — same closure as the FIR row above.** A 2026-07-30 trace claimed "a genuine floating-point 2-pole biquad, IIR by definition". **It is not.** The coefficients read **(1.0, 0.0, 0.0)** and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, **not feedback**. Stateful ≠ recursive. It is the identity 3-tap FIR already on record. Also: `tp+0x74be = 0` makes `0x3b736–0x3b758` dead code |
| ~~`0xC6AFC` + `0xC6AFE`~~ | moved to the flashed table above — **V56, falsified and harmful 2026-07-29** | 🛑 **DONE. Do not re-propose, at any authority value.** The GATE-2 "damping sign OPEN" caveat resolved *against* the mute on-car |
| ~~`0xC6372` / `0xC636E`~~ | boost-assist + damping lane input EMAs | 🛑 **RETIRED 2026-07-30 — DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` routes both consumers past it. Zero effect on this firmware. See the main table |
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

### 🛑 A RE-CUT UNDER THE SAME BUILD NUMBER DESTROYS ITS PREDECESSOR'S PLAIN IMAGE — open, 2026-08-04

**The hazard, stated as it actually happened.** Two V70 cuts were built 19 minutes apart. **Both wrote
`_v70_plain_image.bin`**, so the second silently **overwrote** the first's snapshot. The first cut's
`.rwd` survived and was flashable. ⇒ **a flashable artefact existed that NO gate in this kit could
check**: `verify_v70_image.py` asserts the *current* topology (`0x3AA96 == 0xC5`, `0xC6446 == 512`), so
it **fails on the superseded build by construction**, and `diff_build_vs_stock.py` has no image to read.

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
100.6; orchestrator-verified from `_cache_r50/r50s1.npz`.]**

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
