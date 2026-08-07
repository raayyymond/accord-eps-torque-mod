# HANDOFF 2026-08-07 (latest) — V76 flew clean; grind #1 is dose-limited, the ratchet is NOT; and the ReLU / bigger-table plan **inverts on contact with the evaluator**

**Session shape:** orchestrator + 6 subagents. Operator brief: *"I drove on V76. There is still grind #1
and micro-ratcheting at creep. Take V75's damper dose at ~5 mph and apply 150% of it. Both FactorC and
FactorE should be made ReLUs — one of them isn't. If there aren't enough points in the lookup table,
build new tables in free memory and repoint all readers."*

**Headline: the dose half of the brief is right and costs ONE u16 cell. The mechanism half is
unnecessary, and the FactorC-ReLU part is actively harmful.**

---

## 1. V76 FLEW, AND IT FLEW CLEAN

Route `75604b0a432fdc89_00000065--ae43aa0f27`, segs 0–10, **636.30 s / 63,477 frames**, 0–96.7 km/h,
engaged 450.98 s (**70.87%**).

**Build identity settled four independent ways** [EVIDENCE] — this matters, because the kit has
previously analysed a drive through the wrong build's decoder:
- bits 6/5 are structurally unreachable on the V76 cave: **0 / 63,477**.
- every frame's probe field is one of the 8 reachable combos: **0 violations**.
- V75's four damper bits are a **thermometer by construction**; 44,454 frames (70.0%) violate it ⇒
  **not a V75 log**.
- the superseded V76 (`V76-V74BASE-GATE-FB-ARM5244`) has bit3 structurally zero; here bit3 reads
  **99.926%** ⇒ ruled out too.

**No fault.** Zero DTC-active transitions, zero STEER_SENSOR_STATUS 7→4, zero `0x7FFF` angle sentinels,
no frame-rate collapse — the exact fingerprint that caught V74 (route 61) and V75 (route 5e).

### ★ The friction-margin probe: a clean, real null
**bit7 (`|gp-0x6b26| > 448`) fired 0 / 63,477 frames**, with the positive control (bit3, `gp-0x67fa == 5`)
alive at 99.93% in the same frames ⇒ **never fired, not never armed.** Across every speed band and both
arms (44,989 engaged / 18,488 manual). The friction lane never came within 63 counts of the 512-count
monitor ceiling on an ordinary 10.6-minute drive.
⚠ This **weakens but does not refute** the V73-unlocked-interlock story: it says whatever produced
V74's and V75's crossings is rare, not that it does not exist. `gp-0x6c2c`'s physical scale stays OPEN.

### ★ Mode lag measured directly — and it is 2.5× shorter than the record said
`gp+0x63fd` holds the ENGAGED column for a median **994.9 ms [830.0, 1575.0]** after `latActive` falls
(mean 1133 ms, range 830–2070, n=6 clean episodes, bootstrapped over episodes).
🛑 **Prior handoffs quote ~2.5 s.** This is a direct bit4 probe built for the question; treat it as the
better measurement, but n=6 on one route does not prove the 2.5 s figure was measuring the same thing.

---

## 2. ★★★★ THE DOSE-RESPONSE SPLIT — the most decision-bearing result of the session

Fit `ln(band / 24–28 Hz control) = a + b·k` over V72,V73 (k=0), V74 (0.5799), V75 (1.5798),
V76 (1.3866), creep, speed-stratified, **episode-bootstrapped**. V76 sits *between* V74 and V75, so a
monotone model makes a falsifiable point prediction rather than just a direction.

| band | V74 | V75 | V76 observed | monotone prediction | slope b [95% CI] | verdict |
|---|---|---|---|---|---|---|
| ratchet 6–9 Hz | 4.536 | 3.768 | 3.877 [3.098, 5.161] | 3.906 (−0.06 dB) | **−0.094 [−0.291, +0.098]** | **DOSE-INDEPENDENT** |
| grind #1 18–22 Hz | 3.538 | 1.336 | 1.577 [1.380, 1.831] | 1.613 (−0.19 dB) | **−0.614 [−0.810, −0.416]** | **DOSE-LIMITED** |

