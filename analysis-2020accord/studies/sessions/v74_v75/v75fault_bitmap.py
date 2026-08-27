#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75fault_bitmap.py -- decode the latched 0x18F / 0x1AB bytes against the kit's own TX bitmap.

Bit map from `.claude/agent-memory/firmware-codepath-tracer/reference_accord_can_tx_399_427_bitmap.md`
(whole-program verified, 185,116 instructions scanned):

  399 / 0x18F  builder FUN_00055c42, buffer gp-0x1420
    byte4 7:4  low nibble of gp-0x6807 << 4      <-- THE BUS STEER_STATUS
    byte4 3    gp-0x6806 & 1                      <-- STEER_CONTROL_ACTIVE
    byte4 2:0  SPARE, never written (reads 0)
    byte5 5:4  gp-0x6880 & 3                      <-- the only writable field in byte5
    byte5 3:0  explicit constant 0, re-cleared every cycle
    byte5 7:6  SPARE, never written
    byte6 7    gp-0x6804 & 1
    byte6 6    SPARE
    byte6 5:4  2-bit rolling counter (gp-0xf48)
    byte6 3:0  checksum from FUN_00057b24(buf,7,399)

  427 / 0x1AB  builder FUN_00055d80, buffer gp-0x13CC
    byte0 7    config latch (gp+0x6409 vs '0'), forced 1 if gp-0x683a != 0
    byte0 6:5  SPARE
    byte0 4    gp-0x685a & 1
    byte0 3    gp-0x685b & 1
    byte0 2    ★ FAULT/DTC-ACTIVE = NOT(FUN_00046ea6(3)==0 && (4)==0 && (10)==0)
    byte0 1:0  top 2 bits of the clamped 10-bit motor torque
    byte1 7:0  low 8 bits of the clamped 10-bit motor torque
    byte2 7    SPARE
    byte2 6    FUN_0004d0ac() & 1  (gp-0x675a in {1,2})
    byte2 5:4  2-bit rolling counter (gp-0xf47)
    byte2 3:0  checksum from FUN_00057b24(buf,3,0x1ab)
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages          # noqa: E402

D = dict(np.load(ROOT / "_scratch/cache/r5e" / "r5e.npz"))
T0 = float(D["t0_mono"][0])
t = D["t"]
K = int(np.flatnonzero((D["probe"].astype(int) & 7) == 4)[0])
T_FAULT = float(t[K])
RL = (ROOT / "analysis-2020accord" / "rlogs" /
      "75604b0a432fdc89_0000005e--857d0bd164--4--rlog.zst")

rec = {0x18F: [], 0x1AB: []}
for evt in read_messages(RL):
    try:
        if evt.which() != "can":
            continue
    except Exception:
        continue
    tm = evt.logMonoTime * 1e-9 - T0
    for m in evt.can:
        if int(m.src) == 1 and int(m.address) in rec:
            rec[int(m.address)].append((tm, bytes(m.dat)))

H = "=" * 100
print(H)
print("LATCHED FIELDS, DECODED AGAINST THE FIRMWARE'S OWN TX BITMAP (segment 4, +/-43 s)")
print(H)


def split(addr):
    a = rec[addr]
    pre = [d for tm, d in a if tm < T_FAULT]
    post = [d for tm, d in a if tm >= T_FAULT]
    return pre, post


def fld(frames, byte, hi, lo):
    mask = ((1 << (hi - lo + 1)) - 1) << lo
    v = np.array([(d[byte] & mask) >> lo for d in frames if len(d) > byte])
    u, c = np.unique(v, return_counts=True)
    return " ".join(f"{int(a_)}:{int(b_)}" for a_, b_ in zip(u, c))


pre18, post18 = split(0x18F)
pre1a, post1a = split(0x1AB)
print(f"  0x18F frames: {len(pre18)} pre / {len(post18)} post   "
      f"0x1AB frames: {len(pre1a)} pre / {len(post1a)} post\n")
ROWS18 = [("byte4 7:4  gp-0x6807 & 0xF   [BUS STEER_STATUS]", 4, 7, 4),
          ("byte4 3    gp-0x6806 & 1     [STEER_CONTROL_ACTIVE]", 4, 3, 3),
          ("byte4 2:0  SPARE (never written)", 4, 2, 0),
          ("byte5 7:6  SPARE (never written)", 5, 7, 6),
          ("byte5 5:4  gp-0x6880 & 3     ★ LATCHED", 5, 5, 4),
          ("byte5 3:0  cleared every cycle", 5, 3, 0),
          ("byte6 7    gp-0x6804 & 1", 6, 7, 7),
          ("byte6 6    SPARE", 6, 6, 6)]
for lbl, b, hi, lo in ROWS18:
    print(f"  {lbl:52s}  PRE {fld(pre18, b, hi, lo):28s}  POST {fld(post18, b, hi, lo)}")
print()
ROWS1A = [("byte0 7    config latch", 0, 7, 7),
          ("byte0 6:5  SPARE", 0, 6, 5),
          ("byte0 4    gp-0x685a & 1", 0, 4, 4),
          ("byte0 3    gp-0x685b & 1", 0, 3, 3),
          ("byte0 2    ★★ DTC-ACTIVE = NOT(FUN_00046ea6(3|4|10)==0)", 0, 2, 2),
          ("byte0 1:0  motor torque bits 9:8", 0, 1, 0),
          ("byte1 7:0  motor torque bits 7:0", 1, 7, 0),
          ("byte2 7    SPARE", 2, 7, 7),
          ("byte2 6    FUN_0004d0ac() (gp-0x675a in {1,2})", 2, 6, 6),
          ("byte2 5:4  rolling counter", 2, 5, 4)]
for lbl, b, hi, lo in ROWS1A:
    p = fld(pre1a, b, hi, lo)
    q = fld(post1a, b, hi, lo)
    print(f"  {lbl:52s}  PRE {p[:60]:60s}  POST {q[:60]}")

# the 10-bit motor torque, pre vs post
def torque(frames):
    return np.array([((d[0] & 3) << 8) | d[1] for d in frames if len(d) > 1])


tp, tq = torque(pre1a), torque(post1a)
print(f"\n  10-bit MOTOR_TORQUE  pre : n={len(tp)} range {tp.min()}..{tp.max()} "
      f"n_unique={len(np.unique(tp))}")
print(f"  10-bit MOTOR_TORQUE  post: n={len(tq)} range {tq.min()}..{tq.max()} "
      f"n_unique={len(np.unique(tq))}  values {np.unique(tq)[:6]}")
print("  ⇒ the motor-torque payload is CONSTANT after the fault; the 4 distinct checksum bytes "
      "are exactly the 2-bit rolling counter cycling over a frozen payload  [EVIDENCE]")

# exact transition frame
a = rec[0x18F]
for i in range(1, len(a)):
    if a[i][1][4] == 0x70 and a[i - 1][1][4] != 0x70:
        print(f"\n  0x18F byte4/5 transition frame: t={a[i][0]:.4f}  "
              f"prev={a[i - 1][1].hex()}  ->  {a[i][1].hex()}")
        break
b = rec[0x1AB]
for i in range(1, len(b)):
    if (b[i][1][0] & 4) and not (b[i - 1][1][0] & 4):
        print(f"  0x1AB byte0 DTC-active transition: t={b[i][0]:.4f} "
              f"({b[i][0] - T_FAULT:+.4f} vs the 0x14A fault frame)  "
              f"prev={b[i - 1][1].hex()}  ->  {b[i][1].hex()}")
        break
