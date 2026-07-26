---
name: reference-accord-assist-curve-family-sport-mode
description: "The base-assist boost curve is selected by the byte gp+0x63fd (POSITIVE gp displacement, 0xFEDFE3FD), indexing a 34-entry pointer array @0xCA154. CONFIDENT NEGATIVE: Sport-mode steering tightening is NOT implemented by this EPS -- all 3 writers traced to instruction level (boot table / internal fault-failover / PasCom UDS), none CAN-fed, and our part number's 4 reachable columns are {10,10,11,11} which differ by ~1%"
metadata:
  node_type: memory
  type: reference
---

Answers the operator's question "is the Accord's Sport-mode steering tightening applied by the EPS firmware?" — a **documented negative**, recorded so it does not get re-traced in a future session.

## The mechanism that *looks* like a mode selector

`FUN_00034a72` (the base-assist boost-curve producer, writes lane `gp-0x6bbe`) selects its curve family from a byte:

```
0x34abc  ld.bu 0x63fd[gp], r10        ; POSITIVE gp displacement -> 0xFEDFE3FD
```

That byte indexes six parallel tables: boost curve `@0xCA154`, gain scalar `@0xCA324`, rate curve `@0xCA4F4`, per-variant byte `@0xCA40C`, scalar clamp `@0xC7A58`, and `@0xCA23C`.

**The boost-curve pointer array has 34 entries, not 8 or 16.** (An early read sampled only the first 8 and drew a wrong conclusion about which curve this car runs — see the method note below.) Two shapes exist:

| family | X breakpoints | Y (assist gain) |
|---|---|---|
| **rising** | 0, 640, 2560, 5120, 8960, **12800** | 612, 787, 992, 1141, 1211, **1238** |
| **falling** | 0, 640, 2560, 5120, 7808, **10240** | ~540, ~640, ~655, ~550, **~440** |

The falling family peaks around 2560 counts of column torque and then *drops ~33%* under heavier load. Representative members: idx0 `0xCE578` (rising — the curve already cited in [[reference-accord-dual-torque-sensor-architecture]]), idx4 `0xD0834`, idx10 `0xD2834`, idx11 `0xD2850`, idx33 `0xD986C` (lightest in the image).

## Our car runs curve 10

`gp+0x63fd` is column `tp+0xE012` of the **same** per-part-number table that produces `gp-0x674c/d/e` — see [[reference-accord-ecu-id-variant-table]]. Our A160 = slot 2 (`TVAA1`):

```
e012 = 10 , e013 = 10 , e014 = 11 , e015 = 11
```

Curve 10 = `[541, 639, 653, 551, 439, 439]`, curve 11 = `[547, 645, 659, 557, 445, 445]` — **~1% apart**.

So this Accord runs a *falling* assist curve. The high-assist rising curves belong to other part numbers entirely.

## Why the answer is NO — three independent grounds

**1. No writer is CAN-fed.** All three writers of `gp+0x63fd` traced to instruction level; an exhaustive search of the `0x63fd[gp]` displacement (31 hits) found no others:

- `FUN_00042692` `@0x426ae` — boot-once, gated on the boot-readiness bitmask `gp-0x6d78 & 8` (written only by `FUN_000197b8`, read by ~14 init-stage functions). Reads column `tp+0xE012` of the static ROM table. Zero CAN references.
- `FUN_00042746` `@0x4279e/0x427c4/0x427fc/0x42822` — runs every cycle, CAN re-derive at runtime, **but** every input traces to internal state: `gp-0x6806` and `gp-0x69b0` are written **only** by `m_steer_torque_arbitration`; `gp-0x67e2`/`gp-0x67f6`/`gp-0x68ab` are read *and* written exclusively inside this one function (self-contained latch); `gp-0x4f68` is sensor-derived. It selects among columns `e012/e013/e014/e015` of the same row via a 2-bit state — a **sensor-fault/timeout failover reselector**.
- `FUN_0004a798` `@0x4a7fc` — UDS/PasCom bench-diagnostic command 1 (German strings "Bitte mit PasCom flashen" / "ungueltiges Kommando"). Service-tool path.

**2. No drive-mode signal is decoded.** The EPS decodes 21 standard CAN IDs: `0x94, 0xE4, 0x130, 0x13C, 0x158, 0x17C, 0x198, 0x1A4, 0x1B0, 0x1D0, 0x1DC, 0x1EA, 0x305, 0x324, 0x326, 0x328, 0x374, 0x3A1, 0x6FA, 0x72A, 0x752, 0x78E` (mailbox tables `@0xB733C` ID, `@0xB70F4` mailbox->slot, `@0xB739C` slot->dest; formula validated against the known `0xE4` entry). None reaches this byte. **[OPEN]** semantic names for 20 of the 21 (no local DBC in repo); consumer functions located for only `0x198`.

**3. The data forecloses it anyway.** Our row's four reachable columns are `{10,10,11,11}` — all the same family, ~1% apart. A real Sport mode would need to swing falling (top-end 439) to rising (top-end 1238), a ~2.8x change. **Our variant row does not contain that pair.** Even a hypothetical CAN input could only select a difference nobody could feel.

## Verdict

**Sport-mode steering-effort change is not implemented by this EPS firmware.** It is either done by another module reading a signal this EPS never decodes, or the effect is perceptual. No firmware evidence distinguishes those two.

## Incidental finding worth knowing

Slot 0 is the blank `"00000"` no-match fallback, and its `e012 = 0` -> the **rising** family. An ECU whose HW-ID was never programmed (or that fails to match any key) would run ~2.8x more assist at high column torque than a correctly-ID'd unit. Relevant before swapping or re-IDing an EPS.

## Method note

The first pass at this array read 8 entries of a 34-entry table and concluded "modes 4/5 are the tightened ones" — mapping this car to index 1 when it is actually index 10. The lesson (repeated three times this session): **verify a table's EXTENT before drawing conclusions from its contents.** Locate the array end, do not assume a power-of-two count. Instruction-level rigor does not protect against a truncated data read.

Related: [[reference-accord-base-assist-lane-architecture]], [[reference-accord-ecu-id-variant-table]], [[feedback-verify-subagent-claims]]
