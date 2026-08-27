---
name: reference-operator-flash-hardware-topology
description: "Joey's actual EPS-flash / red-panda hardware rig goes red panda -> comma Bosch harness (harness in the car, comma powers it) -> laptop USB. NOT red-panda-direct-to-OBD-II as docs/guides/RED-PANDA-EPS-SETUP.md claims. Implication: the red panda reaches the harness-tapped buses (incl. bus 1 where body/SCM msgs like 0x221 ECON_STATUS live), so it can sniff body-bus signals — OBD-II alone may not."
metadata:
  type: reference
---

# Operator's real red-panda hardware topology

**Corrected by Joey 2026-05-28** (operator lived experience overrides docs — see [[feedback-operator-lived-experience-overrides-analyst-recs]]).

His EPS-flash / red-panda rig: **red panda → comma Bosch harness → laptop (USB)**. The comma Bosch harness is in the car and powers the rig; the red panda taps the harness (not the OBD-II port directly). *"flashing is not red panda direct to obd II — its always went through the harness."*

**This contradicts `docs/guides/RED-PANDA-EPS-SETUP.md`** (and the EPS-FLASH-RUNBOOK), which state the red panda plugs **directly into OBD-II with the comma harness unplugged**. The docs are wrong/generic for his actual practice. (Doc-fix offered; not yet applied as of writing.)

**Why it matters for CAN work:** going through the harness means the red panda sees the harness-tapped buses — including **bus 1**, where body/SCM messages like **`0x221 ECON_STATUS`** appear. A red panda on OBD-II alone might only see the powertrain bus and miss `0x221`. So for body-bus sniffing his harness rig is viable; the OBD-II-direct assumption (in the now-superseded CAN-SNIFF-RUNBOOK §0) was based on the wrong doc.

For the ECON sniff specifically, comma-only was still chosen (simplest; the comma provably sees `0x221`). See [[reference-vfn-drivemode-personality-port]] and `docs/CAN-SNIFF-RUNBOOK.md` §7.

## Cross-links
- [[feedback-operator-lived-experience-overrides-analyst-recs]] — why the correction stands over the doc
- [[reference-device-access-konik]] — comma SSH/log-pull path for the comma-only sniff
- [[reference-vfn-drivemode-personality-port]] — what the sniff feeds into
