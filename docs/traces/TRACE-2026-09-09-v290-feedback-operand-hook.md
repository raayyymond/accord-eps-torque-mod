# TRACE 2026-09-09 — V290 feedback-operand hook: site, headroom, RAM, flash, and the historical question

**Agent**: `fbhook` (SUBAGENT, orchestrator `main`). Study/analysis only — nothing built, flashed or sent.
**Tools**: GhidraMCP only for disassembly (`disassemble_bytes dry_run:true`, `get_xrefs_to`,
`search_instructions`, `get_function_jump_targets`); raw little-endian Python for every byte-level claim
and for every load-bearing null. **No mutating Ghidra call was made; nothing was saved.**
`gp = 0xFEDF8000`, `tp = 0xBF000`. Constants read little-endian.

**Programs**: `code.bin` (stock, `is_current: true`, 2086 functions, fully auto-analysed) for all
disassembly of the loop body — admissible because the V289 image is byte-identical to stock across the
whole of `FUN_00028ea6` except `0x2A174` (4 B, the V289 hook), **verified this session by a full-file
185-byte diff, not assumed** (§0). Raw byte work against the V289 image
`_v289_…SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ…_plain_image.bin`, sha256
`f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed`.

**Scripts (reproduce everything below)**
- `analysis-2020accord/verify/v290_fbhook_census.py` — image identity, hook-site bytes, cals, the
  gp-relative RAM census (own decoder, 7/7 positive controls), literal-pointer + `movhi`/`movea` scan,
  boot `.data` values, free flash.
- `analysis-2020accord/verify/v290_fbhook_headroom.py` — the operand's measured magnitude from the two
  V289 routes through Honda's byte-exact fb-filter mirror; int32 headroom table; RAM context dumps.
- `analysis-2020accord/verify/v290_fbhook_indirect_gate1.py` — the two indirect access classes a plain
  gp scan cannot see (`ep` windows, re-based `disp16`), with per-form positive controls.

---

## 0. Full-file diff, V289 vs V282 [EVIDENCE, Python]

```
185 bytes differ, in exactly these ranges:
  0x02A174-0x02A177 (4 B)   the sum-notch hook (jr 0xC4C00)
  0x0C4BD6-0x0C4BD9 (4 B)   \
  0x0C4BDC-0x0C4BF7 (28 B)   |  the cave prologue / INIT block
  0x0C4C00-0x0C4C09 (10 B)   |
  0x0C4C0B-0x0C4C1F (21 B)   |  the notch cave body
  0x0C4C21-0x0C4C8B (107 B) /
  0x0C4FFC-0x0C4FFF (4 B)   block CRC [0xC4000,0xC5000)
  0x0C63E8          (1 B)   fb pole a  923 -> 875
  0x0C63EA-0x0C63EB (2 B)   fb pole b 1560 -> 2301
  0x0C6FFC-0x0C6FFF (4 B)   block CRC [0xC6000,0xC7000)
```
⇒ **Nothing in `FUN_00028ea6` between `0x28EA6` and `0x2A174` is modified in V289.** Stock disassembly
of the feedback path is admissible; the site bytes were additionally read from all three images and
compared byte-for-byte (§1).

---

## 1. Q1 — WHERE THE FEEDBACK OPERAND IS FORMED, AND THE LAST POINT IT EXISTS AS ONE REGISTER

### 1.1 Formation [EVIDENCE, `disassemble_bytes dry_run:true`, `0x28F40-0x28FE0`]

```
0x28F4C  ld.h   -0x6a56, gp, r7      ; x = the rate operand (SIGNED halfword)
0x28F50  addi   0x2ee0, r7, r11      \  Honda's own input guard: |x| <= 12000
0x28F54  addi  -0x5dc1, r11, r0      |  fail -> jr 0x290B0 (the bail block; r26 := 0 @0x290B6)
0x28F58  bnc    0x28F5E              /
0x28F66  ld.bu  -0x3d2c, gp, r9      ; the filter's ENABLE byte
0x28F72  cmp    0x1, r9
0x28F76  bne    0x28F82              ; != 1 -> r6 := 0, r26 := 0  (Honda's own filter RESET)
0x28F7C  ld.w   -0x3d30, gp, r26     ; s_old  (32-bit private state)
0x28F86  ld.hu  0x73ea, tp, r16      ; b = cal(0xC63EA)  [V289 = 2301]   (UNSIGNED)
0x28F8A  ld.h   0x73e8, tp, r9       ; a = cal(0xC63E8)  [V289 =  875]   (SIGNED)
0x28F96  ld.hu  0x72e6, tp, r13      ; L = cal(0xC62E6) = 46080  (the clamp, loaded into r13 HERE)
0x28F9C  ld.hu  0x72e6, tp, r14      ; L again, into r14
0x28F8E  mul    r16, r7, r0          ; b*x
0x28F92  mul    r26, r9, r0          ; a*s_old
0x28F9A  sar    0xa, r7  ; 0x28FA0 sar 0xa, r9
0x28FA2  add    r7, r9               ; s_new
0x28FA4  add    r9, r26              ; <<< r26 = s_old + s_new  = THE TWO-SAMPLE SUM (DC 30.89)
0x28FA6  cmp    r13, r26
0x28FA8  st.w   r9, -0x3d30, gp      ; state := s_new (the increment, not the sum)
0x28FAC  ble    0x28FB2
0x28FAE  mov    r14, r26             ; r26 := +46080
0x28FB0  br     0x28FBE
0x28FB2  subr   r0, r14              ; r14 := -46080
0x28FB4  cmp    r14, r26
0x28FB6  bge    0x28FBE
0x28FB8  ld.hu  0x72e6, tp, r26
0x28FBC  subr   r0, r26              ; r26 := -46080
0x28FBE  mov    r26, r16             ; <<< THE CLAMP IS RESOLVED HERE; r26 = the final operand
0x28FC0  sar    0x5, r16   ; 0x28FC2 shl 0x5, r16 ; 0x28FC4 bp ; 0x28FC6 subr r0,r16
                                     ; r16 = | (r26>>5)<<5 | -- a RECTIFIED, 32-quantised copy that
                                     ;   feeds the per-variant table walk at 0x28FC8+ and ultimately
                                     ;   gp-0x6a34 (st.h @0x290CA)
```

### 1.2 Consumption — the subtraction [EVIDENCE, `0x29D40-0x29DA0`]

```
0x29D6A  mov    r8, r16              ; setpoint (from the assist-map LERP)
0x29D6C  mulh   r13, r16             ; * the per-variant scale
0x29D6E  ld.hu  0x72e4, tp, r10      ; r10 = cal(0xC62E4) = 4   -- LIVE, consumed at 0x29D7E
0x29D72  st.h   r16, -0x6a32, gp     ; <<< publish sp   (4 bytes, bytes 64 87 ce 95)
0x29D76  shl    0x5, r16             ; r16 = 32*sp
0x29D78  sub    r26, r16             ; <<< E = 32*sp - r26   THE SUBTRACTION
0x29D7A  mov    r16, r6 ; 0x29D7C sar 0x5,r6 ; 0x29D7E cmp r10,r6 ; 0x29D82 ble ...
```

### 1.3 The answer

**`r26` is the feedback operand, and it is a single 32-bit register value continuously from `0x28FBE`
(clamp resolved) to `0x29D78` (the subtraction) — 3,514 bytes of code with ZERO intervening accesses.**

