# TRACE 2026-09-30 — inputs and homes for a speed-scheduled, driver-bled angle-loop cave

**Agent:** `tracer-speed-ram` (firmware-codepath-tracer), subagent of `team-lead` / `main`.
**Goal served:** THE GOAL (2026-09-30) — a 1 kHz firmware inner loop on steering angle in the LKAS lane
`FUN_00028ea6`, with a SPEED-SCHEDULED proportional gain and a bounded integral term that BLEEDS ON DRIVER
TORQUE, as the smallest verified cave. This trace covers the loop's **inputs** (speed, driver torque), the
**LERP machinery** a speed schedule can reuse, and **where the cave's state and code can live**. The angle
signal itself and the hook site are other tracers' surfaces (`tracer-angle`, `tracer-hook`).

**Tooling.** GhidraMCP only for disassembly and decompilation (`decompile_function`, `disassemble_bytes`
with `dry_run:true`, `search_instructions`, `get_function_callers/callees`). No mutating Ghidra call was
made and nothing was saved. Python (`bin_decompile` env) for every byte-level census, CRC walk and boot-value
read. **Programs:** `code.bin` (stock) for items 1–3. For items 4–5 the **V295 image bytes** were read
directly in Python. Ghidra cross-checks for items 4–5 used the open `_v294_…` program. Python shows that
V294 and V295 differ in exactly two places, the cal cell `0xC63EA` (2 bytes) and its CRC trailer `0xC6FFC`
(4 bytes), so the V294 program is code-identical to V295.

**Image on the car:** `_v295_V295-V294BASE-ACCELTRIM.B1050-…_plain_image.bin`,
sha256 `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed` (matches the record).

**Constants.** `gp = 0xFEDF8000`, `tp = 0xBF000`. Anchor: `0xC646C` reads 891 on stock and V295 (the
known 1.000× forward scale) ⇒ `tp + 0x746C = 0xC646C`, no off-by-0x1000.

Every claim is marked **EVIDENCE** (method given) or **BELIEF**.

---

## 1. Vehicle speed

### 1.1 The word to read: `gp-0x6a5e` (unsigned, 64 counts per km/h)

**EVIDENCE (Ghidra decompile + disasm of `FUN_00028ea6`, stock).** The LKAS lane already reads the speed
itself, at function entry:

```
0x28EAE  ld.bu  -0x67f4,gp,r11      ; speed-voter VALID flag
0x28EB2..0x28F08                    ; four wheel channels gp-0x6a44/40/3c/38 and the 0x158 speed gp-0x6a46,
                                    ; each tested (x + 0x1900) < 0x9601  <=>  -6400 <= x <= 32000
0x28F0E  ld.hu  -0x6a5e,gp,r10      ; bytes e4 57 a3 95   <-- the voted speed, UNSIGNED halfword
0x28F12  addi   -0x7d01,r10,r0
0x28F16  setfnc r29                 ; r29 = (speed < 0x7D01)
0x28F1C  mov    0,r29 ; ld.hu -0x6a5e,gp,r10   ; any channel bad or gp-0x67f4 != 1 -> r29 = 0
```

`r29` is Honda's "speed valid" flag, and it requires **all four wheel channels** in range. `r10` holds the
speed only briefly, because it is overwritten before the PID block. **A cave must reload it.**

**Encodings, each validated against an existing V295 instruction with the same bytes (Python):**

| load | r6 | r7 | r10 |
|---|---|---|---|
| `ld.hu -0x6a5e[gp]` ✅ recommended | `e4 37 a3 95` (@0x36FF0) | `e4 3f a3 95` (@0x344E0) | `e4 57 a3 95` (@0x28F0E) |
| `ld.h  -0x6a5e[gp]` | `24 37 a2 95` | `24 3f a2 95` | `24 57 a2 95` (@0x3493C) |
| `ld.bu -0x67f4[gp]` (valid flag) | `84 37 0d 98` (@0x3D4F6) | `84 3f 0d 98` (@0x2B6C4) | `84 57 0d 98` (@0x22026) |

General form: `ld.hu disp[gp], rX` = hw1 `(X<<11)|0x07E4`, hw2 `(disp & 0xFFFE)|1`. `ld.h` = hw1
`(X<<11)|0x0724`, hw2 `disp & 0xFFFE`. The value is 0..32000 (see 1.3), so `ld.h` and `ld.hu` give the
same number. Honda's own idiom is `ld.hu`.

### 1.2 Units and scale — 64 counts per km/h

