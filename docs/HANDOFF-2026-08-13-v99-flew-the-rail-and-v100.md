# HANDOFF 2026-08-13 (later still) — V99 FLEW, THE PID-REFERENCE RAIL CONDITIONS EVERYTHING, AND V100

Record-repair / orchestrator synthesis pass. **V100 is now built — §12 below has the full record,
independently re-verified from the images.** Mark **EVIDENCE** vs **BELIEF** throughout; the method
is given for every EVIDENCE claim.

---

## 1. V99 FLEW — ROUTE `0x82`, FAULT-FREE, IDENTITY CLEAN, AND NOTHING IS CALLED FIXED

**Build**: `0xC40BC` 600→**300** (Coulomb-relay knee, halved — the SAME cell V85 moved the other way,
600→6000) + `0xC63AC` 150→**102** (a straight revert of V97's pole, back to STOCK's own value) + one
cave identity byte. 12 bytes vs V98 in 5 runs (3 CAL + 1 CAVE + 8 CRC), independently re-verified from
the images this session — matches the build's own reported diff exactly.

🛑 **`0xC40BC`'s rationale was already retracted by the SAME session that cut it, before it flew**:
the dose delivers only 0.5–1.2% against Path-2's own ~9% perceptual floor, and 93.1% of the operator's
hands-on engaged frames sit above the 10.61 °/s knee where 300 and 600 are arithmetically identical.
**It flew anyway, the operator's explicit decision** (same class as V91's *"we are flying regardless,
so the instrument is free"*).

**Flight** [EVIDENCE, `scorer-v99`, `docs/TRACE-2026-08-13-v99-flight-score.md`]: route `0x82`,
2026-08-13, 2 segments, 121.7 s. Fault-free — 0 sentinels on `0x14A`/`0x18F`, `CONFIG_VALID` 1.00000,
`OUTPUT_DISABLED` **0.00000**, DTC bit2 0.00000 / 0 transitions, `STEER_STATUS` **{0: 12004}**.
**Identity PASS with ZERO margin consumed**: `b5` duty **1.000000** (0 of 12,005 frames; V98 measured
0.0022 on the byte-identical rung) AND `byte7[7:6]` = {2: 12,005}. ⚠ `byte4[7:3]` reads all EVEN
{6,12,14,20,28,30} — **expected, not a fault**; the ~50-build "always ODD" convention would have
wrongly pulled a working build. Engaged **59.8 s in 4 episodes** (15.9/31.3/2.5/10.1 s), p50
**6.66 km/h**, plus **60.2 s of interleaved LKAS-off arm**. 427: 245 codes, p99 232, 0.000%
saturation. `b3` duty 0.0000, reproducing on a fifth route.

⭐ **Operator, verbatim, do not paraphrase**: *"I think it helped with the audible aspect of the
grinding, though I'm not sure."*
🛑🛑 **NOTHING IS CALLED FIXED. HE HAS NOT CALLED ANYTHING FIXED.** Report it as an uncertain,
qualified impression about ONE aspect (the audible component) of ONE symptom (grinding) — not as a
result for grinding generally, and not for micro-ratcheting or ratcheting.

---

## 2. E1 READS NULL — `0xC40BC` IS CLOSED AT ANY DOSE, NOT JUST 300

All four wheel-rate bins moved, **all four DOWN** (lever bins 0.7335 / 0.8749; control bins 0.9374 /
0.9119) — a route-wide offset, not a rate-selective effect. `build_v99_tva.py` pre-registered the
closing sentence verbatim before the cut:

> *"A change in ALL FOUR bins is an operating-point / route artefact, NOT the lever."*

⇒ **the pre-registered null is licensed, verbatim**:
> *"Doubling the modelled-Coulomb small-signal gain in the 1–13 deg/s micro regime does not move the
> MODEL-vs-ACTUAL arm balance at any wheel rate, so the friction ramp's KNEE POSITION is not what sets
> that balance while he feels the symptom — and since the reachable friction set is unchanged, no
> larger dose of THIS cell can do it either. The next lever must be outside `FUN_0003b8f6`'s friction
> path."*

Because the reachable friction set is **bit-identical** between V98 and V99, **this closes `0xC40BC`
at every dose the kit has ever flown or could fly** — V85's 6000 included, not only V99's 300.

⚠ **Closure rests on the pre-registered rule, not a demonstration the lever did nothing.** The 0–5°/s
bin (0.7335) — the predicted full-dose bin — sits apart from the other three, but the offset-immune
DiD confidence intervals overlap. Say exactly that; do not claim the lever was inert, only that its
own falsifier fired.
🛑 **E2 was UNDERPOWERED and could not arbitrate** — its null width (0.343) exceeds the entire 0.10 gap
between the hypotheses it was built to separate. Its formal NULL is a **power artefact**, not a
finding, and is not evidence for anything.

---

## 3. `0xC63AE` IS NO-GO — DO NOT PROPOSE IT FOR V100

`tracer-c63ae` [EVIDENCE, crux verified by the team lead in Ghidra]: **RULE 7 PASSES** on this cell —
an unconditional bare-`tp` scalar read at `0x38242`, no mode index, so the V69/V70 wrong-record
failure class cannot recur here. That clears the concern the record previously carried against it.

🛑🛑 **But the AC gain through this cell is NON-MONOTONE in scale and REVERSES SIGN across the
operator's own amplitude distribution.** At scale 1536: ratio **0.773 at p10, 1.078 at p50, 1.277 at
p90** — the gain RISES with amplitude, the hardening nonlinearity that sets up a limit cycle (V80
class). **1280 is arithmetically WORSE than stock.** A "median-only" dose analysis (the kind that
priced 2048 as "+28% on the lane, above the perceptual floor") misses this entirely — the median is
not where the hazard lives.

⇒ This is a landmine catch this session: `docs/TRACE-2026-08-13-path2-authority.md` §6–7 was still
actively recommending `0xC63AE` 1024→2048 as the LEAD V100 candidate when this was found. Both its
candidate writeup and its final verdict table have been corrected in place. **Do not read that trace
top-to-bottom and propose the cell — the corrections are in it, but read them.**

