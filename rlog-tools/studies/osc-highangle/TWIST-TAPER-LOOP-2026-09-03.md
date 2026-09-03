# The driver-torque paths in the 7 Hz strong-turn ripple — twist, tapers, and the driver-side loop (V280 rev 2, r32/r33/r34)

Subagent `twistloop`, 2026-09-03. Script: `twist_taper_loop.py` (beside this file; its full stdout is `TWIST-TAPER-LOOP.txt`).
Decompile: `FUN_00028ea6` (Ghidra, stock `code.bin`; byte-identical on V280 rev 2 except the V112 gain-read redirect), `FUN_00052676`,
`FUN_00021724`. Every table below is read from `_v280_V280R2-…_plain_image.bin` at run time. EVIDENCE / BELIEF marked per claim.

Operator hypothesis under test: *"could it be feedback from the driver torque sensor temporarily limiting our torque demand setpoint
input? Or driver torque sensor and the driver-side steering PID loop acting on the feedback?"*

## 0. Headline

1. **There IS a live driver-torque multiplier on the delivered LKAS torque, and it is not the one the kit had on file.** [EVIDENCE]
   The arm selector `gp-0x6803` is **bits 3:2 of the 0xE4 command's byte 2** (`FUN_00052676` @0x526ac), and openpilot sends
   **0** there on every frame of r32/r33/r34 (measured; the stock Honda camera sends 1). So the `== 2` arms the kit modelled
   (`0xCBA74`/`0xCBA04` cliff at 2240–2560 raw; `0xCBB54`×`0xCBAE4` post gate) are **never selected**. The live arms are:
   - setpoint-stage taper **`0xCB924`/`0xCB8B4`** (slot 7 @0xE52FC/0xE5284): flat 255 to **2560 raw**, linear to 0 at **3584 raw**
     — a 1024-count ramp, not a 320-count cliff;
   - post-PID multiplier **`0xCBC34`(grab-rate) × `0xCBBC4`(|driver torque|>>5)** (slot 7 @0xE56F4 / **0xE564C**):
     `0xCBBC4` = X (16,26,38,48,64,96) → Y (255,243,218,179,77,77), i.e. **fades from 512 raw and is 77/255 = 0.30 at 2048 raw**.
     The kit's memory `reference-accord-second-driver-torque-gate-cbae4-cbbc4` called this gate inert; it is inert only in the
     mode-2 arm, which is the one that never runs.
2. **With the live arms the chain mirror closes on the tap**: corr vs the 427 tap **0.888 → 0.955** (median over the 18 F7
   episodes, higher on 17 of 18), whole-route LS slope **0.47–0.58 → 0.86–0.90**. The ~0.5 slope every prior mirror reported was
   this multiplier (mean 178/254 = 0.70 in the episodes), not a tap scale. [EVIDENCE, method: re-run of the same mirror]
3. **But the multiplier is the smaller part of the 7 Hz ripple.** Decomposition of T's 6–8.5 Hz content, as a fraction of |T|:
   **P-driven 0.53, D-driven 0.26, taper(multiplier)-driven 0.10** (medians; taper-driven 0.05–0.45, largest where the bar rings
   hardest). The multiplier's own modulation depth is **0.14 at f0 and 0.33 at 2·f0** (it is indexed by |tq|, which rings at 2f0
   around a near-zero mean). The setpoint-stage taper does **not move at all** in the episodes (depth 0.00): |tq| stays below 2560.
4. **The bar ring is the wheel's inertial reaction to T, not an independent input.** bar↔T coherence **0.99**, phase **−152°** (T
   relative to bar) on every F7 episode. With T leading the rate by ~+115° (prior tables) and bar = −J·α for light hands (α at +90°
   re rate), the predicted phase is −155°. [EVIDENCE for the cross-spectrum; BELIEF for the mechanism]
