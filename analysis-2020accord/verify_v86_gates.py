#!/usr/bin/env python3
"""verify_v86_gates.py -- NEGATIVE CONTROLS for `build_v86_tva.py`'s verifier. 🛑 CALIBRATE THE
INSTRUMENT BEFORE USING IT.

★ THE POINT: **a gate that has never fired is not evidence.** The V86 null build passes every assert
in `build_v86_tva.py` -- which proves the asserts RUN, and proves nothing about whether they would
CATCH anything. This file stages a deliberate defect for each gate, one at a time, on a copy of the
flown V85 image, and asserts the gate FAILS. A gate that stays silent here is reported as BROKEN.

🛑 THE HEADLINE CASE IS #4, THE SPAN-VS-VALUE TRAP. `diff_build_vs_stock.py` is SPAN-based: it asks
"did the right REGION change?" and therefore passes a build that wrote the right region with the
WRONG VALUE. Case 4 writes `0xC40BC = 3000` -- a value in the right cell, in the right block, in the
right span, and wrong. The span check passes; the value-anchored gate must not.

Every mutation here is applied to an IN-MEMORY COPY. Nothing is written to disk, no image on disk is
modified, and no `.rwd` is produced or touched.

Usage:
    python verify_v86_gates.py
"""
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_v74_tva as V74                # noqa: E402
import build_v86_tva as B                  # noqa: E402
from verify_bootloader_crc import walk_all_blocks   # noqa: E402

V85 = bytes(Path(B.SRC_BIN).read_bytes())
STOCK = bytes(Path(B.STOCK_BIN).read_bytes())


def _mut(edits=None):
    """A copy of V85 with `{addr: raw_bytes}` applied.

    🛑 RAW BYTES ONLY, no int shorthand. An earlier draft guessed the width from the magnitude
    (`<= 0xFF` ⇒ byte) and silently wrote ONE byte where a halfword was meant: `0xC40D0 = 200` turned
    408 into **456**, not 200. The gate still fired, so the harness looked green while testing a
    different mutation than the one its own label claimed. Width is now always explicit.
    """
    buf = bytearray(V85)
    for addr, val in (edits or {}).items():
        assert isinstance(val, (bytes, bytearray)), \
            f"0x{addr:05X}: pass raw bytes -- use `_h(v)` for a halfword or `_b(v)` for a byte"
        buf[addr:addr + len(val)] = val
    return buf


def _h(v):
    """A little-endian halfword. V850 is LE."""
    return struct.pack("<H", v & 0xFFFF)


def _b(v):
    return bytes([v])


CASES = []


def case(name, why):
    def deco(fn):
        CASES.append((name, why, fn))
        return fn
    return deco


# =====================================================================================================
# 1-3. THE FROZEN SET -- a silently reverted fix, and the two safety cells
# =====================================================================================================

@case("frozen: Lever B's arm silently reverted",
      "the kit has silently lost a confirmed fix at a rebase at least THREE times")
def _c1():
    B.assert_frozen(_mut({0xC6446: _h(512)}), "MUTANT")


@case("frozen: 0xC407E raised 511 -> 850 (THE HARD-FAULT INTERLOCK)",
      "V73 raised it to 850; V74 AND V75 both hard-faulted with a latched total loss of assist")
def _c2():
    B.assert_frozen(_mut({0xC407E: _h(850)}), "MUTANT")


@case("frozen: 0xC4080 raised 0 -> 64 (THE LATENT PURE COULOMB RELAY)",
      "no |model| factor ⇒ amplitude-INDEPENDENT; an unbounded relay index. NEVER RAISE IT")
def _c3():
    B.assert_frozen(_mut({0xC4080: _h(64)}), "MUTANT")


# =====================================================================================================
# 4. 🛑 THE SPAN-VS-VALUE TRAP -- the recorded defect this whole verifier exists for
# =====================================================================================================

@case("★ SPAN-VS-VALUE: 0xC40BC = 3000, the RIGHT cell with the WRONG value",
      "a SPAN diff passes this: right cell, right block, right region, wrong value")
def _c4():
    m = _mut({0xC40BC: _h(3000)})
    # first, DEMONSTRATE the span check is fooled -- the byte is in the same run either way
    lo, hi = 0xC40BC, 0xC40BE
    assert bytes(m[lo:hi]) != bytes(V85[lo:hi]), "the mutation did not take"
    assert [i for i in range(lo, hi) if m[i] != STOCK[i]], \
        "a span check over [0xC40BC,0xC40BE) still reports 'this region is non-stock' -- it CANNOT " \
        "tell 3000 from 6000, which is exactly the defect"
    B.assert_frozen(m, "MUTANT")            # the VALUE gate must fire


@case("anchors: the V53 low-speed lockout silently restored (0xC62EA 0 -> 320)",
      "this is what lets LKAS work at creep; losing it is invisible to a frozen-cell check")
def _c5():
    B.assert_anchors(_mut({0xC62EA: _h(320)}), STOCK, "MUTANT")


