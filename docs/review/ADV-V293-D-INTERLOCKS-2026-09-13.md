# ADVERSARIAL PASS — V293, surface D: INTERLOCKS AND DOWNSTREAM (GATE 1)

**Agent:** `advD3` (firmware-codepath-tracer), SUBAGENT of the orchestrator (`main`). **Date:** 2026-09-13.
**Role:** adversary. The job was to make V293 FAIL on this surface and to be able to return DO-NOT-FLASH.
**Nothing flashed, nothing sent on any bus, no build script touched, no Ghidra rename/patch/save.**

**Image under attack, hash-verified from disk by me before any analysis:**
`_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin`
SHA256 **`f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17`**.
Base V282 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` ✔ (the prefix the brief named).
Also read: V292 `d1128232…`, V279, stock `code.bin`.

**Method.** Every load-bearing count or null produced TWICE — GhidraMCP (`decompile_function`,
`disassemble_bytes dry_run:true`, `get_function_callers`) and an independent raw little-endian Python
scan of the BUILT image — and **every scanner positively controlled before its null was trusted.**
Scripts in a PRIVATE scratchpad subdirectory `…/scratchpad/advD3/` (see §7 — the session scratchpad is
shared and another agent overwrote one of my files mid-run).

---

## VERDICT: **PASS** — no DO-NOT-FLASH finding on the interlocks surface.

One residual is genuine, quantified and NOT closed: the soft-EME command integrator is a pure
integrate-and-trip and V293 raises dwell. It is reported, not waved away, in §1.5.

| clause | verdict | basis |
|---|---|---|
| **D1** sustained-effort census (gp-0x6b94 / 6ace / 6acc; governor; EME) | **PASS**, one residual (§1.5) | both methods, 11/11 + 7/7 controls |
| **D2** readers of the touched cells; fb/D consumers; dead damper mode | **PASS** | both methods, on the BUILT image |
| **D3** plausibility monitor, lockstep mirror, gp-0x671d, every interlock cal | **PASS** | full-span diff, zero unattributed bytes |
| **D4** fork preset OFF/ON | **PASS on the control path**, three defects in the patch's own evidence (§4.4) | fork working tree |
| **D5** dead twin island | **PASS in effect, FALSE as worded** (§5) | corrected branch scan, 7/7 controls |

**What a FAIL would have looked like, written so this pass is falsifiable:** a second accumulator or
timer on any of the three demand cells; an EME/DTC/governor threshold whose trip condition V293 makes
newly reachable; a reader of `0xC62E6`/`0xC61B6`/`0xC6446` outside the traced sites; a Kd or Kp record
shared with another live table; any unattributed byte in the diff; a writer of `gp-0x680a` on the built
image; a changed interlock cal; a `jarl` into the dead island; or a fork path that runs the rate-plant
feedforward with the mode ON. **Every one was tested and none occurred.**

---

## 1. D1 — THE SUSTAINED-EFFORT QUESTION

The tracer left this open (`TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §7.5): *"an EME-class monitor
that integrates sustained motor effort… I did not locate or read such a monitor."* **I found it. It is
not in the governor and not in `FUN_0004595a`.**

### 1.1 Census of the three demand cells — no accumulator, no timer

Raw opcode-agnostic-for-finding LE scan over `[0x13000, 0x100000)`, **11/11 positive controls PASS**
(`ld.h -0x6a56` @`0x28F4C`, `ld.w -0x3d30` @`0x28F7C`, `ld.hu tp+0x72e6` @`0x28F96`, `ld.hu tp+0x71b6`
@`0x29EE8`, `ld.hu tp+0x7446` @`0x3AC08`, `ld.h -0x6b94` @`0x453E0`, `ld.bu -0x674e` @`0x28FC8`,
`ld.bu -0x3d2c` @`0x28F66`, `st.b -0x671d` @`0x3BD2A` — an **odd** displacement —, `ld.b -0x6752`
@`0x43146`, and the **6-byte** extended form `gp-0x6752` @`0x48E56`). Identical results on V282 and V293.

