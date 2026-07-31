---
name: reference-accord-gp6b70-chain-terminates-at-falsified-c6af0
description: gp-0x6b70 (second aggregator consuming gp-0x6bd0/gp-0x6bbe) chains through FUN_00037fe6 -> gp-0x6ad6 -> FUN_0003a382's PID (already-documented) -> gp-0x6ad4 -> the aggregator; its sole output-shaping cal (0xC6AF0) was flashed by V56, found null, and explicitly reverted in V57/V58
metadata:
  type: reference
---

**2026-07-30, follow-up to [[reference_accord_gp6ac2_ceiling_only_and_no_motor_command_feedforward]] and
[[reference_accord_factorc_lockstep_gate_clear_ceiling_only]].** Team-lead asked me to characterize
`FUN_00038148`/`gp-0x6b70`, which I'd flagged as an uncharacterized second consumer of `gp-0x6bd0`.
Program: stock `code.bin`.

🛑 **Self-correction of record:** tp+0x73a8 is `0xC63A8`, NOT `0xC73A8` — I made the documented
off-by-0x1000 error mid-session and caught it before reporting. All addresses below are re-verified.

## The chain (all 1 kHz, called from `FUN_0002214a`, same dispatcher as the main assist path)

`FUN_00038148` sums SIX unity-weighted terms (cal `0xC63A0/A2/A4/A6/A8/AA` = `1024` each, byte-read):
**`gp-0x6bd0`(damper) + `gp-0x6bbe`(boost) + `gp-0x6b46` + `gp-0x6b26` + `gp-0x6b4e` + `gp-0x6b4c`**,
mode-dwell-scaled, EMA-blended at rate 102/1024 (`0xC63AC`), rate-limited → **`gp-0x6b70`**. So the
damper and boost outputs re-enter a SECOND aggregator at unity gain, parallel to their direct entry into
`FUN_0003aa2c`'s aggregator.

`gp-0x6b70`'s SOLE consumer (2 total accesses image-wide, confirmed search_instructions + independent
byte scan after excluding 19 false positives — `jarl 0x0006b700,lp` calls colliding with the `6b70`
substring, same trap class as the earlier `6bd0`/branch-target collision): **`FUN_00037fe6`**. It's one
of 7 unity-weighted terms (cal `0xC64AD-0xC64B3` = `1` each) summed with `-gp-0x6b4a`, gated by
`gp-0x67ab` (byte, identity unresolved — produced by `FUN_00026c80`, an 11-channel mixer that also
produces `gp-0x6b4a`/`gp-0x6b4c`), scaled by a gain-LERP indexed on `gp-0x69aa` (identity unresolved —
written by `FUN_0004503c` the state-4 governor, read by `FUN_00025c32` the final `distribute_clamp`
stage) → clamped ±25600 → **`gp-0x6ad6`**.

`gp-0x6ad6`'s SOLE consumer (3 total accesses, search + byte scan agree): **`FUN_0003a382`** — already
fully documented in `memory/reference-accord-fun3a382-is-a-real-pid.md`. There, `gp-0x6ad6` is used
ONLY as a 2-state ±8192 bias selector (cal `0xC6200`) for `ERR = gp-0x4f60 - bias`, NOT a continuous
input — a genuine discrete PID (P motor-rate-scheduled `0xC6B26`, I flat=98 `0xC6B12`, **D flat=2048 and
UNATTENUATED `0xC6AE6`**, raw backward-difference reaches output). That memory's cross-validated
frequency table shows **+41.8° to +55.0° phase LEAD at 21 Hz**, `|D|` rivaling `|P|`. Output →
`gp-0x6ad4` (re-confirmed exactly 2 accesses image-wide: writer `0x3a8a0`, sole reader `0x3aca8` in
`FUN_0003aa2c`'s aggregator, plain `add`, alongside `gp-0x6bbe`/`gp-0x6bd0` directly) → `gp-0x6b94` →
the already-documented governor/corridor chain → `gp-0x6b98`.

## ★★ The terminus is already flashed and falsified

`gp-0x6ad4`'s only output-shaping cal is its own authority ceiling, **`0xC6AF0`** (`FUN_0003a382`'s
clamp, `0x3a88c-0x3a8a0`). `build_v56_tva.py` muted it (`Y[0]`/`Y[1]` both zeroed, forcing `gp-0x6ad4`
to 0 unconditionally) — flashed, tested, NULL on the grinding, cost damping elsewhere. **`build_v57_tva.py:411`
and `build_v58_tva.py:369` both assert `0xC6AF0` is stock, literal message "0xC6AF0 must stay STOCK --
V56's mute is falsified."** Since `gp-0x6ad4` has only 2 total accesses image-wide, zeroing it via this
ceiling is equivalent to fully removing the entire `gp-0x6b70` chain's contribution to the aggregate —
already done on-car, already reverted as net-negative. Grepped all newly-found chain addresses
(`0xC63A0-0xC63AC`, `0xC64AD-0xC64B3`, `0xC6200`) against `build_v*_tva.py`: **none appear anywhere,
genuinely untouched.** `0xC6B26`/`0xC6B12`/`0xC6AE6` (the PID's own gains) appear in `build_v43_tva.py`/
`build_v49_tva.py` as stock-value assertions only, not edits.

## Engagement gating
Per the existing PID memory, `gp-0x6ad4` is explicitly NOT gated on openpilot engagement. All three
functions in this chain run unconditionally at 1 kHz alongside the main assist path.

## Open items
- `gp-0x67ab`/`gp-0x69aa` semantic identity (structural role only established).
- `FUN_00026c80` (the 11-channel mixer) only partially read.
- Whether `FUN_0002214a`'s call to these functions is itself phase-mask-gated wasn't checked.

## Bottom line
`gp-0x6b70` is not a live, untested lever — it's a rediscovered path back to a ceiling that's already
been flashed and reverted. If loop gain from the boost/damper re-entry is still unaccounted for, the
more promising open thread is the P/D phase-lead inside `FUN_0003a382` itself (already flagged open in
the existing PID memory as needing the plant transfer function, which isn't in the binary), not the
aggregation weights — which are all unity/stock throughout this entire chain.
