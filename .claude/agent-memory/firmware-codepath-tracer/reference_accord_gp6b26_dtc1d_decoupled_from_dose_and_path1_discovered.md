---
name: reference_accord_gp6b26_dtc1d_decoupled_from_dose_and_path1_discovered
description: DECISIVE Q3 safety answer for the DampAxis/gp-0x6b26 friction lane -- the DTC-0x1d monitor (FUN_00036d74) tests |gp-0x6b26| against 512, but 0xC407E clamps gp-0x6b26 to +-511 strictly upstream of both the monitor AND any 0xCBE74 gain dose, so the dose and the fault are structurally decoupled AT ANY MULTIPLIER as long as 0xC407E stays 511. Also discovers gp-0x6b26's own Path-1 (direct, unweighted, into FUN_0003aa2c), parallel to gp-0x6bd0's, and closes out FUN_0006b9fa/the generic shadow-lockstep idiom.
metadata:
  type: reference
---

# `gp-0x6b26` (`DampAxis`/friction-comp lane) — Q3 safety verdict CLOSED, 2026-08-10 (`DampAxis` task)

Full trace in `docs/TRACE-2026-08-10-dampaxis-sizing-and-safety.md`. Extends
[[reference_accord_fun36c12_sign_settled_dissipative]] and RULE 11 in `docs/BUILD-LINEAGE.md`.
Stock `code.bin` only (confirmed via `list_open_programs`). All addresses fresh-decompiled this
session; V73-V77 lineage table independently re-derived from the actual image files (Python byte
diff), not merely cited.

## ✅✅ THE DECISIVE FINDING: a `0xCBE74` gain dose CANNOT trip DTC 0x1d, at any multiplier, as long as `0xC407E` stays 511

`FUN_00036d74`@`0x36d74` (decompiled fresh): `fVar3 = gp-0x6b26/1024; if (|fVar3| > cal(0xC4004)=0.5)
FUN_000462e6(0x39bc, fVar3, 0, cal, -cal)`. Chased one hop further than the inherited record:
`FUN_000462e6`@`0x462e6` unconditionally calls `FUN_00016de6(0x1d, param_1, 1, 1)`@`0x16de6` — Honda's
generic DTC state-machine entry (manipulates a per-DTC status-bit array with confirmed/pending/
test-fail semantics) — **confirmed this sets DTC 0x1d on every trip, by decompiling the callee, not
by inheriting the claim.** `0xC4004` read fresh = `00 00 00 3f` = float 0.5 ⇒ trip at 512 counts.

But `gp-0x6b26 = clamp(raw, -cal(0xC407E), +cal(0xC407E))` (`FUN_00036c12`@`0x36ccc-ce2`), and the
`0xCBE74` Y-table (the dose target) only affects `raw`, entirely upstream of this clamp. **The stored
value can never exceed `cal(0xC407E)` regardless of the pre-clamp `raw` product or any multiplier
applied to it.** At `0xC407E`=511 (stock, and every build except V73-V75/V76-other/V77/V77b, all of
which raised it to 850), **511 < 512 ⇒ the monitor is untrippable BY CONSTRUCTION for ANY dose
multiplier M** — 1x, 10x, 1000x, doesn't matter. This is stronger than "the fault needs a raised
clamp" (RULE 11's existing claim) — it is that **the gain dose and the fault are structurally
decoupled as long as `0xC407E` is untouched.**

⇒ **`0xCBE74` is SAFE to dose at any multiplier PROVIDED `0xC407E` is explicitly asserted unchanged
(511) in the build script.** V74/V75's faults required `0xC407E` to be raised past 512 FIRST; the
gain dose alone, with the clamp respected, cannot reach that fault path. Verified in both directions
per operator policy: (a) raising `0xC407E` past 512 removes the interlock (RULE 11, re-confirmed), and
(b) raising the gain with the clamp untouched cannot reach the interlock at all (this file's new
contribution).

## Fresh, independent byte-diff corroboration (not just re-citing memory)

Python diff, `[0x13000,0x100000)`, of the actual image files under `ACCORD_FIRMWARE_ROOT`:

```
stock/V76-flown(_v76_v38base_relu_damper): m26 Y=(-9830,-5734,-1966) Honda, 0xC407E=511
V73:                                        m26 Y=Honda (m10 only dosed),   0xC407E=850
V74/V75/V76-other/V77/V77b:                 m26 Y=(-14745,-8601,-2949) x1.5, 0xC407E=850
```
m24 (manual) byte-identical to stock on EVERY build, no exception. The 14-friction-site/86-B figure
reproduces exactly: `0xCF6E0,0xCF6F0,0xD0A5C,0xD2A4C(m10),0xD2A5C,0xD3A5C,0xD3A6C,0xD4A5C,0xD6A5C,
0xD7A5C,0xD7A6C,0xD8A5C,0xD9A5C,0xD9A6C` (84B) + `0xC407E` (2B). V73 carries only `0xD2A4C`.

