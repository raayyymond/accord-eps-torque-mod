# eps-update-tva.py — Adversarial Static QA

**Date:** 2026-05-23
**Reviewer:** static QA agent (no hardware, no CAN)
**Subject:** `flashing-2020accord/eps-update-tva.py` (576 lines)
**Cross-checked against:** `D:/sa-key-hunt/sunnypilot_eps/eps-update.py` (upstream), `flashing-2020accord/tva_sa_key.py`, `flashing-2020accord/encode_eps.py`, `analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md` (SA algorithm §6 + build recipe; distilled from the former `V850_ALGORITHM_VERIFIED.md` / `ACCORD_TVA_ARCHITECTURE_MAP.md`), `docs/guides/EPS-FLASH-RUNBOOK.md`, repo `CLAUDE.md`. Candidate `.rwd` files are external under `../accord-firmware/flashing-2020accord/`.

---

## Verdict: **SHIP** (for rayy dry-run on a real ECU)

The script is safe to run in default (dry-run) mode against a real 2020 Accord TVA. The dry-run code path exits cleanly after the SA handshake with no possibility of reaching erase/program/write code. All four mandatory CLAUDE.md safety rules are upheld. The SA-key routing, CAN-address derivation, format detection, and UDS exchange ordering are correct and match upstream where they should.