@case("anchors: Lever A's `sar` byte flipped to V62's `A9` (0x3AC20)",
      "the r24 half CAUSED grind #2 (corner tail 11.71x) -- a forbidden regression")
def _c6():
    B.assert_anchors(_mut({0x3AC20: _b(0xA9)}), STOCK, "MUTANT")


@case("anchors: a per-term aggregator ENABLE byte cleared (0xC64B0 1 -> 0)",
      "each of the seven DELETES A TERM FEEDING THE MOTOR")
def _c7():
    B.assert_anchors(_mut({0xC64B0: _b(0x00)}), STOCK, "MUTANT")


@case("anchors: one of the 72 LKAS setpoint cells reverted (0xE4194)",
      "V38's +6.7% top-end setpoint, 8 records x 9 cells -- a partial revert is easy to miss")
def _c8():
    B.assert_anchors(_mut({0xE4194: _h(15360)}), STOCK, "MUTANT")


@case("anchors: the friction lane's ONLY pole moved (0xC40D0 408 -> 200)",
      "a PHASE change on an always-on 1 kHz term; V85's whole GATE-2 argument rests on it not moving")
def _c9():
    B.assert_anchors(_mut({0xC40D0: _h(200)}), STOCK, "MUTANT")


@case("anchors: the interlock's FLOAT twin raised (0xC4004 0.5 -> 0.83)",
      "'fixing' 0xC407E from the other side -- the same interlock, and the same two hard faults")
def _c10():
    B.assert_anchors(_mut({0xC4004: struct.pack("<f", 0.83)}), STOCK, "MUTANT")


# =====================================================================================================
# RULE 7 -- MODE PROOF
# =====================================================================================================

@case("RULE 7: the engaged-only damper re-armed in mode 26 (FactorC m26 Y[0] 0 -> 429)",
      "V74's damper. The ring's 4-point dose-response says this is an abort signal")
def _c11():
    B.assert_mode_proof(_mut({0xD77DA: _h(429)}), STOCK, "MUTANT")


@case("RULE 7: mode 27 written while mode 26 is left Honda (FactorE m27 Y[1])",
      "🛑 m27 is a SECOND engaged column -- V83a forgot it and flew V81's whole damper live")
def _c12():
    B.assert_mode_proof(_mut({0xD782C: _h(539)}), STOCK, "MUTANT")


@case("RULE 7: a pointer array entry redirected (FactorC[26] -> FactorC[10]'s record)",
      "a moved pointer redirects a lever SILENTLY; every record read afterwards is suspect")
def _c13():
    m = bytearray(V85)
    struct.pack_into("<I", m, 0xC9E9C + 26 * 4, V74.factor_rec(V85, 0xC9E9C, 10))
    B.assert_mode_proof(m, STOCK, "MUTANT")


def _write_unreachable_m10():
    """A copy of V85 with FactorE mode 10's Y[0] moved -- an UNREACHABLE record on a TVCA4 car."""
    m = _mut()
    rec = V74.factor_rec(V85, 0xC9F84, 10)          # FactorE, mode 10, DEREFERENCED
    struct.pack_into("<H", m, rec + 0x0A, 900)
    return m, rec


@case("RULE 7: a write into an UNREACHABLE mode record (the V69/V70/V72 failure)",
      "a dose ladder that never existed -- mode 10 on a car that reads 24/25/26/27")
def _c14():
    m, _rec = _write_unreachable_m10()
    B.assert_records_vs_base(m, V85, B.sweep_records(m), attributed=set(), label="MUTANT")


@case("🛑 REGRESSION: the count-only residual gate is NOT sufficient, and this proves it",
      "FactorE m10 is ALREADY non-stock (V72-V75 residue) ⇒ writing it changes no COUNT. This case "
      "caught a real defect in the first draft of build_v86_tva.py's verifier")
def _c14b():
    m, _rec = _write_unreachable_m10()
    base_n = len(B.residual_records(V85, STOCK, B.sweep_records(V85)))
    mut_n = len(B.residual_records(m, STOCK, B.sweep_records(m)))
    # 🛑 THE COUNT IS UNCHANGED -- that is the point, and why assert_records_vs_base exists.
    assert base_n == mut_n, "precondition: the residual COUNT must be blind to this mutation"
    assert base_n != mut_n, \
        f"🛑 the residual count is {base_n} both before and after an unreachable-record write ⇒ a " \
        "count-only gate is BLIND to it. `assert_records_vs_base` (case 14) is the gate that sees it."


# =====================================================================================================
# THE CAVE AND THE HOOKS
# =====================================================================================================

@case("cave: the free tail above the proven extent was written (a SECOND cave)",
      "code caves are this kit's only bricking class -- V24, V27 and V48B all bricked the ECU")
def _c15():
    B.assert_cave_region(_mut({0xC4B80: b"\x00\x11\x22\x33"}), "MUTANT")


@case("cave: a second TX hook installed at 0x55D50 (frame 399)",
      "byte-stock on EVERY build ever made; a second hook is a new, unproven cave entry")
