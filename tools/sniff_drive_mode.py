#!/usr/bin/env python3
"""
sniff_drive_mode.py — READ-ONLY CAN sniffer to find the Honda Civic drive-mode / ECON signal.

Run with a RED PANDA plugged into the car's OBD-II port, USB to the laptop (via WSL).
This script ONLY LISTENS. It forces the panda into SAFETY_SILENT (no transmit) and never
calls can_send — it cannot put anything on the car's bus.

Goal: find which CAN (bus, address, byte) changes when you press the ECON button.
Prior finding (from comma rlog): 0x221 ECON_STATUS, real data appears to live in BYTE 0
(0x21 vs 0x22); the opendbc bit positions are wrong for this car. Confirm live here.

Modes
-----
  watch  : print a target address whenever its payload changes (default 0x221).
           -> Toggle ECON a few times during the window; watch byte 0 flip.
  scan   : over the whole window, report every (bus, addr, byte) that took a SMALL number
           of distinct values (button-like). Finds the eco signal even if it is NOT 0x221.
  record : dump every frame to a JSONL file for offline analysis.

Usage (inside WSL, red panda attached via usbipd)
-------------------------------------------------
  python3 sniff_drive_mode.py watch  --addr 0x221 --secs 30
  python3 sniff_drive_mode.py scan   --secs 25
  python3 sniff_drive_mode.py record --secs 30 --out /mnt/c/claudecode/firmware-analysis-kit/tools/econ_cap.jsonl

Tip: ignition ON (engine off is fine) so the bus is live. Press ECON on/off ~3-4 times
during the window, spaced ~2 s apart.
"""
import argparse, json, sys, time


def open_panda():
    try:
        from panda import Panda
    except ImportError:
        sys.exit("panda library not found — run inside the WSL env from EPS-FLASH-RUNBOOK (pip install libusb1; the sunnypilot_eps/panda or openpilot/panda).")
    p = Panda()
    hw = p.get_type()
    names = {b'\x07': "RED_PANDA", b'\x09': "TRES (comma 3X)", b'\x0a': "CUATRO (comma 4)"}
    print(f"panda: {names.get(hw, hw.hex())}  serial={ (p.get_serial() or ['?'])[0] }  bootstub={p.bootstub}")
    if p.bootstub:
        p.close(); sys.exit("panda is in bootstub mode (recovery) — not running app firmware.")
    # HARD READ-ONLY: silent safety mode = panda will not transmit anything.
    p.set_safety_mode(Panda.SAFETY_SILENT)
    h = p.health()
    print(f"health: safety_mode={h.get('safety_mode')}  ignition_line={h.get('ignition_line')}  voltage={h.get('voltage')}mV")
    print("(SAFETY_SILENT = listen-only; this script never transmits.)\n")
    return p


def recv(p):
    for addr, _, data, bus in p.can_recv():
        yield addr, bytes(data), (bus & 0x0F)


def mode_watch(p, addr, secs):
    print(f"WATCH 0x{addr:03X} for {secs}s — toggle ECON now (on/off a few times)...\n")
    last = {}
    t0 = time.monotonic()
    while time.monotonic() - t0 < secs:
        for a, d, bus in recv(p):
            if a != addr:
                continue
            key = bus
            if last.get(key) != d:
                t = time.monotonic() - t0
                b0 = d[0] if d else None
                print(f"  [{t:6.1f}s] bus{bus} 0x{a:03X}  {d.hex():<16}  byte0=0x{b0:02X}" if b0 is not None
                      else f"  [{t:6.1f}s] bus{bus} 0x{a:03X}  (empty)")
                last[key] = d
        time.sleep(0.005)
    print("\nDone. If byte0 flipped in sync with your ECON presses, that's the signal.")


def mode_scan(p, secs):
    print(f"SCAN all buses for {secs}s — toggle ECON ~3-4 times, spaced out...\n")
    perbyte = {}   # (bus,addr) -> list[set] of values per byte index
    seen_payloads = {}  # (bus,addr) -> set of full payloads
    t0 = time.monotonic()
    while time.monotonic() - t0 < secs:
        for a, d, bus in recv(p):
            if len(d) > 8:
                continue
            k = (bus, a)
            seen_payloads.setdefault(k, set()).add(d.hex())
            sets = perbyte.setdefault(k, [set() for _ in range(8)])
            for i, byte in enumerate(d):
                sets[i].add(byte)
        time.sleep(0.005)

    print("Button-like candidates — (bus,addr) byte positions with 2-6 distinct values:")
    print("(counters look like {0,1,2,3} sequential; a button looks like 2 distinct values)\n")
    hits = []
    for (bus, a), sets in perbyte.items():
        npayloads = len(seen_payloads[(bus, a)])
        if npayloads > 16:   # skip high-entropy sensor/counter spam
            continue
        for i, vals in enumerate(sets):
            if 2 <= len(vals) <= 6:
                hits.append((bus, a, i, sorted(vals), npayloads))
    # sort: fewest distinct values first (cleanest buttons), then by addr
    hits.sort(key=lambda x: (len(x[3]), x[1], x[2]))
    for bus, a, i, vals, npay in hits[:40]:
        vstr = " ".join(f"0x{v:02X}" for v in vals)
        flag = "  <== 0x221 (known candidate)" if a == 0x221 else ""
        print(f"  bus{bus} 0x{a:03X} byte{i}: {{{vstr}}}  ({npay} payloads){flag}")
    if not hits:
        print("  (no low-distinct-value bytes seen — was the bus live? did you toggle ECON?)")
    print("\nReport these lines back. The ECON signal is the byte whose value flips with the button.")


def mode_record(p, secs, out):
    print(f"RECORD all frames for {secs}s -> {out}\n")
    n = 0
    t0 = time.monotonic()
    with open(out, "w") as f:
        while time.monotonic() - t0 < secs:
            for a, d, bus in recv(p):
                f.write(json.dumps({"t": round(time.monotonic() - t0, 4), "bus": bus,
                                    "addr": a, "hex": d.hex()}) + "\n")
                n += 1
            time.sleep(0.005)
    print(f"wrote {n} frames to {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    w = sub.add_parser("watch"); w.add_argument("--addr", default="0x221"); w.add_argument("--secs", type=int, default=30)
    s = sub.add_parser("scan");  s.add_argument("--secs", type=int, default=25)
    r = sub.add_parser("record"); r.add_argument("--secs", type=int, default=30); r.add_argument("--out", required=True)
    args = ap.parse_args()

    p = open_panda()
    try:
        if args.mode == "watch":
            mode_watch(p, int(args.addr, 0), args.secs)
        elif args.mode == "scan":
            mode_scan(p, args.secs)
        elif args.mode == "record":
            mode_record(p, args.secs, args.out)
    finally:
        p.close()
        print("\npanda closed.")


if __name__ == "__main__":
    main()
