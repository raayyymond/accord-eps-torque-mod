# STATE — living current state of the kit

**Last updated: 2026-07-31.** This file is the single current-state record. Update it in place at every
close-out; do not append new dated blocks (that is what made `CLAUDE.md` unreadable). The narrative of how
each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` (what has already been flashed, falsified, or **rejected on
review** — check it before proposing any calibration edit) and the latest handoff,
`docs/HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md`
(predecessors: `HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md`, then
`HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`, then
`HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md`).

🛑🛑 **THE HEADLINE, 2026-07-31: V61 made the grinding WORSE, and that inverted the record.** The
torsion-bar RATE lane (`r24`/`r26` in `FUN_0003aa2c`) is the mode's **DAMPER**, not its amplifier. Every
build that touched it — V39, V42, V61 — tested it **downward**. The gradient points **up**. **V62 is
built and is the recommended next flash.** See "On the car right now" below.

🛑 **Explain firmware with Python that mirrors the decompiled arithmetic exactly** — standing operator
instruction, 2026-07-28. Integer `>>`, the real Q-format, the real branch conditions, each line annotated
with its instruction address, constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation
comes *after* the code, never instead of it.

---

## 🛑🛑 THE TWO SYMPTOMS ARE DIFFERENT PHENOMENA — settled by the operator 2026-07-30

Everything before this date conflated them. Read this before any other section.

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz** (Q≈36, 2nd harmonic locked at 15.0 Hz) | **FIXED ~20.9 Hz** ⚠ see below |
| where it dominates | parking-lot creep at large steering angle | ⚠ **CREEP-ONLY on V58** — see below |
| variance share, r29 burst | **33.0%** (6–9 Hz) | **5.3%** (19–24 Hz) |
| vs command saturation | **rises 8.42×** with rail duty | falls to 0.74× |
| in openpilot's command? | **no** — command's 6–9 Hz peak is 6.26 Hz, 6.4 bins away | ⚠ **YES** — see below |

🛑 **Three entries in that table were corrected by the V58 drive (route `2b`, 2026-07-30).** They are
left visible above with pointers rather than silently overwritten:

1. **The frequency law `f = 0.177·v + 20.48` does NOT reproduce.** Strict 18–26 Hz band, sub-bin peak,
   speed stable within 1.5 m/s: slope `a = −0.005 … +0.031` at every prominence cut (n = 23–75, v span
   1.13–17.5 m/s). **`a = 0` fits within 0.12–1.48σ; `a = 0.177` is rejected at 3.2–7.1σ.** Model-free
   per bin: 20.65 / 20.83 / 21.90 / 21.50 / 21.61 / 20.46 Hz over 0–20 m/s vs a predicted 20.66 → 23.49.
   ⚠ **Do not rewrite the law off one route yet** — the recorded value came from a *pooled cross-route*
   fit whose own source warned "steering angle shifts it ±2 Hz", and on route `2b`
   `spearman(v,|ang|) = −0.728`. Re-run the strict-band test over V55/V56/V57 first (step 2 below).
   ⚠ **Search-band trap:** a 15–30 Hz or 17–28 Hz band catches the **ratchet's 2nd harmonic**
   (2×8.0–8.9 = 16–17.8 Hz) at road speed; the argmax then steps down to ~15 Hz and fakes a *negative*
   slope. A creep-only window fakes a *positive* one. Use 18–26 Hz **plus a presence test**.
2. **Creep-only, not road speed.** 18–26 Hz prominence by speed (engaged): 141× / 138× / 518× at
   1–2 / 2–3 / 3–4 m/s, collapsing to 29× / 11× / 8× / 7× at 4–6 / 6–10 / 10–14 / 14–18 m/s — and above
   6 m/s the peak-frequency scatter (sd 1.5–2.2 Hz) shows there is no coherent line at all.
3. **~21 Hz IS in openpilot's command.** Verified on the **native 0xE4 grid**, so not a held-last
   resampling artifact: 20.89 Hz at prominence 34.0×, `coherence(cmd, bar) = 0.917` at 20.96 Hz (K=4,
   95% null 0.632); co-located command peak in 8/21 strong-line windows vs 1/11 weak. The bar's line is
   6–7× sharper, which reads as an echo — but **direction is unresolved.** Carrier phase cannot settle it
   (one-sample mailbox skew = 75° at 21 Hz), and the skew-robust **envelope** cross-correlation was
   **inconclusive** (2/4 runs bar-leads, 2/4 command-leads, peak corr only 0.33–0.44). ⇒ openpilot is
   inside this loop; that is a constraint on any firmware fix, not an action.

⚠ **Operator correction, authoritative:** the 7.4 Hz line is the **ratcheting**, not the grinding. An
earlier pass this session called it "the grinding" and concluded the kit had been chasing the wrong mode
for 50 builds. **That conclusion is withdrawn** — the 20–25 Hz focus was correct all along.
⚠ **Steering-angle excitation of the 7.4 Hz mode is a CORRELATION only**, related through return-to-centre.
Do not treat angle as causal.

**The ratchet is not the V42 ratchet.** `STEER_STATUS == 4` fires in **0 of 37,922 frames** across both
V57 routes, so the state-4 governor (`0x454FE`, root-caused and fixed by V42) is not producing it.
Mechanism unknown. It is a plant limit cycle gated by applied LKAS torque, not commanded: over 0.21 s the
command drifts 510 counts while the torsion bar swings **2,791 counts through 3 sign changes**.

---

## ★★ V59 FLEW 2026-07-30 (route `2c`) — the grinding mechanism is a PARAMETRIC PUMP, and it is MARGINAL

**V59 is FLIGHT-CLEAN.** 50,963 frames / 9 segments (2,5,6,7 not uploaded). `ST==4`: **0/50,963**.
No `steerUnavailable`/`steerTempUnavailable`/`canError`/`steerSaturated`. Probe **100% live, 100%
thermometer-monotonic, fault sentinel 0.000%**, stock low bits `&0x07 == 0b111` with zero exceptions.
`0x14A`/`0x18F` at 100 Hz. Two boundary transients only (a boot cluster in `wrongGear`, and one
`controlsMismatch`/`immediateDisable` at the tail of seg 12 — parked, LKAS off). ⚠ The route was NOT
the pure creep route specified: segs 4/8/9 are road speed to 23.6 m/s. It did deliver what `2b` could
not — **50.2 s of engaged + creep + SUSTAINED hands-off**.

### The mechanism
`gp-0x6ba6` is `|filtered signal|` — **rectified** — so it sweeps the boost-amplitude LERP at **2× the
mode frequency**. Measured, engaged+creep+hands-off (13 runs, K=30, periodograms averaged across
DISJOINT runs, never spliced): the thermometer's own spectrum peaks at **42.19 Hz** (= 2 × 21.09 to
within one bin), prominence 11.10×; the 18–26 Hz band shows only 1.23×. **Disengaged: bit5 NEVER
toggles — 0/4 runs, 61.2 s, K=90, prominence 0.00×.** Depth 76.93% <512 / 18.46% 512-1k / 4.57% 1k-2k
/ 0.04% ≥2048 engaged, vs **99.83% <512** disengaged. Toggle rate **25.55/s hands-off, 9.42/s
hands-ON, 0.00/s disengaged** — hands-on the index sits *pinned high*, it does not modulate.
`corr(env, lvl)` is **positive in 11/11 hands-off runs** (median +0.487, +0.485 partialling out
effort); the negative hands-ON value is pure Simpson's paradox. **0 of 33 windows have the index
sweeping with no grinding line.**

🛑 **What V59 did NOT establish.** The index is `|x|` of a bar-derived signal, so 2f coupling and
index-tracks-mode are **arithmetically forced** once the ripple exists — coherence against the bar is
circular and is not evidence. What is new is the **depth**, and that it survives hands-off.
**Causality is not settleable observationally.** Only an intervention separates drive from echo.

### ⇒ It is an AMPLITUDE-GATED BOOTSTRAP, and it is MARGINAL
A pump at 2f into a mode at f is the principal Mathieu resonance; threshold `eps_crit ≈ 2/Q = 0.147`
at the recorded Q = 13.6. Simulating the **literal integer arithmetic** with the confirmed blend
direction, across both open unknowns (task rate; series question):

| `\|tq\|` amp | 1 kHz y4-only | 1 kHz both | 500 Hz y4-only | 500 Hz both |
|---|---|---|---|---|
| 218 (median) | 0.013 | 0.020 | 0.013 | 0.020 |
| 829 (p90) | 0.072 | 0.104 | 0.055 | 0.080 |
| 1451 (p99) | 0.104 | **0.169** | 0.070 | 0.116 |

eps scales with amplitude ⇒ a **bootstrap**: a kick raises the oscillation → the index swings wider →
the modulation deepens → more pumping, until the curve flattens past index 3645 and the clamps bite.
That is why the grinding **bursts** rather than hums, and why it needs a road input to ignite.

🛑🛑 **THE THRESHOLD COMPARISON IS UNDECIDABLE FROM THIS DATA — do not quote a verdict either way.**
`eps_crit = 2/Q` needs the **PASSIVE** Q (the mode's damping when *not* being driven). That is not
measurable while the mode is active, and V59 contains no free decay to measure it from:
- **Ring-down: none exists.** 66 candidate decays, longest **0.63 cycles** — envelope wiggle, not
  damping. The mode does not ring down; it is sustained while conditions hold.
- **Autocorrelation analytic envelope** (biased-ACF triangular taper divided out, tau capped at 25%
  of record) gives apparent **Q median 102, range 22–1083** (n=8 hands-off runs). ⚠ That is the
  coherence of a *driven* oscillation, **NOT** the passive Q — a self-sustained limit cycle has
  near-infinite apparent Q. It cannot be substituted into `2/Q`.

| assumed Q | eps_crit | verdict vs measured eps (0.020 / 0.104 / 0.169) |
|---|---|---|
| 13.6 (recorded, provenance unverified) | 0.147 | marginal — crosses only at p99 |
| 22 (lowest apparent) | 0.091 | **above** at p90 and p99 |
| 102 (median apparent) | 0.020 | **above everywhere** |

⚠ **What the coherence DOES support:** a passive Q=13.6 mode kicked by broadband road noise would
show coherence ~`Q/(pi*f)` ≈ 205 ms. Observed is 0.33–17 s equivalent — **far more coherent than
random excitation of a lightly-damped mode can produce.** ⇒ there is an **active, phase-coherent
drive**. That is consistent with the parametric pump but does not prove it is the drive.

⇒ **Only an intervention decides it. V60 is the discriminator, not just a candidate fix.**

### The structure — golden model was WRONG, and there is a filter nobody had modelled
`FUN_00034a72`: the two amplitude curves do **not** multiply in series. `0xD2888` scales the final
assist term (`sar 0xe,r13` @`0x35008`); `0xD28DC` enters earlier (`shr 0xe,r28` @`0x34C26`) and is
**differenced against `gp-0x6a56`** then clamped ±12000. ⚠ **UNRESOLVED DISPUTE:** a subagent holds
`0xD28DC` is a dead end (3 image-wide refs to state cell `gp-0x69bc`, all in-function). That argument
is **structurally invalid** — a scan of the STATE CELL cannot show whether the blended value is
consumed in a REGISTER the same tick, which is what a slew-limited gain does. The decompiler shows the
blended y1 as an operand of a `>>14`, and a byte scan finds exactly two `>>14` sites in the function,
one of them at `0x34C26` inside the span the subagent claims to have traced. **Not called. It does not
change the verdict** (see the table — both columns are mostly sub-threshold).

★★ **BOTH LERP outputs are SLEW-BLENDED before use** — previously unmodelled entirely. Rate cal
`0xCA06C[10] -> 0xD2006 = 102` (Q10). **Direction CONFIRMED @`0x34be4`** (`cmp r25,r10 / ble` →
instant snap when raw ≤ old): **FALLING is instant, RISING is slowed** — a fast-attack/slow-release
gain reducer. This is what pulls eps down from the raw-LERP values.

### Levers — one clean, three closed
- ★★ **`0xD2006` = 102, the blend coefficient. THE LEVER, and GATE 1 is CLEAN.** Lowering it
  attenuates the 42 Hz pump **without moving the static gain map at all** (the blend converges to the
  same steady state ⇒ DC assist and manual feel untouched). Blast radius byte-verified: exactly one
  pointer (`0xCA094`) references it; the "three identical copies" in `0xD2000` are modes 10/11/12's
  independent entries, not an array; distinct from the ceiling (`0xD2000`) and gain scalar
  (`0xD200C`) for the same mode; not array-consumed. Only other hit is the CRC/block directory.
  ⚠ Expected benefit is **modest and uncertain** — eps is already mostly sub-threshold, so this bites
  only on the loudest bursts. The argument for it is that a *bootstrap* only needs to be kept below
  threshold at the amplitudes where it currently crosses. Feel cost: slower gain recovery after a
  sharp input (tau ≈ 10 ms now, ≈ 24 ms at cal 43 — short vs steering dynamics).
- 🛑🛑 **FactorC damping (`0xD27BC`/`0xD27C6`) — ALREADY FLASHED AND FALSIFIED. DO NOT RE-PROPOSE.**
  **`V44` set `0xD27C6` 0 → 235 and `0xD27DA` 0 → 234 (modes 10/11), flashed, and it was NULL** —
  because **Factor E (`0xC9F84[mode]`, the motor-rate deadzone) re-zeroes the product downstream.**
  **`V47` then attacked Factor E itself** (`0xD2802/04/06`, `0xD2816/18/1A`) → *"marginally quieter at
  5 mph, no effect in motion."* **Both were confirmed 2026-07-28 to hit the LIVE table** (PN → key
  `TVAA1` → config row 2 → INDEX 10 → `0xD27BC`). `BUILD-LINEAGE.md` states it outright: *"the
  missing-damping hypothesis was genuinely tested and IS falsified — do not resurrect it on a 'wrong
  variant' theory."*
  ⚠ **Damping IS exactly zero below 35 km/h** (`Y[0]=0`, all 34 mode tables) and that remains true and
  relevant as *context* — but the lever has been driven from **both** factors and neither moved the
  grinding. V44's *rationale* was withdrawn (it thought the axis was driver torque; it is speed), yet
  **its on-car NULL stands regardless of why it was built.**
  🛑 **This was re-proposed on 2026-07-30 by the orchestrator as "V61", after the loop hypothesis made
  it look freshly attractive — the operator caught it. The build script was written and deleted
  unexecuted.** Cause: the address was named without grepping `build_v*_tva.py` first. **That grep is
  mandatory and it is cheap. FALSIFIED ≠ untested, and a compelling new mechanism is exactly when the
  check gets skipped.**

  ✅ **Salvage — genuinely new and worth keeping regardless:** the damper's **int/float lockstep is
  SAFE for a FactorC-class edit.** `FUN_000347b8` @`0x347b8` *reads* `gp-0x6bd0` (first line,
  `(float)gp-0x6bd0 * 0.0009765625`) and only re-clamps it with an independently recomputed **ceiling**,
  faulting via `FUN_000462e6(0x417a,…)` if the two differ by more than `0.0048828125` = **5/1024**. It
  **never recomputes the four-factor product**, so FactorA/C/Ramp/MotorRate are *not* float-mirrored.
  And the two ceilings are the **same table in two number formats**, byte-verified:
  `INT 0xC77A0[10] → 0xD209C: X=[300,800] Y=[512,1024]` vs `FLOAT tp+0x7554 = 0xC6554: 300.0, 800.0,
  0.5, 1.0`. ⇒ exact agreement, tolerance never approached. **Damper authority at creep is hard-clamped
  to ±512 against the aggregator's ±10240 (≤5%)** — a firmware-enforced bound worth remembering for any
  future damper-lane work. Confirmed 4 ways (`search_instructions`, raw LE byte scan, `get_xrefs_to`,
  and a **split-encoding check** for `movhi`+`movea` construction of the address — only 2 `movhi 0xd`
  exist image-wide and neither resolves near `0xC9E9C`). Modes 8/11 byte-identical to mode 10.
  Escalation map, for any future damper work: `FUN_000347b8` → `FUN_000462e6(0x417a)` →
  `FUN_00016de6(0x1d)`; and `FUN_00034350`'s own entry-time re-check → `FUN_0004613e(0x4179)` →
  `FUN_00016de6(0x1c)` — **one tolerance in two representations** (0.0048828125 × 1024 = 5.0 exactly),
  not two independent gates.
- 🛑 **RECORD CORRECTION — `0xD2018` is not what we said.** It is **data**, one resolved pointer inside
  `FUN_00035154`'s `0xC7888[mode]` ceiling array — `search_instructions` finds zero because it scans
  instruction operands only. And `FUN_00035154` is simply the `gp-0x6bbe` **analog** of `FUN_000347b8`:
  ceiling-only, same ±0.0048828125 tolerance, same escalation, keyed on `gp-0x6a62` instead of
  `gp-0x6ac2`. The old note ("any edit to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table
  `0xD2018` or it may trip") implied a stronger, different mechanism. It is the same pattern.
- 🛑 **`gp-0x6b70` — TRACED AND CLOSED 2026-07-30. It terminates at an already-falsified lever.**
  Full chain, measured: `FUN_00038148` (1 kHz) sums **six UNITY-weighted terms** — `gp-0x6bd0` (damper)
  and `gp-0x6bbe` (boost) among them, cals `0xC63A0/A2/A4/A6/A8/AA` **all = 1024 = exactly 1.0**,
  byte-read — EMA-blended at `0xC63AC` = 102/1024, → `gp-0x6b70` → `FUN_00037fe6` (one of seven
  unity-weighted terms, cals `0xC64AD-0xC64B3` all = 1) → `gp-0x6ad6` → **`FUN_0003a382`** (the real
  PID) → `gp-0x6ad4` → `FUN_0003aa2c`'s aggregator → `gp-0x6b94` → governor → `gp-0x6b98`.
  ⇒ **So boost and damper DO re-enter a second, parallel aggregator at unity gain.** That structural
  fact is new. But **every weight in the whole chain is unity and stock — there is no hidden loop gain
  in the aggregation.**
  ★★ **And the chain's only output-shaping calibration is `0xC6AF0`** — `FUN_0003a382`'s authority
  ceiling, which **V56 already zeroed, flashed: NULL on the grinding, and it cost damping** (V57/V58
  both carry the assertion `"0xC6AF0 must stay STOCK -- V56's mute is falsified"`). Since `gp-0x6ad4`
  has only 2 accesses image-wide, that mute was equivalent to deleting this entire chain's
  contribution. ⇒ **a second independent reason not to hunt loop gain down this path.**
  ⚠ Genuinely untouched by any build (`grep`ed): `0xC63A0-0xC63AC`, `0xC64AD-0xC64B3`, `0xC6200`, and
  whatever produces `gp-0x67ab`/`gp-0x69aa`. Not proposed as levers — recorded as unexplored.
  ⚠ Open: `gp-0x67ab` / `gp-0x69aa` semantic identity (structural role only); `FUN_00026c80`, the
  11-channel mixer feeding them, only partially read.
- ★ **SECOND instance of the over-count scan trap, same session.** `search_instructions` reported
  **21 hits** for `gp-0x6b70`; **19 were false positives** — substring collision against
  `jarl 0x0006b700,lp`. A raw byte scan finds **exactly 2** (writer `0x382d2`, reader `0x38006`).
  Together with the `6bd0`/`0x00076bd0` collision this is now a **recurring** failure mode, not a
  one-off. **Always confirm a hit is a gp-relative operand, not an address literal.**
- ⚠ **The off-by-0x1000 tp trap recurred again** (a subagent computed `tp+0x73a8` as `0xC73A8`; it is
  `0xC63A8`). Self-caught. That is now **five** recorded occurrences.
- ★ **NEW SCAN TRAP — `search_instructions` can OVER-count too.** `operand_pattern="6bd0"` returned
  false positives from **substring collision against the branch-target literal `0x00076bd0`** in
  `FUN_0006bcb2`/`FUN_000757a2`. Every trap on record so far was about *undercounting*; this is the
  first over-count. **Confirm the hit is a gp-relative operand, not an address literal.**
- 🛑 **`0xC63BA` (=512) — PARTIAL ONLY.** Byte-verified 2-stage EMA, alpha 0.5 both stages, blast
  radius fully contained (2 reads, both in `FUN_0003b66a`). But it filters only the **torque** lane;
  the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
  `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). Both analysts were right.