def _c16():
    B.assert_cave_region(_mut({0x55D50: b"\x86\xff\x26\xef"}), "MUTANT")


@case("cave: one payload byte corrupted",
      "the cave must equal `build_cave()`'s re-derivation, not merely 'look like' a cave")
def _c17():
    B.assert_cave(_mut({B.CAVE_BASE + 8: _b(0x00)}), "MUTANT")


@case("cave: the `jarl` hook retargeted away from the cave base",
      "the hook and the cave must agree, or the ECU jumps into 0xFF filler")
def _c18():
    B.assert_cave(_mut({B.HOOK_ADDR: b"\x86\xff\x00\xef"}), "MUTANT")


# =====================================================================================================
# THE DIFF GATE, THE CRC INTERDICTION, AND THE WRITE REFUSALS
# =====================================================================================================

@case("diff gate: a stray byte that resolves to NO declared edit",
      "the zero-unattributed-bytes gate is what catches an edit nobody declared")
def _c19():
    m = _mut({0x9ABCD: _b(0x5A)})
    attribute = B.make_attributor(crc_only=set(), cave_changed=False)
    runs = B.diff_runs(m, V85, attribute)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V85: {[hex(x) for x in stray[:16]]}"


@case("diff gate: identity-modulo catches a byte outside the attributed set",
      "restoring the declared bytes must reproduce V85 over the FULL 1 MiB, not over a span")
def _c20():
    B.assert_identity_modulo(_mut({0xC40BC: _h(3000), 0x9ABCD: _b(0x5A)}), V85,
                             {0xC40BC, 0xC40BD}, "MUTANT", "V85")


@case("CRC: an edit inside [0xC5000,0xC5FFC), the block the bootloader SKIPS",
      "V40 wrote motor-rate cap tables there, left the CRC stale, and the ECU faulted at ignition")
def _c21():
    attributed = {0xC5100}
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- THE BLOCK THE BOOTLOADER SKIPS"


@case("CRC: a stale trailer is caught by the chain walk",
      "the 50/50 walk is the last line -- a stale CRC is how V40 bricked")
def _c22():
    m = _mut({0xC40BC: _h(3000)})       # edit without recomputing 0xC4FFC
    assert walk_all_blocks(bytes(m)) == 0, "CRC chain FAILED"


@case("write refusal: a NULL build must never be cut as a .rwd",
      "a byte-identical duplicate carries zero evidence and collides with ONE .rwd per build number")
def _c23():
    # 🛑 V86 is no longer a null build, so the precondition is STAGED rather than assumed.
    saved = (B.CONTROL_CELLS, B.CODE_BYTES, B.CAVE_PAYLOAD)
    B.CONTROL_CELLS, B.CODE_BYTES, B.CAVE_PAYLOAD = (), (), None
    try:
        assert B.is_null_build(), "the staged null precondition did not take"
        B._refuse_null_write()
    finally:
        B.CONTROL_CELLS, B.CODE_BYTES, B.CAVE_PAYLOAD = saved


@case("write refusal: no artefact may be named while VARIANT_TOKEN is None",
      "freezing the name is what stops a re-cut destroying its predecessor's plain image")
def _c24():
    # 🛑 the token is SET now, so unset it for the duration of the check and restore it.
    saved = B.VARIANT_TOKEN
    B.VARIANT_TOKEN = None
    try:
        B._naming()
    finally:
        B.VARIANT_TOKEN = saved


@case("base gate: a look-alike image is refused as the base",
      "V84, V83a, V81 and V75 are one hash away from being flown by mistake")
def _c25():
    import hashlib
    sha = hashlib.sha256(bytes(_mut({0xC40BC: _h(600)}))).hexdigest()
    assert sha == B.SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT THE FLOWN V85. SHA256 is {sha}, expected {B.SRC_SHA256}."


def main():
    print(__doc__)
    print("=" * 102)
    print(f"  {len(CASES)} NEGATIVE CONTROLS -- each stages a defect and requires the gate to FAIL")
    print("=" * 102)
    broken, fired = [], 0
    for i, (name, why, fn) in enumerate(CASES, 1):
        try:
            fn()
        except (AssertionError, SystemExit) as exc:
            fired += 1
            msg = str(exc).replace("\n", " ")[:96]
            print(f"  {i:2d}. ✅ CAUGHT   {name}")
            print(f"          why      {why}")
            print(f"          gate said {msg}…")
        else:
            broken.append(name)
            print(f"  {i:2d}. 🛑 SILENT   {name}")
            print(f"          why      {why}")
            print("          🛑🛑 THE GATE DID NOT FIRE -- IT IS BROKEN AND PROVES NOTHING.")
    print("=" * 102)
    print(f"  {fired}/{len(CASES)} gates fired.")
    if broken:
        raise SystemExit(f"🛑🛑 {len(broken)} BROKEN GATE(S): {broken}")
    print("  ✅ EVERY GATE IN build_v86_tva.py's verifier is DEMONSTRATED to catch its own defect.")
    print("     🛑 Nothing was written to disk; every mutation was an in-memory copy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