⭐ **New structural fact, unaffected by the NO-GO**: `Y[9]` of this cell's LERP and the PID's ±8192
output clamp (`0xC6200`) are literally the **same cell** — see §4. The clamp is never the binding
constraint on this lane.

---

## 4. ⭐⭐ THE HEADLINE: `0xC6200` CLAMPS THE PID'S REFERENCE, AND IT CONDITIONS `0.2565`

`tracer-6ad6` [EVIDENCE, crux independently verified by the team lead — `read_memory(0xC6200)` =
`00 20` LE = 8192, `disassemble_bytes(0x3a790..0x3a7f0, dry_run)` reproduces the listing
instruction-for-instruction]:

```
0003a798: ld.h  -0x6ad6[gp],r7     ; the PID REFERENCE, written by FUN_00037fe6, ±25600 clamp
0003a7a2: ld.h  0x7200[tp],r6     ; cal 0xC6200 = 8192                <-- THE CLAMP CONSTANT
0003a7b8:   mov r11,r7            ;   r7 = +8192                       <-- HIGH RAIL
0003a7c8:   subr r0,r7            ;   r7 = −8192                       <-- LOW RAIL
0003a7ca: ld.h  -0x4f60[gp],r8    ; the MEASURED DRIVER TORQUE
0003a7ce: sub   r7,r8             ; err = torque − clamp(ref, ±8192)   <-- THE PID ERROR
0003a7e8: mul   lp,r8,r0          ; × Kp — and I, D derive from the SAME clamped err
```

> **`|gp-0x6ad6| ≥ 8192` ⇒ `∂(gp-0x6ad4)/∂(gp-0x6b70) = 0` — through P, I AND D SIMULTANEOUSLY.**

`gp-0x6b70` (all of Path 2) enters at unit weight through a speed LERP that is the IDENTITY (verified:
Y `0xC6ACA..0xC6AD8` all 1024) — **there is no dilution anywhere for the clamp to hide behind.**

### The condition on `0.2565`
`path2-authority`'s result — `d(gp-0x6b94)/d(gp-0x6b70) = 0.2529/0.2565/0.2617` at 6/7.79/9 Hz, "no
dilution anywhere, every link unity" — **is the UNSATURATED small-signal derivative, valid ONLY while
`|gp-0x6ad6| < 8192`. On any frame where the clamp is active, the true derivative is EXACTLY ZERO, not
0.2565.** Every link IS unity — a hard clamp is simply not a link. **The number is not deleted, it is
conditioned**, everywhere it appears in the record (`STATE.md`, this session's own earlier V98
handoff, the source `path2-authority` trace, and `analysis-2020accord/_v97/fw_loop.md`'s phase-budget
table — all corrected this pass).

### Why this matters for the WHOLE V89→V99 arc, not just V100
🛑🛑 **Ten builds' worth of levers may have been discarded by a saturation nobody had found.** Every
build from V89 on has moved a term feeding this exact residual chain (`0xC40D2`, `0xC40BC`, `0xC63AC`,
`0xC63AE`) and scored its result assuming the unsaturated gain applied. If the clamp was binding on a
meaningful fraction of frames, those levers' outputs were being thrown away downstream of where every
scoring script measured them.

**What is measured, and what is not** [EVIDENCE, `scorer-v99`, over 14,289 engaged frames, 3 routes]:
```
route   n_eng     p50      p90      p99      MAX   MAX/8192   frac>=8192
r82      5979   537.6   2380.8   2956.8   3008.0     0.367      0.0000%
r81      6591   883.2   2611.2   2892.8   3161.6     0.386      0.0000%
r80      1719   601.6   2073.6   2624.0   2675.2     0.327      0.0000%
```
**`|gp-0x6b70|` never exceeds 3,162 counts = 38.6% of the clamp threshold**, with 427 saturation at
0.000% (a real distribution tail, not a measurement ceiling). ⇒ **`gp-0x6b70` cannot rail
`gp-0x6ad6` on its own** — the other six terms in the sum (`gp-0x6b4a` ±25600, `gp-0x6b60` ±15360,
five more at ±10240, combined bound ~100,352 = 12× the threshold) must supply at least **5,030 counts
(61.4%)** of any rail that occurs, and **none of them has ever been on the wire.** ⇒ **`d_clamp` — the
duty the clamp actually binds — is UNBOUNDED in [0, 1] from data the kit already has.**

**⇒ If `d_clamp` comes back HIGH: the saturation is driven by terms the entire V89→V99 arc never
touched, and "every lever was discarded by a saturation" gains a mechanism — V89's flat dose-response
and V97's felt-null are explained by ONE mechanism requiring nothing unmeasured.** If it comes back
LOW: the saturation hypothesis dies, and the `f′`-compression account (§7 below) is the sole survivor.
Either outcome is decisive — that is why measuring it is V100's content.

### Term 0 rails the reference at 32% of its own clamp, not 100%
`gp-0x6b4a` (term 0, ±25600 write clamp, shadow-lockstep protected at `gp-0x4cd2`) does not need to
reach its own rail to zero the PID's sensitivity — it needs only `|gp-0x6b4a| > 8192`, **32% of its
own clamp, a 3.125× lower bar than "rail it" implies.** Every other term's own window against the
same 8192 threshold: `gp-0x6b60` needs 53%, the ±10240 group needs 80%, and `gp-0x6b70` — term 7,
ALL of Path 2 — is clamped at exactly ±8192 by the SAME cal cell, **1.000× — already at the
threshold, no headroom needed at all.**

### `0xC6200` is FOUR things — and the root-cause lesson
| sites | function | role |
|---|---|---|
| 6 | `FUN_000352b4` | friction-magnitude lane |
| 4 | `FUN_00038148` | clamps `gp-0x6b70` — Path 2's OUTPUT |
| 1 | `FUN_000389ec` | Stage-2 LERP `Y[9]` (the `0xC63AE` lane, §3) |
| 3 | `FUN_0003a382` | clamps `gp-0x6ad6` — the PID's REFERENCE (new this session) |
| 1 | `FUN_00039702` | 🛑 UNCHASED |

