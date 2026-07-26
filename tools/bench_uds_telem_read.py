#!/usr/bin/env python3
"""bench_uds_telem_read.py - poll the UDS telemetry DID and log gentle-EME signals to CSV.

Reads the repurposed RDBI DID (default 0x4801) from the 2020 Accord EPS over
UDS-over-CAN and records the decoded gentle-EME signals to a CSV file. This is
the bench-validation companion to the UDStelem .rwd
(the configured firmware rwd directory/39990-TVA,A160-UDStelem-DID4801-RAMread-*.rwd).

WHAT IT SENDS (read-only, no ECU state change):
  UDS ReadDataByIdentifier -> CAN 0x18DA30F1 : [22 48 01]           (bus 1)
  (plus one TesterPresent [3E 00] at start)
WHAT IT EXPECTS BACK:
  0x18DAF130 : [62 48 01 <MAXlo MAXhi AVGlo AVGhi TQlo TQhi ANGlo ANGhi>]
DECODE (4x little-endian u16):
  voter-MAX torque (gp-0x6a62)  -> crosses 320  => 0xC6312 (V33) decider gate
  voter-AVG torque (gp-0x6a5e)  -> crosses 320  => 0xC62FE (V35) deliver-commit gate
  |column torque|  (gp-0x4f68)  -> crosses 4096 => Gate-5 (0xC61EA)
  angle            (gp-0x6cc4)  -> angle-#1 suspect

PRE-REQS / WHERE TO RUN:
  WSL/laptop + red panda  <-- RECOMMENDED (the eps-update-tva.py rig). The red
      panda plugs into the SAME comma harness cable (comma unplugged first), so
      it taps the SAME CAN buses the comma does. This is the PROVEN path to the
      EPS diagnostic UDS channel -- it is how the car is flashed. Same panda env
      as the flasher; auto-uses panda's UdsClient. Use the SAME --bus you flash
      with (--bus 1).
  comma 4:  openpilot/pandad KILLED first (tmux kill-server); run from a
      writable dir (e.g. /data/media/0). NOTE (2026-07): the comma's OWN panda
      did not get a diagnostic reply on bus 0 or 1 -- even though it is on the
      SAME wires as the red panda. That is a comma-panda TX/config issue, NOT a
      bus/gateway dead-end (the red panda on the same cable reaches the EPS
      fine). Prefer the red panda. Falls back to hand-rolled ISO-TP here (the
      device panda ships no uds module).
  CAVEAT (live gentle-EME capture): the red panda and the comma share ONE cable,
      so you cannot poll UDS AND have openpilot steering at the same time. A
      red-panda read is a STATIC snapshot (car on, EPS powered, not actively
      LKAS-steering). The gentle-EME cut needs openpilot engaged -> to catch it
      live you need a second tap (true OBD-II port, if the channel reaches it) or
      a CAN Y-splitter so comma + red panda sit on the bus together.
  either env:  the UDStelem .rwd must be flashed for DID 0x4801 to return the
      8-byte telemetry; otherwise 0x4801 returns its stock 54-byte value (still
      a NON-empty response, which by itself proves the channel is alive).

USAGE:
  python3 bench_uds_telem_read.py                     # bus 1, DID 0x4801, max rate, until Ctrl-C
  python3 bench_uds_telem_read.py --seconds 120       # stop after 120 s
  python3 bench_uds_telem_read.py --hz 50 --out run.csv
  python3 bench_uds_telem_read.py --yes               # skip the send-confirmation prompt (scripting)

SAFETY: SID 0x22 is a read. This changes NO ECU state. Still, it transmits CAN, so it
prints the exact payload and asks for confirmation unless --yes is passed (kit iron rule).
"""
import argparse
import datetime
import os
import struct
import sys
import threading
import time

DEF_ADDR = 0x18DA30F1   # 29-bit ISO-TP request addr (A160 EPS, flasher-verified); resp = 0x18DAF130
DEF_BUS  = 1
DEF_DID  = 0x4801


