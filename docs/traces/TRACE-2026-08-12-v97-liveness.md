# TRACE 2026-08-12 — Is the V97 edit (`0xC63AC` 102→150) LIVE or DEAD?

Agent: `GhidraLiveness`. Tooling: GhidraMCP for all disassembly/decompilation; Python for bytes and
flight data. Every claim below is marked **[EVIDENCE]** or **[BELIEF]**.

## Verdict

**The V97 edit is LIVE.** [EVIDENCE] The address is right, the instruction is right, the function
executes, and it executed *on the flown route* — proven from the car's own telemetry, not inferred.

**But the drive cannot have measured it.** [EVIDENCE] Route `0x80` carried **17.19 s of engaged
driving in ONE episode**, at ≤ 6.6 km/h, against a V96 baseline of **615 s / 690 s engaged**. And the
term the pole rotates, `gp-0x374c >> 4`, sat **below the flown probe's own 2048-count LSB on 100.00 %
of 10,749 frames**, so its magnitude — and therefore the dose — is *unresolved on the wire*.

⇒ The operator's "zero difference" is a **null on the EXPERIMENT, not on the LEVER.** Same class as
V64 (the detector never armed) and V92 (the record read ≠ the record written) — but for a different
reason: here the mechanism is confirmed running and the *exposure* is what failed.

---

## 1. Address correctness — REFUTES "mistaken cal address" [EVIDENCE]

**Instruction.** Raw bytes at `0x381FE`–`0x38205`, hand-decoded and cross-checked against Ghidra:

| addr | bytes | hw0 | reg2 | op | reg1 | hw1 | decode |
|---|---|---|---|---|---|---|---|
| `0x381FE` | `24 37 b5 c8` | `0x3724` | r6 | `0x39` | r4 = **gp** | `0xc8b5` (bit0=1 ⇒ LD.W) | `ld.w -0x374c[gp],r6` — **the Stage-1 accumulator** |
| `0x38202` | `e5 6f ad 73` | `0x6fe5` | r13 | `0x3F` | r5 = **tp** | `0x73ad` (bit0=1 ⇒ LD.HU) | `ld.hu 0x73ac[tp],r13` — **the cal** |

Ghidra `search_instructions(operand="0x73ac")` returns exactly this one instruction with bytes
`e56fad73`. The two loads are adjacent, exactly as `builds/v80_v107/build_v97_tva.py` describes.

`tp = 0xBF000` ⇒ `0xBF000 + 0x73AC = 0xC63AC`.

**Byte values** (Python, LE halfword, read from the images on disk):

| addr | stock | V96 | V97 |
|---|---|---|---|
| **`0xC63AC`** | **102** | **102** | **150** |
| `0xC63A0/A2/A4/A6/A8/AA/AE` | 1024 | 1024 | 1024 |

**Off-by-0x1000 excluded two ways.** `0xC53AC` = 683 on all three images (nothing to do with
102/150). Seven independent anchors read their kit-recorded values in the `tp+0x7000` block:
`0xC62EA`=320 (stock), `0xC6316`=640, `0xC6312`=320, `0xC6318`=640, `0xC61DA`=1092, `0xC6422`=16384,
`0xC61DC`=30720, `0xC646C`=891.

**V96 → V97 full byte diff over `[0x13000, 0x100000)`: exactly 5 bytes** — `0xC63AC 0x66→0x96` plus
the 4-byte block CRC at `0xC6FFC`. Single-variable, zero unattributed bytes.

## 2. Reader/writer census — 1 reader, 0 writers, reproduced independently [EVIDENCE]

| method | result |
|---|---|
| GhidraMCP `search_instructions` operand `0x73ac` | **1** hit: `ld.hu 0x73ac,tp,r13` @`0x38202` (183,570 scanned) |
| Python raw LE scan, ops `0x38`–`0x3F`, **both parities**, **any base register** | **5** raw hits, **1** tp-based |
| Python 6-byte extended form `disp=(sext16(hw2)<<7)\|((hw1>>4)&0x7F)`, base tp | **0** |
| Python `movea`/`movhi` with immediate `0x63AC`/`0x63AD` (absolute synthesis) | **0** image-wide |
| `ep`-relative aliasing test: `movea imm,tp,ep` sites | 98 found, **0** with `imm` inside the 254-byte `sld` reach of `0x73AC` |

