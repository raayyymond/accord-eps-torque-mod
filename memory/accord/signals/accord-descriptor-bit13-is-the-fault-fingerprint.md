---
name: accord-descriptor-bit13-is-the-fault-fingerprint
description: FUN_00040a50 forces the 0x14A angle fields to 0x7FFF on a bit13 fault-descriptor test — so the angle sentinel is a CONSEQUENCE, not a cause. bit13 rules out fid 4/72/80 and rules IN the category-0x2D/0x3D ids including Monitor 1 (28) and Monitor 2 (29). Includes the fault_id off-by-one trap.
metadata:
  type: reference
---

# ★★★★ DESCRIPTOR **bit13** IS THE FAULT FINGERPRINT — and the angle sentinel is a CONSEQUENCE

**[EVIDENCE, orchestrator-verified in Ghidra.]**

`FUN_00040a50` forces the `0x14A` angle fields to **`0x7FFF`** when

```
FUN_00040906(1) == 0xff  &&  FUN_00046ea6(0xd) != 0
```

and `FUN_00046ea6(N)` is **bit N of the OR-aggregate `(gp-0x18d0 | gp-0x18d4)`**. That aggregate ORs the
**first word of the fault-descriptor record** at

```
tp - 0x72bc = 0xBF000 - 0x72BC = 0xB7D44 ,  stride 0x1c ,  fault_id 0 .. 125
```

`0xd` = **bit13**.

## ⇒ The angle sentinel is DOWNSTREAM, not upstream
The `0x14A` `0x7FFF` sentinel **and** `STEER_SENSOR_STATUS` 7→4 seen in
[[accord-v75-fault-pinned-to-the-frame]] are **consequences of a bit13 fault being active**, not evidence
of an angle-sensor problem. 🛑 **No re-pointing of the investigation into the angle domain is warranted.**

## ★ bit13 is a FINGERPRINT — it partitions the candidate fault_ids

**RULES OUT** (their descriptor words have bit13 clear):

| fault_id | DTC | descriptor word | why it's out |
|---|---|---|---|
| 4 | — | `0x00001C01` | init self-test |
| 80 | `0xC41668` | `0x00000C00` | ADC timeout |
| 72 | `0xD48394` | `0x00000C20` | — |

**RULES IN** the category-`0x2D` / `0x3D` ids — including **fid 28 (Monitor 1)** and **fid 29
(Monitor 2 / `FUN_00045a20`)**, both `0x00003D01`. That is the same `0x3D01` hard-eligibility class the
kit already knows from [[accord-dtc-0x18-hard-eligible-cadence-watchdog]] and
[[reference-accord-monitor2-corridor-and-the-c64a4-trap]].

## ⚠ THE fault_id NUMBERING TRAP — several agent reports were one too high
The direct map lives at **`tp - 0x5AB8 = 0xB9548`**, stride **4**, and the DTC is the raw
**bytes[2], bytes[1], bytes[0]** of the entry. Read that way:

| DTC | true fault_id | agents reported |
|---|---|---|
| `0xC41668` | **80** | 81 |
| `0xD48394` | **72** | 73 |
| `0x540011` | **16** | 17 |

**Recompute the id from `0xB9548` before citing one.** Same class of error as the `tp+0x74a4`
off-by-`0x1000` trap — an address handed over rather than derived.

Related: [[accord-dtc-read-is-structurally-blind-here]] ·
[[reference_accord_watchdog_fault_sm_fun43e44]] · [[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]] ·
[[feedback-verify-the-crux-yourself-it-caught-four-errors]]
