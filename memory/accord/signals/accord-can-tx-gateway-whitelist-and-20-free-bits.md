---
name: accord-can-tx-gateway-whitelist-and-20-free-bits
description: New CAN IDs never reach openpilot — the gateway is a whitelist; only 0x14A/0x18F/0x1AB cross, and they carry 20 free structural bits, 4x the channel the kit has been using.
metadata:
  type: reference
---

★★★★ **The gateway is a WHITELIST. A new CAN ID cannot reach openpilot, no matter how correctly the EPS
transmits it. Telemetry must piggyback on `0x14A` (330), `0x18F` (399) or `0x1AB` (427) — and those carry
20 free structural bits, four times what this kit has been using.**

## The dead end, closed empirically

**[EVIDENCE, on-car]** V53 flew FOURFRAME2: four new IDs (`0x6A0`–`0x6A3`), the STRB/SSAM defect fixed,
mechanically correct TX. Result: **zero frames** at the comma tap — while `0x14A`/`0x18F`/`0x1AB`
(97.3 / 97.4 / 48.7 Hz) came through fine, **and other stock-firmware IDs** (`0x19F`, `0x660`, `0x32E`)
that the EPS also fires correctly on the same mailbox at the same cadence were **equally absent**.
⇒ **a downstream gateway whitelist, not a cave defect.** This supersedes the reading of
[[reference-accord-fourframe-strb-ssam-defect]] as "our bug, therefore fixable": the STRB/SSAM defect was
real *and* fixing it changed nothing, because the frame was never going to cross.
⇒ **The "mailbox 16 / new ID" recipe is real and buildable but useless for reaching openpilot. Close that
branch.**

## The TX packers — all FCN0, mailbox 6, one shared HW writer `FUN_0001d68e`

| ID | packer | buffer | DLC | cadence | crosses? |
|---|---|---|---|---|---|
| `0x14A` 330 | `FUN_00055a98` | `gp-0x1518` = `0xFEDF6AE8` | 8 | 100 Hz | **YES** |
| `0x18F` 399 | `FUN_00055c42` | `gp-0x1420` = `0xFEDF6BE0` | 7 | 100 Hz | **YES** |
| `0x1AB` 427 | `FUN_00055d80` | `gp-0x13CC` = `0xFEDF6C34` | 3 | 50 Hz | **YES** |
| `0x660`, `0x64D`, `0x32E`, `0x19F`, `0x720`–`0x723`, any new ID | — | — | — | — | **NO** |

**Checksum is automatic.** Shared helper `FUN_00057b24(buf=r6, dlc=r7, id=r8)` is called once at the end
of each builder (`0x55C18` / `0x55D5A` / `0x55F04`) and runs over whatever is in the buffer **at call
time** ⇒ spare bits written earlier in the same builder are covered with no recompute step. Proven on-car
by four flashes (V31P, V31P-V2, V49P, V51probe).

## Free bits — 20 structural, per-bit verified by fresh disassembly

| frame | bits | status |
|---|---|---|
| 330 | byte4[7:3] — 5 b | never written; **the current channel** (V75/V81 magprobe) |
| 330 | byte7[7:6] — 2 b | never written; **free on V81** (V49P used it but is not on the car) |
| 399 | byte4[2:0] 3 b · byte5[7:6] 2 b · byte6[6] 1 b | never written — **6 clean bits, never claimed by any build** |
| 399 | byte5[3:0] — 4 b | explicitly cleared by `andi 0xf0` @`0x55CD2` every cycle ⇒ needs a **mask-constant edit**, elevated risk tier |
| 427 | byte0[6:5] 2 b · byte2[7] 1 b | never written — **3 bits, never claimed by any build** |

⚠ **Correction to [[accord-can-tx-100hz-base-tick-and-gateway]]**: it says *"0x18F byte5 = CONSTANT ZERO in
100% of frames — a fully free byte."* **Wrong by 2 bits.** `399 byte5[5:4]` is a **live signal**
(`gp-0x6880 & 3`, packed at `0x55CAE`–`0x55CC2`) that merely read zero on the captured route. **Do not use
bits [5:4].**

**Clean-tier total: 5 + 2 + 6 + 3 = 16 bits (~1,500 bit/s); 20 bits if the 399 mask edit is taken.**
Against a 5-bit baseline.

## The write mechanism — an in-place instruction edit, not a new cave shape

All three builders share the same compiler idiom, so the same edit works three times:

```
jarl <critical-section-enter>,lp
movea -<bufoff>,gp,r6        ; <-- HOOK: swap this 4-byte instr for `jarl <cave>,lp`
mov  <DLC>,r7
movea <ID>,r0,r8
jarl 0x57b24,lp              ; checksum — covers whatever the cave just wrote
```

| frame | hook | stock bytes | state on V81 **[EVIDENCE, orchestrator byte read]** |
|---|---|---|---|
| 330 | `0x55C0E` | `2436e8ea` | **`86ff26ef` = TAKEN** (V67/V75/V81 all) |
| 399 | `0x55D50` | `2436e0eb` | **byte-stock — virgin on every build ever** |
| 427 | `0x55EFA` | `243634ec` | **byte-stock — virgin on every build ever** |

The hook is byte-length-preserving (4 B `movea` → 4 B `jarl`), so no branch displacement elsewhere moves.
A small cave behind it masks in the bits, re-executes the displaced `movea` so `r6` is right for the
checksum call, and `jmp [lp]`s back — the `builds/v18_v49/build_v49p_tva.py` `pack_polarity` template, ~54 B each.
**GATE 1 is a non-issue** (writes only spare bits inside already-owned CAN buffers, no new RAM).
**GATE 2 is N/A** (pure observability, no dynamics inserted into any loop).
DTC `0x18` budget: **N/A** — it is boot-only, see [[accord-dtc-0x18-hard-eligible-cadence-watchdog]].

**Cave room on V81:** `[0xC4B34, 0xC4FF0)` — 68 B used, **1,144 B free at `0xC4B78`**. Leave
`0xC4FF0`+ alone (CRC block self-descriptor).

🛑 Every new probe must carry a **known-firing positive control** — this kit has burned three flights on
probes whose null was on the gate. See [[feedback-probe-the-gate-not-just-the-output]].
