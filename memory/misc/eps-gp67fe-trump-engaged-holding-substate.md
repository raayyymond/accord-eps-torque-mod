---
name: eps-gp67fe-trump-engaged-holding-substate
description: "V31P's TRUMP telemetry bit (330 byte7 bit6 = gp-0x67FE == 2) is stuck at 1 for the entire LKAS drive and carries NO event info — gp-0x67FE is the EPS ENGAGED-vs-HOLDING assist substate, not a 'dispatcher trump'. V31P-V2 drops it. Verified 2026-07-13 in Ghidra on stock code.bin."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 03c81800-2f2f-4926-9e12-b63017e563a6
---

**Verified 2026-07-13 (Ghidra, stock `code.bin`, 2020 Accord `39990-TVA-A160`).**
`gp-0x67FE` (= `0xFEDF1802`) is the **EPS assist substate / ENGAGED-vs-HOLDING selector**, NOT a
"dispatcher trump" (that V31P label was a guess). It is a mode byte with values {0,1,2},
lockstep-shadowed at `gp-0x4c3a`, written by `FUN_0003bd7c` from the upstream FOC-mode state
`gp-0x6772`:

- `gp-0x6772 == 5` → writes **2** (active engaged substate)
- `gp-0x6772 == 4` → writes 1
- otherwise → writes 0

It has ~55 readers across the steering cluster, including the ENGAGED handler `FUN_00041222`
(`0x412b2`) and the HOLDING handler `FUN_00041304` — they branch on it to pick ENGAGED vs HOLDING
behavior. During an LKAS drive the EPS sits in the engaged substate (`gp-0x6772==5` →
`gp-0x67FE==2`) essentially the whole time, so V31P's `TRUMP = (gp-0x67FE == 2)` reads **1 in
100% of frames** (confirmed on route 77/79 rlogs). It is a steady-state mode indicator, not an
event — useless as a discriminator. (Side note: because it never leaves 2 through the cuts, the
gentle EME is a torque drop *within* the engaged substate, not an outer state-machine exit.)

**How to apply:** Ignore any V31P `trump` reading. On an rlog decoded with the V31P-V2 schema,
330 byte7 bit6 is relabeled `angleConsensus`, but a car still on **V31P** firmware puts the old
trump bit there — so `angle_consensus` will read ~100% on pre-V2 logs; it only means the new gate
once V31P-V2 is flashed. Related: [[v31p-gateflags-330-piggyback-built]],
[[eps-deliver-cut-gp6809-broken]].
