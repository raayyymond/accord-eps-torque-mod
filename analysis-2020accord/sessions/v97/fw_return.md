# The "return-to-centre" lane — full trace, and a re-identification

`fw-return`, 2026-08-12. Stock `code.bin` in GhidraMCP (explicitly `program:"code.bin"` on every
call — the session's *current* program was the V96 image with **0 functions**, i.e. unanalyzed).
`gp = 0xFEDF8000`, `tp = 0xBF000`.

**Headline: the lane the kit calls "return-to-centre" is a RACK END-STOP CUSHION. There is no LKAS
gate on it. It is dead engaged *and* ~99.3 % dead in manual, by Honda's design, on stock and on
every build we have ever shipped.** The brief's leading hypothesis is refuted.

Two corrections to the kit's own record fall out, both with on-car confirmation. See §6.

---

## 1. The lane, located [EVIDENCE]

| function | addr | role |
|---|---|---|
| `FUN_00035ce6` | `0x35ce6` | prologue, reads `cal(0xC6150)` |
| `FUN_00035d38` | `0x35d38` | **travel-limit envelope** — max/min-hold of `gp-0x6bf0` into `gp-0x6bd8`(UPPER)/`gp-0x6bd6`(LOWER) |
| `FUN_00035e00` | `0x35e00` | **end-stop state machine** — drives enums `gp+0x6440` / `gp+0x6441` |
| `FUN_00036022` | `0x36022` | **margin** — writes `gp-0x6bda` = distance to the envelope edge |
| `FUN_000360fe` | `0x360fe` | term-1 LERP → `gp-0x6b64` |
| `FUN_000361c8` | `0x361c8` | term-2 LERP → `gp-0x6b5e` |
| `FUN_00036388` | `0x36388` | **output** → `gp-0x6b62` (+ lockstep shadow `gp-0x4cda`) |

All called from `FUN_0002214a` (1 kHz, established). Output `gp-0x6b62` is one of the 11 lanes
unconditionally summed in `FUN_0003aa2c` → `gp-0x6b94` → governor → shaper → `gp-0x6b98` → FOC.

### The margin, mirrored in integer Python (each line annotated with its address)

```python
# FUN_00036022 @0x36022
OFFSET = 0 if u8(gp-0x67fe) == 2 else s16(0xC614C)   # 0x36026 ld.bu ; cal = 128
x      = s16(gp-0x6bf0)                              # 0x36068 ld.h
if x < 1:  dist = x - s16(gp-0x6bd6)                 # x - LOWER   -> >= 0
else:      dist = s16(gp-0x6bd8) - x                 # UPPER - x   -> >= 0
w16(gp-0x6bda, dist - OFFSET)
```

🛑 **This CORRECTS my own prior memory**, which had the positive branch as `x - UPPER`. The
decompile is `UPPER - x`. Consequence: `dist` is a **non-negative distance to an envelope edge**,
not a signed margin — which is what makes the whole lane legible as an end-stop cushion.

### The gate — byte-read this session, table @ `0xC695C`

```
count=5   X = [-397, -192,  140,  294,  384]     (0xC695E..0xC6966)
          Y = [   0, 2560, 2560,  717,    0]     (0xC6968..0xC6970)
```
Both ends clamp to **zero**, so this is a genuine window: `Y > 0 ⟺ gp-0x6bda ∈ (−397, 384)` —
exactly the predicate V92's `byte4 b4` flew. Since `dist ≥ 0` and `OFFSET = 128`, we have
`gp-0x6bda ≥ −128 > −397`: **the lower edge can never bind. The gate is purely `dist < 512`.**

---

## 2. Why the gate is shut: the envelope half-width is FLOORED BY CALIBRATION [EVIDENCE]

`FUN_00035d38` keeps UPPER/LOWER as a **non-decaying max/min-hold** of `gp-0x6bf0`:

- keep-old unless `x > UPPER` (resp. `x < LOWER`) → **it can only ever widen**;
- capped at `±cal(0xC614A) = ±10048`;
- **reset to `±(cal(0xC6150) >> 1) = ±(18780 >> 1) = ±9390`** when the reset flag is set.

The one path that could *narrow* it — the re-centre branch `iVar4 = sVar3 + gp+0x643c` — is
**DEAD**: it is guarded by `gp-0x37ba == 0`, and `gp-0x37ba`'s only writer image-wide is
`st.h r0` (writes **zero**) at `0x35df6`. Six hits total, `truncated:false`; the two reads are both
inside `FUN_00035d38`; the three `tp-0x37ba` hits at `0x83bb0+` are a different base and excluded.

⇒ half-width ∈ **[9390, 10048]**, always. Therefore:

```
gp-0x6bda  =  halfwidth - |x| - 128     (envelope centred)
gate open  ⟺  gp-0x6bda < 384
           ⟺  |gp-0x6bf0| > halfwidth - 512   ∈ [8878, 9536]
```

### The cross-validation, and it is exact

The kit's independently-recorded **hands-off `gp-0x6bda` ≈ 9262** is reproduced to the count:

```
18780 >> 1  -  128  =  9390 - 128  =  9262      at x ≈ 0
```

A firmware calibration reproducing an on-car measured value exactly. This upgrades "the envelope is
pinned wide" from BELIEF to **EVIDENCE**, and it retires the open question in
`reference_accord_dwell_relay_polarity_settled_...` about whether the 9262 figure was trustworthy.

---

## 3. It is an END-STOP CUSHION, not a centring lane [EVIDENCE]

`FUN_00035e00` @`0x35e00` arms the state machine on:

```
|gp-0x6b98| > cal(0xC618E) = 4096      final motor command magnitude HIGH (governor max is 4762)
&& gp-0x6ac0 < cal(0xC620C) =  200     motor electrical rate LOW  -> not turning
&& gp-0x4f68 > cal(0xC6190) = 7680
&& gp-0x6a5e >= cal(0xC62E2)           voted vehicle speed at/above a threshold
&& gp-0x67f4 == 1 && gp-0x6990 == 0
```

**High command AND near-zero motor rate = STALL.** It then splits on `sign(gp-0x6bf0)` into two
independent 0/1/2 enums `gp+0x6440` / `gp+0x6441` — **two ends, left stop and right stop** — and
calls diagnostic `FUN_000193ce(0xb, 0)` on any state change. `FUN_00036388` then requires the
relevant enum to have reached **2** ("at the stop") for the direct path (`0x363a2`, `0x364d6`).

And `gp-0x6bf4 = |gp-0x6bf0|` is tested in `FUN_00035e00` against
`(cal(0xC6150)>>1) - 0x280 = 9390 - 640 = 8750` — a second, independent "near the end of travel"
threshold cut from the same calibration.

### `gp-0x6bf0` is position-like, and the proof costs nothing extra [EVIDENCE]

If `gp-0x6bf0` were a **rate**, the arm condition (`motor rate < 200`, i.e. stopped) and the gate
(`|gp-0x6bf0| > 8878`, i.e. moving fast) would be **mutually exclusive** — the lane could never
fire at all. V92 measured it firing (89 frames, `b4/b5` self-consistent and passing their own
structural check). A lane that fires is not a lane that can never fire ⇒ **`gp-0x6bf0` is a
position-like quantity that saturates at the travel limits.** Its producer `FUN_0003bd7c` writes it
at `0x3c0cc` as `(accumulator × cal(0xC6464)) >> 12 × polarity(gp-0x6752)`, with a lockstep shadow
at `gp-0x4cf6` — consistent with a scaled unwrapped position, not a derivative.

⇒ **The V92 duties need no engagement story.** `0.0000` engaged / `0.0074` manual is simply
"you only reach the rack stops near full lock, and never while LKAS is steering."

---

## 4. The brief's hypothesis is REFUTED, two independent ways [EVIDENCE]

> *"the return-to-centre lane is muted while engaged, so the clean manual return is that lane doing
> its job."*

1. **The V92 data already refutes it.** Manual duty is **0.0074**, not ~1. The lane is ~99.3 % dead
   in MANUAL too. It cannot be what makes the manual return clean.
2. **The firmware refutes it.** There is zero engagement dependence in the gate. The only state byte
   in `gp-0x6bda`'s producer is `gp-0x67fe`, and its sole writers are four `st.b` sites inside
   `FUN_0003bd7c` (the resolver/unwrap producer) and `FUN_0003e760` — a **sensor-validity** state.
   59 accesses enumerated, `truncated:false`, none LKAS-related.

This also re-confirms, from a second direction, the earlier finding that **no discrete
`if (LKAS != 0) suppress return` branch exists anywhere in this firmware.**

⇒ **Do not spend V97 re-arming this lane.** It is an end-stop cushion; arming it in the micro
regime injects a term Honda only ever intended at full lock.

---

## 5. Lineage — this is Honda's, not ours [EVIDENCE]

`grep -lE "C6150|C614A|C614C|C618A|C627E|C6132|C63C0|C63BE" build_v*_tva.py` → **only**
`builds/v80_v107/build_v92_tva.py`, and every hit there is read-only (lines 524-525 say verbatim
"🛑 READ-ONLY FOR V92"; line 1042 is a `check()` assertion).

Byte-verified across the shipped images:

| cell | stock | v90 | v91 | v92 | v93 | v94 | v96 |
|---|---|---|---|---|---|---|---|
| `0xC6150` envelope full width | 18780 | 18780 | 18780 | 18780 | 18780 | 18780 | 18780 |
| `0xC614A` envelope cap | 10048 | = | = | = | = | = | = |
| `0xC614C` margin offset | 128 | = | = | = | = | = | = |
| `0xC618A` dwell arm | 1024 | = | = | = | = | = | = |
| `0xC627E` dwell snap | 20 | = | = | = | = | = | = |

**Frozen at stock on all 7 images. Q3 answer: the mute is Honda's design, not a side effect of any
of our 90 builds.**

---

## 6. 🛑 TWO CORRECTIONS TO THE KIT'S RECORD

### 6a. The dwell-relay polarity is INVERTED in the kit's record

`memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md` and
`.claude/agent-memory/.../reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff.md`
both record `window_open = |gp-0x6b64| < 1024` (arms on **SMALL**). **That is backwards.**

Assembly at the site, `FUN_00036388`:

```
00036432: ld.h -0x6b64[gp],r8
00036436: cmp r0,r8            \
00036438: mov r8,r7             |  abs() idiom - validates the operand order below
0003643a: bge 0x00036440        |  (cmp r0,r8 ; bge  =>  r8 >= 0)
0003643c: subr r0,r7            |
0003643e: sxh r7               /   r7 = |gp-0x6b64|
00036440: ld.h  0x718a[tp],r16      r16 = cal(0xC618A) = 1024
00036444: ld.hu 0x727e[tp],r6       r6  = cal(0xC627E) = 20
00036448: cmp r16,r7                V850: computes r7 - r16
0003644a: setfgt r16                r16 = 1  <=>  |gp-0x6b64| > 1024
00036458: cmp r0,r16
0003645a: be 0x00036464             if NOT greater -> DECREMENT path
00036460: add 0x1,r14               else counter++
```

⇒ **the counter increments when `|gp-0x6b64| > 1024` and decrements otherwise.** The decompile
agrees (`iVar11 - iVar17 < 0 == OV && iVar11 != iVar17` is signed `>`).

**Three independent confirmations, and the on-car data is one of them:**

| | wrong polarity (kit's record) predicts | correct polarity predicts | V92 MEASURED |
|---|---|---|---|
| `byte7 b6` snap duty | 1.0 (default-armed) | **0.0** | **0.0000** |
| `byte4 b5` (`gp-0x6b62 ≠ 0`) | 1.0 (flat −1024 bias) | **0.0** | **0.0000** |

Gate shut ⇒ `gp-0x6b64 ≡ 0` ⇒ `|0| > 1024` false ⇒ counter decays to 0 ⇒ no snap ⇒ the term
contributes **exactly zero**.

### 6b. ⇒ The `byte7 b6` rung is NOT indicted — it was reading the truth

`memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md` indicts `byte7 b6` as a dead rung because
a sustained `(gate=0, snap=0)` run of 855 s contradicted the pre-registration in `STATE.md` §E.
**The pre-registration was built on the inverted polarity.** Under the correct polarity,
`(gate=0, snap=0)` is the *predicted* steady state, and the 855 s run is a **clean confirmation**,
not an indictment. Likewise the "flat −1024 CONSTANT bias" concern in my own agent memory rests on
the inverted polarity and **does not occur**: the lane contributes 0, which is exactly what
`b5 = 0.0000` measured.

*(Reported, not fixed — per the brief I have not edited `docs/` or `memory/`.)*

---

## 7. Q4 — what actually provides centring/damping while engaged at parking speed?

**Essentially nothing.** Enumerated:

| candidate | state in the micro regime, current build | evidence |
|---|---|---|
| End-stop cushion `gp-0x6b62` | **ZERO** | this trace + V92 duty 0.0000 |
| Base-assist damper `ch0 = FactorC(speed)×FactorE(rate)>>10` | **ZERO** | `FactorC Y[0] = 0` at `X[0]=35 km/h`; **byte-read on the V96 image this session: m26 `Y=[0,234,429,908]`, m27 `Y=[0,233,426,875]` — V86B's arming is NOT carried on the current car** |
| comp-add `FUN_000456a4` | **ZERO** | gate needs `gp-0x6ac0` ≳ 1000 ct ≈ 212 °/s |
| r24/r26 torque-derivative lane | **LIVE, gain 3.000× (schedule max at creep)** | but it is a **+84° phase-advance on torque**, not a viscous damper |
| `gp-0x6b26` / `0xCBE74` | **LIVE** | an **INERTIA** term — raises apparent inertia, dissipates nothing |
| `FUN_0003a382` D-term, `Kd = 2.000`, unfiltered | **LIVE** | previously identified as the sole **pumping** term at 7.79 Hz |
| column friction | live, mechanical | measured to damp it (grip −0.655 vs control −0.266) |

⇒ **All three viscous candidates are gated off in the micro regime; what remains is a
phase-advance lane, an inertia term, and an anti-damping D-term.** That is a coherent
firmware-side account of the measured `Re(Z) < 0` at 6–9 Hz — no dissipation is scheduled there at
all. **This is the answer to the crux, and it is not "a missing return-centre term".**

---

## 8. Q5 — pricing a re-arm. Recommendation: DO NOT [BELIEF, with the reasoning stated]

The only cal-only way to make the lane fire in normal driving is to **narrow `0xC6150`** (18780),
which makes the ECU believe the rack is much shorter than it is.

- **GATE 1 (RAM ownership):** passes trivially — cal-only, no new RAM, no cave.
- **GATE 2 (closed-loop stability):** **FAILS on inspection.** The term is a magnitude-ramped
  pushback (LERP peak `Y=2560` ≈ 2.5× in Q10, plus a 1024-count snap, clamped ±0x2800) whose sign
  is set by `gp-0x6bf0`, injected unweighted into the same 11-lane sum at 1 kHz. It is a relay, not
  a viscous term — the V80 "worst grinding ever" failure mode is a step at zero rate, and this is
  a step at a *position*.
- **Blast radius:** `0xC6150` has **7 read sites in 5 functions** (`0x35ce6`, `0x35d3e`, `0x35d42`,
  `0x35e0c`, `0x35e5a`, `0x360d2`, `0x5691a`). It sets the envelope reset width, the `−0x280`
  proximity threshold, the `gp+0x643c/643e` re-centre pair, **and** it is read by `FUN_000568d0`,
  which also *writes* the `gp+0x6440` enum — i.e. it reaches a diagnostic state machine that calls
  `FUN_000193ce(0xb,0)`. **Safety-adjacent: it would make the ECU apply end-stop pushback where
  there is no end stop, at high command magnitude.**

⇒ Wrong physics for the crux, and the wrong cell to experiment on.

---

## 8b. Follow-up: the buried `BUILD-LINEAGE.md` dwell-relay note, adjudicated

Team-lead surfaced a note in `docs/BUILD-LINEAGE.md` (after the "Struck LEVERS, 2026-08-09 (late)"
table) describing the dwell relay. **Confirmed in every element except the polarity.**

| element | status | address |
|---|---|---|
| counter `gp-0x6a82` | ✅ exactly 2 sites image-wide | `ld.h` @`0x3642e`, `st.h` @`0x36472` |
| ceiling `0xC627E` = 20 | ✅ | `ld.hu 0x727e[tp]` @`0x36444` |
| threshold `0xC618A` = 1024 | ✅ | `ld.h 0x718a[tp]` @`0x36440` |
| snap value 1024 | ✅ — **the same cal `0xC618A`, dual-purpose** | `ld.h 0x718a[tp],r7` @`0x3649e` |
| writes `gp-0x6b62` | ✅ 3 stores, all in `FUN_00036388` | `0x36514`, `0x3652c`, `0x36544` (`st.h r0`) |
| cals virgin | ✅ byte-frozen stock across stock/v90-v96 | — |

🛑 **`|gp-0x6b64| < 1024` is INVERTED — it is `>`.** See §6a. ⇒ the inverted polarity is in **THREE**
places: `docs/BUILD-LINEAGE.md` (this note), `memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md`,
and `docs/STATE.md` §E. The counter test also uses the **pre-update** value (latched before the ±1 at
`0x36460`/`0x3646a`), so the snap trails by one tick.

### `gp-0x6b64` is a GATED RATE — not a torque, not an error [EVIDENCE]
`FUN_000360fe` @`0x360fe`:
```
gp-0x6b64 = -clamp( (Y1(gp-0x6bda) * gp-0x6abc >>10) * cal(0xC63BE)=1024 >>10, ±0x2800 )
             ^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^
             end-stop proximity      RAW unfiltered motor rate
```
`Y1 = 0` outside `gp-0x6bda ∈ (−397,384)` ⇒ during an engaged return to centre `gp-0x6b64 ≡ 0`
**regardless of rate**, so `|0| > 1024` is false and **the dwell can never complete.**

### Why 0.0000 engaged — it is (a), and (b)/(c) are ruled out [EVIDENCE]
- **(a), specifically "`gp-0x6b64` is identically zero because its own upstream LERP gate is shut"** —
  not "stays above 1024". Direct evidence, already measured: **`b4 ≡ b5` on all 87,317 V92 frames**.
- **(b) ruled out** — `b4`/`b5` *fire* in manual (89/54 frames); a skipped function or store gives a
  frozen bit. The function is in `FUN_0002214a` (1 kHz).
- **(c) ruled out** — V92 probed `gp-0x6b62` itself, and it carries lockstep shadow `gp-0x4cda`; a
  downstream overwrite would trip `FUN_0006b9fa`.
- **`gp-0x67fa` is not involved.** The state byte here is `gp-0x67fe` (sensor validity, different
  cell); `gp-0x67fa` is not referenced in `FUN_00036388`. The record's existing strike stands.

### It is a RELAY, so arming it is contraindicated [EVIDENCE for structure]
```
sVar8 = snap_active ? 1024 (CONSTANT) : |gp-0x6b64| (tracking)
if (gp-0x6b64 < 1) sVar8 = -sVar8
```
A bang-bang detent. The only shaped element is the proximity LERP `Y=[0,2560,2560,717,0]`, and the
snap **flattens exactly that curve into a constant** — the FLATTEN-A-CURVE-INTO-A-RELAY class beside
`0xC4080`/`0xC63AE`/`0xC6200` (V80, "worst grinding in this car's history").

### 🛑 The decisive point: its absence cannot be the missing damping
**For this lane's absence to explain the engaged-vs-manual difference, it would have to be PRESENT in
manual. It is not** — manual duty **0.0074**. So "null on the GATE, V64 class" is true but not
load-bearing: arming it cannot recover a contrast it never contributed to.

### Aggregator summand — confirmed, with a correction [EVIDENCE]
`gp-0x6b62` is read at **`0x3aa38`** in `FUN_0003aa2c` and summed at **unity weight** (no multiply).
⊕ It does not enter bare — it passes a **±8192 zero-reject window** first:
```
0x3aa50: addi 0x2000,r9,r12     ; r12 = gp-0x6b62 + 0x2000
0x3aa54: addi -0x4001,r12,r0    ; CY set iff r12 >= 0x4001  (V850 CY = carry-OUT of the add)
0x3aa58: cmovc 0x0,r9,r16       ; r16 = CY ? 0 : r9  -> out-of-range REJECTED to 0
```
Same idiom as the shaper's `gp-0x6acc` gate. Harmless here (the lane's terms cap near 1024).
⚠ Easy to invert: V850 `CY` is the carry-**out** of the addition, so a subtract sets CY when there is
**no** borrow.

---

## 8c. REPLACEMENT TEXT FOR `docs/STATE.md` §E — apply verbatim (I did not edit that file)

> **§E — the dwell-snap rung `byte7 b6`: PRE-REGISTRATION WAS WRONG, RUNG IS SOUND.**
> The §E pre-registration said a shut gate **arms** the dwell counter, so `snap = 1` should be the
> default whenever the gate is shut, with `(gate=0, snap=0)` only a ~21 ms transient. **That rests on
> an inverted comparison.** The counter arms on **`|gp-0x6b64| > cal(0xC618A)=1024`**, not `<`
> (asm `FUN_00036388`: `cmp r16,r7` @`0x36448` computes `r7−r16` with `r7=|gp-0x6b64|`, then
> `setfgt r16`; the `be` @`0x3645a` takes the **decrement** path when not-greater; operand order
> validated in-block by the abs() idiom @`0x36436`; the decompile agrees).
> ⇒ a shut gate **DISARMS** the counter. Gate shut ⇒ `gp-0x6b64 ≡ 0` ⇒ counter decays to 0 ⇒
> **snap = 0 and the lane contributes exactly 0** — which is what V92 measured on both rungs
> (`byte7 b6` duty 0.0000, `byte4 b5` duty 0.0000). **The 855 s sustained `(0,0)` run is a clean
> confirmation, not an indictment. `byte7 b6` does not need re-flying.** The lane itself is
> re-identified as a **rack end-stop cushion** (stall-armed; gate needs `|gp-0x6bf0| > 8878`), and its
> **manual** duty is 0.0074 — ~99.3 % dead in manual too.

---

## 8d. The aggregator zero-reject windows — scope, lane by lane [EVIDENCE]

Team-lead asked whether the `addi +W / addi −(2W+1) / cmovc` window sits on all eleven lanes.
**Answer: on EIGHT of the eleven, and the half-widths DIFFER per lane** — the record's "all eight
aggregator zero-gates" is the right count, but they are not one uniform width.

`search_instructions(mnemonic="addi", function="FUN_0003aa2c")` → 25 hits, `truncated:false`,
`instructions_scanned: 280`. Exactly 8 form the paired zero-reject idiom (the other 17 have `dst=r0`
with no paired `+W` — single-sided compares for clamps/branches, not this idiom).

| lane | load | window pair | half-width | producer ceiling | vacuous? |
|---|---|---|---|---|---|
| `gp-0x6b62` end-stop | `0x3aa38`→r9 | `0x3aa50`/`0x3aa54` | **±8192** | ≲5786 (1024 snap + LERP2 4762) | yes [BELIEF] |
| `gp-0x6b4c` **LKAS** | `0x3aa3e`→r6 | `0x3aa5c`/`0x3aa60` | **±10240** | **exactly ±10240** | **yes, ZERO margin [EVIDENCE]** |
| `gp-0x6ade` | `0x3aa48`→r14 | `0x3aa68`/`0x3aa6c` | **±1024** | not verified by me | unverified |
| `gp-0x6bd0` damper | `0x3ac78`→r9 | `0x3ac84`/`0x3ac88` | **±2048** | not verified by me | unverified |
| `gp-0x6b86` peak-hold | `0x3ac7c`→r14 | `0x3aca0`/`0x3aca4` | **±12288** | not verified by me | unverified |
| `gp-0x6bbe` viscous | `0x3ac80`→r6 | `0x3ac90`/`0x3ac94` | **±2048** | not verified by me | unverified |
| `gp-0x6b26` inertia | `0x3ac98`→r11 | `0x3acb0`/`0x3acb4` | **±1024** | ≈14–21 % of ±511 | yes (already on file) |
| `gp-0x6ad4` | `0x3aca8`→r6 | `0x3acbc`/`0x3acc0` | **±10240** | not verified by me | unverified |

**No window** on the three remaining lanes: `r24`, `r26` (the RAM-gain lanes off
`gp-0x6e40/6e38/6e30/6e28`) and `FUN_00036682()`→`gp-0x6b46`.

### `gp-0x6b4c` — team-lead's named concern, RESOLVED [EVIDENCE]
Its producer `FUN_00026c80` clamps it to **exactly ±0x2800 = ±10240**:
```
000276de: addi -0x2800,r10,r0     ; test r10 vs +10240
000276e6: ble 0x000276fa
000276ec: movea 0x2800,r0,r8      ; r8 = +10240
000276f0: st.h r8,-0x6b4c[gp]     ; UPPER CLAMP
000276fa: addi 0x2800,r10,r0
000276fe: bge 0x00027712
00027704: movea -0x2800,r0,r8     ; r8 = -10240
00027708: st.h r8,-0x6b4c[gp]     ; LOWER CLAMP
00027716: st.h r10,-0x6b4c[gp]    ; pass-through, only when |r10| <= 10240
```
The aggregator window admits `x ∈ [−10240, +10240]` **inclusive** (at `x=+10240`,
`0xFFFFAFFF + 0x5000 = 0xFFFFFFFF` — no carry out, so CY=0, accepted; CY only sets at `|x| ≥ 10241`).
⇒ **the producer ceiling and the gate width are the SAME number.** The gate is vacuous, but by
*exactly zero margin* — it is a plausibility/corruption check, not a functional limiter.

**⇒ The LKAS lane is big, but it cannot trip its own gate.** That the two constants are deliberately
matched is [BELIEF] evidence the other seven are designed the same way — **but I verified only two of
eight (`gp-0x6b4c` at the producer, `gp-0x6b26` from the existing record). Six are UNVERIFIED by me
and the record's blanket "vacuous" claim should not be treated as closed on my authority.**
⚠ Residual: `movea -0x6b4c, gp, r7` @`0x28b38` takes the cell's **address** into a register (lockstep
repair via `FUN_0006b9fa`), so there is a register-indirect writer. It writes a repaired copy of the
same clamped value, so the bound holds — but an operand-text-only writer census would miss it.