- 🛑 **Speed-keyed assist concentration — REFUTED.** `0xD2834` is nearly flat (rel 0.856 / 0.979 /
  0.987 / 0.997 / 0.903 at 0.5 / 3 / 6 / 10 / 18 m/s).

### Closed and corrected by this drive
- ✅ **The damping SIGN is no longer open.** `gp-0x6bd0` (`FUN_00034350`, sole producer, 3 writes) has
  its sign forced to `-sign(gp-0x6abe)` @`0x3469e-0x346a2` — textbook velocity-proportional damping,
  correct by construction. Joins the aggregator at `0x3ac78` in `FUN_0003aa2c`.
- ✅ **The frequency law is rejected a SECOND time.** Route 2c: `a = 0.177` rejected at **2.60σ**
  presence-tested (n=19, 9 runs), up to 7.08σ without. `a = 0` fits at every cut, ~20.4–21.1 Hz flat.
  Crucially the fitted subset is **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728).
  ⇒ **The fixed ~20.9 Hz line is now the record.**
- ✅ **V58/V59 control PASSES** — grinding statistically identical: 7 of 8 jointly speed-and-effort
  matched cells in 0.76–1.41× with no systematic direction, peak frequency within 0.7 Hz everywhere.
  Exactly what CAL-CRC-unchanged predicts; validates the comparison chain.
