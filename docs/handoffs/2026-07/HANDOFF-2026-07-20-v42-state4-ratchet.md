# HANDOFF — 2026-07-20 — V42: the state-4 governor ratchet, and the vibration reframed

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V42 is **BUILT and independently VERIFIED, NOT FLASHED.** It now carries TWO changes — see below. No CAN, UDS, or flash operation occurred.
**Supersedes:** the V40/V41 root-cause narrative in `HANDOFF-2026-07-19-v40-*` and `handoffs/2026-07/HANDOFF-2026-07-20-v41-ratecap-flat.md`.

## Road results that opened this session

| Build | Result |
|---|---|
| V39 | flashed → fixed neither symptom |
| V40 | flashed → **EPS lamp + power steering fully disabled at ignition** |
| V41 | flashed → **boots and drives cleanly, fixed neither symptom** |

V41 contains V40's **entire** cap-flatten edit and boots fine ⇒ V41 is a clean subtractive experiment.
**The motor-rate cap is falsified as a root cause, and V40's fault is attributable to the slew write.**

## Corrections of record

1. **`0xFFFF` on `0xC6206`/`0xC6208` was NOT a sign or overflow bug.** Both load `ld.hu` (unsigned) at
   `0x45410`/`0x45416`; the Q15 multiplicand is literal-seeded `0x8000` and combined MIN-only, so it is
   provably ≤ 32768; `65535 × 32768 < 0x80000000`; and the slew guard is self-bounded so nothing wraps.
   What `0xFFFF` actually did was make the guard **never fire** → snap-to-target → rate limiting removed.
   Inferred fault path: unfiltered command → `FUN_0004595a`/`FUN_00045a20` → `FUN_00016de6(0x1d)`,
   hard-fault-eligible with **no debounce** → motor off. **The defect was the magnitude, not the direction.**

2. **The "16-phase duty cycle" reading of `andi 0xd30,r25` is RETRACTED.** `r25 = 1 << (gp-0x67fa & 0xf)`
   and `gp-0x67fa` is the **ECU state-machine byte**, so those masks select *states*, not tick phases.
   Every Hz figure derived from a 4/16 or 5/16 duty cycle is invalid. The task rate is now **unresolved**
   (`w_steer_control_task` has zero direct callers; its TCB table at `0xbb8c0` has no located walker),
   so cycle counts **cannot** currently be converted to Hz.

3. **The sign-crossing reset does not explain a small-command vibration.** After a reset the output is
   capped to ±step from zero, so when |target| < step the target passes through unchanged.

## The analytical tool that reorganised the session

The operator had **correctly quartered openpilot's PID** (kp 0.6→0.15, ki 0.18→0.045) to match V38's 4× gain.
Following the units through `C → setpoint = C×−4 → lane = (setpoint × gain) >> 15`:

- for the **same physical torque**, the comma sends C/4 and the gain multiplies by 4 ⇒ **every stage
  downstream of the gain replays stock's exact count sequence**;
- but the **setpoint is 4× smaller** ⇒ everything **upstream** of the gain operates 4× closer to zero;
- the one downstream exception is torque **above stock's 417-count ceiling** — genuinely new territory.