Adjudication of the 4 excluded raw Python hits — each with a stated reason:

| addr | hw0 | disp | base | exclusion |
|---|---|---|---|---|
| `0x64642` | `ff80` | `73ac` | r0 | base is r0, not tp; also a mid-instruction misalignment inside `FUN_00064438` |
| `0x6E73E` | `07a4` | `73ad` | r4 = **gp** | `gp+0x73AC` = `0xFEDFF3AC`, a RAM address, not a cal |
| `0xBD682`, `0xBE9C2` | `3f40` | `73ac` | r0 | both above `0xBB000` — data/table region, not code |

**Set difference between the two tools is EMPTY.** No disagreement to adjudicate.

## 3. THE CRUX — `FUN_00038148` executes, and it executed on route `0x80`

### 3a. Static gate [EVIDENCE]

One caller only: `FUN_0002214a` @ `0x22676` (`get_function_callers`, `get_xrefs_to`, both agree).
`FUN_0002214a` has no `jarl`/`jr` callers image-wide; it is an **RTOS task entry**, its address
appearing once as a literal at `0xBB928` inside a 7-record task-control table (entries `0x2214A`,
`0x22A88`, `0x22B20`, `0x22B24`, `0x22CA0`, `0x2351E`, `0x14C5C`).

The gate, read from the disassembly of `FUN_0002214a`:

```
0002214e  ld.bu -0x67fa[gp],r13
00022172  andi  0xf,r13,r15
0002217c  shl   r15,r11,r25          ; r25 = 1 << (gp-0x67fa & 0xf)
000221d6  andi  0x830,r25,r28        ; r28 != 0  <=>  gp-0x67fa in {4, 5, 11}
...
000225ee  cmp r0,r28 / be / jarl 0x00026c80   ; the CHANNEL MIXER
0002240e  cmp r0,r28 / be / jarl 0x0003b8f6   ; the observer
00022672  cmp r0,r28 / be / jarl 0x00038148   ; <-- OUR FUNCTION, SAME r28
```

🛑 **`FUN_00038148` shares its guard byte-for-byte with `FUN_00026c80`, the assist-channel mixer.**
If `r28 == 0` the car has **no power assist at all**. The operator was steering, provoking grinding,
with assist present ⇒ `r28 != 0` ⇒ `FUN_00038148` ran. This is a structural argument, not a
speed/mode argument: `gp-0x67fa` is the **EPS's own state**, independent of LKAS engagement, so the
lane is live in manual driving too.

**No speed gate, no rate gate, no engagement gate anywhere on the path to `FUN_00038148`.** The only
in-function gate is `if (gp-0x6bfe + 20000U < 0x9c41)`, i.e. the measured signal in ±20000; failing
it writes the sentinel `gp-0x6b70 = 0x7FFF`. **The accumulator update at `0x381FE`–`0x38230` sits
BEFORE that test and is unconditional.**

### 3b. Dynamic proof from the car [EVIDENCE]

V97 carries V96's cave byte-for-byte, which telemeters (`builds/v80_v107/build_v96_tva.py` payload map):
`0x14A` byte4 b7 = `gp-0x6b70 < 0` · **b6 = `(gp-0x374c>>4) < 0`** · b5,b4 = `Mhi` · b3 = mode rung ·
byte7 b7 = `Mlo` · byte7 b6 = identity constant 1.

Decoded from `_scratch/cache/r80/r80.npz` (pairing `raw14_t` with `raw14_b4`/`raw14_b7`, per the recorded
off-by-one trap), 10,750 frames / 109.2 s:

| check | result |
|---|---|
| identity byte7 b6 == 1 | **1.0000** ⇒ the V96/V97 cave IS on the car |
| mode rung b3 constant | unique = {1} ⇒ MAP VALIDATOR 1 and 2 **PASS** |
| **sign of `gp-0x374c` toggles** | **181 transitions in 109.2 s (1.66 /s)**, 36.7 % negative |
| sign of `gp-0x6b70` toggles | 300 transitions (2.75 /s), 65.8 % negative |
| `probe` (427 magnitude) | min 15, median 143, max 207 — **never 1023** ⇒ the ±20000 gate **never failed** |

**A frozen accumulator cannot change sign 181 times.** ⇒ `FUN_00038148` executed throughout route
`0x80`, in the parking-lot-creep regime, with its output gate passing. **The operator's "the logic we
touched isn't used" hypothesis is REFUTED.**

### 3c. Task rate — SETTLED at 1000 Hz [EVIDENCE], via the on-car anchor, NOT statically

⚠ **First, the trap I nearly published.** OSTM0 *is* armed with a clean round period —
`0x3D8 mov 0x13880,r1` → `0x3DE st.w r1,-0x4000[r0]` (OSTM0CMP = 80,000) → `0x3E4 st.b r1,-0x3fec[r0]`
(OSTM0TS = start), re-armed at `0x14C8E mov 0x1387f,r13` → `0x14C94 st.w` (79,999) inside
`FUN_00014c5c`. **This does NOT settle it, and the kit already knows why**
(`model/eps_lkas_chain_model.py:118-127`): **PCLK is 40 MHz, not 80** (option-byte Table 6-7 forces
`PCLK = HEAPCLK/2`; HEAPCLK 80 MHz pinned by the firmware's own CLMA1 compares `0x0053`/`0x004D` at
`0x5C8D8`/`0x5C8E0`) ⇒ OSTM0 is **2.000 ms = 500 Hz** — and moot anyway, because the EI trampoline
`FUN_0001492a` has **no OSTM0 arm**; `gp-0x42fc`, the rate divider's trigger, is written only by
EIIC `0x340` = TAUJ1I2. **The "OSTM0CMP ⇒ 1 kHz at 80 MHz" chain is a documented red herring at both
ends.** My byte reads reproduce the record's; only the interpretation was the trap.

**Statically from a register value: NOT SETTLED** — TAUJ1's period register is still not located.

**But the on-car anchor transfers to this task, and here is the link that was previously missing:**
* `0xC64DF` = **100** (byte-read from the stock image), measured on-car at 100.00 ms ⇒ **1.000 ms per
  decrement**.
* That counter is read at **`0x29288`, inside `FUN_00028ea6`** — `search_instructions` operand
  `0x74df` returns exactly 2 hits (`0x29288` in `FUN_00028ea6`, `0x2A46A` in `FUN_0002a30e`; bodies
  contiguous, `FUN_00028ea6` = `0x28EA6–0x2A30D`).
* `FUN_00028ea6` is called at **`0x22522` from `FUN_0002214a`**, guarded by `r27 = r25 & 0x930`.
* 🛑 **`0x830 ⊆ 0x930`** — `0x830` = bits {11,5,4}, `0x930` = bits {11,8,5,4} ⇒ **every invocation in
  which `FUN_00038148` runs, the dwell counter also decremented. Same task, same invocations, exact
  lockstep.**

⇒ **Task 1 = `FUN_0002214a` = 1000 Hz.** On-car measurement plus a static lockstep argument.
**⇒ V97's `+7.82°` at 7.79 Hz and `fc` 15.9 → 23.3 Hz STAND as written.**

Sensitivity, kept for reference — the direction is unchanged at any rate, only the size moves:

```
fs =  500 Hz -> lead at 7.79 Hz = +11.27 deg,  fc(102)= 7.9 Hz  fc(150)=11.7 Hz
fs = 1000 Hz -> lead at 7.79 Hz =  +7.82 deg,  fc(102)=15.9 Hz  fc(150)=23.3 Hz   <-- CONFIRMED
fs = 2000 Hz -> lead at 7.79 Hz =  +4.34 deg,  fc(102)=31.7 Hz  fc(150)=46.6 Hz
```

