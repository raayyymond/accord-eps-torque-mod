# HANDOFF — 2026-07-12 — comma 4 live RAM-telemetry: bus/OBD analysis + gentle-EME rlog diagnosis

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas uPD70F3508 / V850E2. **STOCK analysis program =
`code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0). Bases: `gp(r4)=0xFEDF8000`,
`tp(r5)=0xBF000`. **Flashed: V31U** (V31 drivability + repurposed UDS DID `0x4801`). Openpilot = operator's
**StarPilot** fork on a **comma 4**, at `../openpilots/raayyymond-StarPilot/StarPilot` (branch `Dom`).

**Builds on** `handoffs/2026-07/HANDOFF-2026-07-11-starpilot-eps-telem-rlog-analysis.md` (the fork's in-drive UDS poller) and the
07-07/07-08 CAN-TX visibility handoffs. This session analyzed the operator's real rlogs, diagnosed the gentle
EME, and root-caused why the in-drive UDS poll returns nothing — down to the panda hardware.

---

## 0. One-line state

**Two results.** (1) **Gentle-EME diagnosed from the rlogs** (route `807a3c21c9f405e8_00000058`): the stock
torque disengage (`gp-0x6a62 ≥ cal 0xC6312 = 320`, still live on V31U) fires during a demanding curve where
openpilot's LKAS command is **saturated (4096)** and a road disturbance (railroad tracks) rings the column
torque past threshold. (2) **The in-drive UDS telemetry poll cannot work on the comma 4**: reaching the EPS
diagnostic requires **OBD multiplexing** (bus 1 → OBD-II), which is the *same* FDCAN2 peripheral that carries
steering. CAN broadcast is separately dead (gateway-blocked). **Operator wants LIVE logging of RAM values (a
reusable capability), NOT the Tier-2 ring-buffer post-drive readout.** The pivotal open experiment: **does the
comma keep steering while staying on OBD mux?** (predicted no; read-only test defined in §5).

---

## 1. Gentle-EME diagnosis (the original task) — DONE

The rlogs had **no `epsTelemetry`** (see §2), so this was reconstructed from comma-visible CAN 399/427/228
(hand-decoded against `_bosch_2018.dbc`). Tooling: `rlog-tools/` + scratch scripts (extractor decodes CAN 399
STEER_STATUS/STEER_TORQUE_SENSOR/STEER_ANGLE_RATE, 427 MOTOR_TORQUE, 228 cmd).

- **The 2:08 event** = route t≈130.4–132.0 s, ~42 mph, LKAS engaged in a left curve: **three
  `STEER_STATUS=NO_TORQUE_ALERT_2` cuts** (91/91/130 ms), each with `STEER_CONTROL_ACTIVE→0` and delivered
  torque → 0 while openpilot's `cmd_torque` stays high/**saturated at 4096**. 6 gentle-EME runs total in the
  drive; the 2:08 cluster is the operator's railroad-track event.
- **Mechanism:** the column-torque sensor rings ±2000–3000 (angle-rate spikes 40–70°/s = the track jolt) on top
  of a saturated LKAS command; the internal MAX-of-5 rising-edge voter `gp-0x6a62` crosses `0xC6312`=320 → the
  engage-SM decider `FUN_00040d58` cuts LKAS torque ~90 ms. The trip is **not** a fixed CAN |torque| (cut #3
  tripped at −2262 while −1961 moments earlier was normal; cut #1 tripped at +1467) — consistent with the
  rising-edge/MAX-of-5 internal signal, of which CAN `STEER_TORQUE_SENSOR` is only a filtered proxy.
- **Direction asymmetry** (EME one way over the tracks, not the other): the trip needs the column-torque **peak**
  to cross 320 = directional (camber/curve) steady load + the disturbance. Only in the EME direction was the
  LKAS command **saturated** (column pre-loaded near threshold), so the bump crossed it; the reverse pass had
  more margin. `carstate.py:128` corroborates the trigger class: *"NO_TORQUE_ALERT_2 can be caused by bump or
  steering nudge from driver"* (and openpilot deliberately does NOT flag it as a fault — which is why it's
  invisible in `carState` and needs raw CAN 399).
- **Note:** V31U does NOT include V33's `0xC6312`→65535 disable, so the gate is live — the EME firing is
  expected on this build. See `[[gentle-eme-fires-on-saturated-lkas-command]]` (memory).

---

## 2. Why there was no `epsTelemetry` in the rlogs — ROOT-CAUSED

The fork IS deployed and the poller IS running (source build live): `sendcan` shows the request `22 48 01` →
`0x18DA30F1` on bus 1 ~10 Hz (bus-129 TX echo confirms egress; the honda.h whitelist works). **But the EPS
returns ZERO `0x4801` responses during driving** (seg 1/2/4/5: ~600 requests each, 0 replies — not even an
ISO-TP First Frame). The only diagnostic replies in the whole route are the boot **firmware-fingerprint**
responses (DID 0xF181/0xF112) during the ~1 s ELM327+OBD-mux window, where the 399 broadcast momentarily
vanished from bus 1. `epsTelemetry` is therefore never published → absent. **Not a fork/poller/param bug.**

---

## 3. On-car diagnostic sweep (2026-07-12) — the routing is now pinned

Read-only bench sweep (openpilot killed, parked, comma 4 built-in panda, `tools/bench_uds_telem_read.py` with
the new `--obd` flag) + `comma4_can_inventory.py` + `sniff_can_id.py`. Results (`guides/inventory_scan_20260712.txt`):

| arm | bus | OBD mux | result |
|---|---|---|---|
| A1 | 1 | off | **FAIL** (0 replies / 32 err) |
| A2 | 1 | **on** | **WORKS** |
| A3 | 0 | (off) | would fail — no EPS on bus 0 |
| A4 | 2 | (off) | would fail — no EPS on bus 2 |

- **Topology (comma 4, this car):** **bus 1 = F-CAN** (EPS feedback 399/427/330 + openpilot's 228 injection +
  powertrain). **bus 0 = bus 2 = camera/ADAS bus** (100 identical IDs: lane-lines `0x2xx`, `0x400` radar).
  `sniff_can_id 0x18F`: 500 frames on bus 1, **0 on bus 0, 0 on bus 2**.
- **The EPS diagnostic server is reachable only via OBD-II** (A2), which the comma's single **FDCAN2 = bus 1**
  reaches only by OBD multiplexing (`panda/board/boards/cuatro.h`→`tres_set_can_mode`, `CAN_MODE_OBD_CAN2`).
  That is the *same* peripheral steering needs. **⇒ live UDS poll during active LKAS is blocked on the comma 4.**
- **CAN broadcast dead (live-confirmed):** inventory shows `0x660/0x19F/0x32E/0x64D` **ABSENT** on every bus —
  the external gateway forwards only `{399,427,330}` (+ diagnostic addressing). A new EPS TX ID is invisible
  (matches 07-08). The visible frames are all safety-relevant steering signals.
- **Read-path caveat found on-car:** a *static* live UDS read of `gp-0x4f68` (|coltq|) can return a
  stale/latched value while CAN 399 shows live torque — an ECU response-cache effect on the live-read path.

---

## 4. What the operator wants + the constraint

**Operator's directive:** LIVE logging of EPS RAM values into the drive log — a **reusable capability** for
future mods — **NOT** the Tier-2 firmware ring-buffer + post-drive readout. And: **challenge the "flip to OBD /
poll / flip back" framing — does *staying* on OBD mux permit steering?**

The hard constraint: on the comma 4, "read the EPS diagnostic" (OBD-II) and "steer" (F-CAN) both want the single
FDCAN2/bus-1 peripheral, and they are mutually exclusive there. So a live channel must either (a) make OBD-mux
coexist with steering, (b) tap the diagnostic bus with a *second* physical interface, or (c) push the RAM values
through a channel the gateway already forwards.

---

## 5. NEXT SESSION — settle "stay on OBD?", then pick a live path

### 5a. THE pivotal experiment — does the comma steer while on OBD mux? (read-only first)

**Prediction: NO.** With OBD mux ON, bus 1 = the gateway's OBD-II diagnostic side; the boot data already showed
399 *vanishes* from bus 1 under mux. openpilot's control loop needs 399/427 at 100/50 Hz (state estimate + fault
monitor) — without them it faults/won't steer — and the gateway will not forward openpilot's 228 from the OBD-II
port to the EPS. But TEST it, don't assume:

```bash
tmux kill-server
# set OBD mux on, then confirm whether steering feedback survives (READ-ONLY):
python3 -c "import sys; sys.path[:0]=['/data/openpilot/third_party/panda','/data/openpilot']; from panda import Panda; Panda().set_obd(True); print('obd on')"
python3 sniff_can_id.py --id 0x18F --bus 1 --seconds 10   # 399 present? (predict ABSENT)
python3 sniff_can_id.py --id 0x1AB --bus 1 --seconds 10   # 427 present? (predict ABSENT)
python3 comma4_can_inventory.py                            # full picture on bus 1 under mux
python3 -c "import sys; sys.path[:0]=['/data/openpilot/third_party/panda','/data/openpilot']; from panda import Panda; Panda().set_obd(False)"  # restore
```

- **399/427 ABSENT under mux** ⇒ staying-on-OBD cannot steer (feedback gone). Settles the challenge; move to 5b.
- **399/427 PRESENT under mux** ⇒ surprising and promising — then a careful *engaged* test (wheels safe) of
  whether openpilot both delivers 228 and reads feedback while on OBD. If that holds, **live UDS poll during
  LKAS is the comma-native general capability** (poll DID 0x4801 / any RAM DID at tens of Hz, already logged by
  the fork's `epsTelemetry` service).

### 5b. If staying-on-OBD fails — the live-logging options (ranked), pick one

1. **Second physical tap: red panda on an independent OBD-II Y-splitter, in parallel with the comma.** Comma
   steers on F-CAN (bus 1 normal); red panda sits on the OBD-II diagnostic bus and polls UDS continuously — no
   mux conflict (two separate interfaces), no firmware change, **full UDS bandwidth / any RAM value**. The
   shared-cable objection is exactly what a splitter removes. **Verify the splitter point is a real independent
   OBD-II tap that does not share the comma's steering bus** (car OBD-II port under the dash, or a harness
   OBD-II breakout that is live without the comma's mux). Red panda logs to a laptop/SD; merge with the rlog by
   timestamp. This is the most general/highest-bandwidth live capability with zero firmware risk.
2. **Firmware spare-bit piggyback on a gateway-FORWARDED frame (399/427/330).** The gateway forwards these to
   the comma, so RAM values stuffed into genuinely-unused bits ride into the raw `can` log live, continuously,
   during LKAS — no OBD, no bus conflict, no openpilot change (raw CAN is logged; decode offline). This is the
   comma-native, always-on, general channel. **Requires:** (i) a DBC + firmware audit of which bits in
   399/427/330 are truly unused by the car AND openpilot's carState (do NOT overwrite STEER_TORQUE_SENSOR /
   STEER_ANGLE_RATE / STEER_STATUS / angle — safety signals), (ii) editing the relevant builder(s)
   (399=`FUN_00055c42`, 427=`FUN_00055d80`, 330=`FUN_00055a98`) to multiplex RAM values into the spare bits with
   the Honda 4-bit checksum kept valid (the builder recomputes it). Bandwidth is limited (few spare bytes →
   round-robin), so it may not hit ≥50 Hz on all four voters at once, but it is a real reusable RAM→rlog channel.
3. **(rejected by operator) Tier-2 ring buffer + post-drive UDS readout** — works and is fully designed
   (07-07 §Tier-2), but it is not live logging. Left here only for completeness.

**Recommendation:** run 5a first (cheap, settles the challenge). If it fails as predicted, evaluate Option 1
(no-firmware, highest bandwidth, needs a verified independent OBD-II tap) vs Option 2 (comma-native, firmware,
limited bandwidth) against how much data the future mods need and whether an extra tap is acceptable.

---

## 6. Artifacts this session

- `tools/bench_uds_telem_read.py` — added a safe `--obd on/off` flag (calls `panda.set_obd`; default = untouched,
  matching the red-panda/flasher path). Syntax-checked. Used for the A1/A2 sweep.
- `guides/inventory_scan_20260712.txt` (operator-captured) — the on-car sweep + bus inventory this analysis rests on.
- This handoff; memory updates (`comma4-eps-uds-poll-comma-vs-redpanda`, `eps-telem-red-panda-cannot-poll-during-lkas`,
  new `gentle-eme-fires-on-saturated-lkas-command`, new feedback memory).

## 7. Iron rules (unchanged)

- **No CAN/UDS send or flash without the operator naming the exact payload/file + bus; repeat it back first.**
  The three read-only frames used this session (operator-run): `22 48 01`/`3E 00` to `0x18DA30F1` bus 1, ISO-TP
  flow control `30 00 00`. `set_obd` is a panda relay config (no bus TX).
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin`.
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`). `comma4_can_inventory.py` /
  `sniff_can_id.py` / `panda_can_sniff.py` / `panda_rx_health.py` are read-only (SILENT), safe.
- ⚠ r2's default `v850` plugin mis-decodes V850E2 — use `v850.gnu`, or Ghidra (`master.bin`) for gp-relative loads.