## 8e. Independent third census of `0xC63AC` — CONFIRMS fw-levers [EVIDENCE]

`0xC63AC` = `tp+0x73ac`. Three methods, all run this session on `code.bin` / the stock image:

1. **Ghidra operand search**: `search_instructions("0x73ac")` → **1 hit**,
   `ld.hu 0x73ac, tp, r13` @`0x38202` in `FUN_00038148`. `instructions_scanned: 183570`,
   `truncated:false` (an unanalysed program would report 0 scanned).
2. **Raw LE byte scan, BOTH parities** (`hw2 ∈ {0x73ac, 0x73ad}` — covers the `hw2 = disp|1` trap and
   the `ld.bu` bit-0/parity trap): **6 raw hits**, adjudicated —
   | addr | hw1 | hw2 | base | verdict |
   |---|---|---|---|---|
   | `0x005b92` | 0x7207 | 0x73ad | r7 | EXCLUDED — base ≠ tp |
   | **`0x038202`** | 0x6fe5 | 0x73ad | **r5 = tp** | ✅ the one real access, matches Ghidra |
   | `0x064642` | 0xff80 | 0x73ac | r0 | EXCLUDED — r0 base, not a load |
   | `0x06e73e` | 0x07a4 | 0x73ad | r4 | EXCLUDED — base ≠ tp |
   | `0x0bd682` | 0x3f40 | 0x73ac | r0 | EXCLUDED — in the data/table region |
   | `0x0be9c2` | 0x3f40 | 0x73ac | r0 | EXCLUDED — in the data/table region |
