# ADVERSARIAL PASS — V291 (C10), surface D: INTERLOCKS AND DOWNSTREAM

Agent `advD` (SUBAGENT; orchestrator = `main`). 2026-09-13.
Job: make V291 FAIL on GATE-1 cell ownership, every consumer of the edited cells and of the state
they feed, the EME shaper, governor ceilings, lockstep monitors, DTC plausibility thresholds, and the
telemetry rung. Nothing flashed, nothing sent, no build script edited, no Ghidra mutation.

**VERDICT: PASS.** D1–D6 all pass. Three corrections to the pre-registration's own description of the
b3 rung, one named BELIEF-grade residual on D3, one cross-surface dependency, and one instrument
caveat the operator must know before reading the telemetry.

---

## 0. The image, and the delta — verified first, independently

| | |
|---|---|
| image | `_v291c10_V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-…_plain_image.bin` |
| sha256 | `a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657` matches brief |
| base | `_v282_…_plain_image.bin` sha `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` |

Full-file byte diff, both images 1,048,576 B: **15 differing bytes in `[0x13000, end)`, 0 below `0x13000`.**

```
0xc4baa 81 -> d1 ; 0xc4bab c9 -> c2     b3 rung load displacement
0xc4ffc..ff 446bb04e -> 26c4ce34        0xC4000 page CRC trailer
0xc63e8 9b -> c2                        a   923 -> 962   (low byte only)
0xc63ea..eb 1806 -> be03                b  1560 -> 958
0xc6446..47 7c14 -> 7512                r24 ENGAGED arm 5244 -> 4725
0xc6ffc..ff 72dfea75 -> bb129bed        0xC6000 page CRC trailer
```

**EVIDENCE.** Exactly the briefed delta, no more. CRC *correctness* is surface C's; I confirm only
that both touched pages got a new trailer and that no third page was touched.

## 0.1 Method, and why its nulls are worth something

Two independent methods, set-differenced, on the **BUILT** image:

- **Python** — my own scanner, written for this pass, deliberately over-matching the union of every
  documented opcode-field convention, then every hit adjudicated. Forms covered: 4-byte disp16 for
  opcode fields 0x38–0x3F with the `ld.bu` hw1-bit-5 parity rule and the `disp|1` quirk; the 6-byte
  extended-disp23 form; base-`r0` absolute addressing; absolute LE32 constants; `movhi`/`movea` pairs;
  `mov imm32`.
- **Ghidra** `search_instructions` on `code.bin` (184,512 instructions, i.e. *including* the
  0x2A508–0x2B421 island analysed and saved this session).

**Seven positive controls, all PASS, on the built image** (not on stock): `gp-0x6acc` finds
`0x431C4` + `0x45932`; `gp-0x67f4` finds `0x3AD76` (even `ld.bu`); `gp+0x63fd` finds `0x3AD88` (odd
`ld.bu`); `gp-0x6a5e` finds `0x3AD7E` (`ld.hu`); `tp+0x72e6` finds `0x28F96`; `gp-0x4f60` finds both
6-byte sites `0x59BFA` / `0x5A0BC`; `gp-0x6a56` returns exactly **30** sites, matching the prior
tracer's independent count. Aggregate counts held after tightening: `gp-0x6752` = 56,
`gp-0x4f60` = 76, `gp-0x6a56` = 30.

My **decoder** was separately validated against Ghidra's own 60-instruction listing of
`0x28F12–0x28FC2`: **60/60 on length, 58/60 on mnemonic** (the two misses are my naming of `setfcc`
vs `setfnc` / `setfne`; structure and length correct). That validation caught two real bugs — see section 7, E1.

---

## 1. D1 — readers/writers of `tp+0x73E8`, `tp+0x73EA`, `tp+0x7446` — PASS

