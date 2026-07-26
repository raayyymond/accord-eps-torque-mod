---
name: reference-accord-b7260-io-mailbox-array
description: The gp-0x1401..0x1502 "poison region" is a subset of a 40-slot × 8-byte I/O-mailbox array listed at 0xb7260 (0xFEDF6AE0..0xFEDF6C18); gp-0x1500 and gp-0x14E0 are LIVE slots. Static RAM clearance fails here — probe live.
metadata:
  type: reference
---

The low-RAM region previously called the "poison region `gp-0x1401..0x1502`" is only a subset of a larger,
now fully-mapped structure: a **40-slot × 8-byte I/O-mailbox / buffer registry**. The slot base-addresses are
listed in a table at **`0xb7260`** (spans `0xb7260..0xb74a8`; hard upper bound = it terminates exactly where
the UDS SID-0x30 session/SA data + the RID table at `0xb7500` begin). The 40 registered RAM slots run at
**exact 8-byte stride from `0xFEDF6AE0` (gp-0x1520) to `0xFEDF6C18`**, then a 23-byte gap
(`gp-0x13E7..gp-0x13D1`, unverified — do not use), then a 2-entry non-8-stride tail (`0xFEDF6C30/6C34`).

Known slots: **slot 2 = `0xFEDF6AE8` = the CAN-330 TX buffer** (the one the V31P/V49P/V50P telemetry probes
hook via `FUN_00055a98` @ `0x55c0e`, `movea -0x1518,gp,r6`), slot 3 = the CAN-660 TX buffer,
**slot 5 = `gp-0x1500` (`0xFEDF6B00`)**, slot 9 = **`gp-0x14E0` (`0xFEDF6B20`)**. Slots are written by
**table-dispatched (register-indirect) pointers** — precisely the blind spot that direct disp16 /
absolute-literal static scans cannot see.

**Consequences (load-bearing):**
- **`gp-0x1500` is NOT free RAM** — it is a live I/O-mailbox slot, written continuously in normal driving
  (proven on-car by the V50P probe: 0 for ~1.15 s at boot, then non-zero on 99.47% of the drive; the lead
  independently re-decoded rlog 5 to confirm). This FALSIFIES the "gp-0x1500 direct-clean / V48B-flash-proven
  / boot self-test framework" belief and is why **V50 is a no-flash** (its EMA state cell would be stomped =
  the V48B RAM-collision brick). See [[reference-accord-v50-lowpass-ema-cave]] and
  [[reference-accord-v48b-flashed-catastrophic-ram-collision]].
- The V48B post-mortem's "vetted-safe alternative `gp-0x14E0`" is slot 9 of this SAME array → also unsafe.
- **Do NOT draw persistent filter/state cells from anywhere in `gp-0x1520..gp-0x13CC`** (the array + tail),
  nor from `gp-0x1700` (`0xFEDF6900` — a separate live CAN-TX-adjacent 32-bit cell; a real
  `st.w r8,-0x1700,gp` exists in `FUN_0001e43a`).
- **Static RAM-ownership clearance is insufficient in this firmware.** It failed on 3 of 8 addresses checked
  (`gp-0x1500`, `gp-0x14E0`, `gp-0x1700`), and `gp-0x1500` passed BOTH static methods (disp16 scan +
  absolute-pointer literal scan) before the probe caught it. **Any candidate state cell MUST be validated by
  a live V50P-class probe read before trust.** Probe-pending replacement candidates OUTSIDE the array:
  `gp-0x1300` + `gp-0x1100` (roomy ~400 B clean corridor, best for a 4-byte state), `gp-0x1600` (tight —
  80 B to a live cell), `gp-0x1800`. See [[feedback-verify-subagent-conclusions]].
