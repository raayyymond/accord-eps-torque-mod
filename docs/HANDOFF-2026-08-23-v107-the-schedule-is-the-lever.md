# HANDOFF 2026-08-23 — V106 EXTINGUISHED THE MODE AT LOW SPEED; THE SCHEDULE IS THE REMAINING LEVER

**Session:** score route `a6` (V106) → V107 built. Four subagents: `a6-score`, `mechanism`,
`feedforward`, `friction-sign`. All confirmed stopped from the harness before any collateral was
written.

**Predecessor:** `docs/HANDOFF-2026-08-22-v106-the-damper-and-the-one-mode.md`.

---

## 0. THE ONE-PARAGRAPH VERSION

V106 flew as route `a6` — 1,224.0 s engaged, fault-free — and **extinguished the 21–27 Hz mode at
low speed**: prominence 1.51 against stock's 1.46, with the argmax following the search-band edge
exactly as stock's does. The 18–30 Hz ratio **cleared its own within-drive split-half null, the
first band-power result in this kit's history to do so.** The operator reports the grinding
attenuated in all three of his scenarios. **RULE 7 is closed** — the car demonstrably reads modes
26/27 when engaged. The residual is a ~27 Hz line **above ~70 km/h**, which is exactly where
Honda's own speed taper makes V106's dose 4.2× weaker than at creep. The uniform dose axis is
**exhausted** (int16 ceiling ×3.3335; V106 is at ×3.0 = 90 % of the floor), so **V107 reshapes the
speed schedule instead** and re-aims the 427 telemetry tap at the cell that will size V108.

---

## 1. WHAT V106 DID — measured

### 1.1 The mode is gone at low speed [EVIDENCE]
Engaged, <16 km/h, at the operator's max-demand arm (|e4tq| ≥ 1600), 4 s Hann, 30 s-block bootstrap:
```
             peak Hz   PROMINENCE   18-30 RMS   argmax vs search-band edge
STOCK 1x      18.23       1.46        0.3121    follows the edge   <- no line
V104 6x       22.23       6.89        7.6624    pinned             <- a real line
V105 notch    20.48       3.42        5.6967    pinned             <- a real line
V106          18.23       1.51        3.7255    follows the edge   <- NO LINE
```
Two independent within-spectrum signatures of "no line present": stock-level prominence, and an
argmax that wanders with the search window instead of staying pinned.

**It clears its own null — the first time in this kit's history.**
```
18-30 RMS   a6/V105  = 0.347   a6's own split-half null [0.482, 1.982]   CLEARS
18-30 RMS   a6/V104  = 0.294                                             CLEARS
18-30 RMS   a6/STOCK = 5.735                                             CLEARS  <- positive control
PROMINENCE  a6/V105  = 0.425   null [0.452, 2.280]                       CLEARS (marginal)
```
a6's null is [0.48, 1.98] where a5's was [0.26, 3.8] — the exposure is what made it decidable.
The a6/STOCK row is the positive control: the instrument has not gone dead.

🛑 **The confound that was cut.** a6's engaged LKAS command is ~4× smaller than a5's at p90
(|e4tq| p90 791 vs 3341) and the mode is command-driven, so "the band collapsed" was equally
consistent with "openpilot didn't push". Re-run in cells of (speed) × (**absolute** |e4tq|),
weighted geometric mean over 7–8 matched cells, the result survives.

### 1.2 Prominence by regime — and where the residual is
```
regime                V104 -> V105 -> V106   (stock)
low                   12.5    4.2     2.0     (2.5)   <- AT STOCK
mid                    4.3    5.9     3.2     (2.4)
hwy 40-95             13.3   24.0     6.5     (1.3)   <- THE RESIDUAL
hwy-matched 55-70      6.1    5.1     1.4     (1.6)   <- AT STOCK
```
**The residual is above ~70 km/h** [EVIDENCE, within-drive]: 55–70 is measured *at stock* (1.4 vs
1.6), and a6's engaged exposure inside 40–95 is 95.2 s (40–60) + 129.3 s (60–80) against 230.7 s
(80–100) + 547.3 s (100+), so the pooled 6.5 must be carried by the >70 portion.