| cell | Python (built image, tightened) | Ghidra (`code.bin`) | writers | abs LE32 | movhi/movea | set-difference |
|---|---|---|---|---|---|---|
| `tp+0x73E8` = `0xC63E8` (`a`) | **1** — `0x28F8A` `ld.h 0x73e8,tp,r9` | **1** — `0x28F8A`, 184,512 scanned | **0** | 0 | 0 | **empty** |
| `tp+0x73EA` = `0xC63EA` (`b`) | **1** — `0x28F86` `ld.hu 0x73ea,tp,r16` | **1** — `0x28F86` | **0** | 0 | 0 | **empty** |
| `tp+0x7446` = `0xC6446` (r24 arm) | **1** — `0x3AC08` `ld.hu 0x7446,tp,r10` | **1** — `0x3AC08` | **0** | 0 | 0 | **empty** |

**Byte-overlap attack** (any access whose *byte range* touches an edited byte, all widths, all
parities, including the high bytes `0xC63E9` / `0xC6447`): 6 raw hits, **3 adjudicated as my own
scanner's over-match** — for opcode field 0x3F the displacement is always `hw2 & 0xFFFE`, so
`0x29D9C` and `0x2AC8E` read `0xC63E6` (Ki = 0) and `0x3AB5E` reads `0xC6444` (= 512). Net = the three
known readers. No `ld.w` spans `a` + `b` together; no `ld.b` / `ld.bu` reads a high byte.

**Stride / table-walk attack.** Zero LE32 words anywhere in the image have a value in
`[0xC6300, 0xC6500)`. Only four `mov imm32` sites materialise any address in the whole `0xC6000` page,
all of them `mov 0x0c6000` (`0x146DC` to r11, `0x59560` to r15, `0x5963E` to r16, `0x59862` to r26); no
load/store with a non-`gp`/`tp` base uses displacement `0x3E8`, `0x3EA` or `0x446`. The one apparent
hit, `0xBC3BA` decoding as `st.w r0,0x3ea[r11]`, sits inside a descending numeric data table
(1278, 649, 326, 163, 81, 41, 20, 10, 5, 3, 1, 0 followed by 256, 128, 64, 32, 16, 8, 4, 2) — **data,
not code.** Base-`r0` absolute addressing excluded with a passing control: 2,222 distinct base-`r0`
6-byte displacements exist image-wide and **none** lands in `[0xC6000, 0xC7000)`.

**EVIDENCE.** GATE 1 holds for all three cells on the built image.

---

## 2. D2 — the feedback state, the sentinel, staleness, cold boot — PASS

### 2.1 Census, V282 vs V291, built images

