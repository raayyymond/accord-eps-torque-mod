"""
verify/diff_build_vs_stock.py -- enumerate EVERY difference between a BUILD and the STOCK 39990-TVA-A160 image.

Usage:  python verify/diff_build_vs_stock.py [v62|v63|...|v68]      (default: v68)
        python verify/diff_build_vs_stock.py v68 --self-test        (prove the gate can still FAIL)

Answers "what has this firmware actually had done to it, in total" -- not the per-build delta. Groups
the raw byte diff into named edits, and 🛑 FAILS LOUDLY on any changed byte it cannot attribute, so an
unaccounted edit cannot hide inside a summary.

🛑 Diff is restricted to [0x13000, 0x100000). build_*.full_image() writes 0xFF filler below 0x13000 and
a naive whole-file diff reports ~51,000 bogus bytes.

🛑 WHY THE TABLE MUST BE KEPT CURRENT (2026-08-03). This file's attribution table had stopped at V59.
On V67 and V68 it therefore reported 3 UNATTRIBUTED bytes -- `0x3AA96` and `0xC6446/47`, which are
V67's two entirely legitimate edits -- and exited non-zero. **While a gate emits known-false
positives, a genuine stray edit is indistinguishable from the noise**, which is the most dangerous
failure mode a verifier can have on a repo whose only bricking class is "a byte somewhere you did not
intend". The table is now current through V68, and `--self-test` injects a synthetic stray byte and
asserts the tool still reports it, so "it passes" cannot quietly become "it cannot fail".
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# 🛑 A GATE MUST BE ABLE TO REACH THE CONSOLE WITH ITS VERDICT. On a Windows cp1252 console this
# script died with UnicodeEncodeError on the first '🛑' it printed -- which is only ever printed on
# the FAILING path, so the crash suppressed exactly the message that says WHICH bytes were
# unattributed. Found 2026-08-04 while verifying V70.
# ⚠ PRECISION, because the first version of this comment overstated it: the EXIT CODE was never
# wrong. A clean run exits 0 (it prints no 🛑 and never crashed); --self-test exits 1 either way,
# because the encoding crash and the real detection both exit non-zero. So the machine-readable
# verdict was always correct and only the human-readable one was lost -- but a reader watching the
# console could not tell a real failure from an encoding crash, and that is enough to matter.
# Same family as the 256-sample floor that made decode_v69_ratchet's own null vacuous: a gate whose
# report cannot reach the reader degrades toward one that cannot fail informatively.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):        # already wrapped, or not a real stream
        pass

from firmware_paths import plain_image_path   # noqa: E402

STOCK = r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\stock_fw_dump\code.bin"
LO, HI = 0x13000, 0x100000

# CRC trailers -- bookkeeping, not behaviour. Every 4 KiB block plus the two big spans.
CRC_WORDS = [(0x13000, 0xC4FFC), (0xC5000, 0xC5FFC), (0xC6000, 0xC6FFC), (0xC7000, 0xCCFFC)]
CRC_WORDS += [(b, b + 0xFFC) for b in range(0xCD000, 0x100000, 0x1000)]

# (lo, hi_exclusive, build, one-line what-it-does)
# `build` = the build whose value V62 currently carries. Where an earlier build first moved the bytes and
# a later one changed them again, both are named. All attributions were derived EMPIRICALLY by walking
# every _v*_plain_image.bin in the archive, not from the lineage doc.
EDITS = [
    (0x13109, 0x1310A, "V22", "part-number string byte '-' -> ',' -- the modified-firmware marker"),
    (0x14120, 0x14121, "V22", "part-number string byte '-' -> ',' (second copy)"),
    (0xC61B2, 0xC61B6, "V22->V38", "LKAS forward-path clamps 512 -> 1024 -> 2048, tracking the gain"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce state-machine cals (gentle-EME fix)"),
    (0xC64B4, 0xC64B8, "V36", "STEER_STATUS debounce state-machine cals (second group)"),
    (0xC64B8, 0xC64B9, "V37", "DTC-0x49 fail-counter gate 112 -> 0xFF -- resolved the gentle EME"),
    (0xC64DE, 0xC64DF, "V18", "re-engage ramp 17 -> 27 (lengthens re-engage; road-validated)"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor, FLOAT set 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor, FLOAT set 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor, INT set 1024 -> 5120 (the lockstep twin)"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper (driver-pushback surface) flat Y 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank -- all 8 selector-reachable records"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0 (steer-to-zero; confirmed on-car)"),
    (0x55C0E, 0x55C12, "V53/V55", "cave HOOK -- the call that reaches the telemetry probe"),
    (0xC4B34, 0xC4B78, "CAVE", "CODE CAVE: 0x14A byte4 telemetry probe"),   # label resolved per build
    (0x2A1F0, 0x2A1F2, "V57", "forward LKAS reader re-pointed 0x746C -> 0x7CD0 (onto the private cell)"),
    (0xC6CD0, 0xC6CD2, "V57", "PRIVATE LKAS forward gain cell = 3564 (the decoupling's new cell)"),
    # ---- added 2026-08-03: the table had stopped at V59 -------------------------------------------
    (0xD2006, 0xD2007, "V60", "boost-amplitude BLEND coefficient 102 -> 43 -- FLASHED, NULL on-car"),
    (0x3AB6C, 0x3AB6E, "V61", "r26 rate-lane tap, reg1 r1 -> r0 (kills the lane) -- FLASHED, WORSE"),
    (0x3AC16, 0x3AC18, "V61", "r24 rate-lane tap, reg1 r1 -> r0 (kills the lane) -- FLASHED, WORSE"),
    (0x3AB76, 0x3AB78, "V62", "r26 torsion-bar RATE lane: sar 0xa -> sar 0x9  (DOUBLE the lane)"),
    (0x3AC20, 0x3AC22, "V62", "r24 torsion-bar RATE lane: sar 0xa -> sar 0x9  (DOUBLE the lane)"),
    (0xC643E, 0xC6440, "V63", "r26 RATE lane, OSCILLATION-only gain arm (state>=5) 1536 -> 3072"),
    (0xC6440, 0xC6442, "V63", "r24 RATE lane, OSCILLATION-only gain arm (state>=5) 2048 -> 4096"),
    (0x3AA96, 0x3AA97, "V67/V71C", "repoint ld.bu gp-0x683c -> gp-0x6806: BOTH gain arms GATED "
                                   "ON LKAS. 🛑 This byte is what makes 0xC6444/0xC6446 LIVE at all"),
    (0xC6446, 0xC6448, "V67/V71C", "r24's LKAS gain arm 512 -> 5244 -- FLASHED, grind #1 fixed"),
    (0xC6444, 0xC6446, "V71C", "r26's LKAS gain arm 512 -> 3072 -- removes V67/V68's ~6x CUT. "
                               "🛑 LIVE only when 0x3AA96 is repointed; null by construction on "
                               "any gateless build (V71A/V71B)"),
    # ---- V69: the gate REVERTS and Honda's own low-speed surface is shaped instead --------------
    # 🛑 0x3AA96 and 0xC6446 appear ABOVE as V67 edits and here as V69 REVERTS. This differ is
    # SPAN-based, so it cannot tell 5244 from 512 at 0xC6446 -- only verify/verify_v69_image.py's exact
    # value anchors can. Run both; neither is sufficient alone.
    # 🛑 SPAN-based, so it cannot tell V69's x4 from V70's x2 at these addresses -- only
    # verify/verify_v69_image.py / verify/verify_v70_image.py's exact value anchors can. The DOSE is per build:
    # V69 = x4 (12288 / 10244), V70 = x2 (6144 / 5122). Both leave rec2/rec3 untouched.
    # 🛑🛑 "V70" IS AMBIGUOUS ON DISK AS OF 2026-08-04 -- TWO .rwd FILES CARRY A V70 PREFIX AND THEY
    # HAVE OPPOSITE CONTROL PATHS. The line above describes ONLY the SPEEDSHAPED-gateREVERTED-x2
    # artefact (rwd 0bdfb0da..., image 3760d9c0..., 08:04), which is what _v70_plain_image.bin and
    # verify/verify_v70_image.py currently are. The OTHER artefact
    # (rwd d716b1a5..., image 8bfcb1fa..., 07:45, "LKASGATED-V68CONTROLPATH") keeps V68's gate=0xFB
    # / arm=5244 and leaves 0xD2A7E/0xD2ABA at STOCK, so this entry matches ZERO bytes on it.
    # ⚠ Attribution here is therefore only as good as which image you fed it. Confirm the .rwd
    # filename AND run the matching verify_v*_image.py -- this differ alone cannot tell them apart.
    # Same trap as the three V68-prefixed .rwd files; see docs/STATE.md.
    (0xD2A7E, 0xD2A82, "V69/V70", "mode-10 gain_B 0 km/h record Y[0..1] 3072 -> 6144 (V70 x2) or "
                                  "12288 (V69 x4); speed-shaped rate lane, rec2/rec3 untouched "
                                  "=> highway EXACTLY 1.000x"),
    (0xD2ABA, 0xD2ABE, "V69/V70", "mode-10 gain_B 10 km/h record Y[0..1] 2561 -> 5122 (V70 x2) or "
                                  "10244 (V69 x4)"),
    # ---- V71: BOTH confirmed fixes restored, and the surface dose dropped ------------------------
    # 🛑 On V71 the two 0xD2A7E/0xD2ABA entries above match ZERO bytes -- the surface is back at
    # STOCK -- and 0x3AB76/0x3AC20 revert to their V62 attribution. The one genuinely new span is
    # 0x454FE, which V42 introduced and which NO build between V53 and V70 carried.
    (0xC6A72, 0xC6A7A, "V71B", "gain_A rec0 (0 km/h) Y[0..3] ALL doubled -> [6144,6144,4868,4096] "
                              "-- r26's default arm, speed-shaped on the SHARED 0xC6010 cross-axis"),
    (0xC6A86, 0xC6A8E, "V71B", "gain_A rec1 (10 km/h) Y[0..3] ALL doubled -> [6144,6144,4976,3072]; "
                              "rec2/rec3 untouched => EXACTLY 1.000000x at and above 50 km/h"),
    (0x454FE, 0x454FF, "V42/V71A/V71B", "state-4 governor ratchet: `bne 0x455C4` -> `br 0x455C4` (V850 "
                                  "cond nibble 0xA -> 0x5; displacement and TARGET unchanged). The "
                                  "kit's one CONFIRMED root cause, lost at the V38/FOURFRAME rebase "
                                  "and restored by V71."),
]

# 🛑 The cave span carries a DIFFERENT payload on every build. Labelling it "V59 boost-index
# thermometer" regardless -- which this file did until 2026-08-03 -- is a false provenance claim on
# eight builds. Sourced from each build's own TAG and docstring, not from memory.
CAVE_BY_BUILD = {
    "59": ("V39->V59", "boost-index DEPTH thermometer on gp-0x6ba6"),
    "60": ("V39->V59", "V59's boost-index thermometer, carried unchanged"),
    "61": ("V39->V59", "V59's boost-index thermometer, carried unchanged"),
    "62": ("V39->V59", "V59's boost-index thermometer, carried unchanged"),
    "63": ("V39->V59", "V59's boost-index thermometer, carried unchanged"),
    "64": ("V39->V64", "oscillation-DETECTOR probe (the detector never armed on-car)"),
    "65": ("V39->V65", "4-level SATURATION LADDER on gp-0x6b94"),
    "66": ("V39->V66", "3-bit GATE PROBE: bit6 gp-0x6806, bit5 gp-0x671d, bit4 gp-0x671a"),
    "67": ("V39->V67", "3-bit ARM SELECTOR: bit6 gp-0x6806, bit5 gp-0x671d, bit4 gp-0x671a>=5"),
    "68": ("V39->V68", "4-bit probe: bit6 gp-0x6806, bit5 gp-0x671d, "
                       "bit4 gp-0x6ac0>=400, bit3 BUILD FINGERPRINT"),
    # 🛑 V69 re-aims the probe from the GRIND detector to the RATCHET: three SIGNED-halfword rungs on
    # the aggregator's own hard nonlinearities, all `ld.h`+`sar 0xc`+`cmp 0x1` at threshold +4096.
    "69": ("V39->V69", "3-bit RATCHET probe: bit6 gp-0x6ada>=+4096 (r24 lane out, post +/-0x2000 "
                       "clip), bit5 gp-0x6b62>=+4096 (return-to-centre), bit4 gp-0x6ad4>=+4096 "
                       "(unfiltered residual); bit3 CONSTANT 0 = build class"),
    # 🛑 V70 REPAIRS all three of V69's rungs -- each returned an uninterpretable zero for a
    # DIFFERENT reason (bit4 structurally unreachable, bit5 insensitive, bit6 no exposure) -- and
    # spends 6 bytes on a SIGN bit. bit3 is a RUNG here, not a constant: that is what makes V70
    # distinguishable from V68 (bit3 constant 1) and V66/V67/V69 (bit3 constant 0) at the same time.
    "70": ("V39->V70", "4-bit SIGN probe: bit6 gp-0x6ada>=+512 (r24 lane out, post-clip), "
                       "bit5 gp-0x67fa==10 (THE STATE GATE), bit4 gp-0x6adc>=0 (r26 mirror SIGN), "
                       "bit3 gp-0x6ada>=0 (r24 mirror SIGN; bit6 => bit3 is an INVARIANT)"),
    # 🛑 V71 reads the gain-chain SELECTORS instead of a lane output -- four probes in a row had
    # returned an uninterpretable zero by reading an OUTPUT. Its four rungs are INDEPENDENT, so all
    # 16 payloads are reachable and it carries NO value-set invariant: identification from the wire
    # is WEAKER than V70's, and the .rwd filename is the pre-drive discriminator.
    "71a": ("V39->V71A", "5-rung GAIN-IN-FORCE probe: bit6 gp-0x671d!=0 (THE MASK, outranks every "
                       "arm), bit5 gp-0x67fa==4 (THE RATCHET STATE this build disables), "
                       "bit4 gp-0x6ada>=+512 (positive control), bit3 gp-0x671a>=5 (the third arm); "
                       "r7 accumulates 5 weights and one `shl 0x3,r7` moves them into bits 7:3"),
    # 🛑 V71B's cave is BYTE-IDENTICAL to V71A's. That is deliberate and it means this differ -- and
    # the CAN wire -- cannot tell the two builds apart from the cave at all. They are separated by
    # the `sar` sites and gain_A, both listed in EDITS, and by the .rwd FILENAME.
    "71c": ("V39->V71A", "the SAME 68-byte cave as V71A, byte for byte -- V71C doses r24 through a "
                         "scalar ARM rather than a `sar`, so it watches the same mirror gp-0x6ada"),
    "71b": ("V39->V71B", "the same 5-rung probe as V71A but with bit4/bit3 RETARGETED to "
                         "gp-0x6adc = r26's post-clip mirror (V71A watches gp-0x6ada = r24's). "
                         "ONE cave byte apart, at 0xC4B4E -- a build must instrument the lane it "
                         "doses, and V71B doses r26 alone. 🛑 That byte is NOT visible on the wire"),
}

# 🛑 Deliberately NOT in the list, and worth stating because it surprises people:
#   0xC646C (the shared sensor scale) is back at STOCK 891. V22/V38 raised it 891->1782->3564, and V57
#   REVERTED it, moving the 3564 onto the private cell 0xC6CD0 so only the forward LKAS path sees it.
#   0x454FE (V42's state-4 governor ratchet fix) is likewise absent -- V42's chain 1 is NOT in the
#   V53->V62 line. Both are asserted below so the claim cannot rot.
ASSERT_STOCK = [
    (0xC646C, "shared sensor scale -- reverted to stock by V57, gain lives at 0xC6CD0 now"),
    (0x454FE, "V42 state-4 governor bne->br -- NOT carried into this build line"),
]
# 🛑 V71 DELIBERATELY RESTORES 0x454FE, so the blanket claim above is false for it -- and a gate that
# emits a known-false failure is the most dangerous kind, because a genuine stray edit then hides in
# the noise (exactly the V67/V68 lesson recorded at the top of this file). The exception is per
# build and per address, never a blanket skip.
ASSERT_STOCK_EXCEPTIONS = {b: {0x454FE: f"V{b.upper()} RESTORES V42's ratchet fix -- expected NOT stock"}
                           for b in ("71a", "71b", "71c")}


def resolve_edits(build):
    """EDITS with the cave's provenance resolved for THIS build, not left at V59's label."""
    label, what = CAVE_BY_BUILD.get(build, ("V39->?", "payload UNKNOWN for this build -- add it"))
    out = []
    for lo, hi, ebuild, text in EDITS:
        if ebuild == "CAVE":
            ebuild, text = label, f"{text} ({what})"
        out.append((lo, hi, ebuild, text))
    return out


def main():
    # ⚠ the EDITS loops below MUST NOT rebind this name -- they use `ebuild`.
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    self_test = "--self-test" in sys.argv
    build = (args[0] if args else "v68").lower().lstrip("v")
    v62 = bytearray(open(str(plain_image_path(f"_v{build}_plain_image.bin")), "rb").read())
    stock = open(STOCK, "rb").read()
    assert len(v62) == len(stock) == 0x100000
    edits = resolve_edits(build)

    if self_test:
        # 🛑 A gate that cannot fail is worthless. Flip one byte in a span no EDITS entry covers and
        # that is not a CRC trailer, then let the normal path run: it MUST report it and exit non-zero.
        covered = {i for lo, hi, _, _ in edits for i in range(lo, hi)}
        covered |= {i for lo, hi in CRC_WORDS for i in range(hi, hi + 4)}
        victim = next(i for i in range(0x20000, 0x2A000) if i not in covered and v62[i] == stock[i])
        v62[victim] ^= 0xFF
        print(f"⚠ --self-test: injected a synthetic stray byte at 0x{victim:05X} "
              f"({stock[victim]:02X} -> {v62[victim]:02X}). The run below MUST FAIL.\n")

    diff = [i for i in range(LO, HI) if v62[i] != stock[i]]
    crc_bytes = {i for lo, hi in CRC_WORDS for i in range(hi, hi + 4)}

    print(f"V{build.upper()} vs STOCK 39990-TVA-A160, range [0x{LO:X},0x{HI:X})")
    print(f"total differing bytes: {len(diff)}\n")

    attributed, rows = set(), []
    for lo, hi, ebuild, what in edits:
        hits = [i for i in diff if lo <= i < hi]
        attributed |= set(hits)
        if hits:
            rows.append((lo, hi, ebuild, what, len(hits)))

    rows.sort()
    print(f"{'address':>18}  {'build':<9} {'n':>3}  what")
    print("-" * 110)
    for lo, hi, ebuild, what, n in rows:
        span = f"0x{lo:05X}" if hi - lo <= 2 else f"0x{lo:05X}-0x{hi - 1:05X}"
        print(f"{span:>18}  {ebuild:<9} {n:>3}  {what}")

    crc_changed = sorted(set(diff) & crc_bytes - attributed)
    unattributed = sorted(set(diff) - attributed - crc_bytes)

    print("-" * 110)
    print(f"{'CRC trailers':>18}  {'--':<9} {len(crc_changed):>3}  "
          f"recomputed block checksums (bookkeeping, not behaviour)")
    print(f"\nfunctional bytes changed : {len(attributed)}")
    print(f"CRC bookkeeping bytes    : {len(crc_changed)}")
    print(f"UNATTRIBUTED             : {len(unattributed)}")
    if unattributed:
        print("\n🛑 UNATTRIBUTED BYTES -- every one must be explained before this summary can be trusted:")
        for i in unattributed[:60]:
            print(f"   0x{i:05X}  stock {stock[i]:02X} -> v62 {v62[i]:02X}")
        raise SystemExit("unattributed differences exist")

    print("\nasserted STILL STOCK (things people assume are changed and are not):")
    exceptions = ASSERT_STOCK_EXCEPTIONS.get(build, {})
    for a, why in ASSERT_STOCK:
        same = v62[a:a + 2] == stock[a:a + 2]
        if a in exceptions:
            print(f"   0x{a:05X}  {'STOCK' if same else 'CHANGED (expected)':<18} {exceptions[a]}")
            assert not same, f"0x{a:05X} IS stock, but V{build.upper()} is supposed to change it"
            continue
        print(f"   0x{a:05X}  {'STOCK' if same else '*** CHANGED ***':<15} {why}")
        assert same, f"0x{a:05X} is not stock -- this file's claim is wrong"

    # This build's own edits, spelled out. ⚠ Matched on a TOKEN, not on equality: labels are compound
    # ("V53/V55", "V39->V68"), so `== f"v{build}"` silently found nothing for most builds.
    tok = f"v{build}"
    own = sorted({(lo, hi, w) for lo, hi, b, w in edits
                  if tok in re.split(r"[^0-9a-z]+", b.lower())})
    print(f"\nV{build.upper()}'s own edits:")
    if not own:
        print("   (none -- this build's changes are all inherited spans)")
    for a, hi, what in own:
        n = hi - a
        if n > 8:                                     # the cave: a span, not a scalar
            changed = [i for i in range(a, hi) if v62[i] != stock[i]]
            used = len(bytes(v62[a:hi]).rstrip(b"\xff"))
            print(f"   0x{a:05X}-0x{hi - 1:05X}  {len(changed)} of {n} bytes differ from stock; "
                  f"payload occupies {used} B, {n - used} B trailing 0xFF")
        elif n == 1:                                  # a single byte (a displacement, a coefficient)
            print(f"   0x{a:05X}  {stock[a]:02X} -> {v62[a]:02X}   (single byte)")
        else:
            s = struct.unpack_from("<H", stock, a)[0]
            v = struct.unpack_from("<H", v62, a)[0]
            if a >= 0xC0000:                          # calibration halfword
                print(f"   0x{a:05X}  {s:5d} -> {v:5d}   (calibration halfword, LE)")
            elif "sar" in what:                       # a Format-II shift: show the imm5 split
                print(f"   0x{a:05X}  {s:04X} -> {v:04X}   sar imm5 {s & 0x1F} -> {v & 0x1F}, "
                      f"opcode 0x{(s >> 5) & 0x3F:02X} and reg2 r{(s >> 11) & 0x1F} UNCHANGED")
            else:                                     # any other code halfword -- no shape claimed
                print(f"   0x{a:05X}  {s:04X} -> {v:04X}   (code halfword, LE; "
                      f"reg1 field r{s & 0x1F} -> r{v & 0x1F})")


if __name__ == "__main__":
    main()