### 1.3 RULE 7 IS CLOSED [EVIDENCE]
🛑 A **pooled** `b5` duty is the wrong estimator — `gp-0x6b26 = K·α` where α is what K damps, so in
a stable closed loop the product is invariant to K (V91/V92 measured 0.99). **Conditioning on
measured α removes the ambiguity.** `b5` duty at matched α:
```
             <30    30-60  60-120 120-250 250-500 500-1k  1k-2k  2k-4k
V104 (x1.5) 0.1578 0.2449 0.3662 0.4400 0.3397 0.2143 0.1270 0.0518
V105 (x1.5) 0.1686 0.2851 0.4390 0.5045 0.4112 0.2460 0.1278 0.0442
V106 (x3.0) 0.1245 0.1724 0.2291 0.2686 0.2357 0.1548 0.0890 0.0275
a6/a5        0.716  0.603  0.534  0.552  0.605  0.643  0.711  0.555   8/8 below 1, sign p=0.0039
```
Within-drive engaged-vs-manual (mode 24 is the built-in control): engaged **0.1907** vs manual
**0.4509** = **−0.2602**, against a5's **+0.1031**. ⇒ **The car reads modes 26/27 engaged. Every
earlier `0xCBE74`-family result becomes interpretable and the V91/V92 mode-record suspicion is
cleared.**

**Q7 closed too:** the ×1.5 WAS in force. Delivered multiplier **1.68× [1.16, 1.88]** vs V105 —
excludes both 1.00 and 3.00. V106 was a genuine ×2 step.

### 1.4 The steering-rate cost is an ACCELERATION PENALTY, not a slew ceiling [EVIDENCE, 3 lines]
- **No rail.** Top of a6's engaged |rate_c| histogram is single-count singletons; share within 5 %
  of p99.9 is a6 **0.00141** vs a5 0.00159, a4 0.00157, r73 0.00263 — a6 is the *least* piled up.
- **Steady state intact.** Under held high demand, <16 km/h: a6 p50/p90/MAX = 26/142/311 vs a5's
  33/225/372 and a4's 24/136/281. **V106 ≈ V104.** That is what `H(0) = 0` predicts.
- **Acceleration is what fell.** |d(rate)/dt| p90: <16 2984→2326→**1517**; 40–70 2731→2529→**657**.

At matched **absolute** max demand (≥2200) and <16 km/h, achieved rate p90: V88 326 · V104 166 ·
V105 229 · **V106 157**. ⇒ **~30 % of peak steering rate given up vs V105, landing back at V104's
level.** A finite manoeuvre does pay; it just does not pay it as a ceiling.

### 1.5 The ratchet is LKAS-DEMAND-driven — a new discriminator [EVIDENCE, within a6]
```
                  rho(demand)   PARTIAL | motor rate        PARTIAL | speed
LINE (7.4-8.6)      +0.3957   +0.1139 [+0.0374,+0.2548]        +0.3342
CARRIER (21-28)     +0.5877   -0.2154 [-0.3191,-0.0747]        +0.6277
PLACEBO (32-38)     +0.5129   -0.1772 [-0.2995,-0.0155]        +0.5855
```
**The LINE is the only band with a positive residual demand association after partialling out
motor rate**; carrier and placebo both go negative. Stratified inside rate bands: 0–5 °/s
0.0024→0.0357 [4.64, 30.04]; 5–15 °/s 0.0405→0.9125 [4.83, 65.54]. **2/2 strata, both CIs exclude
1, placebo flat.** ⇒ the operator's *"ratcheting is still present during high LKAS demand"* is
confirmed **and it is a DEMAND effect, not the historical rate effect.** This is the cleanest
target in the drive for after the grinding.

---

## 2. V107 — WHAT WAS BUILT AND WHY

```
image  c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45
.rwd   78eae7da20a87f1a95295eca11da0d08f4cf2b3b823785594cde4be93a7b24ff
file   39990-TVA,A160-V107-V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3-0x13000-0x100000.rwd
builder analysis-2020accord/build_v107_tva.py, 55/55 assertions, BASE = V106
```
**E1 — RESHAPE B.** `0xD7A5C` / `0xD7A6C`, modes 26/27 only, X untouched:
`(-29490, -17202, -5898)` → `(-29490, -24000, -16000)`.
**E2 — the 427 tap re-aimed.** `0x55DF2` `7a 94` → `d4 93` (gp-0x6b86 → **gp-0x6c2c**);
`0x55E10` `a4` → `a3` (sar 4 → **sar 3**).
10 payload bytes + 8 CRC = 18 bytes vs V106. **Zero unattributed vs stock.**

### 2.1 Why a reshape and not more dose — THE UNIFORM AXIS IS EXHAUSTED [EVIDENCE]
Y is signed int16 (`struct.pack_into("<3h", …)`). Y[0] stock = −9830 ⇒ **k_max = 32768/9830 =
3.3335**, and V106 at ×3.0 is at **90.00 %** of the floor. ×4/×5/×6 stock are **int16 overflow**,
not merely risky. Room to the floor: Y[0] ×1.11 · Y[1] ×1.90 · **Y[2] ×5.56** — and Y[2] is the
≥90 km/h knot, i.e. exactly where the residual line is.