| cell | accesses (V293) | every site adjudicated |
|---|---|---|
| `gp-0x6b94` (aggregator demand) | **9** | `0x36BF0` IIR low-pass `FUN_00036bec`; `0x3ACEC/0x3ACFA/0x3AD12/0x3AD20` the aggregator writer + lockstep; `0x453E0` the governor; `0x4595E` the plausibility monitor; `0x80820` the diagnostic dispatcher; `0xC4B6E` the `0x14A` cave, **read-only telemetry** |
| `gp-0x6ace` (governor output) | **11** | all inside `FUN_0004503c` / `FUN_000456a4` / `FUN_0004595a` / `0x45B1E` |
| `gp-0x6acc` (governed + COMP) | **6** | `0x431C4` the soft-EME command read; `0x4467A` the float monitor `FUN_00043e44`; `0x458B8`; `0x45932/0x45942` writer + lockstep; `0x45B16` |
| `gp-0x6ba4` (\|delivered torque\|) | **10** | `0x43C0C` writer; readers incl. `0x7B100` = the energy budget |
| `gp-0x3570` (soft-EME integrator) | **3** | `0x43214` read, `0x4327C` write, `0x432DE` read by the authority writer |
| 6-byte extended form, all of the above | **0** | — |

**Not one accumulator, timer or integrate-and-trip among the readers of the three demand cells.** The
only integrator in the set is `gp-0x3570`, reached from `gp-0x6acc`, and that is §1.3.

### 1.2 `FUN_0004595a` and `FUN_000456a4` — decompiled, both instantaneous

`decompile_function(0x4595a)`:

```c
fVar1 = gp-0x6b94 / 1024;   iVar5 = |fVar1 * 1024|      // |TARGET|
fVar2 = gp-0x6ace / 1024;   iVar3 = |fVar2 * 1024|      // |OUTPUT|
sVar4 = (short)iVar5 - (short)iVar3;                    // |TARGET| - |OUTPUT|
fVar2 = fVar2 * fVar1;                                  // sign product
if ((sVar4/1024 < -0.01) && (fVar2 < -0.01)) ... else FAULT   // 0xbc23d70b == -0.01f
```

**No state, no accumulator, no timer, no dwell counter.** It faults only if the OUTPUT **exceeds** the
TARGET or the two are strongly opposite in sign. The governor's own snap-on-overshoot invariant makes
the first impossible and its sign-crossing reset handles the second. V293 changes the *value* of
`gp-0x6b94`, never the demand↔governor relation. **[E]**

`decompile_function(0x456a4)` (the post-governor comp-add): `gp-0x6acc = gp-0x6ace + COMP`, where COMP
is a LERP pair over `gp-0x6a10` gated against `gp-0x6ac0`, **sign-flipped by the RAW rate sensor**
(`if (0 < gp-0x6abe) sVar10 = -sVar10`). The one counter in the function is the per-index cadence byte at
`gp-0x3E80+i`, compared against `param_1` — a **task-cadence watchdog**, not an effort integrator.
V293 touches none of COMP's inputs. **[E]**

### 1.3 🛑 THE INTEGRATE-AND-TRIP EXISTS — and I decoded it byte by byte

It is the **soft-EME command integrator `gp-0x3570`** inside the shaper `FUN_00042af8`.
`disassemble_bytes(0x431C4, 188, dry_run:true)` and `(0x430F0, 212)`:

```
0x431C4  ld.h  -0x6acc,gp,r9          cmd_raw
0x431D0  addi  0x2000,r9,r6           plausibility window +/-8192 (r11 := 0 outside it)
0x431CC  ld.bu 0x74c8,tp,r15          MODE = [0xC64C8] = 0 on A160  ->  command = cmd_raw
0x43206  st.h  r11,-0x6b08,gp         the command

0x4320A  mov r11,r14 ; shl 0xf,r14    cmd << 15
0x4320E  mov r29,r9  ; shl 0xf,r9     UPPER bound << 15
0x43214  ld.w  -0x3570,gp,r10         I
0x43218  ble ...                      (four arms: above upper / below lower / decay+ / decay-)
0x4321A  sar 0x2 ; sub ; shl 0x2      I += (cmd - bound) << 15      <-- EXACT, the sar/shl pair is
0x43224  add r14,r16                                                    overflow headroom, not a scale
0x43268  ld.hu 0x71dc,tp,r21          CLAMP = [0xC61DC] = 30720
0x43270  cmp ; bgt ; subr ; cmovle    I = clamp(I, +/- (30720 << 15))
0x4327C  st.w  r10,-0x3570,gp
```

