---
name: accord-lkas-pid-pid-register-map-and-taper
description: CORRECTS the record's P/I/D register mapping at 0x29F18 (r2 is the INTEGRATOR, not P); P = (E*Kp)>>8 clamp 0xC61BC; newly found I-deadband 0xC62E4 and I-clamp 0xC61BA; the always-on x254/256 override taper that makes the delivered rail 2462 not 2481
metadata:
  type: reference
---

## 1. 🛑 The sum's three registers were swapped in the record

`TRACE-2026-09-13-fb-lag-filter-bytes.md` §4 reads `0x29F18 sar 0x7,r2` as **P** and `r9` as I. **It is
the other way round.** From `decompile_function(0x28ea6)`:
`iVar16 = (iVar16 >> 7) + uVar13 + uVar33`, where `iVar16` is the clamped integrator, `uVar13` the
clamped P and `uVar33` the clamped D.

```
0x29F18  sar 0x7,r2      r2 = I  (the INTEGRATOR), >>7
0x29F1E  add r9,r2       r9 = P
0x29F24  add r8,r2       r8 = D
0x29F2A  mov r2,r22      -> gp-0x6b34  (the PID sum)
0x29F2E  mov r8,r27      -> gp-0x6b36  (D)
                         P -> gp-0x6b32
```

**P is formed separately**, `disassemble_bytes(0x29E2C, 44, dry_run:true)`:
```
29E34 mov r16,r8        r16 = E
29E36 mul r9,r8,r0      r8 = E * Kp
29E3A ld.hu 0x71bc,tp   P clamp = [0xC61BC] = 15360
29E3E sar 0x8,r8        ** >>8, NOT >>7 **
```
⇒ `P = clamp((E*Kp) >> 8, ±[0xC61BC])`. At Kp = 248 that is `E × 0.96875`.

## 2. The integrator, with two cals the record's cell list does not carry

```python
e5   = E >> 5
DB   = [0xC62E4] = 4                      # a DEADBAND on E>>5.  Readers 0x29D6E/84/8C/96 (4 live, 3 dead)
exc  = e5-DB if e5 > DB else (e5+DB if e5 < -DB else 0)
ICL  = ([0xC61BA] << 10) >> 3             # 10240 -> 1,310,720
I    = clamp((I_state >> 3) + ((exc * Ki) >> 3), ICL)     # Ki = [0xC63E6] = 0
I_state = I << 3                          # gp-0x6dd0 holds 8*I  (0x29DA4 ld.w / 0x2A190 st.w)
```
The `>>3` on both sides plus the `<<3` on store is a plain integrator, **not** a leak.

## 3. The override taper is NEVER unity — x254/256 always

```
factor = ((A * B) & 0xFFFF) >> 8 ;  S = (factor * S) >> 8
A in {0xCBB54, 0xCBC34}  axis |bar-derivative| ;  B in {0xCBAE4, 0xCBBC4}  axis speed gp-0x6a5e
```
Records for selector 7, read from the images (identical stock/V282/V292):

| table | record | X | Y |
|---|---|---|---|
| A `0xCBB54` | `0xE55A4` | `[0,3,6,8,10,20]` | `[255,255,255,255,255,205]` |
| B `0xCBC34` | `0xE56F4` | same | **identical to A** |
| C `0xCBAE4` | `0xE54FC` | `[24,45,64,80,96,112]` | `[255,205,164,125,90,51]` |
| D `0xCBBC4` | `0xE564C` | `[16,26,38,48,64,96]` | `[255,243,218,179,77,77]` |

**A ≡ B**, so the `bVar1` selector only ever chooses between the two *speed* tapers. At rest the factor
is `(255·255 & 0xFFFF)>>8 = 254`, so **×254/256 = 0.9922 applies even with no driver torque and no
speed.** That is why the delivered rail is **2462**, not the 2481/2505 the record quotes. Table layout
for these six-knot records: X at `rec+2 … rec+0xC`, **Y at `rec+0xE … rec+0x18`** (not `rec+0x16` — that
layout belongs to the 10-knot assist map).

## 4. Other record layouts, confirmed by reading the walk code

| family | ptr array | X | Y | knots |
|---|---|---|---|---|
| assist map | `0xC9A88` → `0xE502C` | `rec+2 … rec+0x14` | `rec+0x16 … rec+0x28` | 10 |
| Kp | `0xCB994` → `0xE5378` | `rec+2 … rec+0xA` | `rec+0xC … rec+0x14` | 5 |
| Kd | `0xCB7D4` → `0xE511C` | `rec+2 … rec+8` | `rec+0xA … rec+0x10` | 4 |
| cmd LIM vs speed | `0xCB844` → `0xE51A8` | `rec+2 … rec+0x12` | `rec+0x14 … rec+0x24` | 9 |

**Kd is `[128,128,128,128]` on stock as well as V282/V292 — it is flat everywhere, not just on the
modded builds.** The "driver-activity" factor folded into the demand-index gain
(`tp+0x7976..0x7984` = `0xC6976..0xC6984`, axis `gp-0x6830`) is **flat at 255**, so the recorded
`idx = |clamp((G·cmd)>>22, ±240)|` needs no correction.

## 5. The DC number the pole actually sets

`DC = 2b/(1024−a)`; at steady state `E = 0` ⇒ `32·sp = DC·x`, so

```
commanded wheel rate = 32·sp / (DC × 8 counts-per-deg/s)
                     = 0.12951 deg/s per sp count (V282, DC 30.8911)
                     = 0.12943 deg/s per sp count (V292, DC 30.9032)
```
**This is what "DC-held" buys: the rate reference scale is untouched by the pole move.**

See [[accord-0x2a0c6-is-a-damper-mode-and-data-boot-values]] and
[[accord-v279-is-the-built-never-flown-torque-mode]].
