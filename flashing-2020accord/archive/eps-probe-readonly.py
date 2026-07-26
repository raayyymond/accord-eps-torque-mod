"""eps-probe-readonly.py - STRICTLY READ-ONLY EPS state probe (V850/TVA).

Purpose
-------
After the v6 flash attempt erased the application region and crashed at
request_download, this script confirms *exactly* which flash regions were
erased vs. survived, and whether the bootloader's UDS read path is alive.
It answers "what got erased?" empirically by sampling the flash map.

SAFETY - this script CANNOT mutate the ECU
------------------------------------------
The ONLY UDS services it issues are read / session / SA-handshake services:

    0x3E  TesterPresent                  (keep-alive)
    0x22  ReadDataByIdentifier           (read app-id 0xF181)
    0x10  DiagnosticSessionControl       (EXTENDED only - NEVER PROGRAMMING)
    0x27  SecurityAccess                 (seed/key handshake - same as dry run)
    0x31 0x03  RoutineControl/REQUEST_RESULTS  (query erase routine result)
    0x23  ReadMemoryByAddress            (sample flash bytes)

It NEVER sends: 0x10 PROGRAMMING, 0x31 0x01/0x02 (start/stop routine),
0x2E WriteDataByIdentifier, 0x34 RequestDownload, 0x36 TransferData,
0x37 RequestTransferExit, 0x3D WriteMemoryByAddress, 0x11 ECUReset.
Those names do not appear below. See ALLOWED_SERVICES / the grep at bottom.

No mock fallback: a probe against a mock tells us nothing, so if the panda
isn't present we abort rather than print misleading "results".

Usage
-----
    python eps-probe-readonly.py --bus 1
    python eps-probe-readonly.py --bus 1 --addr 0x18DA30F1 --size 16
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tva_sa_key import calculate_tva_session_key  # V850 SA (read-path enabler)

# Default CAN address: the comma/red-panda target proven working in the
# dry-run readback (response seen at 0x18DAF130). Override with --addr.
DEFAULT_ADDR = 0x18DA30F1

# Flash map probe points, from analysis-2020accord/V850_STOCK_RWD_ANALYSIS.md
# section 3. "expect" is what a HEALTHY (un-erased) ECU should show, so the
# operator can read the erase boundary at a glance.
#   PROTECTED  = bootloader/descriptor, should NEVER erase
#   APP        = application code/identity, the suspected erased region
#   FILLER     = 0xFF even in stock (already-erased gap)
#   DATAFLASH  = EEPROM/calibration band, should survive a code-flash erase
PROBES = [
    (0x00000000, "PROTECTED", "vector table - 'jr' entries (xx xx 80 07)"),
    (0x00005AF8, "PROTECTED", "boot sw-id 'DV850T05xxxxxV104'"),
    (0x00009000, "PROTECTED", "boot descriptor - cal-id + part #s A110/A160"),
    (0x00012FF0, "APP",       "app identity - 'A1B_A00...', 'Honda_TVAA_Limphome', A160"),
    (0x00014000, "APP",       "application code START (boot jumps to 0x14084)"),
    (0x00014109, "APP",       "app-start part-number copy"),
    (0x00040000, "APP",       "mid application code"),
    (0x0008B000, "APP",       "near end of real code (last fn ~0x86242)"),
    (0x0008B218, "FILLER",    "code end - stock is 0xFF from here"),
    (0x000B7000, "DATAFLASH", "DAQ/measurement meta ('StimEventDAQ', RAM ptrs)"),
    (0x000C4000, "DATAFLASH", "calibration floats (0.1,0.8,1.0,2.0,8.0)"),
    (0x000CD000, "DATAFLASH", "variant/log records 'TVAA05360Y'"),
    (0x000FFFF0, "DATAFLASH", "last 16 bytes of 1 MB flash"),
]

ALLOWED_SERVICES = {0x3E, 0x22, 0x10, 0x27, 0x31, 0x23}  # read/session/SA only


def classify(data: bytes) -> str:
    """Label a sampled block as erased-blank vs programmed."""
    if data is None or len(data) == 0:
        return "no-data"
    if all(b == 0xFF for b in data):
        return "ERASED (all 0xFF)"
    if all(b == 0x00 for b in data):
        return "all 0x00"
    return "PROGRAMMED (has content)"


def ascii_preview(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only EPS flash-state probe (V850/TVA)")
    p.add_argument("--bus", type=int, required=True, help="CAN bus (1 for OBD-II red panda)")
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR,
                   help=f"UDS CAN address (default 0x{DEFAULT_ADDR:08X})")
    p.add_argument("--size", type=int, default=16, help="bytes to read per probe (default 16)")
    p.add_argument("--no-sa", action="store_true",
                   help="skip the SA handshake (try reads in extended session only)")
    args = p.parse_args()

    print("=" * 70)
    print("  EPS READ-ONLY PROBE - no flash mutation is possible from this script")
    print("=" * 70)
    print(f"  CAN address : 0x{args.addr:08X}")
    print(f"  CAN bus     : {args.bus}")
    print(f"  read size   : {args.size} bytes/probe")
    print("=" * 70)

    # Lazy imports so --help works without panda installed.
    from panda import Panda
    from panda.python.uds import (
        UdsClient, SESSION_TYPE, ACCESS_TYPE, DATA_IDENTIFIER_TYPE,
        ROUTINE_CONTROL_TYPE, ROUTINE_IDENTIFIER_TYPE, NegativeResponseError,
    )

    if not hasattr(Panda, "SAFETY_ELM327"):
        Panda.SAFETY_ELM327 = 3
    try:
        panda = Panda(disable_checks=True)
    except Exception as e:
        print(f"[fatal] no real panda ({type(e).__name__}: {e}). "
              "Refusing to mock - a probe needs real hardware.", file=sys.stderr)
        return 2
    panda.can_clear(0xFFFF)
    panda.set_safety_mode(Panda.SAFETY_ELM327)
    uds = UdsClient(panda, args.addr, debug=True, bus=args.bus)

    print("\n[probe] tester present")
    uds.tester_present()

    # --- app id (the A160->A110 fallback signal) ---
    try:
        app_id = uds.read_data_by_identifier(
            DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)
        print(f"[probe] app id (0xF181) = {app_id!r}")
    except NegativeResponseError as e:
        print(f"[probe] app id read denied: {e} (NRC 0x{e.error_code:02X})")

    # --- enter EXTENDED (never PROGRAMMING) + SA so ReadMemoryByAddress is allowed ---
    if not args.no_sa:
        try:
            print("[probe] diagnostic session = EXTENDED (0x03)")
            uds.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
            print("[probe] security access: request seed")
            seed = uds.security_access(ACCESS_TYPE.REQUEST_SEED)[-2:]
            key = calculate_tva_session_key(seed)
            print(f"[probe] seed=0x{seed.hex().upper()} -> key=0x{key.hex().upper()}")
            uds.security_access(ACCESS_TYPE.SEND_KEY, key)
            print("[probe] SA handshake succeeded")
        except NegativeResponseError as e:
            print(f"[probe] session/SA step returned: {e} (NRC 0x{e.error_code:02X}); "
                  "continuing - reads may still work or may be denied")

    # --- ask the ECU for the erase routine's result (best effort) ---
    try:
        res = uds.routine_control(ROUTINE_CONTROL_TYPE.REQUEST_RESULTS,
                                  ROUTINE_IDENTIFIER_TYPE.ERASE_MEMORY)
        print(f"[probe] erase-routine REQUEST_RESULTS (0xFF00) = "
              f"{res.hex().upper() if res else '(empty)'}")
    except NegativeResponseError as e:
        print(f"[probe] REQUEST_RESULTS denied: {e} (NRC 0x{e.error_code:02X}) "
              "- expected if not in programming session")

    # --- the flash map sweep ---
    print("\n" + "=" * 70)
    print("  FLASH MAP SWEEP (ReadMemoryByAddress 0x23)")
    print("=" * 70)
    print(f"  {'address':>10}  {'expect':<10} {'observed':<26} bytes")
    print("  " + "-" * 64)
    results = []
    for addr, expect, desc in PROBES:
        try:
            data = uds.read_memory_by_address(addr, args.size,
                                              memory_address_bytes=4, memory_size_bytes=1)
            label = classify(data)
            print(f"  0x{addr:08X}  {expect:<10} {label:<26} {data.hex()}")
            print(f"  {'':>10}  {'':<10} {'':<26} |{ascii_preview(data)}|  ({desc})")
            results.append((addr, expect, label))
        except NegativeResponseError as e:
            print(f"  0x{addr:08X}  {expect:<10} READ DENIED NRC 0x{e.error_code:02X}  ({desc})")
            results.append((addr, expect, f"denied NRC 0x{e.error_code:02X}"))

    # --- verdict ---
    print("\n" + "=" * 70)
    print("  INTERPRETATION")
    print("=" * 70)
    app = [r for r in results if r[1] == "APP"]
    prot = [r for r in results if r[1] == "PROTECTED"]
    df = [r for r in results if r[1] == "DATAFLASH"]
    erased_app = [r for r in app if r[2].startswith("ERASED")]
    if erased_app and any("PROGRAMMED" in r[2] for r in prot):
        print("  -> APP region reads ERASED while PROTECTED bootloader survives:")
        print("     confirms the unscoped eraseMemory wiped the application only.")
        print("     Recovery = reflash a COMPLETE app image to 0x14000 (the v2 stock),")
        print("     NOT v6. Consider HDS/iHDS if the UDS code-region download is refused.")
    if any("denied" in r[2] for r in app):
        print("  -> some reads were denied: ReadMemoryByAddress may need programming")
        print("     session/SA on this ECU. The app-id fallback (A160->A110) is then")
        print("     the primary erase signal. Do NOT enter programming session to probe.")
    if df and all(r[2].startswith("PROGRAMMED") for r in df):
        print("  -> DATAFLASH/EEPROM band (incl. 0xC4000) intact - calibration survived.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