| cell | V282 | V291 | sites |
|---|---|---|---|
| `gp-0x3d30` (state `s`, to `0xFEDF42D0`) | 2 | **3** | `0x28F7C` `ld.w`, `0x28FA8` `st.w`, **`0xC4BA8` `ld.w` (the cave, NEW)** |
| `gp-0x3d2c` (sentinel) | 2 | 2 | `0x28F66` `ld.bu`, `0x290D4` `st.b` |
| `gp-0x3d34` (sibling state) | 2 | 2 | `0x28F78` `ld.w`, `0x29080` `st.w` |
| `gp-0x3d3c` (output-lag state) | 4 | 4 | `0x2A178` / `0x2A1B0` live, `0x2A89A` / `0x2A8BA` dead island |
| `gp-0x3680` (the b3 rung's OLD source) | 3 | **2** | `0x3A85C` `ld.w`, `0x3A87A` `st.w` (cave read REMOVED) |
| `gp-0x6752` (arm flag) | 56 | 56 | unchanged, incl. 4 six-byte sites `0x48E56`–`0x48E88` |

Exactly the intended +1 on the state cell and -1 on the old source. No other accessor anywhere.
Ghidra independently returns 2 for `gp-0x3d30` on `code.bin`, which is correct — the cave does not
exist in the stock dump.

### 2.2 The filter runs EVERY tick, engaged or not — re-derived from the listing

`disassemble_bytes(0x28F10–0x28FC4, dry_run)` gives exactly **four** bails to `0x290B0`:

| site | test | is it an engagement condition? |
|---|---|---|
| `0x28F3C` | `addi 0x6400,r15,r8` / `ori 0xc801,r0,r16` / `cmp r16,r8` / `bc` — `gp-0x4f60` torsion-bar plausibility | **no** |
| `0x28F48` | `addi 0x1,r6,r12` / `cmp 0x3,r12` / `bc` — `gp-0x6752` arm flag in {-1,0,1} | **no** |
| `0x28F5A` | `addi 0x2ee0,r7,r11` / `addi -0x5dc1,r11,r0` / `bnc` — plausibility bail at rate magnitude 12000 | **no** |
| `0x28F62` | `cmp r0,r14` / `bne` — arm flag not zero | **no** |

The engagement guard is at `0x29A48`, **2,812 bytes later in the same straight-line flow.**
So `s` tracks the wheel continuously while disengaged and can never be stale at re-engage.
**EVIDENCE.** This confirms, not merely relays, the prior trace.

`r25` coupling confirmed as recorded: `0x290AC mov 0x1,r25` / `0x290C0 mov 0x0,r25`, tested at
`0x29A60`. A filter bail forces the PID skip. V291 changes none of this.

### 2.3 Cold boot — no initialiser exists, and it does not matter (three independent reasons)

There is **no initialiser**: `gp-0x3d30` has exactly one writer image-wide and it is the filter itself.
That is the honest finding. It is nevertheless bounded:

1. **The sentinel forces zero.** `0x28F72 cmp 0x1,r9` / `0x28F76 bne 0x28F82`, and the taken branch is
   `0x28F82 mov 0x0,r6` / `0x28F84 mov 0x0,r26` — **explicit zeroing of both states** whenever
   `gp-0x3d2c` does not read exactly 1. Garbage in the sentinel byte does not propagate garbage into `s`.
2. **The output is hard-clamped on the very first tick.** `0x28F96` / `0x28F9C` / `0x28FB8` load
   `0xC62E6` = 46080 and `0x28FA6`–`0x28FBC` clamp `r26` to that magnitude *before* anything downstream
   sees it. A garbage state can only saturate the operand, never exceed V282's own range.
3. **The startup code is not in the flashed payload at all.** Every byte below `0x13000` is `0xFF`
   in **both** V282 and V291 (the stock dump has 50,284 non-`0xFF` bytes there). **No build in this
   lineage can change reset, RAM-init or the vector table** — the init path is byte-identical.

Worst-case persistence if all three protections were somehow void: a full-scale int32 garbage state
decays below 1 in **207 ms (V282) to 344 ms (V291)**, +137 ms. LKAS cannot be engaged that soon after
ECU power-on. **Not a flight risk.**

### 2.4 The numbers, from the built bytes

| | V282 (923, 1560) | V291 (962, 958) |
|---|---|---|
| DC = 2b/(1024-a) | 30.8911 | **30.9032** (+0.039 %) |
| corner -ln(a/1024)/(2 pi 1 ms) | 16.527 Hz | **9.940 Hz** |
| e-fold -1/ln(a/1024) | 9.63 ms | **16.01 ms** |
| 1/(1-a/1024) (the brief's measure) | 10.14 ms | **16.52 ms** |
| steady state s\* at rate 12000 | 185,347 | 185,419 |
| worst a*s vs int32 | x12.55 headroom | **x12.04 headroom** — no overflow |
| `sar`-floor dead zone 1024/b | 0.656 cnt = 0.082 deg/s | **1.069 cnt = 0.134 deg/s** |

The state's magnitude is essentially unchanged because the DC is held; the clamp at 46080 is
therefore reached no more often than on V282, and for a fast input a slower pole reaches it **less**
often. Direction of change is safe.

---

## 3. D3 — r24 downstream: aggregator, governor, lockstep, EME, DTC, the latch — PASS (one residual)

### 3.1 Every interlock cal, read from the IMAGES (not from any build script)

| cell | what | STOCK | V282 | V291 |
|---|---|---|---|---|
| `0xC6206` / `0xC6208` | governor slew step A / B | 512 / 205 | 512 / 205 | **512 / 205** |
| `0xC61DA` | shaper cal | 1092 | 1092 | **1092** |
| `0xC674E` `0xC6750` `0xC675A` `0xC675C` | EME int quad | 1024 1024 -1024 -1024 | 5120 5120 -5120 -5120 | **unchanged** |
| `0xC6768` / `6A` / `6C` | EME ramp triple | 0 / 1536 / 2048 | 5120 / 5120 / 5120 | **unchanged** |
| `0xC6598` | EME float mirror | 1.0 | 5.0 | **5.0** |
| `0xC61C0` / `C2` / `C4` | DTC debounce | 1600 / 896 / 1280 | 65535 x3 | **unchanged** |
| `0xC64B4` / `B6` / `B8` | STEER_STATUS debounce | 24688 / 16438 / 112 | 65535 / 65535 / 255 | **unchanged** |
| `0xC61FA` / `0xC61F8` | `gp-0x671d` SET / RELEASE | 5530 / 1024 | 5530 / 1024 | **unchanged** |
| `0xC61F6` | r24 deadband | 3 | 3 | **unchanged** |
| `0xC6442` / `0xC6440` | gain_B latch arm / other arm | 1024 / 2048 | 1024 / 2048 | **unchanged** |
| `0xC61B4` / `0xC61BE` / `0xC62E6` | lane ceiling / sum clamp / fb clamp | 512 / 15360 / 7680 | 3072 / 15360 / 46080 | **unchanged** |
| `0xC6446` | **r24 ENGAGED arm** | 512 | 5244 | **4725** — the only one that moves |

**EVIDENCE.** Not one threshold, ceiling, debounce, ramp or monitor constant is touched.

### 3.2 The r24 block, re-derived (`0x3ABFA`–`0x3AC54`)

```
0x3ABFA cmp r0,r6 / be 0x3AC04       gp-0x671d latch state -> OUTRANKS
0x3ABFE ld.hu 0x7442,tp,r10          0xC6442 = 1024
0x3AC04 cmp r0,lp / be 0x3AC0E       ENGAGED (gp-0x6806 after the V104 repoint)
0x3AC08 ld.hu 0x7446,tp,r10          <<< THE EDITED CELL, ld.hu
0x3AC12 ld.hu 0x7440,tp,r10          0xC6440 = 2048
0x3AC18 mul r10,r8,r0 ; 0x3AC20 sar 0xa,r8        <<< Q10 CONFIRMED
0x3AC1C/26/38 ld.hu 0x71f6,tp         deadband 0xC61F6 = 3, applied 0x3AC24-0x3AC3C
0x3AC42..0x3AC54 addi/movea/cmovle    clamp r24 to +-0x2000 (8192)
```

`ld.hu`, Q10 (`sar 0xa`), the 8192 clamp — all confirmed. **Reducing the gain cannot create an int32
overflow that 5244 did not already have** (the multiplicand is unchanged and the multiplier is
smaller). Monotone-safe by construction.

### 3.3 Lockstep — cannot diverge from a cal change

All three writers of `gp-0x6b94` are immediately paired with a twin store of the **same register**:

```
0x3ACFA st.h r12,-0x6b94,gp   /  0x3ACFE st.h r12,-0x4ce0,gp
0x3AD12 st.h r12,-0x6b94,gp   /  0x3AD16 st.h r12,-0x4ce0,gp
0x3AD20 st.h r10,-0x6b94,gp   /  0x3AD26 st.h r12,-0x4ce0,gp   (r12 <- r10 @0x3AD24)
```

guarded by `cmp r15,r13 / bne 0x3AD2C` (previous twin vs previous primary). `gp-0x6b94` is clamped to
0x2800 (`0x3ACE8` / `0x3AD04`). **EVIDENCE: a calibration change moves both twins identically; the
lockstep monitor is structurally blind to it.** The same pattern holds in the governor for
`gp-0x6ace` / `gp-0x4cca`, `gp-0x6948` / `gp-0x4c58`, `gp-0x6934` / `gp-0x4c54`, `gp-0x6946` / `gp-0x4c56`,
each falling through to `FUN_0006b9fa` only on a *pre-existing* mismatch.

### 3.4 The governor is a slew limiter, and its step is unchanged

`FUN_0004503c` decompiled: step = (`0xC6206` or `0xC6208`, selected by `gp-0x67F5`) times `uVar15`,
shifted right 15, applied against the previous output held in `gp-0x138A` (first-tick-initialised from
`gp-0x6b94` under the `gp-5000` flag). **The step size depends on neither r24 nor the feedback filter.**

### 3.5 The plausibility monitor IS live and DOES report — and nothing in it changed

`FUN_0004595a`:

```
sVar4 = |gp-0x6b94| - |gp-0x6ace|                 -> gp-0x6aca
prod  = (gp-0x6b94/1024) * (gp-0x6ace/1024)       -> gp-0x6d9c
verdict = +1.0 iff (sVar4/1024 > -0.01) AND (prod > -0.01)   [raw compare vs 0xBC23D70B = -0.01f]
        = -1.0 otherwise                           -> gp-0x68cc
```

and in the governor, `gp-0x68CC` minus `gp-0x68CE` is range-checked against `gp-0x68CA` (0x800) and
`gp-0x68D0` (0) — a -1024 verdict is **below** the lower bound and calls
`FUN_0004613e(0x3702, ...)`. **So this is a real DTC report path, not a status byte.** V291 changes no
threshold, no cal and no instruction in it.

**NAMED RESIDUAL (BELIEF, not EVIDENCE).** The monitor's tolerance is an **absolute** -10.24 counts,
and the governor's compensation term (`gp-0x4F64` times `uVar17`, shifted right 15, negated) is
**torsion-bar-derived and does not scale with r24**. I therefore **cannot prove monotonicity in the
r24 gain from first principles.** What I can prove, and do:

- no threshold, cal or monitor instruction changed;
- the only change is one summand of an approximately 11-term sum, **downward** by 9.90 %;
- `gp-0x6b94` is clamped to 10240, so in the high-stress regime where the monitor sits nearest its
  limit the summand change is absorbed by the clamp and the stressed trajectory is unchanged;
- 4725 lies **strictly inside** the interval from stock's 512 to the seven-times-flown 5244.

So "no new trip" is **BELIEF-grade** here. It is not a FAIL: nothing points at a trip, and every
direction-of-change argument runs the safe way. But it is not proven, and the prereg's D3 wording
("in a way that changes their trip conditions") deserves that qualifier on the record.

### 3.6 The `gp-0x671d` latch does not become reachable by anything V291 changes

Thresholds unchanged (SET 5530, RELEASE 1024). The monitored quantity's producer is
resolver/FOC-domain (`gp-0x501c` / `gp-0x4fd8`), written by `FUN_00041d56` at `0x41EC6`. V291 **reduces**
the motor command (smaller r24; a slower feedback pole passes less high-frequency feedback), so the
direct channel moves the latch **away** from tripping. Note the arm's sign is inverted on V280+: a trip
collapses r24 to 1024, i.e. x0.195 on V282 and **x0.217 on V291** — if it trips, V291 loses slightly
less. **EVIDENCE for the direct channel.**

**CROSS-SURFACE DEPENDENCY (not stated in the prereg).** The only way V291 could *raise* the trip
rate is by de-stabilising the loop enough to increase motor motion — which is **surface B's GATE-2
question, not mine.** If B fails on transient authority or a new lightly damped pole, this D3
conclusion fails with it. The latch is **first-strike and drive-long** (`0x3ABFA` tests for non-zero,
not for a mature count; cleared only by `FUN_0003bcb2`), so one crossing removes roughly 78 % of the
r24 lane for the rest of the drive — a large, latched, one-way change in feel that would masquerade as
a build effect.

---

## 4. D4 — the b3 rung — PASS, and the pre-registration is wrong three ways

Cave decoded `0xC4B34`–`0xC4BD7` in **both** images with the decoder validated 60/60 above.

### 4.1 The edit is displacement-only

```
V282  0xC4BA8   24 37 81 c9   ld.w -0x3680[gp],r6
V291  0xC4BA8   24 37 d1 c2   ld.w -0x3d30[gp],r6
```

`hw1 = 0x3724` identical, so same opcode field 0x39, same base `r4` = gp, same destination `r6`; only
`hw2` changes, and **both are odd**, so both are `ld.w` (32-bit). **Same length, same register, same
width. EVIDENCE.**

### 4.2 No tear, and the cell is written whole

`gp-0x3d30` is `0xFEDF42D0`, **4-byte aligned**; the filter writes it with a single aligned `st.w` at
`0x28FA8`. An aligned 32-bit load is one bus transaction. **No tear is possible.** A cross-task
sampling *skew* remains — the cave may read any tick's state — but that is an interpretation caveat,
not a correctness one.

### 4.3 Honda's bits 0–2 are preserved

The rung's write-back, `0xC4BB2`–`0xC4BBF`:

```
ld.bu -0x1514[gp],r6 ; andi 0x67,r6,r6 ; or r7,r6 ; st.b r6,-0x1514[gp]
```

`0x67` = `0b0110_0111` clears bits 7, 4, 3 and **preserves 0, 1, 2, 5, 6.** The other two rungs use
`andi 0xbf` (bit 6 only) and `andi 0xdf` (bit 5 only). **Honda's bits 0–2 are never disturbed.
EVIDENCE.**

### 4.4 Three corrections to the pre-registration

1. **The buffer cell is `gp-0x1514` (`0xFEDF6AEC`), not `gp-0x1518`.** `gp-0x1518` has exactly
   **one** accessor image-wide (`0x21912`) and is not the cave's target. `gp-0x1514` has **14**:
   6 in the cave (`0xC4B54`, `0xC4B5E`, `0xC4B82`, `0xC4B8C`, `0xC4BB2`, `0xC4BBC`), 6 in Honda's
   0x14A builder (`0x55AAC`–`0x55B06`), 2 at `0x2194A` / `0x21964`.
2. **The re-pointed rung is `b3`, not `b7`.** The prereg's D4 says b7 twice; the orchestrator's
   brief body says b3; **the image says bit 3** (the `add 0x8,r7` at `0xC4BB0` under the `0x67` mask).
   Bits 7 and 4 of the same byte are written by the same instruction word from `sign(gp-0x6b4c)` and
   `sign(gp-0x6ada)` and are unchanged.
3. **It reads a 32-bit WORD, not "the low halfword".** `ld.w` plus `cmp 0x0,r6` plus `bge` tests the
   sign of the full int32 state, so prereg D4's failure mode (reads a halfword whose sign is not the
   sign of `s`) **cannot occur** — b3 equals the sign bit of `s` exactly, at every rate the car reaches.

### 4.5 Nothing depended on the old `gp-0x3680` read

A load is side-effect free, and the cave was a pure reader. `gp-0x3680`'s remaining two accessors
(`0x3A85C` `ld.w`, `0x3A87A` `st.w`) are the driver-torque-tracking PID's own D-term EMA state inside
`FUN_0003A382`. Census: V282 3 sites to V291 2. **Nothing downstream is affected. EVIDENCE.**

### 4.6 Register and stack usage unchanged

The cave uses only `r6` and `r7` as scratch plus `gp` (`r4`) and `r31` (`jmp [r31]` at `0xC4BD6`).
No stack frame, no `prepare` / `dispose`, no callee-saved register touched. Unchanged by the edit.

### 4.7 INSTRUMENT CAVEAT — the operator must know this before reading b3

`s = -1` is an **absorbing state** for every `a` in 923..1023, because the floor of `-a/1024` is -1 for
all `a` below 1024. With `b = 958` the input term (floor of `958*x/1024`) is **zero for rate magnitude
at or below 1 count**.

So **at rest, b3 reads 1 (negative) permanently**, and it only escapes once the rate magnitude reaches
**2 raw counts = 0.25 deg/s**. On V282's `b = 1560` escape needed only 1 count. A long run of b3 = 1
during straight-line hands-off is the **rest state**, not phase information. During a grinding episode
the rate amplitude is far above this, so the instrument works where it is aimed — but the duty
statistic must be conditioned on rate magnitude at or above 2 counts or it will be dominated by the
rest state. **Not a FAIL; a reading rule.**

---

## 5. D5 — the fork — PASS, and it is a confound if enabled

Working tree `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`, HEAD
`305732c85` (kit memory records `0f98d8c75` as of 2026-09-10 — it has moved).

- `common/params_keys.h:393` — `{"AccordCurvatureLead", {PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}}`,
  so the **declared default is "0"**, and `starpilot/system/the_galaxy/tests/test_device_settings_layout.py:504`
  asserts exactly that.
- `starpilot/common/starpilot_variables.py:828` — `default=False`, gated on
  `is_honda_accord and known("AccordCurvatureLead")`.
- Call site `selfdrive/controls/controlsd.py:607–611`:
  `if (CC.latActive and self.starpilot_toggles.accord_curvature_lead and not self.sm.valid['lateralManeuverPlan'])`
  then `new_desired_curvature = self.model_curvature_lead.update(...)`.

**With the toggle OFF, `new_desired_curvature` is not modified and nothing on the openpilot side
changes. EVIDENCE.**

**It IS a confound on the same drive.** It rewrites the desired curvature **upstream of the entire
lateral chain**, i.e. it changes the 0xE4 command stream that V291's loop change is measured against.
V291's pre-registered read is a transfer-function measurement between command and response (ring
half-peak decay about 545 ms to about 183 ms, 10 Hz T-vs-rate phase -14 deg plus or minus 4,
7.3 Hz -12.5 deg); changing the command's spectrum destroys comparability with the V282 baseline.
**Recommendation: keep `AccordCurvatureLead` OFF for the V291 drive.**

