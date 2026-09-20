# -*- coding: utf-8 -*-
"""ARM-KP2: rev 6.4 as flown, SteerKP 1.0 -> 3.0 AND AccordErrorNotchQ 1.0 -> 0.60.  Two toggles.

SUPERSEDES ARM-KP (SteerKP 2.0 alone).  It STRICTLY DOMINATES it on every measured axis:
    closure 33.3 % vs 22.5 %  |  command shake x1.148 vs x1.199  |  shake-band |L| 0.195 vs 0.200
    Ms 1.24 vs 1.25           |  crossover 0.20 Hz PM 141 deg vs 0.88 Hz PM 95 deg
A DOMINANCE claim survives a common multiplicative error in the estimator; a LEVEL claim does not.  That is why
this config is recommended on dominance rather than on its headline number.

🛑 TWO CORRECTIONS TO ARM-KP's OWN DOCSTRING, both re-derived by four independent implementations:
 1. "the loop finally crosses unity at KP 2.0" DOES NOT REPRODUCE.  Max |L| at >=15 m/s is 0.736 (15-22) and
    0.845 (22+).  The first crossing is at SteerKP ~2.7-3.0.
 2. Under ONE denominator across bands, **98 % of the gap is 0.15-0.60 Hz** and there is NO gap above 0.60 Hz
    (V282 0.269 vs torque 0.286).  The earlier "regime B = 64 % of the gap" was a per-band normalisation
    artefact.  The 1.8-3.5 Hz shake band is entirely OUTSIDE the metric -- it is a COST axis, not a gap.

THE METRIC (unchanged): total X->Y error power 0.15-2.4 Hz over in-band demand power, ONE denominator, >=15 m/s,
laterally-engaged hands-off runs >=30 s.  rev 6.4 as flown J = 1.3512 (reproduced to four figures by two
independent implementations).  V282 reference 0.442.
    PREDICTED:  J 1.3512 -> 1.058  =  **33.3 % of the gap**.  Bands 0.568/0.497/0.145/0.141 -> 0.385/0.396/0.139/0.138.
    No route regresses: 6c 1.290->1.014, 6d 1.492->1.136, 6e 0.963->0.738, r76 1.178->0.916.
    Both speed bins improve: 15-22 m/s 1.917->1.478, 22+ 1.259->0.981.

WHY THE NOTCH EARNS ITS PLACE.  `AccordErrorNotchQ` LOWER = WIDER = more attenuation at the steering mode.  It
buys back the shake that the gain raise spends, so the pair costs LESS felt shake than SteerKP 2.0 alone while
closing half again as much.  Lower Q is also the CONSERVATIVE direction at the 2.34 Hz mode that limit-cycled
r71.  Bounds [0.0, 4.0] (starpilot_variables.py:835), declared `params_keys.h:401` default "1.0" in the same
block as AccordRateLoopGain and AccordRefFilter, both of which appear in flown initData -- so the key is on the
device.  ⚠ Q <= 0 BYPASSES the notch: the minimum is the WORST setting, not "no filtering".

🛑 THE SIDE EFFECT THIS CONFIG CARRIES, NAMED IN ADVANCE AND VERIFIED BY HAND.
`error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))` (latcontrol_torque.py:342) puts kp in
the INTEGRATOR's denominator.  For P it cancels exactly (gain = kp + lsf); for I it does not.  So SteerKP 1 -> 3
CUTS low-speed integral authority:
    v m/s        2      4      6      8     10     15     22     28
    I ratio   0.35   0.41   0.48   0.57   0.65   0.82   0.93   0.97
That is the regime the operator calls ratchety, and it is OUTSIDE the metric (scored >=15 m/s, where lsf <= 0.38).
**REPAIR, PRE-AUTHORISED, ONE TOGGLE:** `AccordTorqueKi` 0.30 -> 0.60 restores it to x0.70 at 2 m/s and x1.14 at
8 m/s, and was measured to change the metric by NOTHING (J identical to three decimals, shake identical).  It is
NOT in this config because the dominance result above was established on exactly two toggles -- but if a new
LOW-SPEED symptom appears, apply it rather than abandoning the class.

WHAT IS EXPLICITLY NOT IN THIS CONFIG, AND WHY:
 - `AccordRateLoopGain` 0.001 -> 0.003 (a design stream's headline): **GATE 2 FAILURE, DO NOT FLY.**  Three
   independent lines: the measured inner-loop return ratio |g*F*G| reaches 0.834 at 1.95 Hz and 1.087 at
   3.52 Hz at the toggle ceiling; the fork's OWN source comment (latcontrol_vehicle_tunes.py:281-286) says the
   rate-loop-alone gain must stay below 1 at its -180 deg crossing and that "at 0.0012 it would cross"; and the
   shake-band |L| rises 0.105 -> 0.570, the signature of an inner loop turning from damping into pumping.
 - `SteerLatAccel`: on this study's RETIRED list.  Real bounds are [0.845, 16.893] (latAccelFactor 1.6893 x 0.5
   and x10.0), not the "floor 7.0" a stream asserted.  It has NO low-speed taper -- LAF 14->9 raises the P gain
   at 2 m/s by x1.62 where SteerKP 1->3 raises it by x1.06.
 - `AccordTorqueKiHigh`: measured NEGATIVE on this metric at every dose >= 1.0.

HONEST CEILING: the loop-gain class is not structurally capped (infinite gain gives ~101-106 % closure), but the
maximum DEFENSIBLE closure without spending retired levers is ~33-37 %, and it is bound by the SteerKP ceiling of
3.00 plus the shake cost.  Going further needs fork code (the `STEER_KP_MAX_MULT = 5.0` constant, or a
speed-scheduled notch Q).  This config takes the class as far as toggles reach.

PRE-REGISTERED READOUT -- one short symptomatic drive, >=15 m/s, laterally engaged, hands off:
 G0 TOGGLE TOOK.  initData must carry SteerKP 3.0 AND AccordErrorNotchQ 0.6.  If the notch key reads ABSENT,
    the device's params .so lacks it: **the drive is VOID, not a null.**
 G1 median(torqueState.p / torqueState.error) must read 3.000; median(-(p+i+f)/output) must still read 14.00.
 G2 NOTCH DEPTH ON THE WIRE.  Re-synthesise error_with_lsf and push it through the notch at Q 0.6 and at Q 1.0;
    RMS residual vs the LOGGED torqueState.error must be <= 1e-3 against Q 0.6 and >= 0.05 against Q 1.0.
 G3 THE METRIC.  Predicted J = 1.06.  PASS if J <= 1.16 (>= 22.5 %, at least matching ARM-KP).  FAIL if J >= 1.30.
 G4 BAND SIGNATURE -- the mechanism, not just the number.  0.15-0.30 Hz must fall >= 20 % (predicted x0.68) and
    0.30-0.60 Hz >= 10 % (predicted x0.80), while 0.60-2.40 Hz stays flat within +/-15 %.
    **A metric win with the wrong band signature is not this mechanism and must not be credited to it.**
 G5 SHAKE.  1.8-3.5 Hz steeringRateDeg RMS as a ratio to rev 6.4 on comparable windows.  Predicted <= x1.15.
 G6 LIMIT-CYCLE SCREEN.  No sustained (>3 s) narrow line in 1.8-3.5 Hz.  Common-unit references: rev 6.4 = 32.4,
    r72 (flew clean) = 19.4, **r71 (limit-cycled) = 176.0**.

REVERT = SteerKP 1.0, AccordErrorNotchQ 1.0.  Trigger on ANY of:
 R1 1.8-3.5 Hz wheel-rate RMS > x1.40 of rev 6.4's, or any sustained 1.8-3.5 Hz line.
 R2 The operator reports oscillation, buzz, or a new hunting feel at speed.
 R3 J >= 1.30.  **CLASS-CLOSING**: a null at the SteerKP ceiling WITH the shaping in place falsifies the
    loop-gain class for this build.  Close it, do not re-dose.
 R4 J improves but 0.60-2.40 Hz worsens by > 20 % -- the waterbed is being paid.  Step Q 0.60 -> 0.50 rather
    than backing off SteerKP.
 R5 A NEW LOW-SPEED symptom (< 8 m/s).  Cause named above; apply AccordTorqueKi 0.30 -> 0.60 first.

Exactly TWO settings differ from the as-flown config (asserted).  Codec positive control runs first.
"""
import base64, json, os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1
KP_CEIL = 0.6 * 5.0        # latcontrol_torque.py:28 KP x starpilot_variables.py:459 STEER_KP_MAX_MULT
NOTCH_LO, NOTCH_HI = 0.0, 4.0   # starpilot_variables.py:835