⇒ **Ratchet** (large command, >417) must be downstream. **Vibration** (small command, inside stock's range)
cannot be downstream. This **retro-explains V39 and V41**: both targeted the vibration, both were downstream,
neither could ever have moved it. Implemented as `gain_rescaling_invariance_analysis()`.

## V42 — what it fixes

`FUN_0004503c` holds a substitution branch active while `gp-0x67fa == 4`:

```
0x454f8  ld.bu -0x67fa[gp],r12
0x454fc  cmp   0x4,r12
0x454fe  bne   0x455c4          ; not state 4 -> accept the fresh value
...      |fresh gp-0x6ace| vs |previous gp-0x138a|, ABS+clamped, unsigned bnh
0x455cc  st.h  r6,-0x138a[gp]   ; UNCONDITIONAL writeback
```

While state 4 the command **magnitude can decrease but never increase**, and the suppressed value becomes
the next cycle's baseline — **cumulative and self-sustaining**. State 4 is **reachable mid-drive**,
non-diagnostically, at `0x19bb0` (5→4 when `gp-0x68ad == 0`) and `0x19e54` (10→4). `gp-0x68ad` is preserved
only while `gp-0x679d == 1` OR (`gp-0x6a5e != 0` AND `gp-0x67f4 == 1`) — nonzero voted column torque AND
converged plausibility. A torque zero-crossing or plausibility dropout near sensor saturation trips 5→4 on
the next cycle: exactly a hard, large-angle turn.

**Why only on V38:** the substitution caps the *increase*, so the felt effect is the shortfall
`(demanded − held)`. Stock demanded ≤417; V38 demands 1782 ⇒ ~4× deeper. The mechanism is old.

**No calibration lever exists** — structural, whole-chain walk: all six entry-chain functions contain **zero
`tp+` reads**; the substitution's cals `0xC6134`/`0xC648E` are the *same cells* the primary block and
`FUN_00041464`(16 sites)/`FUN_000456a4` use; and the branch decision reads no cal at all.

## Change 2 — neutralise the `r26` adaptive torque-rate lane (added on operator direction)

V42 also zeroes the `r26` lane's entire gain surface: **18 halfwords**, all inside `[0xC6000,0xC6FFC)`.

| Address | V38 | V42 | What |
|---|---|---|---|
| `0xC6A72` / `0xC6A86` / `0xC6A9A` / `0xC6AAE` | 4 × 4 Y values | `0,0,0,0` each | `gain_A` LERP Y rows, all 4 records |
| `0xC6444` | 512 | 0 | override taken when `gp-0x683c != 0` |
| `0xC643E` | 1536 | 0 | override taken when `assist_state >= 0xC64FA` |

A flat-extrapolated LERP over an all-zero Y row evaluates to 0 everywhere, and the two overrides cover
the non-default gain paths — so `r26 == 0` unconditionally in every reachable state, without touching
`gp-0x69a4`'s producer (shared with the still-live `gp-0x6b86` lane). X rows, counts and terminators are
left stock, as are **all four `r24` cals** (`0xC6440/42/46`, deadzone `0xC61F6`) — asserted, so the two
lanes stay provably independent.

**Why `r26` and not `r24` again.** V39 zeroed `r24` and changed nothing — but `r24` carries a **±3
deadzone** (`0xC61F6`), so it was near-inert at low torque anyway. `r26` has **no deadzone** and is the
only derivative lane live near zero. Decisively, `r26` is a **derivative — a HIGH-pass** — so it passes
exactly the band the arbitration IIR blocks (see below). Both lanes carry the **same sign** (shared
`dtorque` register, single shared polarity load @`0x3ab78`), so this is not removing a counterweight.

⚠ **`r26` is a well-founded hypothesis, not a verified root cause like the state-4 ratchet.** It is the
last mechanism standing after structural elimination, and it fits every on-car constraint — but it has
not been proven. The two changes target **separately observable** symptoms and are **independently
backable-out** (Change 1 = one byte at `0x454FE`; Change 2 = the 18 halfwords), so a null or adverse
result stays attributable.

## ★ The structural finding that put `r26` last-standing: the LKAS lane is a ~1–5 Hz LOW-PASS

The arbitration IIR at `gp-0x3d3c` (`FUN_00028ea6` @`0x2a174`-`0x2a1b0`) is:

```
term1[n] = floor(507 * x[n]   / 1024)      cal 0xC63EE, ld.hu
term2[n] = floor(992 * s[n-1] / 1024)      cal 0xC63EC, ld.h SIGNED  <-- trap: >=0x8000 flips the pole
s[n]     = term1[n] + term2[n]             -> gp-0x3d3c
out[n]   = floor((s[n-1] + s[n]) / 32)     -> iVar34, the LKAS command
```

Pole **0.96875**, **τ ≈ 31.5 cycles**, unity DC gain ⇒ a corner around **0.5–5 Hz**. **A tens-of-Hz
component cannot be COMMANDED through the LKAS lane** — everything upstream of the gain (CAN intake,
setpoint, LERP cascade, *and openpilot's own command dynamics including `STEER_DELTA`*) is band-limited
before it reaches the motor. ⚠ This **materially weakens the `STEER_DELTA` hypothesis** for a fast
symptom; it survives only for a several-Hz one.

**Both IIR self-oscillation hypotheses are DEAD**, proven not merely unobserved: for constant input the
recursion is the monotone map `s[n] = K + floor(a·s[n-1])` with `0<a<1`, which cannot have a period >1
orbit. The dead-band variant is also dead — the `>>5` is a **two-sample rolling average that RECOVERS
resolution**, giving a dead band of ~2 X-units (`1024/507`), not the 32 a naive `LSB/(1−pole)` predicts;
motor-side effect on V38 is **0–2 counts**. The upstream-LERP-quantisation door is closed analytically:
a step into a single-positive-real-pole low-pass emerges as a smooth exponential, never a fast edge.

## The edit

**One byte.** `0x454FE`: `0xBA → 0xB5`, i.e. halfword `0x65BA → 0x65B5` — V850 Bcond condition nibble
`0xA (BNE) → 0x5 (BR)`. Displacement untouched, so the **target stays `0x455C4`** (asserted by decoding both).
No relocation, no cave, no length change, no address shifts. The substitution block `[0x45500,0x455C4)`
becomes unreachable — **verified: no external Bcond or `jr` enters it.**

| Address | V38 | V42 | What |
|---|---|---|---|
| `0x454FE` | `0x65BA` | `0x65B5` | `bne 0x455C4` → `br 0x455C4` |
| `0xC4FFC` | `0xCC2134EF` | `0x62D4CE8C` | main-block CRC (the edit lives in `[0x13000,0xC4FFC)`) |
| `0xC6FFC` | `0x2A0A3DB1` | `0x0B89E4DC` | cal-block CRC (the r26 edits live in `[0xC6000,0xC6FFC)`) |

11 tracked cals asserted stock, including `0xC6206`/`0xC6208` at 512/205 and the entire `r24` set.

## Safety case — why this is not V24/V25/V26/V27

Those faulted from int-vs-float **lockstep divergence**. Four checks say that cannot happen here:

1. `FUN_00043e44` (float watchdog, same `0xd30` gate) reads **neither** `gp-0x67fa` **nor**
   `gp-0x6ace`/`gp-0x138a`/`gp-0x4cca` — zero hits inside `0x43e44`-`0x44a8b`.
2. `gp-0x6ace`'s shadow `gp-0x4cca` is written by the **same instruction pairs on every path**; the pair
   cannot desynchronise. `gp-0x138a` is unshadowed with no reader outside `FUN_0004503c`.
3. `FUN_0004595a` **is** a real no-debounce monitor feeding `FUN_00016de6(0x1d)`; it faults on
   `|gp-0x6ace|` overshooting `|gp-0x6b94|` or opposing signs. **The edit moves toward its safe side:**
   the primary computation reads `gp-0x67fa` **zero times** (verified: no `-0x67fa` displacement in
   `0x4503c`-`0x454f8`) so it is **state-independent**; `gp-0x6ace` and its shadow **already hold** that
   primary value before the state-4 check, which merely overwrites them. So after the edit state 4 leaves
   `gp-0x6ace` holding exactly what states 3/5/6/8/9/10/11 already produce — the value this monitor
   validates on every drive back to stock V9. And the monitor's conditions hold by construction: the slew
   result always lies between `gp-0x138a` and `clamp(gp-0x6b94, ±bound)`, for any held value.
4. **Ordering verified:** the substitution sits **after** the slew limiter (`0x4543a`-`0x45458`) and the
   primary interpolation (`0x4546a`-`0x454e4`). Both the governor clamp (≤4762) and the 512/205 per-cycle
   slew remain fully intact.

### ✅ Item 3 upgraded from argument to PROOF (the slew is asymmetric)

The residual risk above was closed by decoding the slew's branch structure from raw halfwords. One tracer
had described `0x4543a`-`0x45458` as "a MIN/MAX clamp into `[gp-0x138a − step, gp-0x138a + step]`" — a
**symmetric** delta clamp. It is not. There are two toward-zero fast paths:

```
0x4543a  cmp r14,r10      ; HELD vs TARGET
0x4543c  ble 0x4544c      ;   TARGET <= HELD -> decreasing path
0x4543e  cmp r0,r10
0x45440  ble 0x45458      ;   TARGET <= 0 -> SNAP TO TARGET          <-- fast path
0x45442  mov r16,r8 ; add r14,r8      ; candidate = HELD + STEP
0x45446  cmp r8,r10 ; ble 0x45458     ;   TARGET <= candidate -> SNAP
0x4544c  cmp r0,r10 ; bge 0x45458     ;   TARGET >= 0 -> SNAP TO TARGET   <-- fast path
0x45450  mov r14,r8 ; sub r16,r8      ; candidate = HELD - STEP
0x45454  cmp r8,r10 ; blt 0x4545a
0x45458  mov r10,r8                   ; snap to TARGET
```

Motion **away** from zero is capped to `HELD ± STEP`; motion **toward** zero, or a target on the opposite
side of zero, is immediate and unlimited. Three-way corroborated (this decode, an independent tracer's
decode, and the golden model's standing `[VERIFIED]` note). All four branches:

| branch | output | bound |
|---|---|---|
| TARGET > HELD, TARGET ≤ 0 | TARGET | `\|out\| = \|TARGET\|` |
| TARGET > HELD > 0 | `min(TARGET, HELD+STEP)` | `\|out\| ≤ \|TARGET\|` |
| TARGET ≤ HELD, TARGET ≥ 0 | TARGET | `\|out\| = \|TARGET\|` |
| TARGET ≤ HELD, TARGET < 0 | `max(TARGET, HELD−STEP)` | `\|out\| ≤ \|TARGET\|` |

**In every branch `|output| ≤ |TARGET|` and the signs agree.** With `TARGET = clamp(gp-0x6b94, ±bound)`,
that gives `|gp-0x6ace| ≤ |gp-0x6b94|` with matching sign **by construction, for ANY held value** —
including the larger held values this edit permits, which was the specific residual concern. Those are
exactly `FUN_0004595a`'s two fault conditions, so **it cannot trip on the primary path.**

⚠ Under the **symmetric-clamp** reading this would NOT have held: a fast decrease with a large held value
would have overshot `|gp-0x6b94|`. The distinction was load-bearing and worth chasing rather than accepting.

⚠ **Standing fact, recorded but NOT gating V42:** `FUN_00016de6(0x1d, data, 1, 1)` has **no debounce
either** — with `param_3 = param_4 = 1` it walks straight to `FUN_0001611e` (eligibility `record[+8] & 0x41`,
nonzero for `0x1d`) and then `FUN_00018738`, the motor-off entry. The guarding four-condition gate is static
eligibility/session-state, not an occurrence counter. So a single true condition anywhere on this path
reaches motor-off with no grace period. That raises the cost of being wrong about *any* monitor condition
in this region — it just does not apply here, because the condition is unreachable on the primary path.

## The vibration — reframed, and addressed by V42's Change 2

**Operator clarification (2026-07-20): the vibration is speed-independent**, present whenever LKAS commands
torque and the wheel turns, felt at all speeds; the 3–6 mph "grinding" is only where it becomes *audible*.

Eight firmware candidates eliminated:

| Candidate | Eliminated by |
|---|---|
| r24 derivative lane | V39 on-car; also `±3` deadzone-suppressed (`0xC61F6`) near zero |
| motor-rate adaptive cap | V41 on-car |
| `FUN_000456a4` compensation gate | `gp-0x6a10` not command-derived — invariance holds |
| ±8192 sanitize cliff | unreachable (7322 < 8192, both bounds now verified) |
| aggregator reduced mode | unreachable on A160 |
| polarity `gp-0x6752` | static per-variant config byte, `{0,±1}` |
| `gp-0x67fe` toggling | per-drive-cycle readiness state |
| pre-gain deadband `0xC61B8` | gate is off above ~4 mph — **measured, 98,053 raw CAN-399 frames** |

**⚠ The comma-side candidate below was the leading one for most of this session and is now DOWNGRADED.**
The LKAS lane's ~1–5 Hz low-pass (above) means openpilot's command dynamics cannot deliver a tens-of-Hz
component to the motor at all. `STEER_DELTA` survives only as an explanation for a **several-Hz** symptom,
not the buzz. It is still worth a free road test — it costs a drive, not a build — but it is no longer the
primary hypothesis. **`r26` is** (Change 2), because it is a *derivative*, i.e. a high-pass, and therefore
the only mechanism found that passes the band the IIR blocks.

The mechanism, retained because the arithmetic is right and the `1/N` rule generalises: `carcontroller.py:126` rate-limits `actuators.torque`
in **normalized** units, upstream of both `STEER_MAX` and the firmware gain, so the PID rescale never touched it:

| build | lane counts/tick | 0 → stock full scale | vs `steerActuatorDelay` = 100 ms |
|---|---|---|---|
| V9 | 13.4 | 312 ms | limiter dominates ✅ |
| V31 (2×) | 26.7 | 156 ms | limiter dominates ✅ |
| **V38 (4×)** | **53.5** | **78 ms** | **delay dominates ❌** |
| V38 + `STEER_DELTA 0.75` | 13.4 | 312 ms | restored ✅ |

The crossover falls **between 2× and 4×** — and the vibration first appears in the record at V38, not V31.
A retrodiction the model was not fitted to. `STEER_DELTA_UP = STEER_DELTA_DOWN = 0.75` restores stock's physical slew rate and remains a
worthwhile free experiment — but run it as a **separate** trial from V42, not alongside it, or the two
vibration interventions become unattributable.

**Motor torque ripple is RULED OUT** (operator argument, accepted): hand steering delivers comparable or
greater motor torque through the same aggregator → governor → shaper → FOC path and is smooth, so the motor
and the whole shared output stage are demonstrably clean at this torque level. Any ripple story would have
to explain why the same motor at the same current ripples only when the torque arrived over CAN.

## Artifact

```
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V42-LKAS-4x-V38base-state4-ratchet-off-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V42 RWD | `b332d26ccfd87b4e76702d877c1d18c492981aee67271437e389acf74ecbb3c6` |
| `_v42_plain_image.bin` | `63cec7b02c3a946d1994689bc302719bbe786a669deeb92cb4f0b00faf534bd9` |
| `_v38_plain_image.bin` baseline | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/builds/v18_v49/build_v42_tva.py`.

## Verification performed

- Bootloader walk **49/49** and full chain **50/50** on baseline, V42 image, and decoded RWD readback.
- V42 vs V38 = **exactly 35 bytes in 14 runs**: `0x454FE` (1B) + 26 r26 bytes + two 4-byte CRC trailers.
  ⚠ Not 45: ten of the 36 r26 bytes were **already `0x00`** (3072 = `0x0C00`, 2048 = `0x0800`,
  1536 = `0x0600`, 2560 = `0x0A00`, 512 = `0x0200` all have a zero low byte), so zeroing those
  halfwords moves only the high byte. The builder asserts the exact allowed byte SET, not just a count.
- `r26` Y rows verified zero and X rows verified stock in both the image and the decoded RWD; all four
  `r24` cals asserted unmoved.
- Branch **target** decoded before and after — unchanged at `0x455C4`.
- **No external entry** into `[0x45500,0x455C4)` (Bcond + `jr` scan over `0x4503C`-`0x45700`).
- All 11 tracked calibrations asserted stock; cal regions byte-identical.
- RWD round-trips; x31 checksum valid; part number `39990-TVA,A160` intact.
- **Re-verified independently outside the builder**, sharing no helper: CRC walk, Bcond decode, diff and
  the cipher table all re-derived from first principles.

## Recommended order

1. Flash V42 only on explicit operator instruction naming the file and bus. It targets **both** symptoms —
   ratchet via Change 1 (verified root cause), vibration via Change 2 (`r26`, last-standing hypothesis).
2. Score the two symptoms **separately**. They have different mechanisms, different fixes, and different
   confidence levels; a null on the vibration falsifies `r26` without implicating Change 1.
3. `STEER_DELTA 3 → 0.75` as a **separate** later trial if the vibration survives V42 — free and
   reversible, but do not run it concurrently or the two vibration interventions become unattributable.

## Open

- **Task rate in Hz** — blocks every cycles→time conversion. Needs the `0xbb8c0` TCB walker.
- **`FUN_0004595a` overshoot proof** — numerical or live, to close V42's residual risk.
- **`gp-0x67fa` steady-state value** — `flashing-2020accord/eps-read-dtcs.py` already reads `0xFEDF1806`.
  A live poll during a hard turn would quantify the ratchet's duty cycle directly.
- `gp-0x6807 == 3`'s full trigger (`gp-0x69aa ≈ 0x8000` term unresolved) — matters only if the deadband
  candidate is revived.
- **Int/float polarity mismatch** on the `gp-0x6acc` zero-gate: the integer side is **one-sided**
  (`x > +8192 → 0`) but the float twin in `FUN_00043e44` is **symmetric** (`±8.0`). No compare-and-fault
  found between them, so not lockstep-class — but it is a real, previously undocumented inconsistency.
