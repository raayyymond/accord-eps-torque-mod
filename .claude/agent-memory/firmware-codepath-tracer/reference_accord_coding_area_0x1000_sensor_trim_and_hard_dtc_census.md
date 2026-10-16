
---
name: reference-accord-coding-area-sensor-trim-hard-dtc-census
description: Per-ECU data the RWD does not replace (coding TLV at flash 0x1000-0x14CF, data-flash HW-ID TVCA4), sensor trim chain to 0x18F, 37 hard-eligible DTC ids, FUN_00045A20/4595A inequalities, and three corrections (0xC64C3 gate, 0xC61AE, +0x1000 slip)
metadata:
  type: reference
---

Full detail: docs/traces/TRACE-2026-10-05-v37-slot-dependence.md, section FOLLOW-UP (b).

- Coding area: TLV records (u16 CRC16, len, tag, payload) at flash 0x1000..0x14CF, walked by FUN_00048A40; tag 0x54 = polarity gp-0x6752 (the later record at 0x14C0 has 0xFA = -1); bad length raises DTC 0x08 (hard). Below 0x13000, not in the RWD.
- Stock data.bin (de-tagged, words in descending order) holds HW-ID TVCA4 near 0x1760 = operator slot 11.
- Torque chain: sensor trim stream (FUN_000829E2) gives gp-0x506C trim (617..1427) and gp-0x25D4 = 1280*15*trim>>11; CORDIC; range limit gp-0x4F54 = 27/4*U, jump limit gp-0x4F56 = 15/2*U with U = 1280*2*trim>>10; packer 0x55C50: 0x18F b0:1 = -((gp-0x4F60*125)>>7).
- Hard-eligible DTC ids (flag & 0x41): 37 ids, 0x1D reached through FUN_000462E6 from 12 functions; 0x23 and 0x49 are not hard.
- FUN_00045A20: |gp-0x6ACC - gp-0x6ACE|/1024 within +-0.001 unless |rate| >= T(angle), T = lerp(angle*0.1,[350,410],[5000,400]); thrA >= T everywhere. FUN_0004595A: |b94|-|ace| >= -10 and ace*b94 >= -10485.
- CORRECTIONS: gate for the learned scale/offset in FUN_0007F3F8 is 0xC64C3 = 0 (not 0xC63C3 = 4, a +0x1000 slip in the older memory); FUN_00036828's threshold is 0xC61AE (Ghidra mislabels it thunk_FUN_0000702c); 0xC602C is a float 5.0.
- OPEN: BL FUN_00005BAA/C86 read u16 [0x14102+idx*6] and u8 [0x14104+idx*6]; for idx 5 that is the V37-edited byte 0x14120. Key table base (BL tp) not pinned.
