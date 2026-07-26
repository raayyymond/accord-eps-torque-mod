---
name: accord-init-sm-fun220ba-fun1a104
description: Full decompile + analysis of FUN_000220ba and FUN_0001a104 in 2020 Accord EPS init state machine; V850E2/Px4; gp=0xFEDF8000; tp=0xBF000
metadata:
  type: reference
---

## FUN_000220ba (0x220ba) — State=3 → State=4 Gate

**Role:** Returns bool; used by FUN_00019888 as the final gate for the state 3→4 transition, after (gp-0x6d78 & 0x2A10 == 0x2A10) passes.

**Decompile (Ghidra, `../accord-firmware/analysis-2020accord/_v22_plain_image.bin`):**
```c
bool FUN_000220ba(void) {
    int iVar1 = FUN_00022078();
    return iVar1 == 0;
}
```

**FUN_00022078 (0x22078) — the real gate:**
```c
undefined4 FUN_00022078(void) {
    iVar1 = FUN_00018ce8(9);         // read DTC[9] status (5-byte table at gp-0x6F9B)
    if ((iVar1 == 2) || (gp-0x3E5C != 2)) {
        iVar1 = FUN_00018ce8(9);
        if (iVar1 != 0) return gp-0x3E5C;  // return last stored value
        return 0;
    } else {
        gp-0x3E5C = 1;
        gp+0x642C = 1;
        FUN_000193ce(9, 0);          // clear DTC 9
        return 1;
    }
    // also: gp-0x3E5C = uVar2; return uVar2
}
```

**FUN_00018ce8(9)** reads `DAT_fedf1065[9*5]` = DTC[9] status byte from runtime RAM table.
- Returns 0 = no fault, 2 = fault confirmed, other = pending

**FUN_000220ba returns TRUE (1)** when FUN_00022078 returns 0, which happens when:
- DTC[9] status == 2 AND gp-0x3E5C was already 2: path returns 1 (sets gp-0x3E5C=1, clears DTC9, returns 1 → FUN_000220ba returns (1==0) = FALSE)
- Wait — re-read: FUN_000220ba returns (iVar1 == 0). So it returns TRUE when FUN_00022078 returns 0.
- FUN_00022078 returns 0 when DTC[9] == 0 AND gp-0x3E5C != 2 (no pending fault).
- FUN_000220ba returns FALSE (blocking state=3 transition) when DTC[9] != 0 (fault present).

**CRITICAL:** DTC[9] is a RUNTIME status flag in RAM. It is set by runtime health checks, NOT by reading code flash. V21/V22 code patches at 0x42xxx CANNOT affect DTC[9] through code integrity logic.

**Does it call FUN_0006b9fa?** NO. Does it touch 0x42xxx range? NO.

---

## FUN_0001a104 (0x1a104) — State=4 and State=5 Idle Handler

**Role:** Called at the start of BOTH state=4 (FUN_00019970) and state=5 (FUN_00019b10) handlers. Updates gp-0x68ad, which controls whether states 4/5 advance to state=5 or remain.

**Decompile:**
```c
void FUN_0001a104(void) {
    bool bVar1 = (*(short*)(gp-0x6A98) == 0);     // torque sensor zero flag
    int iVar2 = FUN_000197d0(0xf);                  // gp-0x6D78 bit 15
    int iVar3 = FUN_00062c20();                     // gp-0x4F44[0:8]==0 AND DTC[5].active

    if (((iVar3 != 0) || (gp-0x4E70 != 0)) && (iVar2 != 1)) {
        if (gp-0x68ad != 1) {
            if ((gp-0x437C == 1) && (!bVar1)) {
                gp-0x68ad = 1;
                return;
            }
            FUN_00022034();
            return;
        }
        if ((gp-0x4378 != 1) || bVar1) {
            FUN_00022016();
            return;
        }
    }
    gp-0x68ad = 0;
}
```

