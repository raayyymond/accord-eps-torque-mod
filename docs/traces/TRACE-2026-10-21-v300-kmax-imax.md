# TRACE 2026-10-21 — V300 rev 2: Kmax, Imax and the angle error where Kp·E = Kmax − Imax

Image: `_v300_V300-REV2-...A16C_plain_image.bin`, sha256 `7d58c823544e9e6e…f384e` (verified with sha256sum).
Ghidra: imported fresh as `/pidclamps_v300/...bin.4` (no auto-analysis), `create_function(0x28ea6)` → body 5224 B
(= 0x28EA6..0x2A30E, matches the known extent); cave `FUN_000c4c00` decompiled. Not saved; no renames.
Mirror: `analysis-2020accord/_scratch/pidclamps/kmax_imax.py` (all constants byte-read LE from THIS image).
Full V300-vs-stock diff over [0x13000,0x100000): `analysis-2020accord/_scratch/pidclamps/diff.py`.

## 1. Edits on the PID path (Python diff, then Ghidra disassembly of the V300 program)

| site | V300 instruction | effect |
|---|---|---|
| 0x28F4C | `ld.h -0x6a00[gp],r7` | filter input x := θ (gp-0x6a00). The same load feeds Honda's bail: \|θ\| ≤ 12000 (0x28F50/54) |
| cals 0xC63E8/EA | a = 0, b = 8192 | t = (8192·θ)>>10 = 8θ. r26 = t[n−1] + t[n] = 8θ[n] + 8θ[n−1] (0x28F8E..0x28FA4; the `add` is stock). Clamp ±[0xC62E6] = 65535 |
| 0x29D6A | `ld.h -0x69ae[gp],r16` | sp = gp-0x69ae, unquantised |
| 0x29D76 | `jarl 0xC4C00, r6` | the link is in **r6**. The cave returns by `jmp [r6]` (to 0x29D7A) or by `jr 0x29D7E` |
| 0xC4C00..0xC4CD9 | cave | E = 4·sp − r26. Then **r26 := (short)gp-0x6abe** (0xC4C04, the filtered rotor speed). It bails to 0x2A164 unless gp-0x6abe ∈ [−13000, 12998]. E′ = (E·G(v))>>8 (0xC4C54/58). Then the integrator gate (§3) |
| 0x29EE0 | `mov r26,r8 ; nop` | D = clamp((gp-0x6abe·Kd)>>3, ±[0xC61B6]). D acts on the rotor-rate word, NOT the angle |
| 0x2A1EE | `ld.h 0x7cd0[tp],r7` | the forward gain is repointed to 0xC6CD0 = 5346 |

**Setpoint scale [EVIDENCE; the stock code there is identical in V300].** 0x526CA does `mov r10,r6; sxh; shl 2; subr r0,r6`.
The clamp helper `jarl 0x49A90` is called with r7 = −0x4000 and r8 = 0x4000, then `st.h r10,-0x69ae[gp]` @0x526F2.
⇒ **gp-0x69ae = clamp(−4·wire, ±16384)**.

**Error [EVIDENCE, arithmetic].** At steady state θ[n] = θ[n−1]:
`E = 4·(−4·wire) − 16θ = 16·(θsp − θ)` with θsp = −wire, both in gp-0x6a00 counts.
**Angle unit [BELIEF from the record, not re-derived this session].** gp-0x6a00 is 0.1° per count
(`reference_accord_gp6a00_angle_is_a_100hz_hold…`, which gives its formula and the 1.155 near-centre correction). So Δ counts / 10 = degrees.

## 2. P, the sum, Kmax