There is one known caveat (acknowledged in the script's own docstring): the `_transfer_x31` multi-block transfer logic is hardware-unverified for the TVA bootloader. This does NOT affect dry-run safety — it only matters under `--danger`. Recommend gating the first `--danger` run on tight observation, per the script's own note.

The remaining items are suggestions / polish; none block ship.

---

## Mandatory safety items

| # | Item | Status | Evidence |
|---|---|---|---|
| S1 | Dry-run is the default; no flash possible without `--danger` | **PASS** | `argparse.add_argument("--danger", action="store_true")` (L549) defaults False. In `flash()`, the destructive UDS calls (`DIAGNOSTIC_SESSION_CONTROL(PROGRAMMING)`, `routine_control(ERASE_MEMORY)`, `write_data_by_identifier(FLASH_DECRYPTION_KEY, ...)`, `_transfer_x31/x5a`, `request_transfer_exit`) all live **below** the `if not danger: ... return 0` block (L369-385). Dry-run path returns at L385 before any of them execute. |
| S2 | `--danger` required for flash; cannot be reached unless True | **PASS** | The dry-run early-return at L385 is the only path out of `flash()` when `danger=False` (other than exception → return 3). There is no branch where `danger=False` and an erase/program/transfer call fires. |
| S3 | `--yes` requires `--danger`; cannot bypass danger gate | **PASS** | `--yes` is consumed only inside `confirm_danger()` at L256-258 (`if skip_prompt: ... return True`). `confirm_danger()` is itself called only from the `if danger:` branch at L326-328. `--yes` alone with `danger=False` results in identical behavior to `danger=False, yes=False` (dry run, no prompt, exit at L385). No combination of flags yields a flash without `--danger=True`. |
| S4 | Firmware filename + bus echoed before any destructive op | **PASS, double-coverage** | (a) `main()` prints `[boot] firmware file : {path}` and `[boot] CAN bus : {bus}` at L566-567 unconditionally, BEFORE calling `flash()`. (b) `confirm_danger()` re-prints the path, bus, fmt, and CAN address inside the danger banner at L245-248. Both name-back-before-flash and "see it twice" are satisfied. |
| S5 | Interactive `FLASH` confirmation prompt, unbypassable except via `--yes` | **PASS** | `confirm_danger()` at L260 issues `input("Type 'FLASH'...")`. The match at L264 (`if ans.strip() != "FLASH"`) is exact-match on the all-caps literal — typo-resistant. Aborts cleanly on `EOFError`/`KeyboardInterrupt` (L261-263). `--yes` is documented in the script header (L23) and CLI help (L552-554) as still requiring `--danger`. |
| S6 | No accidental CAN writes in dry-run path | **PASS** | Dry-run UDS sequence is exactly: `tester_present` → `read_data_by_identifier(F181)` → `diagnostic_session_control(EXTENDED)` → `security_access(REQUEST_SEED)` → `security_access(SEND_KEY)` → return. None of these are brick-able: they are all read or session-state operations that do not modify flash. `PROGRAMMING` session, `ERASE_MEMORY`, `FLASH_DECRYPTION_KEY` write, `request_download`, `transfer_data`, `request_transfer_exit`, `CHECK_PROGRAMMING_DEPENDENCIES` are gated behind the `if not danger: return 0` (L369-385). |

**Mandatory safety verdict: 6/6 PASS. No blocks.**

---

## Correctness items

| # | Item | Status | Evidence |
|---|---|---|---|
| C1 | x31 routes to `calculate_tva_session_key` (V850 algorithm) | **PASS** | `sa_seed_to_key()` L223-224: `if fmt == "x31": return calculate_tva_session_key(seed_bytes)`. `calculate_tva_session_key` is imported at L58 from `tva_sa_key.py`. That module's `_selfcheck()` validates 6 vectors against `V850_ALGORITHM_VERIFIED.md`. |
| C2 | x5a mirrors upstream: `headers[4]` looked up by `headers[3]` matching `app_id` | **PASS** | `get_x5a_seed_secret()` L168-170 walks `headers[4].values` in parallel with `headers[3].values`, returning `headers[4].values[i].value` where `headers[3].values[i].value == app_id`. Identical structure to upstream `get_seed_secret()` (`eps-update.py:82`). |
| C3 | x5a unmatched `app_id` fails loudly | **PASS** | `get_x5a_seed_secret()` L171-175 raises `RuntimeError` listing the ECU's `app_id` and the supported parts from the .rwd's `headers[3]`. The `except Exception` in `flash()` (L431-434) catches it, prints the traceback, and returns exit code 3. No silent fallback to a wrong key. |
| C4 | x31 CAN address: `%` header (ASCII hex) → `0x18DA__F1` | **PASS** | `get_can_address_x31()` L143-146 walks `parsed["headers"]` looking for `tag == b"%"`, then `int(vals[0].decode("ascii"), 16) << 8 \| 0x18DA00F1`. Matches the format documented in `lib/encode_eps.py:103-112` and in `ACCORD_TVA_ARCHITECTURE_MAP.md` §6.1. TVA `%` header `b'80'` → `0x18DA80F1` ✓. **[2026-05-24] Note:** `b'80'`/`0x18DA80F1` is the **stock HDS/dealer-tool** target. comma/openpilot talks to this EPS at **`0x18DA30F1`** (`%`=`b'30'`), per `opendbc/car/honda/fingerprints.py` `(Ecu.eps, 0x18da30f1)` incl. `HONDA_ACCORD`, bus 1. ECU RX filter is the broad `0x18DAxxF1` family so both reach it. **For the comma/red-panda path use a `%`=30 build** — the flashed `39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd` is one (response `0x18DAF130`). |
| C5 | x5a CAN address: `headers[2][0]` raw byte → `0x18DA__F1` | **PASS** | `get_can_address_x5a()` L152 is a literal copy of upstream `eps-update.py:90`. |
| C6 | Missing `%` header (x31) errors loudly | **PASS** | `get_can_address_x31()` L147 raises `RuntimeError("x31 file has no `%` (CAN sig byte) header")`. Caught and printed by the outer exception handler. Note: the parser in `encode_eps.parse_x31` does not enforce that all 6 header tags are present — but the absence triggers this loud error before any UDS exchange. |
| C7 | Format detection by magic byte | **PASS** | `detect_format()` L78-94: `0x31` → x31, `0x5A` → x5a, anything else → `ValueError` with informative message naming the actual magic byte. Length check at L84-85 guards against a < 3-byte file. |
| C8 | SA failure handling (NRC 0x35/0x36/0x37) | **PASS** | Upstream uds.py `_uds_request` raises `NegativeResponseError` on any NRC (line 636 of D:/sa-key-hunt/sunnypilot_eps/panda/python/uds.py). The script's `try: ... except Exception:` (L340-434) catches this, prints the full traceback (which includes the NRC code and description), and returns exit code 3. No NRC scenario can reach the `if not danger: return 0` block or the post-danger flash code. |
| C9 | Wire format: 2-byte seed in, 2-byte key out | **PASS** | `seed_bytes = data[-2:]` (L356) — same as upstream (`eps-update.py:131`). `calculate_tva_session_key` raises `ValueError` if it does not receive exactly 2 bytes (`tva_sa_key.py` L100-104). `calculate_universal_sa_key` uses `struct.unpack("!H", seed_bytes)[0]` and returns a 2-byte packed result. No 4-byte path is reachable from the flash flow. |
| C10 | SA seed/key UDS sequence preserved from upstream | **PASS** | Order: tester_present → read_data_by_identifier(F181) → diagnostic_session_control(EXTENDED) → security_access(REQUEST_SEED) → compute key → security_access(SEND_KEY). Matches upstream `eps-update.py:115-135` line-for-line. |
| C11 | Multi-block x31 transfer — request_download + transfer_data per block | **CONDITIONAL** | The per-block loop (L500-522) issues `request_download(block.start, block.length)`, then transfers chunks with rolling `seq` byte, then a per-block `request_transfer_exit` between blocks (not after the last; the final exit is the outer one at L417-419). The script header (L484-487) and the `_transfer_x31` docstring (L482-487) acknowledge this is **hardware-unverified for the TVA bootloader.** Some bootloaders want one `request_download` covering the union of regions; some want per-block. **This does not affect dry-run safety.** First `--danger` run on a real TVA should be tightly observed; recommend dry-run first, then a watch-the-bus `--danger` attempt with someone ready to power-cycle. |
| C12 | Per-format key write before transfer | **PASS** | x5a writes `fw.keys` to `FLASH_DECRYPTION_KEY` (L401-403, mirrors upstream). x31 writes `bytes(parsed["key"])` (the 3 cipher bytes from the `&` header, e.g. `BF 10 9E`) to the same DID (L407-414). Note that the x31 path **assumes the ECU accepts the same DID for the cipher key** — this is part of the unverified bootloader behavior in C11; flag it. |

**Correctness verdict: 11/12 PASS, 1 conditional (hardware-unverified, acknowledged in code).** No correctness blocks.

---

## Edge cases (suggestions, not blocks)

| E# | Case | Current behavior | Suggestion |
|---|---|---|---|
| E1 | Bad path / missing .rwd file | `main()` L559-561: `if not os.path.exists(args.rwd): print "[fatal] firmware file not found"; return 2`. ✓ Handled. | None — already correct. |
| E2 | `--bus` missing | argparse `required=True` (L547). argparse exits with usage. ✓ | None. |
| E3 | Panda not connected / wrong VID:PID | `get_uds_client()` catches the panda init exception and falls back to a mock client (L189-208). The dry run still proceeds with canned values (`b'39990-TVA-A160\x00\x00'` for app ID, `b'\x67\x01\x12\x34'` for SA response). | Consider warning louder when the mock activates with `--danger` set — current behavior is to print one line and proceed. If the operator is in `--danger` mode and the panda is unplugged, the mock will sail through the entire flow and look like a successful flash. Recommendation: under `--danger`, refuse to proceed if the panda fails to open. |
| E4 | Wrong bus number / no EPS on that bus | `tester_present()` will time out or get a negative response. The exception handler catches and returns 3. | Add a clearer "no response from ECU at 0x{can_addr:08X} on bus {bus}" message at the catch site to help operator diagnose without reading a traceback. |
| E5 | ECU already in some diagnostic session | Honda EPS will usually accept a re-entry to extended session. If not, NRC fires and the exception handler returns 3. | None — acceptable. |
| E6 | Timeout on any UDS exchange | Caught by the exception handler. | None. |
| E7 | Power loss mid-flash | The script can't recover from this. The README mentions "do NOT interrupt the flash" but the script itself has no resume logic. | None possible at the script layer; this is an operator-procedure concern. |
| E8 | Comma 3X SAFETY mode vs red panda mode | Script always sets `Panda.SAFETY_ELM327` (L193). | None — matches upstream. |
| E9 | `app_id` for x31 has no consumer | The x31 path computes `app_id` (L342-345) but `sa_seed_to_key()` ignores it for x31 (L223-224). So if the firmware doesn't match the ECU's reported app_id, x31 will happily compute and send a key anyway. | The operator's match-check has to happen visually from the printed `app_id` and the printed `[x31] supported part numbers`. The script prints both (L298-300, L345), so this is workable. Consider adding an explicit warning when the operator's app_id does not appear in `headers[/]`'s parts list — at least under `--danger`, refuse to proceed. |
| E10 | x31 has no `%` header | `get_can_address_x31()` raises `RuntimeError` BEFORE the danger banner or any UDS call. ✓ | None. |
| E11 | x5a parser unavailable / wrong path | `_load_x5a_class()` L108-113 attempts the import. If it fails, `flash()` L313-317 prints a helpful message about `EPS_UPDATE_X5A_PATH` and returns 2. ✓ | None, though see N1 below for cross-platform path concerns. |
| E12 | Sigterm during the interactive `FLASH` prompt | `input()` catches `KeyboardInterrupt` and `EOFError` (L261), aborts cleanly. ✓ | None. |

---

## Non-safety notes (note but don't block)

| N# | Item | Comment |
|---|---|---|
| N1 | Hardcoded path `D:/sa-key-hunt/sunnypilot_eps` (L104) | Joey-specific. The env var `EPS_UPDATE_X5A_PATH` (documented in script header, L102-105) is the escape hatch. README does not mention this env var prominently — consider adding it. The x31 path does NOT depend on this, so an Accord operator without the upstream repo can still use the script. |
| N2 | `panda` import errors in `flash()` | Lazy-imported at L281-284 so `--help` works without the panda lib installed. ✓ |
| N3 | `tqdm` is optional | Falls back to `_NullProgress` if not installed (L450-452, L488-492). ✓ |
| N4 | Import paths | `_HERE` (L54-56) prepends the script's directory to `sys.path` so `from tva_sa_key import ...` works regardless of cwd. Verified by `python flashing-2020accord/eps-update-tva.py --help` running cleanly from the repo root. ✓ |
| N5 | README accuracy | README (177 lines) matches the actual script behavior: dry-run default, `--danger` + interactive prompt, `--yes` requires `--danger`, multi-block x31, V850 SA via firmware constants. Tabular "Differences from upstream" matches the code. ✓ |
| N6 | Code quality | Clean, well-commented, single-file. UDS chain is readable. Functions have docstrings. Type hints are present on signatures. |
| N7 | Logging | Useful messages at every step (`[load]`, `[x31]`, `[uds]`, `[sa]`, `[flash]`, `[danger]`, `[boot]`, `[error]`). The dry-run summary banner is informative and reads as an explicit success receipt. ✓ |
| N8 | Mock client's canned `app_id` | `b'39990-TVA-A160\x00\x00'` (L206) — chosen to match the target TVA part number so a fully-offline dry run on x31 also "looks right". Reasonable. |
| N9 | Mock client's canned seed | `b'\x67\x01\x12\x34'` → `seed_bytes = b'\x12\x34'`. `calculate_tva_session_key(b'\x12\x34')` = `b'\x11\x6D'` per the verified test vectors. So an offline dry-run will print "computed key : 0x116D" which is a real verified vector. ✓ |
| N10 | x5a single-block assertion | `assert len(fw.firmware_blocks) == 1` (L454-455). Matches upstream. x5a multi-block is an unsupported case in both. ✓ |

---

## Cross-validation with upstream (positive findings worth calling out)

| Aspect | Upstream | This script | Match? |
|---|---|---|---|
| SA UDS sequence ordering | `tester_present → read_data_by_id(F181) → DSC(EXT) → SA(REQ_SEED) → SA(SEND_KEY)` | identical | ✓ |
| Programming-mode sequence | `DSC(PROG) → routine_control(START, ERASE_MEMORY) → write_data_by_id(FLASH_DECRYPTION_KEY, fw.keys) → request_download → transfer_data → request_transfer_exit → routine_control(START, CHECK_PROGRAMMING_DEPENDENCIES)` | identical for x5a (L388-426); x31 substitutes the cipher-key write with the parsed `&` bytes (L407-414) and runs the per-block transfer loop | ✓ where it should be; x31 deviation is explicit and necessary |
| `calculate_session_key` for x5a (`(seed+k0) ^ (seed*k1) % k2`) | yes | yes, inline as `calculate_universal_sa_key` (L120-131), bit-for-bit | ✓ |
| `get_seed_secret` for x5a | walks `headers[4].values` vs `headers[3].values[i].value == app_id` | identical (L159-175) | ✓ |
| `get_can_address` for x5a | `0x18DA00F1 \| headers[2].values[0].value << 8` | identical (L150-152) | ✓ |
| `--bus` argument | `default=0` (upstream) | `required=True` (this script) — **safer** | ✓ improvement |
| `--danger` semantics | upstream `raise RuntimeError("Safe mode")` after PROGRAMMING DSC — i.e. upstream actually enters programming session even in safe mode | this script returns cleanly **before** PROGRAMMING DSC — **safer** | ✓ improvement |
| Interactive confirmation | none | `FLASH` prompt + name-back of file/bus/addr | ✓ improvement (CLAUDE.md rule) |
| Mock fallback | yes (matches upstream) | yes, with TVA-tuned canned values | ✓ |

**Net assessment:** this script is a strict superset of upstream's safety posture. Wherever it deviates, the deviation tightens safety (required `--bus`, dry-run exits before PROGRAMMING session, interactive prompt with name-back). The x31-specific additions (multi-block transfer, V850 SA routing) are clearly delineated and gated behind format detection.

---

## Recommended fixes — **NONE** required to ship the dry-run path.

The script is approved for first-light dry-run on a real 2020 Accord TVA ECU.

---

## Suggested improvements (post-ship polish)

These are *nice-to-have*, not blocks:

1. **Mock-under-danger guard (E3).** Refuse to proceed if `--danger` is set and the panda fails to open and the mock activates. Current: prints one line and continues. Risk: an operator who fat-fingers a USB unplug then `--danger`-flashes against the mock thinks they flashed when they didn't (would not brick anything, but would leave the operator confused).
2. **Part-number match guard (E9).** Under `--danger`, refuse to proceed if the ECU's reported `app_id` is not in the x31 `/` header's supported-parts list. Current behavior trusts the operator to eyeball it. The dry-run path is fine as-is.
3. **Document `EPS_UPDATE_X5A_PATH` in the README's setup section (N1).** Currently only documented in the script header.
4. **First-light `--danger` x31 caveat in the README.** The README mentions multi-block but does not explicitly carry the "hardware-unverified bootloader nuance" warning that's in the script docstring (L482-487). Worth surfacing to the operator before they hit `--danger`.
5. **Surface NRC code in the catch site (E4).** When the exception handler catches a `NegativeResponseError`, print the NRC byte and the human-readable description prominently before the traceback. The information is in the exception object, but operators reading a wall of traceback may miss it.

---

## Test methodology — what was run

- `python -c "import ast; ast.parse(open(...).read())"` → SYNTAX OK
- `python flashing-2020accord/eps-update-tva.py --help` → CLI surface verified, no missing arg validation
- Code trace from `main()` through `flash()` through every UDS call site, validating that no destructive call is reachable without `danger=True`
- Cross-read against `D:/sa-key-hunt/sunnypilot_eps/eps-update.py` for upstream parity
- Cross-read against `D:/sa-key-hunt/sunnypilot_eps/panda/python/uds.py` to verify NRC handling, seed return format, and the `security_access` signature
- `tva_sa_key.py` test vectors cross-checked against `V850_ALGORITHM_VERIFIED.md` Sample Values table
- README cross-checked line-by-line against script behavior

**No CAN traffic generated. No hardware touched. No file modified beyond this report.**
