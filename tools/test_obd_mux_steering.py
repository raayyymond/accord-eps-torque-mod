#!/usr/bin/env python3
"""test_obd_mux_steering.py - does the comma keep steering feedback while STAYING
on OBD mux?  (read-only, SILENT, always restores the mux)

THE QUESTION (handoff 2026-07-12 §5a). On the comma 4 the EPS diagnostic server is
reachable ONLY via OBD multiplexing (bus 1 -> OBD-II), which is the SAME single
FDCAN2 peripheral that carries LKAS steering (399/427 feedback in, 228 command out).
So a live UDS poll during active LKAS is blocked UNLESS the comma can still steer
while the mux sits on OBD. This settles that -- read-only first.

WHAT IT DOES. One panda session, listen-only, two phases on bus 1:
  * Phase A (OBD OFF, control): confirm 399 (0x18F STEER_STATUS) + 427 (0x1AB
    MOTOR_TORQUE) ARE present -- proves the car is awake and the harness/ignition
    is live, so Phase B is interpretable.
  * Phase B (OBD ON, the test): flip OBD mux on and re-check the SAME two frames.
    openpilot's Honda control loop needs 399 (~100 Hz) + 427 for its state estimate
    and fault monitor; if they vanish, openpilot faults and cannot steer -- so their
    survival on bus 1 under mux is a necessary condition for "steer while on OBD".

PREDICTION: 399/427 ABSENT under OBD mux (boot data showed 399 vanishes from bus 1
when the mux swings FDCAN2 to the OBD-II diagnostic side). If confirmed, staying on
OBD cannot steer -> go to the red-panda-OBD-Y-splitter or firmware spare-bit path.
If they SURVIVE, that's the surprising/promising case -> warrants a careful ENGAGED
test (wheels safe) before trusting it.

SAFETY.
  * 100% READ-ONLY. The panda is forced into SAFETY_SILENT (listen-only) before any
    read, so it physically cannot transmit a CAN frame. No message is ever sent.
  * set_obd(True/False) is a panda RELAY/MUX config transfer, NOT a bus transmit --
    it flips which line FDCAN2 is wired to. It puts nothing on the CAN bus.
  * The mux is ALWAYS restored to OFF in a finally block (even on Ctrl-C / error).
  * This is the read-only FIRST step only. It does NOT engage LKAS. Deciding whether
    openpilot actually delivers torque while on OBD is a separate engaged test that
    is only warranted if this one shows the feedback survives.

USAGE (run on the comma 4 via SSH, openpilot stopped):
  1. ssh comma@192.168.43.1
  2. tmux kill-server            # release the panda from pandad/openpilot
  3. sleep 2
  4. ignition ON (engine off is fine) so the car broadcasts 399/427
  5. python3 /data/test_obd_mux_steering.py            # 8 s per phase
     python3 /data/test_obd_mux_steering.py --seconds 12
"""
import argparse
import os
import sys
import time