```
E'  = (E * G(v)) >> 8                        # 0xC4C54 mul, 0xC4C58 sar 8
P   = clamp((E' * Kp) >> 8, ±[0xC61BC])      # 0x29E34 mov r16,r8 ; 0x29E36 mul ; 0x29E3E sar 8 ; clamp 15360
I   = clamp((Ist>>3) + ((exc*Ki)>>3), ±(([0xC61BA]<<10)>>3))   # 0x29D9C..0x29DC2 ; Ki 40, ICL 8192 -> 1,048,576
D   = clamp((gp-0x6abe * Kd) >> 3, ±[0xC61B6])                # 0x29EE0..0x29F06 ; Kd 48, clamp 10240
S   = (I >> 7) + P + D                       # 0x29F18 sar 7,r2 ; 0x29F1E add r9 ; 0x29F24 add r8
fac = ((A(r21) * C(r1)) & 0xFFFF) >> 8       # 0x2A0B4 mulu ; 0x2A0B8 andi 0xffff ; 0x2A0BC sar 8   (engaged: r25 != 0)
S'  = clamp((fac * S) >> 8, ±[0xC61BE])      # 0x2A0BE mul r2 ; 0x2A0C2 sar 8 ; br 0x2A13E ; clamp 0x2A13E..0x2A162
```
Live records for selector 7 [EVIDENCE; pointer arrays read at +4·7]:
- Kp: 0xCB994 → 0xE5378, Y = [112,112,112,112,112], flat.
- Kd: 0xCB7D4 → 0xE511C, Y = [48,48,48,48], flat.
- A: 0xCBB54 → 0xE55A4, Y[0] = 255 at X ≤ 0.
- C: 0xCBAE4 → 0xE54FC, X [16,26,38,48,64,96], Y [255,243,218,179,77,77].
- Deadband 0xC62E4 = 0.
- ⚠ I did not check the other 27 Kp records.

**Kmax = [0xC61BE] = 15360. It applies AFTER the taper and BEFORE the output lag and the forward gain.** Hands-off, fac =
(255·255 & 0xFFFF)>>8 = 254, so the pre-taper sum must reach **15481** for S′ to hit 15360. P, I>>7, D and Kmax are all in
the same "sum" units. Only the taper sits between them.

## 3. Imax (in I>>7, the units in which it enters the sum) [EVIDENCE, cave 0xC4C5A..0xC4CD4]

Ist = gp-0x6dd0 = 8·I (stored as `r24 = r2<<3`, 0x29DE4 / st.w 0x2A190), so the cave's `Ist >> 10` (0xC4CB0) is exactly I>>7.
Each tick, with θ′ = max(0, θ·sign(E′)) (0xC4C6A..0xC4C78):
```
if   v >  2880: cap = 64*θ' + 1250                       # 0xC4CA6
elif v >  1382: cap = min(16*θ' + 1250, 6144)            # 0xC4C9A
else:           cap = min(16*θ' + 1250, 4096)            # 0xC4C94
integrate (r6 = E'>>5, return jmp [r6]->0x29D7A)  iff  (I>>7)*sign(E') < cap  AND  ramp gp-0x69b0 bit15 set
                                                   AND  |driver torque| gp-0x4f68 <= 1229 ;   else r6 = 0 (freeze)
disengaged (r25 == 0): r16 = r26 = 0, r6 = -(Ist>>6)  -> I bleeds to 3/8 of itself per tick
```
The hard clamp ICL gives |I>>7| ≤ 8192 at every speed. The cap is a freeze, not a clamp. I can pass it by one tick's step,
(5·(E′>>5))>>7 ≈ E′/819 sum units, which is about 40 at the P-clamp error.

| regime (v-word gp-0x6a5e) | km/h and m/s [BELIEF: 64 counts per km/h, from the record] | Imax at θ′=0 | Imax ceiling | ceiling reached at θ′ |
|---|---|---|---|---|
| v ≤ 1382 | ≤ 21.6 km/h, ≤ 6.0 m/s | 1250 | 4096 | 17.8° |
| 1383..2880 | 21.6–45 km/h, 6.0–12.5 m/s | 1250 | 6144 | 30.6° |
| v > 2880 | > 45 km/h, > 12.5 m/s | 1250 | 8192 (ICL) | 10.9° |

r14 at the cave is the engagement ramp [EVIDENCE, partial]. `search_instructions(r14, FUN_00028ea6)` on the V300 program shows
every r14 write after the filter's cal reload at 0x28F9C lies in the ramp block 0x2936A..0x29728 (loads and stores of gp-0x69b0,
`ori 0x8000`, `mov 0`). There is no write between 0x29728 and 0x29D76. I did not enumerate every path through the ramp block.

## 4. Other clamps, and which binds first

- **P clamp [0xC61BC] = 15360**, equal to Kmax. Because of the 254/256 taper, P at its clamp alone gives S′ = 15240. The
  sum clamp then needs I>>7 + D ≥ 121 on top.