[EVIDENCE, `search_instructions function:FUN_00028ea6 operand_pattern:"r26"` → **18 hits, reproduced
exactly this session**, matching `reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry`]:
the only `r26` hits in `[0x28FBE, 0x29D78]` are `0x28FBE` (a READ into r16) and `0x290B6` (a write on
the *bail* block, which is reached only by the three `jr 0x290B0` guards at `0x28F3C/48/5A/62`, all of
which are *before* `0x28FBE`). `r26` is **callee-saved** (`prepare {…,r26,…}` @`0x28EA6`, `dispose`
@`0x2A30A`) — that is why the compiler kept it live across that span.

**⇒ THE INJECTION POINT IS `r26`, anywhere in `[0x28FBE, 0x29D78)`.** The best site is at the *late*
end (§2), because injecting at `0x28FBE` also changes the rectified copy `r16` and therefore
`gp-0x6a34` and the per-variant table walk — a side lane a V290 has no reason to touch.

---

## 2. Q2 — THE 4-BYTE `jr`-SWAPPABLE HOOK

### 2.1 Chosen site: `0x29D72`, `st.h r16, -0x6a32, gp`, bytes **`64 87 ce 95`**

**Byte-verified in all three images** [EVIDENCE, Python]:
`V289 = 64 87 ce 95 | V282 = 64 87 ce 95 | stock = 64 87 ce 95` — **IDENTICAL**. V289 is a V282-based
build and does **not** use this site (V288 rev 2 did; V289 dropped V288's cave entirely, §0's diff
shows the V289 cave at `0xC4BD6`/`0xC4C00` and the hook only at `0x2A174`). **The site is free in V289.**

**This is the same site V288 rev 2 flew on 2026-09-08 and whose cave was confirmed LIVE from the tap**
(`docs/handoffs/2026-09/HANDOFF-2026-09-09-V288-FLEW-…`). That is empirical evidence that the site
executes on engaged ticks — the strongest available, and it is the reason to prefer it over an
unproven swap site.

### 2.2 Liveness at `0x29D72` [EVIDENCE, fresh disassembly of `0x29D40-0x29DA0`; independently agrees with `docs/specs/design/SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md` §1.3]

| register | state | why |
|---|---|---|
| **`r26`** | **LIVE — the feedback operand; THE TARGET** | consumed at `0x29D78`. A V290 cave writes its filtered value back here. |
| **`r16`** | **LIVE — holds `sp`** | produced by `mulh` @`0x29D6C`, consumed by `shl 0x5` @`0x29D76`. The cave must replicate the displaced `st.h r16,-0x6a32,gp` **and** leave `r16` unchanged. |
| **`r10`** | **LIVE — `cal(0xC62E4)` = 4** | loaded @`0x29D6E`, consumed @`0x29D7E`. Must survive. |
| **`lp`** | **LIVE** (the documented `0x29A2C`–`0x2A29A` reuse window contains this site) | **`jr` ONLY, never `jarl`.** |
| `r7` | **DEAD across `0x29D40`–`0x29DAE`** | appears as neither source nor destination anywhere in that 42-instruction listing. **Primary scratch.** |
| `r6` | dead-until-reassigned | last read @`0x29D50`; next write is a fresh `mov r16,r6` @`0x29D7A`. Usable scratch. |
| `r8`, `r9`, `r13` | dead by `0x29D6C` | `r13` is consumed by the `mulh` @`0x29D6C`; `r9` is freshly written @`0x29D80`; `r8` is consumed @`0x29D6A`. Usable scratch. |

**PSW/flag hazard: NONE at this site.** [EVIDENCE — read off the bytes] The instruction before the hook
(`0x29D6E ld.hu`) does not set flags, and the next flag *consumer* after the hook is `ble` @`0x29D82`,
whose flags are freshly armed by `cmp r10,r6` @`0x29D7E` — which is *after* the return point `0x29D76`.
**A cave here does not need to re-issue any `cmp`.** This is a material advantage over the `0x2A1B0`
post-lag site, where `cmp 0x1,r16` @`0x2A1AE` is live into `bne` @`0x2A1B4` and the cave must re-arm it
(prior trace, Q2).

`0x29D72` is **not a branch target** (`get_xrefs_to(0x29D72)` → *No references found*), so the 4-byte
`jr` cannot be jumped into mid-instruction.

### 2.3 The `jr` bytes

Encoding derived from the binary's own `jr`s and checked against two of them
[`0x29A5C jr 0x2A164` = `80 07 08 07`, disp `0x708`; `0x2A174 jr 0xC4C00` = `89 07 8c aa`, disp
`0x9AA8C`]: `hw1 = 0x0780 | (disp >> 16 & 0x3F)`, `hw2 = disp & 0xFFFF`, stored little-endian.

For a cave entry at **`0xC4C90`** (the first 4-byte-aligned free word after the V289 cave):
`disp = 0xC4C90 − 0x29D72 = 0x9AF1E` ⇒ **replace `64 87 ce 95` at `0x29D72` with `89 07 1e af`.**
(Well inside `jr disp22`'s ±2 MB.) The cave's return is `jr 0x29D76`.

### 2.4 What happens on the disengaged path — **THE ONE REAL HAZARD, and it has a known fix**

[EVIDENCE, `disassemble_bytes 0x29A44-0x29A78` + `get_xrefs_to(0x2A164)` = 2, `get_xrefs_to(0x2A0C6)` = 1
— the complete enumeration of skip routes; matches
`memory/accord/firmware/accord-disengage-skips-the-pid-hook-and-gp-0x6cf8-is-hondas-first-tick-sentinel.md`]

```
0x29A48  cmp r0,r14 ; setfne r20        ; r14 = engagement ramp gp-0x69b0
0x29A4E  cmp 0x1,r8 ; setfe  r8         ; r8  = gp-0x6805
0x29A56  bne 0x29A60 ; 0x29A5A bne 0x29A60
0x29A5C  jr  0x2A164                    ; SKIP #1 -- ramp == 0 AND gp-0x6805 != 1
0x29A62  bne 0x29A68
0x29A64  jr  0x2A164                    ; SKIP #2 -- r25 == 0 (inputs invalid)
0x29A68  ld.bu -0x680a,gp,r13 ; cmp 0x1,r13 ; bne 0x29A74
0x29A70  jr  0x2A0C6                    ; SKIP #3 -- gp-0x680a == 1
```

Consequences for a **feedback-side** cave at `0x29D72`:
1. **Ordinary disengage**: demand → 0 while the ramp walks down (0.10 s / 2.05 s, cals `0xC63F4/F6/F8/FC`),
   so the hook still runs for 1–3 s with `sp = 0` — **exactly the window V289's cave also runs in.**
2. **Once the ramp reaches 0, every tick skips the hook.** The cave's biquad state then **freezes**,
   while Honda's own fb EMA at `0x28F86` **keeps running every tick** (it sits at a lower address than
   the guard, so it is not skipped) and keeps tracking the driver's manual steering. On re-engage the
   cave would resume with state from seconds ago against a completely different `r26` — a step into a
   sharp resonator. **This is a bigger hazard for a feedback filter than it was for V288's setpoint
   filter, because `r26` is NOT small or zero while disengaged** (the driver is steering).
3. **Fix, already proven on this exact site**: seed on Honda's own first-tick sentinel
   `gp-0x6cf8 == 0x7FFFFFFF` (32-bit exact compare; written @`0x2A18C`, and loaded as the sentinel only
   on the three skip routes @`0x2A16C`/`0x2A0EA`). V288 rev 1 FAILED for omitting this; V288 rev 2 added
   it and passed. For a notch the correct seed is **not zero** — seed `x1 = x2 = y1 = y2 = r26` so the
   filter's output equals `r26` exactly on the first engaged tick (DC-consistent, no engage transient).

