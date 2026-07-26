"""eps-find-window.py - find the EPS bootloader's accepted download window.

Probes RequestDownload (0x34) across page-aligned (start, size) combinations to
discover which window the V850/TVA bootloader will accept, WITHOUT writing any
flash. On the first accepted start it binary-searches the maximum accepted size,
reports the full [start, end) window, safely closes the transfer, and stops.

THE SAFETY CONTRACT - why this cannot write flash
-------------------------------------------------
A flash write happens ONLY via TransferData (0x36). This script NEVER calls
transfer_data. The string "transfer_data" / SERVICE 0x36 does not appear in the
scan loop. The only download-related services it sends are:

    0x34  RequestDownload        - negotiates a transfer (no write)
    0x37  RequestTransferExit    - closes the negotiated transfer (no write)

RequestDownload sets up a transfer and returns the max block size; with zero
TransferData sent, the target region (already erased) is left unchanged.

Setup services (state changes, NOT flash-content writes):
    0x3E TesterPresent, 0x22 ReadDataByIdentifier, 0x10 Diagnostic Session
    (EXTENDED then PROGRAMMING), 0x27 SecurityAccess, 0x2E WriteDataByIdentifier
    (0xF101 decryption key - a key register, not flash), and OPTIONALLY
    0x31 0x01 0xFF00 eraseMemory ONLY if --erase-first is passed.

It does NOT call: 0x36 TransferData, 0x3D WriteMemoryByAddress, 0x11 ECUReset.

Usage
-----
    # default: NO erase (least-mutating). Programming+SA+key, then probe.
    python eps-find-window.py --bus 1

    # faithful reproduction of the crash precondition (re-erases already-blank
    # app flash - materially harmless but IS an erase routine):
    python eps-find-window.py --bus 1 --erase-first

    # narrow the start range / change page size / resume:
    python eps-find-window.py --bus 1 --start-min 0x10000 --start-max 0x20000
"""

import argparse
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tva_sa_key import calculate_tva_session_key

DEFAULT_ADDR = 0x18DA30F1
CIPHER_KEY = bytes([0xBF, 0x10, 0x9E])   # x31 decryption key (DID 0xF101), same as v6/v7
FLASH_TOP = 0x100000                     # 1 MB
PAGE = 0x1000                            # 4 KB flash page
NRC_OUT_OF_RANGE = 0x31


def ordered_starts(start_min, start_max, page):
    """Page-aligned starts, most-likely-first then ascending sweep for coverage."""
    favored = [0x10000, 0x14000, 0x12000, 0x00000]
    allp = list(range(start_min, start_max, page))
    seq = [s for s in favored if start_min <= s < start_max]
    seq += [s for s in allp if s not in seq]
    return seq


