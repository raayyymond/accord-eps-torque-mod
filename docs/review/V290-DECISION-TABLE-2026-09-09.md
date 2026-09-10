# V290 — ONE DECISION TABLE, and the reconciliation of the two contradictory rankings

**Agent**: `reconcile` (SUBAGENT, orchestrator `main`). **Analysis only — nothing was built, flashed or sent.**
Date 2026-09-09.

**Scripts (everything below reproduces from these two)**
- `rlog-tools/studies/grind/reconcile_v290.py` — the placement switch, the two grid re-runs, the decision table.
  Outputs `_scratch/reconcile_v290_table.txt`, `_scratch/reconcile_v290_task1.txt` (+ `.json` beside each).
- `rlog-tools/studies/grind/reconcile_prail_r31_r34.py` — Task 3, the clamp-bind duty. Output `_scratch/reconcile_prail.txt`.

**Inputs read, not re-derived**: `_scratch/design290b_family.json` (the 304-fit plant family; advnull independently
spot-verified it reproduces to 0.0000 Hz and 0.0000 in ζ on 8 fits, and I use the same file), the flown plain images
under `$ACCORD_FIRMWARE_ROOT/analysis-2020accord/`, and the route caches under
`analysis-2020accord/_scratch/cache/`.

---

## 0. THE HEADLINE

**The two rankings were never in conflict. They answer different questions and both answers are correct.**

`design290d`'s null — 0 of 384, 1 of 1152, and that one row being V282 itself — is a statement about **one
topology**: every filter it scored sits on the loop OUTPUT, in the command path as well as in the loop. Inside
that topology, and inside the cal-only (Kd, fb pole) plane, its null holds and I reproduce it. Re-run in the
feedback placement its two grids give **30 of 384** and **35 of 1152** — but ⚠ **only the first of those is a real
win**: apply the operator's ×1.00 steady-state requirement and 32 of the 35 section-10 rows fall over (they buy
their ζ by cutting Kp and paying 3.5–13.5 % of authority), leaving V282 on top there again. **Its hardest claim —
that PM_worst ≥ 40° does not exist in this space — survives completely, 0 rows in either placement.** §1.3.

`advnull`'s candidate is a statement about a **topology design290d never scored**: the same filter on the
**feedback operand**. Its return ratio — and therefore every pole, ζ, Ms, phase margin, gain margin and the 7 Hz
gate — is algebraically IDENTICAL; only the reference transfer differs, which is exactly the column
(capped-step peak rate) that killed every forward row.

**The best CAVE candidate is `notch 21.5 Hz Q1.5 on the FEEDBACK OPERAND + fb pole 40 Hz`** — the only filter row
that shortens the ring materially (582 → 452 ms, 11.7 → 7.4 cycles) while holding steady-state authority at
×1.000, t90 at V282's 13 ms, the 7 Hz gate at ≤ 1.01, and zero unstable fits.

**But the best candidate OVERALL is neither agent's, and it is cal-only.** `reqaxis`'s trace landed after both
closed out, and its byte facts make a **SCHEDULED Kd cut** (`Y[0..2] = 96, Y[3] = 128` in the slot-7 Kd record)
scorable from rows already in this table. It reaches the **shortest ring in the table, 254 ms / 5.0 cycles**, with
the 7 Hz gate and the capped-step peak rate at ×1.000 **by construction** — because above demand index 32 the Kd
lookup takes its high-clamp branch and returns a byte that has not changed. Ten bytes, no cave, HF noise going the
right way. It has one unmodelled hazard (a gain switching inside the ring cycle is a parametric modulation) and it
reaches only ~half the grinding-episode time. **§5.**

**Two things that must be said with the cave row, because they are costs nobody has priced:**
1. **HF noise into the motor rises ×2.21** (fb 50 Hz) or **×1.91** (fb 40 Hz), rms |R| over 30–500 Hz vs V282.
   That is the price of dragging the feedback pole from 16.5 Hz to 40–50 Hz, and it is a *new* class of risk for
   this kit — no flown build has raised HF loop gain by 2×. **The mechanism is concrete, not abstract**: the
   0x18F wire rate arrives at ~100 Hz and is zero-order-held across the 1 kHz loop, so everything above ~50 Hz in
   that operand is the held value's own staircase. V282's 16.5 Hz feedback pole filters most of it away; a 50 Hz
   pole passes roughly three times as much of it straight to the motor. This is a plausible source of a NEW
   audible artefact, and it is a column advnull's report does not carry at all. **It applies identically in
   either placement** — the notch and the fb pole both sit between the sensor and the motor in both topologies,
   which is why `plant_free`'s return-ratio-based noise figure is the right instrument here.
2. **pkR on the WORST fit is 0.90 / 0.93**, below the operator's 0.95 floor. advnull gated on the MEDIAN;
   design290d's section 10 gated on the MINIMUM. Which the floor means is an operator decision, not ours.

**And one clear negative result the brief asked for**: re-aiming the element at the 16–17 Hz crossing
`modenat2`'s reversal identifies **makes every metric worse**. Do not do it. §3.

---

## 1. TASK 1 — did design290d's ranking include the feedback placement? **NO.** [EVIDENCE]

Method: read `rlog-tools/studies/grind/design290b_candidates.py` end to end (1013 lines) and grep it for any
placement switch.

