#!/usr/bin/env python3
r"""sniff_fourframe.py - capture the FOURFRAME telemetry frames (0x6A0-0x6A3), SILENT / read-only.

WHY THIS EXISTS
    The FOURFRAME firmware cave transmits four NEW broadcast CAN IDs (0x6A0..0x6A3) at 62.5 Hz,
    each carrying four live 16-bit EPS RAM cells. Per
    memory/reference/can/reference-accord-can-tx-architecture-new-id.md the car's downstream gateway forwards
    only a per-ID WHITELIST to the comma's built-in panda -- EPS ID 0x19F is actively fired at
    62.5 Hz from the same mailbox as the visible 0x18F and still never reaches the comma. So these
    new IDs are expected to be INVISIBLE in a comma rlog and visible ONLY on a panda tapped
    directly on the EPS bus (see docs/guides/RED-PANDA-EPS-SETUP.md).

    This tool is that capture. It TRANSMITS NOTHING (SAFETY_SILENT), same class as
    tools/comma4_panda_test.py and tools/sniff_can_id.py -- safe to run any time after openpilot
    is killed (`tmux kill-server`).

USAGE
    python3 sniff_fourframe.py                       # 30 s, all buses, live decode
    python3 sniff_fourframe.py --seconds 120 --csv fourframe_drive.csv
    python3 sniff_fourframe.py --bus 1               # restrict to one bus
    python3 sniff_fourframe.py --raw-only            # just prove presence, skip decoding

    Then FFT the CSV offline with analysis-2020accord/decode_fourframe.py.

PAYLOAD LAYOUT (from builds/telemetry/build_vfourframe_tva.py's cave emitter, signal index i = 0..3)
    byte[2*i]   = HIGH byte of signal i        -> big-endian
    byte[2*i+1] = LOW  byte of signal i
    Each cell is read with `ld.hu` but the firmware cells are signed 16-bit; decode as s16.
"""
import argparse
import csv
import os
import sys
import time
from collections import Counter, defaultdict

