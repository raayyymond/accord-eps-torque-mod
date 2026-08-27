# HANDOFF — 2026-07-07 (v2) — CAN-TX decompilation swarm + "why car-facing vs internal" investigation

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas **uPD70F3508 / V850E2**. **STOCK analysis program =
`code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 → file offset == address). **Bases:**
`gp (r4) = 0xFEDF8000`, `tp (r5) = 0xBF000`.

**Branch:** `claude/radare2-decompilation-tracers-dreujb` — ALL work this session pushed there. **Nothing
flashed; no firmware/build file changed.** This session was 100% read-only static analysis (radare2/rizin +
one openpilot clone for a capture-side cross-check) + memory files.

**Read alongside** the same-day predecessor `docs/handoffs/2026-07/HANDOFF-2026-07-07-gating-map-and-telemetry-plan.md` (the
telemetry-frame plan this session pressure-tested) and the two swarm synthesis memories:
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_can_tx_synthesis_2026-07-07.md` and
`…/reference_accord_why_car_facing_vs_internal_2026-07-07.md`.

---

## 0. One-line state

Two 4-agent `firmware-codepath-tracer` swarms mapped the entire EPS CAN **transmit** subsystem CAN-builder →
hardware, to (a) find a free TX slot for a telemetry frame and (b) explain why 399/427/0x14A are comma-visible
but 0x660/0x19F/0x32E/0x64D are not. **Result: the TX path is one controller (FCN0), one 17-entry dispatch
table with ZERO free slots, and a RUNTIME-DYNAMIC mailbox pool. The car-facing/internal split is NOT explained
by any static mechanism — all of them ruled out — and the discriminator lives in unlocated dynamic-RAM producers
(or in physical-layer config that isn't in `code.bin`).** Key practical fallout: **0x660 proves that being in
the dispatch table does NOT make a frame comma-visible**, so the "extend the table" telemetry plan is necessary
but not sufficient.

---

## 1. What this session did

1. **Verified radare2 before trusting it** (it was not installed). Installed r2 5.5.0; confirmed the handoff's
   tool warning is real — default `v850` plugin mis-decodes (`0x410c0` → bogus `jarl 0x004c0188,r12`), while
   **`v850.gnu`** decodes correctly (`ld.bu -26622[gp],r12; cmp 2,r12` = the `gp-0x67FE==2` trump) and matches
   two independent handoff ground-truth sites (the 399 packer `-(gp-0x4f60 × 125/128)`). r2pipe installed.
2. **Swarm A (4 agents) — map the CAN TX subsystem** to find a free car-facing TX slot. → §2.
3. **Forward-verify tracer** — proved 399 (and 0x660) write FCN0 message buffers, SVD-grounded register by
   register. → §2.
4. **Recorded a standing operator preference**: ground decompilation in the V850 CMSIS-SVD
   (`memory/feedback/measurement/feedback_svd_grounding.md`).
5. **Swarm B (4 agents) + openpilot clone — answer "why car-facing vs internal."** → §3, §4.

---

## 2. The CAN TX subsystem map (deliverable 1)

**The real outbound path (three-way convergent across agents):**
```
builder fns (399=FUN_00055c42@0x55c50, 0x660=FUN_000561b0, …)
  → shared dispatch registry "Table B": fn-ptr 0xB72AC / CAN-ID 0xB721C / DLC 0xB71B8 /
    channel-byte 0xB7208 (==6 for ALL) / buffer-ptr 0xB7264  (17 entries, sentinel 0x800007FF)
  → HW writer FUN_0001d68e  (byte-scatter of 8 data bytes + DLC)
  → FCN0 message buffer  0xFF481000 + mailbox_idx*64   (SVD FCN0M{N}DAT0B..DAT7B / DTLGB)
```
- **Table B = exactly 17 entries, fully occupied, ZERO free logical slots.** Adding a frame means *extending*
  the 3 parallel arrays (into code cave `0xC4E00–0xC4FEF`, ~528 B), not slotting into a gap.
- **Corrected the prior mission brief** (each ≥2 independent agents, byte-verified): `FUN_00016de6` = DTC/fault
  logger (NOT the mailbox writer); `FUN_000541d8` = pure-RAM checksum/retry state machine (NOT the HW driver);
  `FUN_000520d0`/table `0xBB544` = periodic **RX**-validity/lockstep dispatcher (NOT a TX scheduler).
- **Topology (SVD-grounded):** two CAN controllers declared — FCN0 `0xFF480000`, FCN1 `0xFF4A0000`, 64 msg
  buffers each at `base+0x1000+N*0x40`. **`0xFF489000` is FCN0's OWN +0x9000 sub-block (MID/CTL aliases), not a
  second channel** — corrected an initial B/C mis-read.
- **Forward-verify:** 399 and 0x660 both structurally write **FCN0** (base `0xFF481000` is a compile-time literal
  at 3 sites; both builders have zero direct callers → the fn-ptr dispatch is the only path to HW). FCN1 never
  involved. SVD-byte-exact stores: `0x1d70e st.b → FCN0M{N}DTLGB`; `0x1d78c..0x1d7b8 8× sst.b → DAT0B..DAT7B`.

---

## 3. Why are some frames car-facing and others internal? (deliverable 2 — the core question)

**Answer: we do NOT have a firmware-grounded explanation — but Swarm B ruled out every STATIC mechanism and
localized where the answer must be.**

**Ruled out (each by an independent tracer, cross-reconciled):**
| Candidate | Verdict | Agent |
|---|---|---|
| 2nd controller / 2nd physical bus (internal on FCN1) | **RULED OUT** — only FCN0 clocked+enabled (`FCN0GMCLCTL.PWOM=1` @0xdf5e); FCN1 dead, its 3 `0xFF4A8000` byte-matches are flash padding | Seg 3 |
| Static per-message channel/bus/mailbox field | **RULED OUT** — channel byte==6 for all; mailbox is a **runtime dynamic pool** (RAM table `0xFEDF68BC+idx*2`), no static per-ID field | Seg 2 |
| Transmit-request (`CSETR`) gated by CAN ID | **RULED OUT** — CSETR writes are boot-time, buffer-index-keyed, not ID-keyed (`FUN_0001d68e` never writes CSETR) | Seg 1 |
| Software builder gating / cadence | **RULED OUT** — all 7 builders share one ID-blind dispatch chain (gates key on mailbox idx / HW TRQF/TCPF) | Seg 4 |
| Internal IDs consumed by on-board peer (RX) | **RULED OUT** — none appear in any RX MID match table; pure outbound | Seg 4 |

A single controller running an **ID-blind, dynamically-pooled** path would, taken literally, put all seven on
the one bus the comma taps — yet only three appear. So the discriminator is **not in any traced static code.**

**Where the answer MUST live (localized, not yet read):**
1. **Producers of two dynamic RAM tables** — the `0xFEDF68BC` mailbox-**registration** table and the
   `STATUS[idx]` **pending** table (`gp-0x1744`). All four agents found only *readers*; the **writers are
   unlocated** (compile-time `gp`+small-disp stores invisible to absolute-literal scans, in regions `v850.gnu`
   mis-decodes). **Leading hypothesis:** the producer registers/enqueues only the 3 car-facing IDs in normal
   driving, and the 4 internal IDs only under a diagnostic/bench/special mode.
2. **Physical-layer config not in `code.bin`** — Seg 3 found **no pin-mux (PIPC) writes anywhere** despite FCN0
   working → pin routing (and any second transceiver, or a gateway ECU forwarding only the car-facing subset)
   is set up by the **bootloader or another ECU**. Not confirmable/refutable from this binary.

---

## 4. Capture-side / openpilot-DBC cross-check (answers "did our tool miss them?")

- Cloned openpilot to **`../openpilot`** (outside the kit repo; shallow + opendbc submodule).
- **Our `tools/comma4_can_inventory.py` is RAW** — records every `(bus, addr)` from `p.can_recv()` with **no DBC
  filtering**. openDBC is NOT why the internal IDs are missing from our scan. (Rules out "our tool filtered them.")
- The 2020 Accord (Honda Bosch) uses the `honda_civic_hatchback_ex_2017_can` DBC set. It documents the three
  car-facing EPS transmits — **330=STEERING_SENSORS, 399=STEER_STATUS, 427=STEER_MOTOR_TORQUE** — and **defines
  NONE of 0x19F/0x32E/0x64D/0x660** (not even as comments). Years of comma raw-logging never captured them on the
  harnessed bus → **circumstantial corroboration** they don't reach it. Not proof.

---

## 5. Tooling notes (discovered this session — important for next agent)

- **radare2 5.5.0 + `v850.gnu` is the working combo** on `code.bin` (`r2 -q -a v850.gnu -b 32 -m 0 -s <addr>
  -c 'pd N' code.bin`). Default `v850` plugin is WRONG — never use it.
- **`v850.gnu` has real decode GAPS on V850E2** that bit multiple agents:
  - mis-decodes `ld.bu D16_16[ep],rX` (Seg 2 had to pull GNU binutils `opcodes/v850-opc.c` to decode the nibble
    dispatchers; the extraction formula reproduces the project `-26622` self-check).
  - an undecodable recurring opcode `a2 07` (tentatively a `mov …,ep` form) at boot sites `0x1cfa0-0x1d068`,
    `0xe074-0xe250` (Seg 1 & 3).
  - `af`/`pdf`/`aa`/`axt` are unreliable on this whole cluster — hand-walk with linear `pd`; a manual V850 JARL22
    caller scanner is in the scratchpad (`find_jarl_callers.py`).
- **⇒ The next static step should be Ghidra** (with the SVD loaded) for the driver cluster — its dataflow/xref
  can find the `0xFEDF68BC` / `STATUS[]` writers that four r2 passes could not.

---

## 6. NEXT STEPS

1. **Find the `0xFEDF68BC` registration-table writer and the `STATUS[idx]` (`gp-0x1744`) pending-table writer.**
   This is THE lever for the car-facing/internal split. Use **Ghidra** (v850.gnu is insufficient — see §5).
2. **Alternatively / to confirm: a live trace on the car** — dump `0xFEDF68BC` / `STATUS[]` RAM while the ECU
   runs, or scope the EPS CAN pins, to see whether the internal IDs are ever registered/on-wire in normal
   driving vs only under a diagnostic condition. (Read-only; honors iron rules.)
3. **Before any V36 telemetry build:** resolve what registers 399 into the car-facing path but not 0x660 (same
   producer as #1). Only then is "extend Table B into the `0xC4E00` cave" safe — otherwise the new frame risks
   being invisible like 0x660. See §7.
4. Recompute the pin-mux/transceiver topology from the **bootloader** image (not `code.bin`) if a second physical
   egress needs to be ruled in/out definitively.

---

## 7. ⚠ Practical consequence for the telemetry-frame build

**0x660 is living proof that being a fully-populated Table-B TX entry (builder + ID + DLC) does NOT guarantee
comma-visibility** — 0x660 has all of that and never reaches the comma. Therefore the predecessor handoff's plan
"add the telemetry frame by extending Table B → lands on the same wire as 399" is **necessary but NOT sufficient**.
A naively-added frame could behave like 0x660 (invisible) rather than 399 (visible). The build must replicate
399's *registration/enqueue* into the car-facing path — the mechanism identified as unlocated in §3. This revises
(does not void) the confidence of `reference_accord_can_tx_synthesis_2026-07-07.md`: FCN0-at-the-physical-level is
confirmed; car-facing-visibility is gated by a registration step we have not decoded.

---

## 8. IRON RULES (unchanged)
- **No flash without the operator naming file + bus; repeat it back first.** Everything this session is study.
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin`.
- Before any flash on a comma device, openpilot/pandad must be killed (`tmux kill-server`).
- `tools/comma4_can_inventory.py` and `tools/comma4_panda_test.py` are read-only (SILENT mode) — safe any time
  after openpilot is killed.

---

## 9. KEY ADDRESSES / SIGNALS (this session)
| thing | address / value |
|---|---|
| HW mailbox writer | `FUN_0001d68e` → `0xFF481000 + mailbox_idx*64` (FCN0 DATA); stores `0x1d70e`(DTLGB), `0x1d78c..0x1d7b8`(DAT0B..7B) |
| dispatch registry "Table B" | fn-ptr `0xB72AC` / CAN-ID `0xB721C` / DLC `0xB71B8` / channel-byte `0xB7208`(=6) / buf-ptr `0xB7264`; 17 entries, sentinel `0x800007FF` |
| Table-B idx map | 0-3=0x720-0x723, 4=0x660, 5=0x64D, 6=0x32E, 7=0x1AB(427), 8=0x19F, 9=0x18F(399), 10=0x14A, 11-16=RX-only |
| builders | 399=`FUN_00055c42`@0x55c50, 427=`FUN_00055d80`, 0x14A=`FUN_00055a98`, 0x660=`FUN_000561b0`, 0x64D=`FUN_0005605c`, 0x32E=`FUN_000562b8`, 0x19F=`FUN_00055f2e` |
| **dynamic mailbox registration table** | RAM `0xFEDF68BC + mailbox_idx*2` (sentinel 0xFFFF) — **writer UNLOCATED** |
| **pending/STATUS table** | RAM `STATUS[idx]` at `gp-0x1744` (`0xFEDF68BC`) — **writer UNLOCATED** |
| dispatch coordinator / call sites | `FUN_0001dcaa` (polls FCN0M{idx}CTL 0x203==0x201) → `FUN_0001d96e`(0x1db32, N=0..6) / `FUN_0001db74`(0x1dc8e, mov 6,r6); `0x1d904` dead |
| CAN controllers | FCN0 `0xFF480000` (ONLY one enabled; `FCN0GMCLCTL.PWOM=1`@0xdf5e), FCN1 `0xFF4A0000` (dead) |
| TX-request register | `FCN0M{N}CTL` @ `0xFF489038+N*0x40`; field `CSETR` bit2 = set/cancel TX request; `TRQF` bit9 pending; `STRB.SSOW` bit7 = TX dir |
| boot per-buffer init loop | `0x9ba-0xa46` (64 buffers, `ep=0xFF489028+N*0x40`; MID src `0xFD4+idx*4`, content degrades to ASCII past idx~2); loop bound r12=`gp+0x7E24`(`0xFEDFFE24`, runtime, unpinned) |
| code cave (telemetry stub) | `0xC4E00-0xC4FEF` (~528B 0xFF, CRC block auto-recomputed) |
| comma-visible EPS TX (DBC-documented) | bus1: 330/0x14A STEERING_SENSORS, 399/0x18F STEER_STATUS, 427/0x1AB STEER_MOTOR_TORQUE |
| internal-only (NOT in any opendbc) | 0x660, 0x19F, 0x32E, 0x64D |
| openpilot clone | `../openpilot` (outside kit repo); DBC set = `honda_civic_hatchback_ex_2017_can` |

---

## 10. Artifacts produced this session

**Memory files** (`.claude/agent-memory/firmware-codepath-tracer/`):
- Swarm A: `reference_accord_can_tx_segment{A,B,C,D}_*.md` + `reference_accord_can_tx_synthesis_2026-07-07.md`
- Forward-verify: `reference_accord_can_tx_fcn0_forward_verify.md`
- Swarm B: `reference_accord_can_tx_trigger_path.md` (Seg 1), `reference_accord_can_tx_mailbox_index_map.md`
  (Seg 2), `reference_accord_can_init_mid_pinmux_topology.md` (Seg 3), `reference_accord_internal_id_lifecycle.md`
  (Seg 4)
- **Synthesis (read this first): `reference_accord_why_car_facing_vs_internal_2026-07-07.md`**
- Feedback: `memory/feedback/measurement/feedback_svd_grounding.md` (ground decompilation in the V850 CMSIS-SVD)

**Commits** on `claude/radare2-decompilation-tracers-dreujb` (newest first): `c97d11e` (why-synthesis),
`e83f82b` (Seg 2), `fbc407d` (Seg 4 + Seg 3), `5c5df5f` (Seg 1), `26c992d` (forward-verify), `fda5821`
(feedback-svd), `fe4c233`/`0113f31`/`2a8fcba`/`e662389`/`19e4fd3` (Swarm A). Plus this handoff.
