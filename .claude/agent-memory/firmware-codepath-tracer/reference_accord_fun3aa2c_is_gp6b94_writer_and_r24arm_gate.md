---
name: reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate
description: Accord TVA-A160 -- FUN_0003aa2c fully decompiled and identified as the aggregator that WRITES gp-0x6b94 (sums friction gp-0x6b26, damper gp-0x6bd0 clamped +/-0x800, angle-rate gp-0x6bbe, peak-hold gp-0x6b86, plus gp-0x6ade/gp-0x6b4c/gp-0x6ac0-derived terms, clamped +/-0x2800, shadow twin gp-0x4ce0, redundancy-voted via FUN_0006b9fa). Also locates the exact r24-arm gate condition (gp-0x671d==0 && gp-0x683c!=0) that reaches cal tp+0x7446/0xC6446, and flags that gp-0x683c is read at the SAME instruction (0x3AA94) V67's 0x3AA96 repoint targets.
metadata:
  type: reference
---

# FUN_0003aa2c = gp-0x6b94 aggregator writer + r24-arm gate location (2026-08-07)

Found while designing a V83 telemetry payload (team-lead brief). `decompile_function(0x3aa2c)` on `code.bin`,
full body. gp=0xFEDF8000, tp=0xBF000.

## FUN_0003aa2c is the writer of gp-0x6b94

My own memory (`reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed.md`) had
gp-0x6b94's forward hop (reader) unresolved after 5 methods but did not name its writer explicitly. This
session found it directly: `FUN_0003aa2c(char param_1)` sums, in order:
- `iVar14` = clamped `gp-0x6b62` (window `[-0x2000,0x2000)`, i.e. test `x+0x2000U < 0x4001`)
- `iVar19` = clamped `gp-0x6b4c` (window ±0x2800) + `gp-0x6ade` term (±0x400) — both summed via a shared
  path when a branch on `gp-0x671a < tp+0x74fa` and further gates are false
- Full sum path (else branch, gp-0x67ac-gated — see below):
  `iVar19 = gp-0x6ade(±0x400) + gp-0x6b4c(±0x2800) + gp-0x6ad4(±0x2800) + iVar14(gp-0x6b62,±0x2000)
   + gp-0x6b26(±0x400, FRICTION) + gp-0x6bbe(±0x800, ANGLE-RATE) + gp-0x6bd0(±0x800, DAMPER)
   + gp-0x6b86(±0x3000, PEAK-HOLD) + iVar21 + iVar16` (iVar21/iVar16 = two separately-computed,
  independently-clamped ±0x2000 terms built earlier in the function from `gp-0x671a`/`gp-0x671d`/
  `gp-0x6752`-scaled LERP-table lookups over `gp-0x6e28..gp-0x6e40` and cals `tp+0x7440/42/44/46`)
- `FUN_00036682()` is called on the same branch (else path) — an additional term folded into `iVar14`
  before the final sum, not traced further this session.
- Final: `iVar14 = iVar14 + iVar19`, clamped to `[-0x2800, 0x2800]` (±10240), written to **both**
  `gp-0x6b94` and shadow twin `gp-0x4ce0` when they already agree; on disagreement (`sVar6 != sVar20`
  where `sVar6=gp-0x6b94`, `sVar20=gp-0x4ce0`) calls `FUN_0006b9fa(gp-0x4ce0)` — the same redundancy-vote
  helper documented elsewhere in this domain for other shadow-pair mismatches.

**Practically important for telemetry/sizing work**: `gp-0x6bd0` (damper) and `gp-0x6bb e` (angle-rate)
are each individually clamped to ±0x800 (±2048) **at this summing point**, regardless of their native
range elsewhere — use ±2048 as the reference frame for any "near-rail" threshold computed against this
specific consumption site. `gp-0x6b26` (friction) clamps to ±0x400 (±1024) here.

Selector `bVar1 = gp-0x671a < tp+0x74fa` picks between two cal pairs (`tp+0x7136/7138`) for an unrelated
early computation (`sVar7`, feeds `uVar13`), and `gp-0x67ac < 2` gates which of the two summation paths
(sparse 2-term vs full 8+-term) executes — consistent with `reference_accord_gp67ac_aggregator_lane_suppression_gate.md`'s
existing "suppression gate" framing; this session did not re-verify that memory, just noting the same
cell reappears in the same functional role.

## r24-arm gate: exact condition for reaching cal 0xC6446

Inside the same function, the branch that reads `tp+0x7446` (== `0xC6446`, the cal V67/V68 change from
512→5244 to make r24's arm live):
```c
if (*(char *)(gp - 0x671d) == '\0') {
    if (*(char *)(gp - 0x683c) == '\0') {   // bVar4
        if (!bVar1) uVar11 = *(ushort *)(tp + 0x7440);
        // else uVar11 stays at the LERP-table value computed earlier
    } else {
        uVar11 = *(ushort *)(tp + 0x7446);   // <-- THE ARM CAL, reached iff gp-0x671d==0 && gp-0x683c!=0
    }
} else {
    uVar11 = *(ushort *)(tp + 0x7442);
}
```
So the arm-cal read fires exactly when **`gp-0x671d == 0` AND `gp-0x683c != 0`**.

⚠ **`gp-0x683c` is read at `0x3AA94`** (`ld.bu -0x683c[gp],r15`, confirmed the ONLY xref in
`code.bin` via `search_instructions operand_pattern="-0x683c"`, 1 hit) — **this is the exact instruction
V67's build script repoints** (`build_v67_tva.py`: "REPOINT_BYTE = 0x3AA96 ... Repoints `ld.bu
-0x683c[gp],r15` @0x3AA94"). If a future build (e.g. V83) carries that repoint, reading `gp-0x683c`
directly from an INDEPENDENT telemetry cave will NOT reflect what this branch actually tests post-repoint
— the repoint changes the displacement inside this one instruction, not the value at address gp-0x683c
itself. Any telemetry design streaming "arm liveness" must either (a) use only the repoint-independent
half (`gp-0x671d==0`), or (b) be told the exact post-repoint displacement and mirror it.

`gp-0x671d` itself is NOT touched by the repoint and is a well-established plain byte flag — 16 confirmed
read/write sites program-wide this session (`search_instructions operand_pattern="-0x671d"`), matches
prior memory [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]].

## Related
[[reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed]] — the reader/forward-hop
side of gp-0x6b94, still open; this entry closes the writer side.
[[reference_accord_gp67ac_aggregator_lane_suppression_gate]] — same suppression-gate cell reappears here.
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — prior identification of gp-0x671d.
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] — the telemetry-channel
context this trace was done in support of.