3. **6-byte extended form** (`disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7f)` ⇒ needs `hw2=0x00e7`,
   low-7 `=0x2c`): **0 hits.**
4. **Register-indirect / absolute synthesis** (the class Ghidra misses): **`movea/addi/movhi` with
   immediate `0x63ac` — 0 sites image-wide.** The 9 `movhi 0xc` sites cannot form `0x000C63AC`
   without a paired `0x63ac` low half, and there is none.

⇒ **CONFIRMED: exactly 1 reader (`0x38202`, a `ld.hu` — a READ), 0 writers, no second encoding, no
absolute synthesis.** fw-levers' census is independently reproduced. ⊕ Note "0 writers" is trivially
true for any cell in the flash calibration block; the meaningful question was *additional readers*,
and method 4 closes that.

---

## 8f. The "sole actuation route" claim — REFUTED [EVIDENCE]

fw-loop: *"the only route from the LKAS command to the motor is `gp-0x6b4a` → `gp-0x6ad6` → PID →
`gp-0x6ad4` → aggregator, clamped to AUTH"*, with its own falsifier: *"If a second route exists, the
AUTH story is wrong."* **A second route exists.**

### The chain
1. **LKAS is lane 1** — the kit's own census (`reference_accord_gp6afe_gp6b4e_provably_zero_correction`:
   *"7 of 11 lanes, including lane 1 = the established LKAS lane"*).
