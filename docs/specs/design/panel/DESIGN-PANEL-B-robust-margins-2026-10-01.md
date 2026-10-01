# DESIGN PANEL B — robust-margins-first (2026-10-01)

**Status: DESIGN ONLY. Nothing built, flashed or sent; the fork was not touched.** Ghidra was used read-only earlier
in the session (`decompile_function` on the rate path, byte reads of the V295 image); the GhidraMCP server dropped
mid-session, so every byte quoted here is a **Python little-endian read of the V295 plain image** plus the in-place
decodes already dry-run-verified in `DESIGN-ANGLE-LOOP-C1-2026-09-30.md` §1.1 (cited, not re-run). **Re-decode the built
image in Ghidra (H5) before any flash** — flagged as a hazard, not waived.

**Author:** panel designer **B-robust-margins** (a subagent, Opus), for the orchestrator `main`. I do not see the other
four designers. **My angle, per the brief: ROBUST MARGINS FIRST** — every combined member of the credible set
(including `b_q×J_hi`, `b_q×J1.0`, `b_q×tau6`, and every combined member with the 100 Hz hold aged to 20 ticks) must
have **PM ≥ 30° and GM ≥ 6 dB at every speed, nominal/tier-A ≥ 45°**, *before* any tracking is bought. I do **not** pick
a winner across my three implementations — they are scored honestly; the judges choose.