def main() -> int:
    p = argparse.ArgumentParser(description="Find EPS bootloader accepted download window (read-only wrt flash)")
    p.add_argument("--bus", type=int, required=True)
    p.add_argument("--addr", type=lambda s: int(s, 0), default=DEFAULT_ADDR)
    p.add_argument("--page", type=lambda s: int(s, 0), default=PAGE)
    p.add_argument("--start-min", type=lambda s: int(s, 0), default=0x00000)
    p.add_argument("--start-max", type=lambda s: int(s, 0), default=FLASH_TOP)
    p.add_argument("--erase-first", action="store_true",
                   help="issue eraseMemory(0xFF00) before probing (re-erases blank app; IS a mutation)")
    p.add_argument("--out", default=os.path.join(_HERE, "eps-window-scan-results.txt"))
    p.add_argument("--debug", action="store_true", help="verbose ISO-TP frame logging")
    args = p.parse_args()

    log = open(args.out, "w", buffering=1)  # line-buffered so findings survive a crash

    def emit(msg):
        print(msg)
        log.write(msg + "\n")

    emit("=" * 70)
    emit("  EPS DOWNLOAD-WINDOW FINDER - issues 0x34/0x37 only, NEVER 0x36 (no flash write)")
    emit(f"  addr=0x{args.addr:08X} bus={args.bus} page=0x{args.page:X} "
         f"erase_first={args.erase_first}")
    emit(f"  start range [0x{args.start_min:X}, 0x{args.start_max:X})")
    emit("=" * 70)

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
        emit(f"[fatal] no real panda ({type(e).__name__}: {e}); refusing to mock.")
        return 2
    panda.can_clear(0xFFFF)
    panda.set_safety_mode(Panda.SAFETY_ELM327)
    uds = UdsClient(panda, args.addr, debug=args.debug, bus=args.bus)

    # ---- setup: get the ECU into the state where 0x34 is range-checked ----
    try:
        uds.tester_present()
        app_id = uds.read_data_by_identifier(
            DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)
        emit(f"[setup] app id (0xF181) = {app_id!r}")
        uds.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
        seed = uds.security_access(ACCESS_TYPE.REQUEST_SEED)[-2:]
        key = calculate_tva_session_key(seed)
        uds.security_access(ACCESS_TYPE.SEND_KEY, key)
        emit(f"[setup] SA ok (seed 0x{seed.hex().upper()} -> key 0x{key.hex().upper()})")
        uds.diagnostic_session_control(SESSION_TYPE.PROGRAMMING)
        uds.tester_present()
        if args.erase_first:
            emit("[setup] --erase-first: issuing eraseMemory(0xFF00)")
            uds.routine_control(ROUTINE_CONTROL_TYPE.START, ROUTINE_IDENTIFIER_TYPE.ERASE_MEMORY)
            uds.tester_present()
        uds.write_data_by_identifier(DATA_IDENTIFIER_TYPE.FLASH_DECRYPTION_KEY, CIPHER_KEY)
        emit(f"[setup] wrote decryption key {CIPHER_KEY.hex().upper()}")
    except NegativeResponseError as e:
        emit(f"[fatal] setup step failed: {e} (NRC 0x{e.error_code:02X}); cannot probe. "
             "If this is conditionsNotCorrect, retry with --erase-first.")
        return 3

    # ---- probe helpers ----
    def try_download(start, size):
        """Return ('ok', max_chunk) or ('nrc', code). Closes any accepted
        transfer with 0x37 so the next probe starts clean. NEVER sends 0x36."""
        try:
            max_chunk = uds.request_download(start, size)  # 0x34
            # accepted: immediately close the negotiated transfer (no data sent)
            try:
                uds.request_transfer_exit()  # 0x37 - resets download state
            except NegativeResponseError:
                pass  # zero-length exit may NRC; harmless, no write occurred
            return ("ok", max_chunk)
        except NegativeResponseError as e:
            return ("nrc", e.error_code)

    starts = ordered_starts(args.start_min, args.start_max, args.page)
    emit(f"[scan] probing {len(starts)} page-aligned starts...")
    found = None
    nrc_hist = {}
    t0 = time.time()

    for i, start in enumerate(starts):
        remaining = FLASH_TOP - start
        # probe largest-possible first; if rejected, probe one page
        res_full = try_download(start, remaining)
        if res_full[0] == "ok":
            emit(f"[FOUND] start=0x{start:X} accepts FULL size=0x{remaining:X} "
                 f"(max_chunk=0x{res_full[1]:X})")
            found = (start, start + remaining, remaining, res_full[1])
            break
        res_page = try_download(start, args.page)
        if res_page[0] == "ok":
            # start valid; binary-search max size in pages within (page, remaining)
            emit(f"[hit]   start=0x{start:X} accepts 0x{args.page:X}; binary-searching max size")
            lo_pages = args.page // args.page                 # 1 page (known good)
            hi_pages = remaining // args.page                 # all remaining (known bad via res_full)
            best = args.page
            best_chunk = res_page[1]
            while lo_pages + 1 < hi_pages:
                mid = (lo_pages + hi_pages) // 2
                size = mid * args.page
                r = try_download(start, size)
                if r[0] == "ok":
                    lo_pages, best, best_chunk = mid, size, r[1]
                else:
                    hi_pages = mid
                    nrc_hist[r[1]] = nrc_hist.get(r[1], 0) + 1
            emit(f"[FOUND] start=0x{start:X} max accepted size=0x{best:X} "
                 f"-> window [0x{start:X}, 0x{start + best:X}) (max_chunk=0x{best_chunk:X})")
            found = (start, start + best, best, best_chunk)
            break
        # both rejected; record the NRC for the full-size probe
        code = res_full[1]
        nrc_hist[code] = nrc_hist.get(code, 0) + 1
        if i < 8 or code != NRC_OUT_OF_RANGE:
            emit(f"[scan]  start=0x{start:08X}: rejected NRC 0x{code:02X}")
        if i % 32 == 31:
            uds.tester_present()
            emit(f"[scan]  ...{i + 1}/{len(starts)} starts probed "
                 f"({time.time() - t0:.0f}s)  NRC histogram: "
                 f"{ {hex(k): v for k, v in nrc_hist.items()} }")

    emit("=" * 70)
    if found:
        start, end, size, chunk = found
        emit("  RESULT: ACCEPTED WINDOW FOUND")
        emit(f"    start = 0x{start:X}")
        emit(f"    end   = 0x{end:X}  (size 0x{size:X}, {size} bytes)")
        emit(f"    ECU max transfer chunk = 0x{chunk:X}")
        emit("  No flash was written (no 0x36 TransferData was ever sent).")
        emit("  To build a matching image, add to build_stock_tva_v7.py CANDIDATES:")
        emit(f'    ("v7win", 0x{start:X}, 0x{end:X}, "bootloader-accepted window"),')
        emit("  Then flash that .rwd deliberately (name file + bus; iron rule).")
    else:
        emit("  RESULT: NO accepted window across the scanned range.")
        emit(f"    NRC histogram: { {hex(k): v for k, v in nrc_hist.items()} }")
        emit("  If every rejection was 0x31 (requestOutOfRange), the resident")
        emit("  bootloader exposes NO code-flash download path in this state.")
        emit("  This corroborates V850_STOCK_RWD_ANALYSIS.md sec.4: code-flash")
        emit("  reprogramming needs the HDS RAM-resident kernel (not uploaded by")
        emit("  this tool). Recovery path = iHDS / J2534, not another .rwd window.")
        emit("  (If rejections were 0x22 conditionsNotCorrect, retry --erase-first.)")
    emit("=" * 70)
    emit(f"  scanned {len(starts)} starts in {time.time() - t0:.0f}s; results -> {args.out}")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
