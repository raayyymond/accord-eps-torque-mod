# ADVERSARY A — V289 rev 1 — ARITHMETIC surface — 2026-09-08

**VERDICT: PASS** against pre-registered §A (A1–A5) of `ADVERSARIAL-V289-PREREG-2026-09-08.md`. No FAIL criterion met. Six
residuals recorded below (none meets a criterion). Tool: `analysis-2020accord/verify/adv_v289_a_arith.py` — my own V850E2
decoder and exact-integer emulator, written without the builder's encoder/emulator; `python adv_v289_a_arith.py` reproduces every
number here in ~40 s. Image sha256 `f0c10c29…39a3ed` verified before every run.

Everything below is EVIDENCE from the built image bytes unless marked BELIEF. The one load-bearing BELIEF: the hook runs at
**fs = 1 kHz** (kit-wide belief, 0xC64DF=100 measured 100 ms). Every frequency in A1 scales with fs.

## Decisive numbers, per criterion

| crit | question | number that decides it | result |
|---|---|---|---|
| A1 | f0 from the integers within 0.3 Hz of 20.05 | zero of B(z) at acos(31842/32096) → **20.036 Hz** (Δ = −0.014 Hz) | pass |
| A1 | DC gain exactly 1 | ΣB/ΣA = 254/254; **22/22 constant-input runs settle to exactly X** (X ∈ {0, ±1, ±7, ±100, ±1000, ±15360}, zero and worst-case init) | pass |
| A1 | depth ≥ 20 dB | float 20.03/20.05/20.08 Hz: **−54.7 / −47.6 / −37.6 dB**; emulated 20.036 Hz sine A=100/3000/15000: −40.5 / −87.5 / −87.4 dB (floor is the ±3-count quantiser, not the filter) | pass |
| A2 | int32 wrap for \|S\| ≤ 15360, worst-case state | l1 bounds: \|s1\| 0.147·2³¹, \|s2\| 0.146·2³¹, \|acc\| 0.262·2³¹; worst-case sign sequences driven through the emulator AND a big-int shadow: **max intermediate 0.2908·2³¹** (the b1·n product at 0xC4C40), identical outputs from both → no wrap | pass |
| A3 | S = const settles exactly; S = 0 decays to 0 | exact settle in every run (slowest: 456 ticks from worst-case state); zero input from worst-case state: **s1 = s2 = 0 at tick 426, y = 0 exactly** (e residue stays at a constant 635 — sub-LSB, see R1) | pass |
| A4 | decode errors, displaced load | my decoder vs Ghidra on the imported v289 program: **61/61 instructions identical** (mnemonic, bytes, every gp/tp displacement, every branch target); `ld.hu 0x73ee,tp,r7` at 0xC4C84 replicated, r7 == 507 asserted on every emulated tick; FLAG truth table 4000/4000 ticks; tail 1536/1536 cases | pass |
| A5 | live-register / lp / jarl | cave writes **{r6, r7, r9, r12, r13}** only (static census); r11, r14, r15, r16, r22, r24, r27, r29, lp seeded with markers and asserted unchanged on every tick (>50 000 ticks); **no `jarl`** in the 172 new bytes; flags re-armed by `cmp 0x1,r16` @0x2A1AE before `bne` @0x2A1B4, no flag consumer in 0x2A178–0x2A1AC | pass |

## The brief's six attacks, answered

### 1. Independent decode vs Ghidra
Decoded from the image: hook `89 07 8c aa` = `jr` disp22 0x9AA8C → **0xC4C00** ✓; cave return `b6 07 f0 54` = disp −0x9AB10 →
**0x2A178** ✓; 0x14A exit `80 07 06 00` = `jr +6` → **0xC4BDC** ✓. All 61 instructions agree with Ghidra (programmatic compare in §[3]
of the script). My decoder initially tripped a real trap worth recording: **`ld.bu` (0x3C/0x3D) shares hw1 bits 10:6 = 11110 with
`jr`/`jarl`; the discriminator is hw2 bit 0** (1 = ld.bu, 0 = jr/jarl). A decoder without that check reads the tail's
`ld.bu -0x1514,gp,r6` as a `jarl` and returns a false A5 FAIL — the same family of error as the kit's Format-V mask bug.