2. **`0xC4124[1] = 0` ⇒ mode 0.** Byte-read `0xC4124 = [0,0,5,0,5,5,0,0,0,5,0]`, identical stock→v96.
3. **Mode 0 writes `gp-0x62b0[i] = REQ_B = gp-0x62f8[i]`** (`FUN_00026c80` else-branch,
   `*puVar35 = uVar18`). Mode 5 writes `0` there — the only reason the sibling lane is dead.
4. **`gp-0x62f8[lane]` is written at RUNTIME, paired with `gp-0x62e0[lane]`**, by `FUN_00025c32`:
```
0002647c: mov r1,r8  / 0002647e: shl 0x1,r8        r8 = lane*2
00026480: movea -0x62e0,gp,ep / 00026484: add r8,ep / 00026486: sst.h r12,0x0[ep]   REQ_A[lane]
00026490: movea -0x62f8,gp,ep / 00026494: add r8,ep / 00026496: sst.h r14,0x0[ep]   REQ_B[lane] <<<
```
5. **`gp-0x3d88 = Σ gp-0x62b0[i]` → `gp-0x6b4c = clamp(gp-0x3d88, ±10240)` → aggregator @`0x3aa3e`,
   unity weight** → `gp-0x6b94` → governor → shaper → `gp-0x6b98` → FOC.

