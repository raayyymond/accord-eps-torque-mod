---
name: feedback_full_frame_logging
description: Iron rule — every live CAN operation (XCP or UDS) must log the full frames (TX + relevant RX), not summaries.
metadata:
  type: feedback
---

Operator iron rule (Joey, 2026-06-02): **every live thing we do on the bus must log the full XCP/UDS frames** — every TX frame and every relevant RX frame (CTO/DTO, UDS req/resp), with timestamps, to a file we keep. Summarized/decoded-only output is not acceptable for live ops.

**Why:** during the RDX A030 XCP/UDS probing, the decisive evidence (UDS answers, XCP is silent; the panda safety-mode/transport bug) only became legible once we saw raw frames on the wire. Summaries hid the loopback echoes and the missing DTO. Frame-level logs are the ground truth that resolves "tool bug vs ECU-side" questions and feeds the gemini consults.

**How to apply:**
- Wrap `panda.can_send`/`can_recv` so every frame is logged (TX always; RX for the relevant id set — XCP `0x640-0x647`, UDS `0x18DAxxF1`/`0x18DAFxxx`). Don't dump the whole busy vehicle bus, but never drop a frame in our own exchange.
- Tee to a timestamped logfile on the comma (`/data/dordo-recovery/*.log`) and pull it back into the kit.
- Bake this into `xcp_probe_rdx.py` / `xcp_dump_rdx.py` / any UDS ripper, not just ad-hoc scripts.
- Working transport for this comma+EPS: `Panda(disable_checks=True)` + `set_safety_mode(3)` (ELM327), bus 1. `SAFETY_ALLOUTPUT` and `set_obd(True)+ALLOUTPUT` do NOT reach the EPS. See [[reference_rdx_tjb_cipher]] / project handoff.