5. **The driver-side (bar-fed) additive lanes are ≤ 20 % of the LKAS lane's own ripple at 7 Hz** (r24 60–100 ct vs T ripple
   400–700 ct; the 0.93 Hz trim loop ~6 ct; gp-0x6bbe ~30 ct), and the ×6 gain `0xC6CD0` multiplies **none** of them (it is read
   only at 0x2A1EE on the LKAS lane). [EVIDENCE for the gains and the gain-read; BELIEF for r24's gain arm]
6. **Verdict on the hypothesis:** *partly right in kind, wrong in size.* A driver-torque feedback does modulate the delivered
   torque at 7 Hz — the post-PID `0xCBBC4` fade, reading the column twist that T itself causes — but it carries ~0.10 of |T|
   against ~0.5 from the rate-error P term. The oscillation is the rate servo hunting; the bar ring is its footprint, and the fade
   adds a small, mostly in-phase (+0.40 corr with the P-driven part), mildly anti-damping (damping fraction 0.34) modulation on top.
7. **Lever: do not flatten `0xCBBC4`.** It removes ~0.10 of ripple/level but raises |T| **×1.33** in the episodes and **×2.9**
   whenever a hand is on the wheel (|tq| ≥ 1216 raw: r34 hands-on |T| p50 777 → 2264 ct). The V281 rev 2 Kp cap leaves the
   taper-driven fraction unchanged (0.10 → 0.08 of |T|), as a multiplicative term must.

## 1. The arithmetic, pinned (decompile of FUN_00028ea6; addresses from the listing)

```
# --- the two driver-torque BYTES (top of the function) ------------------------------------------ [EVIDENCE]
tq        = gp-0x4f60                                   # raw column torque, sensor B          ld.h @0x28F26
gp-0x682f = min(|tq| >> 5, 254) (255 if larger)         # driver-torque BYTE                    st.b @0x29068
s'        = (s*31 >> 5) + (tq*634 >> 5)                 # 0xC63E2 = 31, 0xC63E4 = 634: pole 0.969 (5 Hz), DC x640
d         = clamp((s' - s) >> 4, +-0x3200)              # derivative of the lagged torque
gp-0x6830 = |d| >> 6                                    # "grab-rate" BYTE                      st.b @0x290DE

# --- the arm selector ----------------------------------------------------------------------------- [EVIDENCE]
gp-0x6803 = (0xE4_byte2 << 0x1c) >> 0x1e                # FUN_00052676 @0x526ac: bits 3:2 of byte 2 of the 0xE4 command
                                                        # (gp-0x6805 = byte2 >> 7 = STEER_REQUEST; gp-0x69ae = clamp(-4*STEER_TORQUE);
                                                        #  FUN_00021724 returns CONCAT(gp-0x1428, gp-0x1427) = bytes 0,1 -> gp-0x1426 = byte 2)
bVar1     = (gp-0x6803 == 2)                            # 0x29a74 ld.bu / cmp 0x2 / setfe
# ON THE WIRE (r32/r33/r34, src 129 = openpilot's 0xE4 to the EPS): byte2 & 0x7F == 0 on 100 % of frames -> gp-0x6803 = 0 -> bVar1 = 0
# (the stock camera's own 0xE4, src 2/128, carries byte2 = 0x84 -> bits 3:2 = 1; value 2 never appears from either source)

# --- (A) setpoint-stage taper, BEFORE the map -------------------------------------------------- [EVIDENCE]
S     = clamp(-4*cmd, +-LIMIT)
if sign(S) == sign(tq):  taper = bVar1 ? LERP(0xCBA74[sel], gp-0x682f) : LERP(0xCB924[sel], gp-0x682f)     # 0x29aa0 arm
else:                    taper = bVar1 ? LERP(0xCBA04[sel], gp-0x682f) : LERP(0xCB8B4[sel], gp-0x682f)     # 0x29b7c arm
(if cal 0xC64B8 (=255) < gp-0x682f: taper = 0 -- unreachable, the byte saturates at 255)
v     = ((taper * speedF) & 0xFFFF) * S >> 16 ; v >>= 6 ; clamp +-240 ; idx = |v| -> gp-0x674b
sp    = sign(v) * LERP(map[sel], idx) ; E = 32*sp - fb ; P = E*Kp(idx) >> 8 ; D = dE*Kd >> 3 ; I = 0

# --- (B) post-PID multiplier, AFTER the PID sum, before the lag and the gain ------------------- [EVIDENCE]
A     = bVar1 ? LERP(0xCBB54[sel], gp-0x6830) : LERP(0xCBC34[sel], gp-0x6830)       # 0x29fe2.. (grab-rate)
B     = bVar1 ? LERP(0xCBAE4[sel], gp-0x682f) : LERP(0xCBBC4[sel], gp-0x682f)       # mov 0xcbbc4 @0x2a04a (driver torque)
m     = ((A * B) & 0xFFFF) >> 8                                                       # 255*255 -> 254
sum   = (m * (P + D)) >> 8 ; clamp +-0xC61BE                                          # 0x2a0c2
lag   : s' = (992 s + 507 u) >> 10 ; y = (s + s') >> 5
T     = clamp((y * ramp >> 15) * (-1) * GAIN(0xC6CD0 = 5346) >> 15, +-0xC61B4 = 3072) -> gp-0x6b38   # 0x2a1ee
```

Slot-7 records, read from the V280 rev 2 image (raw driver torque = X × 32):

| record | slot 7 @ | X | Y | live? | raw torque at the knots |
|---|---|---|---|---|---|
| `0xCBA74` taper, same-sign, mode 2 | 0xE547C | 70,72,78,80 | 254,234,12,0 | **no** | 2240 … 2560 (the kit's "cliff") |
| `0xCBA04` taper, opp-sign, mode 2 | 0xE5404 | 70,72,78,80 | 254,234,12,0 | **no** | 2240 … 2560 |
| **`0xCB924`** taper, same-sign, mode ≠ 2 | 0xE52FC | 32,42,80,112 | 255,255,255,0 | **yes** | flat to 2560, zero at 3584 |
| **`0xCB8B4`** taper, opp-sign, mode ≠ 2 | 0xE5284 | 32,38,80,112 | 255,255,255,0 | **yes** | flat to 2560, zero at 3584 |
| `0xCBB54` postA (grab), mode 2 | 0xE55A4 | 0,3,6,8,10,20 | 255×5,205 | no | — |
| **`0xCBC34`** postA (grab), mode ≠ 2 | 0xE56F4 | 0,3,6,8,10,20 | 255×5,205 | **yes** | grab byte ≥ 10 → falls to 205 at 20 |
| `0xCBAE4` postB (torque), mode 2 | 0xE54FC | 24,45,64,80,96,112 | 255,205,164,125,90,51 | no | 768 … 3584 |
| **`0xCBBC4`** postB (torque), mode ≠ 2 | **0xE564C** | 16,26,38,48,64,96 | 255,243,218,179,77,77 | **yes** | **512, 832, 1216, 1536, 2048, 3072** |

Readers of the `0xCBBC4` pointer table: `FUN_00028ea6` @0x2a04a and the dead out-of-line copy `FUN_0002a93a` @0x2af30 (`search_instructions`
+ a raw LE32 scan of the image, both agree; positive control: the same scan finds the 0xCBAE4 reads at 0x29fe4/0x2aed2). The record 0xE564C
is pointed to only from the table entry at 0xCBBE0 (LE32 scan). Slot 7's record is not shared with any other slot. [EVIDENCE]

**What acts BEFORE the map (on idx/sp):** taper (A), live arms `0xCB924`/`0xCB8B4`, flat until 2560 raw. **What acts AFTER the PID (on T):**
the product `m` of `0xCBC34`(grab) × `0xCBBC4`(|tq|), applied to P+D before the lag and the gain — so it multiplies the delivered torque and its
ripple alike, and its own ripple rides on the mean torque.

Two open bits, both BELIEF: `gp-0x680a` (a byte that, if 1, replaces the taper by a `tp+0x7722` LERP of `gp-0x6a34`) has no writer that
`search_instructions` can see; treated as 0. The grab-rate filter state `gp-0x3d34` is reset to 0 when `gp-0x3d2c != 1` (the same valid-gate the
function uses for the fb filter); the mirror runs it continuously.

## 2. Per episode: modulation depths, cross-spectrum, mirror before/after, decomposition

All rows: engaged frames of the episode, 100 Hz grid, multipliers computed from the 0x18F torque (raw = wire × 1.024) exactly as above (the grab
byte at 1 kHz on the interpolated torque). d7 = 6–8.5 Hz amplitude ÷ mean; d14 = 12–17 Hz ÷ mean (= 2·f0, where a rectified index rings).
"kit" = the mirror as run until now (mode-2 arm, m = 254 flat); "live" = mode-0 arms and the live m. corr = sim vs the 427 tap; resid = 6–8.5 Hz
amplitude of (tap − slope·sim) ÷ |T| p50. Decomposition (each ÷ |T| p50 measured): P-driven = ripple of the live sim with m frozen (< 1 Hz) and
Kd = 0; taper-driven = ripple of (live − m-frozen); D-driven = ripple of (m-frozen − m-frozen,Kd=0). Components are not phase-aligned, so they do
not add to the total.

| route t0 | dur | f0 | tq mean / ring (raw) | taper d7 | postB mean d7 d14 | postA mean d7 d14 | **m mean d7 d14** | coh / phase T re bar | corr kit→live | resid kit→live | meas rip/L (|T|) | sim rip/L kit→live | **P / taper / D** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r32 620.7 | 3.8 | 7.03 | −215 / 1590 | 0.00 | 203 0.07 0.27 | 230 0.04 0.10 | 184 0.09 0.33 | 0.97 / −152 | 0.85→0.92 | 0.13→0.13 | 0.45 (954) | 0.65→0.51 | 0.42 / 0.05 / 0.20 |
| r32 692.8 | 2.8 | 6.64 | −149 / 1743 | 0.00 | 197 0.10 0.31 | 229 0.05 0.11 | 178 0.13 0.37 | 0.97 / −153 | 0.89→0.95 | 0.12→0.14 | 0.56 (857) | 0.93→0.68 | 0.58 / 0.09 / 0.25 |
| r32 726.5 | 1.7 | 6.55 | +208 / 1447 | 0.00 | 209 0.20 0.23 | 230 0.03 0.12 | 189 0.19 0.29 | 0.96 / −159 | 0.87→0.95 | 0.15→0.13 | 0.47 (1046) | 0.63→0.54 | 0.44 / 0.10 / 0.20 |
| r33 100.8 | 1.6 | 6.96 | −54 / 1287 | 0.00 | 206 0.14 0.17 | 234 0.02 0.11 | 188 0.15 0.24 | 0.99 / −155 | 0.78→0.97 | 0.08→0.10 | 0.42 (1066) | 0.59→0.52 | 0.43 / 0.11 / 0.27 |
| r33 212.5 | 1.4 | 7.35 | +113 / 1880 | 0.00 | 180 0.14 0.45 | 224 0.02 0.12 | 160 0.16 0.52 | 1.00 / −159 | 0.90→0.96 | 0.16→0.16 | 0.99 (588) | 1.50→1.22 | 1.01 / 0.18 / 0.33 |
| r33 224.1 | 1.1 | 6.96 | −99 / 1715 | 0.00 | 198 0.10 0.31 | 227 0.04 0.12 | 178 0.11 0.39 | 1.00 / −149 | 0.93→0.95 | 0.12→0.13 | 0.74 (799) | 1.13→0.92 | 0.74 / 0.10 / 0.30 |
| r33 833.5 | 3.6 | 7.42 | +367 / 1598 | 0.01 | 199 0.13 0.27 | 230 0.02 0.11 | 180 0.14 0.33 | 0.99 / −152 | 0.90→0.96 | 0.25→0.17 | 0.91 (600) | 1.24→1.03 | 0.83 / 0.19 / 0.32 |
| r34 35.5 | 1.5 | 7.43 | +266 / 1698 | 0.01 | 193 0.21 0.33 | 225 0.03 0.12 | 171 0.20 0.39 | 0.99 / −152 | 0.94→0.97 | 0.10→0.18 | 0.95 (617) | 1.35→1.10 | 0.91 / 0.23 / 0.39 |
| r34 77.7 | 1.2 | 6.84 | −75 / 1437 | 0.00 | 211 0.14 0.22 | 228 0.04 0.11 | 189 0.15 0.29 | 1.00 / −149 | 0.93→0.97 | 0.10→0.09 | 0.49 (1102) | 0.65→0.55 | 0.43 / 0.10 / 0.25 |
| r34 133.1 (stall) | 2.1 | 7.28 | −434 / 1786 | 0.00 | 173 0.14 0.40 | 231 0.05 0.11 | 157 0.18 0.47 | 1.00 / −145 | 0.87→0.96 | 0.15→0.09 | 0.53 (960) | 0.76→0.58 | 0.48 / 0.08 / 0.23 |
| r34 182.4 | 4.1 | 7.81 | −463 / 1379 | 0.00 | 197 0.05 0.25 | 236 0.03 0.09 | 182 0.07 0.29 | 0.99 / −149 | 0.79→0.93 | 0.18→0.12 | 0.57 (727) | 0.81→0.65 | 0.54 / 0.08 / 0.23 |
| r34 188.2 | 1.1 | 7.48 | +123 / 2223 | 0.01 | 166 0.04 0.53 | 223 0.02 0.12 | 147 0.05 0.60 | 1.00 / −152 | 0.84→0.97 | 0.59→0.14 | 1.37 (503) | 1.69→1.59 | 1.24 / 0.45 / 0.34 |
| r34 343.7 | 1.6 | 7.41 | −75 / 1592 | 0.00 | 206 0.11 0.27 | 226 0.03 0.12 | 184 0.12 0.34 | 1.00 / −153 | 0.94→0.95 | 0.06→0.07 | 0.68 (763) | 0.97→0.82 | 0.68 / 0.09 / 0.33 |
| r34 372.9 | 1.6 | 6.92 | −438 / 1746 | 0.00 | 176 0.10 0.37 | 230 0.05 0.10 | 160 0.14 0.43 | 0.99 / −149 | 0.88→0.96 | 0.10→0.07 | 0.55 (914) | 0.88→0.64 | 0.53 / 0.06 / 0.25 |
| r34 475.7 | 3.5 | 7.03 | −90 / 1784 | 0.00 | 197 0.12 0.33 | 228 0.05 0.11 | 178 0.16 0.40 | 0.98 / −149 | 0.88→0.94 | 0.11→0.12 | 0.67 (814) | 0.98→0.77 | 0.60 / 0.09 / 0.34 |
| r34 480.9 | 3.8 | 6.64 | +225 / 1043 | 0.06 | 152 0.21 0.22 | 243 0.03 0.07 | 142 0.21 0.26 | 0.97 / −160 | 0.89→0.98 | 0.26→0.17 | 0.53 (743) | 0.72→0.62 | 0.50 / 0.17 / 0.33 |
| r34 667.7 | 1.7 | 7.06 | +623 / 1242 | 0.02 | 190 0.10 0.20 | 236 0.05 0.08 | 174 0.15 0.26 | 0.94 / −158 | 0.46→0.94 | 0.09→0.07 | 0.35 (1134) | 0.47→0.39 | 0.34 / 0.09 / 0.22 |
| r34 1003.6 | 1.0 | 7.77 | −364 / 1520 | 0.00 | 204 0.11 0.23 | 229 0.06 0.10 | 184 0.13 0.29 | 1.00 / −149 | 0.92→0.92 | 0.06→0.08 | 0.46 (904) | 0.71→0.55 | 0.46 / 0.06 / 0.23 |
| **F7 median (18)** | | | 1595 | **0.00** | 197 0.11 0.27 | 229 0.04 0.11 | **178 0.14 0.33** | **0.99 / −152** | **0.888→0.955** | 0.12→0.13 | 0.55 | 0.85→0.65 | **0.53 / 0.10 / 0.26** |
| control r34 250.0 (stall, hands on) | 14.0 | — | −410 / 547 | 0.00 | 217 0.03 0.07 | 252 0.01 0.04 | 214 0.04 0.09 | 0.97 / −137 | 0.92→0.99 | 0.29→0.13 | 0.67 (205) | 0.94→0.76 | 0.66 / 0.11 / 0.28 |

Reading the table:
- **The setpoint-stage taper never moves** in a 7 Hz episode (d7 ≤ 0.02 except 480.9 at 0.06): |tq| does not reach the live arm's 2560-raw knee.
  The kit's "cliff duty 2–11 %" on these episodes was computed on the 2240-raw mode-2 arm that is not selected.
- **The post-PID multiplier m is live and rings**: mean 0.70 of full scale, depth 0.14 at f0, 0.33 at 2f0. Nearly all of it is `0xCBBC4` (postB);
  the grab-rate term `0xCBC34` contributes d7 0.04 (its byte reaches 10–20 only at the torque-rate peaks).
- **The mirror with the live arms is a materially better instrument**: corr up on 17 of 18 episodes (mean +0.094), the sim's ripple/level moves
  toward the measured (0.85 → 0.65 vs 0.55 measured), and the whole-route LS slope goes from ~0.5 to ~0.9. The residual ripple is unchanged
  (0.12 → 0.13): what the live m adds is mostly the *level* and the 2f0 content, not the f0 ripple that was missing.
- **T's 7 Hz is P-driven** (0.53 of |T|), with a D-driven term of 0.26 that is in quadrature (prior reports: Kd = 0 changes the total by
  ≤ 0.06) and a **taper-driven 0.10** (0.05–0.19; 0.45 only on 188.2, the hardest bar ring at 2223 raw). Its phase: corr +0.40 with the
  P-driven part (reinforcing, not cancelling), +90° re the wheel rate, damping fraction 0.34 (mildly anti-damping).
- **bar ↔ T**: coherence 0.99 and phase −152 ± 5° on every F7 episode, −137° on the hands-on stall control. The bar torque is locked to T.
- **Control** (r34 250–264 s, the 14 s hand-on stall): bar ring 547 raw with no 7 Hz line; m depth 0.04; the live mirror still improves
  (corr 0.92 → 0.99, residual 0.29 → 0.13) — the multiplier explains the *level* there (m = 214/254 mean), not a ripple.

Whole-route census (engaged frames): |tq| ≥ 512 raw (postB below 255) on 11 / 20 / 30 % of r32 / r33 / r34; ≥ 2048 (m at its 0.30 floor) on
4 / 7 / 12 %; ≥ 2560 (live taper starts to fall) on 2.6 / 4.5 / 6.1 %. The live and kit idx differ on 7 / 11 / 18 % of engaged frames (live
always higher: the kit's 2240 cliff was cutting idx that the car does not cut).

## 3. The driver-side loop at 7 Hz, sized against the LKAS lane

Four bar-fed paths reach the aggregator (`docs/traces/TRACE-2026-08-20-driver-side-feedback.md`, `reference-accord-c646c-shared-gain-not-lkas-only`).
Per F7 episode, amplitude at f0 in aggregator counts, against the LKAS lane's measured T ripple (same counts):

| path | arithmetic | gain at 7 Hz | at the median bar ring (1595 raw) | LKAS lane T ripple (meas) | mark |
|---|---|---|---|---|---|
| r24 (`FUN_0003aa2c`) | −(0.5·(tq[n]−tq[n−4]) · gainA/1024), gainA = `0xC6446` = 512 | 0.5·\|1−z⁻⁴\|·0.5 = 0.044 ct/ct | **~70 ct** (60–104) | 400–700 ct | EVIDENCE arithmetic; BELIEF arm (`gp-0x683c` = 0 ⇒ 512) |
| r26 (same fn) | r24-like × a_smoothed(`gp-0x69a4`)>>10 | unknown schedule | not sized | | BELIEF: same sign as r24 |
| `FUN_00036682` | (tq·891)>>15 → α = 6/1024 IIR, clamp ±512 | 0.0272 × 0.133 | **~6 ct** | | EVIDENCE |
| `gp-0x6bbe` (`FUN_00034a72`) | rate-fed (baseline − raw rate), measured ~90 ct/(rad/s) | at 20–28 deg/s ripple | **~30–45 ct** | | EVIDENCE (V92 on-car) |
| `FUN_0003b8f6` relay | FRICTION ∝ \|delivered cmd\| × sign(motor rate) | switches only on a rate reversal | rate reverses on 0–50 % of frames (median 25 %) | | BELIEF: relay chatter possible in the 9 episodes with reversal ≥ 0.3 |

⇒ The additive driver-side lanes sum to **~110–150 ct at f0**, i.e. **≤ 20–25 % of the LKAS lane's own ripple**, and their sign structure
(r24 differentiates the bar, i.e. is in quadrature with it) does not make them a carrier. **The ×6 gain (`0xC6CD0` = 5346) is read at one
site, 0x2A1EE, on the LKAS lane** (V112's redirect of the `ld.h 0x746c,tp` there); the bar-fed paths still read the stock `0xC646C` = 891 or
their own cals. None of the base-assist lanes is engaged-gated by the LKAS request; the LKAS lane (and its taper/post multipliers) is.
[EVIDENCE for the gain read: `lowcmd_loopgain` header + the c646c reader census; the base-assist boost gain from bar to motor at 7 Hz was
**not** re-derived here — the tap-identified plant G = rate/T already contains it closed.]


## 3b. ADDENDUM 2026-09-03 (after the orchestrator's input on the engaged-only r24 lane, and the operator's "hands off during grind")

**The byte at `0x3AA96` is `fb` on V112 and on V280 rev 2 (stock `c5`), verified from the images.** The r24 gate `ld.bu` therefore reads
`gp-0x6806` (STEER_CONTROL_ACTIVE) instead of the dead `gp-0x683c`, and **while LKAS is engaged r24 takes the flat gain `0xC6446` = 5244**
(stock 512; ×10.24) and r26 takes `0xC6444` = 512 (stock LERP ~3072 at creep). [EVIDENCE: bytes; the mux from the lever index /
`accord-lever-b-is-unreachable`, whose "never reached" verdict was of the STOCK image and does not apply to the flown byte.]

r24's input is `gp-0x4f62` = 2·(bar[n] − bar[n−4]) / Δt with Δt = 4 (`FUN_0007e74a`, ring of 8, N = `0xC6C42` = 4) = 0.5·(bar[n] − bar[n−4]),
a backward difference of the column torque `gp-0x4f60`; r24 = clamp(−1 × deadband(clamp(gp-0x4f62, ±5120) × 5244 >> 10, 3), ±8192),
straight into the 1 kHz aggregator sum. **Sign chain used** (all EVIDENCE): `gp-0x6752` = −1; the frame builder `FUN_00055C42` sends
`−(gp-0x4f60·125 >> 7)` as the 0x18F torque and the kit's cache applies no factor ⇒ **`gp-0x4f60` = −(cache torque) × 1.024**; the kit's
damping convention (positive aggregator counts push toward +wire rate) follows from the rate servo being negative feedback (its feedback
term drives T ∝ −wire rate). Hands-on check: sign(cache torque) = −sign(T) on 95–98 % of hand-on frames ⇒ `gp-0x4f60` carries the same
count sign as T when the driver opposes it ⇒ the driver-opposing taper arm is the "opposite-sign(S, tq)" one (`0xCB8B4`), which on slot 7
is knot-identical to the other, so nothing numeric changes.

**r24 at f0 on the F7 episodes (script section "r24"), aggregator counts, the same frames as §2:**

| | median (range) |
|---|---|
| r24 6–8.5 Hz amplitude | **767 ct** (447–1028); at the stock gain 512 it would be 72 ct |
| r24 ÷ the LKAS lane's own measured T ripple | **1.47** (1.14–1.83) |
| r24 ÷ \|T\| level | 0.90 |
| r24 phase re T | **−132°** |
| r24 phase re wire rate | **−18°** (−10 … −25) — in phase with the wheel rate |
| damping fraction, kit convention (sign ≠ rate) | **0.10** — T's is 0.65 (T re rate ≈ +115°) |
| whole route, engaged: \|r24\| p50 / p90 / p99 | 37 / 176–247 / 784–976 ct; never rails (8192) |
| control, r34 250–264 s hand-on stall | 270 ct, re rate −25°, no 7 Hz line |

**Reading.** With hands off, the bar is the column twist ≈ −J·α of the wheel; a 4-tap difference of it is a jerk term, −ω²·rate at a
single frequency, and the measured phase (−18° re rate) says it lands **in phase with the wheel rate**: under the kit's convention that is
**anti-damping**, at 767 ct, versus the LKAS lane's damping component of ≈ 0.42 × 500 ≈ 210 ct (T at +115°). In the aggregator sum at
7 Hz the engaged-only r24 is ~3.5× the servo's own damping and ~1.5× its whole ripple — a loop closed entirely inside the EPS
(twist → r24 → motor → column → twist), engaged-only, and 10× what Honda ships. **This, not the taper path (0.10 of \|T\|) and not the rate
servo's P term on its own, is now my best candidate for what sustains the 7 Hz strong-turn ripple** [BELIEF: on the sign chain above, each
link EVIDENCE, but the whole has not been closed against the tap — r24 is not on the wire]. Two things argue caution: (a) the kit's
cross-build statistic `accord-lever-b-moves-ratchet-without-spending-authority` found 5244 *less* anti-damped than 512 at 6–9 Hz Re(Z)
(n = 2 vs 7, p 0.056) — a weak, confounded number on a bar×rate cross-spectrum, but opposite in sign to this reading; (b) the plant G = rate/T
identified from the tap already contains r24 closed, so the servo analyses that found "hunting at crossover" were describing the loop
*with* this pump inside it.

**20 Hz creep grind (hands off, per the operator).** The same lane at 20 Hz has 2.9× the gain per raw count (0.5·|1−z⁻⁴| = 0.249 vs 0.088
at 7 Hz), phase +76° re the bar (vs +85°), so the same sign relation holds: in phase with the rate to within ~25°. A 20 Hz twist of only
300 raw would put ~380 ct into the aggregator, engaged-only. The 100 Hz 0x18F torque cannot size the 20 Hz twist reliably from these routes;
the fwloops20 trace's test 1 (tap replay on a creep route) is the discriminator. [BELIEF: r24 is the best-placed 20 Hz candidate by sign,
gain slope and engaged-gating; not sized here.]

### 3c. The 4-tap differencer's own transfer, and the 20 Hz arithmetic

`gp-0x4f62 = 0.5·(bar[n] − bar[n−4])` at 1 kHz. |H| = 0.5·|1 − z⁻⁴| and its phase re the bar:

| f | \|H\| (ct per raw ct) | phase re bar | r24 ct per raw ct at 5244 | at stock 512 |
|---|---|---|---|---|
| 6.6 Hz | 0.0828 | +85.2° | 0.424 | 0.0414 |
| 7.0 Hz | 0.0879 | +85.0° | 0.450 | 0.0439 |
| 7.5 Hz | 0.0941 | +84.6° | 0.482 | 0.0471 |
| **20 Hz** | **0.2487** | **+75.6°** | **1.274** | 0.1243 |

7 Hz, at the episodes' bar ring (1043 / 1595 / 2223 raw): r24 = **469 / 718 / 1000 ct** at 5244, and 46 / 70 / 98 ct at 512.
This closed-form agrees with the per-episode measurement in §3b (medians 767 measured vs 718 closed-form) to within 7 %, which is the
deadband and the clamp. **20 Hz creep, at a bar ring of 140 / 210 / 280 raw: r24 = 178 / 267 / 357 ct at 5244, and 17 / 26 / 35 ct at 512.**
The 20 Hz bar amplitude is an assumption handed to me, not measured — the 100 Hz 0x18F torque cannot carry 20 Hz. [BELIEF]

**Combined driver-side sum at 7 Hz** (all fed by the bar or the rate, none multiplied by the ×6 LKAS gain): r24 **767 ct** + `gp-0x6bbe`
30–45 ct + `FUN_00036682` ~6 ct + r26 (unsized, same sign as r24, gain `0xC6444` = 512 against Honda's ~3072 LERP, so V280 *cuts* it) ≈
**800–820 ct**, of which r24 is ~95 %. The LKAS lane delivers |T| 500–1150 ct with a 400–700 ct ripple. So at 7 Hz the bar-fed lanes carry
roughly **half** of the motor's total 7 Hz content, and the half that is in phase with the wheel rate. [BELIEF — the aggregator sum itself is
not on the wire; only the LKAS lane's `gp-0x6b38` is tapped.]

**The 0x18F ↔ `gp-0x4f60` scale assumption, stated:** raw = wire × 1.024 and sign-inverted, from the frame builder `FUN_00055C42`
(`wire = −(gp-0x4f60·125 >> 7)`) — EVIDENCE for the scale and the sign of the *transmitted* frame. What is **assumed** is that the 0x18F
frame the comma logs is that same builder's output with no further scaling in openpilot's DBC path beyond the ×1.024 the kit applies; the
kit's own memory `accord-wire-torque-is-raw-times-1024` establishes the factor but does not separately verify the DBC sign, and my hand-on
sign check (sign(cache torque) = −sign(T) on 95–98 % of frames) is consistent with it but does not isolate it from the tap's own sign.
A wrong overall sign would not change any amplitude above; it would flip the damping/anti-damping reading, which is the load-bearing claim.

### 3d. The r24 SIGN, settled three ways (orchestrator's request, 2026-09-03)

**(3) Wire test, no sign chain.** On the 18 F7 episodes the 0x18F torque (wire sign) versus the 0x18F rate at f0: coherence 0.78–0.99,
**bar_wire lags the rate by 94°** (median; range −104° … −74°). The bar is therefore ∝ −α of the wheel in wire sign (hands off, the
twist is the wheel's inertial reaction). Using only measured phases, d/dt(bar_wire) re rate = −94° + 90° = **−4°**, or **−9°** with the
4-tap differencer's 5° lag at 7 Hz. So:
- if r24 = **+k·d/dt(bar_wire)** it sits at −9° re the wheel rate → **pumping half-plane** (in phase with the motion);
- if r24 = **−k·d/dt(bar_wire)** it sits at +171° → **damping half-plane**.
The decompile of `FUN_0003aa2c` (0x3ac16–0x3ac58, listing read this session): `r8 = (r1 × gain) >> 10` (`mul r10,r8` / `sar 0xa`), the
±3 deadband (`subr`/`add` against `0xC61F6`), then **`mul r14,r6` with r14 = `ld.b −0x6752[gp]`** (@0x3ab78), clamp ±0x2000 → register
r24 → `add r24,r6` into the aggregator sum (@0x3acca) and `st.h r24,−0x6ada[gp]`. No other negation. With `gp-0x6752` = −1 (kit-verified
three ways), `gp-0x4f62` = +0.5·(gp-0x4f60[n] − gp-0x4f60[n−4]) (`FUN_0007e74a`, decompiled this session: `((cur − old) << 1) / Δt`,
Δt = 4) and **`FUN_00055c42` (decompiled this session) sending the 0x18F torque as `−(gp-0x4f60·125 >> 7)` and the 0x18F rate as
`−gp-0x6a56`**, the chain is r24 = −k·d/dt(gp-0x4f60) = **+k·1.024·d/dt(bar_wire)** → the first case → **pumping**.

The one convention this rests on is *which way positive aggregator counts push the wheel*. Two independent anchors give the same answer:
(a) the LKAS rate servo is negative feedback (it tracks its reference, rate/ref ≈ 1 on these episodes) and its feedback term is
T ∝ +Kp·fb ∝ +gp-0x6a56 = −wire rate, so T-positive must push toward **+wire rate**; this is also what the measured T-re-rate of +114°
requires (a P term on −wire rate through the 16.5 Hz and 5 Hz lags lands at ≈ +100°; the opposite convention would put it near −80°);
(b) Honda's own damper `gp-0x6bd0` = −sign(gp-0x6abe)·M enters the same sum, and gp-0x6abe ∝ −gp-0x6a56 = +wire rate, so it opposes the
wire rate — a damper, as the kit measured (`accord-gate2-damper-phase-passes`), only if aggregator-positive pushes toward +wire rate.
[EVIDENCE for every link above; the only BELIEF is that T's path (gp-0x6b38 → gp-0x6b3c → …) reaches the motor with the same sign as the
aggregator, which the r24-versus-T *ratio* uses but the r24 *sign* does not.]

**(1) V246 and the "protective" statistic.** `docs/BUILD-LINEAGE.md` §V246–V250: **"ALL UNFLOWN"** — V246 (0xC6446 = 7866) was built on
2026-08-30 and never driven. The "protective at the ratchet, p 0.056" is `accord-lever-b-moves-ratchet-without-spending-authority`: a
cross-build regression of the coherence-gated 6–9 Hz **Re(Z)** — the real part of bar/rate in the *driver frame* (carState torque over
carState rate) — Lever B 512 (n = 2 routes) vs 5244 (n = 7) within gain 6×: −73.59 vs −67.78. Three reasons it cannot test r24's sign:
(i) the "512" arm is builds with the gate byte at `c5`, on which r24 runs Honda's LERP (2305 at 50 km/h, 3072 at creep), not 512 — a
1.7–2.3× contrast, not 10×; (ii) the `fb` arm also cuts r26 6× (`0xC6444` = 512 against its ~3072 LERP), so the lane total moved by an
unknown amount (the kit's own formula: (5244 + 512a)/(3072 + 3072a), below stock once a > 0.85); (iii) Re(Z) is the *column's* apparent
impedance seen from the bar, which every loop closed around the column moves indirectly, and its own memory (`accord-rez-sign-frame…`)
warns that a gain change alone shifts it in the observed direction. An 8 % difference at p 0.056 between 2 and 7 routes, on a quantity
two steps removed from r24, is not in conflict with a phase measured directly on 18 episodes at coherence ≥ 0.78. **Both can be right;
neither V246 nor that statistic is a sign measurement of r24.**

**(2) The golden model.** `eps_chain_lanes.py::_inline_torque_rate_b` implements r24 exactly as the disassembly: `scaled = (dtorque ×
gain_q10) >> 10`, ±3 deadzone, `assist_polarity × shaped`, clamp ±0x2000 — **same arithmetic as my chain**. But its `assist_polarity`
defaults to **+1** (`eps_chain_core.py`: "gp-0x6752 assist polarity (−1/0/+1) — SEE THE DEFECT NOTE") while the measured value is −1, and
its docstring lists **"the mechanical loop sign (positive-feedback vs feedforward, needs live telemetry, not disassembly)" as OPEN**. Its
narrative line "MORE r24 DERIVATIVE FEEDBACK = MORE LOOP DAMPING" rests on V87→V88 (6–9 Hz column prominence 0.859× [CI to 0.72], 15–22 Hz
0.549×) — an amplitude contrast on a change that raised r24 ~2× *and* cut r26 6× with `a` unknown, and its own note says the 6–9 Hz half
"CANNOT" be read cross-build. So the golden model neither contradicts the chain nor settles the sign; it defers it to telemetry.

**Verdict on the sign: the anti-damping reading STANDS.** r24 on the car is +k·d/dt(bar_wire), measured at −18° (closed form −9°) from
the wheel rate, in the pumping half-plane under the aggregator convention that both the servo's negative feedback and Honda's own damper
require. Nothing in the record is a phase measurement pointing the other way; the two amplitude statistics that seemed to are confounded
by the r26 cut and by the `c5`-arm misreading. What would flip it: a tap of r24 (or of `gp-0x6b94`) showing it anti-phase to the wire rate,
or a measured `gp-0x6752` ≠ −1 on this car.

### Levers (added), Kp untouched

| lever | class | what it does to r24 at 7 Hz in the episodes | FAIL sentence |
|---|---|---|---|
| **(i) `0x3AA96` `fb` → `c5`** (stock) | 1-byte code edit; the flown state on V101–V103 and every pre-V67 build | r24 falls back to Honda's speed/rate LERP (3072 at creep, less at speed) and r26 back to its LERP: r24 ≈ 450 ct at creep gain (BELIEF: the LERP value at 3–8 m/s not read here), i.e. still ~0.9× the T ripple | *if the F7 ripple/level and the bar ring do not fall by at least the r24 reduction the LERP implies, r24 is not the carrier — but a null here is weak because Honda's own creep gain is only 1.7× below 5244* |
| **(ii) `0xC6446` 5244 → 512** (cal-only, gate byte left `fb`) | one u16, one reader (`FUN_0003aa2c` @0x3ac08); lane stays engaged-selected at the stock flat gain | r24 → **72 ct** (0.14× the T ripple); the taper path and the servo untouched | *if with r24 at 0.1× the F7 episodes persist at ≥ 4 per 100 s with tap ripple/level ≥ 0.4 and the bar still rings ≥ 1000 raw, r24 was not the carrier and the servo P term is; if instead the ripple falls but a slow 2–4 Hz wander appears, r24 was doing Honda's damping job and the sign reading here is wrong* |
| **(iii) `0xC6444` 512 → 3072** (cal-only) | restores r26 toward Honda's creep value while engaged | r26 ≈ r24_stock × 6 × a, a = `gp-0x69a4`/1024 unmeasured — not sized; same sign as r24 | not proposed until `a` is measured |

Lineage note before anyone cuts (ii): V246 flew `0xC6446` at 7866 (×1.5, "protective at the ratchet, p 0.056"); V101–V103 flew the gate at
`c5`; V62 (rate-lane ×2 via `sar`) was the one measured grinding fix and V255/V256 (the same ×2) were undriveable parked and disengaged.
The lane has a history in both directions, which is exactly why a **read-only tap of r24** (or of the aggregator sum) is the cheaper
experiment than either dose.

**Which loop carries what (my current reading, BELIEF unless marked):**
- **7 Hz strong-turn ripple:** the column mode, pumped by the engaged-only r24 (767 ct in phase with the rate) and only weakly damped by
  the rate servo (T at +115°, ~210 ct opposing); the post-PID `0xCBBC4` fade adds 0.10 of \|T\| on top; the setpoint taper does nothing.
  The Kp cap (V281) lowers the servo's contribution but cannot touch r24.
- **20 Hz creep grind (hands off):** r24 by sign and slope, unsized; the D term and the inertia lane are the other candidates the fwloops20
  trace ranks; the tap replay at 20 Hz decides.

## 4. Levers this opens (sized on the same frames, Kp untouched)

**(a) Flatten the live postB `0xCBBC4` (slot 7 record 0xE564C) so the fade starts at the live taper's knee (2560 raw):**
Y (255,243,218,179,77,77) → (255,255,255,255,255,77) with X (16,26,38,48,80,96). Cal-only (12 bytes in the record; no code byte). Readers:
`FUN_00028ea6` only (plus the dead copy). Effect, simulated on the same frames through the live chain:

| where | |T| p50 live → lever | ripple/level |
|---|---|---|
| F7 episodes (median) | **×1.33** (1.11–1.61) | 0.65 → 0.74 (ripple in counts rises with the level; the taper-driven 0.10 is removed, the P-driven part scales up) |
| r34 hands-on frames (\|tq\| ≥ 1216, 19 % of engaged) | 777 → **2264 ct** (×2.9) | — |
| r33 805.8 cliff row (\|tq\| p50 2487) | 798 → **2180** (×2.7) | — |
| r34 172.2 / 747.8 hand-held stalls | 1222 → 1763, 1035 → 1676 | — |
| r34 227.9 (\|tq\| 3336, past 2560) | 732 → 734 | the live taper still cuts idx above 2560–3584 |

**Verdict: do not build it.** It trades a 0.10 ripple fraction for a threefold push against a hand on the wheel across the 1216–2560 raw
window — exactly the operator's override window — and the total ripple in counts goes up, not down.
FAIL sentence: *the build fails if, on a hand-on override at 1500–2500 raw, the tap's |T| rises ×2 or more over V280 rev 2, or if the F7
ripple in counts does not fall.* (It will do both, per the simulation.)

**(b) The opposite direction — steepen/advance the fade — is the "driver torque limits our demand" idea applied deliberately.** It lowers
|T| wherever the bar rings, and it lowers the P-driven ripple with it, but it is a level cut disguised as damping: the multiplier reads the
column twist T itself causes, so it reduces authority in every strong turn, engaged, hands light. Not sized here; it is the wrong lever class
(authority, not damping) for a servo hunting at its crossover.

**(c) V281 rev 2 (Kp flat 341 from idx 24) through the live chain:** sim ripple/level 0.65 → 0.55 (median), taper-driven 0.10 → 0.08. The Kp
cap lowers the P-driven part and leaves the multiplicative fraction where it is. If the multiplier were the carrier, V281 would not help; it is
not the carrier, so V281's effect on the 7 Hz is the P-term effect the kpflat study sized, unchanged by this finding.
FAIL sentence for the taper hypothesis under V281: *if V281 flies and the F7 ripple/level does not fall while the bar ring and m-depth are
unchanged, the P term was not the carrier and this decomposition is wrong.*

## 5. Corrections of record this opens (reports, not licence to act)

0. **`accord-lever-b-is-unreachable` is a statement about the STOCK image.** On V112 and V280 rev 2 the gate byte `0x3AA96` is `fb`, so `0xC6446` = 5244 is reached on every engaged tick; every 'Lever B' measurement on a `fb` build was of a live cell.

1. **`gp-0x6803` is a CAN field, not a mode the ECU chooses** — bits 3:2 of 0xE4 byte 2; openpilot = 0, stock camera = 1, never 2.
   `accord-the-authority-ramp-five-rates` ("mode flag, three values"), `reference-accord-driver-override-curve-kills-lkas-authority`
   ("mode 2 = opposing torque"), and `reference-accord-second-driver-torque-gate-cbae4-cbbc4` ("gate B inert") all read the wrong arm.
2. **The live override taper is `0xCB924`/`0xCB8B4`: 2560 → 3584 raw**, a 1024-count ramp — not `0xCBA74`'s 2240–2560 cliff.
   `accord-override-taper-is-a-cliff-not-a-taper` describes the unselected arm. (V277 flattened all four families, so V277's edit stands.)
3. **The live post-PID gate is `0xCBC34` × `0xCBBC4`, and `0xCBBC4` is a live driver-torque fade from 512 raw**, floor 0.30 at 2048 raw.
   Every mirror that assumed m = 254 (`v280_map_profiles.simulate`, `servo_at_reference`, the loopgain study's `post`) over-predicts |T| by
   ~1/0.7 wherever a hand is on the wheel, which is what the ~0.5 LS slopes were.
4. The `lowcmd_loopgain` header's "postA(|dtq|>>6)" is right in kind (the grab byte is the lagged-torque derivative >> 6, clamp ±0x3200) but
   the live table is `0xCBC34`, not `0xCBB54` (identical contents on slot 7, so no numeric consequence).

## 6. Files

- `rlog-tools/studies/osc-highangle/twist_taper_loop.py` — the script (reads the V280 rev 2 and V281 rev 2 images, the three caches, reuses
  `strongturn_r34` / `v280_map_profiles` for the tap and the chain).
- `rlog-tools/studies/osc-highangle/TWIST-TAPER-LOOP.txt` — full stdout.
- Decompile dump used: scratchpad `FUN_00028ea6.c` (Ghidra, 1308 lines); `FUN_00052676`, `FUN_00021724` decompiled in-session.