⇒ **LKAS reaches the motor without touching `gp-0x6ad6`, the PID, `gp-0x6ad4`, or AUTH.**

### Where the reasoning failed
`0xC63CC = 0` does kill `gp-0x6b4c`'s second term — that arithmetic is right. The error is treating
the survivor `gp-0x3d88` as unrelated to LKAS. It sums **the same 11-channel request structure** that
feeds `gp-0x6b4a`; only the per-channel mode differs. ⊕ The kit already said so: *"The entire LKAS
contribution … flows through `gp-0x6b4c` … **and** through `gp-0x6b4a`."* ⊕ And `0xC6CD0`, our own 4×
LKAS forward gain (**stock 65535 → 3564 on every build v90→v96**), sits on the `gp-0x6b4c` lane — we
have been deliberately scaling the very route concluded to carry no LKAS.

### The contrast that makes it airtight
`gp-0x62c8[]` → `gp-0x6b4e` **is** genuinely dead: mode 0 writes it an explicit `st.h r0`, mode 5 never
writes it, boot zero. **`gp-0x62b0[]` under mode 0 gets a real value instead of a zero store.** All five
arrays are boot-zero (`gp-0x62f8` @flash `0x86DB8`), so liveness rests entirely on the runtime write at
`0x26496` — which link 4 shows.

