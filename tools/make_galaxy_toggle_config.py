# -*- coding: utf-8 -*-
"""Write the Galaxy toggle-config files for the Accord EPS TORQUE-MODE firmware (V293+) and its revert.

The fork side of a torque-map EPS image is NOT code any more (2026-09-13, operator's call): it is a
plain toggle config that Galaxy restores through Settings -> toggle backup -> Restore.  Everything the
Testing-Ground / preset patches did on the control path is expressible with params that already exist
on `raayyymond-StarPilot/StarPilot` @ `Dom`:

    AccordRatePlantFF   True -> False   bypasses the rate-plant feedforward branch in latcontrol_torque.py
                                        (AccordEpsGainScale / AccordEpsSpringScale / AccordFFRateGain are
                                        read only inside that branch, so they go inert with no separate gate)
    SteerKP             0.9  -> 0.3     controlsd writes pid._k_p = [[0],[SteerKP]] every frame
    AccordTorqueKi      0.30 -> 0.15    applied in latcontrol_torque.py on every Accord frame
    SteerFriction       0.01 -> 0.00    🛑 a STABILITY choice: this fork feeds get_friction the LSF-inflated
                                        error, so the compensator gain is (friction/0.30)*(1+lsf/Kp) and a
                                        LOWER Kp makes it WORSE; at friction 0 the loop gain is monotone in Kp
    SteerLatAccel       6.0  -> 6.0     carried over so the first drive is not also a gain change (NOT an
                                        identification -- the first V293 drive identifies it)
    ForceAutoTuneOff    True (pinned)   makes the SteerLatAccel / SteerFriction params the live ones
    ForceAutoTune       False (pinned)
    AdvancedLateralTune True (pinned)   the SteerKP / SteerFriction / SteerLatAccel toggles are read only
                                        under it
    KeepLearnedLatAccelOffset True      the learner's roll/mounting bias stays -- it is a property of the
                                        device and the road, not of the EPS firmware
    AccordTurnFFTaper   False (pinned)  a shaping choice that would bias the LAF identification

The files are DELTAS, not full backups, on purpose.  Galaxy's /api/toggles/restore applies exactly the
keys present in the file and leaves every other param alone (`_restore_toggle_values` in
starpilot/system/the_galaxy/the_galaxy.py); a full 526-key backup taken on 2026-09-10 would also drag
back SteerRatio 16.33 and LaneChangeSmoothing 6, which route 6f's initData shows the operator has since
moved to 16.88 and 4.

File format = what Galaxy itself writes (`backup_toggle_values`): {"format": "starpilot-toggle-backup",
"version": 1, "createdAt": ISO-8601, "settingsCount": N, "data": base64(xor(json, KEY))}, with the codec
from starpilot/system/the_galaxy/utilities.py (`encode_parameters` / `decode_parameters`,
XOR_KEY = "s8#pL3*Xj!aZ@dWq", character-wise).  The codec is checked here against the operator's own
2026-09-10 backup and its decoded copy before anything is written.

REV 2 (2026-09-13, after the first V293 drive, route 70 -- `V293-PLANT-IDENT-2026-09-13.md`): the plant is a
SPRING + Coulomb friction, and the fork's own spring feedforward (the `AccordRatePlantFF` branch) is the right
SHAPE once its tables are re-identified -- which is fork CODE (commit 66cf4454a on Dom: HONDA_ACCORD_EPS_G_V /
K_V; the 4 m/s knot bounded by route 70's own hands-off data, ADV-REV2 finding 3), because no single
AccordEpsSpringScale fits both below 8 m/s and above 12 m/s.  The rev-2 delta then:

    AccordRatePlantFF   False -> True    the spring feedforward, on the V293 tables (fork >= 66cf4454a REQUIRED)
    AccordEpsSpringScale / AccordEpsGainScale 1.0   the tables carry the identification; scales stay unity
    AccordFFRateGain    0.5 (pinned)     with the V293 tables 1/G IS the measured viscous term, but the move term is fed
                                         a planner-limited reference: at 1.0 the FF alone passed full scale for 0.34 s
                                         below 8 m/s on route 70's demand (adversarial replay); at 0.5 max 0.81
    SteerFriction       0.00 -> 0.011    measured Coulomb friction 0.010-0.012, in this toggle's own unit -- the
                                         only term that opposes the friction behind the operator's "snapping";
                                         describing-function check: no relay limit cycle below 0.0235 at 4.5 m/s
    SteerLatAccel       6.0 -> 14.0      in the plant-FF branch this scales ONLY P and I: the one lever on the
                                         low-speed loop gain (the hard-coded low-speed factor is ADDED to Kp, so
                                         SteerKP cannot reduce it; as flown PM -11 deg / Ms 12 at 4.5 m/s)
    SteerKP             0.3 -> 0.85      buys the hold stiffness at speed back after the LAF change (the
                                         operator's "loose"); the Ms <= 2 bound at >22 m/s is SteerKP <= 0.92
                                         at LAF 14 (Ms ~ 1/(1 - Kp_norm) with the 0.20-0.24 s dead time)
    AccordTorqueKi      0.15 -> 0.30     the live integral gain is Ki*(1 + lsf/Kp): 3x lower than flown at
                                         4.5 m/s (the wind-up band), 0.6x at speed; the FF now carries what the
                                         integrator's 38 % share was carrying
    KeepLearnedLatAccelOffset True -> False   the learner's offset is a restored cache (liveValid 0 % on route 70),
                                         -0.07 m/s^2; the larger +0.41 m/s^2 term in the command-vs-f gap is ROLL
                                         compensation (a persistent +2.4 deg estimated roll) that no toggle touches
    SteerDelay          0.2 (pinned)     tau_eq 0.19-0.34 s supports 0.20-0.22; not a lever worth a drive

Usage (from anywhere; Python = the bin_decompile conda env, invoked as `python`):
    python tools/make_galaxy_toggle_config.py            # writes the six files under analysis-2020accord/reference/
    python tools/make_galaxy_toggle_config.py --decode <file.json>   # prints a Galaxy backup's contents
"""
import base64
import datetime as _dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REF = os.path.join(KIT, "analysis-2020accord", "reference")