## New structural finding — `gp-0x6b26` has its OWN Path 1, parallel to `gp-0x6bd0`'s

Full reader census (search_instructions + Python disp16/6-byte/register-indirect scan, zero
disagreement): writer `0x36cf0` (sole). Readers: `0x36ce4` self-shadow-check, `0x36d78` the DTC
monitor, `0x3815c` Path 2 (`FUN_00038148`'s weighted 6-lane mixer, weight `0xC63A6`=1024 stock), and
**`0x3ac98` inside `FUN_0003aa2c` (the aggregator) — a DIRECT, UNWEIGHTED (exactly 1, no cal scale)
addend**, gated `±0x400→0x801` (≡±1024, unreachable, same reasoning as Path 2's gate: the ±511 clamp
binds first). Two more raw hits (`0x6b25a`/`0x6b25e` in `FUN_0006b162`) are false positives — branch-
target-text collisions (`bge 0x6b26c`/`ble 0x6b266`), unrelated function.

This is structurally IDENTICAL to `gp-0x6bd0`'s already-documented two-path structure (golden model
`eps_lkas_chain_model.py` ~line 1193). **Path 1 has zero extra phase and is very likely the dominant
delivery route for any dose** — Path 2 stacks an EMA + LERP + full gain-scheduled PID on top. Sign is
dissipative on both paths (Path 1 by plain unweighted addition of the already-dissipative producer;
Path 2 by the same Stage-2-subtraction/PID-err/polarity² cancellation the golden model already proved
for `gp-0x6bd0`, which sits in the identical structural position — same summing node, same
subtraction, same PID loop).

## `FUN_0006b9fa` — the generic shadow-lockstep idiom, closed

`FUN_0006b9fa(shadow_addr)` = `{ gp[-0x4d6c]=shadow_addr; FUN_0006ce7c(4); }`, called wherever
`value != shadow` at commit time. Found on `gp-0x6b26`/`gp-4cd0` (inside `FUN_00036c12`, at the
friction-lane's own store site), `gp-0x6b94`/`gp-4ce0` (inside the aggregator `FUN_0003aa2c`), and
FOUR more pairs inside `gp-0x6c2c`'s own producer `FUN_00041464` (`gp-0x6abc`/`4cc0`,
`gp-0x6abe`/`4cc2`, `gp-0x6ac0`/`4cc4`, `gp-0x6ac2`/`4cc6`) — **at least 6 instances, a pervasive
RAM-corruption guard, not a narrow "4 pairs" specific to one monitor.** It is a bit-flip/integrity
check (fires only if last cycle's own write did not survive), NOT a magnitude/plausibility monitor —
**orthogonal to any gain-dose question; cannot be tripped by raising a calibration.**

## `0xC646E` (INERTIA's gain) — NEW KILL, do not propose

`FUN_0003b8f6`@`0x3b8f6` decompiled fresh: `INERTIA = clamp(EMA2(d/dt(polarity·gp-0x6abc·12)) *
0xC646E/2^24, ±10)`, stock `0xC646E` read fresh = **1428** (u16 at `tp+0x746E`). Feeds
`gp-0x6bfc = clamp(cal(0xC6468)*(model − FRICTION − INERTIA), ±20000)` — **subtracted from the SAME
plant model, with the SAME polarity, as FRICTION/K1 (`0xC40D2`, the already-flown V89 lever)**, and
has no Path-1 equivalent of its own (Path 2/observer-residual chain only). By the operator's own
V89-verified polarity mechanism ([[accord-friction-polarity-more-assist]]: subtracting more from the
model → residual more negative → PID error grows → assist increases → LIGHTER wheel), **raising
`0xC646E` almost certainly makes the wheel feel LIGHTER, not more damped — the opposite of intent for
anti-ratchet work.** Virgin cell (0 build-script mentions), superficially meets the velocity-
derivative-proportional + dissipative-looking criteria for a Q4 candidate, but the sign inversion via
the shared observer disqualifies it. **Do not propose a dose of `0xC646E`.**

## `gp-0x6c2c` transfer, independently re-derived (3rd/4th confirmation)

Fresh Python time-domain sim of the exact confirmed integer cascade (K0=37/128, K2=22/64, both read
fresh from `0xC643C`/`0xC40DC`): `|H(7.79Hz)|=3.078x, |H(21.09Hz)|=7.542x, |H(28.1Hz)|=9.260x` —
matches [[reference_accord_gp6c2c_transfer_function_triple_verified]] to 3-4 sig figs, independently
reproduced not merely cited.

## `dose_headroom()` / `max_multiplier_for_pin_duty()` — implemented, sanity-checked

Classical hard-clip describing-function formula `N(A)/K = (2/π)[arcsin(R/A) + (R/A)√(1-(R/A)²)]` for
`A>R` else 1, applied at the distribution's p99 magnitude (matches how the kit's own DF figures were
computed). Sanity check on the 2-point placeholder (73, 109 ct, the only figures on record pre-V90)
**reproduces "DF exactly 1.000 through ×4, 0.881× at ×6" EXACTLY** — confirms the formula. Full code
in the trace doc. Ready to consume V90's real `gp-0x6b26` distribution the moment it lands; no
re-derivation needed, just feed the array in.