**Base image:** V295 `_v295_…B1050…TORQUE.TAP_plain_image.bin`, sha256 `5c044d65…52ed` (V294 is code-identical except cal
`0xC63EA`+CRC). **Member source:** `c1r2_members.py` (the full factorial damping×inertia×delay×hold-age — it already
carries `b_q×J_hi`, `b_q×J1.0`, `b_q×tau6`, every `×tau6` and every `+h10` combined member; its `selfcheck()` asserts
identity with the stability refuter's `refute_c1_ind.member_params`). **I extended nothing away** — I gate all of
TIER_A (7, PM≥45) + TIER_B (62, PM≥30) = **69 members × 140 speeds (0.25 m/s grid incl. the plant knots) = 9 660 gated
points** per implementation.

Every decision-bearing claim is **EVIDENCE** (with method) or **BELIEF**, cited by grep string / address, never line
number. Scripts: `analysis-2020accord/studies/angle_loop/panel/B-robust-margins/` (`b_lib.py`, `b2_stab.py`,
`b_env2.py`, `b_fit.py`, `b_gate.py`, `b_track.py`, `b_time.py`; fixed seeds). Outputs:
`analysis-2020accord/_scratch/angle_loop/B-robust-margins/` and `gate_{B1,B2,B3}.txt` / `time_score.txt` next to the
scripts.

---

## 0. The three implementations and the decision in one page

All three share the **in-place angle-loop edit set** (the zero-cave P loop of the goal box: E1 `0x28F4C` operand →
`gp-0x6a00`; E2 `0x28FA4` `subr→add`; B2 `0x29A50` `cmovne`; A2 `0x29A56` `bne→be`; E4 `0x29D6A` sp = `gp-0x69ae`;
H `0x29D76` `jarl 0xC4C00,r6`), the **speed-gain cave** G(v) that scales the error `E' = (E·G(v))>>8` before P and I,
and the cals `a 0 / b 8192 / C 65535` (r26 = 16·θ) with Kp_base 112, Kp-rail/clamps unchanged. They differ in **one
lever each**:

| | **B1 — cut the gain** | **B2 — buy margin with a fresh-rate D lead** | **B3 — no firmware integrator** |
|---|---|---|---|
| lever | held-rate D (edit E5 on `gp-0x6a56`), Kd 20; I freeze on hand torque; **highway Kp cut** until the gate holds | D moved to the **fresh 1 kHz rate `gp-0x6abe`** (E5 operand retarget), Kd≈41 (model 24); I freeze; **higher Kp at the same gate** | **Ki = 0** (no integrator, no freeze); held-rate D Kd 20; DC left to the fork's slow outer integral (τ_o ≥ 1 s) |
| firmware delta vs B1 | — | E5 operand `−0x6a56`→`−0x6abe` (2 B) + drop the negate (sign) + Kd cal 20→41 | Ki cal 56→0; cave drops the 24-byte freeze branch |
| cave bytes | 96 code + 42 table = **138 B** | **138 B** (same cave) | **~72 code + 42 table = ~114 B** |
| new RAM words | 0 | **0** (`gp-0x6abe` is a live global) | 0 |
| GATE 2 (9 660 pts) | **0 fails**, min tier-B PM **31.7°**, GM ≥ 10.0 | **0 fails**, min tier-B PM **31.4°**, GM ≥ 14.5 | **0 fails** (no-I monodromy), min tier-B PM **32.2°**, GM ≥ 6.0 |
| Re(T/ω)₂₀ vs V295 (age 0 / 10) | −0.585 / −0.656 = **0.92× / 0.60×** | **−0.46 / −0.30 = 0.73× / 0.28×** | −0.59 / −0.66 = 0.93× / 0.61× |
| goal tracking slope_inner (≥ 8 m/s, worst) | **0.952** (b_q @17) | **0.961** (b_q @17) | **0.46** (FAILS the 0.95 floor) |
| 0.2 / 0.5 Hz in-phase proxy @17 m/s | 0.82 / 0.34 | **0.87 / 0.41** | 0.44 / 0.36 |
| what it costs | 232–363 ms group delay at 0.2 Hz (M3) | same group delay class, ~10 % less; **BELIEF on `gp-0x6abe`'s EMA corner** | **inner loop tracks only 46–68 % of DC at speed** — relies entirely on the fork integral, which is forbidden < 8 m/s → permanent low-speed dead zone |

**EVIDENCE:** `gate_B1.txt`, `gate_B2.txt`, `gate_B3.txt` (full factorial, two independent linear methods: `b_lib.frf`
LTI margins + exact 10-tick periodic monodromy — `stab_lin.exact` for held D, `b2_stab.exact_fresh`/`rho_gen` for fresh
D and for Ki=0); `track_all.txt` (the goal's own `c1r2_trackmetric` weighting from r71b's measured desired-lat-accel
spectrum, with its positive control ±0.028).

**My reading (not a winner pick):** **all three meet the robust-margins mandate.** On *tracking* under that mandate,
**B2 > B1 ≫ B3**: B2 buys ~15–20 % more highway Kp than B1 for the *same* margins and *less* 20 Hz anti-damping, at the
price of one BELIEF (the `gp-0x6abe` EMA corner, closable with one trace). B1 is the safe default (no unverified
premise). B3 is the smallest edit but **fails the goal's own tracking criterion on the inner loop** — it is only viable
if the fork integral is trusted to carry 30–50 % of the DC, and it leaves a permanent low-speed dead zone. The rev-2
design (`DESIGN-ANGLE-LOOP-C1`) is B1's class; my B1 reaches the same gate with a **6-knot (42 B) table vs rev-2's
7-knot (48 B)**, 6 bytes smaller, at a small 17–22 m/s tracking cost.

---

## 1. Implementation B1 — the robust gain cut (held-rate D)

### 1.1 Loop, integer form
```
s_new  = (8192*theta)>>10 = 8*theta                         # 0x28F8E..  (a=0, b=8192)
r26    = clip(s_old + s_new, -65535, 65535); s_old = s_new  # 0x28FA4 add (E2) ; 16*theta DC
E      = (sp69ae<<2) - r26                                  # cave 0xC4C00: shl 2 ; sub r26   (E4: sp = gp-0x69ae)
G      = walk(TBL_B1, gp-0x6a5e)                            # cave: G(i) + ((v-X(i))*S(i) >> 12)
E'     = s32(E*G) >> 8                                      # cave: mul ; sar 8          <-- THE SPEED GAIN (P and I)
frozen = |gp-0x4f68| > 512  or  (ramp & 0x8000)==0          # cave: I freeze on hand torque / ramp-in
e5     = 0 if frozen else E'>>5                             # FRZ: r6=0 -> Honda exc=0, I unchanged
I      = clip((I8>>3) + ((e5*56)>>3), -(4096<<7), 4096<<7)  # Ki=56, ICL=4096
P      = clip((E'*112)>>8, -15360, 15360)                   # Kp_base=112
D      = clip((-20 * gp-0x6a56)>>3, -10240, 10240)          # E5: held rate, Kd=20, DCL=10240
S      = (I>>7) + P + D                                     # then fade, SCL, output lag 992/507, fwd, OCL
```
`Kp_eff = 112·G/256`, `Ki_eff = 56·G/256` (constant PI corner f_I = 7.8125·56/(2π·112) = **0.622 Hz**).

### 1.2 Bytes (in-place; decodes = C1 §1.1 Ghidra dry runs, byte values re-read from V295 in Python this session)
| id | addr | V295 → B1 | meaning |
|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95`→`24 3f 00 96` | `ld.h -0x6a00[gp],r7` — x = θ (0.1° counts); ±12000 bail tests θ |
| E2 | `0x28FA4` | `89 d1`→`c9 d1` | `subr→add` — r26 = s_old+s_new (2-tap FIR, DC 16) |
| B2 | `0x29A50` | `e2 47 00 00`→`e0 df 34 43` | `cmovne r0,r27,r8` — r8 := (req==1)?bVar2:0 |
| A2 | `0x29A56` | `da 05`→`b2 05` | `bne→be` — PID runs iff ramp≠0 ∧ r8≠0 (kills the 0x7FFF sentinel/latch) |
| E4 | `0x29D6A` | `08 80 ed 80`→`24 87 52 96` | `ld.h -0x69ae[gp],r16` — sp = gp-0x69ae |
| H | `0x29D76` | `c2 82 ba 81`→`89 37 8a ae` | `jarl 0xC4C00, r6` — the cave hook |
| E5 | `0x29EDE`,`0x29EE0` | `c7 00`→`80 39`; `10 40 bb 41`→`24 47 aa 95` | `subr r0,r7` (−Kd) ; `ld.h -0x6a56[gp],r8` — **D on the 100 Hz held rate** |

**Cave `0xC4C00` (96 code + 42 table = 138 B), inside the free span `0xC4BD8..0xC4FEF` (all 0xFF in V295 — EVIDENCE
Python).** The 96 code bytes are byte-identical to C1 rev-2's cave (sha of the code `a6f902d5…`, `c1_assemble.py`); only
the table shrinks. My table is **6 knots** vs rev-2's 7 (12 B → 6 B saved net on the table; still 138 B total because
rev-2's 7-knot table made it 144 B):
```
TBL_B1 (6 rows, LE X u16 / G u16 / S s16 Q12, + 0xFFFF sentinel):  Kp_eff = 112*G/256
  X 714 (3.10 m/s)  G 952   ...  Kp_eff 416
  X1843 (8.00)      G1321        Kp_eff 578
  X2304 (10.00)     G 855        Kp_eff 374
  X2742 (11.90)     G 699        Kp_eff 306   <- the b_q-dip knot (binding member b_q*J1.0*tau6+h10)
  X3571 (15.50)     G1044        Kp_eff 457
  X6198 (26.90)     G2041        Kp_eff 893
```
Fit by LP (`b_fit.py`) to stay ≥ 4 % under the full-factorial PM/GM envelope at every 0.25 m/s point (0 integer-walk
over-envelope points — EVIDENCE `b_fit.py`). The dip at 10–13 m/s is the `b_q` step (b×0.25 at ≥ 12.5 m/s): a 6-knot
table follows it; a 5-knot table cannot (it forces Kp_eff to 191 at 11.9, a 115-count tracking loss — EVIDENCE
`b_fit.py` 5-knot run), so **6 knots is the minimum** for this envelope. A 7th knot at 17.5 m/s recovers ~85 Kp_eff at
17–22 m/s (see §1.5 miss M-trk).

### 1.3 Cals
`a 0xC63E8 = 0 · b 0xC63EA = 8192 · C 0xC62E6 = 65535 · DB 0xC62E4 = 0 · Ki 0xC63E6 = 56 · ICL 0xC61BA = 4096 ·
DCL 0xC61B6 = 10240 · Kp Y 0xE5384 ×5 = 112 · Kd Y 0xE5126 ×4 = 20.` CRC blocks: cave trailer `0xC4FFC`, cal
`0xC6FFC`, Kp/Kd `0xE5xxx` — the builder recomputes all (`verify_bootloader_crc.py`).

### 1.4 GATE 2 — full credible set, hold ages 1–20 (EVIDENCE `gate_B1.txt`)
**0 stability / margin fails on 9 660 gated points.** Two independent methods agree.

| tier | members | min PM (binding, v) | min GM | max Ms | worst 5–30 Hz \|T\| | max ρ |
|---|---|---|---|---|---|---|
| A (≥45) | nominal,J_lo/hi,b_lo/hi,tau0/6 | **52.0** (J_hi, 1.0 m/s); nominal 67.5 | 17.2 | 1.42 | ≤ −5.8 dB | 0.985 |
| B (≥30) incl. every b_q× and +h10 | 62 | **31.7** (`b_lo*J1.0*tau6+h10`, 1.0 m/s); `b_q*J1.0*tau6+h10` 32.8 @26.9 | 10.0 | 2.41 | ≤ −4.8 dB | 0.987 |

Binding-member PM (°): `b_q×J1.0` 40.7 (@26.9) · `b_q×J1.0+h10` ~35 · `b_q×J_hi` 52.0 · `b_lo×J1.0×tau6+h10` 31.7.
**Re(T/ω):** 13 Hz −0.636 (4.24× V295, age 0) / −1.14 (age 10); **20 Hz −0.585 = 0.92× V295 (age 0), −0.656 = 0.60×
(age 10, like-for-like)** — the 20 Hz rule holds. (EVIDENCE `gate_B1.txt`, `_re13.py`.)

### 1.5 Tracking on the goal's own metric (EVIDENCE `track_all.txt`, `c1r2_trackmetric` + its ±0.028 positive control)
slope_inner ≥ **0.952** in every band ≥ 8 m/s on every tabulated member (8 m/s ≥ 0.999; 15–19 m/s 0.952–0.978; > 22
≥ 0.985). **Predicted PASS** of the 0.95–1.05 goal, margin as thin as 0.002 at 17 m/s on the b_q members — inside the
weighting's accuracy, so declared borderline (M-trk). 0.2/0.5 Hz in-phase proxy 0.82/0.34 @17 m/s; group delay at
0.2 Hz 232–363 ms at 12.5–19 m/s (**pre-declared miss M3**).

### 1.6 Pre-declared misses, each with its revert signature
| # | miss | band | predicted | revert signature |
|---|---|---|---|---|
| M1 | low-speed stick-slip / dwell-then-jump ≤ V282 | 0–7 m/s | friction dead zone + hunt (§time) | R9 operator feel; R3 if a 1–5.5 Hz ring grows |
| M2 | dwell-then-jump at the b_q dip | 10–12.5 m/s | a few events (Kp_eff 306) | dj rate above r6c in that band only |
| M3 | transient tracking faster than the metric | 12.5–22 m/s | 0.2 Hz group delay 232–363 ms; 0.5 Hz in-phase 0.34–0.41 | R6 \|θ−θ_sp\|>10° hands-off >0.5 s |
| M-trk | goal tracking at 17–22 m/s is thin (6-knot table) | 17–22 m/s | slope 0.952–0.985; a 7th knot @17.5 recovers it | on-car slope < 0.95 in a band ≥ 8 m/s |
| M9 | residual robustness beyond the gated set | 10–30 m/s | `b_q×J1.3` 27° (report, not gated); `b_q×J1.0` ring ζ 0.13–0.16 at 15 m/s | R3: 1.0–5.5 Hz ring, ζ < 0.10 or growing |

### 1.7 Hazards & instrument
Hazards: the cave encodings are BELIEF until Ghidra decodes the **built** image (H5); B2-dominance/r25/r14 liveness
re-prove on the image (H6); CRC (H8). Fork prerequisites inherited from C1 §9 (F4 version marker, C3/4/5/8, Δmax(v),
O1, τ_o ≥ 1 s, camera LKAS off). **Instrument (no new telemetry bit):** the 427 tap `T` vs the reconstructed
`c_P·(raw−f14A)+c_I·Σ…+c_D·ω_18F`; LIVE if `c_P` tracks the band prediction (Kp_eff/800) and dips at 11.9 m/s; the
I-freeze is live if the I residual is flat in hands-on episodes. One 15–30 s symptomatic drive in two speed bands reads
it out (C1 §6).

---

## 2. Implementation B2 — buy the margin with a fresh-rate D lead (same cave, no new RAM)

**The lever (the brief's "a lead/phase term that buys the margin back instead of cutting gain").** B1's D is capped at
Kd 20 by the 20 Hz anti-damping rule, because the **100 Hz hold** on `gp-0x6a56` inverts the derivative's phase at
20 Hz (`Re(T/ω)₂₀` −0.585 at Kd 20; Kd 24 held already fails at −0.743 — EVIDENCE `b2_kd.py`). Reading the **fresh
1 kHz rate `gp-0x6abe`** (written by `FUN_00041464` @`0x22200` in slot 0, before the PID at `0x22522` — EVIDENCE memory
`reference_accord_gp6a56_pid_feedback_is_a_100hz_hold`) removes that hold inversion: at Kd 24 (model units)
`Re(T/ω)₂₀` is only **−0.46 = 0.73× V295** (age 0) and **−0.30 = 0.28×** (age 10), and the 5–13 Hz band, which B1
*anti-damps*, B2 **damps** (EVIDENCE `b2_kd.py`: fresh Kd 24, Re(5 Hz)/Re(10 Hz) move positive). The freed Kd headroom
damps the lightly-damped **1.3–2.3 Hz plant ring** that bounds `b_q×J1.0`, so the gate holds at a **higher Kp**.

### 2.1 Bytes — B1's set with **one** change, plus a cal
D is computed at E5 in the main flow (the cave hook returns before P/I/D), so B2 retargets E5's operand; **the cave is
byte-identical to B1, and there is no new RAM word.**
| id | addr | B1 → B2 | meaning |
|---|---|---|---|
| E5 operand | `0x29EE0` | `24 47 aa 95`→`24 47 42 95` | `ld.h -0x6a56[gp],r8` → `ld.h -0x6abe[gp],r8` (disp16 `0x9542`, EVIDENCE Python) — D on the **fresh** rate |
| E5 sign | `0x29EDE` | `80 39` (subr, −Kd) → **drop the negate** | `gp-0x6abe` is pol-opposite to `gp-0x6a56` (pol=−1), so D uses **+Kd** to keep D opposing the wheel rate (damping). Exact encoding = build detail; **confirm the sign on the built image (H-sign)**. |
| Kd cal `0xE5126` ×4 | — | 20 → **41** | `gp-0x6abe` is 4.7121 counts/deg·s vs `gp-0x6a56`'s 8.0, so Kd 41 realises model Kd 24 (41·4.7121/8 = 24.2). DCL 10240 unchanged (operand clamp ±13000). |

Cave `0xC4C00` and all other cals and in-place edits = **B1's, unchanged**. Table re-sized for the higher envelope:
```
TBL_B2 (6 knots):  X714 G1106 (Kp_eff 484) · X1843 G1475 (645) · X2304 G989 (433) · X2742 G826 (361, dip) ·
                   X3571 G1213 (531) · X6198 G2241 (980)
```

### 2.2 GATE 2 (EVIDENCE `gate_B2.txt`; fresh-D monodromy `b2_stab.exact_fresh`, ideal-fresh = conservative upper
bound on the D-path HF gain, so the EMA'd build is at least as stable)
**0 fails on 9 660 points.** Tier-A min PM 54.0 (J_hi); nominal 68.2. Tier-B min **31.4°** (`b_lo×J1.0×tau6+h10`,
1.0 m/s); `b_q×J1.0×tau6+h10` 32.7 @26.9; GM ≥ 14.5; max Ms 2.32; worst 5–30 Hz \|T\| ≤ −4.8 dB; max ρ 0.986.
**Re(T/ω): 13 Hz −0.49 (3.28× V295); 20 Hz −0.46 = 0.73× V295 (age 0), −0.30 = 0.28× (age 10).** Every margin equal or
better than B1 **at a higher Kp**.

### 2.3 Tracking (EVIDENCE `track_all.txt`)
slope_inner ≥ **0.961** every band ≥ 8 m/s (15–19 m/s 0.961–0.984 vs B1 0.952–0.978 — **+0.008–0.01**). 0.2/0.5 Hz
proxy 0.87/0.41 @17 m/s (B1 0.82/0.34). **Predicted PASS** with more margin than B1.

### 2.4 Pre-declared misses & hazards
Same M1–M3, M9 as B1 (lower magnitude on M3/M-trk from the higher Kp). **Added BELIEF (the price of B2):**
- **`gp-0x6abe`'s EMA corner is unverified.** The win holds for a corner ≥ ~35 Hz (EVIDENCE `b_env2.py` fresh_ema
  sweep: Kd 24 @ corners 35 and 45 Hz both pass and both beat B1; Kd 28 blows up the HF gain → env 0 at 10–15 m/s, so
  **Kd 24 is the fresh ceiling**). If the measured corner is < ~25 Hz, the 20 Hz margin erodes toward B1's and the Kd
  must drop — **revert to B1's E5** (operand `−0x6a56`, Kd 20). *Fallback if the corner is unusable:* a designed 1-pole
  lead in the cave off the fresh angle `gp-0x69ca` (1 RAM word), corner chosen not measured — +~16 cave bytes, 1 RAM.
- **The D sign on `gp-0x6abe` must be confirmed on the built image** (H-sign) — a wrong sign turns D from damping to
  anti-damping (revert signature: a 5–30 Hz line absent on V295, R4).
- **Instrument:** the 427 tap's `c_D` term now reads the fresh rate — the LIVE check is `c_D` *opposing* `ω_18F` with a
  magnitude ~1.7× B1's (Kd 41 on the 4.71-scale rate). A wrong sign reads as `c_D` *reinforcing* ω → abort.

---

## 3. Implementation B3 — no firmware integrator (Ki = 0), lean on the fork outer integral

**The lever:** set **Ki = 0** (`0xC63E6 = 0`). No integrator ⇒ no wind-up ⇒ **no I-freeze needed** (drop the 24-byte
freeze branch from the cave) ⇒ the smallest cave. DC/steady-state tracking is left to the fork's slow outer integral
(τ_o ≥ 1 s), which GATE 2 E permits only ≥ 8 m/s. Held-rate D (B1's E5, Kd 20) stays for damping.

### 3.1 Bytes & cave
In-place edits E1,E2,B2,A2,E4,H,E5 = B1's. **Cave = B1's displaced pair + G-walk + `E'=(E·G)>>8` + `jmp [r6]`** — the
freeze block (`ld.hu -0x4f68 … FRZ … DONE`, ~24 B) is removed (with Ki=0 the Honda I code computes `exc·0 = 0`, so I is
permanently 0 and the freeze is moot). **Cave ≈ 72 code + 42 table = ~114 B.** Cals as B1 except **Ki `0xC63E6` = 0**
(ICL then inert). Table re-sized for the Ki=0 envelope (no integrator phase lag ⇒ the gate permits more Kp):
```
TBL_B3 (6 knots):  X714 G1690 (Kp_eff 739) · X1843 G1805 (789) · X2304 G1357 (594) · X2742 G1162 (508, dip) ·
                   X3571 G1366 (598) · X6198 G2765 (1210)
```

### 3.2 GATE 2 (EVIDENCE `gate_B3.txt` for PM/GM/Ms/\|T\|; **stability from the no-I monodromy** `b2_stab.rho_gen(with_I=False)`,
because with Ki=0 the stock I register is a dead eigenvalue-1 state that makes the ordinary monodromy read ρ=1.0
spuriously — `_b3chk.py`)
**0 fails on 9 660 points.** Tier-A min PM 56.6 (J_hi @1.0); nominal 64.4. Tier-B min **32.2°**
(`b/1.9×J1.0×tau6+h10`, 11.75 m/s); `b_q×J1.0×tau6+h10` 32.7 @26.9; GM ≥ 6.0 (worst `b_q×J_hi×tau6+h10` 8.0, exact
no-I GM 9.8–18.7 dB on binding members); max Ms 2.46; worst 5–30 Hz \|T\| −2.3 dB (`b_q×tau6+h10`, highest of the
three but still ≪ +3 dB). **No-I monodromy worst ρ 0.9831** (binding `b_q×J1.0×tau6+h10` @15.5) — robustly stable.
Re(T/ω)₂₀ −0.59/−0.66 = 0.93×/0.61× V295.

