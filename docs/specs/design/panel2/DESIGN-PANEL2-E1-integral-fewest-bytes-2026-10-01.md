# DESIGN PANEL 2 — E1: THE INTEGRAL POLICY, FEWEST BYTES (2026-10-01)

**Status: DESIGN ONLY.** Nothing was built, flashed or sent; the fork was not touched; no image or `.rwd` was written.
Ghidra was used read-only (`disassemble_bytes` with `dry_run: true`, `list_open_programs`) on the open **V294** program
(code-identical to V295 except cal `0xC63EA`) and stock `code.bin`. Nothing was saved.

**Author:** designer E1, a subagent (Opus) working for the orchestrator `main`. Three other designers work other axes; I
have not seen their work. **This is a report; a late finding is not licence to act.**

**Axis.** Resolve round-2 refuter finding **F1** — *turn-hold and the goal's tracking metric fail at 15–22 m/s because the
integrator clamp ICL 4096 (≈ 657 T) is below the identified spring load (850–1170 T)* — **without re-opening the
override-release lurch (the V283 class), with the FEWEST firmware bytes.** Baseline skeleton: the C2 rev2-A PRIMARY **P2**
(fresh-rate D Kd 34, 6-knot G, Kp 112 flat, Ki 56, 156-byte cave at `0xC4C00`). Every number below is against P2.

Every decision-bearing claim is **EVIDENCE** (with method) or **BELIEF**. Code is cited by address/grep string.

---

## 0. The answer in one page

**F1 is caused by one scalar and is fixed by one scalar.** The integer I is clamped at `icl = (ICL<<10)>>3 = ICL·128`;
it contributes `(I>>7)` to the sum, so a saturated I delivers `T_I = ICL · 0.9922(fade) · 0.990(lag) · 0.16314(fwd) =
ICL · 0.16024` T. At ICL 4096 that is **657 T** — below the spring load on ordinary 1.5–2.0 m/s² curves at 15–22 m/s.
**Raising ICL to 8192 (a single cal cell, +0 code bytes) delivers up to 1313 T and fully resolves F1.** EVIDENCE: the
mirror arithmetic (`e1_lane.t_from_I_contrib`), the spring-load sizing (`e1_design_icl.py`), and the controlled
nonlinear simulation (`e1_run.py`, engine == the C2 refuter's `nl_sim`, CONTROL max|ΔT| = 0 over 32 cases).

**The brief's constraint — "without re-opening the lurch" — is where the design lives.** Raising ICL re-opens the V283
release lurch (a wound/held high I snaps the wheel back on release). Three facts, each MEASURED, decide the policy:

1. **Freezing I does not bound the lurch — only DRAINING it does.** A frozen high-ICL integrator still holds a large
   value on release (E1-freeze, lowering the freeze to 320, leaves the 10–12.5 m/s light-hand lurch at 11–13°). A
   **firm-hand RESET (I := 0 at |tq| > 1536)** drains it and cuts the firm-hand lurch **3–4×** (15.1° → 3.9° at 10 m/s,
   b_lo×J_hi). +12 cave bytes.
2. **The light-hand lurch cannot be bounded by any torque threshold in the 256–512 band**, because a light override
   (word ≤ 512) is **indistinguishable from the hands-off reaction torque** the column already carries (route a6: 25–48 %
   of fast hands-off frames read > 500). A bleed/freeze in that band drains I during normal hands-off holds: **E1-bleed's
   tracking collapses to 0.787 at 8–15 m/s under the a6 reaction-torque telegraph.** So the light-hand lurch is a
   **pre-declared, quantified miss** (enlarged M6), the same class C2 already declared, with the R9/R3\* stops.
3. **The firm RESET is hands-off-immune.** Its threshold 1536 is above the hands-off torque p99.9 (1166, route a6), so it
   never fires hands-off: **E1-reset's tracking is UNCHANGED by the reaction-torque telegraph** (0.988/0.993, same as
   without it), where E1-bleed's is wrecked.

### 0.1 The implementations (≥ 3; the judges pick, I do not)