### 3d. The unfiltered branch is NOT an empty field [EVIDENCE]

`gp-0x6bfa`'s clamp is a hard-coded `movea 0x4e20` immediate ⇒ **no cal lever there.** `gp-0x6bfe`'s
branch (`FUN_0003b8f6`) carries **four virgin IIR poles of the same class as `0xC63AC`**, all
stock == V97:

| cal | stock | role in `FUN_0003b8f6` |
|---|---|---|
| `0xC40D0` | 408 | friction-term IIR pole |
| `0xC40D4` | 573 | command-path IIR pole (two stages) ⚠ record says *do not propose off that file* |
| `0xC40D6` | 246 | rate-path IIR pole |
| `0xC40D8` | 3686 | column-path IIR pole |

They sit in the **V89 plant-model block** alongside `0xC40D2` = K1 (**102 → 204**, V89's flown dose,
carried on V97), `0xC40BC` = 600, and `0xC4080` = 0 (the NEVER-RAISE relay hazard, untouched).
**No build proposed and none priced — this records only that the field is occupied.**

⊕ **tp arithmetic verified against a live anchor, not assumed:** `tp+0x50D2` must be `0xC40D2` = K1,
and it byte-reads **102 stock / 204 V97**, matching the independent stock-vs-V97 diff at
`0xc40d2 0x66→0xcc`. The `0xC4000`/`0xC5000` off-by-0x1000 trap is excluded for every address above.

## 4. Is the lane load-bearing downstream, in this regime?

### The arithmetic, mirrored [EVIDENCE — from `decompile_function(0x38148)`]

```python
# six lanes, each  lane * in_range(lane) * cal >> 10 ; all six cals are 1024 = unity
sum6 = ( (gp_6b4e * inrange(gp_6b4e, 0x2800) * cal(0xC63A8)) >> 10      # LKAS overlay, +-10240
       + (gp_6b4c * inrange(gp_6b4c, 0x2800) * cal(0xC63AA)) >> 10      # aggregator route, +-10240
       + (gp_6b26 * inrange(gp_6b26, 0x0400) * cal(0xC63A6)) >> 10      # -K*motor accel, +-1024
       + (gp_6b46 * inrange(gp_6b46, 0x0400) * cal(0xC63A4)) >> 10      # +-1024
       + (gp_6bd0 * inrange(gp_6bd0, 0x0800) * cal(0xC63A0)) >> 10      # +-2048
       + (gp_6bbe * inrange(gp_6bbe, 0x0800) * cal(0xC63A2)) >> 10 )    # viscous+DC, +-2048
target = ((sum6 * polarity(gp_6752) * cal(0xC6468)) >> 10) * 16         # 0xC6468 = 2639 = x2.577
gp_374c += ((target - gp_374c) * cal(0xC63AC)) >> 10                    # <-- V97: 102 -> 150
model   = gp_374c >> 4                                                  # 0x38236  sar 0x4,r6
resid   = gp_6bfe + gated(gp_6bfa, +-20000) - model                     # 0x38218 ld.h -0x6bfe[gp]
gp_6b70 = clamp( sign(resid) * LERP(|resid| * cal(0xC63AE) >> 10), +-cal(0xC6200)=8192 )
```

`gp-0x6bfe`: **1 writer** (`FUN_0003bc20` @`0x3BC3E`, called at `0x22416` in the *same* task under the
*same* `r28` guard, *before* `FUN_00038148`) and **1 reader** (`FUN_00038148`). [EVIDENCE]

### No deadband — the residual LERP passes through the origin [EVIDENCE]

Builder = `FUN_000389ec` (writes `X[0]` at `gp-0x64b8`), which runs in a **different, slower task**
(`FUN_00022ca0`). It sets