| finding | where |
|---|---|
| Every filter enters through one door: `Elec.__init__(..., sumfilt=[...])` convolves each `(b, a)` into `self.N`. | `class Elec.__init__` |
| `self.N` is consumed by `bracket()` = `Hlag*N − g*(1−N)`. | `Elec.bracket` |
| `bracket()` is called by **both** `R()` (the return ratio) and `fwd()` (the reference transfer). ⇒ every scored filter is in the command path. | `Elec.R`, `Elec.fwd` |
| The section-4 solve builds `Elec(cc, sumfilt=[(b, aa)])`. Grid = `np.arange(15.0, 22.51, 0.5)` (16 centres) × Q(1.5, 2, 3, 4) × fb(16.53, 20, 25, 30, 35, 40) = **384, all forward.** | `_joint_worker` |
| The section-10 search builds `Elec(cc, sumfilt=sf, g=g)`; `sf` is the notch OR the lead. **1152, all forward.** | `_r9_worker` |
| No occurrence of `place`, `feedback`, `fb_operand`, or any placement flag anywhere in the file, including `mirror_rows`, `recentre_walk` and `frontier`. | whole file |
| It did not act on the forwarded finding: `_scratch/design290b_cands.txt` still ends section 10 with *"DOES NOT EXIST in this space"* over the same 1152 forward combos. | `_scratch/design290b_cands.txt` |

**⇒ "0 of 384" and "1 of 1152" are ONE-TOPOLOGY results.** They are correct about the forward placement and
say nothing about the feedback operand. advnull's structural claim is right.

### 1.1 I verified the crux myself, in design290d's machinery, not advnull's [EVIDENCE]

`reconcile_v290.ElecP` is `design290b.Elec` with exactly one change: `fwd()` drops `N` when `place == "fb"`.
Same notch (21.5 Hz Q1.5, Q14-rounded by design290b's own `rbj`), same fb pole (50 Hz via its own
`dc_held_pole`), same plant (family fit 0), same `metrics()`:

```
                     place=fwd            place=fb
pole f               17.23695402914064    17.23695402914064     identical
pole zeta             0.09077018604097     0.09077018604097      identical
Ms                    2.7142847874132716   2.7142847874132716    identical
gate73                0.9889291943741266   0.9889291943741266    identical
capped-step pkR       0.8905               0.9865                <-- the whole difference
t90                  21 ms                11 ms  (= V282's 11)   <-- and this
```

This is not advnull's code and not advnull's numbers. The topology claim is **EVIDENCE**.

### 1.2 The physical placement is REAL, and its census is already proven [EVIDENCE, `fbhook`]

`docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md` had already closed the question an adversarial
pass would otherwise have to open:

- The feedback operand is register **`r26`**, a single live 32-bit value with **zero intervening accesses** from
  `0x28FBE` (clamp resolved) to `sub r26,r16` at `0x29D78` — 3,514 bytes of code, 18-hit whole-function `r26`
  census reproduced. ⇒ filtering it at hook `0x29D72` touches the rate loop **and nothing else**. The census the
  kit's own rule demands ("a cell is not private because you did not find another reader") is done.
- Hook site `0x29D72`, `st.h r16,-0x6a32,gp`, bytes `64 87 ce 95` → `89 07 1e af` (`jr 0xC4C90`). Cave at
  `0xC4C90`, 868 free bytes, same CRC block as V289's cave — one CRC recompute at `0xC4FFC`.
- **Q6, the historical question**: the feedback placement was scored during the V289 design (row `(d-fb)`,
  identical loop metrics, **authority ×1.03/×1.00 against the sum node's ×0.92/×0.93**), lost on ONE physics
  argument — *"the setpoint's 20 Hz kick still reaches the motor"* — and the hook was left **explicitly open**.
  **No blocker was ever recorded.** That argument is precisely what V288 rev 2 weakened by flying a
  reference-side filter with the grinding unchanged.
- ⭐ **My own adjudication of that lost argument, because it is the only thing that ever counted against the
  feedback placement.** The sum-node placement removes 20 Hz from the *whole* command, the setpoint's own kick
  included, and it scrubs the D-kick on a capped step. The feedback placement does neither. **But that is the
  same fact as its authority advantage, seen from the other side**: pkR is preserved *because* the D-kick is not
  scrubbed. You cannot have both — and the kit has now flown the experiment that says which one to want.
  **V288 rev 2 flew a reference-side filter (a setpoint pre-filter, D-bind ×0.03) and the grinding was
  UNCHANGED.** The reference-side class is closed on the car. ⇒ paying ×0.92/×0.93 of authority to scrub a
  setpoint kick that has been measured not to matter is the wrong trade, and it is the trade V289 made.
- Two build costs advnull did not model, both from `fbhook`: a V289-style Q14 TDF-II **overflows int32** against
  the fb clamp 46080 (bound 5.87e9, margin ×0.37) and needs a **`sar 3` pre-shift + `shl 3` post-shift** (margin
  ×2.93, cost 0.032 deg/s of feedback resolution); and the hook is **skipped once the engage ramp reaches 0**, so
  the cave must seed `x1 = x2 = y1 = y2 = r26` on Honda's first-tick sentinel `gp-0x6cf8 == 0x7FFFFFFF` — not
  zero, or the filter steps into a sharp resonator on re-engage.

### 1.3 The re-run of design290d's own two grids, feedback placement

Same grids, same fits (121 stable for section 4; the same `[::2]` 61-fit subsample for section 10), same
scoring functions. **`_scratch/reconcile_v290_task1.txt`.**

Both stages completed (1242 s and 1954 s). Full output `_scratch/reconcile_v290_task1.txt`.

**Section 4, the joint (notch f, Q, fb pole) solve — the same 384 combos, the same 121 fits:**

| placement | feasible (gate73 ≤ 1.01, pkR_med ≥ 0.95, 0 unstable) |
|---|---|
| forward (design290d) | **0 of 384** |
| **feedback (this re-run)** | **30 of 384** |

Best feasible by worst-case ζ: **21.5 Hz Q1.5 + fb 40 Hz — ζ_w +0.021, ζ_med +0.049, gate 1.009, pkR_med 0.97,
noise ×1.91.** That is advnull's row. (fb 50 Hz is outside design290d's grid, which stops at 40 — which is why its
own search could not have found the fb-50 sibling even in the right topology.)