class IsoTpUds:
    """Minimal UDS-over-ISO-TP client built on ONLY panda.Panda.can_send/can_recv.

    A drop-in stand-in for the two panda `UdsClient` methods this script uses
    (`tester_present`, `read_data_by_identifier`). The comma 4's openpilot
    device panda ships NO `uds.py` (verified on-device: the panda package has no
    `uds` module at all), so `panda.python.uds` / `panda.uds` do not exist and
    `UdsClient` is simply unavailable there. Hand-rolling the transport keeps the
    tool dependent on nothing but the `Panda` class, which does import on the
    comma 4.

    Transport logic is adapted from the repo's proven
    `radar-re/uds_did_sweep.py::isotp_send_recv` (validated on this operator's
    comma against the Honda EPS/radar): single-frame request, ISO-TP-reassembled
    response with tester flow-control, `0x78` responsePending tolerated.
    """

    def __init__(self, panda, req_addr, bus=DEF_BUS, timeout=0.3, resp_addr=None):
        self.p = panda
        self.tx = req_addr
        self.bus = bus
        self.timeout = timeout
        # Honda diag address pairing: req 0x18DAttF1 -> resp 0x18DAF1tt.
        self.rx = resp_addr if resp_addr is not None \
            else (0x18DAF100 | ((req_addr >> 8) & 0xFF))

    def _recv(self):
        """Yield (addr, data, bus_idx), tolerating panda's 3-tuple (newer lib)
        and 4-tuple (older lib, e.g. the comma 4) can_recv() shapes."""
        for msg in self.p.can_recv():
            if len(msg) == 4:
                addr, _bt, data, src = msg
            else:
                addr, data, src = msg
            yield addr, data, src & 0x0F

    def _send_recv(self, payload):
        """Send a single-frame request; return the ISO-TP-reassembled response
        bytes (SID-inclusive) or None on timeout."""
        assert len(payload) <= 7, "only single-frame requests supported here"
        sf = (bytes([len(payload)]) + payload).ljust(8, b"\x00")
        self.p.can_send(self.tx, sf, self.bus)
        data = b""
        expected = None
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            for addr, dat, bus_idx in self._recv():
                if bus_idx != self.bus or addr != self.rx:
                    continue
                pci = dat[0] >> 4
                if pci == 0x0:                       # single frame
                    n = dat[0] & 0x0F
                    frame = bytes(dat[1:1 + n])
                    if len(frame) >= 3 and frame[0] == 0x7F and frame[2] == 0x78:
                        continue                     # responsePending: keep waiting
                    return frame
                elif pci == 0x1:                     # first frame
                    expected = ((dat[0] & 0x0F) << 8) | dat[1]
                    data = bytes(dat[2:8])
                    fc = bytes([0x30, 0x00, 0x00]).ljust(8, b"\x00")
                    self.p.can_send(self.tx, fc, self.bus)   # flow-control: clear-to-send
                elif pci == 0x2:                     # consecutive frame
                    data += bytes(dat[1:8])
                    if expected and len(data) >= expected:
                        return data[:expected]
            time.sleep(0.0005)                       # gentle poll; << the ~90ms cut
        return data[:expected] if (expected and data) else (data or None)

    def tester_present(self):
        self._send_recv(bytes([0x3E, 0x00]))

    def read_data_by_identifier(self, did):
        """Return the RDBI payload AFTER the `62 <did>` echo (matches panda
        UdsClient semantics), or raise on timeout / negative response."""
        resp = self._send_recv(bytes([0x22, (did >> 8) & 0xFF, did & 0xFF]))
        if resp is None:
            raise TimeoutError(f"no response to 22 {did:04X}")
        if resp[0] == 0x7F:
            nrc = resp[2] if len(resp) >= 3 else 0xFF
            raise RuntimeError(f"negative response 7F {resp[1]:02X} {nrc:02X}")
        if resp[0] == 0x62 and len(resp) >= 3:
            return resp[3:]
        return resp  # unexpected shape -> caller's short-response branch logs it


_SAFETY_NAMES = {"silent": 0, "elm327": 3, "alloutput": 17}