**BLOCKING FLAG**: `0xC6200` must not be edited by any future build until `0x39ff6` is chased —
V100 is unaffected (it only reads the cell). 🛑 **Generalisable lesson**: every build script since
V90 labels this cell *"gp-0x6b70's clamp"* — one of its four roles — and that mislabel is what kept
the PID-reference role invisible for ten builds. **A cal cell with multiple roles, labelled by only
one, is a latent wrong answer.** Check every reader before naming a multi-role cell, not just the one
the current task cares about.

### The `0xC6200` ↔ V65 collision, and why there is none
V65's `accord-aggregator-never-rails-loop-is-linear` measured `gp-0x6b94` (the AGGREGATOR OUTPUT,
downstream of the PID) never reaching ±8192 in 120,049 frames. Read carelessly, that null appears to
have already answered whether the OTHER ±8192 clamp — on `gp-0x6ad6`, upstream — binds. **It has
not.** A fully railed reference contributes only `8192 × 0.2565 ≈ 2,101` counts at `gp-0x6b94`,
comfortably inside V65's own NEUTRAL band (`|·| < 4096`). [BELIEF, safe direction only — linearised
via the unsaturated 0.2565]. **The two nulls are compatible, not redundant**; V65 does not bound
`d_clamp`. Reconciliation is now written into both memory files and the constellation.

---

## 5. φ IS MEASURABLE — THE AGGREGATOR NEEDS NO MODEL

`tracer-c63ae` [EVIDENCE, decompile + opcode census]: `FUN_0003aa2c`, the aggregator, is an
**unweighted 11-term sum** — `mov` + TEN `add` + one `jarl`-add, **ZERO multiplies**. Path 2
(`gp-0x6ad4`, the PID output) is exactly one term at coefficient +1.

⇒ **φ (Path-2's share of the delivered command at 6–9 Hz) is `Path2/total` at ONE summing junction —
two numbers at the same node, same units, no modelling required.** The free anchor:
`RMS₆₋₉(gp-0x6b70) / RMS₆₋₉(column torque, 0x18F)`.

🛑 **CORRECTED after this section was first drafted — the anchor's number and its stated precision
were both wrong, and the error was rectification, the same defect closed in §8a.** First computed on
the RECTIFIED 427 channel: **1.190 (route 81) / 1.178 (route 82), "stable to 1.0%."** Recomputed
signed: **r82 1.1725 [1.0709, 1.2709] rel s.e. 4.37% · r81 1.0825 [0.9089, 1.2106] rel s.e. 7.73%** —
**1.173 vs 1.083 is 8% apart, not 1%. Rectification inflated the anchor's apparent stability ~8×.**
**Use `1.13 ± 0.09` and describe it as a LOOSE cross-check, not a tight one.** Recorded here rather
than silently corrected because *"an anchor that looked 8× more stable than it is"* is exactly the
kind of number that gets trusted later without anyone re-deriving it.

🛑🛑 **AND THE `R ≈ 387 ct` CROSSOVER FRAMING FAILED ITS OWN POWER GATE — struck, not merely corrected.**
It tested whether an ABSOLUTE 6–9 Hz RMS on `gp-0x6b70` sat above or below 387 ct, assuming
stationarity via `1/√(2n)`. Route 82 is 4 fragmented episodes at 5.1/6.9/18.9/16.7 km/h — not
stationary. Block-bootstrapped, the true rel s.e. on that absolute RMS is **24–29%, not 3.7%**;
episode variance dominates spectral variance **6–8×**. At 24% s.e., excluding 387 ct needs `R ≤ 231`
or `R ≥ 1,180`; **measured 231.2 (r82) / 225.1 (r81) — exactly on that edge, clearing by 0.1% on one
route and FAILING by 6% on the other. A coin flip, not a crossover.** ✅ **φ itself, being a RATIO,
does not have this problem** — the ratio form measures at the 4.4–7.7% rel s.e. above, **3.8–5.5×
more precise on identical data, for free** (numerator and denominator variance partly cancel across
the same fragmented episodes). ⇒ **Strike the absolute-387-ct framing entirely; any future endpoint
in this family should be a dimensionless ratio against a ratio boundary, never an absolute RMS
against a count.** Stated plainly: this framing was pre-registered, gate-tested, and **rejected
before the cut** — that is the power gate doing its job, and the record should show a framing being
discarded, not hide that one was tried.

⭐ **Standing design law, worth carrying into every future exposure calculation on this car**: *any
precision estimate using `1/√(2n)` is optimistic by 6–8× here, because the drives are fragmented into
short episodes at varying speed, and episode-to-episode variance dominates the within-episode
spectral variance.* Block-bootstrap, don't assume stationarity.

### ⭐ NEW SINCE THE FIRST DRAFT — the `b6` conditioning trap
`n_eff = T·(1−d(b5))/τ`: the conditional `d(b6 | b5=0)` **dies as `d(b5)` → 1** — its usable sample
count collapses above `d(b5) ≈ 0.909` (best-case τ) / `0.578` (central) / `0.153` (worst-case τ).
🛑 **The scenario that makes the headline most interesting — `b5` near 1 — is EXACTLY the one that
empties `b6`'s own conditioning set.** Free mitigation: **pre-register the joint 2×2 `(b6,b5)`**; the
MARGINAL `d(b6)` stays reportable at full `n` regardless of where `d(b5)` lands, and the conditional
is a bonus when the set isn't empty. ⚠ Keep both facts side by side — the marginal is the reportable
statistic, and it is a DIFFERENT quantity from any conditional duty computed against it. The same
discipline applies as in §4's `d_clamp`: an unconditioned statistic is not automatically the
conditional quantity a downstream claim actually needs — state which one is being reported, every
time.

⊕ `gp-0x374c` (what `0xC63AC` acts on) **never leaves `FUN_00038148`** — confirms it cannot reach any
of the aggregator's ten other summands; `build_v97_tva.py`'s "Path 1 is unweighted, unaffected by A"
claim SURVIVES.

---

## 6. THE POWER GATE — WHAT V100'S ENDPOINTS MUST LOOK LIKE

`scorer-v99` [EVIDENCE, `docs/TRACE-2026-08-13-v99-flight-score.md`]:

- **RUNG A** (`d_clamp` as a **within-route absolute**) **PASSES**: 3.0–9.3 σ of margin on a
  0.20/0.80 duty call, resolvable window **[0.030, 0.970]**. It asks a structural question — *"is the
  reference pinned?"* — with no reference to any previous build, decision boundary ~0.5 wide.
- **The SAME rung, read as a cross-build delta vs V99, FAILS** — it inherits E1's exact failure mode
  (§2): a route-wide offset can move all bins together and manufacture a false cross-build "effect."
  🛑 **THE GATE FOR V100: if any endpoint's sentence contains "compared to V99," IT FAILS.** Write
  every endpoint as a single-drive absolute.
- **E2-class endpoints (partial correlations discriminating two values ~0.1 apart) are
  UNBUILDABLE at any exposure this kit can obtain**: needs 25–58 minutes of CONTIGUOUS engaged time
  (empirical block scaling: 288 blocks conservative / 209 optimistic; textbook SE formula: 675
  independent units = 58 min) against a best-ever recorded engaged exposure of **65.9 s** — **16–50×
  short**. **Struck. Do not propose this endpoint class again.**
- The positive control (`|gp-0x6ad6| ≥ |gp-0x6b70|`) PASSES on the same arithmetic and its expected
  value is pre-computable from 427 — a wildly off measured value indicts the instrument, not the car.

⚠ **Design law, worth carrying forward**: different comparator bits have very different
autocorrelation timescales — measured τ ranges from **0.029 s (a fast SIGN bit) to 0.603 s (a slower
threshold/hysteresis bit), roughly a 2–20× spread** — and effective sample count (hence resolvable
duty range) depends on which one a rung uses. **Size the resolution floor per rung from its own
measured τ, not from one assumed value.**

---

## 7. ⭐ THE `f′` COMPRESSION ACCOUNT — STILL THE OTHER LIVE HYPOTHESIS

Carried from the prior handoff, unretired by anything this session: `f′`, the Stage-2 LERP's local
slope, is a deterministic function of `|iVar6|` and reads **6.3× lower** in the operator's own
hands-on regime (0.346) than in the hands-off/steep region (2.174) where V89 and V97 both argued
their direction. **ONE mechanism, consistent with V98's comparable-arms result** [BELIEF, fits all
data — the discriminating test is RUNG A above: if `d_clamp` comes back low, this account is the sole
survivor].