**EVIDENCE (decompile of `FUN_00053216`, stock).** Each wheel channel is `raw * 0x29 >> 6` (×41/64), with
`0x7FFF` as SNA, from the four extractors `FUN_00021646/22/9E/72(gp-0x13e0)`. The 0x158 speed (`FUN_000522FE`,
kit memory) uses the same `×41>>6`. With the Honda DBC raw unit of 0.01 km/h (**BELIEF** — DBC, not firmware),
that gives 64.06 counts per km/h. Three in-firmware cross-checks, all from kit memory and none re-derived this
session, support exactly 64:
- the limp-home arm writes `km/h_byte << 6`;
- `FUN_0004fbde` does `sar 6` to recover integer km/h;
- the LERP speed axes divide by 64 into round km/h.

⇒ **1 count = 1/64 km/h = 0.004340 m/s; 1 m/s = 230.4 counts.** The 0..32000 range is 0..500 km/h.

### 1.3 What the voter does — `FUN_00041eec`, sole writer of all three words

**EVIDENCE (decompile, stock).**

- **Inputs.** The four wheel channels and the 0x158 speed. Each is abs'd first, so the output is a
  **magnitude**, never negative. A channel is valid when `(x+0x1900) < 0x9601`.
- **Vote.** The vote picks the valid channel closest to the previous output. When two or more wheels are valid
  and their spread is under a speed-scaled tolerance (`tp+0x7318`=640, times a `gp-0x6a10` term), it takes the
  wheel **mean** instead. The result is clamped to ≤ `0x7D00` = 32000.
- **Slew.** The result is then slew-limited against the 32-bit state `gp-0x3584`:
  - **down:** `LERP(0xC6842: X=[0,31808,31872,31936,32000], Y=27 flat)` ⇒ **27 counts per update**;
  - **up:** `LERP(0xC685A: X=[5504,6400,8000,11200,17600], Y=[16,14,11,8,5])` ⇒ **16 counts per update
    below 86 km/h**, falling to 5 above 275 km/h. Both tables are byte-identical on stock and V295.
- **Stores, all lockstep-shadowed** (`gp-0x4caa/-0x4cae/-0x4cb0`; a mismatch calls `FUN_0006b9fa`):
  - `gp-0x6a5e` = the slew-limited vote. **One writer, `st.h` @0x42342** (Python scan: one `st.h` and
    51 readers on V295).
  - `gp-0x6a62` = a variant that reads **`0xFFFF` whenever the 0x158 channel is invalid or fewer than
    `cal 0xC6501 = 3` wheels are valid**.
  - `gp-0x6a64` = a second slew (27 counts per update, `tp+0x74EE`) with a floor of 640.
- **Validity flag `gp-0x67f4`** (writers `0x4218A`/`0x421A0`) goes to 0 when no channel at all is valid. It
  goes back to 1 once the new vote is within 0x40 of the previous output.
- **Fault value.** When no channel is valid, the vote starts at **`cal 0xC631C = 5120` (80 km/h)** and
  `gp-0x6a5e` **slews toward 80 km/h**, not to 0. Consumers that care gate on `gp-0x67f4`; e.g.
  `FUN_0003ad74` substitutes `cal 0xC6314 = 5120`.
- **Boot value** (`.data`, flash `0x86260 + off`): `gp-0x6a5e` boots **0**, `gp-0x6a62`/`gp-0x6a64` boot
  **0xFFFF**, and the wheel and 0x158 channels boot **0x7FFF** (SNA). `gp-0x67f4` boots 0.

### 1.4 Update period and ordering vs `FUN_00028ea6`

- **EVIDENCE (`get_function_callers`):** the only caller of `FUN_00041eec` is **`FUN_00022ca0` = RTOS
  task 5**, priority 2.
- **EVIDENCE (Python `jarl` decode of `FUN_0002214a` = task 1, priority 6, control at `0x22522 → 0x28EA6`
  found):** `FUN_00028ea6` runs from task 1.
- **Kit memory, not re-derived:** task 5 = **100 Hz** and task 1 = **1 kHz**
  (`reference_accord_task5_100hz_live_verified_full_producer_census`,
  `reference_accord_rtos_task_table_and_rate_scheduler`).

⇒ The 1 kHz lane sees `gp-0x6a5e` **constant for ten ticks, then a step**, and **0–10 ms stale** plus the
task-5 run time. The store is a single `st.h`, so a torn read is impossible.

### 1.5 Which of the three to read

**Recommendation: `gp-0x6a5e` via `ld.hu`, gated on `gp-0x67f4 == 1`** (and optionally `< 0x7D01`).
- `gp-0x6a62` reads 0xFFFF unless at least three wheels are valid, so it fails closed in a way that would
  silently drop the schedule.
