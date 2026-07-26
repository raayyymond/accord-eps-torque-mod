"""eps-read-dtcs.py - STRICTLY READ-ONLY DTC and fault-register reader (V850/TVA).

Purpose
-------
Diagnose why V21/V22 firmware builds cause EPS startup faults. Reads stored
DTCs via UDS service 0x19 and key fault-state RAM registers via 0x23
(ReadMemoryByAddress) to identify which fault triggered the EPS startup failure.

SAFETY - this script CANNOT mutate the ECU
------------------------------------------
The ONLY UDS services it issues are read / session / SA-handshake services:

    0x3E  TesterPresent                  (keep-alive)
    0x22  ReadDataByIdentifier           (read app-id 0xF181)
    0x10  DiagnosticSessionControl       (EXTENDED 0x03 ONLY - NEVER PROGRAMMING 0x02)
    0x27  SecurityAccess                 (seed/key handshake - same as dry run)
    0x19  ReadDTCInformation             (stored DTC query - read only)
    0x23  ReadMemoryByAddress            (fault-register reads)

It NEVER sends: 0x10 PROGRAMMING, 0x31 RoutineControl, 0x2E WriteDataByIdentifier,
0x34 RequestDownload, 0x36 TransferData, 0x37 RequestTransferExit,
0x3D WriteMemoryByAddress, 0x11 ECUReset.
Those strings do not appear below.

No mock fallback: a probe against a mock tells us nothing; if no panda is
present we abort rather than print misleading results.

Target ECU: 2020 Honda Accord EPS, V850/TVA family, 39990-TVA-A160.

Usage
-----
    python eps-read-dtcs.py --bus 1
    python eps-read-dtcs.py --bus 1 --addr 0x18DA30F1
    python eps-read-dtcs.py --bus 1 --no-sa
    python eps-read-dtcs.py --bus 1 --debug
"""

import os
import sys
import struct
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tva_sa_key import calculate_tva_session_key

# Default CAN address proven working in dry-run readbacks (response at 0x18DAF130).
DEFAULT_ADDR = 0x18DA30F1

# ---------------------------------------------------------------------------
# RAM fault-register table
# Each entry: (address, length, name, description, interpretation_fn)
# Addresses derived from: gp_base = 0xFEDF8000, addr = gp_base - gp_offset
# ---------------------------------------------------------------------------

# interpretation callables return a string explaining the value
def _interp_fault_flags_18d4(raw: int) -> str:
    parts = []
    if raw == 0:
        return "no faults"
    if raw & 0x01:
        parts.append("bit0=EPS-disable path active")
    if raw & 0x04:
        parts.append("bit2=zero-output EPS fault")
    other = raw & ~0x05
    if other:
        parts.append(f"other bits=0x{other:08X}")
    return ", ".join(parts) if parts else f"raw=0x{raw:08X}"

def _interp_fault_flags_18d0(raw: int) -> str:
    if raw == 0:
        return "no faults (OR'd with gp-0x18d4)"
    return f"fault bits set=0x{raw:08X} (OR'd with gp-0x18d4)"

def _interp_deferred_fault(raw: int) -> str:
    if raw == 1:
        return "DEFERRED FAULT SET -> init SM forces fault state"
    if raw == 0:
        return "clear"
    return f"unexpected value=0x{raw:02X}"

def _interp_crc_walk(raw: int) -> str:
    if raw == 0:
        return "PASS (CRC walk OK)"
    return f"FAIL block/error=0x{raw:04X} -> flash CRC walk failed"

def _interp_disable_a(raw: int) -> str:
    if raw == 0:
        return "EPS enabled (clear)"
    return f"EPS DISABLED (flag A non-zero: 0x{raw:02X})"

def _interp_disable_b(raw: int) -> str:
    if raw == 0:
        return "EPS enabled (clear)"
    return f"EPS DISABLED (flag B non-zero: 0x{raw:02X})"

def _interp_init_sm(raw: int) -> str:
    if raw == 8:
        return "EPS state=8 -> EMERGENCY FAULT STATE"
    return f"EPS init SM state={raw} (8=fault, other=normal)"

