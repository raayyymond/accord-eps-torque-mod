---
name: comma4-eps-uds-poll-comma-vs-redpanda
description: "RESOLVED (2026-07-12 on-car sweep): the comma 4 built-in panda reaches the EPS UDS ONLY via bus 1 + OBD multiplexing (A2 works; A1 no-mux fails; bus 0/2 have no EPS). OBD mux = FDCAN2/bus-1 -> OBD-II = the same peripheral that carries LKAS control, so live UDS during active steering is blocked on the comma 4. CAN broadcast is also dead (gateway-blocked, live-confirmed). Operator wants LIVE RAM logging (NOT Tier-2 post-drive readout). Open pivot: does the comma steer while STAYING on OBD mux?"
metadata:
  node_type: memory
  type: project
  originSessionId: da1ed7ee-745a-43f9-a29b-a7b80b6ac40f
---

**On-car sweep 2026-07-12 (comma 4 built-in panda, openpilot killed, parked) — routing pinned:**

- **A1 (bus 1, OBD off): FAILS** (0 replies). **A2 (bus 1, OBD on): WORKS.** So the comma 4 reaches the EPS UDS server **only with OBD multiplexing** (bus 1 -> OBD-II).
- **A3/A4 (bus 0/2) would fail:** inventory + `sniff_can_id` prove the EPS is bus-1-only (399/427/330 on bus 1; 0 frames on bus 0/2). Bus 0/2 are the camera/ADAS bus.
- **OBD mux = FDCAN2/bus-1 -> OBD-II port** (`cuatro.h`->`tres_set_can_mode`, `CAN_MODE_OBD_CAN2`) — the SAME single peripheral that carries EPS control (399/427 in, 228 LKAS out). One peripheral, two mutually-exclusive destinations => **live UDS during active LKAS is blocked on the comma 4 built-in panda.**
- **CAN broadcast is dead (live-confirmed):** 2026-07-12 inventory shows `0x660`/`0x19F`/`0x32E`/`0x64D` **ABSENT** — external gateway forwards only {399,427,330}. A new EPS TX ID is invisible.
- Read-path caveat: a static live UDS read of `gp-0x4f68` can return a stale/latched value (ECU response cache) while CAN 399 shows live torque.

**Operator directive (2026-07-12): wants LIVE logging of EPS RAM values — a reusable capability for future mods. Explicitly NOT the Tier-2 ring-buffer + post-drive readout.** And challenged the "flip to OBD / poll / flip back" idea: **does the comma keep steering while STAYING on OBD mux?**

**Open pivot (test next session, read-only first):** set `panda.set_obd(True)`, then `sniff_can_id --id 0x18F --bus 1` and `--id 0x1AB` — are 399/427 present under mux? **Predicted ABSENT** (boot data showed 399 vanishes under mux; OBD-II is the gateway's diagnostic side and does not carry the F-CAN broadcasts openpilot's control loop needs; the gateway also won't forward 228 from OBD-II). If absent, staying-on-OBD can't steer.

**Live-logging options if staying-on-OBD fails (ranked):** (1) **red panda on an independent OBD-II Y-splitter** in parallel with the comma (comma steers F-CAN, red panda polls OBD-II live; no firmware, full UDS bandwidth; verify the splitter is a real independent OBD-II tap not sharing the steering bus); (2) **firmware spare-bit piggyback on a gateway-forwarded frame** 399/427/330 (RAM values into truly-unused bits -> raw `can` log, live, no bus conflict; needs a DBC+firmware spare-bit audit + builder edit `FUN_00055c42`/`FUN_00055d80`/`FUN_00055a98`, checksum kept valid; limited bandwidth). Full plan: `docs/handoffs/2026-07/HANDOFF-2026-07-12-comma4-uds-live-telemetry-bus-analysis.md` §5. Related: [[eps-telem-red-panda-cannot-poll-during-lkas]], [[gentle-eme-fires-on-saturated-lkas-command]], [[operator-wants-live-general-capabilities]].