- ⚠ **CORRECTION to "creep-only":** that holds for the **hands-off** arm. There is a second
  population at **10–13 m/s under driver load** at large angle (prominence 174–651×), verified NOT a
  tyre order (frequency CV 2.2% vs order CV 9.8%; 3.89 is not an integer order). Correct wording:
  *strongest at creep 1–4 m/s; sampling gap at 6–10; still coherent at 10–13 under steering load;
  absent above 14 m/s* (0 of 48 windows pass presence).
- ⚠ **~21 Hz IS in openpilot's command**, confirmed again: native-`0xE4` prominence median 35× (max
  46×) hands-off, coherence **5/5 above the K-appropriate 95% null**. **Direction still NOT settled**
  — envelope cross-correlation splits 2 bar-leads / 3 command-leads, same as V58.
- ★ **Route 2c contains hands-off engaged creep RATCHET episodes** — 7.56 ± 0.36 Hz, within-run sd
  0.07–0.10 Hz, prominence median 783× (max 2142×), 15 windows / 5 runs, at both 9–15° and 133°.
  `STATE.md` previously recorded route 2b gave **zero** and that a dedicated route was required.
  Mode identity unconfirmed — the data exists, that is all.

### Open gates before V60
1. ✅✅ **RESOLVED 2026-07-31 — TASK 5 IS 100 Hz, and it invalidates the eps table above.**
   The rate divider is `FUN_00014be4`, a mod-100 counter (`gp-0x4304`) on the 1 kHz tick. Verified by
   the orchestrator: `tp-0x3814` = `0xBB7EC` byte-reads **`0x000BB920`**, and `idx*0x30 + 0xBB920`
   reproduces **all seven** TCB entry points exactly (`+0x08`), so the wake argument is a **0-based
   task-slot index**, not an abstract group ID:

   | idx | TCB entry `+0x08` | task | condition | **rate** |
   |---|---|---|---|---|
   | 0 | `0x0002214A` | task 1 — arb, `FUN_0003b66a`, aggregator, governor, shaper | every tick | **1000 Hz** |
   | 1 | `0x00022A88` | task 2 | `c & 1` | 500 Hz |
   | 3 | `0x00022B24` | task 4 | `c % 5 == 2` | 200 Hz |
   | **4** | **`0x00022CA0`** | **task 5 — boost `FUN_00034a72` + damping `FUN_00034350`** | `c % 10 == 4` | **100 Hz** |
   | 5 | `0x0002351E` | task 6 | `c == 0x10` | 10 Hz |

   ⇒ **The V59 eps table bracketed 1 kHz and 500 Hz. Both are wrong.** The boost-amplitude LERPs are
   evaluated at **100 Hz**, so a 42 Hz index modulation is sampled ~2.4×/cycle — barely above Nyquist
   and heavily ZOH-attenuated. **The pump could barely act at all**, which is an independent structural
   reason for V60's null on top of the empirical one.

   ★★ **THE BIGGER CONSEQUENCE — a 100 Hz damper cannot damp a 20.9 Hz mode.** `gp-0x6bd0` is
   velocity-proportional damping (sign forced to `-sign(gp-0x6abe)`), and damping only works when the
   force is in phase with velocity. A zero-order hold at 100 Hz costs `360 · 20.9 · T` of transport
   lag: **37.6° average (T/2), 75.2° worst case**, before any plant phase. ⇒ **a structural explanation
   for why EVERY damper lever was null (V44 FactorC, V47 FactorC+FactorE together) that does not depend
   on the FactorC speed-axis argument** — even with both deadzones fully open, the damper is too slow
   to act on this mode. It may even be anti-damping at 21 Hz.
   ⇒ 🛑 **Any fix acting through boost or damping is fighting 38–75° of architectural lag at the mode
   frequency. Prefer task 1 (1 kHz).** V61's edit is in `FUN_0003aa2c`, task 1 — on the right side of
   this. Any future task-5 change needs this in its GATE 2.