### 3.3 Tracking — **the declared failure of B3** (EVIDENCE `track_all.txt`)
slope_inner **0.46–0.80** at 8–30 m/s (0.46 @17 m/s). **FAILS the goal's 0.95 inner-loop floor by design** — a P-only
inner loop has finite DC gain, so 20–54 % of the DC error is left for the fork integral to close. 0.2/0.5 Hz proxy
0.44/0.36 @17. B3 is interpretable **only** as "inner loop provides robust damping + fast disturbance rejection; the
fork's τ_o ≥ 1 s integral provides DC." Below 8 m/s there is **no integral at all** (fork integral forbidden, no
firmware I) ⇒ a **permanent dead zone** of F_s/(Kp_eff/10) ≈ a few tenths of a degree (quantified in §4 time, bc member).

### 3.4 Pre-declared misses, revert signatures, hazards
| # | miss | band | predicted | revert |
|---|---|---|---|---|
| M-dc | steady-state tracking error (no inner I) | all | slope_inner 0.46–0.80; needs fork integral ≥ 8 m/s | on-car slope < 0.90 with the fork integral on |
| M-dz | low-speed dead zone | 0–8 m/s | ~0.2–0.5° dead zone (no integral there) | R9 operator "won't hold a lane low speed" |
| M9 | ring robustness | 10–30 m/s | `b_q×J1.0` ζ 0.16–0.19 | R3 1.0–5.5 Hz ring ζ<0.10 |
Hazards: same build-image checks (H5/H6/H8); **plus the fork outer-loop interaction is now load-bearing** — if the fork
runs a faster integral (τ_o < 1 s) or any integral < 8 m/s, GATE 2 E goes unstable (EVIDENCE C1 §3.6: τ_o 0.3 s → GM
1.5–2.0 dB at 3 m/s). **Instrument:** the tap's `c_I`/`c_P` ratio should read **≈ 0** (no inner integrator); a nonzero
c_I means the build is wrong.