**The like-for-like comparison is the cleanest possible demonstration.** Take design290d's own printed row
`20.5 Hz Q1.5 fb 35.0` from `_scratch/design290b_cands.txt` and mine from `_scratch/reconcile_v290_task1.txt`:

```
                            z_min  z_med |  PM_w | f_med    Ms | gate73 | pkR_m  pkR_w
design290d, FORWARD         0.021  0.058 |  +6.7 |  15.8 13.13 |  1.032 |  0.78   ...
this re-run, FEEDBACK       0.021  0.058 |  +6.7 |  15.8 13.13 |  1.032 |  0.98   0.94
```

**Every loop metric is identical to the printed digit. Only pkR moves — 0.78 → 0.98.** That single column is the
whole of design290d's null.

**All 30 feasible section-4 rows hold steady-state authority** (dc 0.997–1.003) and **t90 = 13 ms = V282's**.
The lowest-HF-noise feasible row is `19.0 Hz Q2.0 + fb 35 Hz` — ζ_w +0.018 / ζ_med +0.047, gate 1.007,
pkR 0.96/0.92, dc 1.003, noise **×1.80** — a slightly cheaper noise bill than 21.5/fb40's ×1.91 for 0.003 of ζ_w.

**Section 10, the constrained search — the same 1152 combos, the same 61 fits, the same stricter pkR_WORST ≥ 0.95
gate design290d used there:**

| placement | passing the authority gates | of those, PM_worst ≥ 40° | ζ_worst ≥ 0.08 |
|---|---|---|---|
| forward (design290d) | **1 of 1152** (and it was V282) | 0 | 0 |
| **feedback (this re-run)** | **35 of 1152** | **0** | **0** |

⚠ **But read this one carefully, because it is NOT a clean win and I will not present it as one.** Every row that
beats V282 here does it by **cutting Kp to 160 / 200 / 220**, and that costs **steady-state authority: dc drops to
0.865 / 0.936 / 0.965.** design290d's section-10 gates did not include a dc gate. **Apply the operator's standing
×1.00 steady-state requirement (dc ≥ 0.995) and only 3 of the 35 survive**, and the best of those by worst-case ζ
is still V282 itself:

```
Kp248 Kd128 no-notch  fb17 lag5.0  [fwd]  z_w +0.013  z_med +0.031  gate 1.003  pkR 1.00/1.00  dc 1.000  = V282
Kp248 Kd128 nt20Q3    fb25 lag5.0  [fb ]  z_w +0.006  z_med +0.027  gate 1.005  pkR 0.98/0.96  dc 1.000  = V289's notch, moved
Kp248 Kd96  nt18Q1.0  fb35 lag12   [fb ]  z_w +0.003  z_med +0.044  gate 0.968  pkR 1.25/1.14  dc 1.000  Ms 67, noise x3.03
```

⇒ **design290d's section-10 null largely SURVIVES the topology change**, and its harder claim —
*"PM_worst ≥ 40° does not exist in this space"* — survives **completely**: 0 rows in either placement. **The reason
the winner is not here is that section 10 could never have contained it**: its notch list is
`16.7Q3 · 17.5Q2 · 18.5Q1.5 · 20.04Q3 · 18.0Q1.0` — **21.5 Hz Q1.5 is not in it.** The winner lives in section 4's
grid, and only in the feedback placement.



---

## 2. TASK 2 — THE DECISION TABLE

Every row scored with design290b's own `metrics()` / `step_lin()` / `plant_free()` over its own family, so these
numbers sit alongside `_scratch/design290b_cands.txt` without translation. Full 35-row table:
`_scratch/reconcile_v290_table.txt`.

- **FULL** = the 121 fits linear-stable on V289 (ζ289 ≥ 0.005).
- **SUB** = the 87 of those also consistent with the MEASURED V289 burst decay (ζ_eff 0.02–0.13). ⭐ **This is
  the honest read** — see §4, the family is biased pessimistic and the SUB set is the part the car has not
  already contradicted.
- **gate73** = the 7 Hz strong-turn gate, ≤ 1.01 required. **pkR** = capped-step peak rate vs V282, ≥ 0.95.
  **dc** = steady-state authority, ×1.00 required. **noise** = rms|R| 30–500 Hz into the motor vs V282.
  **S1014 / S2230** = worst new-sensitivity-peak ratio vs V282 in 10–14 / 22–35 Hz. **ring** = time for the ring
  to fall to 10 %, at the median fit's own pole frequency.