- `gp-0x6a64` is floored at 640 and slewed a second time.

⚠ **Do not gate the cave on Honda's `r29`.** `r29` requires all four wheel channels valid (see the open item
in §6), and a cave that inherits it could be permanently disabled on this car.

### 1.6 Integer mirror (exact)

```python
def voter_slew(vote, prev):                      # FUN_00041eec tail, per 10 ms update
    def lerp(x, X, Y):                           # clamp-then-walk, int division truncates toward 0
        if x <= X[0]: return Y[0]
        if x >= X[-1]: return Y[-1]
        i = next(k for k in range(1, len(X)) if X[k] > x)
        return int((Y[i]-Y[i-1])*(x-X[i-1]) / (X[i]-X[i-1])) + Y[i-1]
    down = lerp(prev, [0,31808,31872,31936,32000], [27]*5)
    up   = lerp(prev, [5504,6400,8000,11200,17600], [16,14,11,8,5])
    if vote < prev:
        return max(vote, prev - down) if down < prev else vote
    return min(vote, prev + up)
```

---

## 2. Existing speed-indexed gains, and the LERP machinery

### 2.1 There is NO callable LERP helper

**EVIDENCE.**
- `get_function_callees(FUN_00028ea6)` = `FUN_00016de6` (DTC), `FUN_0001cba6` (checkpoint) and
  `FUN_00046ea6` (a fault-bit test). None of them interpolates.
- The decompile shows **every** table lookup in the function **inlined**: the 0xCB844 envelope, the
  gp-0x6b2c lane, the Kp `0xCB994`, the Kd `0xCB7D4`, the setpoint `0xC9A88`, and the four taper arrays.
- The 18 most-called small helpers (the `0x49xxx` cluster and others) were checked by decompile. They are
  clamps, string routines and lookups, not interpolators.
- `FUN_0003c6fc` interpolates, but its table is hard-coded (`tp+0x78B4`), so it is not generic (kit memory).

**The template to copy is Honda's own inline LERP at `0x28FC8–0x29030`** (the 0xCB844 envelope, 26
instructions, 104 bytes):

```
0x28FC8 ld.bu -0x674e,gp,r12 ; variant index
0x28FCC mov   0xcb844,r8     ; pointer array
0x28FD2 shl 2,r12 ; add r8,r12 ; ld.w 0[r12],ep ; ld.w 0[r12],r8   ; ep = r8 = record
0x28FE0 sld.hu 0x2[ep],r16   ; X[0]
0x28FE2 addi 0x14,r8,r8      ; r8 -> Y[0]  (9-knot record: +0 count, +2..+0x12 X, +0x14..+0x24 Y)
0x28FE8 cmp r16,r10 ; bh     ; x > X[0]?  else r16 = Y[0]
0x28FF2 sld.hu 0x10[ep],r13  ; X[last] (ep already +2) ; cmp ; bnc -> r16 = Y[last] (ld.hu 0x10[r8])
0x29008 walk: sld.hu 2[ep] ; add 2,r8 ; add 2,ep ; cmp ; bnc   ; unsigned compares
0x29012 r13=Y[i-1] r16=Y[i] r11=X[i-1] r14=X[i]
0x29020 sub r13,r16 ; sub r11,r12 ; mul r12,r16,r0 ; sub r11,r14
0x2902C divq r14,r16,r0      ; r16 = (dY*(x-X0)) / dX   (dst != src: no Ghidra divq bug here)
0x29030 add r13,r16          ; + Y[i-1]
```

- **Registers** used: `ep, r8, r10` (x), `r11, r12, r13, r14, r16`, and `r7` in the walk.
- **Convention:** X is ascending `u16`; the compares are unsigned; the result clamps to `Y[0]` below `X[0]`
  and to `Y[last]` at or above `X[last]`.
- **Knot count is hard-coded** (`+0x10`/`+0x12` offsets); the `count` field is never read.
- ⚠ It uses **`ep`**. A cave copying it must not be hooked where Honda holds a live `ep`, or it must save
  and restore `ep`.

**BELIEF (design advice):** a cave does not need `divq`. A 2–4-knot schedule with precomputed slopes
(`y = Y0 + ((x - X0) * S) >> k`, clamped at the ends) needs about 8–14 instructions instead of 26, with no
divide-latency variation. Either way, place the new table **inside the cave region** (block `0xC4FFC`, see §5)
so the build dirties no extra CRC page.

### 2.2 Census of speed-indexed lookups reachable at the 1 kHz lane

