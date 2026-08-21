# TRACE — the LKAS command range, wire → motor-torque product

**Question (operator, 2026-08-20):** *"Allow openpilot to send a greater range of numbers. Right now the
range is fixed and the upper value is simply mapped to a larger LKAS torque. Maybe we can modify the
firmware to accept larger values so openpilot can order the demand of torque more finely rather than
coarsely as we increase the torque mod."*

**Status: analysis only.** No build, no flash, no CAN/UDS action. Written against STOCK `code.bin`
(`39990-TVA-A160`, 2086 functions, fully analysed) plus byte reads of the V101/V102/V103 plain images.

**Evidence legend** — **[EVIDENCE]** = read this session, method stated. **[prior EVIDENCE]** = cited from
the kit record, not re-derived. **[BELIEF]** = inference, flagged.

---

## 0. HEADLINE

**Widening openpilot's transmit range is a NULL OPERATION for torque resolution, and the proof is an
integer identity, not an argument about the wire.** [EVIDENCE — exact-arithmetic enumeration, below]

> **# distinct LKAS-lane output counts = GAIN + 1, for every GAIN ≤ 8192,
> independent of how many codes openpilot transmits.**

The binding quantiser is **not** the intake — it is `sar 0xf` at **`0x2a202`**, the Q15 right-shift after
the gain multiply. Everything openpilot sends beyond what that shift can resolve is discarded there. At
the on-car 6× (`0xC6CD0`=5346) the lane can express **5,347** distinct torque counts; at 8× (7128),
**7,129**. openpilot already transmits 8,193 distinct codes — **more than the firmware can represent at
either gain.** The intake is not the bottleneck and has not been since stock.

A sibling agent reached the same *conclusion* by a different and **incorrect** *route* — see §7.

---

## 1. SIGNAL-FLOW DIAGRAM — wire to motor-torque product

Every box annotated with instruction address, cal cell (`0xC…`/`0xE…`) and **stock** value read
little-endian from `stock_fw_dump/code.bin`.