Related: [[reference_accord_fun36c12_sign_settled_dissipative]] (the sign/DF/lineage base this
extends), [[reference_accord_factorb_index_selector_c6498_and_torque_axis_census]] (torque/current
axis census this Q4 census complements), [[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]]
(the earlier 0xC407E census this reconfirms and extends one hop further into the DTC callee).

## ADDENDUM (same session) — `0xC63A6`, band-aware dissipative fraction, GATE-2 reactive risk

### `0xC63A6` (tp+0x73A6, FUN_00038148's Path-2 weight for gp-0x6b26) — census + verdict

Fresh raw Python disp16 scan (positive tp-displacement, both `disp` and `disp|1` forms): **exactly 1
hit, `0x381CA`**, matching Ghidra `search_instructions` (2 raw, 1 real + 1 branch-text false positive
at `0x473a0`). Zero writers (tp-relative reaches cal ROM, not RAM). Stock value read fresh = 1024.

Full disassembly of `FUN_00038148`@`0x38148-0x382d6` pulled and instruction-verified two claims:
1. **Gate precedes weight, confirmed at instruction level**: `0x3818c cmovc 0x0,r6,r10` (the ±1024-ish
   gate, on the RAW `gp-0x6b26` loaded at `0x3815c`) executes BEFORE `0x381ca ld.hu 0x73a6[tp],r15`
   (the weight) and `0x381ce mul r15,r10,r0` (weight applied to the already-gated r10). **`0xC63A6`
   cannot move the gate — confirmed, not inferred.**