| # | candidate | placement | ζw / ζm FULL | ζw / ζm SUB | gate73 | pkR med / worst | dc | t90 | Ms_w | noise | S1014 / S2230 | unst | ring | bytes | class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | **V282 (the revert)** | — | +.013 / +.031 | +.013 / +.034 | 1.003 | 1.00 / 1.00 | 1.000 | 13 | 19.4 | 1.00 | 1.0× / 1.0× | 0 | **582 ms / 11.7 cyc** | 0 | revert |
| **1** | **notch 21.5 Q1.5 + fb 50 Hz** | **feedback** | +.025 / +.052 | **+.040 / +.057** | **0.989** | 0.95 / **0.90** | 1.000 | **13** | 10.0 | **2.21** | 1.6× / 0.9× | 0 | **424 ms / 7.1 cyc** | 4 cal + cave | cave |
| **2** | **notch 21.5 Q1.5 + fb 40 Hz** | **feedback** | +.021 / +.049 | +.035 / +.057 | 1.009 | **0.97** / 0.93 | 1.000 | **13** | 13.1 | 1.91 | 2.0× / 0.9× | 0 | **452 ms / 7.4 cyc** | 4 cal + cave | cave |
| **3** | **Kd 112 flat (cal-only)** | — | +.021 / +.052 | +.021 / +.051 | ❌ **1.038** | 0.97 / 0.94 | 1.000 | 14 | **7.5** | **0.88** | 1.2× / 1.0× | 0 | **359 ms / 7.1 cyc** | 2 cal | cal-only |
| 4 | Kd 96 flat (cal-only) | — | +.029 / +.074 | +.029 / +.073 | ❌ 1.073 | 0.94 / 0.89 | 1.000 | 15 | 4.9 | 0.77 | 1.4× / 0.9× | 0 | 254 ms / 5.0 cyc | 2 cal | cal-only |
| 5 | Kd 80 flat (cal-only) | — | +.038 / +.100 | +.038 / +.097 | ❌ 1.109 | 0.92 / 0.84 | 1.000 | 16 | 3.7 | 0.65 | 1.8× / 0.9× | 0 | 191 ms / 3.7 cyc | 2 cal | cal-only |
| 6 | Kd 120 + fb 18 Hz — design290d's best feasible cell | — | +.013 / +.032 | +.013 / +.033 | 1.002 | 0.97 / **0.96** | 1.000 | 13 | 18.5 | 1.02 | 1.0× / 1.1× | 0 | 568 ms / 11.4 cyc | 4 cal | cal-only |
| — | *V289 as flown, for reference* | forward | +.005 / +.028 | +.020 / +.033 | 1.005 | 0.79 / 0.75 | 1.000 | 14 | 45.6 | 1.40 | 1.6× / 1.6× | 0 | **786 ms / 13.1 cyc** | 4 cal + cave | cave |
| — | *same notch as #1, FORWARD (what design290d scored)* | forward | +.025 / +.052 | +.040 / +.057 | 0.989 | ❌ 0.78 / 0.65 | 1.000 | 18 | 10.0 | 2.21 | 1.6× / 0.9× | 0 | 424 ms / 7.1 cyc | 4 cal + cave | cave |
| — | *fb 25 Hz alone, no notch* | — | −.030 / −.003 | −.028 / −.001 | 0.925 | ❌ 0.50 / 0.09 | 1.000 | 10 | 406 | 1.43 | 0.8× / 4.5× | ❌ **68** | does not decay | 2 cal | cal-only |
| **S** | **SCHEDULED Kd — Y[0..2] = 96, Y[3] = 128** (§5) | — | +.029 / +.074 ¹ | +.029 / +.073 ¹ | **1.003** ² | **1.00 / 1.00** ² | 1.000 | 13 | 4.9 ¹ | **0.77** ¹ / 1.00 ² | 1.4× / 0.9× ¹ | 0 | **254 ms / 5.0 cyc** ¹ | 10 (6 + CRC) | cal-only |
| S′ | scheduled Kd — Y[0..2] = 112, Y[3] = 128 | — | +.021 / +.052 ¹ | +.021 / +.051 ¹ | **1.003** ² | **1.00 / 1.00** ² | 1.000 | 14 | 7.5 ¹ | 0.88 ¹ | 1.2× / 1.0× ¹ | 0 | **359 ms / 7.1 cyc** ¹ | 10 (6 + CRC) | cal-only |

¹ read at the **low-demand operating point** (idx < 22, where the cut is in force): identical to the flat Kd 96 / Kd 112 rows, which are already scored above.
² read at the **high-demand operating point** (idx ≥ 32): the Kd lookup takes its high-clamp branch and returns `Y[3] = 128`, byte-identical to V282, so gate73 and pkR are ×1.000 **by construction, not by estimate**. See §5 for the time-share this holds over and for the one risk it introduces.

