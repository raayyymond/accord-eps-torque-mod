# V294 — the LKAS PID design space, byte-verified (V295 census)

**Agent:** `census` (subagent of the V295 orchestrator), 2026-09-30. **Study only** — nothing built, flashed or
sent; no firmware artifact, fork, STATE, memory or lineage file touched; no commit. Scripts beside this file;
regenerable outputs in `_scratch/out/` (gitignored). Every decision-bearing claim is **[E]** EVIDENCE (method
named) or **[B]** BELIEF. FAIL/surprise criteria: `CRITERIA.md` (⚠ written after the first reads — see its note;
the sha256 asserts and the 23 scanner controls were pre-committed in code).

---

## 0. Headline — what the design agent needs first

1. **[E] V294 is exactly what the record says, and nothing else.** sha256 `3143616d…dbdd85` (c1). Its code
   region `[0x13000, 0xC0000)` differs from V293 and from V282 in **exactly two bytes, `0x28FA4` and
   `0x29D76`** (Python full-range diff, c1). The Ghidra program `/advC/_v294_…` holds the same bytes at the two
   edits and at `0xC63E0–0xC63EF` (`read_memory` vs file) — not a stale import.
2. **[E] My integer mirror of the V294 listing and the golden model's `lkas_rate_pid_tick` agree on 80,000 of
   80,000 ticks** — V294 as built, and with Ki 64, with Kd 128 / D-clamp 10240, and with Ki 8 + Kd 64 made
   live (`c3_pid_mirror.py`, `golden_crosscheck`). The golden model is a correct mirror of the PID for the
   design agent to search with — with one structural caveat, item 6.
3. **[E] THE I TERM ON V294 integrates E>>5 of the post-shift error, E = 4·sp − r26** (decompile lines 977–992
   AND listing `0x29D76 shl 2` → `0x29D78 sub` → `0x29D7C sar 5` → deadband → `0x29DA8 mul Ki`). Because
   Σ r26 telescopes to the lag state, **a non-zero Ki is an integrator of the COMMAND minus a proportional term
   in the lagged wheel RATE**: `S_I ≈ (Ki/32768)·(4·Σsp − 348.9·Δω_f)` (ω_f in deg/s). In a steady curve (hold
   command, wheel still) it **ramps the torque without bound until its clamp** — Ki 64 at idx 58: T 598 → 860
   in 1 s, rail (2239) at 6.1 s (c3, marched on the exact tick). No leak, no freeze on saturation or under
   driver torque, reset only at the `0x2A164` epilogue — which does not run until the engage ramp has fallen
   to 0 (0.1 / 0.5 / 2.05 s after the disengage request, by arm). **It is the lever the operator rejected on
   V283 on principle** (*"it goes against what openpilot is modelling its output as, a torque"*, 2026-09-04).
4. **[E] THE D TERM ON V294 is, in practice, a command-rate feedforward.** Its feedback half (−Kd/8·Δr26) is
   4.4·10⁻⁵·Kd S-counts per deg/s³ — Kd 128 gives 0.0009 T per deg/s³, ~2 T at a 10 deg/s, 2.5 Hz wheel
   oscillation. Its setpoint half is a one-tick kick Kd·Δsp/2 on every 100 Hz command step; through the 5 Hz
   output lag that averages to **+30 T at the 123-count/frame slew cap for Kd 128** (c3). No kick at engage
   (the `0x7FFFFFFF` E_prev sentinel zeroes dE on the first tick).
5. **[E] Every loop value that shapes the acceleration trim is CAL-ONLY** — the fb pole `a` 0xC63E8, gain `b`
   0xC63EA, clamp `C` 0xC62E6, the Kp bank, the map, the output lag 0xC63EC/0xC63EE, Ki/deadband/I-clamp,
   Kd/D-clamp, the tapers. Private to FUN_00028ea6 (+ the uncalled twin island) by Ghidra **and** a
   positive-controlled raw scan. **Only three things need code:** the FF multiplier independent of Kp·b in
   powers of two (the `shl` at 0x29D76, one in-place opcode), the operand type (0x28FA4, one opcode), and
   anything with a second operand, a speed schedule, D-on-measurement, or a conditional/leaky integrator
   (a cave). Section 7.
6. **[E] CORRECTION — the post-PID "override taper" is on DRIVER TORQUE, not speed.** Factor =
   `((F1·F2) & 0xFFFF) >> 8` with F1 ∈ {A 0xCBB54, B 0xCBC34} on gp-0x6830 (|Δ filtered bar|>>6) and
   F2 ∈ {C 0xCBAE4, D 0xCBBC4} on **gp-0x682f = min(|torsion bar>>5|, 254|255)**; the pair is chosen by
   `r25 = (gp-0x6803 == 2)` at `0x29A82`. With openpilot sending 0 in that 0xE4 field → **B×D: the whole LKAS
   sum (FF + trim + I + D) is derated to 179/255 at |bar>>5| = 48 and to 77/255 (×0.30) from |bar>>5| ≥ 64**.
   TRACE-2026-09-13-lkas-pid-tracked-quantity §2.4 ("C/D on speed") and the golden model's
   `override_taper_factor` docstring ("B a SPEED taper… DISPUTED") are wrong on the axis; the dispute is
   resolved (listing 0x29A74–0x29A82, 0x29C56, 0x2A000, 0x2A062; decompile lines 797/1142/1165).
