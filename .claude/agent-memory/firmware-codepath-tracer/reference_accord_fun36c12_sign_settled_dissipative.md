---
name: reference_accord_fun36c12_sign_settled_dissipative
description: SETTLES the FUN_00036c12 / gp-0x6b26 sign question open since 2026-08-06 — on the RESISTIVE axis the lane is DISSIPATIVE, same sense as the damper, structurally (would need >180 deg of lag from two first-order poles to flip), so lowering it removes damping. Also adjudicates a sibling agent's claim that the LERP index gp-0x6a5e is driver torque: it is voted VEHICLE SPEED, sole writer FUN_00041eec @0x42342.
metadata:
  type: reference
---

# `FUN_00036c12` / `gp-0x6b26` — sign SETTLED, 2026-08-10 (`DampAxis` task)

Open since 2026-08-06. **Verdict: DISSIPATIVE, the same effective sign as the damper `gp-0x6bd0`.
NOT anti-dissipative.** Stock `code.bin`, RULE 7 satisfied (read on the ENGAGED mode 26 column).

## Leg 1 — the lane's own gain is NEGATIVE [EVIDENCE, fresh byte read]

`0xCBE74 + 26*4` → pointer `0x000D7A54`. `read_memory 0xD7A54,16` =
`0300 0000 0005 8016 9ad9 9ae9 52f8 0000` ⇒ `n=3, X=[0,1280,5760] ct = [0,20,90] km/h,
Y=[−9830, −5734, −1966]`. **Mode 24 (`0xD6A64`) is byte-identical.**

```python
# integer mirror of 0x36c12, each line annotated with its address
gain = lerp(gp_6a5e, X=[0,1280,5760], Y=[-9830,-5734,-1966])   # ALWAYS NEGATIVE
raw  = (gate(gp_6c2c) * gain) >> 6                              # 0x36cbe mulh / 0x36cc0 sar 6
out  = (raw * 0x111) >> 0x12                                    # 0x36cc4 mul / 0x36cca sar 18
gp_6b26 = clamp(out, -511, +511)                                # cal 0xC407E = 511
# net |k| = |Y|*273/2**24 : 0.1600 @0 km/h, 0.0933 @20, 0.0320 @90
# clamp reached at |gp-0x6c2c| = 511/0.160 = 3194 counts
```
⇒ **`gp-0x6b26 = −k · gp-0x6c2c`, k > 0.**

## Leg 2 — friction lane and damper enter the SAME node with the SAME sign and weight [EVIDENCE]

`FUN_00038148` stage 1 sums six lanes, every one `+`. `read_memory 0xC63A0,16` =
`0004 0004 0004 0004 0004 0004 6600 0004`:

| lane | cell | weight cal | stock | zero-reject window (from the decompile's own range test) |
|---|---|---|---|---|
| LKAS-class | `gp-0x6b4e` | `0xC63A8` | 1024 | ±10240 |
| LKAS | `gp-0x6b4c` | `0xC63AA` | 1024 | ±10240 |
| **friction** | `gp-0x6b26` | **`0xC63A6`** | **1024** | **±1024** |
| torque-domain | `gp-0x6b46` | `0xC63A4` | 1024 | ±1024 |
| **damper** | `gp-0x6bd0` | **`0xC63A0`** | **1024** | **±2048** |
| boost | `gp-0x6bbe` | `0xC63A2` | 1024 | ±2048 |

Plus `0xC63AC`=102 (the α≈0.0996 EMA) and `0xC63AE`=1024. **These windows independently reproduce the
kit's recorded zero-reject numbers exactly.** ⇒ **no relative inversion exists at the summing node.**

## Leg 3 — the phase, and why it CANNOT flip [EVIDENCE + bounded BELIEF]

Damper (the calibrated dissipative reference): `gp-0x6bd0 = −sign(gp-0x6abe)·product`
(`0x3469e cmp r0,r11 / 0x346a0 ble / 0x346a2 subr r0,r8`) ⇒ fundamental 180° from rate, Re < 0.

`gp-0x6c2c`'s ONLY writer is `FUN_00041464` (`sar 0x9,r26` then `st.h r26,-0x6c2c,gp` @`0x4184e`;
fallback store `0x41ac2`; `search_instructions "6c2c"` = 8 hits, all adjudicated, no other writer) —
a backward difference of motor rate wrapped in first-order EMAs.