def xor(d, k):
    return "".join(chr(ord(c) ^ ord(k[i % len(k)])) for i, c in enumerate(d))


def enc(d):
    return base64.b64encode(xor(json.dumps(d), XOR_KEY).encode()).decode()


def dec(e):
    return json.loads(xor(base64.b64decode(e.encode()).decode(), XOR_KEY))


pairs = 0
for f in sorted(os.listdir(REF)):
    if not f.endswith(".decoded.json"):
        continue
    ep = REF / f.replace(".decoded.json", ".json")
    if not ep.exists():
        continue
    e = json.load(open(ep, encoding="utf-8")); d = json.load(open(REF / f, encoding="utf-8"))
    assert dec(e["data"]) == d, f"decode mismatch {f}"
    assert dec(enc(d)) == d, f"re-encode mismatch {f}"
    pairs += 1
assert pairs > 0, "no reference pair to validate the codec against"
print(f"codec positive control: {pairs} reference pairs round-trip both directions")

flown = json.load(open(REF / "toggle-config_V293_r64_ARM-A_asflown.decoded.json", encoding="utf-8"))
assert flown["AccordDobHz"] == 0.6 and flown["AccordHoldLevel"] is True, "ARM-A is not the rev 6.4 as-flown config"
assert float(flown["SteerKP"]) == 1.0, f"as-flown SteerKP is {flown.get('SteerKP')}, expected 1.0"

