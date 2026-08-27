# HANDOFF — 2026-07-13 (evening) — V31P driven → 2 broken bits found → V31P-V2 built

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **STOCK analysis program = `code.bin`**
(Ghidra program `code.bin`, project path `/master.bin`, flat base 0; gp=0xFEDF8000, tp=0xBF000). Openpilot =
operator's **StarPilot** fork on a **comma 4** at `../openpilots/raayyymond-StarPilot/StarPilot` (branch `Dom`).

**Builds on** `handoffs/2026-07/HANDOFF-2026-07-13-v31p-gateflags-330-piggyback.md`. That session BUILT V31P (gate-firing
telemetry into CAN 330 spare bits). Since then **V31P was flashed and driven** — this session analyzed those
rlogs (route 77 `dc09125cc3` segs 0–4, route 79 `6aa3606df8` segs 9–11), found two of the seven telemetry
bits broken, verified a subagent's firmware trace, and **built V31P-V2** to fix them. **V31P-V2 = BUILT,
49/49 CRC, cave re-disassembled in Ghidra, UNFLASHED.**

---

## 0. One-line state

The 5 gate flags (330 byte4[7:3]) work and were read live on route 77/79. The 2 byte7 state bits were
**broken**: `TRUMP` (gp-0x67FE==2) stuck at 1, `DELIVER_CUT` (gp-0x6809!=0) stuck at 0. Root-caused both in
Ghidra. A subagent traced the real hardware motor cut (`gp-0x676e==4` all-3-phase disable in `FUN_0003d4a2`
@`0x3de6c`) — but that's the **HARD** cut, which CAN 427 `OUTPUT_DISABLED` confirms does NOT fire at the
gentle EMEs. **V31P-V2** keeps the 5 gates and replaces byte7 with **angleConsensus** (decider r12==4, the
V34 gate nothing else instruments) + **hardCut** (gp-0x676e==4). Fork + rlog-tools decoders renamed to match.

---

## 1. What the route 77/79 rlogs showed (gate flags at the cuts)

Decoded **raw CAN 330** (0x14A, bus 1) byte4/byte7 directly (fork-independent; `epsTelemetry` events are also
present, 42,375 of them, and decode identically). Cut anchor = raw CAN 399 `STEER_STATUS=no_torque_alert_2`.

- **Route 77 (segs 0–4, 0:00–5:00): 7 cuts.** The operator's flagged events map to: **4:14 = cut@4:13.28
  (pure `engage_sm_cut`)** and **4:58 = a triple cluster 4:58.12 / 4:58.65 / 4:59.25** (first is pure
  `engage_sm_cut`; the two re-cuts go broadband). Aggregate peri-cut elevation vs baseline: `angle_db` 2.3×,
  `rate_gate` 2.1× (low baselines), `engage_sm_cut` 1.2–1.3× (fires alone at the two clean isolated cuts but
  has a high 4.8% baseline).
- **Route 79 (segs 9–11): 5 cuts** (9:21, 9:41, 10:01×2, 10:20; "10:00" = the 10:01 double-cut). NO gate
  elevated at the cuts (all 0.6–1.2×) — that stretch has every gate chattering at 5–6%.
- Gates fire 2–6% during normal driving, so no single gate cleanly dominates; the column-torque gates
  (engage_sm_cut / voter_avg / gate5_torque) co-fire (shared signal).
- ⚠ Segment timing: non-CAN events have logMonoTime outliers; anchor time PER SEGMENT to the CAN stream
  (`route_time = segnum*60 + (t − first_can_t_in_seg)`), not to a global t0.

## 2. The two broken byte7 bits (both Ghidra-verified on stock `code.bin`)

- **DELIVER_CUT (byte7 bit7 = gp-0x6809 != 0): reads 0 in 100% of frames.** Broken 3 ways — (1) firmware
  physical cut is `gp-0x6809 != 1` (verified both sites `0x2975a`/`0x29808`: `cmp 0x1,lp; bne`), not `!=0`;
  (2) live-read in the 330 builder = wrong phase (reads 0 while arbitration sees 1 during delivery), not
  latched; (3) gp-0x6809 has NO gp-relative writer image-wide, and the gate→gp-0x6809 hop was never
  byte-traced. Its silence is NOT evidence about the gates. See `memory/eps-deliver-cut-gp6809-broken`.