- **D clamp [0xC61B6] = 10240.** D = 6·gp-0x6abe. It is zero with the wheel still, so it does not enter the steady-state solve.
- **Output clamp [0xC61B4] = 3072 never binds from the PID.** At 0x2A1EE..0x2A220, delivered = clamp(((r11 + y·ramp>>15)·
  (polarity·5346))>>15, ±3072), and r11 ≡ 0 per the record. The lag (0xC63EC = 992, 0xC63EE = 507) maps S′ = 15360 to y = 15208
  (mirror, 5000 ticks). The delivered value is **−2482**, below 3072. Polarity −1 is BELIEF from the record.
- **Binding order:** the sum clamp 0xC61BE binds first. P's own clamp is reached only at larger errors.

## 5. Solve [EVIDENCE: integer mirror; G(v) from 0xC4CDA]

Closed form, with Δ in 0.1° counts: `P = ((((16Δ·G)>>8)·112)>>8) ≈ Δ·G·7/256`, so **degrees = P_target·0.3657 / G(v)**.
G(v) table entries are (X, Y, slope Q12): (714,1178,1041) (1843,1465,−6264) (2304,760,−2033) (2707,560,1570) (4032,1068,2118) (6198,2188,0) (65535,…).
Below 714, G = 1178. The smallest G is 560, at v = 2707 (42.3 km/h). Above 6198 (96.8 km/h), G = 2188.

The operator's literal equation, with Kmax = 15360 taken as if there were no taper, gives P = 15360 − Imax.
The exact threshold with the taper is P ≥ 15481 − Imax. The table uses the exact form. The literal form moves each angle by ≤ 0.4°.

| speed | G | P = own clamp | P = Kmax−1250 (θ′=0) | P = Kmax − Imax ceiling | P = Kmax − 8192 |
|---|---|---|---|---|---|
| 0–11 km/h | 1178 | 47.7° | 44.2° | **35.4°** (Imax 4096) | 22.7° |
| 20 km/h | 1321 | 42.6° | 39.4° | 31.6° (4096) | 20.2° |
| 25 km/h | 1403 | 40.1° | 37.1° | **24.4°** (6144) | 19.1° |
| 30 km/h | 1347 | 41.8° | 38.7° | 25.4° (6144) | 19.8° |
| 40 km/h | 632 | 88.9° | 82.4° | 54.1° (6144) | 42.2° |
| 45 km/h | 626 | 89.8° | 83.2° | 54.6° (6144) | 42.6° |
| 50 km/h | 748 | 75.1° | 69.6° | 35.7° (8192) | 35.7° |
| 60 km/h | 994 | 56.6° | 52.4° | 26.9° | 26.9° |
| 80 km/h | 1630 | 34.5° | 32.0° | 16.4° | 16.4° |
| ≥ 97 km/h | 2188 | 25.7° | 23.8° | **12.2°** | 12.2° |

Worked example at low speed, with I at its 4096 ceiling. The target is 15481 − 4096 = 11385. Δ = 354 counts gives E = 5664,
E′ = (5664·1178)>>8 = 26062, and P = (26062·112)>>8 = 11402 ≥ 11385. Δ = 353 gives P = 11370. ⇒ 35.4°.
The literal 15360 − 4096 = 11264 lands at 35.0°.

Caveats:
1. This is steady state only. A turning wheel adds D = 6·gp-0x6abe, and its sign relative to P was not re-verified here.
2. Hand torque lowers C(r1) and so lowers fac, which moves the sum clamp further away. Above |τ| = 1229 the I freezes.
3. The Δ is the firmware's θ (gp-0x6a00, a 100 Hz hold, two-sample sum) against −wire, not openpilot's own filtered angle.

## Open / to verify
- gp-0x6a00 = 0.1°/count and gp-0x6a5e = 64 counts per km/h come from prior traces and were not re-derived on this image.
- The polarity byte gp-0x6752 = −1 is from the record. It sets the output sign only, not the magnitude.
- I did not census the other 27 Kp records. Selector 7 is the one the record measured on the wire.
- Whether D damps depends on gp-0x6abe's sign relative to dθ/dt. That was not traced here.