2. **`gp-0x6986` / `gp-0x6988` values unmeasured** — they scale the pump. Both are ≤1024 clamps so
   they can only pull eps *down*.

---

## On the car right now — **V61**

## ★★★ V61 FLASHED AND DRIVEN 2026-07-31 → **WORSE. And that is the best result this kit has had.**

**The first SIGNED on-car outcome on any vibration lever.** Every prior build was a null or a fault.
V61 made the symptom *worse*, which is strictly more informative — it measures the **gradient**, and the
gradient says every previous attempt on this lane was pushing the wrong way.

**What V61 did:** zeroed the torsion-bar torque-RATE lane at **both** taps of its shared
`r1 = clamp(gp-0x4f62, ±5120)` (`0x3AB6C mul r1,r6,r0 → mul r0,r6,r0`; `0x3AC16 mov r1,r8 → mov r0,r8`).
Two single-bit reg1 changes, no cave, no calibration moved.

**Operator, authoritative:**
- **LKAS ON, forward** — grinding still present and **significantly worse**: higher amplitude, louder.
- **LKAS OFF, forward** — grinding **newly present** in manual driving when turning.
- **LKAS OFF, reverse** — grinding **definitely newly present** in manual driving.

### ⇒ The rate lane is the mode's DAMPER, not its amplifier
Sign verified by the orchestrator from image bytes, not relayed:
- `gp-0x6752` (polarity) is **one load @`0x3AB78` reused unmodified by both lanes**, and the *same byte*
  is read by `FUN_0003a382`'s resonance lane @`0x3A71A` — the aggregator's one genuinely
  torque-**proportional** P-term. ⇒ **polarity CANCELS**; its value is not needed to answer the question.
- The combine chain `0x3ACC8`–`0x3ACDA` is **ten instructions, every lane entering with `add`**, each
  add's `reg1` threading the previous add's `reg2`. **Not one `sub`.**
- ⇒ `r24, r26 = +Kd·d(T_bar)/dt` **in phase with assist** — `Kp·x + Kd·dx/dt`, a lead compensator.

For the hands-off mode (steering-wheel inertia on the torsion bar), with motor torque on the column only:
```
phi'' + (Kd·k/J_c)·phi' + k·(1/J_w + (1+K)/J_c)·phi = T_road/J_c
```
The `phi'` coefficient is **`Kd·k/J_c > 0` — positive damping, LINEAR in Kd. At `Kd = 0` the mode has no
damping term at all.** That is V61, and that is what the car did — including in **manual** driving, where
base assist is the only loop running, and worst in **reverse**.

🛑 **A derivative term is DC-neutral** (zero at constant torque), so V61 cannot have "removed assist" — it
changed **only** dynamics. That is what makes this a clean signed measurement rather than a confound.

🛑 **This falsifies the golden model's framing.** `eps_lkas_chain_model.py:1792` called r26
*"excitation-to-amplifier: faster slew → bigger derivative → bigger r26 → more motor torque → repeat"* and
recommended the r26 kill. Both passages are **struck and corrected in place**. ⇒ **V39 (r24), V42 (r26)
and V61 (both) all tested this lane DOWNWARD.** Their results stand; they bracket the **wrong side**.

★ **Why this lane and not the dampers already tried:** `FUN_0003aa2c` is **task 1, 1000 Hz** ⇒ ~3.8° of
ZOH lag at 20.9 Hz. Boost/damping are **task 5, 100 Hz** ⇒ **37.6–75.2°** — the structural reason V44 and
V47 were null. **The rate lane is the only damping mechanism in the chain fast enough to act on this mode.**

⚠ **No rlog analysis is folded in yet** — route `00000031--0441e00d2b` (4 segments) is the V61 drive and
its quantification was still running at close-out. The conclusions above rest on the operator's report
plus the firmware arithmetic, both of which are solid independently. **The rlog should still be analysed**
— see next steps.

---

## 🛑 V60 FLASHED AND DRIVEN 2026-07-31 → **NULL. The parametric pump is CLOSED.**

Operator: *"I drove on the V60 RWD. It did not fix the vibration issue."* **No rlogs** — V60 carries
V59's probe unchanged, so there was no new telemetry to upload.

**This null is a result, not a wasted drive.** V60 was built as a **discriminator** and the record
predicted the outcome: *"Expect it to be NULL… a null closes the parametric mechanism and leaves the
loop standing."* Pump causality was not settleable observationally (the index is `|x|` of a bar-derived
signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a passive Q that V59 could
not measure. Only an intervention could separate drive from echo. It did.
⇒ **V58/V59/V60's whole arc closes. The 42.19 Hz index modulation is real, engagement-gated, and is NOT
the driver of the grinding.**

★ **Consequence — `0xC63BA` is pre-falsified by the same null and must NOT be proposed as a fix.** It
looked ideal (cal-only, 512 = 2-stage EMA α = 0.5 ≈ −0.30 dB at 21 Hz, exactly 2 readers at `0x3B7BA`/
`0x3B7D4`, never edited, explicitly reserved by `build_v59_tva.py:444` as *"a V60 candidate"*). But a
byte scan of its consumers closes it: readers of `gp-0x6b9a` (8) and `gp-0x6ba6` (7) are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer, and V59's probe cave — so the index
drives **only** the boost/damping amplitude LERPs, i.e. the mechanism V60 just falsified. Proposing it
would repeat the V44/FactorC pattern exactly.

