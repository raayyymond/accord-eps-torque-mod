"""eps-read-flash-bulk.py - STRICTLY READ-ONLY bulk flash/data-flash reader (V850/TVA).

WHAT THIS IS FOR
----------------
Companion to eps-read-cal-precise.py. Where that script reads a handful of exact
scalar addresses, this one bulk-dumps an entire region to a .bin so we can recover
the whole calibration sub-sector at once (and diff it against the erased copy in our
Ghidra image). Two ways to pull it, because we don't yet know which the ECU permits:

  (A) CHUNKED ReadMemoryByAddress (0x23)   - default. Many small reads, looped.
  (B) RequestUpload (0x35) + TransferData  - optional (--upload). The read-direction
      twin of the firmware DOWNLOAD: one RequestUpload with a specific addr+size, then
      stream the blocks back. This is the "like the firmware download did, but reading"
      path. 0x35 is NOT in the bootloader service table (decoded @0x9330), so it may be
      refused - but it is read-only and worth an empirical try.

REGIONS (preset via --region, or explicit --start/--size):
  calib      0x000F8000 .. 0x00100000   (32 KB code-flash scalar-cal sub-sector; holds
                                          the arb gain 0xFF46C + clamp 0xFF1B4)   [default]
  window     0x000FF000 .. 0x00100000   (4 KB just around the gain/clamp - fast/targeted,
                                          matches the "very specific offset+size" idea)
  dataflash  0x02000000 .. 0x02008000   (32 KB V850 data-flash / adaptation EEPROM)

SAFETY - this script cannot mutate the ECU
-------------------------------------------
Services it may issue: 0x3E TesterPresent, 0x10 DiagnosticSessionControl (EXTENDED 0x03
ONLY), 0x27 SecurityAccess, 0x23 ReadMemoryByAddress, and - only under --upload -
0x35 RequestUpload / 0x36 TransferData / 0x37 RequestTransferExit, which in UPLOAD
context are READ-direction (the tester sends only a block counter, the ECU returns data).

It NEVER issues 0x34 RequestDownload, 0x3D WriteMemoryByAddress, 0x2E WriteDataByIdentifier,
0x31 RoutineControl, 0x11 ECUReset, and never selects the PROGRAMMING session. 0x36/0x37
are sent ONLY after a positive 0x35 RequestUpload reply; without a preceding 0x34 they
cannot write. A self-guard at the bottom enforces the call whitelist.

CONFIRM-BEFORE-SEND
-------------------
DRY RUN by default: prints the exact payloads (first/last chunk + count, and the upload
request) and sends NOTHING. Re-run with --send to transmit. Kill openpilot/pandad first.

Usage
-----
    python eps-read-flash-bulk.py --bus 1                          # dry run, calib region
    python eps-read-flash-bulk.py --bus 1 --region window          # dry run, 4KB window
    python eps-read-flash-bulk.py --bus 1 --region calib --send    # real chunked 0x23 dump
    python eps-read-flash-bulk.py --bus 1 --region calib --send --upload   # try 0x35 path too
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_ANALYSIS_DIR = os.path.join(os.path.dirname(_HERE), "analysis-2020accord")
if _ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, _ANALYSIS_DIR)

from tva_sa_key import calculate_tva_session_key
from firmware_paths import other_bin_path

DEFAULT_ADDR = 0x18DA30F1

REGIONS = {
    "calib":     (0x000F8000, 0x8000),
    "window":    (0x000FF000, 0x1000),
    "dataflash": (0x02000000, 0x8000),
}


def alfid(addr_bytes: int, size_bytes: int) -> int:
    return ((size_bytes & 0xF) << 4) | (addr_bytes & 0xF)


def rmba_payload(addr: int, size: int) -> bytes:
    return bytes([0x23, alfid(4, 1)]) + addr.to_bytes(4, "big") + size.to_bytes(1, "big")


def upload_payload(addr: int, size: int) -> bytes:
    # 0x35 RequestUpload: dataFormatIdentifier(0x00) + ALFID(4-addr,4-size) + addr + size
    return bytes([0x35, 0x00, alfid(4, 4)]) + addr.to_bytes(4, "big") + size.to_bytes(4, "big")


def classify(data: bytes) -> str:
    if not data:
        return "no-data"
    if all(b == 0xFF for b in data):
        return "ERASED"
    if all(b == 0x00 for b in data):
        return "ZERO"
    return "PROGRAMMED"


def print_plan(addr, start, size, chunk, use_sa, send, upload, out):
    n = (size + chunk - 1) // chunk
    print("=" * 78)
    print("  EPS BULK FLASH READ - read-only (chunked 0x23" + (" + 0x35 upload" if upload else "") + ")")
    print("=" * 78)
    print(f"  CAN address : 0x{addr:08X}")
    print(f"  region      : 0x{start:08X} .. 0x{start + size:08X}  ({size} bytes)")
    print(f"  chunk       : {chunk} bytes  ->  {n} ReadMemoryByAddress requests")
    print(f"  output file : {out}")
    print(f"  SA handshake: {'yes' if use_sa else 'no'}")
    print(f"  upload path : {'WILL ATTEMPT 0x35/0x36 after chunked 0x23' if upload else 'no (chunked 0x23 only)'}")
    print(f"  mode        : {'SEND (will transmit)' if send else 'DRY RUN (prints payloads, sends nothing)'}")
    print("=" * 78)
    print("  Session/SA payloads (if --sa): 3E 00 | 10 03 | 27 01 | 27 02 <KH><KL>")
    print("  First chunk : " + rmba_payload(start, min(chunk, 0xFF)).hex(" ").upper())
    last_addr = start + (n - 1) * chunk
    last_sz = min(chunk, size - (n - 1) * chunk, 0xFF)
    print(f"  Last  chunk : " + rmba_payload(last_addr, last_sz).hex(" ").upper())
    print(f"  ... {n} chunked reads total, addr stepping by {chunk} ...")
    if upload:
        print("  Upload req  : " + upload_payload(start, size).hex(" ").upper()
              + "   then 36 01 / 36 02 / ... / 37 (read blocks)")
    print("=" * 78)
    if not send:
        print("  DRY RUN: nothing transmitted. Re-run with --send. Kill openpilot/pandad first.")
        print("=" * 78)


def main() -> int:
    p = argparse.ArgumentParser(description="Read-only bulk EPS flash/data-flash reader (V850/TVA)")
    p.add_argument("--bus", type=int, required=True)
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR)
    p.add_argument("--region", choices=sorted(REGIONS), default="calib")
    p.add_argument("--start", type=lambda s: int(s, 0), help="override region start address")
    p.add_argument("--size", type=lambda s: int(s, 0), help="override region size (bytes)")
    p.add_argument("--chunk", type=lambda s: int(s, 0), default=0x80, help="bytes per 0x23 read (<=255)")
    p.add_argument("--out", help="output .bin path (default derived from region)")
    p.add_argument("--send", action="store_true", help="actually transmit (default dry-run)")
    p.add_argument("--no-sa", action="store_true", help="skip SA handshake")
    p.add_argument("--upload", action="store_true",
                   help="ALSO try RequestUpload(0x35)/TransferData(0x36) read path (experimental)")
    args = p.parse_args()

    start, size = REGIONS[args.region]
    if args.start is not None:
        start = args.start
    if args.size is not None:
        size = args.size
    chunk = max(1, min(args.chunk, 0xFF))
    use_sa = not args.no_sa
    out = args.out or str(other_bin_path(f"eps-dump-{args.region}-0x{start:08X}-{size:#x}.bin"))

    print_plan(args.addr, start, size, chunk, use_sa, args.send, args.upload, out)
    if not args.send:
        return 0

    from panda import Panda
    from panda.python.uds import (
        UdsClient, SESSION_TYPE, ACCESS_TYPE, SERVICE_TYPE, NegativeResponseError,
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
    uds = UdsClient(panda, args.addr, debug=False, bus=args.bus)

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
            print(f"[warn] session/SA NRC 0x{e.error_code:02X}; continuing")

    # --- (A) chunked ReadMemoryByAddress 0x23 ---
    print("\n" + "=" * 78)
    print("  (A) CHUNKED ReadMemoryByAddress 0x23")
    print("=" * 78)
    buf = bytearray()
    addr = start
    ok = 0
    denied = 0
    first_nrc = None
    while addr < start + size:
        this = min(chunk, start + size - addr)
        try:
            data = uds.read_memory_by_address(addr, this, memory_address_bytes=4, memory_size_bytes=1)
            buf += data
            ok += 1
            if ok <= 4 or classify(data) != "ERASED":
                print(f"  0x{addr:08X} +{this:<3} {classify(data):<11} {data[:16].hex(' ')}"
                      + (" ..." if len(data) > 16 else ""))
        except NegativeResponseError as e:
            denied += 1
            first_nrc = first_nrc if first_nrc is not None else e.error_code
            buf += b"\xFF" * this  # placeholder so file offsets stay aligned
            if denied <= 2:
                print(f"  0x{addr:08X} +{this:<3} DENIED NRC 0x{e.error_code:02X}")
            if denied == 3 and ok == 0:
                print("  ... (0x23 appears unsupported in this session; stopping chunked sweep)")
                break
        addr += this

    if ok:
        with open(out, "wb") as f:
            f.write(buf)
        prog = sum(1 for i in range(0, len(buf), 16) if any(b != 0xFF for b in buf[i:i + 16]))
        print(f"\n  wrote {len(buf)} bytes -> {out}  ({ok} reads ok, {denied} denied, "
              f"{prog} non-erased 16B rows)")
    else:
        print(f"\n  chunked 0x23 produced no data (first NRC 0x{(first_nrc or 0):02X}). "
              "Try --upload, or the cal needs HDS/iHDS.")

    # --- (B) optional RequestUpload 0x35 / TransferData 0x36 (read-direction) ---
    if args.upload:
        print("\n" + "=" * 78)
        print("  (B) RequestUpload 0x35 + TransferData 0x36 (experimental read path)")
        print("=" * 78)
        try:
            req = bytes([0x00, alfid(4, 4)]) + start.to_bytes(4, "big") + size.to_bytes(4, "big")
            print(f"[tx] 35 {req.hex(' ').upper()}  RequestUpload 0x{start:08X} size {size:#x}")
            resp = uds._uds_request(SERVICE_TYPE.REQUEST_UPLOAD, subfunction=None, data=req)
            print(f"[ok] RequestUpload accepted, lengthFormat/maxBlock = {resp.hex(' ').upper()}")
            up = bytearray()
            seq = 1
            while len(up) < size:
                blk = uds.transfer_data(seq & 0xFF)  # upload: returns a data block
                if not blk:
                    break
                up += blk
                seq += 1
                if seq > size:  # hard stop guard
                    break
            uds.request_transfer_exit()
            upout = out.replace(".bin", "-upload.bin")
            with open(upout, "wb") as f:
                f.write(up)
            print(f"[ok] upload read {len(up)} bytes -> {upout}")
        except NegativeResponseError as e:
            print(f"[info] upload path refused: NRC 0x{e.error_code:02X} "
                  "(expected - 0x35 not in the bootloader service table)")
        except Exception as e:
            print(f"[info] upload path unavailable: {type(e).__name__}: {e}")

    print("\n" + "=" * 78)
    print("  Next: send me the bytes at 0xFF46C (gain) and 0xFF1B4 (clamp) from the dump,")
    print("  or attach the .bin, and I will compute the exact 2x calibration edit.")
    print("=" * 78)
    return 0


# --- self-guard: every uds.<method> call must be in the read/upload-read whitelist ---
def _assert_read_only_source() -> None:
    import re
    src = open(os.path.abspath(__file__), "r", encoding="utf-8").read()
    allowed = {"tester_present", "diagnostic_session_control", "security_access",
               "read_memory_by_address", "_uds_request", "transfer_data",
               "request_transfer_exit"}
    calls = set(re.findall(r"\buds\.([a-z_]+)\(", src))
    bad = calls - allowed
    assert not bad, f"READ-ONLY GUARD TRIPPED: non-allowed uds calls present: {sorted(bad)}"
    # Hard-forbid the write-setup SERVICE_TYPE symbol and the programming session.
    # Needles are built from parts so these guard lines are not themselves matches;
    # the docstring uses prose ("RequestDownload"), never the SERVICE_TYPE.X symbol.
    for needle in ["SERVICE_TYPE." + "REQUEST_DOWNLOAD", "SESSION_TYPE." + "PROGRAMMING"]:
        assert needle not in src, f"READ-ONLY GUARD TRIPPED: forbidden symbol {needle!r}"


if __name__ == "__main__":
    _assert_read_only_source()
    sys.exit(main())