**BELIEF (flagged, not proven this session)**: that no branch inside `[0x29A74, 0x29D72)` skips forward
past `0x29D72`. `get_function_jump_targets(FUN_00028ea6)` shows the last target below the hook is
`0x29D6A` and the next is `0x29D84`, and the only enumerated skip jumps are the three above — but that
listing gives targets, not sources, so it does not *prove* the absence of a forward branch. **The
decisive evidence is empirical**: V288 rev 2's cave at this exact address was confirmed LIVE on the
wire over two routes. **Exact next step if a proof is wanted**: `analyze_control_flow` on
`FUN_00028ea6`, or a source-side scan of every conditional branch in `[0x29A74, 0x29D72)` for a target
`> 0x29D78`.

### 2.5 Alternative site, for completeness: `0x28FBE`+`0x28FC0` (`mov r26,r16` + `sar 0x5,r16`, 4 B)

Reachable (three clamp branches converge **on** `0x28FBE`; `get_xrefs_to(0x28FC0)` → *No references
found*, so the pair is a safe 4-byte swap). Its advantage: it sits **before** the engagement guard, so
it runs on **every** tick — no freeze, no seeding logic. Its disadvantage is decisive: the rectified
copy `r16` computed at `0x28FBE`–`0x28FC6` feeds the per-variant table walk at `0x28FC8+` and
`gp-0x6a34` (`st.h` @`0x290CA`, the only writer image-wide), so a filter here **changes a second,
unrelated lane**. **Not recommended** unless the design explicitly wants continuous state.

---

## 3. Q3 — NUMERIC HEADROOM

### 3.1 The clamp, confirmed from the bytes, and where it sits

**`cal(0xC62E6) = 46080` in V289 (and V282); stock is 7680** [EVIDENCE, Python LE u16 read of all three
images]. It is applied at `0x28FA6`–`0x28FBC`, i.e. **BEFORE any injection point in `[0x28FBE,
0x29D78)`**. A cave at `0x29D72` therefore receives an operand already hard-bounded to **±46080**, and
must itself re-clamp its output to ±46080 if it is not to widen `E`'s range (V289's cave used the same
discipline, clamping its output with `cal(0xC61BE)`).

### 3.2 The bound is REACHED on the wire [EVIDENCE, measured]

Honda's byte-exact fb-filter mirror run over the two V289 routes' `0x18F` rate stream (record's scaling,
8 raw counts per deg/s, cited not re-measured):

| route | max \|x\| raw | max \|r26\| pre-clamp | ticks at the ±46080 rail |
|---|---|---|---|
| r62_v289 (V282 pole) | 2641 (330 deg/s) | 74,553 | 200 / 97,545 = **0.205 %** |
| r62_v289 (V289 pole) | 2641 | 77,410 | 204 / 97,545 = **0.209 %** |
| r63_v289 (V282 pole) | 3098 (387 deg/s) | 85,322 | 662 / 70,559 = **0.938 %** |
| r63_v289 (V289 pole) | 3098 | 90,203 | 685 / 70,559 = **0.971 %** |

The clamp binds at `|x| ≈ 46080/30.89 = 1492` raw counts ≈ **186 deg/s** of wheel rate; both routes
exceed that. Honda's own input guard caps `|x|` at 12000, so the *theoretical* pre-clamp maximum is
`30.89 × 12000 = 370,680` — which is why the clamp exists. **Design to ±46080, not to a measured
percentile.**

⚠ **Caveat on the scaling** [BELIEF]: the raw-count conversion uses the record's "8 raw counts per
deg/s" and the `rate_f` (0x18F) channel. `rate_c` (0x14A) reads ~25 % larger on the same routes, which
this session did **not** reconcile. The conclusion ("the rail is reached") is robust to either scaling —
both put the peak far above 1492 counts.

### 3.3 Overflow of a V289-style Q14 TDF-II — **CONFIRMED, the brief is right** [EVIDENCE, arithmetic]

V289's coefficients: `b0 = 16048, b1 = a1 = −31842, b2 = 16048, a2 = 15712`, `a0 = 2^14`. Using the
design's own conservative bound `|acc| ≤ max|coeff| × xmax × 4`:

| operand | xmax | \|acc\| bound | int32? | margin |
|---|---|---|---|---|
| **V289's own `S`** (clamp `0xC61BE`) | 15360 | 1,956,372,480 | OK | **×1.10** |
| **`r26` unshifted** (clamp `0xC62E6`) | 46080 | 5,869,117,440 | **OVERFLOW** | ×0.37 |
| `r26 >> 1` | 23040 | 2,934,558,720 | **OVERFLOW** | ×0.73 |
| **`r26 >> 2`** | 11520 | 1,467,279,360 | OK | **×1.46** |
| **`r26 >> 3`** | 5760 | 733,639,680 | OK | **×2.93** |
| `r26` with Q12 coefficients | 46080 | 1,467,187,200 | OK | ×1.46 |

Note the single product `|b1 · x| = 31842 × 46080 = 1,467,279,360` **does** fit int32; it is the
*accumulator* that does not. V289 itself shipped with only ×1.10 of margin on this bound.

### 3.4 What keeps every intermediate inside int32 — concrete recommendation

**Recommended: pre-shift `x' = r26 >> 3` (`sar 0x3, rX`), run the V289 Q14 coefficient set unchanged,
post-shift `<< 3` (`shl 0x3, rX`), then re-clamp to ±46080.** Margin **×2.93** on the conservative
bound — nearly 3× what V289 flew with — while keeping V289's exact coefficient precision (the design
already flagged Q14 centre-frequency sensitivity; dropping to Q12 doubles that error).

Quantisation cost of `>>3`: 8 counts on a ±46080 operand = **0.017 %**, i.e. `8/30.89 = 0.26` raw rate
counts = **0.032 deg/s** of feedback resolution. Negligible against the loop's own scales. Keep V289's
first-order **error feedback** (`andi 0x3fff` on the `>>14` remainder) so the notch's DC gain stays
exactly 1 and no steady-state bias is introduced by the `sar` floor — V289's own build script asserts
that plain TDF-II parks up to 64 counts low without it.

**V850E2 instructions available, and their widths** [EVIDENCE, forms observed in this binary]:
- `mul reg1, reg2, reg3` — **32×32 → 64-bit**, low half into `reg2`, high half into `reg3`. Honda uses
  `reg3 = r0` everywhere to discard the high half (`0x28F8E`, `0x28F92`, `0x2A180`, `0x2A194`). The
  high half **is** available if a design wants 64-bit intermediate accumulation — but **V850 has no
  add-with-carry**, so 64-bit accumulation costs a manual carry (`cmp`+`setf`) per add and is not worth
  it here. Prefer the pre-shift.
- `mulh reg1, reg2` — 16×16 → 32 (used at `0x29D6C`, `0x2A1F6`). Not enough dynamic range for Q14
  coefficients against a ±46080 operand.
- `mulhi imm16, reg1, reg2` — 16×16 → 32 with an immediate.
- `sar imm5/reg, reg2`, `shl`, `shr` — arithmetic/logical shifts; `sar` floors toward −∞.
- `satadd reg1, reg2` / `satsub` — **32-bit saturating** add/sub. Worth using for the accumulator adds:
  an unforeseen overflow then saturates at ±2^31 instead of wrapping sign, turning a catastrophic
  sign inversion into a bounded error. Cheap insurance the V289 cave did not take.
- `andi imm16, reg1, reg2` — for the error-feedback remainder mask, as V289 uses.

---

## 4. Q4 — STATE RAM (GATE 1)

**Requirement**: 8–12 bytes of biquad state + one telemetry flag halfword. V289's own state cells
(`gp-0x6C44`/`6C40`/`6C3C`/`6C3A`) are **occupied by V289** and cannot be reused.

