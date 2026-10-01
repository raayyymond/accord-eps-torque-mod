---
name: reference_accord_sentinel_delivered_st7_sticky_and_guard_block_edits
description: 2026-09-30. The 0xE4 fault sentinel's 2.048 s lane pulse IS delivered (no fault-cell reader on the mixer/aggregator/governor/EME/FOC path; DTC 0x65 has reaction mask 0); fault => ST=3 not 4/7; ST=7 is STICKY until ECU reset (bail latches LKAS off); gp+0x6400 bit3 is a CODING bit (ST=6 => state-2 full-ramp HOLD, unreachable on row 11); in-place guard fixes 0x29A56 da05->b205 (+0x29A50 -> e0df3443).
metadata:
  type: reference
---

Trace: `docs/traces/TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md`.

- **Fault → ST = 3**, because `bVar2` (r27, `0x2913A`) needs `(unsigned)(gp-0x69ae+0x4000) < 0x8001`.
  State 2 → `0x296F8` (ramp −[0xC63F6]=16/tick, 2.048 s), with the PID running throughout (EVIDENCE).
- **Delivered.** Census of all 9 fault-written cells (Python 4B+6B+literal, Ghidra; extras all in the dead
  `FUN_0002a508`). Non-lane readers: the diagnostic record `FUN_0004e82e`, the 0x18F packer `FUN_00055c42`,
  `FUN_00042746` (guarded by 6806≠0), and `==1` tests where 0xFF ≡ 0. The `gp-0x67a4` delivery gate stays
  at role 3 while the ramp > 0 (`gp-0x67a7 = ramp≠0 || 6809==1`). The aggregator does not gate
  `gp-0x6b4c`. (EVIDENCE)
- **DTC 0x65** (slot 7 id, `.data` flash `0x89F20`) has descriptor `0xB8848` with reaction dword +8 = 0
  ⇒ no fault-class bit in `gp-0x18d0/18d4`. (EVIDENCE)
- **ST = 7 is STICKY**: every non-7 write sits behind `0x29156 cmp 7; bne`. Bail (|x| > 12000, |τ| > 25600,
  pol ∉ ±1) ⇒ PID skip + ST 7 + 0.1 s fade + no re-engage until reset. (EVIDENCE)
- **`gp+0x6400` bit 3 = coding bit** (from variant record byte bit 0x04; row 11 = 0x75 ⇒ 0). ST = 6 would
  make state 2 HOLD full ramp — latent, unreachable at runtime. (EVIDENCE)
- **`0xC63F6` readers:** only the dir-0 ramp-down (4 live sites in the SM).
- **Guard edits:**
  - `0x29A56 da05→b205` gives run iff ramp∧request==1 (mirror: sentinel pulse → decay only, ~105 ms).
  - Adding `0x29A50 e2470000→e0df3443` (`cmovne r0,r27,r8`) gives run iff ramp∧request∧bVar2, which
    covers `gp-0x67fe≠2`.
  - Open: r8 liveness on the `0x2A164` path.

Related: [[reference_accord_0xe4_fault_sentinel_rails_the_lane_on_v293_plus]] (its "NOT traced" is now closed),
[[reference_accord_gp679c_mode3_semantics_and_wire_bit]].