2. **`resid = gp-0x6bfe − EMA(SUM_6ch·polarity·2639) + gp-0x6bfa`** (`0x38238 subr r15,r6` after the
   EMA update at `0x381fe-0x38230`). Raising `0xC63A6` increases `SUM_6ch`'s gp-0x6b26 term → increases
   the SUBTRACTED quantity → REDUCES `resid` (polarity=+1). Raising K1 (`FRICTION` in `FUN_0003b8f6`)
   reduces `gp-0x6bfc`→`gp-0x6bfe` directly → ALSO reduces `resid`. **Both act in the same direction on
   the same node, confirmed by instruction arithmetic — `0xC63A6` IS structurally kin to V89's already-
   flown-and-measured-flat K1 lever, on its Path-2 share only.** `0xC63A6` does NOT touch Path 1 at all
   (Path 1's addend at `0x3ac98` has weight exactly 1, no cal multiply anywhere).

⇒ **`0xCBE74` remains the stronger, more independent single lever** (drives Path 1, which nothing else
in the kit has ever tested, PLUS the K1-kin Path 2). **`0xC63A6` is legitimate as an isolation tool**
(a way to move Path 2 alone, e.g. to empirically separate Path 1's contribution from Path 2's) but its
own independence claim rests entirely on a gating-SHAPE argument (K1 is `|model|`/command-magnitude-
gated, near-zero on 99.1% of the micro-ratcheting regime per V89; `gp-0x6b26`'s Path-2 term is rate-
derivative-gated, non-zero at any rate transient) — real, but weaker than Path 1's clean structural
independence.

### Band-aware dissipative/reactive fraction, 2-35 Hz — clean z-domain derivation, EVIDENCE

`H(f) = 64·H1(f)·(1−z⁻¹)·H2(f)` (the confirmed EMA/differencer/EMA cascade, `z=e^{j2πf/1000}`) gives
`gp-0x6c2c(f)/rate(f)` unambiguously. **Key resolved subtlety**: `phase(H(f))` (UNNEGATED) is exactly
the "deviation from the calibrated dissipative reference" angle the inherited Leg-3 table already
used (verified: reproduces `76.43°/54.63°/44.31°/9.74°/-11.96°/-24.97°` at 7.79/21.09/28.1/60/100/200
Hz to 2 decimals) — because `gp-0x6b26=-k·gp-0x6c2c`'s own 180° and the reference damper `gp-0x6bd0`'s
own 180° (from its relay-vs-rate character) cancel algebraically. **Dissipative fraction = cos(that
angle), reactive fraction = |sin|**:

| f (Hz) | \|H\| | angle | dissipative | reactive | Re(H) | M_rel (vs 7.79Hz, same dissipative torque) |
|---|---|---|---|---|---|---|
| 7.79 (ratchet) | 3.080 | 76.4° | **0.235** | 0.972 | 0.723 | 1.00 |
| 21.09 (grind1) | 7.546 | 54.6° | 0.579 | 0.815 | 4.369 | **0.165** |
| 28.10 (grind2) | 9.267 | 44.3° | 0.716 | 0.699 | 6.631 | **0.109** |

⇒ **the ratchet needs ~6.1× more gain than grind #1 and ~9.2× more than grind #2 to deliver equal
dissipative torque via Path 1** (Path 1 only — flat 1.066 DC gain, no extra shaping, so this ratio
transfers directly; Path 2 needs its own PID-schedule correction on top). Plant-independent AS A RATIO
between two frequencies (the unmeasured `gp-0x6b98→column` transfer cancels, PROVIDED it is roughly
flat between the compared bands — unverified assumption, flagged).

**GATE-2 reactive-component finding [reasoned extension, consistent with the sibling
`(J+k)α=T_driver` memory, not independently re-derived from a mechanical model]**: at 7.79 Hz the
term is 97% reactive with deviation angle landing the raw force at −90° from rate — in phase with
`−acceleration`, i.e. it behaves as ADDED APPARENT INERTIA, not damping, at the ratchet frequency.
For a simple resonance, adding inertia at fixed physical stiffness/damping LOWERS BOTH `ω0` and `ζ` —
so a large dose aimed at 7.79 Hz bundles a small guaranteed real-damping gain (23.5%) with a larger,
sign-uncertain risk to a Q14-29 mode's own damping ratio. **This lane is structurally better-supported
as a grind-#1/#2 lever (58-72% dissipative there) than as a ratchet lever (24% dissipative, 97%
reactive) — a real, evidence-grounded reason to retarget any dose, not merely a nicety.**

### `dose_headroom()` on the real V90 distribution (route 77, 62,180 frames, 0% CAN saturation)

`MOTOR_TORQUE` p50/p95/p99/max = 3/34/67/199 ⇒ `|gp-0x6b26|`(×8/5) = 4.8/54.4/107.2/318.4 ct.
`max_multiplier_for_pin_duty` reproduces the team-lead's own arithmetic exactly: M≤1.605 (zero pin,
off route max) / M≤4.767 (pin<1%, off p99) / M≤9.393 (pin<5%, off p95). Added nuance: at M=4.77, DF
evaluated at the single observed max is already down to 0.42 — a route's observed max is a sample
statistic, not a proven ceiling; recommend sizing off p99 with a margin (e.g. M≤3) rather than trusting
one route's max as a hard bound.

Full write-up: `docs/TRACE-2026-08-10-dampaxis-sizing-and-safety.md`, ADDENDUM 1 section.

## ADDENDUM 3 — session CLOSED with a "do not fly" verdict [EVIDENCE]

**`H(0)=0` proven exactly** (pole/zero: `(1-z^-1)|_{z=1}=0`, both EMAs unity DC gain; confirmed via exact
integer simulation of a constant-rate input converging to `gp-0x6c2c=0` identically) ⇒ **this lane does
NOT limit sustained LKAS steering rate** — only a small (0.85-6.4% of median command), sub-70ms transient
during a rate RAMP. Contrast: FactorC/E's base-assist damper IS rate-indexed (not rate-derivative) and
DOES oppose a held rate continuously — that is the lever the operator's "limits top steering rate" memory
belongs to, not `0xCBE74`.

**Historical pin, fresh byte reads**: V74/V75 both carry `0xC63A0` (damper weight) doubled 1024→2048
alongside the friction dose. **V81** (the fault-fix build) checked directly: friction lane fully
reverted to stock, `0xC407E`=511 reverted, **but `0xC63A0` still 2048, FactorC m26 `Y[0]` still 566
(stock=0) — the damper was still fully live.** If the operator remembers V81 as "we fixed the faults and
it turned out to just be a damper," the damper (not `0xCBE74`) is the mechanically correct attribution.

