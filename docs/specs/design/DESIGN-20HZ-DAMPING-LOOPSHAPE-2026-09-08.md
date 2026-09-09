# DESIGN — raising the damping of the 20 Hz mode by IN-LOOP filtering, with the P/D gains and the low-frequency loop gain held

Subagent `loopshape`, 2026-09-08. **DESIGN STUDY, NOT A BUILD.** Nothing built, flashed or sent; no build script edited.
Scripts: `rlog-tools/studies/grind/loopshape20_loop_model.py` (the loop model, the plant fits, every candidate row) and
`loopshape20_mode_nature.py` (the wire: line frequency vs state, free decays, closed-loop and plant transfers). Outputs in
`rlog-tools/studies/grind/_scratch/loopshape20_*.txt`. Image: V282 `_v282_…_plain_image.bin` (every cell below byte-read from it).
Tracer facts are from `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md` (agent `tracer`, relayed by `main`).
**EVIDENCE (with the method) or BELIEF on every decision-bearing claim.**

**Status: FINAL (2026-09-08 18:40).** §3's census landed after the first draft; every conditional below is resolved against it.

---

## 0. Headline

1. 🛑 **CORRECTION OF RECORD, decision-bearing.** The multiply at `0x2A1E6` is **the output lag's result × the engagement
   ramp `gp-0x69b0`** (Q15, = 1.0 engaged), not `lag_out × |q32(H_fb·rate)|`. The rectified fb magnitude at `0x28FC0–C6` goes
   to `gp-0x6a34` and one gated side lane; it never reaches the torque path. [EVIDENCE — tracer decompile + register census, five
   older tracer memories, and the chain mirror's 4–14 % tap match, which no |fb| multiplier could survive at 10 deg/s.]
   ⇒ `GRIND1-LOOP-SHAPE-V287` headline 10 / A2 / B4 struck the fb pole `0xC63E8/EA` as "a gain lever, not a phase lever" on a
   misidentified instruction. **The fb pole is a linear phase element in the loop and is back in the ranking.**
2. 🛑 **The record's "PM 35–60°, Ms 2–3" is inconsistent with the wire and the reason is identified.** Every measured free decay
   of the 20 Hz ring gives **ζ_eff 0.02–0.09** (V282 r39 marks 0.020/0.090, r35 0.031, V288 marks 0.034/0.049; a 2nd-order-like
   pole with ζ 0.035 has PM ≈ 3.5° and |S|max ≈ 14). The record's plant phase (−28° @10 Hz, −73° @22 Hz) was read from the tap
   **without removing the 3.9 ms inter-stream offset creep20 itself measured**; that offset is **+28° of spurious lead at 20 Hz**
   (+31° at 22). Remove it and the loop at 20.3 Hz sits at **|L| 0.8–0.95, ∠L −170…−185°** — a vector margin of 0.08–0.25, i.e.
   ζ 0.03–0.10. **The record's margins are an artefact of that offset.** [EVIDENCE for the arithmetic; the offset's *cause*
   (stream skew vs an unmodelled physical delay) is open, but it enters the loop phase either way — see §4.]
3. **The electronics alone contribute −72.6° of return-ratio phase at 20.3 Hz** (fb one-pole −47.3°, fb two-sample sum −3.7°,
   PID +61.6° lead, output lag −72.4°, its two-sample sum −3.7°, one tick of latency −7.3°) and **1.74 T counts per raw rate
   count** (creep20 measured 1.88 at the line). The plant must supply ≈ −105 ± 10° for the measured near-critical point.
   **The output lag (−72°) and the fb pole (−47°) are the two dominant lags; the D term is the only lead.** [EVIDENCE, byte-exact]
4. 🛑 **MODE NATURE, from the wire (§3): a PLANT MODE that the loop DE-DAMPS — not the loop's own −180° crossing.** Five builds
   put the line at 20.03–20.08 Hz; Kp 287 → 696 (−26° of controller phase, ×1.5 loop gain) moves it **+0.4 Hz, the wrong sign and a
   tenth of the size** a −180°-limited smooth loop requires, while ζ falls 0.036 → 0.019 without instability. Extrapolated, the mode's
   own damping with the loop open is **ζp ≈ 0.05** and today's loop spends ≈ 30 % of it. [EVIDENCE for the classification.]
   ⇒ On that plant the verdicts are: **a notch at the mode on the PID sum removes the loop's action there** (min|1+L| 0.27–0.46 →
   0.58–0.61, Ms 3.8/2.2 → 1.7/1.6, closed-loop ζ 0.019 → 0.032 on the census-fitted plant; no new pole below — |L| at 13–16 Hz is
   0.3–0.4, so the V105 relocation does not occur here); **every lead (fb pole, output-lag pole, explicit lead) is worse or unstable
   alone**; a D-filter helps on one fit and hurts on another (not robust, and a Kd cut above 15 Hz in disguise).
   The smooth-plant branch — where *no* gain-preserving filter helps and a notch relocates the ring to 15 Hz — is **falsified by §3**,
   and its rows are kept in §5a only so the 14–17 Hz FAIL branch of the pre-registration is written down.
5. **What the model already excludes regardless of plant:** the output-lag pole to 10/15 Hz (`0xC63EC/EE`) — unstable or Ms ≤ 1.3
   with GM 0.5–0.7 on the smooth plant, |dL| 43–62 % below 5 Hz, +16–23° at openpilot's 3.9 Hz crossover; and every lead
   compensator on the PID sum. **Both are struck here, on the same waterbed the V287 study measured.**