### 2.2 Why B and not A — A IS RELAY TERRITORY [EVIDENCE, constant-free]
`|b26|_X(v) = |b26|_measured(v) · Y_X(v)/Y_route(v)` — measured wire × a ratio of two flash
tables. No `>>24`, no `0x111`, no reconstruction. From r77 (×1.0, **undamped** = conservative):
```
variant       <16      16-40     40-70     70-90
V106 today  0.00643   0.00044   0.00007   0.00000
RESHAPE A   0.01871   0.00519   0.01174   0.06223   <- 6.2 % at 70-90.  RELAY TERRITORY.
RESHAPE B   0.01218   0.00180   0.00255   0.01048   <- <=1.05 % everywhere
RESHAPE C   0.01871   0.00414   0.00607   0.03391   <- 3.4 % at 70-90
```
On a6's own (damped) α, B holds **≤0.09 %** at ≥70. **B's clamp knee (1963) sits above r77's
undamped 70–90 p99 of 1836** — safe against the worst distribution the corpus has ever measured,
not merely the damped one. And **route a6 spent 809 s of its 1,224 engaged seconds above 70 km/h**:
this is the majority of the operator's engaged driving, not a rare corner. V80's damper lived at
97 % of ceiling and produced the worst grinding ever recorded — *"does not clip" and "is not a
relay" are different statements.*

**Delivered coefficient after Honda's LERP** (X = (0,1280,5760) counts at 64 counts/km/h):
```
                  5 mph    20 km/h   50 km/h   >=90 km/h   ratio @90+
V106            -24546     -17202    -12358     -5898        1.00x
RESHAPE B       -27282     -24000    -20572    -16000        2.71x
```
**Y[0] is byte-identical** ⇒ creep clamp duty and the relay index are unchanged *by construction*,
and only 4 bytes per row actually change — the diff proves the creep dose did not move.

### 2.3 Why the tap moved
The 427 tap watched `gp-0x6b86`, the biquad lane — a filter this session decided not to build on.
Meanwhile **no route has ever measured `gp-0x6c2c` above 90 km/h at anything near V106's dose**
(r77 has 1.1 s there; r78 has 99.8 s at ×1.5), and every duty number in §2.2 rests on that cell.
`gp-0x6c2c` strictly dominates `gp-0x6b26` as a tap: `|gp-0x6b26|` is bounded at ±511 *by
construction*, so the moment it matters it censors exactly the information needed — it can say
*that* you clamped, never *how far past*. From `c2c`, `|b26|` is computable exactly (Y_eff is in
flash, the clamp is known) **plus** the headroom for any candidate Y.

**Scaler `sar 3`** — LSB 8 counts, full scale 8184, against a measured corpus max of 5,286:
```
shift  LSB  full scale  clip frac  clip frac of the p99.9 tail  p99 in LSBs
sar 2    4        4092   0.000012          0.011765                 280
sar 3    8        8184   0.000000          0.000000                 140
```
`sar 2` doubles resolution but clips **1.18 % of the p99.9 tail**, and the tail is the whole point.
Measured `|gp-0x6c2c|` engaged (r77+r78 pooled, n = 169,449): p50 40 · p90 323 · p99 1,121 ·
p99.9 1,922 · max 5,286.

### 2.4 PRE-REGISTRATION — the sentence a null will license
> *V107's drive must measure `|gp-0x6c2c|` and the resulting clamp duty above 70 km/h — the band
> where the residual line lives, where the reshape does all its work, and where no route in this
> corpus has ever measured this cell at a comparable dose. V106's own drive could not answer it
> because its tap was pointed at `gp-0x6b86`.*

**No cave edit.** The cave is byte-identical to V106, so `b5` still means exactly what route a6
measured it against, and the dose still reads itself out.

---

## 3. THE DRIVE CARD FOR V107 — what the logs must answer

1. **Prominence and 18–30 RMS at ≥70 km/h**, against a6 in matched (speed × absolute demand) cells,
   with the within-drive split-half null run FIRST. **This is the primary band endpoint.** V106
   already put low speed and 55–70 at stock; ≥70 is the only place left to move.
2. **`|gp-0x6c2c|` percentiles and clamp duty at ≥70 km/h**, off the new tap. Sizes V108. If duty
   is materially above ~1 %, V108 must not push the schedule further.
3. **`b5` at matched α**, engaged vs manual. The dose readout is unchanged, so it should shift again
   in proportion; a flat result means the reshape did not land.
4. **The operator's report, per scenario** — 5 mph, hard manual turns, highway. **The primary
   readout.** In his words: grinding / vibrating / micro-ratcheting / ratcheting / excess friction.
5. **Steering rate at ≥70 km/h** — the reshape's cost lands there, not at creep. Distribution and
   maximum of |d(angle)/dt| at high demand, plus |d(rate)/dt|.