**Cross-validation that my numbers really are design290d's numbers**: my `ring` column reproduces its section-E
ring table exactly on every row we share — V282 **582 ms / 11.7 cyc**, V289 rev 1 **786 ms / 13.1 cyc**,
Kd 128→96 **254 ms / 5.0 cyc**. Its `frontier()` best cell reproduces to the digit as well — Kd 120 / fb 18 Hz:
ζ_med **+0.032**, ζ_worst **+0.013**, gate **1.002**, pkR **0.97**, dc **1.000**, both in its output and in mine.
(My Kd 80 reads **191 ms**, not the 178 ms quoted in the brief; 178 does not appear in
`design290b_cands.txt`'s ring table, whose lowest Kd row is Kd 64 at 231 ms. Nothing turns on it.)

### 2.1 Reading the table

- **Only rows 1, 2 and 6 pass all three hard gates on the median** (gate73 ≤ 1.01, pkR_med ≥ 0.95, 0 unstable).
  Row 6 buys nothing: ζ_med +0.032 against V282's +0.031, ring 568 ms against 582 ms — **2 %**. design290d's own
  frontier verdict on the cal-only plane stands, and I reproduce it.
- **Every flat Kd cut fails the 7 Hz gate** — 1.038 / 1.073 / 1.109. That is not a modelling artefact: the gate is
  plant-free, computed from the return ratio at 7.3 Hz alone. design290d is right that a flat Kd cut is a
  *deliberate trade*, not a free win.
- **The fb-25-alone row is the control that shows what V289's notch was carrying**: the same fb pole change
  without the notch is unstable on 68 of 121 fits with pkR 0.50. Nobody should propose the fb pole as a
  standalone lever.
- **V289 as flown is the worst row in the table on ring length** — 786 ms / 13.1 cycles against V282's 582 / 11.7.
  It made the ring *longer*, consistent with what the operator felt (the line moved to 15–17 Hz, louder, in trains).

### 2.2 How much each verdict rests on a FIT vs on the five fit-free measured facts

Per `modenat2`'s standing instruction. The five fit-free facts are: the demand-gated census · the 18–22 Hz band
empty on V289 · the matched-load Kp contrast · the clamp null · the 16.63 Hz plant point.

| column | fit-dependence | what a wrong family would do to it |
|---|---|---|
| **gate73** | **NONE.** Plant-free: `abs(LS73 · R(7.3)/R₀(7.3) + LR73)`, computed from byte-read electronics and the two measured 7.3 Hz constants. | Nothing. The ❌ on rows 3–5 survives any plant. |
| **dc (steady authority)** | **NONE in practice** — ×1.000 on every row; it is set by DC gains that a notch and a pole-move both hold by construction. | Nothing. |
| **noise (HF into the motor)** | **NONE.** Plant-free, `rms|R|` 30–500 Hz. | Nothing. The ×2.21 cost of row 1 is real regardless. |
| **bytes / class / hook feasibility** | **NONE.** Byte facts from `fbhook`. | Nothing. |
| **t90** | **LOW.** Dominated by the loop's own bandwidth; the fb-vs-fwd 13-vs-18 ms split is a numerator effect. | Little. |
| **pkR** | **MEDIUM.** A closed-loop step on each fit; the fb-vs-fwd RANKING is structural (the filter is or is not in the numerator) but the absolute 0.90/0.95 is a family statistic. | The ordering survives; the 0.95 pass/fail could move. |
| **S1014 / S2230, Ms** | **MEDIUM-HIGH.** Sensitivity peaks depend on where the plant's own resonance sits. But the ×4–6 S1014 blow-up on the 16–17 Hz re-aim rows is so large it survives any plausible family. | Magnitudes move; the re-aim verdict does not. |
| **ζ_worst, ζ_median, ring ms** | **HIGH — this is the fit-dependent core.** Every one of these comes from root-finding `1 + L(z) = 0` on a family member. | This is where §4's pessimism bias lives, and why the SUB column exists. |

⇒ **The three decisions that matter most are the three least fit-dependent.** The re-aim is rejected on a
plant-free gate and a blow-up too large to be a fit artefact; the flat Kd cuts fail on a plant-free gate; the
feedback-vs-forward choice is settled by an algebraic identity plus a byte-level census. **Only the SIZE of the
prize — how much shorter the ring gets — rests on the family.**

---

## 3. THE RE-AIM TO 16–17 Hz IS A NEGATIVE RESULT [EVIDENCE]

The brief asked for the same element re-aimed at the 16–17 Hz crossing `modenat2`'s reversal identifies, since
advnull's rows were aimed before that reversal. I scored 16.0 / 16.5 / 17.0 / 17.5 Hz × Q 1.5 / 2 / 3 × fb 40 / 50,
all in the feedback placement (`_scratch/reconcile_v290_table.txt`). **They are worse on every axis that matters.**

| aim | Q | fb | gate73 | S1014 | Ms_w | unstable fits | ζm SUB |
|---|---|---|---|---|---|---|---|
| 16.0 | 1.5 | 40 | ❌ 1.075 | **6.5×** | 11.6 | 0 | +.054 |
| 16.5 | 1.5 | 40 | ❌ 1.067 | **6.3×** | 11.3 | 0 | +.057 |
| 17.0 | 1.5 | 40 | ❌ 1.059 | **6.2×** | 10.9 | 0 | +.061 |
| 17.5 | 1.5 | 50 | ❌ 1.032 | 4.7× | 7.5 | 0 | +.065 |
| 16.5 | 2.0 | 50 | 0.999 | 4.7× | **180** | ❌ 1 | +.047 |
| 16.5 | 3.0 | 50 | 0.948 | 3.2× | **200** | ❌ 13 | +.036 |
| 17.0 | 3.0 | 50 | 0.943 | 2.0× | **480** | ❌ 11 | +.036 |
| **21.5** | **1.5** | **50** | **0.989** | **1.6×** | **10.0** | **0** | **+.057** |

Two independent reasons, and they are not the same reason:

1. **A Q1.5 notch centred at 16–17 Hz reaches down to 7.3 Hz.** Its skirt costs the strong-turn gate 1.03–1.08 —
   and the operator's bookmarks sit on exactly those full-lock turns, where the 7.5 Hz ring was the last loud
   thing before each press. Narrowing to Q2/Q3 buys the gate back and immediately goes Nyquist-unstable on 1–14
   of the 121 fits with Ms 40–480.
2. **Aiming AT the crossing opens a new 10–14 Hz sensitivity peak, ×4.2 to ×6.5 vs V282**, where the 21.5 Hz aim
   opens only ×1.6. This is the waterbed doing exactly what V289 already demonstrated on the car: notch where the
   loop sits and the loop moves somewhere else. **V289's revert signature was a line at 14–17 Hz. These rows
   pre-register the same failure one octave lower.**

⇒ **The 21.5 Hz aim is not a stale target — it is the right one.** It works by sitting ABOVE crossover, where a
wide low-Q element buys phase without touching the turn band. Aiming at the crossing itself is self-defeating.

---

## 4. TASK 3 — THE FAMILY CONFLICT: the P-rail is REAL, and it is not the whole story [EVIDENCE]

**The open item** (design290d §A.4): all 304 fits go Nyquist-unstable at Kp 696, yet r31–r34 flew Kp 696 stable
with the ring at ζ 0.019 and f pinned within +0.4 Hz. Its BELIEF: a large-signal P-rail, which has zero
incremental gain for a small superimposed ring and would pin f across a Kp change.

**Method.** Replay design290b's own byte-exact `Controller` arithmetic — cells read from the flown V278 / V280 /
V282 images — on each route's MEASURED inputs: `x` = wire rate zero-order-held onto the 1 kHz loop grid (what the
ECU actually sees between CAN frames, so this is a MIRROR of the computation, not a simulation of the plant),
`sp` = the 0xE4 request through the assist map. Count, engaged-only, how often each clamp binds pre-clamp. The
map slope is the one assumed quantity, so it is swept ×1.5 / ×3 / ×6 / ×9 of stock's 172-count ceiling, ×6 being
LINEAR.TO6X; the duty is monotone in it.