```
 CAN 0x0E4  STEERING_CONTROL  (openpilot -> EPS, 100 Hz)
 byte0..byte1 = STEER_TORQUE, big-endian signed 16   [DBC: 7|16@0-, declared -4096..4096]
        |
        |  gp-0x1428 (byte0, hi)   <- CAN RX staging, written by the mailbox copier
        |  gp-0x1427 (byte1, lo)      (register-indirect; NOT visible to any operand-text scan)
        v
 [A] FUN_00021724                                    0x2172c ld.bu -0x1428,gp,r14   (opc 0x3C, even)
     return CONCAT11(hi,lo)                          0x21730 ld.bu -0x1427,gp,r28   (opc 0x3D, odd)
     => the FULL 16-bit wire word.  No mask.
        |
        v
 [B] 0x526c6  jarl FUN_00021724, lp
     0x526ca  mov  r10, r6
     0x526cc  sxh  r6                 <-- SIGN-EXTEND ALL 16 BITS.  NO RANGE CHECK, NO MASK.
     0x526ce  movea -0x4000, r0, r7   ; lo = -16384
 **  0x526d2  shl  0x2, r6            ; x4          bytes c232          <-- THE Q-POINT
     0x526d4  subr r0, r6             ; negate  => x-4
     0x526d6  movea 0x4000, r0, r8    ; hi = +16384
     0x526da  jarl FUN_00049a90, lp   ; 3-arg clamp
     0x526f2  st.h r10, -0x69ae, gp
        |
        |   setpoint  gp-0x69ae = clamp(wire * -4, -16384, +16384)
        |   ** 4096 x 4 = 16384 EXACTLY.  The clamp is numerically flush with openpilot's rail. **
        v
 [C] FUN_00028ea6  (arbitration / "steer_torque_arbitration"), body 0x28ea6-0x2a30d
     0x29032 / 0x29124  ld.h -0x69ae, gp
     arb_setpoint_limit LERP, ptr array 0xCB844[12] (stride 0x28), selector gp-0x674e = 7
       -> record 0xE51A8 : count=9,
          X = 3200 3413 3627 3840 4736 5632 6528 7424 8320   (speed counts, ~64 ct/km/h => 50..130 km/h)
          Y = 15360 x9  STOCK    ->  16384 x9  since V38 (on the car)
       ** Y IS FLAT.  The LERP currently returns a CONSTANT.  It is a ceiling, not a curve. **
     setpoint := clamp(setpoint, -Y, +Y)
        |
        |   ... IIR blend / authority ramp; 32-bit accumulators gp-0x3d34, gp-0x3d3c held at Q5,
        |       output re-quantised by `>> 5`; ramp applied as (x * ramp) >> 0xf
        v
 [D] THE GAIN MULTIPLY  —  0x2a1ee .. 0x2a222
     0x2a1ee  ld.h  0x746c, tp, r7      ; tp+0x746c = 0xC646C  STOCK 891
                                        ; V57 rewrites hw2 -> 7cd0 = 0xC6CD0 (private cell)
                                        ;   stock 0xFFFF -> V101 7128 (8x) -> V102/V103 5346 (6x)
     0x2a1f2  ld.b  -0x6752, gp, r13    ; polarity, VERIFIED = -1
     0x2a1f6  mulh  r7, r13             ; r13 = GAIN * polarity
     0x2a1f8  ld.hu 0x71b4, tp, r16     ; 0xC61B4  arb_output_clamp  STOCK 512
     0x2a1fe  mul   r13, r11, r0
 **  0x2a202  sar   0xf, r11            ; >> 15  <-- **THE BINDING RE-QUANTISER**
     0x2a204..0x2a222  clamp to +/- 0xC61B4
     0x2a23c  st.h  r1, -0x6b38, gp
        |
        |   gp-0x6b38 = clamp( (blend * pol * GAIN) >> 15 , +/- 0xC61B4 )
        v
 [E] MIXER / PACK  —  0x2b400..0x2b45c
     0x2b418  ld.h  -0x6b38, gp, r15    ; 0 if the enable reg is 0
     0x2b41c  st.h  r15, -0x6b3c, gp
     0x2b42a  ld.hu 0x71b2, tp, r14     ; 0xC61B2  pack_output_clamp  STOCK 512
     0x2b42e..0x2b44a  clamp to +/- 0xC61B2      ** PURE CLAMP.  NO SHIFT.  No resolution lost. **
     0x2b45c  st.h  r12, -0x6b3a, gp
        |
        v
 [F] AGGREGATOR  FUN_0003aa2c
     lane weights:  0x3ab70 / 0x3ab76 / 0x3ac20  `sar 0xa`  (Q10)   <-- V62's grind-#1 sites
     GATE-3 DROPOUTS (zero-reject, NOT clamps) — [EVIDENCE, disassembled this session]:
       0x3acb8  cmovc 0x0, r11, r15
       0x3acbc  addi  0x2800, r6, r9        ; r9 = lane + 10240
       0x3acc0  addi -0x5001, r9, r0        ; carry <=> r9 >= 0x5001 <=> |lane| > 10240
       0x3acc4  cmovc 0x0, r6, r13          ; r13 = C ? 0 : r6   => OUT OF WINDOW -> ZERO
     LKAS peak at 8x = 3564 counts vs window +/-10240  => 2.87x headroom, never binds.
     0x3acdc  jarl 0x36682   (the 0xC646C feedback reader #5, +/-512 authority, 0.93 Hz pole)
     sum -> clamp +/-0x2800 -> gp-0x6b94
        |
        v
 [G] GOVERNOR  FUN_0004503c
     flat nominal   0xC6202 = 4762  (STOCK, frozen every build)
     slew steps     0xC6206 = 512 / 0xC6208 = 205 (STOCK)
     adaptive motor-rate cap  0xC520C bank  X=(1050,1700,2500,3700,4100) Y=(5325,3584,2406,1587,512)
     THREE MORE Q15 RE-QUANTISERS:  0x453f8 / 0x4540a / 0x4541e   `sar 0xf`
        |
        v
 [H] SOFT-EME SHAPER
     corridor/boost LERP, X knots from tp+0x774a, **Y[0] = tp+0x774e = 0xC674E**
       STOCK 1024 -> 5120 since V38.  Read at 0x43066 (FUN_00042af8), 1 reader, 0 stores.
     final static clamp +/-0x2000 = 8192
     hard lockstep monitor FUN_00043e44 mirrors the corridor arms in FLOAT, +/-5 LSB, no debounce
        |
        v
 [I] integrator -> gp-0x6b98 -> FOC (Park/Clarke + PI + SVPWM, FUN_00071272), carrier ~4 kHz
```