6. **RANKING (robust across the three mode-plant fits; §5b):**
   **(1) the PAIR — notch 20.05 Hz Q 3 on the PID sum (cave, hook `0x2A174`) + fb pole 16.5 → 25 Hz (`0xC63E8/EA` 923/1560 →
   875/2301, cal-only).** The only row neutral on every gate: 7 Hz gate 1.005 (today 1.003), openpilot's 3.9 Hz +0.6°, loop gain
   below 5 Hz within 2 %, capped-step peak rate/accel ×1.00/×1.00, min|1+L| 0.49–0.69, Ms 1.4–2.0. Its one cost is the fb pole's
   ×1.3 loop gain at 25–50 Hz (×1.48 rms noise into D) — guarded by the existing 26–33 / 2–6 statistic.
   **(2) the notch alone, Q 3 on the PID sum** — the cleaner physics (it also removes the D kick's 20 Hz content from the forward
   path), no HF cost, but it **fails the kit's 7 Hz gate on its own** (1.079: −8° on the servo arm at 7.3 Hz re-arms the strong-turn
   ring at the record's |L_tot| 0.976) and costs −3.8° at 3.9 Hz; capped-step peak rate ×0.92 / accel ×0.93 (the ring's own overshoot
   removed, DC unchanged). **(3) the notch alone at Q 4** (gate 1.060, 3.9 Hz −2.9°, ζ 0.022, Ms 2.0) if the 7 Hz gate's 6 % is
   judged inside its own 0.941–0.990 measurement spread (C5.2 of the V287 doc). **The fb pole ALONE is struck**: its verdict flips
   between fits (Ms 1.4 on one, 36 on another) — a blind dose. Output-lag pole, leads: struck on every plant.
   **What the operator should expect if (1) is right: not a cure.** The mode keeps its own ζp ≈ 0.05; the loop stops eating 30 %
   of it. A rung ring decays ≈ 1.7× faster (e-fold ≈ 3 cycles instead of 5, a 1 s grind becomes ≈ 0.5 s) and the *sustained* rings
   (V288 mark 2, held up by capped frames) should stop being sustained. He should feel the grinding **shorter and rarer, not gone**;
   if he feels nothing different, the loop's share of the damping was smaller than 30 % and the residual is the plant's.

---

## 1. The loop, from the bytes (integer mirror, instruction-anchored)

```python
# 1 kHz tick.  x = gp-0x6a56 = -(0x18F wire rate), 8 raw counts per deg/s (measured).  All cells V282 = stock unless noted.
def fb_step(s, x):                       # 0x28F86..0x28FA8 ; a = 0xC63E8 = 923, b = 0xC63EA = 1560
    s_new = (923*s >> 10) + (1560*x >> 10)       # sar 0xa, arithmetic
    r26   = clamp(s + s_new, ±46080)             # add r9,r26 @0x28FA4 = the TWO-SAMPLE SUM ; clamp 0xC62E6 (46080, V276+)
    return s_new, r26                            # DC of r26: 2*1560/101 = 30.89 per raw count
E   = 32*sp - r26                        # 0x29D76 shl 5 ; 0x29D78 sub r26,r16   (V288 filters sp before this; feedback untouched)
P   = clamp(E*248 >> 8, ±15360)          # Kp flat 248 (V281r3+), clamp 0xC61BC
D   = clamp((E - E_prev)*128 >> 3, ±10240)   # 0x29EE2 sub r27,r8 ; 0x29EE4 mul ; sar 3 ; clamp 0xC61B6.  dE is the FULL error difference (tracer Q9)
S   = clamp(254*(P + D) >> 8, ±15360)    # fade 254 hands-off ; clamp 0xC61BE
def lag_step(t, S):                      # 0x2A174..0x2A1B0 ; a2 = 0xC63EC = 992, b2 = 0xC63EE = 507 ; runs EVERY tick, S = 0 disengaged
    t_new = (992*t >> 10) + (S*507 >> 10)
    return t_new, (t + t_new) >> 5               # sar 5 @0x2A1AC -> DC 2*507/32/32 = 0.990
y   = lag_out * ramp >> 15               # 0x2A1E6 mul r14,r9 ; ramp = gp-0x69b0 = 0x8000 engaged  (NOT |fb|: correction §0.1)
T   = clamp(-(-1)*y*5346 >> 15, ±3072)   # gp-0x6752 = -1, K6 = 0xC6CD0 = 5346 ; st.h -0x6b38 @0x2A23C = the 427 tap
```

z-domain, T = 1 ms: `F = (1560/1024)(1+z⁻¹)/(1−(923/1024)z⁻¹)` · `C = 248/256 + 16(1−z⁻¹)` · `Hlag = (507/1024)(1+z⁻¹)/(1−(992/1024)z⁻¹)/32`
· return ratio `R = F·C·(254/256)·Hlag·(5346/32768)·z⁻¹` (T counts per raw rate count); loop `L = R·8·G`, G = deg/s per T count,
**negative feedback** (the two −1s cancel; no extra inversion — the convention the 2026-09-04 defect note fixed).

**Phase budget at 20.3 Hz, electronics only** [EVIDENCE — byte-exact z-domain; `loopshape20_loop_model.txt` §1]:

| element | \|·\| | phase |
|---|---|---|
| fb one-pole (a = 923, 16.53 Hz) | 6.405 | **−47.3°** |
| fb two-sample sum (1+z⁻¹) | 1.996 | −3.7° |
| PID C = Kp/256 + Kd/8·(1−z⁻¹) | 2.313 | **+61.6°** |
| output-lag one-pole (a2 = 992, 5.05 Hz) | 7.735 | **−72.4°** |
| output-lag (1+z⁻¹) | 1.996 | −3.7° |
| one tick compute latency z⁻¹ | 1.000 | −7.3° |
| **return ratio R(20.3)** | **1.742 /count** | **−72.6°** |
| creep20 measured T/rate at the line | 1.88 /count | −111° raw, ≈ −83° with 3.9 ms removed |

