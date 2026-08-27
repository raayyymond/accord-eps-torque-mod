# HANDOFF 2026-08-12 (latest) — V97 FLEW, THE LEVER WAS LIVE, AND THE NULL WAS OURS

**Read after:** `docs/handoffs/2026-08/HANDOFF-2026-08-12-v97-the-loop-pole.md`.
**Session outputs:** `docs/review/AUDIT-2026-08-12-dead-levers-and-liveness.md` (54 KB) ·
`docs/specs/SPEC-2026-08-12-next-telemetry.md` (108 KB) · `docs/scoring/SCORING-2026-08-12-v97-route80.md` ·
`docs/traces/TRACE-2026-08-12-v97-liveness.md` · `docs/traces/TRACE-2026-08-12-stage2-lerp-knots.md` ·
`docs/review/VERIFY-2026-08-12-v97-image.md` · cache `analysis-2020accord/_scratch/cache/r80/`.

---

## 0. WHAT CHANGED, IN SIX LINES

1. **V97 flew as route `0x80`** — a deliberate parking-lot creep. **The operator felt nothing and stopped.**
2. **His two hypotheses — wrong address, dead code — are BOTH REFUTED.** The lever is provably live.
3. **The null is on the EXPERIMENT**: no instrument, one episode, and an observable no amplitude
   statistic can see. ⇒ **`0xC63AC` is UNINTERPRETABLE, not falsified. Do not re-dose it.**
4. **Structure established: V89 and V97 pushed on OPPOSITE ARMS of one observer residual.**
5. **Two standing "unreadable / unpinnable" claims fell** — the Stage-2 transfer, and `f′`.
6. **Two new standing rules from the operator**, both in `CLAUDE.md`.

---

## 1. THE OPERATOR'S OWN WORDS — and the two instructions that reshaped the session

> *"I did not feel any difference in grinding or stuttering (micro-ratcheting) behavior at all on V97,
> so I stopped the drive. All I did was a parking lot creep and engaged LKAS and illicited/provoked
> the grinding and ratcheting."*

> *"Perhaps this pole edit is dead somehow, either a mistaken cal address, or maybe the logic we
> touched isnt used. This has happened before, we need to be careful about determining whether some
> code actually gets executed in the way we think."*

Then, mid-session, two standing instructions:

> *"the exposure really should not matter… if I observe micro-ratcheting or grinding, I am generally
> going to stop instantly. No point in continuing that drive if the single thing I'm testing for did
> not get fixed."*

> *"It should not be uninterpretable is what I'm saying"*

🛑 **Both are now in `CLAUDE.md`. "UNINTERPRETABLE" is a DESIGN FAILURE on our side, not a verdict.**
Design for **~15–30 s of engaged symptomatic frames, one episode** — that is what every future drive
will give.

---

## 2. V97 IS LIVE — the operator's hypotheses, refuted

**"A mistaken cal address" — excluded three independent ways.**
- `0x38202` bytes `e5 6f ad 73` decode to `ld.hu 0x73ac[tp],r13`; `tp+0x73AC = 0xC63AC`. The adjacent
  `0x381FE` is `ld.w -0x374c[gp],r6` — the accumulator, exactly as the docstring says.
- `0xC63AC` reads **102 / 102 / 150** (stock / V96 / V97). Off-by-0x1000 excluded (`0xC53AC` = 683,
  identical in all three) and the six neighbour cals `0xC63A0..0xC63AE` all read 1024 unchanged.
- Census **1 reader / 0 writers** by five methods, including a re-test against the `ep`-aliasing trap.
  **Ghidra ∖ Python set-difference is EMPTY.** V96→V97 diff = **5 bytes** (one cal + its CRC).

**"The logic we touched isn't used" — refuted statically AND dynamically.**
```
0x221D6  andi 0x830,r25,r28          r28 ≠ 0  ⟺  gp-0x67fa ∈ {4,5,11}
0x225EE  cmp r0,r28 / be → jarl 0x26C80   ← the assist-channel MIXER
0x22672  cmp r0,r28 / be → jarl 0x38148   ← OURS.  BYTE-IDENTICAL guard, same r28
```
⇒ **a shut gate would mean NO POWER ASSIST AT ALL.** The operator was steering with assist.
And `sign(gp-0x374c)` **toggled 181× in 109 s** on route `0x80`. **No speed gate, no rate gate, no
engagement gate anywhere on the path**; the accumulator update precedes the only in-function gate.

