---
name: accord-v87-built-measurement-on-v38-base
description: "V87 BUILT/UNFLASHED — the first SUBTRACTIVE build: V38 base + V57 gain + V42 ratchet fix + steer-to-zero + a 2-byte repoint putting |gp-0x6b98| on 427 MOTOR_TORQUE. Every control lever this session died."
metadata:
  node_type: memory
  type: project
---

✅ **V87 IS BUILT, VERIFIED, UNFLASHED.** `builds/v80_v107/build_v87_tva.py`
image `27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034`
rwd `997002f01aa7b5bfe0ac32b8f17396a593a3e298ea11919ea2331b718f6e85f6` (986,042 B)
`39990-TVA,A160-V87-V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98-0x13000-0x100000.rwd`

## ★★★★★ IT IS THE FIRST **SUBTRACTIVE** BUILD IN THE LINEAGE
The arc since V38 — V38–V52 authority/filters/poles/caves · V53–V61 telemetry + lane mutes ·
V62–V73 the rate lane · V74–V83a the damper · V84–V86B damper reverts and phase experiments — **every
one moved a control variable. V87 moves none.** It rebases to V38, keeps only the operator's two named
mods, and adds **2 bytes that repoint a CAN TRANSMIT packer**.

| addr | stock | V87 | what | from |
|---|---|---|---|---|
| `0x2A1F0` | `6c74` | `d07c` | forward LKAS reader → private cal cell | V57 |
| `0xC646C` | 891 | **891** | shared sensor scale at Honda's value ⇒ 4 FEEDBACK readers un-boosted | V57 |
| `0xC6CD0` | blank | **3564** | private forward LKAS gain = **4.000×**, identical to V38's | V38 |
| `0x454FE` | `ba` | `b5` | state-4 command-magnitude clamp unreachable | V42 |
| `0xC62EA` | 320 | **0** | LKAS commandable to 0 km/h | V53 |
| **`0x55DF2`** | `e893` | **`6894`** | **427 `MOTOR_TORQUE` ← `|gp-0x6b98|`** | **NEW** |
| `0x55C0E`+`0xC4B34` | stock/FF | hook + 62 B | 330 byte-4 telemetry, V86B payload verbatim | V86B |

**10 runs / 85 bytes vs the V38 base, ZERO unattributed**; restoring the attributed set reproduces V38
bit-for-bit; CRC 50/50 on the built image, the readback and the shipped file re-read from disk.

## ★ THE PROBE IS A DISPLACEMENT EDIT, NOT A CAVE
`FUN_00055d80` packs 427 (`0x1AB`) as `r6 = gp-0x6c18 → FUN_00049a5a → FUN_00049a78 (abs) →
FUN_00049a90(x*5>>3, 0, 0x3ff) → pack`, and calls the checksum `FUN_00057b24(gp-0x13cc, 3, 0x1ab)`
**LAST**. Changing only the **source load's displacement** makes Honda's own abs / ×5/8 / 10-bit clamp /
pack / checksum chain run on our signal. **Zero control-path effect — we change what a TRANSMIT packer
READS and write nothing.** 0.625 counts/LSB up to 1637, saturating near the ±2000 rail ⇒ full resolution
exactly in the ratchet regime (~120 counts p-p). openpilot decodes it natively, no DBC change.
⊕ The real `MOTOR_TORQUE` is sacrificed deliberately: `|value|`, no sign, not a delivered-torque or cut
anchor. Instruction re-decoded from the BUILT image: `ld.h -0x6B98, gp, r6`.

## 🛑 WHY A MEASUREMENT BUILD — every control lever died
- **`0xC63B8`** refuted five ways — see [[accord-c63b8-8hz-bandpass-is-a-rectified-boost-index]].
- **A cave in the shaper would disable the power steering** — `FUN_00043e44`'s float twin, ±5 counts,
  10 ms → DTC 0xF00049. See [[accord-shaper-float-twin-blocks-filter-insertion]].
- **`0xC646E`'s "1–6 % of clamp" is an unmeasured estimate** that `STATE.md` had promoted to MEASURED.
- ⇒ `|gp-0x6b98|` sets the phase budget for ANY future filter (assumed 120 counts; the answer swings
  **5×**) and discriminates a passive resonance being driven from a closed-loop pole.

## 🛑 HONEST LABEL — read before scoring it
**It will read as a NULL on the ratcheting, by design.** No damping, no filter, no new authority.
**If it moves the ratchet, the model is wrong — and that is itself information.**
⚠ **The feel change is real and comes from the REBASE, not from an 8 Hz lever.** Gone: V85's friction
relay (`0xC40BC` 6000→600, a 10× revert), Lever B (`0x3AA96`/`0xC6446` back to stock), and V86B's
engaged creep damper (`0xD77DA`/`0xD77EE`→0, the low-speed drag the operator disliked). Expect V38's
character plus the ratchet fix plus steer-to-zero.

## ⊕ The ratchet fix REMOVES a rate limiter — the operator asked exactly this
Stock, while `gp-0x67fa == 4`, the governor **forbids the command's magnitude from increasing** and
writes the suppressed value back, re-running a rate-interpolation block seeded from the OLD value ⇒ it
**IS** a rate limiter on the LKAS command, and it is cumulative. `0x454FE` `BA→B5` (Bcond BNE→BR) makes
that block unreachable. It matters most on this base: stock demands ≤417 LKAS counts, **V38 demands
1782**, so the ratchet is ~4× deeper here.

Related: [[accord-v42-ratchet-fix-lost-since-v53]], [[accord-4x-lkas-gain-is-the-frozen-variable]],
[[accord-ratchet-is-a-lightly-damped-resonance]], [[reference-accord-c646c-shared-gain-not-lkas-only]].
