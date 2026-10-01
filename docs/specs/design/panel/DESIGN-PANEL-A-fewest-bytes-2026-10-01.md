# DESIGN PANEL A — FEWEST BYTES (2026-10-01): the speed-re-keyed angle loop

**Status: DESIGN ONLY. Nothing built, flashed or sent. The fork was not touched.** Ghidra was used read-only
(`disassemble_bytes dry_run`, `read_memory`) on the open **V294** program, which is code-identical to V295 except cal
`0xC63EA` (b 567→1050) and its page CRC. Every pre-edit byte was re-read from the image this session.

**Author:** Designer A (fewest bytes), a subagent (Opus) reporting to the orchestrator `main`. Four other designers
work the same problem from other angles; this page does **not** pick a winner across its own implementations — the
judges do.

**The angle:** find the SMALLEST firmware edit that gives a usable 1 kHz angle loop, and state exactly what it cannot
do. Two implementations are delivered and both scored on the full credible set:

- **A1 — ZERO CAVES.** The in-place code edits + cals only, with the **speed re-key** of the existing Kp/Kd LERPs so
  that Kp(v) and Kd(v) are scheduled on **speed** (not the demand index), plus a **flat Ki**. **24 code + 1 version =
  25 in-place bytes + 50 cal bytes = 75 total, NO CAVE, 0 new RAM words** (+4 for the optional B2 mode-3 interlock).
- **A2 — A1 + the smallest cave** that adds only what A1 structurally cannot: a **speed-scheduled Ki** (the integrator
  corner cannot track speed with a single Ki cal). A1's 24 code + the 4-byte cave hook + 1 version + 50 cal + **one
  ~100-byte cave (64 code + 36 table) = ~179 total, 1 cave, still 0 RAM** (register in, register out — no new state
  word, so no GATE-1 init burden and no new wire instrument).