★★ **Grind #1 is dose-limited and the prediction HELD** — V76 landed on the V74→V75 interpolation to
within 0.19 dB. More dose is a validated lever.
🛑 **The micro-ratchet is dose-independent.** CI contains zero across k = 0 → 1.58, with V76's own point
sitting on a flat line. **Raising the damper will not fix the ratchet, and no build should be sold as if
it will.** If the ratchet is the operator's main residual complaint, `k` is the wrong knob.

**Presence on V76** (paired against the same build's own 24–28 Hz control): grind #1 rel. excess
**1.956 [1.214, 4.154]** (excludes 1 ⇒ real and present, worse than V75's 1.572, far better than V74's
9.154); ratchet **5.026 [3.824, 6.592]**, statistically indistinguishable from V74's and V75's.
**Both match the operator's report exactly.**

### 🛑 V76's grind-#2 prediction was FALSIFIED at the one powered rung
Predicted 0.57× vs V75 at 42 °/s; **measured 1.394 [1.017, 1.768] — 39% MORE**, the opposite direction.
85 °/s underpowered (n=7 < 8); 255 °/s never occurred on any of the three routes.
⇒ **Discount the arithmetic surface model's ability to predict delivered grind #2.** Same pattern as the
28 Hz lane-change transient. It does not invalidate the `k` dose axis, which was validated above.

---

## 3. ★★★★★ THE EVALUATOR — and why the operator's mechanism inverts

`FUN_00034350`, sole caller `FUN_00022ca0`. **Orchestrator-verified by decompile, not relayed.**

### Record access is a pointer array per factor
```
mode = *(u8 *)(gp + 0x63fd)
rec  = *(u32 *)(PTR_ARRAY + mode*4)          # 34 modes, 4 bytes/entry
```
`FactorB 0xC9CCC · FactorC 0xC9E9C · FactorD 0xC9DB4 · FactorE 0xC9F84 · ceiling 0xC77A0 · friction 0xCBE74`.
**Every mode has its OWN record — 34 distinct addresses over 34 modes, zero sharing.**

### Record layout [EVIDENCE, byte-verified]
```
base+0      u16    n            breakpoint count
base+2      n*i16  X[]          index, strictly increasing
base+2+2n   n*i16  Y[]          output, Q10 (1024 = unity)
base+2+4n   u16    terminator   0x0000 in every record read
total = 4 + 4n
```
🛑 **X starts at base+2, NOT base+4.** Reading at base+4 silently yields `[X1,X2,X3,Y0]` — the
orchestrator made exactly this error on the first pass. Shipped counts: ceiling n=2 · friction n=3 ·
FactorB/C/E n=4 · FactorD **n=5**.

### 🛑 THE COUNT FIELD IS NEVER READ. More points is a CODE edit.
Each factor's lookup is a genuine `while (X[i] <= idx) i++` search loop, but `n` is pinned per factor by
three hardcoded immediates:

| factor | &Y[0] | X_last | Y_last | n |
|---|---|---|---|---|
| B / C / E | rec+10 | rec+8 | rec+0x10 | 4 |
| D | rec+0xc | rec+10 | rec+0x14 | 5 |
| ceiling | rec+6 | rec+4 | rec+8 | 2 |

⇒ **"just make a bigger table" is impossible as a data-only edit.** It requires editing the always-on
base-assist damper's own instructions — the class that bricked V24, V27 and V48B.
⚠ **Correction to a subagent's mechanism description**, recorded because the pattern recurs: it reported
the five LERPs as separately *unrolled* compare chains. They are loops. The **conclusion** was right; the
mechanism was not. Caught by decompiling personally.

### The product, and the clamp nobody had written down
```c
uVar7 = ((((base*(base<0x401) + (base>=0x401)*0x400)   // gp-0x698a, CLAMPED to <= 1024
            * FB >> 10) * FC >> 10) * FD >> 10) * FE >> 10;
if (0 < *(short *)(gp - 0x6abe)) uVar7 = -uVar7;        // SIGN from gp-0x6abe, NOT the index

uVar10 = ceiling_LERP(gp-0x6ac2);        // ptr 0xC77A0, n=2, X=[300,800] Y=[512,1024]
                                          // if gp-0x6ac2 >= 0x32c9 -> *(u16*)0xC6158 = 512
gp-0x6bd0 = clamp(uVar7, -uVar10, +uVar10);              // SYMMETRIC HARD CLAMP
```
★★ **`|gp-0x6bd0|` can never exceed 1024, and is capped at 512 at low ceiling index.** This is the
binding constraint on damper dose, and it is what breaks the ReLU plan (§4).
Also: **`gp-0x6bd0` is lockstep-shadowed at `gp-0x4cf2`**; two gates zero the chain —
`FactorC → unity if (gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1)`, and
`damper → 0 unless (gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)`.
🛑 **`gp-0x67f4 != 1` disables FactorC's speed shaping entirely and has never been probed.** OPEN.

---

## 4. ★★★★ WHY THE ReLU PLAN INVERTS

**"Not enough points" is false, and it was never the obstacle.** A ReLU has 2 DOF; a 4-point table has
8 numbers and spends 3 on collinearity. Both clamps are independent of the point count.
**More points buy EXACTLY ZERO for a pure ReLU** — there is a constructive witness:
`C X=[0,10815,21630,32445] Y=[0,8946,17892,26838]`, `E X=[0,4356,8712,13068] Y=[0,21824,43648,65472]`
gives dose 206, true-ReLU on both, `E_Y[0]=0`, add-only over 406,500 points.

**🛑 The constraint that breaks is the implicit sixth one — "must not saturate" — and it is
parameter-free.** A ReLU FactorC is speed-proportional with its knee below 515 counts, so
`dose(v,99)/dose(515,99) = v/515` **exactly, whatever values you pick**. Pinning 206 at 5 mph forces
**3,593 raw counts at 140 km/h = 7.02× the 512 ceiling**, and 3.01× at 60 km/h.
**It rails above 3.2 °/s at 140 km/h, 7.0 °/s at 60, 21 °/s at 20 km/h.**

★★ **A railed damper whose sign comes from a DIFFERENT cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay** — describing function `4·512/(πA)`, unbounded as amplitude falls.
**You would forbid the relay at `E_Y[0]` and re-create it at the ceiling.**
On V76's flat FactorC, the same 206 dose rails no earlier than **563 °/s — 176.7× more usable linear
range.**

**Which one "isn't a ReLU" depends on the definition, and the two readings point at opposite tables:**
- **Literal** `max(0, k(x−x0))`: **FactorC** fails (nonzero 566 floor, flat across three of four
  segments, top plateau). FactorE has a true zero floor.
- **The operator's own recorded gloss**, from `v76_surface.py`: *"FactorC 'FLAT — no taper down, like a
  rectified linear unit'"*, read as a **floor clamp**. Under that gloss **FactorC already is one** (and
  the V76 filename says `RELU`), and **FactorE** — with three slopes, 2.521 / 0.100 / 0.259 per count —
  is the one that isn't.