Phase of `−gp-0x6c2c` vs rate (α = 37/128 and 22/64, corners 54.3 / 67.0 Hz at fs=1 kHz):

| band | fs=1000 | fs=312.5 | Re(·) vs rate |
|---|---|---|---|
| 7.79 Hz | +76.4° → 256° | +48.9° → 229° | **negative** |
| 21.09 Hz | +54.6° → 235° | +4.2° → 184° | **negative** |
| 28.1 Hz | +44.3° → 224° | −8.1° → 172° | **negative** |

**All six cells dissipative.** A backward difference gives `+90° − ωT/2`; each first-order EMA gives a lag
strictly in `(−90°, 0°)`. **To flip the sign, cumulative lag would have to exceed 180° — unreachable with
two first-order poles (they asymptote to 180° and never reach it) plus a ≤5° ZOH term.**
⇒ **the dissipative sign is STRUCTURAL, not calibration-dependent.**

## Consequence — stated on the DAMPING axis only

**On the resistive (real-vs-rate) axis `gp-0x6b26` is dissipative ⇒ LOWERING IT REMOVES DAMPING** — the
opposite of the intuition that "less compensation = calmer". Task rate: sole caller `FUN_0002214a` =
**1 kHz**, one of the few lanes fast enough for 18–28 Hz.

🛑 **My first write-up of this file over-reached by adding "it is inertia COMPENSATION, not emulation."
That is a claim on the REACTIVE axis and my real-part argument does not support it — retracted.** The
decomposition at 21–28 Hz (fs=1 kHz) is roughly **25–70 % resistive, 70–97 % reactive**: the term is
mostly an inertia-like reactance with a genuine dissipative real part. A sibling agent
(`reference-accord-fun36c12-negative-accel-feedback`, in `analysis-2020accord/.claude/agent-memory/`)
argues the reactive part **ADDS** apparent inertia via `(J+k)α = T_driver`. **That is compatible with
this file, not contradictory** — they project onto the reactive axis, this file onto the resistive one.
Their inertia sign still depends on an absolute end-to-end polarity that neither trace resolved
independently; this file's relative-to-the-damper argument does not.

[BELIEF caveat, scoped] The phase *magnitudes* depend on the α values carried from
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] rather than re-derived from
`FUN_00041464` this session. **The sign — the thing that was asked — does not depend on them.**

## 🛑🛑 ADJUDICATED: the LERP index `gp-0x6a5e` is voted VEHICLE SPEED, **not driver torque**

The same sibling memory asserts *"`0xCBE74[mode]` is LERP-indexed on `gp-0x6a5e` = voted DRIVER TORQUE …
multiple briefs call it a speed-LERP; it is not"*, and derives *"k is 5.0× stronger at zero DRIVER
TORQUE … strongest on-centre and hands-light."* **That is wrong.**

[EVIDENCE] `search_instructions mnemonic=st.h operand=6a5e` ⇒ **exactly ONE writer: `FUN_00041eec`
@`0x42342`** — the 5-channel **vehicle-speed** voter (independently the sole writer of `gp-0x67f4`, the
speed-voter validity flag, and of `gp-0x6a64` @`0x42360`, 30 bytes later in the same routine).
Corroborating: breakpoints `[0,1280,5760]` = `[0,20,90] km/h` at 64 ct/km/h · FactorC `X[0]=2240` =
35 km/h · overflow rail `>0x7d00` = 500 km/h · `FUN_000757a2`'s creep/highway split `<640` = 10 km/h.
**Four prior memories say speed** ([[reference_accord_gp6a5e_is_voted_vehicle_speed]] + three siblings),
and repo memory `reference-accord-gp6a5e-is-speed-reclassifies-v44-v47` shows **this exact
misidentification was already made and corrected once, and it reclassified builds V44–V47.**
⇒ correct reading: **5.0× stronger at 0 km/h than at 90 km/h — strongest at CREEP, not hands-light.**
Different regime, different lever rationale. Do not act on the torque reading.

🛑 `0xC407E` lineage: hard-fault interlock, 511 on stock and every build V38–V89; V73 raised it to 850 and
**V74/V75 FAULTED**; V81 restored 511. Not proposed here in either direction.

## SIZED, 2026-08-10 — NOT a relay; the zero-reject is UNREACHABLE; safety limit ×3

[EVIDENCE — `size_6b26.py`, all cals byte-read on stock AND `_v89_...FRICTION.C40D2.204..._plain_image.bin`
(sha256 `6eae6826881cb5fd…`); `0xCBE74` is **virgin on V89**, both mode records byte-identical to stock.]