| id | what | Δbytes vs P2 | turn-hold ≥ 0.90 (a_lat 2.0) | goal tracking 8–22 m/s (bar 0.95–1.05) | firm-hand lurch | light-hand lurch | verdict |
|---|---|---|---|---|---|---|---|
| **E1-cal** | flat ICL 8192, pure cal | **+0 code** | **0.998** | **0.986–0.994** | grows (declared) | grows (declared) | **FEWEST-BYTES FLOOR**: meets the goal at zero code bytes |
| **E1-reset** | ICL 8192 + firm reset `I:=0` at \|tq\|>1536 | **+12** | **0.998** | **0.986–0.994** (telegraph-immune) | **bounded (3.9° / 10 m/s)** | declared (M6+) | **PRIMARY** |
| E1-bleed | ICL 8192 + reset + light-hand bleed (256–512) | +34 | 0.998 | **0.787 under telegraph** | bounded | bounded (10–15 m/s) | **REJECTED**: wrecks hands-off tracking |
| E1-freeze | ICL 8192 + reset + freeze lowered to 320 | +12 | 0.998 | 0.988 | bounded | **11–13° (not bounded)** | **DOMINATED**: a freeze holds I high |
| E1-sched | speed-scheduled ICL (table col + walk + inject) + reset | +~44 | 0.90–1.00 | **0.885–0.935 FAIL** | bounded | bounded | **REJECTED**: the deficit is not speed-separable from the lurch band |
| E1-splitP | Kp 200 (P carries the curve), ICL 3072 small | +0 code | **0.76–0.84 FAIL** | fail | — | — | **REJECTED**: GATE 2 (Kp 160 → tier A 40°) and turn-hold both fail |

**Baseline for contrast — P2 as-is (ICL 4096):** turn-hold min **0.727** (a_lat 2.0) / 0.806 (a_lat 1.5); tracking
**0.89–0.90** (8–15) and **0.856–0.864** (15–22). This is F1.

---

## 1. The cause, re-derived (EVIDENCE)

### 1.1 The I ceiling is a scalar (`e1_lane.t_from_I_contrib`, arithmetic)

```
icl = (ICL << 10) >> 3 = ICL * 128           0x29DA0 ld.hu ICL ; 0x29DAC shl 0xa ; 0x29DAE sar 0x3
I   = clamp((I8>>3) + inc, -icl, +icl)        0x29DA4..0x29DC2    (I8 = gp-0x6dd0 holds 8*I)
S   = (I>>7) + P + D                           0x29F18            -> I branch of S is at most ICL
T_I = ICL * (254/256) * DClag(0.990) * (5346/32768)  = ICL * 0.16024 T
```

| ICL | I-branch cap | delivered T_I (fade 254) | fade floor (0.297) |
|---|---|---|---|
| 4096 (P2) | 4096 | **657 T** | 194 T |
| 6144 | 6144 | 985 T | 291 T |
| **8192** | 8192 | **1313 T** | 388 T |

No int32 risk at 8192: I8 ≤ 8·8192·128/8 … `(I8>>3)+inc` ≤ 1.4·10⁶ < 2³¹; the sum clamp SCL 15360 still bounds S, and
the I branch (≤ 8192) stays under SCL (EVIDENCE: `e1_lane`, overflow check).

### 1.2 The spring load needs more than 657 T (EVIDENCE: `e1_design_icl.py`, the r71b family)

`theta_sw = a_lat·L·SR/v²` (L 2.83, SR 16); `load = k·sat·tanh(theta/sat)` from the plant family. ICL needed = load/0.16024.

| a_lat | worst speed ≥ 8 m/s | load | ICL needed (nominal) | ICL needed (b_lo×J_hi) |
|---|---|---|---|---|
| 1.5 m/s² | 17 m/s | 950 T | 5925 | 6822 (at 8 m/s, 60.8°) |
| 2.0 m/s² | 17 m/s | 1166 T | 7274 | 7718 (at 8 m/s) |

**Flat ICL 8192 covers a_lat 2.0 everywhere ≥ 8 m/s on every credible member.** The worst (b_lo×J_hi, 8 m/s) needs 7718.

### 1.3 The fix works (EVIDENCE: controlled simulation; CONTROL max|ΔT| = 0, `e1_control.py`)

| metric (bar) | P2 (ICL 4096) | **ICL 8192** |
|---|---|---|
| turn-hold min, a_lat 1.5, ≥ 8 m/s (≥ 0.90) | 0.806 | **0.998** |
| turn-hold min, a_lat 2.0, ≥ 8 m/s (≥ 0.90) | **0.727 FAIL** | **0.998** |
| goal tracking, r71b paths, 8–15 m/s (0.95–1.05) | 0.89–0.90 FAIL | **0.986–0.988** |
| goal tracking, r71b paths, 15–22 m/s | **0.856–0.864 FAIL** | **0.993–0.994** |
| goal tracking, r71b paths, > 22 m/s | 1.00–1.002 | 1.001–1.006 |