---

## 3. WHY THE DRIVE COULD NOT SCORE IT — three independent reasons

| # | reason | evidence |
|---|---|---|
| 1 | **NO INSTRUMENT** | V96's cave carried unchanged; regressor **34× over-range**. `M ≡ 0` on **10,749/10,749** frames — third replication (7e 99.90 %, 7f 99.97 %, r80 **100 %**). `Mlo` duty 0.0000. S1/S2 **VOID — conceded in `builds/v80_v107/build_v97_tva.py:99-100` BEFORE the flash** |
| 2 | **EXPOSURE** | **1** engaged hands-off episode ≥2 s, **1** decaying-angle return — vs 24/27 and 14/11 on 7e/7f. The `\|Q\|=1.233` direction result rests on **25** |
| 3 | **THE OBSERVABLE** | **DC gain 1.000000 at any `A` — a POLE, not a GAIN** ⇒ no amplitude statistic can see it, **and none was pre-registered** |

Measured anyway, and every channel closed itself:
- phase contrast **+3.27°** in one cell, **−4.08°** in the other — **opposite signs**
- 6–9 Hz cross-build ratio **5.92× is SMALLER than r7e's own split-half noise, 6.98×**
- `sign(gp-0x374c)` crossing-rate: cross-build 12.50× against r7e's split-half **25.50×**, the two V96
  routes disagreeing with **each other** by 14×, and the control bit moving 2.06×

⊕ **V97 never claimed a grinding or ratcheting fix.** Its header prices only a 21 Hz **cost** and argues
direction from **hands-off returns**; route `0x80` was **19.5 % override / 80.5 % hands-off** at creep.
**"No difference in grinding" is consistent with the build working exactly as specified.**

---

## 4. ⭐ THE STRUCTURAL FINDING — one residual, two arms, neither ever measured

```
FUN_0003b8f6 — the 1 kHz PLANT MODEL / disturbance observer
   K0 0xC4080=0 (NEVER RAISE) · K1 0xC40D2=204 (V89, ON THE CAR) · relay 0xC40BC=600
   0xC40D0=408 · 0xC40D4=573 · 0xC40D6=246 · 0xC40D8=3686   ← four VIRGIN poles, same class as 0xC63AC
      │ gp-0x6bfc → FUN_0003bc20 (plausibility ±20000, else 0x7FFF)
      │ gp-0x6bfe ──── MODEL   ────┐  UNFILTERED   ◄── V89's K1
LKAS aggregator FUN_00026c80        │
      │ gp-0x6bfa ──── REQUEST ────┤  UNFILTERED   (its ±20000 gate is DEAD — writer pre-clamps)
six lanes → ×sign(gp-0x6752) → ×2639 (0xC6468) → <<4
      │ IIR pole 0xC63AC 102→150 = ALL OF V97
      │ (gp-0x374c>>4) ─ ACTUAL ───┘  MEASURED < 2048 on 100 % of route 80
                        iVar6 → gp-0x6b70 = sign × LERP(|iVar6|) = the PID REFERENCE
```
Coefficients **exactly ±1**, verified from raw bytes (`0x38238 subr r15,r6` opcode `0x0C`;
`0x3823A add r9,r6` opcode `0x0E`). **Both arms are estimates of the same quantity, same units, same
cal `0xC6468`=2639, entering a DIFFERENCE.**

⇒ **V89's K1 measured FLAT; V97's pole felt like nothing. ONE unmeasured quantity explains both.**

🛑🛑 **A "≤ 9 % share" bound was computed and is RETRACTED — DO NOT REUSE IT.** Bounding one arm
against the other's *admitted range* is invalid for a difference of correlated estimates; the
denominator is the **residual**. **Path-2's share is UNRESOLVED, not small.**

---

