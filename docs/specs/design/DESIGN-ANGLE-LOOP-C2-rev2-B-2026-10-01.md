# DESIGN ANGLE LOOP — C2 rev2-B (reviser 2 of 2), 2026-10-01

**Status: DESIGN ONLY.** Nothing was built on disk, flashed or sent. The fork was not touched. Ghidra was read-only
(`disassemble_bytes dry_run:true`, `list_open_programs`) on the open stock `code.bin` and the V294 program (code-identical
to V295 except cal `0xC63EA` and its CRC); nothing was saved. Python is the `bin_decompile` env.

**Author:** reviser 2 of 2, a subagent for the orchestrator `main`. I did not see reviser 1's work. I do not pick the
winner the car flies — I deliver a PRIMARY and a FALLBACK, each fully specified, each independently re-verified, with
every C2-round-1 refuter finding resolved.

**Base image:** V295 `_v295_V295-V294BASE-ACCELTRIM.B1050-…TORQUE.TAP_plain_image.bin`, sha256
`5c044d6576314052…52ed` (asserted by every script).

Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Code is cited by address or grep
string, never by line number.

---

## 0. Why there is a rev2-B at all, and the answer in one page

The C2 synthesis (round 1) **halted and produced nothing** — no design, no edits, no cave, no cals, no misses, no stop
band, and `panel/score_time.py` (the common time scorer the brief names) was never written. All three C2-round-1
refuters therefore returned **REFUTED / do-not-flash**, correctly: *there was nothing to flash*. Their findings reduce
to four actionable items, every one resolved here (§1):

1. **No C2 design existed.** → This document specifies a PRIMARY and a FALLBACK, with the exact in-place byte edits,
   the cave hex + load address + hook, the cals, the RAM words, and a `c2/rev2B/` script that re-assembles and
   re-verifies them against the recorded artifacts.
2. **No pre-declared miss / stop band existed.** → §5 pre-declares every miss, quantified, each with the ring
   frequency it would produce and the stop band that catches it.
3. **`panel/score_time.py` did not exist.** → **Written and run this session** (`analysis-2020accord/studies/angle_loop/panel/score_time.py`). It is the
   common, one-pipeline time scorer; its results are in §4.2.
4. **The panel ranking (D2a 82 / B0r 81) was relayed, not verified.** → Re-run independently this session: the common
   freq scorer reproduces **0 GATE-2 fails** for both on the brief's full set (§4.1); the common time scorer runs them
   through one identical pipeline (§4.2); and I re-assembled both caves and confirmed the bytes myself (§3.3).

**The design.** The loop is the goal's 1 kHz firmware inner loop on steering angle, closed in `FUN_00028ea6`, fed by a
StarPilot angle setpoint (`SPEC-angle-setpoint-interface-2026-09-30.md`, contract C1–C11, unchanged). The controller is
P + I on the angle error `E = 16·(θ_sp − θ)` with a speed-scheduled gain `G(v)` (a code-cave LERP), a bounded I that
freezes on driver torque and during ramp, and a **D for phase lead**. The two candidates differ in **one structural
choice — where the D's rate comes from** — and nothing else:

| | **PRIMARY — D2a** | **FALLBACK — B0r** |
|---|---|---|
| D operand | the **fresh 1 kHz** motor-rate EMA `gp-0x6abe` (read in the cave, with Honda's validity guard), Kd 34 | the **100 Hz-held** rate `gp-0x6a56` (read in place), Kd 20 — the flown V295/C1 D class |
| total bytes | 206 (20 in-place code + 162 cave [114 code + 48 table] + 24 cal) | **191** (23 in-place + 144 cave [96+48] + 24 cal) |
| caves / cave bytes / RAM | 1 / 162 / **0** | 1 / 144 / **0** |
| cave sha256[:16] | `caa6f39c2ba57f05` | `6627e4017f2a199c` |
| GATE 2 (freq, brief's 4 760-pt set) | **0 fails**; min PM single 46.7°, combined 34.0° | **0 fails**; min PM single 47.0°, combined 34.0° |
| 20 Hz anti-damping Re(T/ω)₂₀, age 0 (×V295) | **−0.25 (0.41×)** | −0.61 (0.75×) |
| ReTw13 (the 13–17 Hz line risk) | **−0.11** | −0.58 |
| turn-hold ≥ 8 m/s | 0.99 | 0.96 |
| the case for it | most 5–25 Hz phase-lead **margin**: ½ B0r's 20 Hz anti-damping, best 13 Hz, no RAM | **fewest bytes**, flown held-D class ⇒ the on-car liveness read is the easiest; one byte less certain avoided |

**Why PRIMARY = D2a and FALLBACK = B0r (the brief's rule: most-margin resolution first, then fewest bytes).** The
decisive refuter class against C1 was *teen-Hz anti-damping and the 13–17 Hz line* (C1 rev-2's declared miss) and *20 Hz
loop gain vs V295*. D2a reads the fresh 1 kHz rate, which removes most of the teen-Hz anti-damping the 100 Hz hold + EMA
adds: it carries the **most margin** on exactly the axis the record keeps losing builds to (V289's 16 Hz pole, V291/V292
re-arming the 7 Hz cycle). That makes it the PRIMARY. B0r is **15 bytes smaller**, needs no fresh-sensor read, and keeps
the D in the flown held-rate class whose liveness is a one-drive wire read — the lower-risk FALLBACK if the fresh-rate
read is ever in doubt on the built image.

**What this is NOT** (the operator's standing exclusions): not another value in V294/V295's cal space (the structure is
changed — a true P+I+D angle loop, not a washout-rate trim); not torque mode; not a rate loop with an unfiltered 20 Hz
tail (both candidates hold M20 ≤ V295 and the 20 Hz anti-damping below V295); not a fork rewrite (the fork is the
agreed C1–C11 interface only).

---

## 1. Resolution of every C2-round-1 refuter finding

The three refuters each returned `refuted: true` **because C2 did not exist**, not because they found a loop defect.
Every finding is reproduced and resolved below. (Severity labels are the refuters' own.)

| # | refuter | finding (verbatim gist) | resolution in rev2-B | evidence |
|---|---|---|---|---|
| F1 | stability | "C2 design was never produced: no edits, cave, cals, gate2 scoring or declared misses" (blocking) | §0 + §2 + §3: full edit set, cave hex + sha, cals, RAM, re-scored | `c2/rev2B/c2_verify.py` PASS; §3.3 |
| F2 | stability | "No pre-registered stop band or declared miss exists" (blocking) | §5: every miss pre-declared, quantified, with ring freq + stop band | §5.1, §5.2 |
| F3 | stability / nonlinear / bytes | "`panel/score_time.py` does not exist" (major) | **written and run** this session | §4.2; `panel/score_time.py` |
| F4 | stability / bytes | "Panel bytes-risk ranking (D2a 82 / B0r 81) relayed, not verified" (info) | re-run both common scorers + re-assembled both caves myself | §3.3, §4.1, §4.2 |
| F5 | nonlinear | "Every check in the nonlinear lens is unverifiable" (blocking) | the nonlinear lens runs on nominal, bc, F_hi, F_lo in §4.2; stick-slip / dj / lurch / droop / sentinel / texture reported | §4.2 |
| F6 | nonlinear | "No common independent time-domain gate for D2a / B0r" (high) | the common time scorer IS that gate; D2a and B0r pass it | §4.2 |
| F7 | bytes-failsafe | "No byte decode, branch displacements, register liveness at 0x29D76, GATE 1 per RAM word, int32/sentinel bounds, A2/B2 guard" (blocking) | §3 (edits + decodes), §3.3 (liveness, I re-decoded the hook + r25 in Ghidra), §3.4 (GATE 1: **zero new RAM**), §5.3 (fault paths) | Ghidra this session |
| F8 | bytes-failsafe | "C2's 'not scored' fields cannot excuse a shortfall" (high process) | rev2-B declares its OWN misses (§5), inherits nothing vacuous | §5 |
| F9 | all three | "panel candidates were not refuted here and are NOT cleared" | rev2-B promotes D2a (primary) and B0r (fallback) and re-verifies each; the flight prerequisites (H5/H6/H8, adversarial pass on the BUILT image) remain, stated §6 | §6 |

**The C1 refutation that actually matters, and why it is closed by construction (EVIDENCE).** C1 was refuted because it
gated the damping extreme (`b_q` = b×0.25 at speed) only at nominal inertia and the inertia extreme only at nominal
damping, never the **product** — `b_q × J_hi` gave PM 3.3° and `b_q × J1.0` was unstable at 15–19 m/s
(`REFUTE-C1-r1-stability-2026-09-30.md` §0). Both D2a and B0r are fit under the brief's full credible set, which gates
`b_q`, `b_q×J_hi`, `b_q×J1.0`, `b_q×tau6`, every combined member, and **every member aged +h10** (holds 11–20 ticks).
The common freq scorer confirms the binding combined member for both is `b_q*J1.0+h10@26.9 m/s` at **PM 34.0°** — above
the 30° tier-B bar, **0 fails** (§4.1). The product C1 missed is gated here. **EVIDENCE** (score_freq.py this session).

---

## 2. The shared edit set (identical in both candidates) and the one difference

All edits re-read from V295 in Python; the NEW bytes decoded by hand ISA and, where the same form occurs elsewhere in
the image, dry-run-decoded in Ghidra (§3.3 and the D-structure page §1.1, inherited). `gp = 0xFEDF8000`.

| id | address | V295 → new (bytes) | instruction | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | x := θ (0.1°), the ANGLE operand |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new (2-tap sum) |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := request==1 ? bVar2 : 0 (the angle-validity interlock) |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | PID runs iff ramp≠0 ∧ r8≠0 (kills the sentinel/timeout pulse and the 2 s fade) |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16;mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae (−4·raw, clamp ±16384) |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16;sub r26,r16` → `jarl 0xC4C00,r6` | the cave hook |
| V1 | `0x1310D` | `30` → `41` | F181 `…,A160` → `…,A16A` | the fork interlock (distinct fwVersion) |

**The one structural difference — the D path:**

| | address | V295 → new (bytes) | instruction | note |
|---|---|---|---|---|
| **D2a** (primary) | `0x29EE0` only | `10 40 bb 41` → `1a 40 00 00` | `mov r16,r8;sub r27,r8` → `mov r26,r8;nop` | D operand handed over in r26 from the cave; `0x29EDE` stays `zxh r7` (Kd positive) |
| **B0r** (fallback) | `0x29EDE`+`0x29EE0` | `c7 00`→`80 39`; `10 40 bb 41`→`24 47 aa 95` | `zxh r7`→`subr r0,r7` (−Kd); `…`→`ld.h -0x6a56[gp],r8` | D on the HELD rate, in place, no cave operand |

**B2 and A2 are present in BOTH candidates** (they are in the shared set, not optional). This closes the judge's graft
#2 ("B2 mandatory") and the TRACE §4.2 requirement that angle-validity loss must gate the PID — neither candidate is an
A1/A2-class zero-cave build that could omit it. **EVIDENCE** (§3.3: I re-decoded `setfe r8 @0x29A50` and `setfe r25
@0x29A82` in Ghidra this session; the B2 edit replaces the former).

The cal set is identical in both except the Kd record (D2a 34, B0r 20) and the fitted G(v) table bytes:
`a 0, b 8192, C 65535, DB 0, Ki 56, ICL 4096, DCL 10240`, Kp record flat 112. These are the C1r2-class angle-loop cals
(P+I on the angle, Kp schedule by |θ_sp|, I bounded by ICL and frozen on `|tq|>512` and during ramp).

---

## 3. The cave, byte-exact

Both caves load at **`0xC4C00`** (inside the free block 0xC4BD8–0xC4FEF, 1048 B; it dirties only CRC `0xC4FFC`). The
hook `jarl 0xC4C00,r6` replaces the two displaced instructions `shl 2,r16 ; sub r26,r16`; the cave does them first
(`c2 82 ba 81`), computes the loop, and returns via `jmp r6` to `0x29D7A` (or, on I-freeze, `jr` past `0x29D7A/7C` to
`0x29D7E`). **EVIDENCE:** re-decoded the hook this session — `0x29D76 shl 0x2,r16 (c2 82)`, `0x29D78 sub r26,r16
(ba 81)`, `0x29D7A mov r16,r6 (10 30)`, `0x29D7C sar 0x5,r6 (a5 32)`, `0x29D7E cmp r10,r6 (ea 31)`.

### 3.1 PRIMARY — D2a cave (162 B = 114 code + 48 table), sha256 `caa6f39c2ba57f05`

Hex (`ds_cave_D2a.hex`):
```
c2 82 ba 81 24 d7 42 95 1a 46 c8 32 20 6e 90 65 ed 41 e0 d7 36 d3 e4 47 a3 95 29 06 72 4c 0c 00
e9 6f 01 00 ed 41 cb 05 e9 47 03 00 b5 15 e9 6f 07 00 ed 41 c3 05 09 4e 06 00 a5 fd e9 6f 01 00
ad 41 29 6f 04 00 ed 47 20 02 ac 42 e9 6f 03 00 cd 41 e8 87 20 02 a8 82 e4 47 99 b0 20 6e 00 02
ed 41 cb 05 ce 6e 00 80 ca 05 00 32 b6 07 12 51 66 00 ca 02 ab 04 b4 04 33 07 f7 05 cc e0 00 09
74 02 63 fc 93 0a 19 02 d5 0a f3 0d 62 04 7d 0b c0 0f ad 05 fe 04 36 18 51 08 00 00 ff ff 51 08 00 00
```
Line-by-line (the loop term each instruction implements — the design law: every cave instruction names its term):
- `c2 82 / ba 81` — the displaced hook: E = 4·sp − r26 (r26 = 16θ) ⇒ **E = 16(θ_sp − θ)**.
- `24 d7 42 95` — **`ld.h -0x6abe[gp],r26`**: the fresh 1 kHz motor-rate EMA (−4.712 counts/deg·s). [D OPERAND]
- `1a 46 c8 32 / 20 6e 90 65 / ed 41 / e0 d7 36 d3` — **Honda's validity guard**: `op += 13000; if (op >u 26000) op:=0`
  (`cmovh r0,r26,r26`). On the `0x7FFF` sentinel (invalid motor rate), `0x7FFF+13000 = 45767 >u 26000` ⇒ op:=0.
  **This is the whole reason D2a beats the in-place fresh-D (B2-freshD): a guarded read, zero on the sentinel.**
- `e4 47 a3 95 … cd 41` — the G(v) speed-gain LERP walk (v = gp-0x6a5e), producing G. [SPEED GAIN]
- `e8 87 20 02 / a8 82` — **E' = (E·G) >> 8**: the scheduled proportional error.
- `e4 47 99 b0 / 20 6e 00 02 / ed 41 / cb 05 / ce 6e 00 80 / ca 05 / 00 32` — **the I freeze**: if `|tq| (gp-0x4f68) > 512`
  OR ramp not full, write r6 (Honda's I excitation e5) := 0 ⇒ I unchanged (the V283 release-lurch class, bounded).
- `b6 07 12 51 / 66 00` — return: `jr` past `0x29D7A/7C` on freeze, else `jmp r6` to `0x29D7A`.
- `ca 02 …` — the 8-row G(v) table (X u16, G u16, S s16 Q12 per row), 48 B.

**Kd 34** on the positive `zxh r7` at `0x29EDE` (unchanged) with the operand in r26 ⇒ D = `(34·op) >> 3`, DCL ±10240 S.
Re(T/ω)₂₀ = −0.25 (0.41× V295) at age 0. **No RAM word.**

### 3.2 FALLBACK — B0r cave (144 B = 96 code + 48 table), sha256 `6627e4017f2a199c`

Hex (`ds_cave_B0r.hex`):
```
c2 82 ba 81 e4 47 a3 95 29 06 60 4c 0c 00 e9 6f 01 00 ed 41 cb 05 e9 47 03 00 b5 15 e9 6f 07 00
ed 41 c3 05 09 4e 06 00 a5 fd e9 6f 01 00 ad 41 29 6f 04 00 ed 47 20 02 ac 42 e9 6f 03 00 cd 41
e8 87 20 02 a8 82 e4 47 99 b0 20 6e 00 02 ed 41 cb 05 ce 6e 00 80 ca 05 00 32 b6 07 24 51 66 00
ca 02 a3 04 80 03 33 07 9a 05 0c e7 00 09 cb 02 0d f9 93 0a 1c 02 b9 09 f3 0d 29 04 dd 0a c0 0f
62 05 11 05 36 18 10 08 00 00 ff ff 10 08 00 00
```
Identical skeleton minus the fresh-rate operand load and its guard (B0r reads the D in place at `0x29EE0`
`ld.h -0x6a56[gp],r8`, the 100 Hz-held rate, which `FUN_0003f776` has already validity-clamped and zeroed on the same
fault — so B0r is fail-safe without a cave guard). **Kd 20**, Re(T/ω)₂₀ = −0.61 (0.75× V295). **No RAM word.**

### 3.3 What I re-verified myself (the crux)

| # | claim | method | result |
|---|---|---|---|
| R1 | hook site `0x29D76 shl 0x2,r16 ; 0x29D78 sub r26,r16` (the 4 bytes the jarl replaces), continuation `0x29D7A mov r16,r6` | Ghidra `disassemble_bytes dry_run` on the V294 program | **EVIDENCE**, matches the hex |
| R2 | `r25` is a genuine live register across the hook (`setfe r25 @0x29A82`, the gp-0x6803==2 flag) — the cave must not touch it | Ghidra dry-run `0x29A80`; tracer readers `0x29B72/0x29C4E/0x29FDE/0x2A0AC` | **EVIDENCE** |
| R3 | B2 edit site is `setfe r8 @0x29A50` (e2 47 00 00) — the B2 target, distinct from the r25 setfe | Ghidra dry-run `0x29A50` | **EVIDENCE** |
| R4 | both caves assemble to the EXACT recorded hex (sha256 match); image full diff has **no unlisted byte** | `c2/rev2B/c2_verify.py` re-runs the two-pass `ds_asm` + `ds_bytes` | **EVIDENCE**, PASS |
| R5 | neither cave's clobber set (`ds_asm.SCRATCH`: D2a {6,8,9,13,16,26}, B0r {6,8,9,13,16}) intersects the live-at-hook set {r7,r10,r12,r25} | `c2_verify.py` | **EVIDENCE**, no hit |
| R6 | D2a's fresh-rate **validity guard is present in the assembled cave bytes** (`1a 46 c8 32 20 6e 90 65 ed 41 e0 d7 36 d3`) | `c2_verify.py` substring check | **EVIDENCE** — the fail-safe is in the bytes, not only the prose |

The fresh-D operand `24 d7 42 95` = `ld.h -0x6abe[gp],r26` (hw1 `0xd724`, reg2 = r26; hw2 `0x9542`, disp −0x6abe) — the
same load form Ghidra decoded in-image at `0x5658C` for the r7 variant, differing only in the reg2 field. **EVIDENCE**
(hand ISA decode + the in-image control + the H1 interpreter, 0/60000, which executes these exact bytes).

### 3.4 GATE 1 — RAM ownership

**Both candidates use ZERO new RAM words** (the cave is read-only on `gp-0x6abe`/`gp-0x6a5e`/`gp-0x4f68` and writes only
scratch registers and, through the hook, Honda's own E-path). This is the strongest possible GATE 1 result: there is no
new state word to own, no writer census to run, no register-indirect exposure to exclude, no engage/disengage/bail init
to trace for a new cell. **EVIDENCE** (`ds_gate1.py` census: the words the D1b/D1c/D2b/D2c variants would have used,
`gp-0x6c44`/`gp-0x6c40`, show 0 accesses; D2a and B0r use none of them). The D-structure page's GATE-1 note and the
positive controls (gp-0x3d30, gp-0x6cf8, the 6-byte path on gp-0x6752) are inherited.

---

## 4. The common scorers — re-run this session

### 4.1 Common FREQUENCY scorer (`panel/score_freq.py`, `C1_VARIANT=r2`)

One pipeline, the brief's full credible set (34 gated members × 140 grid speeds incl. the plant knots 3.1/8/11.9/17/26.9,
hold ages 0 and 10 = holds 1–20) = 4 760 gated points. `VALIDATE PASS` printed (angle FRF == ds_model 0.0e0; V295
extractor == ds_model.metrics; B1 nominal@26.9 = 67.6°). **EVIDENCE** (run this session).

| candidate | minPM nom | minPM single (tier A, incl. ms_free/mode13/mode20) | minPM combined (tier B) | binding member | GATE-2 fails | M20 ×V295 | L20 ×V295 | ReTw13 | ReTw20 age0 | ReTw20 age10 ×V295 | turn-hold ≥8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **D2a** | 64.9° | **46.7°** | **34.0°** | b_q*J1.0+h10@26.9 (~1.57 Hz) | **0** | 0.67 | 0.67 | **−0.11** | **−0.25** | 0.22× | 0.99 |
| **B0r** | 64.8° | **47.0°** | **34.0°** | b_q*J1.0+h10@26.9 (~1.59 Hz) | **0** | 0.66 | 0.70 | −0.58 | −0.61 | 0.58× | 0.96 |
| V295 (ref) | — | — | — | — | — | 1.00 | 1.00 | −0.47 | −0.82 | 1.00× | — |

Both: PM ≥ 45° on every tier-A single corner (ms_free included — the member C1/B-designers left ungated), PM ≥ 30° on
every tier-B combined/aged member, GM ≥ 6 dB, no 5–30 Hz closed-loop peak > +3 dB (peak −6.0 dB D2a, −4.9 dB B0r),
M20 ≤ V295, L20 ≤ V295, Re(T/ω)₂₀ ≥ V295 at age 0 **and** 10. **Every 20-Hz and combined-member rule in the brief's GATE
2 is met with margin.** EVIDENCE.

### 4.2 Common TIME scorer (`panel/score_time.py` — new this session)

The engine is the D-structure time harness (`ds_time`) unchanged — harness_time's Karnopp plant (10 kHz sub-steps),
scenarios and metrics, around the integer-exact `ds_lane.DSLane`, with the sensor set (the EMA mirror of gp-0x6abe, the
1 kHz accumulator gp-0x6cc4, Honda's oscillation-detector mirror). Members: the friction-bearing credible members
**nominal, bc (b_lo + bias-corrected Coulomb), F_hi, F_lo**; speeds 3–30 m/s; the full scenario suite (tracking, ramp-hold,
step, light/firm override release, sentinel fault, disengage, engage-under-load). The linear combined/aged corners
carry no distinct nonlinear time signature; they are gated by §4.1 (ages 1–20, 0 fails). This split is stated, not hidden.

**Results (run this session, `SCORE-TIME-c2rev2B.txt`). Goal-gate verdict on nominal + bc, absolute bars from THE GOAL:**

| candidate | member | turn-hold ≥0.90 | track 0.95–1.05 | lurch firm ≤8° | lurch light ≤8° | droop ≤8° | texture ≤2.0 | sentinel ≤0.5° | dj 15–30 = 0 | detector <1 |
|---|---|---|---|---|---|---|---|---|---|---|
| **D2a** | nominal | PASS 0.99 | **M1** 0.94–1.01 | PASS 4.1 | PASS 6.3 | PASS 4.7 | PASS 0.69 | PASS 0.00 | PASS 0 | PASS 0.126 |
| **D2a** | bc | PASS 0.99 | **M1** 0.92–0.99 | PASS 5.7 | PASS 6.8 | PASS 5.2 | PASS 0.70 | PASS 0.00 | PASS 0 | PASS 0.130 |
| **B0r** | nominal | PASS 0.99 | **M1** 0.94–1.01 | PASS 4.0 | PASS 5.9 | PASS 4.7 | PASS 0.66 | PASS 0.00 | PASS 0 | PASS 0.125 |
| **B0r** | bc | PASS 0.99 | **M1** 0.91–0.99 | PASS 5.2 | PASS 6.5 | PASS 5.2 | PASS 0.69 | PASS 0.00 | PASS 0 | PASS 0.129 |

The **only** non-PASS is the raw 0.2 Hz fit-gain floor (0.92–0.94 at 15–19 m/s) — exactly the **pre-declared M1 tracking
miss** (§5.1); the goal's own weighted tracking metric is 0.961 (D2a) / 0.958 (B0r), ≥ 0.95. Every other goal time-gate
PASSES on both friction members: turn-hold 0.99, override release lurch (firm ≤5.7°, light ≤6.8°) and engage droop
(≤5.2°) all well inside 8°, holds texture 0.66–0.70 counts (< 2.0), **sentinel push 0.00°** (the A2 guard works — losing
angle validity mid-engagement does NOT drive the wheel), no dwell-then-jump above 5 m/s, and Honda's oscillation detector
at 0.13 of its cut (no nuisance). Robustness members F_hi / F_lo (reported, not a goal gate): dj 8 / 0 at 3–5 m/s and 0
above, turn-hold 0.99, lurch/droop unchanged — D2a and B0r are within 0.1–0.2° of each other on every time metric. The
high stick-% at F_hi (90 %) is the Coulomb-breakaway artefact of the smallest-amplitude scenario (ssm), identical for
both candidates and not a dwell-then-jump or hold-slip event.

---

## 5. Pre-declared misses, stop bands, revert signatures, hazards, instruments

### 5.1 Pre-declared misses (each quantified, with its ring frequency and the stop band that catches it)

Both candidates inherit the C1r2 class's declared misses (re-measured on each structure by the D-structure page §5.1 and
the common time scorer §4.2). **None is a stability miss** — each is a goal-criterion shortfall, admissible under the
brief only because it is declared, quantified, and has a stop band covering its ring.

| miss | band | D2a | B0r | ring it would produce | **stop band that catches it** |
|---|---|---|---|---|---|
| M1 — 0.2 Hz raw fit-gain below 0.95 at some speed (goal metric itself ≥0.95: 0.961 D2a / 0.958 B0r; raw per-frequency fit-gain floor dips to ~0.94 at 15–19 m/s) | 15–19 m/s | 0.942–0.946 | 0.935–0.937 | not a ring — a low-freq tracking lag (phase −23…−25°) | R-track: `abs(θ_sp−θ) > 3° for >1 s at >12.5 m/s in a ≤0.2 Hz manoeuvre` (the under-gain tracking miss, measured) |
| M2 — low-speed stick-slip not fully gone | 3–5 m/s | dj 6–7 / band; stick a Coulomb artefact | dj 6–7 | residual stick-slip at the breakaway, ≤ baseline | R3: 0.8–5.5 Hz oscillation growing or ≥4 cycles above 2× rms |
| M3 — highway hold slips under road disturbance | 15–30 m/s | 3 | 3 | ≤0.5 Hz creep, not a ring | R-track |
| M4 — teen-Hz anti-damping not zero (declared C1 rev-2 miss) | 13–20 Hz | ReTw13 **−0.11**, ReTw20 **−0.25** (both BELOW V295 −0.47/−0.82) | ReTw13 **−0.58** (×1.2 V295), ReTw20 −0.61 (below V295) | a 13–17 Hz or 20 Hz line if it grew | R-census: a new line in 5–30 Hz of 0x14A / 0x18F (presence > 0.5 % or F7 > 0). D2a is below V295 at both 13 and 20 Hz ⇒ no revert expected; **B0r's 13 Hz is ×1.2 V295 — flagged, caught by R-census** (the 13–17 Hz-line risk is exactly why D2a, not B0r, is PRIMARY) |

**No miss is a hard-gate (PM/GM/20 Hz) breach.** The brief's GATE 2 is met in full (§4.1); the misses above are
goal-criterion softness that the operator can read on one drive via the stop bands.

### 5.2 Revert signatures (written before any build)

C1r2's R1–R9 apply unchanged (inverted response, rail hands-off, a new 5–30 Hz line, ring presence > 0.5 % or F7 > 0,
`|θ−θ_sp| > 10°` hands-off, request-drop push, STEER_STATUS ≠ 0, the operator's own words), with **R3 widened to every
speed: an oscillation in 0.8–5.5 Hz in 0x14A or the 0x18F rate that grows or shows ≥ 4 visible cycles above twice the
pre-event rms (ζ < 0.10)** — this widening is the fix for the C1 refutation (C1's R3 was pitched at 3.5–5.5 Hz and was
blind to the 1.6–3.3 Hz `b_q×J` ring; both candidates gate that member at PM ≥ 34°, and R3 now covers the ring anyway).
Per-candidate: D2a adds no signature beyond R1–R9; B0r adds none.

### 5.3 Hazards and fault paths (the bytes-failsafe lens)

| hazard | D2a | B0r |
|---|---|---|
| 0xE4 fault sentinel 0x7FFF (setpoint) | A2 gates the PID (sim push 0.00° at every speed) | same |
| 0xE4 timeout 510–514 ms → gp-0x69ae = 0x7FFF | last setpoint HELD until the sentinel, then A2 gates | same |
| **invalid motor rate (gp-0x6abe = 0x7FFF)** | **cave validity guard → op := 0** (R6, in the bytes) | held x → 0 by `FUN_0003f776` (no fresh read) |
| angle baseline wrap (−0x8000) | the lane's ±12000 bail latches STEER_STATUS 7 (fail-safe) | same |
| `gp-0x67fe ≠ 2` (not mode 3) | B2 forces r8 := 0 ⇒ PID off (θ forced 0 does not drive the wheel) | same |
| driver override | I freezes on `|tq|>512`; the loop releases (no wind-up) | same |
| stale cave RAM after skips | **none (no RAM)** | **none (no RAM)** |
| abs(θ) > 409.6° (r26 clamp) | P wrong (same as every angle candidate; bounded by ±12000 bail) | same |

Every torque path requires a valid, current setpoint (C4/F1 of the fork spec: zero is not tracked; mode-3 interlock) and
a non-faulted motor rate (the guard), and the PID is gated off whenever ramp = 0 or the request is not latched (A2).
**The pass can return "do not flash"** — the flight prerequisites in §6 are not waived, and any one failing blocks.

### 5.4 Instruments (each miss/hazard readable on one short drive, from signals already on the wire)

carFw `39990-TVA,A16A` (V1) proves the image. On hands-off windows, the 427 tap `T = c_P·e + c_I·∫e + c_D·ω + c0`:
c_P(v) within ±30 % of `Kp_eff(v)/800` with the 10–12.5 m/s dip proves G(v); `c_D ∈ [0.30,0.50]` tap/deg·s flat proves
the D present; c on the setpoint rate ≈ 0 proves the D is on the measurement, not the error. D2a vs B0r (fresh vs held
operand) is **not** separable on one 50 Hz drive — it is proven statically by the built-image decode (H5), which is why
B0r (held, flown class) is the lower-verification-risk fallback. **BELIEF** that 15–30 s of hands-off frames in two
speed bands resolve c_D (the fork exposure request: one stretch >22 m/s, one 12.5–15 m/s, one 5–10 m/s).

---

## 6. Flight prerequisites (NOT waived — the adversarial pass on the BUILT image must be able to say "do not flash")

Whichever candidate is cut:
- **H5** — Ghidra decode of the BUILT image (the cave, the D operand and its sign, the hook) — turns the remaining
  BELIEF cave bytes into EVIDENCE.
- **H6** — B2 dominance (r27) / r8 deadness and r25/r12/r10/r7 liveness on the BUILT image.
- **H8** — recompute every CRC (main holding 0x13100, `0xC4FFC` cave block, `0xC6FFC` cal page, the E5xxx record block)
  with `verify_bootloader_crc.py`.
- **V1/A16A** — re-header the revert `.rwd` files.
- The four-agent adversarial pass on the built image (arithmetic, unit/scale, build-script audit, interlocks/downstream),
  each re-deriving from the image, with "do not flash" reachable.

---

## 7. Scripts (all under `analysis-2020accord/studies/angle_loop/`, fixed seeds, `python <script>`)

| script | what it does |
|---|---|
| `panel/score_time.py` | **NEW** — the common time scorer (ds_time engine, one pipeline, the friction members, the goal gates) |
| `c2/rev2B/c2_verify.py` | re-assembles D2a and B0r via the verified two-pass `ds_asm`, asserts the cave sha256, the no-unlisted-byte diff, the live-register non-clobber, and D2a's validity guard-in-bytes |
| `panel/score_freq.py` | the common freq scorer (re-run this session; 0 GATE-2 fails for both) |
| `panel/D-structure/ds_asm.py`, `ds_bytes.py`, `ds_final.py`, `ds_time.py` | the verified source of truth for the candidate parameters, the assembler, and the time engine (reused, not re-implemented) |
