# STATE — living current state of the kit

**Last updated: 2026-08-13 (latest) — **V98 FLEW as route `0x81`**; the COMPARATOR ANSWERED, and it
refuted the "arms are wildly unequal" belief. `0xC63AC` moves from UNINTERPRETABLE to **WRONG-DIRECTION**.**

🛑🛑 **ON THE CAR: V98.** Route `0x81` (`75604b0a432fdc89_00000081--c7103d2cb4`, 3 segments,
cache `_cache_r81/`), 2026-08-12, **fault-free** — 0 sentinels on `0x14A`/`0x18F`, `CONFIG_VALID`
1.00000, `OUTPUT_DISABLED` 0.00178, DTC bit2 0.00000, `STEER_STATUS` `{0: 17981, 3: 2}`.
**IDENTITY IS SINGLE-FRAME PROOF:** `0x14A` byte7[7:6] == **2** on **17,983 / 17,983 frames,
duty 1.000000** (V96/V97 hard-wire 1; ≤ V91 give 0 ⇒ structurally excluded).
181.5 s total · **65.9 s engaged in 3 episodes** (longest 29.8 s) · engaged p50 **5.58 km/h** ·
⭐ **plus a BACK-TO-BACK LKAS-OFF ARM** — engaged ends 110.56 s, the operator's deliberate
*"this is how smooth it should be"* demonstration begins 110.57 s. **Consecutive frames, same lot,
same tyres.** This is the within-drive matched control the kit had never obtained.
⇒ **MAKE THE LKAS-OFF ARM MANDATORY IN EVERY FUTURE DRIVE PROTOCOL.** V98's spec called it
*"optional and free"*; it is neither.

⊕ **V98 was a ZERO-CALIBRATION INSTRUMENT BUILD — no symptom verdict is expected or claimable from
it.** The V97→V98 delta is **146 bytes, 142 cave + 4 CRC, ZERO calibration bytes** (verified from the
images two ways).

🛑 **PRIOR OPERATOR REPORT, on V97 (route `0x80`), VERBATIM:** *"I did not feel any difference in
grinding or stuttering (micro-ratcheting) behavior at all on V97, so I stopped the drive."*
⊕ **"Stuttering" ≡ micro-ratcheting — his own parenthetical.** It is not a fourth symptom.

⚠ **IDENTITY IS V96-OR-V97, NOT SINGLE-FRAME V97.** `0x14A` byte7[7:6] ≠ 0 on **10,750/10,750** frames
⇒ **not V94, not V92, not anything ≤ V91** (all mask those bits off — structural). But **V96→V97 is
5 bytes (one cal + its CRC)**: cave, 427 repoint and every bit map are **identical**, so *no* frame can
separate them. We rely on the operator's statement that V97 was flashed.
⇒ 🛑 **STANDING REQUIREMENT: every build must carry a BUILD-IDENTITY FIELD that changes on every cut,
independent of the lever under test.** 2 bits (byte7[7:6]) gives only ONE clean generation and
V96/V97 already burn {1,3}; a durable field needs ≥3 bits and its own `0x18F` hook — **as its own
build**, never combined with a new measurement class (that is how V24/V27/V48B bricked ECUs).

🛑🛑 **THIS FILE SAID "ON THE CAR: V94 … it is still flashed" FOR A FULL SESSION AFTER V96 FLEW, AND
IT COST REAL WORK.** It sent the session's strongest analyst to close its verdict with *"fly V96, S2
answers it"* — V96 had already flown and its regressor was 34× over-range, so **S1 and S2 are BOTH
VOID**. Seventh instance of the kit's "row says UNFLASHED after it flew" defect.
⇒ **NEW CLOSE-OUT GATE, mechanical, run it every time:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`, reconciled
against the identity bit from the most recent route. The old rule ("write the flight result in the
same pass that scores the flight") only fires if someone remembers; this one fails loudly.

## ⭐ FLOWN 2026-08-12 AS ROUTE `0x81` — **V98**, the first COMPARATOR probe in the kit
🛑 **This heading read "BUILT AND UNFLASHED" for a full session after V98 flew — the EIGHTH instance
of the "row says UNFLASHED after it flew" defect. Corrected 2026-08-13.** See the flight result and
the comparator verdict at the head of this file.

```
39990-TVA,A160-V98-V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2-0x13000-0x100000.rwd
  image c9babfed6acf24c0c5877754149a60fd5866dae8407029d7a3a5d74870d151d9
  rwd   fcfa1baa82ea8fbca104eee5c8a398b7d5de8762629351128b05e0cb811e5e3c
  builder analysis-2020accord/build_v98_tva.py   199/199   BASE = V97 (on the car)
```
🛑 **ZERO calibration bytes. ZERO 427 bytes. Cave only — AN INSTRUMENT, NOT A FIX.**
It answers the one question this session could not: **which arm of the observer residual dominates.**

| bit | signal | role |
|---|---|---|
| byte4 b7 | `gp-0x6b70 < 0` | V96's rung, byte-identical |
| **b6** | ⭐ `\|gp-0x6bfe\| ≥ \|gp-0x374c>>4\|` | **MODEL vs ACTUAL** |
| **b5** | ⭐ `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` | **REQUEST vs ACTUAL** — with b6, ranks all three arms per frame, **no scale assumption** |
| b4 | `(gp-0x374c>>4) < 0` | V96's rung — **the converse positive control** (measured `arg(B′)−arg(rate)` = +78.6°/+78.0°) |
| b3 | `gp-0x6752 ≥ 0` | closes a multi-session blocker; **a DEPENDENCY, not a rider** |
| byte7[7:6] | hard-wired **2** | identity + liveness |

**Orchestrator-verified from disk:** both hashes ✓ · V97→V98 diff **146 B**, all in `0xC4B34–0xC4BCD`
+ `0xC4FFC`, **zero unattributed** ✓ · **every cal cell identical to V97** ✓ · **GATE 2 re-derived
independently — exactly 3 stores across exactly 2 cells (`gp-0x1514`, `gp-0x1511`)** ✓.
**GATE 1 PASS** on all four cells; wider 32-bit span scan **67 accesses, ZERO span-only hits**.
**Hook proven from the image to be the 100 Hz `0x14A` builder, NOT the 1 kHz task** (`0x55C14 =
movea 0x14A,r0,r8`). Cave **112 → 154 B (+37.5 %)**, 12.7 % of the extent — stated, not claimed away.

🛑 **SCORER WARNING — the ~50-build "byte4[7:3] is always ODD" convention DOES NOT HOLD on V98.**
`b3` is a measurand, so **byte4 goes EVEN whenever `gp-0x6752 < 0` — that is the FINDING, not a fault.**
Liveness moved to **byte7**. Without this a scorer pulls a working build.
🛑 **`0x7FFF` sentinel pre-registered:** when the plausibility latch fires, `gp-0x6bfe` = `0x7FFF` and b6
reads TRUE for an unrelated reason. The latch rails `gp-0x6b70` ⇒ **427 pins at exactly 1023.
Score b6 only on frames with 427 ≠ 1023, and report the excluded count.**
⚠ **One open gap before any flash:** `mov`'s flag-transparency is **BELIEF** — SLEIGH + Honda's own
instruction scheduling, not a manual quotation.

**DRIVE PROTOCOL: ONE parking-lot creep, LKAS engaged, hands on — stop the moment the symptom is felt.**
~15–30 s of engaged frames. **No matched arms, no episode counts, no highway, no second drive.**
Optional and free: a few seconds of the same creep LKAS-off; and 60 s turning the wheel by hand with the
car OFF (a positive is strong, a negative is weak).

---

## 🛑 V97's VERDICT — UNINTERPRETABLE. Not falsified. **Do not re-dose `0xC63AC`.**

`0xC63AC` 102 → 150, the Path-2 IIR pole in `FUN_00038148`. **FLEW route `0x80`.**

✅ **THE LEVER IS LIVE — BOTH OF THE OPERATOR'S OWN HYPOTHESES ARE REFUTED.**
- *"A mistaken cal address"* — **excluded 3 ways.** `0x38202` bytes `e5 6f ad 73` = `ld.hu 0x73ac[tp]`;
  `tp+0x73AC = 0xC63AC` reads **102 / 102 / 150** (stock / V96 / V97); off-by-0x1000 excluded
  (`0xC53AC` = 683, identical in all three) and the six neighbour cals `0xC63A0..0xC63AE` all 1024
  unchanged. Census **1 reader / 0 writers**, five methods, Ghidra∖Python set-difference **EMPTY**.
- *"The logic we touched isn't used"* — **REFUTED statically AND dynamically.** `FUN_00038148`'s sole
  caller guards it with `andi 0x830,r25,r28` + `cmp r0,r28`/`be` @`0x22672`, **byte-identical to the
  guard on the assist-channel mixer** @`0x225EE` ⇒ **a shut gate would mean NO POWER ASSIST AT ALL.**
  And `sign(gp-0x374c)` **toggled 181× in 109 s** on this route. **No speed gate, no rate gate, no
  engagement gate anywhere on the path**, and the accumulator update precedes the only in-function gate.

🛑 **WHY IT COULD NOT BE SCORED — three independent reasons, none of them the lever:**
1. **NO INSTRUMENT.** V96's cave is carried unchanged; its regressor is **34× over-range** — `M ≡ 0` on
   **10,749/10,749** frames (third replication: 7e 99.90 %, 7f 99.97 %, r80 **100 %**), `Mlo` duty
   **0.0000**. S1/S2 **VOID** — conceded in `build_v97_tva.py:99-100` **before the flash**.
2. **EXPOSURE.** **1** engaged hands-off episode ≥2 s and **1** decaying-angle return, against **24/27**
   and **14/11** on 7e/7f — and the `|Q| = 1.233` direction result rests on **25**.
3. **THE OBSERVABLE.** **DC gain is 1.000000 at any `A` — a POLE, not a GAIN** ⇒ **no amplitude
   statistic can see it, and none was pre-registered.** Measured anyway: phase contrast **+3.27°** in
   one cell, **−4.08°** in the other (**opposite signs**); 6–9 Hz cross-build ratio **5.92× is SMALLER
   than r7e's own split-half noise 6.98×**; the `sign(gp-0x374c)` crossing-rate test sits inside its own
   split-half noise with the control bit moving too. **Four channels, four closing mechanisms.**

⊕ **V97 NEVER CLAIMED a grinding or ratcheting fix.** Its header prices only a **21 Hz cost** and argues
direction from **hands-off returns**. *"No difference in grinding"* **is consistent with the build
working exactly as specified.**

⚠ Correction: the build docstring's per-`A` phase row is **mis-tabulated** (correct: −23.63° / −15.81°);
the **deltas the decision rested on are right**. Task rate is **1000 Hz, EVIDENCE** (`0xC64DF` = 100
measured on-car at 100.00 ms + the `0x830 ⊆ 0x930` lockstep) — 🛑 **NOT from OSTM0**, which is 500 Hz
because PCLK is 40 MHz; that inference is a recorded red herring an agent nearly shipped this session.

🛑 **The number V95 is BURNED — see §A5.** ⚠ The `rlog-tools/v95_*.py` files are **analysis**
scripts, not build scripts.

🛑🛑 **THIS FILE HAS A HARD SIZE CAP: 256 KB. Keep it under ~150 KB.** On 2026-08-09 it reached
**506 KB / 6,114 lines / 53 sections** — past the `Read` limit, so no agent could load it in one call
and **the tail was silently invisible**. 47 superseded sections were split out verbatim to
**`docs/STATE-ARCHIVE-pre-V89.md`** (432 KB) by `analysis-2020accord/shrink_state_md.py`; the
2026-08-11 V90-flight headline went to **`docs/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`**
(30 KB) at the 2026-08-12 close-out. Nothing was deleted. **Update this file IN PLACE at every
close-out. Never append a new dated block — supersede the old one.** Per-build history belongs in
`docs/BUILD-LINEAGE.md`, narrative in `docs/HANDOFF-*.md`, durable facts in `memory/`.

**Reading order:** this file → `docs/BUILD-LINEAGE.md` (RULES 3/5/6/7 first) → the latest
`docs/HANDOFF-*.md` → `memory/MEMORY.md` + `memory/MEMORY-PART2.md` + `memory/MEMORY_CONSTELLATION.md`.
🛑 `memory/MEMORY.md` was split in two on 2026-08-12 — it had reached **287 KB against a 256 KB `Read`
cap**, so its tail was silently invisible. **Read BOTH parts.** The archives are records, **not**
instructions — do not reason from them.

---

## ★★★★★ THE STRUCTURE, ESTABLISHED 2026-08-12 — V89 AND V97 PUSHED ON OPPOSITE ARMS OF ONE OBSERVER RESIDUAL

`FUN_00038148` @`0x38236-0x3823A`, coefficients **exactly ±1**, verified from raw bytes
(`0x38238 subr r15,r6` = opcode `0x0C`; `0x3823A add r9,r6` = opcode `0x0E`):

```
FUN_0003b8f6  — the 1 kHz PLANT MODEL / disturbance observer
                K0 0xC4080=0 (NEVER RAISE) · K1 0xC40D2=204 (V89, ON THE CAR) · relay 0xC40BC=600
                EMAs 0xC40D4=573 · 0xC40D6=246 · 0xC40D0=408 · 0xC40D8=3686   (all four VIRGIN)
      │ gp-0x6bfc → FUN_0003bc20 (plausibility ±20000, else force 0x7FFF)
      │ gp-0x6bfe ────── MODEL   ────────┐  UNFILTERED   ◄── V89's K1 acts HERE
LKAS 11-slot aggregator FUN_00026c80     │
      │ gp-0x6bfa ────── REQUEST ────────┤  UNFILTERED   (its ±20000 gate is DEAD — writer pre-clamps)
six lanes → ×sign(gp-0x6752) → ×2639(0xC6468) → <<4
      │ IIR pole 0xC63AC 102→150 = ALL OF V97
      │ (gp-0x374c>>4) ─ ACTUAL  ────────┘  ◄── V97's pole acts HERE.  MEASURED < 2048, 100 % of r80
                              iVar6
          gp-0x6b70 = sign(iVar6) × LERP(|iVar6|), clamp ±8192 (0xC6200)  = the PID REFERENCE
```

🛑 **BOTH ARMS ARE ESTIMATES OF THE SAME QUANTITY, in the same units, scaled by the same `0xC6468`=2639,
entering a DIFFERENCE.** ⇒ **V89's K1 measured FLAT and V97's pole felt like nothing, and one unmeasured
quantity explains both: the arms may be wildly unequal, so whichever you move, the residual barely
notices.** [BELIEF — but it is the first account explaining two nulls with one mechanism.]

🛑🛑 **A "≤ 9 % share" bound was computed and is RETRACTED — DO NOT REUSE IT.** Bounding one arm against
the other's *admitted range* is invalid for a difference of correlated estimates; the denominator is the
**residual**, not the range. **Path-2's share is UNRESOLVED, not small.**

### The Stage-2 transfer is FULLY READABLE — and the rescale is the IDENTITY
🛑 **`STATE.md` §A6b's "the transfer cannot be read from the image" is FALSE**, and so is the standing
*"`f′` swings ≥10× and cannot be pinned statically"*: **the swing is 1.000×.** `gp-0x6982`/`gp-0x6984`
(the X-divisor and Y-multiplier) have **ZERO writers image-wide** — Ghidra + raw disp16 + raw disp23 +
an exhaustive 32-bit-literal search, **with a working positive control** (the neighbours `gp-0x6980/86/
88/8A` all DO have `st.h` writers and the scan found them) — and both boot to **1024** from `.data`
(flash `0x8672E`/`0x8672C`). The `[204,2048]` cal rails guard a value that never moves.

Knots (mode 26, creep; `0xC63AE`=1024 ⇒ the LERP index is `|iVar6|` **raw**):
```
0.0 km/h  X [0,200,400,800,1200,1800,3000,5000,12000,14490]  Y [0,471,880,1408,1689,1953,2376,2844,4114,8192]
6.6 km/h  X [0,178,356,719,1200,1800,3000,5000,10681,14490]  Y [0,452,839,1382,1838,2131,2546,3043,4245,8192]
```
**Route 80 inverted:** `|gp-0x6b70|` p50 320 → `|iVar6|` **126–136** · p90 2,534 → **2,965–3,675** ·
max 3,187 → **5,681–6,891**. ⇒ **`|iVar6|` ≤ ~6,900 at creep, ~130 half the time** — 2.9× tighter than
the ±20,000 clamp. ⊕ **`|iVar6| ≈ 130` median against a six-lane term admitted to 2048 hints at strong
CANCELLATION between the three terms** — exactly what an observer residual should do. [live hypothesis]
⚠ **These numbers DO NOT TRAVEL above 50 km/h** — `0xC669A`/`0xC66A8` truncate the LERP's X axis to
7,000 there. ⚠ **`mode 24 ≠ mode 26` in THIS family** (recs 0/3/4/5 + breakpoints differ) — the
"stock ships 24 ≡ 26" memory is scoped to the **damper** families and does not generalise here.

### Other results from route `0x80`
- **427 lane (`gp-0x6b70`) is a GOOD instrument**: nonzero **98.29 %**, 250 codes, **0.000 % saturation**,
  p99 3,059 of a ±8192 clamp. Not a V64/V68-class dead probe.
- **The observer's plausibility latch has NEVER fired**: `427 == 1023` duty **0 on 87,423 frames** across
  80/7e/7f — and `>640` (the true reachable ceiling through the clamp) is also **0**.
- **`b3` constant ⇒ `gp-0x674e < 28` settles RULE 7 for the authority curve** — the `Y[last]=0` records
  are live; modes 28–39 excluded. That rung is now **SPENT** and can be reallocated.
- ⚠ **`0xC62EA` = 0 on V97 (stock 320 ≈ 5 km/h)** — the low-speed lockout has been disabled since ~V35,
  so creep sits in a regime stock Honda would have locked out. Context for anything felt at 5 km/h.

## ⚠ SUPERSEDED 2026-08-12 (latest) — the block below described V96 as on the car and V97 as unflashed
## ★★★★★ HEADLINE, 2026-08-12 LATE (SUPERSEDED) — V96 FLEW, THE CRUX IS THE RETURN TRAJECTORY, AND V97 MOVES A LOOP POLE

Narrative: **`docs/HANDOFF-2026-08-12-v97-the-loop-pole.md`.** Agent outputs: `analysis-2020accord/_v97/`.

### A8. V97 — ONE BYTE. `0xC63AC` 102 → 150. THE ARC'S FIRST LOOP-POLE LEVER
```
39990-TVA,A160-V97-V96BASE-C63AC.102to150-0x13000-0x100000.rwd
  .rwd  78c674a899971a6a9763c2d7c89bf4c9169f35dfba3fbe4ce62d9bc445a17372
  image 7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3
  builder analysis-2020accord/build_v97_tva.py   131/131 assertions   BASE = V96 (on the car)