## 5. TWO STANDING CLAIMS THAT FELL

**The Stage-2 transfer IS readable.** `STATE.md` §A6b's *"cannot be read from the image"* is FALSE.

**`f′` does NOT swing ≥10× — it swings 1.000×.** `gp-0x6982`/`gp-0x6984` have **ZERO writers
image-wide** (Ghidra + raw disp16 + raw disp23 + exhaustive 32-bit-literal search, **with a working
positive control** — the neighbours `gp-0x6980/86/88/8A` all DO have `st.h` writers and the scan found
them) and both boot to **1024** from `.data` (flash `0x8672E`/`0x8672C`). The `[204,2048]` rails guard a
value that never moves. **The original claim came from reading cal bounds as a live range without
checking whether the inputs move.**

Knots (mode 26, creep; `0xC63AE`=1024 ⇒ index is `|iVar6|` raw):
```
0.0 km/h  X [0,200,400,800,1200,1800,3000,5000,12000,14490]  Y [0,471,880,1408,1689,1953,2376,2844,4114,8192]
6.6 km/h  X [0,178,356,719,1200,1800,3000,5000,10681,14490]  Y [0,452,839,1382,1838,2131,2546,3043,4245,8192]
```
**Route 80 inverted:** p50 320 → `|iVar6|` **126–136** · p90 2,534 → **2,965–3,675** · max 3,187 →
**5,681–6,891**. ⇒ **`|iVar6| ≤ ~6,900` at creep, ~130 half the time.**
⊕ **Median 130 against a six-lane term admitted to 2048 hints at strong CANCELLATION** — what an
observer residual should do. [live hypothesis]
⚠ **Does not travel above 50 km/h** (`0xC669A`/`0xC66A8` truncate the X axis to 7,000).
⚠ **`mode 24 ≠ mode 26` in THIS family** — the "stock ships 24 ≡ 26" memory is scoped to the **damper**
families and does not generalise.

---

## 6. THE AUDIT — 29 dead levers, 11 classes, and a 12-gate checklist

`docs/review/AUDIT-2026-08-12-dead-levers-and-liveness.md`. Classes T1–T11; **T10 is new**:
**"the instrument is invariant to the lever"** (`y = K·α`, α is what K damps ⇒ in a stable loop the
product is invariant to K). **It explains V91/V92, and V94 cutting the same cell 6× and being ABORTED
proves that cell reaches the car** ⇒ **not a dead lever, an unmeasurable one.**

🛑 **The design law, from all 45 probe builds V53→V97 — now in `CLAUDE.md`:**
> **Every probe that DECIDED something was a SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL, or a
> deliberately-designed CONTROL. Every UNINTERPRETABLE null was a SINGLE THRESHOLD RUNG on a quantity
> with no measured distribution and no positive control.**

⊕ And the kit usually **knew at cut time** — V86's docstring says outright *"THE PROBE CANNOT SCORE
`0xC40D4` IN FORCE"*; **V80 flew after its own docstring said it could not discriminate itself from V79
at the flown speeds.** The knowledge was there; the gate was not.

