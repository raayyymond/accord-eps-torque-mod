# HANDOFF — 2026-07-14 — Gentle-EME root cause RE-LOCATED to the debounce SM; V36 built

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **STOCK analysis program = `code.bin`**
(Ghidra program name `code.bin`, path `/master.bin`, flat base 0 → address==file-offset; `gp (r4)=0xFEDF8000`,
`tp (r5)=0xBF000`). Openpilot = operator's **StarPilot** fork on a **comma 4**.

**Builds on** `HANDOFF-2026-07-13-v31p-gateflags-330-piggyback.md` (V31P-V2 = V31 cals + gentle-EME gate-firing
telemetry in CAN 330 spare bits). This session: operator **flashed V31P-V2**, drove **route 7f**, and reported a
gentle EME with a slight perceptible delay. We analyzed the rlogs, traced the firmware in Ghidra (subagent +
own verification of every load-bearing claim), **re-located the gentle-EME root cause**, and **built V36**.

---

## 0. One-line state

**The gentle EME is produced by a DEBOUNCE STATE MACHINE (`FUN_0002a30e` + an inline twin in
`m_steer_torque_arbitration`), NOT the engage-SM decider torque-MAX gate we'd been chasing.** It sets
`STEER_STATUS=no_torque_alert_2` after **5 sustained cycles** of `torque gp-0x682f > 112 (0xC64B4) OR angle-rate
param_1 > 1600 (0xC61C0)` (multi-tier envelope, 7 cals). **V36 = V31 + those torque/rate cals raised to unsigned
max (0xFF/0xFFFF) → the debounce can never fire.** Cal-only, 0 code edits, 49/49 CRC, **UNFLASHED**.

---

## 1. What the route-7f telemetry showed (V31P-V2 flags, decoded from RAW CAN 330 bus 1)

StarPilot was NOT updated on the comma, so there is no `epsTelemetry` service — the V31P-V2 flags were decoded
by hand from raw CAN **330 (0x14A) on bus 1** (`byte4[7:3]` gates + `byte7[7:6]` angleConsensus/hardCut). Telemetry
confirmed live and healthy. Scripts used are in the session scratchpad; the decode is:
`399 STEER_STATUS=(d4>>4)&0xF (4=EME)`, `330 gate bits = d4 bits3-7 / d7 bits6-7`.

**Two `STEER_STATUS=4` events in the route** (each exactly **99 ms**): route **5:31.3** (onset tq 2007) and
**6:15.9** (tq −1522). `427 OUTPUT_DISABLED` never latches → the EME is **not** a motor-output/hard cut.

**The instrumented flags do NOT identify the trigger.** All 7 fire on a steady **~10 Hz benign cadence**
(engage_sm_cut n=957, voter_avg 727, gate5_torque 865, angle_db 545, rate_gate 192, angle_consensus 68,
hard_cut 1410 over ~146 s). Pre-cut-200 ms firing rates ≈ whole-drive baseline (engage_sm_cut 6.5%→7.7%,
hard_cut 9.6%→7.7%, voter_avg 5.0%→**0%**). **Nothing rises at either cut.** The cuts don't even land on the
drive's CAN peaks (cut torque 2007/1551 vs drive max 4770 / p99 3166; cut rate 24/34°/s vs max 304). ⇒ the
trigger is an internal signal invisible to CAN and uncaught by the 10 Hz gate bits.

**⚠ Operator anchor (record for all future docs):** the felt gentle EME on route 7f is at **route 5:27** (trigger
~5:26), felt as a **sharp, slight straightening of the wheel in the middle of a turn** — NOT the `STEER_STATUS=4`
report at 5:31.3 (a lag / separate later event). The 5:26–5:27 window is gentle small-angle (0.9–2.8°)
oscillation with no `STEER_STATUS=4`; the felt straightening sits below CAN angle resolution (0.1°) and
`torqueOutputCan` logs as 0 there, so it can't be pinned tighter than "in that window, and it did not raise the
status report." The observable to look for is the **wheel-straightening**, not `STEER_STATUS`.

---

## 2. The firmware root cause (Ghidra, every load-bearing claim self-verified)

### 2a. The gentle EME = a debounce state machine, in TWO functions
`STEER_STATUS` byte = **`gp-0x6807`**. It is written =4 by a debounce FSM present in:
- **`FUN_0002a30e`** (0x2a30e): the status producer. Fires `mov 0x4; st.b -0x6807` @ `0x2a46a` (rise) / `0x2a4e6`
  (hold).
- **`m_steer_torque_arbitration`** (~`0x29210`–`0x2931e`): an inline twin — same cals, same `gp-0x6757` counter,
  also writes `gp-0x6807=4`.

