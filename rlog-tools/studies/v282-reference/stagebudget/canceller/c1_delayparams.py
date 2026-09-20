# -*- coding: utf-8 -*-
"""c1: what D really was on each flown route -- toggle or learned?

Reads each route's OWN initData params for the delay-related keys, so "D" is attributed from the wire,
never from a label.  ANALYSIS ONLY (read of cached rlogs).   usage: python c1_delayparams.py
"""
import io, json, os, sys
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
          "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000070--717f5a7866", "00000071--f2c9d073a3", "00000072--8001fc3048",
          "00000073--79fd149dd8", "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]

WANT = ["SteerDelay", "SteerDelayStock", "UseAutoSteerDelay", "SteerDelayModeMigrated",
        "AdvancedLateralTune", "AccordRefFilter", "AccordJerkLpHz", "LiveDelay", "GitCommit"]


def read_params(route, seg):
    path = os.path.join(RLOGS, "75604b0a432fdc89_%s--%d--rlog.zst" % (route, seg))
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    try:
        it = clog.Event.read_multiple_bytes(data)
    except Exception:
        return None
    n = 0
    while n < 6000:
        n += 1
        try:
            evt = next(it)
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
                k = ent.key
            except Exception:
                continue
            if k not in WANT:
                continue
            try:
                v = bytes(ent.value)
            except Exception:
                v = b""
            if k == "LiveDelay":
                out[k] = "<%d bytes capnp>" % len(v)
                out["_LiveDelay_raw"] = v.hex()
            else:
                try:
                    out[k] = v.decode("utf-8", "replace").strip()
                except Exception:
                    out[k] = repr(v)
        return out
    return None


def main():
    res = {}
    for r in ROUTES:
        got = None
        for seg in range(0, 4):
            got = read_params(r, seg)
            if got:
                break
        res[r] = got or {}
        keys = res[r]
        print("%-22s SteerDelay=%-8s Stock=%-8s UseAuto=%-6s AdvLat=%-4s Migrated=%-6s RefFilter=%-6s JerkLp=%-6s LiveDelay=%s" % (
            r, keys.get("SteerDelay", "ABSENT"), keys.get("SteerDelayStock", "ABSENT"),
            keys.get("UseAutoSteerDelay", "ABSENT"), keys.get("AdvancedLateralTune", "ABSENT"),
            keys.get("SteerDelayModeMigrated", "ABSENT"), keys.get("AccordRefFilter", "ABSENT"),
            keys.get("AccordJerkLpHz", "ABSENT"), keys.get("LiveDelay", "ABSENT")))
    with open(os.path.join(HERE, "c1_delayparams.json"), "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
