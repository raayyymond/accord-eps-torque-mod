#!/usr/bin/env python3
"""panda_rx_health.py - is the red panda actually RECEIVING CAN frames?

Non-blocking diagnostic. Reads the panda's per-bus health COUNTERS via USB
control transfers ONLY. It NEVER calls can_recv()/bulkRead -- the blocking bulk
endpoint that froze bench_uds_telem_read.py when nothing was arriving -- so this
tool cannot hang the same way.

WHY: bench_uds_telem_read.py hung inside panda's UdsClient at
can_recv()->bulkRead(), which only blocks when the panda is delivering NO frames
at all. This tool answers the question that hang raised: is the red panda seeing
the bus at all, and on WHICH bus?

READS total_rx_cnt (+ tx/error state) for buses 0/1/2, first in the as-opened
safety mode, then under ELM327 (the bench tool's / flasher's mode), sampling a
few times a second apart:
  * total_rx_cnt CLIMBS on a bus  -> panda HW is receiving that bus. The traffic
    is there; poll UDS on THAT bus number. (If it climbs but reads still fail,
    the issue is downstream: WSL USB delivery, or the ECU not answering.)
  * flat ~0 on every bus, car running -> panda sees no traffic at all
    (wiring / bus mapping / safety mode). No UDS tool can work until fixed.
  * bus_off / error_passive true, or transmit/receive_error_cnt high -> bus
    wiring / termination problem.

SAFE: sets ELM327 safety + clears CAN buffers (same as the bench tool), but
TRANSMITS NOTHING. Run in the same WSL env as eps-update-tva.py:
  python3 panda_rx_health.py
"""
import os
import sys
import time

for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from panda import Panda
except Exception as e:
    print(f"[fatal] cannot import panda ({type(e).__name__}: {e}). "
          f"Use the same env as eps-update-tva.py.", file=sys.stderr)
    sys.exit(2)

if not hasattr(Panda, "SAFETY_ELM327"):
    Panda.SAFETY_ELM327 = 3  # numeric value 3 in all eras


def open_panda():
    try:
        return Panda(disable_checks=True)
    except TypeError:
        return Panda()


def bus_rx(p, bus):
    """(total_rx_cnt, full_dict) via control transfer; NO can_recv."""
    try:
        h = p.can_health(bus)
        rx = h.get("total_rx_cnt", h.get("total_rx", "?"))
        return rx, h
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def sample(p, label, n=4, dt=1.0):
    print(f"\n--- {label}: per-bus total_rx_cnt (control-transfer only) ---")
    for i in range(n):
        cells = []
        for bus in (0, 1, 2):
            rx, _ = bus_rx(p, bus)
            cells.append(f"bus{bus} rx={rx}")
        print(f"  [t={i}s] " + "   ".join(cells))
        if i < n - 1:
            time.sleep(dt)


def main():
    p = open_panda()
    for getter in ("get_type", "get_serial", "get_version"):
        try:
            print(f"[panda] {getter}: {getattr(p, getter)()}")
        except Exception:
            pass
    try:
        print(f"[panda] health: {p.health()}")
    except Exception as e:
        print(f"[panda] health err: {e}")

    # Full per-bus health once (shows bus_off / error state / speed).
    for bus in (0, 1, 2):
        _, full = bus_rx(p, bus)
        print(f"[can_health bus{bus}] {full}")

    # Phase 1: whatever mode the panda opened in.
    sample(p, "as-opened mode")

    # Phase 2: ELM327 (the mode bench_uds_telem_read.py / the flasher use).
    try:
        p.set_safety_mode(Panda.SAFETY_ELM327)
        p.can_clear(0xFFFF)
        sample(p, "after set_safety_mode(ELM327) + can_clear")
    except Exception as e:
        print(f"[elm327] err: {e}")

    print("\n[read this] A bus whose rx climbs is the live one -> use that --bus.")
    print("[read this] All flat ~0 with the car running -> panda sees no traffic")
    print("            (check bus mapping on the comma cable, wiring, safety mode).")


if __name__ == "__main__":
    main()
