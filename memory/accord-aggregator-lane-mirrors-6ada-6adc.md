---
name: accord-aggregator-lane-mirrors-6ada-6adc
description: "Both inline torque-rate lanes are mirrored to RAM post-clamp and NOTHING reads them — gp-0x6ada (r24) and gp-0x6adc (r26) are free, blast-radius-zero telemetry taps."
metadata: 
  node_type: memory
  type: reference
  originSessionId: afe7e152-cb42-4ab4-922a-42b0e91a5421
  modified: 2026-08-04T04:35:03.610Z
---

★★ **`FUN_0003aa2c` stores both inline lane outputs to RAM, AFTER their ±0x2000 saturating clip, and
NOTHING IN THE FIRMWARE READS EITHER CELL.**

| cell | written at | what it holds | census |
|---|---|---|---|
| `gp-0x6adc` | `0x3AD4E` | **r26** lane out, post-clamp | **0 readers / 1 writer** image-wide |
| `gp-0x6ada` | `0x3AD5A` | **r24** lane out, post-clamp | **0 readers / 1 writer** image-wide |

Both `st.h` ⇒ **SIGNED halfwords**. Census re-derived from raw bytes by `V64.gp_access_census`, two
decoders (the required second method — `search_instructions` silently undercounts).

⇒ **These are free telemetry taps on exactly the quantity every rate-lane build scales**, and they
carry the **strongest GATE-1 statement available anywhere in this chain**: nothing consumes them, so
a probe that reads one cannot perturb anything even in principle. V69's bit6 reads `gp-0x6ada` at
threshold +4096 = **half its ±8192 rail**, which makes the bit's duty a direct rail-proximity meter
— see [[accord-v69-ratchet-probe]].

⚠ **r26 is structurally inert on this ROM** (`avg` cal base `0xC6564` = 40 zero bytes), so
`gp-0x6adc` is expected to read ~0. Probing it would be a rung spent on a known constant — the exact
error V68's original bit4 made. **`gp-0x6ada` is the useful one.**

🛑🛑 **THE ONE-BIT TRAP, AND IT IS CONCRETE HERE.** `ld.h` is opcode **0x39**; `st.h` is **0x3B**.
`gp-0x6ada`'s *only* real instance in the image **is** the `st.h` form (`64c72695` @`0x3AD5A`) and it
carries **the same displacement halfword** that an `ld.h` probe must emit (`24372695`). A single bit
turns the read into a **write into a 1 kHz aggregator lane**. Assert the opcode field **by value**,
in the builder and independently in the verifier — see [[accord-v850-scan-traps-formatv-and-storezero]].

Recorded in the golden model at `eps_lkas_chain_model.py`'s `motor_torque_demand_aggregator`
docstring.