| # | where | X axis | output | rate | stored in RAM? | stock / V295 values | usable as the cave's schedule? |
|---|---|---|---|---|---|---|---|
| A | `FUN_00028ea6` @0x28FC8, `0xCB844[variant 7]` = rec `0xE51A8` | `gp-0x6a5e` | envelope on `gp-0x69ae` (setpoint clamp) | 1 kHz | **no** (r16 → r22, register only) | X = 3200…8320 (50–130 km/h); Y **15360 flat (stock)**, **16384 flat (V295)** | **no** — flat, not stored |
| B | `FUN_00028ea6` gp-0x6b2c lane, `tp+0x7736` | `gp-0x6a5e` | `gp-0x6b2c` | 1 kHz | yes | X=[0,31872,31936,32000], **Y = 0,0,0,0** — and gated by `gp-0x6809 == 1`, which has zero writers (kit memory) | **no** — identically 0 |
| C | `FUN_0003ad74` gain_A (r26 lane), static recs `tp+0x7A68/7C/90/A4` | `gp-0x6a5e` if `gp-0x67f4==1`, else 5120; breakpoints `0xC6010` = [0,640,3200,6400] = 0/10/50/100 km/h | **`gp-0x6e28` = Y[0] of a RAM table** (`gp-0x6e30` X, `gp-0x6e28` Y, 4 each) | **100 Hz** | **yes** | Y[0] = 3072 / 3072 / 2664 / 2560 (Q10 = 3.00×→2.50×) | **possible but NOT recommended** — see below |
| D | `FUN_0003ad74` gain_B (r24 lane), `0xCBF5C/0xCC044/0xCC12C/0xCC214[mode]` | same | **`gp-0x6e38` = Y[0]** (`gp-0x6e40` X) | 100 Hz | yes | mode 10 on V295: 3072 / 2561 / 2305 / 2151 | same as C |
| E | `FUN_00034350` FactorC `0xC9E9C[mode]` (mode 10 → `0xD27BC`) | `gp-0x6a5e` | a factor inside the damper product → `gp-0x6bd0` | 100 Hz | no (local) | Y=[0,235,430,877] at 35/60/80/140 km/h | no |
| F | `FUN_00034a72` LERP3 `PTR_LAB_000ca154[mode]` | `gp-0x6a5e` | a factor inside `gp-0x6bbe` | 100 Hz | no (local) | — | no |
| G | the voter's own up-step LERP (§1.3) | `gp-0x6a5e` | slew step | 100 Hz | no | 16→5 | no |

**Verdict.** Only C and D store a pure function of speed in RAM. Both are **100 Hz**, both are
**owned by the r24/r26 derivative lane's calibration**, and both have a **narrow range** (×1.2 for C, ×1.43
for D). A cave that multiplied by them would inherit any future r24/r26 cal edit as a silent change to the
angle-loop gain. **Recommendation: a dedicated inline schedule over `gp-0x6a5e`** (§2.1), with its own
table in the cave block.

C/D addressing, if ever wanted: `ld.h -0x6e28[gp]` (Honda's reader @0x3AAE4 `24 47 d8 91` for r8) and
`ld.h -0x6e38[gp]` (@0x3ABB4 `24 57 c8 91` for r10). Writers are indexed (`st.h rX,-0x6e28[r12]` with
`r12 = gp + 2i`, @0x3AF7A…) and invisible to a plain gp scan.

---

## 3. Driver torque for the I bleed

### 3.1 What the live override fade reads: `gp-0x4f60` (signed int16)

**EVIDENCE (disasm `FUN_00028ea6`, stock and V295 bytes identical):**
```
0x28F26  ld.h  -0x4f60,gp,r15     ; 24 7f a0 b0    driver torque, SIGNED
0x29048  mov r15,r7 ; sar 5,r7 ; bp ; subr r0,r7  ; |t| >> 5  (abs AFTER the shift)
0x29064  cmovc ... ; 0x29068 st.b r8,-0x682f,gp  ; gp-0x682f = min(|t|>>5, 255)   (the taper index)
```
The live post-PID fade (the `0xCBBC4` arm, selected because openpilot sends the 0xE4 byte-2 field as 0) and
the A/B Y-taper both index **`gp-0x682f`**. That cell has 2 writers (`0x29068`, plus `0x290B8` which writes 0
on the gate-fail path) and 10 readers, by a Python dual-encoding scan that agrees with kit memory.

### 3.2 Producer, period, ordering

**EVIDENCE.**
- **Writer.** `FUN_0007f3f8` (decompiled) and `FUN_0007ec34` are the only writers; there are 5 `st.h`
  sites on V295 (`0x7F2EA`, `0x7F934`, `0x7F9C8`, `0x7FCE6`, `0x7FD1A`).
- **Valid path.** The valid path is `t = clamp(gp-0x6b50 + (raw * gp-0x698c) >> 10, ±gp-0x4f54)`,
  enabled by `cal 0xC63C3`. There is **no filter**.
- **Fault path.** On a fault path it **writes 0**.
- **Lockstep shadow.** `gp-0x4486`.
- **Caller and ordering.** `FUN_0007f3f8`'s caller `FUN_0006bb08` is called from task 1 at **`0x221E0`, before
  `0x22522 → FUN_00028ea6`**. ⇒ the value is **fresh in the same 1 kHz tick**.

### 3.3 Units and sign

**EVIDENCE (V295 bytes at 0x55C50 = stock):**
`ld.h -0x4f60,gp,r9 ; mulhi 0x7d,r9,r6 ; sar 7,r6 ; subr r0,r6 ; zxh r6` ⇒
**CAN 0x18F (399) `STEER_TORQUE_SENSOR` = −floor(gp-0x4f60 × 125/128)** ⇒ `gp-0x4f60 ≈ −1.024 × wire`.
The firmware's sign is opposite to the wire field. **No N·m scale is known** in the kit (BELIEF: none
derivable from the image).