⭐ **The map slope is not actually an assumption — `reqaxis`'s byte trace confirms it independently.** Its §3.1
table gives Kd knot `X[3] = idx 32 = 516 0xE4 counts → rate setpoint 138` on V289's LINEAR.TO6X map, and
`1 idx LSB = 16.1257 wire counts` exactly. That is **0.2674 setpoint counts per 0xE4 count** — against the
**0.2683** I took from design290b's `STEP_SP`, a 0.3 % agreement from two completely independent derivations.
Two small conservatisms remain in my mirror, both stated: I did not apply the ±240 idx clamp (so `sp` keeps
growing above 3870 wire counts, where the real one saturates at ~1035 counts — this *over*-counts the P-rail
slightly at the very top of the command), and I did not apply the override taper (`G < 255` on only 1.4–2.9 % of
engaged frames per reqaxis, so negligible).

⚠ **Sign correction, load-bearing.** The pairing `x = −8·rate` with `sp = +slope·e4tq` is the only one of the four
that makes `32·sp` and `fb` positively correlated (+0.377 on r34) and halves median |E| (1209 vs 2544 counts) —
i.e. the only pairing in which the loop tracks. It agrees with `adv_v290_physics`' header
(`x = gp-0x6a56 = −(0x18F wire rate)`). My first run had it backwards and roughly doubled every duty.

**P-clamp bind duty, engaged, at the ×6 (LINEAR.TO6X) slope:**

| route | build | P bind @Kp 248 | P bind @Kp 696 | S-clamp bind (248 / 696) | D bind |
|---|---|---|---|---|---|
| r31 | V278 | 12.0 % | **17.8 %** | 4.9 % / 7.7 % | 2.1 % |
| r32 | V280 | 2.7 % | **5.6 %** | 1.2 % / 2.9 % | 1.7 % |
| r33 | V280 | 8.8 % | **13.2 %** | 3.6 % / 5.9 % | 1.8 % |
| r34 | V280 | 10.7 % | **21.1 %** | 4.5 % / 9.2 % | 1.0 % |
| r39 | V282 (Kp flat 248) | **4.5 %** | (10.8 %) | 1.9 % / 4.9 % | 0.7 % |

r31–r34 carried the Kp CURVE `[248, 512, 645, 696, 696]` indexed by demand, so their true duty lies BETWEEN the
two columns and the Kp-696 column is an upper bound. r39 is Kp flat 248, so 4.5 % is its actual figure. The
result survives the map assumption: even at ×1.5 the Kp-696 duty is 5.7–13.6 %.

**Verdict — CONFIRMED IN DIRECTION, PARTIAL IN MAGNITUDE.**

1. The P clamp is a hard clamp, so its describing function for a small ring superimposed while railed is exactly
   zero. The ring therefore sees roughly `(1 − duty)·Kp`. The duty **roughly doubles from Kp 248 to Kp 696** —
   that is the pinning mechanism design290d proposed, and **it is on the wire**.
