---
name: eps-telem-red-panda-cannot-poll-during-lkas
description: "Red panda can read the Accord EPS UDS telemetry (DID 0x4801) on bus 1 (comma NOT steering) but cannot poll while the comma drives LKAS — they share one cable. Live gentle-EME capture must come from the comma 4's built-in panda, which does not yet complete the round-trip."
metadata: 
  node_type: memory
  type: project
  originSessionId: da1ed7ee-745a-43f9-a29b-a7b80b6ac40f
---

The red panda reads the 2020 Accord EPS gentle-EME UDS telemetry (DID `0x4801` → `0x18DA30F1`, resp `0x18DAF130`) on **bus 1** over the same harness cable it shares with the comma — but **only when the comma is NOT steering** (openpilot killed). The operator **cannot** have the red panda poll while the comma is actively steering (one shared cable). So the red panda is fine for static / hand-turn snapshots but is **NOT** a path to the live gentle EME (the two LKAS voters only move under active LKAS).

**Why the red-panda path works at all:** the app ISO-TP UDS crosses the car gateway to bus 1 (that's how the EPS is flashed); the red-panda flasher/bench rig reaches it with **ELM327 safety mode and NO OBD multiplexing** (no `set_obd` in `eps-update-tva.py`/`bench_uds_telem_read.py`). So the EPS diagnostic is reachable on plain bus 1 — not OBD-II-only, not a bandwidth issue.

**How to apply:** The live capture must come from the **comma 4's built-in panda** (fork at `../openpilots/raayyymond-StarPilot/StarPilot`, branch `Dom`). BUT that panda does not yet complete the UDS round-trip the red panda completes on the same wires — an unresolved comma-panda config/routing issue (NOT impossible, NOT bandwidth, NOT the gateway). Do not pursue a firmware CAN broadcast (gateway-blocked — ruled out 07-08). See [[comma4-eps-uds-poll-comma-vs-redpanda]] for the corrected analysis and the read-only on-car experiment sweep to crack it. Related: [[gentle-eme-fires-on-saturated-lkas-command]].