### 4.1 Independent re-verification of `gp-0x6D74..gp-0x6D2D` (72 bytes)

**Method (independent of the prior trace's script — own decoder, own controls):** a raw LE scan of the
V289 image decoding every gp-relative form — `ld.b`/`st.b` (op `0x38`/`0x3A`), `ld.h`/`ld.w`/`st.h`/`st.w`
(op `0x39`/`0x3B`, `hw2` bit 0 selecting width, **both covered bytes of a word marked occupied**),
`ld.bu` (op `0x3C`/`0x3D` with `reg2 ≠ 0` **and the `hw2`-bit-0 discriminator against the `jr`/`jarl`
Format-V collision**), the 6-byte extended `disp23` form (`reg2 == 0`), gp-direct bit-ops (op `0x3E`),
and `ld.hu` (op `0x3F`, `hw2` bit 0 fixed 1).

**Positive-control battery — 7/7 PASS** (a scanner that misses any of these is broken):

```
gp-0x3D30  fb filter state              hits=  2   PASS
gp-0x6A56  the rate operand             hits= 29   PASS
gp-0x6A32  setpoint publish             hits=  2   PASS
gp-0x6C44  V289 cave state s1           hits=  2   PASS
gp-0x674E  variant selector             hits=  7   PASS
gp-0x6B38  delivered lane torque        hits=  7   PASS
gp-0x6CF8  Honda first-tick sentinel    hits=  4   PASS
```

**Negative controls behave correctly**: `gp-0x6C44..gp-0x6C3A` (V289's own state) reports **11/11
displacements OCCUPIED** with the cave's own addresses; `gp-0x68B0..gp-0x68AA` reports **OCCUPIED**
(`ld.bu`/`st.b` at `0x4274A`, `0x42768`, `0x19AE0`, `0x1FB4E`, …), re-confirming `ADV-V289-D`'s
falsification of that old candidate.

**Result for the primary candidate:**

| check | result |
|---|---|
| gp-relative hits, all 9 forms, 72 bytes | **ZERO** |
| literal 4-byte LE address in `[0xFEDF128C, 0xFEDF12D3]`, any alignment, image-wide | **ZERO** |
| `movhi 0xFEDF` + `movea` pair landing in the run (433 `movhi 0xFEDF` sites scanned) | **ZERO** |
| `movea/addi <disp>, gp, rN` + `ld/st <disp2>, rN` re-based access (2,992 re-base sites, 332 resolved accesses) | **ZERO** |
| `ep`-window overlap (`movea/addi …,gp,ep`, 1,298 sites) | 9 bases within reach — **all adjudicated, none reaches the run** (§4.2) |
| overlaps the recorded stack band `gp-0xC000..gp-0x86E4` | **No** |
| boot `.data` value, all 72 bytes | **0x00000000**, and the surrounding all-zero region extends from `gp-0x6D94` to `gp-0x6D1C` |

The mapping used for boot values (`flash = 0x86260 + (addr − 0xFEDF11B0)`) was **validated by a
positive control before use**: `gp-0x6AB0` reads `0x02880288`, matching the prior trace's independently
recorded value.

The run is **bounded on both sides by live scalars** — `gp-0x6D78` (15 hits), `gp-0x6D7C` (2),
`gp-0x6D28` (2), `gp-0x6D24`/`6D20`/`6D1C` (5 each) — i.e. it is a genuine hole in a densely
gp-addressed pool, not an unscanned region.

### 4.2 The `ep`-window adjudication (a check the prior traces did not run)

`movea/addi <disp>, gp, ep` builds an `ep` base out of `gp`; `sld`/`sst` then reach up to ~255 bytes
above it, invisible to any `disp16` scan. **Nine `ep` bases sit 156–204 bytes below the candidate.**
Each was disassembled and adjudicated:

| ep site | base | why it cannot reach the run |
|---|---|---|
| `0x3AAD8` | `gp-0x6E30` (+188) | 4-knot LERP walk: x-array `gp-0x6E30..6E2A`, y-array `gp-0x6E28..6E22`; `add 0x2,ep` bounded by the knot loop ⇒ max advance **6 B** |
| `0x3ABA4`, `0x3AE42` | `gp-0x6E40` (+204) | same 4-knot walk, x `gp-0x6E40..6E3A`, y `gp-0x6E38..6E32` ⇒ max advance **6 B** |
| `0x3AF64` | `gp-0x6E30` (+188) | same family |
| `0x52D9C`, `0x52DA4`, `0x52E12` | `gp-0x6E14`/`gp-0x6E10` (+156/+160) | `add r28,ep` then `sld.bu 0x0`; `r28` bounded to 0..3 by `mov 0x3,r13; sub r28,r13; shl r13,…` @`0x52DDE` ⇒ **4-byte array** |
| `0x534A0` | `gp-0x6E10` (+156) | `add r26,ep` then `sld.bu 0x0`; `r26` is a bit index (`shl r26,r15,r13`) ⇒ ≤ 31, and even at the 127-byte `sld.b` ceiling reaches only `0xFEDF126F` < `0xFEDF128C` |
| `0x5645E` | `gp-0x6E20` (+172) | `sld.w 0x0, ep` only, no advance; `ep` is then re-pointed at `r6` |

**⇒ the `ep` residual is CLOSED for this candidate**, by instruction-level adjudication of every
overlapping base rather than by a bound assumption.

### 4.3 ⚠ A correction, and the reason not to trust a bare "zero gp hits"

The prior trace stated `gp-0x6AB0..gp-0x6AAA` was "confirmed occupied by this session's own scan too."
**My scan finds ZERO gp-relative hits there** — the falsification actually rests on its **boot value**
(`gp-0x6AB0` and `gp-0x6AAC` both = `0x02880288`, i.e. 648/648), not on any access. Its neighbours are
heavily gp-addressed (`gp-0x6AC0`: 30 hits, `gp-0x6ABC`: 18, `gp-0x6AB8`: 3, `gp-0x6AB4`: 1,
`gp-0x6AA8`: 1). **A cell that is initialised to a real value but has no scannable reader is being
reached some way the scanner cannot see.** The prior trace's *verdict* stands (do not use it); its
stated *method* does not. This is exactly why the primary candidate's all-zero boot image matters as
much as its zero hit count — and it is the honest measure of how far a static null can be trusted here.

**Residual, stated plainly**: a sufficiently indirect computed pointer (a base built in a register from
a non-`gp` source, or an `ep` re-point through a RAM pointer) is not excludable by static scanning —
the same residual this kit already accepts for every free-cell finding since `gp-0x1500`. Every check
this session's toolset supports was run and all pass clean.

### 4.4 Allocation proposal

`gp-0x6D74` (s1), `gp-0x6D70` (s2), `gp-0x6D6C` (error-feedback remainder), `gp-0x6D68` (FLAG halfword
+ spare) — 16 of the 72 bytes, all 32-bit aligned, all within `disp16` of `gp`, addressable with plain
`ld.w`/`st.w -0x6dNN, gp, rX` exactly as V289's cave addresses `-0x6c44`. **56 bytes spare** in the same
run for telemetry or a second section.

---

## 5. Q5 — FLASH

[EVIDENCE, exhaustive byte scan of the V289 image, not sampling]

```
[0xC4A00, 0xC4BD8)   472 B   non-0xFF = 470   OCCUPIED (V282's r24-comparator cave etc.)
[0xC4BD8, 0xC4C00)    40 B   non-0xFF =  30   OCCUPIED -- V289's own cave prologue/INIT block
[0xC4C00, 0xC4C8C)   140 B   non-0xFF = 138   OCCUPIED -- V289's notch cave body
[0xC4C8C, 0xC4FF0)   868 B   non-0xFF =   0   FREE
 0xC4FF0..0xC4FFB     12 B   01 01 01 01 00 00 c6 00 13 00 b2 00   (pre-existing, unidentified, untouched)
 0xC4FFC..0xC4FFF      4 B   a7 61 1f 82  = block CRC for [0xC4000, 0xC5000)
```

**868 free bytes at `0xC4C8C`.** A V289-shaped biquad cave is ~53 instructions / 140 bytes, so a second
one fits with ~6× headroom.

**The existing V289 cave region can host it — as a second, adjacent cave, not by extension.** The V290
feedback cave should start at **`0xC4C90`** (first 4-byte-aligned free word) and is a *separate*
subroutine reached by its own `jr` from `0x29D72`; V289's notch cave at `0xC4C00` keeps its own hook at
`0x2A174` untouched. Both live in the **same CRC block** `[0xC4000, 0xC5000)`, so **one CRC recompute at
`0xC4FFC` covers both** — no new block is touched, and the `0xC6000` block CRC only moves if the fb-pole
cals are changed again. **No second region is needed.**

---

## 6. Q6 — THE HISTORICAL QUESTION: why the feedback placement was dropped

**Verdict: it was NOT dropped for an engineering blocker. There is no recorded blocker. The design
tabulated the feedback placement, scored it, preferred the sum placement on one stated physics
argument, left the feedback hook explicitly open as an alternative — and then the build's
pre-registration was written against the *feedback* row's authority number while the build shipped the
*sum* row. The adversarial pass caught it after the fact.** [EVIDENCE — quotations below]

### 6.1 The design DID cost the feedback placement

`docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md` §5b carries both rows on the same axes
(columns: f/ζ · min\|1+L\| · Ms · \|dL\|<5 · Δ3.9 · gate73 · pkR/pkA · noise):

> `| (d-out) notch PID-sum Q3 | 22.3 / 0.032 [mode removed] | 0.58 [0.61] | 1.7 [1.6] | 9 % | −3.8° | 1.079 | 0.92 / 0.93 | 1.00 | #2 — the physics; fails the 7 Hz gate alone |`
>
> `| (d-fb) notch fb Q3 | 22.3 / 0.032 | 0.58 | 1.7 | 9 % | −3.8° | 1.079 | 1.03 / 1.00 | 1.00 | same loop; the setpoint's 20 Hz kick still reaches the motor |`

**Identical on every loop metric** (ζ, min\|1+L\|, Ms, LF gain, outer-loop phase, 7 Hz gate) —
as it must be, since a filter in the return path changes the return ratio identically. **The only
difference is authority: 1.03 / 1.00 (feedback) vs 0.92 / 0.93 (sum).** §7 repeats it:

> "notch PID-sum Q3 0.92 / 0.93 / 24 ms […]; **notch fb Q3 1.03 / 1.00 / 19 ms**"

### 6.2 The stated reason for preferring the sum — the whole of it

§5b's comment column: **"same loop; the setpoint's 20 Hz kick still reaches the motor"**, and §0.6:

> "**(2) the notch alone, Q 3 on the PID sum** — the cleaner physics (it also removes the D kick's 20 Hz
> content from the forward path)"

That is the complete recorded engineering argument: a forward-path notch additionally scrubs 20 Hz out
of the *command* (the D-kick), which a return-path notch does not. **It is a real argument, but it is a
preference, not a blocker** — and it is the same argument the V288 result has since undercut (V288
filtered the reference and the grinding was **unchanged**; the reference-side class is recorded as
exhausted).

### 6.3 The hook was explicitly left OPEN, not ruled out

§9 ("what this study is waiting on"):

> "2. The **hook for the PID-sum notch**: a 4-byte swap between the sum clamp and `0x2A174` with `lp` not
>    live, **or chain from the fb-operand site at `0xC4C00`** (then the notch is on r26, the forward path
>    stays unfiltered — 5b's d-fb row)."

and §1:

> "**the cleanest feedback-side hook is the existing V288 cave entry at `0xC4C00`** (r16 = sp and r26 = fb
> both live there)"

⚠ **That sentence has since gone stale and would mislead a V290 build**: `0xC4C00` was *V288's* cave
entry, reached by the `jr` at `0x29D72`. **V289 is V282-based and does not carry V288's cave** — §0's
diff shows `0xC4C00` in V289 is the *sum-notch* cave, hooked from `0x2A174`, and `0x29D72` is back to
stock. A V290 feedback cave must install its own `jr` at `0x29D72` (§2.3), not "chain from `0xC4C00`".

### 6.4 The mismatch, and where it was caught

`docs/review/ADV-V289-B-UNITS-LOOP-2026-09-08.md` §B3 — the adversarial pass, *after* the build:

> "The design's headline for 'the pair' — *capped-step peak rate/accel ×1.00/×1.00* (§0.6, §7, §8.1) — is
> the score of a **different topology**: `lm_final.log`'s (f) row is *'notch **fb** Q3 + fb pole 25 Hz'*,
> the notch on the feedback operand. V289 puts the notch on the **PID sum** (forward path). Reproducing
> the design's own linear method on its census plant: fb-notch + fb pole → **×0.998/×1.000**;
> sum-notch + fb pole (the build) → **×0.890/×0.934** […]. **§B3 was written against the 1.00/1.00
> figure, the built topology does not meet it, and the design text misattributes the figure.**"

and the V289 handoff:

> "**B3 failed because the design's authority row was for a different topology** (notch on the feedback
> operand). The built notch on the loop output removes the ring's own overshoot on a step. The operator
> judged that acceptable; it is recorded as his decision, not mine."

