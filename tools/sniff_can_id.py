#!/usr/bin/env python3
"""sniff_can_id.py - watch ONE CAN ID's payload over time (SILENT, no TX).

Tests whether a signal is LIVE. Default watches 0x18F (399 STEER_STATUS) on bus 1,
whose STEER_TORQUE_SENSOR is fed by the SAME gp-0x4f60/gp-0x4f68 column-torque
pipeline our UDS telemetry reads (packer -(gp-0x4f60 * 125/128), tracer-verified).

Turn the wheel while this runs:
  * 399's bytes CHANGE  -> the EPS senses live torque in RAM, so a STATIC UDS read
    of gp-0x4f68 is a read-path staleness bug (ECU response cache / latched value),
    NOT the firmware.
  * 399's bytes DON'T change -> the wheel input didn't load the column (test setup),
    or this ID doesn't carry the torque signal.

SILENT listen-only: transmits NOTHING. Run in the same env as eps-update-tva.py:
  python3 sniff_can_id.py                          # 0x18F, bus 1, 10 s
  python3 sniff_can_id.py --id 0x18F --bus 1 --seconds 15
"""
import argparse
import os
import sys
import time
from collections import Counter

for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from panda import Panda
except Exception as e:
    print(f"[fatal] cannot import panda ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(2)


def recv_norm(panda):
    for m in panda.can_recv():
        if len(m) == 4:
            addr, _bt, dat, src = m
        else:
            addr, dat, src = m
        yield addr, bytes(dat), src & 0x0F


def main():
    ap = argparse.ArgumentParser(description="Watch one CAN ID's payload (SILENT, read-only).")
    ap.add_argument("--id", type=lambda x: int(x, 0), default=0x18F,
                    help="CAN ID to watch (default 0x18F = 399 STEER_STATUS)")
    ap.add_argument("--bus", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=10.0)
    a = ap.parse_args()

    try:
        p = Panda(disable_checks=True)
    except TypeError:
        p = Panda()
    try:
        p.set_safety_mode(0)  # SAFETY_SILENT: listen-only, transmits nothing
    except Exception as e:
        print(f"[warn] set_safety_mode(SILENT): {e}")
    p.can_clear(0xFFFF)
    print(f"[watch] SILENT, id=0x{a.id:X} bus={a.bus} for {a.seconds:g}s. "
          f"---> TURN THE WHEEL now <---")

    payloads = Counter()
    order = []
    nbytes = 0
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.seconds:
        for addr, dat, src in recv_norm(p):
            if addr != a.id or src != a.bus:
                continue
            h = dat.hex()
            if h not in payloads:
                order.append((time.monotonic() - t0, h))
            payloads[h] += 1
            nbytes = max(nbytes, len(dat))

    total = sum(payloads.values())
    print(f"\n[result] {total} frames of 0x{a.id:X} on bus {a.bus}, "
          f"{len(payloads)} UNIQUE payload(s)")
    if total == 0:
        print("  NONE seen -> wrong id/bus, or not transmitted (399 is ~100Hz on bus 1).")
        return

    cols = [[] for _ in range(nbytes)]
    for h in payloads:
        b = bytes.fromhex(h)
        for i in range(len(b)):
            cols[i].append(b[i])
    print("  per-byte value range across all distinct payloads (byte: min..max):")
    for i, vals in enumerate(cols):
        lo, hi = min(vals), max(vals)
        flag = "   <-- VARIES" if hi > lo else ""
        print(f"    byte{i}: {lo:3d}..{hi:3d}  span={hi - lo}{flag}")
    print("\n  first distinct payloads seen (t, hex):")
    for t, h in order[:8]:
        print(f"    [{t:5.2f}s] {h}")

    if len(payloads) == 1:
        print(f"\n[read this] Only ONE payload -> 0x{a.id:X} did NOT change while turning. "
              f"The wheel input didn't load the column, or this ID lacks the signal.")
    else:
        print(f"\n[read this] 0x{a.id:X} CHANGES while turning -> the EPS senses LIVE torque "
              f"in RAM. So the STATIC UDS read of gp-0x4f68 is a read-path staleness bug "
              f"(ECU response cache / latched value), not the firmware.")


if __name__ == "__main__":
    main()