```
*(gp-0x373c) = 0 ;  *(gp-0x3714) = 0 ;   build loop starts at index 1
...
*(gp-0x64b8) = *(gp-0x373c)   ->  X[0] = 0
*(gp-0x641c) = *(gp-0x3714)   ->  Y[0] = 0
```

⇒ `X[0] = Y[0] = 0`. Independently reproduces `reference-accord-residual-lerp-gp3714-runtime-adaptive`.
**Any non-zero residual is on the curve; there is no low-signal dead zone the creep regime could sit
inside.** The 60 km/h speed schedule I found in the builder
(`gp-0x3748 <= cal(0xC62D8)/64 = 60.00 km/h`) only gates a **Y-floor whose cals `0xC617A`/`0xC617C`
are both ZERO in stock** ⇒ that schedule is **inert**, and it is not a creep dead zone. [EVIDENCE]

### But the dose is UNSIZED [EVIDENCE for the bound, BELIEF for the consequence]

* **`X[k>0]` are divided by a runtime factor and `Y[k>0]` multiplied by another** (both from
  `FUN_0003897a` rate-limiters, bounded `[204, 2048]` by cals `0xC639A/0xC639C` and `0xC6390/0xC6392`,
  nominal 1024). ⇒ **the origin slope `f'` swings over ≥10×** and **cannot be pinned statically.**
* The pole moves the model by `|H(150) − H(102)| / |H(102)| = 0.1502` of its 7.79 Hz component.
* **The model's magnitude is below the flown probe's floor**: `Mhi == 0` and `Mlo == 0` on
  **10,749 / 10,749** route-`0x80` frames ⇒ `|gp-0x374c>>4| < 2048`, always. Routes 7e/7f (V96,
  normal driving) show `M == 1` on only **77 / 80,462** and **29 / 83,632** frames.

⇒ the perturbation `Δ(gp-0x6b70) = f'(|resid|) · 0.15 · model_AC(7.79 Hz)` has **both** factors
unknown: `f'` is runtime-scheduled, `model_AC` is under the probe's LSB. **The lever is live and its
size is unmeasured.** [EVIDENCE for both bounds]

## 5. What should V97 have produced on this drive?

Reproduced arithmetic (`fs = 1000 Hz`):

| A | α = A/1024 | τ | integer stall band | \|H\| @7.79 Hz | arg @7.79 Hz | \|H\| @21 Hz |
|---|---|---|---|---|---|---|
| 102 | 0.099609 | 9.53 ms | 11 acc-counts (0.69 model-counts) | 0.9063 | −23.63° | 0.6229 |
| 150 | 0.146484 | 6.31 ms | 7 acc-counts (0.44 model-counts) | 0.9555 | −15.81° | 0.7689 |

**Lead = +7.82°**, 21 Hz throughput ×1.2344 — both reproduce `builds/v80_v107/build_v97_tva.py` exactly. ⚠ The
docstring's *per-A* phase row ("−8.5 / −11.0 / −12.6") is mis-tabulated; the **deltas the decision
rested on are correct.** Also worth recording: the stall band **narrows** 1.57× (11→7), the opposite
direction from the `102→65` case in the memory, so V97 slightly *reduces* the recorded resid-high bias.

**Exposure — the decisive number:**

| | route 7e (V96) | route 7f (V96) | **route 0x80 (V97)** |
|---|---|---|---|
| duration | 806 s | 838 s | **109 s** |
| engaged | **615 s** | **690 s** | **17.2 s, 1 episode** |
| median speed | 42.7 km/h | 41.3 km/h | **1.7 km/h (max 6.6)** |
| engaged 6–9 Hz episodes | 2 | 1 | **1** |

`_scratch/cache/r80/r80_vs_v96.json` already reports `80_ENG` with `n = 1` in every band. **A single episode
supports no interval and no bootstrap.** For scale, V88's grinding result needed 120 s engaged at
≥ 50 km/h, and the standing memory `accord-leverb-discriminator-underpowered` records that this
kit's binding constraint is exposure, not analysis.