⇒ **Neither should be made a literal ReLU**, and the reason is the ceiling clamp, not the point count.
📋 **Rule to carry forward: ask anyone proposing a re-point which FOURTH segment they need. If they
can't name it, n=4 is enough.**

### Relocation, for the record — it is available, just not needed
[EVIDENCE] Repointing is **cal-only**: one u32 into `FACTOR_C_PTRS+26*4 = 0xC9F04` / `FACTOR_E_PTRS+26*4
= 0xC9FEC`, plus record bytes. **`0xD7BB8`–`0xD7FEF` is 1,080 B of virgin `0xFF` in the same page and
the same CRC block (`0xD7FFC`) V76 already recomputes**; the identical run exists at the same offset in
every mode-record page (`0xD0BB8`…`0xE1BB8`). Confirmed unreferenced by a byte-granular whole-image u32
scan (4 raw hits, all disassembled to ordinary displacement/immediate fields, zero real pointers).
**V74's "the six pointer arrays must stay byte-identical to stock" was a SELF-IMPOSED BUILD GUARD, not a
firmware requirement** — the sole reader dereferences without comparison; the only flash writer
(`FUN_0000d934`) has zero static callers; the CRC verifier (`FUN_0000b006`) is UDS-only, with no periodic
app-side re-check. Every documented lockstep pair in this kit is RAM-to-RAM.
🛑 Leave `0xD7FF0`–`0xD7FFB` alone; `0xD7FF8`–`0xD7FFC` is the block's own self-descriptor (`d7 00 01 00`).
⊕ **New Ghidra trap:** `get_xrefs_to(0xD780C)` returned *"No references found"* although the pointer
demonstrably exists at `0xC9FEC`. The twin `0xD77D0` resolved correctly. **Do not trust Ghidra xref
completeness on pointer-array slots.**

