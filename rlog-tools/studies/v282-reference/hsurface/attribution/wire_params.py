# -*- coding: utf-8 -*-
"""Read the flown fork config for the V282 REFERENCE routes (and the V282old group) from each route's
own initData -- the brief's 'attribute the build from the wire'.  The torque-mode routes are already
dumped in ffgain_ceiling/flown_params.json; this fills the reference side, which nothing had read.

ANALYSIS ONLY: reads rlogs, writes one json in this folder.
"""
import io, json, os, re, sys
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [
    ("r64_V282", "75604b0a432fdc89_00000064--ce6b0b0ebb"),
    ("r65_V282", "75604b0a432fdc89_00000065--b9f78988bd"),
    ("r6c_V282", "75604b0a432fdc89_0000006c--2bc842dbac"),
    ("r39_V282old", "75604b0a432fdc89_00000039--f56039af87"),
    ("r3a_V282old", "75604b0a432fdc89_0000003a--283a39a1d6"),
    ("r3c_V282old", "75604b0a432fdc89_0000003c--927965c2b4"),
]
WANT = ["AccordRatePlantFF", "AccordFFRateGain", "AccordHoldMap", "AccordHoldLevel",
        "AccordFrictionHyst", "AccordFrictionHystBand", "AccordRateLoopGain", "AccordDobHz",
        "AccordEpsGainScale", "AccordEpsSpringScale", "AccordVariableSteerRatio",
        "AccordTorqueKi", "AccordTorqueKiHigh", "AccordRefFilter", "AccordJerkLpHz",
        "AccordCurvatureLead", "AccordCurvatureLeadGain", "AccordTurnFFTaper",
        "SteerRatio", "CustomSteerRatio", "SteerLatAccel", "CustomLatAccel", "SteerFriction",
        "CustomFriction", "SteerKP", "CustomSteerKP", "ForceAutoTune", "ForceTorqueController",
        "GitCommit", "GitBranch"]
PAT = re.compile(r"Accord|Steer|LatAccel|Friction|Torque|Force|Curvature|Custom|GitCommit", re.I)


def read_params(prefix, seg=0):
    path = os.path.join(RLOGS, "%s--%d--rlog.zst" % (prefix, seg))
    if not os.path.exists(path):
        return None, "no seg %d" % seg
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    try:
        it = clog.Event.read_multiple_bytes(data)
    except Exception as e:
        return None, "read fail %s" % e
    n = 0
    while n < 4000:
        n += 1
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            break
        try:
            if evt.which() != "initData":
                continue
        except Exception:
            continue
        out = {}
        for ent in evt.initData.params.entries:
            try:
                v = bytes(ent.value).decode("utf-8", "replace")
            except Exception:
                v = "<bin>"
            out[ent.key] = v[:80]
        return out, None
    return None, "no initData in first %d events" % n


ALL = {}
for tag, prefix in ROUTES:
    p, err = None, "not tried"
    for s in (0, 1, 2):
        p, err = read_params(prefix, s)
        if p is not None:
            break
    if p is None:
        print("%-14s FAILED: %s" % (tag, err), flush=True)
        continue
    ALL[tag] = p
    print("\n=== %s  (%s)  %d params ===" % (tag, prefix, len(p)), flush=True)
    for k in WANT:
        print("   %-26s %s" % (k, p.get(k, "ABSENT")), flush=True)
    extra = sorted(k for k in p if PAT.search(k) and k not in WANT)
    if extra:
        print("   -- other matching keys --", flush=True)
        for k in extra:
            print("   %-26s %s" % (k, p[k]), flush=True)

with open(os.path.join(HERE, "out", "v282_wire_params.json"), "w") as fh:
    json.dump(ALL, fh, indent=1, sort_keys=True)
print("\nwrote out/v282_wire_params.json", flush=True)