---

## 4. Time domain — nominal and `bc` (EVIDENCE `time_nominal.json` via `b_time.py`/`_scorenom.py`; `bc` via `_bcquick.py`; `harness_time.run` unmodified)

**B2's D is fresh in firmware; the harness D is on the 100 Hz held rate, so B2 here is run with held D (Kd 20) as a
PROXY for the LOW-FREQUENCY operator metrics** (dwell-then-jump, stick-slip, dead zone, hold, tracking) — those are set
by the Kp/Ki schedule + the I freeze, which B2 shares; the fresh D only improves HF texture/damping (the GATE-2
Re(T/ω) table). B3 is the real thing (Ki = 0, no freeze).

**Nominal plant (EVIDENCE):**

| metric | B1 (held Kd20 Ki56) | B2 (table, held proxy) | B3 (Ki = 0) |
|---|---|---|---|
| dwell-then-jump, total over 3–30 m/s | **32** | **28** | **0** |
| stick %, 3 m/s | 67 % | 62 % | **100 % (dead zone)** |
| hunt p2p, 3 m/s | 3.39° | 3.05° | 0.00° (stuck) |
| turn-hold ratio, 8 / 15 / 30 m/s | 1.00 / 1.01 / 1.00 | 1.00 / 1.01 / 0.99 | **0.80 / 0.44 / 0.64 (FAILS ≥0.90)** |
| tracking tg 0.2 / tg 0.5 Hz, 17 m/s | 0.81 / 0.29 | 0.85 / 0.37 | 0.42 / 0.33 |
| override-latch overshoot, 3 m/s (light+firm hand) | 0.69° | 0.38° | **−4.50°** |
| engage ramp-in / sentinel excursion | 0.0° everywhere (A2) | 0.0° | 0.0° |
| 5–30 Hz texture (hunt as HF proxy), highway | ≤ 0.23° | ≤ 0.19° | 0.00° |