**FUN_00022034** sets gp-0x68ad=1 if several motor/DTC flags (gp-0x679d, gp-0x6814, gp-0x6839, gp-0x6872, gp-0x6871, gp-0x67f5, gp-0x67f4) indicate readiness.
**FUN_00022016** clears gp-0x68ad=0 if gp-0x679d!=1 AND (gp-0x6A5E==0 OR gp-0x67f4!=1).
**FUN_00062c20** returns true if gp-0x4F44[0:8]==0 AND FUN_0005a950(5)==1 (DTC table check).
**FUN_0005a950** indexes DTC active-mask table at 0xBBE4C (RAM, not flash).

**Does it call FUN_0006b9fa?** NO. Does it touch 0x42xxx range? NO. Does it read from code flash? NO.

---

## State Machine Context (FUN_00019888 — State=3 handler)

```c
void FUN_00019888(void) {
    if (tp+0x74F9 == 0xAA) {           // factory/diagnostic mode byte -- 0x00 in V22 binary
        // ... factory path (never taken in normal firmware)
    } else {
        iVar1 = FUN_000197d0(7);        // check gp-0x6D78 bit 7
        if (iVar1 == 1) {
            // fault: transition to state 6
        } else {
            iVar1 = FUN_000197d0(0xf);  // check gp-0x6D78 bit 15
            if ((iVar1 == 0) &&
                ((gp-0x6D78 & 0x2A10) == 0x2A10) &&
                (FUN_000220ba() == 1)) {
                // SUCCESS: transition to state 4
                FUN_0001a1c4();
                FUN_00021ebc();
            }
        }
    }
}
```

The `tp+0x74F9` byte = `data[0xBF000 + 0x74F9]` = `data[0xC64F9]` = **0x00** in V22 binary. The 0xAA/factory path is never taken. The normal state=3→4 path is always the else-branch.

---

## Code Integrity Check Search: NEGATIVE RESULT

**Exhaustive search performed** for any function in 0x19700-0x1bfff (init SM range) and its callees that reads from code flash (0x13000-0xC4FFF) as DATA for CRC/checksum computation.

**Result: NO software code integrity check found** in the application firmware.

- The only CRC function found in the firmware is **FUN_0006b5a2** (CRC8, table at tp-0x2B1C=0xBC4E4). Its sole caller is **FUN_0007007c** which verifies CRC on received **CAN messages** — NOT flash integrity.
- Flash data READ in init range: motor actuator seq tables at 0x8AB30/34/60/70/78, 0x8AF12/14. These are read-only parameter tables, NOT integrity targets, and do NOT overlap with 0x42xxx code patch area.
- The firmware footer at 0xFFFF0 (16 bytes: `01 00 00 00 00 00 00 00 fd 00 03 00 2c 21 b8 fc`) has NO code references and appears to be a flash tool artifact.
- The function pointer at `DAT_00002040` (address 0x2040) = 0xFFFFFFFF (erased flash) — this stub is never reached since it would fault. No ROM-based CRC check observable within the application image.

**Implication for V21 startup fault:** The V21 fault is NOT caused by a software code integrity check over the 0x42xxx flash region. The fault must originate from a HARDWARE mechanism (ROM boot CRC before jumping to application code) or from a RUNTIME behavior difference caused by the modified code itself (changed computation path, not integrity detection).

---

## gp-0x68ad (state 4/5 readiness flag) — Full Logic Map

- **Written 1 by:** FUN_0001a104 directly (on first entry with gp-0x437C==1 and torque!=0), FUN_00022034 (on motor-ready flags set), or gp-0x68ad already=1 path in states 4/5
- **Written 0 by:** FUN_0001a104 directly (on motor-idle path), FUN_00022016 (on re-idle conditions)
- **Read by:** FUN_00019970 (state=4): `if (gp-0x68ad == 1)` → advance to state=5. FUN_00019b10 (state=5): `if (gp-0x68ad != 0)` → call FUN_0001a240 then fall through.

## Verified: Neither function blocks state machine due to V21 code patches

**Why:** DTC[9], gp-0x6D78 bits, gp-0x4F44, gp-0x4E70, gp-0x437C, gp-0x4378, gp-0x6A98 are all RUNTIME flags set by actual hardware/sensor/CAN checks. Code patches in the shaper (0x42xxx) cannot set any of these flags at power-up — only sensors and CAN frames do.

[[accord-gp6d78-init-flag-writers]] [[accord-integrator-update-form]]
