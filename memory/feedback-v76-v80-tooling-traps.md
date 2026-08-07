---
name: feedback-v76-v80-tooling-traps
description: Six tooling/hygiene traps found 2026-08-07 — the wrong V76 probe decoder for route 65, a stale V76 plain image that a Glob returns first, build_v75_tva.py's default lever set not producing the flown V75, route 5d's missing raw rlogs, V80's non-discriminating probe, and the broken default python numpy.
metadata:
  type: feedback
---

# 🛑 SIX TOOLING TRAPS — each one can hand a confident wrong answer

**2026-08-07.** All verified from disk by the orchestrator.

## 1. 🛑 `rlog-tools/decode_v76_probe.py` is the WRONG decoder for route 65
It documents the **superseded, V74-base** V76 (`V76-V74BASE-GATE-FB-ARM5244`), whose **bit7 is
`gp-0x6bd0 != 0`** — **the damper, not the friction lane.** The build that actually flew route 65 is
`V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd`, and its extractor is
`analysis-2020accord/v76flight_extract.py` → `analysis-2020accord/_cache_r65_records.pkl`
(**not** `_cache_r65/`). Using the wrong decoder silently re-labels the probe bits and will give a
confident wrong answer about the friction-lane null.

## 2. 🛑 Multiple `_v76*plain_image.bin` snapshots, and a `Glob` returns the wrong one FIRST
`_v76_gate_fb_arm5244_gateprobe_plain_image.bin` is the **abandoned V74-base candidate** and still
carries the V57 decouple; a first `Glob` returns it **first**. The **V78/V80 ancestor** is
`_v76_v38base_relu_damper_plain_image.bin`. The abandoned candidate's `.rwd` was correctly renamed
`SUPERSEDED-…`, but **the stale plain-image snapshot still reads as current** — the same hazard class as
[[accord-recut-overwrites-the-previous-plain-image]].
⊕ Observed on disk the same day (not in the session-facts file, so flagged rather than asserted): a third
snapshot `SUPERSEDED-DO-NOT-FLASH-_v76_v38base_wrongprobe_plain_image.bin` also exists. ⇒ **always match
the base image by its FULL filename token, never by a `_v76*` glob.**

## 3. `build_v75_tva.py`'s default lever set does **NOT** produce the flown V75
You must pass **`ACCORD_V75_LEVERS=CY0,EX1`**. The default (`CY0` only) writes the **never-flown**
`…CY0.566…` artefacts. There is no overwrite hazard (`lever_token()` appears in both filenames), but the
comment at line 269 is easy to misread. **The flown V75 is the `EX1.200` cut — dose 137, `k` = 1.5798.**

## 4. Route `5d` — V74's first (clean, symptom-measurement) flight — has **NO raw rlogs anywhere in the
repo**
Only the extracted `_cache_r5d/*.npz` + `.pkl` survive. **Every downstream V74 conclusion in `STATE.md`
runs against that cache, not the raw log** — it cannot be re-cut with a different extractor.

## 5. V80's probe **cannot distinguish V80 from V78/V79**
Byte-identical cave, identical trip rates below 80 km/h. Build identity rests on the `.rwd` filename plus
the **absolute** exclusion of V76-V38BASE (13,183 frames set bit6 with bit5 clear — structurally
impossible on that cave). Route 66's `0x14A` byte4 took only {`0x0F`,`0x1F`,`0x5F`,`0xDF`}; bit5
0/89,997; bit3 positive control **100.000%**. ⇒ **the filename is again the only pre-drive
discriminator.**

## 6. The default `python` (anaconda base) has a **broken numpy DLL**
Either prepend `C:\Users\dudei\anaconda3\Library\bin` to `PATH`, or use
`C:/Users/dudei/anaconda3/envs/bin_decompile/python.exe` (which also has `capnp`).

Related: [[accord-recut-overwrites-the-previous-plain-image]] ·
[[accord-check-build-lineage-before-proposing-lever]] · [[feedback-verify-with-ghidra-and-bytes-both]] ·
[[accord-telemetry-conventions-that-produced-wrong-answers]]