---

## 2. ANSWERS TO THE SIX ASSIGNED QUESTIONS

### 2.1 CAN intake of `0x0E4`
`FUN_00021724` **[EVIDENCE, decompile]**: brackets a critical section (`FUN_0001fa42`/`FUN_0001fa72`),
reads `gp-0x1428` and `gp-0x1427` as bytes, returns `CONCAT11(hi,lo)`. **Bit offset 0, width 16,
big-endian on the wire, signed** (the sign is applied by `sxh` at `0x526cc`). That matches opendbc
`STEER_TORQUE : 7|16@0-` on `BO_ 228 STEERING_CONTROL` exactly.
🛑 **The declared `[-4096|4096]` is DBC documentation only — the firmware imposes no such check.**
**[EVIDENCE]** the raw scan of `gp-0x1428/0x1427` returns exactly 2 instructions, both `ld.bu` inside
`FUN_00021724`; the ld.bu parity trap is visible in the encodings (`8477`/opc 0x3C for the even
displacement, `a4e7`/opc 0x3D for the odd) — the scanner handles both.
⇒ **The wire field's true width is 16 bits signed, ±32767.** Nothing in firmware narrows it before the
`× -4` and the `±16384` clamp.

### 2.2 Every clamp/saturation/deadband/rate-limit between wire and gain

| # | site | cal | stock (LE) | rule | binds at 8×? |
|---|---|---|---|---|---|
| 1 | `0x526d2/d4` | — (code literal) | `shl 0x2` + `subr` | `sp = wire × −4` | — (scale) |
| 2 | `0x526da` → `FUN_00049a90` | — (code literal ±0x4000) | `movea -0x4000`/`movea 0x4000` | `clamp(sp, ±16384)` | **YES — binds at exactly `wire = ±4096`** |
| 3 | `FUN_00028ea6` LERP | `0xE51A8` Y[0..8] | 15360 ×9 | `clamp(sp, ±Y)` | **NO on the car** (V38 raised all Y to 16384 = clamp #2) |
| 4 | `0x2a204..0x2a222` | `0xC61B4` | **512** | `clamp(out, ±cal)` | **NO if raised in lockstep**; binds hard if not |
| 5 | `0x2b42e..0x2b44a` | `0xC61B2` | **512** | `clamp(out, ±cal)` | same as #4 |
| 6 | `0x3acbc..0x3acc4` | `0xC61B6`-class literal `0x2800` | 10240 | **zero-reject dropout** | NO (3564 ≪ 10240) |

**[EVIDENCE]** cal values read little-endian from `code.bin`: `0xC61B2` = `00 02` = 512;
`0xC61B4` = `00 02` = 512; `0xC61B6` = `00 28` = 10240; `0xC674E` = `00 04` = 1024;
`0xC407E` = `ff 01` = 511; `0xC6202` = `9a 12` = 4762.
There is **no deadband and no rate limit** between the wire and the gain. (`0xC61B8`'s 102-count
pre-gain deadband is ELIMINATED per the kit record; the only rate limit in the chain is the governor's,
downstream.)

### 2.3 The gain multiply
`0x2a1ee ld.h 0x746c,tp,r7` → `0x2a1f6 mulh r7,r13` (× polarity −1) → `0x2a1fe mul r13,r11,r0` →
**`0x2a202 sar 0xf, r11`**. **Q-format = Q15**, unity would be 32768. Stock 891 ⇒ 0.02719.
The product feeds `st.h → gp-0x6b38` → mixer [E] → aggregator [F] → governor [G] → EME [H] → FOC.
**[EVIDENCE, disassembly + decompile of `FUN_00028ea6`]**

### 2.4 The setpoint LERP that clips to 15360, and `0xC61B2`/`0xC61B4`
Pointer array **`0xCB844`**, 12 × u32, stride `0x28`, dumped this session **[EVIDENCE]**:
`E4180 E41A8 E41D0 E41F8 E4220 E4248 E5180 E51A8 E51D0 E51F8 E5220 E5248`.
Selector `gp-0x674e = 7` (row 11, `TVCA4`) ⇒ record **`0xE51A8`** **[prior EVIDENCE, fully traced
2026-08-06]**. Record layout `u16 count=9 | 9×u16 X | 9×u16 Y | 2 pad`.
**Stock Y = 15360 at all nine knots — the surface is FLAT, so "15360" is a constant, not a taper.**
15360 = `0x3C00` = 93.75 % of 16384 = 15/16 of full scale. V38 rewrote all nine Y to 16384 on both
`0xE4180` and `0xE5180` banks; both images confirm 16384 on V101/V102/V103.

**The clamp↔gain rule, read from the build script and re-derived:**
`CLAMP_RATIO = CLAMP_STOCK / GAIN_STOCK = 512/891 = 0.574635…`, i.e. **`clamp = GAIN × 512 // 891`**
(`build_v101_tva.py:143`). It reproduces every flown pair exactly:
891→512 · 1782→1024 · 3564→2048 · **5346→3072 (on car)** · 7128→4096.
Its purpose: `peak_out = (16384 × GAIN) >> 15 = GAIN/2`, and `GAIN × 512/891 = 0.5746 × GAIN` — i.e.
the clamp is held at **1.149 × peak**, a constant 14.9 % of headroom above the lane's own maximum, at
every gain step. **[EVIDENCE, arithmetic + the four flown pairs]**

### 2.5 The soft-EME floor `0xC674E`
**[EVIDENCE, decompile of `FUN_00042af8` + raw scan]** exactly **one** reader, `0x43066`
(`ld.h 0x774e,tp,r15`), zero stores, zero 6-byte-form hits. In the decompile it is **`Y[0]` of a LERP**
whose X knots begin at `tp+0x774a` (`0xC674A`): when the abscissa `iVar43` is below `X[0]`, the LERP
short-circuits to `sVar49 = *(short*)(tp+0x774e)` — the **narrowest corridor half-width**.

**What the build's assertion actually constrains** (`build_v101_tva.py:418-420`,
`check(eme_floor_int == 5120 and eme_floor_int > CLAMP_TO)`): it guarantees the LKAS lane's own output
clamp stays **strictly inside** the soft-EME corridor at its narrowest point, so the LKAS lane can never
by itself drive the shaper into its limiting region — the region whose arms are mirrored in **float** by
`FUN_00043e44`, the DTC-0xF00049 hard-lockstep monitor with **no debounce and hard motor-off** (the
V25/V26/V27 brick class).
- 8× ⇒ clamp 4096 < 5120 ✅ legal, 25 % headroom.
- 10× ⇒ clamp `8910×512//891` = **5120**, and `5120 > 5120` is **false** ⇒ **illegal by the rule.** ✅ verified.
⚠ **[BELIEF]** It is a *headroom* rule, not an interlock: exceeding it does not immediately fault. It
means the LKAS peak would sit inside a shaped/limited region whose int and float mirrors must then stay
bit-consistent. The rule is prudent and I would keep it.