### 3.4 Ready-made words a cave can read

| word | meaning | writer | encoding (validated against V295 bytes) |
|---|---|---|---|
| `gp-0x4f60` | signed torque | `FUN_0007f3f8` | `ld.h`: r6 `24 37 a0 b0` (@0x2D9A2), r7 `24 3f a0 b0`, r15 `24 7f a0 b0` (@0x28F26) |
| **`gp-0x4f68`** | **`|gp-0x4f60|`, saturated at 0xFFFF** (one writer `st.h` @0x7FECA, shadow `gp-0x448c`) | `FUN_0007f3f8` tail | `ld.hu`: r6 `e4 37 99 b0` (@0x35CF8), r10 `e4 57 99 b0` (@0x2CCBA) |
| `gp-0x682f` | `min(|t|>>5, 255)`, **byte**, written THIS tick at 0x29068 | `FUN_00028ea6` | `ld.bu` **odd** disp: r7 `a4 3f d1 97` (@0x2A3FA); general hw1 `(X<<11)|0x07A4`, hw2 `0x97D1` |

⭐ For a bleed term the cleanest input is **`gp-0x4f68`** (no abs needed, full resolution).
`gp-0x682f` is 32× coarser, but it is exactly what Honda's own override uses.

### 3.5 Is a torsion-bar twist available as a separate word?

**EVIDENCE + BELIEF.**
- `gp-0x4f60` **is** the torque-sensor output, and a torque sensor measures torsion-bar twist. No second,
  angle-of-twist word exists downstream of it.
- Upstream, `FUN_0007f3f8` builds the candidate from per-channel raw tracks: `gp-0x5060[ch] - gp-0x5064[ch]`
  and `(gp-0x5074[ch] - gp-0x5068[ch]) * gp-0x507c[ch] >> 10`, with the channel select `gp-0x27fa`.
  **BELIEF:** these are the dual-track sensor raw values (pre-gain, pre-offset). Their identity is not pinned,
  and they are not recommended for a cave.
- A lagged copy exists: `gp-0x3d34` (32-bit IIR, `a=0xC63E2`, `b=0xC63E4`) inside `FUN_00028ea6`, with
  its rate `gp-0x6830`.

---

## 4. GATE 1 RAM census (V295 image)

### 4.1 Method — five independent methods, every scanner positive-controlled

1. **Ghidra `search_instructions`** on the V294 program (171,309 instructions, code-identical to V295) and on
   `code.bin`, by operand text.
2. **Python gp-relative decoder, every halfword alignment of the whole image.** It covers:
   - Format VII `ld.b/ld.h/ld.w/st.b/st.h/st.w`;
   - `ld.bu` with the odd-displacement `0x3D` field and `hw2[0]=1`;
   - `ld.hu` (`0x3F`, `hw2[0]=1`);
   - Format VIII `set1/not1/clr1/tst1`;
   - the **6-byte disp23** loads and stores (`0x3C/0x3D`, `reg2=0`, `hw2[0]=1`, suffix-decoded);
   - **base constructions** `movea/addi imm,gp,rX`;
   - `mov imm32` of `0xFEDFxxxx`.
3. **Indexed-gp sweep.** Any load or store with a **non-gp base** whose displacement lies in the band. This
   catches Honda's `add gp,ep ; st.b r10,-0x6e10[ep]` idiom, which method 2 is blind to.