**Evidence.** Every number is from a script in `analysis-2020accord/studies/angle_loop/panel/A-fewest-bytes/`
(`panel_schedules.py`, `panel_fast.py` [vectorised FRF, validated == `stab_lin.margins` to 0.00°], `panel_gate2.py`,
`panel_numbers.py`, `panel_time.py`), run this session with fixed seeds. Caches in
`_scratch/angle_loop/panel/A-fewest-bytes/`. The credible-set member source is `c1/c1r2_members.py` (the full
factorial of damping × inertia × delay × hold-age — it already carries b_q×J_hi, b_q×J1.0, b_q×tau6 and every +h10;
`selfcheck` 781/781 triples identical to the refuter's own `member_params`). Marked **EVIDENCE** (with method) or
**BELIEF**.

---

## 0. The decision in one page

| | **A1 (zero cave)** | **A2 (A1 + Ki cave)** |
|---|---|---|
| firmware edit | 24 code + 1 version + 50 cal = **75 B, no cave** | A1 + 4-B hook + **~100-B cave**, no RAM = ~179 B |
| Kp(v) | full envelope (C1 rev 2's Kp_eff), 5-knot speed LERP | **0.72×** that envelope |
| Kd(v) | 20/18/14/10 at 3/8/17/27 m/s (the re-key schedules it) | same |
| Ki | **flat 80** | **Ki(v) = 0.5·Kp(v)** (constant PI corner) |
| GATE 2 tier A (PM≥45, GM≥6) | **PASS** — min PM 58.5°, GM 12.0 dB | **PASS** — min PM 54.5°, GM 13.7 dB |
| GATE 2 tier B (PM≥30, GM≥6) | **PASS except ONE point** (29.5° at aged b_q·J1.0·tau6 @14.5 m/s — stable, exact GM 13.3 dB) | **PASS** — min PM 32.3°, GM 7.6 dB |
| 20 Hz loop gain vs V295 | **0.53×** (L20); M20 1.9 vs 3.58 | **0.53×**; M20 1.9 |
| turn-hold ≥ 0.90 (≥8 m/s) | **MISS at 15–17 m/s** (0.886–0.935) — the flat-Ki penalty | **PASS** (≥0.990 every band) |
| what it cannot do | scheduled integral corner; I-freeze on hand torque | I-freeze on hand torque; the aged J≈1 world; re-key quantisation |

**One-line verdict for the judges.** A1 is the smallest thing that is a real, GATE-2-stable angle loop (29 bytes, no
cave) but **gives up highway turn-hold** because one flat Ki cannot serve a 2.7:1 Kp range. A2 spends ~100 cave bytes to
buy back the integral corner — turn-hold returns to ≥0.99 and the whole credible set gates — at the cost of 0.72× peak
P authority. Neither removes the 13–17 Hz anti-damping that the D-on-rate term adds (declared miss, both).

---

## 1. The re-key — the fewest-bytes lever (EVIDENCE: Ghidra dry run + ISA, this session)

With edit **E4** the setpoint is loaded from `gp-0x69ae` (`0x29D6A ld.h`), so the map LERP output `r13` is **dead for the
setpoint** and the map walk `0x29CFC..0x29D68` is free. The re-key reuses that dead region to put the **speed index**
into the Kp/Kd LERP key:

```
0x29CFC  mov 0xc9a88,r16        30 06 88 9a 0c 00   ->   ld.bu -0x6a5d[gp],r7 ; br 0x29D10   a4 3f a3 95 85 0d  (6B)
0x29D18  sld.hu 0x2,ep,r10      71 50               ->   br 0x29D6A                            95 2d             (2B)
```

- `-0x6a5d[gp]` is the **high byte** of the 16-bit speed word `gp-0x6a5e` (64 counts/km/h), so `r7 = speed>>8`
  = 1.111 m/s per count (range 0..~27 for 0..30 m/s). EVIDENCE: the odd-displacement `ld.bu` encoding `a4 3f a3 95`
  verified against the in-image control `ld.bu 0x74f1,tp,r16 = a5 87 f1 74` (hw2 = disp|1; opcode field 0x3D for odd
  disp); `br +0x10 = 85 0d` and `br +0x52 = 95 2d` decoded from the V850 Format-III disp and checked against the
  in-image `br 0x40 = 85 25` and `br 0x12 = 95 0d`.
- After `br 0x29D10`, `0x29D10 mov r7,r22 ; zxb r22 ; st.b r22,-0x674b` carries `speed>>8` into **r22** (the Kd LERP
  key byte) and the demand tap cell `gp-0x674b`; then `br 0x29D6A` skips the map walk straight to E4.
- The Kp LERP (`0x29DE8 zxh r7`) and the Kd LERP (key `r22`) are now **speed-indexed**. Their record X-knots and
  Y-values become the schedule (cals). EVIDENCE: Ghidra listing of `0x29CD4..0x29E32`.

**Liveness on the new path (EVIDENCE, first-use scan of `0x29D10..0x29DCC`):** `ep` is rebuilt at `0x29DCC` (map ep
unused between); `r6`/`r10`/`r13` are all rewritten before any read (`r6` at `0x29D7A`, `r10` at `0x29D6E`, `r13` at
`0x29D8C`); the garbage `r13` (map Y) is irrelevant because E4 replaced the `mulh r13,r16`. `r7`/`r22` survive to the
LERPs. `r25` (live `0x29A82..0x2A0AC`) is untouched.

**Readers of the re-keyed cells (EVIDENCE: C0 §3.6, dual-form Python scan, control `gp-0x682f`):** `gp-0x674b` and
`gp-0x697a` have 2 writers and **0 direct control readers** — they are telemetry. ⚠ The re-key changes what the demand
tap reads: `gp-0x674b` now carries `speed>>8`, not the demand index. The instrument (§8) accounts for this.

---

## 2. A1 — the zero-cave angle loop

### 2.1 Every in-place byte (EVIDENCE: Ghidra dry run on V294, bytes re-read from V295)

| id | address | old → new | old → new instruction | loop term |
|---|---|---|---|---|
| E1 | `0x28F4E` | `aa 95` → `00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | operand x = θ (0.1° counts); ±12000 bail now on θ |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new (2-tap FIR) |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae (−raw) |
| E5a | `0x29EDE` | `c7 00` → `80 39` | `zxh r7` → `subr r0,r7` | r7 = −Kd |
| E5b | `0x29EE0` | `10 40 bb 41` → `24 47 aa 95` | `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D operand = rate x (1 kHz) |
| RK1 | `0x29CFC` | `30 06 88 9a 0c 00` → `a4 3f a3 95 85 0d` | `mov 0xc9a88,r16` → `ld.bu -0x6a5d[gp],r7 ; br 0x29D10` | key := speed>>8 |
| RK2 | `0x29D18` | `71 50` → `95 2d` | `sld.hu 0x2,ep,r10` → `br 0x29D6A` | skip the dead map walk |
| A2g | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | PID runs iff ramp≠0 ∧ request==1 (kills the 0x7FFF sentinel pulse + override wind-up) |
| V1 | `0x1310D` | `30` → `41` | data: 14th char of the F181 string | "39990-TVA,A160" → "…,A16A" (fork interlock) |

**Byte total: 24 code + 1 version = 25 in-place bytes + 50 cal bytes = 75 (zero cave).** Cal bytes: a/b/C/DB/Ki/ICL/DCL
(7×2=14) + Kp record X(10)+Y(10) + Kd record X(8)+Y(8) = 50. (RECOMMENDED interlock add-on, **+4 bytes → 79**: **B2**
`0x29A50 e2 47 00 00 → e0 df 34 43` = `cmovne r0,r27,r8`, adding the mode-3 dominance bVar2 to the request bit —
EVIDENCE tracer, dominance semantics the less-certain claim; include it to also gate the mode-3 exit, §7 C8.)

### 2.2 Calibration (A1)

| cell | stock | V295 | **A1** | what it is |
|---|---|---|---|---|
| a `0xC63E8` | 923 | 1011 | **0** | fb pole → pure 2-tap FIR |
| b `0xC63EA` | 1560 | 1050 | **8192** | fb gain → s_new = 8θ (r26 = 16θ) |
| C `0xC62E6` | 7680 | 1024 | **65535** | r26 clamp → |θ| ≤ 409.6° |
| DB `0xC62E4` | 4 | 4 | **0** | I deadband 0 (highway error is 1–2 LSB; C0 §2.3) |
| Ki `0xC63E6` | 0 | 0 | **80** | **flat** integral gain |
| ICL `0xC61BA` | 10240 | 10240 | **4096** | I clamp (≈660 T), bounds override-release lurch |
| DCL `0xC61B6` | 10240 | 0 | **10240** | D clamp (re-enabled) |
| Kp record (sel 7) X | idx knots | idx | **(2,7,10,15,24)** key=speed>>8 | re-keyed X |
| Kp record (sel 7) Y `0xE5384`×5 | 248… | 960×5 | **(411,561,330,536,883)** | Kp(v), = C1 rev 2 Kp_eff |
| Kd record (sel 7) X | idx | idx | **(2,7,15,24)** key=speed>>8 | re-keyed X |
| Kd record (sel 7) Y `0xE5126`×4 | 128 | 0 | **(20,18,14,10)** | Kd(v): D = (−Kd·x)>>3 |
| PCL/SCL/OCL/fade/output-lag | — | V295 | **unchanged** | authority stays inside the existing clamps |

### 2.3 The loop in integer form (A1) (EVIDENCE: `lane_mirror_v295` arithmetic + the schedules)

```
theta_sp = -raw            (gp-0x69ae = clamp(-4*raw, +-16384); 0.1 deg per count)
r26 = 8*theta[n] + 8*theta[n-1]                         (= 16*theta at rest; a=0,b=8192,sum)
E   = (gp-0x69ae << 2) - r26 = 16*(theta_sp - theta)    (counts)
key = speed>>8                                          (re-key; 1.111 m/s per count)
Kp  = LERP((2,7,10,15,24),(411,561,330,536,883), key)   P = clamp((E*Kp)>>8, +-15360)
Kd  = LERP((2,7,15,24),(20,18,14,10), key)              D = clamp((-Kd*x_rate)>>3, +-10240)
I   = clamp(I + ((E>>5) * 80) >> 3, +-(4096<<7))        contributes I>>7
S   = fade * ((I>>7) + P + D) ; output lag 5.05 Hz ; x ramp ; x 5346/32768 ; clamp +-3072  -> T (rail 2461)
```
T at DC, hands off ≈ **Kp(v)/10 T counts per degree** (41–88 T/deg across 3–30 m/s). EVIDENCE arithmetic + selftest.

### 2.4 GATE 2 on the FULL credible set (EVIDENCE: `panel_gate2.py A1`, `gate2_A1.json`; two methods; ages 0 and 10)

Members: `c1r2_members` TIER_A (7) + TIER_B (62) on a 1 m/s grid + the plant knots (3.1/8.0/11.9/12.5/17.0/26.9),
each at hold age 0 and 10. Method 1 = `panel_fast` vectorised LTI FRF (PM = min over |L|=1 crossings, LTI GM, Ms,
|S|/|Tc| 5–30 Hz) validated == `stab_lin.margins`. Method 2 = `stab_lin.exact` (periodic monodromy ρ + poles);
`exact_gm` spot-checked on the worst points.

| metric | A1 result | bar |
|---|---|---|
| tier A min PM | **58.5°** (b_lo @8.0 m/s, aged) | ≥ 45 ✓ |
| tier A min LTI GM | **12.0 dB** | ≥ 6 ✓ |
| tier A unstable (ρ≥1) | **0** | 0 ✓ |
| tier A min 5–50 Hz pole ζ | 0.58 @5 Hz | ≥ 0.2 ✓ |
| tier A max |S| 5–30 Hz | **+3.6 dB** (b_lo @7.5, aged) | ≤ +3 — **MINOR MISS** (×1.5, see M4) |
| tier B min PM | **29.5°** (b_q·J1.0·tau6+h10 @14.5) | ≥ 30 — **1 point 0.5° under** (stable, exact GM 13.3 dB, ρ 0.993) |
| tier B min LTI GM | **6.5 dB** | ≥ 6 ✓ |
| tier B unstable | **0** | 0 ✓ |
| nominal min PM / GM / M20 | 79.3° / 14.5 dB / 1.9 | — |
| worst Re(T/ω) 13 Hz (aged) | **−0.773** (V295 −0.15) | reported — **MISS M3** |
| worst Re(T/ω) 20 Hz (aged) | **−0.709** (V295 −0.633 un-aged; un-aged A1 −0.37…−0.52 ≤ V295) | ≤ V295 like-for-like ✓ |
| max M20 (record conv.) | **1.9** (V295 3.58, V282 44.9) → 0.53× | ≤ V295 ✓ |

### 2.5 Time-domain gates (A1) — see §4 (run together with A2)

### 2.6 A1's pre-declared misses, each with a revert signature

- **M1 (turn-hold at highway).** EVIDENCE `panel_numbers.py`: turn-hold |T(0.05 Hz)| = 0.935 @15, **0.886 @17**,
  0.890–0.916 @19–30 m/s — **below the 0.90 gate at 15–17 m/s.** Cause: a single flat Ki = 80 against a 2.7:1 Kp range
  gives an integral corner of only 0.09·Kp/Kp at highway; a higher flat Ki goes unstable on the aged combined members
  (panel_explore: Ki 300 → tier B unstable). This is the structural reason A2 exists. **Revert signature:** operator
  reports "loose / drifts out of the lane on long highway curves"; or steady-state lane error grows with curve
  duration at ≥15 m/s. **Caught by:** the 427/0x14A torque tap — I-share of the delivered torque stays small and the
  steady angle error does not integrate out.
- **M2 (0.2–0.5 Hz tracking lag).** EVIDENCE: in-phase 0.5 Hz tracking 0.72 @17 m/s (A2 0.96). S-bends and lane changes
  at highway lag. **Revert:** "sluggish to settle after a lane change." The goal's own metric (0.04–0.08 Hz, C1 rev 2
  weighting) still passes (I dominates there).
- **M3 (13–17 Hz anti-damping).** Shared with A2 — see §5.
- **M4 (|S| peak at ~7.5 m/s aged).** +3.6 dB (×1.5) on the aged b_lo world — a mild disturbance-amplification peak
  just over the +3 dB tier-A bar. **Revert:** a 5–30 Hz texture/buzz that appears only hands-off at ~25–30 km/h.
- **M5 (no I-freeze on hand torque).** EVIDENCE tracer: I's only input is E; the post-PID fade never touches the
  accumulator; I resets only on skip. The override-release lurch is bounded by ICL 4096 (≈1.7° overshoot after a 1 s
  hand hold at 26 m/s; tracer/harness). **Revert:** "the wheel kicks back when I let go after fighting it." A2 shares
  this (its cave schedules Ki, it does not freeze I).
- **M6 (re-key quantisation).** The speed key is `speed>>8` = 1.111 m/s per count and only 5 Kp / 4 Kd knots. Between
  knots the LERP interpolates continuously; the limit is 5 knots over 0–30 m/s. BELIEF: adequate (the Kp_eff curve is
  smooth); the dip at 11–12.5 m/s is captured by the idx-10 knot.

---

## 3. A2 — A1 + the smallest cave (a speed-scheduled Ki)

### 3.1 What A1 structurally cannot do, and the minimal cave for it

A1's integrator reads one flat Ki cal (`0x29D9C ld.hu 0x73e6[tp],r6`). There is no speed-indexed Ki anywhere in the
lane (EVIDENCE tracer §3.6). The flat Ki is the cause of M1/M2. The minimal fix is a cave that makes **Ki track
speed**, leaving P and D scheduled by the re-key (so P is NOT double-scheduled).

**The cave (≈100 bytes: 64 code + 36 table), inside the free span `0xC4BD8..0xC4FEF` (all 0xFF, EVIDENCE read_memory).
NO RAM write.** It hooks the Ki load and walks a speed→Ki table keyed on **r7**, which still holds `speed>>8` at that
point (the Kp LERP that overwrites r7 is later, at `0x29DE8`; EVIDENCE listing order):

```
hook: 0x29D9C  ld.hu 0x73e6[tp],r6   e5 37 e7 73   ->   jr 0xC4C00   (4 bytes in place; 0x29D9C stays a valid
                                                                       branch target from 0x29D8A/0x29D94)
0xC4C00  mov   r7, r8                 r8 = key = speed>>8 (preserve r7 for the Kp LERP)
         mov   <TBL>, r13             table pointer (mov imm32, 6 B)
         ld.hu 0[r13], r6             X0
         cmp   r6, r8 ; bh WALK       key > X0: walk
         ld.hu 2[r13], r6             Ki = Ki0 (clamp low) ;  jr 0x29DA0
WALK:    ld.hu 6[r13], r6 ; cmp r6,r8 ; bnh SEG ; addi 6,r13,r13 ; br WALK
SEG:     ld.hu 0[r13], r6 ; sub r6,r8          dk = key - X(i)
         ld.h  4[r13], r6 ; mul r6,r8,r0 ; sar 8,r8     dk*S(i) >> 8   (S Q8)
         ld.hu 2[r13], r6 ; add r8,r6          Ki = Ki(i) + (dk*S(i)>>8)
         jr    0x29DA0                return with r6 = Ki(v)
TBL:     5 rows (X u16, Ki u16, S s16 Q8) + sentinel = 36 bytes
```

**GATE 1 (RAM ownership): trivially satisfied — the cave writes NO RAM.** It is register-in (r7), register-out (r6),
scratch r8/r13. No new state word ⇒ no engage/disengage/bail init, and no new wire instrument is required (the
integrator state `gp-0x6dd0` already exists and is observable via the 427 tap / 0x14A). The free-register claim at the
hook (r8, r13 dead; r6 is the output; r7 preserved) is EVIDENCE from the `0x29D9C..0x29DC2` listing; **re-prove on the
built image (H-build).** A piecewise-constant 3-knot variant is ~56 bytes (32 code + 24 table) if fewer bytes are
needed, at the cost of small corner steps.

### 3.2 Calibration (A2) — deltas from A1

| cell | A1 | **A2** | why |
|---|---|---|---|
| Kp record Y | (411,561,330,536,883) | **(296,404,238,386,636)** | 0.72× envelope (the constant corner needs it for PM on the aged combined members) |
| Ki `0xC63E6` | 80 | **0** (unused; the cave supplies Ki) | the cave overrides the Ki load |
| A2 Ki cave table Y | — | **(148,202,119,193,318)** at key (2,7,10,15,24) | Ki(v) = 0.5·Kp(v), constant PI corner |
| Kd record Y, DB, ICL, DCL, a/b/C | as A1 | **unchanged** | — |

### 3.3 The loop in integer form (A2)

Identical to §2.3 except `Kp = LERP(...,(296,404,238,386,636),key)` and `Ki = cave_LERP((2,7,10,15,24),
(148,202,119,193,318), speed>>8)` with `I += ((E>>5)·Ki)>>3`.

### 3.4 GATE 2 on the FULL credible set (EVIDENCE: `panel_gate2.py A2`, `gate2_A2.json`)

| metric | A2 result | bar |
|---|---|---|
| tier A min PM | **54.5°** (J_hi @1.5, aged) | ≥ 45 ✓ |
| tier A min LTI GM | **13.7 dB** | ≥ 6 ✓ |
| tier A max |S| 5–30 | **+3.0 dB** | ≤ +3 ✓ (borderline) |
| tier B min PM | **32.3°** (b/1.9·J1.0·tau6+h10 @11.0, aged) | ≥ 30 ✓ |
| tier B min LTI GM | **7.6 dB**; exact GM 18 dB at the worst PM | ≥ 6 ✓ |
| tier B unstable | **0** | 0 ✓ |
| nominal min PM / GM | 64.7° / 15.5 dB | — |
| worst Re(T/ω) 13 / 20 Hz (aged) | −0.724 / −0.701 | M3 / ≤ V295 like-for-like |
| max M20 | 1.9 → 0.53× V295 | ≤ V295 ✓ |
| turn-hold ≥0.90 (≥8 m/s) | **0.990–1.004 every band** | ✓ (vs A1's 0.886) |

**A2 passes GATE 2 on the whole credible set.** The cave buys the turn-hold and the 0.2–0.5 Hz tracking (0.5 Hz
in-phase 0.96 @17 m/s vs A1's 0.72) at the cost of 0.72× peak P authority.

### 3.5 A2's pre-declared misses

- **M3 (13–17 Hz anti-damping)** — shared, §5.
- **M5 (no I-freeze on hand torque)** — shared; A2 schedules Ki, it does not freeze it.
- **M7 (the aged J≈1 world).** tier B min 32.3° sits on b/1.9·J1.0·tau6+h10 — a world with damping ÷1.9, inertia J≈1
  (physically disfavoured above 10 m/s, C1 §2.1), 6 ms delay and a 20-tick hold all at once. If the real plant is more
  adverse than that, PM falls below 30°. **Revert:** a growing 1.2–2.5 Hz oscillation on highway hard turns.
- **M8 (0.72× peak authority).** A2 delivers 30–64 T/deg vs A1's 41–88. BELIEF: still enough for lane-keeping (the
  I provides the steady torque); if highway hard-turns feel under-powered, raise the top Kp knot.

---

## 4. Time-domain gates (nominal and bc) — EVIDENCE `panel_time_min.py` (exact 1 kHz sim, Coulomb/stiction plant)

bc = b_lo damping with Coulomb ×2 (×1.3 at 8 m/s), the credible-set friction world. Columns per speed, **A1 | A2**.
Turn-hold = hold_ratio over the last 1.5 s of a 3 s hold; dj = dwell-then-jump events (s02 sinusoid); slips = stick-slip
events in the ramp-hold; stick% = frames the wheel is exactly stuck while the reference moves; dead-zone = steady turn
error (deg); hard16 = 1.6–3 Hz wheel-rate rms vs the reference's own; texture = 5–30 Hz T rms (counts, line > 2.0);
lurch = override-release peak T / wheel swing (deg).

| plant v | turn-hold | dj | slips | stick% | dead-zone ess° | tg0.2 | hard16 / ref | texture | lurch T / swing° |
|---|---|---|---|---|---|---|---|---|---|
| nom 3.0 | 1.01 \| 1.01 | 0 \| 0 | 1 \| 1 | 10.6 \| 11.0 | 0.55 \| 0.60 | 1.05 \| 1.11 | 0.98 \| 0.78 vs 1.80 | 0.53 \| 0.49 | 1694/47.6 \| 1380/48.8 |
| nom 12.5 | 0.98 \| 1.01 | 0 \| 0 | 0 \| 3 | 0.12 \| 0.08 | 0.70 \| 0.93 | 0.23 \| 0.17 vs 0.91 | 0.41 \| 0.31 | 681/12.0 \| 636/11.6 |
| **nom 19.0** | **0.79 \| 0.99** | 0 \| 0 | 0 \| 0 | 10.1 \| 8.1 | **0.76 \| 0.06** | 0.45 \| 0.76 | 0.07 \| 0.07 vs 0.38 | 0.86 \| 0.56 | 426/4.1 \| 644/5.5 |
| bc 3.0 | 0.99 \| 0.99 | 0 \| 0 | 0 \| 1 | 17.7 \| 17.6 | 1.01 \| 1.34 | 1.04 \| 1.11 | 1.37 \| 1.39 vs 1.80 | 0.80 \| 0.71 | 1720/47.5 \| 1338/45.2 |
| bc 12.5 | 0.97 \| 1.00 | 0 \| 0 | 0 \| 0 | 20.3 \| 17.7 | 0.18 \| 0.16 | 0.68 \| 0.90 | 0.40 \| 0.31 vs 0.91 | 0.42 \| 0.31 | 657/12.6 \| 612/12.4 |
| bc 19.0 | 0.78 \| 0.98 | 0 \| 0 | 0 \| 0 | 21.2 \| 15.2 | 0.82 \| 0.11 | 0.45 \| 0.76 | 0.12 \| 0.12 vs 0.38 | 0.87 \| 0.53 | 408/4.2 \| 607/5.9 |

**Reading (nominal, 3 & 12.5 m/s; EVIDENCE):**
- **Turn-hold** ≥ 0.98 for both at 3 and 12.5 m/s (the flat-Ki miss M1 is a *highway* effect; the freq model puts A1
  at 0.886 @17 m/s — the 19 m/s time row confirms the direction).
- **Dwell-then-jump = 0** for both at 3 and 12.5 m/s — the goal's "dwell-then-jump ≤ V282" criterion is met in the
  simulable band (V282 not simulable; decided on the car).
- **Hard-turn 1.6–3 Hz energy BELOW the reference** (A1 0.23–0.98, A2 0.17–0.78 vs ref 0.91–1.80) at both speeds, A2
  quieter — the goal's "hard-turn 1.6–3 Hz ≤ V282" is met on the nominal plant, better than the demand itself.
- **Texture** 0.3–0.5 counts ≪ the 2.0-count line — no lane-made 5–30 Hz texture.
- **Low-speed stick-slip IS present (M1-friction):** 1 slip + ~10% stick at 3 m/s (both), and **A2 trades 3 stick-slips
  at 12.5 m/s** for its better tracking (the stronger constant-corner integrator winds against Coulomb then slips) —
  A1 has 0 slips there but tg0.2 only 0.70. **This is the pre-declared friction miss (M9), shared, and it is the one
  goal criterion ("low-speed stick-slip gone") that NEITHER zero-/small-cave design meets** — removing it needs a
  friction feed-forward with its own instrument (C1's friction refuter; a larger cave, deferred).
- **Override release lurch** within the rail (peak T 426–1694 ≤ 2461) across speeds.

**The decisive highway row (19 m/s, EVIDENCE):** A1 turn-hold **0.79** with **0.76° steady lane error** — "loose on
highway curves," failing the 0.90 turn-hold gate (the 3 s hold gives the weak flat Ki even less time than the freq
0.886). A2 turn-hold **0.99**, error **0.06°** — the Ki-schedule cave integrates the curve out. dwell-then-jump = 0 and
hard-turn 1.6–3 Hz energy ≤ reference for both; texture ≤ 0.86 counts. **This single row is the whole A1→A2 case.**

**bc (friction world, Coulomb ×2):** stable throughout, dwell-then-jump = 0, hard-turn 1.6–3 Hz ≤ reference. The
**friction dead zone and stick grow** (stick 17–20% vs ~10% nominal; dead-zone 1.0–1.3° at 3 m/s) — the pre-declared
friction miss is worse in the heavy-friction world but bounded. A1 still under-tracks at bc 12.5 (tg0.2 0.68) where A2
holds 0.90. Light-hand override and engage-droop are bounded by ICL 4096 (M5); the 0x7FFF sentinel pulse is killed by
A2g (§6, hazard 1).

---

## 5. M3 — the 13–17 Hz anti-damping (shared, EVIDENCE `panel_numbers.py` Re(T/ω) sweep)

The D-on-rate term (edit E5), behind the 5.05 Hz output lag + 2 ms transport + the 100 Hz hold, rotates past 90° in the
teens of Hz and **anti-damps**. Controller-only Re(T/ω) (T counts per deg/s; <0 removes damping from a collocated mode):

| f (Hz) | A1 (3/8/12.5/19/26 m/s) | A2 | V295 | V294 |
|---|---|---|---|---|
| 5 | +0.38 / −0.03 / +0.21 / −0.37 / −1.00 | +0.58/+0.00/+0.40/−0.08/−0.61 | +2.63 | +1.42 |
| 13 | −0.44 / −0.48 / −0.37 / −0.44 / −0.50 | −0.39/−0.41/−0.33/−0.37/−0.40 | **−0.15** | −0.08 |
| 20 | −0.52 / −0.50 / −0.43 / −0.41 / −0.37 | −0.51/−0.48/−0.41/−0.39/−0.34 | **−0.63** | −0.34 |
| 25 | −0.50 / −0.46 / −0.40 / −0.37 / −0.31 | −0.49/−0.45/−0.39/−0.36/−0.29 | −0.69 | −0.37 |

**Reading.** At **20–25 Hz both A1 and A2 anti-damp LESS than V295** (which flew without grinding) — good. At **13–15 Hz
they anti-damp ~3× MORE than V295** (−0.44 vs −0.15). V282, which GROUND, is −6.4 at 20 Hz — A1/A2 are ~10× below that.
The 13–17 Hz excess is the declared miss, because the record carries a 13–17 Hz line.

- **Mitigation already in the design:** Kd is scheduled DOWN at highway (10 at 27 m/s vs 20 at 3 m/s), where the
  13–17 Hz line lives, so the highway 13 Hz anti-damping is held near V295's floor. Lowering Kd further trades away the
  1.6–3 Hz wheel-mode damping (hard-turn jerk).
- **Pre-registered revert signature (stop band 11–18 Hz):** if a **11–18 Hz line appears or grows** on the 0x18F rate
  or the 427 tap (presence > 0.5 %, or +3 dB over V294 on curves), revert. This is the ring frequency the excess
  anti-damping would produce. BELIEF: it will not fire (the 20 Hz gain is 0.53× V295 and V295 did not grind), but the
  instrument must watch 11–18 Hz, not just 18–22.

---

## 6. Hazards

1. **The 0x7FFF fault sentinel.** On an 0xE4 RX fault `gp-0x69ae = 0x7FFF` → sp loads as **32767** → P rails. Edit
   **A2g** (`0x29A56`) makes the PID run only while ramp≠0 ∧ request==1; on a fault request→0xFF, so the lane SKIPs
   and the output-lag decays in ~0.1 s instead of railing for 2 s. EVIDENCE tracer + harness. This is why A2g is in the
   A1 edit set, not optional.
2. **The ±12000 bail on θ.** E1 moves the bail from rate to angle; |θ|>1200° latches STEER_STATUS 7 until key cycle.
   The mode-3 wrap on the −0x8000 baseline sentinel is the trigger (FACTS). The fork must keep mode-3 valid (spec).
3. **A2's cave register claim.** r8/r13 dead and r7 preserved at `0x29D9C` is EVIDENCE from the listing; re-prove on
   the built image. The cave touches NO RAM, so there is no init hazard.
4. **13–17 Hz anti-damping (M3).** The one dynamics hazard; stop band 11–18 Hz pre-registered.
5. **Re-key telemetry shift.** `gp-0x674b` now carries speed, not demand. Any downstream/tap consumer must be
   re-pointed; C0's census found 0 control readers (EVIDENCE), but the live tap's demand byte changes meaning.
6. **V1 flasher trap (EVIDENCE tracer §4):** the F181 string changes to "…,A16A"; the revert `.rwd`s must be
   re-headered to list the new string before flashing, or the part-number gate refuses the revert.

---

## 7. Flight prerequisites (fork side / interface) — not firmware bytes

C8 (engage only in mode 3), Δmax(v) rate limit on θ_sp, τ_o ≥ 1 s outer corner / no fork integral below 8 m/s, O1
(release handling), the camera's LKAS off / send `gp-0x6803`≠? per SPEC-angle-setpoint-interface. The **B2** interlock
(+4 bytes) adds the firmware half of the mode-3 dominance. All per the tracer and the interface spec.

---

## 8. The instrument that proves it live in one drive

**No new state word is added (A1 has no cave; A2's cave writes no RAM), so no new telemetry bit is required** — the
loop is read from quantities already on the wire:
- **θ (gp-0x6a00 / 0x14A), driver torque (gp-0x4f68), LKAS demand / θ_sp (0xE4), and the delivered torque (the 427
  tap)** — the operator's own three signals plus the tap.
- **Live discriminator, A1 vs A2, from one drive:** on a steady highway curve, regress delivered torque on (θ_sp−θ)
  and on the integral of (θ_sp−θ). A1's I-share stays small (flat Ki 80 → fI 0.09·Kp at highway) and the steady angle
  error does **not** integrate out (turn-hold < 0.90); A2's I-share rises to carry the curve and the error integrates
  out (turn-hold ≈ 1.0). That single contrast is the whole A1-vs-A2 decision, readable in ~15–30 s of engaged highway.
- **The re-key is self-evident on the wire:** `gp-0x674b` now tracks speed, not demand — a zero-cost confirmation the
  re-key is live.
- **M3 watch:** the 0x18F rate / 427 tap in the **11–18 Hz** band (the stop band), not just 18–22.

---

## 9. Reproduce

```
cd analysis-2020accord/studies/angle_loop/panel/A-fewest-bytes
python panel_schedules.py            # the schedules and cals
python panel_fast.py                 # vectorised FRF == stab_lin.margins (0.00 deg)
python panel_gate2.py A1             # GATE 2, full credible set, A1   (~36 s)
python panel_gate2.py A2             # GATE 2, full credible set, A2   (~37 s)
python panel_numbers.py              # tracking, Re(T/w), per-tier |S|
python panel_time.py both            # time gates, nominal + bc
```