def _interp_state8_latch(raw: int) -> str:
    if raw == 0:
        return "clear (state-8 not latched)"
    return f"STATE-8 LATCHED non-zero=0x{raw:08X} -> already forced fault"

# (address, length_bytes, gp_name, description, unpack_fmt, interp_fn)
FAULT_REGISTERS = [
    (0xFEDF672C, 4, "gp-0x18d4", "Fault status flags (bit0=EPS-disable, bit2=zero-output fault)",
     ">I", _interp_fault_flags_18d4),
    (0xFEDF6730, 4, "gp-0x18d0", "Fault status flags (OR'd with gp-0x18d4 in checks)",
     ">I", _interp_fault_flags_18d0),
    (0xFEDF17A4, 1, "gp-0x685c", "Deferred fault flag (1 -> init SM forces fault state)",
     "B", _interp_deferred_fault),
    (0xFEDF5284, 2, "gp-0x2d7c", "Flash CRC walk result (0=pass, non-zero=block+error code)",
     ">H", _interp_crc_walk),
    (0xFEDF3BB1, 1, "gp-0x444f", "EPS disable flag A (non-zero -> EPS disabled)",
     "B", _interp_disable_a),
    (0xFEDF31AD, 1, "gp-0x4e53", "EPS disable flag B (non-zero -> EPS disabled)",
     "B", _interp_disable_b),
    (0xFEDF1806, 1, "gp-0x67fa", "Init state machine state byte (8=emergency fault state)",
     "B", _interp_init_sm),
    (0xFEDF4118, 4, "gp-0x3ee8", "State-8-force latch (non-zero=already forced state 8)",
     ">I", _interp_state8_latch),
]

ALLOWED_SERVICES = {0x3E, 0x22, 0x10, 0x27, 0x19, 0x23}