### 🛑 What has ACTUALLY moved a symptom — two lists, not merged
**Exactly TWO interventions in sixty builds have BOTH a measured change AND the operator's own report
of improvement: V62 and V88.** Both **rate-lane, mode-proof, command-side**.
⚠ **V88 did not BEAT the kit's best grinding result — it RECOVERED to it**: `V88/V67 = 1.101
[0.424, 2.206]`, after V87's rebase deliberately gave Lever B up.
🛑 **NOTHING has ever moved micro-ratcheting or ratcheting.** Reported present on V76, V81, V83a, V84,
V85, V86B, V87, V88, V89, V90 and V97 — and the only two builds that moved them measurably moved them
the **wrong way** (V83a 1.526× [1.174, 2.019]; V94 aborted).
⇒ **"V97 felt like nothing" is the MODAL outcome of this arc, not an anomaly.**

---

## 7. ⭐ THE COMPARATOR — the design idea that unblocks this

> **When you do not know a signal's scale, do not QUANTISE it — COMPARE it.** A comparator rung is
> **immune to UNDER-RANGED and OVER-RANGED by construction**: no LSB, no ceiling, no assumed
> distribution. It compares at full precision **inside the cave, before quantisation exists**, and its
> **duty is the answer.**

V96 lost a whole channel to a 34× over-range guess; a comparator could not have failed that way.
**Two comparators rank all three arms per frame with no scale assumption at all.**
⚠ Buildability: V96's flown cave was **single-operand on `r6`/`r7`**; a comparator is two-operand ⇒
**recompute the operand inside each rung** (+~20 B, keeps the proven discipline) rather than claim a
third scratch register dead.

**Exposure, re-derived as a per-frame measurement rather than a contrast:** `SE = sqrt(p(1−p)/n_eff)`.
At a pessimistic τ = 1.0 s, **17.2 s gives n_eff = 17 and separates duties 0.9 / 0.5 / 0.1 at ~3σ.**
⇒ **17 s resolves the ORDERING of the arms, which is the endpoint. It does not resolve a duty better
than ±12 %, which is not the endpoint and is not claimed.**

---

## 8. RECORD REPAIRS MADE THIS SESSION

| defect | fix |
|---|---|
| **`0xCBE74` is a POINTER PAIR, byte-identical stock→V97** | The dosed bytes are **`0xD6A6C` (m24) / `0xD7A5C` (m26) / `0xD7A6C` (m27)**. stock `(−9830,−5734,−1966)` → V91/V92 `(−14745,−8601,−2949)` = ×1.5 exactly. 🛑 **V96's "REVERT.CBE74" reverted to V91/V92's DOSE, not to stock — V97 carries it** |
| `memory/…cbe74…md` frontmatter **contradicted its own body** | corrected; `MEMORY.md` pointer rewritten |
| `0xC6194` reason *"output ×0"* **WRONG** (~2 weeks) — that is `0xC6196` | corrected in `memory/reference/firmware/reference-accord-lkas-friction-is-viscous-not-a-rate-limit.md`. Real reason: partition `0xC4118` is all-1 ⇒ 100 % bypasses it |
| **PART1 lever index 15 builds behind** — a grep for `0xC63AC` returned NOTHING | 17 rows added through V97 + a **"CURRENT THROUGH V97" banner** |
| **`BUILD-LINEAGE.md` had NO V97 ROW AT ALL** | written, with the flight result |
| V88 row carried **no operator quote** | added, with the "recovered to V67, did not beat it" scoping |
| V94 row's `a3`→`a1` is right vs V90, **wrong vs V92** | corrected; full 427 chain written out |
| **`specs/SPEC-2026-08-11-telemetry-budget.md` still allocated 427 to `gp-0x6bbe`** — a lever closed as dead | SUPERSEDED banner |
| **Golden model 310 KB — over the `Read` cap, tail silently truncated** | **SPLIT into 4 modules + facade** (§9) |

⚠ **V93/V94 are NOT a walk-back from V91/V92's dose** — both branch off flown **V90**, which is
**byte-stock** at the dose address. The 6× is a valid *ratio* between builds, not a modification of V92.

---

## 9. THE GOLDEN MODEL WAS SPLIT — and there is now a runnable contract

| file | KB | contents |
|---|---|---|
| `model/eps_lkas_chain_model.py` | 31 | **FACADE** — re-exports all 87 symbols; existing imports unchanged |
| `model/eps_chain_core.py` | 37 | SECTIONS 0–1 |
| `model/eps_chain_lanes.py` | 119 | SECTIONS 2–3 |
| `model/eps_chain_control.py` | 90 | SECTIONS 4–6 |
| `model/eps_chain_delivery.py` | 33 | SECTIONS 7–9 + `control_task` + `_self_check` + `_demo` |

Dependency order strict and acyclic: `core → lanes → control → delivery`.
🛑 **CONTRACT — re-run after ANY edit:** 87 symbols, and `_self_check()` + `_demo()` stdout hashing to
**`740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`** (2,512 bytes). Fixtures:
`analysis-2020accord/_scratch/out/_golden_contract_syms.json` / `_golden_contract_baseline.txt`.
**Proof of verbatim move:** concatenating the four blocks reproduces original lines 314–EOF exactly
(3,720 lines, `recon == orig[313:]` True) — no line added, dropped, re-wrapped or reformatted.
⚠ **Line-number citations of the old single file are now WRONG** (`studies/sessions/v77/v77_dose_math.py:20,26,193`,
`lib/_r5d_lib.py:191`, `builds/v50_v79/build_v62_tva.py:17`, `rlog-tools/probe/decode_v70_probe.py:67`). **Grep the symbol name.**

---

## 10. V98 — BUILT AND UNFLASHED, the first COMPARATOR probe in the kit

```
39990-TVA,A160-V98-V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2-0x13000-0x100000.rwd
  image c9babfed6acf24c0c5877754149a60fd5866dae8407029d7a3a5d74870d151d9   1,048,576 B
  rwd   fcfa1baa82ea8fbca104eee5c8a398b7d5de8762629351128b05e0cb811e5e3c     986,042 B
  builder analysis-2020accord/builds/v80_v107/build_v98_tva.py   199/199   BASE = V97 (on the car)
