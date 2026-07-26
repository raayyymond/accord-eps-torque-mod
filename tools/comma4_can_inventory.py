#!/usr/bin/env python3
"""
Comma 4 Panda - CAN Bus INVENTORY  (read-only, non-destructive)

Extends comma4_panda_test.py. Where that script just counts frames per bus for a
5-second go/no-go check, this one sniffs for ~10 s and prints:

  * EVERY CAN ID seen on each bus, with its measured rate (Hz), DLC, and a data sample.
  * An explicit "frames of interest" report for the EPS telemetry decision:
      - the EPS frames that SHOULD be comma-visible  (0x14A, 0x18F/399, 0x1AB/427)
      - the EPS frames we believe are internal-bus only (0x19F, 0x32E, 0x64D, 0x660)
    so you can confirm, live, which bus each is on (or that it is absent).

WHY: the rlogs show 0x660 (our old telemetry-piggyback target) never reaches the
comma. This gives live ground truth on that, plus the real per-ID rates that decide
whether a telemetry frame can be sampled fast enough (the gentle-EME cut is ~90 ms).

100% READ-ONLY. The panda is forced into SAFETY_SILENT (listen-only) before reading,
so it physically cannot transmit any CAN frame. No message is ever sent. This honors
the kit iron rule: never put anything on the bus without explicit operator confirmation.

Usage (run on the comma 4 via SSH):
  1. ssh comma@192.168.43.1
  2. tmux kill-server           # release the panda from pandad/openpilot
  3. sleep 2                    # let the panda settle
  4. python3 /data/comma4_can_inventory.py [seconds]     (default 10)

  Turn the car's ignition ON (engine off is fine) for full bus traffic.
"""

import sys
import time
import os

# EPS transmit frames (from the firmware's 7 CAN content-builders). We expect the
# first three on a comma-visible bus and the last four only on the EPS-internal bus.
EPS_COMMA_VISIBLE = {0x14A: "330", 0x18F: "399 STEER_STATUS", 0x1AB: "427 MOTOR_TORQUE"}
EPS_INTERNAL_ONLY = {0x19F: "415", 0x32E: "814", 0x64D: "1613", 0x660: "1632 (telemetry target)"}


def check_spi_device():
    spi_path = "/dev/spidev0.0"
    exists = os.path.exists(spi_path)
    print(f"[1/5] SPI device {spi_path}: {'FOUND' if exists else 'NOT FOUND'}")
    if not exists:
        print("  ERROR: SPI device missing. Is this a comma 4 / comma 3X?")
    return exists


def check_pandad_running():
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-f", "pandad"], capture_output=True, text=True)
        running = result.returncode == 0
        if running:
            print("[2/5] pandad process: STILL RUNNING")
            print("  WARNING: stop it first -> tmux kill-server ; sleep 2 ; retry.")
        else:
            print("[2/5] pandad process: NOT RUNNING (good)")
        return not running
    except Exception as e:
        print(f"[2/5] pandad check: SKIPPED ({e})")
        return True


def connect_panda():
    try:
        from panda import Panda
    except ImportError:
        sys.path.insert(0, "/data/openpilot/third_party/panda")
        sys.path.insert(0, "/data/openpilot")
        try:
            from panda import Panda
        except ImportError:
            print("[3/5] Panda library: NOT FOUND (need openpilot at /data/openpilot)")
            return None, None
    print("[3/5] Panda library: IMPORTED")
    p = None
    try:
        p = Panda()
        hw_type = p.get_type()
        serial = p.get_serial()
        hw_names = {b'\x07': "RED_PANDA", b'\x09': "TRES (comma 3X)", b'\x0a': "CUATRO (comma 4)"}
        print(f"  Hardware type: {hw_names.get(hw_type, f'UNKNOWN ({hw_type.hex()})')}")
        print(f"  Serial: {serial[0] if serial else 'unknown'}")
        print(f"  Bootstub mode: {p.bootstub}")
        if p.bootstub:
            print("  WARNING: panda is in bootstub mode (not running app firmware).")
            p.close()
            return None, None
        print(f"  Firmware version: {p.get_version()}")
        return p, Panda
    except Exception as e:
        if p is not None:
            p.close()
        print(f"[3/5] Panda connection: FAILED\n  Error: {e}")
        print("  Make sure pandad/openpilot is stopped (tmux kill-server).")
        return None, None


def force_silent(p, Panda):
    """Put the panda in listen-only SILENT mode so it cannot transmit. Returns True on success."""
    mode = getattr(Panda, "SAFETY_SILENT", 0)
    try:
        p.set_safety_mode(mode)
        # flush any stale frames buffered from before we set silent mode
        try:
            p.can_clear(0xFFFF)
        except Exception:
            pass
        print(f"  Safety mode set to SILENT ({mode}) -> panda is listen-only, cannot TX.")
        return True
    except Exception as e:
        print(f"  WARNING: could not set SILENT mode ({e}); reading anyway (still no sends issued).")
        return False