**Hands-off-immune:** with the a6 reaction-torque telegraph on, E1-reset's tracking is unchanged (0.988 / 0.993 / 1.006);
the reset at 1536 never fires hands-off (p99.9 = 1166).

---

## 2. The integral POLICY (the lurch bound) — what the measurement forced

The brief: raise authority *without re-opening the lurch*. Three candidate bounds; only the firm reset survives.

### 2.1 Firm-hand RESET (the PRIMARY's bound) — DRAIN, don't freeze. +12 cave bytes.

Inserted in the cave's existing FRZ path (`r8` already = |driver torque|). Encodings confirmed by Ghidra dry-run
(§4). On a firm grab the cave zeroes `gp-0x6dd0` **before** the I-clamp reads it at `0x29DA4`, so `I_old = 0` and (the
freeze already forcing `exc = 0`) `I = clamp(0) = 0`; `0x2A190` then stores that 0. The I rebuilds from 0 on release.

```
   movea 1536, r0, r13        ; FIRM threshold                 (20 6e 00 06, 4 B)
   cmp   r13, r8              ; r8 = |gp-0x4f68|               (ed 41,       2 B)
   bnh   .noz                 ; |tq| <= FIRM: skip             (Format III,  2 B)
   st.w  r0, -0x6dd0[gp]      ; zero the I8 cell               (64 07 31 92, 4 B)
.noz:  (fall into the existing  mov 0,r6 ; jr 0x29D7E)
```

**Effect (EVIDENCE: `e1_run.lurch`, strong override, overshoot past setpoint on release, nominal/b_lo×J_hi):**

| firm hand (word 2400) | 10 m/s | 12.5 | 15 | 17 |
|---|---|---|---|---|
| ICL 8192, **no reset** | 11.3 / 15.1 | 7.6 / 8.1 | 4.0 / 4.5 | 2.3 / 2.9 |
| ICL 8192, **+ reset** | **6.3 / 3.9** | **3.4 / 0.9** | 0.9 / 0.0 | 0.3 / 0.0 |

The reset cuts the firm-hand lurch **3–4×**. (At 8 m/s a_lat 1.5 is a 48° wheel angle; the release overshoot there is
~13° for **any** policy — it is the P-driven return from a huge displacement, not integral windup, and is intrinsic to
having authority at 8 m/s. Declared.)

### 2.2 Why NOT freeze lower (E1-freeze, dominated) and NOT bleed (E1-bleed, rejected)

- **E1-freeze** (freeze at 320 instead of 512): a freeze HOLDS I at its pre-grab value; a high-ICL hold still snaps back.
  Light-hand lurch at 10–12.5 m/s stays **11–13°** (b_lo×J_hi) despite +12 B. DOMINATED by E1-reset at equal bytes.
- **E1-bleed** (drain I by `I>>3` while 256 < |tq| ≤ 512): bounds the light-hand lurch at 10–15 m/s to ~2–3°, BUT the
  256–512 band is exactly the hands-off reaction-torque band. **Under the a6 reaction-torque telegraph, E1-bleed's goal
  tracking collapses to 0.787 at 8–15 m/s** (EVIDENCE: `e1_track.py frz`) — it drains the very I the raised ICL added.
  REJECTED: it trades F1 back for a hands-off failure. **The light override and the hands-off reaction torque are not
  separable by magnitude**, so the light-hand lurch is irreducible by a torque-threshold policy.

### 2.3 The light-hand lurch is a PRE-DECLARED, QUANTIFIED MISS (enlarged M6)

E1-reset keeps the freeze at 512 (hands-off-safe). A light hand (word ≤ 512, below the freeze) winds I to the raised
ICL and overshoots on release:

| light hand (word 400) | 8 m/s | 10 | 12.5 | 15 | 17 |
|---|---|---|---|---|---|
| nominal | 5.2 | 11.2 | 10.2 | 4.0 | 2.3 |
| **b_lo×J_hi** | 13.1 | **16.8** | **16.0** | 6.6 | 3.9 |