Kp dilutes the D lead: R's phase is −72.6° (Kp 248), −76.9° (300), −88.3° (470), −98.7° (696), |R| ×1.51 at 696. [EVIDENCE]

**Tracer facts used below** [EVIDENCE, relayed]: the output lag is inside the rate loop on the forward path (every tick, on the
clamped sum); `r26` is callee-saved with zero readers/writers between its clamp and `0x29D78`; the cleanest feedback-side hook
is the existing V288 cave entry at `0xC4C00` (r16 = sp and r26 = fb both live there); `0x29EE4` is a 4-byte `jr` swap site for a
D-path filter (r10 scratch, `lp` live → `jr` only); free flash 1048 B at `0xC4BD8+` minus V288's 82 B; **free RAM censused to the
full standard: `gp-0x6ab0..6aaa` (2 words), `gp-0x68b0..68aa` (2 words), `gp-0x6c44..6c3a` (3 words)** — enough for a biquad.

---

## 2. What the wire measures about the pole (before the census)

| measurement | value | source |
|---|---|---|
| line frequency, all builds V278r3 → V288 | 19.8–21.0 Hz; V282 20.05 ± 1.03, V288 marks 20.2–20.4 | census, marks read |
| free-decay ζ_eff (bar envelope after the peak) | 0.020 / 0.090 (r39 m1/m2), 0.031 (r35), 0.034 / 0.003 / 0.049 (V288 m1–3; m2 was still being driven) | marks read §3 |
| presence vs Kp(idx) on V280r2 | 13 % (idx 0) → 42 % → 83 % (idx 20–60) → 73 % | creep20 §3 |
| V280r2 (Kp LERP) → V281r3 (Kp flat 248) | line 3.5× less often, 2.5× smaller | r35 read |
| f vs idx on V280r2 | +0.6 Hz over idx 11–240 (ρ +0.13, p 0.005) | creep20 §2 |
| off-line plant \|G\| ×10⁻³ deg/s per count, raw phase | 42.9/−35° (10 Hz), 41.4/−42° (15), 54.5/−56° (18), 52.8/−69° (20), 34.8/−65° (22) | creep20 §1.1 |
| tap-vs-rate stream offset | 3.9 ms (T_meas trails the byte-exact mirror by +23…+33° at 20 Hz on every window) | creep20 §1.0 |

**A ζ of 0.02–0.05 is not compatible with PM 35–60° under any loop shape**: a pole that rings for 10–25 cycles has |S|max ≳ 10. The
free decays are direct measurements of the closed-loop pole (upper bounds on ζ, since excitation can only prolong them). [EVIDENCE]

---

## 3. Mode nature from the wire — VERDICT: a PLANT MODE the loop DE-DAMPS, not the loop's own crossing

`loopshape20_mode_nature.txt`: 9 routes, 5 builds, 6,254 s engaged, 12,500 census windows, 2,537 line-present, 529 episodes.
Pre-registered discriminators and the readings [EVIDENCE for every number; the mechanism column is the inference]:

| test | smooth plant, loop at its own −180° point predicts | plant mode the loop de-damps predicts | **measured** |
|---|---|---|---|
| f vs Kp on r31–r34 (Kp 287 → 696 = −26° of controller phase, \|R\| ×1.5) | pole moves **DOWN 2–4 Hz**; linearly **unstable above Kp ≈ 350** | pinned within ±0.5 Hz; ζ falls but stays > 0 | **f0 20.01 → 20.05 → 20.11 → 20.24 → 20.57 Hz** by Kp bin (240–300 … 600–700), +0.39 Hz over p10–p90, ρ +0.13 p < 0.001 — **UP, not down**; ζ p50 **0.036 → 0.020 → 0.019** (Kp 240–320 / 320–450 / 450–700), envelope peak 119 → 267 → 287, never unstable |
| the flat-Kp control (V281r3/V282/V288, Kp 248 at every idx) | — | — | f0 by idx bin **20.03 / 20.03 / 20.06 / 20.03** — dead flat (ρ +0.02, p 0.45) |
| f across builds | moves with the controller | pinned | **20.08 / 20.08 / 20.06 / 20.03 / 20.06** (V278r3 / V280r2 / V281r3 / V282 / V288 medians) |
| f vs hands, speed, angle, \|T\|, echo | — | a hand-wheel-side mode shifts with hands | hands-off 20.03, on > 700 19.96, hard > 1500 **19.80 [18.90–20.21]**; v 1–40 m/s 20.00–20.06; angle/\|T\|/echo: ρ ≤ 0.03 |
| free decays after the peak (509 of 529 episodes decay) | exponential, ζ ~0.03 | same | ζ p10/p50/p90 **0.003 / 0.027 / 0.085** on V282; V281r3 0.028; V280r2 0.022; V288 0.013; hands-off 0.025 vs hands-on 0.036 (n 15) |
| off-line plant \|G\| 18–21 Hz over 10–15 Hz (tap, native instants, coh 0.5–0.66 vs 0.26–0.37) | ≈ 1 | a bump | **×1.68 (V282), ×1.81 (r31–r34), ×1.14 (V288)** |
| plant phase with the 3.9 ms removed, 15–23 Hz | falls −4°/Hz (delay-like) | a step or a flat | **flat −85 … −100°** (V282: −85/−98/−101/−100/−96/−93/−100 at 15.6/18/18.8/20.3/21/22/22.7), then \|G\| drops ×2.4 at 24 Hz |
| bar/rate phase 15 → 26 Hz (same 0x18F frame, no timing risk) | smooth | a step between the two sensors | V282 **−26 … −63 (20 Hz) … −21, +3 (22.7), +119, +161** — a +180° step at 22–24 Hz on V282, V288 and V281r3 |
| command → rate / bar closed-loop fits, 15–26 Hz | ζ 0.03–0.1 | same | fn 20.0–22.8, ζ 0.07–0.30 at coherence 0.3–0.6 — **not decisive, as pre-registered** |

