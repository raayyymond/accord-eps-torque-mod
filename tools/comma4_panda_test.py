#!/usr/bin/env python3
"""
Comma 4 Panda CAN Bus Verification Script

Non-destructive read-only test to verify the comma 4's internal panda
is accessible and CAN bus traffic can be read before attempting any
EPS firmware flash operations.

Usage (run on the comma 4 via SSH):
  1. SSH in: ssh comma@192.168.43.1
  2. Kill openpilot: tmux kill-server
  3. Wait 2 seconds for panda release
  4. Run: python3 /data/comma4_panda_test.py

This script does NOT send any CAN messages. It is read-only.
"""

import sys
import time
import os

def check_spi_device():
    """Verify the SPI device exists."""
    spi_path = "/dev/spidev0.0"
    exists = os.path.exists(spi_path)
    print(f"[1/5] SPI device {spi_path}: {'FOUND' if exists else 'NOT FOUND'}")
    if not exists:
        print("  ERROR: SPI device missing. Is this a comma 4 / comma 3X?")
    return exists

def check_pandad_running():
    """Check if pandad is still running (it should NOT be)."""
    try:
        import subprocess
        result = subprocess.run(["pgrep", "-f", "pandad"], capture_output=True, text=True)
        running = result.returncode == 0
        if running:
            print("[2/5] pandad process: STILL RUNNING")
            print("  WARNING: pandad must be stopped first.")
            print("  Run: tmux kill-server")
            print("  Then wait 2 seconds and retry this script.")
        else:
            print("[2/5] pandad process: NOT RUNNING (good)")
        return not running
    except Exception as e:
        print(f"[2/5] pandad check: SKIPPED ({e})")
        return True

def connect_panda():
    """Attempt to connect to the internal panda."""
    try:
        from panda import Panda
    except ImportError:
        print("[3/5] Panda library: NOT FOUND")
        print("  Trying openpilot path...")
        sys.path.insert(0, "/data/openpilot/third_party/panda")
        sys.path.insert(0, "/data/openpilot")
        try:
            from panda import Panda
        except ImportError:
            print("  ERROR: Cannot import panda library.")
            print("  Ensure openpilot is installed at /data/openpilot")
            return None

    print("[3/5] Panda library: IMPORTED")

    p = None
    try:
        p = Panda()
        hw_type = p.get_type()
        serial = p.get_serial()

        hw_names = {
            b'\x07': "RED_PANDA",
            b'\x09': "TRES (comma 3X)",
            b'\x0a': "CUATRO (comma 4)",
        }
        hw_name = hw_names.get(hw_type, f"UNKNOWN ({hw_type.hex()})")

        print(f"  Hardware type: {hw_name}")
        print(f"  Serial: {serial[0] if serial else 'unknown'}")
        print(f"  Bootstub mode: {p.bootstub}")

        if p.bootstub:
            print("  WARNING: Panda is in bootstub mode, not running app firmware.")
            p.close()
            return None

        fw_version = p.get_version()
        print(f"  Firmware version: {fw_version}")

        return p
    except Exception as e:
        if p is not None:
            p.close()
        print(f"[3/5] Panda connection: FAILED")
        print(f"  Error: {e}")
        print("  Make sure pandad/openpilot is stopped (tmux kill-server)")
        return None

def check_health(p):
    """Read panda health to verify communication."""
    try:
        health = p.health()
        print("[4/5] Panda health check: OK")
        print(f"  Voltage: {health.get('voltage', 'N/A')} mV")
        print(f"  Current: {health.get('current', 'N/A')} mA")
        print(f"  Safety mode: {health.get('safety_mode', 'N/A')}")
        print(f"  Ignition line: {health.get('ignition_line', 'N/A')}")
        print(f"  Car harness status: {health.get('car_harness_status', 'N/A')}")
        return True
    except Exception as e:
        print(f"[4/5] Panda health check: FAILED ({e})")
        return False

def read_can_traffic(p, duration_seconds=5):
    """Read CAN bus traffic for a few seconds (read-only, no sends)."""
    print(f"[5/5] Reading CAN traffic for {duration_seconds} seconds (READ ONLY)...")
    print("  Tip: Turn ignition ON (engine off is fine) for more traffic.")

    bus_counts = {0: 0, 1: 0, 2: 0}
    total_messages = 0
    unique_ids = {0: set(), 1: set(), 2: set()}
    sample_messages = []

    start = time.monotonic()
    while (time.monotonic() - start) < duration_seconds:
        msgs = p.can_recv()
        for addr, _, data, bus in msgs:
            bus_idx = bus & 0x0F
            if bus_idx in bus_counts:
                bus_counts[bus_idx] += 1
                unique_ids[bus_idx].add(addr)
                total_messages += 1
                if len(sample_messages) < 5:
                    sample_messages.append((addr, bus_idx, data.hex()))
        time.sleep(0.01)

    print(f"\n  Total messages received: {total_messages}")
    for bus_idx in sorted(bus_counts.keys()):
        count = bus_counts[bus_idx]
        ids = len(unique_ids[bus_idx])
        print(f"  Bus {bus_idx}: {count} messages, {ids} unique CAN IDs")

    if sample_messages:
        print("\n  Sample messages (first 5):")
        for addr, bus, data in sample_messages:
            print(f"    Bus {bus} | ID 0x{addr:03X} | Data: {data}")
    elif total_messages == 0:
        print("\n  No CAN traffic detected.")
        print("  - Is the car's ignition ON?")
        print("  - Is the OBD-C cable connected?")
        print("  - Try: turn key to ACC or ON position.")

    return total_messages > 0

def main():
    print("=" * 60)
    print("  Comma 4 Internal Panda - CAN Bus Verification Test")
    print("  (Read-only, non-destructive)")
    print("=" * 60)
    print()

    results = {}

    results["spi"] = check_spi_device()
    print()
    results["pandad"] = check_pandad_running()
    print()

    if not results["spi"]:
        print("ABORT: No SPI device. This script must run on a comma 3X or 4.")
        sys.exit(1)

    if not results["pandad"]:
        print("ABORT: pandad is still running. Stop openpilot first.")
        sys.exit(1)

    p = connect_panda()
    results["connect"] = p is not None
    print()

    if p is None:
        print("ABORT: Cannot connect to panda.")
        sys.exit(1)

    try:
        results["health"] = check_health(p)
        print()
        results["can_read"] = read_can_traffic(p, duration_seconds=5)
    finally:
        p.close()

    print()
    print("=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    all_pass = all(results.values())
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:12s}: {status}")
    print()

    if all_pass:
        print("  ALL CHECKS PASSED")
        print("  The internal panda is accessible and CAN traffic is flowing.")
        print("  You should be able to run eps-update.py on this device.")
    elif results["connect"] and results["health"]:
        print("  PANDA ACCESSIBLE but no CAN traffic detected.")
        print("  Turn the car's ignition ON and re-run this script.")
    else:
        print("  SOME CHECKS FAILED - review errors above.")

if __name__ == "__main__":
    main()