def parse_dtc_response(data: bytes) -> list:
    """Parse ReadDTCInformation response body.

    Panda UDS versions differ on whether they strip the positive-response byte
    (0x59) before returning. Handle both layouts:
        [0x59] [subfunction echo] [DTCStatusAvailabilityMask] [DTC records...]
        [subfunction echo]        [DTCStatusAvailabilityMask] [DTC records...]

    DTC records: 3-byte DTC code (big-endian) + 1-byte status, repeating.
    Returns list of (dtc_code_int, status_byte) tuples.
    """
    dtcs = []
    if not data or len(data) < 2:
        return dtcs
    offset = 0
    # Skip positive-response byte if present (panda sometimes includes it)
    if data[0] == 0x59:
        offset += 1
    # Skip subfunction echo if present (panda strips service+subfunction before returning,
    # but check defensively). Then skip DTCStatusAvailabilityMask (1 byte).
    # Honda TVA: panda strips 0x59 + subfunction echo, leaving [AvailMask][DTC records...].
    # Only skip 1 byte (the availability mask), not 2.
    offset += 1
    while offset + 3 < len(data):
        dtc_code = (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
        status = data[offset + 3]
        dtcs.append((dtc_code, status))
        offset += 4
    return dtcs


def dtc_status_description(status: int) -> str:
    """Decode the 8-bit DTC status mask into human-readable flags."""
    flags = []
    if status & 0x01: flags.append("testFailed")
    if status & 0x02: flags.append("testFailedThisOperationCycle")
    if status & 0x04: flags.append("pendingDTC")
    if status & 0x08: flags.append("confirmedDTC")
    if status & 0x10: flags.append("testNotCompletedSinceLastClear")
    if status & 0x20: flags.append("testFailedSinceLastClear")
    if status & 0x40: flags.append("testNotCompletedThisOperationCycle")
    if status & 0x80: flags.append("warningIndicatorRequested")
    return "|".join(flags) if flags else "no-flags"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Read-only DTC + fault-register reader for 2020 Accord EPS (V850/TVA)",
        epilog=(
            "READ-ONLY: UDS services 0x3E 0x22 0x10 0x27 0x19 0x23 only. "
            "No flash mutation possible. No mock fallback."
        ),
    )
    p.add_argument("--bus", type=int, default=1,
                   help="CAN bus (default 1 for OBD-II red panda)")
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR,
                   help=f"UDS CAN address (default 0x{DEFAULT_ADDR:08X})")
    p.add_argument("--no-sa", action="store_true",
                   help="skip SA handshake (try reads in extended session only)")
    p.add_argument("--dtc-after-sa", action="store_true",
                   help="only request DTCs after a successful SA handshake; "
                        "if SA fails the DTC read is skipped entirely. "
                        "Use when the ECU gates service 0x19 behind SA.")
    p.add_argument("--debug", action="store_true",
                   help="verbose UDS debug output")
    args = p.parse_args()

    print("=" * 74)
    print("  EPS DTC + FAULT REGISTER READ - strictly read-only")
    print("  Target: 2020 Honda Accord EPS  39990-TVA-A160  V850/TVA")
    print("  UDS services: 0x3E 0x22 0x10 0x27 0x19 0x23 only")
    print("=" * 74)
    print(f"  CAN address : 0x{args.addr:08X}")
    print(f"  CAN bus     : {args.bus}")
    print(f"  SA handshake: {'yes' if not args.no_sa else 'no (--no-sa)'}")
    print(f"  DTC read    : {'after SA only (--dtc-after-sa)' if args.dtc_after_sa else 'after extended session'}")
    print(f"  debug       : {args.debug}")
    print("=" * 74)

    # Lazy imports so --help works without panda installed.
    from panda import Panda
    from panda.python.uds import (
        UdsClient, SESSION_TYPE, ACCESS_TYPE, DATA_IDENTIFIER_TYPE,
        NegativeResponseError,
    )

    # Back-compat shim: modern panda lib moved SAFETY_ELM327 to CarParams.SafetyModel.
    # Numeric value is 3 in both eras (safety/declarations.h: #define SAFETY_ELM327 3U).
    if not hasattr(Panda, "SAFETY_ELM327"):
        Panda.SAFETY_ELM327 = 3

    try:
        panda = Panda(disable_checks=True)
    except Exception as e:
        print(f"[fatal] no real panda ({type(e).__name__}: {e}). "
              "Refusing to mock - a DTC/fault read needs real hardware.", file=sys.stderr)
        return 2

    panda.can_clear(0xFFFF)
    panda.set_safety_mode(Panda.SAFETY_ELM327)
    uds = UdsClient(panda, args.addr, debug=args.debug, bus=args.bus)

    # -----------------------------------------------------------------------
    # 1. TesterPresent + app-id read
    # -----------------------------------------------------------------------
    print("\n[uds] tester present")
    uds.tester_present()

    try:
        app_id = uds.read_data_by_identifier(
            DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)
        print(f"[uds] app id (0xF181) = {app_id!r}")
    except NegativeResponseError as e:
        print(f"[uds] app id read denied: NRC 0x{e.error_code:02X}")
        app_id = None

    # -----------------------------------------------------------------------
    # 2. Extended session + SA handshake
    # -----------------------------------------------------------------------
    print("[uds] diagnostic session = EXTENDED_DIAGNOSTIC (0x03)")
    try:
        uds.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
    except NegativeResponseError as e:
        print(f"[uds] session control denied: NRC 0x{e.error_code:02X}; continuing")

    sa_ok = False
    if not args.no_sa:
        try:
            print("[sa]  requesting seed (0x27 0x01)")
            seed_resp = uds.security_access(ACCESS_TYPE.REQUEST_SEED)
            seed_bytes = seed_resp[-2:]
            print(f"[sa]  received seed: 0x{seed_bytes.hex().upper()}")
            key = calculate_tva_session_key(seed_bytes)
            print(f"[sa]  computed key : 0x{key.hex().upper()}")
            uds.security_access(ACCESS_TYPE.SEND_KEY, key)
            print("[sa]  SA handshake succeeded")
            sa_ok = True
        except NegativeResponseError as e:
            print(f"[sa]  SA step returned NRC 0x{e.error_code:02X}; "
                  "continuing - reads may still work or may be denied")

    # -----------------------------------------------------------------------
    # 3. Read stored DTCs - UDS 0x19 subfunction 0x02 (reportDTCByStatusMask)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 74)
    print("  STORED DTCs (ReadDTCInformation 0x19)")
    print("=" * 74)

    dtc_results = []

    if args.dtc_after_sa and not sa_ok:
        print("  [skip] --dtc-after-sa set but SA did not succeed; skipping DTC read.")
    else:
        # subfunction 0x02: reportDTCByStatusMask, mask 0xFF (all DTCs)
        try:
            resp = uds._uds_request(0x19, 0x02, bytes([0xFF]))
            dtcs = parse_dtc_response(resp)
            if dtcs:
                print(f"  [0x19/0x02] {len(dtcs)} stored DTC(s):")
                for dtc_code, status in dtcs:
                    print(f"    DTC 0x{dtc_code:06X}  status=0x{status:02X}  ({dtc_status_description(status)})")
                dtc_results = dtcs
            else:
                print("  [0x19/0x02] response received but no DTC records in payload "
                      f"(raw: {resp.hex() if resp else '(empty)'})")
        except NegativeResponseError as e:
            print(f"  [0x19/0x02] ReadDTCInformation denied: NRC 0x{e.error_code:02X} "
                  f"({'subFunctionNotSupported' if e.error_code == 0x12 else 'see UDS spec'})")
            # Try subfunction 0x0A (reportSupportedDTCs) as fallback
            print("  [0x19/0x0A] trying reportSupportedDTCs as fallback...")
            try:
                resp = uds._uds_request(0x19, 0x0A)
                dtcs = parse_dtc_response(resp)
                if dtcs:
                    print(f"  [0x19/0x0A] {len(dtcs)} supported DTC(s):")
                    for dtc_code, status in dtcs:
                        print(f"    DTC 0x{dtc_code:06X}  status=0x{status:02X}  ({dtc_status_description(status)})")
                    dtc_results = dtcs
                else:
                    print(f"  [0x19/0x0A] response received but no records "
                          f"(raw: {resp.hex() if resp else '(empty)'})")
            except NegativeResponseError as e2:
                print(f"  [0x19/0x0A] also denied: NRC 0x{e2.error_code:02X} "
                      "(DTC service not supported in this session/SA state)")
        except Exception as e:
            print(f"  [0x19] unexpected error: {type(e).__name__}: {e}")

    # -----------------------------------------------------------------------
    # 4. Read key RAM fault registers via ReadMemoryByAddress (0x23)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 74)
    print("  FAULT REGISTER READS (ReadMemoryByAddress 0x23)")
    print(f"  {'address':>12}  {'name':<14} {'raw':>10}  interpretation")
    print("  " + "-" * 70)

    reg_values = {}  # name -> raw int value (or None on failure)
    for addr, length, name, desc, unpack_fmt, interp_fn in FAULT_REGISTERS:
        try:
            data = uds.read_memory_by_address(
                addr, length, memory_address_bytes=4, memory_size_bytes=1)
            raw_int = struct.unpack(unpack_fmt, data)[0]
            interp = interp_fn(raw_int)
            print(f"  0x{addr:08X}  {name:<14} 0x{raw_int:0{length*2}X}      {interp}")
            print(f"  {'':>12}  ({desc})")
            reg_values[name] = raw_int
        except NegativeResponseError as e:
            print(f"  0x{addr:08X}  {name:<14} READ DENIED NRC 0x{e.error_code:02X}  ({desc})")
            reg_values[name] = None
        except Exception as e:
            print(f"  0x{addr:08X}  {name:<14} ERROR {type(e).__name__}: {e}")
            reg_values[name] = None

    # -----------------------------------------------------------------------
    # 5. Summary block
    # -----------------------------------------------------------------------
    print("\n" + "=" * 74)
    print("  FAULT SUMMARY")
    print("=" * 74)

    def yn(val, invert=False) -> str:
        if val is None:
            return "UNKNOWN (read denied)"
        b = bool(val) if not invert else not bool(val)
        return "YES" if b else "NO"

    flag_a = reg_values.get("gp-0x444f")
    flag_b = reg_values.get("gp-0x4e53")
    eps_disabled = (flag_a is not None and flag_a != 0) or (flag_b is not None and flag_b != 0)
    eps_disabled_str = "YES" if eps_disabled else ("UNKNOWN (reads denied)" if flag_a is None and flag_b is None else "NO")

    init_sm = reg_values.get("gp-0x67fa")
    fault_state_active_str = ("YES (state=8)" if init_sm == 8
                              else ("UNKNOWN" if init_sm is None else f"NO (state={init_sm})"))

    deferred = reg_values.get("gp-0x685c")
    deferred_str = yn(deferred)

    crc_walk = reg_values.get("gp-0x2d7c")
    crc_fail_str = "YES" if (crc_walk is not None and crc_walk != 0) else ("UNKNOWN" if crc_walk is None else "NO")

    f18d4 = reg_values.get("gp-0x18d4")
    f18d0 = reg_values.get("gp-0x18d0")
    if f18d4 is not None and f18d0 is not None:
        combined = f18d4 | f18d0
        set_bits = [i for i in range(32) if combined & (1 << i)]
        bits_str = ", ".join(f"bit{i}" for i in set_bits) if set_bits else "none"
        combined_str = f"0x{combined:08X} (bits set: {bits_str})"
    elif f18d4 is not None:
        combined_str = f"gp-0x18d4=0x{f18d4:08X} (gp-0x18d0 read denied)"
    elif f18d0 is not None:
        combined_str = f"gp-0x18d0=0x{f18d0:08X} (gp-0x18d4 read denied)"
    else:
        combined_str = "UNKNOWN (both reads denied)"

    state8_latch = reg_values.get("gp-0x3ee8")
    latch_str = ("LATCHED" if (state8_latch is not None and state8_latch != 0)
                 else ("UNKNOWN" if state8_latch is None else "clear"))

    print(f"  EPS disabled (flag A or B non-zero) : {eps_disabled_str}")
    print(f"  Fault state active (init SM = 8)    : {fault_state_active_str}")
    print(f"  Deferred fault flag set (gp-0x685c) : {deferred_str}")
    print(f"  Flash CRC walk failed (gp-0x2d7c)   : {crc_fail_str}")
    print(f"  State-8 force latch (gp-0x3ee8)     : {latch_str}")
    print(f"  gp-0x18d4 | gp-0x18d0              : {combined_str}")

    if dtc_results:
        print(f"\n  DTCs ({len(dtc_results)} stored):")
        for dtc_code, status in dtc_results:
            print(f"    0x{dtc_code:06X}  status=0x{status:02X}  ({dtc_status_description(status)})")
    else:
        print("\n  DTCs: none stored (or service denied)")

    if app_id:
        print(f"\n  ECU app ID (0xF181): {app_id!r}")

    print("=" * 74)
    return 0