⚠ **Two more lanes removed from the search, byte-verified:** `FUN_00036c12` (`gp-0x6b26`) and
`FUN_00036388` (`gp-0x6b62`, the return-centre lane that was the operator's own hypothesis) read **no
torque signal at all** — speed- and motor-rate-keyed only.

**V58** = V57's calibration + the angle-rate/boost-lane probe in the cave. Flashed and driven 2026-07-30,
route `2b` (normal commute, 14 segments, ~14 min, 83,959 frames, creep → highway → parking).

```
0xC646C  shared sensor scale = 891 (stock)     <- was 3564 on V38..V56
0xC6CD0  private LKAS forward gain = 3564      <- V57's new cell
0xC62EA  low-speed lockout = 0                 <- V53, unchanged
0xC64DE  re-engage ramp = 27                   <- V18, carried forward correctly
_v58_plain_image.bin  SHA 431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48
V58 .rwd              SHA 7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7
```

**V58 is FLIGHT-CLEAN.** `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/
`immediateDisable`: **0 across all 14 segments** (raw `onroadEvents` scan, verified twice). The only
flags are `commIssue`×2 + `selfdrivedLagging`×1, all at seg 0 t≈8.5 s **in `wrongGear` before the drive
started** — a boot transient, unlike route 28's real mid-drive soft-disable. `STEER_STATUS == 0` in
**83,959/83,959** frames; **`ST==4`: 0**, extending V57's 0/37,922 to 121,881 combined clean frames.
Probe low bits `& 0x07 == 0b111`, zero exceptions. `0x14A`/`0x18F` at 100.00 Hz in every driving segment.

**V58's on-car result — see the handoff for the full numbers:**
- ★★ **The collinearity confound is BROKEN.** Seg 13 gives 60 s of *moving but disengaged* at
  0.5–4.8 m/s. Speed-matched grinding: **13.4×** [95% 3.9–19.8], **16.9×** speed+effort-matched, and
  **184×** on time-occupancy at matched creep. Better than any ratio — **the resonance is ABSENT
  disengaged**: prominence median 122.7× vs 3.6×, with the disengaged "peak" wandering 15–29.9 Hz
  (sd 2.49 Hz) i.e. the argmax of a floor. Confounds run *against* the engaged arm (disengaged has
  |ang| 167° vs 9°, effort 1638 vs 205). ⇒ **the grinding requires applied LKAS torque. Settled.**
- ✅ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED.** The lane never pins, so
  `K1` @`0xD200C` = 43 keeps its headroom.
- 🛑 **bit6 VOID BY CONSTRUCTION.** `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s; it is
  DC-dominated. **The damping sign is STILL OPEN.** ⚠ Pooling runs to force an answer manufactures a
  splice artifact (bit6 has 5/0/0/1 transitions *within* the four engaged runs, so a concatenated
  "coherence 0.5 at 25 Hz" is step discontinuities at the joins). **A sign comparator is a phase probe
  only for a signal that crosses zero at the frequency of interest.**
- ★★ **bit4 FIRED and is the lead.** `sign(gp-0x6b9a)` at 20.93 Hz, per-run coherence
  0.649/0.970/0.769/0.881, own-spectrum peak 10.8× median, `corr(envelope, toggle rate) = +0.834`.
  At matched creep: **13.69 toggles/s engaged vs 0.61 disengaged**, 20.93 Hz line present in one arm and
  absent in the other, duty cycle barely moving ⇒ it *oscillates*, it does not merely sit elsewhere.

🛑 **Hands-off could not be conditioned on anywhere on this route** — zero fully-hands-off windows in
either arm in any qualifying speed bin. Everything above is "any hands", matched on effort instead.

## Built and UNFLASHED

| build | what | status |
|---|---|---|
| ★★ **V62** | V59 + **DOUBLE the torsion-bar RATE lane** — `sar 0xa` → `sar 0x9` on each lane's final shift | ✅ **BUILT 2026-07-31, UNFLASHED. The matched inverse of V61 and the recommended next flash.** `0x3AC20 42AA→42A9` (r24) and `0x3AB76 32AA→32A9` (r26). V61 took `Kd`→0 and the mode diverged; V62 takes `Kd`→2×, the same-sized step back. Stock sustains with **no ring-down at all** ⇒ `zeta_net ≈ 0`, so doubling should move it to `+zeta_lead`. **6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38. ⭐ **CAL CRC unchanged** and ⭐ **`0xD2000`-block CRC unchanged** = machine proof no calibration moved and V60's falsified blend is absent. 50/50 CRC, RWD round-trips with every gate re-run on the readback; re-verified independently from the built image (taps back at `r1`, both shifts `sar 0x9`, `0x3AB70` still `sar 0xa`, exactly 2 code bytes). 🛑 **`sar` immediates chosen OVER the gain cals**, three traced reasons: the live gain arm is a **priority chain** that cannot be pinned statically (`gp-0x671a` is a bounded [0,5] *persistence ramp* that plausibly never saturates during a 21 Hz oscillation); **r24's default arm is MODE-INDEXED** via `gp+0x63fd` through four pointer arrays (`0xD2AEC`←`0xCC154` idx 10, `0xD6AEC`←`0xCC184` **idx 22** — ⚠ **a different MODE, not a redundancy twin; the "V27 desync" reading was wrong**); and `gp-0x683c` has **zero writers** ⇒ `0xC6446`/`0xC6444` are dead arms. A `sar` edit doubles the lane **under every arm and every mode**. 🛑 **`0x3AB76` not `0x3AB70`** — V850 `mul` discards the high word into `r0`, and doubling before the `×gain_A` multiply pushes the worst case to **94% of INT32_MAX** vs 47% (unchanged) after it. **Headroom is arm-dependent**: ~22× / ~11× / **~7.3× worst case**, so doubling keeps ≥3.6× margin. GATE 1 **vacuous** (no cave, no RAM, no new opcode). ⚠ **Residual:** `avg(gp-0x69a4)` magnitude is still unmeasured after three sessions — if r26 were already pinned at ±8192 doubling would deepen a saturation; bounded against by the fact that such a lane would dominate the ±10240 sum clamp and V61 would have been far more dramatic. r24 is immune. ⚠ Manual feel **will** change. Reversible by reflashing V59 or V61. Image SHA `80d9e1f721b741722a9d4b141a2d328fe8d999705765fedffab1ad23aa9264c7`; RWD SHA `1e0806a1eac69688e6d636fa02c5b1e864da40a65a4d3f8137d444d1ec5bff8e` |
| ~~V61~~ | V59 + **kill the torsion-bar RATE lane at BOTH taps of its shared value** | ★★★ **FLASHED 2026-07-31 → WORSE. Do not re-flash except as a deliberate revert.** The signed result that inverted the record — see the section above. Original build note kept below for provenance. **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, `r1 = clamp(gp-0x4f62, ±5120)`, produced at `0x3AAAC-0x3AAC0` and tapped twice: `0x3AB6C mul r1,r6,r0` (r26) and `0x3AC16 mov r1,r8` (r24). **V39 killed only r24 — and only *conditionally*** (cave at `0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright (*"WHY r26 AND NOT r24: r24 was already zeroed by V39"*). Same sign, shared polarity load @`0x3AB78` ⇒ **killing either alone leaves the other transmitting, so each null is uninformative about the lane.** ⭐ **THE EDIT IS TWO SINGLE-BIT REGISTER-FIELD CHANGES** — `0x37E1→0x37E0` and `0x4001→0x4000`, both `reg1: r1→r0`, opcode and reg2 byte-identical (verified programmatically on the built image). **No cave** ⇒ GATE 1 vacuous, and the kit's only bricking class is avoided. r24's tail traced to zero: `mov 0x0,r6` @`0x3AC22` is the default and both deadzone arms skip. **5 bytes off V59** (2 code + 3 CRC), 88 off V38. ⭐ **CAL CRC unchanged** = machine proof no `0xC6xxx` cal moved; **`0xD2000`-block CRC unchanged** = machine proof V60's falsified blend is absent. Every r24/r26 gain cal (`0xC6440/42/46`, `0xC61F6`, `0xC6444`, `0xC643E`) and V42's `gain_A` Y rows asserted **STOCK**, so this is an independent lane test, not V39/V42 layered underneath. 50/50 CRC, RWD round-trips with every gate re-run on the readback. ⚠ **Expect a manual-feel change** — the rate lanes are a phase-lead term in **base** assist and this chain has no LKAS-only decoupling point. Reversible by reflashing V59. ⚠ V59's probe rides along but is **NOT a null control**: it reads `gp-0x6ba6`, upstream of the edit, so the edit cannot move it *directly* — but a quieter bar moves the index, making it a **secondary readout**. Image SHA `35da8600aa42584d0c5cf35bde8e9a751a0396e66f149f5fd18d07982498e23a`; RWD SHA `dd647870272aaa6342c425d25efb01a13eb540b1bd2c58fbbcbef132139f8a05` |
| ~~V60~~ | V59 + the boost-amplitude BLEND coefficient `0xD2006`: 102 → 43 | 🛑 **FLASHED 2026-07-31 → NULL on the vibration. Do not re-flash.** The discriminator fired and returned the predicted null ⇒ **the parametric pump is CLOSED**, and `0xC63BA` goes with it (the index drives only the boost/damping amplitude LERPs). Original build note kept below for provenance. **BUILT 2026-07-30.** **The intervention that settles whether the 42 Hz pump DRIVES the grinding or merely ECHOES it** — the only discriminator left, since causality is not settleable observationally and `eps_crit = 2/Q` needs a passive Q that V59 cannot measure. **5 bytes off V59**: one cal byte + the `[0xD2000,0xD2FFC)` block CRC. ⭐ **MAIN CRC and CAL CRC both UNCHANGED** = machine proof the cave/probe did not move and no `0xC6xxx` calibration moved. 91 bytes off V38. Q10 0.0996 → 0.0420; 42 Hz transmission ~0.37 → ~0.17; tau 10.0 → 23.8 ms @1 kHz. Predicted eps p99 **0.169 → 0.099**. 🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so this lever buys ~1.7× and then flattens (cal 32 only reaches 0.086); 43 is the knee. **GATE 1 vacuous** (calibration halfword, no code, no RAM). **GATE 2 is the argument**: base-assist path, no LKAS-only decoupling point exists in this chain — but it is a pure *dynamics* change on a gain-**scheduling** variable, adds no gain, moves no static map, cannot change any steady-state value, and tau stays <50 ms worst case. Blast radius byte-verified: mode 10's cell is private (modes 11/12 have their own). **V59's probe is UNCHANGED and is the CONTROL** — it reads `gp-0x6ba6`, *upstream* of the blend, so the index distribution must return statistically identical (76.9/18.5/4.6/0.04). 50/50 CRC, RWD round-trips. Image SHA `6328cff064598cac8d9a7a4147626c8b55ddbad2e586ac3e1b8fca9c9459be5c`; RWD SHA `519aaab4908844d6a240d48f50d8a523b39353a3a4e3bffeb3de4bb4e1d19787` |
| **V59** | V58 + cave payload replaced by the **boost-index DEPTH probe** | ✅ **BUILT 2026-07-30, UNFLASHED.** `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense is "index < T", which is what lets the whole cave run on the two pinned condition codes). **19 bytes off V58** (cave + MAIN CRC only; **CAL CRC unchanged** = machine proof no calibration moved), 86 off V38. Same base `0xC4B34`/hook `0x55C0E`/68-byte extent as V55/V57/V58, all flown clean. **No new encoder, no new condition code.** 50/50 CRC, RWD round-trip, cave re-disassembled from the built image; the build also asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic rather than reporting on a surviving subset). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| **V55** | the pre-V56 revert target | ✅ built, driven, fault-free. SHA `2b0fbd61e6658726ea72248f5312f4521638acaebcbd6f09d8c999e1a9e81fbf` |
| ~~V56~~ | the `0xC6AF0` mute | 🛑 **FLASHED AND FALSIFIED.** Do not re-flash |
| ~~V57~~ | the `0xC646C` decoupling + deadband probe | ✅ flashed, fault-free; its calibration is carried by V58 |