### Premises (all confirmed; they were never the problem)
`0xC63CC=0` ✓ · `0xC4118` all-1 ⇒ `gp-0x3d84 ≡ 0`, 100 % bypasses the `0xC6194` slew limiter ✓ ·
`gp-0x6b4a = clamp(gp-0x3d80 + …, ±25600)` ✓ · **AUTH ramp header is `0xC67BE`, not `0xC67C8`** (that
is its `Y[0]`): count=3, X=[128,1280,3200] ct = [2,20,50] km/h, Y=[0,1024,1024] ⇒ 227 / 455 / 1024 at
6 / 10 / ≥20 km/h, reproducing fw-loop exactly. Partners: constant 5120 @`0xC679C`, and a `gp-0x6bda`
table X=[384,1280,12800] Y=[0,5120,5120] that cuts authority to zero **at the rack end stop** —
converging with §3.

🛑 **AUTH is real and correctly characterised. It is simply not exclusive, so it cannot explain the
slow return.** The story's elegance (low-speed, magnitude-independent, matching 2.7×) is not evidence.

### 🛑 Method note
14 of 15 `gp-0x62f8` base-setup sites are `movea -0x62f8, gp, **ep**`; the real accesses are
`sst.h/sld.h 0x0[ep]`, which carry **no `-0x62f8` in operand text**. An operand search finds the base
setup and **zero actual loads/stores** — the `-0x6350` false-zero class, applying to every request
array here. A Python `movea`-immediate scan reproduced Ghidra's 15 sites one-for-one.