Cave semantics as decoded (TDF-II, Q14, first-order error feedback), each line at its address:
```
C4C00 r9 = s1 (ld.w gp-0x6c44)            C4C04/08 r13 = e-word & 0x3FFF (ld.w gp-0x6c3c)
C4C0C r9 += e                             C4C0E/12 r13 = x * 16048  (mul low word)
C4C16 r7 = b0*x                           C4C18 acc = r9 = s1 + e + b0*x
C4C1A/1C y = acc >> 14 (sar, floors)      C4C1E/22 e' = acc & 0x3FFF  -> st.w gp-0x6c3c (zeroes FLAG half)
C4C26/2A/2E r7 = b0*x - 15712*y = s2'     C4C30/34 r13 = s2 (old); st.w s2'
C4C38/3A r9 = n = x - y                   C4C3C/40/44/46 s1' = (-31842)*n + s2_old -> st.w gp-0x6c44
C4C4A-C4C6E FLAG = ((n<0)?2:0 | (|n|>=|y|)?8:0) << 4 -> st.h gp-0x6c3a    (values 0/0x20/0x80/0xA0 only)
C4C72-C4C82 r12 = clamp(y, ±cal 0xC61BE = 15360)    C4C84 r7 = cal 0xC63EE = 507    C4C88 jr 0x2A178
```
Coefficients read from the `movea` immediates: b = [16048, −31842, 16048], a = [16384, −31842, 15712]. Pole radius 0.9793
(τ ≈ 48 ticks). −3 dB band 16.98–23.64 Hz, Q_realised 3.007. |H| and phase at the loop's other frequencies, from the integers:
3.9 Hz 0.998 / −3.85°, 7.3 Hz 0.990 / −7.96°, 13.5 Hz 0.925 / −22.3°, 30 Hz 0.928 / +21.8°. The emulator reproduces these to
the DFT's leakage (integer-cycle frequencies agree to 4 decimals).

### 2. Emulation battery (V850 semantics: `sar` floors, `mul` 32×32→32 low word, `ld.h` sign-extends, `ld.hu` zero-extends, `st.h` truncates, flags Z/S/OV/CY)
- Constants: 22 runs, all exact; settle times from zero state 0–327 ticks (X = ±15360 slowest), from worst-case state ≤ 456.
  Final states s1 = s2 = 336·X in every run (the analytic fixed point (b0 − a2)·X).
- Zero input from worst-case state (s1 = +0.14·2³¹, s2 = −0.14·2³¹, e = 16383): |y| ≤ 1 by tick 425, exactly 0 from 426.
- 20.036 Hz sine: A = 1 → peak |y| 2; A = 10 → 4; A = 100 → 4; A = 3000 → 3; A = 15000 → 3. The residue is the quantiser floor
  (≈ ±3 counts, 0.02 % FS), not leakage of the tone. A = 15000 at 20.05 Hz: peak 65 (= float |H| 0.0042 × 15000).