### 2.6 🛑 THE CRUX — does anything downstream RE-QUANTISE the command?

**YES — at least five integer re-quantisers between the gain and the motor, and the first one is
already coarser than openpilot's wire step.** **[EVIDENCE, disassembly]**

| stage | address | op | effect |
|---|---|---|---|
| gain [D] | **`0x2a202`** | `sar 0xf` | Q15 → **integer count**. THE binding quantiser. |
| aggregator [F] | `0x3ab70`, `0x3ab76`, `0x3ac20` | `sar 0xa` | Q10 lane weights (other lanes) |
| governor [G] | `0x453f8`, `0x4540a`, `0x4541e` | `sar 0xf` | three more Q15 → integer |
| arb blend [C] | (inline) | `>> 5` on 32-bit accumulators `gp-0x3d34`/`gp-0x3d3c` | Q5 → integer |
| engage SM | `gp-0x682f`, `gp-0x6830` | `st.b` of `>>5` / `>>6` | **byte** stores — indices, not torque |

**Proof that this settles the question (monotonicity):** every stage from [B] to [I] is a
non-decreasing map of the previous stage's integer output. The number of distinct values reaching the
motor is therefore **≤ the number of distinct values leaving [D]**. So it is sufficient to count [D].

**Exact-arithmetic enumeration over the full wire range** (integer Python mirroring `shl 0x2` / `subr` /
`clamp ±0x4000` / `clamp ±Y` / `sar 0xf` / `clamp ±0xC61B4`, arithmetic shift, LE constants):

