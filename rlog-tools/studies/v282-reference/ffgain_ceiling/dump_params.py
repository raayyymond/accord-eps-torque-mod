# -*- coding: utf-8 -*-
"""Dump the flown fork toggles (initData params) for every V293 torque-mode route, plus route 70.

Every constant the feedforward reconstruction needs must come from the LOG, not from the current
fork HEAD: the routes flew different revs.  An ABSENT key is printed as ABSENT so a default is
never silently assumed.

ANALYSIS ONLY.  Run: python dump_params.py
"""
import io, json, os, re, sys
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [
    ("r70_ident", "75604b0a432fdc89_00000070--717f5a7866"),
    ("r71",       "75604b0a432fdc89_00000071--f2c9d073a3"),
    ("r74",       "75604b0a432fdc89_00000074--2bf17ca67d"),
    ("r75_rev4",  "75604b0a432fdc89_00000075--6c8687d5bd"),
    ("r76_rev5",  "75604b0a432fdc89_00000076--d0b7ea7e4d"),
    ("r6c_T64",   "75604b0a432fdc89_0000006c--68c6e94b17"),
    ("r6d_T64",   "75604b0a432fdc89_0000006d--05e83bb04f"),
    ("r6e_T64B",  "75604b0a432fdc89_0000006e--6ca3e014fd"),
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
            k = ent.key
            try:
                v = bytes(ent.value).decode("utf-8", "replace")
            except Exception:
                v = "<bin>"
            out[k] = v[:80]
        return out, None
    return None, "no initData in first %d events" % n


ALL = {}
for tag, prefix in ROUTES:
    p, err = read_params(prefix)
    if p is None:
        for s in (1, 2):
            p, err = read_params(prefix, s)
            if p is not None:
                break
    if p is None:
        print("%-12s  FAILED: %s" % (tag, err), flush=True)
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

with open(os.path.join(HERE, "flown_params.json"), "w") as fh:
    json.dump(ALL, fh, indent=1, sort_keys=True)
print("\nwrote flown_params.json", flush=True)