Mechanism (byte-verified both branches, all loads `ld.bu`/`ld.hu` = UNSIGNED, all compares `cmp; bh` = unsigned
"branch if higher", i.e. `cal < signal`): a signed counter **`gp-0x6757`** starts at **−cal `0xC64E2`(=5)** and
only advances while a qualifying condition holds → `STEER_STATUS=4` fires after **5 consecutive qualifying
cycles**, then holds via seed cal `0xC64DF`(=100).

### 2b. The qualifying condition — a multi-tier envelope over TWO variables (7 cals)
Variables: **`gp-0x682f`** = `min(|arb signal r15| >> 5, 255)` (TORQUE channel, produced in
m_steer_torque_arbitration @`0x29068`), and **`param_1`** = an angular-RATE magnitude (clamped ≤65535). Fires if
**any**:

| tier | condition | cals (stock) |
|---|---|---|
| torque alone | `torque > 112` (rise) / `> 96` (hold) | `0xC64B4`=112, `0xC64B5`=96 |
| rate alone | `rate > 1600` | `0xC61C0`=1600 |
| combined A | `torque > 64` AND `rate > 896` | `0xC64B7`=64, `0xC61C2`=896 |
| combined B | `torque > 54` AND `rate > 1280` | `0xC64B6`=54, `0xC61C4`=1280 |

= 4 torque thresholds + 3 rate thresholds. The combined tiers are a staircase approximation of "moderate torque
**and** moderate rate together are dangerous even if neither is extreme alone" — the loaded-curve+bump case. The
torque rise/hold pair (112/96) is hysteresis. **All 7 must be raised to disable both variables completely.**

### 2c. Corrections of record (each self-verified in Ghidra this session)
1. **`gp-0x6809` = DEAD CODE.** 0 writers in all 185,116 instrs (only 4 `ld.bu -0x6809` reads @
   `0x2975a/0x29808/0x29964/0x29a2c` in m_steer_torque_arbitration; searched hex + decimal `26633`). At the gate
   (`0x29766 cmp 0x1,lp / 0x29768 bne 0x297f4`) `lp=gp-0x6809` is never 1 → the bail is taken every cycle. **The
   2026-07-06 gating-map Stage-E1 "deliver-flag `gp-0x6809≠1` = the physical cut" is REFUTED.** Do not anchor on
   it. (Also invalidates the `eps-deliver-cut-gp6809-broken` framing that the cut is `gp-0x6809!=1`.)
2. **`STEER_STATUS=4` is a lagging REPORT, not the torque cut.** Its readers feed a ramp-duration mini-FSM whose
   torque-zero was (wrongly) gated on the dead `gp-0x6809`. **The instruction that actually zeroes the LKAS
   motor term during the felt cut is STILL UNLOCATED** — the single most important open question.
3. **Decider `0xC6312`=320 torque-MAX gate fires ~10 Hz BENIGN and does NOT correlate with the cut** (957× in
   route 7f). The hook IS correctly placed — verified the disengage path `0x40dd6 bnc 0x40dfc` (voterMax≥320) →
   `mov 2,r12` → `br 0x40e64` (store) reaches the hook — it's just not the trigger. **V33's 320→65535 disabled
   the WRONG gate.** (Decider r12 refusal codes, for reference: 2=torqueMAX 0xC6312; 4=angle-consensus 0xC6354;
   5=rate gp-0x6a60≥0xC6310=1600; 6=gp-0x4f68≥0xC61CE=4096; 7=gp-0x6ba4≥0xC61CC=3584; 0=pass.)
4. **V31P-V2's 5 gate flags are non-discriminating** (see §1). The whole gate-telemetry approach watched the
   wrong sites.

### 2d. Left deliberately (not part of the gentle EME)
- **`0xC64B8`=112**: a THIRD `gp-0x682f` threshold, but it gates the SEPARATE **`gp-0x6758`** counter whose
  saturation raises `STEER_STATUS=7` + logs **DTC 0x49** (`FUN_00016de6(0x49,1,1,1)` @`0x2a3ac`). Fault/DTC path,
  not the gentle EME → left stock so real fault detection is preserved.
