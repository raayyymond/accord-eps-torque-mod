# ADV-ARITHMETIC — V298 (first firmware ANGLE LOOP, PRIMARY + CAMERA INTERLOCK)

**Adversary:** ARITHMETIC. **Job:** make the BUILT image FAIL on delivered-surface arithmetic. **Verdict: PASS_WITH_DEFECTS.**
DO_NOT_FLASH was structurally reachable (the FAIL criteria F1–F9, written first, are in `ADV-arithmetic-V298-FAIL-CRITERIA.md`);
no arithmetic defect reached it. One bounded small-signal defect and one scorer-staleness trap are recorded below.

- **Image:** `_v298_…A16A_plain_image.bin` sha256 `177abf04…2066` (re-hashed; matches the builder's report and the open Ghidra copy).
- **Method:** decode = GhidraMCP PseudoDisassembler **linear dump of my OWN import** of the image (`/advArith/V298_ADVARITH_COPY.bin`,
  listings `_scratch/angle_loop/adv-arith-v298/v298_listing*.txt`, 1949 insns + 3 callees, 0 undecodable; cross-checked against the
  flow decode at every edited address). Arithmetic = my **independent integer mirror** transcribed instruction-by-instruction from
  the image bytes, each line annotated with its address, compared tick-for-tick against the common scorer `panel2/score_time.py`
  `CandLane.cave_stage`/`.tick`. Tables + cals read from the image by LE Python (second method). **Nothing read from the build
  script's constants or the design page.** Scripts: `a01_diff.py … a08_sar5_bias.py` beside this file.

---

## What a FAIL looks like (written before any byte was read) — and the result

| # | FAIL criterion | result | EVIDENCE |
|---|---|---|---|
| **F1** | overflow/wrap sign-flip in any intermediate | **PASS** | 0 32-bit wraps flagged in E·G and the I accumulator over 350 k+ ticks (`a03`,`a04`). E∈±131071, E·G≤2.87e8, Ep·112≤1.25e8, e5·40≤1.4e6, I≤±1.05e6 — all < 2³¹. Fade product A·B (0–255 tables) ≤ 65025 < 65536, so the `andi 0xffff` truncation never wraps. |
| **F2** | integral bound broken / negative / escapable | **PASS** | A3 bound = (\|θ\|≪{4,6})+1250, capped 4096 for v≤1382 — strictly ≥1250>0, cannot go negative. Freeze test matched the scorer on 144 375 ticks (`a03`). I hard-clamped ±icl=1 048 576. Escape paths all SHRINK I: freeze→decay, skip→I:=0, cam→decay (`a06`). |
| **F3** | sentinel (0x7FFF/0x7FFFFFFF) consumed as a sample | **PASS (improved)** | V298's D operand is the fresh rate `op=s16(abe)` (OPH `mov r26,r8` @0x29EE0), **not** E−Eprev. The Eprev sentinel loaded @0x29E5E is **overwritten** before the D multiply @0x29EE4, so it never reaches the surface. A sentinel RATE (abe=0x7FFF) trips the op-skip (\|abe\|>13000→invalid→`jr 0x2A164`), so it yields **no torque**, not a huge D. |
| **F4** | control-flow / link / stale ref | **PASS (relink confirmed)** | From the image: hook `jarl 0xC4C00,r6`; G-table ptr `mov 0xC4CDA,r9` (**the relink fix — NOT the defective 0xC4CC4**); freeze `jr 0x29D7E` (**not the stale 0x29D80**); CAM `jr 0x29D7E`; op-skip `jr 0x2A164`; normal `jmp r6`→0x29D7A. All targets **even** and on real instruction boundaries. Cave uses jr/jmp only — lp & sp untouched, dispose restores r20–r29. |
| **F5** | CAM / freeze not inert | **PASS** | Camera (r25=0): E′:=0, op:=0, I decays to 0 from either ±clamp within ~20 ticks, **no bias** (`a06a`). Freeze: e5:=0, I decays. |
| **F6** | G-table lerp defect | **PASS** | My image walk == scorer `glut` on **all v 0..12000** (`a03`), min G=559, max 2188, X monotone, 0xFFFF terminator handled, no step > one quantum, slope signs correct. |
| **F7** | mirror disagrees with the common scorer | **PASS** | My independent cave mirror == `CandLane.cave_stage` on **144 375** valid-rate ticks for Ep, op, freeze and the frozen e5 (`a03`). P/I/D independent recompute == the scorer on 50 000 ticks (`a04`). Builder's own H1 corroborates: 0/40000, both negative controls catch. |
| **F8** | delivered surface exceeds the rail / the claims | **PASS** | SCL=15360 and OCL=3072 **unchanged from V295** (`a07`); sustained worst-case (E rail + I wound + D rail, no freeze) peak \|T\|=**2482 < OCL 3072**. V298 cannot exceed V295's torque ceiling. (DCL 0→10240 and ICL 10240→8192 are the only clamp changes.) |
| **F9** | dead or unbounded-drift integrator (sar-5 quantum) | **PASS with a bounded defect — see below** | — |

---

## The two things worth the operator's attention (neither is DO_NOT_FLASH)

### 1. DEFECT (bounded, inherited, modeled, instrumented): the sar-5 integrator floor bias (F9)
`e5 = Ep>>5` and `inc = (e5·40)>>3` are **arithmetic (floor) shifts**. Under zero-mean small error both floor toward −∞, so
the integral drifts negative. **It is BOUNDED:** the A3 θ-bound pins it at `I>>7 = −1250` at θ=0 (measured, any dither amplitude,
`a08`), i.e. ≈ **+204 output counts** of hands-off torque at centre worst case (≈6.6 % of the OCL rail), reached only after tens of
seconds of sustained symmetric dither; in closed loop the loop corrects it smaller.
- `e5 = Ep>>5` is **STOCK/V295 arithmetic** (inherited); **Ki 40 (was 0) is what makes it live** — this is the first build to run it.
- The common scorer uses the **same** `Ep>>5` floor, so the design's tracking/turn-hold numbers **already include** this effect.
- Covered by the design's **R6** (hands-off \|θ−θsp\|>10° → REVERT) and the wire **c0** offset term. **Classify: bounded defect, not a FAIL.**

### 2. TRAP for the record (does NOT affect V298's validity): the scorer's `CAL["fadeB2"]` is stale
V298's camera gate makes the lane run **only when armed** (gp-0x6803==2), which flips the PID post-fade from fadeA/fadeB to
fadeA2/fadeB2. I confirmed **from the V298 image** (correct firmware stride = selector×4, selector 7): **fadeA2 @0xE56F4 == fadeA
@0xE55A4** (unchanged) and **fadeB2 @0xE564C == fadeB @0xE54FC** (the build's neutralization). Proven in a **running loop**: armed vs
un-armed delivered T is **bit-identical** over 3000×200 ticks (`a06c`). So the design's un-armed C3B-P metrics correctly describe the
armed V298 surface. **However** `score_time.py::_cal_extra` reads `fadeB2` from the **V295 image** (`NS.V295`), so the scorer *as
loaded* carries V295's un-neutralized fadeB2 (X[24,45,…] Y[255,205,…]). This is harmless here (the design scored fade2=False and the
image neutralization holds), **but anyone re-scoring V298 armed on the scorer must patch `CAL["fadeB2"]` to the V298 image value first.**

---

## Delivered surface, re-derived from the image (the arithmetic, annotated)

```
E   = s32((sp<<2) - r26)                 # 0xC4C00 shl2 ; 0xC4C02 sub      sp=s16(gp-0x69ae), r26=fb sum (C clamp ±65535)
rate= s16(gp-0x6abe) ; if (rate+13000)u > 26000u: jr 0x2A164   # 0xC4C04..14  op-skip = fail-safe (I:=0, sentinel, decay)
G   = walk(GB-P, gp-0x6a5e)              # 0xC4C18..52  min 559 @v=2707, max 2188
Ep  = s32(s32(E*G) >> 8)                 # 0xC4C54 mul ; 0xC4C58 sar 8
if gp-0x6803 != 2:  E:=0, op:=0, e5:=-(I8>>6), exit 0x29D7E    # 0xC4C5A..D4  CAMERA -> inert + decay
freeze if |hand4f68|>512  OR (|hand|>300 and sign(hand)!=sign(Ep))  OR  t>=bound  OR (ramp&0x8000)==0
       bound=(|θ| << (6 if v>2880 else 4)) + 1250, capped at 4096 if v<=1382   # 0xC4C5E..CC0
e5  = 0 if freeze else Ep>>5             # 0x29D7C (normal) / cave sets r6 on freeze|cam exits
I   = clamp((I8>>3) + ((e5*40)>>3), ±1048576) ; I8 = I<<3      # 0x29D9C..DC6   Ki 40, ICL 8192
P   = clamp((Ep*112)>>8, ±15360)         # 0x29E34..5C   Kp 112
D   = clamp((48*op)>>3,  ±10240)         # OPH op=rate ; 0x29EE4..F06   Kd 48, DCL 10240
S   = (I>>7) + P + D                      # 0x29F18..24   (I>>7 ≤ 8192, bound-capped near centre to ≤1250)
f   = ((fadeA*fadeB) & 0xFFFF) >> 8 ; Sf = (S*f)>>8 ; Sc = clamp(Sf, ±15360)   # fade attenuates only, no sign flip/wrap
y   = output-lag(Sc) ; yr = s16((y*ramp)>>15) ; T = clamp((yr * pol*5346)>>15, ±3072)   # 0x2A174..220  UNCHANGED from V295
```

Peak \|T\| sustained worst case = 2482 (< OCL 3072). Fail-safe paths all inert/decaying. No overflow, no sentinel kick, no sign flip.

**Out of ARITHMETIC scope (flagged by the builder / other adversaries):** the camera discriminator premise (6803 byte-2 field) is
BELIEF not re-measured; pol=−1 is car-specific; unit/scale chain is adversary 2; the build-script assertion census is adversary 3;
the interlock/downstream consumer census is adversary 4. The cumulative non-stock delta (2471 B) is large but every delivered-surface
cell is bounded by the inherited V295 clamps.