def _parse_obd(x):
    """Parse --obd on/off/1/0 to a bool (None = don't touch the panda's OBD-mux state)."""
    return {"0": False, "off": False, "false": False, "no": False,
            "1": True, "on": True, "true": True, "yes": True}[str(x).strip().lower()]


def resolve_safety(name):
    """Map a --safety value (name or int string) to the panda numeric mode."""
    try:
        return int(str(name), 0)
    except (TypeError, ValueError):
        return _SAFETY_NAMES.get(str(name).lower(), 17)


def _run_with_timeout(fn, timeout, on_timeout_msg):
    """Run fn() in a daemon thread; if it has not returned within `timeout` s,
    print on_timeout_msg and hard-exit. A panda can_recv/bulkRead blocked on an
    empty endpoint (no ECU reply) is otherwise un-interruptible, so this is what
    turns a wrong --addr/--bus into a clean message instead of a frozen terminal.
    Returns fn()'s value, or re-raises whatever fn() raised."""
    box = {}

    def worker():
        try:
            box["r"] = fn()
        except BaseException as e:  # propagate to the caller
            box["e"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(on_timeout_msg, file=sys.stderr)
        sys.stderr.flush()
        os._exit(4)
    if "e" in box:
        raise box["e"]
    return box.get("r")


def build_argparser():
    ap = argparse.ArgumentParser(description="Poll the UDS telemetry DID and log to CSV (read-only).")
    ap.add_argument("--bus", type=int, default=DEF_BUS, help="CAN bus (default 1; EPS is on comma bus 1)")
    ap.add_argument("--safety", default="elm327",
                    help="panda safety mode: elm327 (default; the flasher's proven "
                         "diagnostic mode), silent (RX only, no TX), alloutput "
                         "(UNSAFE -- injected on the ADAS bus and tripped RDM; avoid), "
                         "or a raw int")
    ap.add_argument("--obd", type=_parse_obd, default=None,
                    help="OBD multiplexing (comma-vs-red-panda diagnostic sweep): on = route "
                         "comma bus 1 to the OBD-II port (the boot-fingerprint diagnostic path); "
                         "off = normal harness CAN2. Default: leave the panda's current state "
                         "untouched (matches the red-panda/flasher path, which sets no OBD mux).")
    ap.add_argument("--addr", type=lambda x: int(x, 0), default=DEF_ADDR,
                    help="UDS request addr (default 0x18DA30F1, A160 EPS)")
    ap.add_argument("--did", type=lambda x: int(x, 0), default=DEF_DID,
                    help="DataIdentifier to read (default 0x4801)")
    ap.add_argument("--out", default=None, help="CSV path (default uds_telem_<timestamp>.csv)")
    ap.add_argument("--hz", type=float, default=0.0,
                    help="max request rate; 0 = as fast as responses allow (best for the ~90ms cut)")
    ap.add_argument("--seconds", type=float, default=0.0, help="stop after N seconds (0 = until Ctrl-C)")
    ap.add_argument("--status-sec", type=float, default=2.0, help="status line refresh interval")
    ap.add_argument("--timeout", type=float, default=0.3, help="per-read response timeout (s)")
    ap.add_argument("--tester-present-hz", type=float, default=1.0,
                    help="send TesterPresent at this rate to hold the session (0 = only once at start)")
    ap.add_argument("--yes", action="store_true", help="skip the send-confirmation prompt")
    return ap


def confirm_send(args, did_hi, did_lo):
    print("=" * 70)
    print("  bench_uds_telem_read.py - about to TRANSMIT UDS reads on CAN")
    print("=" * 70)
    print(f"  bus            : {args.bus}")
    print(f"  request addr   : 0x{args.addr:08X}")
    print(f"  will send      : [22 {did_hi:02X} {did_lo:02X}]  (ReadDataByIdentifier, DID 0x{args.did:04X})")
    print(f"  plus           : [3E 00] TesterPresent")
    print(f"  read-only      : SID 0x22/0x3E change NO ECU state")
    print(f"  prereq         : openpilot/pandad killed (tmux kill-server)")
    print("=" * 70)
    if args.yes:
        print("[confirm] --yes given, proceeding")
        return True
    try:
        ans = input("Type 'y' to start polling, anything else to abort: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return ans.strip().lower() == "y"


def main():
    args = build_argparser().parse_args()
    did_hi, did_lo = (args.did >> 8) & 0xFF, args.did & 0xFF

    if not confirm_send(args, did_hi, did_lo):
        print("[abort] not confirmed")
        return 1

    # --- panda / UDS setup ---
    # Two runtime environments, one script:
    #  * WSL/laptop + red panda (the eps-update-tva.py rig): the full panda lib
    #    exposes panda.python.uds.UdsClient -> use it IDENTICALLY to the flasher,
    #    so the read rides the exact transport proven to reach this ECU.
    #  * comma 4 device panda: ships NO uds module -> UdsClient import fails ->
    #    fall back to the hand-rolled IsoTpUds (Panda.can_send/can_recv only).
    # Only prepend the comma openpilot paths if they actually exist, so a WSL
    # host cleanly imports its installed `panda` package (like the flasher does).
    for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from panda import Panda
    except Exception as e:
        print(f"[fatal] cannot import panda ({type(e).__name__}: {e}). "
              f"On WSL/laptop use the same env as eps-update-tva.py; on the "
              f"comma run with openpilot present at /data/openpilot.",
              file=sys.stderr)
        return 2

    try:
        from panda.python.uds import UdsClient  # present in the flasher's env
    except Exception:
        UdsClient = None                        # comma device panda: absent

    try:
        try:
            panda = Panda(disable_checks=True)  # matches eps-update-tva.py
        except TypeError:
            panda = Panda()                     # older lib w/o disable_checks
    except Exception as e:
        print(f"[fatal] cannot open panda ({type(e).__name__}: {e}). "
              f"On the comma: is pandad still running? Run: tmux kill-server. "
              f"On WSL: is the red panda attached / passed through to WSL?",
              file=sys.stderr)
        return 2

    # Safety mode = ELM327 by default (the flasher's proven diagnostic mode). It
    # does not stream the raw bus flood to the host, but it DOES deliver solicited
    # ISO-TP responses -- all a UDS read needs -- and it does not inject onto the
    # ADAS bus. (ALLOUTPUT did, and tripped Road Departure Mitigation on the dash.)
    safety_val = resolve_safety(args.safety)
    panda.can_clear(0xFFFF)
    panda.set_safety_mode(safety_val)

    # OBD multiplexing (diagnostic-path sweep). Only touch it if --obd was given, so the
    # default run matches the red-panda/flasher path (which never calls set_obd). ON routes
    # comma bus 1 (FDCAN2) to the OBD-II port -> the boot-fingerprint diagnostic path.
    if args.obd is not None:
        try:
            panda.set_obd(args.obd)
            print(f"[obd] OBD multiplexing = {args.obd} "
                  f"(bus 1 -> {'OBD-II port' if args.obd else 'harness CAN2 / normal'})")
        except Exception as e:
            print(f"[obd] WARNING: set_obd({args.obd}) failed ({type(e).__name__}: {e})",
                  file=sys.stderr)

    rx_addr = 0x18DAF100 | ((args.addr >> 8) & 0xFF)
    if UdsClient is not None:
        try:
            uds = UdsClient(panda, args.addr, bus=args.bus,
                            timeout=args.timeout, debug=False)
        except TypeError:
            uds = UdsClient(panda, args.addr, bus=args.bus, debug=False)
        print(f"[uds] panda UdsClient (matches eps-update-tva.py transport); "
              f"req=0x{args.addr:08X} resp=0x{rx_addr:08X} bus={args.bus}")
    else:
        uds = IsoTpUds(panda, args.addr, bus=args.bus, timeout=args.timeout)
        print(f"[uds] hand-rolled ISO-TP (no UdsClient dep); "
              f"req=0x{args.addr:08X} resp=0x{uds.rx:08X} bus={args.bus}")

    out_path = args.out or datetime.datetime.now().strftime("uds_telem_%Y%m%d_%H%M%S.csv")
    log = open(out_path, "w", buffering=1)  # line-buffered -> durable if killed
    log.write("iso_time,mono_s,elapsed_s,ok,max,avg,coltq,angle,raw_hex\n")

    print(f"[log] writing CSV -> {out_path}")
    print(f"[run] polling DID 0x{args.did:04X} on bus {args.bus} "
          f"({'max rate' if args.hz <= 0 else f'{args.hz:g} Hz'}); Ctrl-C to stop.")

    period = (1.0 / args.hz) if args.hz > 0 else 0.0
    tp_period = (1.0 / args.tester_present_hz) if args.tester_present_hz > 0 else None
    t0 = time.monotonic()
    n = ok = err = 0
    last = (None, None, None, None)
    last_status = t0
    last_tp = 0.0
    first_ok_printed = False

    # Canary: the first TesterPresent proves the addr/bus actually reach the ECU.
    # Guard it with a hard timeout so a wrong --addr/--bus yields a clean message
    # instead of an un-interruptible bulkRead hang. A negative/odd reply still
    # proves reachability, so only a TIMEOUT (no reply at all) aborts.
    try:
        _run_with_timeout(
            uds.tester_present, max(2.0, args.timeout * 6),
            f"[fatal] no reply to TesterPresent at 0x{args.addr:08X} (resp "
            f"0x{rx_addr:08X}) on bus {args.bus} -- the ECU is not answering. This "
            f"A160 EPS uses request 0x18DA30F1 / resp 0x18DAF130 (flasher-verified); "
            f"check --addr and --bus.")
    except Exception:
        pass
    last_tp = time.monotonic()

    try:
        while True:
            loop_start = time.monotonic()
            if args.seconds and (loop_start - t0) >= args.seconds:
                break

            # periodic tester-present to keep the session alive (cheap, benign)
            if tp_period is not None and (loop_start - last_tp) >= tp_period:
                try:
                    uds.tester_present()
                except Exception:
                    pass
                last_tp = time.monotonic()

            n += 1
            iso = datetime.datetime.now().isoformat(timespec="milliseconds")
            mono = time.monotonic()
            elapsed = mono - t0
            try:
                data = uds.read_data_by_identifier(args.did)
                if len(data) >= 8:
                    mx, av, tq, an = struct.unpack_from("<HHHH", data, 0)
                    log.write(f"{iso},{mono:.4f},{elapsed:.4f},1,{mx},{av},{tq},{an},{data.hex()}\n")
                    ok += 1
                    last = (mx, av, tq, an)
                    if not first_ok_printed:
                        print(f"\n[first read OK] MAX={mx} AVG={av} COLTQ={tq} ANGLE={an}  "
                              f"raw={data.hex()} (len={len(data)})")
                        first_ok_printed = True
                else:
                    log.write(f"{iso},{mono:.4f},{elapsed:.4f},0,,,,,SHORT:{data.hex()}\n")
                    err += 1
            except Exception as e:
                log.write(f"{iso},{mono:.4f},{elapsed:.4f},0,,,,,ERR:{type(e).__name__}:{e}\n")
                err += 1

            # single, in-place status line (no scroll spam)
            now = time.monotonic()
            if (now - last_status) >= args.status_sec:
                rate = ok / (now - t0) if now > t0 else 0.0
                sys.stdout.write(
                    f"\r[{elapsed:7.1f}s] n={n} ok={ok} err={err} {rate:5.0f}/s  "
                    f"last MAX={last[0]} AVG={last[1]} COLTQ={last[2]} ANGLE={last[3]}      "
                )
                sys.stdout.flush()
                last_status = now

            if period:
                dt = time.monotonic() - loop_start
                if dt < period:
                    time.sleep(period - dt)
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        dur = time.monotonic() - t0
        rate = ok / dur if dur > 0 else 0.0
        print(f"\n[done] {dur:.1f}s  samples={n}  ok={ok}  err={err}  avg={rate:.0f}/s")
        print(f"[done] CSV: {out_path}")
        if ok == 0:
            print("[hint] 0 successful reads. Check: .rwd flashed? correct --bus (try 0)? "
                  "openpilot killed? correct --did?")

    return 0


if __name__ == "__main__":
    sys.exit(main())