6. **The ~8 Hz ratcheting LINE vs demand**, replicating §1.5 within the new drive.
7. **Fault-free confirmation**, rung duties, engaged exposure and speed census.

🛑 **AND THE ONE THAT NEEDS NO BUILD, open since the V105 handoff and now the highest-value item:**
**the alternating drive** — ~30 s engaged / 30 s manual at 5–15 km/h, same road, same session,
sweeping command hard and soft. It would close the ~8 Hz LINE null (a6 had only **7** engaged
episodes, one of them 941.6 s), supply the <16 km/h pitch-vs-amplitude cell (30 and 46 windows —
failed for exposure), and give an engaged/manual matched contrast above 25 km/h, which a6 does not
have (0.0 s of manual driving in 25–60 km/h).

---

## 4. THE ARCHITECTURAL FINDING — the feedforward lane already exists

**The operator's ask:** *"add a separate feedforward path… to allow more LKAS-driven demand going
to the EPS motor torque aggregate while continuing to mute or filter the steering wheel feedback."*

**Answer: Honda already built it, four channels already use it, LKAS is not one of them, and moving
LKAS onto it is ONE calibration byte.** `FUN_00026c80` (task 1, 1 kHz, slot `0x15`) routes each of
11 assist channels on the cal table `0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`:
```
                    slot request  gp-0x62f8[i]
                  ROUTER  0xC4124[i]
       mode 0 ──────────┴────────── mode 5
          |                            |
    gp-0x62b0[i]                  gp-0x62c8[i]
    Σ → gp-0x6b4c                Σ → gp-0x6b4e → gp-0x6afe
          |                            |
  🔴 AGGREGATOR FUN_0003aa2c (11 unweighted adds: LKAS + every damping term)
  🔴 GOVERNOR   FUN_0004503c (authority xB, slew ±512/±205)
  🔴 comp-add, 🔴 shaper (Q15 blend scaled by |gp-0x3570>>15| x 1092>>10)
          └──────────────┬─────────────┘
                  sum @ 0x43af4  →  clamp ±gp-0x4f64  →  ±0x2000  →  gp-0x6b98  →  FOC
```
🛑 **CORRECTION OF RECORD.** `accord-gp6b4c-is-an-11-slot-assist-sum` says modes (1,2,5,7) → 0 ⇒
slots {2,4,5,9} FORCED ZERO. **Half right: modes 1 and 2 really do zero; modes 5 and 7 RE-ROUTE.**
Slots {2,4,5,9} are not dead — **they are already on the feedforward lane.**

**Verified by the orchestrator directly** (decompile of `FUN_00026c80`, program `code.bin`):
mode 5 differs from mode 0 in **exactly four writes** — `gp-0x62b0[i]`/`gp-0x4b40[i]` → 0 and
`gp-0x62c8[i]`/`gp-0x4b58[i]` ← request — with `gp-0x6298`, `gp-0x4b28`, `gp-0x6170`, `gp-0x617c`,
`gp-0x625c`, `gp-0x6324`, `gp-0x61e8`, `gp-0x4af8`, `gp-0x61d0` written identically in both.
**LKAS is slot 1**: `FUN_0002b422` reads `gp-0x6b3c`, sets `local_1c = 1`, calls `FUN_00025c32`.

### 4.1 Gates
- **GATE 1 — ownership.** `0xC4124`: 5 readers, **0 writers**. `0xC4118`: 10 readers, **0 writers**.
  Both by Ghidra AND an independent Python LE scan, **set-difference empty**. No new RAM is
  allocated; the four touched cells are written by `FUN_00026c80` itself, both halves of both
  shadow pairs, in the same basic block. **The `gp-0x1500`-class runtime-index risk does not apply
  — there is no new cell.**
- ⭐ **The second reader of each table is the ASIL float plausibility monitor `FUN_00027b0a`, which
  dispatches on the SAME byte** ⇒ it follows the re-route by construction. **No monitor divergence
  is possible.** This is the single most important safety property of the lever.
- **The authority gate is UPSTREAM** [orchestrator-verified in `FUN_00025c32` @`0x25c32`–`0x25c7c`]:
  the very first thing the function does is compare `gp-0x69aa` against `0xC40F4[slot]` and, below
  threshold, zero `gp-0x62f8[i]` — **the cell the router reads for BOTH lanes.** The cutoff is
  inherited, not bypassed.
- **The `×B` cost is bounded.** `FUN_00049a78` is `min(a,b)` and the authority chains are
  min-cascades seeded at `0x8000`, so uninhibited requires `A·B ≥ 29491/32768 = 0.8999` ⇒
  `B ≥ 0.8999`. **The direct lane can be at most +11.1 % hotter, in a narrow band.**
