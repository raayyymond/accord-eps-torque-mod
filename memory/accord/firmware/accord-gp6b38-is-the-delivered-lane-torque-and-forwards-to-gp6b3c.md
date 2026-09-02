---
name: accord-gp6b38-is-the-delivered-lane-torque-and-forwards-to-gp6b3c
description: gp-0x6b38 = clamp(-lane x 5346 >> 15, +-0xC61B4) exactly, stored every tick by `st.h r1,-0x6b38,gp` @0x2A23C -- the LKAS lane's delivered torque. The term added before the gain (gp-0x6b2c, a 4-state ramp keyed on speed gp-0x6a5e) is PROVABLY ZERO: its LERP table tp+0x7736..0x7744 is all-zero (= stock) AND its gate gp-0x6809==1 can never be true (no writer in the image). Ghidra's search_instructions found 3 of 5 accesses: the 4th is a dead writer @0x2A934 (tail-duplicate blob, gain 891), the 5th is a LIVE forwarding copy @0x2B418->st.h -0x6b3c @0x2B41C -- the first byte-level link from the lane's output toward the motor path. V279's CAN-427 tap carries it as (sign(T)<<9)|(|T|>>3).
metadata:
  type: reference
---

# `gp-0x6b38` is the delivered lane torque, and it forwards to `gp-0x6b3c` -- 2026-09-02 [EVIDENCE]

```
0x2a1e6  mul r14,r9 ; sar 0xf ; sxh      r9  = lane lag readout x engagement ramp (Q15)
0x2a1fc  add r9,r11                       r11 = r9 + gp-0x6b2c          <-- gp-0x6b2c == 0 ALWAYS (below)
0x2a1fe  mul r13,r11 ; sar 0xf            x (gp-0x6752 = -1) x 5346 (0xC6CD0) >> 15
0x2a204..0x2a220  clamp +-0xC61B4 (3072)
0x2a226  mov r11,r1 ; 0x2a23c st.h r1,-0x6b38,gp      stored unconditionally, single return path
```
**`gp-0x6b2c` is zero on every path, by two independent mechanisms** (`adv279c`, dumped from V268 with the tp anchor
`tp+0x71b4`=3072 confirmed): the ramp LERP table `tp+0x7736..0x7744` = `0000 807c c07c 007d 0000 0000 0000 0000`
(X 31872/31936/32000, **every Y = 0**, byte-identical to stock); and the branches that compute it are gated by
`*(gp-0x6809) == 1`, which [[eps-deliver-cut-gp6809-broken]] (2026-07-14) established has ZERO writers image-wide.
Either alone keeps it inert. => **T = clamp(-lane x 5346 >> 15, +-3072), no additive term, no transient.**

**Census, subop-validated raw LE scan (hw2 0x94C8 + subop 0x39/0x3B + base r4) -- `search_instructions` found 3 of 5:**
| site | what | status |
|---|---|---|
| `0x2A23C` `st.h r1` | the live writer | FUN_00028ea6 |
| `0x2A934` `st.h r12` | second writer, same clamp shape, gain `tp+0x746c` = 891 (stock's cell) | in the tail-duplicate blob `0x2A892-0x2A93A` before FUN_0002a93a; no jump/pointer/switch reaches it -- dead |
| `0x4E8D2`, `0x4E8E2` `ld.h` | UDS diagnostic record (FUN_0004e82e, bytes 7-8 BE) | readers |
| **`0x2B418` `ld.h` -> `0x2B41C` `st.h r15,-0x6b3c`** | `gp-0x6b3c = r16 ? gp-0x6b38 : 0`, then clamp logic vs `tp+0x71b2` | **LIVE forwarding copy; function at 0x2B3E8 (no Ghidra function), called from FUN_0001b33e @0x1B36A** |

FUN_00028ea6 is `void` -- the lane's output leaves it ONLY through this cell. The next hops toward the motor are: what
sets r16 at 0x2B40E, and who reads `gp-0x6b3c`. **Two Ghidra-blind regions (0x2A892-0x2A93A, 0x2B3E8-) -- always
census by raw scan.**

**V279 replaces V112's `gp-0x6abc` tap on CAN 427** (V268's window loads -0x6ABC, not stock's -0x6c18). Decode:
`T = (-1 if wire>>9 else 1) * ((wire & 0x1ff) << 3)`; 2505 reads 313; `sign(T) == -sign(0xE4 cmd)` on every engaged,
in-taper, ramped frame under pure feedforward.
