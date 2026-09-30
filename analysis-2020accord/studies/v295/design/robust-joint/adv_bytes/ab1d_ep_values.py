exec(open(__file__.replace("ab1d_ep_values.py", "ab1_bytes.py")).read().split("ALL = list(scan(img))")[0])
ALL = list(scan(img))
vals = sorted({d[3] for o, d in ALL if d[0] == "mov32" and (u16(img, o) & 0x1F) == 30})
print(len(vals), [hex(v) for v in vals if not (0xFE000000 <= v)])
