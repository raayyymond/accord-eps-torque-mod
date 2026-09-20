import sys
from pathlib import Path
KIT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(KIT / "rlog-tools" / "lib"))
from rlog_parse import read_messages
p = KIT / "analysis-2020accord" / "rlogs" / "75604b0a432fdc89_0000006e--6ca3e014fd--3--rlog.zst"
cnt = {}; n = 0
for e in read_messages(p):
    try: w = e.which()
    except Exception: continue
    if w == 'can':
        n += 1
        for m in e.can:
            if m.address in (0x14A, 0xE4, 0x18F, 0x156):
                key = (hex(m.address), m.src); cnt[key] = cnt.get(key, 0) + 1
                if m.address == 0x14A and cnt[key] < 3: print(key, bytes(m.dat).hex())
        if n > 3000: break
print(cnt)