---

## 6. D6 — the dead twin island reads none of the three cells — PASS (control passes)

**Positive control first.** The island at `0x2A30E`–`0x2B421` must read `0xC63EC` and `0xC63EE`:

| cell | all sites | in-island | control |
|---|---|---|---|
| `0xC63EC` (output-lag `a`) | `0x2A184`, `0x2A8A2` | `0x2A8A2` | **PASS** |
| `0xC63EE` (output-lag `b`) | `0x2A174`, `0x2A892` | `0x2A892` | **PASS** |

**The three edited cells: ZERO in-island readers.** `tp+0x73E8` gives only `0x28F8A`; `tp+0x73EA` only
`0x28F86`; `tp+0x7446` only `0x3AC08`. `gp-0x3d30` gives `0x28F7C`, `0x28FA8`, `0xC4BA8`, none in the
island. **A verified zero, not a tool zero.**

---

## 7. Extra findings the pre-registration did not think of

**E1 — two V850E2 opcode-field collisions not recorded in this kit's scanner memories.** Both were
caught only because I validated my decoder against Ghidra's own listing; a scanner-only pass would
have shipped them.

- **Opcode field `0x3C` / `0x3D` is shared by Format-V `jr` / `jarl` and the 6-byte
  extended-displacement load.** `hw1 = 0x0780 | reg1` is *identical* for both. **Disambiguator: `hw2`
  bit 0** — a branch displacement is even (bit 0 = 0); the extended load carries a sub-opcode with
  bit 0 = 1. Verified: `jr 0x290B0` at `0x28F3C` = `80 07 74 01` (`hw2` even); `ld.h -0x4f60,gp,r6` at
  `0x59BFA` = `84 07 07 32 61 ff` (`hw2` odd).