---

## 8. THE 427 RECTIFICATION REGRESSION, AND THE EXPOSURE LAW — TWO STANDING DESIGN LAWS

### 8a. Rectifying a signed lane costs 4.9–5.5×, and this kit already knew that
`tracer-c63ae` [EVIDENCE]: CAN 427 carries `|gp-0x6b70|`; the sign is a separate cave bit. Using the
rectified magnitude instead of the sign-reconstructed signal understates 6–9 Hz RMS by **4.86×**
(548.28 signed vs 112.73 rectified) because the sign toggles **5.06×/s** — far too fast for `|x| ≈
±x`. 🛑 **This is a REGRESSION, not a class error**: six earlier scripts (V87, V90, V92, V95, V96,
V97) all correctly used the signed lane; the defect was introduced at **V98**
(`v98_r81_score.py:541`) and inherited by **V99** (`v99_r82_score.py:672,718`) — a one-line omission
in scripts that compute the sign correctly and apply it everywhere else. **Fixed this session** (both
lines patched to apply `sign_6b70`). Measured impact: the 427-derived contrast read **0.865 rectified
(a false 13.5% "improvement") vs 0.976 signed (the correct NULL)**. ⭐ **This is the design law's
"pair a sign bit with a magnitude channel" principle, MEASURED on a real lane — quote it whenever a
rectified-magnitude channel is proposed.**

### 8b. The exposure law — contiguous seconds, not total seconds
[EVIDENCE, `scorer-v99`] Resampling block count is set by the LONGEST CONTINUOUS engaged run, not
total engaged time summed across episodes. Route 82's 59.8 s split across four episodes
(15.9/31.3/2.5/10.1 s) gave only 12–14 blocks; route 81's 65.9 s in three episodes gave **21** — LESS
total exposure produced MORE usable blocks because it was less fragmented.
🛑🛑 **THREE BUILDS IN A ROW — V89, V97, V99 — have had their primary endpoint die to this, and it is
a DRIVE-PROTOCOL fix, not a build fix.** One continuous ~60 s engaged episode roughly doubles the
usable block count at identical total exposure. New standing memory:
`memory/feedback-exposure-law-contiguous-blocks-not-total-seconds.md`.

---

## 9. RECORD DEFECTS FIXED THIS SESSION

- **Eight-plus stale flight-status claims reconciled** across `STATE.md`/`BUILD-LINEAGE.md` as V99
  superseded V98 (V99 previously had no row at all in `BUILD-LINEAGE.md`), including a genuine gap
  distinct from the routine staleness: **V91/V92's rows had never been reconciled at all**, unlike
  their sibling rows in the same table. V92 corrected to FLEW (route `79`, confirmed from
  `STATE.md`/memory); **V91 marked AMBIGUOUS, not flown-or-not** — it is telemetry-identical to V90
  and the operator, asked directly, could not confirm which build route `78` was. Ambiguous beats a
  confident wrong answer either direction.
- **`memory/accord-base-assist-damper-cannot-reach-the-micro-regime.md` REFUTED, corrected in
  place**: six builds (V74/75/76/78/79/80) had BOTH FactorC and FactorE dead zones open
  simultaneously, verified from the images; three flew (V75 route `5e`, V76 route `65`, V80 route
  `66`). Only the route-73/V88 Honda-stock zero result still stands.