XOR_KEY = "s8#pL3*Xj!aZ@dWq"          # starpilot/system/the_galaxy/utilities.py, verbatim
FORMAT, VERSION = "starpilot-toggle-backup", 1

# ------------------------------------------------------------------------------------------------
# THE TWO CONFIGS.  Edit here and re-run; nothing else carries these numbers.
# ------------------------------------------------------------------------------------------------
TORQUE_MODE = {
    # the switch
    "AccordRatePlantFF": False,
    # the tune (all four PROVISIONAL until the first drive's identification)
    "SteerKP": 0.3,
    "AccordTorqueKi": 0.15,
    "SteerFriction": 0.0,
    "SteerLatAccel": 6.0,
    # pins -- already the operator's values on 2026-09-10 and on route 6f; restated so the file is
    # self-sufficient and the rlog's initData.params reads unambiguously
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "KeepLearnedLatAccelOffset": True,
    "AccordTurnFFTaper": False,
}

# the installed rate-servo tune, exactly as the 2026-09-10 backup and route 6f's initData carry it
RATE_SERVO_REVERT = {
    "AccordRatePlantFF": True,
    "SteerKP": 0.9,
    "AccordTorqueKi": 0.3,
    "SteerFriction": 0.01,
    "SteerLatAccel": 6.0,
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "KeepLearnedLatAccelOffset": True,
    "AccordTurnFFTaper": False,
}

# REV 2 -- the retune from the first V293 drive (route 70).  REQUIRES the fork at or after Dom 66cf4454a
# (the re-identified HONDA_ACCORD_EPS_G_V / K_V tables); on the old tables AccordRatePlantFF True under-holds
# x2.1 above 12 m/s.  Every value is a plain existing param; the scorer reads this file's decoded copy.
TORQUE_MODE_R2 = {
    "AccordRatePlantFF": True,
    "AccordEpsSpringScale": 1.0,
    "AccordEpsGainScale": 1.0,
    "AccordFFRateGain": 0.5,
    "SteerFriction": 0.011,
    "SteerLatAccel": 14.0,
    "SteerKP": 0.85,
    "AccordTorqueKi": 0.3,
    "KeepLearnedLatAccelOffset": False,
    "SteerDelay": 0.2,
    "UseAutoSteerDelay": False,
    # pins, as rev 1
    "ForceAutoTuneOff": True,
    "ForceAutoTune": False,
    "AdvancedLateralTune": True,
    "AccordTurnFFTaper": False,
}

FILES = (
    ("toggle-config_V293_torque_mode", TORQUE_MODE),
    ("toggle-config_V293_torque_mode_r2", TORQUE_MODE_R2),
    ("toggle-config_V282_rate_servo_REVERT", RATE_SERVO_REVERT),
)


def xor_encrypt_decrypt(data, key):
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))


def encode_parameters(params_dict):
    return base64.b64encode(xor_encrypt_decrypt(json.dumps(params_dict), XOR_KEY).encode("utf-8")).decode("utf-8")


def decode_parameters(encoded):
    return json.loads(xor_encrypt_decrypt(base64.b64decode(encoded.encode("utf-8")).decode("utf-8"), XOR_KEY))


def galaxy_file(values):
    return {
        "format": FORMAT,
        "version": VERSION,
        "createdAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "settingsCount": len(values),
        "data": encode_parameters(values),
    }


def positive_control():
    """the codec must reproduce the operator's own backup -> its decoded copy, byte for byte in content."""
    enc = json.load(open(os.path.join(REF, "toggle-backup_latest_20260910.json"), encoding="utf-8"))
    dec = json.load(open(os.path.join(REF, "toggle-backup_latest_20260910.decoded.json"), encoding="utf-8"))
    got = decode_parameters(enc["data"])
    assert got == dec, "codec does not reproduce the operator's 2026-09-10 backup"
    assert enc["format"] == FORMAT and enc["version"] == VERSION and enc["settingsCount"] == len(dec)
    # and the reverse direction: re-encoding the decoded copy must decode back to itself
    assert decode_parameters(encode_parameters(dec)) == dec
    return dec


def main(argv):
    if len(argv) >= 2 and argv[1] == "--decode":
        d = json.load(open(argv[2], encoding="utf-8"))
        print(json.dumps(decode_parameters(d["data"]), indent=1, sort_keys=True))
        return 0
    backup = positive_control()
    print("codec positive control: OK (526-key 2026-09-10 backup round-trips)")
    for stem, values in FILES:
        for k in values:
            assert k in backup, "%s is not a key the operator's backup carries -- typo?" % k
        out = galaxy_file(values)
        assert decode_parameters(out["data"]) == values
        p = os.path.join(REF, stem + ".json")
        json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
        json.dump(values, open(os.path.join(REF, stem + ".decoded.json"), "w", encoding="utf-8"), indent=2)
        changed = {k: (backup[k], v) for k, v in values.items() if backup[k] != v}
        print("wrote %s.json (+ .decoded.json): %d keys; differs from the 2026-09-10 backup in %d: %s"
              % (stem, len(values), len(changed), changed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