**Producer chain, byte-exact (`FUN_00041464`, 1 kHz):**
```
valid = -13000 <= gp_4f50 <= 13000     # == gp-0x4f50's OWN producer clamp -> tautology
x     = gp_4f50 * 1024
s1   += (x - s1) * cal(0xC643C)=37 >> 7      # EMA1, alpha 37/128
d     = s1[n] - s1[n-1]                      # TRUE backward difference
d32   = clamp(d*32, +-0xfa0000)
s2   += (d32 - s2) * cal(0xC40DC)=22 >> 6    # EMA2a, alpha 22/64
gp_6c2c = s2 >> 9        # gain 64; |gp_6c2c| <= 32000 BY CONSTRUCTION
```
⇒ **exactly two first-order poles + one differencer** — the structure this file's §Leg-3 bound assumed,
now confirmed. **The phase table above is EVIDENCE end-to-end, no longer BELIEF.**
⇒ two more **producer-clamped tautologies**: `FUN_00036c12`'s ±32000 guard, and the ±13000 validity test.

**★ Scale DERIVED from code (no bus torque):** `gp-0x6abe = EMA1(gp-0x4f50)` exactly — the alternate arm
rescales by `cal(0xC6134)=1000`/1000 with offset `cal(0xC648E)=0`, so **both arms are numerically
identical**, and config byte `0xC40ED`=0 ≠ 0xE9 selects the pass-through anyway. EMA1 DC gain 1 ⇒
**`gp-0x4f50` carries the same 4.7121 ct/(°/s) as `gp-0x6abe`.**

| band | \|gp-0x6c2c\| per count of rate | saturating column amplitude |
|---|---|---|
| 7.79 Hz | 3.080 | 4.50° @0 km/h |
| 21.09 Hz | 7.547 | 3.39° @90 km/h |
| 28.1 Hz | 9.267 | 2.06° @90 km/h |

**NOT a relay:** at the corpus's measured ratchet amplitude (1.29–1.92° p-p) `|gp-0x6b26|` = **73–109 ct
= 14–21 % of the ±511 clamp**, saturation DF **exactly 1.000 through ×4** (×6 → 0.881).

**🛑🛑 The ±1024 zero-reject in `FUN_00038148` is on the lane's OUTPUT — and is UNREACHABLE**, because
`0xC407E` already clamps the lane to ±511 and **511 < 1024**. Same for the damper (window ±2048 vs
ceiling ≤1024 table / **512** scalar `0xC6158`). ⇒ **neither lane can suffer the full-magnitude dropout.**
**Corollary: `0xC407E`=511 is doing double duty — raise it above 1024 and the lane ACQUIRES a dropout it
does not have today.** (V73's 850 stayed under 1024, so that is not what faulted V74/V75.)

**Safety limit ×3**, from two independent limits that coincide: the ±511 clamp begins binding at 1.50°
(vs 0.96° measured max = 1.56× margin), and `|Y|`×4 = 39320 **overflows int16**. ×2 comfortable.

**Referral factor `gp-0x6b26` → `gp-0x6b70`** (measured, not inherited): weight `0xC63A6`=1024 ×
`0xC6468`=2639 (×2.577) × 16, stage-2 `>>4` cancels the ×16 **exactly**, through the `0xC63AC`=102/1024
EMA ⇒ **×2.336 @7.79 Hz, ×1.601 @21 Hz, ×1.318 @28 Hz** — i.e. the lane grows downstream.

**★★ SHAPE — flatten, don't scale.** Because the axis is SPEED (see above), k = 0.1600 @0 km/h vs 0.0320
@90 ⇒ Honda's schedule is **right-way for the creep ratchet, wrong-way for the highway grind**. Lifting
the 20/90 km/h rows toward the 0 km/h value adds damping only where the grind lives, leaves the
nearest-to-rail creep row untouched, and has **16× of int16 room**. 🛑 US7523806B2's "never lift Y[0] off
zero" does **not** apply — the axis is speed, so `X[0]=0` is *stationary*, not zero rate, and `Y[0]` is
already maximal. **No V80 step-at-zero-rate hazard exists on this table.**

🛑 **STRIKE, recorded honestly:** `gp-0x6c2c` is acceleration-like ⇒ amplitude ∝ ring rate at fixed
frequency, but the corpus says the engagement amplification is **rate-INDEPENDENT** (+0.022 [−0.070,
+0.116]). **A linear rate-proportional term cannot produce a rate-independent signature ⇒ this is a
strike against `gp-0x6b26` as the CAUSE.** It is not a strike against it as a **remedy** (a damper need
not be the cause to quench an FIV limit cycle). **Defend it as a damper only, never as the mechanism.**

🛑 **Dose UNRESOLVED and blocked:** the term already delivers 73–109 ct vs a stated requirement of ~29 ct
⇒ implied multiplier **below unity**. Either the 29-ct figure is quoted at a different node or the lever
is unnecessary. **Do not pick a multiplier until the node is stated.**
🛑 **Do not conflate with V89's lever**: `0xC40D2` is the Coulomb scale in `FUN_0003b8f6` (Path-2 plant
model); `0xCBE74` is the comp LERP in `FUN_00036c12`. Different functions, unrelated cells.