**⇒ THE MOST IMPORTANT FINDING FOR V290: no blocker was ever recorded against the feedback placement.
The ×1.00/×1.00 authority the operator's V290 requirement asks for is precisely the score of the
topology V289 did not build, and it is buildable — the hook exists, is byte-free in V289, has clean
liveness and no flag hazard, and has already flown once (V288 rev 2) at that exact address.** The one
genuinely new cost, not present for the sum placement, is the disengage-freeze problem (§2.4), and it
has a proven fix.

---

## 7. Summary

| Q | headline |
|---|---|
| Q1 | The operand is **`r26`**, formed as `s_old+s_new` @`0x28FA4` and clamp-resolved by `0x28FBE`; it is a single live register with **zero intervening accesses** all the way to `sub r26,r16` @`0x29D78` (18-hit whole-function `r26` census reproduced). Last point before the subtraction: `r26` at `0x29D72`. |
| Q2 | **Hook `0x29D72`, `st.h r16,-0x6a32,gp`, bytes `64 87 ce 95` → `89 07 1e af`** (`jr 0xC4C90`). LIVE: `r26` (target), `r16` (`sp`, must be re-stored and preserved), `r10` (`cal 0xC62E4`), `lp` (**`jr` only**). Scratch: **`r7`** (dead across `0x29D40-0x29DAE`), plus `r6`/`r8`/`r9`/`r13`. **No PSW hazard** — unlike the `0x2A1B0` post-lag site. **Disengaged**: hook runs through the 1–3 s ramp-down with `sp=0`, then is **skipped** by three `jr`s at `0x29A5C/64/70` ⇒ **cave state must be seeded on `gp-0x6cf8 == 0x7FFFFFFF`**, and for a notch the seed is `x1=x2=y1=y2=r26`, not zero. |
| Q3 | Clamp **`0xC62E6` = 46080**, byte-confirmed, applied **BEFORE** the injection point, and **reached on the wire** (0.2 % / 0.97 % of ticks on r62/r63). A V289-style Q14 notch **OVERFLOWS int32 at 46080** (bound 5.87e9, margin ×0.37). Fix: **`sar 3` pre-shift + `shl 3` post-shift**, Q14 coefficients unchanged ⇒ margin **×2.93** (V289 itself flew ×1.10) at a cost of 0.032 deg/s of feedback resolution. `mul` gives a 64-bit product but V850 has **no add-with-carry**; `satadd`/`satsub` are available and recommended for the accumulator. |
| Q4 | **`gp-0x6D74..gp-0x6D2D`, 72 bytes, RE-VERIFIED INDEPENDENTLY**: zero gp hits (9 forms, 7/7 positive controls, negative controls behave), zero literal pointers, zero `movhi`/`movea`, zero re-based `disp16`, **all nine overlapping `ep` bases adjudicated instruction-by-instruction and none reaches it**, boots all-zero, outside the stack band. ⚠ **Correction**: the prior trace's stated method for falsifying `gp-0x6AB0` was wrong (it has zero gp hits too); its verdict is right, and its non-zero boot value is the reason — do not use it. |
| Q5 | **868 bytes free, `[0xC4C8C, 0xC4FF0)`, all `0xFF`**. Put the V290 cave at **`0xC4C90`**, a second cave alongside V289's, in the **same CRC block** — one CRC recompute at `0xC4FFC`, no new region. |
| Q6 | **No blocker was ever recorded.** The design scored the fb placement (row `(d-fb)`, identical loop metrics, **authority 1.03/1.00 vs the sum's 0.92/0.93**), preferred the sum on one physics argument ("the setpoint's 20 Hz kick still reaches the motor" / it also scrubs the D-kick), and **left the fb hook explicitly open in §9**. The build shipped the sum; `ADV-V289-B` §B3 then FAILED the build because the pre-registration's ×1.00/×1.00 belonged to the fb topology. ⚠ The design's "chain from the fb-operand site at `0xC4C00`" is **stale for V290** — that was V288's cave; V289 does not carry it. |

## Open questions / verification needed

1. **[BELIEF]** No forward branch inside `[0x29A74, 0x29D72)` skips past the hook. Backed empirically by
   V288 rev 2's cave being LIVE at this exact address on two routes. **To make it EVIDENCE**:
   `analyze_control_flow` on `FUN_00028ea6`, or a source-side scan of every conditional branch in
   `[0x29A74, 0x29D72)` for targets `> 0x29D78`.
2. **[BELIEF]** The `rate_f` → raw-count scaling (8 counts/deg/s) is cited from the record, and `rate_c`
   disagrees by ~25 % on the same routes. Unreconciled. Does **not** affect the §3 conclusion.
3. **Not in scope, flagged**: whether the design's "the setpoint's 20 Hz kick still reaches the motor"
   argument still has force after V288 rev 2 flew a reference-side filter with the grinding unchanged.
   That is a design call for `main`/`design290`, not a tracing question — but it is the *only* recorded
   reason the feedback placement lost.
4. **Residual, unclosable by static scanning**: a computed pointer reaching `gp-0x6D74..gp-0x6D2D`
   through a base built from a non-`gp` source. Same residual the kit accepts since `gp-0x1500`.

## Files
- This trace.
- `analysis-2020accord/verify/v290_fbhook_census.py`
- `analysis-2020accord/verify/v290_fbhook_headroom.py`
- `analysis-2020accord/verify/v290_fbhook_indirect_gate1.py`

---

# ADDENDUM — 2026-09-09, second brief: the hook moves to the RATE OPERAND `x` at `0x28F4C`

Requested after `advnull` (`docs/review/ADV-V290-NULL-2026-09-09.md`) argued for filtering `x`
(bounded ±12000) rather than the fb sum `r26` (clamped 46080). **The argument is sound and the
arithmetic is decisively better — but one of the brief's own premises is wrong, and one new hazard
exists at `0x28F4C` that has no analogue at `0x29D72`.** Both are decision-bearing.

## A1 — `0x28F4C` characterised: CONFIRMED as the fb filter's own read; **REFUTED as "the only signed read"**

**`0x28F4C  ld.h -0x6a56, gp, r7`, bytes `24 3f aa 95`.** [EVIDENCE, `disassemble_bytes dry_run:true`]

- **CONFIRMED**: it is the LKAS rate PID's own read of the rate operand, and the **only** access to
  `gp-0x6a56` anywhere in `FUN_00028ea6` (Ghidra function-scoped census; the raw scan agrees).
- **REFUTED**: it is *not* "the only SIGNED read". **All 25 reads of `gp-0x6a56` image-wide are `ld.h`
  (signed). There is not one `ld.hu` on this cell.** The distinguishing property is *which function*
  it is in, not the load's signedness.

### The reader/writer census, both methods, set-differenced

**Method A — Ghidra `search_instructions operand_pattern:"0x6a56, gp"`** (a tighter filter than the
prior trace's `"6a56"`, so it carries **zero** branch-target digit coincidences and needs no
adjudication): **25 hits = 21 `ld.h` + 4 `st.h`.**

**Method B — raw LE Python scan of the V289 image, all 9 gp-relative forms, 7/7 positive controls PASS**
(`analysis-2020accord/verify/v290_fbhook_census.py`): **29 hits = 25 `ld.h` + 4 `st.h`.**

**Set difference — 4 readers Ghidra MISSES**: `0x2D9BE`, `0x4F942`, `0x4F964`, `0x5150E`. (The prior
trace reported 5 misses; `0x3F7F2` is *not* missed under the tighter operand pattern — corrected here.)
Nothing is found by Ghidra and missed by Python.

**Final census: 25 readers, 4 writers.** All 4 writers are `st.h` inside `FUN_0003F776` (`0x3F7B8`,
`0x3F7D0`, `0x3F7E0`, `0x3F81E`). Two of the 25 reads are self-reads inside that same producer
(`0x3F782`, `0x3F7F2`), leaving **23 external reads across 17 distinct functions**: `FUN_00028ea6`,
`FUN_0002b62c`, `0x2D9BE`, `FUN_0002eda8`, `FUN_00034a72`(x2), `FUN_0003b49a`, `FUN_0003eb38`,
`FUN_00040a50`(x2), `FUN_0004d8f0`(x2), `FUN_0004de0c`(x2), `FUN_0004e82e`(x2), `0x4F942`/`0x4F964`,
`FUN_0004fbde`, `0x5150E`, `FUN_000517ce`, `FUN_000557c8`, `FUN_00055c42`.

🛑 **CONFIRMED: `gp-0x6a56` must NOT be written.** 22 external readers outside `FUN_00028ea6` — the
base-assist boost/viscous lane, both CAN packers, the driver-override plausibility guard, the gentle-EME
re-arm gate. **Substitute into `r7` in-register only.**

## A2 — the ±12000 bound, and where it applies

[EVIDENCE, `disassemble_bytes` of the producer `FUN_0003F776`, `0x3F7A0-0x3F7F7`]

```
0x3F7AA  addi 0x2ee0, r6, r0          ; +12000 test
0x3F7AE  bgt  0x3F7C2
0x3F7B4  movea -0x2ee0, r0, r6        ; r6 := -12000
0x3F7B8  st.h  r6, -0x6a56, gp        ; <-- CLAMPED store
0x3F7C2  addi -0x2ee0, r6, r0         ; -12000 test
0x3F7C6  blt  0x3F7DA
0x3F7CC  movea 0x2ee0, r0, r6         ; r6 := +12000
0x3F7D0  st.h  r6, -0x6a56, gp        ; <-- CLAMPED store
0x3F7DC  sxh  r6 ; 0x3F7E0 st.h r6, -0x6a56, gp   ; in-range store
```
**`0x2EE0 = 12000`. The PRODUCER clamps — so `|gp-0x6a56| <= 12000` is guaranteed at the source.**

The consumer side is **not a clamp but a BAIL**, and it sits **after** `0x28F4C`, reading `r7`:
```
0x28F4C  ld.h  -0x6a56, gp, r7
0x28F50  addi  0x2ee0, r7, r11        ; r11 = x + 12000
0x28F54  addi -0x5dc1, r11, r0        ; r11 - 24001, result discarded, CY set
0x28F58  bnc   0x28F5E                ; |x| <= 12000 -> continue
0x28F5A  jr    0x290B0                ; else BAIL: r26 := 0 @0x290B6, st.b r0,-0x682f @0x290B8,
                                      ;   gp-0x6a34 := 0 @0x290CA, gp-0x3d2c := 2 @0x290D4
```
**Maximum `|x|` reachable at the site: 12000, byte-confirmed on both sides.**

## A3 — 🛑 THE NEW HAZARD: hooking AT `0x28F4C` puts the notch output through Honda's plausibility bail

The guard at `0x28F50`-`0x28F58` tests **`r7`**. If a cave at `0x28F4C` substitutes the notched value
into `r7`, **the guard tests the notched value, not the raw one.** A Q3 notch overshoots on a step —
V289's own build script asserts *"a 0 -> 15360 step peaks at 1.155x = 17735 for ~10 ms"* — so
`1.155 x 12000 = 13,860 > 12,000` and **the cave can spuriously trip Honda's sensor-implausibility
bail**, which zeroes the feedback, clears `gp-0x682f`, zeroes `gp-0x6a34`, and sets `gp-0x3d2c := 2`
(disabling the fb filter the following tick). That is a torque discontinuity manufactured by the cave.
**This hazard does not exist at `0x29D72`.**

**Mandatory mitigation (cheap, and physically free):** the cave must **clamp its output to ±12000
before writing `r7`** — the identical rail the producer already imposes, so the guard then behaves
exactly as it does today for every input. ~4 instructions.

**Alternative if the design prefers the guard to see the RAW `x`**: hook **`0x28F6A`
(`ld.hu 0x73e4, tp, r28`, 4 B, bytes `e5 e7 e5 73`, NOT a branch target)** — after the guard, before
the enable test — or **`0x28F86` (`ld.hu 0x73ea, tp, r16`, 4 B, bytes `e5 87 eb 73`, a branch target,
which is fine for a `jr`)**, which sits immediately before `mul r16,r7,r0` @`0x28F8E` and after both
the guard and the filter-enable/reset branch. Both leave the guard testing raw `x`; both have fewer
free scratch registers than `0x28F4C` (A4).

## A4 — Liveness and PSW discipline at `0x28F4C`

[EVIDENCE: straight-line `disassemble_bytes` of `0x28F40-0x28FE0` and `0x290B0-0x290D8`, plus a
Ghidra function-scoped `operand_pattern:"r7"` census of `FUN_00028ea6` — every register below is
classified by whether its **next access on every path out of the site is a WRITE**.]

**`r7`'s life as `x`**: written by `0x28F4C`, read exactly twice — the guard `addi` @`0x28F50` and
`mul r16,r7,r0` @`0x28F8E` (which also *overwrites* `r7` with the low product). No other access.
`[0x28F4C, 0x28F8E]` is the whole injection window.

| register | state at `0x28F4C` | evidence |
|---|---|---|
| **`r14`** | **LIVE** | read by `cmp r0,r14` @`0x28F5E`, before its next write @`0x28F9C`. |
| **`r10`, `r2`** | **LIVE — via the BAIL path** | `cmp r2,r10` @`0x290C8` and `cmp lp,r10` @`0x290D2` read them, and nothing in `0x290B0`-`0x290C8` writes either. Easy to miss; do not clobber. |
| **`r25`** | **LIVE** | read by `cmp r0,r25` @`0x29A60` (the engagement guard). |
| **`r20, r22, r23, r24, r27, r29`** | **LIVE** | callee-saved and used downstream (the same "must preserve" set V289's cave lists). |
| **`r15`** | **treat as LIVE** | no write found on the paths inspected; not proven dead. |
| **`lp`** | **LIVE** (`0x28EBC`-`0x290D2` reuse window) | **`jr` only, never `jarl`.** |
| **FREE SCRATCH** | **`r1, r6, r8, r9, r11, r12, r13, r16, r21, r26, r28`** | each written before any read on every path out: `r11`@`0x28F50`, `r9`@`0x28F66`, `r28`@`0x28F6A`, `r21`@`0x28F6E`, `r1`@`0x28F74`, `r6`@`0x28F78`/`0x28F82`, `r26`@`0x28F7C`/`0x28F84`, `r16`@`0x28F86`, `r13`@`0x28F96`, `r12`@`0x28FC8`, `r8`@`0x28FCC`; and on the bail path `0x290B0`-`0x290C0` writes `r1,r9,r22,r26,r28,r12,r25`. |

**11 free scratch registers — the most generous site in this function.** (At `0x28F86` the free set
shrinks to `r9, r13, r14, r16` + `r8, r12`, because `r6`/`r26` are by then the loaded filter state.)

**PSW/flag hazard: NONE at `0x28F4C`.** [EVIDENCE, read off the bytes] The flags entering the site were
consumed by `bc` @`0x28F46`; the next flag *consumer* is `bnc` @`0x28F58`, freshly armed by
`addi -0x5dc1,r11,r0` @`0x28F54` — i.e. **after** the return point `0x28F50`. The cave needs no `cmp`
re-issue. (Same clean result as `0x29D72`; contrast `0x2A1B0`, where `cmp 0x1,r16` is live into `bne`.)
`0x28F86` and `0x28F6A` are likewise flag-clean (last consumer before them is `bne` @`0x28F76`, armed by
`cmp 0x1,r9` @`0x28F72`; next is `ble` @`0x28FAC`, armed by `cmp r13,r26` @`0x28FA6`).

**Exact bytes**: replace `24 3f aa 95` at `0x28F4C`. For a cave at `0xC4C90`:
`disp = 0xC4C90 - 0x28F4C = 0x9BD44` ⇒ **`89 07 44 bd`** (`hw1 = 0x0780 | disp>>16`, `hw2 = disp & 0xFFFF`,
LE — the encoding checked against `0x29A5C` and `0x2A174`). The cave replicates `ld.h -0x6a56,gp,r7`,
filters `r7`, clamps to ±12000, and `jr 0x28F50`.

## A5 — ⭐ Execution on every tick, and the disengage behaviour — `0x28F4C`'s decisive advantage

`0x28F4C` sits at a **lower address than the engagement guard** (`0x29A48`-`0x29A70`), so **the three
skip jumps that bypass `0x29D72` do not bypass `0x28F4C`.** [EVIDENCE: `get_xrefs_to(0x2A164)` = 2
(`0x29A5C`, `0x29A64`), `get_xrefs_to(0x2A0C6)` = 1 (`0x29A70`) — the complete enumeration; all three
sources are above `0x28F4C`.]

⇒ **A cave at `0x28F4C` runs on EVERY tick, engaged and disengaged alike. There is no freeze, and the
`gp-0x6cf8 == 0x7FFFFFFF` seeding logic V288 rev 1 failed for is NOT required.** That removes the single
largest correctness risk identified for the `0x29D72` placement (§2.4 of the main trace).

The only guards above it are the function's own bails: `0x28F3C` and `0x28F46`+`0x28F48` (a mode check
on the `r6` parameter, `jr 0x290B0`); the two input guards at `0x28F5A`/`0x28F62` are **after** the
site. Honda's own filter-reset path (`gp-0x3d2c != 1` ⇒ `r6 := 0, r26 := 0` @`0x28F82`/`0x28F84`) is
also after the site; `gp-0x3d2c` is set to 2 only by the bail (`st.b r1,-0x3d2c,gp` @`0x290D4`, `r1 = 2`
from `0x290B0`), so the reset is rare. **BELIEF/design note**: the cave may wish to mirror that reset
(zero or DC-seed its own state when `gp-0x3d2c != 1`) for consistency; not required for safety.

## A6 — Headroom on `x`: **`advnull` is right, no pre-shift is needed**

Conservative bound `max|coeff| x xmax x 4` (the design's own), V289's Q14 set
(`b0=16048, b1=a1=-31842, b2=16048, a2=15712`):

| operand | xmax | \|acc\| bound | int32 | margin |
|---|---|---|---|---|
| **`x` at `0x28F4C`** | **12000** | **1,528,416,000** | **OK** | **x1.405** |
| `x >> 1` | 6000 | 764,208,000 | OK | x2.810 |
| `S`, V289's own | 15360 | 1,956,372,480 | OK | x1.098 <- what V289 shipped |
| `r26` (fb sum) | 46080 | 5,869,117,440 | **OVERFLOW** | x0.366 |

**On `x`, V289's exact Q14 coefficients fit int32 with x1.405 — strictly better than the x1.098 V289
already flew — with no pre-shift and no coefficient rescale.** Individual products at the rail:
`b0*x = 1.93e8`, `b1*x = 3.82e8`, `a1*y(1.155x) = 4.41e8`. **Recommendation: keep Q14, no pre-shift.**
If extra margin is wanted, `sar 1` / `shl 1` buys x2.810 at 2 counts of quantisation = **0.25 deg/s** of
*rate* resolution — noticeably coarser in this domain than the 0.032 deg/s the `>>3` cost on `r26`,
because `x` carries none of the EMA's x30.89 headroom. **Prefer no pre-shift; use `satadd`/`satsub` for
the accumulator adds as bounded-failure insurance** (V850 has no add-with-carry, so 64-bit accumulation
through `mul`'s high half is not worth its manual carry chain).

**Required regardless**: clamp the cave's output to ±12000 (A3), which also caps every downstream
intermediate exactly as today.

## A7 — LTI equivalence and the 46080 clamp: **true where it matters, NOT an identity**

The only elements between `x` (at `0x28F4C`) and `r26` (at `0x28FBE`) are the one-pole EMA
(`0x28F86`-`0x28FA4`, linear), the two-sample sum `(1+z^-1)` (linear), and the **±46080 clamp**
(`0x28FA6`-`0x28FBC`, the sole nonlinearity). **⇒ Notching `x` and notching `r26` are exactly
LTI-equivalent iff that clamp does not bind.** [EVIDENCE for the element list: §1.1 of the main trace.]

**Measured** (Honda's byte-exact fb mirror on both V289 routes' `0x18F` stream, V289 pole 875/2301;
`analysis-2020accord/verify/v290_fbhook_headroom.py`):

| route | \|r26\| p50 | p90 | p99 | p99.9 | max | ticks at ±46080 |
|---|---|---|---|---|---|---|
| r62 all ticks | 83 | 6,219 | 30,462 | 46,080 | 46,080 | 0.209 % |
| **r62 ENGAGED** | **180** | 5,912 | 23,856 | 37,537 | **44,500** | **0.0000 %** |
| r63 all ticks | 174 | 8,760 | 45,647 | 46,080 | 46,080 | 0.971 % |
| **r63 ENGAGED** | **182** | 4,657 | 26,560 | 46,080 | **46,080** | **0.2413 %** |

**Verdict, stated precisely:** the median engaged operand is ~180 counts — two-and-a-half orders of
magnitude below the rail — and on r62 the clamp **never binds while engaged at all**. In the grinding
regime the clamp is irrelevant and the two placements are equivalent. **But it is not "never binds":
on r63 it binds on 0.24 % of engaged ticks** (large manual/override steering, not grinding). The LTI
equivalence therefore holds for >= 99.76 % of engaged ticks and effectively 100 % of the phenomenon
under study, and is **not** a strict identity — worth one line in the design memo rather than a claim
of exactness.

## A8 — Summary of the addendum

| item | answer |
|---|---|
| A1 | `0x28F4C` **IS** the rate PID's own (and only in-function) read of `gp-0x6a56`. It is **NOT** the only *signed* read — **all 25 reads image-wide are `ld.h`**. Census re-run both methods: **25 readers / 4 writers**; Ghidra misses **4** (`0x2D9BE`, `0x4F942`, `0x4F964`, `0x5150E`). 22 external readers ⇒ **never write the cell**. |
| A2 | `\|x\| <= 12000` guaranteed **by the producer** (`FUN_0003F776` clamps at ±`0x2EE0` before all three `st.h`). The consumer's ±12000 test at `0x28F50`-`0x28F58` is **after** `0x28F4C` and is a **BAIL, not a clamp**. |
| A3 | 🛑 **NEW HAZARD**: at `0x28F4C` the notch output is what Honda's plausibility guard tests. Q3 step overshoot 1.155x ⇒ 13,860 > 12,000 ⇒ **spurious bail** (zeroes fb, clears `gp-0x682f`, sets `gp-0x3d2c := 2`). **The cave MUST clamp to ±12000 before writing `r7`.** No analogue at `0x29D72`. Guard-safe alternatives: `0x28F6A` (`e5 e7 e5 73`) or `0x28F86` (`e5 87 eb 73`). |
| A4 | **LIVE**: `r14`, `r10`, `r2` (both via the BAIL path), `r25`, `r15` (unproven), `r20/22/23/24/27/29`, `lp` (**`jr` only**). **FREE: `r1, r6, r8, r9, r11, r12, r13, r16, r21, r26, r28` — 11 registers.** **No PSW hazard.** Replace `24 3f aa 95`; `jr 0xC4C90` = **`89 07 44 bd`**; return to `0x28F50`. |
| A5 | ⭐ `0x28F4C` is **above** the engagement guard, so **none of the three skip jumps bypasses it — it runs every tick, engaged and disengaged. No freeze, no `gp-0x6cf8` seeding required.** The strongest argument for the site. |
| A6 | Q14 on `x` fits int32 at **x1.405**, better than the x1.098 V289 flew. **No pre-shift, no rescale.** `sar 1` buys x2.81 but costs 0.25 deg/s of rate resolution. Use `satadd`/`satsub`. |
| A7 | LTI-equivalent **iff** the 46080 clamp is inert. Engaged: r62 **0.0000 %** at the rail, r63 **0.2413 %**; median engaged \|r26\| **180/182**. Equivalent in the grinding regime; **not a strict identity**. |
| 4, 5, 6 | Unchanged from the main trace: RAM `gp-0x6D74..gp-0x6D2D` (72 B, six methods incl. an `ep`-window adjudication of all nine overlapping bases); flash 868 B at `[0xC4C8C, 0xC4FF0)`, cave at `0xC4C90`, same CRC block; **and NO blocker was ever recorded against the feedback placement** (§6). |

**Site recommendation**: `0x28F4C` **with a ±12000 output clamp inside the cave** — it dominates
`0x29D72` on every axis (11 free registers vs 5; runs every tick vs needing sentinel seeding; x1.405
headroom vs needing a `>>3` pre-shift) and its one new hazard is closed by four instructions. If the
design would rather the cave's output never face Honda's plausibility test, hook `0x28F6A` instead and
accept the smaller scratch set.
