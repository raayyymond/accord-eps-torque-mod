# HANDOFF 2026-07-24 — V50 GATE-1 fail; new-ID CAN-TX capability; four-frame telemetry; diagnose-then-filter

Read `CLAUDE.md`'s 2026-07-24 current-state blocks first; this is the detail of record for the session.

## TL;DR

1. **V50 is NO-FLASH.** The V50P probe drive (rlog 5) proved `gp-0x1500` has a **live writer** → GATE 1
   fails on-car. Root cause: `gp-0x1500` is slot 5 of a 40-slot I/O-mailbox array at `0xb7260`, not free RAM.
   Lead independently re-decoded the rlog to confirm (99.47% of frames non-zero).
2. **Adversarial swarm (5 agents) on the V50 cave:** trampoline PASS; carrier/monitor asymmetry
   conditional-safe (found a missed live raw lane, `FUN_0002eda8`, that V50 should have repointed); GATE-2
   stable but the built deadband is a one-way ratchet (−7 count DC bias); GATE-1 fail as above.
3. **V51P** (cell-probe for replacement cells `gp-0x1300`/`gp-0x1100`) BUILT + lead-verified, UNFLASHED.
4. **NEW-ID CAN-TX capability** — the operator's friend's four-frame telemetry method (SH-2A Clarity),
   ported to V850 A160. Full TX architecture mapped; **`VCANTX-TEST`** (1 frame) and **`FOURFRAME`** (4
   frames, 16 backward-chain signals) BUILT + lead-verified, UNFLASHED. First active-CAN-TX caves in the kit.
5. **Strategy pivot (operator):** stop guessing which base-assist lane carries the 21 Hz (all guesses
   falsified). Log the backward chain from the FOC setpoint, FFT to find the carrier lane, then filter it
   **as late and as few signals as possible.** ⚠ Filtering `gp-0x4f60` itself is **UNTESTED, not falsified**
   (V48B bricked before testing efficacy; V50 unflashed).

## 1. V50 GATE-1 fail (the headline)

- **V50P probe** (`build_v50probe_tva.py`) = V38 + a read-only cave that reads `gp-0x1500` low byte into
  CAN-330 spare bits. Flashed + driven = **rlog 5** (`75604b0a432fdc89_00000005--2ae04b9ba2--*`, in
  `analysis-2020accord/rlogs/`).
- **Decode (`decode_v50p_gate1*.py`, + lead re-verify):** on the EPS/steering bus (bus 1),
  `byte4[7:3]` (= `gp-0x1500` low 5 bits) is **non-zero on 99.47% of 42,154 frames** and varies frame-to-
  frame; it sits at exactly 0 for ~1.15 s after ignition then goes dynamic for the whole drive. Stock
  baseline (`rlogs/manual/aa5b3e0c01`) has those bits pinned at 0. Probe liveness proven three ways
  (kept-stock bits = 0x07 match, cross-field consistency, sharp contrast with the null). ⇒ **`gp-0x1500`
  has a live writer.**
- **Root cause:** `gp-0x1500` (0xFEDF6B00) = slot 5 of a **40-slot × 8-byte I/O-mailbox array listed at
  `0xb7260`** (`0xFEDF6AE0..0xFEDF6C18`), written via a table-dispatched (register-indirect) pointer — the
  blind spot literal/absolute static scans can't see. Slot 2 = CAN-330 TX buffer (`0xFEDF6AE8`), slot 3 =
  CAN-660. The V48B post-mortem's "vetted-safe alt `gp-0x14E0`" is slot 9 of the SAME array → also unsafe.
  **Static clearance failed on 3 of 8 addresses checked (`gp-0x1500`, `gp-0x14E0`, `gp-0x1700`).** In this
  firmware a live probe is the only reliable RAM-ownership test. See
  `memory/reference-accord-b7260-io-mailbox-array.md`.

## 2. Swarm ledger

| Gate | Result |
|---|---|
| Trampoline transparency @0x7FEAC (V24 class) | **PASS** — hook/cave/flags clean, verified vs built image |
| RAM ownership (V48B class) | 🛑 **FAIL** — `gp-0x1500` live writer (lead-re-verified rlog) |
| Monitor asymmetry (V27 class) | conditional-SAFE — but found `FUN_0002eda8` = an unrepointed live raw `gp-0x4f60` command-path lane (→ `gp-0x6b6c` → lane 9 → `gp-0x6ad6` → `FUN_0003a382`); `FUN_0002ec52` = diagnostic, leave-raw |
| Closed-loop stability (GATE 2) | STABLE, but the built 16-bit deadband is a **one-way ratchet** (floor-shift) → −6.5..−7 count DC bias + local +15% gain; fix = round-to-nearest `(74·d+512)>>10` |