**Reading.** (1) Frequency is set by the plant: five builds, two controller-phase regimes and every operating state put the line at
20.03–20.08 Hz; the one lever that changes the controller's phase by −26° (Kp) moves it **+0.4 Hz**, the wrong sign and a tenth of the
size a −180°-limited smooth loop requires. (2) The loop *de-damps* that mode in proportion to its gain: ζ 0.036 → 0.019 for ×1.5,
without instability — extrapolated linearly the mode's own damping with the LKAS loop open is **ζp ≈ 0.05** (Q ≈ 10), and today's loop
at Kp 248 spends ≈ 30 % of it. That is also why stock (forward gain ×1/6) shows no line and why V281 rev 3's flat Kp cut the line 3.5×.
(3) The rate sensor sees the mode only weakly (a broad ×1.7 bump, no 180° swing in G) while the bar/rate ratio carries a +180° step at
22–24 Hz: the resonating degree of freedom is **mostly on the torsion-bar/hand-wheel side** and reaches the wheel-rate operand with a
small residue [BELIEF for the mechanics]. A weakly coupled mode is exactly what the loop can de-damp but not pin — consistent with (1)+(2).
**Mode nature: PLANT MODE, loop de-damped — EVIDENCE for the classification from (1) and (2); the smooth-plant near-critical picture
of §4's fit (i) is falsified by the Kp rows.**

---

## 4. The model, and the resolution of the PM inconsistency

Three plant families were fitted to (f_cl 20.3, ζ 0.035 at Kp 248), the off-line |G|/∠G at 10 and 15 Hz with the 3.9 ms offset
removed, the f-shift for Kp 248 → 696, and (in the constrained run) linear stability at Kp 696 (r31–r34 flew it with a bounded line).
`loopshape20_loop_model.txt` §2; the constrained/unconstrained pair is being re-run at draft time, numbers below are the first pass.

| family | fit | plant | closed loop at Kp 248 | Kp 470 / 696 | verdict |
|---|---|---|---|---|---|
| (i) smooth: g0 e^{−sτ}/(1+s/ω1) | 3.1 | g0 0.093, **τ 8 ms**, f1 20 Hz | f 19.9, **ζ 0.035**, Ms 12.5, PM 9° @18.7, **GM 1.10 @ 20.3** | **UNSTABLE (Nyquist) from Kp ≈ 350** | reproduces ζ; needs \|G\| 2× the off-line estimate at 10–15 Hz; predicts a friction-limited cycle on the LERP routes |
| (ii) resonant: × ωp²/(s²+2ζpωps+ωp²) | 9.9 | fp 21.5, **ζp 0.010**, τ 1 ms | f 20.4, ζ 0.044, Ms 2.2, conditionally stable (GM 0.35 @ 21.2) | ζ 0.023 / 0.016, stable | reproduces ζ and stability at 696; \|G\| 3× too small at 10–18 Hz; f shift −0.8 Hz (measured +0.5) |
| (iii) smooth + moderate mode | 23 | fp 22.5, ζp 0.05, τ 2 ms | f 21.5, ζ 0.026, Ms 3.1, GM 1.58 | stable; ζ 0.036 / 0.046 | \|G\| 4× too small |
| (iv) smooth × (1 + κ(M−1)), the census fit | 25 | fp 22.25, **ζp 0.040, κ 0.3**, τ 4 ms | f 21.5, **ζ 0.019, Ms 3.8, min\|1+L\| 0.27**, \|L(20)\| 0.50 ∠−153° | stable; ζ 0.023 / 0.027 | reproduces the small ζ, the stability and the broad bump; \|G\| 2× low at 10–18 Hz; f shift −1.0 Hz and ζ *rising* with Kp — **wrong signs** |

**No linear fit in these families reproduces all of the census at once** — in particular none gives ζ *falling* with Kp while f
*rises*. That is the expected signature of a mode whose coupling to the wheel-rate operand is not the simple residue these families
allow (§3 point 3: the resonating DOF is mostly on the bar side), and it is stated rather than papered over. **What is robust across
(ii)–(iv), and what the ranking rests on:** at the mode |L| is 0.5–1.0 at −150…−180°, |L| at 13–16 Hz is 0.3–0.4, and the loop's
share of the mode's damping is a minority — so removing the loop's action at the mode returns ζ to the plant's own, and adding lag
below the mode is harmless where it was fatal on the (falsified) smooth plant.

**Phase at 20.3 Hz under the smooth fit:** electronics −72.6°, plant −104° (8 ms delay −58°, 20 Hz pole −45°), ZOH −3.7° → **−180°,
|L| 0.91**. The resonant fit gets there with plant −77° and |L| 0.98 at ∠−153°, i.e. a PM-limited crossing at the mode's own peak.

**Resolution of the inconsistency [EVIDENCE for the arithmetic]:** creep20's `L_in = L_fw · G_raw` used the byte-exact controller
(no offset) times a plant read from streams that carry the 3.9 ms skew. Either the skew is a logging artefact (then G_raw has +28°
of spurious lead at 20 Hz) or it is a physical delay inside the loop (then L_fw is 28° short). **Both put the true loop 28° closer
to −180° than the record's −145…−158°, at |L| 0.8–1.0** — the "PM 35–60°" was never there. creep20 itself wrote that the corrected
phase "moves toward −173°" and set it aside as the at-the-line tautology; but the same correction applies 2 Hz off the line, where
the estimate is not tautological (coherence 0.4–0.8), and there the loop reads −166° (18 Hz) to −175° (22 Hz).