- **TRUMP (byte7 bit6 = gp-0x67FE == 2): reads 1 in 100% of frames.** gp-0x67FE is the EPS
  **ENGAGED-vs-HOLDING assist substate** (values 0/1/2, shadow gp-0x4c3a), written by `FUN_0003bd7c` from FOC
  mode gp-0x6772 (==5→2, ==4→1, else 0); ~55 readers incl. `FUN_00041222`/`FUN_00041304`. Value 2 = engaged
  substate = on the whole drive. Steady-state mode, no event info. See
  `memory/eps-gp67fe-trump-engaged-holding-substate`.
- Bonus correction: **raw CAN 427 `MOTOR_TORQUE` is ~0** (route 77 seg2 = 0x00 all frames; max 128 mean 1.4;
  route 79 tops ~553) and `OUTPUT_DISABLED` never fires at cuts — 427 is NOT a delivered-torque or cut
  anchor. The real delivered LKAS command global is **gp-0x6b98** (0xFEDF1468, shaper `FUN_00042af8`), not
  427's source `gp-0x6c18`. See `memory/honda-op-steeringtorqueeps-always-zero` (corrected).

## 3. V32–V35 lineage + the subagent trace (why the gates aren't the whole story)

The road lineage disabled individual gates and the EME persisted every time: **V32** voterMax `0xC6312`
320→1280; **V33** voterMax →65535; **V34** + angle-consensus NOPs (decider r12==4 path); **V35** + voterAvg
`0xC62FE` →65535. So engage_sm_cut and voter_avg are road-ruled-out as the sole cause. `gate5_torque`
(`0xC61EA`) and `rate_gate` (`0xC6310`) were never disabled.

A `firmware-codepath-tracer` subagent found (and I byte-verified) the real all-motor-disable: in
`FUN_0003d4a2` (FOC/relay sequencer, called every cycle by `FUN_00022ca0`), when `gp-0x676e==4` the tail at
`0x3de6c` calls `FUN_00016de6(chan, X, 0, 1)` on all 3 phases `0x3f/0x40/0x41` with enable arg = 0 (states
1/2/3 each keep one phase live). **That is the HARD cut (full motor shutdown), not the gentle EME** — the
gentle EME keeps the motor enabled and only zeroes the LKAS command. CAN 427 `OUTPUT_DISABLED` (byte2 bit6)
never firing at the 12 gentle cuts confirms `gp-0x676e==4` does not occur at them. **The gentle EME has no
single downstream "cut instruction" distinct from the gates** — it IS the deliver-commit being skipped (gate
bails) → gp-0x6b98 not refreshed while the motor stays on.

## 4. V31P-V2 build — `analysis-2020accord/builds/v18_v49/build_v31p_v2_tva.py` — BUILT, Ghidra-verified, UNFLASHED

RWD `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31P-V2-gateflags-v2-angleconsensus-hardcut-caveC4B34-0x13000-0x100000.rwd`
+ `../accord-firmware/analysis-2020accord/_v31p_v2_plain_image.bin`. **49/49 CRC PASS, ECU-decode==patched, 180 B / 32 runs.**

Same 330 wire layout, ALL-LATCHED (no live-reads → no phase bug). Flag byte `gp-0x1500` now uses bits 0–6.

| wire bit | V31P (broken) | **V31P-V2** | firmware change |
|---|---|---|---|
| byte4 bit3–7 | 5 gate flags | **unchanged** (engage_sm_cut, voter_avg, gate5_torque, angle_db, rate_gate) | existing 5 stubs/sites |
| byte7 bit6 | ~~trump~~ | **angleConsensus** = decider `FUN_00040d58` r12==4 | +3 instrs in the existing decider stub (`cmp 0x4,r12; bne; set1 5,-0x1500[gp]`) — no new site |
| byte7 bit7 | ~~deliverCut~~ | **hardCut** = gp-0x676e==4 all-phase disable | NEW cave stub + NEW 6th site swap at `0x3de6c` (`movea 0x3f,r0,r6` → `jr hardcut_stub`; stub: `set1 6,-0x1500[gp]; movea 0x3f,r0,r6; jr 0x3de70`) |

Pack hook rewritten: byte7[7:6] = `(flagbyte & 0x60) << 1` (bit5→b6, bit6→b7); dropped the gp-0x67FE /
gp-0x6809 live-reads. Clobbers only r6/r7/r8 (unchanged). Every new instruction encoding was harvested from
real stock-image instances and the whole cave was **re-disassembled in Ghidra (`../accord-firmware/analysis-2020accord/_v31p_v2_plain_image.bin`) —
all 38 cave instructions + the `0x3de6c` site (`jr 0x000c4b70`) decode exactly as designed.** `0x3de6c` is
reached by BOTH all-disable entry paths (the `cmp 0x4,r7` fall-through and the forced-4 `jr 0x3de6c` at
`0x3dd34`), so the latch catches every phase-disable.

