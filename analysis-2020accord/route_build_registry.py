#!/usr/bin/env python3
"""route_build_registry.py -- WHICH FIRMWARE WAS ON THE CAR FOR WHICH ROUTE.

This should have existed from V53 onward and did not. Every session so far has re-derived the
route->build mapping from prose in handoffs, and on 2026-08-01 it produced a real gap: nobody --
operator or analyst -- could say with certainty which `.rwd` was flashed for routes `3a`/`3b`, which
left a `0x87` decode ambiguity sitting under a build decision.

🛑 THE MAPPING IS NOT A LABEL. An rlog cannot report the flashed build: EVERY modified image reports
`fw='39990-TVA,A160'` because the version-string edit (`0x13109`, `0x14120`, `-` -> `,`) is shared by
all of them. So the mapping has to be an INFERENCE from evidence, and this module records the
evidence, not just the conclusion. `identify()` re-derives it from a route's own cache so the claim
is checkable rather than asserted.

STANDING PRACTICE, from 2026-08-01: whenever a route is added, add its row here with the evidence
that pins it, and run `identify()` to confirm the row against the data.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Route:
    route: str                  # short id as used everywhere in the docs
    tail: str                   # the hash half of the directory name, so the row is unambiguous
    build: str
    probe: str                  # what `0x14A` byte4 bits 7:3 MEAN on this build
    kd: Optional[float]         # r24 rate-lane multiplier: 0 = V61's kill, 1 = stock sar 0xa, 2 = sar 0x9
    image_sha: str = ""         # first 8 hex of the plain image, "" where not recorded at the time
    rwd_sha: str = ""
    evidence: tuple = field(default_factory=tuple)


# ⚠ `kd=None` means the rate lane was not the variable under test and was not separately verified
# for that route. It does NOT mean "unknown build".
ROUTES = (
    Route("13", "f484e75b00", "V52C-era", "no probe", None, evidence=(
        "Named in HANDOFF-2026-07-26-route13. 🛑 The V52C window 08-12 is ABSENT machine-wide, so no "
        "V52C rlog exists; route 13 is NOT a V52C log despite that handoff's title context.",)),
    Route("1a", "a4ef772958", "V53", "FOURFRAME2 (never transmitted)", None, evidence=(
        "byte4 == 0x07 in 5,994/5,994 (100%) -- the stock STEER_SENSOR_STATUS with NO probe bits, "
        "which is V53's signature. STEER_STATUS=0 in 5,995/5,995 confirms the 0xC62EA=0 steer-to-zero.",)),
    Route("1b", "d2abf1af1c", "V54", "5-bit gp-0x6966 authority", None, evidence=(
        "byte4 == 0x0F in 5,989/5,989 (100%). The single-bit A/B against route 1a's 0x07 is the "
        "end-to-end proof of the 0x14A byte4 piggyback channel.",)),
    Route("1c", "ade8fd5b4a", "V55", "damper variant bit + 4-bit gp-0x6b98", None, evidence=(
        "V55 dual probe fired; the ~21 Hz mode found in gp-0x6b98.",)),
    Route("24", "bc45926e80", "V56", "V55 probe (unchanged)", None, evidence=(
        "0xC6AFC/0xC6AFE muted; operator reported damping removed. Reverted after this route.",)),
    Route("28", "66ab5a2233", "V57", "deadband-gate probe", None, evidence=(
        "V57's bit6 = (gp-0x6806 == 0).",)),
    Route("29", "47bc9c9d99", "V57", "deadband-gate probe", None, evidence=(
        "ST==3 in 120 frames, all at vEgo == 0.000 exactly.",)),
    Route("2b", "7926e8f7e5", "V58", "angle-rate / boost-lane probe", 1.0, evidence=(
        "bit5 = (gp-0x6bbe == +512) read 0 in all 35,964 frames; bit4 fired at 20.93 Hz. "
        "14 segments, 83,959 frames, ST==4 = 0.",)),
    Route("2c", "eb219f392c", "V59", "boost-index THERMOMETER on gp-0x6ba6", 1.0, evidence=(
        "100% thermometer-monotonic (bit5 => bit4 => bit3), fault sentinel 0.000%, "
        "50,963 frames, ST==4 = 0/50,963.",)),
    Route("31", "0441e00d2b", "V61", "V59 probe (unchanged)", 0.0, evidence=(
        "Kd -> 0 (both taps killed). Mode moved 21.18 -> 18.25 Hz with 7.9x the power, and grinding "
        "appeared in MANUAL driving -- a signature no other build produces.",)),
    Route("35", "77808fe7ce", "V64", "oscillation-detector probe", 1.0, evidence=(
        "byte4 == CONSTANT 0x87 for all 14,980 frames, zero variance. That frozen-constant pattern "
        "is V64's own null and distinguishes it from V65's 0x87, which is one of several values.",)),
    Route("37", "6231e33f3d", "V62", "V59 thermometer (carried unchanged)", 2.0, evidence=(
        "86,278 frames; 18-22 Hz suppressed vs V59; ST==4 = 0/86,278. byte4 = 0x87 on 9.24% of "
        "frames, read under V59 thermometer semantics as 'index >= 2048', NOT as V64's null.",)),
    Route("3a", "4e55c1e0f4", "V65", "4-level SATURATION LADDER on gp-0x6b94", 2.0,
          image_sha="f12171a8", evidence=(
        "36,991 frames. byte4 takes THREE distinct values {0x87, 0x97, 0xA7}.",
        "★ 0x97 sets bit4 with bit3 CLEAR. Under V59/V62's thermometer the bits NEST "
        "(bit5 => bit4 => bit3), so 0x97 is STRUCTURALLY IMPOSSIBLE there ⇒ V59 and V62 are EXCLUDED.",
        "★ All three values are legal ladder payloads and all three V65 invariants hold with ZERO "
        "violations over 36,991 frames (bit6=>bit5, bit3=>bit4, never-both-sides).",
        "★ V64 is excluded twice: its route read a FROZEN constant, and 18-22 Hz is SUPPRESSED here "
        "(ratio 0.555 vs Kd=1x) ⇒ the rate lane is doubled, which V64 does not do.",
        "⇒ V65 is the only built artifact carrying BOTH Kd=2x AND the ladder.")),
    Route("3b", "a4a7f4dbf1", "V65", "4-level SATURATION LADDER on gp-0x6b94", 2.0,
          image_sha="f12171a8", evidence=(
        "83,058 frames. byte4 takes {0x87, 0x97}; same structural exclusion of V59/V62 via 0x97, "
        "same zero invariant violations, same 18-22 Hz suppression. Highway from seg 3 (t ~ 25 s).",)),
)

BY_ROUTE = {r.route: r for r in ROUTES}


# ---------------------------------------------------------------------------------------------
# Re-derivation from a route's OWN data, so the table above is checkable and not just asserted.
# ---------------------------------------------------------------------------------------------

def identify(field_values):
    """Narrow the build from the `0x14A` byte4 probe payloads alone.

    `field_values` is the raw byte4 values (ints). Returns (candidates, notes).
    🛑 This narrows; it does not uniquely identify. Payload structure cannot separate builds that
    share a probe, and V64/V65 share the byte 0x87. Combine with the Kd evidence (18-22 Hz
    suppression) and with the built-artifact list before concluding.
    """
    vals = sorted(set(int(v) & 0xFF for v in field_values))
    notes, cands = [], set()

    if vals == [0x07]:
        return {"V53"}, ["byte4 == 0x07 only: stock status bits, no probe -> V53"]
    if vals == [0x0F]:
        return {"V54"}, ["byte4 == 0x0F only: V54's authority probe pinned at one bucket"]

    if any(v == 0 for v in vals):
        notes.append("🛑 byte4 == 0 present: the cave did not fire on some frames -> reading is VOID")

    # V59/V62 thermometer: bits 5,4,3 nest as bit5 => bit4 => bit3.
    therm_ok = all((not (v >> 5 & 1) or (v >> 4 & 1)) and (not (v >> 4 & 1) or (v >> 3 & 1))
                   for v in vals)
    # V65 ladder: bit6 => bit5, bit3 => bit4, and never both sides at once.
    ladder_ok = all((not (v >> 6 & 1) or (v >> 5 & 1))
                    and (not (v >> 3 & 1) or (v >> 4 & 1))
                    and not (((v >> 5) & 3) and ((v >> 3) & 3))
                    for v in vals)

    if therm_ok:
        cands |= {"V59", "V62"}
        notes.append("thermometer nesting HOLDS on every distinct value -> V59/V62 possible")
    else:
        notes.append("★ thermometer nesting VIOLATED -> V59 and V62 are EXCLUDED")
    if ladder_ok:
        cands |= {"V65"}
        notes.append("all V65 ladder invariants HOLD on every distinct value -> V65 possible")
    else:
        notes.append("★ a V65 ladder invariant is VIOLATED -> V65 is EXCLUDED")
    # V66 and V67: four INDEPENDENT booleans in bits 7:4, bit7 hard-wired 1, bit3 NEVER set.
    # 🛑 They are structurally IDENTICAL to each other -- same eight payloads, different cells --
    # and their caves differ by only FOUR bytes. Payload can never separate them; only the .rwd
    # filename can. Recorded here because this is the tightest such pair the kit has produced.
    free4_ok = all((v >> 7 & 1) and not (v >> 3 & 1) for v in vals)
    if free4_ok:
        cands |= {"V66", "V67"}
        notes.append("bit7 set and bit3 clear on every value -> V66/V67 possible. 🛑 THEY ARE "
                     "MUTUALLY INSEPARABLE BY PAYLOAD: V66 reads gp-0x6806/67f5/67fe, V67 reads "
                     "gp-0x6806/671d/671a (>=5). CONFIRM THE .rwd FILENAME.")
    else:
        notes.append("★ bit3 set or bit7 clear somewhere -> V66 and V67 are EXCLUDED")

    if len(vals) == 1 and vals[0] == 0x87:
        cands |= {"V64"}
        notes.append("🛑 a FROZEN constant 0x87 is V64's null, V65's neutral bucket, V66's "
                     "all-gates-zero AND V67's gate-never-true -- payload alone CANNOT separate "
                     "them; use the 18-22 Hz Kd evidence and the flashed filename")
    elif 0x87 in vals:
        notes.append("0x87 present but NOT constant -> not V64's frozen null")

    return cands, notes


def _self_check():
    """Every row's own evidence must survive its own test."""
    c, _ = identify([0x87, 0x97, 0xA7])                     # routes 3a
    assert "V65" in c and "V59" not in c and "V62" not in c, c
    c, _ = identify([0x87, 0x97])                            # route 3b
    assert "V65" in c and "V62" not in c, c
    c, _ = identify([0x87])                                  # route 35 -- genuinely ambiguous
    assert {"V64", "V65"} <= c, c
    assert identify([0x07])[0] == {"V53"}
    assert identify([0x0F])[0] == {"V54"}
    # the table must be internally consistent
    assert len({r.route for r in ROUTES}) == len(ROUTES), "duplicate route id"
    for r in ROUTES:
        assert r.evidence, f"{r.route} has no evidence recorded"
    return True


if __name__ == "__main__":
    _self_check()
    w = max(len(r.build) for r in ROUTES)
    print(f"{'route':<6}{'tail':<13}{'build':<{w + 2}}{'Kd':<5}probe")
    print("-" * 96)
    for r in ROUTES:
        kd = "-" if r.kd is None else f"{r.kd:g}x"
        print(f"{r.route:<6}{r.tail:<13}{r.build:<{w + 2}}{kd:<5}{r.probe}")
    print("\nself-check: PASS -- every row carries evidence and every probe-structure test agrees")
