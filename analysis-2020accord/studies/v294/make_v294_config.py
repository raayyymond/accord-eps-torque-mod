# -*- coding: utf-8 -*-
"""toggle-config_V294_accel-trim_r1: the fork config that flies V294.  EVERY torque-mode fork term OFF, the generic
torque controller on, with three settings that follow from the EPS no longer being a rate servo.

WHAT IT IS.  The V282-era reference config (toggle-config_V282_rate_servo_REVERT.decoded.json: SteerKP 0.9,
AccordTorqueKi 0.3, the values the three "good" V282 routes 64/65/6c flew) with:
  * AccordRatePlantFF false  -- the plant FF models a RATE SERVO (V282 tables) or the bare torque map (V293
                                tables); V294 is neither.  The generic torque-controller FF path runs instead.
  * SteerLatAccel 14.0       -- the torque unit is REAL torque on V293/V294 (2461 counts = 1.0); 14 is the value
                                fitted on the torque map (routes 70/71, rev 2), not the 6.0 fitted THROUGH the
                                V282 rate servo, where "torque" was a rate.
  * SteerFriction 0.011      -- the measured Coulomb friction on the torque map (route 70 ident, 0.010-0.012),
                                the generic relay's own unit.  V282 flew 0.010-0.030 clean for months.
  * every V293 term explicitly at its stock value (AccordHoldMap/FrictionHyst/RateLoopGain/ErrorNotchQ/RefFilter/
    TorqueKiHigh/DobHz/HoldLevel/FrictionHystBand/Dither off, AccordJerkLpHz 1.2), so the file is a complete
    statement regardless of what the device's params hold.
Lane centering stays on.  Nothing else moves.

Codec positive control over every reference pair first; the diff against the V282 reference is asserted to be
exactly the set named above plus the explicit torque-mode zeros.
"""
import base64
import json
import os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1


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
    e = json.load(open(ep, encoding="utf-8"))
    d = json.load(open(REF / f, encoding="utf-8"))
    assert dec(e["data"]) == d, f"decode mismatch {f}"
    assert dec(enc(d)) == d, f"re-encode mismatch {f}"
    pairs += 1
assert pairs > 0
print(f"codec positive control: {pairs} reference pairs round-trip both directions")

v282 = json.load(open(REF / "toggle-config_V282_rate_servo_REVERT.decoded.json", encoding="utf-8"))
assert v282["SteerKP"] == 0.9 and v282["AccordTorqueKi"] == 0.3 and v282["AccordRatePlantFF"] is True

cfg = dict(v282)
cfg["AccordRatePlantFF"] = False
cfg["SteerLatAccel"] = 14.0
cfg["SteerFriction"] = 0.011
TORQUE_MODE_OFF = {
    "AccordHoldMap": False, "AccordFrictionHyst": 0.0, "AccordRateLoopGain": 0.0, "AccordErrorNotchQ": 0.0,
    "AccordRefFilter": 0.0, "AccordTorqueKiHigh": 0.0, "AccordDobHz": 0.0, "AccordHoldLevel": False,
    "AccordFrictionHystBand": False, "AccordDither": 0.0, "AccordDitherGate": True, "AccordJerkLpHz": 1.2,
    "AccordFFRateGain": 0.5, "AccordEpsGainScale": 1.0, "AccordEpsSpringScale": 1.0,
}
cfg.update(TORQUE_MODE_OFF)
cfg["LaneCentering"] = True
diff = {k: (v282.get(k), cfg.get(k)) for k in set(v282) | set(cfg) if v282.get(k) != cfg.get(k)}
assert set(diff) == {"AccordRatePlantFF", "SteerLatAccel", "SteerFriction", "LaneCentering"} | set(TORQUE_MODE_OFF), diff
assert cfg["SteerKP"] == 0.9 and cfg["AccordTorqueKi"] == 0.3 and cfg["KeepLearnedLatAccelOffset"] is True
assert cfg["ForceAutoTuneOff"] is True and cfg["AdvancedLateralTune"] is True

name = "toggle-config_V294_accel-trim_r1"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(cfg), "data": enc(cfg)},
          open(out, "w", encoding="utf-8"), indent=1)
json.dump(cfg, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == cfg
print(f"wrote {out.name}: {len(cfg)} settings; vs the V282 reference: {sorted(diff)}")

# the revert file: V293 rev 6.4 as flown, for the device if V294 goes back to V293 in the same session
asflown = json.load(open(REF / "toggle-config_V293_r64_ARM-A_asflown.decoded.json", encoding="utf-8"))
rev = dict(asflown)
rev["AccordJerkLpHz"] = 4.0        # rev 6's hard-coded value, now a toggle -- as flown
rname = "toggle-config_V294_accel-trim_r1_REVERT_to_V293_r64"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(rev), "data": enc(rev)},
          open(REF / f"{rname}.json", "w", encoding="utf-8"), indent=1)
json.dump(rev, open(REF / f"{rname}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(REF / f"{rname}.json", encoding="utf-8"))["data"]) == rev
print(f"wrote {rname}.json: rev 6.4 as flown + AccordJerkLpHz 4.0 (the value rev 6 hard-coded)")
