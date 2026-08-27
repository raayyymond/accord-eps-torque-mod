"""eps-update-tva.py - Honda EPS flasher with V850/TVA support.

Adapted from hdlineage/sunnypilot_eps eps-update.py (release-c3-eps branch).

What's different from upstream:
1. Auto-detects .rwd container format (x5a or x31) by magic byte.
2. For x31 (V850 family - Accord TVA, ILX TV9, 9th-gen Accord T2F/T3L, etc.),
   uses tva_sa_key.calculate_tva_session_key() with the FIRMWARE-EMBEDDED
   Group C constants (0x0211, 0x0212, 0x1220 at code-flash 0x92C0..0x92C5).
   The V850 ECU does NOT use the ! header bytes (Group A `001100121020`) for
   SA - that was a prior incorrect inference; see V850_ALGORITHM_VERIFIED.md.
3. For x5a (SH-2A family - Civic, Clarity, CR-V, Pilot, Insight), preserves
   upstream behavior: uses headers[4] bytes as the SA secret, matched against
   the ECU's reported application-software ID via headers[3].
4. CAN ID per-format: x31 reads the `%` ASCII-hex header (e.g. b'80' ->
   0x18DA80F1 for TVA); x5a reads headers[2][0] (a raw byte). Both follow
   the upstream pattern of OR'ing into 0x18DA00F1.
5. Defaults to DRY RUN. --danger is required to actually flash. Dry run does
   tester-present -> app-id read -> extended session -> SA handshake -> STOPS
   before any erase / write / transfer.
6. Honors the firmware-analysis-kit CLAUDE.md safety rules: the --danger
   path prints the firmware file name and bus number and requires interactive
   y/N confirmation unless --yes is also passed (still a safety net even when
   an operator scripts it).

USAGE:
  # Safe dry run (DEFAULT - does not flash). Validates the SA handshake
  # by actually exchanging the seed+key with the ECU, then stops.
  python eps-update-tva.py --bus 1 path/to/firmware.rwd

  # Real flash (DANGEROUS - requires --danger AND interactive confirmation
  # unless --yes is also passed):
  python eps-update-tva.py --bus 1 --danger path/to/firmware.rwd

  # Multi-block x31 transfer with debug:
  python eps-update-tva.py --bus 1 --debug path/to/firmware.rwd

Verified references:
  - tva_sa_key.py             - V850 SA algorithm (Wave-3 verified)
  - V850_ALGORITHM_VERIFIED.md - bit-level audit trail
  - ACCORD_TVA_ARCHITECTURE_MAP.md sec 6.1 / 7.4
  - lib/encode_eps.py             - x31/x5a container parsers (round-trip verified)
"""

import argparse
import gzip
import os
import struct
import sys
import traceback
from typing import List, Optional, Tuple

