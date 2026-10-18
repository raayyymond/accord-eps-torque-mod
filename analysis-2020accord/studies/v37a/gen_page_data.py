"""studies/v37a/gen_page_data.py -- the numbers on the V37A page, read from the THREE IMAGES through the golden model.

Writes docs/artifacts/v37a/page_data.json and splices it into docs/artifacts/V37A-PAGE-2026-10-17.html between the
<script id="data"> tags.  Runs in ~2 s.  Nothing on the page is typed by hand: every LERP knot, every surface point
and every cell value comes from stock_fw_dump/code.bin, _v37_plain_image.bin and _v37a_plain_image.bin.
"""
import json
import os
import re
import struct
import sys
from dataclasses import replace
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
sys.path.insert(0, str(_d / "model"))
import eps_lkas_chain_model as GM                                                   # noqa: E402

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
R = Path(ROOT) / "analysis-2020accord"
IMGS = {"stock": (R / "stock_fw_dump" / "code.bin").read_bytes(),
        "V37": (R / "_v37_plain_image.bin").read_bytes(),
        "V37A": (R / "_v37a_REV3_plain_image.bin").read_bytes()}
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]      # noqa: E731
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]      # noqa: E731
u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]      # noqa: E731
DEG_PER_SP = 32 / 30.891 / 8          # E units per sp count / fb DC per raw rate count / wire counts per deg/s


def rec(b, p, n):
    return tuple(u16(b, p + 2 + 2 * i) for i in range(n)), tuple(s16(b, p + 2 + 2 * n + 2 * i) for i in range(n))


def cal_of(b):
    live, kp, kd = u32(b, 0xC9A88 + 28), u32(b, 0xCB994 + 28), u32(b, 0xCB7D4 + 28)
    mx, my = rec(b, live, 10)
    kx, ky = rec(b, kp, 5)
    dx, dy = rec(b, kd, 4)
    return replace(GM.Calibration(), assist_map_x=mx, assist_map_y=my, kp_x=kx, kp_y=ky, kd_x=dx, kd_y=dy,
                   fb_clamp=u16(b, 0xC62E6), pid_p_clamp=u16(b, 0xC61BC), sum_clamp=u16(b, 0xC61BE),
                   pid_d_clamp=u16(b, 0xC61B6), pid_i_clamp=u16(b, 0xC61BA), pid_ki=u16(b, 0xC63E6),
                   fb_lag_a=s16(b, 0xC63E8), fb_lag_b=u16(b, 0xC63EA), out_lag_a=s16(b, 0xC63EC),
                   out_lag_b=u16(b, 0xC63EE), lkas_forward_gain=u16(b, 0xC646C), out_clamp=u16(b, 0xC61B4))


out = {"units": {"deg_per_sp": DEG_PER_SP, "wire_per_idx": 16.125736, "fb_dc": 30.891}}
for nm, b in IMGS.items():
    c = cal_of(b)
    rows = [[i, r["sp"], r["P"], r["T"]] for i in range(0, 241, 2) for r in (GM.lkas_rate_pid_surface(i, c),)]
    tvr = []
    sp120 = GM.lkas_rate_lerp(c.assist_map_x, c.assist_map_y, 120)
    for dps in range(0, 141, 2):
        fb = min(int(round(dps * 8 * 30.891)), c.fb_clamp)
        tvr.append([dps, GM.lkas_rate_pid_surface(120, c, fb=fb)["T"]])
    null_rate = {i: round(GM.lkas_rate_lerp(c.assist_map_x, c.assist_map_y, i) * DEG_PER_SP, 1) for i in (12, 32, 60, 120, 240)}
    rail = next((i for i in range(241) if GM.lkas_rate_pid_surface(i, c)["P"] >= c.pid_p_clamp), None)
    out[nm] = dict(map_x=c.assist_map_x, map_y=c.assist_map_y, kp_x=c.kp_x, kp_y=c.kp_y, kd_y=c.kd_y,
                   fb_clamp=c.fb_clamp, gain=c.lkas_forward_gain, out_clamp=c.out_clamp, pack_clamp=u16(b, 0xC61B2),
                   p_clamp=c.pid_p_clamp, rows=rows, t_vs_rate_idx120=tvr, sp120=sp120, null_rate=null_rate, p_rail_idx=rail,
                   fb_clamp_rate=round(c.fb_clamp / 30.891 / 8, 1))
out["sha"] = {}
import hashlib                                                                        # noqa: E402
for nm, b in IMGS.items():
    out["sha"][nm] = hashlib.sha256(b).hexdigest()

here = Path(__file__).resolve().parents[3] / "docs" / "artifacts"
(here / "v37a").mkdir(parents=True, exist_ok=True)
(here / "v37a" / "page_data.json").write_text(json.dumps(out))
page = here / "V37A-PAGE-2026-10-17.html"
if page.exists():
    html = page.read_text(encoding="utf-8")
    html2 = re.sub(r'(<script id="data" type="application/json">).*?(</script>)',
                   lambda m: m.group(1) + json.dumps(out) + m.group(2), html, flags=re.S)
    page.write_text(html2, encoding="utf-8")
    print("spliced into", page)
print(json.dumps({k: (v if k == "units" or k == "sha" else {kk: vv for kk, vv in v.items() if kk not in ("rows", "t_vs_rate_idx120")}) for k, v in out.items()}, indent=1))