**bc plant (b_lo + friction ×2 at ≥10 m/s; EVIDENCE `_bcquick.py`, 4 speeds × 7 scenarios):**

| metric | B1 | B2 (proxy) | B3 |
|---|---|---|---|
| dj @3 / stick% @3 | 7 / 72 % | 6 / 67 % | 0 / **100 %** |
| stick% @12.5 | 47 % | 40 % | **64 %** |
| turn-hold @19 m/s | 0.99 | 0.99 | **0.49** |
| tg 0.2 @12.5 / @19 | 0.96 / 0.86 | 0.98 / 0.88 | 0.53 / 0.46 |
| ov_latch @3 | 0.28° | 0.08° | **−4.46°** |
| sentinel | 0.0 | 0.0 | 0.0 |

**Reading (EVIDENCE):**
- **B1 / B2 meet turn-hold (0.99–1.01) and keep the sentinel at 0.0° (A2).** Their low-speed stick-slip is *not*
  eliminated — hunt 2.8–3.4° at 3 m/s, dwell-then-jump 6–8 per set — that is the integrator winding through stiction,
  the **pre-declared M1** (the goal's "low-speed stick-slip gone" is a miss for both; no cal/structure in this class
  removes it — see `accord-calibration-cannot-eliminate-the-ratchet`). B2 is consistently a touch better than B1 on
  dwell-then-jump (28 vs 32) and override overshoot (0.38 vs 0.69° @3), and the real fresh D lowers HF texture further.