## 🛑🛑 LINEAGE — `0xCBE74`'s Y ROW IS **NOT VIRGIN**. It flew at ×1.5 on FOUR images.

[EVIDENCE — cross-build read of the *images*, dereferencing `0xCBE74 + mode*4` per build, 2026-08-10.]
A session brief asserted this cell was "never written". **It was written, and flown.**

```
build                         m24 Y (0xD6A64)        m26 Y (0xD7A54)          0xC407E
stock                         [-9830,-5734,-1966]    [-9830,-5734,-1966]          511
v73                           [-9830,-5734,-1966]    [-9830,-5734,-1966]          850
v74_engagedcols_x0_12_addonly [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v75_CY0.566_magprobe          [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v77                           [-9830,-5734,-1966]    [-14745,-8601,-2949] x1.5    850
v81 .. v89                    [-9830,-5734,-1966]    [-9830,-5734,-1966]          511
```
`builds/v50_v79/build_v74_tva.py:79` = **"LEVER D' — THE FRICTION LANE ×1.5"**. `BUILD-LINEAGE.md` carries a 2026-08-07
correction of record (*"introduced by V73, NOT V74"*) and **"the friction row is 14 sites, not one"**
(`0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C 0xD3A5C 0xD3A6C 0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C
0xD9A5C 0xD9A6C`; Honda `9ad99ae952f8` → ×1.5 `67c667de7bf4`).

**On-car — ×1.5 flew exactly THREE times:**