4. **`movhi 0xFEDF` absolute sweep.** Every use of the register within 128 bytes (ld/st/bit-op/movea/addi/ori).
5. **Raw LE32 literal scan** of every RAM address `0xFEDF0000–0xFEDFFFFF` at every byte alignment. This covers
   the CAN RX descriptor tables, DMA address literals and pointer tables.

**Positive controls, all PASS:**
- `ld.hu -0x6a5e` @0x28F0E; `ld.h -0x4f60` @0x28F26; `st.w -0x3d30` @0x28FA8; `ld.w -0x3d30` @0x28F7C.
- `st.b -0x682f` @0x29068; `ld.bu -0x67f4` @0x28EAE.
- **6-byte `st.w -0x42fc` @0x149DC.**
- `gp-0x682f` → exactly 12 accesses (2 W + 10 R), which equals kit memory.
- **Flown-cave controls:**
  - the V292 image finds `ld.hu/st.h -0x6d74` @0xC4C08/0xC4C12 and `-0x6d72` @0xC4C18/0xC4C22;
  - the V289 image finds all four V289 cells;
  - the V288r2 image finds `gp-0x6a32` at 0xC4BDE/0xC4C0E/0xC4C24/0xC4C28.

### 4.2 Results

| candidate | width free | flown with? | Python direct (stock / V295) | Ghidra operand text (V294 = V295 code) | base-ptr / indexed / movhi / LE32 | boot value (`.data` copy) | verdict |
|---|---|---|---|---|---|---|---|
| **`gp-0x6a32`** (0xFEDF15CE) | 2 B | **V288r2 flew** (state word) | **2 writers**: `st.h r16` @**0x29D72** (live, the assist-map-setpoint publish, engaged path only) + `st.h r9` @0x2AC68 (in uncalled twin `FUN_0002a93a`); **0 readers** | 2 matches, same two | none | 0 | **W1R0, not free.** Usable **only** by a cave that **replaces the 0x29D72 store** (V288r2's method). Neighbours `gp-0x6a34` (W @0x290CA, R @0x2A0CA) and `gp-0x6a30` (W @0x2DD52) are occupied. |
| **`gp-0x6c44`, `-0x6c40`, `-0x6c3c`** (+ `-0x6c3a`) (0xFEDF13BC–13C7) | 12 B exactly | **V289 flew** (notch state + FLAG; ⚠ V289 packed its FLAG halfword `-0x6c3a` into the upper half of the `-0x6c3c` word, masking `& 0x3FFF` — by design, ADV-V289-A) | **0 / 0** | 0 (the only `-0x6c4x/-0x6c3x` hits are `-0x6c48`, `-0x6c4c`, `-0x6c38`, `-0x6c36`, `-0x6c34` — neighbours) | none within 0x40 below; no movhi; no LE32 | 0 | **FREE, flight-proven.** Bounded by `gp-0x6c48` (ld/st.w, 6 sites) below and `gp-0x6c38` (`st.h` @0x4172E/0x4199A) above — **no slack**. |
| **`gp-0x6d74`, `gp-0x6d72`** (0xFEDF128C–128F) | 4 B | **V292 flew** (halfword remainders) | **0 / 0** | 0 | none (see 4.3) | 0 | **FREE, flight-proven.** |
| **NEW `gp-0x6d70`** (0xFEDF1290, word-aligned) | 4 B | never used | **0 / 0** | 0 (`-0x6d6`: zero matches; `-0x6d7`: only `-0x6d78`/`-0x6d7c`) | none | 0 | **FREE by every static method.** Not flight-proven. |
| **NEW `gp-0x6d6c`** (0xFEDF1294) | 4 B | never used | **0 / 0** | 0 | none | 0 | **FREE by every static method.** Not flight-proven. |
| (whole run `gp-0x6d74..gp-0x6d2d`) | **72 B** | — | 0 / 0 | 0 | none | all 0 | free run, matches the 2026-09-09 V290 census |
| (rejected alt `gp-0x692c`) | — | — | 0 / 0 | — | **`movea -0x6944,gp,ep` @0x45630 and `-0x693c,gp,ep` @0x45650** are within `sld/sst` reach | 0 | **not recommended** |

### 4.3 Register-indirect adjudication for the 72-byte run (every base within the 0x100-byte `sld/sst` reach below it)

**EVIDENCE (Ghidra `disassemble_bytes dry_run`):**

| site | base | access | max reach | reaches the run? |
|---|---|---|---|---|
| `0x52D9C`/`0x52DA4`/`0x52E12`/`0x534A0` | `ep = gp-0x6e14 / -0x6e10` + `r28`/`r26` (wheel index; `FUN_00052d5e` decompile: `1 << (3 - i)` ⇒ i ∈ 0..3) | `sld.bu 0[ep]`, `st.b -0x6e10[ep]` | gp-0x6e0d | no |
| `0x3AAD8`/`0x3AF64`/`0x3ABA4`/`0x3AE42` | `ep = gp-0x6e30 / -0x6e40` | `sld.h 2[ep]` walk, `sst.h 0[ep]`, loop bound = record count = **4** (all 28 modes, Python) | gp-0x6e22 | no |
| `0x5645E` | `ep = gp-0x6e20` | `sld.w 0[ep]` | gp-0x6e1d | no |
| `0x14766` | `ep = 0xFEDF11B0` | boot `.data` copy | whole `.data` | **yes, boot only** — writes the flash bytes (all 0) |
| `0x58068` etc. | `mov 0xFEDF1194` (+ `ep*4`, index = byte `0xFEDF3CDC`) | function-pointer table; `0xFEDF11AC/11AD` are separate byte objects ⇒ table ≤ 6 words | 0xFEDF11AB | no (BELIEF on the bound, from object layout) |
| `0x197E0` / `0x1987C` | `movhi 0xFEDF` + `clr1 7, 0x1289` / `clr1 0, 0x1288` | byte bit-ops on `gp-0x6d77/-0x6d78` | 0xFEDF1289 | no — **the run's lower neighbour is the live 32-bit `gp-0x6d78`** (12 Ghidra `ld.w` readers, written @0x197CA, plus these absolute bit-ops) |

Non-gp-base hits at 0x6C4B4–0x6C4E4 (`r17 = movhi 0xFF81` = peripheral space), 0x71E26 and 0x31C8A
(mid-instruction misdecodes) were adjudicated **false**.

### 4.4 Power-on init

**EVIDENCE (V295 bytes equal stock for `0x146C0–0x14810`; `.data` source `0x86260–0x8AB18` equal to stock):**
1. The zero-clear loop at **`0x146C0`** wipes `0xFEDEC000–0xFEDFFFFF`.
2. Then the **`.data` copy at `0x1475C`** writes flash `0x86260–0x8AB18` → `0xFEDF11B0–0xFEDF5A68`
   (`gp-0x6E50 .. gp-0x2598`).

Every candidate is in `.data`, and every boot byte is **0x00** (flash offsets `0x8667E`, `0x8646C`, `0x8633C`,
`0x86340`, `0x86344`). None is within stack reach (stack = `0xFEDEC000–0xFEDEF91C`). **No runtime clear
routine covering any candidate was found** by methods 2–5. A cave can choose a non-zero boot value by editing
the flash `.data` image at `0x86260 + (addr − 0xFEDF11B0)`, which sits inside the main CRC block.

### 4.5 Residual — what static methods cannot exclude

A computed-pointer chain more indirect than one `movea`/`mov imm32`/`movhi` base is not excludable by any
static scan. The `gp-0x1500` precedent was a CAN RX buffer that the descriptor tables point at. **None of the
candidates appears as an LE32 literal anywhere** (descriptor or DMA tables included).

The evidence classes differ:
- **6d74/6d72/6c44..39** have flown (V292/V289) **live for whole drives** without an attributable fault.
  That is the strongest evidence available.
- **6d70/6d6c** are "virgin" class. Per `reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram`,
  virgin is the weaker class.

⭐ **Recommendation:**
1. Put the integrator (32-bit) at **`gp-0x6c44`** (flight-proven, word-aligned).
2. Put a second state word at **`gp-0x6c40`**, then **`gp-0x6c3c`** (flight-proven).
3. Fall back to **`gp-0x6d74`** (4 B, flight-proven) before the new `gp-0x6d70/-0x6d6c`.

---

## 5. Code homes in V295

**EVIDENCE (Python on the V295 image; Ghidra dry-run disasm of the tap on the V294 program).**

| home | what is there in V295 | contiguous free | CRC block it dirties (`verify_bootloader_crc.py`, V295 = **49/49 BL, 50/50 full, PASS**) |
|---|---|---|---|
| `0xC4B34–0xC4BD7` | **the V112-lineage telemetry tap, 164 B, in use.** Leaf, scratch r6/r7, reads `gp-0x6ada/-0x6b38/-0x6b94/-0x6b4c` and `ld.w gp-0x3680`, writes `gp-0x1514`/`-0x1511` (CAN 0x14A bytes 4/7 fields), ends with the displaced `movea -0x1518,gp,r6 ; jmp [lp]`. Hook `0x55C0E` = `86 ff 26 ef` (`jarl 0xC4B34`). **No state RAM.** | 0 (occupied) | `[0x13000, 0xC4FFC)` → trailer **`0xC4FFC`** (BL block #49 / full #50) |
| **`0xC4BD8–0xC4FEF`** | **0xFF** | **1048 B** (includes `0xC4C00–0xC4FEF` = 1008 B, the V289/V292 home) | same, **`0xC4FFC` only** |
| `0xC4FF0–0xC4FFB` | block link/trailer fields (`01010101 0000 c600 1300 b200`) | — | **never write** |
| `0x2A174` | **not a cave region** — the V289 hook site in `FUN_00028ea6`. V295 = stock `e5 3f ef 73` (`ld.hu 0x73ee,tp,r7`) | — | `0xC4FFC` |
| `0x28F8E` (V292 hook) / `0x29D72` (V288 hook) / `0x28F4C` | all **stock bytes** in V295 (`f0 3f 20 02` / `64 87 ce 95` / `24 3f aa 95`) | — | `0xC4FFC` |
| `0xC5788–0xC5FF0` (kit memory, 2152 B) | 0xFF | — | **`0xC5FFC`, a block the BOOTLOADER SKIPS** (bridge at 0xC6000) — avoid |
| a new cal table in `0xC6xxx` | — | — | `0xC6FFC` (block #48) — a second CRC; avoid by keeping tables in the cave |

⚠ **V294/V295 changed code next to the V292 hook:** `0x28FA4` is `add r9,r26` on stock and **`subr r9,r26`**
(`89 d1`) on V295 ("FB.DIFF"); `0x29D76` is `shl 5` on stock and **`shl 2`** on V295. A cave reusing those
hook sites must be re-derived against V295's semantics, not V292's.

⇒ **A cave at `0xC4BD8+` plus a hook anywhere in app code dirties exactly ONE CRC word, `0xC4FFC`.** This
holds as long as its tables live in the cave and it does not edit a `0xC6xxx` cal.

---

## 6. Open questions / verification needed

1. **Is CAN 0x1D0 (wheel speeds) actually ingested on this car?**
   - The rlogs carry `0x1D0` on src 1 (`TRACE-2026-08-13-measured-steering-ratio.md`).
   - Kit memory records the RX-descriptor `[+0]` enable for 0x1D0 as 0, with semantics unresolved.
   - If it is not ingested, the wheel channels stay at their 0x7FFF boot value. Then Honda's `r29` is
     **always 0**, `gp-0x6a62` is **always 0xFFFF**, and `gp-0x6a5e` follows the 0x158 speed alone (still
     valid).
   - **Next step:** read `gp-0x6a62` or `r29`'s effect on the wire, or find the descriptor walker. **Design
     consequence either way:** read `gp-0x6a5e` and gate on `gp-0x67f4` only.
2. **Task 5 = 100 Hz** is kit memory, not re-derived this session. If it were wrong the schedule word would
   only be fresher, so it cannot hurt the design.
3. `gp-0x5060/5064/5068/5074` identity as raw torque tracks is **BELIEF**.
4. The `0xFEDF1194` table bound (≤ 6 words) is **BELIEF** from object layout. It sits 0xF8 below the run, so
   reaching the run would need index ≥ 62.

---

## Appendix — the scanner core (Python, reproducible)

```python
# Format VII / VIII / XIV gp-relative decode (reg1 == gp == r4), every halfword alignment
op = (hw1>>5)&0x3f; reg2 = hw1>>11
0x38 ld.b disp16 | 0x39 ld.h (hw2[0]=0) / ld.w (hw2[0]=1) | 0x3A st.b | 0x3B st.h / st.w
0x3C|0x3D with reg2!=0 and hw2[0]=1 -> ld.bu, disp = (hw2 & ~1) | hw1 bit5
0x3F with reg2!=0 and hw2[0]=1     -> ld.hu
0x3E                               -> set1/not1/clr1/tst1 (hw1[15:14])
0x3C|0x3D with reg2==0 and hw2[0]=1 -> 6-byte disp23: d = (hw3<<7)|((hw2>>4)&0x7f), sign-extend 23;
   0x3C: ...0101 ld.b, 00111 ld.h, 01001 ld.w, ...1101 st.b, 01111 st.w ; 0x3D: ...0101 ld.bu, 00111 ld.hu, 01101 st.h
0x30|0x31 imm,gp,rX -> base construction ; mov imm32 (reg2==0, op 0x31) of 0xFEDFxxxx
```