def check_health(p):
    try:
        h = p.health()
        print("[4/5] Panda health check: OK")
        print(f"  Voltage: {h.get('voltage', 'N/A')} mV   Current: {h.get('current', 'N/A')} mA")
        print(f"  Safety mode: {h.get('safety_mode', 'N/A')}   Ignition line: {h.get('ignition_line', 'N/A')}")
        print(f"  Car harness status: {h.get('car_harness_status', 'N/A')}")
        return True
    except Exception as e:
        print(f"[4/5] Panda health check: FAILED ({e})")
        return False


def inventory(p, seconds):
    print(f"[5/5] Sniffing CAN for {seconds}s (READ ONLY, SILENT mode)...")
    print("  Tip: ignition ON (engine off is fine) gives full traffic.\n")
    # stats[bus][addr] = [count, first_t, last_t, dlc, last_data_hex]
    stats = {}
    start = time.monotonic()
    while (time.monotonic() - start) < seconds:
        for addr, _, data, bus in p.can_recv():
            now = time.monotonic()
            b = stats.setdefault(bus, {})
            rec = b.get(addr)
            if rec is None:
                b[addr] = [1, now, now, len(data), bytes(data).hex()]
            else:
                rec[0] += 1
                rec[2] = now
                rec[3] = len(data)
                rec[4] = bytes(data).hex()
        time.sleep(0.005)
    elapsed = time.monotonic() - start

    total = sum(rec[0] for b in stats.values() for rec in b.values())
    print(f"  captured {total} frames over {elapsed:.1f}s across {len(stats)} bus id(s)\n")

    # per-bus full ID inventory with measured Hz
    for bus in sorted(stats.keys()):
        ids = stats[bus]
        print(f"  --- bus {bus}  ({len(ids)} unique IDs) ---")
        print(f"    {'ID':>6} {'dec':>5} {'count':>6} {'Hz':>7} {'DLC':>3}  data(last)")
        for addr in sorted(ids.keys()):
            count, t0, t1, dlc, dhex = ids[addr]
            hz = count / elapsed if elapsed > 0 else 0.0
            print(f"    0x{addr:04X} {addr:>5} {count:>6} {hz:>7.1f} {dlc:>3}  {dhex}")
        print()

    # explicit frames-of-interest report
    def where(addr):
        hits = [(bus, ids[addr]) for bus, ids in stats.items() if addr in ids]
        if not hits:
            return None
        return [(bus, rec[0] / elapsed if elapsed > 0 else 0.0, rec[3]) for bus, rec in hits]

    print("  " + "=" * 66)
    print("  CAN FRAMES OF INTEREST (EPS telemetry planning)")
    print("  " + "=" * 66)
    print("  EPS frames that SHOULD be comma-visible:")
    for addr, name in EPS_COMMA_VISIBLE.items():
        w = where(addr)
        if w:
            s = ", ".join(f"bus {b} @ {hz:.1f}Hz dlc{dlc}" for b, hz, dlc in w)
            print(f"    0x{addr:04X} {name:<18}: PRESENT  {s}")
        else:
            print(f"    0x{addr:04X} {name:<18}: ABSENT   <-- unexpected; check ignition / harness")
    print("\n  EPS frames believed EPS-internal-only (telemetry can't use these):")
    for addr, name in EPS_INTERNAL_ONLY.items():
        w = where(addr)
        if w:
            s = ", ".join(f"bus {b} @ {hz:.1f}Hz dlc{dlc}" for b, hz, dlc in w)
            note = "  *** PRESENT -> reconsider: this frame COULD carry telemetry ***"
            print(f"    0x{addr:04X} {name:<24}: PRESENT {s}{note}")
        else:
            print(f"    0x{addr:04X} {name:<24}: ABSENT  (confirms internal-bus-only)")
    print()
    print("  Read the rates above: a telemetry frame must sit on a comma-visible bus")
    print("  at >=~50Hz for the ~90ms gentle-EME cut. 100Hz single-signal = ~9 samples.")
    return total > 0


def main():
    seconds = 10
    if len(sys.argv) > 1:
        try:
            seconds = max(1, int(sys.argv[1]))
        except ValueError:
            pass

    print("=" * 68)
    print("  Comma 4 Panda - CAN Bus INVENTORY  (read-only, SILENT/listen-only)")
    print("=" * 68 + "\n")

    results = {}
    results["spi"] = check_spi_device(); print()
    results["pandad"] = check_pandad_running(); print()
    if not results["spi"]:
        print("ABORT: no SPI device (run on a comma 3X/4)."); sys.exit(1)
    if not results["pandad"]:
        print("ABORT: pandad still running; stop openpilot first."); sys.exit(1)

    p, Panda = connect_panda(); print()
    results["connect"] = p is not None
    if p is None:
        print("ABORT: cannot connect to panda."); sys.exit(1)

    try:
        force_silent(p, Panda); print()
        results["health"] = check_health(p); print()
        results["can_read"] = inventory(p, seconds)
    finally:
        p.close()

    print("=" * 68)
    print("  RESULTS SUMMARY")
    print("=" * 68)
    for name, ok in results.items():
        print(f"  {name:12s}: {'PASS' if ok else 'FAIL'}")
    if all(results.values()):
        print("\n  ALL CHECKS PASSED - panda reachable, SILENT, and CAN traffic inventoried.")
    elif results.get("connect") and results.get("health"):
        print("\n  Panda reachable but little/no traffic - turn ignition ON and re-run.")


if __name__ == "__main__":
    main()