### Not established
Magnitude of `REQ_B` on lane 1 — I proved the route exists, is runtime-written and is AUTH-free, **not**
what fraction of the delivered command it carries. That is a probe (`gp-0x6b4c` vs `gp-0x6ad4`), not a
trace.

---

## 8g. The complete lane map — LKAS's lane resolved independently [EVIDENCE]

`FUN_00025c32` reads its lane index from **`byte[0]` of the caller's stack struct**:
```
0x25c36: ld.bu 0x0[r6],r8        r6 = caller's sp
0x25c3e: cmp 0xa,r8
0x25c40: cmovh 0xa,r8,r1         r1 = min(lane, 10)
```
Each of the 10 callers stamps its lane as an **immediate** just before `mov sp,ep; sst.b r6,0x0[ep]`
(the `sst.b` sits exactly `0x18` before each `jarl`). All ten recovered:

| lane | caller | `mov imm` site | mode `0xC4124` | region |
|---|---|---|---|---|
| 0 | `FUN_0002e52e` | `0x2e62a` (`sst.b r0`) | **0** | CAN-RX cluster |
| **1** | `FUN_0002b422` | `0x2b522` | **0** | **CAN-RX cluster** |
| 2 | `FUN_0003405a` | `0x341fa` | 5 | assist-compute (adjacent to `FUN_00034350`, the base-assist damper) |
| 3 | `FUN_0002c246` | `0x2c35c` | **0** | CAN-RX cluster |
| 4 | `FUN_00023ad2` | `0x23bba` | 5 | assist-compute |
| 5 | `FUN_00023fe2` | `0x2415a` | 5 | assist-compute |
| 6 | `FUN_0003aff4` | `0x3b240` | **0** | assist-compute |
| 7 | `FUN_0003a8a8` | `0x3a956` | **0** | assist-compute |
| 8 | `FUN_0002caa2` | `0x2cbca` | **0** | CAN-RX cluster |
| 9 | `FUN_000339cc` | `0x33b44` | 5 | assist-compute |
| 10 | — | *no caller* | 0 | — |

Lanes 0–9 are each claimed exactly once; lane 10 has no submitter.

### The refutation no longer depends on the inherited "lane 1 = LKAS" attestation
**Every caller in the CAN-RX address cluster — lanes 0, 1, 3, 8 (`FUN_0002e52e`, `FUN_0002b422`,
`FUN_0002c246`, `FUN_0002caa2`) — is MODE 0.** All four mode-5 lanes (2, 4, 5, 9) belong to the
*internal assist-computation* clusters at `0x23xxx` / `0x33-34xxx`, one of which sits directly beside
the known base-assist damper.

⇒ **Whichever CAN-sourced lane carries LKAS, it is mode 0**, and mode 0 is precisely the branch that
routes `REQ_B` into `gp-0x62b0 → gp-0x3d88 → gp-0x6b4c →` the aggregator, AUTH-free. The kit's prior
census (lane 1 = LKAS, i.e. `FUN_0002b422`, a CAN-region function) is **consistent** with this and is
no longer load-bearing. [EVIDENCE for the map and the modes; BELIEF only for "LKAS is CAN-sourced",
which is not seriously in doubt.]