```
**The whole delta is ONE BYTE** (102 = `0x0066`, 150 = `0x0096`; the high byte is `0x00` in both) plus
its own CRC trailer at `0xC6FFC`. `gp-0x374c += ((target − gp-0x374c) × A) >> 10`, `@0x38202`,
**1 reader / 0 writers established FIVE ways.** 🛑 **DC gain is 1.000000 at any A — it is a POLE, not
a GAIN.** That is why it escapes the sign problem that disqualified all six lane weights.

**THE DIRECTION IS MEASURED, NOT MODELLED — two independent instruments agreeing to <7°:**
- `Q = −d(gp-0x6b70)/d(T)`, hands-off engaged returns, episode-bootstrapped
  (`rlog-tools/v97_measure_Q.py`): **|Q| = 1.233 on BOTH routes**, arg Q −133.7°/−131.5°, coherence
  **0.974/0.978**. The criterion is *inversion iff |Q| < 1 and cos(arg Q) < −|Q|* ⇒ **|Q| > 1 excludes
  inversion at ANY phase**, so the ±28° CAN-join uncertainty is moot.
- The V96 cave's own sign bits: `arg(V) − arg(B′) = −178.1°` on both routes (orchestrator reproduced
  the separation independently at +179.8°/+178.6°). `arg(V)` sits just below −90° ⇒ **cos < 0 =
  ANTI-DAMPING**, the corpus `Re(Z) < 0` seen on a firmware-internal signal for the first time.
  Adding lead rotates it **toward** the damping axis. Better on both routes at every k.

🛑 **COST, and it lands on a symptom he calls FIXED:** +2 %…+13 % at 21 Hz on the total command
(Path-1 dilution — a MODEL, not a measurement). V62 bought grinding by taking 18–22 Hz down 8–42×;
V88's Lever B is on the car. Worst case 1.13 × 0.549 = 0.620, inside V88's CI. **Exchange rate is FLAT
at 0.33°/% — no sweet spot. A = 150 was the OPERATOR'S choice with the trade stated.** RULE 9.

🛑 **V97 IS NOT A RETURN-SPEED FIX.** Clause 2 has **no mechanism** — see §A9. Do not score it as one.

🛑🛑 **THE DIRECTION WAS INVERTED ONCE AND CAUGHT.** `scipy.signal.csd(x,y)` returns `arg(Y)−arg(X)`;
an agent labelled every cross-spectrum backwards and recommended **lowering** this cell. The tell was a
**replicated ~90°** disagreement with the independent `Q` measurement — a bug signature, not physics.
⇒ **The build exists because two instruments were run and allowed to disagree.** Add `csd`'s convention
to the trap list.

### A9. WHAT DIED THIS SESSION — seven levers, each before a build was cut
| lever | how it died |
|---|---|
| **pre-declared V97** (`gp-0x6b4c`/`gp-0x6b4e`) | `gp-0x6b4e` **provably ≡ 0**; §A5's "gates open ⇒ V64 excluded" priced gate WIDTH when the failure mode is the signal never being non-zero. The array is `gp-0x62c8[]`, not `gp-0x62f8[]`, and they are **two different arrays 0x18 apart**, not one split by mode |
| return-to-centre lane | 🛑 **it is a RACK END-STOP CUSHION**, not a centring lane — arms on `\|gp-0x6b98\|>4096` AND motor rate `<200` (a STALL detector), splits by sign into left/right stop enums, **no angle term anywhere**. Gate needs `\|gp-0x6bf0\| > 8878`. **~99.3 % dead in MANUAL too** ⇒ its absence cannot explain the engaged/manual difference |
| `0xC520C` governor ceiling | `gp-0x6ac0` scale reconstructed = **4.7121 ct per column °/s** ⇒ first knot **222.8 °/s**. Measured returns max **528 ct vs a 1050 knot — 0.00 %** reach it |
| `0xC6194` LKAS slew limiter | **REAL and calibrated** (3 ct/tick = 1.37 s full scale) but its input partition `0xC4118` is **all-1** ⇒ 100 % bypasses it. 🛑 The record's "output ×0" reason is WRONG — that is `0xC6196` |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]**, CI excludes the predicted +1 — **and** `gp-0x6b4c` is a second LKAS route that never sees AUTH (lane mode 0 at `0xC4124`, `REQ_B` written at runtime `@0x26496`). ⊕ `0xC6CD0`, our own 4× gain, sits on that lane. ⚠ **The table header is `0xC67BE`; `0xC67C8` is its `Y[0]`** |
| PID Ki `0xC6B12` | **INERT** — at 6–10 km/h the P term alone (16,000 at e=2000) exceeds the anti-windup bound (7,264) ⇒ the integrator is pinned |
| `0xC63A6` / `0xC63A4` | `0xC63A6` is **a cliff edge, not a lever** (V91/V92 ×1.5 null + V94 ×0.25 catastrophe fit closed-loop invariance, not a dose-response). `0xC63A4`'s lane carries **~1.1 ct of a 342 ct signal** |

### A10. TWO BLOCKERS CLOSED, AND ONE `STATE.md` CLAIM RETRACTED
🛑 **§A6b's "the transfer cannot be read from the image" is FALSE.** The LERP is **100 % flash-derived**:
`FUN_000382d8` @`0x382d8` (sole writer) interpolates a 2-D flash table on speed selected by the mode
byte, `FUN_000389ec` rescales into `gp-0x64b8[]`/`gp-0x641c[]`, which is what `FUN_00038148` reads.
⇒ **`f′ ≥ 0` is ENFORCED IN CODE** at three ungated sites (`0x388c4` eight `max(Y[i],Y[i-1])` rungs;
the float-path monotone guard; `0x38de2`/`0x38e48`) ⇒ **holds for any cal, any mode, any build.**
Flash data agrees **14/14 records strictly increasing** (orchestrator-verified).
⊕ **"The 8 float coefficients of `FUN_0003b8f6`" never existed** — 3 floats (two hard ZERO ⇒ the 3-tap
FIR is an **identity**, unity gain, 0.000°) + 6 halfword Q-format cals. The handover also omitted
`0xC4048`, the only nonzero tap.
⊕ **`0xC64DE` identified**: a **BYTE** 17→27, not a halfword 25617→25627 — the half-period of a
relaxation oscillator (`gp-0x6b2c` sign-flips every N ticks, counter re-arms at `(N>>1)+1`).
⚠ 8 of its 16 read sites are in a region Ghidra never analysed ⇒ "dead" is a **tool zero**.

### A11. 🛑 FOUR TOOL-ZEROS IN ONE SESSION — ONE IS A NEW CLASS
1. `get_xrefs_to` tp-relative blind spot (known). 2. `search_instructions` undercounting (known).
3. `movea` + **register-indirect** — `operand_pattern="-0x6350\[gp\]"` returned **0 / 183,570 /
   `truncated:false`** on an array with nine real accesses.
4. ⭐ **NEW — `ep`-relative short-format aliasing.** An array is based once via `movea <off>,gp,ep`,
   then every access is `sld`/`sst` off `ep` with **no offset in the operand text**. `-0x62f8` →
   **15 hits, 14 of them base setups, ZERO actual loads/stores.** 🛑 **Worse than a zero: a healthy
   non-zero count that misses 100 % of accesses.** Recipe in `_v97/fw_return.md` §8h.
   ⊕ Also: a *filtered* zero is not a fact — `operand_pattern="0x0[ep]"` returns 0 because Ghidra
   renders operands as `r6, 0x0, ep` (commas, no brackets).
🛑 **`0xC63AC`'s census was re-tested against trap 4 and is CLEAN** — 98 `movea imm,tp,ep` sites
image-wide, **0** within the 254-byte `sld` reach; a gp-based `ep` cannot reach the cal block at all.

---

## ⊕ SUPERSEDED HEADLINE, 2026-08-12 — V94 REGRESSED THE CAR, AND IN DOING SO MEASURED THE LEVER'S SIGN FOR THE FIRST TIME

**Superseded by §A8–A11.** 🛑 **V94 is NO LONGER ON THE CAR** — V96 flew as routes `7e`/`7f`.

Narrative: **`docs/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md`.**

### A1. 🛑🛑 V94 IS A DAMPER REMOVAL, NOT AN INERTIA REDUCTION [EVIDENCE]

V94 cut `0xCBE74` — mode 24 ×0.50, modes 26/27 ×0.25, fallbacks ×0.75 — **a 6× cut against V92** on
the premise that `gp-0x6b26 = −K·α` is *apparent inertia, nothing is dissipated*, so *"lowering is
strictly safe on both binding bounds"* (`build_v94_tva.py:106`).

**Measured on-car after the fact, on TWO independent drives, ω-partialled against a shuffled control:
the DELIVERED lane sits at `+137°` / `+139°` versus WHEEL rate at 6–9 Hz ⇒ |cos| = 0.73 ⇒
`+518` / `+565` counts of POSITIVE `Re(Z)`.** It is a **real 6–9 Hz damper**, and V94 removed 6/6ths
of it. The car got much worse in exactly the band the damper covers.

| symptom instrument on route `7d` | result |
|---|---|
| motor acceleration > 9 Hz | **3–7× up** vs corpus |
| column-torque ↔ wheel-rate coherence, 18–31 Hz | **highest of any drive in the corpus** |
| faults / DTCs / sentinels | **none** |

⊕ **The code byte is EXONERATED.** `0x55E10` `sar 3`→`sar 1` is the CAN-427 packer shift;
instruction-level walk shows `r6` is consumed only by the `jarl` two instructions later, and
openpilot's `steeringTorqueEps` dead-ends in `carstate.py`. It changes what we *see*, not what the car
*does*. **The regression is the CALIBRATION.**

⊕ 🛑 **The desk correction was ALSO wrong.** *"+75°, 26 % dissipative, structurally cannot damp
6–9 Hz"* (`analysis-2020accord/v94_damping_fraction.py`, now header-marked SUPERSEDED) was the
**producer's filter phase vs MOTOR rate**; the measurement above is the **delivered lane vs WHEEL
rate, with the plant in between**. Two successive phase stories about one lane, both decision-bearing,
both wrong, four days apart. ⇒ the rule is **measure the delivered lane**, not *do the arithmetic*.

⇒ `memory/accord-v94-flew-and-the-lane-is-a-damper.md` ·
`memory/accord-gp6b26-is-a-real-6to9hz-damper.md` ·
`memory/feedback-reducing-a-gain-is-not-a-safety-class.md` (the five-failure process RCA, incl. a
**133/133-green assertion suite that encoded the wrong premise as a PASS condition**).

### A2. 🛑🛑 THE SYMPTOM REGIME IS **ENGAGED + HANDS-ON + OVERRIDE** — AND EVERY `Re(Z)` NUMBER EVER PRODUCED EXCLUDED IT

Operator, 2026-08-12: ***"Steering override is how I get the steering into such a scenario where
grinding and micro ratcheting can be observed."***

The kit's hands-off mask is `steeringPressed` = `|STEER_TORQUE_SENSOR| > 1200` — a threshold on the
**numerator of `Re(Z)`**, and **override is `steeringPressed == True` by definition**. The instrument
was pointed away from the symptom, and the exposure followed: **7121.6 s engaged hands-off against
994.9 s engaged hands-on.**

**Scored in the right regime, on band power, with grip matched out on BOTH arms** (override vs
manual-hands-on), 6–9 Hz column-torque envelope:

```
OVR / MAN-ON  =  1.43  1.65  1.74  1.93  2.22  2.25  2.35  2.38  2.55  2.90
                 10 of 10 routes, 9 builds, every one above 1.4   median ~2.2x
```

🛑 **The operator's report — *"literally every bad symptom is LKAS engaged only"* — is CONFIRMED by the
amplitude instrument in his own regime**, and agrees with the standing 2.8× engagement contrast.
An orchestrator claim that *"~80 % of what you feel isn't gated on LKAS"* was **retracted**; roughly
**55 %** of the 6–9 Hz energy he feels is engagement-attributable. **An LKAS-gated lever is fully back
on the table** — the class V62 and V88 came from.

⊕ **`Re(Z)` and band power never disagreed.** `Re(Z)` is **LATENT** (energy that *would* grow if
excited; hands-off there is almost no excitation — manual 6–9 Hz coherence 0.040 against a 1/n ≈ 0.014
bias floor). **Band power is the FELT quantity.** 1.24× latent and 2.2× felt are different
measurements and both are correct.

🛑 **Override does not support the kit's 5.12 s band estimator.** 5013 contiguous override runs make up
the 994.9 s: median run **0.02 s**, p90 **0.55 s**, and **only SEVEN runs corpus-wide reach 5.12 s**.
Use point-process / event-triggered methods or 1.28 s windows, **and say which.**

⇒ `memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`

### A3. ☠ TWO NAMED MECHANISMS DIED IN THAT REGIME — AND ONE NEW ONE APPEARED

**Mechanism A — "the LKAS authority collapse curve is the 6–9 Hz exciter": DEAD, five ways**, with
**perfect exposure** (median override torque **2235** against a **2240** knot; 33–70 % of override time
above 2560 with authority at exactly zero):
1. knot crossing rate **0.47–1.69 Hz**;
2. reconstructed authority spectrum **88.4–94.9 % in 0.5–3 Hz**, peak **0.79 Hz**, every route;
3. sweeping the unit scale 0.6×–2.0× **never exceeds 1.22 Hz**;
4. 🛑 the chatter↔energy correlation **INVERTS against its own negative control** — OVR
   **−0.194 / −0.255** vs MAN-ON **+0.400 / +0.495** ⇒ it tracks **how hard the driver is working**;
5. **not an exciter either** — 6–9 Hz energy *falls* after a collapse edge, below the shuffled baseline.

**Mechanism B — "a sign-guard relay chatters when the driver opposes": DEAD.** Request-bit duty
**1.0000**, drops/s **0.000**, every route ⇒ the gate never opens. And **openpilot does not back off
when overridden — it winds UP 6.7–15×**, so the premise is false. Direction reversals **0.23–2.66 Hz**
and *lower* during override.

★★★★ **THE NEW ONE — a real surge, at ~0.5–1 Hz.** The EPS holds LKAS authority at **exactly zero for
17.5–40.5 % of override time**, cycling **~0.5–1.7 Hz**, *while* openpilot winds up **6.7–15×**. Ease
back below the knot and authority returns with a command an order of magnitude larger.
🛑 **It is ~0.5–1 Hz, NOT 6–9 — it is not the grinding and not the micro-ratchet.** It would be felt as
a **slow lurch or a "catch"**. **The operator has NOT yet said whether he feels it. Until he does it is
a measured behaviour with no scored symptom attached** and must not be reported as a cause of anything
he has complained about.

⇒ `memory/accord-override-surge-and-two-dead-mechanisms.md`

### A4. INSTRUMENT RESULTS OF RECORD FROM THIS SESSION

- **`Re(Z)` anchored on-car for the FIRST time, parameter-free**: `mean(T·ω)` pooled **+3859**,
  **P(>0) = 0.9238**, n = 20,159, 8 routes / 8 builds. It independently ranks **V80 worst** at
  12–16 / 18–22 Hz (−8883 / −3581) — the build the operator called *"worst grinding ever."* Detection
  floor **~60 ct at ≥12 episodes; use 150.** 🛑 **Never quote `Re(Z)` below 6 Hz from a
  `steeringPressed` mask — 2–4 Hz reverses sign.** ⇒ `memory/reference-accord-rez-anchored-on-car-and-its-floor.md`
- **CAN 427 is RECTIFIED** ⇒ aliasing runs on `2f` and the fold law is `|2f − 50·round(2f/50)|`,
  **not** `f mod 25`. 26/29/31 Hz fold to **2/8/12 Hz**. The band a 427 magnitude probe exposes is
  **2–12 Hz, not 19–24.** ⇒ `memory/reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz.md`
- **`gp-0x6bbe` is RATE-derived, NOT the base-assist output** — contradicting the previous headline.
  Dead as a lever: 9–15 % of `Re(Z)`, rate part 4–9 % of a 73–80 ct DC pedestal.
  ⇒ `memory/reference-accord-gp6bbe-is-rate-derived-not-base-assist.md`
- **Four more 6–9 Hz stories killed by their own controls**, including **Lever B `0xC6446` CLEARED**
  (⇒ V88's grinding fix need not be traded away) and **0 of 41 varying cells** separating 6–9 Hz.
  ⇒ `memory/reference-accord-controls-killed-four-6to9hz-stories.md`
- 🛑 **RETRACTED: task 5 = 100 Hz.** The derivation rested on an address coincidence.
  **Task 5's rate is OPEN.** Task 1 (`FUN_0002214a`) = 1 kHz still survives on two independent methods.
  ⇒ `memory/accord-task5-is-100hz-damper-cannot-damp-21hz.md` now carries a **DISPUTED — DO NOT SIZE A
  BUILD ON THIS FILE** banner.
- **`FUN_0002a93a` is DEAD CODE** (zero callers) and two engagement-gate candidates were struck.
  ⇒ `memory/reference-accord-two-engagement-gate-candidates-struck.md`

### A5. WHAT IS BUILT — AND THE REVERT CANDIDATE

| build | status | image / rwd |
|---|---|---|
| **V97** | ☠ **SUPERSEDED — FLEW as route `0x80`, then superseded by V98.** Its `0xC63AC` = 150 is carried on V98 and is now believed **WRONG-DIRECTION** (it broke Honda's exact 51/512 pole match) | image `7ac009044b46eeb2…` rwd `78c674a899971a6a…` |
| **V96** | ☠ **SUPERSEDED — no longer on the car.** Flew as routes `7e`/`7f`, 2026-08-12, both fault-free | image `876cf2be5800f0f8…` rwd `7e9a65f11cab4ffc…` |
| **V94** | ☠ flown as `7d` and **ABORTED**; **superseded — no longer on the car** | image `cd971c05d483fe9c…` rwd `3feccc09d8cbdd05…` |
| **V93** | built, verified, **never flashed**; carries V94's cal without the packer rescale | image `779180f8aaf88f29…` rwd `9c93dca63e9e404e…` |
| **V92** | flown as route `79`; its calibration is carried byte-for-byte by V96 ⇒ **no revert is pending** | rwd SHA256 `388a1974d5702e17…` |
| ~~V95~~ | 🛑🛑 **VACATED — A BURNED NUMBER. NEVER REUSE IT.** | see the DEAD hashes below |

🛑 **V96's SEPARATION FROM V92 IS NOW EVIDENCE, NOT BELIEF.** §A6 logged at cut time that the separator
was V92's measured b6 duty rather than an impossibility. **The flight discharges it:** V92's byte7 b6
is the dwell-snap rung, measured **0.0000 engaged AND manual over 87,317 frames** (3 runs, longest
855 s); V96's byte7 b6 is a **hard-wired constant 1**, and a **164,096-frame unbroken rail** is a
reading V92's rung has never produced one frame of.

🛑 **V96's INSTRUMENT FAILED AND MUST BE RE-SIZED BEFORE ANY RE-FLY.** `gp-0x374c`'s magnitude code M
is **pinned at 0** on 99.90 % / 99.97 % of frames and **100 %** of route 7f's engaged elicitation time
⇒ `|gp-0x374c>>4| < 2048` throughout, against a field sized for ~68,600 — a **34× over-range**.
**S1 AND S2 ARE BOTH VOID; `f′` is NOT RESOLVED by this flight** (though it was later closed
analytically — §A10). Next regressor LSB should be **128–256**, not 2048.

**Revert candidate, full name:**
`39990-TVA,A160-V92-V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4-0x13000-0x100000.rwd`
🛑 **Not flashed. Flashing is gated on the operator naming the file and the bus.** V92 flew as route
`79` in the earlier lineage with identity **proven single-frame**; it is the last configuration the
operator drove and did not abort.

### A6. V96 — THE BUILD THAT WAS CUT (and why V95 is a burned number)

**Class: an INSTRUMENT build, not a fix.** Base **V92**, with V94's cal cut reverted **by construction**.
```
image  876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3
.rwd   7e9a65f11cab4ffc6286f0365ce5196c11dc461468b9ec85022775e35ebdf093
39990-TVA,A160-V96-V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6-0x13000-0x100000.rwd
builder: analysis-2020accord/build_v96_tva.py   166/166 assertions, reproduces bit-for-bit
```
**107 bytes differ from V92 in 7 runs. ZERO are calibration** — no diff anywhere in `[0xC6000,0xC7000)`
or `[0xD6000,0xD8000)`; all four authority-curve records byte-identical to stock. **112-byte cave
payload inside V92's proven 116-byte footprint — no growth**, same hook, same `jarl`, 4 bytes back to
virgin.

**What it measures, and why this and nothing else.** The blocker on every remaining lever is that
`gp-0x6b70` is a **PID reference that gets subtracted**, so no `FUN_00038148` weight can be moved
without knowing the LERP's local slope (§A6b). V96 puts the **pair** on the wire:
- **CAN 427** ← `gp-0x6b70`, `sar 6`, magnitude + explicit sign bit. **LSB 12.8 counts**, no-clip
  (`8192×5>>6 = 640 ≤ 1023`), 6–9 Hz floor ≈ 3.6 ct.
- **`0x14A` byte4/byte7** ← `gp-0x374c >> 4` — **the firmware's own shift** (`@0x38236`, the
  instruction that forms this very term of `iVar6`) — **saturating at 12288, LSB 2048**, deliberately
  below the 68,614 structural bound because **no build has ever put either cell on the wire**. The
  saturation duty and the 8-code histogram are **first-class reported outputs** so the next build sizes
  off data instead of guessing. ⊕ `b3` = `gp-0x674e < 28`, settling RULE 7 for the authority curve.
- **Identity:** `byte7 b6 ≡ 1` ⇒ **any single frame with `0x14A` byte7[7:6] ≠ 0 proves V96.** V94, the
  build on the car, carries the 74-byte V90 cave and *cannot* write byte 7. ⚠ Separation from **V92**
  is **BELIEF, not EVIDENCE** — V92 also writes byte 7, and the separator is its b6 measuring duty
  0.0000 over 75,227 engaged frames, which is a measured duty, not an impossibility.

**Pre-registered scoring — TWO SLOPES, never merged:**
- **S1** — lag-0/lag-1 slope of `gp-0x6b70` on `gp-0x374c>>4` ⇒ the **OPEN-LOOP `f'`**. **Its SIGN
  decides whether any Path-2 weight lever helps or inverts.** Valid because
  `d(gp-0x6b70)/d(gp-0x374c>>4) = −f'` **independently of `sign(iVar6)`, `gp-0x6bfe` and `gp-0x6bfa`**
  — the two sign factors square to +1 and cancel.
- **S2** — coherence-weighted longer-window slope ⇒ the **CLOSED-LOOP** transfer, folding in `L`.
- ⚠ Errors-in-variables attenuates both magnitudes and **preserves both signs** ⇒ magnitudes are
  **lower bounds**. 🛑 **If S1's CI spans zero the answer is "`f'` is NOT RESOLVED by this flight" —
  NOT "`f'` is zero" — and the weight class stays blocked.**
- Secondary: hands-on 6–9 Hz band power in **override**, event-triggered **1.28 s onset windows**,
  episode bootstrap, POS-1/2/3 · NEG-1/2 · shuffled-pairs, 2× placebo floor.

🛑 **FREEZE EXCLUSION (heuristic, and labelled as one):** `FUN_00038148` sits behind a `gp-0x67fa`
state gate; when it shuts, **both** members of the pair freeze and would enter the regression as
spurious zero-slope samples. The exact gate is **not readable by a cave** — its boolean is **never
stored** (`r28` written once `@0x221D6`, tested `@0x22672`, no store in `[0x2214A,0x22700)` sources it),
recomputing needs a **Format IX `shl reg,reg,reg`** (the hand-encoding class that bricked V24/V27/V48B),
and the affordable `4 ≤ s ≤ 11` approximation is a **superset that would silently read "live" while the
pair is held — worse than no bit, because it would be trusted.** ⇒ the wire-side fallback: drop runs of
≥5 consecutive frames where the 427 code **and** the byte4 field are both bit-exactly unchanged, and
**report the dropped fraction.**

### 🛑🛑 V95 IS A VACATED NUMBER — NEVER REUSE IT
Three artefacts wore it inside two hours as the spec moved. **Retiring the number is cheaper than
disambiguating it forever.** DEAD hashes, written out so a grep finds them:
```
DEAD  lane build (6B4C/6B4E)   image ad8643c1f37ac128c57606c60ad6225420884f3fa250ffd978f9efa6a5fb7faf
DEAD  lane build (6B4C/6B4E)   .rwd  3a791446c268b2b0660e4035a82c51f93572b662faa6225167f16e331277c9d6
DEAD  pair build numbered V95  image 876cf2be…  .rwd 7e9a65f1…   <- SAME BYTES, now correctly V96
```
`analysis-2020accord/build_v95_tva.py` was **deleted** — it would rebuild a vacated number.
⊕ **The lane design is not lost.** `gp-0x6b4c`/`gp-0x6b4e` are the **disjoint partition sums of the
same 11-slot request array** `gp-0x62f8[]` (split by the mode bytes at `0xC4124`), `±10240` each — 5×
and 10× the other two lanes — and `gp-0x6b4c` is **also a direct unity-weight aggregator summand**
(`0x3AA3E`) so it reaches the motor by both paths. Both gates are **structurally always open**, so the
V64-class null is excluded *by arithmetic*. **That is V97, cut fresh from whatever base is current.**