2. But a duty of 0.18–0.21 buys ×0.8. Adding the sum-clamp bind (which zeroes the whole forward path, P and D
   together) gets to about ×0.75–0.80. **The Kp step from 248 to 696 is ×2.8.** Saturation alone does not turn
   "unstable on 304/304 fits" into "flew stable at ζ 0.019". **Do not present this as closing the question** —
   something else (plant friction, or the least-damped-pole-over-8–30-Hz criterion itself) carries the rest.
   design290d's §C already concluded independently that the V289 line is *not* a clamp-limited limit cycle; this
   result is consistent with that and does not overturn it.

**How to re-read every ζ in §2 in this light.**

- Every ζ in the table is computed at the full linear Kp, so **all of them are biased PESSIMISTIC** by the
  saturation duty. The bias is common to every row, so **the RANKING is safe**.
- One systematic tilt: rows that RAISE loop gain (fb pole out to 40–50 Hz) saturate slightly MORE, so their true
  ζ is a little better than the table says. Rows that CUT gain (the Kd cuts) saturate LESS, so their table ζ is
  closer to true. **Net, the bias mildly favours rows 1–2 over rows 3–5.** It does not rescue the Kd rows'
  7 Hz gate failure, which is plant-free and untouched by any of this.
- ⇒ **Read ζ_median on the 87-fit SUB column as the headline, not ζ_worst on the 121.** On that read the top row
  is +0.057 against V282's +0.034.

---

## 5. THE SCHEDULED-GAIN ROW — and it dominates rows 1–3

`reqaxis`'s trace **has** landed: `docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md`. It is a byte-and-axis
trace, not a scored candidate — but its byte facts let the row be scored **without a new run**, because a
scheduled Kd is just the flat-Kd row at one operating point and V282 exactly at the other.

**The byte facts:**
- Both tables are indexed by the **demand index** `idx` = the rectified, taper-scaled, ±240-clamped 0xE4 command.
  `1 idx LSB = 16.1257 wire counts` (exact, `2²²/G/4` at G = 65025, which holds on 97–99 % of engaged frames).
- Kd record `0xE511C`, knots X = `0, 11, 22, 32`, Y = `128, 128, 128, 128`. **Above idx 32 the lookup takes its
  high-clamp branch and returns Y[3].** ⇒ setting `Y[0..2] = 96` and leaving `Y[3] = 128` cuts Kd below idx ~22,
  ramps back to 128 over 22–32, and leaves it **exactly 128 everywhere above 32**.
- Kp and Kd slot-7 records share ONE 4 KB CRC page (`0xE5000`), so a combined edit costs one trailer at `0xE5FFC`.
  A Y-only edit cannot create the `divq` divide-by-zero (no Y is ever a divisor).

**Why this matters more than anything else in the table** — the operator's two authority floors and the symptom
live in *different parts of the axis* (all figures from reqaxis §3.2, pooled r62+r63, engaged):

| population | idx p50 | share of its time at idx ≥ 32 (Kd unchanged) |
|---|---|---|
| capped step (the pkR operating point) | 110 / 86 | **89 % / 81 %** |
| low-speed full-lock turn (the 7 Hz gate, and where his bookmarks sit) | 123 / 74 | **88 % / 76 %** |
| 25 m/s cruise | 3 | **0.0 %** |
| census grinding episodes | **8 / 46** | 31 % / 67 % |

⇒ **A Kd cut confined to Y[0..2] leaves the 7 Hz gate and the capped-step pkR ~80–89 % untouched by
construction** — which is precisely the wall every flat Kd row in §2 hits. That is a structural escape from the
gate/grind trade design290d correctly identified, and it costs 4–6 cal bytes and no cave.

### 5.1 The scoring, and why it needs no new run

A scheduled Kd is **piecewise-constant in demand**, so its small-signal metrics are read at each operating point
from rows already in §2:

| metric | operating point | value | grade |
|---|---|---|---|
| ζ, ring length, Ms, S1014/S2230, noise | cruise and low-demand grinding, **idx < 22** ⇒ Kd = 96 | the flat **Kd 96** row: ζm SUB **+0.073**, ring **254 ms / 5.0 cyc**, Ms 4.9, noise **×0.77** | EVIDENCE (same family, same functions) |
| **gate73** | full-lock turn, **idx p50 74–123 ⇒ Kd = Y[3] = 128**, byte-identical to V282 | **1.003 — ×1.000 of V282, exactly** | EVIDENCE, by construction |
| **pkR, dc, t90** | capped step, **idx p50 86–110 ⇒ Kd = 128** | **1.00 / 1.000 / 13 ms — V282's own** | EVIDENCE, by construction |

**That is the whole point.** The flat Kd rows fail only on gate73, and gate73 is evaluated at an operating point
where a scheduled cut does not apply. Row S therefore reaches the **shortest ring in the entire table — 254 ms /
5.0 cycles against V282's 582 / 11.7 and the best cave row's 424 / 7.1 — for 10 bytes, cal-only, with the 7 Hz
gate and the capped step untouched and HF noise into the motor going the RIGHT way (×0.77).**

