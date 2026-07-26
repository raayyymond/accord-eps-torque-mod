"""eps-read-cal-precise.py - STRICTLY READ-ONLY targeted calibration reader (V850/TVA).

WHAT THIS IS FOR
----------------
The LKAS-torque high-end ceiling on the 2020 Accord EPS (39990-TVA-A160) is set by
the arbitration OUTPUT stage: a Q15 gain at tp+0x746c (= flash 0x000FF46C) and a
symmetric output clamp at +/-tp+0x71b4 (= flash 0x000FF1B4). In the code.bin/data.bin
image we have in Ghidra, the whole tp-relative scalar-cal sub-sector (0x000FF000+)
reads erased (0xFF). A 0xFFFF gain would zero/invert LKAS, yet the car steers fine -
so the RUNNING ECU's copy of that sector is programmed and our dump's is blank.
This script reads those exact bytes off the LIVE ECU so we can compute the 2x edit.

It reads a curated short list of scalar addresses plus a couple of known-PROGRAMMED
control addresses (boot descriptor, arb curve table) so you can tell at a glance
whether the read path works AND whether the cal sub-sector is genuinely blank.

SAFETY - this script cannot mutate the ECU
-------------------------------------------
The ONLY UDS services it can issue are read / session / SA-handshake services:

    0x3E  TesterPresent                (keep-alive)
    0x10  DiagnosticSessionControl     (EXTENDED 0x03 ONLY - never PROGRAMMING 0x02)
    0x27  SecurityAccess               (seed/key handshake; read-path enabler)
    0x23  ReadMemoryByAddress          (the read)
    0x22  ReadDataByIdentifier         (DID fallback if 0x23 is refused)

It NEVER issues, and the strings do not appear below: 0x34 RequestDownload,
0x35 RequestUpload, 0x36 TransferData, 0x37 RequestTransferExit,
0x3D WriteMemoryByAddress, 0x2E WriteDataByIdentifier, 0x31 RoutineControl,
0x11 ECUReset, 0x10 PROGRAMMING.

NOTE on service support (decoded from firmware UDS table @0x9330): the BOOTLOADER
dispatcher lists 0x10,0x11,0x19,0x22,0x27,0x28,0x31,0x34,0x36,0x37,0x2E,0x3E,0x85 -
it does NOT list 0x23 ReadMemoryByAddress. The APPLICATION dispatcher (extended
session, engine of normal diagnostics) may still support 0x23; this script tries it
empirically and, if it is refused (NRC 0x11 serviceNotSupported), falls back to a
ReadDataByIdentifier (0x22) sweep. Expect 0x23 to possibly come back denied.

CONFIRM-BEFORE-SEND
-------------------
By default this is a DRY RUN: it prints every exact UDS payload it would transmit and
sends NOTHING. Review the bytes, then re-run with --send to actually transmit. Kill
openpilot/pandad first (e.g. `tmux kill-server` on a comma device) or the bus will fight.

Usage
-----
    python eps-read-cal-precise.py --bus 1                 # dry run: print payloads only
    python eps-read-cal-precise.py --bus 1 --send          # actually read (after review)
    python eps-read-cal-precise.py --bus 1 --send --no-sa  # try without SA (extended only)
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tva_sa_key import calculate_tva_session_key  # verified V850 SA seed->key

# Physical-addressing CAN id proven in the dry-run readback (response at 0x18DAF130).
DEFAULT_ADDR = 0x18DA30F1

# Curated read list: (flash_address, size, label).
# The two prime targets first, then the clamp/gain neighbourhood, then known-PROGRAMMED
# control reads so a working read path is distinguishable from a blank sector.
TARGETS = [
    (0x000FF46C, 2,  "ARB Q15 GAIN          tp+0x746c   *** prime target ***"),
    (0x000FF1B4, 2,  "ARB OUTPUT CLAMP      tp+0x71b4   *** prime target ***"),
    (0x000FF1B2, 2,  "limit_and_pack clamp  tp+0x71b2"),
    (0x000FF1B6, 2,  "arb clamp sibling     tp+0x71b6"),
    (0x000FF1B8, 2,  "arb clamp sibling     tp+0x71b8"),
    (0x000FF158, 2,  "current-limit fallbk  tp+0x7158"),
    (0x000FF202, 2,  "governor slew init    tp+0x7202"),
    (0x000FF1B0, 16, "window around clamps  tp+0x71b0..0x71bf"),
    (0x000FF460, 16, "window around gain    tp+0x7460..0x746f"),
    # --- known PROGRAMMED control reads (sanity: does the read path work at all?) ---
    (0x00009000, 16, "CTRL: boot descriptor (should be PROGRAMMED)"),
    (0x000E4180, 16, "CTRL: arb LERP curve cb844[0] (should be PROGRAMMED ~15360)"),
]

# DID fallback sweep if 0x23 is refused. These are guesses; ReadDataByIdentifier only
# returns predefined identifiers, so this is a best-effort probe for a cal-exposing DID.
DID_SWEEP = [0xF181, 0xF190, 0xF18C, 0xF1A0, 0xF1A1, 0xF1A2, 0x0100, 0x0110, 0x4900, 0x4901]

ALLOWED_SERVICES = {0x3E, 0x10, 0x27, 0x23, 0x22}  # read / session / SA only


def alfid(addr_bytes: int, size_bytes: int) -> int:
    """addressAndLengthFormatIdentifier: high nibble = #size bytes, low = #addr bytes."""
    return ((size_bytes & 0xF) << 4) | (addr_bytes & 0xF)