### A6b. ⭐ TWO NEW LEADS THE CELL LEDGER TURNED UP — both sit in the override regime

Both came out of reading all **85** build images against stock (`analysis-2020accord/ledger_v94_cells.py`,
`diff` · `matrix` · `grid` · `mask`; `LEDGER_TARGET=V92` to retarget). **Net V94-vs-stock delta: 245
bytes in 114 runs, zero unattributed**, reconciled two ways (215 + 30 = 245, 107 + 7 = 114).

**LEAD 1 — `0xC63A6`. ☠ TRACED AND STRUCK THE SAME DAY. NO-GO — but for a reason that matters more
than the cell does.**
`0xC63A6` is `w[3]` in `FUN_00038148`, **stock 1024 (Q10 = ×1.000)**, on the **`gp-0x6b26`** lane, and
**VIRGIN across all 85 images**. `0xC63A2`/`A4`/`A8`/`AA` are virgin too; only `0xC63A0` has history
(2048 at V72–V75, V76g, V81 — **inert**, frozen at 1024 for 13 builds since V83a). It looked like a
second, independent multiplier on the one signal whose direction is now measured, with `0xCBE74`
exhausted at ×1.5 (≈94 % of its range before int32 wraparound at 1.6005×).

- **Q1 CLOSED [EVIDENCE, three methods].** It weights **only** `gp-0x6b26`, through exactly **one**
  instruction — `ld.hu 0x73a6,tp,r15 @ 0x381ca` in `FUN_00038148`. **Zero writers.** Path 1
  (`FUN_0003aa2c`) never reads it. ⚠ `get_xrefs_to` returned *"No references found"* — **the Ghidra
  tp-relative xref blind spot, not a real zero**; caught and overridden by `search_instructions` plus
  a raw Python LE scan (disp16, LE32 absolute, movea lower-half). Two false positives
  (`be 0x000473a6`, a `jarl` displacement coincidence at `0x652aa`) were each disassembled and excluded.
- 🛑 **Q2 KILLED IT, and NOT on magnitude.** Path 2 is **not** negligible. The problem is that
  **`gp-0x6b70` is not an aggregator addend — it is a PID REFERENCE** (`error = measured torque −
  reference`), so the **sign** of Path 2's contribution depends on the sign of `iVar6` and on the
  **local slope of a RAM-resident LERP** at the operating point. **Neither is known.**

```
sum6 ──(*polarity*2639)>>10, *16──> target                  # 0xC6468 = 2639
gp-0x374c += ((target - gp-0x374c) * 102) >> 10             # 0xC63AC = 102, IIR pole
iVar6 = gp-0x6bfe + gated(gp-0x6bfa, ±20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 1024 >> 10)    # <-- THE UNKNOWN SLOPE
            clamped ±8192                                    # 0xC6200 = 8192
        --> gp-0x6ad6 --> PID reference --> aggregator
```
Path 2's IIR alone is **|H| = 0.94/0.91/0.88 and −18.7°/−23.6°/−26.8°** at 6/7.79/9 Hz; stacked on the
PID's own −11° to −27° at that band, **Path 2 runs ≈ −30° to −54° of lag against Path 1's 0°, unity,
unconditional.**

🛑 **A lever whose SIGN is unresolved is not a lever. That is exactly how V94 reached the car.**
⚠ **One contradiction is still open and is being adjudicated:** the claimed inversion boundary at
`0xC63A0` 1024→2048 (0.59/0.56 "damping" → 1.18/1.12 "INVERTED") should have produced a large
qualitative change on-car, and **`0xC63A0` = 2048 flew four times (V72, V73, V76g, V81) and measured
INERT.** Either the model is wrong, or "inert" was measured hands-off in the wrong regime, or Path 2 is
small at the flown operating point (which would contradict Q2). **Unreconciled.**

**LEAD 2 — `0xC64B8`. ☠ VERIFIED AND DEAD. But it handed back the best lever in the kit.**

The claim was structurally true and behaviourally empty. `0xC64B8` really does gate a branch that
**hard-kills the LKAS authority weight to 0**, the comparison really is `cal < torque_byte`, and with
V37's `0xFF` against a byte that saturates at 255 the kill path is **unreachable**. ⊕ The compared
signal really **is a torque, not a counter** — the "fail-counter" label describes only one of three
live readers; `gp-0x682f = min(|gp-0x4f60| >> 5, 254)`, so the gate would fire at **|raw| ≥ 3616**.

🛑 **But at mode 7 BOTH ARMS DELIVER 0 everywhere the branch could fire** — all four curve records
clamp to `Y[last] = 0` above `X[last]` = 80 or 112, below the gate's 113. **Stock and V37 are
bit-identical on this car. V37 removed nothing.** ⇒ **do not re-propose it.**
⊕ Blast radius closed: **6 readers, 0 writers**, two methods, set difference **empty** — 3 live (all
`FUN_00028ea6`), 3 in dead functions. 🛑 **New parity trap:** `0x4549E`/`0x4556E` have hw2 = `0x74B9`
but opcode field `0x3D` (disp bit0 = 1) ⇒ they address **`0xC64B9`, the neighbour**. A scan keying on
hw2 alone **over-reports by two.**

### ⭐⭐ LEAD 3 — THE AUTHORITY COLLAPSE CURVE. VIRGIN ON ALL 90 IMAGES, AND HE DRIVES ON ITS KNEE