for _p in ("/data/openpilot/third_party/panda", "/data/openpilot"):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from panda import Panda
except Exception as e:  # pragma: no cover - runs on the car, not in CI
    print(f"[fatal] cannot import panda ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------------------------
# Signal map -- mirrors MAILBOXES in analysis-2020accord/builds/telemetry/build_vfourframe_tva.py exactly.
# Two channels carry a documented data-quality caveat and are expected NOT to vary; they are
# kept so the frame layout matches the firmware one-for-one.
# ---------------------------------------------------------------------------------------------
FRAMES = {
    0x6A0: [("gp-0x6b98", "delivered_cmd"),
            ("gp-0x6acc", "shaper_in"),
            ("gp-0x6ace", "governor_out"),
            ("gp-0x6b94", "aggregator_sum")],
    0x6A1: [("gp-0x6b4c", "lkas_lane"),
            ("gp-0x6ad4", "resonance_lane"),
            ("gp-0x6bd0", "damping"),
            ("gp-0x6bbe", "boost")],
    0x6A2: [("gp-0x6b86", "magnitude"),
            ("gp-0x6b26", "friction"),
            ("gp-0x6b62", "return_centre"),
            ("gp-0x6ade", "feedforward_DEAD_CAVEAT")],
    0x6A3: [("gp-0x4f60", "raw_sensorB_torque"),
            ("gp-0x4f62", "torque_rate"),
            ("gp-0x69a4", "r26_gain_input"),
            ("gp-0x67ac", "aggreg_mode_ALWAYS0_CAVEAT")],
}
IDS = sorted(FRAMES)

# Positive controls: whitelisted EPS frames that a correct tap MUST also see.
CONTROL_IDS = {0x18F: "399 STEER_STATUS", 0x1AB: "427 MOTOR_TORQUE", 0x14A: "330"}


def s16(hi, lo):
    v = (hi << 8) | lo
    return v - 0x10000 if v & 0x8000 else v


def decode(addr, dat):
    """Return [(name, label, value_s16), ...] for a FOURFRAME payload."""
    out = []
    for i, (name, label) in enumerate(FRAMES[addr]):
        if 2 * i + 1 < len(dat):
            out.append((name, label, s16(dat[2 * i], dat[2 * i + 1])))
    return out


def recv_norm(panda):
    for m in panda.can_recv():
        if len(m) == 4:
            addr, _bt, dat, src = m
        else:
            addr, dat, src = m
        yield addr, bytes(dat), src & 0x0F


def main():
    ap = argparse.ArgumentParser(description="Capture FOURFRAME telemetry 0x6A0-0x6A3 (SILENT).")
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--bus", type=int, default=None,
                    help="restrict to one bus; default = accept any bus and report which")
    ap.add_argument("--csv", default=None, help="write decoded samples to this CSV")
    ap.add_argument("--raw-only", action="store_true", help="presence check only, no decode")
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

    busmsg = "any bus" if a.bus is None else f"bus {a.bus}"
    print(f"[watch] SILENT, {busmsg}, {a.seconds:g}s, looking for "
          f"{', '.join(f'0x{i:03X}' for i in IDS)}")
    print("        ---> DRIVE AND REPRODUCE THE VIBRATION NOW <---")

    counts = Counter()                 # (addr, bus) -> frames
    controls = Counter()               # (addr, bus) -> frames
    first_payload = {}                 # (addr, bus) -> hex
    rows = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < a.seconds:
        for addr, dat, src in recv_norm(p):
            if a.bus is not None and src != a.bus:
                continue
            if addr in CONTROL_IDS:
                controls[(addr, src)] += 1
                continue
            if addr not in FRAMES:
                continue
            t = time.monotonic() - t0
            counts[(addr, src)] += 1
            first_payload.setdefault((addr, src), dat.hex())
            if not a.raw_only:
                rows.append((t, addr, src, dat.hex(), decode(addr, dat)))

    dur = time.monotonic() - t0
    total = sum(counts.values())

    print(f"\n[controls] whitelisted EPS frames seen (these prove the tap works):")
    if not controls:
        print("    NONE. The tap is not on a bus carrying EPS frames -- fix this before "
              "trusting any absence result below.")
    for (addr, bus), n in sorted(controls.items()):
        print(f"    0x{addr:03X} ({CONTROL_IDS[addr]}) bus {bus}: {n} frames, {n/dur:.1f} Hz")

    print(f"\n[result] {total} FOURFRAME frames in {dur:.1f}s")
    if total == 0:
        print("    ABSENT. Either (a) this tap is downstream of the gateway that drops "
              "non-whitelisted IDs, (b) the cave's TX gates never opened, or (c) the "
              "FOURFRAME image is not the one running.")
        print("    If the controls above DID appear on a red panda wired directly to the EPS "
              "bus, then (a) is excluded and the cave itself is the suspect.")
        return
    for (addr, bus), n in sorted(counts.items()):
        print(f"    0x{addr:03X} bus {bus}: {n} frames, {n/dur:.1f} Hz "
              f"(expect ~62.5)   first={first_payload[(addr, bus)]}")

    missing = [i for i in IDS if not any(k[0] == i for k in counts)]
    if missing:
        print(f"    ⚠ MISSING: {', '.join(f'0x{i:03X}' for i in missing)} -- a partial set means "
              f"the cave ran but some mailbox did not fire.")

    if a.raw_only or not rows:
        return

    print("\n[decode] last sample of each frame:")
    seen = set()
    for t, addr, bus, _h, sig in reversed(rows):
        if addr in seen:
            continue
        seen.add(addr)
        print(f"  0x{addr:03X} @ {t:6.2f}s")
        for name, label, val in sig:
            print(f"      {name:>10s}  {label:<28s} {val:7d}")

    spans = defaultdict(lambda: [None, None])
    for _t, addr, _bus, _h, sig in rows:
        for name, _label, val in sig:
            lo, hi = spans[name]
            spans[name] = [val if lo is None else min(lo, val),
                           val if hi is None else max(hi, val)]
    print("\n[liveness] per-signal value span over the capture "
          "(span 0 = constant; expected for the two CAVEAT channels):")
    for addr in IDS:
        for name, label in FRAMES[addr]:
            if name in spans:
                lo, hi = spans[name]
                flag = "" if hi > lo else "   <-- CONSTANT"
                print(f"    {name:>10s} {label:<28s} {lo:7d}..{hi:7d}{flag}")

    if a.csv:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            hdr = ["t", "addr", "bus"]
            for addr in IDS:
                hdr += [lbl for _n, lbl in FRAMES[addr]]
            w.writerow(hdr)
            for t, addr, bus, _h, sig in rows:
                row = [f"{t:.6f}", f"0x{addr:03X}", bus]
                row += [""] * sum(len(FRAMES[i]) for i in IDS if i < addr)
                row += [v for _n, _l, v in sig]
                w.writerow(row)
        print(f"\n[csv] wrote {len(rows)} samples -> {a.csv}")
        print("      FFT it with analysis-2020accord/decode_fourframe.py")


if __name__ == "__main__":
    main()