---

## 8h. 🛑 NEW TRAP CLASS: `ep`-relative short-format aliasing

**The most dangerous tool-zero found this session, because it does not return zero.**

### What it is
A gp/tp-relative array is addressed once by `movea <off>, gp, **ep**`, after which every actual load
and store uses the **short format** `sld.h/sld.hu/sld.b/sld.w` / `sst.h/sst.b/sst.w` with a small
displacement off `ep`. Those instructions contain **no trace of `<off>` in their operand text**.

An operand search for `<off>` therefore returns the **base-setup sites only** — a plausible-looking,
non-zero count that makes the census *look* like it worked, while **missing 100 % of the accesses.**

> **A census that returns 15 sites and misses every actual access is more dangerous than one that
> returns 0.** A zero prompts suspicion; a healthy-looking count does not.

Measured here: `-0x62f8` → 15 hits, **14 of them `movea … , gp, ep`**, and **zero** actual loads/stores.

### Enumeration recipe
1. Operand-search the offset → collect `movea <off>, gp|tp, ep` sites. **These are base setups, not accesses.**
2. For each, scan forward in the same basic block for `sld.*` / `sst.*` — those are the real accesses.
   The index is usually `add rN, ep` between the `movea` and the access.
3. Cross-check the base-setup list with a Python `movea`-immediate scan: `hw2 == ((-off) & 0xffff)`,
   `hw1` opcode field `0x31`, `reg1 = gp(4)/tp(5)`, `dst = ep(30)`. (Mine reproduced Ghidra's 15
   one-for-one.)
4. To ask *"can address X be reached this way at all?"*, bound it: `sld.hu` displacement is
   `disp7 × 2` = 0..254, so `ep` must land within 254 bytes below X. Enumerate `movea imm, tp, ep`
   (`hw1 = 0xF625`) and test whether any `imm` falls in `[off−254, off]`.

### ⚠ Also confirmed this session: `operand_pattern` syntax silently returns false zeros
`search_instructions(mnemonic="sst.b", operand_pattern="0x0[ep]")` → **0 matches,
`truncated:false`**. Ghidra actually renders the operands as **`r6, 0x0, ep`** (commas, no brackets),
so the filter never matched. Dropping the operand filter returned the sites immediately. Same class as
the `gp-0x6b98` "zero writers" incident. **Never accept a filtered zero; re-run unfiltered/scoped.**
⊕ `search_instructions(operand_pattern="0x7cd0")` likewise returned **0 with `truncated:false`** for
`0xC6CD0` — a cal we have written on seven builds. It is real; it simply has no direct tp-relative
reader (it lives inside a LERP table reached by a table-base pointer).

### Which of this session's censuses are affected
| census | affected? | why |
|---|---|---|
| `gp-0x62f8/62e0/62b0/6298/62c8/633c` base sites | **YES, and handled** | enumerated base setups by two agreeing methods; I did **not** enumerate the individual accesses, and say so |
| **`0xC63AC` (1 reader / 0 writers)** | **NO — re-tested and clean** | added a **fifth** method: 98 `movea imm,tp,ep` sites image-wide, **0** within 254 bytes of `0xC63AC`; and `gp`-based `ep` cannot reach the cal block at all (`movea` ±32768 from `0xFEDF8000`). **Safe to cut a build on.** |
| aggregator zero-reject window map (8 of 11 lanes) | **NO** | derived from `addi`/`cmovc` inside one function via mnemonic search, not offset text |
| `gp-0x37ba` no-non-zero-writer | **NO** | scalar, `gp`-relative direct form; `ep` aliasing needs a `movea … , ep` which does not occur for it |
| return-centre / end-stop cal reads | **NO** | all read via direct `tp`-relative `ld.hu`, byte-confirmed |

---

## 9. Residuals — what I did NOT close

1. **`gp+0x6441`'s writer set was not enumerated** (I enumerated `gp+0x6440`: `FUN_00035e00`
   @`0x3600c`, `FUN_000568d0` @`0x57b08`). The `< 3` test in `FUN_00036022` implies the author
   thought ≥3 reachable (probably an "unlearned/invalid" code). **The finding is robust to this
   either way**: if ≥3 is reachable, `cVar6` is forced to 1 = force-reset every tick, which pins the
   envelope at exactly ±9390 — the same conclusion, only more strongly.
2. **Register-indirect writers to `gp-0x37ba`** cannot be seen by operand-text search. The "dead
   re-centre branch" claim carries that standard residual. To close it: a raw LE byte scan for
   `st.h` with a computed base into `0xFEDF4846`.
3. **`gp-0x6bf0`'s counts-per-degree scale** is not pinned. Not load-bearing for any conclusion
   here (every threshold is cut from the same `0xC6150`, so the lane is scale-invariant), but it
   would be needed if anyone ever wanted to reason about it in physical units.
4. **`cal(0xC64A1)`** (`tp+0x74a1`) selects between two output forms in `FUN_00036388`
   (`sVar3 + sVar13` vs `sVar8 + sVar13`). Not read this session; it does not change the
   gate-shut ⇒ output-zero conclusion, since both forms are zero when the gate is shut.