🛑 **Flash only on explicit operator instruction naming the file and the bus.** Kill openpilot/pandad first.

---

## 🛑 METHODOLOGY — three conventions that were producing wrong answers

These invalidate *reasoning* behind earlier conclusions. None changes a measured on-car outcome, but
every historical amplitude comparison needs rebuilding before it can be trusted.

1. **`carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG engagement proxy.**
   It reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot
   routes where lateral was demonstrably applying. On route 28 it reads 84.0% while lateral applied 49.9%.
   **Use `carControl.latActive`, corroborated by CAN `0x18F` byte4 bit3 (`STEER_CONTROL_ACTIVE`).** The
   three agree to **99.85–99.94%**. Using cruiseState flipped V57's headline verdict from INERT to
   NOT INERT, and inflates V56's creep baseline **28×** by sweeping in hands-on parking manoeuvres at
   |ang| 89.6°.
2. **Hands-off must be SUSTAINED effort `|lowpass(tq, 3 Hz)| ≤ 200`, never raw `|tq| ≤ 200`.**
   The oscillation is ±1400 counts *on the torsion-bar channel itself*, so it trips the raw test by
   itself: 68.3% of frames scored "hands-on" have the driver doing nothing sustained. On genuinely quiet
   frames the raw test **keeps** 390 frames with oscillation rms 103.5 and **drops** 746 with rms 909.2 —
   **8.79× the amplitude.** It selects *against* the phenomenon. Switching recovers 2.5× more usable
   frames and turns subsets that had no contiguous run into computable numbers.
3. **Mean Welch power is the wrong statistic for a bursty limit cycle — use peak/p99 envelope.**
   V57/V55 grinding: median 0.419 but **p99 0.891, max 0.898**. The "halving" lived entirely in the
   median, which is dominated by quiet time between bursts. Operator called this before the data did.

✅ **A fourth problem, SOLVED 2026-07-30 by route `2b`:** engagement and motion used to be collinear —
no speed bin on any route had ≥3 windows in both arms, so the recorded ratios (877×, 786×, 14,750×,
27.7×) were moving-vs-stopped contrasts wearing an engagement label. **Route `2b` breaks it**: seg 13 is
60 s of *moving but disengaged* at 0.5–4.8 m/s against engaged creep at overlapping speeds, giving 3 of
9 speed bins with windows in both arms (18 v 18 windows, but only ~10 independent episodes per arm —
treat n as episodes, not windows). ⇒ **13.4× amplitude [95% 3.9–19.8], 16.9× speed+effort-matched.**
🛑 The old ratios stay retired; **do not resurrect 877×/786×/14,750×** — they were never engagement
contrasts. Quote the route-`2b` numbers, or absolute engaged powers.

⚠ **A fifth convention, learned the hard way this session: use a STRICT 18–26 Hz band plus a presence
test, never a wider search band.** A 15–30 Hz or 17–28 Hz argmax catches the ratchet's 2nd harmonic
(2×8.0–8.9 Hz = 16–17.8 Hz) at road speed and steps down to ~15 Hz, manufacturing a *negative* frequency
slope out of a mode switch. Two independent analysts produced two contradictory "frequency laws" this way
before the band was tightened.

⚠ **A sixth: prominence, not envelope amplitude, is what separates a mode from broadband.** The
disengaged arm's loudest 18–26 Hz moments are single-digit prominence at |ang| up to 295° — a driver
cranking a wheel. An envelope-ratio headline divides one broadband spike by another; the prominence
contrast (34× grinding vs 6.1× ratchet) and the presence/absence are the defensible statistics.

---

## Signal-identity corrections of record

- 🛑★★ **`gp-0x6ba6 == |gp-0x6b9a|`, and `gp-0x6ba6` — not `gp-0x6b9a` — is the boost amplitude index.**
  Byte-verified 2026-07-30; **`build_v58_tva.py`'s docstring was wrong on both counts** and is corrected
  in place. `FUN_0003b66a` writes both from the same r28 (`cmp r0,r28 / mov r28,r13 / bge / subr r0,r13`
  @`0x3b874-87c`, then `st.h` @`0x3b892` and `@0x3b8b0`; byte-scanned for **both** gp-relative encodings:
  exactly one writer each). `gp-0x6b9a`'s only live consumer in `FUN_00034a72` is a **five-input
  plausibility gate** (`|x| ≤ 25600` @`0x34c9c-cb4`, ANDed with `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/
  `gp-0x6c2e` into r21, which zeroes r24 @`0x34fc8`) — **its sign has no effect on the output**, and two
  of its three reads there (`0x34b5e`, `0x34b68`) are **dead** (`tp+0x7499 = 1` takes the branch
  @`0x34b3c`). **`0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`** (which resolves to
  `0xD2888`); resolved from image bytes across all 34 modes.
  ⇒ **THE MECHANISM:** V58 measured the *signed* sibling crossing zero at 20.93 Hz only when LKAS
  applies, so the index is that signal **full-wave rectified** — a minimum at every zero crossing,
  sweeping the boost amplitude curve (`0xD28DC` Y = 16384→8187, `0xD2888` Y = 16384→8176) at **~2× the
  mode frequency on the BASE ASSIST path**. ⚠ **INFERENCE, depth unmeasured**: a sign bit carries no
  amplitude, and the delivered swing depends on how far up the curve the index climbs —
  `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert"
  below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero.
  **V59 measures which regime. Do not move `0xD28DC`/`0xD2888` until it has flown.**
- ⚠ **`FUN_0003b66a` branch A is NOT a biquad** — a subagent claimed "a genuine floating-point 2-pole
  biquad, IIR by definition"; it is not. `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** It is the identity 3-tap FIR already on record, so **"no biquad
  anywhere" survives and there is no new notch candidate.** Also new: `tp+0x74be = 0` (`0xC64BE`) makes
  `0x3b736–0x3b758` (the `divf.s` block) dead code.
- ⚠ **`search_instructions` undercounted again** — 8 access sites for `gp-0x6b9a` where a Python byte
  scan finds **9** (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). The sole-writer
  conclusion held, but only because it was re-derived. **Never let a writer/reader set rest on it alone.**

- 🛑★★ **`gp-0x6a56` is NOT independently sensed.** `FUN_0003f776` (sole producer, 4 `st.h`, all inside it):
  `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)` — a fixed Q15 scale of
  the **motor/resolver electrical rate**. The ±12000 is a magnitude clamp recomputed fresh each tick, not a
  rate limit; `gp-0x6a60` merely mirrors its magnitude. ⇒ **`STEER_ANGLE_RATE` is opendbc-named but is not
  an independent angle sensor**, so "996× on rate vs 877× on torque" is two EPS-internal derivations, not
  independent corroboration. And since `gp-0x6bbe`'s `baseline` is **also** `gp-0x6abe`-derived,
  `rate_error = baseline − angle_rate` may partially cancel ⇒ **the damping sign is UNRESOLVED.**