- **B3 trades the dwell-then-jump for a dead zone and a hold failure.** dj = 0 (no integrator to ratchet), *but*
  stick 100 % at 3 m/s and 64 % at 12.5 m/s (bc) — the wheel does not move for small corrections — and turn-hold
  collapses to 0.44–0.80 (it cannot hold a steady angle without an integrator; the fork's τ_o ≥ 1 s integral must carry
  it, and it is forbidden < 8 m/s). **B3's override-latch overshoot is −4.5° at 3 m/s** on both plants — a large,
  safety-relevant release transient that B1/B2's frozen integrator avoids. **B3 fails the goal's turn-hold and
  low-speed criteria in the time domain**, consistent with its frequency-domain tracking failure (§3.3).

---

## 5. Shared method, the gate, and what a FAIL looks like (written before the runs)

- **Credible set:** `c1r2_members` TIER_A (PM≥45) + TIER_B (PM≥30), 0.25 m/s grid incl. plant knots 3.1/8.0/11.9/17.0/
  26.9, hold ages 1–20 on every tier-B member (`+h10`). `b_q` = b×0.25 at ≥12.5 m/s (floor 3.46); `b_lo` = b/1.8 ≥10,
  ×0.7 below; `tau6` = 6 ms transport; J refits 0.5/0.8/1.0 from p5c. The combined members the brief named
  (`b_q×J_hi`, `b_q×J1.0`, `b_q×tau6`, aged combined) are all present and all gated (EVIDENCE `c1r2_members.selfcheck`).