- **`BUILD-LINEAGE.md`'s V86 row corrected**: the `gp-0x67ab < 2` rung "lever in force three ways"
  claim was wrong on its third leg — `< 2` is true of both the gate-open and gate-closed states, so
  it could never discriminate. The gate's open-ness is known structurally (`gp-0x67ab ≡ 0`, sticky-OR
  over roles {2,3,4}, `0xC4124` contains none of them, byte-identical across 65 images), not from V86.
- 🛑 **Landmine catch**: `docs/TRACE-2026-08-13-path2-authority.md` §6–7 was still actively
  recommending the now-NO-GO `0xC63AE` 1024→2048 as the lead V100 candidate when the AC-gain
  reversal was found (§3 above). Both its candidate writeup and verdict table corrected in place —
  anyone reading that trace top-to-bottom before this fix would have proposed a lever already killed.
- **The V65/`0xC6200` collision defused** (§4 above) — in the V65 memory file itself, not just the
  new one, plus a constellation edge and the generalisable "multi-role cell, single-role label"
  lesson recorded in `BUILD-LINEAGE.md` where a future session naming that cell will see it.
- **V98's engaged/manual `b6` headline corrected**: the raw contrast (0.4235 engaged vs 0.8041
  manual, `docs/SCORING-2026-08-13-v98-route81.md:169`) asserted it *"survives speed matching...not a
  speed artefact"* — **true but insufficient, because the confound is on WHEEL RATE, which
  speed-matching cannot catch.** A robustness check that passes against the wrong variable launders
  the number rather than validating it. Matched on a 4|rate|×6 speed grid: **engaged 0.4543 vs manual
  0.7493, diff −0.2950 [−0.4099, −0.1727]** (route 81); diff −0.3372 [−0.5354, −0.1895] (route 82).
  The finding survives (both CIs exclude zero widely); the magnitude was overstated by ~22%.
- **`docs/STATE.md` shrunk 177 KB → 126 KB**: four self-labelled-superseded flight headlines (V96,
  V94, routes 78/79, V88) moved verbatim to `docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md` (55 KB),
  each confirmed to have its durable findings already homed in `memory/` or `BUILD-LINEAGE.md` before
  the move. Nothing deleted; every archive is a record, not an instruction.
- **Two durable facts promoted from private tracer agent-memory** (no home in the shared record
  before this session): the exposure law (§8b) and a new instrument, the cabin microphone
  (`rawAudioData`, live but currently failing its 6–9 Hz coupling control — do not use it to score
  audible reports yet; `memory/reference-accord-cabin-microphone-instrument-and-jitter-trap.md`),
  plus the aggregator/rectification facts (§5, §8a) as
  `memory/reference-accord-aggregator-unweighted-and-427-rectification-trap.md`.
- **Two dangling internal links found and dropped** rather than shipped pointing at nothing
  (`feedback-run-the-control-before-the-measurement`, `reference-accord-c520c-cap-table-axis-provenance`)
  — both exist only in the separate auto-memory store, not repo `memory/`, confirming those two
  memory systems have diverged. Recorded as its own fact below.

---

## 10. NEW: THE TWO MEMORY SYSTEMS HAVE DIVERGED

