"""eps-update-tva.py - Portable, self-contained Honda EPS flasher (V850/TVA).

This is a SINGLE-FILE tool: it has no dependency on any other file in this
repository. The two pieces it used to import - the V850 SecurityAccess
seed->key algorithm (formerly tva_sa_key.py) and the x31 .rwd container
parser (formerly encode_eps.py) - are now inlined below, so this script can
be copied on its own to any machine with a panda and run as-is.

Runtime dependencies are the STANDARD panda + opendbc libraries that ship
inside any current openpilot checkout (only for the actual flash / dry-run
against real hardware) and, optionally, tqdm (progress bars). All are imported
lazily; --help and --selftest work with none installed.

WHERE IT RUNS (2026-10-17 rework - no custom panda fork, no WSL needed):
  * ON A COMMA 4 / COMMA 3X DIRECTLY (recommended). The device's internal
    panda talks to the car over the harness; nothing else is plugged in.
    - `tmux kill-server` FIRST. openpilot's pandad owns the panda; the script
      refuses to run while a pandad process exists.
    - run with plain `python3 eps-update-tva.py ...`: the script re-execs
      itself under the device's managed venv (/usr/local/venv/bin/python3,
      the only interpreter with usb1 / the panda deps) and puts
      /data/openpilot on sys.path so `panda` and `opendbc` resolve.
    - CAN bus is 1 on the Accord harness (same bus opendbc fingerprints the
      EPS on: opendbc/car/honda/values.py FW_QUERY_CONFIG bus=1).
  * ON A LAPTOP WITH A RED PANDA ON OBD-II. Needs an openpilot (or
    panda + opendbc) checkout on PYTHONPATH; bus 1 as before.

UDS client: current openpilot moved `UdsClient` from `panda.python.uds` to
`opendbc.car.uds`, and the ELM327 safety-mode constant from
`Panda.SAFETY_ELM327` to `CarParams.SafetyModel.elm327`. Both locations are
tried, new first, so the script runs on either generation of the library.

Scope: V850/x31 containers only (Honda Accord TVA and the wider V850 EPS
family - ILX TV9, 9th-gen Accord T2F/T3L, etc.). Every .rwd in this repo is
x31. The old x5a (SH-2A: Civic/Clarity/CR-V/Pilot/Insight) code path has been
removed: it could only be enabled by importing an external, machine-specific
copy of the upstream panda x5a parser, which is exactly the non-portable
reliance this cleanup removes. For SH-2A families use upstream
sunnypilot_eps eps-update.py instead.

Behaviour that is preserved verbatim from the prior version:
1. Auto-detects the .rwd container by magic byte; accepts x31, rejects x5a
   with a clear message.
2. For x31 (V850) it uses the FIRMWARE-EMBEDDED Group C constants (0x0211,
   0x0212, 0x1220 at code-flash 0x92C0..0x92C5) for the SA key. The V850 ECU
   does NOT use the `!` header bytes (Group A) for SA.
3. CAN ID comes from the `%` ASCII-hex header (e.g. b'80' -> 0x18DA80F1 for
   TVA), OR'd into 0x18DA00F1 following the upstream pattern.
4. Defaults to DRY RUN. --danger is required to actually flash. Dry run does
   tester-present -> app-id read -> extended session -> SA handshake -> STOPS
   before any erase / write / transfer.
5. The --danger path prints the firmware file name and bus number and
   requires interactive confirmation unless --yes is also passed.

USAGE:
  # Verify the inlined SA algorithm against the known-good vectors (no
  # hardware, no panda needed):
  python eps-update-tva.py --selftest

  # Safe dry run (DEFAULT - does not flash). Exchanges seed+key with the ECU
  # to prove the SA algorithm/constants, then stops:
  python eps-update-tva.py --bus 1 path/to/firmware.rwd

  # Real flash (DANGEROUS - requires --danger AND interactive confirmation
  # unless --yes is also passed):
  python eps-update-tva.py --bus 1 --danger path/to/firmware.rwd

  # Offline flow check with NO hardware and NO CAN traffic (explicit opt-in;
  # there is no silent mock fallback any more):
  python eps-update-tva.py --mock --bus 1 path/to/firmware.rwd

Verified references (documentation only - not imported at runtime):
  - V850_ALGORITHM_VERIFIED.md      - bit-level SA-key audit trail (Wave 3)
  - SA_KEY_PYTHON_PREP.md           - wire-format walkthrough
  - ACCORD_TVA_ARCHITECTURE_MAP.md  - sec 6.1 / 7.4
"""