**Honest answer: the drive could not have resolved a +7.8° phase rotation of a term whose magnitude
is below the probe's own quantiser, over 17 s in one episode.** [EVIDENCE for the premises,
**BELIEF** for "therefore imperceptible" — perception thresholds are not something I can derive.]

## 5b. ADDENDUM — the three-term residual, and why the "≤ 9 % share" bound is UNSOUND

Added after the orchestrator relayed a parallel decompile and asked for Path-2's share of the
delivered command, with the expectation that V97 is **failure class E** (right cell, negligible lane).
**I confirm the decomposition and REJECT the class-E conclusion.** Both with evidence.

### The decomposition — CONFIRMED, all three signs [EVIDENCE]

V850 semantics: `sub r1,r2` ⇒ `r2 -= r1`; `subr r1,r2` ⇒ `r2 = r1 - r2`; `mul rA,rB,r0` ⇒ `rB = rB*rA`.

```
000381ec add  r8,r14        ; r14 = sum6  (six lanes, each >>10, ALL cals = 1024 unity)
000381f6 mul  r8,r14,r0     ; x polarity (gp-0x6752)
000381fa mul  r16,r14,r0    ; x cal(0xC6468) = 2639
00038206 sar  0xa,r14   /   0003820c shl 0x4,r14      ; -> TARGET
0003820e sub  r6,r14        ; target - acc
00038210 mul  r13,r14,r0    ; x A = cal(0xC63AC)      <-- ALL of V97, and ONLY here
00038220 sar  0xa,r14   /   00038222 add r14,r6   /   00038230 st.w r6,-0x374c[gp]   ; UNCONDITIONAL
00038236 sar  0x4,r6        ; model = acc >> 4
00038238 subr r15,r6        ; r6 = gp-0x6bfe - model        <-- coefficient EXACTLY -1
0003823a add  r9,r6         ; r6 = ... + gated(gp-0x6bfa)   <-- coefficient EXACTLY +1
```

`0xC63AE` = 1024, so the LERP index is **exactly `|resid|`** ⇒ `gp-0x6b70 = ±LERP(|resid|)`, no
intervening scale.

### Both in-function gates are TAUTOLOGICAL [EVIDENCE]

* **`gp-0x6bfa` ±20000 gate is DEAD.** Sole writer `FUN_00026c80` clamps on all three arms —
  `0x273AC movea 0x4e20,r0,r14`+`st.h` (high), `0x273C4 movea -0x4e20,r0,r14`+`st.h` (low),
  `0x273D6 st.h r15` (pass-through, `|r15| <= 20000` by the `addi 0x4e20` tests at `0x2739E`/`0x273BA`)
  ⇒ `gp-0x6bfa + 20000 ∈ [0,40000] < 0x9C41` **always** ⇒ `cmovnc` never fires ⇒ `gated(D) ≡ D`.
* **`0x38234 bnc 0x382ce -> movea 0x7fff` is a RELAY, not a test.** `gp-0x6bfe`'s sole writer
  `FUN_0003bc20` is a plausibility latch: `gp-0x6bfe = gp-0x6bfc` if `|gp-0x6bfc| <= 20000`, **else
  exactly `0x7FFF`** and `gp-0x695c = 0xFFFF`. So `0x38234` fires **iff `gp-0x6bfe == 0x7FFF`**.
  Independently re-derives the recorded `gp-0x695c==0xFFFF <=> gp-0x6b70==0x7FFF` equivalence
  ([[reference-accord-observer-gate-tautology-and-term-mismatch]]). The 427 never saturated on route
  `0x80` ⇒ **the latch never fired all drive.**

### 🛑 The two residual terms are TWO ESTIMATES OF THE SAME QUANTITY [EVIDENCE]

`gp-0x6bfc` has **1 writer**: the last instruction of `FUN_0003b8f6` (`0x3BC1A st.h r7,-0x6bfc[gp]`).

