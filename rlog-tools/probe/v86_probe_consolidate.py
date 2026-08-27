#!/usr/bin/env python3
"""Merge the corrected pass over the first pass into the two deliverable JSONs."""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1].parent
coh = json.loads((ROOT / "_scratch/cache/r6f/probe_v86_coherence.json").read_text())
cross = json.loads((ROOT / "_scratch/cache/r6f/probe_v86_cross_route2.json").read_text())

PROV = {
    "tq": "raw CAN 0x18F(399) bytes0:1 x -1 == STEER_TORQUE_SENSOR negated. The 399 packer is "
          "FUN_00055c42 @0x55c50 and sends STEER_TORQUE_SENSOR = -(gp-0x4f60 x 125/128), so `tq` "
          "is a scaled readout of the FIRMWARE RAM cell gp-0x4f60 -- the column / torsion-bar "
          "torque signal. [EVIDENCE for the packer: docs/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-"
          "2026-07-06.md:41]. NOTE the kit also records a SECOND torque sensor (gp-0x6a62) that is "
          "NOT this one -- see handoffs/2026-06/HANDOFF-2026-06-30-sensorA-identity-gate-scale.md.",
    "cs_tq": "openpilot carState.steeringTorque -- an INDEPENDENT parse of the same 399 field. It "
             "agrees with `tq` to within the probe's resolution: the required second method.",
    "probe": "CAN 0x14A(330) byte4 bits 7:3, written by the 68-byte cave at 0xC4B34. A DIFFERENT "
             "frame and a DIFFERENT packer from 399, so the probe/torque agreement below is not a "
             "same-frame packing artefact.",
}
EPISODES = {"note": "engaged episodes >= 2 s: route 6f = 1, route 70 = 3. An EPISODE-level "
                    "bootstrap is impossible at n=1. Every CI here is a 5 s BLOCK bootstrap, i.e. "
                    "a WINDOW bootstrap, and is therefore OPTIMISTIC -- see "
                    "feedback-episodes-not-windows. Treat every interval as a lower bound on width."}

for tag, f1, f2 in (("6f", "_scratch/cache/r6f/probe_v86_physics.json",
                     "_scratch/cache/r6f/probe_v86_physics2.json"),
                    ("70", "_scratch/cache/r70/probe_v86b_physics.json",
                     "_scratch/cache/r70/probe_v86b_physics2.json")):
    a = json.loads((ROOT / f1).read_text())
    b = json.loads((ROOT / f2).read_text())
    a["relay_vs_linear"] = b["relay_vs_linear"]        # the CORRECTED pass supersedes the first
    a["sign_drivers"] = b["sign_drivers"]
    a["information_gain"] = b.get("information_gain")
    a["strata"] = b["strata"]
    a["coherence_probe_vs_can"] = coh[tag]
    a["cross_route"] = cross
    a["channel_provenance"] = PROV
    a["episode_structure"] = EPISODES
    (ROOT / f1).write_text(json.dumps(a, indent=1), encoding="utf-8")
    print(f"wrote {f1}  ({len(json.dumps(a)):,} bytes)")