⊕ **A free lane nobody has used:** FactorB (n=4) and **FactorD (n=5)** are byte-read flat `Y=1024`
(inert unity) in modes 24 AND 26 on this car, on the same multiply chain. FactorD's axis is `gp-0x6a10`
(angle-tracking error), independent of speed and rate, gated on `gp-0x67fe ∈ {1,2}`. It appears in
`build_v43/v72–v77_tva.py` **only in assert-untouched checks — UNTESTED, not falsified**, and it is
already a **5-point** lane. What `gp-0x6a10` does at the speeds/rates that matter is untraced.

---

## 5. THE BUILD — V78

🛑 **Named V78, not V77.** `build_v77_tva.py` exists, and the V77/V77B `.rwd`s are already renamed
`SUPERSEDED-2026-08-07-BY-V76-V38BASE-…` with `_v77b_C63A0.1024_v75base_plain_image.bin` on disk.
Reusing V77 would break "exactly ONE flashable `.rwd` per build number" and re-open the recorded
plain-image-overwrite hazard.

**Base:** V76 (`_v76_v38base_relu_damper_plain_image.bin`, `54a212a2…c830f33`) — the build that flew.
**Edit: one u16 cell.** FactorE mode-26 record `0xD780C`, **`Y[1] 300 → 449`**, i.e. **2 bytes at
`0xD7818`, `2c01` → `c101`**.
```
V76:  E X = [0, 119, 2500, 4000]   Y = [0, 300, 539, 927]
V78:  E X = [0, 119, 2500, 4000]   Y = [0, 449, 539, 927]      FactorC UNCHANGED [566,566,566,908]
```

| | dose @5 mph, r=99 ct | k | vs V75 | vs V76 |
|---|---|---|---|---|
| V75 (faulted) | 137 | 1.5798 | — | — |
| V76 (flew) | 137 | 1.3866 | 1.00× | — |
| **V78** | **206** | **2.0840** | **1.504×** | **1.504×** |

**The dose lift decays with rate — this is the design's virtue**, and it is why the plateau removal is
kept rather than widened: ×1.50 at 21 °/s · ×1.46 at 42 °/s · ×1.40 at 85 °/s · ×1.20 at 255 °/s ·
**×1.00 at 530 °/s and above.** Max product stays `(566*927)>>10 = 512` — exactly the ceiling floor, so
**this edit introduces no clipping V76 did not already have.**

**Guards:** Y monotone `[0,449,539,927]` ✓ · X untouched ✓ · **`E_Y[0]=0` retained** ✓ (no Coulomb
relay) · add-only vs stock ✓ · mode 24 byte-stock ✓ · six pointer arrays byte-stock ✓ ·
`rec_len = 4+4n` used for clearance, not a flat 0x18 span.

*(Build artifacts, probe map and SHA256s: see §7.)*

---

## 6. 🛑 THE RISK, STATED PLAINLY

