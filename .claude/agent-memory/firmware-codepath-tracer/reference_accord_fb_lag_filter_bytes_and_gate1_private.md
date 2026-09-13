---
name: accord-fb-lag-filter-bytes-and-gate1-private
description: "The LKAS feedback-lag filter at 0x28F4C-0x28FBE decoded byte-exact (32-bit state gp-0x3d30, a is ld.h SIGNED so capped 32767, two SEPARATE sar 0xa floors); 0xC63E8/0xC63EA have exactly ONE reader each and the state cell exactly TWO accesses image-wide -- GATE 1 passes by both methods."
metadata:
  type: reference
---

`FUN_00028ea6` @ `0x28F4C–0x28FBE`, verified 2026-09-13 on `code.bin` (and byte-identical in V282).

```
28F4C ld.h  -0x6a56[gp],r7   x = SIGNED 16-bit rate, ALREADY saturated +-12000 by its producer
28F50..28F58                 |x|<=12000 plausibility BAIL (jr 0x290B0) -- a BAIL, not a clamp
28F66 ld.bu -0x3d2c[gp],r9   SENTINEL; s is loaded only if it reads EXACTLY 1
28F7C ld.w  -0x3d30[gp],r26  s   <-- STATE CELL, 32-BIT (ld.w / st.w)
28F86 ld.hu 0x73ea[tp],r16   b = [0xC63EA] = 1560   UNSIGNED (cap 65535)
28F8A ld.h  0x73e8[tp],r9    a = [0xC63E8] =  923   ** SIGNED (ld.h) -> a is CAPPED AT 32767 **
28F8E mul   r16,r7,r0        low32(x*b), high word discarded into r0
28F92 mul   r26,r9,r0        low32(s*a), high word discarded into r0
28F9A sar   0xa,r7           floor(x*b/1024)   <-- SEPARATE floor
28FA0 sar   0xa,r9           floor(s*a/1024)   <-- SEPARATE floor  (NOT one floor of the sum)
28FA2 add   r7,r9            s_new
28FA4 add   r9,r26           out = s_old + s_new   <-- the two-sample sum
28FA8 st.w  r9,-0x3d30[gp]   state := s_new only
28FA6..28FBC                 clamp out to +-[0xC62E6]  (ld.hu; V282 = 46080, stock = 7680)
```

`DC = 2b/(1024-a)`; at (923,1560) that is `3120/101 = 30.8911` exactly.
`f_c = -ln(a/1024)/(2*pi*Ts)` with **`Ts = 1 ms`** — EVIDENCE-BY-CONSISTENCY, two label/byte
agreements: stock `a=923` -> 16.53 Hz ("16.5 Hz" in the record), V289's byte-read `a=875` -> 25.03 Hz
(its own tag `FBPOLE.25HZ`). Not a scheduler read.

## GATE 1 — the cal cells and the state cell are PRIVATE (both methods, empty set-difference)

Two-encoding raw Python scan (4-byte disp16 with the per-opcode parity rules + the 6-byte extended
form + absolute-LE32 + movhi/movea) over the whole 1 MiB image:

| cell | readers | writers |
|---|---|---|
| `tp+0x73E8` = `0xC63E8` (`a`) | **1** — `0x28F8A` | 0 |
| `tp+0x73EA` = `0xC63EA` (`b`) | **1** — `0x28F86` | 0 |
| `gp-0x3d30` = `0xFEDF42D0` (state `s`) | 1 `ld.w` `0x28F7C` | 1 `st.w` `0x28FA8` |
| `gp-0x3d2c` (sentinel) | 1 `ld.bu` `0x28F66` | 1 `st.b` `0x290D4` |
| `gp-0x3d34` (sibling state) | 1 `ld.w` `0x28F78` | 1 `st.w` `0x29080` |

Ghidra agrees independently: `search_instructions(operand_pattern="0x73e8")` -> `match_count 1`,
`0x28F8A`, 183,576 instructions scanned. No LE32 `0x000C63E8`/`0x000C63EA` anywhere; no movhi/movea
pair; no table base in `[0xC6300,0xC6400)` from which a LERP stride could reach them.

**Flight precedent read from the image, not a build script:** `_v289_..._plain_image.bin` carries
`0xC63E8 = 875`, `0xC63EA = 2301` (DC 30.886, -0.02 %) and page CRC `0xC6FFC = fe780477`; it flew on
r62/r63 with no fault. See [[accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature]].

## Scanner discipline that made the null trustworthy
The scanner was **positively controlled on cases it was not told about**: it reproduced all 30
`gp-0x6a56` accesses (25 ld.h + 4 st.h + 1 ld.bu), both output-lag pole pairs (`0xC63EC` @ `0x2A184`
/ `0x2A8A2`, `0xC63EE` @ `0x2A174` / `0x2A892`, i.e. V289's notch hook AND the known orphan
duplicate), and the 4 six-byte `gp-0x6752` accesses at `0x48E56`-`0x48E88`. A scan that only finds its
own control proves nothing. See [[accord-gp4f60-two-encodings-enumeration-trap]].

## Build-script musts
`a <= 1023` (at 1024 the pole is exactly 1); `a <= 32767` (ld.h); `b <= 65535`; recompute the page CRC
at `0xC6FFC`; re-run the privacy census **on the built image** (a null from stock is not a null for a
modded build); do not raise `0xC61BE` above 32767 (`ld.hu` at `0x2A142` vs `ld.h` at `0x2A146`).
Anything writing `gp-0x6a56` must also write the lockstep mirror `gp-0x4ca6` (`0x3F7BC`/`D4`/`E4`/`822`).

Full trace: `docs/traces/TRACE-2026-09-13-fb-lag-filter-bytes.md`.
Related: [[accord-fb-filter-sentinel-reset-runs-disengaged-and-deadzone]],
[[reference_accord_lkas_pid_filter_form_two_sample_sum_and_oscillation_detector]],
[[reference_accord_fb_operand_clamp_46080_overflows_a_q14_notch]].