```
build              gain      L   clamp | peak cts  DISTINCT  cts per wire LSB
stock 1x            891  15360     512 |      417       836           0.1088
V31   2x           1782  15360    1024 |      835      1672           0.2175
V38   4x           3564  16384    2048 |     1782      3565           0.4351
V102  6x ON CAR    5346  16384    3072 |     2673      5347           0.6526
V101  8x           7128  16384    4096 |     3564      7129           0.8701
hypo             8192  16384    4708 |     4096      8193           1.0000
hypo            16384  16384    9416 |     8192      8193           2.0000   <- WIRE finally binds
```

**Widening the wire, gain held fixed:**

```
gain     N(STEER_MAX=4096)  N(8192)  N(32767)
891                    836      836       836   SAME
3564                  3565     3565      3565   SAME
5346                  5347     5347      5347   SAME
7128                  7129     7129      7129   SAME
8192                  8193     8193      8193   SAME
```

⇒ **`N = GAIN + 1` for every GAIN ≤ 8192, regardless of transmit range.** [EVIDENCE]

---

## 3. THE OPERATOR'S QUESTION, ANSWERED DIRECTLY

His premise is **exactly right**: at 6× on the car, one openpilot LSB is worth **6× the torque** it was
worth at stock. That is real and it is what "coarser" means physically.

But the remedy he proposes cannot work, because **the firmware's own step is already the coarser of the
two**:

```
                        openpilot wire step        firmware count step
   stock 1x             0.109 counts               1 count      <- firmware 9.2x COARSER
   V102 6x (on car)     0.653 counts               1 count      <- firmware 1.53x COARSER
   V101 8x             0.870 counts                1 count      <- firmware 1.15x COARSER
   gain 8192           1.000 counts                1 count      <- MATCHED, first point where
                                                                   widening would buy anything
```

At 6× and 8×, **openpilot is already asking in finer increments than the firmware can represent.** Give
it more codes and `sar 0xf` throws them away. The only way to buy torque levels is to raise the gain —
which is what the kit already does, and which **increases** the level count (5,347 → 7,129 going 6×→8×).