- **GATE 2 PASS** (per implementation, 9 660 pts): tier-A PM≥45 & GM≥6 & stable; tier-B PM≥30 & GM≥6 & stable;
  no closed-loop \|T\| peak > +3 dB in 5–30 Hz; Re(T/ω)₂₀ ≤ V295's at age 0 and 10. All three **PASS**.
- **FAIL ⇒ do not flash:** any gated PM below its bar; GM < 6; ρ ≥ 1 (right monodromy per impl); \|T\|₅₋₃₀ > +3 dB;
  Re(T/ω)₂₀ > V295; the built-image cave not decoding as designed (H5); B2's D sign wrong (H-sign); any CRC (H8).
  The pass structurally *can* return "do not flash": B3's naive monodromy ρ=1.0 and ideal-fresh Kd 28 env=0 are two
  cases where the gate did fire and forced a correction.

---

## 6. Concerns and open items
1. **Everything above ~8 Hz is model, not measurement** (the plant is unidentified there) — the 20 Hz rule, the 13 Hz
   ratios and B2's fresh-D advantage all rest on the loop model, not a measured plant FRF.
2. **B2's whole advantage rests on one unverified number** — `gp-0x6abe`'s EMA corner. Closable with one trace
   (the writer `FUN_00041464`'s accumulator shift). Until then B2's margin win is EVIDENCE-in-model / BELIEF-on-plant.
3. **The goal tracking pass rests on one route's spectrum** (r71b) and the ±0.028 positive control; B1's 17–22 m/s
   margin (0.002–0.03) is inside that accuracy.
4. **GhidraMCP dropped mid-session** — the in-place decodes are cited from C1 §1.1 (dry-run-verified there) and the
   byte values re-read in Python; the cave and B2's E5 sign must be Ghidra-decoded on the built image before flash.
5. **Friction/safety lenses not independently refuted here** — this is the designer's own evidence; an adversarial pass
   on each built image (arithmetic / unit-scale / build-script / interlocks) with "do not flash" reachable is required
   before any flight, per the kit's close-out contract.