- **`0xC6312`=320**: the decider gate (correction #3). V31 base; not the trigger.

### 2e. Task rate (explains the 10 Hz flag cadence)
Decider/deliver-commit/hard-cut (`FUN_00040d58`, `FUN_0003d04c`, `FUN_0003d4a2`) are on the ~100 Hz chain via
`FUN_00022ca0` (`jarl 0x413ae`, `jarl 0x3d4a2`). The gate flags appear at ~10 Hz because the decider state machine
only reaches each gate ~10 % of cycles (not a coarse 330 window — CAN 330 is empirically ~100 Hz on the wire).
`FUN_00055a98` (330 builder / telemetry pack site) has no static callers — dispatch/rate unresolved (low priority
now).

---

## 3. V36 — BUILT, verified, UNFLASHED

**Build:** `analysis-2020accord/build_v36_tva.py` → `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V36-V31-debounceSM-OFF-torqueMax255-rateMax65535-0x13000-0x100000.rwd`
(+ `../accord-firmware/analysis-2020accord/_v36_plain_image.bin`). **V36 = V31 (all cals unchanged) + disable the debounce-SM torque
& rate conditions:**

| cal | stock | → | datatype / why max disables |
|---|---|---|---|
| `0xC64B4`,`0xC64B5`,`0xC64B7`,`0xC64B6` | 112,96,64,54 | **255 (0xFF)** | u8; `gp-0x682f`≤255, so `255<gp-0x682f` never true |
| `0xC61C0`,`0xC61C2`,`0xC61C4` | 1600,896,1280 | **65535 (0xFFFF)** | u16; `param_1`≤65535, so `65535<param_1` never true |

⇒ every tier's `cal < signal` is permanently false ⇒ the debounce counter can never advance ⇒ `STEER_STATUS=4`
can never be produced by EITHER function (both read the same cals). 

**Verification (independent of the build's own asserts — fresh diff of `../accord-firmware/analysis-2020accord/_v36_plain_image.bin` vs stock
`code.bin`):** all 7 cals set correctly; `0xC64B8`=112 and `0xC6312`=320 left stock; **ZERO byte diffs in both
FSM functions** (`[0x29000,0x29400)` and `[0x2a30e,0x2a508)`) = proven cal-only; no diffs outside {cal block
0xC6000–0xC6FFF, CRC 0xC4FFC, PN}; 41 total byte diffs (V31 set + 10 new debounce bytes + 2 CRCs); 49/49 CRC OK;
round-trip `decode==patched`. **Blast radius verified contained**: `0xC64B4-B7` & `0xC61C0/C2/C4` are read ONLY by
the two FSM functions (all other operand-search hits were branch-target false positives; `mov 0xc71c4,ep`
@0x2bb36 is a different ADDRESS).

**⚠ V36 is a DISCRIMINATING EXPERIMENT, not a guaranteed fix.** It provably kills the `STEER_STATUS=4` debounce
SM, but because the actual motor-zeroing path (correction #2) is unlocated: **IF** the felt assist-drop is driven
by this same `gp-0x682f`/`param_1` condition (likely — same signals, same arbitration function) V36 eliminates
the gentle EME; **IF** the felt straightening persists with NO `STEER_STATUS=4`, that result proves the
assist-drop is a separate path and tells us exactly where to look next. Either outcome is decisive.

---

## 4. NEXT SESSION

1. **Flash V36** (operator names file + bus; iron rule; kill openpilot/pandad first). File:
   `39990-TVA,A160-V36-V31-debounceSM-OFF-torqueMax255-rateMax65535-0x13000-0x100000.rwd`.
2. **Drive the route-7f 5:27 section**, hands-off through the loaded curve. **Watch for the wheel-straightening**
   (§1 anchor), not `STEER_STATUS`.
3. **Verdict:** straightening gone → root cause confirmed + fixed; straightening persists with no `STEER_STATUS=4`
   → the assist-drop is a separate path → hunt the actual motor-zeroing instruction (open Q #1).
4. If we want telemetry that actually discriminates next time, log the **values** of `gp-0x682f`, `param_1`, and
   the debounce counter `gp-0x6757` (not the old 5 gate bits).

---

## 5. Open questions (ranked)
1. **The actual LKAS-motor-zeroing instruction during the felt cut** (unlocated; `gp-0x6809` was the dead lead).
2. **`gp-0x682f`'s source `r15`** in m_steer_torque_arbitration (`min(|r15|>>5,255)` @0x29068; r15 origin not
   fully traced).
3. **`param_1`'s caller** — `FUN_0002a30e` is called indirectly (0 static callers); needed to name the rate
   signal exactly and convert the 5-cycle debounce to ms.
4. `FUN_00055a98` (330 builder) dispatch site/rate.

## 6. Iron rules (unchanged)
- **No CAN/UDS send or flash without the operator naming the exact file/payload + bus; repeat it back.** V36 is a
  STUDY ARTIFACT until then.
- Analyze STOCK `code.bin` only (never `_v*_plain_image.bin` except to *verify a build*, as in §3). r2 default
  `v850` mis-decodes V850E2 — use `v850.gnu` or Ghidra.
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`).

## 7. Artifacts this session
- `analysis-2020accord/build_v36_tva.py`, `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V36-...rwd`,
  `../accord-firmware/analysis-2020accord/_v36_plain_image.bin`.
- Memories: `v36-debounce-sm-root-cause-and-build` (new); `gentle-eme-fires-on-saturated-lkas-command`,
  `eps-deliver-cut-gp6809-broken`, `v31p-gateflags-330-piggyback-built` (updated); `MEMORY.md`.
- Correction banner added to `docs/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md`.