```
🛑 **ZERO calibration bytes. ZERO 427 bytes. Cave only — AN INSTRUMENT, NOT A FIX.**

| bit | signal | role |
|---|---|---|
| byte4 b7 | `gp-0x6b70 < 0` | V96's rung, byte-identical |
| **b6** | ⭐ `\|gp-0x6bfe\| ≥ \|gp-0x374c>>4\|` | **MODEL vs ACTUAL** |
| **b5** | ⭐ `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` | **REQUEST vs ACTUAL** — with b6, ranks all three arms **per frame, no scale assumption** |
| b4 | `(gp-0x374c>>4) < 0` | V96's rung — **the converse positive control**, previously measured `arg(B′)−arg(rate)` = **+78.6°/+78.0°** on two routes. A broken bit map cannot fake +78° |
| b3 | `gp-0x6752 ≥ 0` | closes a multi-session blocker; **a DEPENDENCY, not a rider** — it multiplies the whole six-lane sum, so b4 is otherwise ambiguous by a global sign flip |
| byte7[7:6] | hard-wired **2** | identity + liveness |

**Why a comparator** — `[[accord-probe-design-law-compare-dont-quantise]]`: no LSB, no ceiling, no
assumed distribution. **V96 lost a whole channel to a 34× over-range guess; this cannot fail that way.**

**ORCHESTRATOR-VERIFIED FROM DISK** (not relayed): both hashes ✓ · V97→V98 diff **146 B**, all in
`0xC4B34–0xC4BCD` + `0xC4FFC`, **zero unattributed** ✓ · **every cal cell identical to V97** ✓ ·
**GATE 2 re-derived independently — gp-relative store scan of the built image vs stock returns exactly
3 stores across exactly 2 cells (`gp-0x1514`, `gp-0x1511`), none removed** ✓.

**GATE 1 PASS** — `gp-0x6bfe` 1R/1W · `gp-0x6bfa` 2R/3W (±20000 clamp, shadow `gp-0x4cfa`) ·
`gp-0x6752` **51R/5W** (boot-parsed, shadow-validated static in {−1,0,1}; 🛑 **not** 49R/6W, **not** 55) ·
`gp-0x374c` **already read twice by V96's flown cave**. Wider 32-bit span scan **67 accesses, ZERO
span-only hits**; 0 `movhi`/literal synthesis with the detector validated on 7,647 candidates; loads
side-effect-free (all 58 peripheral bases in `0x40000000–0x407EC000`).

⭐ **PSW hazard checked MECHANICALLY from the built image's own decode** — 9 `cmp`→branch windows,
7 adjacent, 2 containing exactly one `mov imm5`, **0 violations**; all three `sar 0x4,r6` immediately
followed by the `cmp` that re-establishes flags.
⭐ **Hook rate PROVEN FROM THE IMAGE**: `0x55C14 = movea 0x14A,r0,r8`, four instructions past the hook
⇒ **the 100 Hz `0x14A` CAN-TX builder, NOT the 1 kHz control task.** DI window +~1–2 µs against 10 ms.
`cmp rA,rB` = `rB − rA` verified four ways ⇒ **the comparators do not invert.**

**Cave 112 → 154 B (+42 B, +37.5 %), 43 → 59 instructions, 12.7 % of the 1,212 B extent — stated, not
claimed away.** ⚠ **`SPEC §R8` under-priced this**: a comparator needs **three live values in two
registers**, so recomputation alone cannot fix it. Byte 4 is read-modify-written twice with two masks
(`0xDF`/`0x27`) **proven to partition the byte**. **Path 2 was never available** — `r6`/`r7` are the only
registers the record can defend.

🛑 **SCORER WARNING — the ~50-build *"byte4[7:3] is always ODD"* convention DOES NOT HOLD on V98.**
`b3` is a measurand, so **byte4 goes EVEN whenever `gp-0x6752 < 0` — and that is the FINDING, not a
fault.** Liveness moved to **byte7**. Without this, a scorer pulls a working build.
🛑 **`0x7FFF` sentinel, PRE-REGISTERED:** when the plausibility latch fires, `gp-0x6bfe` = `0x7FFF` and
b6 reads TRUE for a reason unrelated to the share. The latch rails `gp-0x6b70` ⇒ **427 pins at exactly
1023. Score b6 only on frames with 427 ≠ 1023, and report the excluded count.** Measured duty **0 on
87,423 frames** — but *"measured never" is not "structurally impossible"*.
⚠ **ONE OPEN GAP BEFORE ANY FLASH:** `mov`'s flag-transparency is **BELIEF** — Ghidra's SLEIGH model
plus Honda's own instruction scheduling, **not a manual quotation**.

**DRIVE PROTOCOL: ONE parking-lot creep, LKAS engaged, hands on — stop the moment the symptom is felt.**
~15–30 s of engaged frames. **No matched arms, no episode counts, no highway, no second drive.**
Optional and free: a few seconds of the same creep LKAS-off; and **60 s turning the wheel by hand with
the car OFF** (a positive is strong, a negative is weak).

**How V98 differs from the whole arc since V38** — V38–V52 authority/filters/poles · V53–V61 telemetry ·
V62–V73 the rate lane · V74–V83a the damper · V84 damper reverted · V85–V94 the plant model and its dose ·
V96 an instrument · V97 a loop pole. **Every instrument in that list measured ONE quantity against an
ASSUMED SCALE, and six died to that assumption. V98 measures nothing — it COMPARES**, and asks which arm
of the observer residual is biggest. **That question has never been asked, and the two most recent levers
(V89, V97) both moved arms of that same residual blind.**

## 11. OPEN

1. **Which arm of the observer residual dominates.** The whole point of V98.
2. **`sign(gp-0x6752)`** — no longer a blocker: **49 readers, a whole-instruction twin at `0x28F22`**, one
   rung closes it. It multiplies the **whole six-lane sum**, not just a Path-1 gate.
3. **Clause 2 (return-to-centre speed) still has NO mechanism.** Three candidates died; the field is empty.
4. **Plant vs firmware is still unrun.** ⭐ Cheapest test in the kit: **turn the wheel by hand, car off,
   60 seconds.** A positive is strong; a negative is weak (unpowered friction masks the mode). **Run it.**
5. **Build identity needs ≥3 bits.** byte7[7:6] gives ONE clean generation and V96/V97 burn {1,3}.
   A durable field needs its own `0x18F` hook — **as its own build**, never combined with a new
   measurement class (that is how V24/V27/V48B bricked ECUs).
6. **Task rate is 1000 Hz [EVIDENCE]** — `0xC64DF`=100 measured at 100.00 ms + the `0x830 ⊆ 0x930`
   lockstep. 🛑 **NOT from OSTM0**, which is 500 Hz (PCLK is 40 MHz). An agent nearly shipped that
   circular inference this session and caught it against the record.
7. **`TaskList` reports "No tasks found" while agents are alive.** Roll-call with a `TaskStop` probe on a
   bogus id — its error enumerates running teammates. **Sub-agents spawned BY sub-agents are the ones
   you forget.**