There are two distinct memory systems in play this session: **repo `memory/`** (168 KB, the kit's
shared record, what every subagent reads) and the **auto-memory index**
(`.claude/projects/…/memory/`, ~26.5 KB, orchestrator-scoped, not visible to subagents). They have
diverged — cross-links written assuming one contain facts that only live in the other. **Named
casualty**: `feedback-run-the-control-before-the-measurement` (*"run the control before the
measurement; four claims died to controls in one session"*) exists in auto-memory only, not repo
`memory/`. A size warning about one store is not a fact about the other. Reconcile deliberately in a
future session rather than rediscovering the gap a fourth time.

---

## 11. WHAT V100 SHOULD BE, IN ORDER

1. **RUNG A** — `|gp-0x6ad6| ≥ 8192` (the PID-reference clamp), read as a **within-route absolute**,
   never as a cross-build delta. This is the decisive measurement — see §4 and §6.
2. **The positive control** — `|gp-0x6ad6| ≥ |gp-0x6b70|`, pre-computable expected value from 427.
3. Do **not** propose `0xC63AE` (§3, NO-GO). Do **not** propose `0xC40BC` at any dose (§2, closed). Do
   **not** propose an E2-class partial-correlation endpoint (§6, unbuildable).
4. **Drive protocol**: one continuous ~60 s engaged episode, not fragmented total exposure (§8b).
5. If flight-scoring 427-derived bands from any script touching this lane, confirm the sign fix from
   §8a is applied — do not trust an `mt427` row without checking.

Standing open items carried forward unresolved: `iVar6` cave-reachability, the total arm-to-arm phase
budget, and `0x39ff6` (the fifth, unchased reader of `0xC6200` — blocks only a future EDIT of that
cell, not V100).

⇒ **§11 was written before V100 was cut. It IS built. See §12 for the realized build, independently
re-verified from the images this session — every point above (RUNG A, the positive control) is what
it measures.**

---

## 12. V100 IS BUILT AND NOT FLASHED. V99 REMAINS ON THE CAR.

🛑🛑 **Stating both explicitly — this kit has shipped TEN instances of a stale flight-status row.**

```
image  c1d36b68390421bfce6c826799108839a8acb90decfb18c72a584189e54197db
rwd    6a763aa78b6cefcb0dc6ab158401d048a9dd7527be524d5a86c59b07a6eb4f21   (986,042 B)
39990-TVA,A160-V100-V99BASE-CAVE.SAT.6AD6.C6200.4F60-SIGN.6B94-ID.B3CONST1-427.6B94-0x13000-0x100000.rwd
builder analysis-2020accord/build_v100_tva.py   139/139   BASE = V99 (on the car)
pushed: accord-firmwares 30f7845 · kit 95b3a17
```
**Both hashes independently re-derived this session** from `_v100_V99BASE-CAVE.SAT.6AD6.C6200.4F60-
SIGN.6B94-ID.B3CONST1-427.6B94_plain_image.bin` and the shipped `.rwd` — match exactly. **Exactly ONE
V100 `.rwd` confirmed on disk.**

**128 bytes differ from V99, in 12 runs — independently re-verified byte-for-byte against V99's own
plain image, matches the builder's reported diff exactly**: `0x55DF2` (1 B, the 427 repoint) ·
`0xC4B36..0xC4BCD` (123 B, cave) · `0xC4FFC` (4 B, CRC). **ZERO calibration bytes ⇒ only ONE CRC
block moves — `0xC6FFC` does NOT.**

⭐ **The 427 repoint is a ONE-byte diff, not two** — `-0x6B70 = 0x9490` and `-0x6B94 = 0x946C` share
the high byte `0x94`, so only the low byte of the displacement moves.

**Cave: 132 B / 49 instructions / 10.9% of extent** (V99: 154 B / 59 instructions) — **smaller and
tighter than every cave since V96.** Store set `{gp-0x1514, gp-0x1511}` unchanged from every prior
cave; registers written `{r6, r7}` only — *tighter* than V96/V98/V99; branch set `{bge}` only, a
strict SUBSET of the flown `{bge, bnh}`.

**Class: a ZERO-CALIBRATION INSTRUMENT BUILD. It measures `\|gp-0x6ad6\| ≥ cal(0xC6200)` — RUNG A —
and the sign of `gp-0x6b94` via the 427 repoint. It is NOT a fix and must not be recorded as one.**

---

## 13. TWO NEW FIRMWARE FACTS FROM THE BUILDER

**`tp` liveness CLOSED** [EVIDENCE, `builder-v100`]: the boot initialiser at `0x140C0-0x140D6` sets
**both `gp` and `tp` by the SAME idiom, four instructions apart, from the same `r1`**
(`gp = 0xFEDF8000`, `tp = 0x000BF000`) — `tp` is exactly as constant and live as `gp`, which every
tp-relative cal read in this kit already assumed. 🛑 **Ghidra never analysed that region —
`search_instructions` returned a TOOL ZERO, and a raw Python byte scan found it immediately.** A
tool-reported zero for an unanalysed region is a silence, not a negative — every other raw candidate
near it had to be individually adjudicated out (the hw2 half of a `jarl` disp22, or an `andi` imm16,
Format-V aliasing) before this one could be trusted. Recorded as an 8th instance in
`memory/accord-v850-scan-traps-formatv-and-storezero.md`.

**`gp-0x6b94` ↔ `gp-0x4ce0` is a shadow-lockstep pair** — on record since the original 2026-07-19
sweep, now with instruction-level detail: sites `0x3acfa/0x3acfe`, `0x3ad12/0x3ad16`,
`0x3ad20/0x3ad26`; mismatch → `jarl 0x6b9fa`, the `FUN_00045a20` hard-shutdown monitor. **Reading is
free — V100's cave only reads it — but WRITING either half of the pair trips the monitor.** This is a
binding constraint on any FUTURE build that writes the aggregator output, not on V100 itself. Recorded
in `memory/reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs.md`.

⊕ Also confirmed by the builder: `FUN_00049a5a` decompiles as `abs()` — 427 really is
`clamp(\|X\|·5>>6, 0, 0x3FF)`, no sign ambiguity in the packer itself. `gp-0x6b94`'s own writer clamp
is **±0x2800 at `0x3acf6`/`0x3ad0e`** ⇒ max 427 code **800 of 1023 — saturation is structurally
impossible** on this lane, the same "no-clip by construction" property V90's 427 repoint had.

---

## 14. ⭐⭐ THE OPERATOR'S DELTA TABLE — EVERY NON-STOCK CELL ON THE CAR RIGHT NOW (V99)

**Self-contained. Read from the V99 image, not the build scripts.** V99 is what is currently flashed;
this is what is physically different about this car's ECU compared to a factory unit, cell by cell,
in plain language. Paste-ready for the close-out message.

**313 differing bytes vs STOCK, in 113 runs, ZERO unattributed** (every one traces to a build present
in the on-disk chain). Image `a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726`.
153 bytes are the telemetry cave (read-only instrumentation, changes no control signal) and 20 are
block CRCs (a mechanical consequence of the edits below, not levers themselves) — omitted from the
table; the 140 bytes below are every cell that actually changes how the car drives.

| what it physically is | stock | now | what the change does to the car | introduced | status |
|---|---|---|---|---|---|
| **LKAS command scale** (`0xC6CD0`, +decouple `0x2A1F0`) | unset (−1) | **3564 = 4.000×** | The LKAS steering command reaching the loop is **4× stronger** than Honda's own feedback path (which is NOT boosted) — this is EXCITATION, not the loop's own gain. | V57 (introduced); current cells stable since V81 | ✅ **MEASURED, multiple flights.** Never lower it — it is not the cause of any symptom, only the volume it's heard at. |
| **"Lever B" — the r24 rate-feedback arm** (`0x3AA96` gate + `0xC6446` arm) | dead gate / 512 | **live gate / 5244 (2×)** | Doubles a rate-feedback term inside the loop while LKAS is actively steering. | V67 (gate), V88 (arm restored + fixed) | ✅ **MEASURED FIX.** Operator: audible grinding fixed on V88; 15–22 Hz delivered-command content cut in half with no loss of steering authority. Still on the car. |
| **Macro-ratchet fix** (`0x454FE`, branch opcode) | conditional branch | **unconditional** | Removes a governor state (state 4) that otherwise forbids the LKAS command from increasing while active — this was the FIX for a specific hard-ratcheting fault mode. | V42 (original fix); ⚠ **lost silently off the car from V53 to V79** (11 total moves on this one byte), **restored at V80 and unchanged since** | ✅ **MEASURED FIX**, on the car now — but its history is not a clean single introduction; it was off the car for a real stretch of this kit's history without anyone deciding that. |
| **K1 — modelled Coulomb friction gain** (`0xC40D2`) | 102 | **204 (2×)** | The plant-model's estimate of how much friction the steering rack has is doubled. More modelled friction → the observer commands MORE assist (verified end-to-end) → a LIGHTER wheel, not heavier. | V89 | ✅ direction measured (lighter wheel); ⚠ whether this is doing anything useful is unresolved — see §2, this is the "MODEL arm" of a chain a saturation may be zeroing entirely. |
| **`0xC40BC` — Coulomb relay knee** | 600 | **300** | Halves the wheel-rate threshold at which the plant model's friction estimate switches into its "high-confidence" relay mode. | V99 | 🛑 **CLOSED THIS SESSION — E1 shows it does nothing at any dose** (300 or the earlier 6000 both tested); operator: *"I think it helped with the audible aspect of the grinding, though I'm not sure"* — not a fix he has called fixed. |
| **`0xCBE74` friction/damper dose, modes 26/27** (6 Y-values) | Honda's own values | **×1.5 the dose** | The same friction/damper model used above, at a higher gain, only while LKAS is engaged. | V74/75 (first flown, both hard-faulted at an old clamp value); safe since V91/92 under the fix below | ⚠ **Carried since V96's revert-by-construction of a later cut** — this is the kit's most-fought single lever, currently at its ×1.5 setting with no clean measured verdict either way. |
| **Hard-fault interlock clamp** (`0xC407E`) | 511 | **511 (stock)** | The safety clamp that the ×1.5 friction dose above would otherwise trip. | — | Stock value — but its EXISTENCE mattered: an earlier build (V75) ran this dose at 850 and hard-faulted; it's back at Honda's own 511, which is what makes the ×1.5 dose above safe to carry. |
| **Low-speed steer lockout window** (`0xC62EA`) | 320 (≈5 km/h) | **0** | Removes a low-speed cutout — LKAS can steer to zero speed instead of disengaging under ~5 km/h. | first touched V53, current value (0) stable since V81 | Deliberate, unverified as a symptom fix — a usability change, not a grinding/ratchet lever. |
| **DTC-0x49 fail-counter gate** (`0xC64B8`) | 0x70 | **0xFF** | Fixes a specific false-fault (DTC 0x49) that used to trip under normal driving. | V37 | ✅ **Resolved on-car** (operator-confirmed, 2026-07-14). Not a steering-feel change. |
| **Gentle-EME debounce thresholds** (6 cells, `0xC61C0-C5`, `0xC64B4/6`) | Honda's values | **disabled (all 0xFFFF)** | Related to a soft momentary-assist-loss behavior; the debounce that used to delay it is turned off. | V36 (pre-dates this kit's active work) | Carried, unexamined this era. |
| **Arbitration/LKAS-gain output clamps** (`0xC61B2`/`B4`) | 512 | **2048 (4×)** | Widens an internal ceiling upstream of the boost logic. | first touched V22, current value stable since V38 | Carried, unexamined this era. |
| **Corridor-wall & boost-floor constants** (14 cells, floats + ints) | Honda's values | **wider (≈5× on most)** | Pre-dates this kit's active investigation; widens an authority/boost envelope from the very first builds. | first touched V25/V29/V31, current values stable since V38 | Carried, unexamined this era — flagged so the operator knows it's non-stock even though nobody on this kit has re-examined why. |
| **ARB setpoint limits** (72 cells, all authority-curve records) | 15360 | **16384** | Widens the ceiling on how far LKAS is allowed to command the wheel, across every selector/mode. | V38 | Carried since the kit's own oldest active lever — this is the "V38 baseline" every later build sits on top of. |
| **CAN telemetry repoints & packer scale** (`0x55DF2`, `0x55E10`) | — | changed twice more | These do not change what the car does — they change what gets reported on the diagnostic CAN bus for this kit's own instrumentation. | V87 / V92 | Telemetry only, zero effect on driving. |
| **Cosmetic part-number bytes** (2 ASCII characters) | `-` | `,` | A build marker so this kit can tell its own firmware apart from a factory dump at a glance. No functional effect. | V22 | Cosmetic. |