This is the C2 M6 class, enlarged by the raised ICL (C2 M6 was 10.6°). **It cannot be bounded in firmware without
wrecking hands-off tracking (§2.2).** Declared as **M6-E1** with the same stops C2 used: **R9** (operator's words — a
lurch on letting go) and **R3\*** (0.5–5.5 Hz ring). The operator's lived experience decides acceptability; his first
hands-off drive carries the LIVE check (§5). A fork-side override taper (O1) and the existing fade both attenuate it.

---

## 3. Everything else is unchanged (EVIDENCE)

- **GATE 2.** E1-cal / E1-reset / E1-bleed have the **identical linear loop transfer** to C2 P2 (same Ki 56, Kp 112,
  Kd 34, G table). ICL is a nonlinear anti-windup clamp, invisible to the small-signal GATE-2 analysis; the reset/bleed
  act only hands-on, outside the hands-off GATE-2 operating point. **They inherit P2's GATE-2 PASS exactly** (0 fails,
  tier A 46.7°, tier B 30.5°). The refuters' open issues on the D path (F2 operand frame ratio 1.155; F3 13–20 Hz
  phase-fragility) are inherited unchanged — E1 touches neither the D operand nor the loop gain.
- **E1-splitP FAILS GATE 2** (EVIDENCE: `score_freq`): Kp 160 → tier A **40.0°**, tier B **19.6°**; Kp 200 → tier A
  **29.7°**, tier B **11.0°** (bars 45° / 30°). And it FAILS turn-hold (0.76–0.84 at Kp 200). P cannot carry a curve to
  zero steady error; the credible set forbids the Kp it would need (≈ ×4.7).
- **Engage-under-load droop UNCHANGED** across every policy (EVIDENCE `e1_run.engage`): 4.5 / 6.1° at 8 m/s down to
  0.6 / 0.7° at 27 m/s (nominal / b_lo×J_hi) — identical to P2, = C2 M7 (engage starts at I = 0; ICL and the reset do
  not touch the build-up).
- **Co-steer, stale-I settle.** Co-steer (a helping torque < 512) winds I toward the assisted angle; on release the
  droop is the same class as C2's co-steer (≤ 2.6°). Stale-I: on any skip tick I := 0 (`0x2A190`, unchanged); on
  re-engage I rebuilds from 0 (= engage droop above). The reset makes a firm hand look like a skip tick for I. BELIEF:
  the co-steer number is not re-run here beyond C2's; it is unaffected by ICL (co-steer torque < freeze).

---

## 4. Bytes (the axis) and GATE 1

**ICL is a CAL** (`0xC61BA`, P2 already writes it = 4096 → E1 writes 8192): **+0 code bytes.**

| impl | cave B | written B | Δ vs P2 | new RAM write | GATE 1 |
|---|---|---|---|---|---|
| **E1-cal** | 156 | 200 | **+0** | none | **nothing new** (smallest footprint) |
| **E1-reset** | 168 | 212 | **+12** | `gp-0x6dd0` on firm-hand ticks | the lane's OWN I8 cell |
| E1-bleed | 190 | 234 | +34 | `gp-0x6dd0` | rejected anyway |
| E1-freeze | 168 | 212 | +12 | `gp-0x6dd0` | dominated anyway |
| E1-sched | 200 | 244 | +~44 | `gp-0x6dd0` + r17 carry | rejected anyway |

**GATE 1 for the reset.** `gp-0x6dd0` is the lane's **own** integrator cell: written every tick at `0x2A190`, and its
first read after the hook is `0x29DA4` (EVIDENCE: the lane-hook trace §2–§6, which lists `gp-0x6dd0` as *private* to
`FUN_00028ea6`). The cave runs inside the 1 kHz task between `0x29D76` and `0x2A190`; no other task interleaves. So the
cave zeroing `gp-0x6dd0` writes the lane's private cell before its own read — **clean**. E1-cal makes **no** new RAM
claim at all (the smallest possible GATE-1 surface), which is its one advantage over E1-reset.

**Encodings confirmed (Ghidra dry-run, this session):** `st.w r24,-0x6dd0[gp] = 64 c7 31 92` → `st.w r0 = 64 07 31 92`;
`movea 512,r0,r13 = 20 6e 00 02` → `movea 1536 = 20 6e 00 06`; `cmp r13,r8 = ed 41`.

---

## 5. The wire instrument (no new telemetry bit)

