---
name: reference-accord-lkas-driver-torque-taper-cascade-and-gp69b0-q15
description: "The LKAS controller output is multiplied by TWO cascaded driver-torque-indexed Q8 curves at 0x2a0b4 (mulu/andi/sar8/mul/sar8) before the +-0xC61BE clip -- Y[0]=255 (transparent) hands-off, falling to 77-51/255 hands-on, starting at raw torque 512-768 not 2240. All four tables VIRGIN on 103 images. Also corrects my own claim that gp-0x69b0 is 'a GATE not a multiplier': it is a Q15 multiplier at 0x2a1ee and it structurally gates the WHOLE LKAS controller block."
metadata:
  type: reference
---

# ⭐⭐ THE LKAS LANE HAS A SMOOTH DRIVER-TORQUE TAPER THAT STARTS AT A LIGHT HAND

Found 2026-08-27 (`ratchet` task, hands-off/engagement mechanism hunt) on stock `code.bin`.
This is **distinct from, and upstream of, the already-recorded override curve** in
[[reference-accord-driver-override-curve-kills-lkas-authority]] — that one is a 254→0 cliff at raw
2240–2560 on a *different* lane. This one is a smooth cascade on the **LKAS lane itself**.

## The site — byte-verified [EVIDENCE]

`FUN_00028ea6`, inside the block guarded by `gp-0x69b0 != 0` (i.e. engaged only):

```
0x2a0b4  mulu  r9, r23, r0        e9bf2202   ; r23 = A * B      (both Q8, 0..255)
0x2a0b8  andi  0xffff, r23, r12   d766ffff   ; & 0xFFFF         (max 255*255 = 65025, safe)
0x2a0bc  sar   0x8, r12           a862       ; >> 8
0x2a0be  mul   r2, r12, r0        e2672002   ; * r2  = the LKAS controller output (PID/corridor)
0x2a0c2  sar   0x8, r12           a862       ; >> 8
0x2a0c4  br    0x0002a13e                    ; -> clamp +- cal(0xC61BE) = 15360
```

⇒ `LKAS_cmd = ( ((A*B & 0xFFFF) >> 8) * PIDout ) >> 8`, i.e. **a multiplicative authority
factor ≈ (A/256)·(B/256)**, applied **before** the 15360 clip and before the `0xC646C`=891 (1.000×)
forward scale. Live pointer-array reads: `0x29ff0`/`0x29ff6` (`0xCBAE4`) and `0x2a052`/`0x2a058`
(`0xCBBC4`). The twins in `FUN_0002a93a` (`0x2aed8`, `0x2af38`) are **dead** (no callers).

## The four tables — mode 7, read LE from stock `code.bin` [EVIDENCE]

Arm selected by `bVar1 = (gp-0x6803 == 2)`. Record layout: `+0x00` count(=6), `+0x02..0x0C` six X
shorts, `+0x0E..0x18` six Y shorts.

| factor | ptr array | mode-7 record | X | Y | index |
|---|---|---|---|---|---|
| **B** (`==2`) | `0xCBAE4` | `0xE54FC` | 24, 45, 64, 80, 96, 112 | **255**, 205, 164, 125, 90, **51** | `gp-0x682f` |
| **B** (`!=2`) | `0xCBBC4` | `0xE564C` | 16, 26, 38, 48, 64, 96 | **255**, 243, 218, 179, 77, **77** | `gp-0x682f` |
| A (`==2`) | `0xCBB54` | `0xE55A4` | 0, 3, 6, 8, 10, 20 | 255, 255, 255, 255, 255, **205** | `gp-0x6830` |
| A (`!=2`) | `0xCBC34` | `0xE56F4` | 0, 3, 6, 8, 10, 20 | 255, 255, 255, 255, 255, **205** | `gp-0x6830` |

🛑 **ALL FOUR ARE BYTE-IDENTICAL TO STOCK ON ALL 103 `_v*_plain_image.bin` FILES.** No build has ever
touched them. (Mode 0 records carry the same numbers.)

### The B axis is byte-verified driver column torque; the A axis is NOT
```
0x29048  mov  r15, r7      ; r15 = gp-0x4f60 (Sensor-B driver column torque), loaded @0x28f26
0x2904a  sar  0x5, r7
0x2904c  bp   0x29050
0x2904e  subr r0, r7       ; => |t| >> 5      (abs AFTER the shift)
0x29064  cmovc r16, r7, r8 ; saturate at 255
0x29068  st.b r8, -0x682f, gp
```
⇒ **`gp-0x682f = min(|gp-0x4f60| >> 5, 255)` ⇒ X·32 = raw torque counts.** ✔

⚠ **`gp-0x6830` is NOT `|t|>>6`.** At `0x290c4` (`shr 0x6, r8`) the source `r28` is
`|clamp( ((r15>>5)+(r6>>5) − r6) >> 4 , ±12800 )|` built at `0x2906c–0x29098`, where `r6` carries a
cross-cycle accumulator (`st.w r14, -0x3d34, gp` @`0x29080`) and both `mul` sites at `0x29052`/`0x2905c`
multiply by *previous-cycle* sign flags. **The A-arm axis is UNRESOLVED — do not label it raw torque.**
(`TRACE-2026-08-20-lkas-command-range.md:213`'s "`>>5` / `>>6`" shorthand is right about the shift and
misleading about the operand.)

