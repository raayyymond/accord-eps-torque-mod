# TRACE 2026-09-30 — the steering angle `gp-0x6a00` as a 1 kHz feedback operand

Subagent `tracer-angle`, for the orchestrator. Goal box: STATE.md "THE GOAL" (a 1 kHz firmware angle loop
in the LKAS lane `FUN_00028ea6`). Program: **stock `code.bin`** in GhidraMCP. Every function named
below is **byte-identical in V295** (Python slice compare of the stock and V295 plain images, listed in §8).
Python mirror: `analysis-2020accord/studies/angle_loop/angle_signal_mirror.py`.

Constants: `gp = 0xFEDF8000`, `tp = 0xBF000`. Anchor check: `0xC63EA` reads 1560 (stock) and 1050 (V295),
matching V295's build record (567→1050 on V294's base, stock 1560), so the tp mapping is right.

---

## 0. Headline

1. **`gp-0x6a00` is a 100 Hz sample-and-hold, not a 1 kHz signal.** Its only writer runs in RTOS
   slot 4, which the tick dispatcher activates on one tick in ten. A cave in `FUN_00028ea6` would see it
   1 to 10 ms old, a mean of 5.5 ms. **[EVIDENCE]**
2. **Every input to the angle is fresh at 1 kHz.** `FUN_0003bd7c` runs in the 1 kHz task at `0x2224a`,
   before the PID at `0x22522`. It updates the motor-position accumulator `gp-0x6cc4` and the linear angle
   `gp-0x69ca`, and the raw motor position is snapshotted earlier in the same tick. A cave can rebuild
   the angle every tick. **[EVIDENCE]**
3. **Collateral, decision-bearing for the whole rate-loop record:** the PID's own feedback operand
   `gp-0x6a56` (read at `0x28F4C`) is produced by `FUN_0003f776` in the **same 100 Hz task**. The "1 kHz
   rate loop" therefore closes on a 10 ms hold of its feedback. `TRACE-2026-09-10-command-intersample-zoh.md`
   ("no staleness") compared phase masks only and never checked the task rate. Its conclusion is wrong.
   **[EVIDENCE]**
4. **Mode 3 holds for the whole drive in the logged data.** 0x14A byte 4 bit 1 (`gp-0x679b`) can be 1
   only on the mode-3 path with `gp-0x67fe == 2`. It reads 1 in every healthy frame of 2,318,504 frames
   across 91 routes. The only drop is the already-recorded V75 hard fault on route 0x5e. **[EVIDENCE]**
5. `FUN_00028ea6` **does not read `gp-0x6a00` at all.** The brief's "reads at ~0x29D76" refers to the
   feedback-operand hook, which handles `gp-0x6a56`-derived `r26`. **[EVIDENCE]**

---

## 1. Update rate and ordering

### 1.1 The scheduler [EVIDENCE]

| fact | method | evidence |
|---|---|---|
| Tick flag `gp-0x42fc := 1` on interrupt EIIC `0x340` | decompile `FUN_0001492a` | `else if (in_EIIC == 0x340) { *(gp-0x42fc) = 1; }` |
| Flag consumed by `caxi` checkpoints, which call `FUN_00014be4` | disasm `FUN_00022ca0`, decompile `FUN_00086242` | 46 `caxi [gp-0x42fc]` sites in tasks 1/2/5/6 and the idle task |
| Dispatcher activates slot 0 every pass, slot 4 when `c % 10 == 4`, counter `gp-0x4304` wraps at 100 | disasm `FUN_00014be4` | `0x14bf6 mov 0x0,r6; jarl 0x861e0` · `0x14c28 mov 0xa,r7; divq r7,r8,r10; cmp 0x4,r10; bne; mov 0x4,r6; jarl 0x861e0` |
| `FUN_000861e0` (activate) has exactly 5 callers, all in the dispatcher | raw `jarl` byte scan, positive control `0x22522`→`FUN_00028ea6` | `0x14bf8, 0x14c08, 0x14c1e, 0x14c34, 0x14c44` |
| Slot table | Python LE read of `0xBB920 + i*0x30` | slot 0 entry `0x2214A` attr `0x00010607`; slot 4 entry `0x22CA0` attr `0x00050207` |

