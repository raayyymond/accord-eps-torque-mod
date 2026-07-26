---
name: reference-v850-sa-algorithm-tva
description: Verified V850 (TVA Accord) SecurityAccess seed→key algorithm; universal Honda formula with Group C constants firmware-embedded at 0x92C0; .rwd ! header is family-marker not SA secret
metadata:
  type: reference
source: collaborative
---

The 2020 Honda Accord (TVA chassis, V850E2/Px4 MCU) EPS firmware uses the **universal Honda EPS seed→key algorithm**, identical in structure to the SH-2A family:

```python
key16 = ((seed16 + k0) & 0xFFFF) ^ ((seed16 * k1) % k2)
```

**Constants (Group C, firmware-embedded at `0x92C0..0x92C5` in code.bin):**
- `k0 = 0x0211` at `0x92C0` (addend)
- `k1 = 0x0212` at `0x92C2` (multiplier)
- `k2 = 0x1220` at `0x92C4` (modulus)

As ASCII hex secret: `021102121220`.

**Wire format:** 2-byte seed, 2-byte key. Tester sends 2 key bytes (msg[2..3] BE).

**Handler chain:**
```
dispatcher 0xD43A → case 0xD56C → length check 0xC0C8 → SA handler 0xC94C
  ├─ subfn 1 (RequestSeed): jarl 0xB24E → 0xDF58 (RNG) + 0xAA52 (LCG mix)
  └─ subfn 2 (SendKey):     jarl 0xB30C → 0xAAD8 → jarl 0xAAB4 (THE ALGORITHM)
```

`0xC94C` is the SA handler with HIGH confidence — writes SA-exclusive UDS NRCs `0x35` (InvalidKey), `0x36` (ExceededAttempts), `0x37` (RequiredTimeDelay).

**The `!` header in V850 .rwd files is NOT the SA secret.** All 52 V850 .rwds in iHDS carry the family-invariant Group A value (`001100121020`), but V850 firmware never reads it during SA validation — the firmware uses its own embedded Group C constants. iHDS likely uses the `!` header as a family marker only, with per-chassis SA secret logic on the tester side.

**Why:** verified via bit-level datasheet decode (V850E2M Architecture Manual + Ghidra V850E2M SLEIGH PR #1430 + binaryninja-v850 cross-check). Resolved two compounding rizin/Ghidra bugs (see [[reference-rizin-ghidra-v850-quirks]]) that initially obscured the algorithm.

**How to apply:** for any TVA EPS SA work, use `flashing-2020accord/tva_sa_key.py` (`calculate_tva_session_key(seed_bytes)`). For sibling V850 chassis (T2F, T3L, TV9, etc.), the algorithm is the same but their firmware constants may differ — decode their code.bin's `0x92C0..0x92C5` region to extract per-chassis constants. See [[reference-honda-eps-sa-secret-per-mcu-family]] for the cross-family pattern.

**Audit trail:** `analysis-2020accord/V850_ALGORITHM_VERIFIED.md` (bit-level decode), `analysis-2020accord/SA_KEY_PYTHON_PREP.md` (assumption chain), `analysis-2020accord/ACCORD_TVA_ARCHITECTURE_MAP.md §7.4` (consolidated reference).