## The taper, mirroring the integer arithmetic exactly [EVIDENCE]

`factor = (((A*B) & 0xFFFF) >> 8) / 256`, A pinned at its low-index value 255:

| raw \|t\| | `gp-0x682f` | B (`==2`) | factor | B (`!=2`) | factor |
|---|---|---|---|---|---|
| 0–768 | 0–24 | 255 | **0.992** | 255→245 | **0.992→0.953** |
| 1000 | 31 | 238 | 0.926 | 232 | 0.902 |
| 1229 | 38 | 221 | 0.859 | 218 | 0.848 |
| 1536 | 48 | 198 | 0.770 | 179 | 0.695 |
| 1800 | 56 | 181 | 0.703 | 128 | 0.496 |
| **2048** | 64 | 164 | 0.637 | **77** | **0.297** |
| ≥3584 | ≥112 | 51 | 0.195 | 77 | 0.297 |

If A also falls to its own floor 205, multiply every factor by 0.804.
⇒ **Hands-off the LKAS lane is TRANSPARENT (0.992). Hands-on it is tapered 1.2–3.3×, and the taper
begins at raw 512–768 — a light hand, not the 2240 firm push of the override curve.**

## ⚠ `gp-0x6803` is NOT the engagement flag
`FUN_00052676` @`0x526ac`: `gp-0x6803 = (byte)(((uint)bVar4 << 0x1c) >> 0x1e)` where
`bVar4 = *(byte*)(gp-0x1426)` ⇒ **bits [3:2] of a CAN-derived config byte**, values 0..3, forced to
`0xFF` on several fault paths. Boot value 0. Which arm is live on our car is **UNRESOLVED** — but both
arms are transparent at Y[0]=255 and both taper, so the qualitative finding is robust to it.
`gp-0x1426` still has zero found writers ([[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]]).

## 🛑 SELF-CORRECTION: `gp-0x69b0` IS a Q15 MULTIPLIER, not merely a gate
My own `reference_accord_mode_column_ramp_gp69b0_disengage_delay` says *"`gp-0x69b0` is a GATE not a
multiplier (zero `mul` found on it anywhere traced)"*. **That is wrong.** In `FUN_00028ea6`:
```
LKAS_lane = (short)(( IIR_out * (uint)*(ushort*)(gp-0x69b0) ) >> 15)     ; at LAB_0002a1ee
gp-0x697e = 0x400 - ((gp-0x69b0 * (0x400 - cal)) >> 15)                  ; two more Q15 uses
```
It spans **0 → 0x8000 = 32768 = 1.000 in Q15** (consistent with the 5 ramp rates: 32768/328 = 100 ticks
= 100 ms; 32768/16 = 2048 ticks = 2048 ms, and with the independently-decoded `0x8000` full scale).
Read **unsigned**, so the −32768 end also reads 32768.

⭐ **And it is a STRUCTURAL engaged/manual switch, not just a gain:** the guard
`if (((gp-0x69b0 != 0) || (cal(0xC64E2) == 1)) && bVar3)` wraps the *entire* LKAS command-formation
block — the PID with its `gp-0x6cf8`/`gp-0x6dd0` int32 integrator states, both taper LERPs, the
`0xC61BE` clip. `cal(0xC64E2) = 5`, so that disjunct is dead. **Manual ⇒ the block does not execute,
the else-arm sets the lane to 0, and `gp-0x3d3c`'s IIR decays to zero.**

## The rest of the tail, anchored [EVIDENCE]
```
clip ±cal(0xC61BE)=15360 @0x2a13e  -> gp-0x3d3c IIR: s[n] = (cal(0xC63EC)=992)/1024·s[n-1]
                                                          + (cal(0xC63EE)=507)/1024·x[n];  out=(s[n-1]+s[n])>>5
  -> deadband cal(0xC61B8)=102 + sign-guard vs gp-0x6b30, enabled by cal(0xC64A3)=1 AND gp-0x6806==0
  -> × gp-0x69b0 >>15                                   (LAB_0002a1ee)
  -> + iVar28 (base-assist arm)  × (char)gp-0x6752 = −1 × cal(0xC646C)=891  >>15
  -> clamp ±cal(0xC61B4)=512  -> gp-0x6b38 -> gp-0x6b3c
```
✔ Cross-check that validates the whole read: `(15360 × 891) >> 15 = 417`, exactly the recorded stock
V9 maximum, and 417 < 512 — which is *why* `0xC61B4`/`0xC61B2` measured 0 % of the effect.

## 🛑 Two tool traps hit this session
1. **`get_xrefs_to(0xFEDF17D1)` returned "No references found"** for `gp-0x682f` — a **FALSE ZERO**.
   The Python dual-encoding scan found **12** accesses (2 writers `0x29068`/`0x290b8`, 10 readers).
   The gp-relative blind spot again.
2. **I nearly made off-by-0x1000 #6**: wrote `tp+0x71b4` as `0xC71B4` and got −20418. `tp = 0xBF000`
   ⇒ `0xC61B4` = 512. **The implausible value is the tell — anchor on a known cal immediately.**

Links: [[reference-accord-driver-override-curve-kills-lkas-authority]] ·
[[accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee]] ·
[[accord-fprime-compression-explains-v89-and-v97]] · [[reference_accord_c61be_gate1_clean_ladder_and_arb_curve_inputs]]