⭐ **In one sentence**: the car currently drives with a 4× stronger LKAS command reaching a loop whose
own gain is untouched, a doubled rate-feedback term that fixed the grinding the operator used to hear,
a doubled friction-model gain whose real effect is still unresolved, and a friction/damper dose at
1.5× Honda's own value that has never had a clean verdict either way — sitting on top of an authority
envelope this kit widened from the very first build (V38) and a handful of older, unexamined
Honda-adjacent changes from V22-V36 that predate this kit's active investigation.

⚠ **One cell in the table WAS carried by accident, for a while** — the macro-ratchet fix (`0x454FE`)
was silently off the car from V53 to V79 (11 total moves on that one byte across the kit's history)
before being deliberately restored at V80, where it has stayed since. It is back on the car now,
deliberately, but it was absent for a real stretch of this kit's history without anyone deciding that
at the time — flagged in its own row above rather than glossed over here.

**Everything else in the table above is NOT carried by accident.** The standing warning about a silent
revert — seven levers lost at a V38 rebase — is about a DIFFERENT rebase (V76's) than the one in this
car's actual lineage. V99 descends through **V87's rebase**, which was deliberate and fully accounted
for at the time (11 bytes, zero unattributed, verified against V38 bit-for-bit before the two named
mods were reapplied) — not V76's. Every other cell traces to a deliberate edit in the build that
introduced it, verified from the image itself this session, not inferred from a build script's stated
intent.

*(Two very small, likely-noise cells are omitted from the table above for readability: `0x55C0E`, the
4-byte cave hook itself, and `0xC64DE`, a "legacy re-engage ramp" whose label is disputed and whose
delta is 10 counts on a ~25,600 baseline — neither changes driving feel. The full byte-exact
enumeration, all 140 control-law bytes, is in `docs/BUILD-LINEAGE.md`'s per-build rows and reproducible
with `python analysis-2020accord/ledger_v38_to_v99_bytes.py delta`.)*

---

# 13. ⭐ AFTER THE CLOSE-OUT — THE OPERATOR'S TWO QUESTIONS, AND FOUR RESULTS

Added 2026-08-13 (final). Prompted entirely by the operator, not by the session plan. Traces:
`TRACE-2026-08-13-4x-gain-to-term0.md` · `…-variable-ratio-rack.md` · `…-measured-steering-ratio.md`.

## 13a. "There's feedback on the LKAS command — shouldn't it be scaled 4× too?"
**It WAS, and that was a bug V57 fixed.** `0xC646C` is a **shared sensor-scale with 6 readers** (1 forward,
≥3 feedback, two of which read the raw torque sensor). Raising it for "4× authority" silently scaled two
raw-sensor feedback paths. V57 split the forward reader onto `0xC6CD0` and returned `0xC646C` to Honda's
891. **Leaving feedback at 1× is correct**: the forward path scaled coherently (clamps 512→2048, also 4×)
while the feedback path's limit is a **hardcoded ±0x200 literal**, not a cal — scaling it drives into a
ceiling that cannot move, i.e. a relay, the V80 class.

## 13b. ✅ THE 4× IS EXONERATED, TWICE [EVIDENCE, orchestrator-verified at `0x2b52a`/`0x2b52c`]
It does **not** reach term 0: `FUN_0002b422` writes a **literal zero (`r0`)** into struct field `+2` while
the 4× command goes to field `+4` ⇒ `gp-0x6b4c`. Forward and backward walks agree. And it is **not
saturating** — ceiling **512 → 2048, exactly 4× with the gain**, next fixed clamp **5×** above.
⇒ ***"Extra command buys no extra authority" is REFUTED. The 4× delivers a genuine, unsaturated 4×.***

## 13c. 🛑 TERM 0 IS IDENTICALLY ZERO — and the rail search lands on what V100 already measures
`gp-0x6b76 = -clamp(driver_torque, ±cal 0xC616C)` and **`0xC616C` = 0** (stock and V99, orchestrator
re-read `00 00` LE) ⇒ a clamp with limit zero annihilates its input; the other branch emits `0x7FFF`
which fails its own 20480 gate. **Both branches zero ⇒ `gp-0x6b4a ≡ 0`.**
⇒ **`gp-0x6ad6` is entirely terms 1–7, block-gated by `gp-0x67ab`. TERM 7 IS `gp-0x6b70`, whose own clamp
is the SAME cell `0xC6200` as the reference threshold ⇒ ZERO HEADROOM.** V100's `b5` measures exactly this.
⚠ `0xC616C` is a standing **NEVER-RAISE** cell — independently rediscovered from scratch this session.

## 13d. ✅ THE RACK QUESTION IS CLOSED — AND THREE ORCHESTRATOR HYPOTHESES DIED
The operator supplied Honda's variable-ratio rack curve and reported worst grinding in the centre band.
1. **"The plant model is structurally blind to rack position" — REFUTED.** `FUN_0003b8f6` reads absolute
   steering angle at `0x3ba12` and indexes `0xC6B64` (virgin on all 96 images).
2. **"The firmware under-compensates ~3×" — REFUTED by measurement.** 47 routes / 427 min, four disjoint
   estimators: **16.9:1 centre → 11.1:1 lock**, swing 0–120° **1.176 [1.147, 1.201]** vs the firmware's
   **1.206×** ⇒ **adequate, agreeing 0.01–0.07 at every knot.** The **1.67–1.82×** figure came from an
   orchestrator pixel-reading of a **schematic** graph whose depth is not recoverable. **Do not re-derive
   a rack number from that image.**
3. **"The left side is 3–5 % quicker" — REFUTED and retracted.** All 19 paired CIs cover equality; an
   **injected 2 % asymmetry IS caught** ⇒ a real ≥2 % asymmetry is **EXCLUDED**. θ₀ exonerated both ways
   (0.9 % leverage over a −7…−1.5° sweep); the per-side θ₀ split is **chord extrapolation** — midpoint
   pinned at −4.21°.
⊕ **What survives:** ~20 % uncompensated **beyond 120°**, where **all** exposure is **below 5 m/s**.
**65 % of engaged time is inside 0–34°, where compensation is correct.** ⇒ **No angle-dependent
plant-model error exists in the band he drives; this line is dead as a symptom explanation.**

## 13e. 🛑🛑 TWO INSTRUMENT FACTS THAT INVALIDATE OTHER ANALYSES
- **`carState.yawRate` is IDENTICALLY ZERO** — 0 nonzero of 512,895. Anything reading `cs_yaw` reads
  zeros. Use `livePose.angularVelocityDevice.z` (**z-DOWN ⇒ negative on a LEFT turn**).
- **`vEgo` is invalid as a speed reference at steering angle** — averages four wheels, **+7.9 %** fast at
  250–400°, **shaped exactly like a flat plateau**. It produced a **FALSE PASS of the ratio study's own
  positive control.** Use `(ws_rl+ws_rr)/2`.
⭐ Method note worth reusing: **a shuffle control is uninformative by construction here** (it kills the
sign relation, null [−1.43, +1.49]). **Injection nulls replaced it** — a genuinely flat rack reads back
**0.979 [0.968, 0.988]** through the identical pipeline.

## 13f. GOLDEN-MODEL GAP, OPENED AND MARKED
`eps_chain_control.py` models `gp-0x6ad4` as a lane and **does not model the PID's internals at all**, so
neither clamp is in it. A header note now sits at the exact site with the instruction addresses.
**Implementing it changes delivered numbers and must be its own verified pass with a re-derived
`_self_check`/`_demo` contract.** The **87-symbol / `740f4bcd…` contract PASSES** at this close-out
(comment-only edit, 2,512 bytes unchanged).