| | k time-weighted, 35–80 km/h | vs V74 | vs V76 |
|---|---|---|---|
| stock / V38 | 0.0692 | 0.15× | 0.05× |
| V74 (flew) | 0.4493 | 1.00× | 0.32× |
| V75 (**hard-faulted**) | 1.0699 | 2.38× | 0.77× |
| V76 (flew, 1 drive) | 1.3934 | 3.10× | 1.00× |
| **V78** | **2.0855** | **4.64×** | **1.50×** |

- **V78 is the first point in this lineage above V75's creep loop gain** (k 2.084 vs 1.580), and V75
  hard-faulted.
- [BELIEF] the fault was the friction lane and the V38 base closes it ⇒ this is a **GATE-2 stability**
  exposure, not a re-opened DTC-0x1d exposure. **But the two have never been separated on-car.**
- **Two hard faults in two days. V76 has exactly one clean flight. n=1 is not a safety record.**
- Grind #2 rose 39% from V75 to V76 against a prediction of −43%; V78 adds a further ×1.46 at 42 °/s.
- 🛑 **The micro-ratchet is not expected to improve at all.**

**Nothing here is clearance to fly. The operator makes that call.**

---

## 7. ARTIFACTS

**V78 — BUILT, VERIFIED, UNFLASHED.** Build script `analysis-2020accord/build_v78_tva.py`.
- rwd `39990-TVA,A160-V78-V76BASE-EY1.449-dose206-probe-6bd0-63fd-67fa-0x13000-0x100000.rwd`
  sha256 `305234c37f797d0476b89ac793b414d6b0d5ba7cbbadf665d6e64778fe091afb`
- image `_v78_v76base_ey1_449_dose206_plain_image.bin`
  sha256 `c8d8e5e1c606dd920ccec8d41ea6398c73dbe473f58912092770e700ffd50ab1`
- base `_v76_v38base_relu_damper_plain_image.bin` `54a212a2…c830f33`

**V76 → V78 = 51 bytes in 7 runs, all attributed** (orchestrator-verified independently from the
artifact on disk, script `verify_v78.py`, not relayed from the builder):
| run | bytes | attribution |
|---|---|---|
| `0xC4B4A`–`0xC4B76` (4 runs) | 42 | the probe cave — **entirely inside the proven 68-byte extent** `[0xC4B34, 0xC4B78)`; extent NOT grown |
| `0xD7818` | **1** | **the calibration edit** — FactorE m26 `Y[1]` `0x2C`→`0xC1` |
| `0xC4FFC`, `0xD7FFC` | 8 | the two CRC trailers, the same two V76 already recomputes |

🛑 **ONE byte, not two** — `300 = 0x012C` and `449 = 0x01C1` share their high byte, so only the low byte
moves. The "count CELLS, not bytes" trap, hit again; the orchestrator's own spec said 2 bytes.

**Independent verification, all PASS:** FactorE m26 `X=[0,119,2500,4000] Y=[0,449,539,927]` · Y monotone
and `E_Y[0]=0` · FactorC m26 byte-identical to V76 `[566,566,566,908]` · **all six factors' mode-24
records byte-stock** · **all six pointer arrays byte-stock over all 34 modes** · `dose(515 ct, 99 ct)`
**137 → 206, ratio 1.5036, k 2.0840**.

### The probe — and the builder corrected the orchestrator's spec
| bit | predicate | why it earns its bit |
|---|---|---|
| 7 | `\|gp-0x6bd0\| >= 448` | **448 < 512 ≤ ceiling at EVERY value the LERP can produce**, so **bit7 == 0 across a drive PROVES no clipping occurred, whichever ceiling was in force** — i.e. no Coulomb relay at the rail, the exact hazard raising dose creates. Its null IS the answer. |
| 6 | `\|gp-0x6bd0\| >= 192` | **the V76→V78 DOSE DISCRIMINATOR.** The same threshold needs **598 ct (127 °/s)** on V76 and **93 ct (20 °/s)** on V78 — a **6.4× shift**, and 93 ct sits just under `R_OP` = 99 ct, so it runs at ~50% duty inside exactly the bursts this build is dosed for. Also calibrates the unobservable `gp-0x6ac0` against CAN steering rate. |
| 4 | `gp+0x63fd & 0x2` | mode index — the mode-lag measurement is still only n=6 |
| 3 | `gp-0x67fa == 5` | **the positive control** |