- 🛑 **`FUN_0004613e` is not a rate limiter.** It snapshots params into log cells and calls
  `FUN_00016de6(0x1c,…)`, a fault logger; **`0x3638` (13880) is a diagnostic TAG** (the same callee takes
  `0x38c7` elsewhere). The `gp-0x6bb2/4/6/8` cluster is a cross-tick **integrity watchdog** re-deriving the
  same ±512 ceiling in float, with **no forward path into any control signal**. Golden model corrected.
  ⚠ Its fault path calls `FUN_000462e6(0x39e9,…)` **ungated** — Monitor 2's hard-shutdown chain. Any edit
  to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table `0xD2018` to match, or it may trip.
- 🛑 **`0xC6372`/`0xC636E` is a DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every
  build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. Any
  GATE-2 analysis of those two cals is analysing a lever with zero effect on this firmware.
- **The FIR slots are real but cannot notch.** `FUN_0003b66a` implements a genuine **3-tap transversal FIR**
  (`y[n] = b0·x[n] + b1·x[n−1] + b2·x[n−2]`, two persisted delay states `gp-0x365c`/`gp-0x3658`) — **not a
  2-pole IIR biquad**, so it is unconditionally stable. Coefficients `0xC4018/1C/20` = floats
  **(1.0, 0.0, 0.0)** = identity; a second instance `0xC4048/4C/50` (`FUN_0003b8f6`) is also identity.
  Exactly **one consumer each**. See "closed levers" for why enabling them fails.
- 🛑 **The ±565/cycle slew in `FUN_0003b66a` is a CODE IMMEDIATE** (`mov 0x440d4000,r6` = 565.0f), not a
  calibration. Editing it is a code-patch-class change. The halfword 565 in the cal region
  (`[0,191,402,565,686,804,878]` at `0xCE43C` etc.) is an unrelated LERP entry — numeric coincidence.
- ⚠ **The two `STEER_ANGLE_RATE` copies disagree by a constant 1.25×** (`0x18F[2:4]×−0.1` reads 0.799–0.800
  of `0x14A[2:4]×−1.0`, corr +0.9997). One DBC scale factor is wrong. Frequencies, Q, prominence and ratios
  are unaffected; **absolute deg/s figures are not.**
- 🛑 **`STEER_STATUS` is `0x18F` byte4 bits 7:4**, not bits 2:0 (which are SPARE — never written anywhere in
  the image, boot-zeroed, read 0 forever). Reading bits 2:0 yields a tautological "always 0". Route 29 shows
  `ST==3` in **120 frames**, all at `vEgo == 0.000` exactly, never with LKAS applying, in two episodes
  (1.08 s at log start, 0.10 s at t=77.8 s). **Not a V57 regression** — `0xC62EA` is byte-identical across
  V55/V56/V57. Amends the record's "ST=3 never fires on V53+".
- 🛑 **The "8.69 Hz line V56 introduced" never existed — it is wheel order 1.** V56's 35 windows sat at
  v ≈ 18 m/s where `0.489·v − 0.186 = 8.69`; its own edge windows move to 7.03 and 9.77 Hz, and V57 tracks
  identically (7.03 → 8.98 → 9.38). **Its absence on V57 is NOT evidence the `0xC6AF0` mute was live** — a
  different liveness proof is needed.
- ⚠ **The recorded V56 baseline `7.66e4` is suspect** — within 5% of route 24 seg 0's *all-frames* power,
  and that segment contains **zero** LKAS-applying frames.

---

## ✅ The tyre line — CONFIRMED, firmware-independent, and actionable