Mode-7 records: `0xE547C` / `0xE5404` (primary, X = 70/72/78/80 → Y = 254/234/12/**0**) and
`0xE52FC` / `0xE5284` (blend, X = 32/42/80/112 → Y = 255/255/255/**0**).
**Authority goes 254 → 0 between raw 2240 and 2560 — a 320-count window, nearly a step.**
🛑🛑 **All four are VIRGIN across all 90 `_v*` images. No build has ever touched them.**

| quantity | raw | torque byte |
|---|---|---|
| curve first knot `X[0]` | 2240 | 70 |
| **measured median override torque** | **2235** | **69** |
| fully collapsed `X[3]` | 2560 | 80 |
| `0xC64B8` gate (dead) | 3616 | 113 |

**One count below the first knot.** A few counts either side is the difference between full authority
and none — and it is the mechanism behind the measured **~0.5–1 Hz surge** (§A3).

🛑 **IT IS NOT A 6–9 Hz LEVER**, and the curve was already refuted as one **five ways** this session.
**Softening it targets the SURGE, not the grinding or the micro-ratchet.** Do not conflate them, and
do not propose it until the operator says whether he feels the surge.

🛑🛑 **THE SAFETY DIRECTION IS NOT SYMMETRIC.** Honda collapses authority when the driver pushes hard —
that is **driver-override behaviour**. Widening the window makes the car **fight the driver harder and
for longer**. ⇒ **the only defensible shape change is MONOTONE-NON-INCREASING** — authority never
higher than stock at any torque; start the decay *earlier* and make it gradual, reaching 0 at the same
place. **Anything that raises `Y` at any `X` is a different and far more serious proposal.** GATE 2 is
entirely untouched, and the curve gates the whole LKAS delivery path.

⚠ **One gap, and V96 closes it with one rung** (`b3` = `gp-0x674e < 28`). `gp-0x674e` = 7 comes from code + the config table +
V73's on-car variant row — **never a direct on-car read of the byte.** It matters: **modes 28–39 have
`Y[last] = 51`, not 0**, and there the `0xC64B8` branch would *not* be redundant.
⊕ Table trap: the ASCII key sits at block `+0x24`, so it renders as the **next** row's label — row 11
is `18 19 1a 1b` (24/25/26/27 ✓ TVCA4) while the string in the same window reads "TVCA6". **A naive
`+0x12` dump is off by one row.**

⇒ `memory/accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee.md`

⊕ Also flagged, not implicated: **`0xC64DE` = 25627 since V22 — non-stock for 85 builds, its label
disputed since 2026-07-18, and never once isolated.** The longest-carried unmeasured cell in the image.

### A7. 🛑 STILL OPEN

1. **Task 5's true rate** — the 100 Hz claim is retracted; nothing replaces it.
2. **`gp-0x6733` identity** — it drives `gp-0x67e2`, which picks the mode-table column A/B.
   Both **26 AND 27** are engaged columns.
3. **The `gp-0x67fa == 4` record inconsistency.**
4. **`FUN_0003897a` / `gp-0x6350` / the LERP `X[0]`.**
5. **The ~0.5–1 Hz surge** — measured, unattributed to any complaint. **Question outstanding to the
   operator** (§A3).
6. **The left/right ramp-rate asymmetry** — `0xC63F8` = 33 vs `0xC63FC` = 328, a **10×** difference.
   **Question outstanding to the operator: does the car feel different turning left versus right?**

---

## ⊕ SUPERSEDED HEADLINE, 2026-08-11 — ROUTES 78/79 SCORED; "THE DOSE DID NOTHING AND THE LEVER IS THE WRONG PHYSICS"

**Superseded by §A1.** Narrative: `docs/HANDOFF-2026-08-11-routes-78-79-and-the-inertia-reversal.md`.
The V90-flight-session block that sat here went verbatim to
`docs/STATE-ARCHIVE-2026-08-11-v90-flight-session.md`.

**What it got RIGHT and is still live:**
- Both drives **fault-free**. Route 78 = 927 s / 67.0 % engaged / **160 s ≥ 80 km/h**; route 79 =
  875 s / 86.2 % engaged.
- **The ×1.5 dose measured 0.99 [0.91, 1.26]** engaged (manual control 1.009), against a pre-registered
  1.50 — **and the explanation is now known**: `gp-0x6b26 = K·α` where α is *what K damps*, so in a
  stable closed loop **the product is invariant to K. The instrument was structurally incapable of
  measuring its own dose.** ⇒ measure the **input** (`gp-0x6c2c`) or a symptom, never the product.
- **`Re(Z) < 0` replicated on three drives** — 6–9 Hz −3375 / −3176 / −3073, sign flip to damped at
  ~24–26 Hz on all three; strongest in the **micro 1–13 °/s** regime (−3480, coh² 0.804).
- **Return-centre + detent are DEAD ENGAGED** — `gp-0x6b62 ≠ 0` and the `gp-0x6bda` gate both **0.0000
  over 75,227 engaged frames**, with an **855 s sustained (0,0) run**. **Do not propose a detent lever.**
- **Routes 77/78/79 are the same functional car** ⇒ the kit's largest **placebo floor**: 6–9 Hz
  **1.37×**, 18–22 **1.31×**, 26–31 **1.99×**, 32–38 control **1.54×**. **No claim below 2× is
  supportable in either direction.**

**What it got WRONG:**
- 🛑 *"`gp-0x6b26 = −K·α` ADDS APPARENT INERTIA and dissipates nothing ⇒ LOWER it"* — **refuted by the
  V94 flight and by direct measurement of the delivered lane.** See §A1.
- 🛑 *"`gp-0x6bbe` = the base-assist output"* — **refuted**; it is rate-derived. See §A4.

---

## ★★★★ STANDING CORPUS RESULTS (from the 2026-08-09 V89 analysis session) — still the live evidence base

**Superseded as the headline by the 2026-08-11 block above; the findings below are NOT superseded.**
Narrative: `docs/HANDOFF-2026-08-09-v89-the-rate-axis.md`.

### 0. ★★★★★ THE NEW INPUT — the operator separated the symptoms, and the separator is STEERING RATE
> *"micro-ratcheting and ratcheting when LKAS is engaged and spinning the wheel **at all**
> (micro-ratcheting) and **quickly** (ratcheting), respectively. Macro-ratcheting is on **large
> steering angle transients**."*

Every ratchet measurement in this kit had been stratified by **vehicle speed**. The operator's axis
is **wheel rate**, and in this corpus the two are strongly anti-correlated (**corr(log rate, log
speed) = −0.640** engaged) — you spin the wheel in a car park, not at 116 km/h. ⇒ **D5's headline
"the ratchet decays 4.8× from creep to highway" is partly a RATE effect read as a SPEED effect**:
the creep stratum's median |rate| is **13 deg/s** against the highway stratum's **1 deg/s**.

### 1. ★★★★★ THE FULL CORPUS — 30 routes, 284 min, 235 episode blocks
🛑 **The 12-route version of this section was WRONG and is replaced.** The operator caught it: the
loader globbed only `_cache_r*/r<NN>.npz` and **skipped every PER-SEGMENT cache**, seeing ~180 min
of ~417 min on disk. `v89_c1_full_corpus.py` now loads 30 routes (10 Lever-B, 20 not) —
**235 episode blocks against the earlier 93.** Route→build is documented; ambiguity is harmless
because Lever B exists only from V67, so every pre-V67 route is unambiguously Lever-B = no.

`v89_c2_powered_discriminator.py`, band contrast = 6–9 Hz minus the 32–38 Hz control, same windows:

| term | 6–9 Hz | control | **band contrast** | verdict |
|---|---|---|---|---|
| **`eng`** | **+1.015 [+0.713, +1.302]** | +0.602 [+0.392, +0.810] | **+0.413 [+0.146, +0.667]** | **EXCLUDES 0** |
| `eng × log rate` | +0.133 [−0.005, +0.261] | +0.112 [+0.014, +0.195] | **+0.022 [−0.070, +0.116]** | **NULL — and it REFUTES the 12-route +0.144** |
| `eng × log rate × LeverB` | +0.124 | +0.049 | +0.075 [−0.099, +0.245] | inconclusive |
| `eng × DAMPER` | −0.091 | −0.105 | +0.014 [−0.483, +0.386] | NULL, refutes ±0.413 |
| **`log hands`** | **−0.655 [−0.750, −0.525]** | −0.266 [−0.323, −0.196] | **−0.389 [−0.471, −0.290]** | **EXCLUDES 0** |

⇒ ★★★★★ **[EVIDENCE] ENGAGING LKAS MULTIPLIES THE 6–9 Hz COLUMN MODE BY 2.8×, AND BY 1.5× MORE THAN
IT MULTIPLIES A CONTROL BAND.** A **constant, band-specific, engagement-gated amplification.**
⇒ 🛑🛑 **[EVIDENCE] IT DOES NOT GROW WITH WHEEL RATE.** The rate term is the same in both bands
(+0.133 vs +0.112). **The earlier "+0.144, the operator's axis is band-specific" claim is RETRACTED
— refuted by 2.4× the data.** What *does* grow with rate is the EXCITATION (`log rate` main effect,
present in every band): turn the wheel faster, feed the mode harder. Engagement then multiplies it
by a constant 2.8×. **Both compound, which is exactly why he feels more of it when spinning fast —
but the firmware term itself is NOT rate-dependent.**
⇒ ★★★★★ **THEREFORE: NOTHING HERE ARGUES FOR LIMITING THE LKAS COMMAND'S ANGLE RATE.** The target is
a constant gain, not a rate. **The operator's constraint and the measured target agree.**
⇒ ★★ **[EVIDENCE] The mode is strongly damped by FRICTION AT THE COLUMN** — `log hands` −0.655 vs
the control's −0.266, CIs disjoint. Confirmed independently in §1b.

### 1b. ★★★★★ THE MECHANISM, AND IT INVERTS A STANDING RECOMMENDATION — `0xC40BC`
On V87/V88 **stock modes 24 ≡ 26 are byte-identical in all six factor families**, so engaging
changes **no calibration at all**. The only change is the LKAS command entering the aggregator ⇒ a
constant 2.8× amplification must come from the command's ENTRY moving the loop through a
**nonlinearity**. There is exactly one on record: **`FUN_0003b8f6`, a Coulomb relay PROPORTIONAL TO
THE COMMAND**, whose `ratio` saturates against gate **`0xC40BC`** — pinned across 99.62 % of its
range at the stock gate, i.e. a pure relay. Raising the gate widens the linear region and
**de-relays** it.

```
0xC40BC =  600   stock, V87, V88  -- THE CAR RIGHT NOW
0xC40BC = 6000   V85, V86, V86B only (routes 6e, 6f, 70)
```
`v89_c3_friction_relay.py`, identified **within-route** (the flag is constant per route, so only the
engaged-vs-manual gap carries it — route fixed effects absorb everything else):

| `0xC40BC` | engaged/manual 6–9 Hz amplification |
|---|---|
| **600 — stock, and on the car** | **2.89× [2.14, 3.92]** |
| **6000 — V85/V86/V86B** | **6.58× [3.19, 13.14]** |

**`eng × FRIC6000` band contrast = +0.682 [+0.213, +1.166] — EXCLUDES 0, and it is POSITIVE.**

⇒ 🛑🛑 **DE-RELAYING THE COULOMB FRICTION TERM MADE THE RATCHET BAND 2.3× WORSE.**
⇒ 🛑🛑 **`STATE.md`'s standing "FREEZE `0xC40BC` at 6000" is CONTRADICTED on the 6–9 Hz band.** It was
set on relay-saturation duty and other bands. **The car is at 600 and that is the better value for
ratcheting. Do not restore 6000.**
⇒ ★★★★★ **TWO INDEPENDENT LINES NOW AGREE: COULOMB FRICTION AT THE COLUMN DAMPS THIS MODE** — the
driver's own grip (−0.655) and the firmware's own friction relay (600 beats 6000 by 2.3×).
**⇒ THE LEVER CLASS IS "MORE COLUMN FRICTION / DAMPING", NOT "LESS COMMAND".**

⚠ **Scope, honestly:** the flag lives on **3 routes**, all from one era, and **V86 also moved
`0xC40D4`** (573→286) while **V86B armed the damper**. The model carries damper and Lever-B
interactions and both come back inconclusive-to-null, but `0xC40BC` **cannot be fully separated from
V86's `0xC40D4`**. The *association* is EVIDENCE; **attributing it specifically to `0xC40BC` is
BELIEF.** ⚠ And the instrument measures **6–9 Hz band energy, not "feels smooth"** — more Coulomb
friction can reduce the oscillation while making the wheel feel notchier. **The operator scores that,
not the instrument.**

### 2. 🛑🛑 TWO OF THIS SESSION'S OWN READINGS RETRACTED BY THEIR OWN CONTROLS
1. **"The rate axis is band-specific to the ratchet"** — `v89_a1` found `e_6-9` slope **+0.490** and
   `e_18-22` **+0.039**, which looked decisive. **It was an ARTEFACT of order-vetoing each band on a
   DIFFERENT window set.** On matched windows (`v89_a2` T2) the slopes are **+0.492 / +0.385 /
   +0.400** and the contrast CI **includes 0**. **Spinning the wheel raises the WHOLE column
   spectrum**, so a rate slope alone can never separate firmware from driver. Only the
   engaged-vs-manual **interaction** in §1 does.
2. **The binned engaged/manual dose curve (2.09× → 21.17×, `v89_a4`)** — **inflated by two
   confounds its own controls caught.** K2: at 8–50 deg/s the MANUAL arm carries **~9× the sustained
   column load** (1724–1878 ct vs 193–201) — slower, heavier parking, and a hard-gripped wheel is
   damped by arm impedance. K4: only 5 routes contribute any cell and they contribute to **different
   bins**, so a build effect can masquerade as a rate trend. 🛑 **Quote §1's model numbers
   (1.16×→3.94×), never the 21×.**

### 3. 🛑 `cmd → column` COHERENCE IS NOT AN ATTRIBUTION INSTRUMENT — dropped, with the reason
`gp-0x6b98` is the **TOTAL motor command, base assist included**, and base assist is a function of
column torque. Its 6–9 Hz coherence with the column is **0.254 engaged but 0.544 MANUAL**, where the
LKAS command is identically absent. **That is loop feedthrough, not attribution.** The road channels
(`imu_vert`/`imu_lat`/wheel-speed roughness) sit **at their shuffled controls in the engaged arm**.
⚠ This also bounds the V88 handoff's own §5 coherence table — the honest carrier there was always
the prominence contrast (52 % vs 13.3 %), as its scoring agent said.

### 4. 🛑🛑 THE BASE-ASSIST DAMPER IS CLOSED AS A MICRO-RATCHETING LEVER — on arithmetic, not on a null
`analysis-2020accord/v89_b1_damper_surface.py`, read from V88's own image.
`ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)` has **two MULTIPLICATIVE dead zones**:

```
FactorC  X=[2240,3840,5120,8960] ct = [35,60,80,140] km/h    Y=[0,234,429,908]   <- 0 below 35 km/h
FactorE  X=[  60, 400,2500,4000] ct = [12.7,84.9,530,849] °/s Y=[0,140,539,927]   <- 0 below 12.7 °/s
```
Mode 24 ≡ 26 and 25 ≡ 27, byte-identical on V88. Against route 73's measured engaged distribution:
**the damper contributes exactly ZERO on 95.91 % of engaged frames**, and on **100.0 %** of the
operator's micro-ratcheting regime (229 s at |rate| 1–13 deg/s) and **100.0 %** of his ratcheting
regime at parking-lot speed (131 s).

★ **AND NEITHER PRIOR TEST EVER HAD BOTH ZONES OPEN** — a RULE-5 failure against a *product*:
- the **`FactorE X[0]` lever was withdrawn as "structurally vacuous"** because FactorC was 0 at creep;
- **`FactorC Y[0]` WAS tested, as V86B on route 70**, lifted to the record's own `Y[3]` (908/875) —
  but **FactorE stayed 0 below 12.7 deg/s**, so V86B armed the damper only for *spinning quickly*,
  never for *spinning at all*. Operator on V86B: *"extra dampening on LKAS and in general at slow
  speed"* — the cost was felt; the micro regime was never armed.

🛑 **But sizing kills it anyway.** With FactorC `Y[0]` lifted AND `FactorE X[0]` 60→12, `ch₀` at
creep reads **0 / 3 / 10 / 25** counts at 2 / 5 / 10 / 20 deg/s. Reaching even 25 % authority (256)
at 10 deg/s needs `FactorE(10 °/s) ≥ 288` — **unreachable by moving X; it requires raising `Y[0]`
off zero, which is a STEP AT ZERO RATE = a relay in rate = the V78/V79/V80 move, recorded as
"WORST GRINDING EVER".** ⇒ **Do not propose the damper for micro-ratcheting. Cal-only, it cannot
deliver.**

### 5. ⇒ WHERE V89 STANDS — the lever must be ENGAGEMENT-GATED **and** RATE-DRIVEN
§1 says the firmware's contribution scales with wheel rate. That is a **structural filter on
candidates**, and it is new. Ruled out or already spent:

| candidate | status |
|---|---|
| command-side HF reduction (Lever B class) | 🛑 **measured NON-fix** — V88 halved 15–22 Hz command content, ratchet `e_6-9` V88/V67 = 1.040 [0.759, 1.260] |
| a bigger `0xC6446` dose | 🛑 blocked by the ±8192 rail (2.5× at the rail hot-end, 3× pins) **and** the elasticity failed its out-of-sample dose test |
| base-assist damper (FactorC/FactorE) | 🛑 **closed this session** — §4 |
| FactorD / `gp-0x6a10`, `0xC64C8` m2, `0xC61F6`, a pole on r24, `0xC63B8` | 🛑 all previously killed on structure |
| **the r24 engaged arm ITSELF** | ⏳ **the one untested candidate that fits §1** — Lever B makes r24's gain switch on `gp-0x6806` from 2622 to **5244 when LKAS applies**, i.e. the firmware already contains an *engagement-gated, rate-derivative* gain. **Every build has pushed it UP. §1 says test it DOWN.** |

### 5b. 🛑 THE LEVER-B DISCRIMINATOR, ON THE FULL CORPUS — still inconclusive, but no longer exposure-blocked
`eng × log|rate| × LeverB` band contrast **+0.075 [−0.099, +0.245]** over 235 blocks; `eng × LeverB`
**+0.274 [−0.094, +0.652]**. Both still fail to resolve the effects they are testing.
🛑 **But the reason has changed and it matters:** the earlier "we need 4× the exposure, design a new
drive" recommendation was **based on a loader bug, and is withdrawn.** The corpus is 2.4× what that
glob saw and the answer did not sharpen ⇒ **more of the same driving will not settle Lever B.**
⊕ It also no longer matters much: §1 shows the amplification is **not rate-dependent**, which was the
whole reason r24 (a rate derivative) was the lead candidate. **r24's engaged arm is demoted, and
§1b's friction line replaces it.**

### 6. ⏹ SUPERSEDED — V89 flew (routes `75`/`76`) and V90 (route `77`) carries its K1 unchanged
The "BUILT, VERIFIED, UNFLASHED" block that stood here is superseded by the flight results and moved
verbatim to `docs/STATE-ARCHIVE-pre-V89.md`. **What survives and is still load-bearing:**
`0xC40D2` = **204** is on the car and stays there · `0xC40D2` is **1 reader / 0 writers** (`0x3BAFE`
in `FUN_0003b8f6`), censused twice through the `hw2 = disp|1` trap that returns a **false zero** on a
naive scan · 🛑 **`0xC4080` (K0, the NEVER-RAISE pure-relay hazard) is untouched at 0** — K1 scales
the `|model|` arm alone and is **not** the V80 class.
**On-car verdict: FLAT** (order-clean stratum contrast 0.947 [0.827, 0.979] inside a same-build
placebo band of [0.900, 1.111] = 0.92σ), and V90's data says why **structurally**: above 1 °/s
friction and `|model|` are near-collinear (headline §B). 🛑 **The block-bootstrap CI excluded 1.00 and
would have been reported as a resolvable 5 % fix — the placebo control earned its keep on first use.**

### 6b. ✅ THE POLARITY IS VERIFIED — V89's HOLD IS LIFTED. More modelled friction ⇒ MORE assist
The operator asked *"I thought we didn't want friction… how do we know it's modelling friction?"* and
the second half of that exposed an unverified sign. It is now traced end to end, every link read in
Ghidra on stock `code.bin`.

**THE TERM IS COULOMB FRICTION — five ways, four of them independent of this session:**
1. **Form.** `friction = |model| × sign(polarity × gp-0x6abc) × K1/1024` = `F = μ·N·sign(v)`.
2. **The sign IS a velocity sign.** `FUN_00041464` @`0x4170C`: `gp-0x6abc ← gp-0x4f50`, which
   `STATE.md`'s own signal table calls the **resolver/motor ELECTRICAL RATE**.
3. **Its companion is INERTIA** — a term ∝ `d(rate)/dt` scaled by `0xC646E`, a cal the kit's own
   FROZEN lists already label **"INERTIA gain"**. Applied torque − friction − inertia = a mechanical model.
4. **The record named it first:** V87's `BUILD-LINEAGE.md` row already calls `gp-0x6b70`
   *"the Coulomb friction compensator"* and measured it on-car — **non-zero 99.80 %, negative 67.19 %,
   aggregator optional-term gate OPEN 100 %.**
5. ⊕ **Coulomb friction is rate-INDEPENDENT by definition**, and §1 measured the engagement effect as
   rate-independent (+0.022 [−0.070, +0.116]). **Independent corroboration nobody designed for.**

**THE SIGN CHAIN, link by link:**

| # | where | effect of raising K1 |
|---|---|---|
| 1 | `0x3BBC2` `subf.s r10,r8,r8` — friction is **subtracted** from the model | model out **↓** |
| 2 | `FUN_0003bc20` plausibility ±20000 → `gp-0x6bfe` | ↓ |
| 3 | `FUN_00038148` `residual = MODEL − ACTUAL` | ↓ (already 67 % negative) |
| 4 | `gp-0x6b70 = sign(res) × LERP(\|res\|)` | **more negative** |
| 5 | `FUN_00037fe6`: `gp-0x6ad6 = (… + gp-0x6b70) × LERP >> 10` — lane ENABLE flag `0xC64B0` = 1, unit weight | **↓** |
| 6 | `FUN_0003a382`: `error = gp-0x4f60 (measured driver torque) − clamp(gp-0x6ad6)` | **↑** |
| 7 | PID (P, I, D all positive-coefficient) → `gp-0x6ad4` | **↑** |
| 8 | `0x3ACA8` `ld.h -0x6ad4[gp],r6` → windowed → **`mov`, `add`×8, no negation** → `0x3AD20 st.h r10,-0x6b94[gp]` | **↑** |
| 9 | `gp-0x6b94` → governor → `gp-0x6ace` → comp-add → `gp-0x6acc` → shaper → `gp-0x6b98` → motor | **more assist** |

⇒ ✅ **MORE MODELLED COULOMB FRICTION ⇒ MORE ASSIST ⇒ A LIGHTER WHEEL, NOT A HEAVIER ONE.**
**V89 does not fight the LKAS demand — it assists it.** The operator's constraint is satisfied in the
favourable direction, and the earlier "may feel notchier/heavier" caveat is **withdrawn as stated**.

★ **And the physics is right.** `gp-0x6ad6` is a **torque-tracking REFERENCE**, not a torque added to
the motor. The loop holds the driver's *felt* torque at that target. Telling it the plant has more dry
friction **lowers the target driver effort**, so the PID delivers more motor torque to hold the felt
torque down. And because Coulomb friction **flips sign at every wheel reversal**, an estimate that is
wrong by a constant produces a **step error at every reversal — which is what a ratchet is.**

🛑 **THE ONE HONEST CAVEAT — V56 muted this exact lane and got a null.** `0xC6AFC`/`0xC6AFE`
32768 → 0 killed the whole `FUN_0003a382` → `gp-0x6ad4` output bound, and the memory says the lane is
*"ELIMINATED as the driver… do not re-propose"*. **But that null was scored on `P[15–26 Hz]` — the
20–25 Hz mode — NOT on 6–9 Hz**, and route `24` is **not on disk**, so the ratchet band was never
scored against it. `0xC6AFC`/`0xC6AFE` = 32768 on **all 30 other builds**, so the corpus cannot test
it either. ⇒ **The elimination is BAND-SCOPED and is being carried as if it were general.** That is a
real risk to V89's thesis and it is not resolvable from the data on hand — **it is what the flight tests.**

🛑 **CORRECTION — THE OFF-BY-0x1000 TRAP, FIFTH RECURRENCE.** An earlier draft of this section said
*“lane weight `0xC74B0` = 32, siblings 176/161/14/14”*. **Wrong region.** `tp` = `0xBF000`, so
`tp+0x74B0` is **`0xC64B0`**. The real cells are `0xC64AD..0xC64B3` and they are **0/1 ENABLE FLAGS,
all = 1** — exactly as this file already recorded. Likewise the observer's ACTUAL-side gains are
`0xC63A0..0xC63AE` (all 1024 = unity, EMA α `0xC63AC` = 102 — *the same “Path-2 IIR” the V88 handoff
discusses*), and `gp-0x6b70`'s clamp is `0xC6200` = **8192**, not 41064.
✅ **The sign chain is UNAFFECTED** — the lane still enters with a `+` at unit weight. Only the weight
characterisation was wrong.
🛑 `build_v83a_tva.py` carries an assertion naming this exact trap (*“tp+0x73A0 is 0xC63A0, NOT
0xC73A0 — the off-by-0x1000 trap has recurred four times”*) **and it still happened.** A warning in one
build script does not protect a session that never opens it. ⇒ **compute `tp+off` in code, never by eye.**
⚠ Still unsized: `gp-0x6b70`'s magnitude response to the dose — the LERP it passes through lives in
**RAM** (`gp-0x64b8`/`gp-0x641c`), so the transfer cannot be read from the image.
⊕ Method note: the orchestrator hand-decoded the `add` field split with a Format-VII layout on a
Format-I instruction and got nonsense. **Ghidra's listing is the authority** — `mov`, eight `add`s,
no `sub`/`subr`/`negf` in the accumulator. This is exactly the standing "assembly CONFIRMS, it does
not FORM" rule doing its job.

### 7. ⏹ SUPERSEDED — the V89 pre-registration, and how it scored
Full text moved verbatim to `docs/STATE-ARCHIVE-pre-V89.md`. Outcome: **IDENTITY PASS · H1 (probe
fires) PASS · 🛑 H2 (THE LEVER) FAIL — no band-specific fall survives the order veto · H3 (the
operator's constraint) PASS, no sign-chain inversion · H4 the operator: *"fixed nothing, still only as
good as V88."*** The honest label held: the dose *direction* was measured, "K1 acts like the gate" was
BELIEF, and the null landed on the BELIEF.
⊕ **What the flight added that the pre-registration could not**: V89's own probe showed the friction
term is `sign(motor rate)`-gated and `|friction| ≥ 0.0625` on only **0.9 %** of micro-ratcheting
frames — **arithmetic saying the lever was pointed away from the target**, a fifth independent
confirmation that the term is Coulomb friction, and **not** a falsification of the friction account.
V90 then added the sixth (the rate-gate visible directly in the (b6,b5) 2×2 below 1 °/s).

### 6. ✅ COLLATERAL — `STATE.md` size discipline
See the cap note at the top of this file. `CLAUDE.md` carries the rule now.

---

## ★★★★★ SUPERSEDED HEADLINE, 2026-08-09 — V88 FLEW, THE FORK CLOSED, AND THE HIGHWAY ARRIVED
**Superseded as the headline by the 2026-08-11 block at the top; the findings below are NOT
superseded.** V88's grinding fix is still on the car (Lever B, carried through V89/V90/V91/V92).

### 0. ✅ V88 FLEW — route `73` (`75604b0a432fdc89_00000073--9380c74d52`), 11 segments, cache `_cache_r73/`
61,161 frames / 613.4 s, **72.7 % engaged = 7.41 min**, **fault-free**: `STEER_STATUS` {0: 61,147, 3: 15},
DTC-active duty **0.000000**, 0 sentinels, no EPS event in 1,786 `onroadEvents`.
**Operator, in his words: the audible GRINDING IS FIXED · hints of grind #2 but he could not elicit it ·
MICRO-RATCHETING and RATCHETING (stuttering) are now the main remaining issues.**

★★ **THE ≥50 km/h DROUGHT IS OVER — 119.6 s engaged ≥50 km/h, 80.2 s ≥80, v_max 116.6 km/h**, against
**0.0 s on each of the four prior routes.** Highway = segments 4–5, both 100 % engaged.

**IDENTITY, parameter-free, triple-measured:** `b6 == (427 wire ≥ 160)` = **0.9654** vs the V87 control
**0.4022**, with **chance = 0.6028** from the marginals ⇒ V87 sits essentially *at* chance. Duty match
0.27330 vs 0.27334; edge-conditioned agreement 0.9901; lag sweep peaks at lag 0.

### 1. ★★★★★ H1 CONFIRMED — THE FIX DID NOT COST STEERING AUTHORITY
Speed-matched 2–4 m/s, engaged, unclipped, episode-bootstrapped (orchestrator's independent crude
estimator in brackets):

| band | V88/V87 | verdict |
|---|---|---|
| **0.5–3 Hz — the peak effective LKAS command** | **1.192 [0.780, 1.812]** [1.121] | **NULL — untouched** |
| 3–6 Hz | 1.165 [0.959, 1.375] | null |
| 6–9 Hz | 0.859 [0.503, 1.171] [0.720] | null |
| 9–12 Hz | 0.604 [0.465, 0.943] | FALL |
| **15–22 Hz** | **0.549 [0.407, 0.844]** [0.625] | **FALL** |

**Aliasing excluded on two independent 100 Hz channels** (427's Nyquist is 24.9 Hz): `tq` 15–22 Hz
**0.33×**, `rate_c` **0.31×**, while **28–35 Hz is FLAT (1.13× / 0.94×)**. Column `tq` 15–22 Hz rms
**259.4 → 84.6**. ⇒ **Lever B halved the delivered command's HF content at zero low-frequency cost.**

🛑 **THE ORCHESTRATOR'S PRE-FLIGHT HYPOTHESIS WAS REFUTED.** He predicted a 15–22 Hz **RISE**, reasoning
that r24 is a differentiator whose gain Lever B doubles. **r24 is rate FEEDBACK inside the loop and
`gp-0x6b98` is the loop's OUTPUT, not its input** ⇒ more derivative feedback = more damping = **less** HF
everywhere. V87's engaged spectrum rising with frequency (29 / 29 / 52 ct rms) against a **flat** manual
arm (~9) is the signature of an **under-damped closed loop at stock derivative gain.**

### 2. ★★★★★ H2 — THE FORK CLOSED, AGAINST THE FIRMWARE
V88's `b7` sign bit reconstructed the **SIGNED** delivered command and V87's rectification screen was
**dropped entirely** — 75 unclipped engaged windows vs V87's 14 screened. Controls first: the sign bit
flips at median `|cmd|` **36.8 ct = the 22.9th percentile** (a noise bit sits at the 50th); `b5`/`b6`
agree with the 427 magnitude in 99.56 % / 96.02 %; corr(0.2–3 Hz signed cmd, column) = **−0.671** where
the *rectified* magnitude gives **+0.030**.

| channel | 6–9 Hz prominence | above the p95 floor (10.64) |
|---|---|---|
| column torque `0x18F` | **11.17 [7.85, 16.30]** | **52.0 %** |
| **SIGNED `gp-0x6b98`** | **5.46 [5.12, 5.94]** | **13.3 %** |
| rectified `\|cmd\|` (V87's view) | 5.62 [5.10, 6.80] | 12.0 % |
| openpilot `0x0E4` | 4.43 [3.87, 4.93] | 1.3 % |

**Signed ≈ rectified ⇒ rectification was NEVER hiding a line; V87's null was CORRECT** and is now
established rather than assumed. ⇒ **THE RATCHETING IS NOT A TONE THE EPS COMMANDS. No notch, and no
phase lever at 7.79 Hz.** Reproduced at nw=256 and on the independent 100 Hz cave grid.

★ **AND THE GATE-2 HAZARD MOVED.** Signed-cmd↔column coherence² vs a shuffled-pairs control of
**0.009 [0.001, 0.061]**: 2–4 Hz 0.038 · 6–9 **0.123** · 9–12 0.090 · 12–18 0.133 · **18–24 Hz 0.310 —
the HIGHEST, above the ratchet's own band.** The loop is tightest in **grind #1's** band ⇒ **any future
filter's phase cost lands at ~21 Hz, not at 7.8 Hz.** (At 7.79 Hz: coh² 0.343, `|tq/cmd|` 6.24, phase
−30.9°; the rectified channel returns 0.009 = *exactly* the control.)

### 3. ★★★★ THE THREE SYMPTOMS — the instrument agrees with the operator on all three
**Grinding (he says FIXED).** `e_18-22`, engaged creep, on the ruler the ~109 target was measured on —
and the ruler is calibrated: this session reads V67 at **110.7** against the record's ~109.

| build | `e_18-22` |
|---|---|
| V67/r47 | 110.7 [75.2, 172.1] |
| V81/r67 | 69.1 · V84/r6d 221.8 · V85/r6e 343.7 · V86B/r70 186.5 |
| **V87/r71** | **400.2 [261.6, 917.4]** |
| **V88/r73** | **150.5 [118.5, 183.8]** |

**V88/V67 = 1.101 [0.424, 2.206] — a clean null ⇒ V88 is statistically indistinguishable from the kit's
best-ever grind-#1 result.** On the tighter creep ruler the separation from V87 is disjoint (161.0
[127.3, 420.0] vs 932.8 [442.6, 1532.5]). Negative control 32–38 Hz inside its null ⇒ band-specific.
🛑 V88/V87 = 0.549 [0.277, 0.979] excludes 1.00 but does **NOT** clear V87's own split-half null of
[0.30, 3.40] ⇒ **the load-bearing statement is the absolute level against V67, not the ratio.**

**Grind #2 (he says hints, could not elicit).** **ZERO events** in the strict creep-cornering regime
(0.3–4 m/s, |ang| ≥ 100°), max 367.3 against the 500 ct criterion — the same zero as V67/V68.
🛑 **Exposure 47.4 s = 29 % of the 166 s interpretability floor ⇒ formally UNINTERPRETABLE**; the zero is
real but weak, and is not upgraded. 5 marginal crossings elsewhere (1.02–1.31× threshold vs V86's 2796.5),
**four of them at highway speed** — events no prior route could have detected, not creep grind #2.

**Micro-ratcheting and ratcheting (he says these are the main remaining issues).** 🛑 **UNCHANGED, and
unchanged all the way back to V67**: `e_6-9` V88/V67 = **1.040 [0.759, 1.260]** over 14 matched cells —
the tightest null in the session. V88/V87 = 1.278 [0.801, 2.073], inside null. **That is exactly V88's
pre-registration.** ⇒ **The ratcheting did not get worse; the grinding above it came down, so it is now
the loudest thing left.**
🛑 **The data do NOT separate "micro-ratcheting" from "ratcheting" as two objects** — the apparent 9–10.5
and 10.5–12 Hz clusters are **wheel order 2** at higher speed. That is a statement about the instrument,
**not** about the car: the operator names two symptoms and he is the one feeling them.

### 4. ★★★★★ THE HIGHWAY — the ratchet is SPEED-INVARIANT, and it is now PROVEN
Never testable before; the four prior routes had 0.0 s engaged above 50 km/h. Every row carries a
per-window speed census and a wheel-order veto (orders 1–6, circumference swept 2.073–2.088 m).

| stratum | n | v med (m/s) | **f0 [CI] Hz** | prominence | **e_6-9 ct** | order-vetoed |
|---|---|---|---|---|---|---|
| creep <10 km/h | 26 | 2.11 | 8.01 [7.87, 8.47] | 9.01 | 402 | 10/36 dropped |
| 10–40 km/h | 60 | 7.40 | 8.08 [7.93, 8.18] | 5.18 | 286 | 114/174 dropped |
| 40–80 km/h | 36 | 13.20 | 8.31 [8.24, 8.69] | 2.85 | 195 | 21/57 dropped |
| **>80 km/h** | 58 | 30.23 | **8.36 [8.23, 8.49]** | 2.37 | **83.5** | **0/58 — intrinsically clean** |

**The discriminating test is the SLOPE: `f0 = +0.0102·v + 7.998 Hz`, against wheel order 1's 0.4807 —
47× flatter**, corr(f0, v) = +0.106. ⇒ **SPEED-INVARIANCE CONFIRMED [EVIDENCE].**
★ **The >80 km/h stratum is intrinsically order-clean** — at 30 m/s order 1 has climbed to 14.5 Hz, above
the band, so **no order 1–6 can reach 6–9 Hz at highway speed** ⇒ the cleanest ratchet measurement in the
corpus, and it cannot be a road-input artefact.
★ **Amplitude decays 4.8× from creep to highway (402 → 83.5 ct)** ⇒ **the ratchet is a LOW-SPEED
phenomenon in AMPLITUDE while being FIXED in FREQUENCY** — consistent with eliciting it in the car park.

### 5. ★★★★ THE 26–31 Hz RING IS REAL, AND IT IS 29.02 Hz
Marked UNSCOREABLE on `6f`/`70`/`6e`/`71` for exposure. Free argmax 24–34 Hz over 115 engaged windows
above 40 km/h: **f0 median 29.02 Hz**, prominence 10.25. Order 2 lands within 0.8 Hz in 41.7 % of windows
⇒ contamination is real; **after the veto 49/115 survive: `e_26-31` = 121.4 [77.6, 176.5], prominence
5.67 [4.82, 8.40]. The line SURVIVES the veto — it is not wheel order 2.** Same family as V81's 27.75 Hz
and V80's 27.4 Hz. **Above 80 km/h it is the dominant non-order band on every channel** (`tq` 32.28 vs
18–22 Hz 16.30; `rate_c` 3.46, the largest of six bands). **Grind #1 falls away at highway** —
`e_18-22` 161.0 (creep) → 43.0 [32.6, 86.1] (>80 km/h).

### 6. 🛑 WHAT ROUTE 73 COULD NOT ANSWER — recorded verbatim, unedited
1. **Ring-down ζ / Q.** 2 usable edges, one with the wrong sign. Needs a deliberate engage/hold/disengage protocol.
2. **The V88/V87 grind-#1 ratio against route 71's own noise floor** — V87's split-half null is [0.30, 3.40]; nothing under ~3× is resolvable on that arm.
3. **Grind #2 at creep cornering** — 47.4 s = 29 % of the 166 s floor.
4. **Any engaged-vs-manual contrast above 20 km/h** — zero manual seconds exist there.
5. **Micro-ratcheting vs ratcheting as two objects** — no instrument here separates them.
6. **Any 15–22 Hz claim from the 427 probe alone at highway** (the 28–35 Hz alias). The creep-band claim in §1 *was* separated, on the 100 Hz channels.
⊕ And the ladder at speed is null across V67/V81/V84/V85/V88 — **74 s above 80 km/h would need ~10 min** to resolve a 1.15× effect.

### 7. 🛑 INSTRUMENT DEFECT FOUND THIS SESSION — kit-wide, all 13 caches
`z["t"] == z["raw14_t"][1:]` and `z["probe"] == z["raw14_b4"][1:]` in **every** cache `_cache_r5e` …
`_cache_r73`. `extract()` appends `raw14_*` on every 0x14A frame but a **row** only after the first
0x18F, so the row family is permanently one sample shorter. **Pairing `t` with `raw14_b4` reads the cave
byte one frame (~10 ms) early = 28° of phase at 7.79 Hz.** It cost the orchestrator's own identity check
0.9437 instead of 0.9654. **Safe pairings: `(t, probe)` and `(raw14_t, raw14_b4)` — never cross them.**
Audit: `analysis-2020accord/audit_raw14_offbyone.py`. **H2's script was checked and uses the aligned pair
⇒ H2 is unaffected.** ⚠ **NOT audited: whether any HISTORICAL result rests on the crossed pairing.**

### 8. 🛑 FIRMWARE LEVERS EXAMINED AND KILLED THIS SESSION — structure, not nulls
- **FactorD / `gp-0x6a10`** — the axis is **ABSOLUTE STEERING ANGLE, not a tracking error**, so the
  1/ω selectivity argument is dead: **this firmware has NO frequency-selective lever.** Also inert below
  ~35 km/h because FactorC's `Y[0]` = 0 multiplies in first. ⚠ **Scope: the inertness is speed-scoped and
  does NOT apply above ~35 km/h**, where 210 of route 73's engaged seconds now sit.
  🛑 The **auto-memory** copy of `accord-factord-is-the-angle-error-lever` was the stale pre-correction
  version and **sent a subagent down a dead thread this session** — corrected. **When a `reference_*` fact
  is corrected, correct BOTH copies.**
- **`0xC64C8` mode 2** — byte-exact **no-op**: `0xC61D4` = 0 on stock and on V88 (orchestrator-verified),
  so mode 2 = `clamp(gp-0x6acc[±8192] + 0, ±12288)` = mode 0. And even non-zero it is a flat scalar bias,
  never a filter. **Structurally impossible, not merely untested.**
- **`0xC61F6` (r24 deadzone, frozen at 3 in all 59 builds)** — **raising it cuts the WRONG way.** A
  fixed-count deadband clips the *smaller* signal first, and LF-sourced `dtorque` is ~12× smaller than
  HF-sourced for equal physical amplitude ⇒ it spends its budget on low-frequency content. Dead on
  arithmetic. (The record's standing "DO NOT" is about *lowering* it — a different claim.)
- **r24 has NO pole anywhere** between the difference and the aggregator sum (4 independent decompiles).
  r26 has a 2-tap boxcar but on its **gain**, not its signal: `|H(7.79 Hz)| = 0.9997`. ⇒ **adding a pole
  on this lane is a CODE edit, not a cal edit.**
- **Both friction relays are speed-gated only** ⇒ neither can explain the engaged-vs-manual asymmetry.
- ★ **The `<3 Hz` row is STRUCTURALLY protected from any r24-side edit**: the N=4 backward difference gives
  `|H(18 Hz)|/|H(1 Hz)| = 17.85×`, so a derivative-lane change cannot reach the LKAS command band.

### 9. 🛑🛑 THE OBVIOUS V89 — A BIGGER `0xC6446` DOSE — IS BLOCKED BY THE CLAMP
Orchestrator-computed, `analysis-2020accord/orch_c6446_clamp_headroom.py`.
`r24 = clamp( (clamp(dtorque, ±5120) * gain) >> 10, ±8192 )`, LERP 2622 (mode 24 ≡ 26), V88 = 5244.
Against V65's `|dtorque|` = **123–839 ct over 120,049 frames**, folding in the **1.77×–2.55×**
scalar-vs-curve spread (hot end = 1.275× nominal, and the hot end meets the rail first):

| `0xC6446` | dose | `\|r1\|` to rail | hot-end margin | verdict |
|---|---|---|---|---|
| 2622 | 1.000× stock | 3199 | 2.99× | clear |
| **5244** | **2.000× — V88, FLOWN** | **1600** | **1.50×** | **thin — inside V80's blind spot** |
| 6555 | 2.500× | 1280 | **1.20×** | 🛑 at the rail at the hot end |
| 7866 | 3.000× | 1066 | **1.00×** | 🛑🛑 pins — relay class |
| 10488 | 4.000× | 800 | 0.75× | 🛑🛑 pins |

⇒ **The usable dose window above V88 is narrow to non-existent.** ★ **This gives a MECHANISM for
`accord-v62-fixed-the-grinding`'s "2× ≈ OPTIMUM, not a ramp" — the RAIL, not the tuning.**
🛑 **But the margin rests on a `|dtorque|` distribution measured on V65, a different build and route.**
The arithmetic is EVIDENCE; the margin is BELIEF.
⇒ **V89 should MEASURE `|dtorque|` on V88, not bet on V65's distribution.** `gp-0x6ada` is r24's
post-clamp RAM mirror — **1 writer / 0 readers, free, blast-radius-zero telemetry** — and settles it.
### 10. 🛑🛑 THE CO-MOVEMENT FAILED ITS OWN DOSE TEST — a retraction, out-of-sample
The +0.364 co-movement looked like a lever. **V88 is the experiment that settles it, against the slope.**
- Speed-partialled elasticity `d(log ratchet)/d(log 15–22 Hz cmd)` = **+1.082 [+0.814, +1.329]**
  (band rms, corr +0.646); prominence gives +0.682 [+0.256, +1.200].
- **Predicted from V88's 0.549× cut: ratchet ratio 0.523 [0.451, 0.614]** — far below the resolvable
  floor of 0.759, i.e. **plainly visible if real**.
- **Measured: `e_6-9` V88/V67 = 1.040 [0.759, 1.260]. The intervals DO NOT OVERLAP.**
- Inverting V88 into a causal elasticity: **b_causal = −0.065 [−0.385, +0.460]** — consistent with ZERO,
  and its **upper bound sits BELOW the observational slope's lower bound.** Not the same quantity.
- ⊕ **The 32–38 Hz NEGATIVE CONTROL also responds** (elasticity **+0.664 [+0.441, +0.827]**) — a band
  that is neither symptom tracks the command at ~60 % of the ratchet's rate ⇒ **operating-point
  covariation a firmware dose does not reproduce.**

⇒ 🛑 **DO NOT spend V89 on further HF command reduction hoping the ratchet follows.** On the most
optimistic elasticity still consistent with V88 (b = +0.46), halving the ratchet needs the 15–22 Hz
command at **0.22× of V87 — a further 2.5× cut on top of V88** — which reaches into the range where
0.5–3 Hz authority is at risk. **On the central estimate, no achievable cut moves it at all.**
⊕ **The operator's sentence:** *"Cutting high-frequency content out of the delivered steering command is
now a measured fix for the grinding and a measured NON-fix for the ratcheting."*

### 11. 🛑🛑 NEXT STEPS ARE ANALYSIS ON EXISTING LOGS — **NOT another drive.** Operator-corrected.
**The orchestrator recommended a dedicated ring-down driving session and was corrected: the diagnosis of
micro-ratcheting and ratcheting is a parking-lot-speed question, and route `73` already contains it** —
segments 0/8/9 give ~118 s engaged below ~15 km/h, exactly where D5 measured the ratchet at its largest
(402 ct). **A new drive buys nothing diagnostic.**

★ **And ring-down is no longer the only route to Q. V88 changed that and the session under-used it.**
Ring-down *was* the only ζ estimator that had passed its own control, so "we cannot measure Q" had
collapsed into "we need more disengagement edges". **V88's sign bit broke that**: H2 already produced
`|tq/cmd|` = **6.24 at 7.79 Hz, phase −30.9°**, with coherence² going **0.009 (rectified — exactly the
shuffled control) → 0.343 (signed)**. **That is a transfer-function measurement, and a resonance's Q falls
out of its peak shape and phase roll-through with no disengagement at all.** V87 could not do this because
rectification destroyed the phase — which is precisely why that session fell back on ring-down.

**⇒ THREE ANALYSES, all on data already on disk:**
1. **Fit `cmd → column` across 4–15 Hz on route 73's creep segments (0, 8, 9).** Extract Q from the peak
   and from the phase slope, coherence as the quality gate. **This is the measurement V88 was built to
   make possible, and the session used it only for a yes/no.**
2. **Pool ring-down edges across all 13 caches**, not just `r71`/`r73`. Only those two were screened, and
   only on `latActive` falling edges under strict criteria. ⚠ Screen by damper state: V87/V88 are stock on
   FactorC and pool cleanly; **V74–V86B do not.**
3. **Partial coherence against the IMU** (`imu_vert`/`imu_lat`, wheel speeds), run alongside 1 because it
   can undercut it: **if the mode is excited mainly by ROAD input rather than by the command, `cmd→column`
   is the wrong transfer function and its Q is biased.** Which path dominates is itself the result — it
   decides whether *any* command-side lever could ever work.

🛑 **The only thing that genuinely needs new driving is a BUILD comparison — and that needs a new build,
not a new drive.** Everything diagnostic about the two remaining symptoms at parking-lot speed is on tape.

⊕ **The ring-down sizing below is retained as knowledge, not as a request.** Revisit only if 1–3 return
coherence too low to fit — and even then, prefer a probe on a build being flashed anyway.

Ring-down is the only ζ estimator that passes its own control; route 73 gave **2 usable edges from 5
disengagements, one with the wrong sign.** Monte-Carlo of the actual fit through route 73's own beds:

| pre-edge amplitude | sd(log ζ) | N for ±50 % | N for ±30 % |
|---|---|---|---|
| 400 ct (creep) | 0.636 | 10 | 23 |
| **250 ct (35–45 km/h)** | 0.783 | **15** | **35** |
| 90 ct (highway) | 1.077 | 28 | 65 |

🛑 **NOT the parking lot — 35–45 km/h, straight, empty road.** 7–14 km/h is where **wheel orders 4–7 land
inside 6–9 Hz**, and an order does not decay when LKAS drops ⇒ it pins the floor and flattens the fit;
below ~5 km/h the lockout means LKAS is barely applying (6.9 s engaged below 5 km/h all route).
**Order-clean bands for 6–9 Hz: 1.8–3.6 · 33.8–44.6 · 67.7+ km/h.**
🛑 **The orchestrator's counter-argument was TESTED AND REFUTED** — he argued a persistent order should
land in the estimator's subtracted floor and cost dynamic range, not bias. Injecting a non-decaying tone:
**bias 1.01× (none) → 3.53× (25 % at −0.93 Hz) → 5.69× (50 % at +0.27 Hz).** Head-to-head, creep-with-order
needs **38** edges for ±50 % at sd_log 1.26; **road-no-order needs 16 at sd_log 0.80.** Road wins on both.
**Route 73's 5 edges failed as:** 3.5 s / 3.4 s manual after (needs 4) · 0.1 s engaged before (needs 3) ·
**envelope GREW after the edge** (re-excited by hands or road) · 1 USABLE. ⇒ **hold engaged ≥5 s, stay
hands-off ≥5 s after, disengage with the cancel button — never by grabbing the wheel or braking.**
✅ **The confound is ABSENT on V88, byte-checked**: FactorC is stock in all four modes and **mode 24 ≡
mode 26** (`0xD77DA`/`0xD77EE` = 0 where V86B had 908/875), and the full-image delta has **no edit
anywhere in `0xD6000–0xD8000`** ⇒ **disengaging removes the excitation and nothing else.**

---

## 🛑 STANDING INSTRUMENT CORRECTIONS — they apply to every analysis in this file

### 🛑🛑 NAMED TRAPS ADDED 2026-08-11 (the V90 flight session) — eight, each of which changed or would have changed an answer

**1. 🛑🛑 THE RATE-CHANNEL RULE, AND ITS SCOPE. Getting this wrong INVERTS a build decision.**
- **For PHASE and IMPEDANCE work use the `0x18F`-sourced rate (`rate_f`).** `tq` and `rate_f` are both
  fields of the **same held `0x18F` frame** (`last18[0]`/`last18[1]` in the extractor), so the ~9.15 ms
  staleness is common to numerator and denominator and **cancels exactly** in `Z = S_Tω/S_ωω`.
  **Proved, not asserted:** recomputing `Z` with `rate_c` separates the phase by exactly the skew
  (−11.1° vs −9.9° predicted at 3 Hz; −100.1° vs −93.9° at 28.5 Hz; −116.6° vs −108.7° at 33 Hz).
  > **Had `rate_c` been used, 26–31 Hz would read −30.3° instead of +69.6°, giving `+0.184 PUMPING`
  > instead of `−0.336 DAMPING` — the OPPOSITE BUILD DECISION, from the same data, at the same
  > coherence (0.827 vs 0.834). Same flip at 18–22 Hz (+45.8° ⇒ +0.180 PUMPING).**
- 🛑 **But for ABSOLUTE MAGNITUDE use `rate_c` (`0x14A`).** Regressed on the differentiated angle
  (`0x14A`, 0.1 °/count — a solid LSB anchor) over four routes:

  | channel | slope vs d(angle)/dt | r |
  |---|---|---|
  | **`rate_f` (`0x18F`)** | **0.743 · 0.756 · 0.763 · 0.767** | 0.96–0.98 |
  | **`rate_c` (`0x14A`)** | **0.952 · 0.958 · 0.962 · 0.963** | 0.98–0.99 |

  ⇒ **`rate_f` reads ~24 % LOW.** The kit's old "~25 % low" note is confirmed and **pinned to that
  channel specifically.** ⇒ 🛑 **STATE WHICH CHANNEL YOU USED, EVERY TIME.**

**2. 🛑🛑 A SAME-FIRMWARE PLACEBO PAIR IS MANDATORY FOR ANY CROSS-BUILD CLAIM — and the band contrast
does NOT rescue a thin cut.** V90 changes no calibration cell, so route 77 vs 75/76 is the **same
firmware on different drives**:

| pair (SAME FIRMWARE) | `e_6-9` | `e_18-22` | `e_32-38` (control) |
|---|---|---|---|
| **r77 ÷ r75** | **1.288 [1.017, 1.661]** — CI **excludes 1** | 1.121 [0.870, 1.472] | 0.993 [0.807, 1.189] |
| r77 ÷ r76 | 1.340 [0.925, 2.259] | **1.333 [1.001, 2.307]** — CI **excludes 1** | 1.379 [0.977, 2.164] |

**Two drives on byte-identical firmware return band ratios whose episode-block CIs exclude 1.00, and
one of them excludes 1.00 on the BAND CONTRAST as well.** ⇒ the honest resolution floor is
**±16–22 %** (32–38-contrasted) to **±33 %** (raw ratio). **Any cross-build ratio quoted with a
block-bootstrap CI and no placebo-pair null is over-confident.**

**3. 🛑 A BYTE-DIFF REPORTS THE FIRST DIFFERING BYTE, NOT THE CELL ADDRESS.** If a `u16`'s low byte is
unchanged, the run starts **one byte INTO the cell**. This produced off-by-one addresses for the
corridor/boost walls (`0xC674E/50/5A/5C`, floats `0xC6598/9C/AC/B0`) and the clamps
(`0xC61B2`/`0xC61B4`). **THE TELL IS THE VALUE**: the real cell reads a clean **512 → 2048** or
**1024 → 5120**; the off-by-one reads **2 → 8** and **4 → 20** — nonsense as calibration values.
⇒ **plausibility-check the VALUE, not just the address.**

**4. 🛑 AN ARRAY SWEEP MUST BE BOUNDED BY THE ARRAY'S OWN RECORDED EXTENT.** `range(32)` on a 34-slot
array **hid two modes**; "walk until it stops looking valid" **over-walked into `gain_B` and invented
two** (a prior walk reached "mode 289" and reported phantom differences at "modes 68/126", which are
`gain_B` array 0/1 mode 10). **The friction pointer array is 34 slots, modes 0–33.
`0xCBE74 + 34*4 = 0xCBEFC` is the FIRST SLOT PAST IT** — and it holds `0x000DAA44`, a perfectly
valid-looking pointer to a perfectly valid-looking `n=3` record. **A guessed bound is not a bound, and
neither is an exhaustion walk.**

**5. 🛑 `searchsorted` ON `logMonoTime` SILENTLY MISPAIRS ROWS — AND THE TIMESTAMP CHECK STILL PASSES.**
`evt.can` can carry **two `0x14A` frames in one event**, sharing `logMonoTime` *exactly* — **3,018
duplicate raw14 timestamps on r77** — so `searchsorted` collapses onto the first of each tie and
**mispairs 1,604 rows.** **Only a BYTE check catches it.** ⊕ The correct fix for the kit-wide `raw14`
off-by-one is that the map is a **constant lead** (= 1 on r77), derived and asserted elementwise
against both `raw14_t` and `raw14_b4` and stored as `row2raw14` in the npz
(`rlog-tools/extract_r77.py::_row2raw14`) — **not** a timestamp reconstruction.

**6. 🛑 `_r31_common.runs_of` RETURNS A GENERATOR.** The first consumer exhausts it and **every later
consumer silently sees ZERO windows.** This produced an all-NaN shuffled control on the first D3 pass
— **and a NaN control reads as "no control available", not as a bug.** Materialise with `list()`.
Worth auditing anywhere `runs_of` is passed to more than one estimator.

**7. 🛑 `np.interp` ON `raw14_b4` INTERPOLATES A BITFIELD.** `v88_d1_exposure.grid` does this; the
interpolated values have **meaningless bits**, so any bit test reading `g["b4"]` is suspect. Pair
nearest-within-10 ms instead.

**8. 🛑 A GROUP-DELAY SIGN IS A REQUIRED SCREEN FOR ANY TRANSFER QUOTED FOR SIZING.** Forward causation
*requires* the response to LAG the input, so a **negative group delay is positive proof of
feedthrough.** `|tq/b26|` = **17.76 ct/ct at 6–9 Hz**, coh² 0.289 against a shuffled 0.000 — the best
transfer on the route — **is feedthrough: the column LEADS `gp-0x6b26` by 48.8 ms.** Disqualified for
sizing. The **only** band that survives is **15–22 Hz** (2.64 ct/ct, −42.1°, coh² 0.333 vs shuffled
0.000, group delay **+6.3 ms**) — ⚠ **and even that is a closed-loop correlation that merely failed a
one-sided test, not a proven plant gain.**

⊕ **NINTH, re-measured this session: THE WHEEL-ORDER VETO'S SCREENING ASYMMETRY INVERTS AT HIGHWAY.**
With circumference 2.073–2.088 m and guard 0.8 Hz, order *k* reaches a band over
`v ∈ [(lo−0.8)·2.073/k, (hi+0.8)·2.088/k]`: **6–9 Hz** is clean only above **20.46 m/s** (18.8 is
*not* conservative enough) · **18–22 Hz** — order 2 covers 17.83–23.80 m/s, clean only above 47.6 m/s
(171 km/h) · **32–38 Hz** — order 3 covers 21.60–27.00 m/s, clean only above 81 m/s.
⇒ **No speed stratum is clean for all three bands at once, and above ~21.6 m/s it is the 32–38 Hz
NEGATIVE CONTROL that order 3 contaminates.** Measured on the v ≥ 22.2 arm: **18/205 order hits on
18–22 Hz but 76/205 on the 32–38 control.** ⇒ **use a SYMMETRIC veto** — drop a window if any order
1–6 lands on **any** scored band's own measured line. **Per-band vetoes build different window sets
per band and turn a contrast into a comparison of two different sets.**

**🛑🛑 10. A VERIFIED ARTEFACT FOR A SUPERSEDED DESIGN IS *MORE* DANGEROUS THAN AN UNVERIFIED ONE.**
Everything about it looks correct — **including its assertion log.** And **a hash reported in a
transcript OUTLIVES the artefact it names**: a future session greps the transcript, finds a SHA256 with
every assertion passing, and has no way to tell the artefact is dead.

> ⇒ **WHEN A BUILD IS RE-CUT, THE SUPERSEDED HASHES MUST BE EXPLICITLY NAMED DEAD IN THE RECORD, NOT
> MERELY OMITTED FROM IT.**

**Stripping stale hashes from the docs is NECESSARY AND NOT SUFFICIENT** — omission is invisible, a
DEAD marker is not. **The instance:** a real, fully-verified V92 cut (**182/182 assertions, from-disk
verified**, image `b092bf19…`, rwd `630248a5…`) carried the **old rung map** and was superseded before
flight; **the only tell left in the transcript was a `6ABC` token buried in the old filename**, which
reads as a warning only to someone who already knows a swap happened. See §E for the full DEAD marker.
🛑 **AND WRITE THE DEAD HASH OUT IN FULL.** The search that will actually be run is a **paste of the
full 64-char string out of the transcript** — a truncated or prefix-only entry in the record returns
**nothing**, so the marker fails at exactly the moment it is needed. **Full string, next to the word
DEAD.**
⊕ **The BUILDER caught this itself and pushed back on the orchestrator's own proposed filename, which
had mischaracterised the superseded artefacts as a "dry run". They were a real cut — and that
distinction IS the hazard.** Same pattern as this session's other catches: the correction came from the
agent that owned the artefact, against the orchestrator's description of it.
⊕ **Corollary for the `SUPERSEDED-DO-NOT-FLASH-…` rename this kit already does:** the rename fixes the
**filesystem** and does nothing for the **transcript**. Both need doing.

### 🛑 THE `0x18F`-vs-`0x14A` SKEW — SETTLED AT SOURCE, 2026-08-10, AND THE MAGNITUDE IS NOT 10 ms

The long-standing *"`0x18F` is one frame (~10 ms) stale vs `0x14A`"* is **CONFIRMED**, but it was never
measured until now, it survived one wrong withdrawal and two wrong discriminators, and **its size is
~9.15 ms, not 10.0**.

**Mechanism [EVIDENCE, from the extractor].** `extract66()` appends a row on a **`0x14A`** frame while
holding `last18`, so **the order of messages inside `evt.can` decides everything**. `tm` is
`evt.logMonoTime` — **per-event, not per-message** — so co-logged frames share it exactly.
```python
for m in evt.can:
    if   addr == 0x18F: raw18_t.append(tm); last18 = (...)          # updates the hold
    elif addr == 0x14A: raw14_t.append(tm); rows.append((tm, ..., last18[0], ...))