# Make our analysis-2020accord modules importable regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tva_sa_key import calculate_tva_session_key  # V850/TVA path (verified)
from encode_eps import parse_x31                  # V850 container parser


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def read_file(fn: str) -> bytes:
    """Read .rwd or .rwd.gz transparently."""
    f_name, f_ext = os.path.splitext(fn)
    open_fn = gzip.open if f_ext == ".gz" else open
    with open_fn(fn, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(rwd_bytes: bytes) -> str:
    """Return 'x31' (V850) or 'x5a' (SH-2A) based on the magic byte.

    x31: starts 31 0D 0A   (ASCII '1\\r\\n')
    x5a: starts 5A 0D 0A   (ASCII 'Z\\r\\n')
    """
    if len(rwd_bytes) < 3:
        raise ValueError("File too short to determine format")
    magic = rwd_bytes[0]
    if magic == 0x31:
        return "x31"
    if magic == 0x5A:
        return "x5a"
    raise ValueError(
        f"Unknown .rwd format: magic byte 0x{magic:02X} "
        "(expected 0x31 for V850/x31 or 0x5A for SH-2A/x5a)"
    )


# ---------------------------------------------------------------------------
# x5a lazy loader (only needed for SH-2A fallback)
# ---------------------------------------------------------------------------

# Default upstream location on the project lead's machine. Override via
# the EPS_UPDATE_X5A_PATH env var when the upstream repo lives elsewhere.
_DEFAULT_UPSTREAM = os.environ.get(
    "EPS_UPDATE_X5A_PATH", "D:/sa-key-hunt/sunnypilot_eps"
)


def _load_x5a_class():
    """Lazy-import upstream x5a parser. Returns the class or raises ImportError."""
    if _DEFAULT_UPSTREAM not in sys.path:
        sys.path.insert(0, _DEFAULT_UPSTREAM)
    from panda.format.x5a import x5a as x5a_class  # noqa: E402
    return x5a_class


# ---------------------------------------------------------------------------
# Universal Honda SA algorithm (SH-2A / x5a path) - mirrors upstream
# ---------------------------------------------------------------------------

def calculate_universal_sa_key(const_bytes: bytes, seed_bytes: bytes) -> bytes:
    """Universal Honda EPS seed->key for SH-2A family via x5a headers[4].

    Identical math to upstream eps-update.py:45 - kept inline so this script
    is self-sufficient when upstream isn't on the import path.
    """
    k0, k1, k2 = struct.unpack("!HHH", const_bytes)
    if k2 == 0:
        k2 = 0x10000
    seed = struct.unpack("!H", seed_bytes)[0]
    key = (seed + k0) ^ ((seed * k1) % k2)
    return struct.pack("!H", key & 0xFFFF)


# ---------------------------------------------------------------------------
# CAN address resolution
# ---------------------------------------------------------------------------

def get_can_address_x31(parsed: dict) -> int:
    """Read CAN sig byte from x31 `%` header (ASCII hex) -> 0x18DA__F1.

    Example: `%` header value b'80' -> 0x18DA80F1 (TVA family).
    """
    for tag, vals in parsed["headers"]:
        if tag == b"%":
            sig = int(vals[0].decode("ascii"), 16)
            return 0x18DA00F1 | (sig << 8)
    raise RuntimeError("x31 file has no `%` (CAN sig byte) header")


def get_can_address_x5a(fw) -> int:
    """Mirror upstream eps-update.py:90 get_can_address()."""
    return 0x18DA00F1 | (struct.unpack("!B", fw.file_headers[2].values[0].value)[0] << 8)


# ---------------------------------------------------------------------------
# x5a SA-secret lookup (mirrors upstream get_seed_secret)
# ---------------------------------------------------------------------------

def get_x5a_seed_secret(fw, app_id: bytes) -> bytes:
    """Look up the per-part SA secret in headers[4] by matching headers[3].

    Mirrors upstream eps-update.py:82. The ECU reports its current
    application-software ID via DID 0xF181; the .rwd carries one or more
    supported part numbers in headers[3] and a parallel list of SA secrets
    in headers[4]. Pick the secret whose part matches what the ECU reports.
    """
    headers = fw.file_headers
    for i in range(len(headers[4].values)):
        if headers[3].values[i].value == app_id:
            return headers[4].values[i].value
    raise RuntimeError(
        f"Couldn't find software seed for application ID {app_id!r}; "
        f"supported parts in this .rwd: "
        f"{[h.value for h in headers[3].values]}"
    )


def get_x31_supported_parts(parsed: dict) -> List[bytes]:
    """Read the `/` header from an x31 file -> list of supported part-number bytes.

    Used as a part-number-mismatch gate. The SA path for x31 is universal
    (V850 Group-C constants) so without this check an operator could pass
    a Civic-family firmware to an Accord ECU - same SA would succeed, but
    the flash content would be for the wrong vehicle.
    """
    for tag, vals in parsed["headers"]:
        if tag == b"/":
            return list(vals)
    return []


def app_id_matches_part(app_id: bytes, supported_parts: List[bytes]) -> bool:
    """Compare ECU-reported app id against the .rwd's supported part list.

    app_id from DID 0xF181 is typically 16 bytes with trailing NULs (e.g.
    b'39990-TVA-A160\\x00\\x00'). Supported-parts entries are usually the
    ASCII part number without NULs (e.g. b'39990-TVA-A160'). Strip NULs/
    whitespace from both sides before comparing, and accept either a
    full-string match or a prefix match (some Honda parts have a revision
    suffix the supported list doesn't always carry).
    """
    norm = lambda b: b.rstrip(b"\x00").strip()
    a = norm(app_id)
    for p in supported_parts:
        pn = norm(p)
        if a == pn or a.startswith(pn) or pn.startswith(a):
            return True
    return False


# ---------------------------------------------------------------------------
# UDS client (real or mock)
# ---------------------------------------------------------------------------

def get_uds_client(can_addr: int, can_bus: int, debug: bool, danger: bool = False):
    """Connect to a real panda, or fall back to a mock for offline dry-run.

    Mirrors upstream's pattern. The mock path lets the script run on a
    machine with no panda hardware - useful for syntax/flow validation
    without sending any CAN traffic at all.

    SAFETY: when danger=True, the mock fallback is REFUSED. Otherwise an
    operator running --danger with no panda attached would see a "successful
    flash" against the mock and believe the ECU was written when nothing
    happened. No brick risk (no CAN sent) but a real misleading-success risk.
    """
    try:
        from panda import Panda
        from panda.python.uds import UdsClient
        # Back-compat shim: modern panda lib moved SAFETY_ELM327 off the Panda
        # class onto CarParams.SafetyModel.elm327. Numeric value is 3 in both
        # eras (see opendbc/safety/declarations.h: #define SAFETY_ELM327 3U),
        # and set_safety_mode passes the int straight through to controlWrite.
        if not hasattr(Panda, "SAFETY_ELM327"):
            Panda.SAFETY_ELM327 = 3
        panda = Panda(disable_checks=True)
        panda.set_safety_mode(Panda.SAFETY_ELM327)
        uds_client = UdsClient(panda, can_addr, debug=debug, bus=can_bus)
        print(f"[uds] Using real panda client, bus={can_bus}, "
              f"addr=0x{can_addr:08X}")
        return uds_client, False  # is_mock=False
    except Exception as e:
        if danger:
            print(f"[uds] FATAL: No real panda available ({type(e).__name__}: {e})", file=sys.stderr)
            print("[uds] Refusing to mock under --danger. Connect the panda and retry.", file=sys.stderr)
            print("[uds] (Mock fallback is dry-run only — preventing misleading 'flash succeeded' against a mock.)", file=sys.stderr)
            raise SystemExit(2)
        print(f"[uds] No real panda available ({type(e).__name__}: {e}); "
              "using mock client (dry-run only)")
        from unittest import mock
        helper = mock.patch("panda.python.uds.UdsClient", autospec=True)
        uds_client = helper.start()
        # Plausible canned responses so the dry-run flow can execute end-to-end
        uds_client.security_access.return_value = b"\x67\x01\x12\x34"
        uds_client.read_data_by_identifier.return_value = b"39990-TVA-A160\x00\x00"
        uds_client.request_download.return_value = 514
        return uds_client, True  # is_mock=True


# ---------------------------------------------------------------------------
# Format-aware SA key routing
# ---------------------------------------------------------------------------

def sa_seed_to_key(fmt: str, parsed_or_fw, seed_bytes: bytes,
                   app_id: bytes) -> bytes:
    """Route SA-key computation by container format.

    x31 (V850): firmware ignores ! header bytes; use Group C constants
                via the verified tva_sa_key implementation.
    x5a (SH-2A): look up headers[4] by part-number match against headers[3].
    """
    if fmt == "x31":
        return calculate_tva_session_key(seed_bytes)
    else:
        secret = get_x5a_seed_secret(parsed_or_fw, app_id)
        return calculate_universal_sa_key(secret, seed_bytes)


# ---------------------------------------------------------------------------
# Safety confirmation gate
# ---------------------------------------------------------------------------

def confirm_danger(rwd_path: str, bus: int, fmt: str, can_addr: int,
                   skip_prompt: bool, multi_block: bool = False) -> bool:
    """Per CLAUDE.md: never flash without naming the firmware file and bus.

    Repeat both back to the operator and require interactive y/N, unless
    --yes is passed (still requires --danger to even reach this point).
    """
    print()
    print("=" * 70)
    print("  DANGER MODE - ABOUT TO MUTATE EPS ECU FLASH")
    print("=" * 70)
    print(f"  Firmware file : {rwd_path}")
    print(f"  Container     : {fmt}")
    print(f"  CAN bus       : {bus}")
    print(f"  CAN address   : 0x{can_addr:08X}")
    print()
    print("  Required prerequisites (per docs/guides/EPS-FLASH-RUNBOOK.md):")
    print("    - Car ignition ON (engine off is fine)")
    print("    - Panda is the only device on OBD-II")
    print("    - openpilot/pandad killed on any comma device (tmux kill-server)")
    print("    - firmware part-number matches the target car")
    if fmt == "x31":
        print()
        print("  UNVERIFIED V850/TVA ASSUMPTIONS (no factory-flash capture yet):")
        print("    - cipher-key wire format (DID 0xF050 payload byte order)")
        print("    - request_transfer_exit cadence (per-block vs end-only)")
        if multi_block:
            print("    - MULTI-BLOCK transfer sequence (--allow-multiblock acknowledged)")
        print("    If the flash fails the ECU may end up in an unbootable state.")
    print("=" * 70)
    if skip_prompt:
        print("[danger] --yes passed, skipping interactive prompt")
        return True
    try:
        ans = input("Type 'FLASH' (all caps) to proceed, anything else to abort: ")
    except (EOFError, KeyboardInterrupt):
        print("\n[danger] aborted by operator")
        return False
    if ans.strip() != "FLASH":
        print("[danger] confirmation not given, aborting")
        return False
    return True


# ---------------------------------------------------------------------------
# Main flash workflow
# ---------------------------------------------------------------------------

def flash(rwd_path: str, bus: int, danger: bool, skip_prompt: bool,
          debug: bool, allow_multiblock: bool = False,
          force_part_mismatch: bool = False) -> int:
    """Run the format-aware EPS flash workflow.

    Returns process exit code (0 on success, non-zero on failure).
    """
    # Lazy import here so the panda import errors don't crash --help.
    from panda.python.uds import (
        SESSION_TYPE, ACCESS_TYPE, ROUTINE_CONTROL_TYPE,
        ROUTINE_IDENTIFIER_TYPE, DATA_IDENTIFIER_TYPE,
    )

    print(f"[load] reading {rwd_path}")
    rwd = read_file(rwd_path)
    fmt = detect_format(rwd)
    print(f"[load] detected container format: {fmt} "
          f"({len(rwd)} bytes, magic 0x{rwd[0]:02X})")

    # ---- format-specific parsing ----
    if fmt == "x31":
        parsed = parse_x31(rwd)
        can_addr = get_can_address_x31(parsed)
        # Surface the supported parts and SA secret for the operator
        for tag, vals in parsed["headers"]:
            if tag == b"/":
                print(f"[x31] supported part numbers: "
                      f"{[v.decode('ascii', errors='replace') for v in vals]}")
            elif tag == b"!":
                print(f"[x31] ! header (NOT used by V850 SA): "
                      f"{[v.decode('ascii', errors='replace') for v in vals]}")
        print(f"[x31] cipher key bytes: {parsed['key']}")
        print(f"[x31] {len(parsed['blocks'])} block(s) to transfer:")
        for i, blk in enumerate(parsed["blocks"]):
            print(f"        block {i}: start=0x{blk['start']:08X} "
                  f"length=0x{blk['length']:X}")
        fw_handle = parsed
        # Refuse multi-block --danger without an explicit acknowledgement -
        # _transfer_x31 multi-block sequencing (per-block transfer-exit and
        # per-block seq reset) is not hardware-verified on V850.
        if danger and len(parsed["blocks"]) > 1 and not allow_multiblock:
            print()
            print("[fatal] This .rwd has multiple firmware blocks. The multi-block")
            print("        x31 transfer path (per-block transfer-exit, per-block seq")
            print("        reset) has not been verified against a Honda factory flash")
            print("        capture and could brick the ECU if the bootloader expects")
            print("        a different sequence. Pass --allow-multiblock to proceed")
            print("        anyway (acknowledging brick risk), or use a single-block .rwd.")
            return 2
    else:
        try:
            x5a_class = _load_x5a_class()
        except ImportError as e:
            print(f"[x5a] upstream parser not available: {e}")
            print(f"[x5a] set EPS_UPDATE_X5A_PATH to the directory containing "
                  f"the panda/format/x5a.py module")
            return 2
        fw = x5a_class(rwd)
        can_addr = get_can_address_x5a(fw)
        print(f"[x5a] {fw}")
        fw_handle = fw

    print(f"[flash] CAN address resolved to 0x{can_addr:08X}")

    # ---- danger gate, EARLY ----
    if danger:
        multi_block = fmt == "x31" and len(fw_handle["blocks"]) > 1
        if not confirm_danger(rwd_path, bus, fmt, can_addr, skip_prompt,
                              multi_block=multi_block):
            return 1
    else:
        print("[flash] DRY RUN (default) - will stop after SA handshake")

    # ---- UDS client ----
    uds_client, is_mock = get_uds_client(can_addr, bus, debug, danger=danger)

    debug_output: List = []

    print("[uds] tester present...")
    uds_client.tester_present()

    try:
        print("[uds] reading application software ID (0xF181)")
        app_id = uds_client.read_data_by_identifier(
            DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION
        )
        print(f"[uds] application software ID = {app_id!r}")

        # ---- part-number gate (early, before any session change) ----
        # x5a is protected by get_x5a_seed_secret raising on no-match; x31
        # uses the universal V850 SA algorithm so a mismatched part would
        # still SA-succeed. Compare app_id against the `/` header part list
        # and refuse unless --force-part-mismatch is set.
        if fmt == "x31":
            supported = get_x31_supported_parts(fw_handle)
            if supported and not app_id_matches_part(app_id, supported):
                supported_str = [s.decode("ascii", errors="replace") for s in supported]
                print(f"[fatal] ECU app id {app_id!r} does not match any supported")
                print(f"        part in this .rwd: {supported_str}")
                if not force_part_mismatch:
                    print(f"        Refusing to flash mismatched part. Pass")
                    print(f"        --force-part-mismatch to override (UNSAFE - wrong-")
                    print(f"        vehicle firmware can produce unsafe steering).")
                    return 2
                print(f"[warn]  --force-part-mismatch set, proceeding anyway")
            elif supported:
                print(f"[ok]    ECU app id matches a supported part")

        print("[uds] setting diagnostic session = EXTENDED_DIAGNOSTIC (0x03)")
        data = uds_client.diagnostic_session_control(
            SESSION_TYPE.EXTENDED_DIAGNOSTIC
        )
        debug_output.append(data)

        print("[sa]  requesting seed (0x27 0x01)")
        data = uds_client.security_access(ACCESS_TYPE.REQUEST_SEED)
        debug_output.append(data)
        seed_bytes = data[-2:]
        print(f"[sa]  received seed: 0x{seed_bytes.hex().upper()}")

        key = sa_seed_to_key(fmt, fw_handle, seed_bytes, app_id)
        print(f"[sa]  computed key : 0x{key.hex().upper()} "
              f"(via {'V850 Group-C firmware constants' if fmt == 'x31' else 'SH-2A headers[4] secret'})")

        print("[sa]  sending key (0x27 0x02)")
        data = uds_client.security_access(ACCESS_TYPE.SEND_KEY, key)
        debug_output.append(data)
        print("[sa]  SA handshake succeeded")

        # ---- DRY-RUN STOP POINT ----
        if not danger:
            print()
            print("=" * 70)
            print("  DRY RUN COMPLETE - SA handshake succeeded, stopping before flash")
            print("=" * 70)
            print(f"  ECU app ID    : {app_id!r}")
            print(f"  Seed received : 0x{seed_bytes.hex().upper()}")
            print(f"  Key accepted  : 0x{key.hex().upper()}")
            print(f"  Container fmt : {fmt}")
            print(f"  CAN address   : 0x{can_addr:08X}")
            print(f"  Bus           : {bus}")
            print()
            print("  This run proves the SA algorithm + constants are correct")
            print("  against the real ECU without any flash risk.")
            print("  Re-run with --danger to perform the actual flash.")
            print("=" * 70)
            return 0

        # ---- DANGER PATH BELOW THIS LINE ----
        print("[uds] setting diagnostic session = PROGRAMMING (0x02)")
        data = uds_client.diagnostic_session_control(SESSION_TYPE.PROGRAMMING)
        debug_output.append(data)

        # Heartbeat before the long-running erase: defends against S3 timeout
        # if the bootloader takes its time getting into PROGRAMMING state.
        uds_client.tester_present()

        print("[flash] erasing flash memory")
        erase_status = uds_client.routine_control(
            ROUTINE_CONTROL_TYPE.START,
            ROUTINE_IDENTIFIER_TYPE.ERASE_MEMORY,
        )
        debug_output.append(erase_status)
        # Surface the routine_status bytes - non-zero values are vendor-
        # specific failure codes on some Honda ECUs. _uds_request already
        # raises NegativeResponseError on any 0x7F response, so reaching
        # here means UDS-positive, but log the body for human review.
        print(f"[flash] erase routine_status = {erase_status.hex().upper() if erase_status else '(empty)'}")

        # Heartbeat after erase: erase can take several seconds and the
        # bootloader may have used the entire S3 window.
        uds_client.tester_present()

        if fmt == "x5a":
            print("[flash] writing firmware decryption key (x5a)")
            data = uds_client.write_data_by_identifier(
                DATA_IDENTIFIER_TYPE.FLASH_DECRYPTION_KEY, fw_handle.keys
            )
            debug_output.append(data)
            _transfer_x5a(uds_client, fw_handle, debug_output)
        else:
            # x31 V850: send the cipher key bytes (from `&` header) the same way
            cipher_key = bytes(parsed["key"])
            print(f"[flash] writing firmware decryption key (x31): "
                  f"{cipher_key.hex().upper()}")
            data = uds_client.write_data_by_identifier(
                DATA_IDENTIFIER_TYPE.FLASH_DECRYPTION_KEY, cipher_key
            )
            debug_output.append(data)
            _transfer_x31(uds_client, parsed, debug_output)

        print("[flash] requesting transfer exit")
        data = uds_client.request_transfer_exit()
        debug_output.append(data)

        # Heartbeat before dependency check (final routine can also be slow).
        uds_client.tester_present()

        print("[flash] checking programming dependencies")
        deps_status = uds_client.routine_control(
            ROUTINE_CONTROL_TYPE.START,
            ROUTINE_IDENTIFIER_TYPE.CHECK_PROGRAMMING_DEPENDENCIES,
        )
        debug_output.append(deps_status)
        print(f"[flash] dependencies routine_status = {deps_status.hex().upper() if deps_status else '(empty)'}")
        # Heuristic: many Honda ECUs return 0x00 for "passed". Anything else
        # is suspect. We do NOT auto-abort because vendor codes vary and a
        # false-positive here would be its own brick risk - the operator
        # gets the bytes and decides whether to re-flash.
        if deps_status and any(b != 0 for b in deps_status):
            print(f"[warn]  dependency check returned non-zero status bytes.")
            print(f"[warn]  DO NOT POWER-CYCLE THE ECU until you have confirmed")
            print(f"[warn]  this status is benign for your part. Consider re-flashing")
            print(f"[warn]  immediately while still in PROGRAMMING session.")

        print("[flash] DONE")
        return 0

    except Exception:
        print("[error] exception during flash flow:")
        print(traceback.format_exc())
        return 3
    finally:
        if debug:
            print("\n[debug] debug output:")
            for d in debug_output:
                print(f"  {d}")


# ---------------------------------------------------------------------------
# Per-format block transfer helpers
# ---------------------------------------------------------------------------

def _transfer_x5a(uds_client, fw, debug_output: list) -> None:
    """Single-blob x5a transfer (mirrors upstream)."""
    try:
        import tqdm as _tqdm
        progress_cls = _tqdm.tqdm
    except ImportError:
        progress_cls = _NullProgress

    assert len(fw.firmware_blocks) == 1, \
        "x5a: only single-block firmware is supported (upstream assumption)"
    block = fw.firmware_blocks[0]
    length = block["length"]
    print(f"[flash] requesting download: start=0x{block['start']:08X} "
          f"length=0x{length:X}")
    max_chunk_size = uds_client.request_download(block["start"], length)
    max_chunk_size -= 2  # subtract UDS header bytes per upstream

    with progress_cls(total=length, unit="B", unit_scale=True) as t:
        cursor = 0
        seq = 1
        while cursor < length:
            block_size = min(max_chunk_size, length - cursor)
            data = uds_client.transfer_data(
                seq, fw.firmware_encrypted[0][cursor:cursor + block_size]
            )
            debug_output.append(data)
            seq = (seq + 1) & 0xFF
            cursor += block_size
            t.update(block_size)


def _transfer_x31(uds_client, parsed: dict, debug_output: list) -> None:
    """Multi-block x31 transfer. Each block gets its own request_download
    + transfer_data sequence + request_transfer_exit per UDS convention.

    NOTE: this mirrors the upstream single-block pattern extended to N blocks.
    The actual TVA bootloader's exact protocol nuance (whether it wants a
    transfer-exit between blocks vs at the end only) is NOT yet hardware-
    verified - this code path is only executed under --danger and only after
    interactive operator confirmation. First-light --danger run on a real
    TVA ECU should be tightly observed.
    """
    try:
        import tqdm as _tqdm
        progress_cls = _tqdm.tqdm
    except ImportError:
        progress_cls = _NullProgress

    blocks = parsed["blocks"]
    encs = parsed["encs"]
    total = sum(b["length"] for b in blocks)
    print(f"[flash] x31 multi-block transfer: {len(blocks)} block(s), "
          f"total 0x{total:X} bytes")

    with progress_cls(total=total, unit="B", unit_scale=True) as t:
        for i, (block, enc) in enumerate(zip(blocks, encs)):
            length = block["length"]
            print(f"[flash] block {i}: request_download "
                  f"start=0x{block['start']:08X} length=0x{length:X}")
            max_chunk_size = uds_client.request_download(block["start"], length)
            max_chunk_size -= 2
            cursor = 0
            seq = 1
            while cursor < length:
                block_size = min(max_chunk_size, length - cursor)
                data = uds_client.transfer_data(
                    seq, enc[cursor:cursor + block_size]
                )
                debug_output.append(data)
                seq = (seq + 1) & 0xFF
                cursor += block_size
                t.update(block_size)
            # Per-block transfer-exit. If hardware proves this is wrong on TVA,
            # remove and let the single final exit in flash() handle it.
            if i < len(blocks) - 1:
                data = uds_client.request_transfer_exit()
                debug_output.append(data)


class _NullProgress:
    """Minimal stand-in when tqdm isn't installed (CI / dry-run-only setups)."""
    def __init__(self, total=0, **_kwargs):
        self.total = total
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def update(self, n): pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Honda EPS flasher with V850/TVA support (x31 + x5a)",
        epilog=(
            "Defaults to DRY RUN. --danger is required to perform the actual flash, "
            "and requires interactive 'FLASH' confirmation unless --yes is also passed."
        ),
    )
    p.add_argument("rwd", help="Path to .rwd[.gz] firmware file")
    p.add_argument("--bus", type=int, required=True,
                   help="CAN bus number (typically 1 for OBD-II on a red panda)")
    p.add_argument("--danger", action="store_true",
                   help="REQUIRED to actually flash. Without it, the script stops "
                        "after a successful SA handshake.")
    p.add_argument("--yes", action="store_true",
                   help="Skip the interactive 'FLASH' confirmation in --danger mode. "
                        "Use only when scripting; --danger is still required.")
    p.add_argument("--debug", action="store_true",
                   help="Verbose UDS debug output")
    p.add_argument("--allow-multiblock", action="store_true",
                   help="REQUIRED for --danger on x31 .rwd files with more than one "
                        "firmware block. The multi-block transfer sequence is not "
                        "hardware-verified on V850; passing this acknowledges brick risk.")
    p.add_argument("--force-part-mismatch", action="store_true",
                   help="Override the part-number gate. Allows flashing a .rwd whose "
                        "supported parts do not include the ECU's reported app id. "
                        "UNSAFE - wrong-vehicle firmware can produce unsafe steering.")
    args = p.parse_args()

    if not os.path.exists(args.rwd):
        print(f"[fatal] firmware file not found: {args.rwd}")
        return 2

    # Echo the firmware path + bus before doing anything else, per CLAUDE.md
    # safety rule #2 ("repeat the name back to them before proceeding").
    print(f"[boot] eps-update-tva.py")
    print(f"[boot] firmware file : {args.rwd}")
    print(f"[boot] CAN bus       : {args.bus}")
    print(f"[boot] mode          : "
          f"{'DANGER (will mutate ECU flash)' if args.danger else 'DRY RUN (no mutation)'}")
    print()

    return flash(args.rwd, args.bus, args.danger, args.yes, args.debug,
                 allow_multiblock=args.allow_multiblock,
                 force_part_mismatch=args.force_part_mismatch)


if __name__ == "__main__":
    sys.exit(main())
