---
name: reference_accord_factorb_index_selector_c6498_and_torque_axis_census
description: CORRECTS the FactorB-index claim in reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm — cal byte 0xC6498=1 selects gp-0x6ba6 (rate composite), NOT gp-0x4f60 torque; the torque arm is DEAD. Plus the full census of which LERP axes in the assist/compensation path are torque- or current-indexed, and why none is a clean cal lever.
metadata:
  type: reference
---

# Which damping/loss axes are TORQUE- or CURRENT-indexed (2026-08-10, `DampAxis` task)

Program: stock `code.bin` only. `gp=0xFEDF8000`, `tp=0xBF000`. Decompile-first, then disasm to confirm.

## 🛑 CORRECTION — FactorB's index is NOT driver torque on this calibration [EVIDENCE]

[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] records FactorB's index as
"built from `gp-0x4f60`". **That is the DEAD arm.** The selector:

```
000343ec: ld.bu 0x7498[tp],r7    ; cal 0xC6498  (0xBF000+0x7498, computed not eyeballed)
000343f0: cmp   0x1,r7
000343f2: be    0x00034424       ; ==1 -> TAKEN on stock
00034424: ld.hu -0x6ba6[gp],r10  ; index := BOOST-AMPLITUDE index (resolver-rate-dominant)
00034438: st.h  r10,-0x6bcc[gp]
```
`read_memory 0xC6494,16` = `6400 f401 01 01 0000 0000 0101 0001 0001` ⇒ **`0xC6498`=1 AND `0xC6499`=1**.
- **Parity-robust**: `ld.bu` carries disp bit0 in hw1 bit5 (the `0x3C`/`0x3D` trap), so 0xC6498-vs-0xC6499
  is normally ambiguous — but both bytes read 1, so the branch is taken either way.
- **Off-by-0x1000 anchored**: `0xC6499`=1 reproduces the recorded boost-curve-index fact.

The earlier trace read the decompile and never read the selector byte. **Operator informed 2026-08-10;
the old memory file was NOT edited** (standing rule: ask before updating another session's memory).

**`build_v48b_tva.py:42` already recorded this mechanism in July 2026** — *"the 2 mode-gated DORMANT reads
(`FUN_00034350` @0x34392, `FUN_00034a72` @0x34ace) — bypassed in stock cal (0xC6498/0xC6499=1)"*.
`build_v59_tva.py:382` asserts both bytes are 1 as a precondition. **`0xC6498` has NEVER been written.**

## The one-BYTE repoint, and why it is inert

`0xC6498` 1→0 takes the else-arm (`0x343f4-0x3441e`) and makes FactorB's index
`abs(clamp( EMA(gp-0x4f60·32, α=0xC636E) + polarity·gp-0x6c2e·0xC636C , ±25600 ))` — a **driver-torque
magnitude**, with a secondary select to `|gp-0x4f60|` above threshold `gp-0x4f68`. Dimensionally sane:
FactorB X=[205,1331,2355,3072] = 0.8–12 % of the ±25600 torque window.

🛑 **Buys nothing alone.** FactorB Y is **flat 1024×4 on mode 26** (`0xD774C`, byte-identical to mode 24
`0xD6760`) — repointing a flat table is a no-op. And FactorC zeroes the product below 35 km/h, and
`FUN_00034350` is **100 Hz**.

## Torque/current-indexed axes that DO exist — and why none is a clean lever

| axis | index | verdict |
|---|---|---|
| **FOC Iq/Id gain schedule, 12 tables `[0xC5462…0xC5540]`** | `gp-0x4ac` = ABC-frame instantaneous **phase-current** power/torque estimate | Literally Delphi's `I_MAG` axis. But it is a current-loop PI/FF **gain**, not dissipation, and it sits **inside the CRC-skipped `[0xC5000,0xC5FFC)` block** (V40 brick). Out of bounds. |
| **`gp-0x69a4`, r26's lane gain** | `abs(clamp(gp-0x4f60, ±cal 0xC6200) + gp-0x6b4a)` = driver torque mag | Live at creep, **1 kHz**, no rate dead-zone. 🛑 The 10-segment curve is **RAM-rebuilt every cycle** (`FUN_00039702→FUN_000389ec→FUN_000352b4`); ROM seed `0xC6564` = 40 bytes of zero. **No cal shapes it.** |
| `FUN_00038148`'s residual LERP | \|Path-2 residual\| × `0xC63AE`/1024 | RAM-resident (`gp-0x64b8`/`gp-0x641c`), Y[0]=0. |
| FactorB | see above | flat + dead index arm + 100 Hz. |

## ★ The structurally interesting repoint: FactorC's index

`ld.hu -0x6a5e[gp],r7` @ **`0x344e0`**, single 16-bit displacement. Read as torque, Honda's own
X=[2240,3840,5120,8960] / Y=[0,234,429,908] becomes **exactly** `GAIN = max(0, K_G·(I_MAG − G_OFFSET))`
with `G_OFFSET`=2240 counts — zero below a torque offset, rising with torque, **no step at zero rate ⇒ no
V80 relay hazard**. Still 100 Hz (6–9 Hz only) and FactorE's 60-count rate dead-zone still multiplies in.
🛑 **[BELIEF/OPEN] 2240 counts of `gp-0x4f60` is not sized in Nm — that number decides whether the offset
is light pressure or a shove. Gating unknown before anyone builds it.**

## Other corrections found the same session

- **`gp-0x69aa` (the `FUN_00037fe6` LERP index) is a Q15-normalised 0…1 ratio, NOT raw vehicle speed.**
  `read_memory 0xC6ABA,32`: X=[0,6554,13107,19661,22938,26214,29491,32768] = 0/0.2/…/1.0 × 32768, gated
  `<0x8001`. 32768 ct would be 512 km/h at 64 ct/km/h.
- **That LERP's Y is FLAT UNITY (`0xC6ACA` = `[1024]×8`) ⇒ inert.** Zero build-script mentions ever.
  Third Honda hook left flat, with FactorB and FactorD.
- **`FUN_00036388` (return-to-centre) contains NO LERP** — pure state machine on `0xC718A`/`0xC727E`/
  `0xC73C0`/`0xC720C`/`0xC72E2`. Drop it from factor-family enumerations.

## Task rates, all confirmed fresh via `get_function_callers` (each returned exactly ONE caller)

**100 Hz (`FUN_00022ca0`)**: `FUN_00034350` damper, `FUN_00034a72` boost, `FUN_00035b20`.
**1 kHz (`FUN_0002214a`)**: `FUN_000352b4`, `FUN_00036c12`, `FUN_00038148`, `FUN_00037fe6`, `FUN_0003b8f6`.
⇒ **Every mode-indexed factor family is on the 100 Hz task ⇒ FactorA–F can NEVER address 18–28 Hz.**

## Virgin cells surfaced (grep of all `build_v*_tva.py`, never written)

`0xC6498` · `0xD774C` (FactorB **mode 26** — zero mentions ever) · `0xC6ABA`/`0xC6ACA` ·
**`0xC63A6` — the friction-lane weight in the mixer**, while siblings `0xC63A0`/`A2`/`AC`/`AE` have all
been touched · `0xC6178`. For reference `0xC63A0` was 2048 on V72–V75/V81, silently reverted at the V38
rebase, **1024 = Honda's on V85/V86 → current**.

Related: [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] (corrected here),
[[reference_accord_factord_six_family_map_and_1khz_lane_v84]],
[[reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected]],
[[reference_accord_fun757a2_iqid_gainschedule_bridge_resolved]],
[[reference_accord_fun36c12_sign_settled_dissipative]].