```
**Measured over 51,691 co-logged events across r73/r75/r76** (`rlog-tools/v89_i1_can_order.py`, one
pass straight from the rlogs): **`0x14A` precedes `0x18F` on 91.28 %** (per route 91.61 / 90.52 /
91.71 — no route is special). ⇒ the row usually carries the **previous** `0x18F`.

🛑 **It is a MIXTURE, not a pure delay**, and nobody was accounting for the amplitude term:
`H(f) = 0.9128·e^{−j2πf·0.01} + 0.0872`

| f | pure 10 ms | **effective** | effective delay | \|H\| |
|---|---|---|---|---|
| 3.00 Hz | −10.80° | **−9.86°** | 9.13 ms | 0.999 |
| **7.79 Hz** | −28.04° | **−25.67°** | **9.15 ms** | 0.991 |
| 21.09 Hz | −75.92° | **−70.75°** | 9.32 ms | 0.938 |
| 23.00 Hz | −82.80° | **−77.45°** | 9.35 ms | **0.928** |

Applying a full 10 ms **over-corrects by +0.9° at 3 Hz, +2.4° at 7.79 Hz, +5.4° at 23 Hz.**

**🛑 HOW TO CORRECT IT — and the honest answer is that the caches CANNOT be fully corrected.**
Co-logged frames **share a `logMonoTime`**, so **no timestamp-based reconstruction can tell which was
processed first.** A `searchsorted(..., side="left") - 1` reconstruction always picks the previous
`0x18F` ⇒ it **reproduces the mixture rather than removing it** (predicted 8.72 % of rows at age ≈ 0;
**measured 0.000 % on all three routes** — the check that falsified it). Ranked:
- **flat 10 ms** — over-corrects by +2.4° at 7.79 Hz, +5.4° at 23 Hz;
- **`H(f)⁻¹`** — correct *on average*, but gains noise **1.078× at 23 Hz**;
- **`payload_time` via `searchsorted`** — exact for **which frame index the row holds** (correct to the
  frame on 91.28 % of rows), no better on the processing-order mixture, but it **does** handle dropouts
  (`payload_age > 20 ms` flags 0.7–0.9 % of rows, better than assuming them away).
  ⚠ **It is NOT a no-op even on r73**: it differs from the naive `raw18_t[i]` on **10.45 % of rows**
  (max 543 ms at a dropout), because r73's own shift census is a *mixture* — `0 ×54,771 · −1 ×6,367 ·
  −2 ×10 · … · −7 ×1`. **"r73 is shift 0" was the modal case, not the route.** Applying it to
  `v89_g1` tightened exposure 147 → 118 engaged windows (~20 % dropped, correctly) and **moved no
  conclusion**: γ² still refuses (0.385/0.465), the engaged lag is still negative (−7.25
  [−15.88, −1.00]), the manual arm still matches `H_A` (+8.50 [+6.00, +11.75]).
  ⚠ Its flat 9.939 ms age is computed *under* the `0x14A`-first assumption, so **it is not independent
  evidence of uniformity** — the flatness is partly built in;
- **only RE-EXTRACTION recording the `0x18F` timestamp per row is complete.**

⇒ **Residual on the existing caches is now BOUNDED rather than guessed: ≤2.4° and ≤1 % at 7.79 Hz;
≤5.4° and ~7 % at 23 Hz.** Below anything load-bearing in the current record.

🛑 **r76 STAYS IN.** Its row↔frame *index* shift really does drift (−1 → −4) and its frame counts
differ by 2 — **but that is bookkeeping, not timing.** Its payload *age* is flat at 9.93 ms and its
tails are the **cleanest of the three** (rows >12 ms: 4.88 / 4.64 / **4.61 %**). `payload_time` is
computed from timestamps, not indices, so it is immune. Excluding r76 would cost **10.95 engaged
minutes at the corpus's highest engaged fraction (86.6 %)** for a defect all three share.

🛑 **THREE DISCRIMINATORS THAT DO NOT WORK** — each was cited as decisive during this dispute:
`sstat` (>99.87 % constant; shifts −3…0 all match at 1.000000) · `raw18_b4 → sca` (only 7–16
transitions, and the row's byte-4 reconstruction ties to 5 decimals at every shift) · **"payload age
vs the most recent `0x18F`"**, which returns 0.000 ms by *assuming the row holds the newest frame* —
the very question at issue. ⊕ `len(raw18_t) − len(raw14_t)` is a valid **tripwire**, never a shift.

### 🛑 NAMED TRAP: **AN ADDRESS IS NOT A MODE.** Three instances, 2026-08-10.
**Never let a raw address stand in for a mode in a spec. Dereference `0xCBE74 + mode*4` and print the
mode number beside it.** Byte-verified map for the friction-comp LERP (`FUN_00036c12`, `gp-0x6b26`):

| mode | record | X array | **Y ARRAY** | V74 dosed ×1.5? | |
|---|---|---|---|---|---|
| 10 | `0xD2A44` | `0xD2A46` | `0xD2A4C` | YES | **DISENGAGED — V73's only edit, inert on this car** |
| 23 | `0xD6A54` | `0xD6A56` | `0xD6A5C` | YES | another variant's engaged column |
| **24** | `0xD6A64` | `0xD6A66` | **`0xD6A6C`** | **no — never touched, ever** | ★ **THIS CAR, MANUAL** |
| 25 | `0xD7A44` | `0xD7A46` | `0xD7A4C` | no | row-11 B branch |
| **26** | `0xD7A54` | `0xD7A56` | **`0xD7A5C`** | YES | ★ **THIS CAR, ENGAGED** |
| 27 | `0xD7A64` | `0xD7A66` | `0xD7A6C` | YES | row-11 B branch |

🛑 **The Y array is at RECORD BASE + 8.** Writing Y values at `base+2` lands them in the **X breakpoint
array**, which the LERP compares **unsigned** — e.g. `−29490` reads as `36046`, every speed falls below
`X[0]`, and the table returns a flat `Y[0]` at all speeds. **A silent, plausible-looking 5× increase at
highway.** Assert the X arrays unchanged in any builder that touches this row.

### 🛑 `0xCBE74` LINEAGE — the friction row has ZERO clean flights on a live column
Three separate overstatements were made about this cell in one session, in both directions. The
byte-verified truth:

| build | ×1.5 on a **live** column (24/26)? | on-car |
|---|---|---|
| V73 | **NO** — mode 10 only (disengaged) | flew clean — **says nothing about this lever** |
| **V74** | **YES** (13 engaged modes) | 🛑 **HARD FAULT, latched loss of assist** |
| **V75** | **YES** | 🛑 **HARD FAULT, latched** |
| V76 *(flown = `_v76_v38base_relu_damper`)* | **NO** — reverted by the V38 rebase | clean |
| V77 / V77B | YES | **never flew** |

⇒ **×1.5 on this car's live columns has flown exactly TWICE and both flights hard-faulted.**
🛑 **And it inverts the standing fault attribution:** the record blames `0xC407E` = 850, but **V73 carried
850 and flew clean.** V73→V74 is 64 differing runs (13 friction sites + 51 others) so the friction row
**cannot be pinned** — but the control meant to exonerate it is the thing that implicates it. ⇒ the row
moves from *exonerated* to *open suspect*, and no dose should fly until a probe measures the lane.
⚠ Two artefacts share the V76 number; **the lineage row's BASE column is the discriminator, and a glob
is not a check.**

⊕ **NAMED TRAP, four instances in one session: a COUNT or an INDEX RELATION is not a PHYSICAL FACT.**
The r76 "drift", the `gp-0x6752` writer census (a 6-byte-encoding blind spot read as "3 stores"), the
V86-vs-V89 rung map, and the payload-age metric. **Measure the physical quantity directly.**

`band_envelope` is **peak-to-peak scale**, not amplitude ·
**a ring-down through a bandpass MUST be quoted against a step control through the identical filter** ·
`rate_f` scale ~25 % low — **now pinned at 0.743–0.767 and scoped, see NAMED TRAP 1 above** ·
for N ≥ 5 only a phase-lock test establishes a harmonic.

---
Update it in place at every close-out; do not append new dated blocks (that is what made `CLAUDE.md`
unreadable). The narrative of how each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` — 🛑 **start with `RULE 3` at the top of that file: a
"CONFIRMED" result is about a LEVER, not about the car you are driving. Byte-check the current image
before reasoning from any recorded result.** 🛑 **Then `RULE 6` — a lever is only in force if the car
reads the TABLE you edited.** 🛑 **Then `RULE 7` — a lever is mode-proof, or it is a bet; this car is
`TVCA4`, modes 24/25 manual and 26/27 ENGAGED.** Then the latest handoff (the 2026-08-08 late one,
V83a's flight and V84), then
**the latest handoff is `docs/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md`** (V90's
flight, the six closed levers, and V91/V92), preceded by
`docs/HANDOFF-2026-08-10-v89-flew-and-the-mechanism-is-friction.md`, then
`docs/HANDOFF-2026-08-08-v81-flew-and-the-aggregator-reaches-the-motor.md`, then
`docs/HANDOFF-2026-08-07-v80-flew-the-damper-is-a-relay.md` (V80's flight and V81),
then `docs/HANDOFF-2026-08-07-v76-flew-and-the-relu-plan-inverts.md`, then
`docs/HANDOFF-2026-08-07-v76-v38base-and-the-friction-ceiling.md`, then
`docs/HANDOFF-2026-08-07-v74-fault-rlogs-the-damper-WAS-in-force.md`, then
`docs/HANDOFF-2026-08-06-v74-also-faulted-and-the-damper-was-not-in-force.md`, then
`docs/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md`, then
`docs/HANDOFF-2026-08-06-v74-flew-the-damper-is-real.md`, then
`docs/HANDOFF-2026-08-05-v72-flew-the-damper-was-never-in-force.md` (spec: `docs/V73-DESIGN.md`),
then `docs/HANDOFF-2026-08-04-both-confirmed-fixes-were-off-the-car.md`
(predecessors: `HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md`, then
`HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md`, then
`HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md`, then
`HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`, then `HANDOFF-2026-08-03-the-detector-was-always-there.md`, then
`HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md`, then
`HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md`, then
`HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md`, then
`HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md`, then
`HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md`, then
`HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md`, then
`HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`).

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-07 (night) — superseded by the 2026-08-08 headline above: V80 FLEW. IT DID NOT FAULT, AND IT PRODUCED THE WORST
GRINDING THIS CAR HAS EVER MADE. THE CAUSE IS ITS OWN DAMPER — A FLAT `FactorC` AT `k` = 4.16 TURNS THE
DAMPER INTO A NEAR-BANG-BANG COULOMB RELAY, AND THE BUILD'S NO-CLIP GATES WERE STRUCTURALLY BLIND TO IT.
**V81 — A 126-BYTE REVERT FROM THE FLOWN V75, WITH BOTH LEGS OF THE FAULT MECHANISM REMOVED — IS BUILT,
VERIFIED AND UNFLASHED. THE FLASH DECISION IS THE OPERATOR'S.**

**Route `75604b0a432fdc89|00000066--276b942769`, 15 segments, 901.71 s, 89,997 frames @ 100.0 Hz,
downloaded to `analysis-2020accord/rlogs/`. Engaged (`carControl.latActive`) 30,260 frames = 302.6 s =
33.62%**, 9 engaged episodes ≥ 2 s, speed −0.09 … 31.34 m/s (112.8 km/h).
**Operator's verdict: the WORST grinding the car has ever produced** — loud, strong, felt through the
whole car, ~90% of LKAS-engaged time, at both low and high speed, causing noticeable vehicle instability.
🛑 **V80 DID NOT FAULT. This is a STABILITY failure, not a fault-class failure.** `0x1AB` DTC-active:
**0 transitions, 0.000% duty**, 0 × `0x7FFF` sentinels; `STEER_STATUS` histogram {0: 63,861, 3: 26,136},
same shape as route 65. [EVIDENCE]
⊕ `build_v80_tva.py`'s own header says verbatim *"GATE 2 (magnitude AND phase) is NOT satisfied by
argument. **V80 IS NOT CLEARED TO FLY.**"* It was flown anyway.

### ★★★★★ ROOT CAUSE — V80's damper is a near-bang-bang Coulomb relay

Damper dose vs motor rate at **5 km/h**, recomputed by the orchestrator from the shipped plain images,
records dereferenced through their pointer arrays (`FactorC 0xC9E9C`, `FactorE 0xC9F84`,
`ceiling 0xC77A0`, `friction 0xCBE74`), **mode 26** (this car is `TVCA4`: 26 engaged / 24 manual):

| rate (ct) | 20 | 40 | 99 | **119** | 150 | 255 | 530 | 1000 | 1941 | 4000 |
|---|---|---|---|---|---|---|---|---|---|---|
| ≈ °/s (4.7121 ct per °/s) | 4 | 8 | 21 | **25** | 32 | 54 | 112 | 212 | 412 | 849 |
| **V75** | 12 | 44 | 137 | 169 | 218 | 297 | 297 | 297 | 297 | 512 |
| **V80** | 82 | 166 | 412 | **495** | 495 | 495 | 496 | 498 | 501 | 512 |

⇒ **V80 emits a constant 495 counts — 3.4% variation across a 34× rate range — at 97% of the 512 ceiling,
above only ~25 °/s, at EVERY speed** (FactorC is flat). V75 plateaus at 297 (58% of ceiling) and only
above 54 °/s. [EVIDENCE, orchestrator's own Python LE read of the flashed images]

🛑🛑 **WHY THE BUILD'S OWN GATES WERE BLIND.** Every no-clip guard tests `product > ceiling`. V80's
supremum is `(566*927)>>10 = 512` = the ceiling **exactly**, so it clips **0.00%** and passes. The flat
FactorC did not remove the relay — it **moved** it from the ceiling clamp to **FactorE's own knee**,
**17 counts under the rail** (slope drops ~1200× at `X[1] = 119`). **"Does not clip" and "is not a relay"
are different statements, and only the first was ever checked.** [EVIDENCE]

**Describing function** `N(R)` (fundamental-harmonic gain of `force = −sign(rate)·M(|rate|)`; constant
`N` = viscous = stabilising, `N` rising as amplitude falls = relay = limit-cycle generator):

| R (ct) | 25 | 50 | **99** | 150 | 250 | 500 | 1000 |
|---|---|---|---|---|---|---|---|
| V75 @creep | 0.580 | 1.065 | **1.319** | 1.410 | 1.317 | 0.734 | 0.375 |
| V80 @creep | 4.007 | 4.087 | **4.127** | 3.698 | 2.421 | 1.250 | 0.632 |
| V80/V75 @60 km/h | 17.7× | 9.4× | **7.6×** | 6.4× | 4.5× | 4.1× | — |

Relay-ness index `N(50)/N(500)`: **V75 = 1.45× (creep) / 1.43× (60 km/h); V80 = 3.27× at both.**
Small-signal loop gain `k`: **V75 1.5798 · V76 1.3866 · V74 0.5799 · V80 4.1597** — 2.63× V75, 3.00× V76,
extrapolating 2.6× beyond the last measured point. [EVIDENCE]

★★★★ **THE MEASUREMENT THAT SETTLES IT — both builds' own cave probes.**

| | damper `\|gp-0x6bd0\| ≥ 448 counts`, engaged |
|---|---|
| **V75** (route `5e`, 28,317 pre-fault frames) | **0.000%** — never above 128 counts *at all* above 40 km/h |
| **V80** (route `66`) | **19.4%** overall · 32.7% above 15 m/s · **71% through the worst 29 s event** |

V75's engaged level census: L0 (dead) 56.8% · L1 (1–127) 25.3% · L2 (128–287) 9.3% · L3 (288–447) 8.6% ·
**L4 (≥448) 0.000%.** **V75's damper never entered its saturated regime. V80's lives there.**
[EVIDENCE — the single cleanest statement of the root cause]

★★ **THE DAMPER'S NET SIGN IS RESOLVED, AND IT IS DISSIPATIVE.** `gp-0x6abe` is the **signed twin of
`gp-0x6ac0`** (both filtered from `gp-0x4f50` in `FUN_00041464`; `0x41b56`:
`gp-0x6abe = (short)(uVar16>>10)` signed vs `gp-0x6ac0 = |uVar16|>>10` rectified). Sign applied at
`0x3469E`–`0x346A2` (`cmp r0,r11 / ble / subr r0,r8`) ⇒ `sign(gp-0x6bd0) = −sign(motor rate)`.
**Path 2 through the PID is NON-INVERTING**: the Stage-2 subtraction in `FUN_00038148` and the PID's
`err = setpoint − feedback` cancel, and the two `polarity(gp-0x6752)` multiplications cancel regardless of
value ⇒ `(−P)(+1)(−1)(+P) = P² = +1`. `FUN_00037fe6` is a genuine unity adder (all 7 weights at
`tp+0x74ad..0x74b3` read `01`). Path 1 (bare) and Path 2 both enter `FUN_0003aa2c` with unity weight and
**REINFORCE** ⇒ **dissipative by construction at `gp-0x6b94`, high confidence.** [EVIDENCE]
⚠ **STILL OPEN: the `gp-0x6b94` → motor forward hop.** New node: **`gp-0x6ace`** = the governor-clamped
form of `gp-0x6b94` (written by `FUN_0004503c` via `FUN_00049a90`); its only readers are `FUN_000456a4` /
`FUN_00045a20`, both hard-shutdown monitors. Both of `FUN_00042af8`'s documented external inputs are
RULED OUT: `gp-0x6b08` is self-referential; `gp-0x6afe`'s sole writer `FUN_00042ac6` is fed by
`FUN_00026c80`, an independent Sensor-B lane that runs BEFORE `FUN_0003aa2c` in the same tick.
**A missing link, not a discovered inversion.**

### WHAT ROUTE 66 ACTUALLY SHOWS

★★★ **(a) A broadband HF floor lift — the dominant effect.** Median engaged periodogram, **V80 minus
V76**, matched 10–40 km/h stratum:
```
 Hz    7.8   12.1   18.0   19.9   21.9   23.8   26.2   28.1   30.1   34.0   35.9   39.9   44.2   48.1
dB   -6.03  -0.20  +0.05  -0.72  -0.58  +2.44  +3.75  +5.27  +5.70  +9.22 +10.41  +8.15  +8.49 +11.47
```
**Grind #1's own band is UNCHANGED; the ratchet is 6 dB DOWN; everything above ~24 Hz lifts by a flat,
prominence-neutral offset.** Cell-stratified V80/V76 = **2.09× [1.46, 2.70]** on the 30–49 Hz floor, and a
pre-declared **32–38 Hz negative control fails identically (2.035)** ⇒ the whole HF region moved together.
**This is NOT "grind #2 got worse".** [EVIDENCE]
**Falsifiers, all cell-stratified V80/V76:** torsion bar 30–49 Hz **2.09 [1.40, 2.71]** · steering angle
30–49 Hz (a **different CAN message**, `0x14A`) **1.60 [1.26, 2.03]** · **IMU vertical 20–49 Hz 1.07
[0.92, 1.33] ⇒ NOT a rougher road** · openpilot `0x0E4` command 1.25 [1.12, 1.44] · 1–4 Hz driver-input
exposure check 1.14 [0.88, 1.47].
★ **FFT-FREE CONFIRMATION** — sample-to-sample sign reversals, immune to spectral leakage. Engaged windows
containing ≥1 reversal of `|step| > 300` counts: **V75 3.0% · V74 22.0% · V76 22.0% · V80 73.0%**. At
`|step| > 800`: **V75 0.0% · V74 0.5% · V76 0.6% · V80 23.3%.** Exactly the near-Nyquist chatter a
bang-bang relay injects. [EVIDENCE]

★★★★ **(b) A sustained ~27.4 Hz limit cycle that NO other build produces.** Engaged windows with 26–31 Hz
envelope > 1000 counts: **V74 0/413 · V76 0/328 · V75 0/133 · V80 32/215 (14.9%)**, in segments 8, 12, 13,
at 54–104 km/h.
**THE WORST EVENT — segment 8, route-global t ≈ 500.9–530.3 s, 99–104 km/h, ~30 s unbroken.**
Orchestrator's own Welch spectrum over the window: **27.56 Hz at ×92 over the in-band median**; manual at
the same speed peaks at ×3.1. Torsion bar **6,830 counts p-p**, σ = 1,059. At 10.24 s resolution the line
is **27.344 Hz, prominence 292, Q ≈ 140.** Steering angle p-p **1.92°**, angle rate p-p 234 °/s. Damper
`≥448` duty through the event: **71%**. `sstat`=0, `sca`=1, `cc_lat`=1 throughout — **no fault, no
lockout.** Envelope goes 50 → 3000+ counts within ~1.5 s of engagement and collapses to ~150 the instant
LKAS disengages.
**Relay tests:** amplitude clamped ±15% over 30 s ✅ · crest factor **1.838** (sine 1.414, square 1.000) =
near-sinusoidal limit cycle ✅ · **NOT wheel order 2**: measured `df/dv` = **−0.131 [−0.231, −0.016]** Hz
per m/s where order 2 demands **+0.961**; at 54–62 km/h the line sits at 28.7–30.1 Hz where order 2 would
be 14.4–16.7 Hz ❌.
Speed-tracking check (engaged, 26–30 Hz peak): 1–5 m/s → 30.3 Hz ×2.1 · 10–15 → 26.2 Hz ×1.6 · 15–20 →
29.1 Hz ×10.3 · **24–32 → 27.6 Hz ×94.9.** **Frequency pinned across a 20× speed range** (wheel order 1
would sweep 1.5 → 13.7 Hz), **amplitude exploding with speed.**
⚠ **The mode is NOT new to V80 — it is the kit's ~28 Hz line, amplified.** V74's strongest windows
29.4–29.5 Hz, e = 450–531 ct @106–114 km/h; V76's 28.3–28.9 Hz, e = 815–920 ct; V80's 26.8–28.2 Hz,
**e = 1759–2686 ct**. V80 raised it ~2.7×, dropped f0 by 1–2 Hz, and turned intermittent episodes into a
sustained limit cycle. [BELIEF] the f0 drop with loop gain is what a control-loop mode does and a fixed
mechanical resonance does not.
⚠ **Aliasing (common mode):** fs ≈ 100.0 Hz, so 27.344 Hz is indistinguishable from 72.66/127.34 Hz.
Identical on all four routes ⇒ cannot affect the contrast, only the identification.
⚠ **Command caveat:** openpilot's own `0x0E4` carries 25–30 Hz at rms 45.8 ct, correlated +0.93 at lag 0
with the bar; bar/command ratio at 27 Hz is **15.8×**. [BELIEF] an echo, not a cause — the EPS LKAS lane
is a ~1–5 Hz low-pass on standing EVIDENCE, so a 27 Hz command component cannot reach the motor that way.
**Settling it needs a phase-resolved coherence, not the lag-0 correlation that was run.**

★★ **(c) Damper-saturation dose–response** (engaged 2.56 s windows), 17–30 Hz band power binned by the
fraction of the window the damper spent ≥448 counts:
`0–5% → 1.1e3 · 5–20% → 9.2e3 · 20–40% → 3.0e4 · 40–60% → 2.1e5 · 60–80% → 1.4e6.`
**Three orders of magnitude, monotone.** ⚠ speed and saturation duty are mutually confounded ⇒
**[EVIDENCE] on the association, [BELIEF] on causal direction.**

★★ **(d) "~90% of engaged time" — quantified, scored on the band that MOVED (30–49 Hz).** Thresholds taken
from V76's own engaged distribution (so V76 reads 50/25/10% by construction):

| threshold | V74 | V76 | V75 | **V80** |
|---|---|---|---|---|
| V76 p50 (85.7 ct) | 42.9% | 50.0% | 42.9% | **79.5% [70.3, 87.7]** |
| V76 p75 (128.1 ct) | 21.1% | 25.0% | 11.3% | **75.3% [66.2, 83.9]** |
| V76 p90 (203.5 ct) | 6.8% | 10.1% | 4.5% | **64.7% [52.8, 74.9]** |

Per stratum at V76-p50: creep 37.1% · **10–40 km/h 93.9%** · **40–80 km/h 80.0%** · **>80 km/h 100%.**
Independently, on the 17–30 Hz p-p criterion: **89.1% of engaged windows ≥100 ct p-p**, and **17.1% of
engaged time >1,500 ct p-p — an amplitude reached in ZERO of 432 manual windows.** Engagement test: median
per-edge ratio **×2476** (18–22 Hz) within 4 s of the `latActive` rising edge, 6/7 edges up; falling edges
×0.34. **[EVIDENCE] engagement-conditional, switches on within seconds.**

### 🛑🛑 TWO RETRACTIONS THE RECORD NOW CARRIES

🛑 **(1) GRIND #1 IS INERT TO THE DAMPER DOSE.** Four-point ladder on ONE instrument
(`rlog-tools/compare_v75_v76_v80_grind.py`, NFFT 256/hop 128, p99 analytic band envelope, ~10.2 s
bootstrap blocks nested inside engagement runs), ratio to V76:

| band | V74 k=0.58 | V76 k=1.39 | V75 k=1.58 | V80 k=4.16 |
|---|---|---|---|---|
| **18–22 grind #1** | 1.166 [0.98,1.41] | 1.000 ref | 0.735 [0.50,1.22] | 0.835 [0.64,1.07] |
| 6–9 micro-ratchet | 0.818 [0.70,1.09] | 1.000 ref | 0.821 [0.66,1.09] | **0.418 [0.33,0.61]** |
| 26–31 | 0.823 [0.72,1.02] | 1.000 ref | 0.865 [0.71,1.20] | 1.197 [0.80,1.52] |
| **40–49 grind #2** | 0.810 [0.70,0.97] | 1.000 ref | 0.961 [0.77,1.24] | **2.017 [1.32,2.83]** |
| **30–49 HF floor** | 0.820 [0.73,1.01] | 1.000 ref | 0.953 [0.81,1.26] | **2.091 [1.46,2.70]** |
| **32–38 neg control** | 0.865 [0.76,1.03] | 1.000 ref | 0.959 [0.82,1.22] | **2.035 [1.45,2.57]** |

Split-half nulls (300 halvings, per route): 18–22 Hz ≈ **[0.63, 1.60]**. **Every grind-#1 point sits inside
its own noise floor across k = 0.58 → 4.16.** ⇒ 🛑 **V80 did NOT "overshoot an optimum" on grind #1 —
grind #1 never responded to `k` at all.** On this instrument V75's "no grind #1" vs V76's "still grind #1"
is a **creep-EXPOSURE difference** (V76's creep windows carry 3.4× V75's steering effort), not a dose
difference. **This retracts the "grind #1 is DOSE-LIMITED" verdict in the superseded headline below.**
[EVIDENCE]
★ The operationally useful statement: **something switches on between `k` = 1.58 and 4.16 that costs 2×
broadband HF plus a limit cycle. Where in that gap it switches on is UNMEASURED.**
🛑 **CORRECTED 2026-08-07 by the orchestrator:** an earlier draft of this line read *"`k` ∈ [1.39, 1.58]
buys most of the ratchet benefit at zero HF cost"* — **that clause is withdrawn.** It contradicts the very
next paragraph: 6–9 Hz is FLAT from `k` = 0.58 to 1.58, so that bracket buys **no measurable ratchet
benefit over a LOWER dose**. The only ratchet gain in the corpus is at `k` = 4.16, and it is the point that
also carries the HF penalty. **There is no measured "free ratchet benefit" bracket.**
★ **The micro-ratchet's own reading, stated precisely:** on this ladder (ratio to V76, split-half null
≈ **[0.66, 1.45]**) 6–9 Hz is **FLAT across `k` = 0.58 → 1.58** — V74 0.818 [0.70, 1.09], V75 0.821
[0.66, 1.09], both **inside** the null ⇒ the earlier **"dose-independent" verdict was ACCURATE over the
range then available, and is not refuted — its DOMAIN is bounded above.** It improves significantly **only
at `k` = 4.16**, the first point outside the null: **0.418 [0.33, 0.61]** [EVIDENCE]. ⇒ **V80 bought a real
ratchet gain and paid for it with the HF floor.**
⚠ **Calling the four points MONOTONE is [BELIEF], not EVIDENCE** — three of the four are inside the null,
so only the top point carries it.

🛑 **(2) V80's CREEP NUMBERS ARE AN EXPOSURE ARTEFACT — do not read them.** V80's engaged creep windows
have median sustained effort **173 counts** and median `|angle rate|` **1.3 °/s**, against V74/V76/V75's
685/588/1113 counts and 33/33/48 °/s. **Zero matched cells.** An earlier claim this session that "V80 is
3–30× quieter than V76 at creep" is **RETRACTED — the driver was not turning the wheel.** Also
unresolvable: whether V80's near-zero creep angle rate is itself an *effect* of a 412-count-at-all-speeds
damper making the wheel feel sticky.
⚠ Also not comparable: the **>80 km/h** stratum — V75 never exceeded 65 km/h and V80 has **1 engagement
run / 3 blocks** there (the limit-cycle event itself). **The 10–40 and 40–80 km/h strata are well matched
and carry the load.**

### ★★★★★ THE FAULT MECHANISM — CONFIRMED IN GHIDRA, AND THE `0xC63A0` PREMISE IS REFUTED

**`0xC407E` (= `tp+0x507E`; anchored `0xBF000+0x507E`, the off-by-0x1000 trap avoided) is the whole story.**
- **Monitor `FUN_00036d74`** — orchestrator's own decompile: `fVar3 = gp-0x6b26 * 0.0009765625`; if
  `|fVar3| > *(float*)(tp+0x5004)` → `FUN_000462e6(0x39bc,…)` → `FUN_00016de6(0x1d,…)` = **DTC 0x1d,
  latched total loss of assist**. `0xC4004` bytes `0000003f` = f32 **0.5** ⇒ trip at **512 counts**.
  Symmetric, **no debounce.** Called from the 1 kHz task `FUN_0002214a` @`0x2290A`; the caller's
  `gp-0x67fa ∈ {4,5,11}` gate is the SAME gate that wraps the producer's call ⇒ unconditional *relative to
  the producer* — no path writes `gp-0x6b26` without the monitor checking it that cycle.
- **Sole writer of `gp-0x6b26`**: `st.h r6,-0x6b26[gp]` @`0x36CF0` in `FUN_00036c12` — **exactly one writer
  image-wide**, confirmed by Ghidra + a raw Python LE scan covering disp16, the 6-byte disp23 form, LE32
  address literals and movhi/movea pairs (**0 hits on all three alternatives**). The stored value is
  already clamped to ±`0xC407E` (clamp arms at `0x36CCC`–`0x36CE2`).
- **`0xC407E` itself**: 0 writers, 3 readers, all `ld.h` SIGNED, **all three inside `FUN_00036c12`** ⇒ the
  cell's entire blast radius is one lane's clamp magnitude.
- **Margins**: stock / V38 / V76 / V78 / V79 / V80 **511 → +1, UNTRIPPABLE** · V73 / V74 / V75 **850 →
  −338, TRIPPABLE** · **V81 511 → +1, UNTRIPPABLE.**
⇒ **At 511 the monitor is untrippable BY CONSTRUCTION** — the only value that ever reaches the cell is
already clamped below the trip, whatever the plant, mode or lever set does. [EVIDENCE]

🛑🛑 **THE `0xC63A0` PREMISE IS REFUTED.** The standing operator directive *"do not double `0xC63A0`, that
is what was causing hard faults"* rests on a **false premise**. `0xC63A0` (= `tp+0x73A0`) has **exactly one
reader**, `ld.hu` @`0x381AC`, **0 writers, 0 disp23 hits**. Its only reader `FUN_00038148` writes exactly
two cells — `gp-0x374c` (accumulator) and `gp-0x6b70` (output) — and **never** `gp-0x6b26`, `gp-0x6c2c` or
`gp-0x6a5e`. `gp-0x6c2c`'s two writers are both inside `FUN_00041464` (`0x4184E`, `0x41AC2`).
**There is NO firmware data path from `0xC63A0` to the faulting monitor.** A *physical* path exists
(aggregator → motor → plant → motor rate → `gp-0x6c2c`) and is irrelevant, because **the clamp acts before
the store.** [EVIDENCE]
⊕ `build_v80_tva.assert_c63a0_block` still hard-asserts 1024 with the old rationale — **the comment there
is now known-wrong** and should be corrected. (V80 is a different lineage, so nothing conflicts.)

★ **V75's fault was NOT the damper.** In the last 5 s before the trip the damper was identically **zero for
4.98 s** and reached only level 2 (128–288) **19 ms** before the fault. The car was stationary T−5→T−1 s
then launched (0 → 7.6 km/h). Column rate reversed sign twice in the final 150 ms (+55, +31, −38 °/s);
**peak jerk 7,154 °/s² = 4.3× that route's own p99.9 (1,664)** and the route maximum. Exactly what the
`0xC407E` mechanism predicts. [EVIDENCE]
⚠ **[BELIEF, not EVIDENCE]** "`0xC407E` = 850 caused BOTH faults" — **the DTC number was never confirmed
on-car.** What is EVIDENCE: the mechanism exists, is single-frame, is mode-proof, and the build history
lines up exactly. **V81 closes it whether or not it fired.**

### 🛑 THE V38 REBASE SILENTLY REVERTED ~~THREE~~ **SEVEN** THINGS

🛑 **CORRECTED 2026-08-08 (late): this heading read "THREE LEVERS" and the count has now been walked to
SEVEN.** The record named `0xC63A0`, `0xC407E` and friction ×1.5 (the last two **declared**); `0xC62EA`,
the V57 decouple triplet and `0x454FE` were added later; and a **SEVENTH has never been logged anywhere
until now — `gain_A` rec0/rec1.**

Orchestrator's own byte read across the lineage:

| lever | V62 · V68 · **V74 · V75** | **V76 · V78 · V79 · V80** |
|---|---|---|
| `0x2A1F0` reader disp | `0x7CD0` → **decoupled** `0xC6CD0` = 3564 | `0x746C` → **shared** `0xC646C` = 3564 |
| `0xC646C` shared sensor scale | stock **891** | **3564 (4×)** |
| `0xC62EA` low-speed steer lockout | **0** (removed) | **320** (restored) |
| `0xC63A0` Path-2 damper weight | **2048** | 1024 |
| `0x454FE` V42 macro-ratchet fix | `0xB5` | `0xBA` — 🛑 **the SECOND silent loss of this byte** (V76/V78/V79); **V80 restored it to `0xB5`** |
| 🆕 **`gain_A` rec0** `0xC6A72`–`0xC6A78` | **512** | **Honda's `3072 / 2434 / 2048`** |
| 🆕 **`gain_A` rec1** `0xC6A86`–`0xC6A8C` | **512** | **Honda's `3072 / 2488 / 1536`** |
| `0xC407E` friction-lane clamp *(declared)* | **850** — ⚠ **V73/V74/V75 only**; V62/V68 carry 511 | **511** |
| friction row, 14 sites *(declared)* | **×1.5** — ⚠ **V73/V74/V75 only**; V62/V68 carry Honda's row | **stock** |

🛑 **V80 vs V75 was NEVER a single-variable damper comparison — and the confound count is FIVE, not four.**
The **silent** ones are `0xC63A0`, `0xC62EA`, the V57 decouple triplet, `0x454FE`, and now **`gain_A`
rec0/rec1**; `0xC407E` and the friction row were declared. V76 was cut from V38, which predates V57's
decouple, and nothing in the V76 → V78 → V79 → V80 chain re-applies it.
⇒ **Any conclusion drawn from a V80-vs-V75 (or V76-vs-V75) contrast must name all five.** [EVIDENCE]

**`0xC646C` — full reader map, and why it is NOT the 27 Hz driver.** Exactly **6 static readers, 0 stores,
0 disp23 hits, 0 LE32-pointer hits** (three independent methods: Ghidra `search_instructions`, a fresh raw
Python LE scan of both encodings, fresh decompiles). **Q15 dimensionless multiplicative scale** —
`(x * cal) >> 0xf` at every site; 3564 = 4×891 exactly.

| # | addr | function | role |
|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` | **LKAS arbitration / CAN-setpoint→command — the one V57 decoupled** |
| 2 | `0x2a904` | *(orphan)* | **DEAD** — no function, no xrefs |
| 3 | `0x2b656` | `FUN_0002b62c` | **RECLASSIFIED**: output `gp-0x6af0` reaches only a private 2-function mode-flag debounce loop (`gp-0x677d` has exactly 2 static refs image-wide) + a UDS packer with 0 static callers. **No torque path.** |
| 4 | `0x2c488` | `FUN_0002c478` | output `gp-0x6b10` has **3 refs, all `st.h`, ZERO loads** — proven dead |
| 5 | `0x36686` | `FUN_00036682` | **the only one reaching the motor** — multiplies RAW `gp-0x4f60`, adds into `FUN_0003aa2c` → governor → `gp-0x6b98` |
| 6 | `0x3684a` | `FUN_00036828` | modulates #5's hysteresis half-band via `gp-0x6b44` (2nd-order) |

**Reader #5 cannot drive a 27 Hz limit cycle — a BANDWIDTH argument.** Its output passes an IIR with
`alpha = tp+0x73d2 = 6` ⇒ `6/1024 = 0.00586`, corner **≈0.93 Hz, ≈−26.6 dB at 21 Hz.** [EVIDENCE]
(This also settles the prior "6 vs 14" open discrepancy **in favour of 6**.)
**Reachability screen of reader #5's pre-filter `±0x200` clamp**, whose trigger on `|gp-0x4f60|` drops from
~18,829 counts at stock to **~4,707 at 4×** — never previously run against a V76-lineage log: on route 66,
`|bar|` engaged p50 174 · p90 1,424 · p99 3,346 · p99.9 3,712 · **max 3,849**; `|bar| ≥ 4707` fired
**0 / 89,997 frames**; worst event max 3,437. ⇒ **It did not bind.** ⚠ **Margin only 22%**, and the CAN
sensor's count scale is not proven identical to `gp-0x4f60`'s internal scale ⇒ **"did not fire on this
drive", NOT "cannot fire".** Worth a probe.
⇒ **NET: the shared-cell 4× is a real, uncosted regression in headroom that nobody signed off on, but it is
NOT the 27 Hz driver.** **V81 removes the exposure for free by being cut from the V75 base.**
✅ `0xC6CD0` = `0xFFFF` on V76/V78/V80 is **provably inert** — 0 instructions read `tp+0x7cd0` anywhere.

### 🛑 TOOLING / HYGIENE FINDINGS FROM THIS SESSION

1. 🛑 **`rlog-tools/decode_v76_probe.py` is the WRONG decoder for route 65** and will give a confident wrong
   answer. It documents the **superseded** V74-base V76 (`V76-V74BASE-GATE-FB-ARM5244`), whose bit7 is
   `gp-0x6bd0 != 0` — the damper, not the friction lane. The build that flew route 65 is
   `V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd`; its extractor is
   `analysis-2020accord/v76flight_extract.py` → `analysis-2020accord/_cache_r65_records.pkl`
   (**not** `_cache_r65/`).
2. 🛑 **Two `_v76*plain_image.bin` on disk.** `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` is the
   abandoned V74-base candidate and still carries the V57 decouple; a first `Glob` returns it FIRST. The
   V78/V80 ancestor is `_v76_v38base_relu_damper_plain_image.bin`. The `.rwd` was correctly renamed
   `SUPERSEDED-…`; **the stale plain-image snapshot still reads as current.**
3. **`build_v75_tva.py`'s default lever set does NOT produce the flown V75** — you must pass
   `ACCORD_V75_LEVERS=CY0,EX1`. The default (`CY0` only) writes the never-flown `…CY0.566…` artefacts. No
   overwrite hazard (`lever_token()` is in both filenames), but the comment at line 269 is easy to misread.
   **The flown V75 is the `EX1.200` cut, dose 137, k = 1.5798.**
4. 🛑 **V74's first (clean, symptom-measurement) flight — route `5d`, 17 segments — is MISSING from
   `analysis-2020accord/rlogs/`.** Only the extracted `_cache_r5d/*.npz` + `.pkl` survive, while
   `analysis-2020accord/extract_r5d_cache.py` (977 lines) is its canonical extractor and
   `docs/BUILD-LINEAGE.md` leans on that cache. **Every downstream V74 conclusion in this file runs
   against the cache, not the raw log — and the cache cannot be re-cut or re-scored.** Re-confirmed
   2026-08-08 (late). ⇒ **Recover or re-download it** (NEXT item 9).
5. **V80's probe cannot distinguish V80 from V78/V79** — byte-identical cave, identical trip rates below
   80 km/h. Build identity rests on the `.rwd` filename plus the absolute exclusion of V76-V38BASE (13,183
   frames set bit6 with bit5 clear, structurally impossible on that cave). Route 66's `0x14A` byte4 took
   only {`0x0F`, `0x1F`, `0x5F`, `0xDF`}; bit5 0/89,997; bit3 positive control **100.000%**.
6. The bash/PowerShell default `python` (anaconda base) has a **broken numpy DLL.** Either prepend
   `C:\Users\dudei\anaconda3\Library\bin` to `PATH` or use
   `C:/Users/dudei/anaconda3/envs/bin_decompile/python.exe` (which also has `capnp`).

### ⇒ ★★★ NEXT

1. **Fly V84.** 🛑 **Flash decision is the operator's; the file and the bus must be named back.** Its
   damper surface is byte-identical to V67/V68, so grind #1 is an interpolation onto a measured point.
   **Fly it with creep, mid-speed and highway engaged exposure** so the highway grind — which V84 does
   **not** claim to fix — is scored rather than assumed.
2. **Read the V84 probe first, then the spectra.** `b3` is the positive control; if `b3` is not ~100%,
   nothing else in the readout is interpretable (the V64/V68 lesson).
3. ~~Bracket the switch-on point in `k` ∈ (1.58, 4.16]~~ — **DEPRIORITISED.** The `k` dose axis is now
   falsified for the 26–31 Hz ring (headline §1) and grind #1 was already inert to `k`. The `k` ladder's
   one surviving claim is the **micro-ratchet gain at `k` = 4.16**, and it comes bundled with the HF floor.
4. **Settle the 27 Hz command-vs-plant question** with a phase-resolved coherence on `sendcan` `0x0E4` vs
   the torsion bar. This is now the *only* live route to the ring, the damper having been falsified.
5. **Probe the friction lane at 320/352/416** if V81 variant B is ever wanted — converts the bet into a
   measurement for ~30 cave bytes.
6. **Correct `build_v80_tva.assert_c63a0_block`'s now-known-wrong rationale comment.**
7. 🛑 **Correct the `0xC61B2`/`0xC61B4` label in the build scripts** — `build_v83a_tva.py:359-360` and
   `build_v84_tva.py:544-545` call them *"pre-gain deadband arm"*. **They are not.** See the correction in
   *Signal-identity corrections of record*. Comment-only; changes no byte.
8. **Re-run reader #5's `±0x200` clamp screen** with a proven `gp-0x4f60` scale — the 22% margin is thin.
9. 🛑 **Recover or re-download route `5d`'s raw rlogs** (V74's clean symptom-measurement flight, 17
   segments) — they are **missing from `analysis-2020accord/rlogs/`** while `extract_r5d_cache.py`
   (977 lines) is its canonical extractor and `BUILD-LINEAGE.md` leans on that cache. Every V74 conclusion
   runs against the cache, not the log.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-07 (evening): V76 FLEW AND FLEW CLEAN. GRIND #1 IS ~~DOSE-LIMITED~~
AND THE MICRO-RATCHET IS **DOSE-INDEPENDENT** — a resolved split. THE OPERATOR'S "150% OF V75'S 5 mph
DOSE" IS RIGHT AND COSTS **ONE u16 CELL** (**V78**); THE "BOTH FACTORS AS ReLUs + BIGGER TABLES" HALF
**INVERTS** — 4 points was never the obstacle, and a literal ReLU FactorC RE-CREATES THE COULOMB RELAY
AT THE CEILING CLAMP.**

**Route `75604b0a432fdc89_00000065--ae43aa0f27`, segs 0–10, 636.30 s / 63,477 frames, 0–96.7 km/h,
engaged 450.98 s (70.87%). ZERO DTC transitions, zero `0x7FFF` sentinels, no frame-rate collapse.**
Build identity settled **four independent ways** (bits 6/5 structurally unreachable: 0/63,477 · 8-value
legal payload set: 0 violations · V75's thermometer invariant violated on 70.0% ⇒ not V75 · the
superseded V76's structurally-zero bit3 reads 99.926% here).

★★ **THE FRICTION-MARGIN NULL IS REAL, NOT AN UNARMED GATE.** bit7 (`|gp-0x6b26| > 448`) fired
**0 / 63,477** with the positive control (bit3) at 99.93% in the same frames, across every speed band
and both arms. ⚠ **Weakens but does not refute** the V73-interlock story — it bounds `gp-0x6c2c` from
one side only; the physical scale stays OPEN.
★ **Mode lag measured directly: median 994.9 ms [830.0, 1575.0]**, n=6 episodes — **2.5× shorter than
the ~2.5 s in prior handoffs.** Treat this as the better number; n=6 on one route does not prove the
older figure measured the same thing.

★★★★ **THE DOSE-RESPONSE SPLIT** (fit over V72/V73 k=0, V74 0.5799, V75 1.5798, V76 1.3866; creep,
speed-stratified, **episode**-bootstrapped; V76 sits *between* V74 and V75 so the model made a
falsifiable point prediction):
| band | V76 observed | monotone prediction | slope b [95% CI] | verdict |
|---|---|---|---|---|
| ratchet 6–9 Hz | 3.877 [3.098, 5.161] | 3.906 (−0.06 dB) | **−0.094 [−0.291, +0.098]** | **DOSE-INDEPENDENT** |
| grind #1 18–22 Hz | 1.577 [1.380, 1.831] | 1.613 (−0.19 dB) | **−0.614 [−0.810, −0.416]** | ~~DOSE-LIMITED~~ 🛑 **RETRACTED 2026-08-07 (night)** |
🛑🛑 **THE GRIND-#1 "DOSE-LIMITED" VERDICT IS RETRACTED — see the current headline, retraction (1).** On a
four-point ladder run on ONE instrument across `k` = 0.58 → 4.16, **every grind-#1 point sits inside its own
split-half noise floor [0.63, 1.60]**. What this three-point fit read as a dose slope is a **creep-EXPOSURE
difference** between the routes (V76's creep windows carry 3.4× V75's steering effort).
✅ **THE 6–9 Hz DOSE-INDEPENDENT LEG IS *NOT* REFUTED — its DOMAIN is now bounded above.** On the four-build
ladder (ratio to V76, split-half null ≈ **[0.66, 1.45]**) the micro-ratchet is **FLAT across `k` = 0.58 →
1.58** — V74 **0.818 [0.70, 1.09]**, V75 **0.821 [0.66, 1.09]**, both inside the null ⇒ **"dose-independent"
was ACCURATE over the range then available.** It improves significantly **only at `k` = 4.16**, the first
point outside the null: **0.418 [0.33, 0.61]** [EVIDENCE].
⚠ **Reading all four points as a monotone trend is [BELIEF], not EVIDENCE** — three of the four sit inside
the null, so **only the top point carries it.**
🛑 ~~More damper will NOT fix the micro-ratchet.~~ Grind #1 present on V76 at rel. excess
**1.956 [1.214, 4.154]** (worse than V75's 1.572, far better than V74's 9.154); ratchet **5.026
[3.824, 6.592]**, indistinguishable from V74/V75. **Both match the operator's report exactly.**
🛑 **V76's grind-#2 prediction was FALSIFIED** at the one powered rung: predicted 0.57× vs V75 at
42 °/s, **measured 1.394 [1.017, 1.768]** — opposite direction. Discount the arithmetic surface's
ability to predict *delivered* grind #2; the `k` dose axis itself was validated.

★★★★★ **THE EVALUATOR, orchestrator-verified by decompile (`FUN_00034350`, sole caller `FUN_00022ca0`):**
- Records are reached through a **pointer array per factor** (`FactorB 0xC9CCC · FactorC 0xC9E9C ·
  FactorD 0xC9DB4 · FactorE 0xC9F84 · ceiling 0xC77A0 · friction 0xCBE74`), `u32 @ arr + mode*4`,
  **34 distinct records over 34 modes, zero sharing.**
- Layout: `base+0` u16 n · `base+2` n×i16 X · `base+2+2n` n×i16 Y · `base+2+4n` u16 terminator; `4+4n`.
  🛑 **X starts at base+2, NOT base+4** (reading at +4 silently yields `[X1,X2,X3,Y0]`).
- 🛑 **THE COUNT FIELD IS NEVER READ.** The lookup is a real `while (X[i] <= idx) i++` loop, but `n` is
  pinned per factor by three hardcoded immediates — B/C/E `rec+10 / rec+8 / rec+0x10` (n=4), D
  `rec+0xc / rec+10 / rec+0x14` (n=5), ceiling `rec+6 / rec+4 / rec+8` (n=2). **More points = a CODE
  edit to the always-on base-assist damper = the class that bricked V24/V27/V48B.**
- ★★ **THE OUTPUT IS HARD-CLAMPED**: `gp-0x6bd0 = clamp(product, ±ceiling_LERP(gp-0x6ac2))`, ceiling
  record n=2 `X=[300,800] Y=[512,1024]`, fallback `*(u16*)0xC6158 = 512`. **`|gp-0x6bd0|` can never
  exceed 1024, and is 512 at low ceiling index.** This — not the point count — is the binding constraint.
- `gp-0x6bd0` is **lockstep-shadowed at `gp-0x4cf2`**. Two gates zero the chain: FactorC → unity if
  `(gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1)`; damper → 0 unless
  `(gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)`.
  🛑 **`gp-0x67f4` has never been probed** and disables FactorC's speed shaping entirely.

★★★★ **WHY THE ReLU PLAN INVERTS.** A ReLU is 2 DOF; a 4-point table has 8 numbers and spends 3 on
collinearity, so **more points buy EXACTLY ZERO for a pure ReLU** (constructive witness in the handoff).
**The constraint that breaks is parameter-free:** a ReLU FactorC is speed-proportional, so
`dose(v,99)/dose(515,99) = v/515` *whatever values you pick* — pinning 206 at 5 mph forces **3,593 counts
at 140 km/h = 7.02× the 512 ceiling**, railing above **3.2 °/s at 140 km/h, 7.0 at 60, 21 at 20 km/h**.
★★ **A railed damper whose sign comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay — you would forbid it at `E_Y[0]` and re-create it at the ceiling.** On V76's flat
FactorC the same dose rails no earlier than **563 °/s — 176.7× more usable linear range.**
⚠ **"Which factor isn't a ReLU" has two readings that point at OPPOSITE tables** — literal
`max(0,k(x−x0))` indicts **FactorC** (566 floor); the operator's own recorded gloss in `v76_surface.py`
(*"FLAT — no taper down, like a rectified linear unit"*, read as a floor clamp) indicts **FactorE**
(three slopes: 2.521 / 0.100 / 0.259 per count). **Neither should be made a literal ReLU.**
📋 **RULE: ask anyone proposing a re-point which FOURTH segment they need. If they can't name it, n=4 is
enough.**

⊕ **Relocation is AVAILABLE though not needed** — it is **cal-only**: one u32 into `0xC9F04` /
`0xC9FEC`. **`0xD7BB8`–`0xD7FEF` = 1,080 B virgin `0xFF`, same page, same CRC block `0xD7FFC` V76
already recomputes**; the same run exists at the same offset in every mode-record page. Confirmed
unreferenced by a byte-granular whole-image u32 scan. **V74's "pointer arrays must stay byte-identical"
was a SELF-IMPOSED BUILD GUARD, not a firmware requirement** (sole reader dereferences without
comparison; the only flash writer `FUN_0000d934` has zero static callers; the CRC verifier
`FUN_0000b006` is UDS-only). 🛑 Leave `0xD7FF0`–`0xD7FFB` alone (`0xD7FF8` is the block self-descriptor).
⊕ **New Ghidra trap: `get_xrefs_to(0xD780C)` returns "No references found"** though the pointer exists at
`0xC9FEC`; the twin `0xD77D0` resolved fine. **Do not trust xref completeness on pointer-array slots.**
⊕ **A free, never-touched lane: FactorD is n=5, flat `Y=1024` (inert) in modes 24 AND 26**, axis
`gp-0x6a10` (angle-tracking error), gated `gp-0x67fe ∈ {1,2}`. UNTESTED, not falsified.

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

- 🛑 **`0xC61B2` / `0xC61B4` ARE NOT "the pre-gain deadband arm" — corrected 2026-08-08 (late).** They are
  **output clamps on the forward path**: `0xC61B2` (= `±tp+0x71b2`) is the **arbitration output clamp**
  in `FUN_0002b422`, and `0xC61B4` (= `±tp+0x71b4`) is the **LKAS-gain output clamp**. They were doubled
  **alongside the LKAS gain**, in lockstep, at both steps: stock **512 → 1024 at V22 → 2048 at V38 = 4×
  Honda**, and unchanged since. **The pre-gain deadband is a DIFFERENT cell — `0xC61B8` = 102 — and it
  was never rescaled** (that is the whole point of the deadband box in `BUILD-LINEAGE.md`). [EVIDENCE]
  ⚠ **The wrong label is still live in two build scripts**: `analysis-2020accord/build_v83a_tva.py:359-360`
  and `analysis-2020accord/build_v84_tva.py:544-545` both read `"pre-gain deadband arm."` in their KEEP
  lists. **Comment-only; no byte is affected** — but fix it before the label propagates into a third build
  (NEXT item 7).

- 🛑★★ **`gp-0x6c2c` — the oscillation detector's input — is a MOTOR-RATE DERIVATIVE, not torque and not
  a raw per-tick difference.** Produced in `FUN_00041464` @`0x4184E`; all cals byte-read LE:
  ```python
  K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
  x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
  if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
  target = x * 1024
  step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
  acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
  state += ((acc - state) * K2) >> 6                  # EMA #2
  gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
  ```
  ⇒ **an ACCELERATION** — differencing kills DC, so a sustained large steering input cannot drive it.
  Sibling `gp-0x6c2e` takes the same `acc` through a slower EMA (cal `0xC40DA` = 3, `>>7`).
  **Sizing:** a 21.3 Hz sinusoid needs `|gp-0x4f50|` ≈ **1683** counts @1 kHz / **1821** @100 Hz to trip
  `T` — inside that signal's own ±13000 validity ceiling, so **the detector is NOT structurally blind to
  the mode; the drive was ~1.7–2× short.** Independently reproduced in the frequency domain
  (`|1-H1|`=0.43041 × `|H2|`=0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ U = **1685**) — 4 significant figures by
  a different method. The `acc` clamp bites at U ≈ 4017 ⇒ `T` is reached at ~42% of saturation, linear there.
  🛑 **Do NOT size `T` from bus torque.** A pass this session derived "T ≈ 2048–2560" and "LSB ≤3.29×
  finer" from the `0x18F` torque channel; **both are VOID** — `gp-0x6c2c` is not torque-derived and does
  not share that LSB. Also void: a "per-tick rate ⇒ effectively dead" reading that priced the chain at
  unity gain and missed the `×1024` and `×32` pre-scales, which are invisible from the bus.
  ⚠ `gp-0x4f50`'s physical units remain **untraced** (needs the ISR writing `gp-0x29c4`, or a probe), so
  1683 is in raw counts of a signal whose scale is unknown.
- 🛑★ **`gp-0x671a` is NOT private to the rate lanes — 4 external consumers.** Byte-scanned both
  encodings, whole image: 8 real hits, 6 reader functions, sole writer `0x42A12`. External:
  **`FUN_0003a382`** (a **continuous LERP index**, not a gate, shaping the live P/I/D lane `gp-0x6ad4`),
  **`FUN_00036c12`** (friction-comp `gp-0x6b26`, sums into the *same* aggregator; ⚠ its own gate uses cal
  `0xC64FD`, **not** CEIL), **`FUN_000352b4`** (gates a 2nd-order IIR update), **`FUN_00035b20`** (selects
  between two LERP-blend curves). ⇒ **lowering `T` changes five things at once.** By contrast `gp-0x67df`
  is **clean** (2 hits, both inside `FUN_000428d4`) and `T` itself has 4 readers, all inside the detector.
  `CEIL` (`0xC64FA`) is **not** private — 3 external readers.
  ✅ `gp-0x671a` is logged into a diagnostic record array each low-torque tick (`FUN_00045608(2,…)`) but
  the DTC-0x21 dispatch in that tail reads a *different* array (`gp-0x6544[2]`, producer untraced) ⇒
  "touches diagnostic logging, does not appear to gate a fault" — not chased to full closure.
- 🛑 **`0xC64FA` (CEIL) is a BYTE cal = 5, read by `ld.bu` @`0x3AA78`.** A halfword read gives **517** and
  is wrong. Lowering CEIL means writing one byte. (`T` at `0xC620A` *is* a halfword, `ld.h`, = 12800.)
- 🛑 **`gp-0x671d` is NOT "r24's override flag".** It is a **saturating rising-edge counter on a
  torque-residual/observer check** (`FUN_00041d56`, 5-tap filter combination vs `tp+0x71f8`/`0x71fa`),
  feeding DTC dispatch `FUN_00016de6(0x5e,…)`, reset only by `FUN_0003bcb2`'s resync — **not** every tick.
  8 reader functions including the motor-off dispatcher `FUN_0003d4a2`. It read **0** for all of route
  `35`, so r24 *was* covered by V64's arm. Writer/reader set confirmed exhaustive by whole-image raw byte
  scan in **both** encodings (disp16: 16 hits; disp23: 0).

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


---

## ⚠⚠ SUPERSEDED 2026-08-13 — THE BLOCK BELOW IS A RECORD, NOT THE CURRENT STATE
🛑 **It said "ON THE CAR: V94 … Still flashed" and that is FALSE.** V94 was aborted and superseded by
V96 → V97 → **V98**, which is on the car as of route `0x81` (identity single-frame, `0x14A`
byte7[7:6] == 2, duty 1.000000, 17,983 frames). **The head of this file is the authority.**
⇒ This was one of SIX stale flight-status claims found and corrected in one sweep on 2026-08-13
(`STATE.md` ×3, `BUILD-LINEAGE.md` ×3). **Run the gate at EVERY close-out — it fails loudly, memory does not.**

## ON THE CAR RIGHT NOW, AND WHAT IS BUILT — ⚠ SUPERSEDED, SEE ABOVE

🛑🛑 **ON THE CAR: V94 — AND THE OPERATOR STOPPED DRIVING IT.** Flown as route `7d`, 2026-08-12,
**fault-free**. *"It vibrated the entire car, and I decided it was not safe to drive."* **Still flashed.**
image sha256 `cd971c05d483fe9c…` · rwd sha256 `3feccc09d8cbdd05…`
V94 vs stock: **245 differing bytes in 114 runs, zero unattributed** — full table in
`docs/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md` §6b, reader
`analysis-2020accord/ledger_v94_cells.py`.

**Unflashed candidates on disk:**
- **V92 — the REVERT candidate.** rwd sha256 `388a1974d5702e17…`. The last configuration the operator
  drove and did **not** abort (route `79`, identity proven single-frame). Its cal row is **stock on
  three of five sites and ×1.5 on modes 26/27** — "revert to V92" is *not* "revert to stock".
- **V93** — carries V94's cal without the packer rescale. Valid artefact, measures itself poorly.
- **V96** — the instrument build cut at the 2026-08-12 close-out. **The live candidate.** See §A6.
  🛑 **V95 is a VACATED number** — three artefacts wore it; do not reuse it.

🛑 **Flashing is gated on the operator naming the file and the bus, every time.**

🛑 **Before proposing any calibration edit:** grep `analysis-2020accord/build_v*_tva.py` **and**
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` for the address, and state its on-car result.
`FALSIFIED` ≠ `INERT-BY-MODE` ≠ `never-tried`, and *"the same lever pushed the other way"* is a
different claim from *"a new lever"*.

---

## RECOMMENDED NEXT STEPS, IN ORDER

🛑 **NO openpilot-side modifications.** Standing operator instruction; openpilot is a measurement
instrument only.
🛑 **Score in the regime the operator drives in: ENGAGED + HANDS-ON + OVERRIDE, on BAND POWER.** §A2.
The corpus already holds the exposure — what it does not hold is 5.12 s windows (**only SEVEN**).

1. 🛑🛑 **GET V94 OFF THE CAR.** It is the only build the operator has ever aborted. Whether that is
   V96 or a straight V92 revert is his call and needs him to name the file and the bus.
2. ★★★★★ **Answer the two questions that are waiting on the operator, before cutting another lever:**
   (a) does he feel a **slow lurch or "catch"** during override, distinct from the buzz? (§A3 — a
   quantified ~0.5–1 Hz surge mechanism is sitting there unattached to any complaint);
   (b) does the car feel **different left versus right**? (`0xC63F8` = 33 vs `0xC63FC` = 328 is a
   **10×** asymmetry, virgin on all 85 images, and nobody has ever asked).
3. ★★★★ **Resolve the two live leads in §A6b** — `0xC63A6` (a virgin second multiplier on the lane
   whose direction is now measured) and `0xC64B8` (non-stock for 66 builds, sitting exactly in the
   high-driver-pushback regime). Both have traces in flight; **neither is EVIDENCE yet.**
4. ★★★ **Rebuild the band estimator for override.** Point-process or event-triggered, or 1.28 s
   windows. Every existing band number in this file comes from a 5.12 s window in a regime the
   operator does not produce the symptom in.
5. ⚠ **Audit whether any HISTORICAL result rests on the crossed `raw14` pairing** (the kit-wide
   off-by-one found on route 73). Safe pairings are `(t, probe)` and `(raw14_t, raw14_b4)` — never
   crossed. The defect predates route 73 by at least eight routes and **has not been audited backwards.**
6. ⚠ **`0xC64DE` = 25627 has been non-stock since V22 — 85 builds — with a disputed label and no
   isolation.** The longest-carried unmeasured cell in the image. Not implicated in anything current.
7. 🛑 **`analysis-2020accord/eps_lkas_chain_model.py` IS 297 KB AND IS OVER THE `Read` CAP. NOT FIXED.**
   Found at the 2026-08-12 close-out — the **fourth** instance of this defect, and the worst-placed,
   because `CLAUDE.md` makes the golden model **mandatory reading before evaluating any lever**:
   *"a lever is only understood once you can say where it sits in that chain."* At 297 KB an agent
   that reads it whole gets a **silently truncated tail**, and the tail is where the newest chain
   corrections live. ⚠ It was already over before this session; my own edits took it 292.8 → 297.4 KB.
   **NOT fixed deliberately:** it is a live, importable, re-runnable Python module, a builder was
   mid-cut, and module surgery under those conditions is how you break the one artifact everything
   else is checked against. **Fix pattern:** the file is mostly comment blocks — lift the narrative
   commentary into a companion `docs/GOLDEN-MODEL-NOTES.md` and leave the executable model lean, or
   split by chain stage into an importable package. **Assert `import` + a round-trip run before and
   after, exactly as the lossless carves in item 8 were asserted.**
8. ✅ **DONE 2026-08-12 — the `Read`-cap defect is fixed in the other three places.** `memory/MEMORY.md` was
   287 KB (split verbatim to `MEMORY.md` + `MEMORY-PART2.md`, 312 links before and after, none lost);
   `docs/BUILD-LINEAGE.md` was 293.8 KB (Part 1 carved to
   `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`, lossless carve asserted in code); this file is back
   under cap. 🛑 **The 170 SUPERSEDED/DEAD/FALSIFIED bullets were deliberately NOT pruned** — they are
   load-bearing, and four candidate levers were killed by them in one session. **The cause is hook
   length (829 B average). Compress hooks; do not delete pointers.**