**No instrument exists for I (`gp-0x6dd0`).** But the EDIT's effect is observable on signals already on the wire, so no
cave bit is spent (prefer the inert tap):

- **The goal itself is the instrument.** The failure F1 fixes is a *steady hold error at 15–22 m/s*. On the **427 tap**
  (T = `gp-0x6b38`, 50 Hz) in a hands-off 1.5–2 m/s² curve: V295 holds with |θ_sp − θ| ≈ 8° and the tap short of the
  load; E1 holds with |θ_sp − θ| ≲ 2° and the tap at the load. The C2 §7 regression (c_I/c_P corner, the I component)
  already reads the integral on the tap; a rising c_I that holds the curve = the raised ICL is live.
- **LIVE:** at 15–22 m/s, hands-off, a curve held with |θ_sp − θ| < ~3° where V295 lagged ~8°.
- **The reset** fires only hands-on (|tq| > 1536) and is not part of a hands-off symptomatic drive; it needs no
  instrument. If the operator wants to see it, a single `0x14A` cave bit (byte 4, bits 3–7 are cave-owned per the record)
  can flag "reset fired", +0 code if folded into an existing status write — **not proposed** (the drive is hands-off).
- **REVERT (R9):** the operator reports a lurch on letting go of a turn (the declared M6-E1). **R3\***: a 0.5–5.5 Hz
  growing ring. **R6:** |θ − θ_sp| > 10° hands-off at > 8 m/s.

---

## 6. What a FAIL looks like (written before any build)

| id | failure |
|---|---|
| H1 | on the BUILT image, the reset block does not decode as `movea 1536 ; cmp r13,r8 ; bnh ; st.w r0,-0x6dd0[gp]`, or the cave writes any RAM other than `gp-0x6dd0`, or any register outside the P2 scratch set + r13/r8 changes |
| H2 | the linear GATE-2 on the built table/cals differs from P2 (it must be identical — same Ki/Kp/Kd/G) |
| H3b | the goal tracking slope < 0.95 for any member in any band ≥ 8 m/s, on the built cals, **with the reaction-torque telegraph on** (E1-reset must be telegraph-immune; E1-bleed fails this and is why it is rejected) |
| H4 | int32 wrap at ICL 8192 anywhere in the I path |
| H-hoff | the reset fires on any hands-off frame of a real route (|tq| > 1536 hands-off) — it must not |

**On the car:** FAILED its stated goal if on-car turn-hold < 0.90 or tracking outside 0.95–1.05 in any band ≥ 8 m/s.
The pre-declared miss **M6-E1** (light-hand release lurch, up to ~17° b_lo×J_hi at 10–12.5 m/s) is a FAIL of the lurch
criterion, declared now, bounded by R9/R3\*.

---

## 7. Files (all `python`, bin_decompile env; CONTROL == nl_sim at baseline)

Scripts in `analysis-2020accord/studies/angle_loop/panel2/E1-integral-fewest-bytes/`; text outputs in `out/` (tracked),
caches in `_scratch/angle_loop/E1-integral-fewest-bytes/` (gitignored):

| script | what | output |
|---|---|---|
| `e1_lane.py` | the E1 lane = nl_sim.Lane + the integral policy as per-column switches; `t_from_I_contrib` | — |
| `e1_control.py` | CONTROL: E1Lane(baseline) == nl_sim.run bit for bit (32 cases, max|ΔT| 0) | `out/control_out.txt` |
| `e1_design_icl.py` | ICL sizing from the spring load | `out/icl_design_out.txt` |
| `e1_policies.py` | the implementations (E1-cal/reset/bleed/freeze/sched/splitP) | — |
| `e1_run.py` | turn-hold, lurch, engage, vectorised over policies | `turnhold/lurch/engage.json` |
| `e1_track.py [frz]` | the goal tracking metric on r71b paths, with/without the reaction-torque telegraph | `out/track_out.txt`, `out/track_frz_out.txt` |
| `e1_bytes.py` | the byte account (encodings confirmed vs Ghidra) | `out/bytes_out.txt` |

**Do not pick a winner here; the judges pick.** My ranking by the brief (priority 1 goal, priority 2 bytes): E1-reset
(primary) > E1-cal (the +0-byte floor, if the firm-hand lurch is acceptable) ≫ E1-bleed/E1-freeze/E1-sched/E1-splitP
(rejected/dominated).