Order tracking (rescale each window's frequency axis by its own wheel frequency before pooling) puts
**both** builds at **order 1.000**:

| build | K | v range | order peak | prom | implied circumference |
|---|---|---|---|---|---|
| **V57 / r28** | 9 | 4.2–20.1 m/s | **1.000** | 11.7 | **2.088 m** |
| V56 / r24 | 59 | 9.5–20.5 m/s | **1.000** | 6.2 | **2.088 m** |

Estimator calibrated on V56 first, where the answer was known. Decoys at order 0.70/1.40/1.80/2.00 all
score far below. Per-window on V57's road episode: 2.056–2.105 m, with a 715× prominence burst at
19.5 m/s. A 235/45R18 is 2.05–2.11 m ⇒ **one line per wheel revolution**.

⇒ 🛑 **Get a wheel balance / road-force check.** Firmware cannot move a road input, and it didn't.

★ Separately, a **fixed ~7.4 Hz resonance** is present on V57 (Q 36.2 at nfft=1024, prominence 40–136×) at
1.2 m/s where wheel order is only 0.59 Hz ⇒ **not the tyre**. It is the ratchet. Route 28's creep misses it
because that creep is |ang| 5.8° — **excitation, not absence** (r29 creep is 26.5°, matching the historical
set's 12.6–42.2°).

---

## Recommended next steps, in order

🛑 **NO openpilot-side modifications.** Standing operator instruction. openpilot remains a *measurement
instrument* only.

0. ★★★ **FLASH V62 — the recommended next action.** It is the matched inverse of the one build that
   produced a signed result. `Kd`→0 diverged; `Kd`→2× is the same-sized step back, and the damping
   coefficient is **linear in Kd**, so this is the highest-expected-value experiment on the board.
   **Route:** repeat the V61 route so the comparison is like-for-like — parking-lot creep, deliberate
   LKAS on/off passes at matched speed and angle, **plus the same manual-forward and manual-REVERSE
   passes**. 🛑 **Manual reverse is the highest-information single test**: V61 introduced grinding there
   from nothing, with no LKAS in the loop at all, so it reads the lane's damping with the cleanest
   possible confound structure. Probe unchanged (`rlog-tools/decode_v59_boostindex.py`) — secondary
   readout only, since `gp-0x6ba6` is upstream of the edit.
   **Interpretation set in advance, so it cannot drift:**
   - **BETTER** ⇒ the lane is the damper, the direction is confirmed, and the next question is *how much
     more* (V63 = 4×, or the phase lever below).
   - **NULL** ⇒ the lane's damping is already **phase-limited**, not gain-limited. Then the next lever is
     the lead's **PHASE**, not its gain: **`0xC6C42` (delay D) 4 → 2 halves the differentiator's transport
     lag, 15.1° → 7.6° at 20.9 Hz.** ⚠ Note the earlier objection to D — "it is half a lockstep pair" —
     is **RETRACTED**: `0xC6C42` has exactly one reader (`FUN_0007e74a`) and D feeds a single computation
     broadcast to both cells in sync. The real caveat is that D sets the differentiator's time window and
     its response at other D is uncharacterised. Characterise it before building.
   - **WORSE** ⇒ the lead has gone past optimum into noise amplification; back off to 1.5× rather than
     abandoning the lane.
1. **Analyse the V61 rlog, route `00000031--0441e00d2b`** (4 segments). Not blocking V62, but it is the
   only quantitative record of a *signed* change and it answers two things nothing else can: whether the
   newly-appearing **manual/reverse** line sits at the **same ~20.9 Hz and Q** as the engaged grinding
   (⇒ same mode, unmasked) or elsewhere (⇒ a different finding, and V62's rationale needs revisiting),
   and whether **`ST==4`** stayed at 0. Use the strict 18–26 Hz band + presence test, `latActive`,
   sustained-effort hands-off, and peak-frequency **scatter** as the mode-vs-floor discriminator.
2. 🛑🛑 **RESOLVED 2026-07-31 — AND THE ANSWER WAS THAT THERE WAS NEVER A NUMBER. V52C DID NOT HALVE
   ANYTHING.** This step used to read "re-derive V52C's halving under the corrected statistics; the
   rlogs exist." **Both halves of that were false.**
   - **"Halved the mode" is the FILTER'S OWN TRANSFER FUNCTION, relabelled as an on-car result.**
     V52C's EMA at α = 74/1024, fs = 1 kHz, gives `|H(20.9 Hz)| = 0.4963` = **−6.08 dB**. −6.1 dB **is**
     0.496× **is** "halved". The two figures in the record are the same statement written twice.
     Independently recomputed 2026-07-31 in `analysis-2020accord/eps_feedback_path_coverage.py`.
   - **Textual lineage, git-traced.** The phrase was born in `f0adb24`
     (`HANDOFF-2026-07-28-v55-...md:205`) as a **caveat explaining why V52C's NULL is weak evidence**:
     *"⚠ V52C's null is weak — only −6.1 dB at 21 Hz while adding 61° of lag. It halved the mode's
     content; it did not remove it."* By `59acdd2` (the V59 handoff) it had become *"halved the mode —
     the largest single effect any build has had"* and the word **null had vanished**.
   - **Every contemporaneous on-car record says NULL, including the operator's own words:**
     `HANDOFF-2026-07-26-route13-...md:8` — *"V52C did not fix the vibration; it clearly changed manual
     feel."* `ARCHIVE-CLAUDE-MD-2026-07-27.md:56` — *"V52C's null is MEANINGFUL: −6.1 dB at 20.9 Hz, so
     it WAS a fair test of the `gp-0x4f60` lane ⇒ real evidence AGAINST that lane."*
   - **There are no V52C rlogs and there never were.** Routes on disk: `13,1a,1b,1c,24,28,29,2b,2c`.
     The V52C window (`08`–`12`) is absent from the whole machine and was never in git.
   ⇒ **The loop hypothesis loses its retrodiction entirely.** It now rests only on the two things that
   were actually measured: the **21.09 Hz command→torsion-bar transfer peak** (global max over 3–46 Hz)
   and the **traced absence of any motor-command feedforward**. Both stand.
   ⚠ This does **not** falsify the loop: a 2× gain cut that also adds ~57–61° of lag is a poor
   stabiliser, so a null is what a real loop with <6 dB gain margin would also produce. V52C is
   **weak-to-moderate evidence against the `gp-0x4f60` VALUE path**, not against the loop.
2b. ~~**Flash V60 as a DISCRIMINATOR**~~ — ✅ **DONE 2026-07-31, null, pump closed.** Kept for provenance:
   It attacks the
   *pump*, and the pump now looks like a passenger. **A null is the informative outcome**: it would
   close the parametric mechanism this kit spent V58/V59/V60 on and leave the loop standing.
   **Route:** parking-lot creep **v ≤ 5 m/s**, LKAS applying, **sustained hands-off ≥ 3 s**
   (`|lowpass(tq,3Hz)| ≤ 200`), deliberate LKAS on/off passes at matched speed and angle, plus a pass
   at the **10–13 m/s under-load** population. Decode with `rlog-tools/decode_v59_boostindex.py` — the
   probe is **unchanged and is the CONTROL**: the index distribution must return statistically
   identical to V59 (76.9 / 18.5 / 4.6 / 0.04 at engaged+creep+hands-off). If the index matches and the
   grinding moved, the blend is the only thing that did.
3. 🛑 **Sizing any loop fix needs the phase margin, and the bus cannot give it.** One 100 Hz mailbox
   sample is **~76° at 21 Hz** — larger than any phase worth reading. Establishing loop phase needs a
   **firmware-side probe** (a V59-class thermometer on a signal that crosses zero at 21 Hz), not more
   rlog analysis. Until then, any gain reduction is empirical and iterative.
4. ⚠ **Base-assist loop gain (`0xCA154[mode]` → `0xD2834`, speed-keyed) is the untested handle** — and
   it is a **direct trade against steering weight**, so it is an operator decision, not an analyst's.
   Grep it and state its history before proposing it. The amplitude curves `0xD28DC`/`0xD2888` and
   `0xC63BA` are the other in-loop knobs; all sit on base assist, none has an LKAS-only decoupling
   point (traced and confirmed — unlike V57's `0xC646C`, this chain has no fork).
5. **Re-run the strict-band (18–26 Hz + presence test) analysis over the V55/V56/V57 routes.** Route 2c
   independently rejected `a = 0.177` (2.60σ presence-tested, up to 7.08σ raw) and its fitted subset is
   **confound-free** (`spearman(v,|ang|) = +0.068` vs 2b's −0.728), so the fixed ~20.9 Hz line is now
   the record — but the historical amplitude baselines still need re-deriving on lateral engagement +
   sustained-effort hands-off + envelope statistics. Treat `7.66e4` as provisional.
6. ★ **The ratchet: route `2c` HAS clean episodes, and the record says it shouldn't.** 7.56 ± 0.36 Hz,
   within-run sd 0.07–0.10 Hz, prominence median **783×** (max 2142×), **15 windows / 5 runs**,
   hands-off + engaged + creep, at both 9–15° and 133°. `STATE.md` previously recorded that route 2b
   gave **zero** and that a dedicated comma-commanded route would be required. **Mode identity
   unconfirmed** — this was found incidentally by an analyst outside its brief. Verify before building
   on it.
7. **The ratchet still has no cal lever and no mechanism.** All rate-limit candidates are closed (see
   `BUILD-LINEAGE.md`). Next step is measurement, not a build. The return-centre lane `gp-0x6b62`
   (aggregator, ZERO-gated ±0x2000) has never been probed and is the operator's own hypothesis.
   🛑 **Route `2b` cannot speak to the ratchet in either direction, and the operator said so before the
   data did.** Hands-off + engaged + `|e4tq| ≥ 3500` + v ≤ 3.0 m/s yields **9 runs / 139 frames (~1.4 s)**,
   all inside one 8 s window in seg 1 that overlaps a hands-on manoeuvre sweeping −24° → +302° — i.e.
   transient zero-crossings of the lowpassed effort signal *during* hands-on driving. **Zero clean
   episodes.** The driver-applied sharp turns don't show it either: 6–9 Hz sits at or below a strict
   quiet baseline in 8 of 11 long episodes, with the 5–10 Hz peak wandering 5.3–9.9 Hz rather than
   locking at 7.4 Hz with Q≈36. **A dedicated comma-commanded route is required.**
8. 🛑 **Do NOT move `0xD28DC`, `0xD2888`, or `tp+0x73ba` (`0xC63BA` = 512).** All sit on the **base
   assist** path with no LKAS-only decoupling point, so they change manual feel and all need GATE 2.
   ⚠ `0xC63BA` is **partial by construction**: byte-verified as a 2-stage EMA (α = 0.5 both stages,
   blast radius fully contained — 2 reads, both in `FUN_0003b66a`), but it filters only the **torque**
   lane, and the index is a **sum** of that and a **resolver-rate-derivative** lane (`gp-0x6abc`, via
   `FUN_00041464` ← `FUN_00068f52`'s angle-delta differentiator). It cannot touch the second lane.
9. **Re-derive the V31 boost-floor margin** (`0xC67D8`, `0xC61B4`) — the recorded arithmetic does not
   reconcile with the image. Not blocking; V54 measured the margin directly.
6. **The take-over beep is closed** — `commIssue`/`selfdrivedLagging` under device CPU load, clean CAN/EPS
   null. Seen again on both V57 routes (route 28's at t=126.5 s produced a real soft-disable).

🛑 **Do NOT re-drive at road speed merely to "see if authority moves."** `gp-0x6966` is wind-up-driven, not
speed-driven, and V31's boost floor makes wind-up unreachable (V54 measured this on-car under railed
command).

---

## Still-standing results worth not re-deriving

- **`gp-0x6966` authority ≡ 0 by design on V31+** — soft-EME wind-up magnitude, pinned by V31's boost
  floor; `0xC6AF0` selects unity in 100% of normal operation. Measured on-car, route `1b`, 5,989/5,989.
- **Steer-to-zero works** — `0xC62EA` = 0, `ST=3` never fires while moving, 226 frames of
  `STEER_CONTROL_ACTIVE=1` below 5 km/h on route `1a`.
- **The `0x14A` byte4 bits 7:3 piggyback is proven across FOUR flashes** (V54, V55, V56, V57). Use it for
  all future firmware telemetry; **do not build another new-mailbox channel** (FOURFRAME2 was never
  transmitted — that null remains uninterpretable).
- **No notch/biquad exists anywhere** on the arb, aggregator, r24/r26, comp-add, boost/damping/friction,
  shaper, or governor paths, nor in the three non-aggregator consumers of `gp-0x6b94`
  (`FUN_0004503c` governor, `FUN_0004595a` redundancy monitor, `FUN_0007ff08` boot interlock). Two regions
  remain unswept: the raw CAN → `gp-0x4f60` producer, and the FOC current loop below `gp-0x6b98`.
- **An rlog cannot identify the flashed build from the version string** — every build reports
  `fw='39990-TVA,A160'`. Behaviourally: `ST=3` never firing while moving ⇒ V53+; probe field semantics
  identify V54/V55/V56/V57/V58 exactly.