🛑 **The orchestrator specified bit6 as `>= 512`; the builder refused it and was right.** `>= 512` is
*implied by* `>= 448`, so if bit7 reads zero the 512 rung is zero **without having been measured** — a
bit spent on a conditional refinement of a null, which is precisely the V64/V68/V69 failure mode
(*"size a probe rung against the lane's own reachable output"*). Recorded because the orchestrator
issued the bad spec and the subagent caught it, which is the direction this kit less often sees.
⊕ Sizing context: the kit's observed rate maximum across its whole corpus is **1,941 counts**
(RULE 8, route 5d, both CAN channels agreeing). At r = 1,941 this build's damper tops out at **285**
counts to 80 km/h and **333** at 96.7 km/h — comfortably under 448.

🛑 **REPO DEFECT, reported and deliberately NOT fixed this session:**
**`rlog-tools/decode_v76_probe.py` decodes the SUPERSEDED V76** (the V74-base `GATE-FB-ARM5244` build),
**not the V38-base build that actually flew.** It was caught before use — the census agent wrote a fresh
decoder (`analysis-2020accord/v76flight_extract.py`) that re-reads the bit weights, thresholds and
`wire_model()` straight out of `build_v76_v38base_tva.py` at import time and cross-checks its own decode
against the builder's own function exhaustively. **That re-read-the-builder discipline is the pattern to
keep**; a stale hand-maintained decoder is exactly how a drive gets analysed through the wrong build.

⚠ **One residual the tracer flagged honestly and did not close:** its exactly-once byte scans cannot rule
out a `movhi`+`movea` **split-immediate** reference to a record or pointer-array address elsewhere in the
image (low search specificity — many unrelated `0xD0000`-range accesses share the same `movhi` high
half). Judged low-risk given the single-caller / no-parameter structure of `FUN_00034350`, but **not
formally closed.** It would matter only for a relocation, not for an in-place cell edit.

🛑 **REPO DEFECT, reported and deliberately NOT fixed this session:**
**`rlog-tools/decode_v76_probe.py` decodes the SUPERSEDED V76** (the V74-base `GATE-FB-ARM5244` build),
**not the V38-base build that actually flew.** It was caught before use — the census agent wrote a fresh
decoder (`analysis-2020accord/v76flight_extract.py`) that re-reads the bit weights, thresholds and
`wire_model()` straight out of `build_v76_v38base_tva.py` at import time and cross-checks its own decode
against the builder's own function exhaustively. **That re-read-the-builder discipline is the pattern to
keep**; a stale hand-maintained decoder is exactly how a drive gets analysed through the wrong build.

⚠ **One residual the tracer flagged honestly and did not close:** its exactly-once byte scans cannot rule
out a `movhi`+`movea` **split-immediate** reference to a record or pointer-array address elsewhere in the
image (low search specificity — many unrelated `0xD0000`-range accesses share the same `movhi` high
half). Judged low-risk given the single-caller / no-parameter structure of `FUN_00034350`, but **not
formally closed.** It would matter only for a relocation, not for an in-place cell edit.

## 8. OPEN, in priority order

1. **The micro-ratchet needs a non-dose lever.** Dose is resolved-flat across k = 0 → 1.58.
2. **`gp-0x67f4`** — the unprobed enable that turns FactorC's whole speed shaping to unity.
3. **`gp-0x6ac2`** — the ceiling index. Every rail figure in this document assumes it sits at 0
   (ceiling 512); if it ever exceeds 300 the ceiling rises toward 1024 and the rails move later.
4. **`gp-0x6c2c`'s physical scale** — still open; V76's bit7 null bounds it from one side only.
5. **FactorD (`gp-0x6a10`)** — a free, 5-point, never-touched lane on the same multiply chain.
6. **Grind #2's delivered response** — the arithmetic surface does not predict it.