**Is 1 count coarse?** At 8×, full LKAS authority is 3,564 counts ⇒ one step is **0.028 % of full
authority**, ~11.8 bits. **[BELIEF]** That is not a plausible source of any felt roughness. The felt
"coarseness" of a big gain is much more likely to be **rate**, not amplitude: openpilot's slew limiter
(`STEER_DELTA_UP/DOWN = 3` per 10 ms tick) is also in normalized units, so its **counts-per-tick scales
with the firmware gain** — 13.4/tick at stock, 80.2 at 6×, 106.9 at 8× — driving time-to-full-torque
from ~170 ms (outside openpilot's 100 ms `steerActuatorDelay`) to ~28 ms / ~21 ms (well inside it). That
is the documented limit-cycle coupling in `docs/FEASIBILITY-8X-LKAS.md` §2.0/§2.4. **Widening the wire
does not touch it.**

---

## 4. SHAPE-BY-SHAPE VERDICT

### (a) Widen the intake clamp and lower the gain proportionally — **REFUTED, provably null**
Wire field is 16 bits signed, so ±32767 is physically available; but re-splitting the Q-point gives the
**identical output set**:

```
configuration                        peak cts   DISTINCT  step set
stock intake  wire+/-4096  shl 2         3564       7129      {1}
widened       wire+/-8192  shl 1         3564       7129      {1}
widened       wire+/-16384 shl 0         3564       7129      {1}
widened       wire+/-32767 sar 1         3563       7128      {1}
```
Same 7,129 reachable torque levels, same minimum step of 1 count. It only relabels which wire code maps
to which count. **[EVIDENCE, enumeration]** ⇒ **Do not build.**

**Byte-exact edits, if the operator ever wants them anyway** — all four encodings **round-tripped
through Ghidra's own decoder**, not hand-derived:

Format II: `halfword = (reg2 << 11) | (opcode << 5) | imm5`, `SHR=0b010100`, `SAR=0b010101`,
`SHL=0b010110`; stored little-endian.
- `shl 0x2, r6` = `(6<<11)|(0x16<<5)|2` = `0x32C2` → **`c2 32`** ✅ matches `0x526d2` in the image
- `shl 0x1, r6` = `(6<<11)|(0x16<<5)|1` = `0x32C1` → **`c1 32`** ✅ verified @`0x21da`,`0x1610c`,`0x163a4`,…
- `sar 0x1, r6` = `(6<<11)|(0x15<<5)|1` = `0x32A1` → **`a1 32`** ✅ verified @`0x1a89e`,`0x1a990`,`0x298b8`,`0x321ba`,…
- `shr 0x1, r6` = `(6<<11)|(0x14<<5)|1` = `0x3281` → **`81 32`** ✅ verified @`0x299c`,`0x14ebc`,`0x16eb6`,…

**⇒ `0x526d2`: `c2 32` → `a1 32` converts `×4` to `÷2`. 2 bytes, same length, in-place. It is correct
and it is pointless.** And it requires an openpilot-side `STEER_MAX` change, which is barred by standing
policy (`memory/feedback-no-openpilot-side-modifications.md`).

### (b) Move the multiply's Q-point instead of the gain constant — **NOT A LOCAL EDIT**
`sar 0xf → sar 0xe` doubles the lane output; it is the *same* lever as doubling `0xC6CD0`, reachable as
a **cal** edit instead (operator preference order says prefer the cal). It buys no resolution: it moves
peak and step together.
To buy genuine resolution you would have to make the *downstream count scale finer* — i.e. re-interpret
`gp-0x6b38`…`gp-0x6b98` on a finer Q. Everything downstream reads those counts against **fixed cal
constants**: `0xC61B2/4`, the `0x2800` literals at `0x3acbc/0x3acc0`, `0xC6202`=4762, the `0xC520C`
adaptive table, `0xC674E`=5120 **and its float mirror in `FUN_00043e44`**. A Q-point move is therefore a
**whole-chain rescale touching the DTC-0xF00049 lockstep pair** — the exact class that bricked V25–V27
and nearly bricked V48B. **⇒ Do not build.**

### (c) Pre-existing fractional / dither / accumulator path — **EXISTS, but upstream and unusable**
**[EVIDENCE, decompile]** `FUN_00028ea6` keeps two **32-bit** IIR accumulators, `gp-0x3d34` and
`gp-0x3d3c`, updated with `>> 10` coefficients (`tp+0x73ec`, `tp+0x73ee`) and re-quantised by `>> 5`
before use. So ~5 fractional bits already exist **upstream of the gain**. They are filter state, not a
command carrier: the `>> 5` and then `sar 0xf` both truncate them, and the value that leaves [D] is an
integer count regardless. **No dither, no noise-shaping, no error-feedback accumulator exists anywhere
on the command path.** Adding one is a cave on the 1 kHz task. **⇒ Not available; do not build.**

### (d) LERP-shaped gain curve keyed on `|setpoint|` — **the family has ONE cal-only member, and it is not a gain curve**
- The inline LERP template the sibling noticed is real (`FUN_00028ea6` ~line 1024 of the decompile, and
  again in `FUN_00042af8` at `0x43066`). But **its X source is fixed in code.** No cal edit can repoint
  an X axis onto `|setpoint|`. Building a `|setpoint|`-keyed gain curve therefore needs a **cave** on the
  1 kHz path. ⇒ **Do not build.**
- **The one cal-only member: `0xE51A8`'s nine Y knots.** They are flat (15360 stock / 16384 now), and
  V38 already rewrote all nine — a well-precedented, cal-only, mode-proof edit. **[BELIEF, strong]** the
  X axis is **vehicle speed** (`0xC62EA` = 320 counts ≈ 5 km/h anchors 64 counts/km/h ⇒ X spans
  50–130 km/h). Making Y a taper gives a **speed-scheduled command ceiling** — it *reallocates* authority
  across speed. It does **not** change torque resolution.
- 🛑 **If it is ever proposed, it must clear a linearity check, not a saturation check.** The V80 lesson
  is explicit: *"the no-clip gate is blind to `= ceiling − 17`."* Pre-register **flatness (`max/min` of
  delivered-per-commanded)**, **`N(50)/N(500)`**, and **distance-to-rail in counts** — a lane can sit one
  count under its ceiling for a whole drive and pass every no-clip test.

---

## 5. BLAST RADIUS — every reader, counted two ways

Method A = `mcp__ghidra__search_instructions` (operand text). Method B = raw little-endian byte scan of
`stock_fw_dump/code.bin` covering **both** gp/tp encodings (4-byte disp16 incl. the `disp|1` form for
`ld.hu`/`ld.w`, and the 6-byte extended form `disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7f)`), filtering on
`reg1 == tp(r5)`/`gp(r4)` and opcode ∈ {0x30..0x3F}.

| cell | A (Ghidra) | B (Python) | adjudicated | verdict |
|---|---|---|---|---|
| `0xC646C` tp+0x746c | **5** | **6** | **6** = A ∪ {`0x2a904`} | `0x2a904` is in the **known-dead gap `[0x2a507,0x2a93a)`** (`FUN_0002a30e`/`FUN_0002a93a`, dead out-of-line copies, 0 callers/xrefs/pointers — `build_v37/v38_tva.py`'s own annotation). **5 live.** |
| `0xC6CD0` tp+0x7cd0 | 0 | **0** | 0 in STOCK | The cell does not exist until V57's 2-byte hw2 edit at `0x2A1F0` creates its single reader. Confirms `0xC6CD0` is **provably inert on any build whose `0x2A1F0` reads `746c`**. |
| `0xC61B2` tp+0x71b2 | — | **5** (`0x2b42a/436/43c/446`, `0x2b5b6`) | 5, all in the live mixer | single clamp site + one other |
| `0xC61B4` tp+0x71b4 | **4** | **8** | **4 live** (`0x2a1f8`,`0x2a20c`,`0x2a212`,`0x2a21c`), **4 dead** (`0x2a910`,`0x2a91e`,`0x2a924`,`0x2a92e`) | the 4 extra are the same dead gap. Ghidra's 4 = the live set exactly. |
| `0xC61B6` tp+0x71b6 | — | **7** | 7 | the ±10240 window family; **not proposed for edit** |
| `0xC674E` tp+0x774e | — | **1** (`0x43066`) | 1 reader, **0 stores** | but see the FLOAT mirror in `FUN_00043e44` — a lockstep pair, never edit one side |

🛑 **Disagreement adjudication:** in both cases Python is right about the *bytes* and Ghidra is right
about the *live* set — the extra hits are real instructions in a region Ghidra never turned into a
function. This is the **6th recorded instance** of `search_instructions` undercounting in this kit; it
reported `truncated:false` both times. **Neither tool alone is correct: Python finds all encodings,
Ghidra distinguishes live from dead.**

⚠ **Not covered by either method:** register-indirect access (`ld.h 0[rN]` through a table base). The
CAN staging bytes `gp-0x1428/0x1427` are certainly written that way — the mailbox copier is invisible to
both scans. **[BELIEF]** No cal cell above is plausibly reached indirectly (they are scalars, not table
rows), but that is not proven and would need a `movea …,tp,rX` base-pointer sweep to close.

---

## 6. WHAT IS ACTUALLY ON THE CAR (read from the images, not the scripts)

| cell | STOCK | V101 (8×) | **V102 (6×)** | V103 | what it is |
|---|---|---|---|---|---|
| `0xC646C` | 891 | 891 | 891 | 891 | shared Q15 sensor scale — 5 live readers, stock since V57 |
| `0xC6CD0` | 0xFFFF | 7128 | **5346** | 5346 | private forward LKAS gain (V57's cell) |
| `0xC61B2` | 512 | 4096 | **3072** | 3072 | pack_output_clamp, tracks the gain |
| `0xC61B4` | 512 | 4096 | **3072** | 3072 | arb_output_clamp, tracks the gain |
| `0xC61B6` | 10240 | 10240 | 10240 | 10240 | ±0x2800 window — **frozen every build** |
| `0xC674E` | 1024 | 5120 | 5120 | 5120 | soft-EME corridor floor (V25→V38) |
| `0xC407E` | 511 | 511 | 511 | 511 | hard-fault interlock — **do not touch** |
| `0xC6202` | 4762 | 4762 | 4762 | 4762 | governor flat nominal — **frozen every build** |
| `0xE4180`/`0xE51A8` Y | 15360 | 16384 | 16384 | 16384 | setpoint-limit surface (V38) |
| `0x2A1F0` disp | `746c` | `7cd0` | `7cd0` | `7cd0` | V57 decouple, in force |

**[EVIDENCE]** — all read little-endian directly from the `_plain_image.bin` files.

---

## 7. VERDICT ON THE SIBLING'S "NULL OPERATION" CLAIM

**Conclusion: AGREE. Reasoning: REFUTED — it is wrong in a way that would matter if the gain ever
exceeded 8192.**

Verified true, item by item:
- ✅ `0x526cc sxh r6`, full int16, no mask — **confirmed** (decompile + `e600` at `0x526cc`).
- ✅ `movea -0x4000` / `shl 0x2` / `subr r0` / `movea 0x4000` / clamp / `st.h -0x69ae,gp` — **confirmed
  byte-for-byte** at `0x526ce`–`0x526f2`.
- ✅ `4096 × 4 = 16384` exact — **confirmed**; the clamp literal is `0x4000`.
- ✅ counts per wire LSB 0.109 / 0.435 / 0.653 / 0.871 / 1.000 — **confirmed**, they are `GAIN/8192`.
- ✅ the `sar 0x1` proposal at `0x526d2` giving 0.109 — **arithmetic confirmed**, encoding `a132`
  **independently round-tripped**.
- ⚠ `STEER_MAX` provenance and the wire-density statistics were **not re-verified** — they are
  openpilot-side and rlog-side, outside this trace. Flagging, not disputing.

**The error.** The sibling wrote that `arb_command` is *"linear and one-to-one in the wire code,"* so the
deliverable-output count is capped by the transmitted-code count. **It is not one-to-one — it is
many-to-one**, because of `sar 0xf` at `0x2a202`. At the on-car 6×, **8,193 wire codes collapse onto
5,347 outputs**: 35 % of openpilot's transmitted distinctness is already being discarded *today*, before
anyone widens anything.

That inversion matters:
- The sibling's rule predicts widening the wire always helps once the clamps are opened. **The true rule
  — `N = GAIN + 1` for `GAIN ≤ 8192` — predicts it helps only above gain 8192,** i.e. above 9.2× stock,
  which the `0xC674E > clamp` rule already forbids at 10×.
- Under the sibling's rule, going 6× → 8× *coarsens* the command. Under the true rule it **refines** it
  (5,347 → 7,129 addressable levels) while raising authority. **The kit should not be told that raising
  the gain costs resolution — it does not.**

**Cost of the both-sides fix, for the operator to rule on (presented, not recommended):**
| | |
|---|---|
| firmware side | 2 bytes in place at `0x526d2`, `c2 32` → `a1 32`, plus the `0xC6FFC` CRC. Same length, no cave, no new instruction. |
| openpilot side | `CarControllerParams.STEER_MAX` 4096 → 32760 (`interface.py:114-115` `lateralParams.torqueBP/torqueV`) — **barred by `memory/feedback-no-openpilot-side-modifications.md`** |
| measured benefit | **ZERO additional torque levels. Same 7,129-value output set, same 1-count minimum step.** |
| new risk | openpilot's slew limiter is in normalized units; an 8× wider `STEER_MAX` with an 8× finer LSB leaves counts/tick unchanged — neutral on the limit-cycle concern, but it makes every openpilot-side rate constant mean something different, on the one instrument the kit uses to measure the car. |

⇒ **Recommendation: build nothing from this. Keep `0x526d2 = c232` and `STEER_MAX = 4096`.**
If the operator wants the resolution question closed permanently, the sentence to remember is:
**the firmware can express `GAIN + 1` distinct LKAS torque levels and openpilot can already address every
one of them.**

---

## 8. OPEN ITEMS

1. **The felt "coarseness" is unexplained by amplitude quantisation.** **[BELIEF]** the rate path
   (openpilot slew in normalized units, scaling with gain) is the better candidate. Closing it needs a
   within-episode readout of commanded-vs-delivered slope during the symptom, not another gain cut.
2. **Register-indirect readers of the cal cells** — not swept. Would need a `movea …,tp,rX` base-pointer
   enumeration over `tp+0x6000..0x7FFF`.
3. **`0xE51A8`'s X axis is speed** is **[BELIEF]**, anchored only on `0xC62EA` = 320 ≈ 5 km/h. One
   `gp-0x674e`-style static read, or a decompile of the abscissa's producer, would make it EVIDENCE.
4. **Is 1 arb count actually below the motor's own resolution floor?** The FOC current loop and its
   ADC/current-sense scaling were not traced (still OPEN from `FEASIBILITY-8X-LKAS.md` item 1). If the
   current loop quantises more coarsely than 1 arb count, the resolution headroom is even larger than
   stated — it cannot be smaller.
