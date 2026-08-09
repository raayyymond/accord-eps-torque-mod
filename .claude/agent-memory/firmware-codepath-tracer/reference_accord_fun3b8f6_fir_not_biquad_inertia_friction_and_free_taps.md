---
name: reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps
description: Full instruction-level decode of FUN_0003b8f6 (Path 2's entry point) -- the "biquad" is a dead 3-tap FIR (no poles, identity coeffs on every build), a real FRICTION relay and a small phase-rotated INERTIA term both live inside it, and gp-0x6c00/6ae0/6ae2/695c are confirmed 0-reader/1-writer free telemetry taps. Closes the open item in reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing.md.
metadata:
  type: reference
---

# FUN_0003b8f6 fully decoded (2026-08-09, V85 session, `fw-plantmodel` task)

Entry: `0x3b8f6`, called ONLY from `FUN_0002214a` (1 kHz dispatcher) at `0x2240e`, same gate register
(`r28`) as `FUN_0003b66a`/`FUN_0003bc20`/`FUN_00041d56`/`FUN_00040e7e` -- CONFIRMED 1 kHz, unconditional.
This is the function my own prior memory
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]] flagged as its own open
item #1 ("FUN_0003b8f6's float cascade... not byte-read"). **Now byte-read and transfer-function'd.**

## 1. The "biquad" is REFUTED as an IIR/resonator -- it is a dead 3-tap FIR

`[EVIDENCE, full disasm 0x3b9d2-0x3ba04]`. Three cal cells, all raw 32-bit FLOATS (`ld.w`, not `ld.hu`):
`tp+0x5048`(=0xC4048), `tp+0x504c`(=0xC404C), `tp+0x5050`(=0xC4050). Two RAM state cells, `gp-0x363c`
(x[n-1]) and `gp-0x3638` (x[n-2]), confirmed BOTH read and written (write sites `0x3b9e6`/`0x3ba04`) --
a genuine 2-deep shift register. Structure:
```
y[n] = c1*x[n] + c2*x[n-1] + c0*x[n-2]     c1=tp+0x5048 c2=tp+0x504c c0=tp+0x5050
```
**No instruction anywhere reads y[n-1]/y[n-2] back as an input.** Zero feedback ⇒ 2 zeros, 0 poles ⇒
CANNOT ring, CANNOT have Q, CANNOT resonate, by construction -- regardless of coefficient values. This is
the single most important structural fact: even a hand-edited version of this block can only ever be a
broad FIR null (a zero), never a Q-having notch.

**Byte-read stock AND V84 (`_v84_LEVERB...` image), identical**: `(c1,c2,c0) = (1.0, 0.0, 0.0)` ⇒ `y=x`
exactly -- **a literal identity pass-through on every build ever made.** `build_v58_tva.py:20` already
called this "the two 3-tap FIR slots (0xC4018/1C/20 and 0xC4048/4C/50)... dead as a lever" -- CORROBORATED.

**Reconciles an apparent conflict, not a real one.** `build_v52c_tva.py`'s comment on `0x3B908`
("its float biquad stage is degenerate in stock cal (coeffs 0.0f), leaving two poles at ~366 Hz each")
is talking about the SAME chain but a different stage: `tp+0x50d8` = 3686/4096 = 0.8999 is the alpha of
the 2-stage EMA that FEEDS the FIR (its input, `x[n]`), and `-fs/(2π)ln(1-alpha)` = **366.3 Hz per pole**
-- exactly their number. Their "coeffs 0.0f" remark is accurate too (2 of the 3 FIR coefficients ARE
0.0f). So the two write-ups describe the same object at different resolution; neither is wrong once
reconciled. `x[n]` = 2-stage EMA(gp-0x4f60/1024, α=3686/4096) × `tp+0x713a`(=0xC613A=1159)/32768 -- and
`0xC613A`=1159 is the SAME cal `build_v68_tva.py` independently confirmed for the `gp-0x6ac0`→bus scale
chain, so it may be a SHARED cal, not private to this function -- **not checked this session, flag for
whoever touches 0xC613A next.**