arm = dict(flown)
arm["SteerKP"] = 3.0
arm["AccordErrorNotchQ"] = 0.6
assert 0.05 <= arm["SteerKP"] <= KP_CEIL, f"SteerKP outside [0.05, {KP_CEIL}]"
assert NOTCH_LO < arm["AccordErrorNotchQ"] <= NOTCH_HI, "Q must be > 0 -- Q <= 0 BYPASSES the notch"
diff = {k: (flown.get(k), arm.get(k)) for k in set(flown) | set(arm) if flown.get(k) != arm.get(k)}
assert set(diff) == {"SteerKP", "AccordErrorNotchQ"}, diff

name = "toggle-config_V293_r64_ARM-KP2_shaped-loopgain"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(arm), "data": enc(arm)},
          open(out, "w", encoding="utf-8"), indent=1)
json.dump(arm, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == arm, "written file does not decode to the intended config"
print(f"wrote {out.name}: {len(arm)} settings, changes {diff}, verified by decoding the written file")
print(f"  SteerKP at its ceiling {KP_CEIL}; notch Q 0.6 in ({NOTCH_LO}, {NOTCH_HI}]")
print("  predicted J 1.3512 -> 1.058 = 33.3% of the gap, command shake x1.148 (DOMINATES ARM-KP on every axis)")
print("  low-speed integral falls to x0.35 at 2 m/s -- pre-authorised repair AccordTorqueKi 0.30 -> 0.60")