⚠ **What the linear model cannot decide alone:** the smooth fit says r31–r34 (Kp up to 696) were linearly unstable above idx ≈ 30
and the bounded 100–120-raw line they showed was a **Coulomb-friction-limited limit cycle** (consistent with 73–83 % presence and
the r34 t 336–342 window at idx 30 being the first to rail P). The resonant fit says they were stable with ζ 0.016–0.023. §3's
f-vs-Kp reading separates them: the smooth fit moves f **down** with Kp.

---

## 5. Candidates on the model — the full table is `loopshape20_loop_model.txt` §3; the decision rows

Legend: f/ζ = closed-loop pole; Ms = sensitivity peak; |dL|<5 = largest |ΔL/L| below 5 Hz (authority/LF loop gain); Δ3.9 = loop phase
change at openpilot's crossover; R73 = servo-arm ratio at 7.3 Hz and **gate73 = |Ls·R + Lr|** (LOOPSHAPE-LAGPOLE-KD §4, pooled
split Ls 0.55∠96° / Lr 1.19∠−27°; ≤ 1.000 passes; ratio only per the convention note); pkR/pkA = peak wheel rate / accel of the
linear closed-loop response to a capped-frame reference step (×1056 E counts) relative to as-built; noise = rms rate→D gain
30–500 Hz relative. Lineage of every cell is in §9.

### 5a. On the SMOOTH near-critical plant (fit (i))

| candidate | f / ζ | GM @ f180 | Ms | \|dL\|<5 | Δ3.9 | gate73 | noise | verdict |
|---|---|---|---|---|---|---|---|---|
| as-built V282 | 19.9 / 0.035 | 1.10 @ 20.3 | 12.5 | — | — | 1.003 | 1.00 | |
| (a) fb pole 25 Hz (875/2301) | 22.3 / 0.004 | 0.99 @ 22.3 | 103 | 10 % | +4.4° | 0.925 | 1.49 | **UNSTABLE / marginal** — lead +8°, gain ×1.3 at the new crossing |
| (a) fb pole 33 / 50 Hz | 23.8 / 0.021 · 25.9 / 0.034 | 0.95 · 0.91 | 19 · 11 | 15–20 % | +6.5…+8.8° | 0.885–0.843 | 1.9–2.8 | worse; the crossing moves up, |L| there rises |
| (b) lag pole 10 / 15 Hz (962/982 · 932/1458) | 24 / 0.14 · 26.9 / — | 0.67 · 0.53 | — | **43–62 %** | **+16…+23°** | 0.75 · 0.58 | 1.00 | **UNSTABLE**; also breaks the LF loop gain and the outer loop. STRUCK (agrees with V287 §3) |
| (c) D filter k=3 (21 Hz) · k=4 (10 Hz) | 16.8 / 0.07 · 15.2 / 0.08 | 0.80 · 0.78 | 4.8 · 4.3 | 10–19 % | −2…−5° | 1.083 · 1.175 | 0.22 · 0.11 | relocates the critical point to 15–17 Hz **and** fails the 7 Hz gate. A Kd cut above ~15 Hz in disguise |
| (d) notch fb or PID-sum, 20.3 Hz Q2/Q3/Q4 | 14.7–16.1 / 0.012–0.014 | 0.94–0.95 @ 14.6–16.0 | **19–23** | 7–13 % | −3…−6° | 1.06–1.11 | 1.00 | **relocates the ring to 15–16 Hz, sharper** — the V105 lesson; fails the 7 Hz gate |
| (e) lead z20/p60 · z14/p42 · z10/p30 | 24.5 / 0.015 · 25.6 / 0.045 · 26.2 / 0.10 | 1.04 · 0.88 · 0.74 | 30 · 8 · 3 | 14–30 % | +6…+13° | 0.89–0.77 | 1.00 | gain ×1.15–1.6 at the crossing: worse or unstable. STRUCK |
| (ref) Kd 128 → 96 | 18.2 / **0.088** | 1.27 @ 19.2 | 5.4 | 11 % | −5° | 1.073 | 0.75 | the only row that helps — **the gain-cut class the operator rejects**, and it fails the 7 Hz gate |

### 5b. On the MODE plants — the census fit (iv) first, fit (ii) in brackets where it differs