- **Opcode field `0x3F` is shared by `ld.hu`, `mul reg1,reg2,reg3` (`hw2 = 0x0220`) and `setfcc`
  (`hw2` below `0x0020`).** Same disambiguator: **a real `ld.hu` always has `hw2` bit 0 = 1.** The
  documented `disp|1` quirk is not a quirk — it is the opcode discriminator. Verified: `mul r16,r7,r0`
  at `0x28F8E` = `f0 3f 20 02`, `setfnc r29` at `0x28F16` = `e9 ef 00 00`.

Over-matching without these rules is *safe for a null* (my D1/D2 nulls survive), but a **decoder**
without them reads `jr` as a load and `mul` as `ld.hu` — which is precisely how a phantom reader gets
invented. Worth a memory file.

**E2 — the whole boot region is absent from the flashed payload.** Every byte below `0x13000` is
`0xFF` in both V282 and V291 (the stock dump has 50,284 non-`0xFF` bytes there). **No build in this
lineage can change reset, RAM-init or the vector table.** Standing safety property; it is what makes
the cold-boot question in 2.3 a non-delta.

**E3 — `0xC6444` = 512 sits one halfword below the edited r24 arm and is read at `0x3AB5E`.** It was
not touched and must not be: my over-matching scan flagged it and it had to be adjudicated out. A
future edit in this neighbourhood should expect the same trap.

