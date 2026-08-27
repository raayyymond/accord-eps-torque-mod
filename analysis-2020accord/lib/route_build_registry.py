#!/usr/bin/env python3
"""lib/route_build_registry.py -- WHICH FIRMWARE WAS ON THE CAR FOR WHICH ROUTE.

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
# ⚠ route 47 (V67) is the first CONDITIONAL dose: kd=2.0 there means "2x WHILE THE LKAS GATE IS
# TRUE, stock 1x otherwise". Do not pool it with the unconditional 2x routes without saying which
# arm you mean -- its disengaged arm is a Kd=1 population.
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
    Route("47", "3e0b6134c0", "V67", "3-bit ARM SELECTOR: bit6 gp-0x6806, bit5 gp-0x671d, "
                                     "bit4 gp-0x671a>=5", 2.0, evidence=(
        "150,327 frames over 26 segments. byte4 takes exactly TWO values, {0x87, 0xC7}: bit7 set "
        "and bit3 clear on both, so the V66/V67 payload class holds and V53/V54 are excluded.",
        "★ bit5 (gp-0x671d, the masking arm that OUTRANKS the gain arm) and bit4 (gp-0x671a) are "
        "ZERO in all 150,327 frames, and bit3 and the VOID sentinel never fire ⇒ the arm is a clean "
        "binary, stock mode-10 LERP vs cal 0xC6446 = 5244, with nothing masking it.",
        "★ bit6 == carControl.latActive in 150,302/150,327 frames (99.983%); the 25 disagreements "
        "are single-frame transition edges. That identifies bit6 as gp-0x6806, the LKAS "
        "deadband/engage gate first probed on V57 -- and it EXCLUDES V59/V62 on semantics even "
        "though their thermometer nesting survives both payloads structurally: under V59/V62 bit6 "
        "is the FAULT sentinel, which read 0.000% on route 2c and route 37, not 77.5%.",
        "★★ V66 IS EXCLUDED BY THE Kd SIGNATURE, which is the first thing that has ever separated "
        "the V66/V67 pair -- payload cannot (see identify()). V66 reverts BOTH `sar` taps, so it is "
        "Kd=1 in BOTH arms and must read ~1.0 against the Kd=1 pool in both. Measured "
        "(studies/sessions/r47/analyze_r47_grind1.py S3c, 18-22 Hz engaged-creep envelope p99, cell-stratified, "
        "episode-clustered): ENGAGED arm 0.524 [0.337, 0.804] vs the Kd=1 pool and 1.183 "
        "[0.773, 1.617] vs the Kd=2 pool, while the DISENGAGED arm reads 1.055 [0.669, 1.354] vs "
        "the Kd=1 pool. Suppression in ONE arm only is V67's conditional design and no other built "
        "artifact produces it.",
        "🛑 This is strong evidence, not proof: it rests on 28 engaged-creep windows / 11 episodes. "
        "CONFIRM THE .rwd FILENAME as well.",
        "flight health: ST==4 = 0/150,327; ST==3 = 12; zero steerUnavailable / steerTempUnavailable "
        "/ canError / controlsMismatch / immediateDisable / steerSaturated.")),
    # ⚠ ROUTES 4f / 50 / 54 / 58 ARE MISSING FROM THIS TABLE. They were flown and cached (V69, V70,
    # V71B, V71C) but never rowed here, so the standing practice lapsed for four routes. Not
    # back-filled from route 59's seat -- fabricating their evidence would be worse than the gap.
    Route("59", "9070b9dcee", "V72",
          "5 rungs on THREE cells: bit6/bit5 = `a` (gp-0x69a4) thermometer at 512/1024, "
          "bit4 = |gp-0x6bd0| >= 64 (base damper), bit3 = gp-0x6ac0 >= 512 (rate axis)", 2.0,
          image_sha="466b5f29", rwd_sha="2751ffa6", evidence=(
        "87,953 raw 0x14A src-1 byte4 frames over 15 segments (879.4 s) take exactly THREE values: "
        "{0x87: 82,965, 0x8F: 4,788, 0xC7: 200}. bit7 set on every one ⇒ VOID = 0 and V53 (0x07) "
        "and V54 (0x0F) are EXCLUDED ABSOLUTELY.",
        "★★ The bit5 => bit6 MONOTONE INVARIANT holds with ZERO violations in all 87,953 frames. On "
        "V72 both `a` rungs come from ONE `sar 0x9`, so the implication is structural and a single "
        "violation would have falsified V72. ⚠ ONE-WAY: holding does not prove it.",
        "★ 0xC7 sets bit6 with bit5 CLEAR ⇒ V65's ladder invariant (bit6 => bit5) is VIOLATED ⇒ V65 "
        "EXCLUDED. 0x8F sets bit3 ⇒ V66/V67 EXCLUDED (bit3 is never set there). 0x87 is present ⇒ "
        "V68 EXCLUDED; and 0x87 is NOT constant ⇒ this is not V64's frozen null.",
        "V59/V62 survive the STRUCTURAL test -- all three values are thermometer-legal -- and are "
        "excluded on SEMANTICS instead: under V59/V62 bit6 is the FAULT sentinel, measured at "
        "0.000% on routes 2c and 37, whereas here it fires in 200 frames (0.227%), all engaged, all "
        "at 84-105 km/h. Same style of argument as route 47's.",
        "★★ THE CAVE IS PINNED BY ITS OWN POSITIVE CONTROL. bit3 agrees frame-for-frame with bus "
        "|rate_c| >= 108.66 deg/s (512 counts / 4.7121) in 87,914 / 87,940 frames = 99.9704% "
        "(recall 99.69%, precision 99.77%), and a 1 deg/s sweep peaks at 109 deg/s ⇒ implied scale "
        "4.697 counts-per-deg-s vs the settled 4.7121, a 0.3% error. Engaged duty 3.373% against "
        "the PRE-REGISTERED 2.750% -- inside the factor-of-1.5 band written before the drive.",
        "★ THE TWO V72 CUTS ARE SEPARABLE ON THIS ROUTE, unlike the V70 re-cut. `_v72_plain_image."
        "bin` carries decode_v72_probe.CAVE_HEX byte-for-byte at 0xC4B34 (Python byte read); the "
        "SUPERSEDED plateau-only image's 68 cave bytes DIFFER, and the difference is in the bit3 "
        "rung. The observed rung is `>= 512 counts` at 99.970% agreement, against 92.340% for the "
        "next candidate threshold tried (144 counts) ⇒ the flown artefact is the WHOLEAXIS cut. "
        "🛑 CONFIRM THE .rwd FILENAME as well: payload narrows, it does not prove.",
        "🛑 bit4 (|gp-0x6bd0| >= 64) read ZERO in all 87,953 frames INCLUDING 34,275 frames "
        "(342.8 s) above 35 km/h, where the rung's own pre-registered positive control says stock "
        "already damps ⇒ that rung's creep reading is UNINTERPRETABLE. It does not bear on build "
        "identification: bit3 and bit6 both vary, so the cave demonstrably ran.",
        "⚠ SIGNEDNESS OF THE `a` RUNGS, RESOLVED: the cave's `a` and rate loads are `ld.hu` "
        "(opcode 0x3F, ZERO-extending) and only the damper load is `ld.h` (0x39) -- GhidraMCP "
        "decodes 0x3AB3A `e4375d96`, byte-identical to the cave's own load, as `ld.hu -0x69a4,gp,"
        "r6`. So bit6 is `raw16 >= 512` UNSIGNED, and a negative int16 `a` (raw >= 0x8000) would "
        "necessarily have set bit5. bit5 read 0 / 87,940 ⇒ raw16 < 1024 in EVERY frame ⇒ no frame "
        "carried a negative value, and the bracket holds under either signed or unsigned reading.",
        "★★★★ `a` = gp-0x69a4 < 512 (< 0.5 in Q10) in 100.000% of 39,160 creep frames, including "
        "1,503 engaged-creep frames at |cs_tq| >= 2517 where the engaged-HIGHWAY arm fires 41.1% "
        "⇒ a POWERED null, not an empty regime. bit5 (a >= 1024) is 0 / 87,940 route-wide.",
        "⚠ kd = 2.0 IS SPEED-CONDITIONAL AND UNGATED on this build: the whole rate axis is armed at "
        "the 0 and 10 km/h records (r24 -> 5244, r26 -> 512) and the 50/100 km/h records are "
        "BYTE-STOCK ⇒ highway is EXACTLY 1.000000x by record-selection geometry, and the dose "
        "applies in the MANUAL arm too. Route 59's manual data is NOT a stock control.",
        "flight health: ST==4 = 0/87,940; ST==3 = 13 (all in segment 14, parked); no "
        "steerUnavailable / steerTempUnavailable / canError / controlsMismatch / steerSaturated. "
        "The soft-disable events are wrongGear (parked) plus commIssue / selfdrivedLagging, the "
        "known device-load signature.")),

    # -------------------------------------------------------------------------------------------
    # Added 2026-08-05. These eight routes were present in `analysis-2020accord/rlogs/` and ABSENT
    # from this table, which is exactly the gap this module exists to close. Every attribution below
    # is sourced to the route's OWN byte4 payload set (raw 0x14A src-1 walk) or to the cache's
    # mechanically-asserted `probe_rwd`, never to handoff prose. 🛑 Two are flagged UNRESOLVED and
    # must not be used as build-attributed data until the .rwd filename is checked.
    # -------------------------------------------------------------------------------------------
    Route("4a", "346bf31d97", "V66-or-V67 (UNRESOLVED)",
          "V66/V67 payload class: bit6 = gp-0x6806 (LKAS gate), bits 5/4/3 silent", None, evidence=(
        "35,994 frames over 12 segments. byte4 takes exactly TWO values, {0x87: 17,086, "
        "0xC7: 18,913}: bit7 set and bit3 clear on both ⇒ the V66/V67 payload class holds, and "
        "V53 (0x07) / V54 (0x0F) / V68 (never emits 0x87) are EXCLUDED.",
        "★ bit6 == carControl.latActive in 35,980 / 35,994 frames (99.9611%); the 14 disagreements "
        "are single-frame transition edges. Same signature route 47 used to identify bit6 as "
        "gp-0x6806. bits 5/4/3 read 0.000% route-wide.",
        "🛑 UNRESOLVED, AND DELIBERATELY SO: route 47's own entry records that the PAYLOAD CANNOT "
        "SEPARATE V66 FROM V67 -- that pair needed the Kd dose signature (a one-armed 18-22 Hz "
        "suppression) to break. That analysis has NOT been run on this route, so the build is left "
        "as a pair and `kd` is None rather than guessed. V66 is Kd=1 in BOTH arms; V67 is Kd=2 in "
        "the engaged arm only, so a wrong pick here would mislabel the dose in every cross-build "
        "pool this route entered.",
        "⇒ TO RESOLVE: run the route-47 Kd argument (engaged vs disengaged 18-22 Hz envelope p99 "
        "against the Kd=1 and Kd=2 pools, cell-stratified, episode-clustered), or read the .rwd "
        "filename from the flash record for this drive.")),

    Route("4c", "d0ea3c14b4", "V68",
          "V68 probe; bit3 CONSTANT 1 is the class discriminator, bit6 tracks engagement", None,
          evidence=(
        "30,000 raw 0x14A src-1 byte4 frames over 5 segments (independent rlog walk, no cache) "
        "take exactly TWO values: {0x8F: 25,036, 0xCF: 4,964}.",
        "★ bit3 is SET on 30,000 / 30,000 frames. That is the discriminator route 59's entry names "
        "from the other side: '0x87 is present ⇒ V68 EXCLUDED' -- i.e. V68 never emits a bit3-clear "
        "payload. It simultaneously EXCLUDES V66/V67 (route 47: 'bit3 is never set there'), V53, "
        "V54 and V69 (route 4f below is constant 0x87).",
        "bit6 fires on 4,964 / 30,000 = 16.5% of frames, i.e. it varies ⇒ the cave demonstrably ran "
        "and this is not a frozen-null stream.",
        "🛑 `kd` left None: V68's rate-lane dose is GATED and speed-conditional, so no single scalar "
        "multiplier is correct for this route and a number here would be pooled as if it were.",
        "⚠ CONFIRM THE .rwd FILENAME. The payload class pins V68; it does not pin which V68 cut.")),

    Route("4e", "11f5b814b6", "V68",
          "V68 probe; bit3 CONSTANT 1, bit6 CONSTANT 1 (the drive is fully engaged)", None,
          evidence=(
        "23,999 raw 0x14A src-1 byte4 frames over the 4 segments held locally take exactly ONE "
        "value: {0xCF: 23,999}. bit7 set ⇒ VOID = 0.",
        "★ SAME PAYLOAD CLASS AS ROUTE 4c: bit3 SET on every frame ⇒ V68, and V66/V67/V69/V53/V54 "
        "excluded by the same argument recorded there.",
        "bit6 constant 1 ⇒ latActive true throughout, consistent with this route's role as the "
        "highway lane-change capture (BUILD-LINEAGE records the ~28 Hz transient at seg 33).",
        "⚠ ONLY 4 OF THIS ROUTE'S SEGMENTS ARE PRESENT LOCALLY -- the lineage references seg 33, so "
        "the local copy is a SUBSET. Any exposure census computed from these files is a census of "
        "the subset, not of the drive.",
        "🛑 A CONSTANT payload is the weakest possible build evidence: it proves only that a "
        "bit3-setting, bit6-setting cave ran. CONFIRM THE .rwd FILENAME before using this route in "
        "a cross-build comparison.")),

    Route("4f", "61171e660d", "V69",
          "V69 ratchet probe: bit6 gp-0x6ada>=+4096, bit5 gp-0x6b62>=+4096, bit4 gp-0x6ad4>=+4096, "
          "bit3 CONSTANT 0", None, evidence=(
        "47,997 byte4 frames over 8 segments take exactly ONE value: {0x87: 47,997}, bit7 set.",
        "★ THIS MATCHES THE FLIGHT RESULT ALREADY RECORDED IN docs/BUILD-LINEAGE.md FOR V69 EXACTLY "
        "-- 'byte4 = 0x87 on 100% of frames, bit7 set, bit3 = 0 ⇒ V68 excluded absolutely'. The "
        "row is therefore a cross-check of an existing attribution, not a new inference.",
        "🛑 ALL THREE OF V69's RUNGS READ ZERO, so the payload carries no within-build information "
        "and the identification rests on (a) the constant-0x87 signature excluding V68 (bit3≡1), "
        "V66/V67 (bit6≡latActive, and this route is 345.7 s engaged with bit6 = 0 throughout) and "
        "V53/V54, and (b) the lineage record. ⚠ A constant 0x87 is ALSO V64's frozen-null "
        "signature and V73's mode 0 -- neither applies here on route ordering, but the payload "
        "alone cannot say so. CONFIRM THE .rwd FILENAME.",
        "🛑 `kd` left None ON PURPOSE: V69's dose is 4.000x to 10 km/h falling to EXACTLY 1.000x at "
        "and above 50 km/h, by record-selection geometry. No scalar is correct.")),

    Route("50", "50f2e00e8f", "V70",
          "V70 4-bit SIGN probe: bit6 gp-0x6ada>=+512, bit5 gp-0x67fa==10, bit4 gp-0x6adc>=0, "
          "bit3 gp-0x6ada>=0", None, evidence=(
        "18,012 byte4 frames over 3 segments take THREE values: {0x87: 1,644, 0x97: 2,360, "
        "0x9F: 14,008}. bit7 set on all ⇒ VOID = 0.",
        "★ V70's structural invariant bit6 => bit3 HOLDS -- vacuously, because bit6 never fires in "
        "any of the three values. That is consistent with V70 but, being vacuous, it does NOT "
        "discriminate; the invariant only excludes builds when bit6 actually sets.",
        "★ bit5 (gp-0x67fa == 10, the state gate) reads 0 in every frame, which is exactly the "
        "PRE-REGISTERED prediction recorded for V70 ('bit5 reads LOW').",
        "🛑🛑 V70 WAS RE-CUT, AND THE TWO CUTS SHARE A BYTE-IDENTICAL CAVE ⇒ THE PAYLOAD CANNOT "
        "SEPARATE THEM. The first cut is renamed `SUPERSEDED-DO-NOT-FLASH-…`. Unlike route 59 -- "
        "where the two V72 cuts differ in the bit3 rung and so ARE separable from the data -- here "
        "the .rwd FILENAME is the ONLY discriminator. Treat this row as 'V70, cut unknown'.")),

    Route("54", "4e67ae1164", "V71B",
          "V71 4-rung probe (see rlog-tools/probe/decode_v71_probe.py)", None,
          evidence=(
        "★ ATTRIBUTED FROM CACHE PROVENANCE, NOT PAYLOAD: `_scratch/cache/r54/r54s*.npz` carries "
        "`probe_build = 'V71B'` and `probe_rwd = '39990-TVA,A160-V71B-LKAS-4x-mss0-decouple0xC646C-"
        "RESTORE-0x454FE-gainA…'`. `extract/extract_r54_cache.py` re-reads CAVE_HEX and RWD_NAME out of the "
        "decoder at import time and FAILS the extraction if either has drifted, so the label is "
        "mechanically linked to the decoded artefact rather than typed in.",
        "223,296 byte4 frames over 21 segments: {0x87: 13,019, 0x8F: 110,128, 0x97: 61, "
        "0x9F: 88} -- four values, bit7 set on all, so the cave ran and multiple rungs vary.",
        "🛑 `kd` left None: V71B's LKAS 4x is not the r24 rate-lane scalar this field means.")),

    Route("58", "1d1005262f", "V71C",
          "V71 4-rung probe (see rlog-tools/probe/decode_v71_probe.py)", None,
          evidence=(
        "★ ATTRIBUTED FROM CACHE PROVENANCE: `_scratch/cache/r58/r58s*.npz` carries `probe_build = 'V71C'` "
        "and `probe_rwd = '39990-TVA,A160-V71C-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-V67ga…'`"
        ", under the same import-time CAVE_HEX/RWD_NAME assertion as route 54.",
        "92,840 byte4 frames over 16 segments: {0x87: 26,667, 0x8F: 61,677, 0x97: 2,239, "
        "0x9F: 2,249, 0xAF: 8} -- five values, bit7 set on all.",
        "🛑 `kd` left None, same reason as route 54.")),

    Route("5a", "2d32bec040", "V73",
          "bit7 liveness; bits 6:3 = (gp+0x63FD) & 0xF, THE BASE-ASSIST DAMPER MODE SELECTOR; "
          "bits 2:0 = stock STEER_SENSOR_STATUS", None, evidence=(
        "★ ATTRIBUTED FROM CACHE PROVENANCE: `_scratch/cache/r5a/r5as*.npz` carries `probe_build = 'V73'` "
        "and the full V73 `probe_rwd`; `extract/extract_r5a_cache.py` re-reads CAVE_HEX and RWD_NAME out of "
        "`rlog-tools/probe/decode_v73_probe.py` at import and fails the extraction on any drift.",
        "104,061 byte4 frames over 18 segments take exactly TWO values: {0xC7: 26,295, "
        "0xD7: 77,766} ⇒ mode 8 (25.27%) and mode 10 (74.73%). bit7 set on 104,061/104,061 ⇒ "
        "VOID = 0, 0 illegal. Confirmed by an independent raw rlog walk on segs 0/2/13/16 that "
        "shares no code with the cache decoder: counts matched EXACTLY.",
        "★★★★ THE MODE IS A DETERMINISTIC FUNCTION OF ENGAGEMENT, not of HW-ID coding as the traced "
        "structure predicted: mode 8 while disengaged, mode 10 while engaged, with a 1.02 s "
        "ON-delay (n=9, sd 4.9 ms) and a 2.08 s OFF-delay (n=9, sd 0.8 ms). Modelling that "
        "asymmetric delay leaves 4 residual frames / 104,061 = 0.0038%, all single-frame edge "
        "quantisation. All 18 mode edges pair 1:1 with an engagement edge of the same direction.",
        "🛑 THE READING IS `mode & 0xF`. The probe emits 4 bits, so 8 aliases 24 and 10 aliases 26. "
        "The 0xCD000 config-row table contains NO row with raw mode 8; row 11 (TVCA4) -> "
        "[24,25,26,27] is the only row aliasing to (8,10) ⇒ THE CAR RUNS MODES 24 (manual) / 26 "
        "(engaged), and the 4-bit reading alone could not have said so.",
        "🛑🛑 CONSEQUENCE FOR EVERY PRIOR DAMPING/FRICTION BUILD: modes 24 and 26 point at FactorC "
        "0xD67E4 / 0xD77D0, FactorE 0xD6820 / 0xD780C and friction 0xD6A64 / 0xD7A54, and ALL SIX "
        "records are BYTE-IDENTICAL TO STOCK in the V73 image (Python byte read). V44/V47/V72 wrote "
        "modes 10/11; V73 wrote 0-5/12/14 plus mode 10's friction record. NONE of them was ever "
        "READ by this car. ⇒ V73's Lever E was in force on 0 / 104,061 frames.",
        "⚠ ALL 16 payload values are legal on V73 (no `bit5 => bit6` analogue), so the value SET "
        "proves only that SOME bit7-setting cave ran. mode 0 would transmit as 0x87, colliding with "
        "V64's frozen null. The .rwd FILENAME remains the pre-drive discriminator.",
        "⚠ An earlier V73 cut targeting modes 0/2 ONLY exists, renamed `SUPERSEDED-DO-NOT-FLASH-…`. "
        "Its probe is identical, so the stream cannot separate the cuts -- the V70 hazard again.",
        "flight health: ST==4 = 0/104,061; ST==3 = 5 (segment 17, parked); fs = 99.98-100.03 Hz. "
        "⚠ segment 0's wall clock is unusable (wall_t0 07:05:06 against segment 1's 09:01:38, clk "
        "sd 1.5e7); relative time within the segment is unaffected.")),
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

    # ★★ V68: bit7 AND bit3 are BOTH hard-wired constants (one `movea 0x88,r0,r7`), so V68 never
    # emits 0x87 and every legal frame carries both. This is the first build in the kit that any
    # payload test can pin -- and it is NOT absolute. Stated at its real strength:
    #   * ABSOLUTE against V53 (0x07), V54 (0x0F, bit7 clear) and V66/V67 (bit3 NEVER set).
    #   * WEAK against V59/V62: six of V68's eight payloads {0x8F,0x9F,0xBF,0xCF,0xDF,0xFF} are
    #     also thermometer-legal, so the thermometer branch above stays in the candidate set and
    #     is only resolved by V59/V62's recorded routes containing 0x87 (which V68 cannot emit).
    #   * NEARLY absolute against V65: only 0x9F is ladder-legal.
    v68_ok = all((v >> 7 & 1) and (v >> 3 & 1) for v in vals) and 0x87 not in vals
    if v68_ok:
        cands |= {"V68"}
        notes.append("bit7 AND bit3 set on every value and 0x87 absent -> V68 possible. This "
                     "EXCLUDES V53/V54/V66/V67 absolutely; V59/V62 overlap 6 of 8 payloads and are "
                     "excluded only because their recorded routes contain 0x87.")
    else:
        notes.append("★ a value lacks bit3 or bit7, or 0x87 is present -> V68 is EXCLUDED")

    # ★★ V72: bit7 hard-wired 1, and `bit5 => bit6` MONOTONE because both `a` rungs come from ONE
    # `sar 0x9`. A single bit5-set/bit6-clear frame falsifies V72 outright -- the strongest
    # single-frame falsifier any build in this table carries. 🛑 It is ONE-WAY: 12 of 16 payloads
    # remain legal and six of them are thermometer-legal too, so V59/V62 are NOT excluded by
    # structure and V72 is NOT confirmed by it. Semantics and the .rwd filename do the rest.
    v72_ok = all((v >> 7 & 1) and (not (v >> 5 & 1) or (v >> 6 & 1)) for v in vals)
    if v72_ok:
        cands |= {"V72"}
        notes.append("bit7 set and bit5 => bit6 on every value -> V72 possible. 🛑 ONE-WAY: this "
                     "cannot CONFIRM V72, only fail to falsify it. V72's own positive control is "
                     "bit3 == (bus |rate_c| >= 108.66 deg/s) frame-for-frame.")
    else:
        notes.append("★ bit7 clear somewhere, or bit5 set with bit6 clear -> V72 is EXCLUDED")

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
    # 🛑 V66 and V67 always appear TOGETHER or not at all -- there is no payload that separates them.
    for probe in ([0x87], [0x87, 0xC7], [0x87, 0xF7, 0xB7], [0x87, 0x97, 0xA7]):
        c, _ = identify(probe)
        assert ("V66" in c) == ("V67" in c), f"{probe}: V66/V67 must never be separable, got {c}"
    assert "V66" not in identify([0x8F])[0], "bit3 set must EXCLUDE V66/V67"
    assert identify([0x07])[0] == {"V53"}
    assert identify([0x0F])[0] == {"V54"}
    # ---- V68: the first build any payload test can pin, and its limits, both asserted ----------
    v68_all = sorted({0x88 | a | b | c | 0x07
                      for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)})
    c, _ = identify(v68_all)
    assert "V68" in c, "V68's own full payload set does not identify as V68"
    assert not ({"V53", "V54", "V66", "V67", "V65"} & c), \
        f"V68's payload set must exclude V53/V54/V65/V66/V67 absolutely, got {c}"
    # 🛑 ...and the honest limit: a V68 log restricted to thermometer-legal bytes does NOT exclude
    # V59/V62. Asserted so nobody can quietly upgrade the claim.
    c, _ = identify([0x8F, 0xCF])
    assert {"V68", "V59", "V62"} <= c, \
        f"V59/V62 must REMAIN candidates on thermometer-legal V68 bytes, got {c}"
    assert "V68" not in identify([0x87, 0xCF])[0], "0x87 present must EXCLUDE V68"
    assert "V68" not in identify([0x87])[0] and "V68" not in identify([0x97, 0xA7])[0]
    for probe in ([0x87], [0x87, 0xC7], [0x87, 0x97, 0xA7]):
        assert "V68" not in identify(probe)[0], f"{probe} must not identify as V68"
    # ---- V72 (route 59): the monotone invariant, and its honest one-way limit ------------------
    c, _ = identify([0x87, 0x8F, 0xC7])                      # route 59's ACTUAL payload set
    assert "V72" in c, "route 59's own payloads must not falsify V72"
    assert not ({"V53", "V54", "V64", "V65", "V66", "V67", "V68"} & c), \
        f"route 59's payloads must exclude V53/V54/V64-V68, got {c}"
    assert {"V59", "V62"} <= c, \
        "🛑 V59/V62 must REMAIN candidates on V72 payloads -- they are excluded on SEMANTICS " \
        "(bit6 is their fault sentinel, measured 0.000%), never on structure. Do not upgrade this."
    # 0xA7 = bit5 set, bit6 clear -- the single-frame falsifier. (0x97 is bit4, not bit5.)
    assert "V72" not in identify([0x87, 0xA7])[0], "bit5 set with bit6 clear must EXCLUDE V72"
    assert "V72" not in identify([0x07])[0] and "V72" not in identify([0x0F])[0]
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
