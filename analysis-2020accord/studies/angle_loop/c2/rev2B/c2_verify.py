# -*- coding: utf-8 -*-
r"""c2_verify.py -- C2 rev2-B (reviser 2) re-verification of the PRIMARY (D2a) and FALLBACK (B0r) edit sets.

ANALYSIS ONLY.  Builds nothing on disk, flashes nothing, sends nothing; the fork is not touched.

C2 rev2-B does NOT re-implement the assembler.  The adversarial-pass graft (JUDGE-bytes-risk graft #5) is that the
D-structure verification toolchain (two-pass ds_asm, 27 encoding-form controls against V295, the H1 interpreter at
0/60000, the ds_bytes full diff) is the bar for whichever cave is cut.  This script RE-RUNS that verified toolchain on
the two caves C2 rev2-B adopts, and asserts, independently of the design doc:
  1. the cave assembles to the EXACT bytes recorded in ds_cave_D2a.hex / ds_cave_B0r.hex (sha256 compare);
  2. applying the edits to the V295 image (sha asserted) yields a full diff with NO unlisted byte;
  3. the cave does NOT write r25 (the gp-0x6803==2 flag, live across the hook -- confirmed in Ghidra this session:
     setfe r25 @0x29A82, read @0x29B72/0x29C4E/0x29FDE/0x2A0AC) or any other live register at the hook;
  4. D2a's fresh-rate read carries Honda's validity guard INSIDE the assembled cave bytes (not just the prose):
     the sequence addi 13000 / movea 26000 / cmp / cmovh r0,r26,r26 is present, so op:=0 on the 0x7FFF sentinel.

usage:  python c2_verify.py
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent
DS = HERE.parents[1] / "panel" / "D-structure"
for _p in (str(DS),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ds_asm as A        # noqa: E402  the two-pass assembler + H1 interpreter test
import ds_bytes as B      # noqa: E402  applies the edits to V295, full diff
import ds_final as F      # noqa: E402  the candidate parameters (one source of truth)

PRIMARY, FALLBACK = "D2a", "B0r"
RECORDED = {
    "D2a": "caa6f39c2ba57f05",      # ds_cave_D2a.hex sha256[:16] (ds_bytes_out.txt)
    "B0r": "6627e4017f2a199c",      # ds_cave_B0r.hex
}
# Live registers across the hook 0x29D76 that a cave must NOT clobber (Ghidra + tracer, this session):
#   r25 (gp-0x6803==2 flag), r12 (Kp/Kd selector base), r10 (DB), r7 (Kp key).  ds_asm declares each cave's clobber set.
LIVE_AT_HOOK = {7, 10, 12, 25}


def _hex_bytes(cid):
    p = DS / f"ds_cave_{cid}.hex"
    return bytes(int(x, 16) for x in p.read_text().split())


def verify(cid):
    tbl = F.tables()[cid]
    # (1) assemble via the verified two-pass assembler, compare to the recorded hex
    code, labels, lines = A.assemble(cid if cid not in ("D1a", "B0r") else "B0", tbl)
    cave = bytes(code)
    recorded = _hex_bytes(cid)
    sha = hashlib.sha256(cave).hexdigest()
    ok_hex = (cave == recorded)
    ok_sha = sha.startswith(RECORDED[cid])
    # (2) full diff on the image
    img, listing, cave2, _ = B.build(cid, tbl)
    import struct  # noqa
    V = B.V
    diff = [a for a in range(0x13000, 0x100000) if img[a] != V[a]]
    listed = set()
    for kind, a, old, new, dec, term in listing:
        n = len(bytes.fromhex(old.replace(" ", "")))
        listed |= {a + i for i in range(n) if img[a + i] != V[a + i]}
    cave_set = {a for a in range(A.CAVE, A.CAVE + len(cave2)) if img[a] != V[a]}
    unlisted = [hex(a) for a in diff if a not in listed and a not in cave_set]
    # (3) clobber set (ds_asm.SCRATCH = the registers the cave writes) vs live registers at the hook
    clob = set(A.SCRATCH["B0" if cid in ("B0r", "D1a") else cid])
    live_hit = sorted(clob & LIVE_AT_HOOK)
    # (4) D2a validity guard present in the assembled cave bytes
    guard = bytes.fromhex("1a 46 c8 32 20 6e 90 65 ed 41 e0 d7 36 d3".replace(" ", ""))
    has_guard = guard in cave
    return dict(cid=cid, sha=sha, ok_hex=ok_hex, ok_sha=ok_sha, n_diff=len(diff),
                unlisted=unlisted, clob=sorted(clob), live_hit=live_hit, has_guard=has_guard, nbytes=len(cave))


def main():
    print(f"PRIMARY = {PRIMARY}   FALLBACK = {FALLBACK}\n")
    allok = True
    for cid in (PRIMARY, FALLBACK):
        r = verify(cid)
        print(f"== {cid} ({F.CANDS[cid].name}) ==")
        print(f"   cave {r['nbytes']} B  sha256 {r['sha'][:16]}  == recorded hex: {r['ok_hex']}  sha match: {r['ok_sha']}")
        print(f"   full diff {r['n_diff']} B over [0x13000,0x100000)  UNLISTED: {r['unlisted'] or 'none'}")
        print(f"   cave clobber set {r['clob']}  live-reg hits at hook {r['live_hit'] or 'NONE'}")
        if cid == "D2a":
            print(f"   fresh-rate validity guard present in assembled bytes: {r['has_guard']}")
        ok = (r["ok_hex"] and r["ok_sha"] and not r["unlisted"] and not r["live_hit"]
              and (r["has_guard"] if cid == "D2a" else True))
        print(f"   VERDICT: {'PASS' if ok else 'FAIL'}\n")
        allok &= ok
    print("ALL CHECKS PASS" if allok else "SOME CHECKS FAILED")
    return allok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
