# eps-update-tva.py

Honda EPS (Electric Power Steering) firmware flasher with V850/TVA support.

Adapted from [`hdlineage/sunnypilot_eps`](https://github.com/hdlineage/sunnypilot_eps)
`eps-update.py` (release-c3-eps branch). Extends it with x31 container support
(V850 ECU family — Accord TVA, ILX TV9, 9th-gen Accord T2F/T3L), defensive
safety gates, and modern panda library compatibility.

## What this script does

Flashes a Honda `.rwd` firmware blob to the EPS ECU over CAN bus using UDS
(ISO-14229). Auto-detects the container format by magic byte:

- **x5a** (0x5A `'Z'`) — SH-2A family: Civic, Clarity, CR-V, Pilot, Insight
- **x31** (0x31 `'1'`) — V850 family: Accord TVA, ILX, 9th-gen Accord

The two families use different Security Access (SA) algorithms, different
firmware container layouts, and (likely) different multi-block transfer
sequencing. The script routes by detected format.

## What's different from upstream

| Area | Upstream | This script |
|---|---|---|
| Container formats | x5a only | Auto-detects x31 and x5a |
| V850 SA algorithm | N/A | `calculate_tva_session_key` using firmware-embedded Group-C constants at code-flash 0x92C0..0x92C5 (verified in `V850_ALGORITHM_VERIFIED.md`) |
| Multi-block transfer | Asserts single block | Handles N blocks (sequencing not yet hardware-verified — see safety gates) |
| Default behavior | Flashes immediately | DRY RUN by default; `--danger` required to actually write flash |
| Mock fallback | Silent under any failure | Refused under `--danger` to prevent misleading "flash succeeded" against a Python mock |
| Modern panda lib | Crashes on `Panda.SAFETY_ELM327` (attribute removed) | Back-compat shim: sets `Panda.SAFETY_ELM327 = 3` if missing |
| ECU part-number gate | Implicit (via headers[4] lookup) for x5a only | Explicit gate for x31 by comparing ECU app id against the `/` header part list |
| Routine-status visibility | Discarded | `ERASE_MEMORY` and `CHECK_PROGRAMMING_DEPENDENCIES` status bytes logged; non-zero deps status triggers a "do not power-cycle, re-flash now" warning |
| S3 keep-alive | None | `tester_present()` heartbeats before erase, after erase, before dependency check |
| Danger confirmation | None | Interactive `FLASH` typed-confirmation banner with firmware path + bus + CAN address echoed back; `--yes` bypasses interactivity but still requires `--danger` |

## Dependencies

**Not bundled** — must be on the Python path or in the working directory:

- `tva_sa_key.py` — V850 SA key algorithm (Wave-3 verified, bit-level audit
  trail in `V850_ALGORITHM_VERIFIED.md`).
- `encode_eps.py` — x31 container parser.
- `panda` Python library — comma's panda library. The `from panda.python.uds`
  imports require a version that still bundles `panda/python/uds.py` (modern
  `commaai/panda` removed this module — use the sunnypilot_eps bundled panda
  fork, or vendor `uds.py` into your local `panda/python/` directory).
- For x5a firmware only: `panda.format.x5a` — only exists in the
  sunnypilot_eps fork. Override the search path with the `EPS_UPDATE_X5A_PATH`
  environment variable; default is `D:/sa-key-hunt/sunnypilot_eps`.

## Usage

### Safe dry run (default)

Validates the SA handshake end-to-end against the real ECU and stops before
any erase or write. This is the recommended first run for any new firmware
file or new ECU target.

```
python eps-update-tva.py --bus 1 path/to/firmware.rwd
```

A successful dry run prints the ECU's reported app id, the received seed,
the computed key, and the resolved CAN address. If the SA handshake succeeds
in dry run, the algorithm and constants are correct against the live ECU.

### Real flash

```
python eps-update-tva.py --bus 1 --danger path/to/firmware.rwd
```

Prints a danger banner with the firmware file, bus, CAN address, and any
unverified-assumption warnings. Requires typing `FLASH` (all caps) to proceed.

Multi-block x31 firmware additionally requires `--allow-multiblock` (the
multi-block transfer sequencing is not yet verified against a Honda factory
flash capture).

If the ECU's reported app id does not match any part listed in the `.rwd`'s
`/` header, the script refuses unless `--force-part-mismatch` is also passed
(use only when you have specifically verified the firmware applies to your
ECU revision).

### Flags

| Flag | Effect |
|---|---|
| `--bus N` | CAN bus number (required). Typically `1` for OBD-II on a red panda. |
| `--danger` | Actually flash. Without it, the script stops after the SA handshake. |
| `--yes` | Skip the interactive `FLASH` typed confirmation (still requires `--danger`). |
| `--allow-multiblock` | Required for `--danger` on x31 `.rwd` files with more than one block. Acknowledges brick risk on unverified multi-block sequence. |
| `--force-part-mismatch` | Override the part-number gate. UNSAFE — wrong-vehicle firmware can produce unsafe steering. |
| `--debug` | Verbose UDS debug output. |

## Safety gates

The `--danger` path is defensively gated on every assumption that has not
been hardware-verified against a real V850 factory flash capture:

1. **Mock-fallback refusal** — under `--danger`, if no real panda is
   reachable, the script exits with a fatal error rather than silently
   falling through to a Python `mock` that returns canned UDS responses.
2. **Multi-block guard** — refuses multi-block x31 flashes unless
   `--allow-multiblock` is passed.
3. **Part-number gate** — refuses to flash a `.rwd` whose `/` header does
   not list the ECU's reported app id (unless `--force-part-mismatch`).
4. **Typed-confirmation banner** — the danger banner echoes the firmware
   path, container format, CAN bus, and CAN address back to the operator
   and requires literally typing `FLASH` to proceed.
5. **Routine-status surfacing** — `ERASE_MEMORY` and
   `CHECK_PROGRAMMING_DEPENDENCIES` response bodies are logged. Non-zero
   dependency status triggers a "DO NOT POWER-CYCLE — re-flash now"
   warning rather than silently exiting 0.
6. **S3 timeout defense** — `tester_present()` heartbeats inserted around
   the long-running erase and before the final dependency check.

## Unverified V850 assumptions

Honest disclosure — these assumptions have NOT been validated against a
captured Honda factory TVA reflash. The script proceeds with reasonable
defaults but emits warnings:

- **`FLASH_DECRYPTION_KEY` DID and payload byte order** — assumed identical
  between SH-2A and V850 (the SH-2A precedent). If V850 expects a different
  DID or byte order, the ECU will decrypt the firmware with the wrong key
  and write garbage. The danger banner calls this out explicitly.
- **`request_transfer_exit` cadence** — the script sends a per-block exit
  AND a final exit. UDS standard is end-only, but Honda may diverge per
  family. If wrong, the bootloader may finalize prematurely or reject
  subsequent downloads.
- **`transfer_data` sequence counter** — resets to 1 at each new block.
  Correct IF the bootloader resets sequence per download; wrong if it
  expects monotonic across the session.

If you have access to a captured TVA factory reflash trace (HDS, autoecu,
or other), comparing the wire bytes against this script's output would
settle all three.

## Lineage

- Upstream: [`hdlineage/sunnypilot_eps`](https://github.com/hdlineage/sunnypilot_eps)
  `eps-update.py` @ `release-c3-eps`
- SH-2A SA algorithm: identical math to upstream `calculate_session_key`
- V850 SA algorithm: per the project's `V850_ALGORITHM_VERIFIED.md`
  (Wave-3 verified, bit-level audit trail)
- x31/x5a parsers: round-trip verified in `encode_eps.py` (companion module)

## Risk acknowledgement

A failed EPS flash can leave the ECU in an unbootable state. The car will
not have power steering until the ECU is recovered (which generally requires
re-establishing a security access session against the bootloader — possible
in most cases, but not guaranteed).

Do not run `--danger` without:

- Car ignition ON (engine off is fine)
- Panda as the only device on the OBD-II port
- openpilot/pandad killed on any comma device (`tmux kill-server`)
- A backup `.rwd` for the ECU's current firmware (recoverable rollback)
- A clear plan for what you'll do if the dependency check returns non-zero
