"""Probe one segment: event types, can src/address counts, batch structure, busTime usage."""
import sys
from collections import Counter, defaultdict
from pathlib import Path
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
import rlog_parse
p = KIT / "analysis-2020accord" / "rlogs" / sys.argv[1]
wc = Counter(); addr = Counter(); send = Counter(); bt = []
nb_per_evt = []
first = {}
for i, e in enumerate(rlog_parse.read_messages(p)):
    try:
        w = e.which()
    except Exception:
        w = "?"
    wc[w] += 1
    if w == "can":
        nb_per_evt.append(len(e.can))
        for m in e.can:
            addr[(int(m.address), int(m.src))] += 1
            if len(bt) < 40: bt.append((e.logMonoTime, int(m.address), int(m.src)))
    elif w == "sendcan":
        for m in e.sendcan:
            send[(int(m.address), int(m.src))] += 1
    if w in ("carState", "controlsState", "carControl", "sendcan") and w not in first:
        first[w] = str(getattr(e, w))[:3000]
print(wc.most_common(40))
print("can frames/evt", Counter(nb_per_evt).most_common(5))
for k, v in sorted(addr.items()):
    if k[0] in (0xE4, 0x14A, 0x18F, 0x1AB, 0x156, 0xE5, 0x1FA, 0x33D) or k[1] >= 128:
        print(hex(k[0]), k[1], v)
print("sendcan", {(hex(a), s): v for (a, s), v in send.items()})
print(bt[:20])
for k, v in first.items():
    print("=====", k); print(v)