`hardCut` prediction: it stays **0** through gentle EMEs (firmware proof the gentle EME ≠ phase disable) and
lights up only on a real hard EME / fault / shutdown. If it ever fires on a "gentle" event, that reframes the
diagnosis.

## 5. Fork + rlog-tools decoder changes (committed with this session)

- **Fork (`raayyymond/StarPilot` branch `Dom`):** `cereal/custom.capnp` EpsTelemetry — renamed `trump @5 →
  angleConsensus @5`, `deliverCut @6 → hardCut @6` (**same @ids ⇒ wire-compatible**, no reflash of already-
  logged data needed); `selfdrive/car/eps_telemetry.py` `EpsTelemetrySample` (slots + bit decode); `card.py`
  publish (`et.angleConsensus`/`et.hardCut`).
- **rlog-tools:** `cereal/custom.capnp` mirror renamed the same; `decode/extract_eps_telemetry.py` — renamed columns,
  rewrote the stale UDS docstring, and **fixed a latent crash** (it still referenced the old UDS-schema
  `row["valid"]`/`col_torque`/`voter_max`). Verified: runs clean on the route-77 rlog (331 eps rows).
  ⚠ On a car still on **V31P** (pre-V2), byte7 bit6 carries the OLD trump bit, so `angle_consensus` reads
  ~100% and `hard_cut` ~0 — those bits only mean the new gates once V31P-V2 is flashed.

## 6. NEXT SESSION

1. **Flash V31P-V2** (operator names file + bus; iron rule). File:
   `39990-TVA,A160-V31P-V2-gateflags-v2-angleconsensus-hardcut-caveC4B34-0x13000-0x100000.rwd`.
2. **Source-build the fork** on the comma (`Dom`): `UsePrebuilt=0; scons` (compiles cereal = the schema
   check). No panda reflash (no honda.h/TX change). Reboot.
3. **Drive, provoke gentle EMEs**, then `python rlog-tools/decode/extract_eps_telemetry.py <route>--*/rlog.zst -o
   eme.csv`. At each `STEER_STATUS→no_torque_alert_2` cut, read the 5 gates + `angle_consensus`; expect
   `hard_cut` = 0 (confirming gentle ≠ phase disable). The standout uninstrumented-by-lineage suspects are
   `gate5_torque` (`0xC61EA`) and `angle_consensus`/`angle_db`.
4. If the gentle EME truly never trips ANY instrumented gate at the cut, the next lever is the deliver-commit
   fault returns (`FUN_0003d04c` return 5/6) or a finer LKAS-command (`gp-0x6b98`) collapse latch.

## 7. Iron rules (unchanged)
- No CAN/UDS send or flash without the operator naming the exact payload/file + bus; repeat it back. V31P-V2
  transmits nothing new (330 is existing; only spare bits change).
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin` (except to *verify a build*, as in §4).
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`).

## 8. Key addresses
| thing | address |
|---|---|
| angleConsensus gate (V2 byte7 b6) | decider `FUN_00040d58` r12==4 @ epilogue `0x40e64` (`FUN_000406ae` / `\|gp-0x6cc4\|>0xC6354`) |
| hardCut = all-phase disable (V2 byte7 b7) | `FUN_0003d4a2` `gp-0x676e==4` dispatch @ `0x3de6c` (3× `FUN_00016de6(chan,X,0,1)`, chans 0x3f/0x40/0x41) |
| delivered LKAS command global | `gp-0x6b98` = 0xFEDF1468 (shaper `FUN_00042af8`; → `gp-0x6b54` motor reg via `FUN_00056420`) |
| deliver flag (broken bit) | `gp-0x6809` = 0xFEDF17F7 — cut = `!=1` @ `0x2975a`/`0x29808`; no writer |
| assist substate (broken bit) | `gp-0x67FE` = 0xFEDF1802 (0/1/2, writer `FUN_0003bd7c`, shadow `gp-0x4c3a`) |
| cave | `0xC4B34` (128 B used of 1212); pack hook, decider/gate/angle/hardcut stubs |
| build script | `analysis-2020accord/builds/v18_v49/build_v31p_v2_tva.py` |