and the authority writer, `disassemble_bytes(0x432A8, 64, dry_run:true)`:

```
0x432B0  ld.hu 0x71da,tp,r16          K = [0xC61DA] = 1092
0x432B8  mov r24,r9                   r9 = |I >> 15|
0x432BA  mulu r16,r9,r0 ; shr 0xa,r9 ; zxh r9
0x432C8  st.h  r13,-0x6966,gp         authority = (|I>>15| * 1092) >> 10
```

SM2 arms when authority ≥ `[0xC6422]` = 16384 (read at `0x436F4`/`0x43746`).

⇒ **`I >> 15` is literally the running sum, in counts, of the per-tick excess of the command over the
bound, at 1 kHz.** SM2 arms at `|I>>15| ≥ 15361`. **A sustained 100-count excess arms SM2 in 154 ms.**
This confirms — independently, from the bytes — the 2026-08-06 correction banner in
`memory/reference/firmware/reference_accord_soft_eme_bound_arm_gating.md` (*"a PURE UNATTENUATED
INTEGRATOR… 153 ms, not seconds"*) and refutes any dwell argument built on a 1/4-per-cycle tracker.

**Inside the corridor the integrator LEAKS**, at a rate proportional to the distance from the nearer
wall (`0x4323E–0x43266`), and it cannot cross zero. So only a **net-positive** excursion accumulates.

The bound, `disassemble_bytes(0x430F0, 212)`:

```
UPPER r29 = MAX( corridor_upper,  IIR_upper >> 8,  boost r23 )     built 0x43136-0x4318A
LOWER r27 = MIN( corridor_lower, -IIR_lower >> 8, -boost )
corridor is ZEROED unless |gp-0x6bf0| is outside +/-[0xC6156]=9216 AND authority == [0xC641A]=0
boost is zeroed only by the SM at 0x42FB8-0x43016 AFTER authority > [0xC641E]=16384 for [0xC64E3]=20 cycles
```

### 1.4 Why it PASSES — every bounding cal read from the BUILT image

| quantity | cal | stock | V282 | **V293** | V282→V293 |
|---|---|---|---|---|---|
| boost LERP Y0/Y1/Y2 (the always-live bound arm) | `0xC6768/6A/6C` | 0 / 1536 / 2048 | **5120 flat** | **5120 flat** | **identical** |
| corridor dir1 / dir2 | `0xC674E/50`, `0xC675A/5C` | ±1024 | ±5120 | ±5120 | identical |
| governor cap table Y | `0xC520C`, `0xC5224` | `[5325,3584,2406,1587,512]` | same | same | identical |
| governor nominal ceiling | `0xC6202` | 4762 | 4762 | 4762 | identical |
| COMP ceiling | `0xC67DC` | 2560 | 2560 | 2560 | identical |
| LKAS lane output clamp | `0xC61B4` | 512 | **3072** | **3072** | identical |
| integrator clamp / authority scale / SM2 arm | `0xC61DC`/`0xC61DA`/`0xC6422` | 30720 / 1092 / 16384 | same | same | identical |
| energy-budget threshold / ceiling / gain | `0xC509E`/`0xC5164`/`0xC5128` | 5325 / 0 / 1024 | same | same | identical |

**So the bound is ≥ 5120 at all times in normal operation** (boost is floored flat and is gated only by
an authority that the wind-up itself would have to create first — V31's self-stable fixpoint, re-derived
here from the bytes).

**And the ENERGY BUDGET is unreachable, by a tighter argument than the record's.** `FUN_0007b022`
charges only when `gp-0x6ba4 > [0xC509E] = 5325` (strict). `gp-0x6ba4` is written at `0x43C0C` as the
magnitude of the post-governor-clamp torque, so `gp-0x6ba4 ≤ gp-0x4f64 ≤ 5325` — **the cap table's own
maximum**. The record bounds it by `0xC6202 = 4762`; the table bound is the one that actually applies and
it still closes the case. `0xC509E` has **exactly one reader** (`0x7B122`) and `0xC6202` **exactly one**
(`0x7B06A`), both inside `FUN_0007b022`. Unreachable on stock, V282 and V293 alike. **[E]**

**Range identity.** `|gp-0x6ace| ≤ gp-0x4f64 ≤ 5325`; COMP ≤ 2560; LKAS lane ≤ 3072. V293 changes none
of them, so the **reachable set of `gp-0x6acc` is identical on the two builds.** The peak excess over the
5120 bound is ≤ 2765 counts on BOTH.

### 1.5 🛑 THE RESIDUAL — stated, not waved away

**What V293 does change is DWELL.** With `fb ≡ 0` the lane holds its full commanded torque however fast
the wheel is already moving, where V282's lane decays toward zero as the wheel reaches the commanded
rate. The integrator is dwell-sensitive by construction, so **"the instantaneous ranges are identical"
does NOT entail "the integrator's reachable state set is identical."** I will not pretend otherwise.

Three bounds on how far that can go, each read from bytes:

1. **The LKAS lane cannot drive wind-up alone.** It is hard-clamped at 3072 (`0xC61B4`, identical on both
   builds) against a 5120 bound, so **at least 2048 counts — and against the tracer's realized 2481-count
   rail, at least 2639 — must come from lanes V293 does not touch.** V293 can only ever be a
   co-contributor.
2. **The largest NEW excess V293 can create where V282 had none is 205 counts** — the band
   `5120 < |gp-0x6acc| ≤ 5325` with COMP at zero, i.e. V282's command below the bound and V293's at the
   governor cap. 205 counts sustained needs **75 ms of continuous residency** to arm SM2.
3. **Two structural anti-correlations.** The governor cap `gp-0x4f64` falls monotonically with motor rate
   (`[5325,3584,2406,1587,512]` over X `[1050,1700,2500,3700,4100]`) while V293's advantage over V282
   grows with wheel rate; and COMP, whose sign is `−sign(gp-0x6abe)`, **subtracts** from the command in
   exactly the regime where V293's lane exceeds V282's (wheel moving in the commanded direction).
   **[E]** for both arithmetic forms; **[B]** for the polarity reconciliation between `gp-0x6abe`'s raw
   sign and the delivered command's, which I did not re-derive through `pol = gp-0x6752`.

**Why this is not a FAIL by D1's own criterion** (*"can trip on V293 that could not on V282"*): the same
excess band, the same bound and the same 154 ms-per-100-counts law exist on V282, and nothing in V282
prevents a sustained excursion either — its base-assist lanes have no rate feedback either. This is not a
path that *could not* trip on V282. **It is a rise in exposure, not a new mechanism.** And SM2/SM3
**self-clear** — the 2026-08-06 banner establishes the recovery branch has no bypass condition, so the
worst case is a transient cutback with a ~10 s ramp back, not a latched loss of assist.

**Exact next step to close it** (not required before flight, in my judgement): the drive read already
plans `0x14A` b4–b7 duties; add nothing, but score `|427 tap|`'s time above the value corresponding to
`gp-0x6acc` = 5120 on the first V293 episode, and compare with the same statistic on a V282 route.

---

## 2. D2 — READERS OF THE TOUCHED CELLS, ON THE BUILT IMAGE

All from the **V293 image**, both methods, controls as in §1.1. V282 and V293 are identical for every row
(V293 changes no code byte).

| cell | readers | where | island |
|---|---|---|---|
| **`0xC62E6`** fb-lag output clamp | **3** (prereg expected 3) | `0x28F96`, `0x28F9C`, `0x28FB8` — all inside the filter | **0** |
| **`0xC61B6`** D clamp | **7** (prereg expected 4 live + 3 dead) | live `0x29EE8`, `0x29EF2`, `0x29EF8`, `0x29F02`; dead `0x2ADD4`, `0x2ADDC`, `0x2ADEC` | **3** |
| **`0xC6446`** r24 engaged arm | **1** | `0x3AC08` | 0 |
| `0xC61B4` lane clamp | 8 | 4 live + 4 dead | 4 |
| `0xC62E4` / `0xC63E6` / `0xC61BA` (I path) | 7 / 2 / 2 | unchanged from the record | 3 / 1 / 1 |

⚠ **A build script asserting "exactly three readers of `0xC62E6`" is correct on a V282 base and would be
WRONG on a V292 base** (five there, two orphaned by the cave). V293 is V282-based, so three is right.

**The Kd and Kp records.** 28 + 28 records, pointer families `0xCB7D4` and `0xCB994`, **both families
byte-identical V282→V293** (only the records they point at changed). **No record is shared with any other
table:** an all-alignment LE32 scan of the whole code region for pointers landing inside a touched record
finds **exactly 56, and all 56 are the two owning families** (control: the scan finds all 56 own-family
pointers). The assist map `0xC9A88`, the limit family `0xCB844` and all four taper families
`0xCBAE4/0xCBB54/0xCBBC4/0xCBC34` have **zero** records overlapping a touched record.

**Consumers of the fb operand and the D term, other than the PID sum:**

| quantity | consumers | verdict |
|---|---|---|
| `gp-0x6a34` = `\|fb>>5\|` (published `0x290CA`) | one live reader `0x2A0CA` — **inside the dead `gp-0x680a == 1` damper mode** — plus one island reader `0x2AFAE` | **no live consumer** |
| `gp-0x3d30` fb filter state | **2** — `0x28F7C` read, `0x28FA8` write, both in the filter. (V292 has a third, the cave's `0x14A` b3 rung; **V293 is V282-based and does NOT have it**) | private |
| D term / PID internals `gp-0x6b2e/32/34/36` | writes at `0x2A17C/2A188/2A1A2/2A19C`; the only read is `0x2A896`, **inside the island** | orphan-safe |
| `gp-0x6b38` delivered lane torque | `0x55DF0` (CAN-427 tap) and `0xC4B40` (the `0x14A` cave) — both **reads** | telemetry only |

**The dead viscous-damper mode at `0x2A0C6`, keyed on `gp-0x680a` — still unreachable on the BUILT V293
image. [E], and I corrected my own scanner to get it.** A first, loose scan reported **10** accesses of
`gp-0x680a`. Eight of them are opcode field `0x3D` (`ld.bu` ODD), which under the correct parity rule
(`true_disp = (hw2 & 0xFFFE) | (op & 1)`) address `gp-0x6809`, **a different cell one byte away** — the
documented `ld.bu` bit-5 trap, caught by tightening the rule and re-running with an odd-displacement
control. The true census is **2 accesses, both `ld.bu` (op `0x3C`), on stock, V282, V292 AND V293**:
`0x29A68` (live) and `0x2A96A` (island). **Zero writers in any 4-byte or 6-byte `gp` form.** With the
`.data` boot byte at flash `0x868A6` = `00` (inherited **[E]**), `gp-0x680a ≡ 0` and the mode cannot run.
Residual, same as every scan of this class: a register-indirect `st.b` through a pointer is invisible to
an operand scan. **[B]** that none exists.

---

## 3. D3 — MONITOR, MIRROR, LATCH, AND EVERY INTERLOCK CAL

### 3.1 The full-span diff: 378 bytes, 183 runs, **ZERO unattributed**

Restricted to `[0x13000, 0x100000)` (never a whole-file diff — the `0xFF`-filler trap). **Bytes differing
outside that window: 0.**

| class | bytes | detail |
|---|---|---|
| the three named cells | **4** | `0xC61B7` `28`→`00` (D clamp 10240→0) · `0xC62E7` `b4`→`00` (fb clamp 46080→0) · `0xC6446/47` `7c14`→`0008` (r24 arm 5244→2048) |
| inside the 28 Kd + 28 Kp records | **352** | Kd Y `128`/`64` → `0` on all 28; Kp Y `205`/`248`/`266`/`307` → `120` on all 28 |
| CRC trailers | **22** | `0xC6FFC`, `0xE4FFC`, `0xE5FFC`, `0xE6FFC`, `0xE7FFC`, `0xE8FFC` |
| **unattributed** | **0** | — |

**All six touched CRC pages recomputed by me with `zlib.crc32` over `[page, trailer)` and each equals the
stored trailer on both V282 and V293.** `0xC4FFC` (block 1), `0xC5FFC` and `0xCDFFC` are byte-identical
V282→V293 and verify on both — correct, since V293 changes no code byte and no `0xC5`/`0xCD` cal.

⚠ My `0xCB000` check reports a mismatch on **V282 as well as V293**, identically. V282 has flown. Per the
standing rule *a check that condemns the flown build is broken*, that is my range/algorithm guess being
wrong for that page, **not** a V293 defect — and the `0xCB` region is byte-identical between the two
images anyway.

### 3.2 The interlock cals — every one byte-identical V282 → V293

Read from both images: governor ceiling and both slew STEPs; the whole energy-budget quad; the soft-EME
integrator clamp, authority scale, SM2 arm, boost-SM threshold and cycle count, IIR alpha, corridor gates;
all four corridor Y and all three boost Y; the COMP 3-point LERP; the command MODE selector; the lane and
request-array clamps; P clamp, sum clamp, Ki, I clamp, I deadband; the forward gain; **DTC debounce
`0xC61C0/C2/C4`; STEER_STATUS debounce `0xC64B4/B6/B8`; the `gp-0x671d` SET `0xC61FA` and RELEASE
`0xC61F8`; the r24 deadband `0xC61F6`; `0xC6440/42/44`; `dec_gate7` `0xC61CC`; the gentle-EME gate
`0xC6312`.** **Not one differs.** The only cal differences V282→V293 are the three named cells and the
two banks.

`FUN_0004595a`'s Ghidra body is `0x4595A–0x45A1F`; **no changed byte lies in it or in any other code**, so
every monitor is byte-identical and only its *inputs'* values move.

### 3.3 The lockstep mirror `gp-0x4ca6` — it compares the SENSOR cell, not the feedback operand

**[E], and this closes the brief's "prove it".** `gp-0x4ca6` has **exactly 5 accesses image-wide**, all
inside `FUN_0003f776` (body `0x3F776–0x3F883`): one read `0x3F78E` and four writes `0x3F7BC`, `0x3F7D4`,
`0x3F7E4`, `0x3F822`. `decompile_function(0x3f776)` shows it written in lockstep with `gp-0x6a56` from the
**raw sensor**, *upstream of the fb filter*:

```c
*(short *)(gp - 0x6a56) = sVar3;   *(short *)(gp - 0x4ca6) = sVar3;   // the pair
```

`0xC62E6`'s three readers are all inside `FUN_00028ea6`. **The two sets are in disjoint functions, so the
mirror comparison never involves the clamp at all** — the question of "both cores reading the same zero"
does not arise. V293's edit is downstream of the mirrored quantity.

### 3.4 The `gp-0x671d` latch — not made more reachable

Its SET/RELEASE cals are byte-identical (§3.2), and the only cal V293 touches anywhere in the r24 lane is
`0xC6446`, which moves **down**, 5244 → 2048, toward Honda's 512. The lane's contribution shrinks.
**[E]** for the byte values and the single reader `0x3AC08`; **[B]** that the latch input scales
monotonically with that arm.

---

## 4. D4 — THE FORK PRESET

🛑 **SUPERSEDED IN ITS MECHANISM, NOT IN ITS VERDICT — 2026-09-13, later the same day.** Everything in
§4 below was scored against the fork patch as it stood at the time: a param, `AccordEpsTorqueMode`,
plus four `AccordTorqueMode*` sliders. **That patch was reworked onto Testing Ground 9 ("Accord EPS
Torque Mode", variant B) and all five params were deleted.** The body of §4 is left exactly as
written — it is the record of what was scored — but read it with these three substitutions, and see
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` for the current card:
- *"`AccordEpsTorqueMode` OFF"* → **variant A** (or any other slot selected). The gate is now
  `self.is_honda_accord and accord_torque_mode_testing_ground_active()`, i.e.
  `testing_ground.use("9","B")`; `honda_accord_torque_mode_active()` no longer exists.
- *"`accord_curvature_lead_active()` gains `and not accord_eps_torque_mode`"* → it gains a fourth
  parameter, `torque_mode_active`, which `controlsd` supplies from the same slot gate. The logic is
  unchanged.
- 🛑 **D4's Safe Mode reasoning does NOT carry over.** Safe Mode manages params and has never touched
  Testing Grounds, so **a Safe Mode trip now leaves variant B active** rather than forcing it off.
  That inverts the fail-safe direction assumed anywhere below.
§4.1's deployment warning stands verbatim: `epsTorqueMode @8` is still written every frame in both
variants, so the capnp schema change must ship with the Python change.

Read from the operator's own working tree, `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`,
**read-only** (`git diff`, no edit). ⚠ The uncommitted patch carries **two** features, not one:
`AccordEpsTorqueMode` **and** `AccordCurvatureLead`/`ModelCurvatureLead` (V292's subject). Both must be
scored, because both are in the tree that would fly V293.

### 4.1 With `AccordEpsTorqueMode` OFF — the control path is unchanged

`honda_accord_torque_mode_active()` = `is_honda_accord AND toggle`; default `"0"`, safe-mode `"0"`
(`common/params_keys.h`), read with `default=False` (`starpilot_variables.py:851`). With it False:

- `_apply_accord_torque_mode_tune()` is not called — it sits behind `if accord_torque_mode:`.
- The three new conjuncts are all `not accord_torque_mode` = True, so `AccordTurnFFTaper`, the
  `accord_torque_ki` write and the **rate-plant feedforward branch** evaluate exactly as before.
- `accord_curvature_lead_active()` gains `and not accord_eps_torque_mode` — also True, so unchanged.

**Control output: identical to pre-patch. [E]**, by reading every one of the five changed conditions.

⚠ **Not byte-identical in the published log**: `self.starpilot_lateral_state.epsTorqueMode` is written
**every frame in both toggle states**, and the field is new (`cereal/custom.capnp`, `epsTorqueMode @8`).
**Deployment note, and it is a real OFF-state regression risk:** if the capnp schema change does not ship
with the Python change, that assignment raises on every frame **regardless of the toggle**. The schema
edit is in the same uncommitted patch, so this is a "do not ship half the patch" warning, not a defect.

### 4.2 With it ON — the rate-plant feedforward cannot execute by any path

`get_honda_accord_rate_plant_ff` has **exactly one call site image-wide**,
`latcontrol_torque.py:637`, inside

```python
if self.is_honda_accord and not accord_torque_mode and getattr(starpilot_toggles, "accord_rate_plant_ff", True):
```

`accord_torque_mode` is the same local computed at the top of `update()` that gates everything else, so
there is no stale-value path. `AccordEpsGainScale` / `AccordEpsSpringScale` are read only inside that
branch and become inert with it. **[E] — the branch is unreachable with the mode ON.**

### 4.3 The mismatch hazard, both directions — and the prereg's direction is INCOMPLETE

| configuration | what actually runs | direction |
|---|---|---|
| **V282/V292 firmware + mode ON** | rate-plant FF forced off ⇒ the generic lat-accel FF, which the patch's own constants block sizes at **2.4–4.3× the correct steady command**; LAF 6.0, friction 0.01, Kp 0.3, Ki 0.15 | **over-commands** — matches the prereg |
| **V293 firmware + mode OFF** | rate-plant FF **runs** ⇒ steady FF **2.4–4.3× LOW**; *and* Kp stays at the `SteerKP` toggle (0.9, **3×** the torque-mode value) with Ki at `AccordTorqueKi` 0.30 (**2×**) | **not simply "sluggish"** |

🛑 **The prereg calls OFF-on-V293 "sluggish". That is only half of it.** The feedforward is starved
2.4–4.3× **and** the feedback P and I are 3× and 2× the torque-mode design — an FF-starved loop leaning on
a high-gain integrator, which is exactly what the patch's own comment calls *"the configuration that
hides the error until it is a wallow."* **The page should say both halves.**

### 4.4 Three defects in the patch's own evidence (reported, not fixed)

1. **`safe_mode.py`'s justification is unsupported.** Its comment says forcing the mode OFF is
   conservative because *"on a torque-map image it under-drives the feedforward rather than over-driving
   it."* But Safe Mode **also** forces `AccordRatePlantFF` to `"0"` (its safe-mode value in
   `params_keys.h:389` is `"0"` against a default of `"1"`). With the rate-plant branch off, the FF
   structure in Safe Mode is the **generic** one — the same structure torque mode uses — so the stated
   "under-drives" mechanism does not apply. The *conclusion* (Safe Mode is safe here) survives and is
   arguably stronger than claimed; the reason given is wrong.
2. **`epsTorqueMode` is published unconditionally**, so the patch is not inert with the toggle off in the
   log domain, and it hard-depends on the capnp change (§4.1).
3. `self.model_curvature_lead.reset(self.curvature)` in `controlsd.py` runs **ungated** whenever
   `not CC.latActive`. It only mutates that object's own state and the object is never read unless
   `accord_curvature_lead_active()` is true, so it is inert — but it is an ungated new call on the main
   control path and should be named as such.

**`AccordCurvatureLead` itself:** default `"0"`, safe-mode `"0"`, and **forced inert by torque mode**
(`and not accord_eps_torque_mode` in `accord_curvature_lead_active`). Nothing to flag.

---

## 5. D5 — THE DEAD TWIN ISLAND `0x2A30E–0x2B421`

🛑 **D5 AS WORDED IS FALSE.** *"The dead twin island reads none of the touched cells"* — **it reads
`0xC61B6` at three sites**, `0x2ADD4`, `0x2ADDC`, `0x2ADEC` (§2). It also holds `imm32` references to
both touched pointer families, `0xCB7D4` at `0x2AD66` and `0xCB994` at `0x2ACBA` — the island's own copy
of the PID walks the same Kd and Kp records the live PID does. It does **not** read `0xC62E6` or
`0xC6446` (0 island hits each).

**The conclusion survives because the island is unreachable, and I verified that on the BUILT V293 image
after my first scanner failed its controls.** A first branch scan returned 0/5 controls — its Format-V and
Format-III masks were wrong — so I discarded its output entirely rather than report an uncontrolled null.
The corrected decoders, derived from known sites (`jr` @`0x28F8E` `hw1=0x0789 hw2=0xBC72` → `+0x09BC72`;
`jarl` @`0x432D6` `hw1=0xFF82 hw2=0x8724` → `0x6B9FA`; Bcond verified on four in-block branches), give
**7/7 controls PASS** over 22,110 distinct targets:

| test | result |
|---|---|
| branch/call targets inside the island | 239 |
| of those, with **any source outside** the island | **0** |
| **`jarl` calls landing in the island** | **0** |
| Ghidra `get_function_callers(FUN_0002a30e)` | *No callers found* |

**Residual, marked BELIEF:** a computed or table-dispatched jump is invisible to a static branch scan.
This is the same open residual `ADV-V292-D` recorded as its F3, unchanged by V293.

---

## 6. What I did NOT verify

1. ~~`gp-0x4f64 ≤ 5325` rests on the writers all coming from the cap table.~~ **CLOSED before delivery,
   now [E].** Raw scan of the **V293 image**: `gp-0x4f64` has **11 accesses, exactly 3 of them writers** —
   `0x7C2E2`, `0x7C3B4`, `0x7C47C` — and all three lie inside `FUN_0007b022`, whose Ghidra body is
   `0x7B022–0x7C4F1` (`get_function_by_address`). They are its three mode branches, each writing a LERP
   of the cap table, whose Y range is `[512, 5325]` on V293 (read from the image). A LERP cannot leave
   its knot range, and both out-of-range arms return a knot. ⇒ `gp-0x4f64 ≤ 5325`. Residual: the standing
   register-indirect blindness, **[B]** that no such writer exists.
2. **The realized 2481-count lane rail** is the tracer's integer mirror, not mine. My §1.5 argument needs
   only the hard clamp `0xC61B4 = 3072`, which I read from the bytes.
3. **The COMP polarity reconciliation** through `pol = gp-0x6752` (§1.5 bound 3). The sign formula
   `−sign(gp-0x6abe)` is **[E]** from `FUN_000456a4`; that it opposes the *delivered command* in the
   V293-vs-V282 regime is **[B]**.
4. **Register-indirect writers** to `gp-0x680a` (§2) and any indirect jump into the island (§5).
5. **`gp-0x6ac0`'s physical scale**, so I give no deg/s figure for where the governor cap starts falling.

## 7. Tooling note for the rest of the session

🛑 **The session scratchpad is SHARED across agents.** Another agent overwrote my `census.py` with a file
of its own between two of my runs; the second run executed *their* script and failed with a confusing
`NameError` after printing their output. **Anyone writing scripts there should use a private
subdirectory.** Mine is `…/scratchpad/advD3/`.

Also re-confirmed: **`disassemble_bytes` with `dry_run:true` on already-analysed regions is
non-mutating**, and no `save_program` was issued. The current GhidraMCP program was `code.bin` (stock,
2090 functions) for every Ghidra call in this document, confirmed by `list_open_programs` at the start;
every stock-vs-built comparison in this document was made in **Python against the images**, never by
trusting the Ghidra database for a built-image claim.