## 3. V51P cell-probe (for a V51 rebuild, if the diagnose-then-filter path isn't taken first)

`build_v51probe_tva.py` — reads candidate cells **B = `gp-0x1300`** and **D = `gp-0x1100`** (both outside the
mailbox array, ~400 B clean corridor) as FULL 16-bit nonzero detectors, plus a **liveness beacon** (byte4
bit7 = 1) so a clean read is distinguishable from a non-probe drive. Decode: `beacon=(b4>>7)&1` must be 1;
`B_nonzero=(b4>>6)&1`, `D_nonzero=(b7>>7)&1` = 0 all drive ⇒ clean. Whichever reads clean earns the V51
rebuild (winning cell + round-to-nearest ratchet + repoint the 7 carriers **and** `FUN_0002eda8`, keeps 4×).

## 4. New-ID CAN-TX architecture (mapped + lead-verified)

See `memory/reference-accord-can-tx-architecture-new-id.md`. Single FCN0 (`0xFF480000`); emitter
`FUN_0001d82e`→`FUN_0001d68e` is slot-coupled (18 packed slots via `0xB7208`/`0xB721C`(ID<<18)/`0xB7C9C`
cadence); `FUN_0001cf30` configures HW mailboxes 0-63, leaving **7-32 bare/free**. All broadcast IDs ride
mailbox 6; the comma-visible (399/427/330) vs absent (660/64D/32E/19F) split is a **downstream gateway
per-ID whitelist** — the 4 absent IDs are actively scheduled + fired (0x19F @62.5 Hz, same as visible 399)
yet don't reach the comma ⇒ **a new ID is visible on a red panda on the EPS bus, not the comma rlog.** TX is
gated on `gp-0x1712` bit0 (readiness; drops during reconfig/bus-off) AND `DAT_ff48024c` bit4 — any cave must
respect both.

## 5. The two active-TX builds (UNFLASHED, lead-verified off the built image)

- **`VCANTX-TEST-txgate`** (`build_vcantx_test_tva.py`): mailbox 16, ID `0x555`, fixed magic payload, gated
  on `gp-0x1712` bit0. Single-frame mechanism test. Cave 224 B @0xC4B34 on V38.
- **`FOURFRAME`** (`build_vfourframe_tva.py`): mailboxes 16-19, IDs `0x6a0-0x6a3`, dual-gated
  (`gp-0x1712` bit0 + `DAT_ff48024c` bit4). 774 B cave @0xC4B34 on V38, 438 B headroom, Ghidra-clean 180/180.
  Lead-verified: only mailboxes 16-19 touched (negative controls confirm no in-use mailbox), both gate skip-
  `jr`s land on the epilogue, 4×/hook/CRC intact, SHA matches. IDs collision-clear on the comma scans
  (red-panda listen = definitive). ~5% bus load.

  **FOURFRAME decode map** (each cell = 1 big-endian s16, `struct.unpack('>h', bytes([hi,lo]))`):
  - **0x6A0** (mbx16): `gp-0x6b98` delivered_cmd | `gp-0x6acc` shaper_in | `gp-0x6ace` governor_out | `gp-0x6b94` aggregator_sum
  - **0x6A1** (mbx17): `gp-0x6b4c` lkas | `gp-0x6ad4` resonance_lane | `gp-0x6bd0` damping | `gp-0x6bbe` boost
  - **0x6A2** (mbx18): `gp-0x6b86` magnitude | `gp-0x6b26` friction | `gp-0x6b62` return_centre | `gp-0x6ade` feedforward **[dead cell — flat]**
  - **0x6A3** (mbx19): `gp-0x4f60` raw_sensorB | `gp-0x4f62` torque_rate | `gp-0x69a4` r26_gain_in | `gp-0x67ac` suppression_gate **[proven const-0]**

  (The friend's original bundle — Clarity SH-2A, IDs 0x6a0-0x6a3, "descriptor 0→2 for TX", 50 Hz hook — is
  in the operator's uploaded `FOUR_FRAME_TELEMETRY_PORTING_BUNDLE.zip`. A160 differs: no editable descriptor
  table + no reusable payload helper, so we raw-program the free mailboxes; the *method* ports, not the bytes.)