- **Downstream neutrality:** `FUN_00038148` reads BOTH lanes 16 bytes apart, weights `0xC63AA`
  (gp-0x6b4c) and `0xC63A8` (gp-0x6b4e) **both 1024 = unity on stock AND V106** ⇒ the move is
  exactly neutral for the reference-model output `gp-0x6ad6`.

### 4.2 🛑 What it does NOT buy — retracted this session
**Retracted:** *"Every count of damping is a count of LKAS authority, exactly."* Two errors:
(a) it is only true AT the ±0x2800 clamp, and V105's `b6` read **0.000000 across 65,959 frames**,
meaning `|gp-0x6b94|` never even reached the lower `gp-0x4f64` ceiling; (b) worse, the count-for-
count subtraction is a property of the **final add `cmd = ff + agg` at `0x43af4`**, which is
downstream of BOTH lanes — **so it survives the lane move unchanged.** Moving LKAS does **not**
stop the damper opposing it, and **does not buy back the steering rate.**

**What it does buy, strongest first:** ① LKAS leaves the shaper's integrator/blend chain — a
**state-dependent modulation of LKAS by an integrator's magnitude** — and becomes algebraically
flat from `gp-0x62f8[1]` to the final clamp. That is the closest thing to *"unfiltered LKAS demand
driving the EPS target torque"* the architecture admits. ② It decouples LKAS from the shared slew
budget (a coupling, never a cap: LKAS's own max increment is ~78 ct/tick against a 205 ct/tick
limit). ③ **No extra authority** — the lane max stays `(0xC61BE × gain) >> 15` = **2505 counts at
6×**. **Rank 1 is a topology change, not an authority change.**

⊕ **[BELIEF, untested, and the reason to run it soon]** A state-dependent gain in the loop is
exactly the ingredient that produces an amplitude-dependent crossover. If that integrator-scaled
blend IS the amplitude-dependent gain, moving LKAS off it is a **grinding** lever, not just a rate
one. `gp-0x3570` is not telemetered; nothing in the existing corpus can test it.

### 4.3 The other ranked options
- **Rank 2** — flatten `0xC520C`/`0xC5224` bank A (Y = [5325,3584,2406,1587,512], a **10.4×
  collapse with motor rate**). Cal-only; **precedent: V41's CHANGE 2 booted and drove cleanly.**
  Keep the two mirrors identical (the fault-0x17 monitor trips on them disagreeing *between
  cycles*, never on the value). **SHARED** — raises the ceiling for the damping terms too.
- **Rank 3** — `0xC61BE` (15360). Conditional on the pre-gain LERP output actually reaching it,
  never measured.
- **Rank 4** — a cave at `0x43ae0`. **Strictly dominated by Rank 1.**
- **Rank 5** — `0xC64C8` = 1. Listed for completeness, **not recommended.**

🛑 **Shadow-lockstep pairs: `FUN_00028d22` protects EIGHT per-slot arrays × 11 slots, plus
`gp-0x4f64`/`gp-0x448a`. Treat "at least six pairs" as badly stale.**

---

## 5. THE FRICTION AUDIT — `0xC40D2` = 204 makes the wheel LIGHTER

**Answer: LIGHTER. The memory's CONCLUSION survives; its SIGN CHAIN does not.** It was right for
the wrong reason — two errors that cancelled — which is worse than being wrong, because the
reasoning breaks the moment anyone reuses it.

🛑 **`gp-0x6752` is not "a negation in the PID". It is the DRIVER-FRAME ↔ AGGREGATOR-FRAME
CONVERTER**, applied at exactly the 7 places a signal crosses between frames: `0x3B92E`, `0x3B91C`,
`0x381EE`, `0x3668E`, `0x358C2`, `0x3AB78`, `0x3A71A`. **Count FRAME CROSSINGS, never negations.**
The golden model already *names* it `assist_polarity`; the kit had the right name and never joined
it to the frame story.

**The self-checking argument, which needs no parity count:**
```
u  = POL·K·(Ts − Tref)          [FUN_0003a382 @0x3A874]
Ts = P·u + Text                  [plant]
Ts = (L·Tref + Text)/(1+L),  L = −P·POL·K
```
`L > 0` is forced physically — at `L < 0` the loop amplifies `Text`; at `L < −1` it runs away. The
car assists and does not run away. ⇒ `dTs/dTref = L/(1+L) > 0`: **`gp-0x6ad6` IS a target felt
effort, and lowering it lightens the wheel.**
⊕ **Cross-check:** this predicts `d(gp-0x6b94)/d(gp-0x6b70) > 0`; the kit MEASURED
**+0.2529 / +0.2565 / +0.2617** with a passing positive control.