- 17 / 23 Hz edges: |H| 0.704 / 0.640 (−3.0 / −3.9 dB), phases −45.2° / +50.2°.
- Step 0 → 15360: linear peak **17736 (×1.155) at tick 36**; clamp binds on 187 of the next 500 ticks (the decaying 20 Hz
  ring's positive half-cycles); emitted max 15360; **first undershoot 11324 (×0.737) at tick 11** (see R3).
- Rail square ±15360 at 20 Hz (25 ticks/half): max emitted |y| 15197, max |register| 0.290·2³¹.
- Random rail-bang 5000 ticks: max |register| 0.158·2³¹.
- l1 worst-case sign sequences (1500 ticks, built from the exact rational impulse responses x → s1, s2, acc): reach 0.147 /
  0.146 / 0.137·2³¹ in the states, 0.2908·2³¹ peak intermediate; emulator output == big-int shadow output tick-for-tick.

### 3. Downstream widths (real bytes 0x2A178–0x2A1B4 emulated after the cave, lag state persistent, 3800 ticks of step/rail/square)
`st.h r12,gp-0x6b2e` @0x2A17C: |r12| ≤ 15360 by the cave's clamp — **the same cell (0xC61BE) and the same bound V282 had**, so
the publish cannot truncate. Lag: r12·507 (max 7.79 M, ≫ fits), state max **243 360**, `r9 = (s + s') >> 5` max **15 210**.
Ramp multiply @0x2A1E6: 15 210 × 32 767 = 4.98·10⁸ = 0.232·2³¹, `sar 0xf` → 15 209, `sxh` is a no-op. Gain stage @0x2A1F6:
`mulh 891 × (gp-0x6752 = −1)`, then r11 = (r11 + r9)·(−891) >> 15, clamped to ±cal(0xC61B4) = 3072 at 0x2A204–0x2A220,
published `st.h r1,gp-0x6b38`. Nothing on this path sees a wider value than V282 produced. The overshoot never reaches r12.

### 4. Register / flag clobber
Static census of every destination in the 52 cave instructions: r6, r7, r9, r12, r13. `mul … ,r0` discards the high word.
r12 is written last at 0xC4C7A/0xC4C82 (the clamp) and then only read. Dynamic markers on r11/r14/r15/r16/r22/r24/r27/r29/lp
held on every tick. PSW: the cave's last flag-setting instruction is `cmp r9,r12` @0xC4C7E; downstream, 0x2A178–0x2A1AC contains
no bcond/setf/adf/sbf/satadd, and `cmp 0x1,r16` @0x2A1AE re-arms before `bne` @0x2A1B4. No `jarl` in hook, cave or tail.

### 5. The 0x14A tail (0xC4BDC–0xC4BF7)
`ld.hu gp-0x6c3a,r7 ; andi 0xA0 ; ld.bu gp-0x1514,r6 ; andi 0x5F ; or r7,r6 ; st.b r6,gp-0x1514 ; movea -0x1518,gp,r6 ; jmp [lp]`.
Exhaustive emulation, 6 FLAG values × 256 byte-4 values: output == (b4 & 0x5F) | (FLAG & 0xA0) in **1536/1536** cases; bits
0–4 and 6 preserved; r6 = gp−0x1518 and lp intact on exit. The relocated epilogue bytes `24 36 e8 ea 7f 00` at 0xC4BF2 are
byte-identical to V282's at 0xC4BD2 (asserted against the V282 image). Caller: the instruction after the `jarl` at 0x55C0E is
`mov 0x8,r7` @0x55C12 (v289 program, Ghidra) — **r7 is dead at the return**. Filler 0xC4BDA–0xC4BDB and 0xC4BF8–0xC4BFF is 0xFF.

### 6. Error feedback — poles unchanged, no limit cycle > 1
Algebra: with acc_k = b0·x_k + s1_k + e_{k−1}, y_k = ⌊acc_k/2¹⁴⌋, e_k = acc_k − 2¹⁴·y_k ∈ [0, 16383], the recursion is exactly
2¹⁴·y_k = b0·x_k + s1_k + (e_{k−1} − e_k). The bracket is a bounded external sequence (|Δe| < 2¹⁴) entering at the same node as
the input, so A(z)·Y = B(z)·X + (z⁻¹ − 1)·E/2¹⁴: **the denominator A(z) — hence the poles (r = 0.9793) — is untouched**, the noise
transfer has a zero at DC, and BIBO stability of the linear part bounds y. Fixed points for x = X: s1 = s2 = 336·X and **any**
constant e ∈ [0, 16383] gives y = X exactly — a continuum of exact equilibria, which is why the emulation settles exactly instead of
dithering (the builder's docstring under-claims here: "dithers within ±1" — observed: exact). Emulation: no run showed a cycle;
the only non-decaying quantity is e itself (R1). The 20 Hz small-signal residue of ±3 counts (attack 2) is the in-band
noise-shaping floor, not a cycle: it is present only while a tone drives the filter.

## Residuals (recorded, none meets a §A criterion)
- **R1** With S = 0 the remainder word e settles to a non-zero constant (635 in the worst-case run), not 0. It is a sub-LSB
  residue: y = 0 exactly, s1 = s2 = 0, and any constant e is an exact equilibrium. Effect on y at the next input: < 1 count.
- **R2** Quantiser floor: a 20.036 Hz tone of any amplitude leaves a ±3–4 count residue (0.02 % of 15360) on y; noise into the
  lag is of that order (the builder's "< 2 counts rms" is consistent with a ±3–4 peak).
- **R3** Inherent notch step response, for Adversary B's B3: a rail step 0 → 15360 delivers 15045 on the first tick, **dips to
  11324 (×0.737) at 11 ms**, overshoots to a linear 17736 (×1.155, clipped to 15360) at 36 ms, and rings at 20 Hz with τ ≈ 48 ms.
  The clamp clips only the positive half-cycles, so the emitted mean during the ring sits slightly below the rail. Not an
  arithmetic fault; it is what a Q-3 notch does to a step, and the design's capped-step figures should already include it.
- **R4** FLAG handoff race: `st.w` @0xC4C22 zeroes the FLAG halfword (it writes the whole e word) and `st.h` @0xC4C6E rewrites
  it 19 instructions later. If the 100 Hz frame builder can preempt the 1 kHz task inside that window, that frame reads
  b5 = b7 = 0. Only matters if the 100 Hz task has higher priority than the 1 kHz one (unknown to me — BELIEF that it does not);
  the effect would be a small downward bias on both duties, never a wrong sign paired with a wrong magnitude (single atomic read).
- **R5** Pre-existing, stock: Honda's lag at 0x2A178–0x2A1B0 (`sar 0xa` floors) parks a negative state at −24 after the input
  returns to 0 (r9 = −2 counts). Byte-identical to V282; noted because it showed up in the downstream emulation.
- **R6** fs = 1 kHz is a BELIEF. f0 = 20.036 Hz × (fs / 1000). The A1 margin (0.3 Hz) tolerates a 1.5 % fs error only.

## What a FAIL would have looked like (pre-registered, for the record)
Any decoder/Ghidra mismatch; any live register or lp marker changed; any `jarl`; any intermediate ≥ 2³¹ in the shadow or a
shadow/emulator disagreement; any constant-input run whose tail is not exactly X; f0 outside 19.75–20.35 Hz; depth above −20 dB
at 20.05 Hz; tail output differing from (b4 & 0x5F) | (FLAG & 0xA0). None occurred.

## Method notes
Ghidra: v289 image imported as a second program (`_v289_…_plain_image.bin`, V850:LE:32, no auto-analysis), all disassembly via
`disassemble_bytes(dry_run=true)` — no database mutation, program saved, active program returned to `code.bin`. Hook-site context
(0x2A140–0x2A2A7) from `code.bin`; identical bytes in V282/V289 outside the 4-byte hook. Diff census V289 vs V282 over
[0x13000, end): 185 bytes, exactly the declared runs (hook 4, 0x14A exit 4, tail 28, cave 140, 0xC63E8/EA 4, two CRC cells).
The fb-pole cells read 875 (`ld.h`, signed OK) and 2301 (`ld.hu`, unsigned OK) — widths fine; their loop effect is B's surface.