★★ **ACTIONABLE, not asked for but load-bearing for V85 design**: this FIR sits directly on a
lightly-smoothed copy of the RAW TORQUE SENSOR (`gp-0x4f60`) and is reachable by a **pure 12-byte cal
edit (3 raw floats), no cave**. It CANNOT become a resonant notch (no poles), but it CAN become an
arbitrary FIR-3 null/lead/lag on the torque-sensor branch of Path 2 with zero code risk. Distinct from,
and much cheaper than, the Q≈20 biquad-cave NO-GO in `docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md`
§3.4 -- but also much weaker (FIR-3 has no sharp selectivity). [BELIEF: usefulness for the operator's
actual self-interference goal is NOT evaluated here -- this session only confirms the structure and its
cal-reachability.]

## 2. Enable gate, exact bounds `[EVIDENCE, asm 0x3b8f6-0x3b93e]`
```
|gp-0x6b98| <= 0x2000 (8192)                       -- unsigned-trick range check, exact
-25600 <= gp-0x4f60 <= 25600ish (wide validity)     -- DAT_6400/DAT_c801 offsets
-13000 <= gp-0x6abc < 12969 (wide validity)         -- DAT_32c8/DAT_6591 offsets
gp-0x6752 (polarity) in {-1, 0, 1} exactly
```
On gate fail: `gp-0x6bf6=0x7fff`, `gp-0x6c00=0xffff`, `gp-0x6bfc=0x7fff` (sentinel, same LAB_0003bc16
tail as the success path writes `gp-0x6c00`/`gp-0x6bfc` -- **but `gp-0x6ae0`/`gp-0x6ae2` have exactly ONE
writer each, on the SUCCESS path only** -- they hold stale data across a gate failure, never reset).

## 3. `gp-0x6752` (polarity) is a BOOT-TIME CONSTANT, always +1 in the field `[EVIDENCE]`
`FUN_000490ac` (decompiled): `if (gp-0x6752 == gp-0x4c2d [lockstep shadow]) { gp-0x6752=1; gp-0x4c2d=1; }
else FUN_0006b9fa(...)` [fault handler]. Set ONCE at init via a lockstep self-check, never touched again
in normal operation (52 disp16 hits image-wide, all `ld.b` reads except the 3 stores at
`0x490c0/0x49838/0x49844`, all inside this same init function). ⇒ the two separate polarity
multiplications in FUN_0003b8f6 (cmd path, iVar20 for friction+inertia) **do not cancel and never flip
sign in the field** -- confirmed, not assumed.

## 4. `gp-0x6abc` is a THIRD, independent rate/derivative lane, not the FOC core's `gp-0x6c2c`
`[EVIDENCE, cross-referenced against [[reference_accord_boost_index_input_is_resolver_rate_not_torque]]
and [[reference_accord_below_gp6b98_foc_delivery_path_swept]]]`. All of `gp-0x6ac0`/`gp-0x6abc`/
`gp-0x6abe`/`gp-0x6ac2` share ONE root (`gp-0x4f50`, rotor-speed estimate) and ONE producer
(`FUN_00041464`), but via DIFFERENT per-cell transforms. `gp-0x6c2c` (the FOC core's own acceleration
input) is yet ANOTHER, separately-filtered derivative of the same root (K0=37/128 EMA → diff×32 →
KA=22/64 EMA). **FUN_0003b8f6 takes `gp-0x6abc` (not `gp-0x6c2c`) and differentiates it a THIRD time,
itself** (one-cycle backward difference at 1 kHz, `iVar20[n]-iVar20[n-1]`, `iVar20=polarity*gp-0x6abc*12`).
So the INERTIA term's acceleration estimate is INDEPENDENT of the FOC core's own `gp-0x6c2c` -- three
different filter chains off the same physical sensor, not a reuse.
🛑 `gp-0x6abc`'s exact counts-per-°/s scale is NOT independently confirmed (only sibling `gp-0x6abe` is,
at 4.7121 counts/°/s, per [[reference_accord_gp6abe_column_degps_scale_settled]]) -- used here as a
[BELIEF]-flagged proxy only.

## 5. Full cal dump, tp-relative, BYTE-IDENTICAL stock vs V84 (`_v84_...` image) -- NONE mode-indexed
All are flat `tp` scalars/tables, no pointer-array indirection observed anywhere in this function's
disasm ⇒ **RULE 7 is moot here: editing any of these touches every mode uniformly.**

