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

⚠ ~~**r26 is structurally inert on this ROM** (`avg` cal base `0xC6564` = 40 zero bytes), so
`gp-0x6adc` is expected to read ~0. Probing it would be a rung spent on a known constant.~~
🛑 **DOWNGRADED 2026-08-04 to BELIEF — see [[accord-r26-is-structurally-inert]].** `0xC6564` **is** 40
zero bytes, but **its link to `gp-0x69a4` was never verified** (the real producer is a live runtime
10-segment LERP at `0x355C6` in `FUN_000352b4`). ⇒ **`gp-0x6adc` is NOT a known constant, and probing
it is no longer a wasted rung — it is the measurement that settles the question.**

## ★★ THE MEASUREMENT — `gp-0x6adc` vs `gp-0x6ada` is a MATCHED SIGN PAIR
r24 and r26 share **ONE polarity load** — `ld.b -0x6752[gp],r14` @`0x3AB78`, reused at `0x3AB7E` (r26)
and `0x3AC3E` (r24) — so **they always carry the same sign** (`gp-0x69a4` is an unsigned magnitude at
both ends). Therefore, with r26's mirror on one bit and r24's on another:

| observation | verdict |
|---|---|
| **bit4 pinned at 1 while bit3 toggles** | **r26 is ZERO** ⇒ r24 carries the lane, as believed |
| **bit4 TRACKS bit3** | **r26 is LIVE** ⇒ the V42/V61/V62 single-lane re-attribution falls |

**Non-vacuous in both directions. V70 flies exactly this pair.**

⚠ **And V69's bit6 threshold on `gp-0x6ada` failed for a different reason entirely:** on route `4f` the
replay predicts **~1** one-sided hit, observed **0**, **p ≈ 0.37** — no exposure, hence no positive
control. A *sign* rung does not have that problem, which is part of why the pair above is the right
instrument. See [[feedback-size-probe-rungs-against-lane-reachable-output]].

🛑🛑 **THE ONE-BIT TRAP, AND IT IS CONCRETE HERE.** `ld.h` is opcode **0x39**; `st.h` is **0x3B**.
`gp-0x6ada`'s *only* real instance in the image **is** the `st.h` form (`64c72695` @`0x3AD5A`) and it
carries **the same displacement halfword** that an `ld.h` probe must emit (`24372695`). A single bit
turns the read into a **write into a 1 kHz aggregator lane**. Assert the opcode field **by value**,
in the builder and independently in the verifier — see [[accord-v850-scan-traps-formatv-and-storezero]].

Recorded in the golden model at `model/eps_lkas_chain_model.py`'s `motor_torque_demand_aggregator`
docstring.