| build | ×1.5 on m26? | `0xC407E` | on-car |
|---|---|---|---|
| **V73** | 🛑 **NO — m10 ONLY** (disengaged, another variant's row ⇒ **INERT here**) | 850 | flew clean — **says nothing about this lever** |
| **V74** | yes | 850 | **HARD-FAULTED** (latched total loss of assist) |
| **V75** | yes | 850 | **HARD-FAULTED** |
| `_v76_gate_fb_arm5244_gateprobe` | yes | 850 | **not the flown artifact** |
| **`_v76_v38base_relu_damper`** | **STOCK** | **511** | **THE ONE THAT FLEW** (route 65, clean) |
| V77 | yes | 850 | **NEVER FLEW** |
| V78 / V79 / V80 / V81 → V89 | stock | 511 | — |

🛑 **TWO V76 ARTIFACTS EXIST and they differ on this cell.** `BUILD-LINEAGE`'s V76 row is
`| V76 | V38 | … | FLEW route 65 |` — base **V38** ⇒ `_v76_v38base_relu_damper` ⇒ **stock friction, 511
clamp.** That row's own note explains it: *"the V38 rebase silently reverted SEVEN things"* — the ×1.5
row and the 850 clamp were two of them. **The lineage FORKED**: V76-v38base → V78 → V79 → V80 carry
stock; V77 and V81 came off the V74/V75 branch.

Faults are attributed to `0xC407E`=850, not this row (the clamp is mode-proof; V74 faulted with LKAS
*disengaged*). ⚠ **Mode 24 was NEVER touched on any build** — V74's design was engaged-column-only.

🛑🛑 **ZERO CLEAN FLIGHTS OF THIS LEVER, EVER.** Verified by 34-mode dereference: **V73 dosed exactly ONE
friction Y row — m10 (`0xD2A4C`), DISENGAGED, belonging to rows 2/3/6/7 = another variant ⇒ inert on this
car.** V74 dosed 14 (13 engaged + V73's inherited m10). ⇒ **×1.5 on a live column flew exactly TWICE
(V74, V75) and BOTH HARD-FAULTED.**
⇒ I twice claimed a V73 clean flight of this lever — first as "an era", then as "one clean route". **Both
retracted.** The prior is **untested, with a 2-for-2 fault association.** ×2 is NOT reopened.

## 🛑 THE FAULT ATTRIBUTION IS INVERTED — the clamp is exonerated, the friction row is implicated

| build | clamp | friction on a LIVE column | on-car |
|---|---|---|---|
| V73 | **850** | no (m10 only, inert) | **CLEAN** |
| V74 | 850 | **yes** | **HARD FAULT** |
| V75 | 850 | **yes** | **HARD FAULT** |

**The standing record blames `0xC407E`=850 for V74/V75. V73 flew clean with the same 850.** ⚠ Cannot be
pinned — V73→V74 is 64 differing runs, not single-variable — but **the control meant to exonerate the
friction row is the thing that implicates it.** ⇒ **a ×3 dose is DOUBLE the dose carrying that
association.** The saturation/dropout safety envelope (DF, clamp margin, int16, zero-reject, dissipative
sign) says nothing about a **latched-fault** mechanism, which is what actually happened twice.
⇒ **PROBE-ONLY is the right call. Do not recommend a dose until the probe reports the term's real duty.**

## 🛑 THE ADDRESSES — an ADDRESS IS NOT A MODE. Dereference, always.

```
m24 (manual) : base 0xD6A64 · X 0xD6A66 [0,1280,5760] · ** Y ARRAY 0xD6A6C **
m26 (engaged): base 0xD7A54 · X 0xD7A56 [0,1280,5760] · ** Y ARRAY 0xD7A5C **
0xD6A5C -> mode 23 (NOT 24) · 0xD7A6C -> mode 27
```
Two separate near-misses on this in one session: I named **record bases** where Y arrays were meant, and
team-lead named **`0xD6A5C`** (mode 23, from the V74-dosed set) as mode 24. **The V74-dosed set ≠ the set
V90 should write — V74 never touched m24.**
⊕ **Consequence of writing Y values at `base+2` is SILENT, not a crash**: `X` becomes `[-29490,…]`, read
as **u16 36046** by the LERP's unsigned compare ⇒ every speed falls below `X[0]` ⇒ **flat `Y[0]`=−9830 at
all speeds = an accidental 5× at highway.** Plausible-looking, wrong experiment. **Assert X unchanged.**

## The 14-site question — ANSWERED: two records is correct and sufficient

Dereferencing `0xCBE74 + m*4` for all 34 modes and diffing each Y row against the V74 image: the
"14 sites" are **the 13 ENGAGED modes across every row {2,3,5,11,14,15,17,23,26,27,29,32,33} + V73's
stray m10** (disengaged). All 14 are reachable from a mode index; 34 distinct Y rows exist.
**m24 (`0xD6A6C`) and m25 (`0xD7A4C`) were never dosed.**

⇒ **Writing only m24 `0xD6A64` + m26 `0xD7A54` is correct** — this car's two MEASURED live columns
(V73's probe: 104,061 frames, 18 transitions, manual=24 / engaged=26, forced by the manual arm).
🛑 **NOT the V69 failure**: V69 wrote modes 10/11, on rows 2/3/6/7 — *another variant's* rows. Writing
24/26 hits the live columns. Opposite error class.
🛑 **But writing BOTH makes the dose SYMMETRIC where V74's was ENGAGED-ONLY** ⇒ it changes **manual**
feel, which V74/V75 never did. Recommended anyway: Honda ships m24 ≡ m26, so symmetry is conservative;
and the engaged-only alternative's "free within-drive control" is **already known underpowered**
(Lever-B × rate contrast −0.101 [−0.381, +0.298], CI half-width 2.4× the effect).
🛑 **ASSERT m25/m27 byte-stock, do not dose them** — V83a's recorded defect was leaving m27 carrying a
package unintentionally, and stock m25/m27 means a `gp-0x67e2` flip falls back to Honda's value.

## ★★ GATE 2 — the sign CAN be closed, structurally; the magnitude CANNOT

Closed loop: `gp-0x6b26 → gp-0x6b70 → gp-0x6ad6 → PID → aggregator → gp-0x6b98 → FOC → motor →
resolver → gp-0x4f50 → gp-0x6c2c → back into gp-0x6b26`. **A loop-gain edit, not a feedforward tweak.**
🛑 Magnitude not statically closable — the PID gain is runtime-scheduled.
✅ **Sign closable and total: `−gp-0x6c2c` stays dissipative at EVERY frequency to Nyquist** (+76.4° @7.79,
+54.6° @21, +44.3° @28, +9.7° @60, −12.0° @100, −25.0° @200 — **never reaches −90°**). Two first-order
poles contribute at most 180° and the differencer starts at +90°, so −90° is approached asymptotically and
never crossed. ⇒ **raising this gain cannot destabilise by sign at any frequency.**

**Dissipative projection matters** — only the real-vs-rate part is damping: `cos` = 0.235 @7.79 Hz,
0.579 @21, 0.716 @28. At the measured ring the lane delivers **17–26 ct dissipative at creep**,
**11.7 at highway**, ×2.34/×1.60/×1.32 referred to `gp-0x6ad6`.
**Biased DF does NOT apply to this lane**: `gp-0x6c2c` is *differenced*, so a quasi-static bias is
rejected 78× relative to 7.79 Hz. DF = **1.000 through ×4** (kit scale: Honda 1.00, V75 1.45, V80 3.27).

## V90 DECISION — uniform ×3, and the hazard is NOT where it looks

**Clamp-binding column amplitude (deg), per row × frequency, `×1 / ×3`:**

| row | k@×1 | k@×3 | 7.79 Hz | 21.09 Hz | 28.1 Hz |
|---|---|---|---|---|---|
| **0 km/h** | 0.1600 | **0.4799** | 4.497 / **1.499** | 0.678 / **0.226** | 0.414 / **0.138** |
| 20 km/h | 0.0933 | 0.2799 | 7.709 / 2.570 | 1.162 / 0.387 | 0.710 / 0.237 |
| 90 km/h | 0.0320 | 0.0960 | 22.48 / 7.494 | 3.390 / 1.130 | 2.072 / 0.691 |

🛑 **The 20/90 km/h rows are the SAFEST under uniform scaling** (lowest `k`) — the intuition that they are
the risk is backwards. **The real exposure is `creep × 28 Hz`: binding falls 0.414° → 0.138° at ×3**, and
grind #2 is recorded as "creep cornering", so that combination is live. At 7.79 Hz the margin is fine
(1.499° vs 0.96° measured = 1.56×). ⇒ **the saturation abort rung must be sized for creep×28 Hz.**

**Chose UNIFORM ×3 over flatten and over a hybrid, three reasons** (the third is the strongest and is
independent): ① the grind is fixed, so the upper rows have no symptom to serve — flatten aims at the
wrong target now; ② a hybrid (all rows → 29490 = ×3/×5.14/×15, all int16-legal) makes it a two-variable
experiment; ③ **uniform scaling preserves Honda's schedule SHAPE exactly, so the speed-gradient of wheel
feel is unchanged** — flatten and hybrid both introduce a new speed-dependence the operator would have to
disentangle from the dose.

**Probe:** b7 sign · b6 `|x|≥32` · **b5 `|x|≥128` = DOSE** (undosed 73–109 straddles from below, dosed
220–327 clears) · **b4 `|x|≥511` = SATURATION/ABORT** (exact, because the lane is hard-clamped there;
abort if >5 % of engaged frames).

## 🛑🛑 THE REQUIREMENT AND THE MEASUREMENT ARE INCOMMENSURABLE — both struck as sizing inputs

The `ring/Q` requirement is in **column-torque counts**; `|gp-0x6b26|` is in **aggregator/motor-command
counts**. Converting needs the `cmd → column` plant, which **cannot be measured on this car**: the engaged
estimator returns a **negative group delay (−8.75 ms)**, proving it is feedback-dominated, and the fit was
refused at the pre-registered coherence bar (max γ² = 0.475).
⇒ **my "implied multiplier 0.40×/0.08×" was comparing two unit systems and is VOID**, and so is the
"~29 counts" target. **What survives is the safety envelope, which lives entirely in one unit system**:
DF, clamp margin, int16 ceiling, zero-reject — all computed at `gp-0x6b26` in aggregator counts.
⇒ **V90 is sized to the SAFETY LIMIT, not to a computed requirement.** That is a weaker kind of claim than
V85's "the lever delivered 7.21×" and should be stated as such.

Related: [[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] (whose §Phase estimate flagged
this as BELIEF — now upgraded and the fs ambiguity bounded),
[[reference_accord_factorb_index_selector_c6498_and_torque_axis_census]],
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]].