| name | tp off | abs | stock=V84 | fmt | build_v*_tva.py touch? |
|---|---|---|---|---|---|
| FIR c1 (x[n]) | 0x5048 | 0xC4048 | 1.0 | f32 | mentioned (rationale only) V58/59/64/65/66/67, never WRITTEN |
| FIR c2 (x[n-1]) | 0x504c | 0xC404C | 0.0 | f32 | same, never written |
| FIR c0 (x[n-2]) | 0x5050 | 0xC4050 | 0.0 | f32 | same, never written |
| sensor pre-scale | 0x713a | 0xC613A | 1159 | u16/Q15 | referenced (read-only) build_v68 |
| cmd IIR2 alpha | 0x50d4 | 0xC40D4 | 573 | u16/Q12 | none found |
| sens IIR2 alpha | 0x50d8 | 0xC40D8 | 3686 | u16/Q12 | none found |
| friction IIR alpha | 0x50d0 | 0xC40D0 | 408 | u16/Q12 | none found |
| friction scale | 0x50d2 | 0xC40D2 | 102 | u16/Q10 | none found |
| **friction const** | **0x5080** | **0xC4080** | **0** | u16/Q10 | none found -- ⚠ CORRECTS the session brief's guess of `tp+0x507c`/`0xC407C`; true addr is `+4`, **only 2 bytes from the `0xC407E` hard-fault interlock** (even closer than guessed) |
| inertia IIR2 alpha | 0x50d6 | 0xC40D6 | 246 | u16/Q12 | none found |
| **inertia gain** | **0x746e** | **0xC646E** | **1428** | u16, scale 2^-24 | none found -- untouched by any build ever |
| output scale | 0x7468 | 0xC6468 | 2639 | u16 | none by this function; SAME cal read by Path-2 stage-1 (`FUN_00038148`, per prior memory) |
| ratio normalizer | 0x50bc | 0xC40BC | 600 | u16 | none found |
| angle-err LERP X[0..12] | 0x7b66-0x7b7e | 0xC6B66-0xC6B7E | [0,340,640,850,1000,1200,1400,1576,1736,1916,2084,2280,4776] | u16×13 | none found |
| angle-err LERP Y[0..12] | 0x7b80-0x7b98 | 0xC6B80-0xC6B98 | [899,908,981,1060,1083,1084×8] | u16×13 | none found |

⚠ **The angle-error LERP is NOT flat-unity** (Y ranges 899-1084, i.e. ~0.878-1.059× — a mild ±9%
modulator, saturating by ~10° of tracking error), and its X breakpoints (0,34,64,85,100,120,140,...°)
do **not** match the `[0,50,100,150,700]`-count breakpoints my system-prompt index attributes to
"FactorD" — **this table is structurally distinct from FactorD** (own address block, own shape, own
gate at the identical `0x2711` overflow rail though) despite sharing the SAME index variable
(`gp-0x6a10`). [BELIEF: not fully reconciled against the FactorD memory file, which I could not load
verbatim this session — flag for whoever owns that memory to cross-check.]

## 6. Transfer functions, exact DT math, fs=1000 Hz (script:
`analysis-2020accord/` ad hoc, not saved -- reproduce from the cal table above + the formulas below)

- **FIR: H=1, 0 dB, 0° at every frequency, unconditionally** (structure, not cal-dependent for the
  "no poles" half of the claim).
- **cmd_f** (2-stage EMA, α=573/4096=0.13989): DC gain 1/1024; single-pole corner ≈24.0 Hz/pole (×2
  cascaded). At 21.09 Hz: |H|=0.000552×(gp-0x6b98 amplitude), phase −75.25°.
- **sens branch** (2-stage EMA α=3686/4096=0.8999, ×1159/32768 prescale, ×identity FIR): single-pole
  corner ≈366 Hz/pole -- effectively all-pass in-band (phase only −1.68° at 21 Hz). Its own `±15` clamp
  needs `gp-0x4f60` ≈ 441,000 counts to reach -- **UNREACHABLE**, the validity gate caps `gp-0x4f60` at
  ±25600, i.e. this clamp uses at most **5.8%** of its range. Not a relay, wildly oversized.