**E4 — cross-surface dependency, section 3.6.** D's claim that the latch does not become reachable is
conditional on B's stability verdict. State it on the artifact.

---

## 8. What a FAIL would have looked like, and what I actually found

The prereg fixed the FAIL conditions before the pass ran. Against them:

| prereg condition | result |
|---|---|
| D1 — any reader of `tp+0x73E8` / `73EA` other than `0x28F8A` / `0x28F86`, or of `tp+0x7446` outside the r24 block, by raw byte scan AND Ghidra | **not found** — 1 each, both methods, empty set-difference, controls 7/7 |
| D2 — any consumer of `gp-0x3d30` other than the filter's `ld.w` / `st.w`; any path on which the state can be stale at re-engage | **not found** — the one new consumer is the intended cave read; the filter runs every tick, four bails, none an engagement condition |
| D3 — the r24 change reaches EME / governor slew / lockstep / DTC thresholds in a way that changes a trip condition, or makes `gp-0x671d` reachable | **not found** — every cal byte-identical; lockstep writes twins from one register; latch channel moves the safe way. **One BELIEF-grade residual named in 3.5.** |
| D4 — rung reads a halfword whose sign is not the sign of `s`; change not displacement-only; bits 0–2 disturbed | **none of the three** — it is a `ld.w` (sign exact), the edit is displacement-only, mask `0x67` preserves 0–2. Prereg's own description corrected three ways. |
| D5 — with the toggle OFF something changes on the openpilot side | **not found** — default "0", call site gated. Confound if enabled; recommend OFF. |
| D6 — the dead island reads any of the three cells | **not found**, with a passing positive control |

---

## VERDICT: PASS

Surface D finds nothing that warrants "do not flash". Carried forward to the orchestrator:

1. **BELIEF, not EVIDENCE**, that `FUN_0004595a`'s plausibility check gains no new trip — the reason
   is stated in 3.5 and is a limit of what this surface can prove, not a defect found.
2. **The latch conclusion is conditional on surface B.** Section 3.6.
3. **Three corrections to the pre-registration's D4 text.** Section 4.4 — the cell is `gp-0x1514`, the
   rung is b3, and it is a word read.
4. **A reading rule for the b3 instrument**, section 4.7: it is pinned at 1 below 0.25 deg/s of rate,
   so its duty must be conditioned on a rate magnitude of at least 2 counts.
5. **Keep `AccordCurvatureLead` OFF for the V291 drive.** Section 5.