import argparse
import gzip
import os
import struct
import subprocess
import sys
import traceback
from binascii import a2b_hex
from typing import List


# ===========================================================================
# Environment bootstrap (comma device / openpilot checkout)
#
# Standard openpilot keeps its Python deps in a managed venv on the device
# (/usr/local/venv) and does NOT install `panda`/`opendbc` as site-packages:
# they are importable only with the openpilot checkout on sys.path. This block
# makes `python3 eps-update-tva.py` just work from any directory on a comma
# device, and is a no-op on a machine that already has everything importable.
# ===========================================================================

_COMMA_VENV_PYTHON = "/usr/local/venv/bin/python3"
_OPENPILOT_ROOTS = [
    os.environ.get("OPENPILOT_ROOT", ""),
    "/data/openpilot",
    "/data/pythonpath",
    os.path.expanduser("~/openpilot"),
]


def _bootstrap_env() -> None:
    """Re-exec under the device venv if needed, then add openpilot to sys.path."""
    # 1. On a comma device the system python3 lacks usb1 (and everything else
    #    panda needs). If the managed venv exists and we are not already in it,
    #    re-exec there. Guarded by an env var so it can only happen once.
    #    NOTE: the venv's python3 is a symlink to /usr/bin/python3, so compare
    #    sys.prefix (the venv sets it), never the interpreter's realpath.
    venv_dir = os.path.dirname(os.path.dirname(_COMMA_VENV_PYTHON))
    if (os.path.exists(_COMMA_VENV_PYTHON)
            and os.path.realpath(sys.prefix) != os.path.realpath(venv_dir)
            and not os.environ.get("EPS_UPDATE_NO_REEXEC")):
        try:
            import usb1  # noqa: F401
        except ImportError:
            os.environ["EPS_UPDATE_NO_REEXEC"] = "1"
            print(f"[env] re-executing under {_COMMA_VENV_PYTHON} (panda deps live there)")
            sys.stdout.flush()
            os.execv(_COMMA_VENV_PYTHON, [_COMMA_VENV_PYTHON] + sys.argv)
    # 2. Make `panda` and `opendbc` importable from the openpilot checkout.
    try:
        import panda  # noqa: F401
        return
    except ImportError:
        pass
    for root in _OPENPILOT_ROOTS:
        if root and os.path.isdir(os.path.join(root, "panda")) and root not in sys.path:
            sys.path.insert(0, root)
            print(f"[env] added {root} to sys.path for panda/opendbc")
            return


