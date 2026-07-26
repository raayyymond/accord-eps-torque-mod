#!/usr/bin/env python3
"""panda_can_sniff.py - passive host-level CAN sniff (SILENT mode, no TX).

Follow-up to panda_rx_health.py, which showed the panda HARDWARE receives on all
buses but that SAFETY_ELM327 (the bench tool's mode) froze bus1 RX and delivered
nothing to the host -> can_recv() blocked -> bench_uds_telem_read.py hung.

This answers two things the HW counters can't:
  1. Does the HOST actually get frames via can_recv() (i.e. is USB delivery under
     WSL working at all)?
  2. Which bus carries the EPS? -> flags 0x18F(399 STEER_STATUS),
     0x1AB(427 MOTOR_TORQUE), 0x14A.

It runs in SAFETY_SILENT (listen-only: receives + forwards to host, ACKs/TX
NOTHING). The panda is flooded with frames there, so can_recv returns at once and
cannot hang the way ELM327 did.

SAFE: SILENT transmits nothing. Run in the same WSL env as eps-update-tva.py:
  python3 panda_can_sniff.py
"""
import os
import sys
import time
from collections import Counter, defaultdict

for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from panda import Panda
except Exception as e:
    print(f"[fatal] cannot import panda ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(2)

SNIFF_SEC = 3.0
EPS_IDS = {0x18F: "399 STEER_STATUS", 0x1AB: "427 MOTOR_TORQUE", 0x14A: "0x14A"}


def open_panda():
    try:
        return Panda(disable_checks=True)
    except TypeError:
        return Panda()


def recv_norm(panda):
    """Yield (addr, data, bus) tolerating panda's 3- and 4-tuple can_recv shapes."""
    for msg in panda.can_recv():
        if len(msg) == 4:
            addr, _bt, dat, src = msg
        else:
            addr, dat, src = msg
        yield addr, dat, src & 0x0F


def is_diag(i):
    return (i >> 8) == 0x18DAF1 or 0x720 <= i <= 0x7FF


def main():
    p = open_panda()
    try:
        p.set_safety_mode(0)  # SAFETY_SILENT: listen-only, forwards RX to host
    except Exception as e:
        print(f"[warn] set_safety_mode(SILENT) failed: {e}")
    p.can_clear(0xFFFF)
    print(f"[sniff] SILENT listen-only for {SNIFF_SEC:g}s (no TX). Draining can_recv...")

    per_bus = Counter()
    ids_by_bus = defaultdict(Counter)
    t0 = time.monotonic()
    while time.monotonic() - t0 < SNIFF_SEC:
        for addr, _dat, src in recv_norm(p):
            per_bus[src] += 1
            ids_by_bus[src][addr] += 1

    if not per_bus:
        print("[result] HOST received ZERO frames even in SILENT -> the problem is "
              "USB delivery under WSL (usbipd), not the safety mode. Flag this.")
        return

    for bus in sorted(ids_by_bus):
        ids = ids_by_bus[bus]
        eps_hits = [f"0x{i:X}({EPS_IDS[i]})" for i in EPS_IDS if i in ids]
        diag = sorted({f"0x{i:X}" for i in ids if is_diag(i)})
        top = ", ".join(f"0x{i:X}:{n}" for i, n in ids.most_common(8))
        print(f"\n[bus {bus}] frames={per_bus[bus]} unique_ids={len(ids)}")
        print(f"   EPS frames : {eps_hits or 'NONE'}")
        if diag:
            print(f"   diag IDs   : {diag}")
        print(f"   top IDs    : {top}")

    print("\n[read this] Host receiving here => the hang was ELM327-specific, not "
          "WSL/USB. The bus listing 0x18F/0x1AB/0x14A is the EPS bus -> that is the "
          "--bus for the read once we switch the read tool off ELM327.")


if __name__ == "__main__":
    main()
