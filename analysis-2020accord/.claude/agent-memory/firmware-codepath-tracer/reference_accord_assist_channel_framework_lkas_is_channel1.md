---
name: reference-accord-assist-channel-framework-lkas-is-channel1
description: The EPS has an 11-slot assist-request framework (FUN_00025c32 register / FUN_00026c80 mix); LKAS is CHANNEL 1 and its torque is the +-0x2800 field. Cal 0xC4124 routes each channel to gp-0x6b4c (aggregator) or gp-0x6b4e/gp-0x6afe (direct injection past the governor). Both destinations are observer lanes at unity gain.
metadata:
  type: reference
---

Traced 2026-08-10 on Ghidra `/code.bin` (stock `39990-TVA-A160`). tp anchor verified (`0xC40D2`=102,
`0xC40BC`=600) before any tp claim.

## The framework

`FUN_00025c32` is a **registration API for 11 assist-torque channels**. `param_1` is a stack struct:

| offset | field | clamp | destination array |
|---|---|---|---|
| +0 | channel id (0..10) | — | — |
| +1 | channel command/state (0..5) | — | `gp-0x61a0+i` (runtime state byte) |
| +2 | torque field **A** | ±0x4000 | `gp-0x62e0+2i` |
| +4 | torque field **B** | ±0x2800 | `gp-0x62f8+2i` |
| +6 | torque field **C** | ±900 | `gp-0x6274+2i` |
| +8 | **field D — the DECLARED-DISTURBANCE slot, see below** | ±20000 | `gp-0x633c+2i` |
| +10/12/14 | gains | 0..0x400 | `gp-0x6230 / -0x6218 / -0x6200 +2i` |

`FUN_00026c80` (0x26c80-0x27801) is the **mixer**. Its first loop switches on a **static per-channel
routing MODE byte** at cal `tp+0x5124` = **`0xC4124..0xC412E`**, byte-read stock = **[0,0,5,0,5,5,0,0,0,5,0]**.
Per-channel ENABLE at `0xC4118..0xC4122` = all 1.

- **mode 0** -> field B goes to `gp-0x62b0+2i`, `gp-0x62c8+2i = 0`
- **mode 5** -> field B goes to `gp-0x62c8+2i` (**direct injection**), `gp-0x62b0+2i = 0`

Two sums come out:
- `Sigma gp-0x62b0` -> `gp-0x3d88` -> **`gp-0x6b4c`** (clamp ±0x2800), stores @`0x276f0/0x27708/0x27716`
- `Sigma gp-0x62c8` -> `gp-0x3d8c` -> **`gp-0x6b4e`** (clamp ±0x2800), store @`0x27466`, and the same value
  is passed to `FUN_00042ac6` @`0x277f6`, which writes **`gp-0x6afe`** @`0x42ad6` — read once at `0x43ae0`
  and **added straight into the final motor command in `FUN_00042af8`, past the governor and corridor**.

`gp-0x6b4c`'s second term is gated by cal **`0xC63CC` = 0** in stock, so it is a pure channel sum.

## LKAS is CHANNEL 1

`FUN_0002b422` (the 8-state ENABLE FSM), disassembled:
```
0002b42e: ld.h -0x6b3c[gp],r12     <- arbitrated LKAS torque from FUN_00028ea6 @0x2a2ea
0002b42a/36/3c/46: clamp r12 to +-u16(0xC61B2)
0002b45c: st.h r12,-0x6b3a[gp]     <- clamped mirror (useful repoint source)
0002b51e: st.b r14,-0x67a4[gp]     <- ENABLE byte
0002b522: mov 0x1,r10 -> sst.b r10,0x0[ep]   ** CHANNEL ID = 1 **
0002b52c: sst.h r12,0x4[ep]                  ** field B = THE LKAS TORQUE **
   (fields A/C/D all written as r0 = 0)
0002b53e: jarl 0x00025c32,lp
```
Channel 1's mode byte (`0xC4125`) = **0** => LKAS lands in `gp-0x6b4c`.

## Why it matters

`gp-0x6b4c` is read by exactly two assist consumers: the aggregator `FUN_0003aa2c` @`0x3aa3e`, and **the
disturbance observer `FUN_00038148` @`0x3816c` at unity gain (cal `0xC63AA` = 1024)**. So the LKAS command
is a KNOWN INPUT to the observer — see [[reference-accord-observer-filter-mismatch-leaks-the-command]] for
where it nonetheless leaks back in.

## ★★ FIELD D IS THE OBSERVER'S DECLARED-DISTURBANCE INPUT (resolves `gp-0x3d90`)

```
field D -> gp-0x633c+2i                                    (FUN_00025c32)
        -> gp-0x6324+2i   in modes 0,1,2,3,5; forced 0 in modes 4,6,7  (FUN_00026c80 loop 1)
        -> SUM over all 11 channels, *** UNGATED by the enable byte *** (FUN_00026c80 loop 2)
        -> gp-0x3d90 (32-bit) -> clamp +-20000 -> gp-0x6bfa  st.h @0x273b0/0x273c8/0x273d6
        -> FUN_00038148 @0x38208 :  res = (model - recon) + gp-0x6bfa
```

**Why it is a declared-disturbance slot, not another torque lane** [EVIDENCE]:
- Fields A/B/C carry **command-side** clamps (±0x4000, ±0x2800, ±900). **Field D's clamp is ±20000 —
  bit-for-bit the model's OWN output clamp** at `gp-0x6bf6`/`gp-0x6bfc` (`0x3ba96`/`0x3bbce`) ⇒ it is
  denominated in **observer units**, not command units.
- It is the only one of the four summed **without** the per-channel enable gate.
- Its sole destination is the residual sum.

⇒ Every assist channel can declare *"expect this much torque I am applying that your reconstruction cannot
see."* **LKAS passes ZERO** (`0002b530: sst.h r0,0x8[ep]`, bytes `84 04`) — and that is **correct as
shipped**, because LKAS's torque is already in the reconstruction via `gp-0x6b4c` at unity; filling field D
would double-count it.

**One-byte edit derived for the record, NOT recommended.** Format IV resolves as
`hw = (reg2 << 11) | 0x480 | (disp >> 1)`, cross-checked on four encodings in `FUN_0002b422`
(`r0,0x2`=`0x0481` · `r12,0x4`=`0x6482` · `r0,0x8`=`0x0484` · `r16,0xa`=`0x8485`). So
`sst.h r12,0x8[ep]` = `0x6484` = one byte `0x04 -> 0x64` at file offset **`0x2B531`**. It double-counts and
is 2.577× under-scaled (raw command counts into an observer-units slot). Recorded because it is the
architecturally-correct injection point for any *future* observer-bias term.

## OPEN
- Which subsystems own the **mode-5** channels 2/4/5/9. Ten callers of `FUN_00025c32` exist
  (`FUN_00023ad2, 23fe2, 2b422(=LKAS,ch1), 2c246, 2caa2, 2e52e, 339cc, 3405a, 3a8a8, 3aff4`) for 11 channels.
  Method that works: read the `mov N,r10` immediately before each `jarl 0x25c32`.
- The channel INPUT arrays are written only register-indirect (a whole-image Format-VII scan finds zero
  direct gp-relative writers) — do not conclude "dead" from a displacement scan there.