- **INERTIA** (backward-diff × 8.7266 × 2-stage EMA α=246/4096=0.060059 × gain 1428×2⁻²⁴): per-pole
  corner ≈9.9 Hz -- the SLOWEST filter in the function, meaningful lag already by grind-#1's band.
  Net transfer, magnitude (unclamped INERTIA per 1 raw count of `gp-0x6abc` amplitude) and phase RELATIVE
  TO RATE (not acceleration):

  | band | \|H\| | phase vs rate | phase vs accel (−90°) |
  |---|---|---|---|
  | 7.79 Hz (S2) | 0.000269 | **+14.7°** | −75.3° |
  | 21.09 Hz (S1) | 0.000212 | **−36.2°** | −126.2° |
  | 27.4 Hz (ring lo) | 0.000176 | **−45.6°** | −135.6° |
  | 28.5 Hz (ring hi) | 0.000171 | **−46.8°** | −136.8° |

  **⇒ Real part vs rate stays POSITIVE across the ENTIRE 7.79-28.5 Hz symptom band (phase never exceeds
  ±90° from rate)**, i.e. **this term is functionally a LAGGED VELOCITY DAMPER, not inertia
  compensation** (a true inertia-comp term would sit near 0° vs ACCELERATION, i.e. −90° vs rate; instead
  it sits within +15°/−47° of rate, i.e. resembles damping with growing lag as frequency rises). It never
  inverts (never crosses ±90° vs rate) at any of the four bands checked, so **raising `0xC646E` is, on
  this evidence, damping-consistent everywhere checked, not destabilizing by sign** -- though see §7 on
  loop membership before treating that as "safe to raise."

## 7. FRICTION collapses to a hard SIGN RELAY under any realistic amplitude `[EVIDENCE + BELIEF proxy]`
`ratio = clamp(polarity*gp-0x6abc*12/600, -1, 1)` saturates at only **50 raw counts** of `gp-0x6abc`
(≈10.6°/s at the BELIEF-proxy scale) -- far below any real column motion. `friction_const`(tp+0x5080)=0
on every build ⇒ `FRICTION = clamp(IIR(sign(polarity*rate)*|model|*102/1024, α=408/4096≈16.7Hz corner),
±10)`. **Entering as `model − FRICTION`, subtracting a term proportional to `sign(rate)*|model|` REDUCES
the delivered command whenever rate and model share a sign** -- i.e. it opposes ongoing motion in
proportion to the command driving it. This is structurally a genuine Coulomb-friction-ADDING term (not
compensation) and is a **previously-uncatalogued candidate contributor to the operator's own S4
("excess friction/impedance under max command")**, separate from the already-characterized friction lane
`FUN_00036c12`/`gp-0x6b26`. [BELIEF: contribution size not quantified against the known friction lane's
magnitude this session -- would need `|model|`'s typical amplitude, not derived here.]

## 8. Clamp/headroom summary, physical-estimate chain flagged [BELIEF]
Using the brief's own recipe (column angle p-p 1.29-1.92°, rate scale 4.7121 counts/°/s BELIEF-proxied
onto `gp-0x6abc`): INERTIA reaches only **0.4-1.3%** of its ±10 clamp at 7.79/21.09 Hz. Cross-checked
against V68's independently-measured sibling-cell (`gp-0x6ac0`) amplitude distribution (p99≈843,
MAX≈2219 counts, surviving-chain figures) -- even at MAX, INERTIA reaches only **~4.7-6.0%** of its
clamp. **⇒ INERTIA is NOT a relay under any plausible operating point -- unlike V80's damper, it never
approaches saturation.** FRICTION's *ratio* nonlinearity, by contrast, IS effectively always saturated
(§7) -- but that saturates a SIGN selector, not the ±10 magnitude clamp itself, which was not separately
sized this session.

## 9. Consumer census -- `gp-0x6c00`/`gp-0x6ae0`/`gp-0x6ae2`/`gp-0x695c` are CONFIRMED free taps
`[EVIDENCE, scan_gp_accesses.py (validated disp16+ext23 scanner) + independent LE32-literal pointer-table
check, all three methods agree, stock code.bin; FUN_0003b8f6/FUN_0003bc20 code region byte-identical
stock vs V84]`:

| cell | writers | readers | note |
|---|---|---|---|
| `gp-0x6bfc` | 1 (`0x3bc1a`, this fn) | 1 (`0x3bc20`, `FUN_0003bc20`, first insn) | NOT free -- consumed |
| `gp-0x6c00` | 1 (`0x3bc16`) | **0** | FREE TAP -- written every tick (pass or fail) |
| `gp-0x6ae0` (INERTIA×1024) | 1 (`0x3bc00`) | **0** | FREE TAP -- success-path only, stale on gate-fail |
| `gp-0x6ae2` (FRICTION×1024) | 1 (`0x3bc04`) | **0** | FREE TAP -- success-path only, stale on gate-fail |
| `gp-0x6bf6` (model×2639, dead) | 2 (`0x3bac0`,`0x3bc0e`) | **0** | already known dead, re-confirmed |
| `gp-0x695c` (bonus, `FUN_0003bc20`'s "valid" flag) | 1 (`0x3bc42`) | **0** | FREE TAP, not asked for, found for free |

Zero LE32-literal pointer-table references to any of these six absolute addresses either (ruled out
indirect/table access as a 4th method). `gp-0x6abc` (18 disp16 hits, 14 loads/4 stores) and `gp-0x6752`
(52 disp16 hits) are widely shared, consistent with and extending prior censuses -- not re-litigated here
beyond confirming FUN_0003b8f6's own hit (`0x3b91c` for 6abc, `0x3b92e` for 6752) matches exactly.

## 10. Loop-membership warning for anyone pricing `0xC646E`/`0xC4080`/`0xC40D6` as a "lever"
`[EVIDENCE via cross-reference to [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]]`
`gp-0x6bfc` (this function's main output) feeds `FUN_0003bc20`→`gp-0x6bfe`→`FUN_00038148` stage 2, which
DIFFERENCES it against the `gp-0x6bd0`-weighted stage-1 composite (that composite is divided by 16
(`>>4`) before the subtraction, while `gp-0x6bfe` enters at full weight) → `gp-0x6b70` →
`FUN_00037fe6`→`gp-0x6ad6`→PID `FUN_0003a382`→aggregator→governor→**`gp-0x6b98`, closing the loop this
same function reads at its own top.** **⇒ FUN_0003b8f6's `gp-0x6b98`-direct term appears roughly an
order of magnitude LESS diluted into Path 2's actual error signal than `gp-0x6bd0`'s own (the one term
this kit's `0xC63A0` lever has ever touched)** [BELIEF: dilution ratio argued structurally from the `>>4`
vs full-weight entry, not independently re-verified against fresh Stage-2 disasm this session -- the
prior memory's Stage-2 description is trusted, not re-derived]. **Any edit to `tp+0x746e`/`tp+0x5080`/
`tp+0x50d6` is therefore a Path-2 LOOP-GAIN edit, not an isolated feedforward tweak, and needs GATE 2
(magnitude AND phase across the WHOLE loop) before flying, exactly like any other Path-2 change.**

## Open items
1. `0xC613A`=1159 may be a SHARED cal with the `gp-0x6ac0`→bus-scale chain (`build_v68_tva.py`) -- not
   confirmed this session; check before editing it for either purpose.
2. Angle-error LERP table (§5) vs "FactorD" reconciliation -- not resolved, needs the FactorD memory
   file read verbatim.
3. `gp-0x6abc`'s exact counts-per-°/s scale is unconfirmed (only sibling `gp-0x6abe` is pinned) -- every
   physical-amplitude number in §6/§8 inherits this uncertainty.
4. FRICTION's ±10 clamp reachability (as opposed to its ratio-relay) was not sized against a measured
   `|model|` amplitude this session.
5. Path-2 dilution ratio (§10) is argued structurally, not computed from a fresh Stage-2 disasm this
   session -- next step if this becomes decision-bearing: re-disassemble `FUN_00038148` stage 2 fresh
   and compute the actual number.

## Fills a gap the 2026-07-20/21 negative-result search explicitly flagged
[[reference_accord_notch_biquad_search_negative_result]] named "the FOC/motor-current-loop functions
downstream of `gp-0x6b98`" as an unchecked region and "the natural next place to look." `FUN_0003b8f6`
reads `gp-0x6b98` directly and IS that region. Result: **the first genuine "two delayed states,
cross-multiplied coefficients" shape found anywhere in this kit's search** (x[n-1]/x[n-2], c1/c2/c0) --
but it has NO feedback term (no y[n-1]/y[n-2] read anywhere), so it is an FIR, not the biquad/IIR shape
that search was looking for, and its coefficients are identity on every build ⇒ **the negative result is
EXTENDED, not overturned, but for a more precise reason than "no two-state structure exists" — one does,
it just cannot resonate and is presently inert.**

Related: [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]],
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]],
[[reference_accord_below_gp6b98_foc_delivery_path_swept]], [[reference_accord_gp6b4c_lane_chain]],
[[reference_accord_notch_biquad_search_negative_result]].