| candidate | f / ζ | min\|1+L\| | Ms | \|dL\|<5 | Δ3.9 | gate73 | pkR / pkA | noise | verdict |
|---|---|---|---|---|---|---|---|---|---|
| as-built V282 | 21.5 / **0.019** [20.4 / 0.044] | 0.27 [0.46] | 3.8 [2.2] | — | — | 1.003 | 1.00 / 1.00 | 1.00 | |
| **(f) notch Q3 + fb pole 25 Hz** | 22.5 / **0.024** [no peak] | **0.49 [0.69]** | **2.0 [1.4]** | **2 %** | **+0.6°** | **1.005** | **1.00 / 1.00** | 1.48 | **#1 — neutral on every gate; cost = HF gain into D** |
| **(d-out) notch PID-sum Q3** | 22.3 / **0.032** [mode removed] | **0.58 [0.61]** | **1.7 [1.6]** | 9 % (phase −5° at 5 Hz, gain −0.4 %) | −3.8° | **1.079** | 0.92 / 0.93 | 1.00 | **#2 — the physics; fails the 7 Hz gate alone** |
| (d-fb) notch fb Q3 | 22.3 / 0.032 | 0.58 | 1.7 | 9 % | −3.8° | 1.079 | 1.03 / 1.00 | 1.00 | same loop; the setpoint's 20 Hz kick still reaches the motor |
| (d) notch Q4 (sum or fb) | 22.3 / 0.022 | 0.49 | 2.0 | 7 % | −2.9° | 1.060 | 0.93 / 0.95 | 1.00 | **#3** — smaller 7 Hz cost, smaller benefit |
| (d) notch Q2 | 22.4 / — | 0.70 [0.10] | 1.4 [10] | 13 % | −5.8° | 1.115 | 0.91 / 0.90 | 1.00 | too wide at 7 Hz (−12°); unstable on fit (ii) |
| (a) fb pole 25 Hz alone | 21.7 / **0.002** [no peak] | **0.03 [0.71]** | **36 [1.4]** | 10 % | +4.4° | 0.925 | 1.00 / 1.00 | 1.49 | **verdict flips between fits — STRUCK ALONE (a blind dose)** |
| (a) fb pole 33 / 50 Hz alone | UNSTABLE [no peak] | | | 15–20 % | +6.5…+8.8° | 0.885–0.843 | | 1.9–2.8 | struck |
| (f) fb pole 25 Hz + D filter k3 | 20.9 / 0.036 | 0.30 | 3.3 | 11 % | +2.5° | 1.002 | 1.09 / 0.66 | 0.31 | a lag-to-lead swap; helps, gate-neutral, **but a Kd cut above 15 Hz in disguise** (\|Hd(20)\| 0.72) |
| (c) D filter k=3 · k=4 alone | 20.7 / 0.14 · 20.0 / 0.29 [0.009 · 0.042] | 0.49 · 0.64 [0.12 · 0.39] | 2.1 · 1.6 [8.6 · 2.5] | 10–19 % | −2…−5° | 1.083 · 1.175 | 1.12 / 0.66 · 0.61 | 0.22 · 0.11 | not robust across fits; fails the 7 Hz gate; a Kd cut in disguise |
| (b) lag pole 10 / 15 Hz, (e) every lead, (f) lag 10 + D k3 | UNSTABLE or Ms 43 | | | **21–62 %** | **+9…+23°** | 0.58–0.94 | | | STRUCK on every plant |
| (ref) Kd 96 | 21.5 / 0.040 [0.015] | 0.43 [0.28] | 2.3 [3.5] | 11 % | −5° | 1.073 | 0.94 / 0.78 | 0.75 | the rejected class; not better than the notch |

**Disguised gain cuts, flagged as the brief asked:** the D filter (c) halves the D term's action above ~15 Hz (|Hd(20)| 0.72 for
k = 3) while leaving it intact below 10 Hz — the operator would be right to read it as a frequency-dependent Kd cut; the notch (d)
is a gain cut **only inside ±3 Hz of 20.3 Hz** (|H| 0.93 at 13.5 Hz, 0.998 at 3.9 Hz, 1.000 at DC) and touches no P/D coefficient;
the fb-pole raise is not a gain cut at all (it *raises* loop gain above 16 Hz).