for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from panda import Panda
except Exception as e:  # noqa: BLE001
    print(f"[fatal] cannot import panda ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(2)

# The LKAS feedback frames openpilot's control loop needs on bus 1 to steer.
WATCH = {0x18F: "399 STEER_STATUS", 0x1AB: "427 MOTOR_TORQUE"}


def pandad_running():
    try:
        import subprocess
        return subprocess.run(["pgrep", "-f", "pandad"],
                              capture_output=True, text=True).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def recv_norm(panda):
    """Yield (addr, data_bytes, bus) tolerant of 3- or 4-tuple can_recv() shapes."""
    for m in panda.can_recv():
        if len(m) == 4:
            addr, _bt, dat, src = m
        else:
            addr, dat, src = m
        yield addr, bytes(dat), src & 0x0F


def sniff_phase(p, bus, seconds):
    """Listen `seconds` on `bus`. Return (counts{watch_id:n}, all_ids set, total)."""
    counts = {a: 0 for a in WATCH}
    all_ids = set()
    total = 0
    p.can_clear(0xFFFF)
    t0 = time.monotonic()
    while time.monotonic() - t0 < seconds:
        for addr, _dat, src in recv_norm(p):
            if src != bus:
                continue
            total += 1
            all_ids.add(addr)
            if addr in counts:
                counts[addr] += 1
        time.sleep(0.002)
    return counts, all_ids, total


def report_phase(label, counts, all_ids, total, seconds):
    print(f"  [{label}] {total} frames on the bus, {len(all_ids)} unique IDs")
    for addr, name in WATCH.items():
        n = counts[addr]
        hz = n / seconds if seconds > 0 else 0.0
        state = f"PRESENT {hz:5.1f} Hz" if n > 0 else "ABSENT"
        print(f"      0x{addr:04X} {name:<18}: {state}")
    return all(counts[a] > 0 for a in WATCH)


def main():
    ap = argparse.ArgumentParser(
        description="Does the comma keep 399/427 steering feedback while on OBD mux? (read-only)")
    ap.add_argument("--bus", type=int, default=1,
                    help="bus that carries EPS feedback (default 1 = F-CAN)")
    ap.add_argument("--seconds", type=float, default=8.0,
                    help="listen seconds per phase (default 8)")
    a = ap.parse_args()

    print("=" * 70)
    print("  OBD-mux steering-feedback test (read-only, SILENT, auto-restores mux)")
    print("=" * 70)
    print("  PREDICTION: 399/427 ABSENT on bus 1 once OBD mux is ON.\n")

    if pandad_running():
        print("[abort] pandad is still running -> run `tmux kill-server; sleep 2` first.")
        sys.exit(1)

    try:
        p = Panda(disable_checks=True)
    except TypeError:
        p = Panda()

    obd_on = False
    try:
        # listen-only: the panda physically cannot transmit from here on
        try:
            p.set_safety_mode(getattr(Panda, "SAFETY_SILENT", 0))
        except Exception as e:  # noqa: BLE001
            print(f"[warn] set_safety_mode(SILENT): {e} (still issuing no sends)")

        try:
            h = p.health()
            print(f"  panda: harness={h.get('car_harness_status', '?')} "
                  f"safety_mode={h.get('safety_mode', '?')} "
                  f"ignition={h.get('ignition_line', '?')}\n")
        except Exception:  # noqa: BLE001
            pass

        # --- Phase A: OBD OFF (control) --------------------------------------
        p.set_obd(False)
        time.sleep(0.3)
        print(f"--- Phase A: OBD mux OFF (baseline), {a.seconds:g}s on bus {a.bus} ---")
        ca, ida, ta = sniff_phase(p, a.bus, a.seconds)
        a_ok = report_phase("OBD off", ca, ida, ta, a.seconds)
        print()

        # --- Phase B: OBD ON (the test) --------------------------------------
        p.set_obd(True)
        obd_on = True
        time.sleep(0.3)
        print(f"--- Phase B: OBD mux ON (the test), {a.seconds:g}s on bus {a.bus} ---")
        cb, idb, tb = sniff_phase(p, a.bus, a.seconds)
        b_ok = report_phase("OBD on ", cb, idb, tb, a.seconds)
        print()

        # sample of what OBD mux exposes INSTEAD, if the feedback vanished
        if not b_ok and idb:
            shown = ", ".join(f"0x{i:03X}" for i in sorted(idb)[:12])
            print(f"  (bus {a.bus} under mux now shows: {shown}"
                  f"{' ...' if len(idb) > 12 else ''})\n")

    finally:
        # ALWAYS put the mux back, even on Ctrl-C / exception
        try:
            p.set_obd(False)
            if obd_on:
                print("[restore] OBD mux set back OFF.")
        except Exception as e:  # noqa: BLE001
            print(f"[restore] WARNING: could not restore OBD mux OFF: {e}")
        try:
            p.close()
        except Exception:  # noqa: BLE001
            pass

    # --- verdict -----------------------------------------------------------
    print("=" * 70)
    if not a_ok:
        print("  RESULT: INVALID -- 399/427 were NOT present even with OBD OFF.")
        print("  The car is asleep / ignition off / harness not seated. Phase B means")
        print("  nothing. Turn ignition ON (engine off is fine) and re-run.")
    elif b_ok:
        print("  RESULT: SURPRISE -- 399/427 SURVIVE under OBD mux (prediction WRONG).")
        print("  Feedback is still on bus 1 with the mux on OBD. This is the promising")
        print("  case: a live UDS poll during LKAS MIGHT be possible. NEXT = a careful")
        print("  ENGAGED test (wheels safe) of whether openpilot both delivers 228 and")
        print("  reads feedback while on OBD. If that holds, your eps_telemetry.py poller")
        print("  becomes the comma-native live-telemetry capability with no extra hardware.")
    else:
        print("  RESULT: CONFIRMED -- 399/427 VANISH under OBD mux (prediction held).")
        print("  Staying on OBD starves openpilot's steering feedback -> it cannot steer")
        print("  while on the mux. A software-only fork change cannot poll UDS during LKAS")
        print("  on the comma 4. Go to a live path that avoids the mux conflict:")
        print("    1. red panda on an independent OBD-II Y-splitter (comma steers F-CAN,")
        print("       red panda polls UDS on OBD-II; full bandwidth, no firmware change), or")
        print("    2. firmware spare-bit piggyback into gateway-forwarded 399/427/330.")
    print("=" * 70)


if __name__ == "__main__":
    main()