7. **[E] Physical constants of the as-built trim** (c3, c6; x = 8 counts per deg/s per the V294 redo):
   FF **2.404 T per sp count = 10.34 T per idx = 0.641 T per wire count**; K_α **0.210 T per deg/s² below the
   2.03 Hz pole**; the trim at 2.5 Hz is **1.82 T per deg/s damping + 0.026 T per deg/s² inertia (13° from pure
   damping)**; one r26 count = **2.87 deg/s² = 0.60 T** (the trim's quantum); cap C = 1024 → **±615 T**, binding
   only above ~2935 deg/s² (below the pole) or ~231 deg/s (above it). Read as an acceleration servo, E = 0 at
   **α_ref = 11.46 deg/s² per sp count = 3.06 deg/s² per wire count**.
8. **[E] Frozen on every one of the 272 images on disk:** I deadband 4, I clamp 10240, P clamp 15360, sum clamp
   15360, output lag 992/507. Ki has been non-zero on three images (5 on V270/V271, 1 on V272 — unflown; **50 on
   V283 — flown and rejected**). Kd 128 on every image except V279/V293/V294 (0). (`c5_cross_build_matrix.py`.)

---

## 1. Provenance and method

| item | value / method |
|---|---|
| images | stock `code.bin` `3f1d55a9…`, V282 `0ea98d06…`, V293 `f75e77cf…`, V294 `3143616d…` (c1 asserts) |
| Ghidra | V294: `/advC/_v294_…` (55 functions, FUN_00028ea6 body 0x28EA6–0x2A30D, **decompiled first**, then `disassemble_bytes dry_run:true` at 0x28F4C–0x28FE0, 0x29080–0x290E0, 0x29A40–0x29AB0, 0x29C40–0x2A0C6, 0x2A13E–0x2A2F0). Image-wide xrefs: the fully analysed stock `code.bin` (2090 fns, 184,512 instructions) — valid for V294 because the code region differs from stock only at 0x13109, 0x14120, 0x28FA4, 0x29D76, 0x2A1F0–1, 0x35A08–18, 0x3AA96, 0x454FE, 0x55C0E–11, 0x55DF2–0x55E11 (c1), none of which is a load of a PID cell (c2). Every `disassemble_bytes` used `dry_run:true`; one `run_analysis` was invoked on the V294 program (7 ms, 0 new functions — it has no seeded entries); **nothing saved**; the V294 program was left open alongside `code.bin`. |
| raw scan | `c2_reader_census.py`: 4-byte Format VII incl. the `ld.bu` bit-5 parity and `hw2` bit-0 discriminators, Format VIII bit ops (set1/clr1 writers), the 6-byte extended form, absolute LE32. **23/23 positive controls PASS** on V294 (incl. the odd-displacement `ld.bu -0x3d2c`, the 6-byte `gp-0x6752` at 0x48E56, and the `mov imm32 0xCB994`). Linear-sweep caveat: it decodes every even offset, so it can report a spurious mid-instruction hit (two found and adjudicated: `0xC05D5` "st.b" at 0x297BE and a `0xC6744` reader at 0x52E56 are halves of real instructions — Ghidra listing). Nulls are unaffected. |
| set-difference | Ghidra `search_instructions` (stock) = Python (stock) **exactly** for: `0x73e6` Ki (2), `0x72e4` deadband (7), `-0x6dd0` I state (4), `0x71ba/bc/b6/be/b8/b4/b2` (2/7/7/8/4/8/5), `0x73e2/e4/e8/ea/ec/ee/e0`, `-0x6809` (8 rd, 0 wr), `-0x3570` (3), `-0x680a` (2 rd), `-0x6b2c` (24), `-0x6b2e/30/32/34/36/38/3c`. No disagreement to adjudicate. |
| mirror | `c3_pid_mirror.py`: every line annotated with its instruction; every cal READ FROM THE IMAGE (`read_cal`), incl. the `shl` immediate and the add/subr opcode. |

---

## 2. The loop on one page — V294, byte-exact (abridged from `c3_pid_mirror.py`)

```python
# ---- demand (0x29A74..0x29D72) ---------------------------------------------------- per tick, 1 kHz
cmd  = clamp(-4*wire, ±0x4000)                     # 0x0E4 handler -> gp-0x69ae            [INHERITED E]
cmd  = clamp(cmd, ±LERP(0xCB844 rec, speed))       # 16384 flat on V282+  -> inert
bar5 = min(|bar>>5|, 254) or 255                   # gp-0x682f (0x29068)
if [0xC64B8]=255 < bar5: prod = 0                  # 0x29A78/0x29A88 driver cut -- never fires on V282+ (255)
G    = LERP(0xCB924 | 0xCB8B4, bar5)               # same-sign | opposite-sign arm (0x29A8E..); 0xCBA74/0xCBA04 if gp-0x6803==2
act  = LERP(0xC6976.., gp-0x6830)                  # 255 flat, all images
prod = (((G*act) & 0xFFFF) * cmd) >> 16            # 0x29CB4 mulu ; 0x29CB8 andi ; 0x29CBC mul ; 0x29CC0 sar 16
v    = prod >> 6 ; sgn = -1 if v < 0 else 1        # 0x29CD6 sar 6 ; 0x29CD8 cmovn
idx  = |clamp(v, -[0xC64F1], +[0xC64F0])|         # 240/240 ; byte ; st.b gp-0x674b (the 427 tap's idx)
sp   = sgn * LERP(0xC9A88 rec, idx)                # 0x29D6C mulh (16x16 SIGNED) ; st.h gp-0x6a32 @0x29D72
# ---- feedback former (0x28F4C..0x28FBE, runs EVERY tick, engaged or not) -----------------------------
s_old = s if sentinel==1 else 0                    # gp-0x3d30 / gp-0x3d2c (both boot 0, .data)
s_new = ((a*s_old)>>10) + ((b*x)>>10)              # a=[0xC63E8] ld.h 1011 ; b=[0xC63EA] ld.hu 567 ; x = gp-0x6a56
r26   = clamp(s_new - s_old, ±[0xC62E6])           # 0x28FA4 SUBR (V294) ; C = 1024 ; s := s_new @0x28FA8
# ---- PID (0x29D76..0x2A162; runs iff (ramp gp-0x69b0 != 0 or gp-0x6805 == 1) and no filter bail) ----
E   = (sp << 2) - r26                              # 0x29D76 shl 2 (5 on every other image) ; 0x29D78 sub
e5  = E >> 5 ; exc = e5-4 if e5>4 else (e5+4 if e5<-4 else 0)      # 0x29D7C ; deadband [0xC62E4]=4
I   = clamp((I8>>3) + ((exc*Ki)>>3), ±((10240<<10)>>3)) ; I8 = I<<3 # Ki [0xC63E6]=0 ; clamp [0xC61BA] ; gp-0x6dd0
P   = clamp((E*Kp)>>8, ±15360)                     # Kp LERP(0xCB994 rec, idx) = 960 flat ; 0x29E36/3E ; [0xC61BC]
dE  = E - (E_prev if |E_prev| <= 768000 else E)    # 0x29E5E..0x29E7E ; E_prev gp-0x6cf8 (0x7FFFFFFF after skip)
D   = clamp((dE*Kd)>>3, ±[0xC61B6])                # Kd LERP(0xCB7D4 rec, idx) = 0 ; D clamp 0 on V294
raw = (I>>7) + P + D                               # 0x29F18 sar 7 (I) ; 0x29F1E +P ; 0x29F24 +D
S   = clamp((raw * (((F1*F2)&0xFFFF)>>8)) >> 8, ±15360)   # taper B x D at rest = 254 ; [0xC61BE]
# ---- output lag + delivery (0x2A174..0x2A23C, runs on BOTH paths) -------------------------------------
L_new = ((992*L)>>10) + ((S*507)>>10) ; y = (L + L_new)>>5 ; L = L_new   # [0xC63EC] ld.h, [0xC63EE] ; gp-0x3d3c
yr  = 0 if gate else sxh((y*ramp)>>15)             # gate armed only ramping DOWN: [0xC64A3]=1, |y|<=[0xC61B8]=102 or sign flip
T   = clamp(((0 + yr) * pol * 5346) >> 15, ±3072)  # addend gp-0x6b2c == 0 ; gain 0xC6CD0 ; [0xC61B4] ; st.h gp-0x6b38
```

---

## 3. The census, item by item (values read from the four images; readers = V294 image, both methods)

Legend — **per-variant**: a 28-pointer bank, stride 4, record = LE32 at bank + 4·7 (live selector 7), 28
distinct record pointers on every bank (c1); **global**: one scalar in the 0xC6xxx page. "twin" = the uncalled
island 0x2A30E–0x2B421 (zero callers, ghidrafill 2026-09-13).

### (1) Demand map: cmd 0xE4 → idx → sp

| cell | read as | stock / V282 / V293 / V294 | arithmetic, range | readers | scope |
|---|---|---|---|---|---|
| LIM 0xCB844 → rec 0xE51A8 (9 knots, on speed) | u16 | 15360 flat / 16384 ×3 | clamp(cmd, ±LIM); cmd ≤ 0x4000 anyway → **inert** on V282+ | mov imm32 @0x28FCC (+twin) | per-variant |
| G same-sign 0xCB924 → 0xE52FC | u16 | X [32,42,80,112] Y [255,255,255,0] ×4 | G·act & 0xFFFF — **wraps if G·act > 65535** (G ≤ 257 at act 255) | @0x29B0C | per-variant |
| G opp-sign 0xCB8B4 → 0xE5284 | u16 | X [32,38,80,112] Y [255,255,255,0] ×4 | idx → 0 as driver torque |bar>>5| goes 80 → 112 | @0x29BE8 | per-variant |
| G override 0xCBA74 / 0xCBA04 | u16 | X [70,72,78,80] Y [254,234,12,0] ×4 | only if gp-0x6803 == 2 (the 0xE4 field openpilot sends as 0 — memory) | @0x29AA4 / 0x29B80 | per-variant |
| activity 0xC6976.. (4 knots, gp-0x6830) | u16 | Y 255 flat ×4 | ×255 | @0x29C5E (+twin) | global |
| idx clamp 0xC64F0 / 0xC64F1 | u8 | 240 / 240 ×4 | idx is a BYTE (zxb, st.b) — ≤ 255 | 0x29CD0/CE0 / 0x29CE6/CF0 (+twin) | global |
| driver cut 0xC64B8 | u8 | **112** / 255 / 255 / 255 | cut if gp-0x682f > cell; 255 = never. Also read at 0x2920A/0x2921C (engage state machine) | 3 live + 3 twin | global |
| **assist map 0xC9A88 → rec 0xE502C** | u16, via **mulh 16×16 signed** | stock Y [0,24,42,50,62,100,126,154,166,172]; V282/93/94 **[0,52,86,103,138,275,413,550,688,1032]** (linear 4.30/idx) | sp = sgn·LERP(idx). **Y must stay ≤ 32767** (mulh sign). 10 knots, X [0,12,…,240] — count fixed by code offsets | @0x29CFC (+twin 0x2ABF4) | per-variant (3 distinct Y over 28) |

**Scale [E]:** idx = |(65025·cmd) >> 22| (two floors) → **16.12573 wire counts per idx LSB** = 2²²/(4·65025)
(re-derived from the listing; matches the record's 16.125736). idx saturates at |wire| ≈ 3870.
**[E] L/R asymmetry (new):** the two `sar`s floor toward −∞, so for a POSITIVE wire (negative cmd) idx =
⌈w/16.13⌉ and for a negative wire ⌊w/16.13⌋ — they differ on 3870 of 3899 wire values; **+1 wire count already
gives idx 1 (sp −4, T ≈ −10), −1..−16 give 0**. A ±½-idx (≈ ±5 T) offset and a one-sided 16-count deadband in
the demand. Stock behaviour, unchanged by any build.

### (2) Feedback former

| cell | read as | stock / V282 / V293 / V294 | arithmetic, range | readers | scope |
|---|---|---|---|---|---|
| x = gp-0x6a56 | s16 | — | pol·((raw·48·[0xC613A]=1159)>>15), saturated ±12000 by FUN_0003f776 (4 writers + lockstep mirror gp-0x4ca6); 8 counts per deg/s **[E, V294 redo]** | 25 rd / 4 wr image-wide; ONE read in the PID (0x28F4C) | — |
| **a 0xC63E8** | **s16 (ld.h)** | 923 / 923 / 923 / **1011** | pole −ln(a/1024)/2πTs = **2.03 Hz**; must stay ≤ 1023 (a = 1024 is an integrator), ≤ 32767 (sign) | **1** (0x28F8A); 0 writers | global |
| **b 0xC63EA** | u16 (ld.hu) | 1560 / 1560 / 1560 / **567** | DC of s = b/(1024−a) = 43.6 per x-count; r26 = 8·Ts·DC·α_f = **0.349 counts per deg/s²** below the pole, **8b/1024 = 4.43 counts per deg/s** above it. **Overflow:** a·b·12000/(1024−a) < 2³¹ (the state at the |x| = 12000 bail edge) — 4.06× margin as built; **b ≤ 2301 at a = 1011, ≤ 1231 at a = 1017** (b_max = 2³¹·(1024−a)/(12000·a); c3 grid) | **1** (0x28F86) | global |
| **C 0xC62E6** | u16 | 7680 / 46080 / 0 / **1024** | clamp on r26; trim authority C·Kp/256 = 3840 S = **615 T** | **3**, all in the filter | global |
| state gp-0x3d30 | s32 | boots 0 | s = s_new; **not** reset by 0x2A164 | 1 ld / 1 st, both in the filter | — |
| sentinel gp-0x3d2c | u8 | boots 0 | 1 normal, 2 after a bail → next tick s := 0 (the restart pulse, r26 = (b·x)>>10, ≤ C) | 1 / 1 | — |
| **code 0x28FA4** | opcode | `add r9,r26` (c9d1) ×271 images / **`subr r9,r26` (89d1)** V294 only | sum (≈ 2× lagged rate) vs difference (lagged acceleration) | — | — |
| **code 0x29D76** | opcode | `shl 5` ×271 / **`shl 2`** V294 only | E = sp·2ⁿ − r26: the FF multiplier | — | — |

Bails (0x28F3C bar implausible, 0x28F48 pol ∉ {−1,0,1}, 0x28F5A |x| > 12000, 0x28F62 pol == 0) → r26 := 0,
r25 := 0 → the PID is skipped that tick (I reset, E_prev poisoned). **[E] the difference operand settles to
exactly 0 at any constant x; floors give ≤ 1-count dither** (golden-model self-check + c3).

### (3) P: Kp bank, >>8, P clamp

| cell | read as | stock / V282 / V293 / V294 | arithmetic, range | readers | scope |
|---|---|---|---|---|---|
| **Kp 0xCB994 → rec 0xE5378** (5 knots, X = idx [0,68,112,136,208]) | u16 (zxh) | [248,512,645,696,696] / [248]×5 / [120]×5 / **[960]×5, all 28 records** | P = (E·Kp)>>8 | mov imm32 @0x29DC6 (+twin 0x2ACBA) | per-variant |
| **P clamp 0xC61BC** | u16 (ld.hu ×4) | 15360 ×4 (all 272 images) | P rails at \|E\| ≥ 4096: at r26 = 0 from **idx ≈ 238**; with r26 at −C the assisting side clips from **idx ≈ 179** | 4 live (0x29E3A/44/4A/58) + 3 twin | global |

**[E] Overflow:** |E|·Kp < 2³¹ — |E| ≤ 4·1032 + C = 5152 at C = 1024, so **any u16 Kp is safe**; only a C
near 65535 with a large Kp could overflow (|E|·Kp = 4.6·10⁹). **The Kp schedule is on idx only** — no speed axis.

### (4) THE I TERM, in full

| cell | read as | value (all four) | where |
|---|---|---|---|
| **Ki 0xC63E6** | u16 (ld.hu) | **0** (non-zero on disk: 5 V270/V271, 1 V272, **50 V283 — flown, rejected**) | 0x29D9C (+twin 0x2AC8E); 0 writers |
| deadband 0xC62E4 | u16 | 4 (272/272 images) | 0x29D6E/84/8C/96 (+3 twin) |
| I clamp 0xC61BA | u16 | 10240 (272/272) | 0x29DA0: ICL = (v<<10)>>3 = 1,310,720; I>>7 ≤ v = 10240 S = **1641 T** |
| accumulator gp-0x6dd0 | s32, holds **8·I** | boots 0 | ld.w 0x29DA4, st.w 0x2A190 (+twin 2); nothing else reads it |

**Arithmetic [E, listing 0x29D7A–0x29DE4]:** `e5 = E>>5`; `exc = e5∓4` outside ±4, else 0; `I = clamp((I8>>3) +
((exc·Ki)>>3), ±ICL)`; `I8 := I<<3`; the sum gets `I>>7` (0x29F18). Per tick the sum's I part moves by
Ki·exc/1024 → **dT_I/dt ≈ 0.157·Ki·(E/32 − 4) T-counts per second** at rest taper.

**Leak / decay / conditional integration — [E] none.** `(I8>>3)<<3` is exact (|8·I| ≤ 1.07·10⁷ ≪ 2³¹ for any
cell value). The I integrates on every tick the PID runs — **regardless of the P clamp, the sum clamp, the lane
clamp, the driver-torque taper (so it WINDS UP while the driver overrides and the output is cut to ×0.30) or
the ramp.** The only anti-windup is its own clamp. **Reset** = `0x2A190 st.w r24` with r24 = 0 on the
`0x2A164` epilogue (and the unreachable 0x2A0C6 lane), taken when (ramp gp-0x69b0 == 0 and gp-0x6805 != 1) or
on a filter bail. The PID keeps running through the ramp-DOWN, so **the I survives a disengage request by the
ramp-down time: 328/tick → 0.1 s, 66/tick → 0.5 s, 16/tick → 2.05 s** (cells 0xC63F4/FA/F6, decompile lines
378–459) — V283 measured 139–383 counts still delivered 0.5–1.0 s after STEER_REQUEST dropped.

**Floor asymmetries [E, c3]:** (i) the dead band is **[−128, +159]** in E (e5 floors), (ii) `(exc·Ki)>>3` floors:
at |E| = 200 for 1 s, Ki 1 → +0 / −1000; Ki 8 → +2000 / −3000. **A negative bias of ~1 exc-count per tick
regardless of Ki** — Ki a multiple of 8 removes (ii) but not (i).

**Resolution on V294 [E]:** `shl 2` made E 8× smaller for the same sp, so E>>5 = sp/8 − r26/32: **one I
input LSB = 8 sp counts ≈ 1.9 idx ≈ 30 wire counts = 92 deg/s² of α-error**, and the dead band 4 = **|sp| < 40
(idx < 9.3, |wire| < ~150) or |α-error| < 367–456 deg/s²**. On stock the same dead band was 4 sp counts.

**What a non-zero Ki does on V294 [E for the arithmetic, B for the closed loop]:** Σ E = 4·Σ sp − Σ r26 and
Σ r26 telescopes to (s − s_reset) = 348.9·(ω_f − ω_f,reset). So

    S_I ≈ (Ki/32768) · [ 4·Σ_ticks sp  −  348.9 · Δω_f(deg/s) ]         (above the dead band, below the clamp)
        = an integrator of the command  +  a lagged-RATE damper of −0.0017·Ki T per deg/s

i.e. it integrates the **acceleration error** (α_ref − α_f), whose integral is a **rate error against a rate
reference equal to the integral of the command**. In a steady curve the fork's torque controller holds a
non-zero hold command with the wheel still, so **the I ramps the torque to its clamp** (c3: Ki 64 at idx 58 —
T 598 → 860 @1 s → 2239 @6 s; Ki 256 at idx 120 — rail in 0.7 s). In closed loop the only equilibrium is
|E>>5| ≤ 4, i.e. **the fork's command collapses to |wire| ≲ 150 with the I carrying the hold torque** — the EPS
becomes an integrating actuator in series with the fork's own integrator (Ki 0.3). The damper half cannot be
had without the integrator half: matching the trim's 1.8 T per deg/s would need Ki ≈ 1050, at which the
command integrator adds the whole FF in ~0.12 s. **Consequence for the design: Ki on the V294 operand is only
coherent if the fork's command semantics change to "desired acceleration, zero in a steady curve" and the EPS I
learns the hold torque.** The V283 record (Ki 50 on V282's rate operand) is the flown precedent: consistent
oversteer, tight-curve achieved/asked 1.278, rejected. With I (or D) live the rail rises from 2461 (P clamp
binding) to **2481** (sum clamp binding) — +0.8 %.

### (5) THE D TERM, in full

| cell | read as | stock / V282 / V293 / V294 | where |
|---|---|---|---|
| **Kd 0xCB7D4 → rec 0xE511C** (4 knots, X = idx [0,11,22,32] — **unschedulable above idx 32**) | u16 (zxh) | [128]×4 / [128]×4 / [0]×4 / [0]×4 (all 28 records) | mov imm32 @0x29E76 (+twin) — per-variant |
| **D clamp 0xC61B6** | u16 (ld.hu ×4) | 10240 / 10240 / **0 / 0** (2560 V287r1, 7680 V287r2) | 0x29EE8/EF2/EF8/F02 + 3 twin — global |
| E_prev gp-0x6cf8 | s32 | window ±768,000 (code literals 0x29E62/0x29E68, not a cal) | ld.w 0x29E5E, st.w 0x2A18C (+twin) |

**Arithmetic [E, 0x29E5E–0x29F06]:** dE = E − E_prev (E_prev replaced by E when outside the window — only the
0x7FFFFFFF sentinel written by every skip is outside, so **the first tick after (re)engage has dE = 0: no
engage kick**). D = clamp((dE·Kd)>>3, ±Dclamp) on the FULL error. **No filter on D** (the 5 Hz output lag is
the only smoothing). On V294 dE = 4·Δsp − Δr26:
- **setpoint kick** Kd·Δsp/2 on the one tick in ten the command changes; at the 123-count/frame slew cap
  (Δidx ≈ 7) that is 15.5·Kd S for one tick — Kd 128: 1984 S, delivered **+30 T mean during a max-slew ramp**;
  Kd 512: 7936 S, +99 T (the sum clamp starts to bind at high idx). This is a **command-rate feedforward**,
  T_D ≈ 2.1·10⁻⁵·Kd T per (wire count/s).
- **jerk feedback** −(Kd/8)·Δr26 = **−4.4·10⁻⁵·Kd S per deg/s³** below the pole (Kd 128 → 0.0009 T per deg/s³),
  plus a ±Kd/8 per-tick dither from r26's integer steps. Negligible at any Kd that keeps the kicks sane; the
  redo's "anti-damps below 3.2 Hz" is a phase statement about a term this small.
- Overflow: |dE|·Kd ≤ 2·5152·65535 = 6.8·10⁸ < 2³¹ at C = 1024 — safe for any u16 Kd.

### (6) Sum, taper, sum clamp, output lag, lane clamps

| cell | read as | value (all four unless noted) | arithmetic, range | readers |
|---|---|---|---|---|
| taper B 0xCBC34 → 0xE56F4 (gp-0x6830 axis) | u16 | X [0,3,6,8,10,20] Y [255×5, 205] | F1 | @0x29F78 (per-variant) |
| **taper D 0xCBBC4 → 0xE564C (gp-0x682f = \|bar>>5\| axis)** | u16 | X [16,26,38,48,64,96] Y [255,243,218,179,77,77] | F2: **the live driver-torque derate** of FF + trim + I + D | @0x2A04A (per-variant) |
| taper A 0xCBB54 / C 0xCBAE4 | u16 | A = B; C X [24,45,64,80,96,112] Y [255,205,164,125,90,51] | only when gp-0x6803 == 2 | per-variant |
| taper product | — | ((F1·F2) & 0xFFFF)>>8 = **254 at rest** | **wraps if F1·F2 > 65535** (a Y > 257) | 0x2A0B4–0x2A0C2 |
| **sum clamp 0xC61BE** | ld.hu compare / **ld.h assign** | 15360 (272/272) | **never above 32767** (latent sign defect 0x2A142/0x2A146) | 4 live + 4 twin |
| **output-lag a 0xC63EC** | **s16 (ld.h)** | **992** (272/272) | pole 5.05 Hz; ≤ 1023 | **1** (0x2A184) + 1 twin |
| **output-lag b 0xC63EE** | u16 | **507** (272/272) | DC = 2b/((1024−a)·32) = 0.990 | **1** (0x2A174) + 1 twin |
| state gp-0x3d3c | s32 | — | runs on BOTH paths (decays after a skip); not reset | 1/1 + twin |
| output gate 0xC64A3 / 0xC61B8 | u8 / s16 | 1 / 102 | only while ramping DOWN (gp-0x6806 == 0): yr = 0 if \|y\| ≤ 102 or y·yr_prev ≤ 0 | 1+1 / 2+2 |
| forward gain 0xC6CD0 (via the V57 displacement 0x2A1F0) | s16 | −1 (stock reads 0xC646C = 891) / 5346 ×3 | T = (yr·pol·gain)>>15 | 1 |
| **lane clamp 0xC61B4** | ld.hu / **ld.h** assign | 512 / 3072 ×3 | T → gp-0x6b38 (the 427 tap); **never above 32767** | 4 + 4 twin |
| **forward clamp 0xC61B2** | ld.hu / **ld.h** @0x2B436 | 512 / 3072 ×3 | gp-0x6b3c (gated copy, 0x2A2EA) → clamp → gp-0x6b3a + the request struct to FUN_00025c32 (FUN_0002b422) → aggregator | 4 in FUN_0002b422 + 1 monitor (FUN_0002b57a) |

**The output lag IS a cal pair [E]:** 0xC63EC/0xC63EE, private (1 live + 1 twin reader each), never changed on
any of 272 images. It sits after the sum, so it lags the FF and the trim alike (−22° at 2 Hz, −45° at 5 Hz as
built) and is what turns D kicks into a smooth derivative. c6 grid: 960/1014 (10.3 Hz) raises the trim's
2.5 Hz magnitude 1.86 → 2.02 T per deg/s but moves its phase +13° → +25°, so the added part is inertia — the
damping component stays ~1.8 T per deg/s; 1000/380 (3.8 Hz) the other way (1.73 at +6°). DC must be re-held
by b (b ≈ 15.84·(1024 − a)). The FF sees the same lag.

### (7) Sibling lanes at the motor (FUN_0003aa2c, not the PID)

[E, decompile of the V294 program] gp-0x6b94 = clamp(Σ, ±0x2800) of gp-0x6b4c (the LKAS lane, via FUN_0002b422 →
FUN_00025c32 → FUN_00026c80), the base assist (FUN_00036682), gp-0x6ad4 (driver-torque tracking PID), gp-0x6b62,
gp-0x6ade, gp-0x6b26, gp-0x6bbe, gp-0x6bd0, gp-0x6b86 and two bar-derivative lanes, **all at unit weight** (plus a
lockstep shadow gp-0x4ce0). The two lanes use the operand clamp(gp-0x4f62, ±5120) (torsion-bar derivative):
- **r24 lane → gp-0x6ada:** deadband((op·arm)>>10, ±[0xC61F6]=3), ×pol, ±0x2000. arm = LERP(speed) disengaged;
  **[0xC6446] when gp-0x6806 != 0 (engaged): stock 512 / V282 5244 / V293-V294 2048**; [0xC6442] = 1024 when the
  gp-0x671d first-strike latch is set.
- **r26 lane → gp-0x6adc:** ((avg(gp-0x69a4)·op)>>10)·arm>>10, arm [0xC6444] = 512 engaged ([0xC643E] = 1536
  disengaged-high-activity), zeroed when gp-0x6b5e != 0 and gp-0x671a < [0xC64FA] = 5.
They add to the LKAS lane at the motor; no PID cell feeds them and they read no PID cell.

### (8) Everything else FUN_00028ea6 reads (complete tp-relative census, c4: 59 cells + 12 bank bases)

- **Damper mode gp-0x680a == 1 → 0x2A0C6** (−sign(r26)·LERP(|r26>>5|) over 0xC6712–0xC6730): **unreachable** —
  2 readers, 0 writers (Ghidra = Python), boots 0 (.data 0x868A6). On V294 its operand gp-0x6a34 = |r26>>5| is 0…32.
- **Dither addend gp-0x6b2c** (state machine gp-0x3d37, period cells 0xC6288/0xC628A/0xC64DE, enable gp-0x6809):
  **≡ 0 by two independent facts [E]** — its LERP Y 0xC673E–0xC6744 = [0,0,0,0] on all four images, and the
  enable gp-0x6809 has **0 writers image-wide** (Ghidra 8 rd = Python 8 rd) and boots 0 (.data 0x868A7). This
  upgrades the golden model's "identically zero (inherited)" to EVIDENCE.
- **Engagement/ramp cells** (gate the loop, are not loop values): 0xC62E8/0xC62EA speed window, 0xC63F2 cmd-valid,
  ramp steps 0xC63F4 (328) / 0xC63F6 (16) / 0xC63F8 (33 up) / 0xC63FA (66) / 0xC63FC (328 up), the override/
  engage state machine 0xC64B4–B7 (stock 112/96/54/64 → **255 on V282+**), 0xC61C0/C2/C4 (stock 1600/896/1280 →
  **65535 on V282+**), 0xC64DF/E0/E1/E2. The V282-era 255/65535 values disable the stock driver-override exits.
- **Published scale factors gp-0x697e / gp-0x697c** = 1024 − ((1024 − cal)·ramp>>15) with cals 0xC63DA/DC/DE/E0
  = 1024 on all four → constant 1024 (unity); consumed as fields of the FUN_0002b422 request struct. Inert.
- Polarity gp-0x6752 (±1, never 0): multiplies x at the producer and T at the output — cancels in the loop.
- Published PID cells gp-0x6b2e (S), gp-0x6b32 (P), gp-0x6b34 (raw sum), gp-0x6b36 (D): **zero live readers**
  (gp-0x6b2e one twin reader). There is no published I cell. **Nothing on the wire can observe I or D directly**
  — the 427 tap and the 0x14A cave read gp-0x6b38 (T). An I/D build needs its own instrument.

### (9) Interlocks a larger trim / I / D could newly reach

- **Soft-EME integrator gp-0x3570 [E topology, B consequence]:** 3 accesses, all in the shaper FUN_00042af8
  (Ghidra = Python). It integrates the excess of the **post-governor total command** gp-0x6b08 over a bound,
  `I += (cmd − bound)<<15`, clamp ±[0xC61DC]=30720<<15, authority (|I>>15|·[0xC61DA]=1092)>>10 (decompile lines
  647–703). The LKAS lane reaches it only through T (±3072 by 0xC61B4, ±3072 again by 0xC61B2, aggregator
  ±0x2800). **No PID value can raise the lane's peak; I and D change its DWELL.** Inherited from
  ADV-V293-D (not re-derived): bound = max(corridor, IIR, boost floor 5120), SM2 arms at |I>>15| ≥ 15361, the
  5120 < |cmd| ≤ 5325 band needs ~75 ms residency, exists on V282 too. An I term that holds the lane near
  its rail through a long curve is the configuration that makes that residency likelier.
- **Forward-lane monitor FUN_0002b57a** (record 0x434E): compares gp-0x6b3a with ±[0xC61B2] ± 0.003 — gp-0x6b3a is
  already clamped to ±[0xC61B2] at 0x2B42A–0x2B45C, so no PID value can trip it [E structure, B semantics].
- **fb operand plausibility:** the |x| ≤ 12000 bail (0x28F50) and the producer's saturation + lockstep pair
  gp-0x6a56/gp-0x4ca6 (FUN_0003f776 only; the PID writes neither).
- **Aggregator lockstep** gp-0x6b94/gp-0x4ce0 (FUN_0003aa2c → FUN_0006b9fa on disagreement); FUN_0004595a
  instantaneous |gp-0x6b94| vs |gp-0x6ace| comparator (inherited, 2026-09-13 trace).
- **No monitor reads any PID internal** (I, E_prev, P/D/S published cells, the fb or output-lag states) — c2.

---

## 4. What each knob PHYSICALLY does in the acceleration loop (c6, exact linear 1 kHz transfer functions)

Controller response **T/ω** (T counts per deg/s of wheel rate) and the phase of the opposing torque
(0° = pure damping, +90° = pure inertia, −90° = spring-like). No plant — the closed loop needs J, k(v), b(v),
delay, which are **[B]** (fork identification).

| setting | 0.3 Hz | 1 Hz | 2 Hz | 2.5 Hz | 3 Hz | 5 Hz | 10 Hz | 20 Hz |
|---|---|---|---|---|---|---|---|---|
| **V294 (a 1011, b 567, Kp 960)** | 0.39 +78° | 1.16 +53° | 1.75 +24° | **1.86 +13°** | 1.91 +3° | 1.76 −23° | 1.18 −52° | 0.65 −70° |
| a 1017, b 567 (1.1 Hz) | 0.71 +71° | 1.77 +36° | 2.18 +7° | 2.19 −3° | 2.16 −11° | 1.86 −32° | 1.20 −57° | 0.65 −73° |
| a 993, b 567 (4.9 Hz) | 0.17 +83° | 0.53 +67° | 0.95 +46° | 1.10 +37° | 1.22 +28° | 1.37 0° | 1.09 −37° | 0.64 −62° |
| a 993, b 1352 (same K_α) | 0.39 +83° | 1.27 +67° | 2.27 +46° | 2.63 +37° | 2.90 +28° | 3.28 0° | 2.61 −37° | 1.53 −62° |
| b 1134 (×2) | 0.78 +78° | 2.32 +53° | 3.49 +24° | 3.73 +13° | 3.81 +3° | 3.53 −23° | 2.37 −52° | 1.30 −70° |
| out-lag 960/1014 (10.3 Hz) | 0.39 +80° | 1.18 +58° | 1.84 +34° | 2.02 +25° | 2.13 +18° | 2.23 −4° | 1.88 −33° | 1.22 −57° |

- **K_α — the loop gain (b · Kp).** Below the pole T = −K_α·α with **K_α = (Kp/256)·8·Ts·b/(1024−a)·0.1603 =
  0.210 T per deg/s² as built**; above it T → −(Kp/256)·(8b/1024)·0.1603·ω = 2.66 T per deg/s before the output
  lag (the table's 1.9 at 3 Hz and 0.65 at 20 Hz include it).
  `b` scales the feedback ONLY. `Kp` scales feedback AND feedforward (one multiply). K_α/J = 1.0 at the
  record's J (**[B]**) means the wheel sees twice its inertia below 1 Hz — the loop tracks α_ref only at
  α/α_ref = K_α/(J + K_α) ≈ 0.5 there; a tighter acceleration servo needs K_α/J ≫ 1, i.e. b ×N, bounded by
  **overflow (b ≤ ~2250 at a 1011)**, by the trim cap C, and by loop stability through the output lag and the
  ms-level delay (redo: |L| 1.1–1.2 as built, 180° crossing 19–24 Hz).
- **The lag pole `a`** sets where the operand turns from acceleration (inertia) to rate (damping): holding b,
  lowering the pole raises the low-frequency inertia gain ∝ 1/(1024−a) and moves the damping peak down; the
  high-frequency damping (8b/1024) is independent of a. Holding K_α (b ∝ 1024−a) while raising the pole makes
  the trim MORE inertia-like at 2–3 Hz (+37° at 4.9 Hz vs +13°) and much larger above 5 Hz.
- **The trim cap C** bounds r26 → ±C·Kp/256 S. Scale-free; as built it binds only far outside the measured
  operating range. It also bounds the restart pulse after every filter bail.
- **FF level.** FF = (Kp/256)·2ⁿ·map(idx) (n = the shl). With n fixed by code, holding FF while changing Kp
  requires re-scaling the **map Y** (per-variant, cal-only, ≤ 32767) or accepting an FF change. Holding FF and
  changing the trim is simply `b`.
- **I** — section 3(4): integrates acceleration error = rate error against the integrated command; winds up on
  any held command; dead band ±~40 sp; resolution 92 deg/s².
- **D** — section 3(5): command-rate feedforward (kick) + negligible jerk feedback; unschedulable above idx 32.

---

## 5. THE DESIGN SPACE, plainly

**CAL-ONLY (no code byte; page CRCs only)**
- fb former: **a 0xC63E8** (≤1023), **b 0xC63EA** (overflow bound above), **C 0xC62E6** — global.
- **Kp bank** (5 knots on idx, 28 records), **Kd bank** (4 knots on idx ≤ 32), **map** (10 knots, Y ≤ 32767) — per-variant.
- **Ki 0xC63E6, dead band 0xC62E4, I clamp 0xC61BA** — global.
- **D clamp 0xC61B6, P clamp 0xC61BC** (u16), **sum clamp 0xC61BE, lane clamp 0xC61B4, forward clamp 0xC61B2** (each
  ≤ 32767 — ld.h assign), forward gain 0xC6CD0.
- **Output lag 0xC63EC (≤1023, signed) / 0xC63EE** — global, never moved on any image.
- Tapers A–D and G banks (driver-torque shaping), idx clamps (byte), output gate.
- Knot COUNTS are fixed by code offsets (X/Y values free; X non-decreasing; the walk cannot divide by zero).

**ONE IN-PLACE OPCODE (same length, the V57/V104/V294 class)**
- `0x29D76 shl imm5` — FF multiplier 2ⁿ independent of Kp·b (and the I input resolution).
- `0x28FA4 add/subr` — operand: lagged rate (sum) vs lagged acceleration (difference).
- The shift immediates: `0x29D7C sar 5` (I input scale — e.g. `sar 2` restores the stock I resolution per sp
  on V294), `0x29E3E sar 8` (P), `0x29EEC sar 3` (D), `0x29F18 sar 7` (I into the sum), `0x2A0BC`/`0x2A0C2
  sar 8` (taper). (The accumulator's storage pair `0x29DB0 sar 3` / `0x29DE4 shl 3` must stay matched.)
- `0x29A80 cmp 0x2` / `0x29A82 setfe r25` — which taper/G arm is live.

**NEEDS A CAVE**
- Any **speed schedule** of the trim, the pole or Kp (every PID bank is on idx; the fb/out-lag cells are
  scalars) — relevant to the redo's low-speed ζ× 0.89 finding.
- **Two operands at once** (rate damping + acceleration inertia with independent gains; the filter yields one r26).
- **D on measurement only** (no setpoint kick): dE is formed on the full error at 0x29EE2.
- **Conditional / leaky integration** (freeze on P/sum/lane saturation or under driver torque, leak, reset at
  the disengage request instead of at ramp end) or an I on the measured side only.
- Extra filters (notch, second pole) — V289's 0x2A174 hook is the precedent; finer x resolution — V292's cave.
- **An instrument for I or D** (no cell of theirs has a reader; a 427-source repoint or a 0x14A bit is code).

---

## 6. Corrections / additions to the record (reports — nothing edited)

1. **Taper axis** — C/D are on gp-0x682f (|bar>>5|), not speed; selector r25 = (gp-0x6803 == 2) @0x29A82; live =
   B×D. Affects TRACE-2026-09-13-lkas-pid-tracked-quantity §2.4 / §7.4 and the golden model's
   `override_taper_factor` docstring (whose default 254 is right at rest).
2. **Golden-model address erratum:** `e5 = E >> 5  # 0x29D6C sar 0x5` — the sar is at **0x29D7C**; 0x29D6C is
   `mulh r13,r16` (sp = sign·map). Arithmetic unaffected (0/80,000 mismatches).
3. **Dither addend gp-0x6b2c ≡ 0 is now EVIDENCE** (LERP Y all zero + zero writers of the enable + boots 0).
4. **Rail with I or D live = 2481**, not 2461 (the sum clamp binds instead of the P clamp).
5. **Demand L/R asymmetry** (±½ idx, one-sided 16-count dead band) — stock arithmetic, not previously recorded here.
6. **I reset lags disengage by the ramp-down** (0.1 / 0.5 / 2.05 s by arm) — the mechanism behind V283's
   measured 0.5–1.0 s residual.
7. **V294's `shl 2` coarsened the I input 8×** (dead band 4 sp → 40 sp) — any Ki proposal on this base inherits it.

## 7. Not verified / BELIEF

- The 0x0E4 handler's `clamp(−4·wire, ±0x4000)` (inherited EVIDENCE, not re-derived); Ts = 1 ms
  (label↔byte consistency only); x = 8 counts per deg/s (the V294 redo's bytes + angle-derivative check).
- The plant (J, k(v), b(v), delays) — every closed-loop statement about ζ or tracking ratio is **[B]**.
- The soft-EME bound/band numbers (ADV-V293-D, inherited); FUN_0002b57a's semantics beyond its operands.
- Register-indirect writers of the gp flags (gp-0x6809, gp-0x680a) — excluded only by operand scans + .data boot
  values, the standing residual.
- The dead-twin island is uncalled by direct-call/constant evidence only (standing residual).
- I did not load a fully analysed V294 program; image-wide xrefs rest on the stock program + the byte-diff
  argument + the Python scan of the V294 image.

## Files

`c1_images_and_cells.py` (hashes, diffs, every cell ×4 images) · `c2_reader_census.py` (controlled reader
census) · `c3_pid_mirror.py` (byte-exact mirror + golden cross-check + I/D/fb/out-lag tables) ·
`c4_function_cal_census.py` (every cal FUN_00028ea6 reads) · `c5_cross_build_matrix.py` (PID cells down 272
images) · `c6_trim_response.py` (knob physics) · `CRITERIA.md` · outputs in `_scratch/out/`, decompiles in
`_scratch/`.