## 6. Backward-chain map + the falsified-vs-untested distinction

`foc-backward-map` (golden-model cross-checked) enumerated `FUN_0003aa2c`'s aggregator summands — each a
candidate 21 Hz carrier: LKAS `gp-0x6b4c`, resonance lane `gp-0x6ad4` (via `FUN_0003a382`), friction
`gp-0x6b26`, boost `gp-0x6bbe`, damping `gp-0x6bd0`, magnitude `gp-0x6b86`, return-centre `gp-0x6b62`, dead
feedforward `gp-0x6ade`, inline r24/r26 (no cell), filtered-Sensor-B `FUN_00036682`. A wholesale suppression
gate `gp-0x67ac`==1 drops 8 of them simultaneously (trigger unresolved; proven const-0 on this firmware). The
FOC Iq_ref bridge into `FUN_00071272` is genuinely unlocated → anchor at `gp-0x6b98`.

⚠ **That agent mis-ranked cal `0xC6450` as the "best genuinely-new lever" — WRONG.** Verified vs the build
scripts: `0xC6450` (Stage A pole) = **V46** (1024→32, falsified), `0xC644A` (Stage C pole) = **V43**
(falsified) — BOTH poles of that exact lane are dead. Trust the structural map, not the ranking.

**Levers, categorized** (`memory/reference-accord-vibration-levers-falsified-vs-untested.md`):
- **Validly falsified** (cal-only, flashed+drove, no effect): r24/V39, r26/V42, `0xC644A`/V43, `0xC6450`/V46,
  damping/V44+V47.
- **UNTESTED** (never got a valid efficacy test): the `gp-0x4f60` signal-filter — V48B (notch) bricked
  catastrophically; V50 (low-pass) never flashed. **This is the leading OPEN hypothesis**, to be done
  late+narrow (one summand producer output), not V48B/V50's early/broad "filter the root feeding 7+ carriers".

## 7. Recommended next steps (all on-car, operator's iron-rule call)

1. **Red-panda test of FOURFRAME:** red panda on the EPS bus, engine on, parked → listen for `0x6a0-0x6a3`
   collisions → kill pandad → flash (name file + bus) → confirm the 4 IDs @~62.5 Hz, payload moves with the
   wheel, and **no bus disruption to 399/427/330.** (Or flash VCANTX-TEST first for the minimal mechanism check.)
2. **Drive with the buzz, capture (red panda), FFT the 16 signals** → the lane with a 21 Hz peak is the carrier.
3. **Filter that one lane, late + narrow** — the fix, on the right signal, once. If the carrier is
   `gp-0x4f60`-derived, that's the untested signal-filter hypothesis aimed surgically.
4. Parallel/fallback: V51P cell-probe drive (comma rlog) → V51 filter rebuild on a proven-clean cell.

## 8. Open items

- Which lane carries the 21 Hz — the whole point of FOURFRAME (unresolved until a drive).
- `0x6a0-0x6a3` collision on the EPS bus not definitively cleared (comma scans clear; red-panda listen needed).
- `gp-0x67ac`==1 suppression-gate trigger unresolved (proven const-0 on this firmware; a nonzero telemetry
  reading would itself be diagnostic).
- FCN0 RX-mask (DNBMRX) not fully ruled out for mailboxes 7-32 (low risk; mailboxes 16-19 exhaustively
  confirmed free by the movhi-enumeration method).
- Sampling: FOURFRAME is hooked at 62.5 Hz (~3 samples/cycle at 21 Hz — enough to detect a peak, not high-res);
  a faster hook is possible at higher bus load if cleaner spectra are needed.

## Process notes (worth carrying forward)

- **Verify subagent conclusions before acting** paid off twice: the rlog writer finding (re-decoded), and the
  `0xC6450`-is-a-new-lever error (caught vs the build scripts). See
  `memory/feedback-verify-subagent-conclusions.md`.
- **Static RAM-ownership clearance is not sufficient in this firmware** — a live probe is mandatory.
- **Active-TX caves are a new, higher-risk class** (they transmit on the steering bus) — mirror stock's TX
  gating (`gp-0x1712` + `DAT_ff48024c`) and validate with a red-panda listen before flash.