```
gp-0x6bf6 = clamp( cal(0xC6468)=2639 * MODEL_A , +-20000 )
gp-0x6bfc = clamp( cal(0xC6468)=2639 * (MODEL_A - friction - inertia) , +-20000 )
  MODEL_A = LPF2( gp-0x6b98 * polarity / 1024 ) + angle-scheduled-gain * clamp15(column terms)
```

**Branch A (`gp-0x6bfe`)** is built from the **final motor command `gp-0x6b98`**, float, two-stage IIR.
**Branch B (`gp-0x374c>>4`)** is built from the **six assist lanes**, integer, through the `0xC63AC`
pole. **Same units. Same `0xC6468` = 2639 scale.** This is the recorded "two filters on one signal"
structure ([[reference-accord-observer-filter-mismatch-leaks-the-command]]).

⇒ **Comparing Branch B's measured ceiling (2048) against Branch A's *admitted range* (±20000) is not
a share estimate — a difference of two CORRELATED estimates is smaller than either, so the correct
denominator is the residual, not the admitted range.** The ≤ 9 % figure is an artifact of that
comparison. And this is **not** the `0xC63A4` shape: `0xC63A4`'s lane was *summed alongside* others;
here the coefficient is **exactly −1 into a difference**, so **one count of Path-2 movement is one
count of residual movement, with zero dilution inside the residual.**

### What actually decides the share

| quantity | value | source |
|---|---|---|
| `gp-0x6b70` p50 / p99, route `0x80` | 320 ct / 3059 ct | 427 lane, live, 0.000 % saturation |
| `\|gp-0x374c>>4\|` | **< 2048** on 10,749/10,749 | cave `M` histogram (tighter than the `Mhi`-only < 4096) |
| `\|resid\|` p50 | **320 / f'** | `gp-0x6b70 = LERP(\|resid\|)`, index scale exactly 1 |
| `f'` | **runtime-scheduled, ≥10× swing** | `FUN_000389ec`: X÷factor, Y×factor, both `[204,2048]` via `gp-0x6982`/`gp-0x6984` |

Plausible `f' ∈ [0.1, 10]` ⇒ `|resid| p50 ∈ [32, 3200] ct`, against a Path-2 term admitted up to
**2048 ct**. **Over essentially the whole plausible range of `f'`, the Path-2 term is comparable to or
larger than the residual it enters — it is capable of dominating.**

**⇒ Path-2's share is UNRESOLVED, not small. Failure class E is NOT established.** [EVIDENCE for every
premise; the refusal to name a number is deliberate — `f'` is not statically knowable.]

## 6. What would settle it

1. 🛑 **Re-scale the cave's regressor rung — now the top item.** `builds/v80_v107/build_v97_tva.py:99-100` concedes it
   is 34× over-range; `M` is pinned at 0 because its LSB is 2048 and `|gp-0x374c>>4|` never reaches it.
   Move the shift so the LSB lands near **128** and V96's own **S1** (slope of `gp-0x6b70` on
   `gp-0x374c>>4`, lag 0 and lag 1) becomes measurable for the first time. **S1 *is* `f'`, and `f'`
   plus `|resid|` *is* the share of §5b.** One probe-only build, no dynamics touched — it converts
   every "unsized" verdict in this thread, V97's *and* the friction-dose work, into a number.
2. **A matched re-fly.** 7e already contains **136.6 s at 0–5 km/h** and 7f **62.7 s** — a matched
   low-speed A/B is possible from existing data as soon as route `0x80` gets more engaged minutes.
3. **Trace `gp-0x6982` / `gp-0x6984`**, the two friction-LERP gain schedulers that set `f'`. The
   static complement to (1). Not done in this session.
4. **Pin the task rate** (§3c) — it scales every phase figure in the V97 rationale.

## Files

* `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\stock_fw_dump\code.bin`
* `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin`
* `C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v97_V96BASE-C63AC.102to150_plain_image.bin`
* `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\_scratch/cache/r80\` (V97 flight)
* `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\builds/v80_v107/build_v97_tva.py`