Priority byte (attr byte 1): slot 0 = 6, slot 4 = 2. **[BELIEF]** that higher is higher priority
(rate-monotonic: the 1 kHz task carries the largest value). Either way slot 0 is activated first in the
same pass, so on an activation tick the PID runs before the angle refresh.

The 1 kHz tick itself rests on the kit's dwell measurement (100 ticks of `0xC64DF` gave 100.00 ms on the
bus, TRACE-2026-09-06 §3.2). Independent corroboration measured this session: 0x14A and 0x18F arrive at
~6000 frames per 60 s segment, i.e. 100 Hz. The prior record places both builders under slot 4
(handler-table slot 10 ← `FUN_00022ca0`, STATE-ARCHIVE-pre-V89). I did not re-verify that handler link
this session.

### 1.2 Call sites [EVIDENCE: raw `jarl` byte scan, positive-controlled; Ghidra `get_function_callers` agrees]

| function | writes | sole call site | task |
|---|---|---|---|
| `FUN_0006bb08` → `FUN_00063818` | `gp-0x4eea = gp-0x4ed8 >> 2` (`0x638f2`) | `0x221e0` | slot 0, 1 kHz |
| `FUN_0006bb08` → `FUN_00065eda` | `gp-0x4ee8 = gp-0x4eea` (`0x65fb0`, only writer) | `0x6bc50` | slot 0, 1 kHz |
| `FUN_0003bd7c` | `gp-0x6cc4`, `gp-0x69d2`, `gp-0x69d0`, `gp-0x69d4`, `gp-0x69ca`, `gp-0x67fe` | `0x2224a` | slot 0, 1 kHz |
| `FUN_00040e7e` | `gp-0x6ce0` (relative accumulator, only when mode ≠ 3) | `0x22426` | slot 0, 1 kHz |
| `FUN_00028ea6` | the LKAS rate PID | `0x22522` | slot 0, 1 kHz |
| `FUN_0003f776` | `gp-0x6a56` (angle rate, the PID's feedback) | `0x22de2` | **slot 4, 100 Hz** |
| `FUN_0003e6d8` | `gp-0x6a00` (only writer, `0x3e758`) | `0x22e32` | **slot 4, 100 Hz** |
| `FUN_000413ae` → `FUN_00040a50` | `gp-0x679c` state, 0x14A angle fields `gp-0x69ec/69ee` | `0x22e9c` → `0x4141e` | slot 4, 100 Hz |

Within slot 0 the order is `0x221e0` (raw snapshot) → `0x2224a` (`FUN_0003bd7c`) → `0x22522` (PID).
Gates: `FUN_0003bd7c` under phase mask `0xd38`, the PID under `0x930`, a subset. So `gp-0x6cc4` and
`gp-0x69ca` are **fresh, same tick**, wherever the PID runs.

### 1.3 Staleness at the PID [EVIDENCE for the structure, BELIEF for the upper bound]

On an activation tick `k`, slot 0 runs first and reads the old value; slot 4 then writes a new one from
the tick-`k` inputs. Ticks `k+1 … k+10` see it. **Age 1–10 ms, mean 5.5 ms.** This assumes slot 4 reaches
`0x22e32` before tick `k+1`. It is preemptible, so a late run adds whole ticks. Mirror result:

| steering | phase cost of the hold | worst |held − fresh| |
|---|---|---|
| 0.5 Hz, ±30° | 1.0° | 1.20° (4 % of amplitude) |
| 2 Hz, ±5° | 4.0° | 0.70° (14 %) |
| 5 Hz, ±2° | 9.9° | 0.70° (35 %) |

At 20 Hz the same hold costs about 40° of phase, which is why the `gp-0x6a56` finding matters.

---

## 2. Units, sign, width, range

### 2.1 Formation [EVIDENCE: decompile then disasm of `FUN_0003e6d8`, `FUN_0003e600`, `FUN_0003bd7c`]

```
d          = gp-0x6cc4 - gp-0x69d0                      # motor counts, 32-bit
gp-0x69d4  = int16( pol * ((((d>>3)*1159)>>8)*900 >> 14) )   # 0x3C000-0x3C030
gp-0x69ca  = int16( base + pol*(...same 32-bit value...) )    # 0x3C090; base = gp+0x6470, or 0 if 0x7FFF
gp-0x3608  = int16( pol * C( pol * (((base<<16)/900)<<9)/1159 ) )  # 0x3E6DC-0x3E712, only when base changes
gp-0x6a00  = int16( gp-0x3608 + pol*C(d) + (gp-0x69ca*128 >> 7) )  # 0x3E722-0x3E758, if gp-0x67fe in {1,2}
gp-0x6a00  = 0                                                     # otherwise
C(x)       = sign(x) * LERP( int16((|x|*45)>>9) ; X 0xC6892, Y 0xC68A2 )   # FUN_0003e600
```

`pol = gp-0x6752 = -1` (the kit's frame converter, recorded as settled three ways in
`reference_accord_gp6752_*`). Cals, LE from the image: `0xC6432` = 900, `0xC613A` = 1159, `0xC64F2` = 128
(byte), `0xC6358` = 2. The LERP knots are X = `[0, 784, 1162, 1503, 1858, 2284, 4340, 11513]` and
Y = `[0, 43, 59, 69, 73, 72, 45, -52]`.

- **Unit: 0.1° of steering-wheel angle per count, signed int16.** The 0x14A packer stores `-gp-0x6a00`
  (mode-3 path, `0x40B08`: `mov r0,r26; sub r14,r26`) with no scaling, and opendbc reads
  STEER_ANGLE = field × −0.1°. So **`gp-0x6a00` = 10 × openpilot's raw steering angle in degrees, same
  sign.** **[EVIDENCE]** for firmware. The opendbc factor comes from the kit's DBC decode.
- **Linear scale:** 32.168 motor counts per 0.1°. At 4096 counts per motor revolution that is 12.73° of
  wheel per motor revolution, a ratio of about 28:1. **[EVIDENCE]** arithmetic. **[BELIEF]** that
  `gp-0x4ee8` is 4096 counts per motor revolution, inferred from the ±0x800/0x1000 wrap.
- **The correction `C` is not small near centre.** It rises 0 → +4.3° over the first 27.7°, so
  **d(`gp-0x6a00`)/d(`gp-0x69ca`) = 1.155 near centre**, then 1.120, 1.083, 1.032, 0.993, 0.963 and
  0.962 outward. **[EVIDENCE]** (mirror, from the knots.) **[BELIEF]** that this is the variable-gear-ratio
  rack shape.

### 2.2 Range and the sentinel [EVIDENCE]

- **No clamp** in `FUN_0003e6d8`: the int32 sum is truncated by `st.h`.
- **`0x7FFF` is never written into `gp-0x6a00`.** That cell has one writer, `0x3e758`. The sentinel goes
  into `gp-0x69ec`/`69ee`/`69ea` only, on the `FUN_00040906(1) == 0xFF && fault bit 13` path
  (`0x40a92`–`0x40aa8`). The 0x14A builder also substitutes it when `gp-0x67fa == 8`.
- **The baseline sentinels are hazards to the value itself.** `gp+0x6470 == 0x7FFF` makes the baseline 0,
  so the angle is relative and `gp-0x3608` becomes −52. `gp+0x6470 == -0x8000` ("never established") is
  **not excluded** at `0x3C076`. It adds −32768, so `gp-0x6a00` wraps to about +32700 (mirror). **A cave
  must gate on `gp-0x679c == 3`**, which excludes −0x8000 through every state handler, or test
  `gp+0x6470` itself.
- Readers that care bound it themselves: `FUN_00040a50` (|a| ≤ 10000 for `gp-0x679b`) and
  `FUN_0002e734` (|a| ≤ 10000 for the 10 Hz history).

### 2.3 The default branch is a different signal [EVIDENCE: `FUN_00040a50` decompile]

When `gp-0x679c ≠ 3`, 0x14A carries `-(pol·lin(gp-0x6ce0))` clamped to ±15120 (±1512.0°). `gp-0x6ce0` is
a relative accumulator from power-on, advanced by `FUN_00040e7e` only while mode ≠ 3. It has no baseline
and no correction. On the first mode-3 pass the packer only sets the latch `gp-0x35bc` and **holds** the
previous field. From the next pass it packs `-gp-0x6a00`. Seen on the wire at the start of route 0x75:
`b4 = 0x65, angle 0` → 10 ms later `b4 = 0x67, angle −93`. **That is a full-angle step on the bus at
mode-3 entry.**

### 2.4 Encodings a cave would use [EVIDENCE: bytes read from the image; generator reproduces them]

```
ld.h -0x6a00[gp], rX   = 24 (rX<<3|7) 00 96      r14: 24 77 00 96 (@0x40aea, @0x2e912)
ld.h -0x69ca[gp], r26  = 24 d7 36 96             (@0x3e722)
ld.w -0x6cc4[gp], r8   = 24 47 3d 93             (@0x3e72a, hw2 bit0 = 1 -> .w)
ld.h -0x69d0[gp], r6   = 24 37 30 96             (@0x3e72e)
ld.h -0x3608[gp], r12  = 24 67 f8 c9             (@0x3e740)
ld.h  0x6470[gp], r14  = 24 77 70 64             (@0x3e6dc, POSITIVE displacement)
ld.bu -0x67fe[gp], r10 = 84 57 03 98             (@0x3e716)
ld.bu -0x679c[gp], r10 = 84 57 65 98             (@0x40a4a, odd disp -> hw1 bit5 form)
```

---

## 3. The gates

### 3.1 `gp-0x679c` — mode [EVIDENCE: all writers + all nine handlers decompiled]

- **One setter, `FUN_00040d38(r6)`** (`0x40d44 st.b r6,-0x679c[gp]`, shadow `gp-0x4c35`). It has 17
  callers, all in the handlers of the dispatcher `FUN_000413ae`. ⚠ The dispatcher's state byte **is**
  `gp-0x679c`: `0x413ba` decodes as `ld.bu -0x679c[gp]` (raw byte scan). Memory
  `reference_accord_engage_sm_full_dispatcher_and_trump_exits.md` claims `gp-0x67DC`, but its own
  displacement −26524 equals −0x679C, as `reference_accord_decider_shared_epilogue_trampoline_anchors.md`
  already flagged. The "engage SM" label in older memories is this angle-reference machine.
- **Into 3:** from state 0 when `gp-0x67fe == 2` and `gp+0x6470 ∉ {−0x8000, 0x7FFF}` (also presets
  `gp-0x35bc = 1`). From 2 when `gp-0x67fe == 2`. From 4 when decider(4) passes and `gp-0x67fe == 2`.
  From 7 and 8 when `gp-0x67fe == 2` and a latch `gp-0x138D` or `gp-0x1390` is set.
- **Out of 3** (`FUN_000410da`): to **1** if `gp+0x6470 == −0x8000`, to **4** if `gp-0x67fe ≠ 2`.
  **Mode 3 is not structurally sticky.** It is exactly "assist substate 2 and a valid absolute baseline".
- **What blocks 3 at power-on:** a never-established baseline (`−0x8000` → state 1, the learning states
  1/5/6/7 with the 4-channel consensus `FUN_000406ae` and decider `FUN_00040d58`), or `gp-0x67fe ≠ 2`.
- **The baseline is set in `FUN_0003c7fc`** (task 5 via `FUN_0003d4a2`): `gp+0x6470 = pol·lin(est −
  gp-0x6cc4)` when |est − `gp-0x6cc4`| ≤ `0xC6354` = 4825, else `0x7FFF`. **[BELIEF]** that `gp+0x6470`
  is non-volatile. Its address `0xFEDFE470` appears in a record table at `0x8B144` next to a size/ID word
  and callback pointers, which is the shape of a data-flash block table. That would explain why mode 3 is
  already up at the first logged frame.
- **Time to 3 after key-on:** not measurable from the logs. 90 of 91 routes are already in mode 3 at the
  first logged frame. Route 0x75 caught the switch 10 ms into logging, with no earlier frames.
  Statically it is time-to-FOC-mode-5 plus at most two 100 Hz passes. `FUN_0003d4a2` (the FOC SM) was not
  decoded.

### 3.2 `gp-0x67fe` — assist substate [EVIDENCE: all 5 writers]

Writers: 4 in `FUN_0003bd7c` (1 kHz) and **1 in `FUN_0003e760`** (`0x3e770`). That fifth writer was
missed by the "exactly 4 writers" memory.

- `FUN_0003bd7c`: FOC mode `gp-0x6772` ≤ 3 or 6–8 → 0, latch `gp-0x6845` cleared. Mode 4/5 with fault
  bit 8 clear, `gp-0x671d < 0xC6500` (= 3), `gp-0x6851 == 0` and latch clear → **2 if mode 5, else 1**.
  Mode 4/5 with any gate failing → 0 and **latch = 1**, sticky until mode drops below 4. Mode ≥ 9 →
  unchanged.
- `FUN_0003e760` (from `FUN_0003e87a`, 1 kHz): if the bitmask `gp-0x676f` (maintained just before
  `FUN_0003d4a2`) is nonzero while `gp-0x67fe ≠ 0` for `0xC62A2` = 100 ticks, it zeroes `gp-0x67fe`,
  `gp-0x69ca`, `gp-0x69d4`, `gp-0x69de` and more, and sets the sticky latch.
- **Whenever `gp-0x67fe ∉ {1,2}`, both `gp-0x6a00` (next 100 Hz pass) and `gp-0x69ca` (same tick) become
  0.** An angle loop would see a step error of the full angle. **A cave must gate its output on
  `gp-0x67fe == 2`.**
- **How often in normal driving: never observed.** 0x14A byte 4 bit 1 is `gp-0x679b`, which
  `FUN_00040a50` sets to 1 only on the latched mode-3 path with `FUN_00040884() ≠ 0`, `gp-0x67fe == 2`,
  |`gp-0x6a00`| ≤ 10000 and `gp-0x6798`. Measured on 395 segments of 91 routes (every third local
  rlog, method: `rlog-tools/lib/rlog_parse.read_messages`, `can` events with `src == 1` and
  `address == 0x14A`, counting `dat[4] & 7` and its transitions; bits 3–7 are cave telemetry and are
  masked off): **2,316,807 frames read bits[2:0] = 7.** The only exceptions are 1696 frames of the recorded V75
  hard fault (route 0x5e, segment 4, 43.02 s, STEER_STATUS → 7, angle → 0x7FFF; see
  `memory/accord/builds/accord-v75-fault-pinned-to-the-frame.md`) and the one cold-start frame on route
  0x75. **This contradicts "`gp-0x67fe` == 1 in 100 % of frames" (V31P): it is 2.** The 100 Hz sampling
  cannot see a drop shorter than 10 ms that leaves the sticky latch clear. That would need FOC mode to
  leave and re-enter 4/5 within one pass.

---

## 4. Integrity monitors and the reader census

### 4.1 Census of `gp-0x6a00` [EVIDENCE: Ghidra `search_instructions` and raw LE scan agree exactly]

Raw scan: disp16 forms and 6-byte forms, plus the absolute address `0xFEDF1600` as LE32 (0 hits).
Positive controls passed: `0x3e758 st.h`, `0x28F4C ld.h -0x6a56`, `0x40aea`, `0x2e912`,
`0x3bf46 st.w -0x6cc4`, `0x3c09a st.h -0x69ca`. **15 accesses: 1 writer, 14 readers, no 6-byte forms,
set-difference empty.**

| readers | function | task | role | torque path? |
|---|---|---|---|---|
| `0x40aea 0x40b04 0x40c68 0x40c78 0x40c92` | `FUN_00040a50` | slot 4 | 0x14A pack; \|a\| ≤ 10000 test for `gp-0x679b` | no |
| `0x2e912 … 0x2ea18` (7) | `FUN_0002e734` | slot 5, 10 Hz | 110-sample history `gp-0x5728` → `gp-0x69f8` → sign used by `FUN_0002fab6` (window statistics, 16-bit status `gp-0x6a9a`) | not traced to torque; outputs open |
| `0x55812 0x55826` | `FUN_000557c8` | CAN TX table `0xB72B4` | CAN 0x722 builder | no |

**No reader is in the 1 kHz task and none writes a torque cell directly.** `FUN_0002fab6`'s outputs were
not followed (§7).

### 4.2 Lockstep shadows [EVIDENCE]

- `gp-0x4c8a` is the shadow of `gp-0x6a00`, written only in `FUN_0003e6d8` (`0x3e74c`/`0x3e752`).
  Readers compare it before use and call `FUN_0006b9fa` on a mismatch.
- `gp-0x4c80`/`gp-0x4c82` shadow the packed `gp-0x69ec`/`69ee`, compare-then-write only inside
  `FUN_00040a50`.
- `gp-0x4c76` shadows `gp-0x69ca`; `gp-0x4d0c` shadows `gp-0x6cc4`; `gp-0x4c78` shadows `gp-0x69d0`.
- **A new reader disturbs none of them. A cave must never WRITE any of these cells.**

### 4.3 Plausibility checks that compare the angle to something [EVIDENCE for the census, BELIEF for "none other"]

- `FUN_0003e462` compares `gp-0x69ca` against `gp-0x6a18` (another estimate, from `FUN_0004012e`)
  through an IIR, with a 1500 = 150° threshold, raising DTC `0x43`. Both inputs are measured angles, so a
  loop that makes the wheel track a setpoint cannot open a 150° gap.
- `FUN_000406ae` / `FUN_0003c7fc` compare `gp-0x6cc4` against the 4-channel consensus at 4825 counts
  (about 15°). The trigger is sensor disagreement, not command tracking.
- **None of the three `gp-0x6a00` readers, and none of its producers, reads an LKAS command or output
  cell** (`gp-0x69ae`, `gp-0x6b38`, `gp-0x6b2e`). So no "assist follows angle" comparator exists on
  `gp-0x6a00`. **[EVIDENCE]** (the decompiles above.)
- ⚠ **`gp-0x69ca` does have torque-path consumers.** 18 accesses, including `FUN_0003fc16` →
  `gp-0x6a10` → FactorD in `FUN_00034350` and the `FUN_0003b8f6` LERP, per
  `reference_accord_fun34350_*` and `reference_accord_angle_position_scale_*`. These are angle-scheduled
  gains, not monitors. A firmware angle loop moves their operating point physically, as any steering
  does. Reading `gp-0x69ca` from a cave changes nothing for them. I did not re-read the `gp-0x6cc4`
  consumers (45 accesses, ~16 functions, `reference_accord_gp6cc4_tracking_pipeline.md`).

---

## 5. The mirror and the engage sequence

`analysis-2020accord/studies/angle_loop/angle_signal_mirror.py` mirrors `FUN_0003e600`, the angle
portion of `FUN_0003bd7c`, `FUN_0003e6d8` and the 0x14A angle pack. Each line carries its instruction
address, and the cals are read LE from the stock or V295 image. It runs a 1 kHz scenario with slot 4 on
`c % 10 == 4`.

- **Self-checks:** `C` is odd-symmetric, `C(0) = 0`, and cal identities assert on both images. The
  generated encoding matches the image bytes. Ghidra's `emulate_function` could not run as a third method
  because it is hard-wired to x86 registers ("Undefined register: ESP").
- **Engage:** none of `FUN_0003bd7c`, `FUN_0003e6d8` or `FUN_00040a50` reads any LKAS engagement cell
  (`gp-0x6805`, `gp-0x6806`, `gp-0x69b0`, `gp-0x67a4`). `gp-0x67fe` is FOC-derived and measured constant
  at 2. **At the engage tick the lane sees the same held `gp-0x6a00` as the tick before, with the same
  age.** Nothing resets, nothing steps. Mirror: wheel parked at +11.6°, ticks 0–29, engage at 23. The
  held value is 116 throughout, and the 0x14A field is −116, i.e. +11.6° to openpilot.

---

## 6. What this means for the cave (recommendation, not a design)

1. **Do not close a 1 kHz loop on `gp-0x6a00`.** It is a 100 Hz hold: about 4° of phase at 2 Hz and
   10° at 5 Hz, plus a 10 ms staircase. That is the class of structure the kit now attributes the rate
   loop's troubles to (§0.3).
2. **Fresh options, cheapest first:**
   - (a) read `gp-0x69ca` (linear angle, 1 kHz, one `ld.h`). The cost is a frame mismatch against
     openpilot's angle: gain 0.87 near centre (1/1.155) and a 0 to 7.3° offset shape.
   - (b) rebuild the full `gp-0x6a00` at 1 kHz: `gp-0x3608 + gp-0x69ca + pol·C(gp-0x6cc4 − gp-0x69d0)`.
     Calling `FUN_0003e600` clobbers r6–r16 and `ep`, and writes `gp-0x69dc`. That cell has 2 stores and
     0 readers by raw scan, so the write is benign, but it needs stating at GATE 1.
     `FUN_0003e600` is reentrant: it uses registers only plus that one store, so preempting slot 4 inside
     it is safe.
   - (c) use `gp-0x6a00` with a 1 kHz correction from the `gp-0x69ca` delta since the last refresh. This
     needs a new state word.
3. **Gates the cave must carry:** `gp-0x67fe == 2` (or the angle snaps to 0) and `gp-0x679c == 3` (or
   the baseline can be −0x8000 garbage). The `gp-0x69d0` offset bleeds toward 0 at 2 counts per tick,
   about 6.2°/s of apparent angle drift. It is nonzero only after a re-reference write at `0x3d41a`
   (FOC SM). Its frequency was not measured.
4. **Instrument:** the bus already carries `-gp-0x6a00` (100 Hz) on 0x14A and mode-3/substate-2 health
   on byte 4 bit 1. A fresh 1 kHz angle needs its own tap if the cave uses option (a) or (b).

---

## 7. Open — exact next steps

1. **`gp-0x6a56` 100 Hz hold vs the record of the rate PID** (two-sample-sum filter, "20 Hz crossover
   resonance"): re-derive the loop with a 10-tick ZOH on the feedback. Owner: the orchestrator. This trace
   only establishes the hold.
2. Execution time of slot 4 up to `0x22e32`: no static bound found. A 1 kHz tap of a slot-4-written cell
   would measure it.
3. `FUN_0002fab6` outputs (`gp-0x6a9a`, `gp-0x68a8`, `gp-0x6e08/0c`, `gp-0x68c6`): who reads them, and
   do they gate assist or LKAS? Method: raw census of each, then decompile the readers.
4. `FUN_0003d4a2` (FOC SM): what drives `gp-0x6772` to 4/5, the `0x3d41a` re-reference of `gp-0x69d0`,
   and the meaning of `gp-0x676f`. Large; only needed if (3.2) or the bleed matters.
5. Confirm `gp+0x6470` is data-flash backed: find the reader of the `0x8B120` record table.

## 8. Byte identity stock vs V295 [EVIDENCE, Python slice compare]

Identical: `FUN_0003e600`, `FUN_0003e6d8`, `FUN_0003bd7c`, `FUN_00040a50`, `FUN_00040e7e`,
`0x40F42–0x41464` (dispatcher and handlers), `FUN_0003f776`, `FUN_00014be4`, the slot 4 body
`0x22CA0–0x234FC`, the slot 0 body `0x2214A–0x22A88`, `FUN_00065eda`, `FUN_0003c7fc`, and cals `0xC6892`,
`0xC68A2`, `0xC6432`, `0xC613A`, `0xC64F2`, `0xC6358`, `0xC6354`.

Ghidra state: no rename, label, comment, `disassemble_bytes` or save was made this session.