The whole flat-Kd column becomes available as a dose axis this way, because every one of those rows failed ONLY
on the gate: `Y[0..2] = 112` → **359 ms**, `= 96` → **254 ms**, `= 80` → **191 ms**, all at gate 1.003 and
pkR 1.00. ⚠ But the dose and the parametric hazard in §5.2.3 move together — a bigger cut means a bigger 96/128
(or 80/128) contrast switching at the knot — so **the aggressive end is not free, and I would start at 112 or 96,
not 80.**

### 5.2 The three honest costs

1. **It reaches only about half the grinding.** Pooling r62 and r63 by seconds, **50.5 %** of census
   grinding-episode time sits below idx 32. r62 and r63 disagree badly (31 % vs 67 % above idx 32, on 12 and 15
   episodes) — reqaxis flags that split as unresolved and a design must not lean on either number alone.
   Cruise, by contrast, is **100 %** covered.
2. **The gate/pkR protection is a time-share, not an absolute.** 76–88 % of full-lock-turn time and 81–89 % of
   capped-step time is at idx ≥ 32. The remaining 12–24 % sees Kd 96, where the local gate is 1.073.
3. ⚠ **A gain that switches inside the ring cycle is a PARAMETRIC modulation, not a gain change.** If the 7 Hz
   ring itself swings the demand index across the knot at 32, Kd alternates 96/128 at ring frequency. This kit
   has a standing memory on exactly this hazard
   (`memory/.../accord-parametric-pump-intervention-never-run.md`) and it has never been run deliberately. **This
   is the one thing that could make row S worse than the linear reading, and it is not modelled anywhere.** The
   mitigation is available and cheap: place the cut wholly below the band the ring visits, or widen the
   `22 → 32` ramp by moving `X[2]`/`X[3]` so the transition is gradual rather than a step.
   **A design that proposes row S must address this explicitly, and must ship the instrument that would see it**
   (the demand index is already on the wire; a tap on which Kd cell was selected would be one comparator bit).

---

## 6. WHAT I WOULD PUT TO THE OPERATOR

In descending order of what the evidence supports:

1. **The SCHEDULED Kd cut (row S, §5) is the strongest candidate on the table.** It is the only one that escapes
   the gate/grind trade *structurally* rather than by paying for it: shortest ring (254 ms / 5.0 cyc), 7 Hz gate
   and capped step ×1.000 by construction, HF noise ×0.77, 10 bytes, cal-only, no cave, no int32 overflow
   question, no engage seeding. Its two real limits are that it reaches only ~50 % of grinding-episode time and
   that the parametric hazard in §5.2.3 is unmodelled. **Address the parametric question before building it.**
2. **If a cave is to be cut, it is `notch 21.5 Hz Q1.5 on the FEEDBACK OPERAND + fb pole 40 Hz`** — the fb-40
   sibling, not fb 50. It gives up ζ_med +0.057 → +0.057 (SUB: no change) and ζ_w +0.040 → +0.035 for a
   materially lower HF noise cost (×1.91 vs ×2.21), a better pkR (0.97/0.93 vs 0.95/0.90), and it still passes the
   gate at 1.009. **The ×2.2 HF-noise step of the fb-50 row is a new risk class for this kit and is not worth
   0.005 of ζ.**
3. **Do not re-aim at 16–17 Hz.** §3.
4. **Do not build `Kd 120 + fb 18`.** It is a 2 % change dressed as a feasible cell.
5. **Put design290d's flat-Kd trade to the operator in his own words if the scheduled row fails** — *"the grind
   gets 2–3× shorter and the strong-turn ring at 7 Hz comes back 4–11 % stronger; which do you want?"* — exactly
   as its §F.2 recommends. It is not ours to decide.

**Open, and unresolved:**
- **pkR_worst vs pkR_median — the one open gate.** Rows 1 and 2 pass on the median and fail on the worst fit,
  and the SUB family barely moves it (`_scratch/reconcile_v290_table.json`):

  | row | pkR med / worst, FULL | pkR med / worst, SUB |
  |---|---|---|
  | notch 21.5 Q1.5 + fb 50 [FB] | 0.950 / 0.901 | 0.955 / **0.906** |
  | notch 21.5 Q1.5 + fb 40 [FB] | 0.967 / 0.928 | 0.971 / **0.928** |
  | Kd 120 + fb 18 | 0.968 / 0.963 | 0.969 / **0.963** |
  | **scheduled Kd (row S)** | — | **1.000 / 1.000, by construction** |
  | V289 as flown | 0.793 / 0.745 | 0.805 / 0.745 |

  Which reading the operator's 0.95 floor means has never been written down. **Note that row S sidesteps the
  question entirely** — it is the only candidate that does not have to be argued past this gate.
- The residual of the Kp-696 conflict after the P-rail (§4.2).
- The r62/r63 disagreement on where grinding episodes sit on the demand axis (§5).

---

## 7. Files

- This memo.
- `rlog-tools/studies/grind/reconcile_v290.py` → `_scratch/reconcile_v290_table.txt`, `_scratch/reconcile_v290_task1.txt`.
- `rlog-tools/studies/grind/reconcile_prail_r31_r34.py` → `_scratch/reconcile_prail.txt`.
- Read, not re-derived: `docs/specs/design/DESIGN-V290B-2026-09-09.md`, `docs/review/ADV-V290-NULL-2026-09-09.md`,
  `docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md`,
  `docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md`.