def pandad_running() -> List[str]:
    """Return the command lines of any running pandad / openpilot processes.

    pandad holds the panda open; a flash attempt while it runs either fails to
    connect or, worse, races pandad for the bus. On a comma device the fix is
    `tmux kill-server`.
    """
    try:
        out = subprocess.run(["pgrep", "-a", "-f", r"(^|/)(pandad|manager\.py|launch_openpilot)"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return []
    return [ln for ln in out.splitlines() if ln.strip() and str(os.getpid()) != ln.split()[0]]


# ===========================================================================
# Inlined: V850/TVA SecurityAccess seed->key algorithm
# (formerly tva_sa_key.py - VERIFIED via disassembly of the V850E2 firmware
#  SA-key routine at 0x00AAB4; full audit trail in V850_ALGORITHM_VERIFIED.md)
#
#   seed16 = received_seed & 0xFFFF
#   key16  = ((seed16 + 0x0211) & 0xFFFF) XOR ((seed16 * 0x0212) mod 0x1220)
#
# The three constants are read from firmware code flash at 0x92C0..0x92C5 and
# match the iHDS catalog "Group C" secret `021102121220`. The "Group A" bytes
# `001100121020` in the `!` header are NOT the SA secret on V850.
# ===========================================================================

TVA_K0 = 0x0211   # addend     (firmware halfword at 0x92C0)
TVA_K1 = 0x0212   # multiplier (firmware halfword at 0x92C2)
TVA_K2 = 0x1220   # modulus    (firmware halfword at 0x92C4)


def _compute_key16(seed16: int, k0: int = TVA_K0, k1: int = TVA_K1,
                   k2: int = TVA_K2) -> int:
    """Integer-domain implementation of the verified V850 algorithm.

    key16 = ((seed16 + k0) & 0xFFFF) XOR ((seed16 * k1) mod k2)

    Both XOR operands are guaranteed < 0x10000, so the result fits in 16 bits.
    """
    s = seed16 & 0xFFFF
    if k2 == 0:
        # Defensive: real firmware k2=0x1220, never zero. Treat 0 as a 16-bit
        # modulus to avoid ZeroDivisionError on caller mistakes.
        k2 = 0x10000
    return ((s + k0) & 0xFFFF) ^ ((s * k1) % k2)


def calculate_tva_session_key(seed_bytes: bytes) -> bytes:
    """Compute the expected SA key for a TVA EPS, given a 2-byte UDS seed.

    Input  : exactly 2 bytes, big-endian seed as received from the ECU
             (the payload following `0x67 0x01` in the SA response).
    Output : exactly 2 bytes, big-endian key to send as the payload following
             `0x27 0x02` in the SendKey request.
    """
    if len(seed_bytes) != 2:
        raise ValueError(
            f"TVA SA seed must be exactly 2 bytes on the UDS wire; "
            f"got {len(seed_bytes)} bytes ({seed_bytes!r})"
        )
    seed16 = struct.unpack("!H", seed_bytes)[0]
    key16 = _compute_key16(seed16)
    return struct.pack("!H", key16)


def _selfcheck_sa() -> bool:
    """Validate the inlined SA algorithm against the known-good vectors.

    These are the primary + boundary vectors from V850_ALGORITHM_VERIFIED.md.
    Running this needs no hardware and no third-party libraries - it proves
    the inlined constants/algorithm still match the verified reference.
    """
    vectors = [
        (b"\x00\x00", b"\x02\x11"),  # seed=0 -> key=k0
        (b"\x12\x34", b"\x11\x6D"),
        (b"\xAB\xCD", b"\xA1\x54"),
        (b"\xFF\xFF", b"\x0E\x5E"),
        (b"\x7F\xFF", b"\x8C\x3E"),  # boundary (signed/unsigned safety)
        (b"\x80\x00", b"\x92\x51"),  # boundary
    ]
    ok = True
    for seed, expected in vectors:
        got = calculate_tva_session_key(seed)
        status = "OK  " if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"[selftest] {status} SA(0x{seed.hex().upper()}) = "
              f"0x{got.hex().upper()} (expected 0x{expected.hex().upper()})")
    print(f"[selftest] {'all SA vectors pass' if ok else 'SA VECTOR MISMATCH'}")
    return ok


# ===========================================================================
# Inlined: x31 (V850 family) .rwd container parser
# (formerly encode_eps.parse_x31 - round-trip byte-verified on same-family
#  siblings: 9th-gen Accord T2F/T3L, ILX TV9)
#
# Format: 31 0D 0A | 6 headers each `[tag 0D 0A] value 0D 0A ... [tag 0D 0A]`
#         | payload of 130-byte chunks `[addr_hi][addr_mid][data:128B]`
#           (addr = hi<<12 | mid<<4) | [file_checksum:u32 LE]
# Header tags (in order): # ? / ! & %
#   /: supported part numbers (ASCII, one per supported version)
#   !: Group-A security bytes (ASCII; NOT used by the V850 SA algorithm)
#   &: encryption key ASCII hex (e.g. b'BF109E' -> 0xBF, 0x10, 0x9E)
#   %: CAN address significant byte ASCII hex (e.g. b'80' in 0x18DA__F1)
# ===========================================================================

def parse_x31(data: bytes) -> dict:
    assert data[:3] == b"\x31\x0D\x0A"
    i = 3
    headers = []
    for _h in range(6):
        tag = data[i:i + 3]
        i += 3  # `[tag_byte 0D 0A]`
        vals = []
        while data[i:i + 3] != tag:
            end = data.find(b"\x0D\x0A", i)
            vals.append(data[i:end])
            i = end + 2
        i += 3
        headers.append((tag[0:1], vals))
    payload_start = i
    payload_chunks = data[i:-4]
    trailer = data[-4:]
    # Parse 130B chunks -> contiguous blocks.
    chunk_size = 130
    data_size = 128
    blocks = []
    encs = []
    expected_addr = None
    cur_start = None
    cur_data = b""
    for j in range(0, len(payload_chunks) - chunk_size + 1, chunk_size):
        addr = (payload_chunks[j] << 12) | (payload_chunks[j + 1] << 4)
        if addr != expected_addr:
            if cur_data:
                blocks.append({"start": cur_start, "length": len(cur_data)})
                encs.append(cur_data)
            cur_start = addr
            cur_data = b""
        cur_data += payload_chunks[j + 2:j + 2 + data_size]
        expected_addr = addr + data_size
    if cur_data:
        blocks.append({"start": cur_start, "length": len(cur_data)})
        encs.append(cur_data)
    # Extract cipher key bytes from the '&' header.
    key = None
    for hid, vals in headers:
        if hid == b"&":
            key = a2b_hex(vals[0])
    return {
        "headers": headers,
        "key": list(key) if key else None,
        "blocks": blocks,
        "encs": encs,
        "payload_start": payload_start,
        "payload_chunks": payload_chunks,
        "trailer": trailer,
    }


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def read_file(fn: str) -> bytes:
    """Read .rwd or .rwd.gz transparently."""
    _f_name, f_ext = os.path.splitext(fn)
    open_fn = gzip.open if f_ext == ".gz" else open
    with open_fn(fn, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(rwd_bytes: bytes) -> str:
    """Return 'x31' (V850) for a supported file, else raise.

    x31: starts 31 0D 0A   (ASCII '1\\r\\n')
    x5a: starts 5A 0D 0A   (ASCII 'Z\\r\\n') - NOT supported by this tool.
    """
    if len(rwd_bytes) < 3:
        raise ValueError("File too short to determine format")
    magic = rwd_bytes[0]
    if magic == 0x31:
        return "x31"
    if magic == 0x5A:
        raise ValueError(
            "This is an x5a (SH-2A) container. This flasher is a self-contained "
            "V850/x31 tool (Honda Accord TVA family) and does not handle x5a. "
            "Use the upstream sunnypilot_eps eps-update.py for SH-2A families "
            "(Civic/Clarity/CR-V/Pilot/Insight)."
        )
    raise ValueError(
        f"Unknown .rwd format: magic byte 0x{magic:02X} "
        "(expected 0x31 for V850/x31)"
    )


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


# ---------------------------------------------------------------------------
# Part-number gate
# ---------------------------------------------------------------------------

def get_x31_supported_parts(parsed: dict) -> List[bytes]:
    """Read the `/` header from an x31 file -> list of supported part-number bytes.

    Used as a part-number-mismatch gate. The SA path for x31 is universal
    (V850 Group-C constants) so without this check an operator could pass a
    Civic-family firmware to an Accord ECU - same SA would succeed, but the
    flash content would be for the wrong vehicle.
    """
    for tag, vals in parsed["headers"]:
        if tag == b"/":
            return list(vals)
    return []


def app_id_matches_part(app_id: bytes, supported_parts: List[bytes]) -> bool:
    """Compare ECU-reported app id against the .rwd's supported part list.

    app_id from DID 0xF181 is typically 16 bytes with trailing NULs (e.g.
    b'39990-TVA-A160\\x00\\x00'). Supported-parts entries are usually the
    ASCII part number without NULs. Strip NULs/whitespace from both sides
    before comparing, and accept a full-string match or a prefix match (some
    Honda parts have a revision suffix the supported list doesn't carry).
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

# Honda's cipher-key DID. The custom sunnypilot_eps panda fork carried this as
# DATA_IDENTIFIER_TYPE.FLASH_DECRYPTION_KEY = 0xF101; the standard opendbc
# uds.py has no such member, so it is pinned here. EVIDENCE: every successful
# flash log in flashing-2020accord/archive/ shows the write on the wire as
# `2E F1 01 BF 10 9E` (output_flash*_20260524.txt), and the firmware's key-
# write handler is documented against 0x2E F101 in
# analysis-2020accord/notes/HOW_TO_BUILD_ACCORD_TVA_RWD.md.
FLASH_DECRYPTION_KEY_DID = 0xF101


class _FallbackUdsEnums:
    """Just the UDS constants the flow uses, for --mock with no library at all.

    Values are the ISO 14229 standard ones and are identical in both
    opendbc.car.uds and the legacy panda.python.uds.
    """
    from enum import IntEnum as _IntEnum

    class SESSION_TYPE(_IntEnum):
        PROGRAMMING = 2
        EXTENDED_DIAGNOSTIC = 3

    class ACCESS_TYPE(_IntEnum):
        REQUEST_SEED = 1
        SEND_KEY = 2

    class ROUTINE_CONTROL_TYPE(_IntEnum):
        START = 1

    class ROUTINE_IDENTIFIER_TYPE(_IntEnum):
        ERASE_MEMORY = 0xFF00
        CHECK_PROGRAMMING_DEPENDENCIES = 0xFF01

    class DATA_IDENTIFIER_TYPE(_IntEnum):
        APPLICATION_SOFTWARE_IDENTIFICATION = 0xF181

    __name__ = "fallback-enums (mock only)"


def import_uds(allow_fallback: bool = False):
    """Import the UDS module from wherever this generation of openpilot keeps it.

    Current openpilot/opendbc: `opendbc.car.uds` (panda/python/uds.py is gone).
    Older panda library:        `panda.python.uds`.
    Returns the module; the enum names used below are identical in both.
    With allow_fallback (mock mode only) a constants-only stand-in is returned
    when neither library is importable.
    """
    try:
        from opendbc.car import uds as uds_mod
        return uds_mod
    except ImportError:
        pass
    try:
        from panda.python import uds as uds_mod  # legacy location
        return uds_mod
    except ImportError:
        if allow_fallback:
            return _FallbackUdsEnums
        raise


def enable_uds_debug_trace(uds_mod) -> None:
    """Make --debug print the ISO-TP / CAN trace on the current library.

    The legacy client took debug=True and printed; opendbc's logs through
    `opendbc.car.carlog` at DEBUG level, which is silent unless the logger is
    turned up and given a handler.
    """
    try:
        import logging
        from opendbc.car.carlog import carlog
        carlog.setLevel(logging.DEBUG)
        if not carlog.handlers:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(logging.Formatter("%(message)s"))
            carlog.addHandler(h)
    except Exception:
        pass


def elm327_safety_mode() -> int:
    """Resolve the ELM327 safety-mode constant across library generations.

    Current: CarParams.SafetyModel.elm327 (opendbc.car.structs).
    Legacy:  Panda.SAFETY_ELM327.
    Both are 3 (opendbc/safety/declarations.h: #define SAFETY_ELM327 3U) and
    set_safety_mode() passes the int straight through to the control write.
    """
    try:
        from opendbc.car.structs import CarParams
        return int(CarParams.SafetyModel.elm327)
    except Exception:
        pass
    try:
        from panda import Panda
        return int(Panda.SAFETY_ELM327)
    except Exception:
        return 3


def _mock_uds_client():
    """Canned UDS client for an offline flow check. NEVER sends CAN traffic."""
    from unittest import mock
    uds_client = mock.MagicMock(name="MockUdsClient")
    # Plausible canned responses so the dry-run flow can execute end-to-end
    uds_client.security_access.return_value = b"\x67\x01\x12\x34"
    uds_client.read_data_by_identifier.return_value = b"39990-TVA-A160\x00\x00"
    uds_client.request_download.return_value = 514
    return uds_client


def get_uds_client(can_addr: int, can_bus: int, debug: bool, danger: bool = False,
                   use_mock: bool = False):
    """Connect to the panda (device-internal over SPI, or a USB red panda).

    `use_mock=True` (the --mock flag) returns a canned client for an offline
    flow check on a machine with no panda - no CAN traffic is ever sent.

    There is deliberately NO silent fallback to the mock: a connect failure
    (pandad still running, USB not attached, ignition off) is FATAL. The old
    behaviour printed "DRY RUN COMPLETE" against a mock when the panda was
    merely busy, which reads as a passed pre-flight when nothing was tested.
    The mock is also refused outright under --danger.
    """
    if use_mock:
        if danger:
            print("[uds] FATAL: --mock cannot be combined with --danger.", file=sys.stderr)
            raise SystemExit(2)
        print("[uds] --mock: using canned UDS client; NO CAN traffic will be sent")
        return _mock_uds_client(), True  # is_mock=True

    # Refuse to race openpilot for the panda.
    running = pandad_running()
    if running:
        print("[uds] FATAL: openpilot/pandad is running and owns the panda:", file=sys.stderr)
        for ln in running:
            print(f"         {ln}", file=sys.stderr)
        print("[uds] On a comma device run `tmux kill-server`, wait ~3 s, then retry.", file=sys.stderr)
        raise SystemExit(2)

    try:
        from panda import Panda
        uds_mod = import_uds()
        if debug:
            enable_uds_debug_trace(uds_mod)
        panda = Panda(disable_checks=True)   # also disables the heartbeat
        #                                     # watchdog + power save, so the
        #                                     # panda stays in ELM327 mode for
        #                                     # the whole multi-minute flash
        hw = panda.get_type()
        serial = panda.get_serial()[0] if hasattr(panda, "get_serial") else "?"
        print(f"[uds] panda connected: type={hw!r} serial={serial} "
              f"transport={'SPI (device-internal)' if getattr(panda, 'spi', False) else 'USB'}")
        try:
            h = panda.health()
            ign = bool(h.get("ignition_line")) or bool(h.get("ignition_can"))
            print(f"[uds] panda health: ignition_line={h.get('ignition_line')} "
                  f"ignition_can={h.get('ignition_can')} voltage={h.get('voltage')} mV "
                  f"-> ignition {'ON' if ign else 'OFF'}")
            if not ign:
                print("[uds] WARNING: panda reports ignition OFF. The EPS will not answer UDS")
                print("[uds]          unless the car is at least in ACC/ignition-on.")
        except Exception as e:
            print(f"[uds] (health read failed: {type(e).__name__}: {e})")
        panda.can_clear(0xFFFF)
        panda.set_safety_mode(elm327_safety_mode())
        import inspect
        kw = {"bus": can_bus}
        if "debug" in inspect.signature(uds_mod.UdsClient.__init__).parameters:
            kw["debug"] = debug          # legacy panda.python.uds only
        uds_client = uds_mod.UdsClient(panda, can_addr, **kw)
        print(f"[uds] Using real panda client, bus={can_bus}, "
              f"addr=0x{can_addr:08X}, uds module={uds_mod.__name__}")
        return uds_client, False  # is_mock=False
    except SystemExit:
        raise
    except Exception as e:
        print(f"[uds] FATAL: could not open the panda ({type(e).__name__}: {e})", file=sys.stderr)
        print("[uds] Checks: comma device -> `tmux kill-server` done? red panda -> USB attached?", file=sys.stderr)
        print("[uds] For an offline flow check with no hardware pass --mock explicitly.", file=sys.stderr)
        if debug:
            traceback.print_exc()
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# Safety confirmation gate
# ---------------------------------------------------------------------------

def confirm_danger(rwd_path: str, bus: int, can_addr: int,
                   skip_prompt: bool, multi_block: bool = False) -> bool:
    """Never flash without naming the firmware file and bus.

    Repeat both back to the operator and require interactive confirmation,
    unless --yes is passed (still requires --danger to reach this point).
    """
    print()
    print("=" * 70)
    print("  DANGER MODE - ABOUT TO MUTATE EPS ECU FLASH")
    print("=" * 70)
    print(f"  Firmware file : {rwd_path}")
    print(f"  Container     : x31 (V850)")
    print(f"  CAN bus       : {bus}")
    print(f"  CAN address   : 0x{can_addr:08X}")
    print()
    print("  Required prerequisites (see ONBOARDING.md / EPS_UPDATE_TVA_README.md):")
    print("    - Car ignition ON (engine off is fine), stay in the car, do not")
    print("      touch the ignition or unplug anything until DONE is printed")
    print("    - comma device: openpilot killed (tmux kill-server) - enforced above")
    print("    - red panda: it is the only device on OBD-II")
    print("    - firmware part-number matches the target car (checked above)")
    print()
    print("  Single-block x31 sequence (cipher key to DID 0xF101, one transfer-exit)")
    print("  has flashed this ECU successfully many times since 2026-05-24.")
    if multi_block:
        print("  UNVERIFIED: MULTI-BLOCK transfer sequence (--allow-multiblock acknowledged)")
    print("  If the flash is interrupted the ECU may end up in an unbootable state.")
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
          force_part_mismatch: bool = False, use_mock: bool = False) -> int:
    """Run the V850/x31 EPS flash workflow.

    Returns process exit code (0 on success, non-zero on failure).
    """
    # Lazy import here so the panda import errors don't crash --help/--selftest.
    uds_mod = import_uds(allow_fallback=use_mock)
    SESSION_TYPE = uds_mod.SESSION_TYPE
    ACCESS_TYPE = uds_mod.ACCESS_TYPE
    ROUTINE_CONTROL_TYPE = uds_mod.ROUTINE_CONTROL_TYPE
    ROUTINE_IDENTIFIER_TYPE = uds_mod.ROUTINE_IDENTIFIER_TYPE
    DATA_IDENTIFIER_TYPE = uds_mod.DATA_IDENTIFIER_TYPE

    print(f"[load] reading {rwd_path}")
    rwd = read_file(rwd_path)
    fmt = detect_format(rwd)  # raises on x5a / unknown
    print(f"[load] detected container format: {fmt} "
          f"({len(rwd)} bytes, magic 0x{rwd[0]:02X})")

    parsed = parse_x31(rwd)
    can_addr = get_can_address_x31(parsed)
    # Surface the supported parts and cipher key for the operator.
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

    print(f"[flash] CAN address resolved to 0x{can_addr:08X}")

    # ---- danger gate, EARLY ----
    if danger:
        multi_block = len(parsed["blocks"]) > 1
        if not confirm_danger(rwd_path, bus, can_addr, skip_prompt,
                              multi_block=multi_block):
            return 1
    else:
        print("[flash] DRY RUN (default) - will stop after SA handshake")

    # ---- UDS client ----
    uds_client, is_mock = get_uds_client(can_addr, bus, debug, danger=danger,
                                         use_mock=use_mock)

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
        # x31 uses the universal V850 SA algorithm so a mismatched part would
        # still SA-succeed. Compare app_id against the `/` header part list and
        # refuse unless --force-part-mismatch is set.
        supported = get_x31_supported_parts(parsed)
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

        key = calculate_tva_session_key(seed_bytes)
        print(f"[sa]  computed key : 0x{key.hex().upper()} "
              f"(via V850 Group-C firmware constants)")

        print("[sa]  sending key (0x27 0x02)")
        data = uds_client.security_access(ACCESS_TYPE.SEND_KEY, key)
        debug_output.append(data)
        print("[sa]  SA handshake succeeded")

        # ---- DRY-RUN STOP POINT ----
        if not danger:
            print()
            print("=" * 70)
            if is_mock:
                print("  MOCK FLOW CHECK COMPLETE - no hardware was touched, nothing proven")
            else:
                print("  DRY RUN COMPLETE - SA handshake succeeded, stopping before flash")
            print("=" * 70)
            print(f"  ECU app ID    : {app_id!r}")
            print(f"  Seed received : 0x{seed_bytes.hex().upper()}")
            print(f"  Key accepted  : 0x{key.hex().upper()}")
            print(f"  Container fmt : {fmt}")
            print(f"  CAN address   : 0x{can_addr:08X}")
            print(f"  Bus           : {bus}")
            print()
            if is_mock:
                print("  Canned responses only. Run WITHOUT --mock on the car to prove")
                print("  the SA handshake before any --danger flash.")
            else:
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
        # raises NegativeResponseError on any 0x7F response, so reaching here
        # means UDS-positive, but log the body for human review.
        print(f"[flash] erase routine_status = {erase_status.hex().upper() if erase_status else '(empty)'}")

        # Heartbeat after erase: erase can take several seconds and the
        # bootloader may have used the entire S3 window.
        uds_client.tester_present()

        # x31 V850: send the cipher key bytes (from `&` header).
        cipher_key = bytes(parsed["key"])
        print(f"[flash] writing firmware decryption key (x31): "
              f"{cipher_key.hex().upper()}")
        data = uds_client.write_data_by_identifier(
            FLASH_DECRYPTION_KEY_DID, cipher_key   # 0x2E F101 on the wire
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
        # Heuristic: many Honda ECUs return 0x00 for "passed". Anything else is
        # suspect. We do NOT auto-abort because vendor codes vary and a false-
        # positive here would be its own brick risk - the operator gets the
        # bytes and decides whether to re-flash.
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
# x31 block transfer
# ---------------------------------------------------------------------------

def _transfer_x31(uds_client, parsed: dict, debug_output: list) -> None:
    """Multi-block x31 transfer. Each block gets its own request_download +
    transfer_data sequence + request_transfer_exit per UDS convention.

    NOTE: this mirrors the upstream single-block pattern extended to N blocks.
    The actual TVA bootloader's exact protocol nuance (whether it wants a
    transfer-exit between blocks vs at the end only) is NOT yet hardware-
    verified - this code path is only executed under --danger and only after
    interactive operator confirmation. First-light --danger run on a real TVA
    ECU should be tightly observed.
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

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def update(self, n):
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Portable Honda EPS flasher with V850/TVA (x31) support",
        epilog=(
            "Defaults to DRY RUN. --danger is required to perform the actual flash, "
            "and requires interactive 'FLASH' confirmation unless --yes is also passed."
        ),
    )
    p.add_argument("rwd", nargs="?", help="Path to .rwd[.gz] firmware file")
    p.add_argument("--bus", type=int,
                   help="CAN bus number. 1 on a comma device on the Accord harness "
                        "(the bus opendbc fingerprints the EPS on) and 1 on a red "
                        "panda on OBD-II.")
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
    p.add_argument("--mock", action="store_true",
                   help="Offline flow check with a canned UDS client: no panda, no CAN "
                        "traffic, proves nothing about the car. Dry-run only; refused "
                        "with --danger. (There is no longer a silent mock fallback.)")
    p.add_argument("--selftest", action="store_true",
                   help="Validate the inlined SA algorithm against the known-good "
                        "vectors and exit (needs no hardware and no panda/tqdm).")
    args = p.parse_args()

    if args.selftest:
        return 0 if _selfcheck_sa() else 1

    if not args.rwd:
        p.error("rwd firmware file is required (unless --selftest)")
    if args.bus is None:
        p.error("--bus is required (unless --selftest)")

    if not os.path.exists(args.rwd):
        print(f"[fatal] firmware file not found: {args.rwd}")
        return 2

    # Echo the firmware path + bus before doing anything else (safety: repeat
    # the name back to the operator before proceeding).
    print(f"[boot] eps-update-tva.py")
    print(f"[boot] firmware file : {args.rwd}")
    print(f"[boot] CAN bus       : {args.bus}")
    print(f"[boot] mode          : "
          f"{'DANGER (will mutate ECU flash)' if args.danger else 'DRY RUN (no mutation)'}"
          f"{' [MOCK - no hardware]' if args.mock else ''}")
    print(f"[boot] python        : {sys.executable}")
    print()

    if not args.mock:
        _bootstrap_env()

    return flash(args.rwd, args.bus, args.danger, args.yes, args.debug,
                 allow_multiblock=args.allow_multiblock,
                 force_part_mismatch=args.force_part_mismatch,
                 use_mock=args.mock)


if __name__ == "__main__":
    sys.exit(main())
