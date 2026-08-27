---
name: eps-deliver-cut-gp6809-broken
description: "V31P's DELIVER_CUT telemetry bit (330 byte7 bit7 = gp-0x6809 != 0) is BROKEN — it reads 0 in 100% of frames, so its silence is NOT evidence about which gate causes the gentle EME. V31P-V2 drops it. Verified 2026-07-13 in Ghidra on stock code.bin."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 03c81800-2f2f-4926-9e12-b63017e563a6
---

> **CORRECTION 2026-07-14 (Ghidra, self-verified) — `gp-0x6809 != 1` is NOT the cut; it is DEAD CODE.**
> `gp-0x6809` has **zero writers** in the whole image (re-confirmed: 4 `ld.bu` reads only, hex + decimal
> `26633` searches empty), so it can never equal 1 → the `cmp 0x1,lp / bne` bail at `0x29768` etc. is taken
> **unconditionally every cycle** = a dead gate protecting a permanently-zero term (`gp-0x6b2c`). So point #1
> below ("firmware zeroes the LKAS term when `gp-0x6809 != 1`") is WRONG — that path is inert, not the cut.
> Point #3 (no writer) was the correct seed. **The gentle EME is actually produced by the debounce state
> machine `FUN_0002a30e` (+ arb twin), and `STEER_STATUS=4` is a lagging REPORT; the real motor-zeroing
> instruction is still unlocated.** Full record: [[v36-debounce-sm-root-cause-and-build]]. Net effect on this
> memory's advice is unchanged: still ignore any V31P `deliver_cut` reading and anchor on CAN 399.

**Verified 2026-07-13 (Ghidra, stock `code.bin`, 2020 Accord `39990-TVA-A160`).** V31P's
`DELIVER_CUT` bit was meant to be the "physical cut happened" anchor, independent of the 5 gate
flags. It is broken three independent ways, so a session that saw it read 0 must NOT conclude
"none of the gates cause the cut":

1. **Wrong condition.** The firmware zeroes the LKAS term in `m_steer_torque_arbitration`
   (`FUN_00028ea6`) when the deliver flag `gp-0x6809 != 1` — verified at BOTH read sites
   `0x2975a` and `0x29808` (`ld.bu -0x6809[gp],lp ; cmp 0x1,lp ; bne <bail>`). V31P tests
   `gp-0x6809 != 0`. Different condition, and for a "cut" flag the polarity is backwards
   (if 1 = delivering, `!= 0` reads closer to "delivering" than "cut").
2. **Wrong sampling.** It is a LIVE-READ inside the 330 builder (`FUN_00055a98`), one phase
   sample per frame — not latched at the decision site like the 5 gate flags. It reads 0 in all
   ~30k frames even though LKAS was actively delivering (which needs `gp-0x6809 == 1` at the
   arbitration read). Same address, different execution phase.
3. **`gp-0x6809` has NO gp-relative writer** in the whole 185k-instruction image (only 4 reads,
   all in `m_steer_torque_arbitration`; written indirectly). The gate-bail → `gp-0x6809` hop was
   never byte-traced end-to-end, and prior analysis judged that arbitration function UNLIKELY to
   be the gentle-EME root cause (its bail thresholds sit 7–10× above real driving magnitudes).

**Deeper point:** the gentle EME has no single downstream "cut instruction" distinct from the
gates — it IS the deliver-commit being skipped (gate bails) → the LKAS command `gp-0x6b98` stops
being refreshed while the motor stays enabled. The one real downstream all-motor-disable
(`gp-0x676e==4` in `FUN_0003d4a2`) is the HARD cut, not the gentle one.

**How to apply:** Ignore any V31P `deliver_cut`/`deliverCut` reading. Anchor gentle cuts on raw
CAN 399 `STEER_STATUS=no_torque_alert_2`. V31P-V2 repurposes 330 byte7 bit7 to `hardCut`
(`gp-0x676e==4`, latched at `0x3de6c`). Related: [[v31p-gateflags-330-piggyback-built]],
[[eps-gp67fe-trump-engaged-holding-substate]], [[gentle-eme-fires-on-saturated-lkas-command]].
