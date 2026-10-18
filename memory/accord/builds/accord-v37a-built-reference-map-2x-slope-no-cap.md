---
name: accord-v37a-built-reference-map-2x-slope-no-cap
description: "2026-10-17: the operator's Downloads rwd '…V37-2xTorque.rwd' IS V37 byte-exact (sha 8a809d1b…); V37A BUILT NOT FLOWN = V37 with the 2× moved from the torque constant onto the rate-reference map (28 records → line, slot 7 Y = 4·idx exactly, no cap; 0xC62E6 7680→42865; 0xC646C/0xC61B2/B4 back to stock 891/512/512); peak LKAS torque HALVES to Honda's 410, reference 2× small-signal / 5.6× top, P rails from idx 63 at a stall; four adversarial lenses PASS_WITH_DEFECTS; rwd c9bd3446…, image 7cb6fd3a…; page https://claude.ai/artifact/TavHVFCPZmYEeNng6e5Loq"
metadata:
  type: project
---

**Identification:** the Downloads file decrypts to `_v37_plain_image.bin`; V37 vs stock is 42 bytes (V18 gain/clamps, V25–V31 corridor/boost, V36/V37 debounce/DTC cals, ramp, PN, CRCs). Pre-telemetry base — no cave, no tap; the lane's forward gain is the SHARED `0xC646C` (no V57 decouple).

**V37A (`builds/v18_v49/build_v37a_tva.py`):** [A] Y[i] = round(2·Y[1]·X[i]/12) on all 28 assist-map records (live slot 7: 0,48,…,960 = 4·idx at every idx; selectors 0/2/4/5 off a line by ≤ 1.17 counts); [B] fb clamp 42865 = Honda's 1.3953 sp:fb ratio at the new top (3 `ld.hu` readers — verified by the orchestrator's own positive-controlled scan); [C] gain/clamps stock. Delivered: P rails from idx 63 at fb = 0, T 410 (stock 399, V37 799 at idx 240); null rate at idx 120 ≈62 deg/s (stock 19).

**Adjudicated risk:** the 0xE4 RX-fault sentinel (0x7FFF → idx 238) now rails P for 2.048 s at 410 T chasing 123 deg/s (stock 397 toward 22; V37 794). Mitigation `0xC63F6` 16→328 exists, NOT applied. Other defects: V280's 7 Hz stall ripple reachable at 1/6 torque (BELIEF milder); DTC 0x5E observer under stall (BELIEF); V36/V37 trips off ⇒ no firmware override.

**Why:** the kit's post-V38 diagnosis ([[accord-lkas-commands-rate-not-torque]]): torque never bought angle rate because the map is the REFERENCE. V37A is the first reference-lever build on a STOCK-torque image. **How to apply:** if flown, read wheel rate per idx at idx ≤ 60 (should double) and the strong-turn ripple; null = inert (selector ≠ 7). Lineage `BUILD-LINEAGE-PART6-V291-ONWARD.md` V37A; handoff `HANDOFF-2026-10-17-v37a-reference-map.md`. Related: [[accord-scaling-a-setpoint-does-not-scale-its-feedback]], [[accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire]].