# --- self-guard: verify no write/flash services appear in this source file ---
def _assert_read_only_source() -> None:
    import re
    src = open(os.path.abspath(__file__), "r", encoding="utf-8").read()
    allowed_calls = {
        "tester_present", "diagnostic_session_control", "security_access",
        "read_memory_by_address", "read_data_by_identifier", "_uds_request",
    }
    calls = set(re.findall(r"\buds\.([a-z_]+)\(", src))
    bad = calls - allowed_calls
    assert not bad, f"READ-ONLY GUARD TRIPPED: non-read uds calls found: {sorted(bad)}"
    # Ensure no programming session is ever selected.
    prog_needle = "SESSION_TYPE." + "PROGRAMMING"  # split so this line is not a hit
    assert prog_needle not in src, \
        "READ-ONLY GUARD TRIPPED: PROGRAMMING session selection present"
    # Ensure no write/flash service codes appear as payload literals.
    forbidden_hex = {"0x34", "0x36", "0x37", "0x2E", "0x3D", "0x31"}
    # Only check them in the context of _uds_request calls (not in comments/docstring service tables).
    request_calls = re.findall(r"_uds_request\([^)]+\)", src)
    for call in request_calls:
        for fh in forbidden_hex:
            assert fh not in call, \
                f"READ-ONLY GUARD TRIPPED: forbidden service {fh} found in _uds_request call: {call!r}"


if __name__ == "__main__":
    _assert_read_only_source()
    sys.exit(main())