**Consequences:** K1 = 204 is **not** a source of the steady "excess friction" complaint, and
**reverting it would make the wheel HEAVIER** — the wrong way. It **cannot** rate-limit a 6× LKAS
command (LKAS enters via `gp-0x6b4c` directly into the aggregator; K1 only moves the PID's
reference). ⚠ **The one honest route by which 204 could still feel bad:** Coulomb friction flips
sign at every reversal, so larger K1 = larger **step at each reversal** — notchiness on turn-in,
not steady drag. Transient, unmeasured, and V89's own docstring pre-registered it.

🛑 **A premise in the orchestrator's own brief was WRONG:** V81's *"removes drag the operator is
used to"* was **EDIT 2, the ×1.5 friction TABLE** (14 mode-record sites `0xCF6E0…0xD9A6C` behind
`0xCBE74`, feeding the `gp-0x6b26` lane) — **not** `0xC40D2`, a `tp`-block scalar in the plant model
in `FUN_0003b8f6`. **Two different mechanisms sharing the word "friction."** V81 never touched
`0xC40D2` (204 on V89/V98/V100/V104/V105/V106; 102 on stock).

---

## 6. RETRACTIONS AND CORRECTIONS THIS SESSION

| # | claim | status |
|---|---|---|
| 1 | *"V106 reduced the effective inertia of the mode"* (orchestrator) | **DEAD.** Phasor-sector argument: the term's torque phasor lands in 180–270° or, sign-flipped, 0–90°. Raising a resonance while damping it needs 90–180°, unreachable in **either** polarity. Sign-independent. |
| 2 | *"Attenuation and pitch-rise are the same knob"* (orchestrator, relaying `mechanism`) | **DEAD.** Three builds, three best-powered cells, all excluding −1.93 Hz/e-fold. V106 ≥70 km/h (n=405): **+0.391 [−0.386, +0.607]**. |
| 3 | *"Move the EMA poles into the 90–180° sector"* (orchestrator) | **DEAD, and closed permanently.** Geometrically reachable, but `\|H\|` costs 1.9–7.1× and Y can only buy back ×1.111 (int16). Best reduced-inertia on the whole grid is 0.90 vs today's 6.22 added inertia — 6.9× smaller. |
| 4 | *"`gp-0x671a >= 5` bypasses the mode records at highway"* (orchestrator) | **DEAD.** It is the oscillation detector's half-cycle counter; needs 5 crossings of `\|gp-0x6c2c\| > 12,800` against a corpus max of 5,320. Its decay is gated on speed being HIGH ⇒ a bypass would be a *creep* phenomenon. And `0xC640A` is byte-identical V105/V106, so fallback frames contribute ratio 1.00 — yet the measured ratio is 1.68, CI excluding 1.00. |
| 5 | `mechanism`'s **9.98 %** clamp duty at <16 km/h | **REFUTED, 10–16× high.** Model-free: r77's measured wire × 3.0 gives **0.643 %**; S1-like **1.00 %**; r78 at matched dose **0.00000**. The pre-registered ~1 % was right. **50× more clamp headroom than assumed.** |
| 6 | `mechanism`'s *"highway α is smaller than creep α"* | **BACKWARDS.** Measured r77 p99: <16 = 1183, 70–90 = **1836** ⇒ **1.55× creep**. a6 corroborates at 1.74–1.94×. This is why A's ≥70 cell is worst in every table. |
| 7 | `feedforward`'s *"every count of damping is a count of LKAS authority"* | **WITHDRAWN** (see §4.2). Conditional on the clamp binding, and it is a property of the final add, so it survives the lane move. |
| 8 | `feedforward`'s *"LKAS is hard-dropped below 90 % authority"* | **Too strong.** It sets an inhibit flag **with hysteresis**; what it does depends on the request-type byte. Identical for both lanes either way. |
| 9 | `a6-score`'s commissioned **bimodality test** | **KILLED BY ITS OWN CALIBRATION.** Fires at f = 0, silent at f = 0.25. Expected cluster separation 1.28 sd ⇒ one broad hump, not a valley. |
| 10 | `a6-score`'s a6 `c2c` reconstruction (its §2) | **RETRACTED before it was read.** The α→\|b26\| law was fitted pooled over speed, so dividing by `Y_eff(v)` double-counts the schedule. |
| 11 | `mechanism`'s *"`0xC64B0` off-by-0x1000, sixth recurrence"* | **NOT A DEFECT.** The memory already carries that correction, at step 5 and in its caveat block. No sixth recurrence entered the record. |
| 12 | The orchestrator's brief citing **V81** as a friction-polarity control | **WRONG LANE.** See §5. |
| 13 | *"`0xC640A` is a better lever than the reshape"* (orchestrator) | **WRONG.** A two-byte edit into a branch the car does not execute. And **not virgin**: V93/V94 cut it ×0.75; V94 flew as route `7d` and was aborted — *"not safe to drive"* — confounded with a mode-record cut in the same build. |

