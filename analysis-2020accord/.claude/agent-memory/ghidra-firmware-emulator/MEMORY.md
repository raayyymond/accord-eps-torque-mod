# Agent Memory Index

- [reference-v23-envelope-check-analysis](reference_v23_envelope_check_analysis.md) — V23 shl 0x9 patch: check does NOT trip at rest (both signals are 0); trips during active torque when stock_diff >= 3 (V23_diff = 2x stock_diff, window fixed at +-5)
- [reference-ghidra-program-names](reference_ghidra_program_names.md) — Open program names in Ghidra: _v24_plain_image.bin (current), _v23_plain_image.bin, _v22_plain_image.bin, code.bin (stock baseline, 2113 functions)
- [reference-v24-fault-monitor-validation](reference_v24_fault_monitor_validation.md) — V24 max 2x command: all 7 bits NO FIRE, accumulator=0.0 vs EME threshold 128.0, bits 1&2 diff=0 by self-cancellation, full 15/1024 margin
