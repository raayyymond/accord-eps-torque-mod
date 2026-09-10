---
name: reference-accord-kp-kd-schedule-axis-is-the-demand-index
description: The Kp (0xE5378) and Kd (0xE511C) LERP records are indexed by the SAME demand index the assist map uses -- idx = |clamp((G*clamp(-4*cmd,±LIM))>>22, ±240)| with G=(taper*255)&0xFFFF -- so 1 idx LSB = 16.1257 wire 0xE4 counts exactly; record layout is X[0] at rec+0x02, Y[0] at rec+0x02+2n; both slot-7 records sit in ONE CRC page 0xE5000.
metadata:
  type: reference
---

**The X axis of the LKAS rate-PID's Kp and Kd schedules is the DEMAND INDEX `idx`** — not |E|, not the
setpoint, not speed. Traced 2026-09-09 on `code.bin` (span `0x29CA8–0x29EC0` byte-identical in V289).

## The index chain (EVIDENCE — `disassemble_bytes` dry_run)

```
0x29032 ld.h -0x69ae,gp,r13   cmd = gp-0x69ae = clamp(wire 0xE4 STEER_TORQUE * -4, ±0x4000)  [FUN_00052676]
0x29036 andi 0xffff,r16,r22   LIM = LERP(0xCB844[sel]) flat: 15360 stock, 16384 V280r2+
0x2903A..0x29044              r22 = clamp(cmd, ±LIM)
0x29A80..0x29CB2              taper = LERP(0xCB924 same-sign | 0xCB8B4 opposite-sign) at gp-0x682f
                              (cliff arms 0xCBA04/0xCBA74 chosen only if gp-0x6803==2; openpilot sends 0)
                              spF = LERP(tp+0x7974 = 0xC6974) = X 4,6,8,10 / Y 255x4  -> FLAT 255
0x29CB4 mulu ; 0x29CB8 andi   G = (taper*spF) & 0xFFFF   (max 65025)
0x29CBC mul  ; 0x29CC0 sar 16 v = (G * r22) >> 16
0x29CD6 sar 6                 v >>= 6
0x29CD8 cmovn -1,r8,r8        r8 = sign(v)  (re-applied to the MAP output only, 0x29D6C mulh)
0x29CDC..0x29CF4              v = clamp(v, -cal(0xC64F1)=240, +cal(0xC64F0)=240)
0x29CFA subr r0,r7            idx = |v|
0x29D12 zxb r22 / 0x29D14     gp-0x674B = idx & 0xFF  -> the ASSIST MAP key (0xC9A88 bank)
0x29DDA st.h r7,-0x697a,gp    gp-0x697a = idx (halfword)
0x29DE8 zxh r7                Kp key = idx & 0xFFFF  (bank 0xCB994 @0x29DC6)
0x29E92 mov r22,r13           Kd key = idx & 0xFF    (bank 0xCB7D4 @0x29E76)
```

**Scale: 1 idx LSB = 2^22 / G / 4 = 16.1257 wire 0xE4 counts at G = 255*255 = 65025.** idx 240 lands at
3870 counts, a hair past the 0xE4 field's own ±3840 saturation. openpilot's 123-count slew cap = 7.63 idx
per 100 Hz frame. G measured 65025 at p10/p50/p90 engaged on r62/r63/r5e (taper < 255 on 1.4–2.9 % of frames).

**Bypass:** `gp-0x682f > cal(0xC64B8)=112` jumps to `0x29CC4` which sets `r7 = 0` — an override drives the
schedule to knot 0, it does not freeze it.

## Record layout — do NOT read it as "u32 n then X then Y"

`n` (u16) · `X[0..n-1]` · `Y[0..n-1]` · 2-byte pad. **X[0] at rec+0x02, Y[0] at rec+0x02+2n.**
`0x29DDE sld.hu 0x2,ep,r9` (X[0]) and `0x29DE2 add 0xc,r10` (&Y[0] for n=5) settle it. The naive u32-header
split ALSO fits the bytes and gives a different, wrong X/Y — I nearly published it. X[0] is always 0.

| record | bank | slot 7 | n | stride | X | Y stock | Y V281r3→V289 |
|---|---|---|---|---|---|---|---|
| Kp | 0xCB994 | 0xE5378 | 5 | 24 B | 0,68,112,136,208 | 248,512,645,696,696 | 248 x5 |
| Kd | 0xCB7D4 | 0xE511C | 4 | 20 B | 0,11,22,32 | 128 x4 | 128 x4 |
| map | 0xC9A88 | 0xE502C | 10 | 44 B | 0,12,20,24,32,64,96,128,160,240 | 0,24,42,50,62,100,126,154,166,172 | ...,1032 |

Y byte offsets: Kp `0xE5384/86/88/8A/8C`, X `0xE537A/7C/7E/80/82`. Kd Y `0xE5126/28/2A/2C`, X `0xE511E/20/22/24`.
**Both slot-7 records are in the SAME CRC page `[0xE5000, 0xE5FFC)` (slots 6–11) — a combined Kp+Kd edit
costs ONE trailer.** Pages: 0xE4000 (0–5) · 0xE5000 (6–11) · 0xE6000 (12–17) · 0xE7000 (18–23) · 0xE8000 (24–27).

🛑 `divq` divides by the SEGMENT WIDTH X[i]−X[i−1] — X must be strictly increasing. No Y is ever a divisor.

## Kd is unschedulable above idx 32

`0x29EA0 sld.hu 0x6,ep,r10` = X[3] = 32 is the high-clamp test; above it the lookup returns Y[3] flat.
Kp's non-zero knots (68/112/136/208) all sit **above the p90 of engaged demand** — see
[[reference-accord-demand-index-distribution-on-the-wire]].

## Banks that are NOT this axis

`0xCBAE4`/`0xCBBC4` (post-PID fade, key gp-0x682f = |driver torque|>>5), `0xCBB54`/`0xCBC34` (post-PID fade,
key gp-0x6830 = grab rate), `0xCB924`/`0xCB8B4`/`0xCBA04`/`0xCBA74` (setpoint taper, key gp-0x682f).
All driver-torque/grab-rate axes. Confusing them with the demand axis is easy and would be wrong.

## The tp trap bit again (5th+ recurrence)

I read the clamps at `0xC71BC` before catching it. `tp = 0xBF000` ⇒ `tp+0x71BC = 0xC61BC` = P clamp 15360,
`tp+0x71B6 = 0xC61B6` = D clamp 10240, `tp+0x71BE = 0xC61BE` = sum clamp 15360, `tp+0x73E6 = 0xC63E6` = Ki.
`tp+0x74F0/F1 = 0xC64F0/F1` = ±240. Anchor against a known kit constant before trusting any tp read.

Related: [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] · [[reference-accord-op-0e4-steer-command-full-path]]
· [[reference_accord_ki0_pd_loop_explains_amplitude_gain_curve]]