def rmba_payload(addr: int, size: int, addr_bytes: int = 4, size_bytes: int = 1) -> bytes:
    """Build the exact 0x23 ReadMemoryByAddress request payload (for printing)."""
    return (bytes([0x23, alfid(addr_bytes, size_bytes)])
            + addr.to_bytes(addr_bytes, "big")
            + size.to_bytes(size_bytes, "big"))


def classify(data: bytes) -> str:
    if not data:
        return "no-data"
    if all(b == 0xFF for b in data):
        return "ERASED (all 0xFF)"
    if all(b == 0x00 for b in data):
        return "all 0x00"
    return "PROGRAMMED"


def print_plan(addr: int, send: bool, use_sa: bool) -> None:
    print("=" * 74)
    print("  EPS PRECISE CALIBRATION READ - read-only (0x23 / 0x22 / session / SA)")
    print("=" * 74)
    print(f"  CAN address : 0x{addr:08X}")
    print(f"  mode        : {'SEND (will transmit)' if send else 'DRY RUN (prints payloads, sends nothing)'}")
    print(f"  SA handshake: {'yes (0x27 seed/key)' if use_sa else 'no (--no-sa)'}")
    print("=" * 74)
    print("  Exact UDS request payloads that WOULD be sent (in order):")
    print("    3E 00                          TesterPresent")
    if use_sa:
        print("    10 03                          DiagnosticSessionControl EXTENDED")
        print("    27 01                          SecurityAccess RequestSeed")
        print("    27 02 <KH> <KL>                SecurityAccess SendKey (key computed from seed)")
    for a, sz, label in TARGETS:
        print(f"    {rmba_payload(a, sz).hex(' ').upper():<30} ReadMemoryByAddress 0x{a:08X} [{sz}]  {label}")
    print("=" * 74)
    if not send:
        print("  DRY RUN: nothing was transmitted. Re-run with --send to read for real.")
        print("  (Kill openpilot/pandad first so it does not contend for the bus.)")
        print("=" * 74)


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only precise EPS calibration reader (V850/TVA)")
    p.add_argument("--bus", type=int, required=True, help="CAN bus (1 for OBD-II red panda)")
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR,
                   help=f"UDS CAN address (default 0x{DEFAULT_ADDR:08X})")
    p.add_argument("--send", action="store_true",
                   help="actually transmit (default is dry-run that only prints payloads)")
    p.add_argument("--no-sa", action="store_true", help="skip SA handshake (extended session only)")
    args = p.parse_args()

    use_sa = not args.no_sa
    print_plan(args.addr, args.send, use_sa)
    if not args.send:
        return 0

    # --- real transmit path ---
    from panda import Panda
    from panda.python.uds import (
        UdsClient, SESSION_TYPE, ACCESS_TYPE, NegativeResponseError,
    )

    if not hasattr(Panda, "SAFETY_ELM327"):
        Panda.SAFETY_ELM327 = 3
    try:
        panda = Panda(disable_checks=True)
    except Exception as e:
        print(f"[fatal] no real panda ({type(e).__name__}: {e}). Refusing to mock.", file=sys.stderr)
        return 2
    panda.can_clear(0xFFFF)
    panda.set_safety_mode(Panda.SAFETY_ELM327)
    uds = UdsClient(panda, args.addr, debug=True, bus=args.bus)

    print("\n[tx] 3E 00  TesterPresent")
    uds.tester_present()

    if use_sa:
        try:
            print("[tx] 10 03  DiagnosticSessionControl EXTENDED")
            uds.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
            print("[tx] 27 01  SecurityAccess RequestSeed")
            seed = uds.security_access(ACCESS_TYPE.REQUEST_SEED)[-2:]
            key = calculate_tva_session_key(seed)
            print(f"[tx] 27 02 {key.hex(' ').upper()}  SendKey (seed=0x{seed.hex().upper()})")
            uds.security_access(ACCESS_TYPE.SEND_KEY, key)
            print("[ok] SA handshake succeeded")
        except NegativeResponseError as e:
            print(f"[warn] session/SA returned NRC 0x{e.error_code:02X}; continuing (reads may be denied)")

    print("\n" + "=" * 74)
    print(f"  {'address':>10}  {'observed':<18} bytes / ascii")
    print("  " + "-" * 70)
    denied_23 = False
    for a, sz, label in TARGETS:
        try:
            data = uds.read_memory_by_address(a, sz, memory_address_bytes=4, memory_size_bytes=1)
            ascii_prev = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            print(f"  0x{a:08X}  {classify(data):<18} {data.hex(' ')}  |{ascii_prev}|")
            print(f"  {'':>10}  {'':<18} {label}")
        except NegativeResponseError as e:
            print(f"  0x{a:08X}  READ DENIED NRC 0x{e.error_code:02X}  {label}")
            if e.error_code == 0x11:
                denied_23 = True

    if denied_23:
        print("\n[fallback] 0x23 refused (serviceNotSupported). Trying ReadDataByIdentifier 0x22 sweep:")
        for did in DID_SWEEP:
            try:
                d = uds.read_data_by_identifier(did)
                print(f"  DID 0x{did:04X} -> {d.hex(' ')}  |{''.join(chr(b) if 32<=b<127 else '.' for b in d)}|")
            except NegativeResponseError as e:
                print(f"  DID 0x{did:04X} -> NRC 0x{e.error_code:02X}")

    print("\n" + "=" * 74)
    print("  INTERPRETATION")
    print("  - If the CTRL reads (0x9000, 0xE4180) are PROGRAMMED but 0xFF46C/0xFF1B4 read")
    print("    0xFF, the read path works and the cal sub-sector really is blank on this ECU.")
    print("  - If 0xFF46C/0xFF1B4 come back PROGRAMMED, those bytes are the stock gain/clamp:")
    print("    GAIN is signed Q15 (>>15); CLAMP is unsigned magnitude. Send them to me and")
    print("    I will compute the exact 2x edit.")
    print("  - If ALL reads are denied NRC 0x11, this ECU has no arbitrary-read service in")
    print("    this session; we need the cal from a full dump or the HDS/iHDS cal tool.")
    print("=" * 74)
    return 0


# --- self-guard: every uds.<method> call in this file must be in the read-only set ---
def _assert_read_only_source() -> None:
    import re
    src = open(os.path.abspath(__file__), "r", encoding="utf-8").read()
    allowed = {"tester_present", "diagnostic_session_control", "security_access",
               "read_memory_by_address", "read_data_by_identifier"}
    calls = set(re.findall(r"\buds\.([a-z_]+)\(", src))
    bad = calls - allowed
    assert not bad, f"READ-ONLY GUARD TRIPPED: non-read uds calls present: {sorted(bad)}"
    # Programming session must never be selected (extended 0x03 only).
    prog_needle = "SESSION_TYPE." + "PROGRAMMING"  # built from parts so this line isn't a hit
    assert prog_needle not in src, \
        "READ-ONLY GUARD TRIPPED: programming-session selection present"


if __name__ == "__main__":
    _assert_read_only_source()
    sys.exit(main())
