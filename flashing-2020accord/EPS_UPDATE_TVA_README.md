# eps-update-tva.py — V850/TVA-aware EPS flasher

A drop-in adaptation of upstream
[`hdlineage/sunnypilot_eps/eps-update.py`](https://github.com/hdlineage/sunnypilot_eps/blob/release-c3-eps/eps-update.py)
that handles both the SH-2A `.rwd` family (Civic, Clarity, CR-V, Pilot,
Insight — upstream's only target) and the V850 `.rwd` family (2020 Accord
TVA, ILX TV9, 9th-gen Accord T2F/T3L, etc. — new in this fork).

Container parsing, SA-key computation, and CAN-address routing are all
auto-selected from the `.rwd` magic byte. Defaults to dry-run; `--danger`
is required to mutate the ECU.

The flasher source is tracked here, but proprietary `.rwd` files are stored
under `../accord-firmware/flashing-2020accord/rwd/` by default. From the
repository root, Python tools use `../accord-firmware` unless
`ACCORD_FIRMWARE_ROOT` overrides it.

> **Status (2026-05-24):** `../accord-firmware/flashing-2020accord/rwd/39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd`
> flashed successfully on the operator's car via this script (bus 1, `0x18DA30F1`,
> `--danger`). That validates the whole chain — SA handshake, multi-block x31
> transfer, and the V9b payload cipher — against real hardware. The build recipe
> behind that file is `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md`.

---

## What's different from upstream

1. **Format auto-detection.** The magic byte at offset 0 selects the
   container parser:
   - `0x31` ('1\r\n') → x31 (V850 family) → `encode_eps.parse_x31`
   - `0x5A` ('Z\r\n') → x5a (SH-2A family) → upstream `panda.format.x5a.x5a`
2. **V850 SA algorithm uses firmware-embedded constants.** Upstream's
   `calculate_session_key(secret, seed)` uses `headers[4]` of the x5a
   container as the secret. That logic does NOT work for V850 — the V850
   ECU ignores the `!` header bytes (Group A `001100121020`) and uses
   constants embedded in code flash at `0x92C0..0x92C5` (Group C
   `021102121220`). This fork routes x31 through
   `tva_sa_key.calculate_tva_session_key()`, which encodes the verified
   Group C constants (`k0=0x0211`, `k1=0x0212`, `k2=0x1220`). See
   `V850_ALGORITHM_VERIFIED.md` and `ACCORD_TVA_ARCHITECTURE_MAP.md` §7.4.
3. **Per-format CAN address resolution.**
   - x31: reads the `%` header (ASCII hex byte) → `0x18DA__F1` for TVA.
     The stock `.rwd` ships `%`=`b'80'` (`0x18DA80F1`, the HDS/dealer-tool
     target). **comma/openpilot talks to the Accord EPS at `0x18DA30F1`**
     (target `0x30`) — see `opendbc/car/honda/fingerprints.py`
     `(Ecu.eps, 0x18da30f1)`, bus 1. The ECU RX filter is the broad
     `0x18DAxxF1` family so both reach it; **use a `%`=30 build for the
      comma/red-panda path** (the flashed `../accord-firmware/flashing-2020accord/rwd/39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd`
     is a `%`=30 build, response `0x18DAF130`).
   - x5a: reads `headers[2][0]` (raw byte, e.g. `0x30`) → `0x18DA30F1`
     for Civic (upstream behavior, unchanged).
4. **Multi-block x31 transfer.** Upstream `assert`s a single firmware
   block (x5a is a single blob). V850 `.rwd`s carry multiple sparse
   blocks (TVA-A160 reconstruction: 62 blocks). The x31 transfer loop
   issues one `request_download` per block.
5. **Default = dry run; `--danger` required to flash; interactive
   confirmation on top.** The dry-run path executes
   tester-present → app-ID read → extended session → SA seed/key exchange
   and STOPS. With `--danger`, the script also prints the firmware
   filename, CAN address, bus number, and required prerequisites, then
   prompts the operator to type `FLASH` before continuing. Pass `--yes`
   to skip the prompt (still requires `--danger`).

The wire workflow (UDS sequence ordering, request_download semantics,
transfer chunk sizing, programming-dependencies routine) is unchanged
from upstream — only the SA-key, container parsing, CAN address, and
multi-block transfer differ.

---

## Usage

### Safe dry run (default — no mutation)

```
python flashing-2020accord/eps-update-tva.py --bus 1 ../accord-firmware/flashing-2020accord/rwd/path/to/firmware.rwd
```

Runs the UDS chain through the SA send-key step and exits. If the
script reports `SA handshake succeeded`, the algorithm and constants
are validated against the real ECU.

Sample dry-run tail output:

```
[sa]  received seed: 0xABCD
[sa]  computed key : 0xA154 (via V850 Group-C firmware constants)
[sa]  sending key (0x27 0x02)
[sa]  SA handshake succeeded

======================================================================
  DRY RUN COMPLETE - SA handshake succeeded, stopping before flash
======================================================================
  ECU app ID    : b'39990-TVA-A160\x00\x00'
  Seed received : 0xABCD
  Key accepted  : 0xA154
  Container fmt : x31
  CAN address   : 0x18DA80F1
  Bus           : 1
======================================================================
```

### Real flash (DANGEROUS — requires explicit confirmation)

```
python flashing-2020accord/eps-update-tva.py --bus 1 --danger ../accord-firmware/flashing-2020accord/rwd/path/to/firmware.rwd
```

After the SA handshake, the script prints a danger banner with
firmware file, container format, bus, and CAN address; the operator
must type `FLASH` (all caps) to continue. With `--yes`, the prompt is
skipped (script use only — `--danger` is still required).

---

## Validating the V850 SA story on real hardware

The dry-run path is exactly the validation harness for the V850 SA
algorithm. Run it on a real 2020 Accord TVA with the bench/car powered
on and the panda attached. Three outcomes:

| Outcome | Meaning |
|---|---|
| `SA handshake succeeded` | Algorithm + Group C constants are correct against the ECU. Safe to proceed to `--danger` after the usual eyes-on review. |
| `0x7F 0x27 0x35` (invalidKey) at SendKey | Algorithm or constants wrong. Stop. Re-audit `tva_sa_key.py` against `V850_ALGORITHM_VERIFIED.md` and the firmware at `0x92C0..0x92C5`. |
| `0x7F 0x27 0x36` (exceededNumberOfAttempts) | Wait the lockout period; the ECU rate-limits SA attempts. Power-cycle and retry. |

No flash risk in any of those — the dry run never reaches
`diagnostic_session_control(PROGRAMMING)` or `routine_control(ERASE_MEMORY)`.

---

## Hardware safety preamble

Per `CLAUDE.md` and `docs/guides/EPS-FLASH-RUNBOOK.md`:

- **Car ignition ON** (engine off is fine; CAN bus must be active).
- **Panda is the only device on OBD-II.** If a comma device's harness
  is connected, unplug it.
- **openpilot / pandad must be killed** before any flash workflow. On a
  comma device: `tmux kill-server`. Failing to kill openpilot has been
  reported to illuminate every dashboard error light (recoverable but
  alarming).
- **Firmware part number must match the target car.** Cross-flashing
  between part numbers (or between V850 and SH-2A families) is not
  safe. The dry run will print the ECU's reported application-software
  ID and the supported part numbers from the `.rwd` headers — confirm
  they match before passing `--danger`.
- **Do NOT interrupt the flash once started.** A partial write can
  brick the EPS ECU.
- **`--danger` is NEVER passed without explicit operator confirmation.**
  The interactive `FLASH` prompt enforces this; do not script around
  it (`--yes`) without a deliberate decision.

---

## Reference

- `tva_sa_key.py` — verified V850 SA implementation (2026-05-23)
- `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md` — **the single build recipe**:
  x31 container spec, V9b cipher (confirmed), flash window, CRC scheme, SA algorithm,
  and the patched-firmware pipeline. (Distilled from the former `V850_ALGORITHM_VERIFIED.md`,
  `ACCORD_TVA_ARCHITECTURE_MAP.md`, `ENCODER_REPORT.md`, `STOCK_RECONSTRUCTION_REPORT.md`.)
- `analysis-2020accord/notes/TORQUE_PATH_AND_TABLE.md` — torque input→output code path + tables
- `docs/guides/EPS-FLASH-RUNBOOK.md` — red panda + laptop flash workflow

---

## Differences in tabular form

| Aspect | Upstream `eps-update.py` | This fork (`eps-update-tva.py`) |
|---|---|---|
| Supported formats | x5a only (asserts magic via parser) | x5a + x31 (auto-detect) |
| SA constants source (x5a) | `headers[4]` via part-number match | unchanged |
| SA constants source (x31) | not supported | firmware-embedded Group C (`tva_sa_key`) |
| CAN address (x5a) | `headers[2][0]` raw byte | unchanged |
| CAN address (x31) | not supported | `%` header ASCII hex |
| Transfer blocks | single (asserted) | multi (per x31 block) |
| Dry-run default | yes (raises after SA) | yes (clean exit after SA) |
| `--danger` confirmation | none | interactive `FLASH` prompt (skip via `--yes`) |
| Echoes firmware file + bus | no | yes (per CLAUDE.md safety rule #2) |
| Mock client when no panda | yes | yes (canned values updated for V850) |

---

## Provenance

This file documents `eps-update-tva.py` only. The script itself is a
fork-with-attribution of the upstream `eps-update.py` (Apache-2.0 in
the upstream's repo, attributed in the script header). The V850
SA-key routing is original work in this kit, validated against the
firmware at `0x92C0..0x92C5` via the audit chain in
`V850_ALGORITHM_VERIFIED.md`.