**What each top candidate does NOT touch:** Kp, Kd, the P/D/sum clamps (`0xC61BC/B6/BE`), the output clamp `0xC61B4`, the forward
gain `0xC6CD0`, the map, the fb clamp `0xC62E6`, the r24 lane (`0xC6446`), the DC gain of any filter (exactly 1 for the notch; the
fb pole is re-tuned to DC 30.891), the setpoint path (V288's cave, if kept).

---

## 6. GATE 2 — every loop the signal is in

- **The 7.3 Hz strong-turn ring** (model (b), ratio only): the notch Q3 rotates the servo arm −8° and scales it ×0.99 at 7.3 Hz →
  gate 1.079 (worse than today's 1.003 by 7.6 %); Q4 → 1.060; Q2 → 1.115. At today's |L_tot| 0.976 [0.944–0.990] that is
  **|L_tot| 1.05 [1.02–1.07] — the ring re-arms** unless paired with something that returns phase at 7 Hz. The fb pole 25 Hz gives
  R(7.3) = 1.05∠+8° → gate 0.925 (better); **the pair notch Q3 + fb 25 is 1.005 (neutral to 0.2 %)**. ⇒ **A bare notch of any Q
  fails GATE 2 at 7 Hz on the kit's own gate; only the paired form passes.** [EVIDENCE for the arithmetic; the gate's split and
  |L_tot| are the record's, BELIEF-grade as absolutes, ratio-grade as used here]
- **openpilot's outer loop (3.9 Hz):** notch Q3 −3.8° / |H| 0.998; fb 25 +4.4°; pair +0.6°. V288's pre-filter already spent ≈ 20°
  there; the pair spends nothing. The outer-loop PM has never been measured (standing open item).
- **The blind band (25–50 Hz):** the notch is unity there (|H| → 1 above ~30 Hz); the fb pole 25 Hz raises |R| ×1.3–1.5 at 25–50 Hz
  (×1.49 rms noise into D over 30–500 Hz), which under the smooth plant is exactly what moves the critical point up. **With the
  pair, the notch removes the 20 Hz problem and the fb pole's HF gain rise becomes the new exposure** — the 26–33 / 2–6 guard
  (P2 of the V287 pre-registration, route spread 1.25×) is the instrument for it.
- **The always-on base-assist loop:** untouched — every candidate lives inside `FUN_00028ea6`'s engaged-only rate PID; S = 0
  disengaged and the notch/filter state must be re-zeroed on the hook-skipping routes (V288 rev 1's FAIL, `gp-0x6cf8` sentinel).
- **Honda's oscillation-reversal detector** (`FUN_000428d4`, > 10 Hz reversals on `gp-0x6c2c`): a 20 Hz ring that persists is
  what feeds it; removing the ring cannot arm it. The fb pole's HF rise could, only if it creates a new persistent > 10 Hz
  reversal train — the V287 replay found that needs a sensitivity peak like the 10 Hz lag pole's (Ms > 100), not 1.4.

---

## 7. Authority — what the operator cares about

Linear closed-loop response of the wheel rate to a capped-frame reference step (33 sp counts = 1056 E counts), census fit (iv)
[fit (ii)]: as-built peak rate 1.00 / peak accel 1.00 / t90 19 ms; **the pair 1.00 / 1.00 / 19 ms** [1.27 / 0.91]; notch PID-sum Q3
0.92 / 0.93 / 24 ms [1.19 / 0.83]; notch fb Q3 1.03 / 1.00 / 19 ms; fb 25 alone 1.00 / 1.00. **Steady-state (DC) gain is unchanged to < 0.1 % in every row** (|dL| below
5 Hz: notch 9 %, fb 25 10 %, pair 2 %). The peak-accel dip of the notch is the ring's own overshoot being removed, not a slower
loop; the max rate a full-scale command reaches is set by the reference (map ceiling 1032 → ~134 deg/s at 6×) and the P/sum
clamps, none of which move. [EVIDENCE for the model rows; the map-ceiling statement is the record's.] The V62 counter-example
(a rate clamp) is a different class: it capped the reference; nothing here does.

---

## 8. The top two, instrumented

### 8.1 THE PAIR — notch on the PID sum, 20.05 Hz Q 3 (census centre: bar line 20.03–20.08, rate line 19.98–20.06), + fb pole 16.5 → 25 Hz (`0xC63E8/EA` 923/1560 → 875/2301)

Integer mirror (Direct Form I, Q14, 32-bit; what the cave would execute; checked against the float response on a 5–45 Hz chirp,
rms error 33 counts on a 3000-count signal):

```python
B = [16048, -31842, 16048]; A1, A2 = -31842, 15712        # RBJ notch f0 20.1 Hz, Q 3, fs 1 kHz, Q14 (recompute for 20.05); a0 = 16384 implied
def notch_tick(x, st):                                    # x = S (the clamped PID sum, ±15360) ; st = [x1, x2, y1, y2]
    acc = B[0]*x + B[1]*st[0] + B[2]*st[1] - A1*st[2] - A2*st[3]
    y = acc >> 14                                         # sar 14 floors; |acc| <= 16044*15360*4 = 9.9e8 < 2^31
    st[:] = [x, st[0], y, st[2]]
    return y                                              # DC gain exactly 1 (B sums to A)
```
Placement [EVIDENCE, tracer Q10–Q12, relayed]: the four paths that produce the clamped sum S (in r12) converge **exactly at
`0x2A174`** (`ld.hu 0x73ee,tp,r7`, bytes `e5 3f ef 73`, 4 bytes) — replace it with a 4-byte `jr` to the cave, filter r12 there,
and end the cave by replicating `r7 := 507` before returning to `0x2A178`. Live and untouchable across the site: r16, r22, r24,
r27, r29; free scratch r6, r7, r9, r13; `lp` live → `jr` only. The site runs **every tick**: the `0x2A164` disengage route arrives
with S = 0 (the notch state decays by itself), the `0x2A0C6` route arrives with an S from a LERP on `gp-0x6a34` that is **not
confirmed zero (open)** — so the state must either be re-zeroed on that route or the LERP shown to be 0 (the V288 rev 1 lesson,
Honda's `gp-0x6cf8` sentinel is the existing marker). State 4 words = the `gp-0x6c44..6c3a` run (3 words) + one word of a 2-word
run, or x1/x2 packed as halfwords. Cost ≈ 20–25 instructions ≈ 100 cycles ≈ 2.5 µs at 40 MHz, 0.25 % of the tick [BELIEF, tracer];
960 bytes free from `0xC4C30`. fb pole: two halfwords, cal-only, CRC recomputed. ⚠ Coefficient sensitivity: at Q14 the notch centre
quantises to ±0.05 Hz and the depth is set by the 1 LSB of (A2 − B0·…): assert the realised f0/Q from the integer coefficients,
not from the design values.

**Instrument (design law: a sign bit paired with a magnitude, or a comparator; no bare thresholds).** Spendable 0x14A byte-4
bits on a V282 base: **b4.5** (V282's |r24| ≥ |aggregator|, never used in an analysis), **b4.7** (sign of the 11-slot fault sum,
never used), **b4.3** (sign(gp-0x3680), unused); **b4.4** = sign(r24) and **b4.6** = |r24| ≥ |T| stay; **b4.0–2 are Honda's** and
must not be touched (V288 rev 1's FAIL). The notch's removed component `n = S − y` is the 20 Hz content of the PID sum:
- **b4.5 := sign(n)** — at 100 Hz a 20 Hz sinusoid gives 5 samples/cycle; its cross-spectrum with the 0x18F rate at the line
  reads the notch's centring (phase) and its duty ∈ (0,1) proves the rung executes;
- **b4.7 := |n| ≥ |y|** (comparator, scale-free) — duty = the fraction of ticks where the in-band content dominates the PID sum;
  it must rise inside a grind episode and sit near 0 in steady creep.
Positive control: b4.4/b4.6 keep their V282 duties (0.404 / 0.114–0.156). The 0x1AB tap (T = the lane after the notch) keeps
reading the delivered torque, and the byte-exact mirror with the notch inserted predicts it on every tick (Q1-style liveness).

**What the wire shows if it works, in one 20 s episode:** the 18–22 Hz line on the bar and the wheel rate at a bookmarked
turn-out is absent or decays at ζ ≥ 0.1 (free-decay fit, the same estimator as the V288 marks read) while b4.7 fires
(the excitation reached the notch); the 0x1AB tap's 18–22 Hz content falls ≥ ×0.5 against the mirror-without-notch; the 6–9 Hz
band at |ang| > 60° and the 26–33 / 2–6 guard stay inside V282's route spread (×1.09 / ×1.25).

**The sentence a null licenses:** *"b4.5 duty strictly inside (0,1) and b4.7 firing at the episode onsets proves the notch executed
on the 20 Hz content of the PID sum; if the bar/rate line at the bookmarks is unchanged in frequency and decay, the loop's own
action at 20.3 Hz is not what sustains the ring — the mode is rung and damped outside this loop (r24 / base assist / mechanics),
and the in-loop filter class for grind #1 is CLOSED."* **If instead a new line appears at 14–17 Hz, §3's plant verdict was wrong
(smooth plant), the notch relocated the critical point exactly as the model's 5a rows predict, and the build is reverted.**

### 8.2 The notch alone, Q 3 (or Q 4) on the PID sum — the fallback if the fb-pole half is refused

Same cave, no cal change, no HF cost (|H| → 1 above 30 Hz, noise into D ×1.00), DC 1. Predicted: ζ 0.019 → 0.032 (Q4: 0.022),
min|1+L| 0.27 → 0.58 (Q4 0.49), capped-step peak rate ×0.92 / accel ×0.93. **Its 7 Hz cost is the reason it is #2, not #1:** −8°
on the servo arm at 7.3 Hz → gate 1.079 (Q4: 1.060), which at the record's |L_tot| 0.976 [0.944–0.990] reads **1.05 [1.02–1.07]** —
the strong-turn ring re-arms on the kit's own gate. That gate's input is measured to 0.941–0.990 across poolings (V287 doc C5.2),
wider than the 6–8 % here, so the operator's own stutter report (Q11) is the real criterion; Q4 is the version to fly if the fb pole
is refused. Instrument identical to 8.1 (b4.5/b4.7 on the notch's removed component). **The fb pole alone is not offered**: its
predicted damping flips from "mode removed" to "Ms 36" between two plant fits that both match the census — a blind dose.

---

## 9. Lineage (grep of `analysis-2020accord/builds/*/build_v*_tva.py`, and the ledger's F-rows)

| cell / class | history | this proposal |
|---|---|---|
| `0xC63E8/EA` fb pole 923/1560 | referenced (asserted frozen) in V274–V288 scripts; **923/1560 in all 285 images — never moved** | (a): first move; the V287 doc's "gain lever" strike rests on the misread instruction (§0.1) |
| `0xC63EC/EE` output lag 992/507 | asserted frozen V274–V288; V287 rev 1's first pass chose 974/792 then withdrew it; **never flown** | struck here at 10/15 Hz (unstable on every plant); not proposed |
| `0xC61B6` D clamp | V287 rev 2 7680 flown, operator: "still felt the grinding" | not touched (invisible to the linear loop) |
| notch class | F61 V48B (biquad on the shared bar input, cave, BRICK — RAM collision + a resonator in the always-on loop); F67 V105 (25.5 Hz on the `gp-0x6b86` assist lane, relocated the mode 22.7 → 20.5); F68 V144–V241 notch on the same assist lane, NONE FLOWN, that lane's 18–22 share 4.6 % | **RE-RUN of the class in a DIFFERENT loop**: the LKAS rate PID's own path (79 % of the tap's 20 Hz), engaged-only, S = 0 disengaged (not the always-on loop), state in censused RAM, on a base whose 20 Hz line is now attributed to this loop by the census. The V105 relocation is exactly what the (falsified) smooth-plant rows predict; §3 rules that branch out, and the 14–17 Hz FAIL branch stays in the pre-registration |
| first-order filter on D / lead | F58 V43 `0xC644A` (a *different* D branch, Stage-C `FUN_0003a382`) falsified; no filter on this PID's D has ever flown | (c)/(e) struck here on the model, not proposed |
| in-body hook in `FUN_00028ea6` | V288 rev 2 is the first (`0x29D72` jr swap, flown 2026-09-08, cave live) | the notch would be the second; same technique |

---

## 10. What a tracer / the census still has to settle before anything is buildable

1. **§3's verdict** (this study's own script) — the plant nature decides between "notch + fb pole" and "no in-loop filter".
2. The **hook for the PID-sum notch**: a 4-byte swap between the sum clamp and `0x2A174` with `lp` not live, or chain from the
   fb-operand site at `0xC4C00` (then the notch is on r26, the forward path stays unfiltered — 5b's d-fb row).
3. **State re-zero on the three hook-skipping routes** and the engage-init tick (the V288 rev 1 FAIL class).
4. The **on-car register-indirect residual** on the chosen RAM run (GATE 1's live-probe requirement; V48B).
5. The 1 kHz task's cycle budget for a 5-multiply biquad per tick (unmeasured; the tracer's standing open item).

## 11. Files
`rlog-tools/studies/grind/loopshape20_loop_model.py` → `_scratch/loopshape20_loop_model.txt`, `…_unconstrained.txt`, `loopshape20_plants*.json` ·
`loopshape20_mode_nature.py` → `_scratch/loopshape20_mode_nature.txt`, `loopshape20_windows.npz`, `loopshape20_episodes.npz` · `_scratch/loopshape20_loop_model_final.txt` (the census-fitted run, families (i)–(iv)).