**Q-B, the decisive sizing question**: at the clip-envelope-forced ×1.5, delivered damping is **below an
11% resolvability floor in every band checked — 0.16% (6-9Hz), 1.20% (18-22Hz), 2.15% (26-31Hz,
model-extrapolated, robust to the extrapolation's 0.5-1.37× cross-validated uncertainty).**
**RECOMMENDATION: do not fly `0xCBE74` as a dose — underpowered by construction, 5-69× below floor in
every band.** Session closed on this verdict.

## ADDENDUM 2 — NEW SAFETY FINDING: intermediate int32 overflow in `FUN_00036c12`, quantified [EVIDENCE]

🛑 Distinct from the DTC-0x1d/`0xC407E` story. Checking the int16 Y-storage headroom for a `0xCBE74`
dose led to tracing the arithmetic one level deeper via **raw P-code** (`get_function_pcode`), not the
C decompile, which hides this.

**Two multiplies at `0x36cbe`/`0x36cc6`**: `0x36cbe mulh r12,r13` (`sVar7 × gate(gp-0x6c2c)`) —
**checked via P-code and confirmed NOT 16-bit-truncating** (my first hypothesis, from the `mulh`
mnemonic alone, was wrong; P-code shows both operands sign-extended to 32-bit first, then a clean
32×32→32 `INT_MULT` — this is exactly the "assembly confirms, do not guess ISA semantics" discipline
working as intended: I formed a wrong hypothesis from the mnemonic, checked it against ground-truth
P-code, and it was refuted before I reported it). `0x36cc6 mul r13,r6,r0` (`×0x111=273`) — **this one
IS a real 32×32→32 multiply keeping only the low 32 bits (r0=high half discarded) — standard
2's-complement wraparound if the true product exceeds int32.**

**Overflow threshold**: `|gp-0x6c2c| > (2³¹−1)/273×64 / Y_dosed`. Stock (Y=9830): threshold=51,215,
safely above `gp-0x6c2c`'s own 32000 producer ceiling ⇒ **provably safe at M=1**. Falls with dose:
M=1.6→32,009 (≈ the producer ceiling itself) · M=2→25,607 · M=3→17,072 · M=3.333(int16 ceiling)→15,366.

**Cross-checked against realistic `gp-0x6c2c`**, inferred from V90's real `|gp-0x6b26|` percentiles
(`k∈[0.032,0.160]`, worst-case/least-sensitive row): **route-77 measured max (319.1 ct) implies
`|gp-0x6c2c|` up to ~9,972.** At M=3 the overflow margin is **1.71×** — real but not generous
(comparable to the 1.56× clamp-binding margin already on record elsewhere in this kit); at M=2 it's
2.57×. **NOT proven that `gp-0x6c2c` can never exceed ~10,000 in a rarer/fault-adjacent transient** —
flagging per RULE 11's lesson about assuming bounds are "practically unreachable," not resolving.

**Consequence if triggered**: `iVar4` wraps arbitrarily (not clamps) before the `0xC407E` clamp
comparison runs — corrupts one tick's `gp-0x6b26` sample. Likely self-limiting (the `gp-0x4cd0`
shadow-lockstep would plausibly catch such a jump, single-tick, no persistent state), but not proven
zero-risk. **This is now the binding constraint alongside DF-at-max in the M≈2-3 region** — both
independent ceilings converge there, worth treating as a combined bound, not either alone.

Also this session: confirmed the LERP-join "no new knee from uniform scale" claim is a direct
consequence of piecewise-linear interpolation's linearity in Y (provable, not merely likely, provided
X stays untouched); confirmed the `±511` clamp's own knee is pre-existing at M=1 (not created by a
dose, fully characterized by the existing DF/pin-fraction functions); discovered `FUN_000428d4`
(1kHz, called from the same `FUN_0002214a` task) — a live Honda oscillation-reversal detector on
`gp-0x6c2c` itself (threshold `cal(0xC620A)`=12800, read fresh), feeding DTC 0x21 AND writing
`gp-0x671a`, which is the SAME cell `FUN_00036c12` (this lane) tests to decide whether to run its
normal LERP or fall back to a fixed value (`cal(0xC64FD)`=5, read fresh) — a genuine, already-existing
runtime circuit breaker on the exact signal any `0xCBE74` dose amplifies, independent of anything added.