---

## 7. DEFECTS FOUND IN THE RECORD — reported, deliberately NOT silently patched

1. 🛑 **THE GOLDEN MODEL IS SEEDED WITH THE WRONG POLARITY.** `eps_chain_core.py`:
   `assist_polarity: int = 1`, contradicting `accord-gp6752-is-negative-one` (★★★★★, verified 3
   ways including on-car). **Nothing anywhere overrides it** — it is a dataclass default — so every
   `_demo()` / `_self_check()` run uses the pre-retraction sign, and 3 call sites in
   `eps_chain_lanes.py` inherit it.
   **NOT FIXED, deliberately.** `_self_check()`'s expected values were themselves computed at +1
   (e.g. `_inline_torque_rate_b(st) == 1533`), so flipping the default breaks them — and editing
   *those* to match the model's new output would make the test agree with the code by construction
   and destroy its value. **The fix is re-deriving those expectations FROM THE FIRMWARE.** A loud
   defect note is now in place at the field. **Contract re-verified intact: 2,512 B,
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`.**
2. 🛑 **`docs/BUILD-LINEAGE-CATCHUP-V76-V100.md` still says V100 is "BUILT AND NOT FLASHED".**
   **V100 FLEW as route `0x85`, 2026-08-13**, and `STATE.md` already flags the row as stale. That
   row's own text warns the kit has shipped **ten** stale flight-status rows; this is the eleventh.
   ⭐ **And V100 carried a comparator on `|gp-0x6ad6| ≥ 8192` — the exact rail that decides whether
   `0xC40D2`'s dose is merely small or structurally ZERO. Its duty was never harvested, and route
   `0x85` is on disk.**
3. **`accord-gp6b4c-is-an-11-slot-assist-sum`** — modes 5/7 re-route, they do not zero (§4).
4. **`accord-friction-polarity-more-friction-is-more-assist`** — conclusion stands, sign chain
   replaced (§5). Replacement text is in the memory file.
5. **`memory/MEMORY.md` points at `accord-friction-polarity-more-assist.md`; the file is
   `accord-friction-polarity-more-friction-is-more-assist.md`.** Broken link.
6. **`gp-0x4f62` is `d(gp-0x4f60)/dt`** (`FUN_0007e74a` @`0x7E860`, ring-buffered N-sample finite
   difference), **not a second torque channel** — it is r24's input. The golden model has this
   right (`col_torque_rate`); flagged because the aggregator's `iVar21` *reads* as base assist and
   is not. The real base-assist map is `gp-0x6b86` (`FUN_000352b4`), carrying `POL` at `0x358C2`.

---

## 8. THE INSTRUMENT LESSON OF THIS SESSION

⭐ **A STATIONARY MODE RETURNS A FAKE FREQUENCY-vs-AMPLITUDE SLOPE.** Injected at a ladder of
amplitudes into a6's own manual-driving noise, through the identical binning + argmax pipeline:
```
injected 22.0 Hz -> vs log(BAND RMS) -0.000 Hz/e-fold | vs log(TRUE amp) -1.138
injected 20.0 Hz -> vs log(BAND RMS) -0.000           | vs log(TRUE amp) -0.759
injected 26.0 Hz -> vs log(BAND RMS) +0.000           | vs log(TRUE amp) +1.731
```
**Against band RMS the artefact floor is ZERO. Against an INDEPENDENT amplitude axis it is ±1.7 Hz
per e-fold, and the sign tracks (band centre − mode frequency).** Lineless low-amplitude windows
scatter their argmax to the band centre.
🛑 **`accord-f0-crossover-is-the-endpoint`'s −1.93 Hz/e-fold was measured against COMMAND amplitude
— an independent axis — and therefore sits inside that artefact's range.** It is **not** retracted
here: `f0` is a `Re(Z)` zero-crossing, not an argmax, and that estimator has not been calibrated.
**But the same family has already produced `q_of` = 79 and Q = 36.2 on white noise. Push a
stationary synthetic through the actual `Re(Z)` f0 code before −1.93 sizes anything.**

⊕ **And a lesson for the orchestrator:** `eps_chain_core.py` already documented `gp-0x671a`
correctly — *"reads 0 during smooth steering; `>= 5` means AN OSCILLATION IS HAPPENING"* — and
`accord-gp671a-blast-radius-not-a-free-lever` already named `FUN_00036c12` as a reader **and named
`0xC64FD` as its gate**. **The golden model and the memory had the answer to the gate hypothesis
before it was raised.** Grep both for a cell before building a theory on it.

---

## 9. OPEN ITEMS, WITH WHAT WOULD CLOSE EACH

| # | open item | what closes it |
|---|---|---|
| 1 | 🛑 **The alternating drive** — open since the V105 handoff | ~30 s engaged / 30 s manual at 5–15 km/h, same road, same session, command swept hard and soft. **No build needed.** Closes #2, #3, and the engaged/manual contrast above 25 km/h. |
| 2 | The ~8 Hz ratcheting LINE ratio is NOT-CURRENTLY-DECIDABLE | a6 had **7** engaged episodes (one 941.6 s). Many short runs, not one long one. |
| 3 | Pitch-vs-amplitude at <16 km/h — the operator's own grind-#1 regime | 30 and 46 windows on V105/V106. Same drive. |
| 4 | **The `Re(Z)` f0 estimator has never been calibrated** | Stationary synthetic at an amplitude ladder through the actual f0 code. Bears on a ★★★★★ memory used for sizing. |
| 5 | **V100's `\|gp-0x6ad6\| ≥ 8192` rail duty never harvested** | Route `0x85` is on disk. Decides whether `0xC40D2`'s dose is small or structurally zero — i.e. whether it can be reverted freely. |
| 6 | Golden-model `assist_polarity` | Re-derive `_self_check()`'s expectations from the firmware, then flip the default and update the contract hash in `CLAUDE.md`. |
| 7 | The feedforward lane (`0xC4124[1]` 0→5) — **V108 candidate** | A drive. Gates cleared except: degraded-mode behaviour of the direct lane is bounded (≤+11.1 %) but not *observed*; and channels 2/4/5/9 are unidentified, so whether Honda dimensions that lane for full-scale requests is unknown. |
| 8 | Does the aggregator's ±0x2800 clamp ever bind under high driver torque? | A `\|gp-0x6b94\| ≥ 10240` rung, stratified by `\|gp-0x4f60\|`. Cheap insurance; **do not price Rank 1 on it.** |
| 9 | Does `gp-0x4f64` ever bind on the FINAL sum? | `b6` tested the *pre-governor* comparison. Probe `\|gp-0x6afe + uVar34\| ≥ gp-0x4f64` at `0x43afe` + a raw tap on `gp-0x6ac0`. The "223 °/s knee" is a reconstruction, not a measurement. |
| 10 | Is `0xC61BE` = 15360 ever reached pre-gain? | Decides whether Rank 3 does anything. |
| 11 | The ratchet is demand-driven — mechanism unknown | The next target after the grinding. §1.5 is the discriminator. |
| 12 | `\|gp-0x6c2c\|` above 90 km/h at a comparable dose | **V107's own drive.** This is what E2 exists for. |
| 13 | Fallback fraction f ≈ 0.10–0.15 pooled, but **0 at 70–90 km/h** | Consistent with estimator bias at low speed; mechanistically the detector cannot arm. Not worth a build. |
| 14 | Coulomb step at reversal from K1 = 204 (notchiness, not drag) | Unmeasured, structural. Would need a reversal-triggered probe. |

---

## 10. HOW V107 DIFFERS FROM THE ARC SINCE V38

```
V38-V52    authority / filters / poles / caves
V53-V61    telemetry probes and lane mutes
V62-V73    the rate lane (r24/r26)
V74-V83a   the base-assist damper        (structurally ZERO in the operator's window)
V84        damper reverted to Honda
V85-V99    observer / plant-model probes
V100-V103  the gain ladder + arming the biquad
V104       c4, a flat lane gain          FLOWN, NULL
V105       the biquad's SHAPE            FLOWN, relocated the mode, did not damp it
V106       gp-0x6b26 Y row x3.0 uniform  FLOWN, EXTINGUISHED the mode at low speed
V107       gp-0x6b26's SPEED SCHEDULE    <- the second axis of the same cell
```
**V106 was the first delivered damping into 18–28 Hz at low speed in 68 builds, and it worked.**
**V107 is not "more of V106" — the uniform axis is arithmetically exhausted at ×3.3335 and V106 is
at 90 % of it.** V107 moves the *shape* of the speed schedule, which is a different degree of
freedom on the same cell, and it is aimed at a band (>70 km/h) that V106 measurably did not fix
because Honda's own taper made the dose 4.2× weaker there.

**Frozen across this whole arc:** `0xC6CD0` = 5346 (the 6× gain — **never lower it**, it scales
excitation, not loop gain), `0xC407E` = 511 (the interlock), the X breakpoints, both MANUAL mode
records, `0xC640A`/`0xC640C`.

**What is genuinely new in V107 vs a re-run:** the *schedule shape* has never been edited on this
cell in 107 builds — every prior touch scaled Y uniformly or not at all. And the 427 tap has never
pointed at `gp-0x6c2c` on any build.
